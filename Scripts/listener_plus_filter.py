import time, sys, numpy as np
from faster_whisper import WhisperModel
import sounddevice as sd, yaml

def log(*a, **k):
    print(*a, **k); sys.stdout.flush()

CFG = yaml.safe_load(open(r"C:\Calyx_Terminal\config.yaml","r",encoding="utf-8"))["settings"]
DEV         = int(CFG.get("mic_device_index", -1))
SR_IN       = int(CFG.get("samplerate", 44100))
SR_OUT      = 16000
CHUNK_MS    = int(CFG.get("chunk_ms", 1000))
OVERLAP_MS  = int(CFG.get("overlap_ms", 500))

# Tighten gates
SIL_GATE    = float(CFG.get("silence_gate", 0.025))
SIL_GATE    = max(0.05, min(0.08, SIL_GATE))      # slightly higher static floor
GAIN_CAP    = min(2.5, float(CFG.get("gain_cap", 3.0)))  # a bit less boost to avoid false triggers

# Decoding: conservative
BEAM_SIZE   = 1
BEST_OF     = 1
TEMP        = 0.0

log(f"[DBG] dev={DEV} sr_in={SR_IN} sr_out={SR_OUT} chunk={CHUNK_MS}ms overlap={OVERLAP_MS}ms gate={SIL_GATE:.4f} gain_cap={GAIN_CAP}")

model = WhisperModel(CFG.get("model_size","tiny"),
                     device=CFG.get("faster_whisper_device","cpu"),
                     compute_type=CFG.get("faster_whisper_compute_type","float32"))

chunk = max(1024, int(SR_IN * (CHUNK_MS/1000.0)))
hop   = max(512,  int(SR_IN * (max(0,CHUNK_MS-OVERLAP_MS)/1000.0)))

def np_resample_linear(x, sr_in, sr_out):
    if len(x) == 0 or sr_in == sr_out:
        return x.astype("float32", copy=False)
    dur_s = len(x) / float(sr_in)
    n_out = max(1, int(round(dur_s * sr_out)))
    t_in  = np.linspace(0.0, dur_s, num=len(x), endpoint=False, dtype=np.float64)
    t_out = np.linspace(0.0, dur_s, num=n_out, endpoint=False, dtype=np.float64)
    return np.interp(t_out, t_in, x).astype("float32", copy=False)

# Rolling noise floor (EMA)
noise_rms = 0.0
alpha = 0.95  # smoothing

def preprocess(x):
    global noise_rms
    x = x * min(GAIN_CAP, max(1.0, 0.1 / max(1e-9, SIL_GATE)))
    rms = float(np.sqrt((x**2).mean()) + 1e-12)
    noise_rms = alpha*noise_rms + (1-alpha)*rms if noise_rms>0 else rms

    # dynamic gate: above both absolute SIL_GATE and 3x noise floor
    dyn_gate = max(SIL_GATE, 3.0*noise_rms)
    gated = np.where(np.abs(x) < dyn_gate, 0.0, x)
    nz = int(np.count_nonzero(gated))
    ratio = nz / max(1,len(gated))

    if len(gated) > 1:
        gated = np.append(gated[0], gated[1:] - 0.97*gated[:-1])
    mx = np.max(np.abs(gated)) + 1e-9
    gated = gated / mx
    x16 = np_resample_linear(gated.astype("float32", copy=False), SR_IN, SR_OUT)
    return x16, rms, nz, ratio, dyn_gate

def transcribe(x16):
    segs, info = model.transcribe(
        x16, language="en",
        beam_size=BEAM_SIZE, best_of=BEST_OF, temperature=TEMP,
        vad_filter=True,
        vad_parameters=dict(
            silero_threshold=0.70,          # pickier
            min_speech_duration_ms=350,
            max_speech_duration_s=10,
            speech_pad_ms=100
        ),
        condition_on_previous_text=False,   # avoid run-on hallucinations
        no_speech_threshold=0.75,
        compression_ratio_threshold=2.0,
        log_prob_threshold=-0.12,
    )
    txt = "".join(s.text for s in segs).strip()
    # reject ultra-short or boilerplate starts when short
    bad_starts = ("hello everyone", "welcome to my channel", "today i'm going to")
    if txt and (len(txt) < 6 or txt.lower().startswith(bad_starts) and len(txt.split()) < 15):
        return ""
    return txt

log("[DBG] starting… speak 2–3s phrases; Ctrl+C to stop.")
last_log = time.time()
backlog = np.zeros(0, dtype=np.float32)
read_size = hop

# Require decent activity before decode + simple cooldown
MIN_NZ_RATIO = 0.15
COOLDOWN_S   = 1.0
last_emit    = 0.0

try:
    with sd.InputStream(device=DEV, channels=1, samplerate=SR_IN, dtype="float32", blocksize=read_size) as st:
        while True:
            data, _ = st.read(read_size)
            x = data[:,0]
            backlog = np.concatenate([backlog, x])
            if backlog.size >= chunk:
                window = backlog[-chunk:]
                backlog = backlog[-chunk:]

                x16, rms, nz, ratio, dyn_gate = preprocess(window)
                now = time.time()
                if now - last_log > 0.5:
                    log(f"[VU] rms={rms:.4f} nz_ratio={ratio:.2%} dyn_gate={dyn_gate:.4f}")
                    last_log = now

                if ratio < MIN_NZ_RATIO:
                    log("[DBG] gated silence/room noise (skip)")
                    continue

                if (now - last_emit) < COOLDOWN_S:
                    log("[DBG] cooldown (skip)")
                    continue

                txt = transcribe(x16)
                if txt:
                    log(f"[Heard] {txt!r}")
                    last_emit = now
                else:
                    log("[Heard] ''")
except KeyboardInterrupt:
    log("\n[DBG] stopped.")
