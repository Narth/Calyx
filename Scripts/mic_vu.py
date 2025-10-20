import sounddevice as sd, numpy as np, time, yaml, pathlib
cfg = yaml.safe_load(open(str(pathlib.Path(__file__).resolve().parents[1] / "config.yaml"), "r", encoding="utf-8"))
dev = cfg["settings"]["mic_device_index"]
info = sd.query_devices(dev, "input")
sr = int(info.get("default_samplerate") or 48000)
print(f"[VU] Using device {dev} at {sr} Hz -> {info['name']}")
block = max(1024, int(sr*0.2))
with sd.InputStream(device=dev, channels=1, samplerate=sr, blocksize=block, dtype="float32") as st:
    t0 = time.time()
    while time.time()-t0 < 8:
        data, _ = st.read(block)
        rms = float(np.sqrt((data**2).mean()) + 1e-9)
        print(f"[VU] rms={rms:.6f}")
