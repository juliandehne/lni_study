"""
reconcile_disagreements.py

Phase B, after `icr` - turn the intercoder disagreement into a decision.

`compute_icr.py` says HOW MUCH the two coders disagree and, since the
per-subcategory split, WHICH subcategory they disagree on. It cannot say WHO IS
RIGHT. This step closes that loop:

  1. Find the SYSTEMATIC disagreements. For every (dimension, subcategory) the
     two coders' present/absent decisions form a 2x2 table; the off-diagonal
     cells are the disputed papers. A pool qualifies when it is
       - BIG ENOUGH to matter: >= --min_disagreements disputed papers, and
       - GENUINELY CONTESTED: positive specific agreement below --max_agreement
         (default 0.65). This is the substance filter. A category the two coders
         mostly agree on does not become a problem just because the handful of
         leftovers happen to sit on one side; recoding it would rewrite a
         largely shared reading on the strength of a few papers. Only the
         categories where the two readings really diverge are reviewed - and
         only reviewed categories can be recoded.
     A qualifying pool is then classified, which decides what its result means:
       - DIRECTIONAL: the disputed papers fall mostly on one side, i.e. one
         coder applies the category systematically more often than the other.
         Tested with an exact two-sided McNemar (binomial) test, which is the
         right test here because the two coders judge the SAME papers. This is
         a definition the two read differently - a winner is meaningful.
       - SYMMETRIC: both apply it about equally often but to different papers.
         That is mutual confusion about the category's boundary, and it usually
         does not resolve by declaring a winner (the joint reading will rarely
         lean far enough to trigger a rewrite, which is the correct outcome:
         the fix belongs in the schema).

  2. SAMPLE 3-5 papers per pool for a joint reading (more papers for a bigger
     pool, capped at 5 - the point is to find the critical point, not to re-code
     the corpus), drawn from BOTH sides of the disagreement so the session sees
     each coder's reading. The draw is seeded per pool, so re-running offers the
     same papers and an interrupted session resumes where it stopped.

  3. REVIEW them together, at the subcategory level: for each sampled paper the
     two coders decide jointly whether that one category applies. Verdicts are
     appended to goldstandard/disagreement.csv (id, category, what each coder
     had, the joint verdict, who it supports, a free-text note).

  4. DECIDE. When a pool's joint verdicts LEAN CLEARLY to one coder's reading
     (>= --lean of at least --min_reviewed verdicts), the step offers to apply
     that reading to the whole pool: the other coder's rows are rewritten so the
     category's presence matches the winner's on the disputed papers. Papers
     that were actually read jointly are set to the JOINT verdict for BOTH
     coders - a read paper outranks the winner's habit. Nothing is written
     without an explicit y at the prompt, and every file is copied to
     coding_<name>.backup-reconcile-<timestamp>.csv first.

The research-software gate is review-only and off by default (--include_gate):
flipping it cascades (a rejected paper's dimension rows are dropped by the next
`gold` save), so the step reports the recommendation and leaves the edit to
`run_pipeline.cmd gold <coder> fix-icr`.

Usage (from the lni_study repo root):
    python src/reconcile_disagreements.py --coders alice lukka
    python src/reconcile_disagreements.py --coders alice lukka --list_only
    python src/reconcile_disagreements.py --coders alice lukka --include_gate

Output:
    goldstandard/disagreement.csv   one row per jointly reviewed paper
    goldstandard/disagreement.md    the pools, the verdicts and what was applied
"""

import argparse
import datetime as dt
import math
import os
import random
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as cat  # noqa: E402
from build_goldstandard import load_decisions, open_paper_pdf, RS_DIM  # noqa: E402
from compute_icr import confirmed_rs_ids, load_coders, token_set  # noqa: E402

DISAGREEMENT_CSV = "disagreement.csv"
DISAGREEMENT_MD = "disagreement.md"
COLUMNS = ["dimension", "category", "paper_id", "coder_a", "coder_b",
           "a_has", "b_has", "verdict", "supports", "note", "reviewers", "reviewed_at"]

VERDICT_APPLIES = "applies"
VERDICT_NOT_APPLIES = "not_applies"
VERDICT_INSUFFICIENT = "insufficient_information"


class NoInput(Exception):
    """Raised when stdin is exhausted - the step was started without a terminal."""


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        raise NoInput from None


