"""
pool_manager.py — no-token pool maintenance for the lni_study working sets.

The pipeline keeps several working sets under `.workingset/` that are filled by
the non-LLM estimator (`select_candidates.py`): narrow, gold, final and a `pool`
reservoir. This utility reports how full each set is versus its target and tops
up any short, corpus-filled set straight from the read-only corpus — without
spending a SAIA token. It also draws the **full-study PRETEST** subset: a
stratified sample of `.workingset/final` copied into `.workingset/full_study_pretest`
so a TEST run of the final-study step annotates an isolated subset (its own
folder-derived checkpoint), leaving the real study independent.

Modes (`--mode`):
  report        Print a size-vs-target table for every set. Pure read, offline.
  refill        report, then top up any short corpus-filled set
                (narrow/gold/final/pool) by re-running the estimator. The
                estimator is deterministic and cache-fast, so this just confirms
                full sets and draws more for short ones. Reads the corpus.
  ensure-final  Make sure `.workingset/final` holds at least --need papers (for a
                final-study run of that size); refill from the corpus if short.
  draw-pretest  Rebuild `.workingset/full_study_pretest` as a fresh stratified
                draw of --pretest_n papers from `.workingset/final` (refilling
                final first if it is short). The TEST full-study run annotates
                this folder.

Refill / ensure-final / draw-pretest delegate the actual corpus streaming to
`select_candidates.py` (one tested code path), so the working sets stay exactly
what the `estimate` step would have produced.

Usage (from the lni_study repo root):

    python src/pool_manager.py --mode report  --workroot .workingset
    python src/pool_manager.py --mode refill   --corpus "Z:\\...\\Proceedings" \
        --narrow 50 --gold 100 --final 500 --cap 2000
    python src/pool_manager.py --mode draw-pretest --pretest_n 5 \
        --corpus "Z:\\...\\Proceedings" --final 500 --cap 2000
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sampling import stratified_sample, volume_under, paper_id, format_allocation  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
# LNI_DATA_ROOT supersedes the in-repo default so generated data (.workingset/,
# results/) can live in an external working dir. Mirrors select_candidates.py.
DATA_ROOT = Path(os.environ.get("LNI_DATA_ROOT") or REPO_ROOT).resolve()
DEFAULT_WORKROOT = DATA_ROOT / ".workingset"
SELECT_CANDIDATES = Path(__file__).resolve().parent / "select_candidates.py"

# The corpus-filled sets, in the order the estimator fills them. 'pool' soaks up
# the rest up to --cap. full_study_pretest is NOT corpus-filled — it is drawn
# from `final` — so it is reported but never topped up from the corpus here.
PRETEST_SET = "full_study_pretest"

MANIFEST_COLUMNS = ["id", "volume", "rel_path", "src", "dst", "score", "pages", "signals"]


# --- size reporting ----------------------------------------------------------
def count_pdfs(set_dir: Path) -> int:
    """PDFs actually present on disc in a set (recursive; sets are small + local)."""
    return sum(1 for _ in set_dir.rglob("*.pdf")) if set_dir.is_dir() else 0


def count_manifest(set_dir: Path) -> int | None:
    """Rows in a set's manifest.csv, or None when there is no manifest yet."""
    manifest = set_dir / "manifest.csv"
    if not manifest.is_file():
        return None
    try:
        return len(pd.read_csv(manifest, dtype={"id": str}))
    except Exception:
        return None


def set_targets(args) -> list[tuple[str, int | None]]:
    """Ordered (set name, target) pairs. Pool target mirrors select_candidates'
    `cap - (narrow+gold+final)`; the pretest target is whatever was requested
    for this run (or None = not applicable to a refill)."""
    pool_n = args.cap - (args.narrow + args.gold + args.final)
    targets: list[tuple[str, int | None]] = [
        ("narrow", args.narrow),
        ("gold", args.gold),
        ("final", args.final),
        ("pool", max(pool_n, 0)),
        (PRETEST_SET, args.pretest_n if args.pretest_n else None),
    ]
    return targets


def report_sets(workroot: Path, args) -> None:
    print("\n  Working-set pools "
          f"(workroot: {workroot})")
    print("    set                 on_disk   manifest   target   status")
    print("    " + "-" * 58)
    for name, target in set_targets(args):
        set_dir = workroot / name
        disk = count_pdfs(set_dir)
        man = count_manifest(set_dir)
        man_s = "-" if man is None else str(man)
        tgt_s = "-" if target is None else str(target)
        if target is None:
            status = "" if set_dir.exists() else "(absent)"
        elif disk >= target:
            status = "OK"
        else:
            status = f"SHORT by {target - disk}"
        print(f"    {name:<18}{disk:>9}{man_s:>11}{tgt_s:>9}   {status}")
    print()


