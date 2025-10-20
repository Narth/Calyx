import sounddevice as sd

rates = [None, 48000, 44100, 32000]  # None = device default
print("=== Probing input devices ===")
for i, d in enumerate(sd.query_devices()):
    if d.get("max_input_channels", 0) <= 0:
        continue
    print(f"\n[{i}] {d['name']}")
    for r in rates:
        sr = int(d["default_samplerate"]) if r is None else r
        try:
            with sd.InputStream(device=i, channels=1, samplerate=sr):
                print(f"  OK  samplerate={sr}")
        except Exception as e:
            msg = str(e).splitlines()[-1]
            print(f"  NO  samplerate={sr}  -> {msg}")