# --- finding the systematic disagreements -----------------------------------

def mcnemar_exact(only_a: int, only_b: int) -> float | None:
    """Two-sided exact McNemar (binomial) p for a 2x2 of paired decisions.

    Only the discordant cells carry information: under "the two coders differ at
    random", each disputed paper is equally likely to fall on either side, so
    `only_a` is Binomial(n_discordant, 0.5). A small p means the disagreement has
    a DIRECTION - one coder systematically applies the category more."""
    n = only_a + only_b
    if n == 0:
        return None
    k = min(only_a, only_b)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def label_sets(df: pd.DataFrame, dim: str) -> dict[str, set[str]]:
    """{paper id: set of categories} for one dimension of one coder."""
    d = df[df["dimension"] == dim]
    return {str(pid): token_set(val)
            for pid, val in zip(d["id"], d["final_category"])}


def build_pools(a: pd.DataFrame, b: pd.DataFrame, min_disagreements: int,
                p_level: float, max_agreement: float) -> list[dict]:
    """Every (dimension, subcategory) whose disagreement looks systematic."""
    pools = []
    for dim in cat.DIMENSIONS:
        a_sets, b_sets = label_sets(a, dim), label_sets(b, dim)
        shared = sorted(set(a_sets) & set(b_sets))
        if not shared:
            continue
        universe = set().union(*(a_sets[p] for p in shared)) | \
            set().union(*(b_sets[p] for p in shared))
        for label in sorted(universe):
            only_a = [p for p in shared if label in a_sets[p] and label not in b_sets[p]]
            only_b = [p for p in shared if label in b_sets[p] and label not in a_sets[p]]
            both = [p for p in shared if label in a_sets[p] and label in b_sets[p]]
            n_dis = len(only_a) + len(only_b)
            if n_dis < min_disagreements:
                continue
            n_a, n_b = len(only_a) + len(both), len(only_b) + len(both)
            ppa = 2 * len(both) / (n_a + n_b) if (n_a + n_b) else None
            # The substance filter: agree on most of the category's uses and it
            # is not a contested definition, however the few leftovers fall.
            if ppa is not None and ppa >= max_agreement:
                continue
            p = mcnemar_exact(len(only_a), len(only_b))
            directional = p is not None and p <= p_level
            pools.append({
                "dimension": dim, "category": label, "kind": "gate" if dim == RS_DIM
                else ("directional" if directional else "symmetric"),
                "n_shared": len(shared), "n_a": n_a, "n_b": n_b, "n_both": len(both),
                "only_a": only_a, "only_b": only_b, "n_disagree": n_dis,
                "p_mcnemar": None if p is None else round(p, 4),
                "positive_agreement": None if ppa is None else round(ppa, 3),
            })
    pools.sort(key=lambda x: (-x["n_disagree"], x["dimension"], x["category"]))
    return pools


def gate_pool(state_a: dict, state_b: dict, a_name: str, b_name: str,
              min_disagreements: int) -> dict | None:
    """The research-software gate as a pool: papers one coder accepted and the
    other rejected. Review-only - see the module docstring."""
    only_a = sorted(p for p, st in state_a.items()
                    if st.get("rs") == "1" and state_b.get(p, {}).get("rs") == "0")
    only_b = sorted(p for p, st in state_b.items()
                    if st.get("rs") == "1" and state_a.get(p, {}).get("rs") == "0")
    n_dis = len(only_a) + len(only_b)
    if n_dis < min_disagreements:
        return None
    return {"dimension": RS_DIM, "category": "is_research_software", "kind": "gate",
            "n_shared": len(set(state_a) & set(state_b)), "n_a": len(only_a),
            "n_b": len(only_b), "n_both": 0, "only_a": only_a, "only_b": only_b,
            "n_disagree": n_dis, "p_mcnemar": mcnemar_exact(len(only_a), len(only_b)),
            "positive_agreement": None}


# --- sampling ----------------------------------------------------------------

def sample_size(pool_n: int) -> int:
    """3 to 5 papers, more for a bigger pool. Small pools are read in full."""
    if pool_n <= 3:
        return pool_n
    if pool_n <= 8:
        return 3
    if pool_n <= 15:
        return 4
    return 5


