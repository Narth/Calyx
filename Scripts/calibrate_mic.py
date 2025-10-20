import argparse, time, sys, pathlib, statistics
import numpy as np
import sounddevice as sd
import yaml

# ASCII-only prints to dodge Windows cp1252 issues
def say(msg=""):
    try:
        print(str(msg).encode("ascii", "ignore").decode("ascii"), flush=True)
    except Exception:
        print(str(msg), flush=True)

# Simple, dependency-free resampler to 16k
def resample_to_16k(x, sr_in):
    x = np.asarray(x, dtype=np.float32).flatten()
    if sr_in == 16000 or len(x) == 0:
        return x.astype(np.float32)
    n_out = max(1, int(round(len(x) * 16000.0 / float(sr_in))))
    # linear interpolation
    idx_in = np.arange(len(x), dtype=np.float32)
    idx_out = np.linspace(0, len(x) - 1, n_out, dtype=np.float32)
    return np.interp(idx_out, idx_in, x).astype(np.float32)

def frame_rms(x, sr, frame_ms=200):
    n = max(1, int(sr * (frame_ms/1000.0)))
    rms = []
    for i in range(0, len(x), n):
        w = x[i:i+n]
        if len(w) == 0: continue
        rms.append(float(np.sqrt((w**2).mean()) + 1e-9))
    return rms

def softlimit(x, gain, cap=8.0):
    g = min(max(1.0, float(gain)), float(cap))
    return np.tanh(x * g)

def capture(seconds, dev, sr, channels=1):
    say(f"[Cal] Capturing {seconds}s at {sr} Hz from device {dev} ...")
    audio = []
    block = max(1024, int(sr * 0.2))
    with sd.InputStream(device=dev, channels=channels, samplerate=sr, blocksize=block, dtype="float32") as st:
        t0 = time.time()
        while time.time() - t0 < seconds:
            data, _ = st.read(block)
            audio.append(data.copy())
    x = np.concatenate(audio, axis=0).astype(np.float32).flatten()
    say(f"[Cal] Collected {len(x)} samples.")
    return x

def guess_gate(noise_rms, speech_rms):
    # robust defaults if speech estimate is close to noise
    if speech_rms <= noise_rms * 1.2:
        return max(0.006, noise_rms * 2.5)
    # sit roughly 1/3 of the way from noise->speech
    return float(noise_rms + 0.33*(speech_rms - noise_rms))

def try_transcribe(x16, model_name, device, compute_type):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, info = model.transcribe(
        x16,
        language="en",
        beam_size=5,
        vad_filter=True,
        temperature=0.0,
    )
    txt = "".join([s.text for s in segments]).strip()
    stats = {"avg_logprob": None, "avg_no_speech": None, "len": len(txt)}
    lp = [s.avg_logprob for s in segments if hasattr(s, "avg_logprob") and s.avg_logprob is not None]
    ns = [s.no_speech_prob for s in segments if hasattr(s, "no_speech_prob")]
    stats["avg_logprob"] = float(sum(lp)/len(lp)) if lp else -1.0
    stats["avg_no_speech"] = float(sum(ns)/len(ns)) if ns else 1.0
    return txt, stats

