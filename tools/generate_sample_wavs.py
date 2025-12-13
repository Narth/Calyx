"""Generate short synthetic WAV files for eval_wake_word mock testing.

Creates 4 positive samples (filenames include 'calyx') and 4 negative samples (noise/other words)
under samples/wake_word/{positive,negative}.
"""
import wave
import struct
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pos_dir = ROOT / "samples" / "wake_word" / "positive"
neg_dir = ROOT / "samples" / "wake_word" / "negative"
pos_dir.mkdir(parents=True, exist_ok=True)
neg_dir.mkdir(parents=True, exist_ok=True)

def write_sine(path: Path, freq=440.0, duration=0.6, sr=16000, amp=0.2):
    n_samples = int(sr * duration)
    with wave.open(str(path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for i in range(n_samples):
            t = i / sr
            val = amp * math.sin(2 * math.pi * freq * t)
            iv = int(max(-1.0, min(1.0, val)) * 32767)
            wf.writeframes(struct.pack('<h', iv))

def write_noise(path: Path, duration=0.6, sr=16000):
    import random
    n_samples = int(sr * duration)
    with wave.open(str(path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for _ in range(n_samples):
            iv = random.randint(-2000, 2000)
            wf.writeframes(struct.pack('<h', iv))

# positive samples (filenames map to 'calyx' transcripts in mock mode)
write_sine(pos_dir / 'calyx_01.wav', freq=500.0)
write_sine(pos_dir / 'calyx_02.wav', freq=600.0)
write_sine(pos_dir / 'calyx_03.wav', freq=550.0)
write_sine(pos_dir / 'calyx_04.wav', freq=520.0)

# negative samples
write_noise(neg_dir / 'noise_01.wav')
write_sine(neg_dir / 'otherword_01.wav', freq=300.0)
write_sine(neg_dir / 'activate_01.wav', freq=350.0)
write_noise(neg_dir / 'noise_02.wav')

print(f"Wrote {len(list(pos_dir.iterdir()))} positive and {len(list(neg_dir.iterdir()))} negative samples")
