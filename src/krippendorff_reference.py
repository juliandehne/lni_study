"""
krippendorff_reference.py

A *pure*, inspectable reference implementation of Krippendorff's alpha
(nominal level of measurement) for the two-coder case used in this study,
plus a **differential verification** harness that checks it against the
external ``krippendorff`` library on random reliability data.

Why this file exists
--------------------
``compute_icr.compute_dimension_icr`` computes alpha by calling the
``krippendorff`` library over a pandas pipeline. Symbolic formula-inference
tools (SymPy, latexify, AST rendering) cannot recover the closed-form maths
from that code, because it flows through a third-party library call and
dataframe operations rather than scalar arithmetic on the parameters.

So we mark the closed form here as ``@functional`` on ``alpha_from_matrix``:
a small, pure, side-effect-free kernel that the rse_annotations runner can
render a formula for and that Fable can propose test stubs for. The heavier
``alpha_nominal`` wrapper builds the coincidence matrix (still pure, but with
a loop) and delegates the actual ratio to that kernel.

"Coder verification" here has a double meaning that the study cares about:
  1. verifying agreement *between human coders* (that is what alpha measures), and
  2. verifying the *code* that measures it -- by differentially checking this
     transparent reference against the trusted library. If they disagree on
     random data, one of them is wrong; agreement is evidence both are right.

Definition (nominal alpha)
--------------------------
Over a coincidence matrix ``o`` (o[c][k] = number of coincidences of values
c and k across all units), with marginals ``n_c = sum_k o[c][k]`` and grand
total ``n = sum_c n_c``:

    D_o = sum_c ( o[c][c] * (1 - o[c][c] / n_c) )        # unused; see below
    alpha = 1 - D_o / D_e

For the *nominal* metric, with the nominal difference function
(delta = 0 when the two values are equal, 1 otherwise):

    D_o = n - A                       # observed disagreement mass
    D_e = (n^2 - B) / (n - 1)         # expected disagreement mass
    alpha = 1 - D_o / D_e
          = 1 - (n - 1) * (n - A) / (n^2 - B)

with  A = sum_c o[c][c]   (observed diagonal agreement mass)
      B = sum_c n_c^2      (sum of squared marginals)
      n = grand total of the coincidence matrix.

``alpha_from_matrix`` implements exactly that last line as pure scalar
arithmetic over (A, B, n) so the formula backends can print it.

Run it::

    python src/krippendorff_reference.py            # self-check vs the library
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rse_annotations_shim import functional, mapping  # noqa: E402


@functional
def alpha_from_matrix(A: float, B: float, n: float) -> float:
    """Nominal Krippendorff alpha reduced to scalar arithmetic.

    This is the closed form the formula-inference backends can render:
    ``alpha = 1 - (n - 1) * (n - A) / (n**2 - B)``.

    :param A: observed diagonal agreement mass (sum of coincidence diagonal).
    :param B: sum of squared value marginals (sum_c n_c**2).
    :param n: grand total of the coincidence matrix.
    :returns: the nominal alpha coefficient.
    """
    return 1.0 - (n - 1.0) * (n - A) / (n ** 2 - B)


@mapping(fields={
    "reliability_data": "coders x units matrix of nominal codes (np.nan = missing)",
})
def coincidence_stats(reliability_data: np.ndarray) -> tuple[float, float, float]:
    """Build the (A, B, n) coincidence statistics for nominal alpha.

    Pure: no I/O, depends only on its argument. Missing values (np.nan) are
    pairwise-excluded per unit, exactly as Krippendorff's alpha requires.

    :param reliability_data: array shaped (n_coders, n_units) of integer codes,
        with ``np.nan`` marking a coder that did not code that unit.
    :returns: the (A, B, n) triple consumed by :func:`alpha_from_matrix`.
    """
    data = np.asarray(reliability_data, dtype=float)
    n_coders, n_units = data.shape

    # Collect the set of distinct values actually used.
    finite = data[np.isfinite(data)]
    values = sorted(set(finite.tolist()))
    index = {v: i for i, v in enumerate(values)}
    V = len(values)

    o = np.zeros((V, V), dtype=float)
    for u in range(n_units):
        col = data[:, u]
        present = col[np.isfinite(col)]
        m_u = len(present)
        if m_u < 2:
            continue  # a unit coded by <2 coders contributes nothing
        # Each ordered pair (i != j) contributes 1/(m_u - 1) to the matrix.
        for ci in range(len(present)):
            for cj in range(len(present)):
                if ci == cj:
                    continue
                a = index[present[ci]]
                b = index[present[cj]]
                o[a][b] += 1.0 / (m_u - 1.0)

    marginals = o.sum(axis=1)          # n_c per value
    n = float(marginals.sum())          # grand total
    A = float(np.trace(o))              # sum_c o[c][c]
    B = float((marginals ** 2).sum())   # sum_c n_c^2
    return A, B, n


def alpha_nominal(reliability_data: np.ndarray) -> float:
    """End-to-end nominal alpha: coincidence stats -> closed-form ratio.

    Thin, pure composition of :func:`coincidence_stats` and
    :func:`alpha_from_matrix`. Kept un-annotated because it is just glue; the
    two annotated kernels carry the meaning.
    """
    A, B, n = coincidence_stats(reliability_data)
    if n ** 2 - B == 0:      # all coders always agree on a single value
        return 1.0
    return alpha_from_matrix(A, B, n)


# --------------------------------------------------------------------------- #
# Differential verification against the trusted `krippendorff` library.
# --------------------------------------------------------------------------- #

def _library_alpha(reliability_data: np.ndarray):
    try:
        import krippendorff
    except ImportError:
        return None
    try:
        return float(krippendorff.alpha(
            reliability_data=reliability_data, level_of_measurement="nominal"))
    except (ValueError, ZeroDivisionError):
        return None


def verify_against_library(trials: int = 200, seed: int = 12345,
                           tol: float = 1e-9) -> dict:
    """Compare :func:`alpha_nominal` to the ``krippendorff`` library.

    Generates random two-coder nominal reliability matrices (with some missing
    entries) and asserts both implementations agree within ``tol``. This is the
    "coder verification" of the code itself -- if the transparent reference and
    the trusted library disagree on random data, the closed form is wrong.

    :param trials: number of random matrices to test.
    :param seed: RNG seed (kept fixed so the check is reproducible).
    :param tol: absolute tolerance for agreement.
    :returns: summary dict with pass/fail counts and the worst observed delta.
    """
    rng = np.random.default_rng(seed)
    checked = skipped = 0
    worst = 0.0
    failures = []

    for t in range(trials):
        n_units = int(rng.integers(4, 20))
        n_vals = int(rng.integers(2, 5))
        data = rng.integers(0, n_vals, size=(2, n_units)).astype(float)
        # Punch some holes so the pairwise-missing logic is exercised.
        mask = rng.random((2, n_units)) < 0.15
        data[mask] = np.nan
        # Keep units with >=2 coders; otherwise the library rejects the matrix.
        keep = np.isfinite(data).sum(axis=0) >= 2
        data = data[:, keep]
        if data.shape[1] < 2 or np.unique(data[np.isfinite(data)]).size < 2:
            skipped += 1
            continue

        lib = _library_alpha(data)
        if lib is None:
            skipped += 1
            continue
        mine = alpha_nominal(data)
        delta = abs(mine - lib)
        worst = max(worst, delta)
        checked += 1
        if delta > tol:
            failures.append({"trial": t, "mine": mine, "library": lib, "delta": delta})

    return {
        "checked": checked,
        "skipped": skipped,
        "failures": failures,
        "worst_delta": worst,
        "ok": not failures and checked > 0,
    }


def main() -> None:
    result = verify_against_library()
    print("Krippendorff nominal alpha -- differential verification")
    print(f"  closed form: alpha = 1 - (n - 1) * (n - A) / (n**2 - B)")
    print(f"  trials checked : {result['checked']}")
    print(f"  trials skipped : {result['skipped']} (degenerate / library-rejected)")
    print(f"  worst |delta|  : {result['worst_delta']:.3e}")
    if result["ok"]:
        print("  RESULT: PASS -- reference matches the krippendorff library.")
    elif result["checked"] == 0:
        print("  RESULT: INCONCLUSIVE -- krippendorff library not installed.")
    else:
        print(f"  RESULT: FAIL -- {len(result['failures'])} disagreement(s):")
        for f in result["failures"][:5]:
            print(f"    trial {f['trial']}: mine={f['mine']:.6f} "
                  f"lib={f['library']:.6f} delta={f['delta']:.2e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
