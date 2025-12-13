"""Provide resample_poly if available (SciPy), otherwise a small numpy-based fallback.

This keeps scripts resilient when SciPy is unavailable (common in lightweight venvs on Windows).
"""
try:
    from scipy.signal import resample_poly  # type: ignore
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False

import numpy as _np


def _resample_poly_fallback(x, up, down):
    # conservative linear-resample fallback using numpy.interp
    if x is None:
        return x
    if up == down:
        return _np.asarray(x)
    # compute output length
    try:
        sr_in = down
        sr_out = up
        # interpret up/down as target/input samplerate ratio: target = up, input = down
        duration = len(x) / float(down if down else 1)
        n_out = max(1, int(round(duration * up)))
    except Exception:
        # fallback: keep same length
        n_out = len(x)
    if n_out <= 0:
        return _np.asarray(x)
    t_in = _np.linspace(0.0, 1.0, num=len(x), endpoint=False)
    t_out = _np.linspace(0.0, 1.0, num=n_out, endpoint=False)
    return _np.interp(t_out, t_in, _np.asarray(x)).astype(_np.float32)


def get_resample_poly():
    if _HAVE_SCIPY:
        from scipy.signal import resample_poly as _rp

        return _rp
    return _resample_poly_fallback


# convenience: export name used by scripts
resample_poly = get_resample_poly()
