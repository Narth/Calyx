goldset_example

Place a minimal gold set here to try the eval tool without large downloads.

Expected structure under a data root (use samples/wake_word in this repo or copy here):
- positive/  # audio files containing the wake word (e.g., "Calyx")
- negative/  # audio files without the wake word

Optional sidecar transcripts (for fast mock mode, no model):
- For each audio file foo.wav, you may provide a foo.txt containing the transcript text.

Quick start (mock mode):
- powershell
  python tools/eval_kw.py --dir tools/goldset_example --kw calyx

Real mode (uses faster-whisper if installed):
- powershell
  python tools/eval_kw.py --dir samples/wake_word --kw calyx --real
