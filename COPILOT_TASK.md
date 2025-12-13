Copilot Brief — Improve Phonetic Recognition (Wake word: “Calyx”)
Repo context

Python project using faster-whisper for live transcription.

Streaming mic input via sounddevice; chunked with overlap; simple VAD/silence gating.

“Aurora” is recognized reliably; “Calyx” is not (often misheard as “Calix”, “Kaylix”, “Kelly’s”, etc.).

Goal: robust detection of the wake word “Calyx” in noisy/real-world conditions without tanking general accuracy.

Deliverables

Implement a lightweight, layered solution:

Decoder biasing toward “Calyx”

Use initial_prompt and decoding params in faster-whisper to bias toward the tokenization of “Calyx”.

Expose config toggles in YAML:

wake_word: "Calyx"
bias:
  enable_initial_prompt: true
  initial_prompt_text: "Words you may hear: Calyx, Aurora, terminal, system."
  beam_size: 5
  best_of: 5
  temperature: 0
  word_timestamps: true
  no_speech_threshold: 0.6
  log_prob_threshold: -1.0
  compression_ratio_threshold: 2.4


Add a small helper to inject a prefix when the previous chunk looked like a near-miss (see section 3).

Phonetic Keyword Spotter (KWS)

Implement a post-decoder keyword spotter that operates on text + token/word timestamps.

Steps:

Normalize transcript case/punctuation.

Generate phonetic encodings for candidate words/phrases using Double Metaphone (or fallback Soundex).

Maintain a list of common confusions for “Calyx”: ["calix","kaylix","calyxes","kelly's","kallax","caleks"].

Score matches by (a) phonetic distance, (b) Levenshtein ratio, (c) word-level logprob when available.

Output a structured detection:

WakeWordHit(
  word="Calyx",
  confidence=float,          # 0..1 fused score
  start_time=float,          # seconds
  end_time=float,
  source="kws|decoder|hybrid",
  matched_variant="kaylix"
)


Near-miss rescoring + guided prefix

If the KWS sees a near-miss (score in 0.6–0.8) but below trigger:

Re-run just that time span with a stronger initial_prompt like:
"You may hear the proper noun 'Calyx' (pronounced KAY-liks). If unsure between 'Calix' and 'Calyx', prefer 'Calyx'."

Optionally tighten beam_size and set temperature=0.

Noise/VAD and chunking tweaks

Make SIL_GATE, VAD on/off, CHUNK_MS, and OVERLAP_MS configurable.

Add optional py-webrtcvad gate before Whisper (config flag). Keep it off by default; enable in tests.

Provide a helper that estimates SNR and lowers no_speech_threshold dynamically in clean audio.

Common-variant normalizer (safe mapping)

After full decoding: if the transcript contains a high-confidence near-variant (e.g., “Calix”), replace with “Calyx” only when the KWS fused score ≥ 0.85 and the word is capitalized/proper-noun context (surrounded by terms like “terminal”, “hey”, “launch”, etc.). Otherwise, leave original text.

Telemetry & evaluation harness

Add tools/eval_wake_word.py:

Loads WAVs from samples/wake_word/{positive,negative}/.

Runs the pipeline; writes a CSV with per-file: predicted label, confidence, start/end, latency.

Prints precision/recall/F1 and ROC-AUC for the wake-word detection.

Add logs for false positives/negatives with 3-sec audio excerpt timestamps.

File changes (create or modify)

asr/pipeline.py — wire in initial_prompt, timestamps, and config.

asr/kws.py — phonetic KWS (Double Metaphone + Levenshtein fusion).

asr/normalize.py — safe proper-noun normalizer with context rules.

asr/config.py — load new YAML options; sensible defaults.

tools/eval_wake_word.py — batch evaluator/metrics.

samples/wake_word/... — placeholder README + a few test clips (we’ll add real audio later).

Function signatures (suggested)
# asr/kws.py
def score_wake_word(
    transcript_words: list[tuple[str,float,float]],  # (word, start, end)
    candidates: list[str],
) -> list["WakeWordHit"]: ...

# asr/pipeline.py
def transcribe_chunk(audio: np.ndarray, cfg: Cfg) -> dict: ...
def rescore_span(audio: np.ndarray, t0: float, t1: float, cfg: Cfg, strong_bias: bool=False) -> dict: ...

# asr/normalize.py
def normalize_proper_nouns(text: str, hits: list["WakeWordHit"], cfg: Cfg) -> str: ...

Acceptance criteria

Wake-word recall ≥ 95% on samples/wake_word/positive with mixed noise (fan, café, street).

False positives ≤ 1 per 10 minutes on samples/wake_word/negative (random speech, “Calix” the company, IKEA “Kallax”).

Average added latency from KWS & optional rescoring ≤ 60 ms per chunk on target machine.

General transcription WER does not degrade by more than +0.5% vs. baseline on samples/general/.

Configurable entirely via YAML; defaults keep current behavior if bias.enable_initial_prompt=false and KWS disabled.

Test plan (quick)

python tools/eval_wake_word.py --model small --cfg config.yaml

Verify printed metrics meet thresholds.

Live test: speak “Calyx” 10× at 3 distances + 2 angles; expect 10/10 hits and stable timestamps.

Live negative: read tech paragraphs for 10 min; expect ≤1 false trigger.

Stretch (nice to have)

Cache phonetic encodings for speed.

Small “confusion matrix” report showing which variants appear most often.

Optional integration with a classic wake-word engine (e.g., Porcupine) behind a common WakeWordProvider interface without making it a hard dependency.

Quick config snippet to drop in config.yaml
wake_word: "Calyx"
kws:
  enabled: true
  variants: ["calix","kaylix","calyxes","kelly's","kallax","caleks"]
  trigger_threshold: 0.85
  near_miss_low: 0.60
  near_miss_high: 0.84
bias:
  enable_initial_prompt: true
  initial_prompt_text: "Words you may hear: Calyx (KAY-liks), Aurora, terminal, system."
  beam_size: 5
  best_of: 5
  temperature: 0
vad:
  webrtcvad_enabled: false
  silence_gate: 0.025
streaming:
  chunk_ms: 1000
  overlap_ms: 500