def main():
    parser = argparse.ArgumentParser(description="Calyx Mic Calibration")
    parser.add_argument("--seconds", type=int, default=12, help="capture length")
    parser.add_argument("--model", type=str, default="small", help="whisper size: tiny/base/small/medium")
    parser.add_argument("--device", type=int, default=None, help="override mic index")
    parser.add_argument("--apply", action="store_true", help="write suggestions back to config.yaml")
    parser.add_argument("--fast", action="store_true", help="skip Whisper scoring; only compute gate/gain")
    parser.add_argument("--compute", type=str, default=None, help="override compute_type (e.g. int8)")
    args = parser.parse_args()

    cfg_path = pathlib.Path(__file__).resolve().parents[1] / "config.yaml"
    if cfg_path.exists():
        cfg = yaml.safe_load(open(cfg_path, "r", encoding="utf-8")) or {}
        s = cfg.get("settings", {})
    else:
        cfg, s = {}, {}

    # Device discovery
    if args.device is not None:
        dev = int(args.device)
    else:
        dev = int(s.get("mic_device_index", 0))
    info = sd.query_devices(dev, "input")
    sr_default = int(info.get("default_samplerate") or 48000)

    say("[Cal] Device: %d  Name: %s" % (dev, info.get("name", "unknown")))
    say("[Cal] Default sample rate: %d" % sr_default)

    # Prompt the user with an ASCII-only sentence (for consistent phonemes)
    prompt = "Please read clearly: The quick brown fox jumps over the lazy dog. Count 1 2 3 4 5."
    say("")
    say(prompt)
    say("Starting in 1.5s...")
    time.sleep(1.5)

    x = capture(args.seconds, dev, sr_default, channels=1)

    # Analyze noise vs speech
    rms_series = frame_rms(x, sr_default, frame_ms=200)
    if len(rms_series) < 3:
        say("[Cal] Not enough audio captured.")
        sys.exit(1)

    # Noise = lower 20% frames; Speech = upper 20% frames
    sorted_rms = sorted(rms_series)
    k = max(1, int(0.2 * len(sorted_rms)))
    noise_rms = float(statistics.median(sorted_rms[:k]))
    speech_rms = float(statistics.median(sorted_rms[-k:]))
    gate = guess_gate(noise_rms, speech_rms)

    # Prepare test variants
    gains = [3.0, 6.0, 8.0]
    chunk_ms = 1000
    overlap_ms = 500

    say("")
    say("[Cal] Noise RMS ~ %.5f   Speech RMS ~ %.5f   -> initial gate: %.5f" % (noise_rms, speech_rms, gate))

    # Resample full take once
    x_norm = x.copy().astype(np.float32)
    # Pre-normalize lightly so gain search is stable
    base_rms = float(np.sqrt((x_norm**2).mean()) + 1e-9)
    if base_rms > 0:
        x_norm = x_norm / (base_rms * 3.0)

    results = []
    if args.fast:
        # pick gain by pushing speech rms into a comfy zone (~0.03–0.06 after pre-norm)
        target = 0.04
        base_rms = float(np.sqrt((x_norm**2).mean()) + 1e-9)
        g_est = min(8.0, max(3.0, target / max(1e-6, base_rms)))
        results = [{"gain": round(g_est,1), "text": "", "stats": {"avg_logprob": 0.0, "avg_no_speech": 1.0, "len": 0}, "score": 0.0}]
    else:
        for g in gains:
            x_proc = softlimit(x_norm, gain=g, cap=g)
            x16 = resample_to_16k(x_proc, sr_default)
            # speed tweaks: greedy decode, no beam search
            say(f"[Cal] Transcribing gain={g:.1f} on model={args.model} (greedy) ...")
        try:
            # allow override of compute_type
            ctype = args.compute or s.get("faster_whisper_compute_type","float32")
            from faster_whisper import WhisperModel
            model = WhisperModel(args.model, device="cpu", compute_type=ctype)
            segments, _ = model.transcribe(
                x16, language="en", beam_size=1, best_of=1, vad_filter=True, temperature=0.0
            )
            txt = "".join([seg.text for seg in segments]).strip()
            lp = [getattr(seg, "avg_logprob", None) for seg in segments]
            lp = [v for v in lp if v is not None]
            ns = [getattr(seg, "no_speech_prob", None) for seg in segments]
            ns = [v for v in ns if v is not None]
            st = {
                "avg_logprob": (sum(lp)/len(lp)) if lp else -1.0,
                "avg_no_speech": (sum(ns)/len(ns)) if ns else 1.0,
                "len": len(txt),
            }
        except Exception as e:
            txt, st = "", {"avg_logprob": -999.0, "avg_no_speech": 1.0, "len": 0}
            say(f"[Cal] Transcribe error at gain {g:.1f}: {e}")

        except Exception as e:
            txt, st = "", {"avg_logprob": -999.0, "avg_no_speech": 1.0, "len": 0}
            say(f"[Cal] Transcribe error at gain {g:.1f}: {e}")
        score = (st["avg_logprob"] or -999) - (st["avg_no_speech"] or 1.0)
        results.append({"gain": g, "text": txt, "stats": st, "score": score})

    # Pick best by score, then by length
    results.sort(key=lambda r: (r["score"], r["stats"]["len"]), reverse=True)
    best = results[0] if results else None

    say("")
    say("=== RESULTS (best first) ===")
    for r in results:
        say(f"- gain={r['gain']:.1f}  score={r['score']:.3f}  avg_logprob={r['stats']['avg_logprob']:.3f}  no_speech={r['stats']['avg_no_speech']:.3f}")
        say(f"  text: {r['text'][:140]}")
    say("============================")

    if best is None:
        say("[Cal] No result to suggest.")
        sys.exit(2)

    # Suggest final settings
    suggest = {
        "mic_device_index": dev,
        "samplerate": sr_default,
        "silence_gate": float(round(gate, 6)),
        "gain_cap": float(best["gain"]),
        "chunk_ms": chunk_ms,
        "overlap_ms": overlap_ms,
        "model_size": args.model,
        "faster_whisper_device": s.get("faster_whisper_device","cpu"),
        "faster_whisper_compute_type": s.get("faster_whisper_compute_type","float32"),
    }

    say("")
    say("=== SUGGESTED config.yaml block ===")
    say("settings:")
    say(f"  faster_whisper_device: \"{suggest['faster_whisper_device']}\"")
    say(f"  faster_whisper_compute_type: \"{suggest['faster_whisper_compute_type']}\"")
    say(f"  model_size: \"{suggest['model_size']}\"")
    say(f"  mic_device_index: {suggest['mic_device_index']}")
    say(f"  samplerate: {suggest['samplerate']}")
    say(f"  silence_gate: {suggest['silence_gate']}")
    say(f"  gain_cap: {suggest['gain_cap']}")
    say(f"  chunk_ms: {suggest['chunk_ms']}")
    say(f"  overlap_ms: {suggest['overlap_ms']}")
    say("===================================")

    if args.apply:
        # merge back into config.yaml
        cfg.setdefault("settings", {}).update(suggest)
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
        say(f"[Cal] Applied to {str(cfg_path)}")

if __name__ == "__main__":
    main()