# --- corpus refill (delegates to the estimator) ------------------------------
def run_estimator(args, final_target: int) -> int:
    """Top up the corpus-filled sets by re-running select_candidates.py with the
    given final-set target (cap is raised if final would not otherwise fit). The
    estimator is deterministic + score-cached, so full sets are merely re-confirmed
    and only short sets draw fresh papers. Returns the subprocess exit code."""
    if not args.corpus:
        print("  [refill] no --corpus given; cannot draw from the corpus. "
              "Reporting only.")
        return 1
    corpus = Path(args.corpus)
    if not corpus.is_dir():
        print(f"  [refill] corpus not reachable ({corpus}); skipping the draw. "
              "Reporting only.")
        return 1
    cap = max(args.cap, args.narrow + args.gold + final_target)
    cmd = [
        sys.executable, str(SELECT_CANDIDATES),
        "--corpus", str(corpus),
        "--min_score", str(args.min_score),
        "--narrow", str(args.narrow),
        "--gold", str(args.gold),
        "--final", str(final_target),
        "--cap", str(cap),
        "--short_pages", str(args.short_pages),
        "--max_short_frac", str(args.max_short_frac),
        "--workroot", str(args.workroot),
        "--seed", str(args.seed),
    ]
    print(f"  [refill] streaming the corpus to fill narrow/gold/final({final_target})/pool "
          f"(cap {cap}) ...")
    return subprocess.run(cmd, cwd=str(REPO_ROOT)).returncode


def ensure_final(workroot: Path, args, need: int) -> int:
    """Guarantee `.workingset/final` holds at least `need` papers, refilling from
    the corpus if short. Returns the final paper count after any refill."""
    final_dir = workroot / "final"
    have = count_pdfs(final_dir)
    if have >= need:
        print(f"  [ensure-final] final has {have} paper(s) >= {need} needed — no refill.")
        return have
    print(f"  [ensure-final] final has {have} paper(s) < {need} needed — refilling.")
    run_estimator(args, final_target=max(args.final, need))
    have = count_pdfs(final_dir)
    if have < need:
        print(f"  [ensure-final] WARNING: final still holds only {have} paper(s) "
              f"(< {need}). The corpus may be exhausted at score>={args.min_score}.")
    return have


# --- full-study PRETEST draw -------------------------------------------------
def draw_pretest(workroot: Path, args) -> int:
    """Rebuild `.workingset/full_study_pretest` as a fresh stratified draw of
    --pretest_n papers from `.workingset/final` (refilling final first if short).
    Returns the number of papers placed in the pretest set."""
    n = args.pretest_n
    if not n or n < 1:
        raise SystemExit("draw-pretest needs --pretest_n >= 1.")
    final_dir = workroot / "final"
    ensure_final(workroot, args, need=n)

    pdfs = sorted(final_dir.rglob("*.pdf"))
    if not pdfs:
        print(f"  [draw-pretest] no PDFs under {final_dir}; nothing to draw. "
              "Run 'estimate' (or check the corpus path) first.")
        return 0
    if len(pdfs) < n:
        print(f"  [draw-pretest] final holds only {len(pdfs)} paper(s) < {n} "
              f"requested — drawing all {len(pdfs)}.")
        n = len(pdfs)

    vol_of = volume_under(final_dir)
    vol_by_path = {str(p): vol_of(p) for p in pdfs}
    selected, alloc = stratified_sample(
        pdfs, n, seed=args.seed, group_fn=lambda p: vol_by_path[str(p)])
    sizes = {}
    for p in pdfs:
        sizes[vol_by_path[str(p)]] = sizes.get(vol_by_path[str(p)], 0) + 1
    print(f"  [draw-pretest] stratified draw of {len(selected)} of {len(pdfs)} "
          f"final paper(s) across {len(sizes)} volume(s) (seed={args.seed}).")
    print(f"  [draw-pretest] allocation: {format_allocation(alloc, sizes)}")

    # Enrich the new manifest rows from final's manifest (score/pages/signals/src)
    # when available; fall back to bare path info otherwise.
    final_rows = _manifest_by_id(final_dir)

    pretest_dir = workroot / PRETEST_SET
    # Rebuild from scratch so the annotate target is EXACTLY the freshly drawn N
    # (a previous, larger draw must not leave stale PDFs that would be annotated).
    if pretest_dir.exists():
        shutil.rmtree(pretest_dir)
    pretest_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for src_pdf in selected:
        rel = src_pdf.relative_to(final_dir)
        dst = pretest_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not (dst.exists() and dst.stat().st_size == src_pdf.stat().st_size):
            shutil.copy2(src_pdf, dst)
        pid = paper_id(src_pdf, final_dir)
        base = final_rows.get(pid, {})
        rows.append({
            "id": pid,
            "volume": base.get("volume", vol_by_path[str(src_pdf)]),
            "rel_path": rel.as_posix(),
            "src": base.get("src", str(src_pdf)),
            "dst": str(dst.relative_to(DATA_ROOT)) if dst.is_relative_to(DATA_ROOT) else str(dst),
            "score": base.get("score", ""),
            "pages": base.get("pages", ""),
            "signals": base.get("signals", "{}"),
        })
    pd.DataFrame(rows, columns=MANIFEST_COLUMNS).to_csv(
        pretest_dir / "manifest.csv", index=False)
    print(f"  [draw-pretest] wrote {len(rows)} paper(s) -> {pretest_dir}")
    print(f"  [draw-pretest] the TEST full-study run annotates this folder "
          f"(checkpoint tag derived from '{PRETEST_SET}', isolated from the real study).")
    return len(rows)


