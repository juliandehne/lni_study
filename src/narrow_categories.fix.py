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

The SOURCE OF TRUTH for the typology is now ``prompts/category_schema.yaml``
(see schema_io.py / categories.py). Its per-dimension ``active`` list drives the
annotation prompt; ``rejected`` becomes the "do not use" guidance; and a
per-dimension ``candidates`` bucket is the merge-not-clobber inbox the loop
appends machine-discovered subcategories to. This module fills and drains that
bucket:

  1. collect — gather the model's ``new_suggestion`` subcategories and APPEND the
     new ones to each dimension's ``candidates`` bucket in the schema YAML
     (--to_schema), never touching the human's ``active`` / ``rejected`` choices.
     For the narrowing LOOP, mine a confirmed batch with --from_set:

         python src/narrow_categories.py --mode collect --from_set narrow --to_schema

     Legacy mode (stratified corpus sample + CSV, optionally --annotate_missing)
     is still available via --corpus.

  2. review — interactive CLI over the schema's pending ``candidates``: accept
     (promote to ``active``; uses the model rationale as the description if the
     curator gives none) / merge (fold into an EXISTING ``active`` key chosen by
     number, appended to that key's ``examples`` synonym whitelist) / decline
     (move to ``rejected`` with a reason) / skip / quit. Round-trips the YAML with ruamel so
     the curator's comments survive. Re-runnable: skipped/undecided candidates stay
     in the bucket. Editing the YAML by hand (or via Claude) is always equivalent.

         python src/narrow_categories.py --mode review

Loop: confirm (--advance the cursor by 50) -> collect (--to_schema) -> review /
hand-edit the YAML -> repeat until collect surfaces no new candidates (saturation),
then lock the schema and run the goldstandard.

Token map: collect = no token when mining checkpoints/--from_set; +token only with
--annotate_missing. review = no token.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as cat  # noqa: E402
import schema_io  # noqa: E402
import schema_cow  # noqa: E402  (copy-on-write + 3-way merge for concurrent schema writes)
from sampling import stratified_sample, format_allocation, volume_under, paper_id  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
# LNI_DATA_ROOT supersedes the in-repo default so generated data (results/,
# .workingset/) can live in an external working dir. See annotate_lni.DATA_ROOT.
DATA_ROOT = Path(os.environ.get("LNI_DATA_ROOT") or REPO_ROOT).resolve()
RESULTS_DIR = DATA_ROOT / "results"
CHECKPOINT_DIR = RESULTS_DIR / "checkpoints"
WORKROOT = DATA_ROOT / ".workingset"

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
    df = pd.DataFrame.from_dict(rows, orient="index")
    if df.empty:
        return df
    # Cache to a checkpoint so a later `collect` reuses these annotations
    # (load_all_annotations globs annotations_*_checkpoint.csv) and spends no new
    # token. Merge with any prior cache and dedupe by id.
    out = df.copy()
    if "id" not in out.columns:
        out.insert(0, "id", out.index)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    ck = CHECKPOINT_DIR / "annotations_narrowcollect_checkpoint.csv"
    if ck.exists():
        prev = pd.read_csv(ck, dtype={"id": str})
        out = pd.concat([prev, out], ignore_index=True).drop_duplicates(subset="id", keep="first")
    out.to_csv(ck, index=False)
    return df


def clean_cell(v) -> str | None:
    """Return a real string value, or None for a missing/blank annotation cell.

    pandas reads empty cells as float NaN, and ``str(NaN) == "nan"`` — a truthy,
    non-empty string. Without this guard an absent ``new_suggestion`` leaked in as
    a literal ``"nan"`` candidate (and ``"nan || nan || ..."`` explanations).
    """
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    return s


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
            chosen = clean_cell(r.get(cat_col)) or ""
            for tok in (t.strip() for t in chosen.split(";")):
                if tok in chosen_counts:
                    chosen_counts[tok] += 1
            key = clean_cell(r.get(sugg_col))
            if key is not None:
                e = suggested.setdefault(key, {"count": 0, "ids": [], "explanations": []})
                e["count"] += 1
                if len(e["ids"]) < MAX_EXAMPLES:
                    e["ids"].append(pid)
                expl = clean_cell(r.get(expl_col))
                if expl is not None and len(e["explanations"]) < MAX_EXAMPLES:
                    e["explanations"].append(expl)

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


def suggested_by_dimension(ids: list[str], ann: pd.DataFrame) -> dict[str, dict]:
    """{dim: {key: {'count', 'ids', 'explanations'}}} of model `new_suggestion`s
    over the given paper ids — the raw material the loop appends to the schema's
    `candidates` buckets."""
    present = [i for i in ids if i in ann.index]
    out: dict[str, dict] = {}
    for dim in cat.DIMENSIONS:
        sugg_col = f"{dim}_new_suggestion"
        expl_col = f"{dim}_explanation"
        d: dict[str, dict] = {}
        for pid in present:
            r = ann.loc[pid]
            key = clean_cell(r.get(sugg_col))
            if key is None:
                continue
            e = d.setdefault(key, {"count": 0, "ids": [], "explanations": []})
            e["count"] += 1
            if len(e["ids"]) < MAX_EXAMPLES:
                e["ids"].append(pid)
            expl = clean_cell(r.get(expl_col))
            if expl is not None and len(e["explanations"]) < MAX_EXAMPLES:
                e["explanations"].append(expl)
        out[dim] = d
    return out


def merge_candidates_into_schema(suggested: dict[str, dict], round_label=None) -> dict[str, list]:
    """Append NEW suggested subcategories to each dimension's `candidates` bucket
    in category_schema.yaml, without touching `active` / `rejected` (merge, not
    clobber). A key already present anywhere (active, rejected, or candidates) is
    not re-added; a repeat candidate just has its `count` bumped. Returns
    {dim: [newly_added_keys]} for the saturation readout.

    Writes go through schema_cow: edits land on a numbered work copy and are
    3-way-merged back into a fresh read of the canonical, so a concurrent writer
    (e.g. a `synccats` folding coder categories into `active`) is not clobbered.
    """
    work_path = schema_cow.work_copy()
    schema = schema_io.load_schema(work_path)
    dims = schema.get("dimensions") or {}
    added: dict[str, list] = {}

    for dim, cands in suggested.items():
        spec = dims.get(dim)
        if spec is None or not cands:
            continue
        active_keys = {str(e.get("key")) for e in (spec.get("active") or [])}
        # Alternate names already merged into an active category (its `examples`
        # whitelist) must not be re-offered as fresh candidates either.
        example_keys = {str(a) for e in (spec.get("active") or [])
                        for a in (e.get("examples") or [])}
        rejected_keys = {str(e.get("key")) for e in (spec.get("rejected") or [])}
        bucket = spec.get("candidates")
        if bucket is None:
            bucket = schema_io.new_seq()
            # Insert the new bucket right after `rejected` (or `active`) rather
            # than at the mapping's end: a trailing comment block on the last
            # dimension (e.g. the `pending_restructuring` banner) is attached to
            # the end of the mapping, so a plain append would land the bucket
            # *after* that comment. Positional insert keeps it next to rejected.
            keys = list(spec.keys())
            anchor = "rejected" if "rejected" in keys else ("active" if "active" in keys else None)
            pos = (keys.index(anchor) + 1) if anchor else len(keys)
            spec.insert(pos, "candidates", bucket)
        cand_idx = {str(e.get("key")): e for e in bucket}

        for key, info in sorted(cands.items(), key=lambda kv: -kv[1]["count"]):
            if key in active_keys or key in rejected_keys or key in example_keys:
                continue  # already curated — ignore
            if key in cand_idx:
                e = cand_idx[key]
                e["count"] = int(e.get("count", 0) or 0) + info["count"]
                continue
            item = schema_io.new_map(
                key=key,
                count=info["count"],
                example_ids="; ".join(info["ids"]),
                rationale=" || ".join(info["explanations"]),
            )
            if round_label is not None:
                item["seen_round"] = round_label
            bucket.append(item)
            cand_idx[key] = item
            added.setdefault(dim, []).append(key)

    schema_io.save_schema(schema, work_path)
    rep = schema_cow.merge_back(work_path, keep_work_copy=False)
    if rep.conflicts:
        print(rep.summary(), flush=True)
    return added


def load_set_ids(set_name: str) -> list[str]:
    """Paper ids from a working set's manifest — preferring the LLM-confirmed
    variant (`<set>_confirmed`) over the raw estimator set (`<set>`)."""
    for sub in (f"{set_name}_confirmed", set_name):
        manifest = WORKROOT / sub / "manifest.csv"
        if manifest.is_file():
            df = pd.read_csv(manifest, dtype={"id": str})
            return [str(i) for i in df["id"].tolist()]
    raise SystemExit(
        f"No manifest for set {set_name!r} (looked for "
        f"{WORKROOT / (set_name + '_confirmed') / 'manifest.csv'} and "
        f"{WORKROOT / set_name / 'manifest.csv'}). Run 'confirm' / 'estimate' first.")


def run_collect_from_set(args) -> None:
    """Loop mode: mine the model's suggestions over a confirmed working set and
    append the new ones to the schema's `candidates` buckets. No corpus resample,
    no token (annotations come from the checkpoints `confirm` already wrote)."""
    ids = load_set_ids(args.from_set)
    ann = load_all_annotations()
    if ann.empty:
        raise SystemExit("No Phase A checkpoints in results/checkpoints/. Run "
                         "'confirm' (or 'a-gold') on the set first.")
    present = [i for i in ids if i in ann.index]
    print(f"Mining suggestions over set '{args.from_set}': "
          f"{len(present)}/{len(ids)} paper(s) found in checkpoints.")

    suggested = suggested_by_dimension(ids, ann)
    total_sugg = sum(len(d) for d in suggested.values())
    if not args.to_schema:
        print(f"  {total_sugg} distinct suggestion(s) across dimensions. "
              "Pass --to_schema to append the new ones to category_schema.yaml.")
        for dim in cat.DIMENSIONS:
            if suggested[dim]:
                keys = ", ".join(f"{k}({v['count']})" for k, v in
                                 sorted(suggested[dim].items(), key=lambda kv: -kv[1]["count"]))
                print(f"    {dim}: {keys}")
        return

    added = merge_candidates_into_schema(suggested, round_label=args.round)
    n_added = sum(len(v) for v in added.values())
    print(f"\nSchema updated: {schema_io.SCHEMA_PATH}")
    if n_added == 0:
        print("  +0 NEW candidates — the typology may be SATURATING for this set. "
              "If two consecutive rounds add nothing new, lock the schema and run "
              "the goldstandard.")
    else:
        print(f"  +{n_added} NEW candidate(s) added to the `candidates` bucket(s):")
        for dim, keys in added.items():
            print(f"    {dim}: {', '.join(keys)}")
        print("Next: review them — python src/narrow_categories.py --mode review "
              "(or edit the YAML directly).")


def run_collect(args) -> None:
    if args.from_set:
        run_collect_from_set(args)
        return
    if not args.corpus:
        raise SystemExit("collect needs either --from_set <name> (loop mode) or "
                         "--corpus <dir> (legacy stratified-sample mode).")
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

    if args.to_schema:
        added = merge_candidates_into_schema(
            suggested_by_dimension(sample_ids, ann), round_label=args.round)
        n_added = sum(len(v) for v in added.values())
        print(f"  +{n_added} NEW candidate(s) appended to {schema_io.SCHEMA_PATH.name}.")
    print("Next: python src/narrow_categories.py --mode review "
          "(reviews the schema's pending candidates).")


# =============================================================================
# review: drain the schema's pending `candidates` -> active / rejected
# =============================================================================

def _bucket_index(seq, key: str) -> int:
    for i, e in enumerate(seq):
        if str(e.get("key")) == key:
            return i
    return -1


def run_review(args) -> None:
    """Interactive accept/merge/decline over the schema's pending `candidates`.

    Accept -> move the key into that dimension's `active` (prompting for a German
    description; if none is given, the model's own rationale is used as the
    description). Merge -> append the candidate as an alternate NAME to an EXISTING
    active subcategory's `examples` whitelist, picked by number from a listing (the
    prompt renders it as a "(auch: ...)" synonym hint, and the collect dedup skips
    it thereafter). Decline -> move
    it into `rejected` (prompting for a reason). Skip leaves it in `candidates` for
    a later pass; quit stops. The YAML is round-tripped after every decision so the
    curator's comments survive and the review is resumable. Editing the YAML by
    hand is always an equivalent path.

    Decisions are written to a schema_cow work copy and 3-way-merged back into a
    fresh read of the canonical at the end (and on [q]uit). The promote/decline
    moves (a candidate removed from `candidates`, added to `active`/`rejected`)
    are deletions, which the 3-way merge applies against its base snapshot — so a
    concurrent additive writer is preserved rather than clobbered.
    """
    work_path = schema_cow.work_copy()
    schema = schema_io.load_schema(work_path)
    dims = schema.get("dimensions") or {}

    # Snapshot the pending (dim, key) pairs up front; we mutate buckets in place
    # and re-locate by key each time, so the snapshot stays valid.
    pending = []
    for dim in cat.DIMENSIONS:
        spec = dims.get(dim) or {}
        for e in (spec.get("candidates") or []):
            k = str(e.get("key", "")).strip()
            if k and k.lower() not in ("nan", "none"):
                pending.append((dim, k))

    if not pending:
        schema_cow.discard(work_path)  # nothing edited; don't leave a stray copy
        print("No pending candidates in the schema. Nothing to review.")
        print(f"(Run `collect --to_schema` to discover candidates, or edit "
              f"{schema_io.SCHEMA_PATH.name} directly.)")
        return

    print(f"Reviewing {len(pending)} pending candidate(s) from "
          f"{schema_io.SCHEMA_PATH.name}.")
    print("Decisions round-trip the YAML after each step (resumable).\n")

    last_dim = None
    decided = 0
    for n, (dim, key) in enumerate(pending, start=1):
        spec = dims[dim]
        bucket = spec.get("candidates") or []
        idx = _bucket_index(bucket, key)
        if idx < 0:
            continue  # already moved out in a prior decision this run
        entry = bucket[idx]

        if dim != last_dim:
            print("\n" + "=" * 70)
            print(f"Dimension: {cat.TYPOLOGY[dim]['label']} ({dim})")
            last_dim = dim

        print(f"\n  [{n}/{len(pending)}] Candidate: {key!r}  "
              f"[count={entry.get('count', '?')}]")
        if entry.get("rationale"):
            print(f"    Model rationale(s): {entry.get('rationale')}")
        if entry.get("example_ids"):
            print(f"    Example papers: {entry.get('example_ids')}")

        # One decision loop per candidate: a sub-menu that backs out (or fails
        # validation) just re-prompts THIS candidate instead of skipping it.
        # `action` is set only when the candidate is finally resolved.
        action = None  # accept | merge | decline | skip | quit
        while action is None:
            choice = input("    [a]ccept->active / [m]erge->existing / "
                           "[d]ecline->rejected / [s]kip / [q]uit > ").strip().lower()

            if choice == "q":
                action = "quit"
            elif choice == "s":
                action = "skip"

            elif choice == "a":
                # Accept -> active. If the curator gives no description, fall back
                # to the model's own rationale (collected during `collect`) so the
                # prompt still has a definition; only stay pending if neither exists.
                desc = input("    German description "
                             "(Enter = use the model rationale): ").strip()
                if not desc:
                    desc = str(entry.get("rationale") or "").strip()
                    if desc:
                        print("    Using the model rationale as the description "
                              "(tighten it later in the YAML if you like).")
                    else:
                        print("    No description and no model rationale — "
                              "keeping it pending.")
                        continue  # re-prompt this candidate
                spec.setdefault("active", schema_io.new_seq())
                spec["active"].append(schema_io.new_map(
                    key=key, source="added", description=desc))
                action = "accept"

            elif choice == "m":
                # Merge -> record this candidate as an alternate NAME of an
                # existing active subcategory: appended to that entry's `examples`
                # list, which the prompt renders as a "(auch: ...)" synonym hint.
                # (No separate `rejected` entry — the alias is the whitelist; the
                # dedup in merge_candidates_into_schema also skips example names,
                # so it won't be re-offered as a fresh candidate.)
                # Quick association: pick the target by number from the active list.
                active = spec.get("active") or []
                if not active:
                    print("    No active subcategories to merge into yet — "
                          "use [a]ccept or [d]ecline.")
                    continue
                print("    Merge into which existing subcategory? "
                      "(number, or [b] to go back)")
                for i, e in enumerate(active, start=1):
                    ek = str(e.get("key"))
                    edesc = str(e.get("description") or "").strip().replace("\n", " ")
                    if len(edesc) > 60:
                        edesc = edesc[:57] + "..."
                    print(f"      {i:>2}) {ek}" + (f"  — {edesc}" if edesc else ""))
                sel = input("    number > ").strip().lower()
                if sel in ("b", ""):
                    continue  # back: re-prompt this candidate
                if not sel.isdigit() or not (1 <= int(sel) <= len(active)):
                    print(f"    Not a listed number (1-{len(active)}).")
                    continue
                target_entry = active[int(sel) - 1]
                target = str(target_entry.get("key"))
                ex = target_entry.get("examples")
                if ex is None:
                    ex = schema_io.new_seq()
                    target_entry["examples"] = ex
                if key not in [str(x) for x in ex]:
                    ex.append(key)
                print(f"    Merged {key!r} -> example of {target!r}.")
                action = "merge"

            elif choice == "d":
                reason = input("    Reason for rejecting (and target group, if any): ").strip()
                move_to = input("    move_to (existing key to use instead, or blank): ").strip()
                item = schema_io.new_map(key=key, reason=reason)
                if move_to:
                    item["move_to"] = move_to
                spec.setdefault("rejected", schema_io.new_seq())
                spec["rejected"].append(item)
                action = "decline"

            else:
                print("    Please type a, m, d, s, or q.")

        if action == "quit":
            print("\nStopped. Merging this run's decisions into the schema...")
            break
        if action == "skip":
            continue

        # accept / merge / decline all consume the candidate: drain + persist to
        # the work copy (resumable across a hard kill — the work copy keeps the
        # progress and can be merged later).
        del bucket[idx]
        schema_io.save_schema(schema, work_path)
        decided += 1

    # Merge the run's decisions back into a fresh read of the canonical (covers
    # both normal completion and the [q]uit break above).
    rep = schema_cow.merge_back(work_path, keep_work_copy=False)
    if rep.conflicts:
        print(rep.summary(), flush=True)

    remaining = 0
    for dim in cat.DIMENSIONS:
        remaining += len(((dims.get(dim) or {}).get("candidates")) or [])
    print(f"\nDecided {decided} this run; {remaining} candidate(s) still pending.")
    print("The schema now drives the annotation prompt (categories.py). Re-run "
          "`a-gold` to re-annotate under the updated typology, or run the loop again.")


# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Narrow the RSE subcategories from a stratified sample, with a "
                    "human accept/decline+explanation CLI producing a white/blacklist.")
    parser.add_argument("--mode", required=True, choices=["collect", "review"])
    # collect — loop mode
    parser.add_argument("--from_set", default=None,
                        help="[collect] Mine the model's suggestions over this working "
                             "set (prefers .workingset/<set>_confirmed). Loop mode; no token.")
    parser.add_argument("--to_schema", action="store_true",
                        help="[collect] Append NEW suggested subcategories to the "
                             "`candidates` buckets in prompts/category_schema.yaml.")
    parser.add_argument("--round", default=None,
                        help="[collect] Optional round label stamped on new candidates "
                             "(e.g. r2) for saturation tracking.")
    # collect — legacy stratified-sample mode
    parser.add_argument("--corpus", help="[collect] Legacy: folder with LNI volume "
                                          "subfolders (searched recursively).")
    parser.add_argument("--sample", type=int, default=50,
                        help="[collect] Stratified sample size (default 50).")
    parser.add_argument("--shuffle_seed", type=int, default=42,
                        help="[collect] Seed for the stratified draw.")
    parser.add_argument("--annotate_missing", action="store_true",
                        help="[collect] Annotate sampled papers absent from Phase A "
                             "checkpoints via SAIA (needs SAIA_API_KEY).")
    parser.add_argument("--max_text_chars", type=int, default=40000,
                        help="[collect] Truncate extracted text for --annotate_missing.")
    args = parser.parse_args()

    print(f"[config] data root  : {DATA_ROOT}"
          + ("  (in-repo default)" if DATA_ROOT == REPO_ROOT else "  (LNI_DATA_ROOT)"))
    print(f"[config] working set: {WORKROOT}")
    print(f"[config] schema     : {schema_io.SCHEMA_PATH}  [in repo, committed]")
    print(f"[config] mode       : {args.mode}\n")

    if args.mode == "collect":
        run_collect(args)
    else:
        run_review(args)


if __name__ == "__main__":
    main()
