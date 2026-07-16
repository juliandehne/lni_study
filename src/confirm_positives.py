"""
confirm_positives.py

Optional pipeline step `confirm` — the LLM half of selection, merging the old
`a-candidates` (annotate) and `filter` (keep label==1) into one batched,
top-up loop.

The estimator (`select_candidates.py`) is high-recall: a paper with score >=
min_score is only LIKELY to present research software. This step asks the SAIA
LLM to confirm, but WITHOUT annotating the whole pool up front:

  1. Take the estimator working set named by --set (e.g. `gold`) as the first
     batch of candidates, then the `pool` reservoir as overflow.
  2. Annotate them in batches of --batch (default 50). After each batch, keep the
     papers the model labels `label_research_software == 1`.
  3. Stop as soon as --target confirmed positives have been collected; if a batch
     does not yield enough, the next --batch papers are drawn from the pool and
     annotated. So you only spend API calls until you have enough confirmed RSE
     papers, not on the entire pool.

Output: `.workingset/<set>_confirmed/` (the confirmed PDFs, copied) plus its
`manifest.csv` (id, volume, rel_path, title, certainty) — the same shape
`filter_positives.py` produced, so `prepare_workingset.py --restrict` and the
downstream human steps consume it unchanged. Annotations are also written to a
resumable checkpoint under results/checkpoints/.

Usage (from the lni_study repo root; needs a SAIA token):

    python src/confirm_positives.py --set gold --target 100
    python src/confirm_positives.py --set narrow --target 50 --batch 50
"""

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

import pandas as pd
from openai import OpenAI
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotate_lni import (  # noqa: E402
    DEFAULT_PROMPT, DEFAULT_SAIA_ENDPOINT, CHECKPOINT_COLUMNS, DEFAULT_MAX_TOKENS,
    RateLimiter, load_prompt_template, pdf_to_paper, classify_paper,
)
import paper_length  # noqa: E402  (short-paper cap for the top-up draw)
import preflight  # noqa: E402  (fail-fast SAIA + path checks before the slow load)

REPO_ROOT = Path(__file__).resolve().parent.parent
# LNI_DATA_ROOT supersedes the in-repo default so generated data (results/,
# .workingset/) can live in an external working dir. See annotate_lni.DATA_ROOT.
DATA_ROOT = Path(os.environ.get("LNI_DATA_ROOT") or REPO_ROOT).resolve()
DEFAULT_WORKROOT = DATA_ROOT / ".workingset"
RESULTS_DIR = DATA_ROOT / "results"
CHECKPOINT_DIR = RESULTS_DIR / "checkpoints"


def resolve_repo_path(p: str | Path) -> Path:
    """Manifest 'dst' is stored relative to the data root; resolve it back."""
    p = Path(p)
    return p if p.is_absolute() else (DATA_ROOT / p)


def _manifest_pages(value) -> int | None:
    """Parse a manifest 'pages' cell to an int page count, or None if absent."""
    if value is None or value == "" or pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def record_is_short(rec: dict, threshold: int) -> bool:
    """Is this candidate a short paper? Uses the manifest page count, falling back
    to a cheap local page_count() of the working copy when the manifest predates
    the page column. Unknown length is treated as NOT short. Caches the resolved
    count on the record so order_within_cap doesn't re-open the PDF."""
    pages = rec.get("pages")
    if pages is None:
        pages = paper_length.page_count(rec.get("pdf"))
        rec["pages"] = pages
    return paper_length.is_short(pages, threshold)


def load_set_candidates(workroot: Path, name: str) -> list[dict]:
    """Read a working-set manifest into ordered candidate records.

    Each record carries the LOCAL copy (dst) we extract from — fast disc — and the
    set root so the paper id matches the manifest.
    """
    manifest = workroot / name / "manifest.csv"
    if not manifest.is_file():
        return []
    df = pd.read_csv(manifest, dtype={"id": str})
    set_root = (workroot / name).resolve()
    records = []
    for r in df.to_dict("records"):
        local = resolve_repo_path(r["dst"]) if isinstance(r.get("dst"), str) else None
        pdf = local if (local and local.is_file()) else Path(str(r.get("src", "")))
        records.append({
            "id": str(r["id"]),
            "volume": r.get("volume"),
            "rel_path": r.get("rel_path"),
            "pdf": pdf,
            "set_root": set_root,
            "pages": _manifest_pages(r.get("pages")),
        })
    return records


