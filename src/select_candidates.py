"""
select_candidates.py

Estimator-driven candidate selection (pipeline step `estimate`).

Instead of scoring the WHOLE corpus and then taking a stratified top-N (which
reads and extracts every PDF on the slow mount before selecting anything), this
step STREAMS the corpus folder-balanced and stops as soon as it has collected
enough likely-research-software papers:

  1. Enumerate the volume folders under --corpus and COUNT the PDFs in each
     (a cheap non-recursive listing — no text extraction, no whole-tree rglob).
  2. Build a folder-weighted draw order (`sampling.folder_weighted_order`): each
     folder is weighted by its file count, so every PDF has the same probability
     of being drawn, but the pass spans all volumes from the start.
  3. Walk that order ONE PDF AT A TIME (tqdm): extract its text, score it with
     the non-LLM `rse_estimator`, and if it clears --min_score copy it into the
     CURRENT working set. The sets are filled in sequence:
        narrow (50)  ->  gold (100)  ->  final (500)  ->  pool (the rest)
     and the whole pass stops once --cap estimator-positives have been found
     (default 2000) or the corpus is exhausted.

So the SAIA API (and the human gold-coding) only ever sees papers the estimator
flagged, and we never extract more of the corpus than we have to.

Output: one `.workingset/<name>/` per set (PDFs copied preserving their
corpus-relative path, plus `manifest.csv`). The `pool` set is the reservoir the
optional LLM-confirmation step (`confirm_positives.py`) tops up from.

Scores are cached to `results/rse_scores_<corpus>.csv` as we go, so a re-run (or
the rest of an interrupted pass) skips re-extracting already-scored PDFs.

Usage (from the lni_study repo root):

    python src/select_candidates.py --corpus "Z:\\Publikationen\\LNI\\Proceedings" \
        --min_score 2.0 --narrow 50 --gold 100 --final 500 --cap 2000

Downstream: human steps run against `.workingset/narrow` and `.workingset/gold`,
the final study annotates `.workingset/final`, and `confirm_positives.py` can
LLM-confirm any of these from `.workingset/pool`.
"""

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

try:
    from tqdm import tqdm
except ImportError:  # tqdm is a dependency, but degrade gracefully
    def tqdm(it=None, **_kw):
        return it if it is not None else []

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdf_text_extraction import extract_text_from_pdf, mupdf_warning_summary  # noqa: E402
from rse_estimator import estimate  # noqa: E402
from sampling import folder_weighted_order, volume_under, paper_id  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKROOT = REPO_ROOT / ".workingset"
RESULTS_DIR = REPO_ROOT / "results"

SCORE_COLUMNS = ["id", "volume", "rel_path", "src", "score", "signals"]
MANIFEST_COLUMNS = ["id", "volume", "rel_path", "src", "dst", "score", "signals"]


def enumerate_volumes(corpus: Path) -> dict[str, list[Path]]:
    """Map each volume folder under `corpus` to its PDFs (one cheap listing).

    Mirrors annotate_lni.find_pdfs: the corpus is shallow
    (`<corpus>/<volume>/<paper>.pdf`), so a NON-recursive glob per volume avoids
    walking the whole tree on the slow mount and gives the per-folder counts we
    weight the draw by.
    """
    volumes = sorted(d for d in corpus.iterdir() if d.is_dir())
    groups: dict[str, list[Path]] = {}
    pbar = tqdm(volumes, desc="Counting PDFs per volume", unit="vol")
    for vol in pbar:
        files = sorted(vol.glob("*.pdf"))
        if files:
            groups[vol.name] = files
        try:
            pbar.set_postfix_str(f"{sum(len(v) for v in groups.values())} pdfs")
        except AttributeError:
            pass
    return groups


def load_score_cache(cache: Path, rescore: bool) -> dict[str, float]:
    """id -> score for already-scored PDFs, so a re-run skips re-extraction."""
    if rescore or not cache.is_file():
        return {}
    df = pd.read_csv(cache, dtype={"id": str})
    print(f"Score cache {cache.name}: {len(df)} PDF(s) already scored "
          "(skipped unless --rescore).")
    return dict(zip(df["id"].astype(str), df["score"].astype(float)))


def write_manifest(workroot: Path, name: str, rows: list[dict]) -> Path:
    """Write one working set's manifest.csv (idempotent — safe to call repeatedly,
    e.g. the moment a set fills AND again at the end of the scan)."""
    manifest = workroot / name / "manifest.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=MANIFEST_COLUMNS).to_csv(manifest, index=False)
    return manifest


def load_cache_rows(cache: Path) -> dict:
    """id -> full cached row (src/score/signals/...), for rebuilding manifests."""
    if not cache.is_file():
        return {}
    df = pd.read_csv(cache, dtype={"id": str})
    return {str(r["id"]): r.to_dict() for _, r in df.iterrows()}


