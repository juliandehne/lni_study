"""
sync_coder_categories.py

Integrate human-coined categories into the typology schema (the knowledge base).

During interactive goldstandard coding (`build_goldstandard.py`) a coder may
introduce a NEW subcategory for a dimension — one the seed list and the other
coder did not already offer. Because the other coder is extremely unlikely to
independently invent the same category *and the same name*, such a category would
otherwise register as a pure disagreement in `compute_icr` (and the typology would
never actually accumulate the coders' findings). This step lifts every
coder-created category out of the coding files and merges it into the SINGLE
SOURCE OF TRUTH — `prompts/category_schema.yaml` — as ACTIVE groundtruth, so the
next coder (and the model) sees it as a first-class category.

Reads (under the shared goldstandard folder):
  - coding_<coder>.csv          : the authoritative usage. Every row with
                                  is_new == True is a category the coder applied
                                  that was not a known seed/other-coder key at
                                  decision time. Multi-value (techstack) strings
                                  are split on ';' so each token is considered.
  - new_categories_<coder>.csv  : OPTIONAL sidecar written by build_goldstandard
                                  when the coder typed a one-line description for a
                                  new category (columns: dimension,key,description,
                                  coder). Supplies the human DEFINITION so the
                                  merged category is immediately usable by the
                                  model (an active entry with no description is
                                  excluded from the prompt until one is written).

Writes:
  - appends each genuinely-new key to schema `dimensions.<dim>.active` as
    {key, source: "coder:<names>", description: <from sidecar or "">}, deduped
    against the dimension's active / rejected / candidate keys AND the alias
    (`examples`) names — exactly like narrow_categories.merge_candidates_into_schema.
    Round-trips the YAML so comments and layout survive.

Default merge target is `active` ("as groundtruth", the intent). Pass
`--bucket candidates` to route the coders' categories through the normal `review`
inbox instead of trusting them directly.

Usage (from the lni_study repo root):
    python src/sync_coder_categories.py --shared_folder goldstandard [--dry_run]
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as cat  # noqa: E402  (eager schema load + DIMENSIONS)
import schema_io  # noqa: E402
import schema_cow  # noqa: E402  (copy-on-write + 3-way merge for concurrent schema writes)
from build_goldstandard import _to_bool  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
# LNI_DATA_ROOT redirects generated data (results/, .workingset/, goldstandard/);
# the schema YAML always stays in the repo (see schema_io.SCHEMA_PATH).
DATA_ROOT = Path(os.environ.get("LNI_DATA_ROOT") or REPO_ROOT).resolve()
SIDECAR_PREFIX = "new_categories_"


def _tokens(value) -> list[str]:
    """Split a (possibly multi-value) final_category into clean tokens."""
    return [t.strip() for t in str(value).split(";") if t.strip()]


def load_sidecar_descriptions(shared_folder: Path) -> dict:
    """{(dim, key): description} merged across all coders' new_categories_*.csv.

    A non-empty description wins over an empty one; conflicting non-empty
    descriptions keep the first seen (the curator can reconcile in the YAML)."""
    out: dict = {}
    for f in sorted(shared_folder.glob(f"{SIDECAR_PREFIX}*.csv")):
        try:
            df = pd.read_csv(f)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            continue
        if not {"dimension", "key", "description"}.issubset(df.columns):
            continue
        for _, r in df.iterrows():
            dim = str(r["dimension"]).strip()
            key = str(r["key"]).strip()
            desc = "" if pd.isna(r["description"]) else str(r["description"]).strip()
            if not dim or not key:
                continue
            if desc and not out.get((dim, key)):
                out[(dim, key)] = desc
            else:
                out.setdefault((dim, key), desc)
    return out


def collect_coder_categories(shared_folder: Path) -> dict:
    """{dim: {key: {"coders": set, "count": int}}} from is_new rows in coding_*.csv.

    The coding file's RS_DIM rows carry is_new == False, so they never appear
    here; only dimensions in cat.DIMENSIONS are kept."""
    found: dict = {}
    for f in sorted(shared_folder.glob("coding_*.csv")):
        coder = f.stem.replace("coding_", "")
        try:
            df = pd.read_csv(f)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            continue
        if not {"dimension", "final_category", "is_new"}.issubset(df.columns):
            continue
        for _, r in df[df["is_new"].map(_to_bool)].iterrows():
            dim = str(r["dimension"]).strip()
            if dim not in cat.DIMENSIONS:
                continue
            for key in _tokens(r["final_category"]):
                if cat.is_reserved_category(key):
                    continue  # the INSUFFICIENT_INFO sentinel is not a real category
                d = found.setdefault(dim, {}).setdefault(
                    key, {"coders": set(), "count": 0})
                d["coders"].add(coder)
                d["count"] += 1
    return found


def _ensure_bucket(spec, bucket: str):
    """Return the named list in a dimension spec, creating it (positioned next to
    active/rejected) if absent — mirrors narrow_categories.merge_candidates_into_schema."""
    seq = spec.get(bucket)
    if seq is not None:
        return seq
    seq = schema_io.new_seq()
    keys = list(spec.keys())
    anchor = "rejected" if "rejected" in keys else ("active" if "active" in keys else None)
    pos = (keys.index(anchor) + 1) if anchor else len(keys)
    spec.insert(pos, bucket, seq)
    return seq


def merge_coder_categories_into_schema(shared_folder: Path, bucket: str = "active",
                                       dry_run: bool = False,
                                       schema_path: Path | None = None) -> dict:
    """Merge every coder-created (is_new) category into the schema `bucket`.

    Dedups against the dimension's active/rejected/candidate keys and alias
    (`examples`) names. Returns {dim: [newly_added_keys]}. Writes the YAML unless
    `dry_run`. `schema_path` overrides the default (used by tests)."""
    path = Path(schema_path) if schema_path else schema_io.SCHEMA_PATH
    found = collect_coder_categories(shared_folder)
    descs = load_sidecar_descriptions(shared_folder)
    # Edit a copy-on-write work copy; 3-way-merged back into a fresh read of the
    # canonical at the end so a concurrent additive writer (e.g. a round's
    # `collect`) is preserved rather than clobbered.
    work_path = schema_cow.work_copy(path)
    schema = schema_io.load_schema(work_path)
    dims = schema.get("dimensions") or {}
    added: dict = {}

    for dim, cats in found.items():
        spec = dims.get(dim)
        if spec is None or not cats:
            continue
        active = spec.get("active") or []
        known = {str(e.get("key")) for e in active}
        known |= {str(a) for e in active for a in (e.get("examples") or [])}
        known |= {str(e.get("key")) for e in (spec.get("rejected") or [])}
        known |= {str(e.get("key")) for e in (spec.get("candidates") or [])}

        target = _ensure_bucket(spec, bucket)
        in_target = {str(e.get("key")) for e in target}

        for key, info in sorted(cats.items(), key=lambda kv: -kv[1]["count"]):
            if key in known or key in in_target:
                continue
            coders = ",".join(sorted(info["coders"]))
            item = schema_io.new_map(
                key=key,
                source=f"coder:{coders}",
                description=descs.get((dim, key), ""),
            )
            target.append(item)
            in_target.add(key)
            added.setdefault(dim, []).append(key)

    if added and not dry_run:
        schema_io.save_schema(schema, work_path)
        rep = schema_cow.merge_back(work_path, path, keep_work_copy=False)
        if rep.conflicts:
            print(rep.summary(), flush=True)
    else:
        schema_cow.discard(work_path)  # dry-run or no-op: drop the work copy
    return added


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Merge coder-created categories into the typology schema (knowledge base).")
    ap.add_argument("--shared_folder", default=str(DATA_ROOT / "goldstandard"),
                    help="Folder with the coders' coding_*.csv + new_categories_*.csv "
                         "(defaults to <LNI_DATA_ROOT>/goldstandard).")
    ap.add_argument("--bucket", choices=["active", "candidates"], default="active",
                    help="Schema bucket to merge into (default 'active' = groundtruth; "
                         "'candidates' routes them through the review inbox).")
    ap.add_argument("--dry_run", action="store_true",
                    help="Report what WOULD be merged; do not write the schema.")
    args = ap.parse_args()

    shared = Path(args.shared_folder).resolve()
    print(f"[config] goldstandard: {shared}")
    print(f"[config] schema      : {schema_io.SCHEMA_PATH}")
    print(f"[config] bucket      : {args.bucket}"
          + ("   (DRY RUN - no write)" if args.dry_run else ""))
    if not shared.is_dir():
        raise SystemExit(f"shared folder not found: {shared}")

    added = merge_coder_categories_into_schema(
        shared, bucket=args.bucket, dry_run=args.dry_run)
    n = sum(len(v) for v in added.values())
    if n == 0:
        print("No new coder categories to merge - the schema already knows every "
              "category the coders used.")
        return

    descs = load_sidecar_descriptions(shared)
    verb = "Would add" if args.dry_run else "Added"
    print(f"{verb} {n} coder category(ies) to the schema `{args.bucket}` bucket:")
    for dim, keys in added.items():
        print(f"  {dim}:")
        for k in keys:
            tag = "" if descs.get((dim, k)) else \
                "   (NO description yet - excluded from the model prompt until filled in)"
            print(f"    + {k}{tag}")
    if not args.dry_run:
        print(f"\nWrote {schema_io.SCHEMA_PATH}.")
        print("Re-run any annotate/gold step to pick the new categories up.")


if __name__ == "__main__":
    main()
