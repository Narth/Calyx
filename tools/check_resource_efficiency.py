#!/usr/bin/env python3
"""Quick resource efficiency check"""
import psutil

cpu = psutil.cpu_percent(interval=1)
ram = psutil.virtual_memory().percent

print(f"Current Resources:")
print(f"  CPU: {cpu:.1f}%")
print(f"  RAM: {ram:.1f}%")
print()

if cpu > 60:
    print("[WARNING] CPU above 60%")
elif cpu > 50:
    print("[CAUTION] CPU above 50%")
else:
    print("[OK] CPU utilization acceptable")

if ram > 90:
    print("[CRITICAL] RAM above 90%")
elif ram > 85:
    print("[WARNING] RAM above 85%")
elif ram > 80:
    print("[CAUTION] RAM above 80%")
else:
    print("[OK] RAM utilization acceptable")

