# Code annotations (rse_code_annotations testbed)

This branch (`feat/rse-code-annotations`) uses `lni_study` as a **testbed** for the
[`rse_code_annotations`](../rse_code_annotations) framework: role annotations for
(generated) code plus an interactive tool that helps review the maths and scaffold
tests.

The framework is a **normal, locally-installed Python library**. All the logic —
the decorators, the checks, formula inference, the differential-verification
harness, and the command-line tool — lives in the library. This project only
(a) imports the four decorators and (b) supplies a couple of domain-specific
pieces (I/O fixtures and a Krippendorff reference). There is no shim and no
vendored copy of the framework in this repo.

## Install the framework (local, editable)

From the `lni_study` repo root:

```bash
pip install -e ../rse_code_annotations               # decorators + tool
pip install -e "../rse_code_annotations[formula]"    # + SymPy/latexify formula inference
```

This makes `from rse_annotations import ...` importable, so `src/compute_icr.py` and
`src/krippendorff_reference.py` import the decorators directly, and exposes the
tool as `python -m rse_annotations.cli` (no PATH setup needed).

## What is annotated

| Function | File | Annotation | Meaning |
| --- | --- | --- | --- |
| `load_coders` | `src/compute_icr.py` | `@data_input` | reads the `coding_*.csv` coder files |
| `encode_nominal` | `src/compute_icr.py` | `@mapping` | category strings → integer codes |
| `compute_dimension_icr` | `src/compute_icr.py` | `@mapping` | coder frames → per-dimension ICR metrics |
| `write_icr_outputs` | `src/compute_icr.py` | `@data_output` | writes `icr_goldstandard.csv` / `.md` |
| `alpha_from_matrix` | `src/krippendorff_reference.py` | `@functional` | pure closed-form nominal Krippendorff α |
| `coincidence_stats` | `src/krippendorff_reference.py` | `@mapping` | reliability matrix → (A, B, n) |

The Krippendorff computation in `compute_dimension_icr` runs through the external
`krippendorff` library over a pandas pipeline, so symbolic tools cannot recover its
formula from that code. The transparent closed form therefore lives in
`src/krippendorff_reference.py` as a pure `@functional`, whose formula the tool
**infers and prints**, and which is **differentially verified** against the library.

## Run the tool

The tool ships with the installed library and is invoked with
`python -m rse_annotations.cli` (this needs nothing on your PATH). Point it at the
**repo root** — it walks every `*.py` file in every folder, imports each so its
decorators register, and shows a two-option menu. From the `lni_study` repo root:

```bash
python -m rse_annotations.cli .            # scan the whole repo, interactive menu
python -m rse_annotations.cli . --inspect  # straight to Option 1 (inspect @functional)
python -m rse_annotations.cli . --stubs    # straight to Option 2 (generate test stubs)
```

(You can still scan a single subtree by passing its path, e.g. `... src`.)

**Option 1 — Inspect `@functional` annotations.** Each `@functional` (here
`alpha_from_matrix`) is shown with its source and **inferred formula**; you accept
or decline it, and the verdicts are written to `inspection.yaml` (in the scanned
root). The α formula is rendered for inspection, e.g.

```
alpha = 1 - (n - 1) * (n - A) / (n**2 - B)
```

**Option 2 — Generate unit-test stubs.** A `pytest` stub is generated per annotation
from its per-kind pattern (determinism + expected-value for `@functional`, shape
transform for `@mapping`, `tmp_path` read/write for `@data_input`/`@data_output`),
written to `tests/test_<module>.py` (under the scanned root, per Python convention).
Every body calls `pytest.skip(...)` so nothing passes until you fill it in.

### Differential verification of the Krippendorff reference

The reference implementation is checked against the trusted `krippendorff` library
on random reliability matrices. The *harness* is framework logic
(`rse_annotations.differential_check`); this project supplies only the reference
callable and the random-matrix generator. Run it standalone:

```bash
python src/krippendorff_reference.py
# -> differential check PASS -- 200 checked, 0 skipped, worst |delta| ~1e-16
```

## Formula inference vs. formal verification

Symbolic backends recover a closed form only for *scalar arithmetic on the parameters*.
They cannot infer α straight from `compute_dimension_icr` (it flows through a library
call + dataframes). Formal verifiers (Dafny/Why3/Coq/CBMC) *check code against a spec*
— they do not *infer* the formula either. The honest pipeline is therefore: isolate the
maths as a pure `@functional`, let the tool render its formula for human inspection,
and pin correctness by differential testing against a trusted implementation. See
[`../rse_code_annotations/FORMULA_INFERENCE.md`](../rse_code_annotations/FORMULA_INFERENCE.md)
for the full landscape.
