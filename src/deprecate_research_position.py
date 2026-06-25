"""Deprecate (blank) the model's research_position suggestion for UNCODED papers
in the goldconfirm checkpoint, so `fill-gold absent-only` re-queries just that
dimension under the updated schema.

One-off maintenance utility (applied 2026-06-23 after the research_position
descriptions in prompts/category_schema.yaml were tightened). Idempotent: a
re-run after the cells are already blank is a no-op for those rows.

"Uncoded" matches annotate_lni._coded_paper_ids exactly: id not present in the
`id` column of ANY goldstandard/coding_*.csv. Only RSE rows (label_research_
software==1) are touched -- those are the rows fill-gold will actually refill.

Usage (from anywhere):
    python src/deprecate_research_position.py            # dry run, prints counts
    python src/deprecate_research_position.py --apply     # back up + blank cells
"""
import sys
import shutil
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CKPT = ROOT / "results/checkpoints/annotations_goldconfirm_mistral-large-3-675b-instruct-2512_rse_typology_prompt_v1_run_1_checkpoint.csv"
GOLD = ROOT / "goldstandard"
DIM = "research_position"
COLS = [f"{DIM}_category", f"{DIM}_certainty", f"{DIM}_new_suggestion", f"{DIM}_explanation"]
TRUTHY = ("1", "1.0", "true", "True")

apply = "--apply" in sys.argv


def coded_ids() -> set[str]:
    ids: set[str] = set()
    for f in sorted(GOLD.glob("coding_*.csv")):
        try:
            col = pd.read_csv(f, usecols=["id"], dtype={"id": str})["id"]
        except (pd.errors.EmptyDataError, ValueError, KeyError):
            continue
        ids.update(col.dropna().astype(str).str.strip())
        print(f"  coding file: {f.name:50s} ids={col.dropna().nunique()}")
    return ids


def is_blank(v) -> bool:
    return str(v).strip().lower() in ("", "nan", "none")


df = pd.read_csv(CKPT, dtype=str, keep_default_na=False)
print(f"Checkpoint rows: {len(df)}")
missing = [c for c in COLS if c not in df.columns]
if missing:
    raise SystemExit(f"Missing expected columns: {missing}")

coded = coded_ids()
print(f"Total coded ids across coding_*.csv: {len(coded)}")

idn = df["id"].astype(str).str.strip()
is_rse = df["label_research_software"].astype(str).str.strip().isin(TRUTHY)
is_uncoded = ~idn.isin(coded)
target = is_rse & is_uncoded

cat_nonblank = df[f"{DIM}_category"].map(lambda v: not is_blank(v))
print(f"\nRSE rows:                              {int(is_rse.sum())}")
print(f"Uncoded rows (any RSE-status):         {int(is_uncoded.sum())}")
print(f"Target rows (RSE & uncoded):           {int(target.sum())}")
print(f"  of those, with a non-blank {DIM}_category to clear: {int((target & cat_nonblank).sum())}")
print(f"  of those, already blank (no-op):                    {int((target & ~cat_nonblank).sum())}")

# sanity: coded RSE rows we are deliberately NOT touching
print(f"\nCoded RSE rows left intact:             {int((is_rse & ~is_uncoded).sum())}")

if not apply:
    print("\n[DRY RUN] No file written. Re-run with --apply to blank the cells.")
    sys.exit(0)

bak = CKPT.with_suffix(CKPT.suffix + ".predeprecate-bak")
n = 1
while bak.exists():
    n += 1
    bak = CKPT.with_suffix(CKPT.suffix + f".predeprecate-bak{n}")
shutil.copy2(CKPT, bak)
print(f"\nBackup written: {bak.name}")

for c in COLS:
    df.loc[target, c] = ""

tmp = CKPT.with_suffix(CKPT.suffix + ".tmp")
df.to_csv(tmp, index=False)
import os
os.replace(tmp, CKPT)
print(f"Wrote {CKPT.name}: blanked {COLS} for {int(target.sum())} uncoded RSE rows.")
