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

Only papers/dimensions coded by BOTH coders are included (pairwise complete).

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

try:
    import krippendorff
except ImportError:  # pragma: no cover
    krippendorff = None

try:
    from sklearn.metrics import cohen_kappa_score
except ImportError:  # pragma: no cover
    cohen_kappa_score = None


def load_coders(shared_folder: Path) -> dict[str, pd.DataFrame]:
    coders = {}
    for f in sorted(shared_folder.glob("coding_*.csv")):
        username = f.stem.replace("coding_", "")
        try:
            coders[username] = pd.read_csv(f, dtype={"id": str})
        except pd.errors.EmptyDataError:
            continue
    return coders


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

    rows = []
    for dim in cat.DIMENSIONS:
        res = compute_dimension_icr(a, b, dim)
        if res is not None:
            rows.append(res)

    if not rows:
        raise SystemExit("No overlapping coded papers between the two coders yet.")

    df_icr = pd.DataFrame(rows)
    print(df_icr.to_string(index=False))

    csv_path = shared_folder / "icr_goldstandard.csv"
    md_path = shared_folder / "icr_goldstandard.md"
    df_icr.to_csv(csv_path, index=False)
    header = f"# Goldstandard Intercoder Reliability ({a_name} vs {b_name})\n\n"
    md_path.write_text(header + df_icr.to_markdown(index=False), encoding="utf-8")
    print(f"\nSaved: {csv_path}\nSaved: {md_path}")


if __name__ == "__main__":
    main()