def manifest_rows_from_disk(set_dir: Path, cache_by_id: dict) -> list[dict]:
    """Reconstruct a set's manifest rows from the PDFs already copied into it.

    Used by --regen_manifests to recover a run that copied the PDFs but was
    interrupted before writing the manifests. id/volume/rel_path come from the
    on-disk paths (the working copy preserves each PDF's corpus-relative path);
    src/score/signals are filled from the score cache when the id is present."""
    vol_of = volume_under(set_dir)
    rows = []
    for pdf in sorted(set_dir.rglob("*.pdf")):
        rel = pdf.relative_to(set_dir)
        pid = paper_id(pdf, set_dir)
        c = cache_by_id.get(pid, {})
        dst = str(pdf.relative_to(REPO_ROOT)) if pdf.is_relative_to(REPO_ROOT) else str(pdf)
        rows.append({
            "id": pid,
            "volume": vol_of(pdf),
            "rel_path": rel.as_posix(),
            "src": c.get("src", ""),
            "dst": dst,
            "score": c.get("score", ""),
            "signals": c.get("signals", "{}"),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stream the corpus folder-balanced and copy estimator-positive "
                    "papers into the narrow/gold/final/pool working sets, stopping "
                    "once --cap positives are found.")
    parser.add_argument("--corpus", required=True,
                        help="Full corpus folder (LNI volume subfolders; on the slow disc).")
    parser.add_argument("--min_score", type=float, default=2.0,
                        help="A paper counts as research-software when its estimator "
                             "score is >= this (default 2.0).")
    parser.add_argument("--narrow", type=int, default=50,
                        help="Size of the subcategory-narrowing set (default 50).")
    parser.add_argument("--gold", type=int, default=100,
                        help="Size of the goldstandard set, disjoint from narrow (default 100).")
    parser.add_argument("--final", type=int, default=500,
                        help="Size of the final-study set, disjoint from the above (default 500).")
    parser.add_argument("--cap", type=int, default=2000,
                        help="Stop after this many estimator-positives total; the leftover "
                             "(cap - narrow - gold - final) becomes the 'pool' reservoir "
                             "for LLM confirmation (default 2000).")
    parser.add_argument("--seed", type=int, default=42,
                        help="Seed for the folder-weighted draw (reproducible).")
    parser.add_argument("--max_text_chars", type=int, default=300000,
                        help="Truncate extracted text before scoring (bounds regex time).")
    parser.add_argument("--workroot", default=str(DEFAULT_WORKROOT),
                        help="Root for working sets (default: .workingset/).")
    parser.add_argument("--scores_csv", default=None,
                        help="Score cache path (default results/rse_scores_<corpus>.csv).")
    parser.add_argument("--rescore", action="store_true",
                        help="Ignore the score cache and re-extract every PDF visited.")
    parser.add_argument("--list_only", action="store_true",
                        help="Score + select + write manifests, but do NOT copy PDFs.")
    parser.add_argument("--regen_manifests", action="store_true",
                        help="Recovery: rebuild each set's manifest.csv from the PDFs "
                             "already in .workingset/<set>/ + the score cache, WITHOUT "
                             "scanning the corpus. Use if a run copied PDFs but was "
                             "interrupted before writing manifests.")
    args = parser.parse_args()

    corpus = Path(args.corpus).resolve()
    if not corpus.is_dir() and not args.regen_manifests:
        raise SystemExit(f"--corpus is not a directory: {corpus}")

    # Working-set targets, filled in this order. 'pool' soaks up the rest up to --cap.
    pool_n = args.cap - (args.narrow + args.gold + args.final)
    if pool_n < 0:
        raise SystemExit(
            f"--cap ({args.cap}) is smaller than narrow+gold+final "
            f"({args.narrow + args.gold + args.final}); raise --cap or lower a set size.")
    targets = [("narrow", args.narrow), ("gold", args.gold),
               ("final", args.final), ("pool", pool_n)]
    targets = [(name, n) for name, n in targets if n > 0]

    workroot = Path(args.workroot).resolve()
    # Safety: never write a working copy into (or over) the read-only corpus.
    if workroot == corpus or workroot.is_relative_to(corpus) or corpus.is_relative_to(workroot):
        raise SystemExit(
            f"Refusing to run: workroot {workroot} overlaps the read-only corpus "
            f"{corpus}. Choose a --workroot outside the corpus.")

    cache = Path(args.scores_csv).resolve() if args.scores_csv \
        else RESULTS_DIR / f"rse_scores_{corpus.name}.csv"

    if args.regen_manifests:
        cache_by_id = load_cache_rows(cache)
        print(f"Regenerating manifests from the working sets under {workroot} "
              f"(no corpus scan; {len(cache_by_id)} cached score(s) available).")
        for name, _n in targets:
            set_dir = workroot / name
            if not set_dir.is_dir():
                print(f"  {name:7s}: no folder under {workroot}, skipped.")
                continue
            rows = manifest_rows_from_disk(set_dir, cache_by_id)
            manifest = write_manifest(workroot, name, rows)
            n_cached = sum(1 for r in rows if r["score"] != "")
            print(f"  {name:7s}: {len(rows):5d} paper(s) -> {manifest}  "
                  f"({n_cached} with cached score)")
        return

    groups = enumerate_volumes(corpus)
    total_pdfs = sum(len(v) for v in groups.values())
    if total_pdfs == 0:
        raise SystemExit(f"No PDFs found under {corpus}")
    print(f"Corpus: {total_pdfs} PDF(s) across {len(groups)} volume folder(s).")
    print(f"Targets (in order): "
          + ", ".join(f"{name}={n}" for name, n in targets)
          + f"  | gate score>={args.min_score}, cap={args.cap}")

    order = folder_weighted_order(groups, seed=args.seed)

    score_cache = load_score_cache(cache, args.rescore)
    vol_of = volume_under(corpus)

    # Prepare working-set dirs + manifest row buffers.
    set_rows: dict[str, list[dict]] = {name: [] for name, _ in targets}
    for name, _ in targets:
        (workroot / name).mkdir(parents=True, exist_ok=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    # Append newly-scored rows to the cache as we go, so an interrupted pass over
    # the slow mount does not have to re-extract what it already read.
    cache_is_new = not cache.is_file()
    cache_fh = None if args.rescore else open(cache, "a", newline="", encoding="utf-8")
    if args.rescore:  # start the cache fresh
        cache_fh = open(cache, "w", newline="", encoding="utf-8")
        cache_is_new = True
    cache_writer = csv.DictWriter(cache_fh, fieldnames=SCORE_COLUMNS)
    if cache_is_new:
        cache_writer.writeheader()

    ti = 0                       # current target index
    found = {name: 0 for name, _ in targets}
    n_scored = n_extracted = n_positive = 0

    pbar = tqdm(order, desc="Scanning corpus", unit="pdf")
    try:
        for pdf in pbar:
            if ti >= len(targets):
                break
            pid = paper_id(pdf, corpus)
            vol = vol_of(pdf)
            rel = pdf.relative_to(corpus)

            if pid in score_cache:
                score = score_cache[pid]
                signals = "{}"
            else:
                try:
                    text = extract_text_from_pdf(pdf)
                except Exception as exc:  # a broken PDF must not abort the scan
                    text = None
                    tqdm.write(f"  extraction error ({type(exc).__name__}) for {pdf.name}; score 0")
                if text and args.max_text_chars and len(text) > args.max_text_chars:
                    text = text[:args.max_text_chars]
                est = estimate(text)
                score = est["score"]
                signals = json.dumps(est["signals"], ensure_ascii=False)
                score_cache[pid] = score
                n_extracted += 1
                cache_writer.writerow({"id": pid, "volume": vol, "rel_path": rel.as_posix(),
                                       "src": str(pdf), "score": score, "signals": signals})
                if n_extracted % 50 == 0:
                    cache_fh.flush()
            n_scored += 1

            if score >= args.min_score:
                n_positive += 1
                name, n = targets[ti]
                dst = workroot / name / rel
                if not args.list_only:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not (dst.exists() and dst.stat().st_size == pdf.stat().st_size):
                        shutil.copy2(pdf, dst)
                set_rows[name].append({
                    "id": pid, "volume": vol, "rel_path": rel.as_posix(),
                    "src": str(pdf),
                    "dst": str(dst.relative_to(REPO_ROOT)) if dst.is_relative_to(REPO_ROOT) else str(dst),
                    "score": score, "signals": signals,
                })
                found[name] += 1
                if found[name] >= n:
                    write_manifest(workroot, name, set_rows[name])
                    tqdm.write(f"==> '{name}' set complete: {found[name]} paper(s) "
                               f"-> manifest written (scanned {n_scored}, "
                               f"{n_positive} positives so far).")
                    ti += 1

            try:
                cur = targets[ti][0] if ti < len(targets) else "done"
                fill = f"{found[cur]}/{dict(targets).get(cur, 0)}" if cur != "done" else "all sets full"
                pbar.set_postfix_str(f"pos {n_positive} | filling {cur} {fill}")
            except (AttributeError, KeyError):
                pass
    finally:
        if cache_fh is not None:
            cache_fh.flush()
            cache_fh.close()

    print(f"\n{mupdf_warning_summary()}")
    print(f"Scanned {n_scored}/{total_pdfs} PDF(s) "
          f"({n_extracted} freshly extracted, {n_scored - n_extracted} from cache); "
          f"{n_positive} estimator-positive (score>={args.min_score}).")

    # Write each set's manifest. Completed sets were already written the moment
    # they filled; this also covers any set the corpus ran dry on (e.g. pool).
    for name, n in targets:
        manifest = write_manifest(workroot, name, set_rows[name])
        status = "OK" if found[name] >= n else f"SHORT (corpus exhausted before {n})"
        print(f"  {name:7s}: {found[name]:5d}/{n:<5d} -> {manifest}  [{status}]")

    if any(found[name] < n for name, n in targets):
        print("\nWARNING: at least one set is short — the corpus ran out of "
              "estimator-positives before the targets were met. Lower --min_score "
              "and re-run (cached scores make the re-run fast) if you need more.")

    print("\nNext:")
    print("  - human steps run on .workingset/narrow and .workingset/gold")
    print("  - final study annotates .workingset/final")
    print("  - (optional) LLM-confirm a set, topping up from .workingset/pool:")
    print("      python src/confirm_positives.py --set gold --target 100")


if __name__ == "__main__":
    main()