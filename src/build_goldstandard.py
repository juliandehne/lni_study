"""
build_goldstandard.py

Interactive goldstandard coding session (notes steps 8-11).

After the machine-annotation bootstrap (`annotate_lni.py`) has produced typology
labels and a list of suggested new subcategories, two human coders validate and
consolidate the categories into a goldstandard.

For each paper the model labelled `label_research_software == 1`, this script
runs a forward/backward interactive session (`run_session`). Per paper it:

  - opens the paper PDF in the default browser so the coder can check it
    themselves (notes step 9),
  - first asks the coder to RE-VALIDATE the research-software gate by hand
    (model value shown as a default). Rejecting it records `rs=0` and CASCADES —
    that paper's typology dimensions are skipped and not written,
  - if accepted, walks each typology dimension (`categories.DIMENSIONS`) and
    shows the model's chosen category, its certainty, and any NEW subcategory the
    model suggested (notes step 9), plus the new subcategories the OTHER coder has
    already proposed for that dimension so the two coders converge on shared names
    (notes step 10),
  - lets the coder ACCEPT the model's category (or KEEP a previously-saved one),
    pick an existing seed/other-coder category, or type a NEW one (with a confirm
    step so spelling is validated, notes step 9),
  - navigation: `p`=prev paper, `x`=next, `g`=goto #, `q`=save & quit; inside a
    dimension `b` steps back a paper and `s` skips the dimension — so earlier
    decisions can be revisited and changed.

Persistence: the coder's decisions file (`coding_<username>.csv`) is REWRITTEN in
full from the in-memory state after every decision (not append-only), so the
session is both resumable AND editable — re-deciding a paper or rejecting a
previously-coded one updates/cascades cleanly with no duplicate rows. The file
carries one `label_research_software` row per coded paper (the human RS boolean)
plus one row per accepted dimension, recording whether a reused new category was
accepted by this coder (notes step 11).

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


def _to_bool(v) -> bool:
    """Robustly coerce a CSV/`is_new` value to bool (avoids bool('False') == True)."""
    return str(v).strip().lower() in ("true", "1", "yes")


def prompt_decision(dim: str, model_category, model_certainty, model_suggestion,
                    other_suggestions: list[str], current=None) -> tuple[str, bool, str | None]:
    """Drive one dimension's CLI interaction.

    Returns (final_category, is_new, nav) where `nav` is None for a normal
    decision, or one of 'skip' / 'back' / 'quit' for navigation requests.
    If `current` (a previously saved {final_category, is_new} dict) is given,
    [Enter] keeps it instead of accepting the model's category."""
    seeds = existing_seed_keys(dim)
    label = cat.TYPOLOGY[dim]["label"]
    print(f"\n  --- {label} ({dim}) ---")
    print(f"    Model: {model_category!r}  (certainty={model_certainty})")
    if current is not None:
        print(f"    Current: {current['final_category']!r}"
              + ("  (new)" if _to_bool(current.get("is_new")) else ""))
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
        default_txt = "keep current" if current is not None else "accept model"
        print(f"    Choose: [Enter]={default_txt}, a number from the list, a seed/other "
              "key, 'new' to add a category, 's'=skip dimension, 'b'=back a paper, "
              "'q'=save & quit.")
        choice = input("    > ").strip()

        if choice == "":
            if current is not None:
                return current["final_category"], _to_bool(current.get("is_new")), None
            final = str(model_category) if model_category is not None else ""
            if not final:
                print("    Model category is empty — please type a category or 'new'.")
                continue
            is_new = is_new_category(final, seeds, other_suggestions)
            return final, is_new, None
        low = choice.lower()
        if low == "s":
            return "", False, "skip"
        if low == "b":
            return "", False, "back"
        if low == "q":
            return "", False, "quit"
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                picked = options[idx]
                return picked, is_new_category(picked, seeds, other_suggestions), None
            print(f"    No option [{choice}] — pick 1..{len(options)}.")
            continue
        if low == "new":
            new_cat = input("    New category key (snake_case): ").strip()
            if not new_cat:
                print("    Empty — cancelled.")
                continue
            confirm = input(f"    Confirm new category {new_cat!r}? [y/N] ").strip().lower()
            if confirm == "y":
                return new_cat, True, None
            continue
        # Treat as an explicit category key (seed or other-coder)
        is_new = is_new_category(choice, seeds, other_suggestions)
        if is_new:
            confirm = input(f"    {choice!r} is not a known key — add as new? [y/N] ").strip().lower()
            if confirm != "y":
                continue
        return choice, is_new, None


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