def _manifest_by_id(set_dir: Path) -> dict[str, dict]:
    """id -> manifest row dict for a set, or {} when there is no manifest."""
    manifest = set_dir / "manifest.csv"
    if not manifest.is_file():
        return {}
    df = pd.read_csv(manifest, dtype={"id": str})
    return {str(r["id"]): r.to_dict() for _, r in df.iterrows()}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report and refill the lni_study working-set pools, and draw "
                    "the full-study pretest subset. No SAIA token is ever used.")
    parser.add_argument("--mode", required=True,
                        choices=["report", "refill", "ensure-final", "draw-pretest"],
                        help="report sizes / refill short sets / ensure final size / "
                             "draw the pretest subset from final.")
    parser.add_argument("--corpus", default=os.environ.get("LNI_CORPUS"),
                        help="Corpus folder (needed by refill/ensure-final/draw-pretest "
                             "when a set is short).")
    parser.add_argument("--workroot", default=str(DEFAULT_WORKROOT),
                        help="Root for the working sets (default: .workingset/).")
    parser.add_argument("--min_score", type=float, default=2.0)
    parser.add_argument("--narrow", type=int, default=50)
    parser.add_argument("--gold", type=int, default=100)
    parser.add_argument("--final", type=int, default=500)
    parser.add_argument("--cap", type=int, default=2000)
    parser.add_argument("--short_pages", type=int, default=6)
    parser.add_argument("--max_short_frac", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--need", type=int, default=None,
                        help="ensure-final: minimum papers final must hold (default --final).")
    parser.add_argument("--pretest_n", type=int, default=None,
                        help="draw-pretest: how many papers to draw from final into "
                             "the pretest set (also reported as the pretest target).")
    args = parser.parse_args()

    workroot = Path(args.workroot).resolve()
    print(f"[config] data root  : {DATA_ROOT}"
          + ("  (in-repo default)" if DATA_ROOT == REPO_ROOT else "  (LNI_DATA_ROOT)"))
    print(f"[config] working set: {workroot}")
    if args.corpus:
        print(f"[config] corpus     : {args.corpus}  [read-only source]")

    if args.mode == "report":
        report_sets(workroot, args)
        return

    if args.mode == "refill":
        report_sets(workroot, args)
        rc = run_estimator(args, final_target=args.final)
        print("\n  After refill:")
        report_sets(workroot, args)
        sys.exit(rc)

    if args.mode == "ensure-final":
        need = args.need if args.need else args.final
        report_sets(workroot, args)
        have = ensure_final(workroot, args, need=need)
        # Non-zero exit only when we could not reach the requested size, so the
        # caller can warn; the annotate step still runs on whatever is present.
        sys.exit(0 if have >= need else 2)

    if args.mode == "draw-pretest":
        report_sets(workroot, args)
        placed = draw_pretest(workroot, args)
        report_sets(workroot, args)
        sys.exit(0 if placed > 0 else 2)


if __name__ == "__main__":
    main()
