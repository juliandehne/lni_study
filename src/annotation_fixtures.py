"""Fixtures that let the rse_annotations runner *invoke* the boundary
functions of ``compute_icr`` in a sandbox, so the I/O-success check can
confirm they really read / write files (instead of reporting WARN).

Each fixture has the signature ``fixture(tmpdir, tracer) -> (args, kwargs)``:
it may create setup files under ``tmpdir`` (those writes are cleared from the
tracer afterwards so only the *function's own* I/O is measured), then returns
the positional/keyword arguments to call the annotated function with.

Wire these into the runner via ``Runner(..., fixtures=FIXTURES)``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


def _load_coders_fixture(tmpdir, tracer):
    """Two minimal coder files so ``load_coders`` has something to read."""
    folder = Path(tmpdir)
    for name in ("alice", "bob"):
        df = pd.DataFrame({
            "id": ["rs1", "rs2"],
            "dimension": ["purpose", "purpose"],
            "final_category": ["tool", "library"],
        })
        df.to_csv(folder / f"coding_{name}.csv", index=False)
    # Only measure the reads performed by load_coders itself.
    tracer.reads.clear()
    tracer.writes.clear()
    return (folder,), {}


def _write_icr_outputs_fixture(tmpdir, tracer):
    """A tiny metrics table so ``write_icr_outputs`` has something to write."""
    folder = Path(tmpdir)
    df_icr = pd.DataFrame([{
        "dimension": "purpose",
        "n_shared": 2,
        "raw_agreement": 1.0,
        "krippendorff_alpha": 1.0,
        "cohen_kappa": 1.0,
    }])
    tracer.reads.clear()
    tracer.writes.clear()
    args = (df_icr, folder, "alice", "bob", {"rs1", "rs2"}, set(), None)
    return args, {}


FIXTURES = {
    "load_coders": _load_coders_fixture,
    "write_icr_outputs": _write_icr_outputs_fixture,
}
