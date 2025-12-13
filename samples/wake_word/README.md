Directory for wake-word evaluation samples.

Place positive examples (audio files containing the wake-word) under `positive/` and negative examples under `negative/`.

Expected layout:

samples/wake_word/
  positive/
  negative/

Run the evaluator after populating with audio files:

python tools/eval_wake_word.py --model small --cfg config.yaml

Generating quick synthetic samples (Windows only)
-----------------------------------------------
You can generate neutral TTS samples using the provided PowerShell helper:

  .\tools\generate_tts_samples.ps1

This will write a few positive/negative WAVs into the `samples/wake_word` folders.
