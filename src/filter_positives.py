"""
filter_positives.py

Pipeline step `filter`: from the LLM annotation of the estimator-selected
candidates, keep only the papers the model labelled as CONTAINING research
software (`label_research_software == 1`). Those positives are the pool the
narrowing and goldstandard working sets are drawn from.

No token: it only reads the Phase A checkpoint(s) produced by
`annotate_lni.py --lni_folder .workingset/candidates` and writes a manifest of the
label==1 papers to `.workingset/positives/manifest.csv` (id, volume, rel_path,
title, certainty). `prepare_workingset.py --restrict` then limits the narrow/gold
draws to these ids.

Usage (from the lni_study repo root):

    python src/filter_positives.py
    python src/filter_positives.py --pattern "annotations_candidates_*_checkpoint.csv"
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = REPO_ROOT / "results" / "checkpoints"
DEFAULT_OUT = REPO_ROOT / ".workingset" / "positives" / "manifest.csv"


def load_checkpoints(pattern: str) -> pd.DataFrame:
    """Concatenate the candidate annotation checkpoint(s); dedupe by id."""
    files = sorted(CHECKPOINT_DIR.glob(pattern))
    if not files:
        raise SystemExit(
            f"No checkpoint matching {pattern!r} in {CHECKPOINT_DIR}.\n"
            "Run the 'a-candidates' step first "
            "(annotate_lni.py --lni_folder .workingset/candidates).")
    frames = []
    for f in files:
        try:
            frames.append(pd.read_csv(f, dtype={"id": str}))
        except (pd.errors.EmptyDataError, FileNotFoundError):
            continue
    df = pd.concat(frames, ignore_index=True)
    print(f"Read {len(df)} annotation row(s) from {len(files)} checkpoint(s): "
          + ", ".join(f.name for f in files))
    return df.drop_duplicates(subset="id", keep="first")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Keep only label_research_software==1 candidate papers as the "
                    "narrowing/goldstandard pool.")
    parser.add_argument("--pattern", default="annotations_candidates_*_checkpoint.csv",
                        help="Glob (within results/checkpoints/) for the candidate "
                             "annotation checkpoint(s).")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="Output manifest path (default .workingset/positives/manifest.csv).")
    args = parser.parse_args()

    df = load_checkpoints(args.pattern)

    label = pd.to_numeric(df.get("label_research_software"), errors="coerce")
    positives = df[label == 1].copy()
    n_total = len(df)
    n_pos = len(positives)
    print(f"Research-software positives: {n_pos}/{n_total} "
          f"({0 if not n_total else round(100 * n_pos / n_total)}% of annotated candidates).")
    if n_pos == 0:
        raise SystemExit("No label==1 papers found — nothing to narrow/gold-code.")

    # Volume column is `source_folder` in the checkpoint (volume_under key).
    out_cols = pd.DataFrame({
        "id": positives["id"],
        "volume": positives.get("source_folder"),
        "rel_path": positives.get("rel_path"),
        "title": positives.get("title"),
        "certainty": positives.get("label_research_software_certainty"),
    })

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out_cols.to_csv(out, index=False)
    print(f"\nPositives manifest written: {out}")
    print("Next: draw the narrow/gold working sets from this pool, e.g.")
    print("  python src/prepare_workingset.py --corpus .workingset/candidates "
          "--name narrow --sample 50 --restrict .workingset/positives/manifest.csv")


if __name__ == "__main__":
    main()