def _locate_workingset_pdf(workroot: Path, out_dir: Path, rel_path: str) -> Path | None:
    """Find a stageable source PDF for a confirmed paper whose id is no longer in
    the current candidate lists (e.g. the pool reservoir was rebuilt between confirm
    runs, so `load_set_candidates` no longer yields it). Scans the immediate
    working-set subfolders -- pool, gold, narrow, ... -- for `<sub>/<rel_path>`,
    skipping the confirmed output folder itself. Returns the first match, or None.
    This is the reconciliation fallback that keeps the staged folder from drifting
    below the checkpoint (the coder's worklist)."""
    rel = Path(rel_path)
    try:
        subs = [p for p in workroot.iterdir()
                if p.is_dir() and p.resolve() != out_dir.resolve()]
    except OSError:
        return None
    for sub in subs:
        cand = sub / rel
        if cand.is_file():
            return cand
    return None


def materialize_confirmed(workroot: Path, set_name: str, checkpoint: Path,
                          all_candidates: list[dict], done: dict) -> tuple:
    """Stage every checkpoint-confirmed (label==1) paper into `<set>_confirmed/` and
    write its manifest.csv from that same set.

    The SOURCE OF TRUTH is the checkpoint (the coder's worklist), NOT the in-memory
    candidate lists, and each paper is STAGED in the pass its manifest row is written
    -- so the staged folder + manifest can never drift below the checkpoint. This is
    the invariant whose violation left coders with worklist rows whose PDF never
    opened (checkpoint appended per-paper, but PDFs/manifest materialized once at the
    end from `all_candidates`, which a crash or a rebuilt pool reservoir could desync).

    `done` maps id -> final label; a paper is confirmed iff `done.get(id) == 1`. For a
    confirmed id no longer in the candidate lists, the source PDF is located in any
    sibling working-set folder via `_locate_workingset_pdf`. Returns
    `(confirmed_ids, staged_rows, unstaged_ids, out_dir, manifest_path)`."""
    out_dir = workroot / f"{set_name}_confirmed"
    out_dir.mkdir(parents=True, exist_ok=True)

    cand_by_id = {c["id"]: c for c in all_candidates}
    cert_by_id: dict = {}
    title_by_id: dict = {}
    ck_meta: dict = {}   # id -> (volume, rel_path) for ids no longer in candidates
    ck_order: list = []  # checkpoint id order (for ids not seen among candidates)
    if checkpoint.exists():
        ck = pd.read_csv(checkpoint, dtype={"id": str}, on_bad_lines="skip")
        ck["id"] = ck["id"].astype(str)
        cert_by_id = dict(zip(ck["id"],
                              ck.get("label_research_software_certainty", pd.Series(dtype=object))))
        title_by_id = dict(zip(ck["id"], ck.get("title", pd.Series(dtype=object))))
        for r in ck.to_dict("records"):
            cid = str(r["id"])
            if cid not in ck_meta:
                ck_meta[cid] = (r.get("source_folder"), r.get("rel_path"))
                ck_order.append(cid)

    # Ordered union: candidate order first, then any checkpoint-only ids. `done`
    # gives each id's FINAL label, so a reannotated 0->1 paper is included and a
    # 1->0 one is not.
    ordered = [c["id"] for c in all_candidates]
    seen_ids = set(ordered)
    for cid in ck_order:
        if cid not in seen_ids:
            seen_ids.add(cid)
            ordered.append(cid)
    confirmed_ids = [cid for cid in ordered if done.get(cid) == 1]

    rows = []
    unstaged = []
    for cid in confirmed_ids:
        c = cand_by_id.get(cid)
        if c is not None:
            volume, rel = c["volume"], c["rel_path"]
        else:
            volume, rel = ck_meta.get(cid, (None, None))
        if not rel:
            rel = f"{cid}.pdf"
        dst = out_dir / Path(rel)
        # Locate a source PDF: the candidate's local copy first, then -- only if the
        # paper isn't already staged -- any sibling working-set folder.
        src = None
        if c is not None and c["pdf"] and Path(c["pdf"]).is_file():
            src = Path(c["pdf"])
        if src is None and not dst.is_file():
            src = _locate_workingset_pdf(workroot, out_dir, rel)
        if src is not None:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not (dst.exists() and dst.stat().st_size == src.stat().st_size):
                shutil.copy2(src, dst)
        if not dst.is_file():
            unstaged.append(cid)
            continue
        rows.append({
            "id": cid, "volume": volume, "rel_path": rel,
            "title": title_by_id.get(cid), "certainty": cert_by_id.get(cid),
            "dst": str(dst.relative_to(DATA_ROOT)) if dst.is_relative_to(DATA_ROOT) else str(dst),
        })

    manifest = out_dir / "manifest.csv"
    pd.DataFrame(rows, columns=["id", "volume", "rel_path", "title", "certainty", "dst"]).to_csv(
        manifest, index=False)
    return confirmed_ids, rows, unstaged, out_dir, manifest


