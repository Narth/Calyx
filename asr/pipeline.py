from typing import Dict, Any
import numpy as np
import hashlib
import functools
import time
from .config import Cfg

try:
    from faster_whisper import WhisperModel
    _FW_AVAILABLE = True
except Exception:
    WhisperModel = None
    _FW_AVAILABLE = False


@functools.lru_cache(maxsize=4)
def _get_model(model_size: str, device: str, compute_type: str):
    if not _FW_AVAILABLE:
        return None
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def _audio_hash(audio: np.ndarray) -> str:
    # simple hash for caching/recheck; use bytes view
    try:
        b = audio.tobytes()
    except Exception:
        b = str(audio.shape).encode("utf-8")
    return hashlib.sha1(b).hexdigest()


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    # collapse multi-channel to mono by averaging
    try:
        if audio.ndim == 2 and audio.shape[1] > 1:
            return audio.mean(axis=1)
    except Exception:
        pass
    return audio


def _resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int = 16000) -> np.ndarray:
    if orig_sr == target_sr:
        return audio
    # simple linear resample via numpy.interp
    import numpy as _np
    try:
        duration = audio.shape[0] / float(orig_sr)
        new_n = int(duration * target_sr)
        if new_n <= 0:
            return audio
        old_idx = _np.linspace(0, audio.shape[0] - 1, num=audio.shape[0])
        new_idx = _np.linspace(0, audio.shape[0] - 1, num=new_n)
        return _np.interp(new_idx, old_idx, audio).astype(audio.dtype)
    except Exception:
        return audio


def transcribe_chunk(audio: np.ndarray, cfg: Cfg, sr: int | None = None) -> Dict[str, Any]:
    """Transcribe a single chunk of audio using configured decoding bias.

    If faster-whisper is available this will run a real decode. Otherwise returns
    an empty result structure.
    """
    settings = cfg.settings()
    if not _FW_AVAILABLE:
        return {"text": "", "words": []}

    # ensure mono and resample to 16k if sr provided
    if sr is not None:
        audio = _ensure_mono(audio)
        audio = _resample_audio(audio, orig_sr=sr, target_sr=16000)

    model_size = settings.get("model_size", "small")
    device = settings.get("faster_whisper_device", "cpu")
    compute = settings.get("faster_whisper_compute_type", "float32")
    model = _get_model(model_size, device, compute)
    if model is None:
        return {"text": "", "words": []}

    # build decode options
    bias_cfg = settings.get("bias", {})
    decode_opts = {}
    # prefer word timestamps to drive KWS; allow override in config
    decode_opts["word_timestamps"] = bias_cfg.get("word_timestamps", True)
    if bias_cfg.get("enable_initial_prompt"):
        decode_opts["initial_prompt"] = bias_cfg.get("initial_prompt_text")
    # pass through common options if present
    for k in ("beam_size", "best_of", "temperature", "word_timestamps"):
        if k in bias_cfg:
            decode_opts[k] = bias_cfg[k]
    try:
        # faster-whisper expects float32 numpy array
        a = np.asarray(audio, dtype=np.float32)
        result = model.transcribe(a, **decode_opts)
        # result may be (segments, info) or just segments
        if isinstance(result, tuple) and len(result) == 2:
            segments, info = result
        else:
            segments = result
            info = None
        # ensure segments is a list so we can iterate it safely
        try:
            segments = list(segments)
        except Exception:
            pass
        # diagnostic
        try:
            print("transcribe_chunk: segments type:", type(segments))
            try:
                print("transcribe_chunk: segments length:", len(segments))
            except Exception:
                print("transcribe_chunk: segments len() not available")
            try:
                if len(segments) > 0:
                    first = segments[0]
                    print("transcribe_chunk: first seg repr:", repr(first))
            except Exception as e:
                print("transcribe_chunk: couldn't inspect first segment:", e)
        except Exception:
            pass
    except Exception as e:
        import traceback
        print("transcribe_chunk: exception during model.transcribe:")
        traceback.print_exc()
        return {"text": "", "words": []}
    except Exception:
        return {"text": "", "words": []}

    # collect text and word timestamps if available
    full_text = ""
    words = []
    decoder_probs = {}
    try:
        for seg in segments:
            # segments may be dict-like or object
            seg_text = getattr(seg, "text", None) or seg.get("text", "")
            full_text += seg_text + " "
            # try to get avg_logprob for the segment
            try:
                seg_avg_logprob = getattr(seg, "avg_logprob", None)
                if seg_avg_logprob is None and isinstance(seg, dict):
                    seg_avg_logprob = seg.get("avg_logprob")
            except Exception:
                seg_avg_logprob = None
            # collect words if available
            wlist = getattr(seg, "words", None) or seg.get("words", [])
            for w in wlist:
                # w might be dict or object: expect (word, start, end) or {"word":..}
                if isinstance(w, dict):
                    wd = w.get("word", "")
                    st = w.get("start", 0.0)
                    en = w.get("end", 0.0)
                    prob = w.get("probability") or w.get("prob") or w.get("p") or None
                else:
                    # try attributes
                    wd = getattr(w, "word", None) or (w[0] if len(w) > 0 else "")
                    st = getattr(w, "start", None) or (w[1] if len(w) > 1 else 0.0)
                    en = getattr(w, "end", None) or (w[2] if len(w) > 2 else 0.0)
                    prob = getattr(w, "probability", None) or getattr(w, "prob", None)
                # normalize word text
                try:
                    wd_str = str(wd).strip()
                except Exception:
                    wd_str = ""
                words.append((wd_str, float(st), float(en)))
                # record decoder probability (0..1) using lowercased token key; keep max if duplicate
                try:
                    if prob is not None:
                        p = float(prob)
                        key = wd_str.lower().strip().strip(".,!?\"'()[]")
                        if key:
                            decoder_probs[key] = max(decoder_probs.get(key, 0.0), p)
                    else:
                        # fallback: use segment avg_logprob if available
                        try:
                            import math
                            if seg_avg_logprob is not None:
                                p = float(min(0.0, seg_avg_logprob))
                                # map negative logprob to 0..1 via exp
                                p_norm = float(math.exp(p))
                                key = wd_str.lower().strip().strip(".,!?\"'()[]")
                                if key:
                                    decoder_probs[key] = max(decoder_probs.get(key, 0.0), p_norm)
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception:
        # fallback: make rudimentary tokenization with no timestamps
        try:
            text = "".join([getattr(s, "text", "") for s in segments])
            tokens = text.split()
            words = [(t, 0.0, 0.0) for t in tokens]
            full_text = text
        except Exception:
            full_text = ""
            words = []

    # If no per-word timestamps were available, but we have text, return tokens with zeroed timestamps
    if not words and full_text.strip():
        tokens = full_text.strip().split()
        words = [(t, 0.0, 0.0) for t in tokens]

    # include decoder_probs in results
    return {"text": full_text.strip(), "words": words, "decoder_probs": decoder_probs}
    


