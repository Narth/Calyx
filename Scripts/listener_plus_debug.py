import time, numpy as np
from scipy.signal import resample_poly
from faster_whisper import WhisperModel
import sounddevice as sd, yaml

CFG = yaml.safe_load(open(r"C:\Calyx_Terminal\config.yaml","r",encoding="utf-8"))["settings"]
DEV         = int(CFG.get("mic_device_index", -1))
SR          = int(CFG.get("samplerate", 44100))
CHUNK_MS    = int(CFG.get("chunk_ms", 1000))
OVERLAP_MS  = int(CFG.get("overlap_ms", 500))
# OVERRIDES for debug (make it more sensitive + talkative)
SIL_GATE    = float(CFG.get("silence_gate", 0.025))
SIL_GATE    = min(SIL_GATE, 0.03)     # clamp lower
GAIN_CAP    = float(CFG.get("gain_cap", 3.0))
GAIN_CAP    = max(GAIN_CAP, 4.0)      # ensure some boost
BEAM_SIZE   = int(CFG.get("beam_size", 5))
BEST_OF     = int(CFG.get("best_of", 5))
TEMP        = float(CFG.get("temperature", 0.0))

print(f"[DBG] dev={DEV} sr={SR} chunk={CHUNK_MS}ms overlap={OVERLAP_MS}ms gate={SIL_GATE:.4f} gain_cap={GAIN_CAP}")
model = WhisperModel(CFG.get("model_size","tiny"), device=CFG.get("faster_whisper_device","cpu"),
                     compute_type=CFG.get("faster_whisper_compute_type","float32"))

chunk = max(1024, int(SR * (CHUNK_MS/1000.0)))
hop   = max(512,  int(SR * (max(0,CHUNK_MS-OVERLAP_MS)/1000.0)))

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
    # 5) resample to 16k
    x16 = resample_poly(gated, 16000, SR).astype("float32")
    return x16, rms, mean_abs, nz, ratio

def transcribe(x16):
    segs, info = model.transcribe(
        x16, language="en",
        beam_size=BEAM_SIZE, best_of=BEST_OF, temperature=TEMP,
        vad_filter=False,                       # DEBUG: off (see raw)
        no_speech_threshold=0.5,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0
    )
    txt = "".join(s.text for s in segs).strip()
    return txt

print("[DBG] starting… speak 2–3s phrases; Ctrl+C to stop.")
last_log = time.time()
backlog = np.zeros(0, dtype=np.float32)
read_size = hop

try:
    with sd.InputStream(device=DEV, channels=1, samplerate=SR, dtype="float32", blocksize=read_size) as st:
        while True:
            data, _ = st.read(read_size)
            x = data[:,0]
            backlog = np.concatenate([backlog, x])
            if backlog.size >= chunk:
                window = backlog[-chunk:]
                backlog = backlog[-chunk:]  # keep sliding window

                x16, rms, mean_abs, nz, ratio = preprocess(window)
                now = time.time()
                if now - last_log > 0.5:
                    print(f"[VU] rms={rms:.4f} mean|x|={mean_abs:.4f} nz={nz}/{len(window)} ({ratio:.2%})")
                    last_log = now

                if nz < 200:
                    print("[DBG] gated silence (skip)")
                    continue

                txt = transcribe(x16)
                safe = txt.encode("ascii","ignore").decode("ascii")
                print(f"[Heard] {safe!r}" if safe else "[Heard] ''")
except KeyboardInterrupt:
    print("\n[DBG] stopped.")
