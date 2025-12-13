"""Debug helper: run transcribe_chunk on a single WAV and print result.

Usage:
  python tools/debug_transcribe.py samples/wake_word/positive/calyx_pos_01.wav
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import soundfile as sf
from asr.config import load_config
from asr.pipeline import transcribe_chunk


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/debug_transcribe.py <wav-path>")
        return
    p = Path(sys.argv[1])
    if not p.exists():
        print("File not found:", p)
        return
    audio, sr = sf.read(p)
    print(f"Loaded audio: sr={sr}, dtype={audio.dtype}, shape={getattr(audio, 'shape', None)}")
    try:
        print(f"min={audio.min()}, max={audio.max()}")
    except Exception:
        pass
    cfg = load_config("config.yaml")
    res = transcribe_chunk(audio, cfg, sr=sr)
    print("TRANSCRIBE RESULT:")
    print(res)

    # direct faster-whisper sanity check
    try:
        from faster_whisper import WhisperModel
        settings = cfg.settings()
        model_size = settings.get("model_size", "small")
        device = settings.get("faster_whisper_device", "cpu")
        compute = settings.get("faster_whisper_compute_type", "float32")
        print(f"Attempting direct faster-whisper load: size={model_size} device={device} compute={compute}")
        m = WhisperModel(model_size, device=device, compute_type=compute)
        print("Model loaded; running transcribe with word_timestamps=True (may be slow)...")
        arr = audio
        try:
            segments, info = m.transcribe(arr, word_timestamps=True)
        except TypeError:
            segments = m.transcribe(arr, word_timestamps=True)
            info = None
        print("Segments from direct model:")
        for s in segments:
            try:
                print(repr(s))
                print("SEG TEXT:", getattr(s, "text", s.get("text", None) if isinstance(s, dict) else None))
                print("SEG WORDS:", getattr(s, "words", s.get("words", None) if isinstance(s, dict) else None))
            except Exception as e:
                print("Error printing segment:", e)
    except Exception as e:
        print("faster-whisper direct test skipped/error:", e)


if __name__ == '__main__':
    main()
