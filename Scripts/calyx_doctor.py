import sys, os, time, pathlib, json, textwrap
from datetime import datetime
import yaml
import sounddevice as sd

ROOT = pathlib.Path(r"C:\Calyx_Terminal")
CFG  = ROOT / "config.yaml"
DIAG = ROOT / "_diag"
DIAG.mkdir(parents=True, exist_ok=True)
REPORT = DIAG / "calyx_report.txt"
BACKUP = DIAG / f"config.backup.{int(time.time())}.yaml"

def load_cfg():
    if CFG.exists():
        with open(CFG, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}
def dump_cfg(cfg):
    with open(CFG, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)

def probe_ok(device_idx, rate):
    try:
        with sd.InputStream(device=device_idx, channels=1, samplerate=rate):
            return True, None
    except Exception as e:
        return False, str(e).splitlines()[-1]

def choose_input(preferred=None):
    devices = sd.query_devices()
    # If preferred is valid input and opens at a common rate, keep it
    if preferred is not None and 0 <= preferred < len(devices):
        d = devices[preferred]
        if d.get("max_input_channels", 0) > 0:
            for r in (44100, 48000, int(d.get("default_samplerate") or 44100)):
                ok,_ = probe_ok(preferred, r)
                if ok:
                    return preferred, r, "preferred_ok"
    # Otherwise: prefer Razer Seiren X, then any input that opens at 44.1 or 48k
    candidates = []
    for i,d in enumerate(devices):
        if d.get("max_input_channels",0) <= 0: 
            continue
        name = d.get("name","").lower()
        score = 0
        if "razer" in name or "seiren" in name: score += 10
        for r in (44100, 48000):
            ok,_ = probe_ok(i, r)
            if ok:
                candidates.append((score, -r, i, r))  # prefer higher score, then 48k
                break
    if not candidates:
        return None, None, "no_input_found"
    score, neg_rate, idx, rate = sorted(candidates, reverse=True)[0]
    return idx, rate, "autopick"

def quick_vu(device_idx, rate, seconds=3):
    import numpy as np
    block = max(1024, int(rate*0.2))
    rms_vals = []
    with sd.InputStream(device=device_idx, channels=1, samplerate=rate, blocksize=block, dtype="float32") as st:
        t0 = time.time()
        while time.time()-t0 < seconds:
            data, _ = st.read(block)
            rms = float(np.sqrt((data**2).mean()) + 1e-9)
            rms_vals.append(rms)
    if not rms_vals: 
        return 0.0, 0.0, 0.0
    import statistics as stats
    return min(rms_vals), float(stats.median(rms_vals)), max(rms_vals)

def main():
    args = set(a.lower() for a in sys.argv[1:])
    do_fix = ("--fix" in args)
    cfg = load_cfg()
    cfg.setdefault("settings", {})
    pref = cfg["settings"].get("mic_device_index", None)

    header = []
    header.append(f"time: {datetime.now().isoformat(timespec='seconds')}")
    header.append(f"python: {sys.version.split()[0]}")
    header.append(f"sd lib version: {sd.get_portaudio_version()}  hostapis: {sd.query_hostapis().__len__()}")

    devices = sd.query_devices()
    rows = []
    for i,d in enumerate(devices):
        rows.append({
            "idx": i,
            "name": d.get("name",""),
            "in": d.get("max_input_channels",0),
            "out": d.get("max_output_channels",0),
            "rate": int(d.get("default_samplerate") or 0)
        })

    picked_idx, picked_rate, how = choose_input(pref)
    problems = []
    if pref is None:
        problems.append("mic_device_index missing")
    else:
        if not (0 <= int(pref) < len(devices)):
            problems.append(f"configured index {pref} out of range")
        else:
            d = devices[int(pref)]
            if d.get("max_input_channels",0) <= 0:
                problems.append(f"configured device {pref} is not an input ({d.get('name')})")

    # Test VU if we have a pick
    vu_line = "VU: (skipped)"
    if picked_idx is not None:
        try:
            mn, md, mx = quick_vu(picked_idx, picked_rate, 2)
            vu_line = f"VU(min/med/max) ~ {mn:.4f} / {md:.4f} / {mx:.4f} @ {picked_rate} Hz"
        except Exception as e:
            vu_line = f"VU: error -> {e}"

    rec = []
    if picked_idx is None:
        rec.append("No working input found. Ensure your physical mic is enabled in Windows Sound > Recording.")
    else:
        pname = devices[picked_idx]["name"]
        rec.append(f"Use input idx {picked_idx} → {pname} @ {picked_rate} Hz")
        if problems or pref != picked_idx:
            rec.append("Update config: settings.mic_device_index = {picked_idx}")

    # Optionally fix config
    changed = False
    if do_fix and picked_idx is not None:
        # backup
        if CFG.exists():
            BACKUP.write_text(CFG.read_text(encoding='utf-8'), encoding='utf-8')
        cfg["settings"]["mic_device_index"] = int(picked_idx)
        dump_cfg(cfg)
        changed = True

    # Write report
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("=== Calyx Doctor Report ===\n")
        for h in header: f.write(h+"\n")
        f.write("\nCurrent config:\n")
        f.write(textwrap.dedent(json.dumps(cfg, indent=2, ensure_ascii=False)))
        f.write("\n\nDetected audio devices (inputs shown with in>0):\n")
        for r in rows:
            flag = "IN " if r["in"]>0 else "out"
            f.write(f"[{r['idx']:2}] {flag}  rate={r['rate']:<6}  {r['name']}\n")
        f.write("\nDecision:\n")
        f.write(f"  preferred_index: {pref}\n")
        f.write(f"  picked_index   : {picked_idx}\n")
        f.write(f"  picked_rate    : {picked_rate}\n")
        f.write(f"  method         : {how}\n")
        f.write(f"  {vu_line}\n")
        if problems:
            f.write("\nProblems detected:\n")
            for p in problems: f.write(f"  - {p}\n")
        f.write("\nRecommendation:\n")
        for rline in rec: f.write(f"  - {rline}\n")
        if changed:
            f.write(f"\nConfig updated and backup saved at: {BACKUP}\n")

    print(f"[Doctor] Report saved to: {REPORT}")
    if changed:
        print("[Doctor] Config auto-fixed.")
    else:
        print("[Doctor] Run with --fix to write recommendation to config.yaml")

if __name__ == "__main__":
    main()
