"""
build_goldstandard.py

Interactive goldstandard coding session (notes steps 8-11).

After the machine-annotation bootstrap (`annotate_lni.py`) has produced typology
labels and a list of suggested new subcategories, two human coders validate and
consolidate the categories into a goldstandard.

For each paper where the model labelled `label_research_software == 1`, and for
each typology dimension, this script:

  - shows the model's chosen category, its certainty, and any NEW subcategory the
    model suggested (notes step 9),
  - also shows new subcategories the OTHER coder has already proposed for that
    dimension, so the two coders converge on shared names (notes step 10),
  - opens the paper PDF in the default browser so the coder can check it
    themselves (notes step 9),
  - lets the coder ACCEPT the model's category, pick an existing seed/other-coder
    category, or type a NEW one (with a confirm step so spelling is validated,
    notes step 9),
  - appends the decision to a SHARED CSV in a common repo folder, recording
    whether a reused new category was accepted by this coder (notes step 11),
  - prints progress (how many papers coded).

Usage (from the lni_study repo root):

    python src/build_goldstandard.py ^
        --username alice ^
        --pdf_folder "../rse-elearning-evaluation/data/data/lni132" ^
        --annotations results/checkpoints/annotations_lni132_..._checkpoint.csv ^
        --shared_folder goldstandard

The shared folder is committed to the repo so the second coder sees the first
coder's proposed categories. Each coder writes their own decisions file
(`goldstandard/coding_<username>.csv`); `compute_icr.py` then merges the two and
computes intercoder reliability (notes step 12).
"""

import argparse
import os
import sys
import webbrowser
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as cat  # noqa: E402


def existing_seed_keys(dim: str) -> list[str]:
    return list(cat.TYPOLOGY[dim]["examples"].keys())


def other_coder_suggestions(shared_folder: Path, username: str, dim: str) -> list[str]:
    """Collect new categories other coders already accepted for this dimension."""
    suggestions: set[str] = set()
    for f in shared_folder.glob("coding_*.csv"):
        if f.stem == f"coding_{username}":
            continue
        try:
            df = pd.read_csv(f)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            continue
        if {"dimension", "final_category", "is_new"}.issubset(df.columns):
            mask = (df["dimension"] == dim) & (df["is_new"] == True)  # noqa: E712
            suggestions.update(df.loc[mask, "final_category"].dropna().astype(str))
    return sorted(suggestions)


def is_new_category(final: str, seeds: list[str], other_suggestions: list[str]) -> bool:
    """Whether `final` introduces a category unknown so far. Multi-value techstack
    strings (e.g. 'javascript_web;other_unspecified') are split on ';' so they only
    count as new when at least one token is not an existing seed/other category."""
    known = set(seeds) | set(other_suggestions)
    tokens = [t.strip() for t in str(final).split(";") if t.strip()]
    return any(t not in known for t in tokens)


def prompt_decision(dim: str, model_category, model_certainty, model_suggestion,
                    other_suggestions: list[str]) -> tuple[str, bool]:
    """Drive one dimension's CLI interaction. Returns (final_category, is_new)."""
    seeds = existing_seed_keys(dim)
    label = cat.TYPOLOGY[dim]["label"]
    print(f"\n  --- {label} ({dim}) ---")
    print(f"    Model: {model_category!r}  (certainty={model_certainty})")
    if model_suggestion and str(model_suggestion).strip():
        print(f"    Model suggests NEW: {model_suggestion!r}")
    # Numbered pick-list: seeds first, then any other-coder categories not already
    # a seed. The coder can type the number instead of the full key (faster).
    options = seeds + [o for o in other_suggestions if o not in seeds]
    print("    Pick by number:")
    for i, key in enumerate(options, 1):
        tag = "" if key in seeds else "  (other coder)"
        print(f"      [{i}] {key}{tag}")

    # Curated white/blacklist guidance from the narrowing step (narrow_categories.py).
    guidance = cat.dimension_guidance(dim)
    if guidance["whitelist"]:
        print("    Whitelist (curated — prefer these):")
        for e in guidance["whitelist"]:
            expl = f" — {e['explanation']}" if e.get("explanation") else ""
            print(f"      + {e['key']}{expl}")
    if guidance["blacklist"]:
        print("    Blacklist (curated — avoid):")
        for e in guidance["blacklist"]:
            expl = f" — {e['explanation']}" if e.get("explanation") else ""
            print(f"      - {e['key']}{expl}")

    while True:
        print("    Choose: [Enter]=accept model, a number from the list, a seed/other "
              "key, 'new' to add a new category, or 's' to skip.")
        choice = input("    > ").strip()

        if choice == "":
            final = str(model_category) if model_category is not None else ""
            if not final:
                print("    Model category is empty — please type a category or 'new'.")
                continue
            is_new = is_new_category(final, seeds, other_suggestions)
            return final, is_new
        if choice.lower() == "s":
            return "", False
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                picked = options[idx]
                return picked, is_new_category(picked, seeds, other_suggestions)
            print(f"    No option [{choice}] — pick 1..{len(options)}.")
            continue
        if choice.lower() == "new":
            new_cat = input("    New category key (snake_case): ").strip()
            if not new_cat:
                print("    Empty — cancelled.")
                continue
            confirm = input(f"    Confirm new category {new_cat!r}? [y/N] ").strip().lower()
            if confirm == "y":
                return new_cat, True
            continue
        # Treat as an explicit category key (seed or other-coder)
        is_new = is_new_category(choice, seeds, other_suggestions)
        if is_new:
            confirm = input(f"    {choice!r} is not a known key — add as new? [y/N] ").strip().lower()
            if confirm != "y":
                continue
        return choice, is_new


