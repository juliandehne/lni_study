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
    pick an existing seed/other-coder category, type a NEW one (with a confirm
    step so spelling is validated, notes step 9), or mark the dimension
    `i`=insufficient information when the paper does not say enough to code it,
  - navigation: `p`=prev paper, `x`=next, `g`=goto #, `q`=save & quit; inside a
    dimension `b` steps back a paper and `s` skips the dimension — so earlier
    decisions can be revisited and changed.

The `i`=insufficient-information answer (stored as the reserved
`categories.INSUFFICIENT_INFO` sentinel) is a REAL coded decision: a row is
written and it counts in intercoder reliability as a nominal label (two coders
both marking it agree). It is distinct from `s`=skip, which leaves the dimension
undecided (no row, excluded from ICR), and it is never treated as a new category
to sync into the schema.

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
import csv
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


def subcategory_descriptions(shared_folder: Path, dim: str) -> dict[str, str]:
    """Map subcategory key -> human definition for `dim`, for the on-demand 'd'
    view in prompt_decision. Combines the ACTIVE typology definitions from the
    schema (cat.dimension_guidance whitelist) with the descriptions other coders
    typed for the categories they coined (the new_categories_*.csv sidecars), so a
    coder can look up what every numbered option — seed or other-coder — means."""
    desc: dict[str, str] = {}
    for e in cat.dimension_guidance(dim)["whitelist"]:
        if e.get("explanation"):
            desc[e["key"]] = e["explanation"]
    for f in shared_folder.glob("new_categories_*.csv"):
        try:
            with open(f, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    if (row.get("dimension") == dim and row.get("key")
                            and row.get("description")):
                        desc.setdefault(row["key"], row["description"])
        except OSError:
            continue
    return desc


def is_new_category(final: str, seeds: list[str], other_suggestions: list[str]) -> bool:
    """Whether `final` introduces a category unknown so far. Multi-value techstack
    strings (e.g. 'javascript_web;other_unspecified') are split on ';' so they only
    count as new when at least one token is not an existing seed/other category. The
    reserved INSUFFICIENT_INFO sentinel is always known (never a new category)."""
    known = set(seeds) | set(other_suggestions) | {cat.INSUFFICIENT_INFO}
    tokens = [t.strip() for t in str(final).split(";") if t.strip()]
    return any(t not in known for t in tokens)


def _to_bool(v) -> bool:
    """Robustly coerce a CSV/`is_new` value to bool (avoids bool('False') == True)."""
    return str(v).strip().lower() in ("true", "1", "yes")


NEW_CAT_SIDECAR_COLS = ["dimension", "key", "description", "coder"]

# When the model is at least this certain about an EXISTING category, its
# speculative NEW-subcategory suggestion is noise and is not shown to the coder.
HIGH_CERTAINTY = 0.90


def _as_float(value):
    """Best-effort float coercion; returns None for blank/'nan'/non-numeric."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # drop NaN


def _has_suggestion(value) -> bool:
    """True only for a real, non-empty NEW-subcategory suggestion (filters
    out None, pandas NaN, and the literal strings 'nan'/'none'/'')."""
    if value is None:
        return False
    if isinstance(value, float) and value != value:  # NaN
        return False
    return str(value).strip().lower() not in ("", "nan", "none")


def record_new_category(shared_folder: Path, username: str, dim: str, final: str) -> None:
    """Persist a coder-created category (+ optional one-line description) to the
    per-coder sidecar `new_categories_<username>.csv`.

    `sync_coder_categories.py` later lifts these into the schema knowledge base as
    groundtruth, with the German definition typed here — so the OTHER coder (who is
    unlikely to independently coin the same name) sees the category as a first-class
    option instead of disagreeing by default. Multi-value (techstack) strings are
    split so each genuinely-new token is recorded. A (dim,key) already in the
    sidecar is NOT re-prompted; we only ask for a description the first time a key
    appears, so re-visiting/editing a paper never nags the coder again."""
    path = shared_folder / f"new_categories_{username}.csv"
    existing: dict[tuple[str, str], dict] = {}
    if path.exists():
        try:
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    existing[(row.get("dimension", ""), row.get("key", ""))] = row
        except OSError:
            pass

    known = set(existing_seed_keys(dim)) | set(other_coder_suggestions(shared_folder, username, dim))
    new_tokens = [t.strip() for t in str(final).split(";") if t.strip()]
    changed = False
    for key in new_tokens:
        if key in known or (dim, key) in existing:
            continue  # an established key, or already recorded — do not re-prompt
        desc = input(f"    One-line description for new category {key!r} "
                     "(for the shared knowledge base; Enter to skip): ").strip()
        existing[(dim, key)] = {"dimension": dim, "key": key,
                                "description": desc, "coder": username}
        changed = True

    if changed:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=NEW_CAT_SIDECAR_COLS)
            w.writeheader()
            for row in existing.values():
                w.writerow({c: row.get(c, "") for c in NEW_CAT_SIDECAR_COLS})


def prompt_decision(dim: str, model_category, model_certainty, model_suggestion,
                    other_suggestions: list[str], current=None,
                    model_explanation=None,
                    descriptions: dict[str, str] | None = None) -> tuple[str, bool, str | None]:
    """Drive one dimension's CLI interaction.

    Returns (final_category, is_new, nav) where `nav` is None for a normal
    decision, or one of 'skip' / 'back' / 'revert' / 'quit' for navigation
    requests. 'revert' asks the caller to step back ONE dimension and re-decide
    the previous entry (distinct from 'back', which steps back a whole paper).
    Choosing 'i' returns the reserved cat.INSUFFICIENT_INFO sentinel (is_new
    False, nav None) — a real "not enough info to code this" answer, unlike 's'
    which returns nav 'skip' and writes no row.
    If `current` (a previously saved {final_category, is_new} dict) is given,
    [Enter] keeps it instead of accepting the model's category.

    'new' does NOT commit the typed key directly: it adds the category to the
    numbered list and RE-PROMPTS, so the coder selects it (alongside any others)
    by number. For a multi-value dimension (cat.TYPOLOGY[dim]['multi']) the
    numbered pick accepts a comma-separated list (e.g. '1,3,4'); the picks are
    joined with ';' — the same format the model emits and is_new_category /
    record_new_category split on."""
    seeds = existing_seed_keys(dim)
    multi = bool(cat.TYPOLOGY[dim].get("multi"))
    label = cat.TYPOLOGY[dim]["label"]
    question = cat.TYPOLOGY[dim].get("question") or ""
    aliases = cat.TYPOLOGY[dim].get("aliases", {})
    descriptions = descriptions or {}
    print(f"\n  --- {label} ({dim}) ---")
    # The dimension's coding question (what this dimension actually asks). Printed
    # up front so the coder sees the definition of the dimension, not just its key.
    if question:
        print(f"    Q: {question}")
    print(f"    Model: {model_category!r}  (certainty={model_certainty})")
    if _has_suggestion(model_explanation):
        print(f"    Model explanation: {str(model_explanation).strip()}")
    if current is not None:
        print(f"    Current: {current['final_category']!r}"
              + ("  (new)" if _to_bool(current.get("is_new")) else ""))
    # Only surface the model's speculative NEW subcategory when it's a real
    # suggestion AND the model isn't already confident about an existing category.
    cert = _as_float(model_certainty)
    if _has_suggestion(model_suggestion) and not (cert is not None and cert >= HIGH_CERTAINTY):
        print(f"    Model suggests NEW: {model_suggestion!r}")
    # Numbered pick-list: seeds first, then any other-coder categories not already
    # a seed, then categories the coder adds via 'new' this session. The coder can
    # type the number(s) instead of the full key (faster).
    added: list[str] = []  # categories created with 'new' during this prompt

    def current_options() -> list[str]:
        opts = seeds + [o for o in other_suggestions if o not in seeds]
        return opts + [k for k in added if k not in opts]

    def print_options(opts: list[str]) -> None:
        print("    Pick by number"
              + (" (comma-separated for multiple, e.g. 1,3):" if multi else ":"))
        for i, key in enumerate(opts, 1):
            if key in added:
                tag = "  (new)"
            elif key in seeds:
                tag = ""
            else:
                tag = "  (other coder)"
            print(f"      [{i}] {key}{tag}")

    def print_descriptions(opts: list[str]) -> None:
        """On-demand ('d') view: every numbered option with its definition, so the
        coder can look up what each subcategory means without leaving the prompt."""
        print("    Subcategory descriptions:")
        for i, key in enumerate(opts, 1):
            d = descriptions.get(key)
            al = aliases.get(key)
            alias_txt = ("  (auch: " + ", ".join(al) + ")") if al else ""
            body = d if d else "(no description on file)"
            print(f"      [{i}] {key}: {body}{alias_txt}")

    options = current_options()
    print_options(options)

    # Curated white/blacklist guidance from the narrowing step (narrow_categories.py).
    # Not shown by default to keep the prompt compact — the coder reveals it on
    # demand with 'l' (see the menu / print_guidance below).
    guidance = cat.dimension_guidance(dim)

    def print_guidance() -> None:
        if not guidance["whitelist"] and not guidance["blacklist"]:
            print("    (no curated white/blacklist guidance for this dimension)")
            return
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
        pick_txt = "number(s)" if multi else "a number"
        print(f"    Choose: [Enter]={default_txt}, {pick_txt} from the list, a seed/other "
              "key, 'new' to add a category, 'd'=show subcategory descriptions, "
              "'l'=show white/blacklist guidance, "
              "'i'=insufficient info (paper doesn't say enough to code this dimension), "
              "'s'=skip dimension, 'r'=revert/redo previous dimension, "
              "'b'=back a paper, 'q'=save & quit.")
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
        if low == "d":
            print_descriptions(options)
            continue
        if low == "l":
            print_guidance()
            continue
        if low == "r":
            return "", False, "revert"
        if low == "s":
            return "", False, "skip"
        if low == "i":
            # The coder asserts the paper lacks the information to code this
            # dimension. This is a real coded answer (a row is written, counted in
            # ICR), distinct from 's'=skip which leaves the dimension undecided.
            return cat.INSUFFICIENT_INFO, False, None
        if low == "b":
            return "", False, "back"
        if low == "q":
            return "", False, "quit"
        if low == "new":
            # Add a category, then RE-PROMPT (do not commit it directly) so the
            # coder selects it — together with any others — by number below.
            new_cat = input("    New category key (snake_case): ").strip()
            if not new_cat:
                print("    Empty — cancelled.")
                continue
            confirm = input(f"    Confirm new category {new_cat!r}? [y/N] ").strip().lower()
            if confirm != "y":
                continue
            if new_cat not in current_options():
                added.append(new_cat)
            options = current_options()
            print(f"    Added {new_cat!r}.")
            print_options(options)
            continue

        # A pick by number, or a comma-separated list of numbers (multi only).
        parts = [p.strip() for p in choice.split(",") if p.strip()]
        if parts and all(p.isdigit() for p in parts):
            if len(parts) > 1 and not multi:
                print("    This dimension takes a single category — pick one number.")
                continue
            idxs = [int(p) - 1 for p in parts]
            if any(not (0 <= i < len(options)) for i in idxs):
                print(f"    Out of range — pick 1..{len(options)}.")
                continue
            picked: list[str] = []
            for i in idxs:
                if options[i] not in picked:
                    picked.append(options[i])
            final = ";".join(picked)
            return final, is_new_category(final, seeds, other_suggestions), None

        # Treat as explicit category key(s): seed / other-coder / freshly added.
        keys = [p.strip() for p in choice.split(",") if p.strip()]
        if len(keys) > 1 and not multi:
            print("    This dimension takes a single category — give one key.")
            continue
        confirmed: list[str] | None = []
        for k in keys:
            if is_new_category(k, seeds, other_suggestions + added):
                ans = input(f"    {k!r} is not a known key — add as new? [y/N] ").strip().lower()
                if ans != "y":
                    confirmed = None
                    break
            confirmed.append(k)
        if confirmed is None:
            continue
        final = ";".join(confirmed)
        return final, is_new_category(final, seeds, other_suggestions), None


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


def dims_missing(st: dict | None) -> list[str]:
    """For an RS-accepted paper, the typology dimensions not yet decided (in
    `cat.DIMENSIONS` order). A dimension marked 's'=skip leaves no row and so
    counts as missing here — by design, so a deliberately-skipped paper is
    re-offered for finishing on the next session. Returns [] for unseen or
    rejected papers (they have no dimensions to complete)."""
    if not st or st.get("rs") != "1":
        return []
    coded = st.get("dims", {})
    return [d for d in cat.DIMENSIONS if d not in coded]


def is_incomplete(st: dict | None) -> bool:
    """A paper still needing coder attention: never decided (rs is None) or
    accepted as RS but missing one or more typology dimensions. A rejected
    paper (rs == '0') cascades to no dimensions and is therefore complete."""
    if not st or st.get("rs") is None:
        return True
    return bool(dims_missing(st))


def next_incomplete(df, state, start: int) -> int:
    """Index of the first incomplete paper at or after `start`, or len(df) if
    none remain (ending the session). Used to advance PAST already-complete
    papers when finishing a partially-coded worklist — so completing one partial
    jumps straight to the next paper that needs work instead of re-walking coded
    ones. In a first-pass session every later paper is unseen, so this is just
    `start`. Explicit navigation (x/p/g) is unaffected and still moves literally."""
    n = len(df)
    for k in range(max(start, 0), n):
        if is_incomplete(state.get(str(df.iloc[k]["id"]))):
            return k
    return n


def run_session(df, state, out_path, username, pdf_folder, shared_folder) -> None:
    """Forward/backward interactive coding over the model-positive papers.

    Per paper the coder first answers the RS gate (default: contains research
    software). Rejecting it records rs=0 and skips all dimensions (cascade);
    accepting it walks the typology dimensions. Navigation: p=prev, x=next,
    g=goto, q=save & quit; inside a dimension 'b' steps back to the prev paper
    and 'r' reverts/redoes the previous dimension within the same paper.

    The walk STARTS at the first INCOMPLETE paper — one not yet decided (rs is
    None) OR accepted as RS but still missing typology dimensions (e.g. a paper
    whose coding was interrupted by a mid-paper save & quit). This means a
    resumed session finishes half-coded papers instead of skipping past them to
    the first wholly-unseen paper. All half-coded papers (not just the one the
    cursor lands on) are also listed up front so they can be reached with g.

    After a paper is FINISHED (all dimensions coded) or REJECTED, the cursor
    auto-advances to the next INCOMPLETE paper (via next_incomplete), skipping
    any already-complete papers in between — so a finishing pass doesn't re-walk
    coded papers. Explicit navigation (x=next, p=prev, g=goto) still moves
    literally by one, so earlier/complete papers stay reachable for review."""
    n = len(df)
    i = next_incomplete(df, state, 0)
    if i >= n:
        i = 0  # nothing outstanding — open at the start for review/editing

    # Suggest every half-coded paper (accepted as RS but missing dimensions) for
    # finishing — not only the one the cursor lands on, since p/g can reach any.
    partials = []
    for k in range(n):
        st = state.get(str(df.iloc[k]["id"]))
        miss = dims_missing(st)
        if miss:
            partials.append((k, str(df.iloc[k]["id"]), miss))
    if partials:
        print(f"{len(partials)} paper(s) accepted as RS but not fully coded "
              "(suggested to finish — use 'g' to jump to #):")
        for k, pid, miss in partials:
            print(f"   #{k + 1:<5} {pid:<22} missing: {', '.join(miss)}")
    if i:
        print(f"Resuming at paper {i + 1}/{n} (first incomplete; "
              f"{i} complete before it — use p/g to revisit).")
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
        rs_expl = row.get("label_research_software_explanation")
        if _has_suggestion(rs_expl):
            print(f"  Model explanation: {str(rs_expl).strip()}")
        print("  [Enter]=YES, code dimensions   n=NO, reject (skip all dimensions)")
        print("  r=revoke RS decision (back to undecided)")
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
        if choice == "r":
            if st["rs"] is None:
                print("  (nothing to revoke — RS gate is already undecided)")
                continue
            prev = "YES" if st["rs"] == "1" else "NO"
            st["rs"] = None
            # Dimension work is kept in memory so re-affirming YES this session
            # restores it, but an undecided paper is NOT persisted (save_decisions
            # drops rs=None), so the previously-saved row(s) are removed from the
            # CSV and the paper resurfaces as incomplete.
            save_decisions(out_path, df, state, username)
            print(f"  -> revoked RS decision (was {prev}); now undecided "
                  f"(paper will resurface for re-coding).")
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
            i = next_incomplete(df, state, i + 1)  # jump past complete papers
            continue

        # Enter / 'y' / anything else => the paper contains research software.
        st["rs"] = "1"
        back = False
        dims = cat.DIMENSIONS
        j = 0  # index-based so 'revert' can step back a dimension within the paper
        while j < len(dims):
            dim = dims[j]
            final, is_new, nav = prompt_decision(
                dim,
                row.get(f"{dim}_category"),
                row.get(f"{dim}_certainty"),
                row.get(f"{dim}_new_suggestion"),
                other_coder_suggestions(shared_folder, username, dim),
                current=st["dims"].get(dim),
                model_explanation=row.get(f"{dim}_explanation"),
                descriptions=subcategory_descriptions(shared_folder, dim),
            )
            if nav == "quit":
                save_decisions(out_path, df, state, username)
                print(f"\nSaved. Decisions written to {out_path}")
                return
            if nav == "back":
                back = True
                break
            if nav == "revert":
                # Undo the PREVIOUS dimension's decision and re-prompt it (the
                # current dimension hasn't been saved yet, so there's nothing to
                # undo there). Clears the human label so the re-prompt starts from
                # the model default again.
                if j == 0:
                    print("    (nothing to revert — already at the first dimension)")
                    continue
                j -= 1
                reverted = st["dims"].pop(dims[j], None)
                save_decisions(out_path, df, state, username)
                shown = reverted["final_category"] if reverted else "(was skipped)"
                print(f"    Reverted {dims[j]!r} (was {shown!r}) — re-deciding it.")
                continue
            if nav == "skip":
                j += 1
                continue  # leave this dimension undecided
            st["dims"][dim] = {"final_category": final, "is_new": is_new}
            save_decisions(out_path, df, state, username)
            if is_new:
                # Capture the new category (+ a definition) so the sync step can
                # add it to the shared knowledge base for the other coder.
                record_new_category(shared_folder, username, dim, final)
            j += 1
        if back:
            i -= 1
            continue
        print(f"  Saved paper {i + 1}/{n}.")
        i = next_incomplete(df, state, i + 1)  # jump past complete papers

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
