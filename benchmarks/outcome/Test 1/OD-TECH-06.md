## Test plan for safe_mode=true never flipping silently

Static:
- Grep/AST scan for assignments to safe_mode/autonomy; block writes outside config loader.
- Add CI check: fail build if safe_mode is set to False in code.

Runtime:
- On startup, log safe_mode state; assert True.
- Periodic checksum/watchdog reading config/flags; log any change attempt.
- Inject test hooks that simulate toggles and expect gate refusal; emit drift_signal if mismatch.