RS_DIM = "label_research_software"  # pseudo-dimension storing the human RS boolean


def load_decisions(out_path: Path) -> dict:
    """Load prior decisions into {id: {"rs": "1"/"0"/None, "dims": {dim: {...}}}}.

    Back-compat: files coded before the RS-boolean gate have dimension rows but
    no `label_research_software` row; any paper that already has dimension
    decisions is treated as rs == "1" (it was implicitly accepted as RS)."""
    state: dict = {}
    if not out_path.exists():
        return state
    try:
        prev = pd.read_csv(out_path, dtype={"id": str})
    except pd.errors.EmptyDataError:
        return state
    for _, r in prev.iterrows():
        pid = str(r["id"])
        st = state.setdefault(pid, {"rs": None, "dims": {}})
        dim = str(r["dimension"])
        if dim == RS_DIM:
            try:
                st["rs"] = "1" if int(float(r["final_category"])) == 1 else "0"
            except (TypeError, ValueError):
                st["rs"] = "1"
        else:
            st["dims"][dim] = {"final_category": r["final_category"],
                               "is_new": _to_bool(r.get("is_new"))}
    for st in state.values():
        if st["rs"] is None and st["dims"]:
            st["rs"] = "1"
    return state


def save_decisions(out_path: Path, df: pd.DataFrame, state: dict, username: str) -> None:
    """Rewrite the whole decisions CSV from in-memory state (supports edit/back-nav).

    Only papers with a decided RS boolean are persisted. A rejected paper
    (rs == "0") writes just the RS row — its dimension rows are dropped (cascade)."""
    cols = ["id", "coder", "dimension", "final_category", "is_new",
            "model_category", "model_certainty"]
    rows = []
    for _, row in df.iterrows():
        pid = str(row["id"])
        st = state.get(pid)
        if not st or st.get("rs") is None:
            continue
        rows.append({
            "id": pid, "coder": username, "dimension": RS_DIM,
            "final_category": st["rs"], "is_new": False,
            "model_category": row.get("label_research_software"),
            "model_certainty": row.get("label_research_software_certainty"),
        })
        if st["rs"] != "1":
            continue  # cascade: no dimension rows for a rejected paper
        for dim in cat.DIMENSIONS:
            d = st["dims"].get(dim)
            if not d:
                continue
            rows.append({
                "id": pid, "coder": username, "dimension": dim,
                "final_category": d["final_category"], "is_new": bool(d["is_new"]),
                "model_category": row.get(f"{dim}_category"),
                "model_certainty": row.get(f"{dim}_certainty"),
            })
    pd.DataFrame(rows, columns=cols).to_csv(out_path, index=False)


def open_paper_pdf(pdf_folder: Path, row) -> None:
    """Open the paper PDF in the browser so the coder can read it (step 9).
    Prefer the volume-relative path; fall back to id then bare filename."""
    rel = str(row.get("rel_path") or "").strip()
    if not rel:
        pid = str(row.get("id") or "").strip()
        rel = f"{pid}.pdf" if pid else str(row.get("filename", ""))
    pdf_path = pdf_folder / Path(rel)
    if pdf_path.exists():
        webbrowser.open(pdf_path.as_uri())
    else:
        print(f"  (PDF not found at {pdf_path})")


