"""
prepare_workingset.py

Materialize a small, LOCAL working copy of a stratified PDF sample so the human
annotation cycles (subcategory narrowing review, goldstandard coding) never touch
the full corpus.

Why: the full LNI corpus lives on a slow mounted disc. The narrowing and
goldstandard steps open the same handful of PDFs over and over, which is painful
off a slow mount. The full corpus only needs to be read (a) here, when drawing a
sample, and (b) for the final full-corpus annotation. Everything in between runs
against a fast local copy under `.workingset/` (gitignored; PDFs are never
committed).

Each PDF is copied **preserving its path relative to the corpus root**, e.g.
  <corpus>/lni338/sub/x.pdf  ->  <workdir>/<name>/lni338/sub/x.pdf
so the paper id (`<immediate-parent>/<stem>`) and the LNI-volume stratum
(top-level folder) are identical whether a script runs on the full corpus or the
local copy. As a result `annotate_lni.py`, `narrow_categories.py` and
`build_goldstandard.py` work against the working copy with no changes — just
point their folder argument at `.workingset/<name>`.

Sampling is the same stratified, proportional draw used everywhere else
(`sampling.py`), with the LNI volume folders as strata. Pass `--exclude` a prior
manifest to draw a sample DISJOINT from it (e.g. the goldstandard set excluding
the narrowing set), and `--restrict` a manifest to draw ONLY from a given pool
(e.g. the label==1 positives from `filter_positives.py`).

Usage (from the lni_study repo root). In the estimator pipeline the narrow/gold
sets are drawn from the locally-copied candidates, restricted to the positives:

    # Narrowing set: 50 papers from the research-software positives
    python src/prepare_workingset.py ^
        --corpus .workingset/candidates ^
        --name narrow --sample 50 ^
        --restrict .workingset/positives/manifest.csv

    # Goldstandard set: 100 positives, disjoint from the narrowing set
    python src/prepare_workingset.py ^
        --corpus .workingset/candidates ^
        --name gold --sample 100 ^
        --restrict .workingset/positives/manifest.csv ^
        --exclude .workingset/narrow/manifest.csv

Writes the copied PDFs plus `.workingset/<name>/manifest.csv` (id, volume,
rel_path, src, dst). Idempotent: already-copied PDFs are skipped, so a re-run
resumes an interrupted copy.
"""

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sampling import stratified_sample, format_allocation, volume_under, paper_id  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKROOT = REPO_ROOT / ".workingset"


def load_manifest_ids(paths: list[str], flag: str) -> set[str]:
    """Collect paper ids from one or more manifest CSV(s) (the 'id' column)."""
    ids: set[str] = set()
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = REPO_ROOT / raw
        if not p.is_file():
            raise SystemExit(f"{flag} manifest not found: {p}")
        df = pd.read_csv(p, dtype={"id": str})
        if "id" not in df.columns:
            raise SystemExit(f"{flag} manifest has no 'id' column: {p}")
        ids.update(df["id"].dropna().astype(str))
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy a stratified PDF sample to a local working set for fast "
                    "human-annotation cycles.")
    parser.add_argument("--corpus", required=True,
                        help="Full corpus folder (LNI volume subfolders; on the slow disc).")
    parser.add_argument("--name", required=True,
                        help="Working-set name, e.g. 'narrow' or 'gold' "
                             "(-> .workingset/<name>/).")
    parser.add_argument("--sample", type=int, required=True,
                        help="Stratified sample size (volumes as strata).")
    parser.add_argument("--seed", type=int, default=42,
                        help="Seed for the stratified draw (reproducible).")
    parser.add_argument("--exclude", action="append", default=[],
                        help="Prior manifest CSV(s) whose papers to EXCLUDE, so this "
                             "draw is disjoint from them. Repeatable.")
    parser.add_argument("--restrict", action="append", default=[],
                        help="Manifest CSV(s) whose papers are the ONLY ones eligible "
                             "(e.g. the label==1 positives pool). Repeatable; the draw "
                             "pool is the intersection with these ids.")
    parser.add_argument("--workroot", default=str(DEFAULT_WORKROOT),
                        help="Root for working sets (default: .workingset/).")
    parser.add_argument("--list_only", action="store_true",
                        help="Draw + write the manifest but do NOT copy PDFs (preview).")
    args = parser.parse_args()

    corpus = Path(args.corpus).resolve()
    if not corpus.is_dir():
        raise SystemExit(f"--corpus is not a directory: {corpus}")
    pdfs = sorted(corpus.rglob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found under {corpus}")

    excluded = load_manifest_ids(args.exclude, "--exclude")
    restricted = load_manifest_ids(args.restrict, "--restrict") if args.restrict else None
    pool = [p for p in pdfs
            if paper_id(p, corpus) not in excluded
            and (restricted is None or paper_id(p, corpus) in restricted)]
    if restricted is not None:
        print(f"Restricting to {len(restricted)} eligible paper id(s) from "
              f"{len(args.restrict)} manifest(s).")
    if excluded:
        print(f"Excluding {len(excluded)} paper(s) from {len(args.exclude)} prior "
              f"manifest(s); pool: {len(pool)}/{len(pdfs)}.")
    if not pool:
        raise SystemExit("Draw pool is empty after --restrict/--exclude filtering.")

    vol_of = volume_under(corpus)
    sizes = {v: sum(1 for p in pool if vol_of(p) == v)
             for v in {vol_of(p) for p in pool}}
    sample_pdfs, alloc = stratified_sample(pool, args.sample, seed=args.seed, group_fn=vol_of)
    print(f"Corpus: {len(pdfs)} PDF(s) across {len(sizes)} volume(s) under {corpus}.")
    print(f"Stratified draw of {len(sample_pdfs)} (seed={args.seed}).")
    print(f"  Allocation per volume: {format_allocation(alloc, sizes)}")

    workdir = Path(args.workroot).resolve() / args.name
    # Safety: the corpus is strictly read-only. Refuse to write the working copy
    # into (or as a parent of) the corpus tree, so a misconfigured --workroot can
    # never overwrite source PDFs.
    if workdir == corpus or workdir.is_relative_to(corpus) or corpus.is_relative_to(workdir):
        raise SystemExit(
            f"Refusing to run: working dir {workdir} overlaps the read-only corpus "
            f"{corpus}. Choose a --workroot outside the corpus.")
    workdir.mkdir(parents=True, exist_ok=True)

    rows = []
    copied = skipped = 0
    for pdf in sample_pdfs:
        rel = pdf.relative_to(corpus)          # preserve structure -> stable id/volume
        dst = workdir / rel
        if not args.list_only:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and dst.stat().st_size == pdf.stat().st_size:
                skipped += 1
            else:
                shutil.copy2(pdf, dst)
                copied += 1
        rows.append({
            "id": paper_id(pdf, corpus),
            "volume": vol_of(pdf),
            "rel_path": rel.as_posix(),
            "src": str(pdf),
            "dst": str(dst.relative_to(REPO_ROOT)) if dst.is_relative_to(REPO_ROOT) else str(dst),
        })

    manifest = workdir / "manifest.csv"
    pd.DataFrame(rows).to_csv(manifest, index=False)

    if args.list_only:
        print(f"\nlist-only: no PDFs copied. Manifest written: {manifest}")
    else:
        print(f"\nCopied {copied} new, skipped {skipped} existing -> {workdir}")
        print(f"Manifest: {manifest}")
    print("\nNext: run Phase A and the human steps against this local copy, e.g.")
    print(f"  python src/annotate_lni.py --lni_folder {workdir}")


if __name__ == "__main__":
    main()
