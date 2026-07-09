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

Usage (from the lni_study repo root):
    python src/compute_icr.py --shared_folder goldstandard

Output:
    goldstandard/icr_goldstandard.csv
    goldstandard/icr_goldstandard.md
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
from rse_annotations_shim import (  # noqa: E402
    data_input,
    data_output,
    mapping,
)

try:
    import krippendorff
except ImportError:  # pragma: no cover
    krippendorff = None

try:
    from sklearn.metrics import cohen_kappa_score
except ImportError:  # pragma: no cover
    cohen_kappa_score = None


@data_input(fields={
    "shared_folder": "goldstandard directory scanned for coding_*.csv coder files",
    "coders": "username -> parsed decision DataFrame (one per coder file read)",
})
def load_coders(shared_folder: Path) -> dict[str, pd.DataFrame]:
    """Read every ``coding_<username>.csv`` in the goldstandard folder.

    :param shared_folder: directory holding the per-coder decision CSVs.
    :returns coders: mapping of username to the coder's decision DataFrame.
    """
    coders = {}
    for f in sorted(shared_folder.glob("coding_*.csv")):
        username = f.stem.replace("coding_", "")
        try:
            coders[username] = pd.read_csv(f, dtype={"id": str})
        except pd.errors.EmptyDataError:
            continue
    return coders


@mapping(fields={
    "values": "categorical label Series (final_category strings) to encode",
    "codes": "integer code array aligned with values (NaN-preserving)",
    "code_map": "category string -> integer code lookup used for the encoding",
})
def encode_nominal(values: pd.Series) -> tuple[np.ndarray, dict]:
    """Map category strings to integer codes for ICR libraries.

    :param values: nominal category labels as a pandas Series.
    :returns codes: numpy integer codes; also returns the code_map used.
    """
    cats = sorted(set(values.dropna().astype(str)))
    code_map = {c: i for i, c in enumerate(cats)}
    return values.astype(str).map(code_map).to_numpy(), code_map


@mapping(fields={
    "a": "coder A's decisions (id, dimension, final_category)",
    "b": "coder B's decisions (id, dimension, final_category)",
    "dim": "the typology dimension to compute reliability for",
})
def compute_dimension_icr(a: pd.DataFrame, b: pd.DataFrame, dim: str) -> dict | None:
    """Compute ICR for one dimension between two coders on shared paper ids.

    Not @functional: the Krippendorff alpha itself flows through the external
    ``krippendorff`` library over a pandas pipeline, so the closed-form maths
    is not recoverable from this code by symbolic inference. The pure,
    inspectable formula lives in ``krippendorff_reference.alpha_nominal`` and is
    differentially verified against this library call.

    :param a: coder A decisions. :param b: coder B decisions. :param dim: dimension.
    :returns: per-dimension metrics dict, or None when the coders share no ids.
    """
    a_dim = a[a["dimension"] == dim].set_index("id")["final_category"]
    b_dim = b[b["dimension"] == dim].set_index("id")["final_category"]
    shared = a_dim.index.intersection(b_dim.index)
    if len(shared) == 0:
        return None

    pair = pd.DataFrame({"a": a_dim.loc[shared].astype(str),
                         "b": b_dim.loc[shared].astype(str)})
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


@data_output(fields={
    "df_icr": "per-dimension ICR metrics table to persist",
    "shared_folder": "goldstandard directory the outputs are written into",
    "a_name": "first coder's username (report header)",
    "b_name": "second coder's username (report header)",
    "confirmed": "paper ids both coders confirmed as research software",
    "vetoed": "paper ids one coder vetoed",
    "gate": "research-software gate agreement summary (or None)",
})
def write_icr_outputs(df_icr, shared_folder: Path, a_name, b_name,
                      confirmed, vetoed, gate) -> tuple[Path, Path]:
    """Write the ICR table to ``icr_goldstandard.csv`` and a markdown report.

    :param df_icr: the metrics table. :param shared_folder: output directory.
    :param a_name: coder A. :param b_name: coder B. :param confirmed: confirmed ids.
    :param vetoed: vetoed ids. :param gate: gate-agreement summary.
    :returns: the (csv_path, md_path) pair that was written.
    """
    csv_path = shared_folder / "icr_goldstandard.csv"
    md_path = shared_folder / "icr_goldstandard.md"
    df_icr.to_csv(csv_path, index=False)
    header = f"# Goldstandard Intercoder Reliability ({a_name} vs {b_name})\n\n"
    gate_line = (f"Research-software gate: {len(confirmed)} papers confirmed by both coders"
                 f" (ICR computed over these); {len(vetoed)} vetoed by one coder")
    if gate is not None:
        gate_line += (f"; gate agreement {gate['raw_agreement']} over "
                      f"{gate['n_both_decided']} jointly-decided papers")
    md_path.write_text(header + gate_line + ".\n\n" + df_icr.to_markdown(index=False),
                       encoding="utf-8")
    return csv_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute goldstandard intercoder reliability.")
    parser.add_argument(
        "--shared_folder",
        default=str(
            (Path(os.environ.get("LNI_DATA_ROOT") or Path(__file__).resolve().parent.parent)
             / "goldstandard").resolve()))
    args = parser.parse_args()

    shared_folder = Path(args.shared_folder).resolve()
    print(f"[config] goldstandard: {shared_folder}  "
          f"(reads coding_*.csv, writes icr_goldstandard.csv/.md)")
    coders = load_coders(shared_folder)
    if len(coders) < 2:
        raise SystemExit(f"Need >=2 coder files in {shared_folder}, found {len(coders)}: "
                         f"{list(coders)}")

    names = list(coders)
    if len(names) > 2:
        print(f"Note: {len(names)} coders found; computing ICR for the first two: {names[:2]}")
    a_name, b_name = names[0], names[1]
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

    csv_path, md_path = write_icr_outputs(
        df_icr, shared_folder, a_name, b_name, confirmed, vetoed, gate)
    print(f"\nSaved: {csv_path}\nSaved: {md_path}")


if __name__ == "__main__":
    main()
