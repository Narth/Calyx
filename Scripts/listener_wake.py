import time
import sys
import re
import numpy as np
from faster_whisper import WhisperModel
import sounddevice as sd
import yaml

import calyx_console
from command_router import route


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

# Gates (keep tight but practical)
SIL_GATE = float(CFG.get("silence_gate", 0.025))
SIL_GATE = max(0.05, min(0.08, SIL_GATE))
GAIN_CAP = min(2.5, float(CFG.get("gain_cap", 3.0)))

# Decode
BEAM_SIZE = 2
BEST_OF = 2
TEMP = 0.0

WAKE_WORDS = ["aurora", "calyx"]
WAKE_RE = re.compile(r"\b(" + "|".join(map(re.escape, WAKE_WORDS)) + r")\b", re.I)
ARM_WINDOW_S = 8.0
COOLDOWN_S = 1.0
MIN_NZ_RATIO = 0.12
RELEASE_SILENCE_S = 0.8
MAX_CAPTURE_S = ARM_WINDOW_S + 2.0

log(
    f"[DBG] dev={DEV} sr_in={SR_IN} sr_out={SR_OUT} chunk={CHUNK_MS}ms overlap={OVERLAP_MS}ms gate={SIL_GATE:.4f} gain_cap={GAIN_CAP}"
)

model = WhisperModel(
    CFG.get("model_size", "tiny"),
    device=CFG.get("faster_whisper_device", "cpu"),
    compute_type=CFG.get("faster_whisper_compute_type", "float32"),
)

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


def transcribe(x16):
    segs, info = model.transcribe(
        x16,
        language="en",
        beam_size=BEAM_SIZE,
        best_of=BEST_OF,
        temperature=TEMP,
        vad_filter=True,
        vad_parameters=dict(
            threshold=0.70,
            min_speech_duration_ms=300,
            max_speech_duration_s=10,
            min_silence_duration_ms=200,
            speech_pad_ms=100,
        ),
        condition_on_previous_text=False,
        no_speech_threshold=0.75,
        compression_ratio_threshold=2.0,
        log_prob_threshold=-0.12,
    )
    txt = "".join(s.text for s in segs).strip()
    return txt


def handle_text(txt, source="wake"):
    if not txt:
        return
    parts = route(txt)
    if not parts:
        return
    log(f"[Route] {parts}")
    try:
        calyx_console.dispatch(CONFIG, parts, source=source, transcript=txt)
    except Exception as exc:
        log(f"[Route] dispatch error: {exc!r}")


def finalize_capture(buf):
    global last_emit
    if buf.size == 0:
        return None

    x16, rms, nz, ratio, dyn_gate = preprocess(buf)
    if ratio < MIN_NZ_RATIO:
        log("[Wake] capture below activity threshold (skip)")
        return None

    try:
        txt = transcribe(x16)
    except Exception as e:
        log(f"[ASR] error: {e!r}")
        return None

    if txt:
        log(f"[Heard] {txt!r}")
    else:
        log("[Heard] ''")

    last_emit = time.time()
    return txt


log("[DBG] wake listener. Say 'Aurora' or 'Calyx' to arm; Ctrl+C to stop.")
state = "idle"
arm_until = 0.0
last_emit = 0.0
last_log = time.time()
backlog = np.zeros(0, dtype=np.float32)
capture_buf = np.zeros(0, dtype=np.float32)
capture_active = False
last_speech = 0.0
read_size = hop

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
                log(
                    f"[VU] rms={rms:.4f} nz_ratio={ratio:.2%} dyn_gate={dyn_gate:.4f} state={state}"
                )
                last_log = now

            if state == "armed":
                capture_buf = np.concatenate([capture_buf, window])
                max_samples = int(SR_IN * MAX_CAPTURE_S)
                if capture_buf.size > max_samples:
                    capture_buf = capture_buf[-max_samples:]

                if ratio >= MIN_NZ_RATIO:
                    capture_active = True
                    last_speech = now

                should_finish = False
                if capture_active and (now - last_speech) >= RELEASE_SILENCE_S:
                    should_finish = True
                if now >= arm_until:
                    should_finish = True

                if should_finish:
                    if capture_active:
                        txt = finalize_capture(capture_buf)
                        if txt:
                            handle_text(txt, source="wake")
                    else:
                        log("[Wake] no speech detected (idle)")

                    state = "idle"
                    capture_buf = np.zeros(0, dtype=np.float32)
                    capture_active = False
                    last_speech = 0.0
                    arm_until = 0.0
                    log("[Wake] window ended (back to idle)")

                continue

            if ratio < MIN_NZ_RATIO:
                continue

            if (now - last_emit) < COOLDOWN_S:
                continue

            try:
                txt = transcribe(x16)
            except Exception as e:
                log(f"[ASR] error: {e!r}")
                continue

            if not txt:
                continue

            last_emit = now

            if WAKE_RE.search(txt):
                state = "armed"
                arm_until = now + ARM_WINDOW_S
                capture_buf = np.zeros(0, dtype=np.float32)
                capture_active = False
                last_speech = now
                log(f"[Wake] armed by: {txt!r}")
                continue

            handle_text(txt, source="wake")

except KeyboardInterrupt:
    if state == "armed" and capture_active and capture_buf.size:
        txt = finalize_capture(capture_buf)
        if txt:
            handle_text(txt, source="wake")
    log("\n[DBG] stopped.")
