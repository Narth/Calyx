#!/usr/bin/env python3
from configparser import ConfigParser

# Test the failing tensor dimensions
size = 3145728

print("Analyzing 3,145,728 element tensor:")
print(f"Possible dimensions:")

candidates = []
for M in [512, 768, 1024, 1536, 2048, 3072, 4096]:
    if size % M == 0:
        K = size // M
        candidates.append((M, K))
        print(f"  M={M:4d}, K={K:4d}")

# Load kernel configs
config = ConfigParser()
config_path = '/home/narth/bitnet_build/BitNet/include/kernel_config.ini'
config.read(config_path)

print("\nAvailable kernel configurations:")
for kernel in config.sections():
    m = int(config.get(kernel, 'm'))
    k = int(config.get(kernel, 'k'))
    bm = int(config.get(kernel, 'bm'))
    bk = int(config.get(kernel, 'bk'))
    print(f"  M={m:4d}, K={k:4d}  (BM={bm}, BY={bk})")

print("\nChecking which candidate has a matching kernel config:")
for M, K in candidates:
    found = False
    for kernel in config.sections():
        if int(config.get(kernel, 'm')) == M and int(config.get(kernel, 'k')) == K:
            found = True
            bm = config.get(kernel, 'bm')
            bk = config.get(kernel, 'bk')
            print(f"  ? M={M}, K={K} --> Kernel config exists (BM={bm}, BY={bk})")
            break
    if not found:
        print(f"  ? M={M}, K={K} --> NO KERNEL CONFIG")
