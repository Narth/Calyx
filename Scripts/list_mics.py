import sounddevice as sd
for i, d in enumerate(sd.query_devices()):
    print(f"{i:2}  {d['name']}")
