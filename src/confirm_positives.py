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
from pathlib import Path

import pandas as pd
from openai import OpenAI
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotate_lni import (  # noqa: E402
    DEFAULT_PROMPT, DEFAULT_SAIA_ENDPOINT, CHECKPOINT_COLUMNS,
    RateLimiter, load_prompt_template, pdf_to_paper, classify_paper,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKROOT = REPO_ROOT / ".workingset"
RESULTS_DIR = REPO_ROOT / "results"
CHECKPOINT_DIR = RESULTS_DIR / "checkpoints"


def resolve_repo_path(p: str | Path) -> Path:
    """Manifest 'dst' is stored relative to the repo root; resolve it back."""
    p = Path(p)
    return p if p.is_absolute() else (REPO_ROOT / p)


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
        })
    return records


def load_done_labels(checkpoint: Path) -> dict[str, int | None]:
    """Resume: id -> label_research_software for papers already annotated."""
    if not checkpoint.exists():
        return {}
    df = pd.read_csv(checkpoint, dtype={"id": str}, on_bad_lines="skip")
    lbl = pd.to_numeric(df.get("label_research_software"), errors="coerce")
    return {str(i): (None if pd.isna(v) else int(v)) for i, v in zip(df["id"], lbl)}


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
    parser.add_argument("--pool", default="pool",
                        help="Working set used as the overflow reservoir (default 'pool').")
    parser.add_argument("--batch", type=int, default=50,
                        help="Annotate in batches of this size, checking progress between "
                             "batches (default 50).")
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
    args = parser.parse_args()

    workroot = Path(args.workroot).resolve()

    # Candidates: the named set first, then the pool reservoir (deduped, in order).
    primary = load_set_candidates(workroot, args.set)
    if not primary:
        raise SystemExit(
            f"No manifest at {workroot / args.set / 'manifest.csv'}. "
            "Run the 'estimate' step first.")
    target = args.target if args.target is not None else len(primary)

    seen = {c["id"] for c in primary}
    overflow = [c for c in load_set_candidates(workroot, args.pool) if c["id"] not in seen]
    candidates = primary + overflow
    print(f"Confirming '{args.set}': target {target} positive(s). "
          f"Candidates: {len(primary)} from '{args.set}' + {len(overflow)} from "
          f"'{args.pool}' = {len(candidates)} available.")

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
    if args.advance is not None:
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

    # Paper-level progress bar. It starts sized to the named set only (so it reads
    # e.g. /50, matching "confirm the set first"); it grows to the full candidate
    # count ONLY if the set is exhausted before --target and we top up from the pool.
    # Updates per PDF and stops early once --target is reached. The postfix shows
    # confirmed/target live; the per-batch summary uses tqdm.write so it doesn't
    # tear the bar.
    pbar_total = len(worklist) if args.advance is not None else len(primary)
    pbar = tqdm(total=pbar_total, desc=f"Confirming {args.set}", unit="paper")
    topped_up = False
    for start in range(0, len(worklist), args.batch):
        if target is not None and len(confirmed) >= target:
            break
        batch = worklist[start:start + args.batch]
        batch_pos = 0
        for j, c in enumerate(batch):
            if target is not None and len(confirmed) >= target:
                break
            # Crossed out of the named set into the pool reservoir: grow the bar and
            # announce the top-up, so it's obvious why the total jumps past the set size.
            # (Only meaningful in target mode; advance mode has its own fixed worklist.)
            if args.advance is None and not topped_up and (start + j) >= len(primary):
                topped_up = True
                pbar.total = len(candidates)
                pbar.refresh()
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
                                          rate_limiter)
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

            if label == 1:
                confirmed.append(c)
                batch_pos += 1

            pbar.update(1)
            tgt = "-" if target is None else target
            pbar.set_postfix(confirmed=f"{len(confirmed)}/{tgt}",
                             annotated=annotated, reused=reused, errors=errors)

        bnum = start // args.batch + 1
        tgt = "-" if target is None else target
        tqdm.write(f"  batch {bnum}: +{batch_pos} confirmed "
                   f"(total {len(confirmed)}/{tgt}; annotated {annotated}, "
                   f"reused {reused}, errors {errors}).")
    pbar.close()

    # The confirmed set is CUMULATIVE: every paper the checkpoint labels ==1 across
    # all rounds, not just this run's batch. (In advance mode the loop only touched
    # a slice, so recompute from `done` over the full candidate list.)
    confirmed = [c for c in all_candidates if done.get(c["id"]) == 1]

    # Materialize the confirmed set.
    out_dir = workroot / f"{args.set}_confirmed"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    cert_by_id = {}
    if checkpoint.exists():
        ck = pd.read_csv(checkpoint, dtype={"id": str}, on_bad_lines="skip")
        cert_by_id = dict(zip(ck["id"].astype(str),
                              ck.get("label_research_software_certainty", pd.Series(dtype=object))))
        title_by_id = dict(zip(ck["id"].astype(str), ck.get("title", pd.Series(dtype=object))))
    else:
        title_by_id = {}
    for c in confirmed:
        rel = Path(c["rel_path"])
        dst = out_dir / rel
        if c["pdf"].is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not (dst.exists() and dst.stat().st_size == c["pdf"].stat().st_size):
                shutil.copy2(c["pdf"], dst)
        rows.append({
            "id": c["id"], "volume": c["volume"], "rel_path": c["rel_path"],
            "title": title_by_id.get(c["id"]), "certainty": cert_by_id.get(c["id"]),
            "dst": str(dst.relative_to(REPO_ROOT)) if dst.is_relative_to(REPO_ROOT) else str(dst),
        })

    manifest = out_dir / "manifest.csv"
    pd.DataFrame(rows, columns=["id", "volume", "rel_path", "title", "certainty", "dst"]).to_csv(
        manifest, index=False)

    tgt = "-" if target is None else target
    print(f"\nConfirmed {len(confirmed)}/{tgt} positive(s) -> {out_dir}")
    print(f"Manifest: {manifest}")
    if args.advance is not None:
        remaining = len([c for c in all_candidates if c["id"] not in done])
        print(f"Cursor advanced; {remaining} paper(s) still unannotated in "
              f"'{args.set}'+'{args.pool}'. Next: mine this batch with "
              f"`narrow_categories.py --mode collect --from_set {args.set} --to_schema`.")
    elif target is not None and len(confirmed) < target:
        print("\nWARNING: ran out of candidates before reaching the target. "
              "Re-run the 'estimate' step with a larger --cap (or lower --min_score) "
              "to enlarge the pool, then re-run this step (annotations are cached).")


if __name__ == "__main__":
    main()
