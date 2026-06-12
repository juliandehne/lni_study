"""
narrow_categories.py

Subcategory-narrowing step (notes step 7b) — sits between Phase A (machine
annotation bootstrap) and Phase B (goldstandard creation).

The bootstrap lets the models propose ever more new subcategories. Before the
expensive goldstandard coding, a human narrows the typology down: a small,
**stratified 50-paper sample** (LNI volumes as strata) is used to surface the
candidate subcategories per dimension (the seed categories plus every new
subcategory the models suggested for those 50 papers), and a human accepts or
rejects each one — *with an explanation*.

The result is an **explicative white/blacklist** (`prompts/category_whitelist.json`)
that then feeds the goldstandard creation in two places:
  - it is injected into the annotation prompt as {category_guidance_block}
    (see categories.render_category_guidance_block), and
  - it is shown to the human coders inside build_goldstandard.py.

Two modes:

  1. collect — draw the stratified 50-paper sample and gather candidate
     subcategories. By default this REUSES the Phase A annotation checkpoints
     (no API calls / no token). Sampled papers not present in any checkpoint are
     reported; pass --annotate_missing (needs the SAIA token) to annotate them
     on the fly. Writes results/category_candidates_<corpus>.csv.

         python src/narrow_categories.py --mode collect ^
             --corpus "../rse-elearning-evaluation/data/data" --sample 50

  2. review — interactive CLI over the candidates: for each dimension and each
     candidate subcategory, accept (whitelist) / decline (blacklist) / skip, plus
     a free-text explanation. Writes prompts/category_whitelist.json (resumable).

         python src/narrow_categories.py --mode review

Token map: collect = PDFs only (or +token with --annotate_missing); review = no
PDFs, no token (reads the candidates CSV).
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as cat  # noqa: E402
from sampling import stratified_sample, format_allocation, volume_under, paper_id  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"
CHECKPOINT_DIR = RESULTS_DIR / "checkpoints"
WHITELIST_PATH = cat.WHITELIST_PATH  # prompts/category_whitelist.json

MAX_EXAMPLES = 5  # example ids / explanations kept per candidate


# =============================================================================
# collect: stratified sample -> candidate subcategories per dimension
# =============================================================================

def load_all_annotations() -> pd.DataFrame:
    """Concatenate every Phase A checkpoint CSV; dedupe by id (first wins)."""
    frames = []
    for f in sorted(CHECKPOINT_DIR.glob("annotations_*_checkpoint.csv")):
        try:
            frames.append(pd.read_csv(f, dtype={"id": str}))
        except (pd.errors.EmptyDataError, FileNotFoundError):
            continue
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates(subset="id", keep="first").set_index("id")


def annotate_missing(missing_pdfs: list[Path], corpus: Path, max_text_chars: int) -> pd.DataFrame:
    """Annotate sampled papers absent from the checkpoints (needs SAIA token).
    Reuses annotate_lni's extraction + classification machinery. `corpus` is the
    root used to compute the (relpath-based) paper id, so ids match the rest of
    the pipeline."""
    import annotate_lni as alni
    from openai import OpenAI

    saia_api_key = os.getenv("SAIA_API_KEY")
    if not saia_api_key:
        raise SystemExit(
            f"{len(missing_pdfs)} sampled paper(s) are not in any checkpoint and "
            "--annotate_missing was given, but no SAIA_API_KEY is set (.env).")
    base_url = os.getenv("SAIA_API_ENDPOINT") or alni.DEFAULT_SAIA_ENDPOINT

    system_prompt, user_prompt_template = alni.load_prompt_template(alni.DEFAULT_PROMPT)
    client = OpenAI(api_key=saia_api_key, base_url=base_url, timeout=300.0)
    rate_limiter = alni.RateLimiter()

    rows = {}
    for pdf in missing_pdfs:
        paper = alni.pdf_to_paper(pdf, corpus, max_text_chars)
        if paper["extraction_failed"]:
            continue
        flat = alni.classify_paper(client, paper, "mistral-large-3-675b-instruct-2512",
                                   system_prompt, user_prompt_template, 0, 42, 1.0, rate_limiter)
        rows[paper["id"]] = flat
    return pd.DataFrame.from_dict(rows, orient="index")


def collect_candidates(sample_ids: list[str], ann: pd.DataFrame) -> pd.DataFrame:
    """Aggregate candidate subcategories per dimension from the sampled papers.

    Candidates = the seed subcategories (source=seed) PLUS every distinct
    new_suggestion the models produced for the sampled papers (source=suggested).
    For each we record how often it occurred and a few example ids/explanations.
    """
    present = [i for i in sample_ids if i in ann.index]
    rows = []

    for dim in cat.DIMENSIONS:
        seeds = list(cat.TYPOLOGY[dim]["examples"].keys())
        cat_col = f"{dim}_category"
        sugg_col = f"{dim}_new_suggestion"
        expl_col = f"{dim}_explanation"

        # How often each seed was picked as the chosen category (context only).
        chosen_counts: dict[str, int] = {s: 0 for s in seeds}
        # Suggested-new candidates -> ids + explanations.
        suggested: dict[str, dict] = {}

        for pid in present:
            r = ann.loc[pid]
            chosen = str(r.get(cat_col) or "")
            for tok in (t.strip() for t in chosen.split(";")):
                if tok in chosen_counts:
                    chosen_counts[tok] += 1
            sugg = r.get(sugg_col)
            if sugg is not None and str(sugg).strip():
                key = str(sugg).strip()
                e = suggested.setdefault(key, {"count": 0, "ids": [], "explanations": []})
                e["count"] += 1
                if len(e["ids"]) < MAX_EXAMPLES:
                    e["ids"].append(pid)
                expl = r.get(expl_col)
                if expl is not None and str(expl).strip() and len(e["explanations"]) < MAX_EXAMPLES:
                    e["explanations"].append(str(expl).strip())

        for s in seeds:
            rows.append({
                "dimension": dim, "candidate_key": s, "source": "seed",
                "frequency": chosen_counts[s],
                "seed_description": cat.TYPOLOGY[dim]["examples"][s],
                "example_ids": "", "example_explanations": "",
            })
        for key, e in sorted(suggested.items(), key=lambda kv: -kv[1]["count"]):
            rows.append({
                "dimension": dim, "candidate_key": key, "source": "suggested",
                "frequency": e["count"], "seed_description": "",
                "example_ids": "; ".join(e["ids"]),
                "example_explanations": " || ".join(e["explanations"]),
            })

    return pd.DataFrame(rows)


def run_collect(args) -> None:
    corpus = Path(args.corpus).resolve()
    if not corpus.is_dir():
        raise SystemExit(f"--corpus is not a directory: {corpus}")
    pdfs = sorted(corpus.rglob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found under {corpus}")

    vol_of = volume_under(corpus)
    sizes = {v: sum(1 for p in pdfs if vol_of(p) == v)
             for v in {vol_of(p) for p in pdfs}}
    sample_pdfs, alloc = stratified_sample(pdfs, args.sample, seed=args.shuffle_seed, group_fn=vol_of)
    print(f"Found {len(pdfs)} PDF(s) across {len(sizes)} volume(s) under {corpus}.")
    print(f"Stratified sample of {len(sample_pdfs)} (seed={args.shuffle_seed}).")
    print(f"  Allocation per volume: {format_allocation(alloc, sizes)}")

    sample_ids = [paper_id(p, corpus) for p in sample_pdfs]
    ann = load_all_annotations()
    if ann.empty:
        print("\nNo Phase A checkpoints found in results/checkpoints/.")
    have = set(ann.index) if not ann.empty else set()
    missing = [p for p, pid in zip(sample_pdfs, sample_ids) if pid not in have]
    print(f"  In Phase A checkpoints: {len(sample_ids) - len(missing)}/{len(sample_ids)}; "
          f"missing: {len(missing)}.")

    if missing:
        if args.annotate_missing:
            print(f"  Annotating {len(missing)} missing paper(s) via SAIA (token required)...")
            extra = annotate_missing(missing, corpus, args.max_text_chars)
            ann = pd.concat([ann, extra]) if not ann.empty else extra
        else:
            print("  (Pass --annotate_missing to annotate these via SAIA; "
                  "otherwise they are skipped.)")

    cand = collect_candidates(sample_ids, ann)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"category_candidates_{corpus.name}.csv"
    cand.to_csv(out, index=False)
    n_sugg = int((cand["source"] == "suggested").sum())
    print(f"\nCandidates written: {out}")
    print(f"  {len(cand)} candidate row(s): "
          f"{len(cand) - n_sugg} seed + {n_sugg} model-suggested.")
    print("Next: python src/narrow_categories.py --mode review "
          f"--candidates {out.name}")


# =============================================================================
# review: human accept/decline + explanation -> white/blacklist JSON
# =============================================================================

def load_whitelist() -> dict:
    if WHITELIST_PATH.exists():
        try:
            return json.loads(WHITELIST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"version": 1, "dimensions": {}}


def save_whitelist(data: dict) -> None:
    WHITELIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WHITELIST_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def decided_keys(data: dict, dim: str) -> set[str]:
    entry = data.get("dimensions", {}).get(dim, {})
    keys = {e["key"] for e in entry.get("whitelist", [])}
    keys |= {e["key"] for e in entry.get("blacklist", [])}
    return keys


def run_review(args) -> None:
    candidates_path = Path(args.candidates) if args.candidates else None
    if candidates_path is None:
        matches = sorted(RESULTS_DIR.glob("category_candidates_*.csv"))
        if not matches:
            raise SystemExit("No candidates CSV found. Run --mode collect first.")
        if len(matches) > 1:
            raise SystemExit("Multiple candidates CSVs:\n  "
                             + "\n  ".join(m.name for m in matches)
                             + "\nPass --candidates to pick one.")
        candidates_path = matches[0]
    elif not candidates_path.is_absolute():
        candidates_path = RESULTS_DIR / candidates_path
    if not candidates_path.is_file():
        raise SystemExit(f"Candidates CSV not found: {candidates_path}")

    cand = pd.read_csv(candidates_path).fillna("")
    data = load_whitelist()
    data.setdefault("dimensions", {})
    data["source_candidates"] = candidates_path.name

    print(f"Reviewing candidates from {candidates_path.name}")
    print(f"Decisions are written to {WHITELIST_PATH} (resumable).\n")

    for dim in cat.DIMENSIONS:
        label = cat.TYPOLOGY[dim]["label"]
        dim_rows = cand[cand["dimension"] == dim]
        entry = data["dimensions"].setdefault(dim, {"whitelist": [], "blacklist": []})
        already = decided_keys(data, dim)

        print("=" * 70)
        print(f"Dimension: {label} ({dim})")
        for _, row in dim_rows.iterrows():
            key = str(row["candidate_key"])
            if key in already:
                continue
            print(f"\n  Candidate: {key!r}  [{row['source']}, freq={row['frequency']}]")
            if row["seed_description"]:
                print(f"    Seed description: {row['seed_description']}")
            if row["example_explanations"]:
                print(f"    Model rationale(s): {row['example_explanations']}")
            if row["example_ids"]:
                print(f"    Example papers: {row['example_ids']}")

            while True:
                choice = input("    [a]ccept / [d]ecline / [s]kip / [q]uit > ").strip().lower()
                if choice in ("a", "d", "s", "q"):
                    break
                print("    Please type a, d, s, or q.")

            if choice == "q":
                save_whitelist(data)
                print(f"\nStopped. Progress saved to {WHITELIST_PATH}")
                return
            if choice == "s":
                continue
            explanation = input("    Explanation (why keep / why drop, what to use instead): ").strip()
            target = "whitelist" if choice == "a" else "blacklist"
            entry[target].append({"key": key, "explanation": explanation})
            already.add(key)
            save_whitelist(data)  # save after each decision (resumable)

    save_whitelist(data)
    n_w = sum(len(d["whitelist"]) for d in data["dimensions"].values())
    n_b = sum(len(d["blacklist"]) for d in data["dimensions"].values())
    print(f"\nDone. {n_w} whitelisted, {n_b} blacklisted -> {WHITELIST_PATH}")
    print("This guidance now feeds the annotation prompt ({category_guidance_block}) "
          "and build_goldstandard.py.")


# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Narrow the RSE subcategories from a stratified sample, with a "
                    "human accept/decline+explanation CLI producing a white/blacklist.")
    parser.add_argument("--mode", required=True, choices=["collect", "review"])
    # collect
    parser.add_argument("--corpus", help="[collect] Folder with LNI volume subfolders "
                                          "(searched recursively).")
    parser.add_argument("--sample", type=int, default=50,
                        help="[collect] Stratified sample size (default 50).")
    parser.add_argument("--shuffle_seed", type=int, default=42,
                        help="[collect] Seed for the stratified draw.")
    parser.add_argument("--annotate_missing", action="store_true",
                        help="[collect] Annotate sampled papers absent from Phase A "
                             "checkpoints via SAIA (needs SAIA_API_KEY).")
    parser.add_argument("--max_text_chars", type=int, default=40000,
                        help="[collect] Truncate extracted text for --annotate_missing.")
    # review
    parser.add_argument("--candidates", default=None,
                        help="[review] Candidates CSV (auto-discovered in results/ if omitted).")
    args = parser.parse_args()

    if args.mode == "collect":
        if not args.corpus:
            raise SystemExit("--corpus is required for --mode collect.")
        run_collect(args)
    else:
        run_review(args)


if __name__ == "__main__":
    main()