def sample_pool(pool: dict, seed: int) -> list[str]:
    """Draw the review sample from BOTH sides, so the session reads each coder's
    application of the category, not just the more prolific one. Seeded per pool
    (dimension + category), so the sample is stable across runs and independent
    of which other pools exist."""
    rng = random.Random(f"{seed}:{pool['dimension']}:{pool['category']}")
    k = sample_size(pool["n_disagree"])
    only_a, only_b = list(pool["only_a"]), list(pool["only_b"])
    rng.shuffle(only_a)
    rng.shuffle(only_b)
    if not only_a or not only_b:
        return (only_a or only_b)[:k]
    # Proportional to the two sides, but never zero from a side that has papers.
    k_a = max(1, min(len(only_a), round(k * len(only_a) / pool["n_disagree"])))
    k_b = max(1, min(len(only_b), k - k_a))
    k_a = min(len(only_a), k - k_b)
    return only_a[:k_a] + only_b[:k_b]


# --- the joint review --------------------------------------------------------

def load_reviewed(path: Path) -> dict[tuple[str, str, str], dict]:
    """Prior verdicts keyed by (dimension, category, paper id), so an
    interrupted session resumes instead of re-asking."""
    if not path.exists():
        return {}
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except pd.errors.EmptyDataError:
        return {}
    return {(r["dimension"], r["category"], r["paper_id"]): dict(r)
            for _, r in df.iterrows()}


def save_reviewed(path: Path, reviewed: dict) -> None:
    rows = [{c: r.get(c, "") for c in COLUMNS} for r in reviewed.values()]
    df = pd.DataFrame(rows, columns=COLUMNS)
    if not df.empty:
        df = df.sort_values(["dimension", "category", "paper_id"])
    df.to_csv(path, index=False)


def supports_of(verdict: str, a_has: bool, b_has: bool) -> str:
    """Whose reading the joint verdict backs: the coder whose presence/absence
    matches it. `insufficient_information` backs neither."""
    if verdict == VERDICT_APPLIES:
        return "a" if a_has and not b_has else ("b" if b_has and not a_has else "both")
    if verdict == VERDICT_NOT_APPLIES:
        return "a" if not a_has and b_has else ("b" if not b_has and a_has else "both")
    return "neither"


def describe(dim: str, label: str) -> str:
    return cat.TYPOLOGY.get(dim, {}).get("examples", {}).get(label, "(no description on file)")


def review_pool(pool: dict, sample: list[str], a_sets: dict, b_sets: dict,
                a_name: str, b_name: str, reviewed: dict, reviewers: str,
                pdf_folder: Path, out_path: Path) -> str:
    """Read the sampled papers together and record one verdict each.

    Returns 'quit' if the session asked to stop, else 'done'."""
    print(f"\n{'=' * 78}\n  {pool['dimension']} / {pool['category']}   "
          f"[{pool['kind']}]  {pool['n_disagree']} disputed papers "
          f"({a_name} only: {len(pool['only_a'])}, {b_name} only: {len(pool['only_b'])})")
    print(f"  Definition: {describe(pool['dimension'], pool['category'])}")
    if pool["p_mcnemar"] is not None:
        print(f"  McNemar p={pool['p_mcnemar']}   positive agreement="
              f"{pool['positive_agreement']}")
    print(f"  Reading {len(sample)} of them together.\n{'=' * 78}")

    try:
        return _review_papers(pool, sample, a_sets, b_sets, a_name, b_name,
                              reviewed, reviewers, pdf_folder, out_path)
    except NoInput:
        save_reviewed(out_path, reviewed)
        print("\n  No interactive input (stdin is closed) - stopping the review. "
              "Run this step from a terminal, or pass 'list' to only print the pools.")
        return "quit"


