"""
compute_icr.py

Intercoder reliability for the goldstandard (notes step 12).

Merges the two coders' decision files produced by `build_goldstandard.py`
(`goldstandard/coding_<username>.csv`) and computes, per typology dimension,
the intercoder reliability between the human coders on the *final categories*.

Metrics (nominal categorical labels):
  - Krippendorff's alpha (nominal)
  - Cohen's kappa (raw agreement adjusted for chance)
  - raw percent agreement

ICR is computed ONLY over the human-confirmed goldstandard: a paper is included
only when BOTH coders set the research-software gate to 1. A single rs=0 is a
VETO — one coder rejecting a paper as not-research-software removes it from the
goldstandard, so it is excluded from every dimension's reliability (the typology
only describes papers that actually contain research software). Within that
confirmed set, each dimension still uses the pairwise-complete papers (both
coders coded that dimension). The gate itself is reported separately as a
research-software-agreement line, not as a typology dimension.

Multi-value dimensions are reported TWICE, because one number cannot describe
them honestly:
  1. as SETS - a `;`-separated cell is stripped, de-duplicated and sorted before
     comparison, so the same categories in a different order count as agreement.
     This is exact-match: one extra category is a full disagreement, which on a
     dimension like software_lifecycle (three to five phases per paper) makes the
     nominal alpha a lower bound rather than a description.
  2. SPLIT INTO BINARY VARIABLES - each subcategory of a multi-value dimension
     becomes its own present/absent variable over the same papers, scored with
     the same three metrics plus positive specific agreement and Jaccard. This
     prices partial overlap fairly and localises the disagreement to the
     category. Written to icr_by_label.csv and into the .md report, with a
     macro average over subcategories per dimension.

Backup and variant files (`coding_<user>.<suffix>.csv`) are ignored, so the pair
is never two versions of the same coder. Name the pair explicitly with --coders.

Usage (from the lni_study repo root):
    python src/compute_icr.py --shared_folder goldstandard --coders alice bob

Output:
    goldstandard/icr_goldstandard.csv   per dimension
    goldstandard/icr_by_label.csv       per subcategory of the multi-value dimensions
    goldstandard/icr_goldstandard.md    both, as a report
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as cat  # noqa: E402
from build_goldstandard import load_decisions, RS_DIM  # noqa: E402

try:
    import krippendorff
except ImportError:  # pragma: no cover
    krippendorff = None

try:
    from sklearn.metrics import cohen_kappa_score
except ImportError:  # pragma: no cover
    cohen_kappa_score = None


def load_coders(shared_folder: Path) -> dict[str, pd.DataFrame]:
    """Load the live coder files, ignoring backups and variants.

    A live coder file is `coding_<username>.csv` with a plain username. Backups
    and experiment variants carry a dotted suffix
    (`coding_alice.backup-2026-06-19.csv`,
    `coding_bob.theirs-with-methodology.backup-2026-06-22.csv`) and are skipped
    — otherwise the alphabetically-first two files can be two versions of the
    SAME coder, which yields a meaninglessly high reliability."""
    coders = {}
    skipped = []
    for f in sorted(shared_folder.glob("coding_*.csv")):
        username = f.stem.replace("coding_", "", 1)
        if "." in username:
            skipped.append(f.name)
            continue
        try:
            coders[username] = pd.read_csv(f, dtype={"id": str})
        except pd.errors.EmptyDataError:
            continue
    if skipped:
        print(f"[coders] ignored {len(skipped)} backup/variant file(s): {', '.join(skipped)}")
    return coders


def normalize_multi(value) -> str:
    """Canonical form of a `;`-separated multi-value cell.

    Coders enter the same set of categories in different orders, so a raw
    string comparison scores `entwurf;implementierung` and
    `implementierung;entwurf` as a disagreement. Tokens are stripped,
    de-duplicated and sorted, so agreement is judged on the SET. Single-valued
    dimensions pass through unchanged apart from whitespace."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "nan"
    tokens = {t.strip() for t in str(value).split(";")}
    tokens.discard("")
    return ";".join(sorted(tokens)) if tokens else "nan"


