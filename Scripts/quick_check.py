import sounddevice as sd, numpy as np
from _resample_safe import resample_poly
from faster_whisper import WhisperModel
import yaml, pathlib, time

cfg = yaml.safe_load(open(r"C:\Calyx_Terminal\config.yaml", "r", encoding="utf-8"))["settings"]
sr = int(cfg.get("samplerate", 44100)); dev = int(cfg.get("mic_device_index", -1))
print(f"[Check] Recording 5s @ {sr} Hz from device {dev}...")
data = sd.rec(int(5*sr), samplerate=sr, channels=1, dtype="float32", device=dev, blocking=True)
x = data[:,0]
rms = float(np.sqrt((x**2).mean())+1e-12)
print(f"[Check] RMS={rms:.4f}")
# gate + light preemphasis + normalize
x = x * min(cfg.get("gain_cap",3.0), max(1.0, 0.1/cfg.get("silence_gate",0.025)))
x = np.where(np.abs(x) < cfg.get("silence_gate",0.025), 0.0, x)
x = np.append(x[0], x[1:] - 0.97*x[:-1])
x = x / (np.max(np.abs(x))+1e-12)
# resample to 16k for Whisper
x16 = resample_poly(x, 16000, sr).astype("float32")
model = WhisperModel(cfg.get("model_size","base"), device="cpu", compute_type=cfg.get("faster_whisper_compute_type","float32"))
segs, info = model.transcribe(x16, language="en", beam_size=cfg.get("beam_size",1), best_of=cfg.get("best_of",1), temperature=cfg.get("temperature",0.0), vad_filter=False)
txt = "".join(s.text for s in segs).strip()
print("[Check] Transcript:", repr(txt))
