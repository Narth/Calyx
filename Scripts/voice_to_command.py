# Voice → Command v1.3 (probe + VU + verbose; resample to 16k)
import yaml, queue, sys, pathlib, subprocess, time
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from command_router import route

ROOT = pathlib.Path(__file__).resolve().parents[0].parents[0]
CONFIG_PATH = ROOT / "config.yaml"
SCRIPTS_DIR = ROOT / "Scripts"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def resample_to_16k(audio: np.ndarray, src_rate: int) -> np.ndarray:
    dst_rate = 16000
    if src_rate == dst_rate or len(audio) == 0:
        return audio.astype(np.float32, copy=False)
    duration = len(audio) / float(src_rate)
    dst_len = max(1, int(duration * dst_rate))
    src_idx = np.linspace(0, len(audio) - 1, num=dst_len)
    return np.interp(src_idx, np.arange(len(audio)), audio).astype(np.float32)

def pick_stream_params(mic_index: int | None):
    # prefer user's mic, then default input, then any input
    cand_devices = []
    if mic_index is not None:
        cand_devices.append(mic_index)
    try:
        default_in = sd.default.device[0]
        if default_in is not None and default_in not in cand_devices:
            cand_devices.append(default_in)
    except Exception:
        pass
    if not cand_devices:
        cand_devices = [i for i, d in enumerate(sd.query_devices()) if d.get("max_input_channels", 0) > 0]

    for dev in cand_devices:
        try:
            info = sd.query_devices(dev, 'input')
        except Exception:
            continue
        rates = [int(info.get('default_samplerate') or 48000), 48000, 44100, 32000]
        tried = set()
        for r in rates:
            if r in tried: 
                continue
            tried.add(r)
            try:
                with sd.InputStream(channels=1, samplerate=r, device=dev):
                    return dev, r
            except Exception:
                continue
    raise RuntimeError("No valid input device/rate found.")

def listen_loop(model, dev_index: int, samplerate: int):
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print("[AudioStatus]", status, file=sys.stderr)
        q.put(indata.copy())

    blocksize = max(1024, int(samplerate * 0.25))  # ~250ms
    with sd.InputStream(channels=1, samplerate=samplerate, blocksize=blocksize, dtype="float32",
                        callback=callback, device=dev_index):
        audio_buffer = np.zeros(0, dtype=np.float32)
        last_vu = time.time()
        print(f"[Calyx] Voice listener active at {samplerate} Hz (device {dev_index}). Speak a short command... (Ctrl+C to stop)")
        while True:
            data = q.get()
            mono = data[:, 0]
            audio_buffer = np.concatenate([audio_buffer, mono])

            # simple VU print every ~1s
            if time.time() - last_vu > 1.0:
                rms = float(np.sqrt((mono**2).mean()) + 1e-9)
                print(f"[VU] rms={rms:.6f}  buffer_len={len(audio_buffer)}")
                last_vu = time.time()

            # process every ~1s of audio
            if len(audio_buffer) >= samplerate * 1.0:
                chunk = audio_buffer
                # --- adaptive gain and overlap-friendly buffering ---
                rms = float(np.sqrt((chunk**2).mean()) + 1e-9)
                # Skip low-noise chunks, but update baseline dynamically
                silence_gate = 0.008
                if rms < silence_gate:
                    continue

                # Gentle normalization (no clipping)
                gain = min(6.0 / max(rms, 1e-4), 8.0)  # auto-adjust gain, cap at 8x
                chunk = np.tanh(chunk * gain)  # soft limit instead of clip()

                # 50% overlap to preserve speech context
                chunk_16k = resample_to_16k(chunk, samplerate)
                chunk_16k = np.concatenate((prev_chunk_16k[-8000:], chunk_16k)) if 'prev_chunk_16k' in locals() else chunk_16k
                prev_chunk_16k = chunk_16k.copy()

                if len(chunk_16k) == 0:
                    continue
                print(f"[Transcribe] {len(chunk)/samplerate:.2f}s chunk -> 16k len={len(chunk_16k)}")
                segments, _ = model.transcribe(chunk_16k, beam_size=1)
                text = " ".join([s.text for s in segments]).strip()
                print(f"[Text] {text!r}")
                if text:
                    yield text

def main():
    cfg = load_config()
    device = cfg["settings"]["faster_whisper_device"]
    compute = cfg["settings"]["faster_whisper_compute_type"]
    model_size = cfg["settings"]["model_size"]
    mic_index = cfg["settings"]["mic_device_index"]

    print(f"[Calyx] Loading faster-whisper '{model_size}' on {device}/{compute}...")
    model = WhisperModel(model_size, device=device, compute_type=compute)

    try:
        dev_index, sr = pick_stream_params(mic_index)
        name = sd.query_devices(dev_index, 'input')['name']
        print(f"[Audio] Using device {dev_index}: {name} @ {sr} Hz")
        for text in listen_loop(model, dev_index, sr):
            print(f"[Heard] {text}")
            cmd = route(text)
            if cmd:
                print(f"[Route] {' '.join(cmd)}")
                subprocess.run([sys.executable, str(SCRIPTS_DIR / 'calyx_console.py'), *cmd])
    except KeyboardInterrupt:
        print("\n[Calyx] Voice listener stopped.")
    except Exception as e:
        print(f"[Calyx] Audio init failed: {e}")
        print("[Calyx] Try another mic_device_index, or set mic default format to 48000/44100 Hz and disable Exclusive Mode.")

if __name__ == "__main__":
    main()