def run_session(df, state, out_path, username, pdf_folder, shared_folder) -> None:
    """Forward/backward interactive coding over the model-positive papers.

    Per paper the coder first answers the RS gate (default: contains research
    software). Rejecting it records rs=0 and skips all dimensions (cascade);
    accepting it walks the typology dimensions. Navigation: p=prev, x=next,
    g=goto, q=save & quit; 'b' inside a dimension steps back to the prev paper.

    The walk STARTS at the first paper the coder has not yet decided (rs is
    None), so a resumed session — including one where the `topup` step has just
    appended freshly LLM-confirmed papers to the end of the worklist — continues
    where the coder left off instead of re-walking already-coded papers. Earlier
    papers stay reachable with p/g."""
    n = len(df)
    i = next((k for k in range(n)
              if state.get(str(df.iloc[k]["id"]), {}).get("rs") is None), 0)
    if i:
        print(f"Resuming at paper {i + 1}/{n} (first undecided; "
              f"{i} already coded — use p/g to revisit).")
    while 0 <= i < n:
        row = df.iloc[i]
        pid = str(row["id"])
        st = state.setdefault(pid, {"rs": None, "dims": {}})
        status = {"1": "RS=yes", "0": "RS=no", None: "unseen"}[st["rs"]]
        print("=" * 70)
        print(f"Paper {i + 1}/{n}: {pid}   [{status}]")
        print(f"  Title: {row.get('title')}")
        open_paper_pdf(pdf_folder, row)

        # --- RS gate: human boolean assessment (default = contains RS) ---
        model_rs_txt = "YES" if row.get("label_research_software") == 1 else "NO"
        cur_txt = {"1": "YES", "0": "NO", None: "undecided"}[st["rs"]]
        print(f"\n  Contains research software?  model={model_rs_txt} "
              f"(certainty={row.get('label_research_software_certainty')})  "
              f"current={cur_txt}")
        print("  [Enter]=YES, code dimensions   n=NO, reject (skip all dimensions)")
        print("  p=previous   x=next (leave undecided)   g=goto #   q=save & quit")
        choice = input("  > ").strip().lower()

        if choice == "q":
            break
        if choice == "p":
            i -= 1
            continue
        if choice in ("x", "next"):
            i += 1
            continue
        if choice == "g":
            dest = input("  goto paper # : ").strip()
            if dest.isdigit() and 1 <= int(dest) <= n:
                i = int(dest) - 1
            else:
                print(f"  (out of range 1..{n})")
            continue
        if choice == "n":
            st["rs"] = "0"
            st["dims"] = {}  # cascade: a non-RS paper has no dimension annotations
            save_decisions(out_path, df, state, username)
            print("  -> rejected: not research software; dimensions skipped.")
            i += 1
            continue

        # Enter / 'y' / anything else => the paper contains research software.
        st["rs"] = "1"
        back = False
        for dim in cat.DIMENSIONS:
            final, is_new, nav = prompt_decision(
                dim,
                row.get(f"{dim}_category"),
                row.get(f"{dim}_certainty"),
                row.get(f"{dim}_new_suggestion"),
                other_coder_suggestions(shared_folder, username, dim),
                current=st["dims"].get(dim),
            )
            if nav == "quit":
                save_decisions(out_path, df, state, username)
                print(f"\nSaved. Decisions written to {out_path}")
                return
            if nav == "back":
                back = True
                break
            if nav == "skip":
                continue  # leave this dimension undecided
            st["dims"][dim] = {"final_category": final, "is_new": is_new}
            save_decisions(out_path, df, state, username)
        if back:
            i -= 1
            continue
        print(f"  Saved paper {i + 1}/{n}.")
        i += 1

    save_decisions(out_path, df, state, username)


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
    # Only papers the model judged to contain research software (notes step 6).
    # The human coder re-validates this boolean per paper and may reject it,
    # which cascades to skip that paper's dimension annotations.
    df = df[df.get("label_research_software") == 1].reset_index(drop=True)

    state = load_decisions(out_path)

    total_papers = len(df)
    print(f"[config] coder       : {args.username}")
    print(f"[config] data root   : {DATA_ROOT}"
          + ("  (in-repo default)" if DATA_ROOT == REPO_ROOT else "  (LNI_DATA_ROOT)"))
    print(f"[config] PDFs        : {pdf_folder}")
    print(f"[config] annotations : {annotations_path}")
    print(f"[config] decisions   : {out_path}  [shared by coders]")
    print(f"papers with research software (model): {total_papers}\n")

    run_session(df, state, out_path, args.username, pdf_folder, shared_folder)

    print(f"\nDone. Decisions written to {out_path}")


if __name__ == "__main__":
    main()