REPO_ROOT = Path(__file__).resolve().parent.parent
# LNI_DATA_ROOT supersedes the in-repo default so generated data (results/,
# .workingset/, goldstandard/) can live in an external working dir. See
# annotate_lni.DATA_ROOT.
DATA_ROOT = Path(os.environ.get("LNI_DATA_ROOT") or REPO_ROOT).resolve()


def discover_annotations(pdf_folder: Path, override: str | None) -> Path:
    """Locate the Phase A annotation CSV. Phase B needs no token — it just reads
    the machine annotations produced earlier. If --annotations is not given, find
    `results/checkpoints/annotations_<folder>_*_checkpoint.csv` by folder name."""
    if override:
        p = Path(override)
        if not p.is_file():
            raise SystemExit(f"--annotations not found: {p}")
        return p

    # Search local checkpoints first, then committed locations (so a second coder
    # on another machine can read an annotations CSV shared via the repo).
    search_dirs = [
        DATA_ROOT / "results" / "checkpoints",
        DATA_ROOT / "results",
        DATA_ROOT / "goldstandard",
    ]
    matches = []
    seen = set()
    for d in search_dirs:
        for m in sorted(d.glob(f"annotations_{pdf_folder.name}_*_checkpoint.csv")):
            if m.name not in seen:
                seen.add(m.name)
                matches.append(m)
    if not matches:
        raise SystemExit(
            f"No annotation CSV (annotations_{pdf_folder.name}_*_checkpoint.csv) found in\n  "
            + "\n  ".join(str(d) for d in search_dirs)
            + "\nRun Phase A first (annotate_lni.py) or pass --annotations explicitly.")
    if len(matches) > 1:
        listing = "\n  ".join(str(m.name) for m in matches)
        raise SystemExit(
            f"Multiple annotation CSVs for '{pdf_folder.name}':\n  {listing}\n"
            f"Pass --annotations to pick one (e.g. a specific model/run).")
    print(f"Using annotations: {matches[0].name}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive goldstandard coding for the LNI RSE typology.")
    parser.add_argument("--username", required=True, help="Coder username (e.g. alice).")
    parser.add_argument("--pdf_folder", required=True, help="Folder with the LNI PDFs (to open in browser).")
    parser.add_argument("--annotations", default=None,
                        help="Phase A annotation CSV. Optional: auto-discovered from "
                             "the folder name in results/checkpoints/ if omitted.")
    parser.add_argument("--shared_folder", default=str(DATA_ROOT / "goldstandard"),
                        help="Common folder for coders' decision files "
                             "(defaults to <LNI_DATA_ROOT>/goldstandard).")
    args = parser.parse_args()

    pdf_folder = Path(args.pdf_folder).resolve()
    annotations_path = discover_annotations(pdf_folder, args.annotations)
    shared_folder = Path(args.shared_folder).resolve()
    shared_folder.mkdir(parents=True, exist_ok=True)
    out_path = shared_folder / f"coding_{args.username}.csv"

    df = pd.read_csv(annotations_path, dtype={"id": str})
    # Only papers the model judged to contain research software (notes step 6)
    df = df[df.get("label_research_software") == 1].reset_index(drop=True)

    already_done: set[tuple[str, str]] = set()
    if out_path.exists():
        prev = pd.read_csv(out_path, dtype={"id": str})
        already_done = set(zip(prev["id"], prev["dimension"]))

    total_papers = len(df)
    print(f"[config] coder       : {args.username}")
    print(f"[config] data root   : {DATA_ROOT}"
          + ("  (in-repo default)" if DATA_ROOT == REPO_ROOT else "  (LNI_DATA_ROOT)"))
    print(f"[config] PDFs        : {pdf_folder}")
    print(f"[config] annotations : {annotations_path}")
    print(f"[config] decisions   : {out_path}  [shared by coders]")
    print(f"papers with research software: {total_papers}\n")

    coded_papers = 0
    for _, row in df.iterrows():
        paper_id = row["id"]
        pending = [d for d in cat.DIMENSIONS if (paper_id, d) not in already_done]
        if not pending:
            continue

        coded_papers += 1
        print("=" * 70)
        print(f"Paper {coded_papers}/{total_papers}: {paper_id}")
        print(f"  Title: {row.get('title')}")

        # Open the PDF in the default browser so the coder can read it (step 9).
        # Prefer the volume-relative path (handles PDFs nested in subfolders);
        # fall back to the id (= rel_path without suffix) then the bare filename.
        rel = str(row.get("rel_path") or "").strip()
        if not rel:
            pid = str(row.get("id") or "").strip()
            rel = f"{pid}.pdf" if pid else str(row.get("filename", ""))
        pdf_path = pdf_folder / Path(rel)
        if pdf_path.exists():
            webbrowser.open(pdf_path.as_uri())
        else:
            print(f"  (PDF not found at {pdf_path})")

        for dim in pending:
            final, is_new = prompt_decision(
                dim,
                row.get(f"{dim}_category"),
                row.get(f"{dim}_certainty"),
                row.get(f"{dim}_new_suggestion"),
                other_coder_suggestions(shared_folder, args.username, dim),
            )
            if final == "":
                continue  # skipped
            record = {
                "id": paper_id,
                "coder": args.username,
                "dimension": dim,
                "final_category": final,
                "is_new": is_new,
                "model_category": row.get(f"{dim}_category"),
                "model_certainty": row.get(f"{dim}_certainty"),
            }
            pd.DataFrame([record]).to_csv(
                out_path, mode="a", header=not out_path.exists(), index=False)
            already_done.add((paper_id, dim))

        print(f"  Saved. Progress: {coded_papers}/{total_papers} papers visited this corpus.")

    print(f"\nDone. Decisions written to {out_path}")


if __name__ == "__main__":
    main()
