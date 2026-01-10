#!/usr/bin/env python3
from safetensors import safe_open

model_path = '/home/narth/bitnet_build/BitNet/models/bitnet_b1_58-large/model.safetensors'

with safe_open(model_path, framework='pt') as f:
    keys = list(f.keys())
    print(f"Total tensors: {len(keys)}\n")
    
    for idx, key in enumerate(keys[:15]):
        tensor = f.get_tensor(key)
        shape = tuple(tensor.shape)
        elements = tensor.numel()
        print(f"{idx:2d}. {key:50s} | Shape: {str(shape):20s} | Elements: {elements:12,d}")
        
        # Check if shape matches kernel configs
        if len(shape) == 2:
            M, K = shape
            known_configs = [(1536, 4096), (1536, 1536), (4096, 1536)]
            if (M, K) not in known_configs:
                print(f"    ??  NO KERNEL CONFIG for M={M}, K={K}")
