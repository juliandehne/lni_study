"""Safe access to the rse_code_annotations framework.

The framework lives in the sibling submodule ``publications/rse_code_annotations``.
This shim imports the real decorators when the framework is installed (or importable
from the sibling path), and otherwise falls back to **no-op** decorators so the
lni_study pipeline keeps running unchanged even without the dependency. This is what
lets us annotate the code on a feature branch without risking the main pipeline.

Install the framework with::

    pip install -e ../rse_code_annotations          # from the lni_study repo root
    #   or, with formula inference + Fable extras:
    pip install -e "../rse_code_annotations[formula,fable]"
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing straight from the sibling submodule without an install.
_SIBLING = Path(__file__).resolve().parents[2] / "rse_code_annotations"
if _SIBLING.is_dir() and str(_SIBLING) not in sys.path:
    sys.path.insert(0, str(_SIBLING))

try:
    from rse_annotations import data_input, data_output, functional, mapping  # noqa: F401

    HAVE_RSE_ANNOTATIONS = True
except Exception:  # noqa: BLE001 - any import problem -> graceful no-op fallback
    HAVE_RSE_ANNOTATIONS = False

    def _noop(func=None, *, fields=None):  # type: ignore[no-redef]
        """No-op stand-in used when the framework is not installed."""
        def wrap(fn):
            return fn
        if callable(func) and fields is None:
            return wrap(func)
        return wrap

    functional = mapping = data_input = data_output = _noop  # type: ignore[assignment]
