"""Regression test for the gold-worklist desync bug.

A colleague coding the gold task saw rows whose PDF never opened. Root cause:
the coder's worklist is the checkpoint (source of truth), but PDFs + manifest for
`<set>_confirmed/` were materialized once at the end from the in-memory candidate
lists. When the pool reservoir was rebuilt between confirm runs, a confirmed paper
could vanish from every candidate manifest while still being label==1 in the
checkpoint -- so its worklist row had no staged PDF.

`materialize_confirmed` now drives off the checkpoint and reconciles a dropped
paper's PDF from any sibling working-set folder via `_locate_workingset_pdf`. This
test reproduces the drop and asserts the paper is re-staged, not lost.
"""
import sys
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from confirm_positives import (  # noqa: E402
    load_set_candidates, load_done_labels, materialize_confirmed,
)


def _write_pdf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def test_dropped_confirmed_paper_is_restaged_from_sibling_folder(tmp_path):
    workroot = tmp_path / ".workingset"

    # Candidate that IS still in the gold manifest (the normal path).
    keep_pdf = workroot / "gold" / "lni1" / "keep.pdf"
    _write_pdf(keep_pdf, "KEEP")

    # Confirmed paper that was DROPPED from every candidate manifest but whose PDF
    # still lives in the pool reservoir -- the exact desync the fix reconciles.
    drop_pdf = workroot / "pool" / "lni1" / "drop.pdf"
    _write_pdf(drop_pdf, "DROP")

    # A negative paper that must NOT be staged.
    neg_pdf = workroot / "pool" / "lni1" / "neg.pdf"
    _write_pdf(neg_pdf, "NEG")

    # gold/manifest.csv lists ONLY the surviving candidate (absolute dst so the
    # test is independent of LNI_DATA_ROOT / resolve_repo_path's data-root base).
    (workroot / "gold").mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"id": "lni1/keep", "volume": "lni1", "rel_path": "lni1/keep.pdf",
         "dst": str(keep_pdf)},
    ]).to_csv(workroot / "gold" / "manifest.csv", index=False)

    # Checkpoint = coder's worklist / source of truth. Two positives (keep, drop),
    # one negative (neg). 'drop' appears here but in NO candidate manifest.
    checkpoint = tmp_path / "goldconfirm_checkpoint.csv"
    pd.DataFrame([
        {"id": "lni1/keep", "label_research_software": 1,
         "label_research_software_certainty": "high", "title": "Keep",
         "source_folder": "lni1", "rel_path": "lni1/keep.pdf"},
        {"id": "lni1/drop", "label_research_software": 1,
         "label_research_software_certainty": "high", "title": "Drop",
         "source_folder": "lni1", "rel_path": "lni1/drop.pdf"},
        {"id": "lni1/neg", "label_research_software": 0,
         "label_research_software_certainty": "high", "title": "Neg",
         "source_folder": "lni1", "rel_path": "lni1/neg.pdf"},
    ]).to_csv(checkpoint, index=False)

    all_candidates = load_set_candidates(workroot, "gold")
    done = load_done_labels(checkpoint)

    # Sanity: the dropped paper really is absent from the candidate list.
    assert "lni1/drop" not in {c["id"] for c in all_candidates}

    confirmed_ids, rows, unstaged, out_dir, manifest = materialize_confirmed(
        workroot, "gold", checkpoint, all_candidates, done)

    # The dropped positive is confirmed and re-staged from the pool sibling folder.
    assert "lni1/drop" in confirmed_ids
    assert (out_dir / "lni1" / "drop.pdf").is_file()
    assert (out_dir / "lni1" / "drop.pdf").read_bytes() == b"DROP"

    # Both positives staged, the negative excluded, nothing left unstaged.
    staged_ids = {r["id"] for r in rows}
    assert staged_ids == {"lni1/keep", "lni1/drop"}
    assert "lni1/neg" not in staged_ids
    assert unstaged == []

    # Manifest row count matches the checkpoint's label==1 count (the invariant:
    # the staged manifest never drifts below the coder's worklist).
    n_positive = 2
    written = pd.read_csv(manifest, dtype={"id": str})
    assert len(written) == n_positive
    assert set(written["id"]) == {"lni1/keep", "lni1/drop"}


def test_confirmed_paper_with_no_source_pdf_is_reported_unstaged(tmp_path):
    """A confirmed paper whose PDF exists nowhere must be reported as unstaged
    (so the caller can warn), not silently written into the manifest."""
    workroot = tmp_path / ".workingset"
    (workroot / "gold").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [], columns=["id", "volume", "rel_path", "dst"]
    ).to_csv(workroot / "gold" / "manifest.csv", index=False)

    checkpoint = tmp_path / "goldconfirm_checkpoint.csv"
    pd.DataFrame([
        {"id": "lni1/ghost", "label_research_software": 1,
         "label_research_software_certainty": "low", "title": "Ghost",
         "source_folder": "lni1", "rel_path": "lni1/ghost.pdf"},
    ]).to_csv(checkpoint, index=False)

    all_candidates = load_set_candidates(workroot, "gold")
    done = load_done_labels(checkpoint)

    confirmed_ids, rows, unstaged, out_dir, manifest = materialize_confirmed(
        workroot, "gold", checkpoint, all_candidates, done)

    assert confirmed_ids == ["lni1/ghost"]
    assert unstaged == ["lni1/ghost"]
    assert rows == []
