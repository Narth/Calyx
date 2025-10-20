import sys, time, pathlib, yaml, numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from faster_whisper import WhisperModel

CFG = yaml.safe_load(open(r"C:\Calyx_Terminal\config.yaml","r",encoding="utf-8"))["settings"]

DEV         = int(CFG.get("mic_device_index", -1))
SR          = int(CFG.get("samplerate", 44100))
CHUNK_MS    = int(CFG.get("chunk_ms", 1000))
OVERLAP_MS  = int(CFG.get("overlap_ms", 500))
SIL_GATE    = float(CFG.get("silence_gate", 0.025))
GAIN_CAP    = float(CFG.get("gain_cap", 3.0))

BEAM_SIZE   = int(CFG.get("beam_size", 5))
BEST_OF     = int(CFG.get("best_of", 5))
TEMP        = float(CFG.get("temperature", 0.0))

print(f"[Plus] Device={DEV} SR={SR} chunk={CHUNK_MS}ms overlap={OVERLAP_MS}ms gate={SIL_GATE} gain_cap={GAIN_CAP}")
print(f"[Plus] Decoding: beam_size={BEAM_SIZE} best_of={BEST_OF} temperature={TEMP}")
model = WhisperModel(CFG.get("model_size","small"), device=CFG.get("faster_whisper_device","cpu"),
                     compute_type=CFG.get("faster_whisper_compute_type","float32"))

chunk = max(1024, int(SR * (CHUNK_MS/1000.0)))
hop   = max(512,  int(SR * (max(0,CHUNK_MS-OVERLAP_MS)/1000.0)))

buf = np.zeros(chunk, dtype=np.float32)
read_size = hop

def preprocess(x):
    # apply gain based on gate
    gain = min(GAIN_CAP, max(1.0, 0.1 / max(1e-9, SIL_GATE)))
    x = x * gain
    # gate low-level noise
    x = np.where(np.abs(x) < SIL_GATE, 0.0, x)
    # light pre-emphasis
    if len(x) > 1:
        x = np.append(x[0], x[1:] - 0.97*x[:-1])
    # normalize (avoid division by zero)
    mx = np.max(np.abs(x)) + 1e-9
    x = x / mx
    # resample to 16k for Whisper
    x16 = resample_poly(x, 16000, SR).astype("float32")
    return x16

def transcribe_chunk(x16):
    # Use tighter defaults to reduce hallucinations
    segs, info = model.transcribe(
        x16,
        language="en",
        beam_size=BEAM_SIZE,
        best_of=BEST_OF,
        temperature=TEMP,
        vad_filter=True,                    # drop non-speech
        no_speech_threshold=0.5,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0
    )
    txt = "".join(s.text for s in segs).strip()
    return txt

print("[Plus] Starting. Speak briefly and clearly. Ctrl+C to stop.")
try:
    with sd.InputStream(device=DEV, channels=1, samplerate=SR, dtype="float32",
                        blocksize=read_size) as stream:
        backlog = np.zeros(0, dtype=np.float32)
        last_print = time.time()
        while True:
            data, _ = stream.read(read_size)
            x = data[:,0].copy()
            # Roll into a sliding window (chunk length), 50% overlap by default
            backlog = np.concatenate([backlog, x])
            if backlog.size >= chunk:
                window = backlog[-chunk:]
                backlog = backlog[-chunk:]  # keep last chunk worth for overlap building
                # RMS meter every ~0.5s just for sanity
                if time.time() - last_print > 0.5:
                    rms = float(np.sqrt((window**2).mean()) + 1e-12)
                    print(f"[VU] rms={rms:.4f}")
                    last_print = time.time()
                x16 = preprocess(window)
                if np.count_nonzero(x16) < 200:  # almost all gated = skip
                    continue
                txt = transcribe_chunk(x16)
                if txt:
                    # ASCII-print to dodge Windows console encoding surprises
                    safe = txt.encode("ascii","ignore").decode("ascii")
                    print(f"[Heard] {safe}")
except KeyboardInterrupt:
    print("\n[Plus] Stopped by user.")