def rescore_span(audio: np.ndarray, t0: float, t1: float, cfg: Cfg, strong_bias: bool = False) -> Dict[str, Any]:
    """Re-run transcription for a narrow timespan [t0,t1] with optional stronger bias.

    Safeguards:
    - limit the maximum rescore span length to avoid latency spikes
    - avoid rescoring if span too short or too long
    - allow strong_bias to temporarily override initial_prompt and decoding params
    """
    settings = cfg.settings()
    sr = settings.get("samplerate", 44100)
    max_span = settings.get("rescore_max_sec", 3.0)
    min_span = settings.get("rescore_min_sec", 0.05)

    span = max(0.0, float(t1) - float(t0))
    if span < min_span or span > max_span:
        # skip rescore to avoid expensive operations; return empty/fast path
        return {"text": "", "words": []}

    # extract samples for span
    try:
        start_idx = int(t0 * sr)
        end_idx = int(t1 * sr)
        sub = audio[start_idx:end_idx]
    except Exception:
        sub = audio

    if strong_bias:
        # temporarily modify cfg settings for a stronger prompt
        # create a shallow copy of cfg.raw with overridden bias values
        raw = dict(cfg.raw)
        bias = dict(raw.get("settings", {}).get("bias", {}))
        bias["enable_initial_prompt"] = True
        bias["initial_prompt_text"] = "You may hear the proper noun 'Calyx' (pronounced KAY-liks). If unsure between 'Calix' and 'Calyx', prefer 'Calyx'."
        bias["beam_size"] = 3
        bias["temperature"] = 0.0
        raw.setdefault("settings", {})["bias"] = bias
        strong_cfg = Cfg(raw=raw)
        return transcribe_chunk(sub, strong_cfg)

    return transcribe_chunk(sub, cfg)
