import time, sys, numpy as np
from faster_whisper import WhisperModel
import sounddevice as sd, yaml

def log(*a, **k):
    print(*a, **k); sys.stdout.flush()

CFG = yaml.safe_load(open(r"C:\Calyx_Terminal\config.yaml","r",encoding="utf-8"))["settings"]
DEV         = int(CFG.get("mic_device_index", -1))
SR_IN       = int(CFG.get("samplerate", 44100))   # hardware capture rate
SR_OUT      = 16000                                # whisper expects ~16k
CHUNK_MS    = int(CFG.get("chunk_ms", 1000))
OVERLAP_MS  = int(CFG.get("overlap_ms", 500))

SIL_GATE    = float(CFG.get("silence_gate", 0.025))
SIL_GATE    = min(SIL_GATE, 0.03)
GAIN_CAP    = float(CFG.get("gain_cap", 3.0))
GAIN_CAP    = max(GAIN_CAP, 4.0)
BEAM_SIZE   = int(CFG.get("beam_size", 5))
BEST_OF     = int(CFG.get("best_of", 5))
TEMP        = float(CFG.get("temperature", 0.0))

log(f"[DBG] dev={DEV} sr_in={SR_IN} sr_out={SR_OUT} chunk={CHUNK_MS}ms overlap={OVERLAP_MS}ms gate={SIL_GATE:.4f} gain_cap={GAIN_CAP}")

model = WhisperModel(CFG.get("model_size","tiny"),
                     device=CFG.get("faster_whisper_device","cpu"),
                     compute_type=CFG.get("faster_whisper_compute_type","float32"))

chunk = max(1024, int(SR_IN * (CHUNK_MS/1000.0)))
hop   = max(512,  int(SR_IN * (max(0,CHUNK_MS-OVERLAP_MS)/1000.0)))

def np_resample_linear(x, sr_in, sr_out):
    """Simple, stable linear resampler (SciPy-free)."""
    if len(x) == 0 or sr_in == sr_out:
        return x.astype("float32", copy=False)
    dur_s = len(x) / float(sr_in)
    n_out = max(1, int(round(dur_s * sr_out)))
    t_in  = np.linspace(0.0, dur_s, num=len(x), endpoint=False, dtype=np.float64)
    t_out = np.linspace(0.0, dur_s, num=n_out, endpoint=False, dtype=np.float64)
    y = np.interp(t_out, t_in, x).astype("float32", copy=False)
    return y

def preprocess(x):
    # 1) gain based on gate
    gain = min(GAIN_CAP, max(1.0, 0.1 / max(1e-9, SIL_GATE)))
    x = x * gain
    # 2) measure stats BEFORE gate
    rms = float(np.sqrt((x**2).mean()) + 1e-12)
    mean_abs = float(np.mean(np.abs(x)))
    # 3) gate
    gated = np.where(np.abs(x) < SIL_GATE, 0.0, x)
    nz = int(np.count_nonzero(gated))
    ratio = nz / max(1,len(gated))
    # 4) pre-emphasis + norm
    if len(gated) > 1:
        gated = np.append(gated[0], gated[1:] - 0.97*gated[:-1])
    mx = np.max(np.abs(gated)) + 1e-9
    gated = gated / mx
    # 5) resample to 16k (SciPy-free)
    x16 = np_resample_linear(gated.astype("float32", copy=False), SR_IN, SR_OUT)
    return x16, rms, mean_abs, nz, ratio

def transcribe(x16):
    segs, info = model.transcribe(
        x16, language="en",
        beam_size=BEAM_SIZE, best_of=BEST_OF, temperature=TEMP,
        vad_filter=False,
        no_speech_threshold=0.5,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0
    )
    txt = "".join(s.text for s in segs).strip()
    return txt

log("[DBG] starting… speak 2–3s phrases; Ctrl+C to stop.")
last_log = time.time()
backlog = np.zeros(0, dtype=np.float32)
read_size = hop

try:
    with sd.InputStream(device=DEV, channels=1, samplerate=SR_IN, dtype="float32", blocksize=read_size) as st:
        while True:
            data, _ = st.read(read_size)
            x = data[:,0]
            backlog = np.concatenate([backlog, x])
            if backlog.size >= chunk:
                window = backlog[-chunk:]
                backlog = backlog[-chunk:]

                x16, rms, mean_abs, nz, ratio = preprocess(window)
                now = time.time()
                if now - last_log > 0.5:
                    log(f"[VU] rms={rms:.4f} mean|x|={mean_abs:.4f} nz={nz}/{len(window)} ({ratio:.2%})")
                    last_log = now

                if nz < 200:
                    log("[DBG] gated silence (skip)")
                    continue

                txt = transcribe(x16)
                safe = txt.encode("ascii","ignore").decode("ascii")
                log(f"[Heard] {safe!r}" if safe else "[Heard] ''")
except KeyboardInterrupt:
    log("\n[DBG] stopped.")