def _review_papers(pool, sample, a_sets, b_sets, a_name, b_name, reviewed,
                   reviewers, pdf_folder, out_path) -> str:
    for n, pid in enumerate(sample, 1):
        key = (pool["dimension"], pool["category"], pid)
        if key in reviewed and reviewed[key].get("verdict"):
            print(f"  [{n}/{len(sample)}] {pid}: already reviewed "
                  f"({reviewed[key]['verdict']}) - skipping")
            continue
        a_has = pool["category"] in a_sets.get(pid, set())
        b_has = pool["category"] in b_sets.get(pid, set())
        print(f"\n  [{n}/{len(sample)}] paper {pid}")
        print(f"      {a_name:<10} {sorted(a_sets.get(pid, set()))}"
              f"   <- {'HAS' if a_has else 'does NOT have'} {pool['category']}")
        print(f"      {b_name:<10} {sorted(b_sets.get(pid, set()))}"
              f"   <- {'HAS' if b_has else 'does NOT have'} {pool['category']}")

        while True:
            print(f"      Does '{pool['category']}' apply to this paper? "
                  "[y]=yes, [n]=no, [i]=insufficient info, [o]=open PDF, "
                  "[s]=skip, [q]=save & quit")
            choice = ask("      > ").lower()
            if choice == "o":
                open_paper_pdf(pdf_folder, {"id": pid})
                continue
            if choice == "s":
                break
            if choice == "q":
                save_reviewed(out_path, reviewed)
                return "quit"
            verdict = {"y": VERDICT_APPLIES, "n": VERDICT_NOT_APPLIES,
                       "i": VERDICT_INSUFFICIENT}.get(choice)
            if verdict is None:
                print("      (pick y, n, i, o, s or q)")
                continue
            note = ask("      Note (why - the critical point; optional): ")
            reviewed[key] = {
                "dimension": pool["dimension"], "category": pool["category"],
                "paper_id": pid, "coder_a": a_name, "coder_b": b_name,
                "a_has": str(a_has), "b_has": str(b_has), "verdict": verdict,
                "supports": supports_of(verdict, a_has, b_has), "note": note,
                "reviewers": reviewers,
                "reviewed_at": dt.datetime.now().isoformat(timespec="seconds"),
            }
            save_reviewed(out_path, reviewed)  # after every verdict: crash-safe
            print(f"      -> {verdict} (supports "
                  f"{ {'a': a_name, 'b': b_name}.get(reviewed[key]['supports'], reviewed[key]['supports']) })")
            break
    return "done"


# --- the decision ------------------------------------------------------------

def pool_lean(pool: dict, reviewed: dict, min_reviewed: int,
              lean: float) -> dict:
    """Does the joint reading back one coder clearly enough to generalise?"""
    rows = [r for (d, c, _), r in reviewed.items()
            if d == pool["dimension"] and c == pool["category"] and r.get("verdict")]
    votes = [r["supports"] for r in rows]
    n_a, n_b = votes.count("a"), votes.count("b")
    decisive = n_a + n_b  # 'both'/'neither' verdicts back no reading
    winner, share = None, None
    if decisive:
        share = max(n_a, n_b) / decisive
        if len(rows) >= min_reviewed and share >= lean and n_a != n_b:
            winner = "a" if n_a > n_b else "b"
    return {"n_reviewed": len(rows), "n_a": n_a, "n_b": n_b,
            "share": None if share is None else round(share, 2),
            "winner": winner, "rows": rows}


def backup_once(path: Path, done: set, stamp: str) -> None:
    """Copy a coder file aside before the first edit of this run. The dotted
    suffix keeps `load_coders` from ever reading it back as a coder."""
    if path in done or not path.exists():
        return
    dest = path.with_name(f"{path.stem}.backup-reconcile-{stamp}.csv")
    shutil.copy2(path, dest)
    print(f"  backup: {dest.name}")
    done.add(path)


def set_label(cell, label: str, present: bool) -> str:
    """Add or remove one category in a `;`-separated cell, keeping the coder's
    original order and appending a newly-set label at the end."""
    tokens = [t.strip() for t in str(cell or "").split(";") if t.strip()]
    if present and label not in tokens:
        tokens.append(label)
    elif not present and label in tokens:
        tokens = [t for t in tokens if t != label]
    return ";".join(tokens)