def load_done_labels(checkpoint: Path) -> dict[str, int | None]:
    """Resume: id -> label_research_software for papers already annotated."""
    if not checkpoint.exists():
        return {}
    df = pd.read_csv(checkpoint, dtype={"id": str}, on_bad_lines="skip")
    lbl = pd.to_numeric(df.get("label_research_software"), errors="coerce")
    return {str(i): (None if pd.isna(v) else int(v)) for i, v in zip(df["id"], lbl)}


def purge_checkpoint_ids(checkpoint: Path, ids: set[str]) -> int:
    """Drop the given ids from the checkpoint so a forced re-annotation REPLACES
    their rows instead of appending duplicates. The original is archived to a
    `.bak` (mirroring annotate_lni's --overwrite), and the kept rows are written
    back reindexed to CHECKPOINT_COLUMNS so the later append (which writes no
    header onto the existing file) stays column-aligned. Returns rows removed."""
    if not ids or not checkpoint.exists():
        return 0
    df = pd.read_csv(checkpoint, dtype={"id": str}, on_bad_lines="skip")
    kept = df[~df["id"].astype(str).isin(ids)]
    removed = len(df) - len(kept)
    if removed == 0:
        return 0
    bak = checkpoint.parent / (checkpoint.name + ".bak")
    n = 1
    while bak.exists():
        n += 1
        bak = checkpoint.parent / (checkpoint.name + f".bak{n}")
    checkpoint.rename(bak)
    kept.reindex(columns=CHECKPOINT_COLUMNS).to_csv(checkpoint, index=False)
    print(f"  --reannotate: archived checkpoint -> {bak.name}; dropped {removed} "
          f"row(s) so they are re-annotated, not duplicated.")
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLM-confirm estimator-positive papers in batches, topping up "
                    "from the pool until --target are confirmed (annotate + filter).")
    parser.add_argument("--set", default="gold",
                        help="Working set to confirm first (e.g. gold, narrow, final).")
    parser.add_argument("--target", type=int, default=None,
                        help="Number of LLM-confirmed (label==1) papers to collect. "
                             "Default: the size of --set's manifest.")
    parser.add_argument("--advance", type=int, default=None,
                        help="LOOP/cursor mode: instead of collecting --target positives, "
                             "annotate the next N not-yet-checkpointed papers and stop "
                             "(checkpoint membership is the cursor, so repeated calls walk "
                             "forward). Used to feed the next ~50 papers into the narrowing "
                             "loop. Overrides --target.")
    parser.add_argument("--reannotate", action="store_true",
                        help="FORCE-REDO mode: re-annotate the already-confirmed (label==1) "
                             "papers of --set (+pool top-ups) under the CURRENT prompt/schema "
                             "instead of reusing their cached labels. Their old checkpoint rows "
                             "are dropped (a .bak is kept) and replaced. Use after changing the "
                             "typology (e.g. methodology -> software_lifecycle) so `collect` "
                             "immediately mines the new dimension across the whole confirmed set, "
                             "without waiting for `advance` to add fresh papers. Combine with "
                             "--advance N to cap how many are redone (bounds token spend).")
    parser.add_argument("--pool", default="pool",
                        help="Working set used as the overflow reservoir (default 'pool').")
    parser.add_argument("--batch", type=int, default=50,
                        help="Annotate in batches of this size, checking progress between "
                             "batches (default 50).")
    parser.add_argument("--short_pages", type=int, default=paper_length.SHORT_PAGE_THRESHOLD,
                        help="A paper with fewer than this many pages is 'short' "
                             f"(default {paper_length.SHORT_PAGE_THRESHOLD}).")
    parser.add_argument("--max_short_frac", type=float, default=paper_length.MAX_SHORT_FRACTION,
                        help="Cap the top-up draw from the pool so at most this fraction of "
                             f"its prefix is short (default {paper_length.MAX_SHORT_FRACTION} = "
                             "20%%). Set to 1.0 to disable the cap on the draw.")
    parser.add_argument("--workroot", default=str(DEFAULT_WORKROOT),
                        help="Root for working sets (default: .workingset/).")
    parser.add_argument("--model", default="mistral-large-3-675b-instruct-2512",
                        help="SAIA model name.")
    parser.add_argument("--run", default="run_1", help="Run identifier.")
    parser.add_argument("--prompt_template", default=str(DEFAULT_PROMPT),
                        help="Path to the prompt template markdown.")
    parser.add_argument("--saia_token", default=None, help="SAIA API key (overrides env).")
    parser.add_argument("--saia_endpoint", default=None, help="SAIA base URL (overrides env).")
    parser.add_argument("--max_text_chars", type=int, default=40000,
                        help="Truncate extracted main text before annotation.")
    parser.add_argument("--max_tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help="Cap the completion length (default %(default)s; a "
                             "complete answer is ~1350 tokens max). 0 = uncapped.")
    args = parser.parse_args()

    workroot = Path(args.workroot).resolve()

    # Fail-fast preflight (BEFORE the candidate load, which scans the pool for
    # page counts). Previously a missing/expired token only surfaced AFTER that
    # load, so a doomed run still "took a long time to start, then crashed". Now
    # an unreachable SAIA endpoint, a rejected token, or a vanished mount aborts
    # in ~1s with a clear message.
    _saia_key = args.saia_token or os.getenv("SAIA_API_KEY")
    _base_url = args.saia_endpoint or os.getenv("SAIA_API_ENDPOINT") or DEFAULT_SAIA_ENDPOINT
    preflight.require(
        [preflight.check_saia(_base_url, _saia_key),
         preflight.check_path(workroot, label="workroot")]
        + preflight.check_data_root())

    # Candidates: the named set first, then the pool reservoir (deduped, in order).
    primary = load_set_candidates(workroot, args.set)
    if not primary:
        raise SystemExit(
            f"No manifest at {workroot / args.set / 'manifest.csv'}. "
            "Run the 'estimate' step first.")
    target = args.target if args.target is not None else len(primary)

    seen = {c["id"] for c in primary}
    overflow = [c for c in load_set_candidates(workroot, args.pool) if c["id"] not in seen]

    # Short-paper cap (topping off): reorder the pool draw so EVERY prefix is
    # <=max_short_frac short. The top-up consumes `overflow` in order until it has
    # enough confirmed positives, so whatever prefix it stops at stays >=80% full
    # papers. The named set ('--set', the goldstandard itself) is left in its
    # manifest order — the cap is scoped to the pool reservoir it draws from.
    n_short_overflow = 0
    if overflow and args.max_short_frac < 1.0:
        # Records whose manifest lacks a page count force a one-time PDF reopen
        # (record_is_short -> paper_length.page_count) here, BEFORE any annotation.
        # On a legacy pool manifest (no `pages` column) that's a scan of the whole
        # reservoir over the corpus mount, which reads as a stall before the bar
        # moves. Time it and report so the slow phase is attributable.
        n_need_scan = sum(1 for c in overflow if c.get("pages") is None)
        if n_need_scan:
            print(f"  scanning page counts for {n_need_scan}/{len(overflow)} pool "
                  f"paper(s) missing a manifest page count (one-time; reopens the "
                  f"PDF). Rebuild the pool manifest to avoid this next time.")
        _t0 = time.perf_counter()
        is_short = lambda c: record_is_short(c, args.short_pages)  # noqa: E731
        overflow = paper_length.order_within_cap(overflow, is_short, args.max_short_frac)
        n_short_overflow = sum(1 for c in overflow if record_is_short(c, args.short_pages))
        _scan_s = time.perf_counter() - _t0
        if n_need_scan:
            print(f"  page scan done in {_scan_s:.1f}s "
                  f"({_scan_s / n_need_scan:.2f}s/paper).")

    candidates = primary + overflow
    print(f"[config] data root  : {DATA_ROOT}"
          + ("  (in-repo default)" if DATA_ROOT == REPO_ROOT else "  (LNI_DATA_ROOT)"))
    print(f"[config] working set: {workroot}")
    print(f"[config] results    : {RESULTS_DIR}  (checkpoints in {CHECKPOINT_DIR.name}/)")
    print(f"Confirming '{args.set}': target {target} positive(s). "
          f"Candidates: {len(primary)} from '{args.set}' + {len(overflow)} from "
          f"'{args.pool}' = {len(candidates)} available.")
    if overflow and args.max_short_frac < 1.0:
        print(f"  pool draw short-capped: {n_short_overflow}/{len(overflow)} short "
              f"(<{args.short_pages}p), interleaved so every top-up prefix is "
              f"<={args.max_short_frac:.0%} short.")

    # SAIA client
    saia_key = args.saia_token or os.getenv("SAIA_API_KEY")
    if not saia_key:
        raise SystemExit("Missing SAIA token. Set SAIA_API_KEY in .env or pass --saia_token.")
    base_url = args.saia_endpoint or os.getenv("SAIA_API_ENDPOINT") or DEFAULT_SAIA_ENDPOINT
    client = OpenAI(api_key=saia_key, base_url=base_url, timeout=300.0)
    rate_limiter = RateLimiter()
    system_prompt, user_prompt_template = load_prompt_template(args.prompt_template)
    prompt_name = Path(args.prompt_template).stem
    temperature, seed, top_p = 0, 42, 1.0

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"{args.set}confirm_{args.model}_{prompt_name}_{args.run}"
    checkpoint = CHECKPOINT_DIR / f"annotations_{tag}_checkpoint.csv"

    # Resume: reuse labels already in the checkpoint.
    done = load_done_labels(checkpoint)
    confirmed: list[dict] = []
    annotated = reused = errors = 0

    # Cursor/loop mode: annotate the next --advance not-yet-done papers and stop.
    # The checkpoint IS the cursor (no extra state file): undone papers are taken
    # in candidate order, so repeated --advance calls walk forward through the set.
    all_candidates = candidates
    if args.reannotate:
        # Force-redo mode: deliberately revisit ALREADY-CONFIRMED (label==1) papers
        # so they are re-annotated under the current prompt/schema. The checkpoint is
        # NOT the cursor here — we drop the redo ids' cached rows up front (keeping a
        # .bak) and pop them from `done`, so the loop annotates them fresh and the
        # rewritten checkpoint has exactly one (new) row per paper.
        target = None
        redo = [c for c in candidates if done.get(c["id"]) == 1]
        if args.advance is not None:
            redo = redo[:args.advance]
        redo_ids = {c["id"] for c in redo}
        purge_checkpoint_ids(checkpoint, redo_ids)
        for cid in redo_ids:
            done.pop(cid, None)
        worklist = redo
        cap = f" (capped at --advance {args.advance})" if args.advance is not None else ""
        print(f"  --reannotate: re-annotating {len(worklist)} already-confirmed "
              f"(label==1) paper(s) of '{args.set}'(+'{args.pool}'){cap} under the "
              f"current prompt so `collect` sees the new dimension immediately.")
    elif args.advance is not None:
        target = None  # advance mode ignores the positive target
        undone = [c for c in candidates if c["id"] not in done]
        worklist = undone[:args.advance]
        print(f"  --advance {args.advance}: annotating the next {len(worklist)} "
              f"not-yet-annotated paper(s) "
              f"({len(candidates) - len(undone)}/{len(candidates)} already done).")
    else:
        worklist = candidates

    print(f"  endpoint: {base_url} | model: {args.model} | batch: {args.batch}")
    print(f"  checkpoint: {checkpoint}")

    # Progress bar. Two modes:
    #   target mode  -> the bar measures CONFIRMED positives toward --target, so it
    #                   fills to 100% exactly when the job is done (it advances only
    #                   on a label==1 paper; papers examined/annotated/reused show in
    #                   the postfix). The reservoir scanned to get there is incidental.
    #   advance mode -> no target, so the bar is per-PAPER over the fixed worklist.
    # The per-batch summary uses tqdm.write so it doesn't tear the bar.
    target_mode = target is not None
    unit = "confirmed" if target_mode else "paper"
    pbar_total = target if target_mode else len(worklist)
    pbar = tqdm(total=pbar_total, desc=f"Confirming {args.set}", unit=unit)
    examined = 0
    topped_up = False
    loop_t0 = time.perf_counter()
    for start in range(0, len(worklist), args.batch):
        if target is not None and len(confirmed) >= target:
            break
        batch = worklist[start:start + args.batch]
        batch_pos = 0
        for j, c in enumerate(batch):
            if target is not None and len(confirmed) >= target:
                break
            # Crossed out of the named set into the pool reservoir: announce the
            # top-up so it's obvious where the extra positives are coming from.
            # (Only meaningful in target mode; advance mode has its own fixed worklist.)
            if args.advance is None and not topped_up and (start + j) >= len(primary):
                topped_up = True
                tqdm.write(f"  '{args.set}' exhausted at {len(confirmed)}/{target} "
                           f"confirmed -> topping up from '{args.pool}' "
                           f"({len(overflow)} available).")
            cid = c["id"]
            if cid in done:
                label = done[cid]
                reused += 1
            else:
                paper = pdf_to_paper(c["pdf"], c["set_root"], args.max_text_chars)
                if paper["extraction_failed"]:
                    flat = {"llm_error": "pdf_extraction_failed", "llm_raw_response": None}
                else:
                    flat = classify_paper(client, paper, args.model, system_prompt,
                                          user_prompt_template, temperature, seed, top_p,
                                          rate_limiter, max_tokens=(args.max_tokens or None))
                row = {
                    "id": cid, "source_folder": c["volume"], "filename": Path(c["rel_path"]).name,
                    "rel_path": c["rel_path"], "title": paper.get("title"),
                    "authors": paper.get("authors"), "model": args.model,
                    "prompt_template": prompt_name, "run": args.run, **flat,
                }
                pd.DataFrame([row], columns=CHECKPOINT_COLUMNS).to_csv(
                    checkpoint, mode="a", header=not checkpoint.exists(), index=False)
                annotated += 1
                if flat.get("llm_error"):
                    errors += 1
                lbl = flat.get("label_research_software")
                try:
                    label = None if lbl is None or lbl == "" else int(float(lbl))
                except (TypeError, ValueError):
                    label = None
                done[cid] = label

            examined += 1
            if label == 1:
                confirmed.append(c)
                batch_pos += 1
                if target_mode:
                    pbar.update(1)  # bar tracks confirmed/target
            if not target_mode:
                pbar.update(1)      # bar tracks papers examined
            if target_mode:
                pbar.set_postfix(examined=examined, annotated=annotated,
                                 reused=reused, errors=errors)
            else:
                pbar.set_postfix(confirmed=len(confirmed), annotated=annotated,
                                 reused=reused, errors=errors)

        bnum = start // args.batch + 1
        tgt = "-" if target is None else target
        elapsed = time.perf_counter() - loop_t0
        # Wall time per NEWLY annotated paper — the real per-paper LLM+extraction
        # cost (reused/cached papers are instant, so divide by `annotated`, not
        # `examined`). This is the number that explains a slow run.
        per_annot = elapsed / annotated if annotated else 0.0
        eta = ""
        if target_mode and len(confirmed) and len(confirmed) < target and annotated:
            # Project remaining wall time: more confirmations needed, divided by the
            # observed confirm-per-annotation rate, times the per-annotation cost.
            conf_rate = len(confirmed) / annotated  # confirmed positives per annotation
            more_annot = (target - len(confirmed)) / conf_rate if conf_rate else 0.0
            eta = f", eta ~{more_annot * per_annot / 60:.0f}m"
        tqdm.write(f"  batch {bnum}: +{batch_pos} confirmed "
                   f"(total {len(confirmed)}/{tgt}; annotated {annotated}, "
                   f"reused {reused}, errors {errors}; "
                   f"{elapsed / 60:.1f}m elapsed, {per_annot:.1f}s/annotated{eta}).")
    pbar.close()

    # The confirmed set is CUMULATIVE and its SOURCE OF TRUTH is the checkpoint the
    # coder's worklist reads: every paper the checkpoint labels ==1 across all rounds.
    # Materialize MUST be driven by that set -- not by the in-memory candidate lists.
    # Previously this rebuilt `confirmed` from `all_candidates` and copied PDFs in a
    # single terminal pass, so (a) a crash/early-stop between the per-paper checkpoint
    # append and this block, or (b) a pool reservoir rebuilt between confirm runs
    # (dropping a confirmed id from the candidate lists), left the staged folder +
    # manifest a subset of the checkpoint. Coders then saw worklist rows whose PDF
    # never opened. Fix: iterate the checkpoint's label==1 ids, and STAGE each paper
    # in the same pass its manifest row is written -- locating a source PDF from any
    # sibling working-set folder when it has fallen out of the candidate lists.
    # (Extracted to `materialize_confirmed` so the invariant is unit-testable offline.)
    confirmed_ids, rows, unstaged, out_dir, manifest = materialize_confirmed(
        workroot, args.set, checkpoint, all_candidates, done)
    if unstaged:
        shown = ", ".join(unstaged[:8]) + (" ..." if len(unstaged) > 8 else "")
        print(f"  WARNING: {len(unstaged)} confirmed paper(s) in the checkpoint could "
              f"not be staged (no source PDF found under {workroot.name}/): {shown}. "
              f"Their worklist rows will not open until the PDF is restored.")

    tgt = "-" if target is None else target
    print(f"\nConfirmed {len(confirmed_ids)}/{tgt} positive(s) -> {out_dir}")
    print(f"Manifest: {manifest} ({len(rows)} staged)")
    if args.advance is not None:
        remaining = len([c for c in all_candidates if c["id"] not in done])
        print(f"Cursor advanced; {remaining} paper(s) still unannotated in "
              f"'{args.set}'+'{args.pool}'. Next: mine this batch with "
              f"`narrow_categories.py --mode collect --from_set {args.set} --to_schema`.")
    elif target is not None and len(confirmed_ids) < target:
        print("\nWARNING: ran out of candidates before reaching the target. "
              "Re-run the 'estimate' step with a larger --cap (or lower --min_score) "
              "to enlarge the pool, then re-run this step (annotations are cached).")


if __name__ == "__main__":
    main()
