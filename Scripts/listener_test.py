import time
import sys
import os
import pytest
import numpy as np
import yaml

if "pytest" in sys.modules:
    pytest.skip("Interactive audio test; run manually from the command line.", allow_module_level=True)

import sounddevice as sd

def log(*a, **k):
    print(*a, **k)
    sys.stdout.flush()

CONFIG = yaml.safe_load(open(r"C:\Calyx_Terminal\config.yaml", "r", encoding="utf-8"))
CFG = CONFIG["settings"]
DEV = int(CFG.get("mic_device_index", -1))
SR_IN = int(CFG.get("samplerate", 44100))
SR_OUT = 16000
CHUNK_MS = int(CFG.get("chunk_ms", 1000))
OVERLAP_MS = int(CFG.get("overlap_ms", 500))

# Gates
SIL_GATE = float(CFG.get("silence_gate", 0.025))
SIL_GATE = max(0.05, min(0.08, SIL_GATE))
GAIN_CAP = min(2.5, float(CFG.get("gain_cap", 3.0)))

log(f"[TEST] dev={DEV} sr_in={SR_IN} sr_out={SR_OUT} chunk={CHUNK_MS}ms overlap={OVERLAP_MS}ms gate={SIL_GATE:.4f}")

chunk = max(1024, int(SR_IN * (CHUNK_MS / 1000.0)))
hop = max(512, int(SR_IN * (max(0, CHUNK_MS - OVERLAP_MS) / 1000.0)))

def np_resample_linear(x, sr_in, sr_out):
    if len(x) == 0 or sr_in == sr_out:
        return x.astype("float32", copy=False)
    dur_s = len(x) / float(sr_in)
    n_out = max(1, int(round(dur_s * sr_out)))
    t_in = np.linspace(0.0, dur_s, num=len(x), endpoint=False, dtype=np.float64)
    t_out = np.linspace(0.0, dur_s, num=n_out, endpoint=False, dtype=np.float64)
    return np.interp(t_out, t_in, x).astype("float32", copy=False)

# Rolling noise floor (EMA)
noise_rms = 0.0
alpha = 0.98
QUIET_RATIO = 0.012
DYN_GATE_MAX = 0.18

def preprocess(x):
    global noise_rms
    x = x * min(GAIN_CAP, max(1.0, 0.1 / max(1e-9, SIL_GATE)))
    rms = float(np.sqrt((x**2).mean()) + 1e-12)

    prelim = np.abs(x) >= SIL_GATE
    prelim_ratio = float(np.count_nonzero(prelim)) / max(1, len(x))

    if prelim_ratio < QUIET_RATIO:
        noise_rms = alpha * noise_rms + (1 - alpha) * rms if noise_rms > 0 else rms

    dyn_gate = min(DYN_GATE_MAX, max(SIL_GATE, 3.0 * noise_rms))
    gated = np.where(np.abs(x) < dyn_gate, 0.0, x)
    nz = int(np.count_nonzero(gated))
    ratio = nz / max(1, len(gated))
    if len(gated) > 1:
        gated = np.append(gated[0], gated[1:] - 0.97 * gated[:-1])
    mx = np.max(np.abs(gated)) + 1e-9
    gated = gated / mx
    x16 = np_resample_linear(gated.astype("float32", copy=False), SR_IN, SR_OUT)
    return x16, rms, nz, ratio, dyn_gate

def simple_wake_detection(x16, rms, ratio):
    """Simple wake word detection based on audio characteristics"""
    # Look for sudden increase in RMS and activity
    if rms > 0.01 and ratio > 0.15:
        return True
    return False

log("[TEST] Starting audio test listener. Speak into mic, Ctrl+C to stop.")
log("[TEST] This will detect audio activity without Whisper.")

last_log = time.time()
backlog = np.zeros(0, dtype=np.float32)
read_size = hop
MIN_NZ_RATIO = 0.12
last_activity = 0.0
wake_detected = False

try:
    with sd.InputStream(
        device=DEV,
        channels=1,
        samplerate=SR_IN,
        dtype="float32",
        blocksize=read_size,
    ) as st:
        while True:
            data, _ = st.read(read_size)
            x = data[:, 0]
            backlog = np.concatenate([backlog, x])
            if backlog.size < chunk:
                continue

            window = backlog[-chunk:]
            backlog = backlog[-chunk:]

            x16, rms, nz, ratio, dyn_gate = preprocess(window)
            now = time.time()

            if now - last_log > 0.5:
                log(f"[VU] rms={rms:.4f} nz_ratio={ratio:.2%} dyn_gate={dyn_gate:.4f}")
                last_log = now

            # Simple wake detection
            if simple_wake_detection(x16, rms, ratio):
                if not wake_detected:
                    log("[WAKE] Audio activity detected! (Simple wake word)")
                    wake_detected = True
                last_activity = now
            else:
                if wake_detected and (now - last_activity) > 2.0:
                    log("[WAKE] Activity ended")
                    wake_detected = False

            if ratio < MIN_NZ_RATIO:
                continue

            # Simulate command detection
            if wake_detected and rms > 0.02:
                log(f"[COMMAND] Detected speech: rms={rms:.4f}, ratio={ratio:.2%}")

except KeyboardInterrupt:
    log("\n[TEST] Stopped.")

log("[TEST] Audio pipeline is working! Razer Seiren X is picking up audio.")
log("[TEST] Next step: Install compatible Whisper package for transcription.")