def apply_pool(pool: dict, lean: dict, a_name: str, b_name: str,
               shared_folder: Path, backups: set, stamp: str) -> list[str]:
    """Rewrite the losing coder's rows for this pool. Returns a change log.

    Reviewed papers are set to the JOINT verdict for BOTH coders (a paper the
    two actually read together outranks the winner's habit); the remaining
    disputed papers get the loser aligned to the winner."""
    winner_name = a_name if lean["winner"] == "a" else b_name
    loser_name = b_name if lean["winner"] == "a" else a_name
    winner_has_it = {p: True for p in (pool["only_a"] if lean["winner"] == "a"
                                       else pool["only_b"])}
    winner_has_it.update({p: False for p in (pool["only_b"] if lean["winner"] == "a"
                                             else pool["only_a"])})

    # The joint verdict overrides for the papers that were actually read.
    joint = {}
    for r in lean["rows"]:
        if r["verdict"] == VERDICT_APPLIES:
            joint[r["paper_id"]] = True
        elif r["verdict"] == VERDICT_NOT_APPLIES:
            joint[r["paper_id"]] = False  # insufficient_information: leave alone

    targets = {winner_name: {}, loser_name: {}}
    for pid, present in winner_has_it.items():
        if pid in joint:
            targets[winner_name][pid] = joint[pid]
            targets[loser_name][pid] = joint[pid]
        else:
            targets[loser_name][pid] = present

    log = []
    for coder, wanted in targets.items():
        if not wanted:
            continue
        path = shared_folder / f"coding_{coder}.csv"
        df = pd.read_csv(path, dtype=str).fillna("")
        mask_dim = df["dimension"] == pool["dimension"]
        changed = 0
        for pid, present in wanted.items():
            m = mask_dim & (df["id"] == pid)
            if not m.any():
                continue
            before = df.loc[m, "final_category"].iloc[0]
            after = set_label(before, pool["category"], present)
            if after != before:
                backup_once(path, backups, stamp)
                df.loc[m, "final_category"] = after
                changed += 1
        if changed:
            df.to_csv(path, index=False)
            log.append(f"{coder}: {changed} row(s) rewritten for "
                       f"{pool['dimension']}/{pool['category']}")
    return log


# --- reporting ---------------------------------------------------------------

def pools_table(pools: list[dict], a_name: str, b_name: str) -> pd.DataFrame:
    return pd.DataFrame([{
        "dimension": p["dimension"], "category": p["category"], "kind": p["kind"],
        f"{a_name}_only": len(p["only_a"]), f"{b_name}_only": len(p["only_b"]),
        "both": p["n_both"], "disputed": p["n_disagree"],
        "p_mcnemar": p["p_mcnemar"], "positive_agreement": p["positive_agreement"],
        "sample": sample_size(p["n_disagree"]),
    } for p in pools])