def encode_nominal(values: pd.Series) -> tuple[np.ndarray, dict]:
    """Map category strings to integer codes for ICR libraries."""
    cats = sorted(set(values.dropna().astype(str)))
    mapping = {c: i for i, c in enumerate(cats)}
    return values.astype(str).map(mapping).to_numpy(), mapping


def compute_dimension_icr(a: pd.DataFrame, b: pd.DataFrame, dim: str) -> dict | None:
    """Compute ICR for one dimension between two coders on shared paper ids."""
    a_dim = a[a["dimension"] == dim].set_index("id")["final_category"]
    b_dim = b[b["dimension"] == dim].set_index("id")["final_category"]
    shared = a_dim.index.intersection(b_dim.index)
    if len(shared) == 0:
        return None

    pair = pd.DataFrame({"a": a_dim.loc[shared].map(normalize_multi),
                         "b": b_dim.loc[shared].map(normalize_multi)})
    codes, _ = encode_nominal(pd.concat([pair["a"], pair["b"]]))
    a_codes = codes[:len(pair)]
    b_codes = codes[len(pair):]

    raw_agreement = float((pair["a"].values == pair["b"].values).mean())

    alpha = None
    if krippendorff is not None:
        try:
            alpha = round(float(krippendorff.alpha(
                reliability_data=np.vstack([a_codes, b_codes]),
                level_of_measurement="nominal")), 3)
        except (ValueError, ZeroDivisionError):
            alpha = 1.0 if raw_agreement == 1.0 else None

    kappa = None
    if cohen_kappa_score is not None:
        try:
            kappa = round(float(cohen_kappa_score(a_codes, b_codes)), 3)
        except ValueError:
            kappa = None

    return {
        "dimension": dim,
        "n_shared": int(len(shared)),
        "raw_agreement": round(raw_agreement, 3),
        "krippendorff_alpha": alpha,
        "cohen_kappa": kappa,
    }


