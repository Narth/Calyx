"""Compatibility shim for Path.write_text to accept an `append` keyword.

This is a small, low-risk shim intended as a temporary mitigation for
running deployments that may call `Path.write_text(..., append=True)`.
It monkey-patches pathlib.Path.write_text to support an `append`
keyword by doing an append open when requested, otherwise delegating to
the original implementation.

This module is safe to import at Python startup (for example from
`sitecustomize.py`). It's intentionally minimal and defensive.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


_orig_write_text = Path.write_text


def _write_text_compat(self: Path, data: Any, encoding: str | None = None, errors: str | None = None, **kwargs) -> int:
    """Compat wrapper for Path.write_text that accepts `append=True`.

    If `append=True` is present in kwargs, the function will open the
    file in append mode and write the given data. Otherwise it calls
    the original Path.write_text.
    """
    append = False
    if "append" in kwargs:
        append = bool(kwargs.pop("append"))

    if append:
        # Ensure data is str-like
        text = data if isinstance(data, str) else str(data)
        # Use open('a') to append using the requested encoding/errors
        with self.open("a", encoding=encoding, errors=errors) as fh:
            fh.write(text)
        return len(text)

    # Delegate to original (preserve signature behavior)
    return _orig_write_text(self, data, encoding=encoding, errors=errors)


# Apply the patch globally. Do this at import time so any subsequent
# imports that call Path.write_text(..., append=True) will work.
try:
    Path.write_text = _write_text_compat  # type: ignore[assignment]
except Exception:
    # If monkey-patching fails for any reason, do not crash the process.
    pass
