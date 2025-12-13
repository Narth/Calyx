import sys
try:
    import llama_cpp  # type: ignore
    print("OK")
    sys.exit(0)
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)
