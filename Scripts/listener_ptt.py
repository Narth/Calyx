import time, sys, numpy as np
from faster_whisper import WhisperModel
import sounddevice as sd, yaml
from ctypes import windll  # Windows key state

import calyx_console
from command_router import route

def log(*a, **k):
    print(*a, **k); sys.stdout.flush()

CONFIG = yaml.safe_load(open(r"C:\Calyx_Terminal\config.yaml","r",encoding="utf-8"))
CFG = CONFIG["settings"]
DEV         = int(CFG.get("mic_device_index", -1))
SR_IN       = int(CFG.get("samplerate", 44100))
SR_OUT      = 16000
CHUNK_MS    = int(CFG.get("chunk_ms", 1000))
OVERLAP_MS  = int(CFG.get("overlap_ms", 500))

# Conservative gates
SIL_GATE    = float(CFG.get("silence_gate", 0.025))
SIL_GATE    = max(0.05, min(0.08, SIL_GATE))
GAIN_CAP    = min(2.5, float(CFG.get("gain_cap", 3.0)))

# Decode settings (stable)
BEAM_SIZE   = 2
BEST_OF     = 2
TEMP        = 0.0

# PTT settings
USE_PTT_HOLD   = True   # Hold Space to arm capture
armed_toggle   = False   # press T to toggle arm
# virtual-key codes
VK_SPACE = 0x20
VK_T     = 0x54
user32 = windll.user32

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

# Noise floor (EMA) — update only on quiet frames
noise_rms = 0.0
alpha = 0.98   # slow smoothing
QUIET_RATIO = 0.012  # <1.2% active samples counts as "quiet"
DYN_GATE_MAX = 0.12  # never let dynamic gate exceed this

def preprocess(x):
    global noise_rms
    x = x * min(GAIN_CAP, max(1.0, 0.1 / max(1e-9, SIL_GATE)))
    rms = float(np.sqrt((x**2).mean()) + 1e-12)

    # Measure activity before gating
    prelim = np.abs(x) >= SIL_GATE
    prelim_ratio = float(np.count_nonzero(prelim)) / max(1,len(x))

    # Only adapt noise on quiet frames so speech doesn't inflate the floor
    if prelim_ratio < QUIET_RATIO:
        noise_rms = (alpha*noise_rms + (1-alpha)*rms) if noise_rms>0 else rms

    dyn_gate = min(DYN_GATE_MAX, max(SIL_GATE, 3.0*noise_rms))
    gated = np.where(np.abs(x) < dyn_gate, 0.0, x)

    nz = int(np.count_nonzero(gated))
    ratio = nz / max(1,len(gated))

    # Pre-emphasis + norm
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
            threshold=0.70,
            min_speech_duration_ms=350,
            max_speech_duration_s=10,
            min_silence_duration_ms=200,
            speech_pad_ms=100
        ),
        condition_on_previous_text=False,
        no_speech_threshold=0.75,
        compression_ratio_threshold=2.0,
        log_prob_threshold=-0.12,
    )
    txt = "".join(s.text for s in segs).strip()
    bad_starts = ("hello everyone", "welcome to my channel", "today i'm going to")
    if txt and (len(txt) < 6 or txt.lower().startswith(bad_starts) and len(txt.split()) < 15):
        return ""
    return txt

_prev_t_down = False
def _key_down(vk):
    # high bit set means key is physically down now
    return (user32.GetAsyncKeyState(vk) & 0x8000) != 0

def ptt_state():
    """
    Returns tuple: (armed_now, mode_str)
    - HOLD: armed when Space is physically down
    - TOGGLE: press T to flip armed_toggle (also arms if enabled)
    """
    global armed_toggle, _prev_t_down
    # toggle edge on 'T'
    t_down = _key_down(VK_T)
    if t_down and not _prev_t_down:
        armed_toggle = not armed_toggle
        log(f"[PTT] toggle -> {'ARMED' if armed_toggle else 'idle'}")
    _prev_t_down = t_down

    hold = _key_down(VK_SPACE) if USE_PTT_HOLD else False
    armed_now = hold or armed_toggle
    mode = "PTT" if hold else (f"TOGGLE-{'ARMED' if armed_toggle else 'IDLE'}" if not USE_PTT_HOLD else ("PTT+TOGGLE" if armed_toggle else "PTT"))
    return (armed_now, mode)