def token_set(value) -> set[str]:
    """The set of categories in a `;`-separated cell (empty set when missing)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return set()
    tokens = {t.strip() for t in str(value).split(";")}
    tokens.discard("")
    return tokens


def label_universe(a_sets: pd.Series, b_sets: pd.Series, dim: str) -> list[str]:
    """Every subcategory that could be present for `dim`.

    The schema is the source of truth (so a label neither coder used is still
    reported, as an all-zero row that documents the omission), extended with
    anything the coders actually entered — coder-coined categories not yet
    synced into the schema, and the reserved `insufficient_information`."""
    schema = set(cat.TYPOLOGY.get(dim, {}).get("examples", {}))
    schema |= set(cat.TYPOLOGY.get(dim, {}).get("deprecated", set()))
    used = set().union(*a_sets, *b_sets) if len(a_sets) else set()
    return sorted(schema | used)


def binary_icr(a_bits: np.ndarray, b_bits: np.ndarray) -> dict:
    """Reliability of one present/absent variable between two coders."""
    n = len(a_bits)
    n_a, n_b = int(a_bits.sum()), int(b_bits.sum())
    n_both = int((a_bits & b_bits).sum())
    n_union = int((a_bits | b_bits).sum())
    raw = float((a_bits == b_bits).mean()) if n else float("nan")

    alpha = None
    if krippendorff is not None:
        try:
            # As 0/1 ints, not bools: krippendorff cannot build a value domain
            # for dtype kind 'b' and would raise for every single label.
            alpha = round(float(krippendorff.alpha(
                reliability_data=np.vstack([a_bits, b_bits]).astype(int),
                level_of_measurement="nominal")), 3)
        except (ValueError, ZeroDivisionError):
            # Degenerate: the label is present (or absent) in every paper for
            # both coders. Alpha is undefined - no observable disagreement to
            # correct for - but perfect agreement is still worth recording.
            alpha = 1.0 if raw == 1.0 else None

    kappa = None
    if cohen_kappa_score is not None:
        try:
            k = float(cohen_kappa_score(a_bits, b_bits))
            kappa = None if np.isnan(k) else round(k, 3)
        except ValueError:
            kappa = None

    return {
        "n_shared": n,
        "n_a": n_a,
        "n_b": n_b,
        "n_both": n_both,
        "prevalence": round((n_a + n_b) / (2 * n), 3) if n else None,
        "raw_agreement": round(raw, 3),
        # Positive specific agreement: agreement on PRESENCE only. Unlike kappa
        # it does not collapse for rare labels, where the shared absences that
        # dominate raw agreement carry no information.
        "positive_agreement": round(2 * n_both / (n_a + n_b), 3) if (n_a + n_b) else None,
        "jaccard": round(n_both / n_union, 3) if n_union else None,
        "krippendorff_alpha": alpha,
        "cohen_kappa": kappa,
    }


def compute_label_icr(a: pd.DataFrame, b: pd.DataFrame, dim: str) -> list[dict]:
    """Per-subcategory binary ICR for one multi-value dimension.

    A multi-value cell is not a nominal label but a SET, and comparing sets for
    exact equality is unfairly harsh: on `software_lifecycle`, where coders name
    three to five phases per paper, one extra phase scores as total
    disagreement. Splitting the dimension into one present/absent variable per
    subcategory measures what the coders actually disagree about — which phase,
    which language — and localises it to the label."""
    a_dim = a[a["dimension"] == dim].set_index("id")["final_category"]
    b_dim = b[b["dimension"] == dim].set_index("id")["final_category"]
    shared = a_dim.index.intersection(b_dim.index)
    if len(shared) == 0:
        return []

    a_sets = a_dim.loc[shared].map(token_set)
    b_sets = b_dim.loc[shared].map(token_set)

    rows = []
    for label in label_universe(a_sets, b_sets, dim):
        a_bits = np.array([label in s for s in a_sets], dtype=bool)
        b_bits = np.array([label in s for s in b_sets], dtype=bool)
        if not a_bits.any() and not b_bits.any():
            continue  # neither coder ever used it: nothing to be reliable about
        rows.append({"dimension": dim, "category": label,
                     "in_schema": label in cat.TYPOLOGY.get(dim, {}).get("examples", {}),
                     **binary_icr(a_bits, b_bits)})
    return rows


def set_level_scores(a: pd.DataFrame, b: pd.DataFrame, dim: str) -> dict | None:
    """Per-paper set overlap for a multi-value dimension, averaged over papers.

    The companion to the per-label view: `mean_jaccard` and `mean_dice` say how
    close the two coders' sets are on the average paper, where the nominal alpha
    in the main table only asks whether they are identical."""
    a_dim = a[a["dimension"] == dim].set_index("id")["final_category"]
    b_dim = b[b["dimension"] == dim].set_index("id")["final_category"]
    shared = a_dim.index.intersection(b_dim.index)
    if len(shared) == 0:
        return None
    jac, dice = [], []
    for pid in shared:
        sa, sb = token_set(a_dim.loc[pid]), token_set(b_dim.loc[pid])
        if not sa and not sb:
            jac.append(1.0)
            dice.append(1.0)
            continue
        inter = len(sa & sb)
        jac.append(inter / len(sa | sb))
        dice.append(2 * inter / (len(sa) + len(sb)))
    return {"dimension": dim, "n_shared": len(shared),
            "mean_jaccard": round(float(np.mean(jac)), 3),
            "mean_dice": round(float(np.mean(dice)), 3),
            "exact_set_match": round(float(np.mean([j == 1.0 for j in jac])), 3)}


def confirmed_rs_ids(state_a: dict, state_b: dict) -> tuple[set, set]:
    """Papers BOTH coders confirmed as research software (rs == '1').

    A single rs == '0' is a VETO that removes the paper. Returns
    (confirmed, vetoed) where `confirmed` = both coders rs=1 and `vetoed` =
    papers one coder confirmed while the other rejected (gate disagreement)."""
    a1 = {pid for pid, st in state_a.items() if st.get("rs") == "1"}
    b1 = {pid for pid, st in state_b.items() if st.get("rs") == "1"}
    a0 = {pid for pid, st in state_a.items() if st.get("rs") == "0"}
    b0 = {pid for pid, st in state_b.items() if st.get("rs") == "0"}
    confirmed = a1 & b1
    vetoed = (a1 & b0) | (b1 & a0)
    return confirmed, vetoed


def gate_agreement(state_a: dict, state_b: dict) -> dict | None:
    """Raw agreement on the research-software gate over papers both coders decided."""
    both = [pid for pid in state_a
            if state_a[pid].get("rs") in ("0", "1")
            and state_b.get(pid, {}).get("rs") in ("0", "1")]
    if not both:
        return None
    agree = sum(1 for pid in both if state_a[pid]["rs"] == state_b[pid]["rs"])
    return {"n_both_decided": len(both), "raw_agreement": round(agree / len(both), 3)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute goldstandard intercoder reliability.")
    parser.add_argument(
        "--shared_folder",
        default=str(
            (Path(os.environ.get("LNI_DATA_ROOT") or Path(__file__).resolve().parent.parent)
             / "goldstandard").resolve()))
    parser.add_argument(
        "--coders", nargs=2, metavar=("A", "B"), default=None,
        help="The two coder usernames to compare, e.g. --coders alice lukka. "
             "Defaults to the first two live coder files found.")
    args = parser.parse_args()

    shared_folder = Path(args.shared_folder).resolve()
    print(f"[config] goldstandard: {shared_folder}  "
          f"(reads coding_*.csv, writes icr_goldstandard.csv/.md)")
    coders = load_coders(shared_folder)
    if len(coders) < 2:
        raise SystemExit(f"Need >=2 coder files in {shared_folder}, found {len(coders)}: "
                         f"{list(coders)}")

    names = list(coders)
    if args.coders:
        missing = [n for n in args.coders if n not in coders]
        if missing:
            raise SystemExit(f"Unknown coder(s) {missing} in {shared_folder}; "
                             f"available: {names}")
        a_name, b_name = args.coders
    else:
        if len(names) > 2:
            print(f"Note: {len(names)} coders found ({names}); computing ICR for the first "
                  f"two: {names[:2]}. Pass --coders A B to choose.")
        a_name, b_name = names[0], names[1]
    print(f"[coders] comparing {a_name} vs {b_name}")
    a, b = coders[a_name], coders[b_name]

    # Restrict ICR to the human-confirmed goldstandard: a paper counts only when
    # BOTH coders set the research-software gate to 1. A single rs=0 is a veto.
    state_a = load_decisions(shared_folder / f"coding_{a_name}.csv")
    state_b = load_decisions(shared_folder / f"coding_{b_name}.csv")
    confirmed, vetoed = confirmed_rs_ids(state_a, state_b)
    gate = gate_agreement(state_a, state_b)

    print(f"\n[gate] research-software confirmed by both coders: {len(confirmed)}  "
          f"vetoed (one rs=1, other rs=0): {len(vetoed)}")
    if gate is not None:
        print(f"[gate] research-software agreement: {gate['raw_agreement']} "
              f"over {gate['n_both_decided']} papers both coders decided")
    if not confirmed:
        raise SystemExit("No papers confirmed as research software by BOTH coders yet; "
                         "nothing to compute ICR over.")

    a = a[a["id"].isin(confirmed)]
    b = b[b["id"].isin(confirmed)]

    rows = []
    for dim in cat.DIMENSIONS:
        res = compute_dimension_icr(a, b, dim)
        if res is not None:
            rows.append(res)

    if not rows:
        raise SystemExit("No overlapping coded dimensions among the confirmed papers yet.")

    df_icr = pd.DataFrame(rows)
    print(df_icr.to_string(index=False))

    # --- multi-value dimensions, split into one binary variable per subcategory ---
    # The nominal alpha above treats a multi-value cell as one atomic label, so a
    # single extra category counts as complete disagreement. Below, each
    # subcategory becomes its own present/absent variable, which both prices the
    # partial overlap fairly and shows WHICH categories the coders diverge on.
    multi_dims = [d for d in cat.DIMENSIONS if cat.TYPOLOGY.get(d, {}).get("multi")]
    label_rows, set_rows = [], []
    for dim in multi_dims:
        label_rows.extend(compute_label_icr(a, b, dim))
        sl = set_level_scores(a, b, dim)
        if sl is not None:
            set_rows.append(sl)

    df_labels = pd.DataFrame(label_rows)
    df_sets = pd.DataFrame(set_rows)
    macro = pd.DataFrame()
    if not df_labels.empty:
        # A metric is None where it is undefined for that label, which makes the
        # column dtype object; coerce so the macro averages are numeric.
        for col in ("krippendorff_alpha", "cohen_kappa", "positive_agreement"):
            df_labels[col] = pd.to_numeric(df_labels[col], errors="coerce")
        # Macro average over the subcategories of a dimension: every category
        # weighs the same regardless of how often it was used, so a dimension is
        # not carried by one dominant label.
        macro = (df_labels.groupby("dimension")
                 .agg(n_categories=("category", "size"),
                      mean_alpha=("krippendorff_alpha", "mean"),
                      mean_kappa=("cohen_kappa", "mean"),
                      mean_positive_agreement=("positive_agreement", "mean"))
                 .round(3).reset_index())
        if not df_sets.empty:
            macro = macro.merge(df_sets.drop(columns=["n_shared"]),
                                on="dimension", how="left")

        print("\n[per-label] multi-value dimensions split into binary present/absent "
              "variables, macro-averaged over subcategories:")
        print(macro.to_string(index=False))
        weak = (df_labels[(df_labels["n_a"] + df_labels["n_b"]) >= 3]
                .dropna(subset=["krippendorff_alpha"])
                .nsmallest(10, "krippendorff_alpha"))
        if not weak.empty:
            print("\n[per-label] weakest subcategories (alpha, at least 3 uses):")
            print(weak[["dimension", "category", "n_a", "n_b", "n_both",
                        "positive_agreement", "krippendorff_alpha"]].to_string(index=False))

    csv_path = shared_folder / "icr_goldstandard.csv"
    md_path = shared_folder / "icr_goldstandard.md"
    label_csv_path = shared_folder / "icr_by_label.csv"
    df_icr.to_csv(csv_path, index=False)
    if not df_labels.empty:
        df_labels.to_csv(label_csv_path, index=False)
    header = f"# Goldstandard Intercoder Reliability ({a_name} vs {b_name})\n\n"
    gate_line = (f"Research-software gate: {len(confirmed)} papers confirmed by both coders"
                 f" (ICR computed over these); {len(vetoed)} vetoed by one coder")
    if gate is not None:
        gate_line += (f"; gate agreement {gate['raw_agreement']} over "
                      f"{gate['n_both_decided']} jointly-decided papers")
    body = header + gate_line + ".\n\n## Per dimension (multi-value cells as sets)\n\n"
    body += df_icr.to_markdown(index=False) + "\n"
    if not df_labels.empty:
        body += ("\n## Multi-value dimensions, one binary variable per subcategory\n\n"
                 "Each subcategory is scored as present/absent, so partial overlap is "
                 "priced fairly and the disagreement is localised to the category. "
                 "`positive_agreement` is the specific agreement on presence "
                 "(2*both / (a+b)), which stays informative for rare categories, where "
                 "the shared absences that dominate raw agreement carry no information. "
                 "Macro averages weigh every subcategory equally.\n\n")
        body += macro.to_markdown(index=False) + "\n\n### Per subcategory\n\n"
        body += df_labels.to_markdown(index=False) + "\n"
    md_path.write_text(body, encoding="utf-8")
    print(f"\nSaved: {csv_path}\nSaved: {md_path}")
    if not df_labels.empty:
        print(f"Saved: {label_csv_path}")


if __name__ == "__main__":
    main()
