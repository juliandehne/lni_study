"""Pytest bootstrap for the lni_study testbed.

Puts the repo root on ``sys.path`` so the auto-generated stub tests under
``tests/`` (written by ``python -m rse_annotations.cli . --stubs``) can do
``from src.compute_icr import ...`` / ``from src.krippendorff_reference import ...``
when collected from the repo root. The stub generator derives those dotted module
names from the scanned root, so the scanned root must be importable at test time.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