log("[DBG] starting. Hold SPACE to talk (or press T to toggle). Ctrl+C to stop.")
last_log = time.time()
backlog = np.zeros(0, dtype=np.float32)
read_size = max(1024, int(SR_IN * 0.20))  # ~200ms blocks = more responsive PTT
MIN_NZ_RATIO = 0.12
COOLDOWN_S   = 0.8
MAX_CAPTURE_S = 8.0
MIN_CAPTURE_S = 0.35
last_emit    = 0.0
capture_buf  = np.zeros(0, dtype=np.float32)
capture_active = False

def emit_capture(buf):
    """Run transcription on the buffered capture once the user releases PTT."""
    global last_emit
    if buf.size == 0:
        return

    min_samples = int(SR_IN * MIN_CAPTURE_S)
    if buf.size < min_samples:
        log("[PTT] capture too short (skip)")
        return

    x16, rms, nz, ratio, dyn_gate = preprocess(buf)
    if ratio < MIN_NZ_RATIO:
        log("[PTT] capture below activity threshold (skip)")
        return

    now = time.time()
    if (now - last_emit) < COOLDOWN_S:
        log("[PTT] cooldown (skip)")
        return

    try:
        txt = transcribe(x16)
    except Exception as e:
        log(f"[ASR] error: {e!r}")
        return

    if txt:
        log(f"[Heard] {txt!r}")
    else:
        log("[Heard] ''")
    last_emit = now
    return txt


def handle_text(txt):
    if not txt:
        return
    parts = route(txt)
    if not parts:
        return
    log(f"[Route] {parts}")
    try:
        calyx_console.dispatch(CONFIG, parts, source="ptt", transcript=txt)
    except Exception as exc:
        log(f"[Route] dispatch error: {exc!r}")

try:
    with sd.InputStream(device=DEV, channels=1, samplerate=SR_IN, dtype="float32",
                        blocksize=read_size, latency='high') as st:
        while True:
            try:
                data, _ = st.read(read_size)
            except Exception as e:
                log(f"[AUDIO] read error: {e!r}")
                time.sleep(0.05)
                continue

            x = data[:,0]
            backlog = np.concatenate([backlog, x])[-chunk:]  # keep last chunk

            x16, rms, nz, ratio, dyn_gate = preprocess(backlog)
            now = time.time()
            # compute PTT state for this tick (no extra voice-activity gating)
            armed_now, mode_str = ptt_state()
            if armed_now:
                if not capture_active:
                    capture_buf = np.zeros(0, dtype=np.float32)
                capture_buf = np.concatenate([capture_buf, x])
                max_samples = int(SR_IN * MAX_CAPTURE_S)
                if capture_buf.size > max_samples:
                    capture_buf = capture_buf[-max_samples:]
                capture_active = True
            else:
                if capture_active:
                    txt = emit_capture(capture_buf)
                    if txt:
                        handle_text(txt)
                    capture_buf = np.zeros(0, dtype=np.float32)
                    capture_active = False

            if now - last_log > 0.5:
                log(f"[VU] rms={rms:.4f} nz_ratio={ratio:.2%} dyn_gate={dyn_gate:.4f} mode={mode_str}")
                last_log = now

            if not armed_now:
                continue

            # While armed we just keep buffering; ratio info is still useful for VU logs.
            if ratio < MIN_NZ_RATIO:
                continue

except KeyboardInterrupt:
    if capture_active and capture_buf.size:
        txt = emit_capture(capture_buf)
        if txt:
            handle_text(txt)
    log("\n[DBG] stopped.")