def write_report(path: Path, a_name: str, b_name: str, pools: list[dict],
                 table: pd.DataFrame, leans: dict, applied: list[str],
                 criteria: str = "") -> None:
    body = [f"# Disagreement reconciliation ({a_name} vs {b_name})", "",
            f"_Generated {dt.datetime.now().isoformat(timespec='seconds')}._", "",
            "Systematic disagreements between the two coders, at the subcategory "
            "level. A category is only listed - and so only ever recoded - when the "
            "two readings genuinely diverge, not when a mostly shared reading has a "
            "few stray papers. A **directional** pool is one coder applying a "
            "category systematically more than the other (exact McNemar p <= level) - "
            "a definition the two read differently. A **symmetric** pool is both "
            "coders using it about equally often but on different papers - a "
            "definition unclear to both, which declaring a winner will not fix.", ""]
    if criteria:
        body += [f"Selection: {criteria}.", ""]
    body += ["## Pools", "", table.to_markdown(index=False), ""]
    if leans:
        body += ["## Joint review", ""]
        for (dim, label), ln in sorted(leans.items()):
            head = f"### {dim} / {label}"
            if ln["winner"]:
                who = a_name if ln["winner"] == "a" else b_name
                head += f" - leans to **{who}** ({ln['share']:.0%} of {ln['n_reviewed']})"
            elif ln["n_reviewed"]:
                head += f" - no clear lean ({ln['n_a']}:{ln['n_b']} of {ln['n_reviewed']})"
            body += [head, ""]
            for r in ln["rows"]:
                who = {"a": a_name, "b": b_name}.get(r["supports"], r["supports"])
                note = f" - {r['note']}" if r.get("note") else ""
                body.append(f"- `{r['paper_id']}`: **{r['verdict']}** (supports {who}){note}")
            body.append("")
    body += ["## Applied", ""]
    body += [f"- {line}" for line in applied] or ["- nothing applied"]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review and resolve the systematic intercoder disagreements.")
    parser.add_argument("--shared_folder", default=str(
        (Path(os.environ.get("LNI_DATA_ROOT") or Path(__file__).resolve().parent.parent)
         / "goldstandard").resolve()))
    parser.add_argument("--pdf_folder", default=str(
        (Path(os.environ.get("LNI_DATA_ROOT") or Path(__file__).resolve().parent.parent)
         / ".workingset" / "gold_confirmed").resolve()))
    parser.add_argument("--coders", nargs=2, metavar=("A", "B"), default=None)
    parser.add_argument("--min_disagreements", type=int, default=4,
                        help="Smallest disputed pool worth a joint reading (default 4).")
    parser.add_argument("--p_level", type=float, default=0.05,
                        help="Exact-McNemar level for calling a pool directional.")
    parser.add_argument("--max_agreement", type=float, default=0.65,
                        help="A pool is only reviewed (and so only ever recoded) when "
                             "the two coders' positive specific agreement on the "
                             "category is BELOW this - i.e. the disagreement is about "
                             "the definition, not about a few stray papers (default .65).")
    parser.add_argument("--min_reviewed", type=int, default=3,
                        help="Verdicts needed before a pool may be applied.")
    parser.add_argument("--lean", type=float, default=0.75,
                        help="Share of decisive verdicts one coder needs to win a pool.")
    parser.add_argument("--seed", type=int, default=20260902,
                        help="Sampling seed; the same seed re-offers the same papers.")
    parser.add_argument("--reviewers", default=None,
                        help="Who sat together (recorded in disagreement.csv).")
    parser.add_argument("--list_only", action="store_true",
                        help="Print the pools and the sample sizes, review nothing.")
    parser.add_argument("--include_gate", action="store_true",
                        help="Also review the research-software gate vetoes "
                             "(review-only: the step never rewrites the gate).")
    args = parser.parse_args()

    shared_folder = Path(args.shared_folder).resolve()
    print(f"[config] goldstandard: {shared_folder}")
    coders = load_coders(shared_folder)
    if len(coders) < 2:
        raise SystemExit(f"Need >=2 coder files in {shared_folder}, found {list(coders)}")
    names = list(coders)
    if args.coders:
        missing = [n for n in args.coders if n not in coders]
        if missing:
            raise SystemExit(f"Unknown coder(s) {missing}; available: {names}")
        a_name, b_name = args.coders
    else:
        # Not names[0..1]: the folder still holds abandoned coder files (bob).
        # Default to the two with the most coded rows - the live pair.
        busiest = sorted(names, key=lambda n: -len(coders[n]))
        a_name, b_name = busiest[0], busiest[1]
        print(f"[coders] no --coders given; defaulting to the two busiest files "
              f"({', '.join(f'{n}: {len(coders[n])} rows' for n in busiest[:2])})")
    print(f"[coders] {a_name} (a) vs {b_name} (b)")

    state_a = load_decisions(shared_folder / f"coding_{a_name}.csv")
    state_b = load_decisions(shared_folder / f"coding_{b_name}.csv")
    confirmed, vetoed = confirmed_rs_ids(state_a, state_b)
    print(f"[gate] {len(confirmed)} papers confirmed by both, {len(vetoed)} vetoed")
    if not confirmed:
        raise SystemExit("No jointly confirmed papers - nothing to reconcile.")

    a = coders[a_name][coders[a_name]["id"].isin(confirmed)]
    b = coders[b_name][coders[b_name]["id"].isin(confirmed)]
    pools = build_pools(a, b, args.min_disagreements, args.p_level,
                        args.max_agreement)
    if args.include_gate:
        gp = gate_pool(state_a, state_b, a_name, b_name, args.min_disagreements)
        if gp:
            pools.insert(0, gp)
    criteria = (f">= {args.min_disagreements} disputed papers AND positive specific "
                f"agreement < {args.max_agreement} (directional at exact-McNemar "
                f"p <= {args.p_level})")
    if not pools:
        print(f"No contested category left after the filter ({criteria}). "
              "Nothing to review.")
        return

    table = pools_table(pools, a_name, b_name)
    print(f"\n[pools] {len(pools)} contested category/ies - {criteria}")
    print(f"[pools] {sum(sample_size(p['n_disagree']) for p in pools)} papers to read jointly:")
    print(table.to_string(index=False))

    out_csv = shared_folder / DISAGREEMENT_CSV
    out_md = shared_folder / DISAGREEMENT_MD
    if args.list_only:
        write_report(out_md, a_name, b_name, pools, table, {}, [], criteria)
        print(f"\nSaved: {out_md}   (--list_only: nothing reviewed)")
        return
    if not sys.stdin.isatty():
        write_report(out_md, a_name, b_name, pools, table, {}, [], criteria)
        print(f"\nSaved: {out_md}\nNot a terminal - run interactively to review.")
        return

    reviewers = args.reviewers or f"{a_name}+{b_name}"
    reviewed = load_reviewed(out_csv)
    pdf_folder = Path(args.pdf_folder)
    print(f"\nJoint review. {len(reviewed)} verdict(s) already on file; "
          f"'q' saves and quits at any point.")

    for pool in pools:
        dim = pool["dimension"]
        a_sets = label_sets(a, dim) if dim != RS_DIM else {}
        b_sets = label_sets(b, dim) if dim != RS_DIM else {}
        if dim == RS_DIM:  # gate pool: the "category" is the rs boolean itself
            a_sets = {p: {"is_research_software"} for p in pool["only_a"]}
            b_sets = {p: {"is_research_software"} for p in pool["only_b"]}
        if review_pool(pool, sample_pool(pool, args.seed), a_sets, b_sets,
                       a_name, b_name, reviewed, reviewers, pdf_folder,
                       out_csv) == "quit":
            print("\nStopped. Re-run to continue where you left off.")
            break

    save_reviewed(out_csv, reviewed)
    print(f"\nSaved: {out_csv}")

    # --- what the joint reading decided, and what to do about it -------------
    leans = {(p["dimension"], p["category"]):
             pool_lean(p, reviewed, args.min_reviewed, args.lean) for p in pools}
    applied: list[str] = []
    backups: set = set()
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M")

    print(f"\n{'=' * 78}\n  What the joint reading produced\n{'=' * 78}")
    for pool in pools:
        key = (pool["dimension"], pool["category"])
        ln = leans[key]
        print(f"\n  {pool['dimension']} / {pool['category']}  [{pool['kind']}]  "
              f"{pool['n_disagree']} disputed, {ln['n_reviewed']} read jointly")
        for r in ln["rows"]:
            who = {"a": a_name, "b": b_name}.get(r["supports"], r["supports"])
            print(f"      {r['paper_id']}: {r['verdict']} (supports {who})"
                  + (f"  - {r['note']}" if r.get("note") else ""))
        if not ln["winner"]:
            print(f"      => no clear lean ({a_name} {ln['n_a']} : {b_name} {ln['n_b']}"
                  f" of {ln['n_reviewed']}). Left as it is - this is a definition to "
                  "sharpen in the schema, not a coder to correct.")
            continue
        winner = a_name if ln["winner"] == "a" else b_name
        loser = b_name if ln["winner"] == "a" else a_name
        print(f"      => leans to {winner} ({ln['share']:.0%} of {ln['n_reviewed']} "
              f"decisive verdicts)")
        if pool["kind"] == "gate":
            print("      Gate pool: NOT rewritten here (flipping the gate cascades "
                  "into the dimension rows). Fix it with "
                  f"'run_pipeline.cmd gold {loser} fix-icr'.")
            continue
        n_reviewed_in_pool = len([r for r in ln["rows"]
                                  if r["verdict"] != VERDICT_INSUFFICIENT])
        print(f"      Applying would rewrite {loser}'s rows on up to "
              f"{pool['n_disagree']} disputed paper(s) to match {winner}'s reading, "
              f"and set BOTH coders to the joint verdict on the "
              f"{n_reviewed_in_pool} paper(s) read together. "
              f"{loser}'s file is backed up first.")
        try:
            answer = ask(f"      Apply {winner}'s reading to this pool? [y/N] ").lower()
        except NoInput:
            answer = "n"
        if answer == "y":
            applied += apply_pool(pool, ln, a_name, b_name, shared_folder, backups, stamp)
        else:
            print("      skipped")

    write_report(out_md, a_name, b_name, pools, table, leans, applied, criteria)
    print(f"\nSaved: {out_md}")
    if applied:
        print("\nApplied:")
        for line in applied:
            print(f"  {line}")
        print("\nRe-run 'run_pipeline.cmd icr' to see the reliability after the fix.")


if __name__ == "__main__":
    main()
