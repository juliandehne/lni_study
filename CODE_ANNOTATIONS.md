# Code annotations (rse_code_annotations testbed)

This branch (`feat/rse-code-annotations`) uses `lni_study` as a **testbed** for the
[`rse_code_annotations`](../rse_code_annotations) framework: role annotations for
(generated) code plus a runner that checks they hold and helps review the maths.

The framework is a **normal, locally-installed Python library**. All the logic —
the decorators, the checks, formula inference, the differential-verification
harness, and the command-line runner — lives in the library. This project only
(a) imports the four decorators and (b) supplies a couple of domain-specific
pieces (I/O fixtures and a Krippendorff reference). There is no shim and no
vendored copy of the framework in this repo.

## Install the framework (local, editable)

From the `lni_study` repo root:

```bash
pip install -e ../rse_code_annotations               # decorators + runner + CLI
pip install -e "../rse_code_annotations[formula]"    # + SymPy/latexify formula inference
pip install -e "../rse_code_annotations[formula,fable]"  # + Fable-assisted test stubs
```

This installs the `rse-annotations` console command and makes `from rse_annotations
import ...` importable, so `src/compute_icr.py` and `src/krippendorff_reference.py`
import the decorators directly.

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
`src/krippendorff_reference.py` as a pure `@functional`, whose formula the runner
**infers and prints**, and which is **differentially verified** against the library.

## Run the checker

The runner is the library's console command. From the `lni_study` repo root:

```bash
rse-annotations run compute_icr krippendorff_reference \
    --path src --fixtures annotation_fixtures:FIXTURES

rse-annotations run compute_icr krippendorff_reference --path src --json     # machine-readable
rse-annotations run compute_icr krippendorff_reference --path src --no-stubs # snippet-only, no Fable
```

`--path src` adds the project's source root to `sys.path` so the top-level modules
(`compute_icr`, `krippendorff_reference`, and their `annotation_fixtures`) are
importable by name. Fable stub generation runs when `ANTHROPIC_API_KEY` is set and
the `fable` extra is installed; pass `--no-stubs` to skip it entirely.

The runner:
1. checks every annotation is placed correctly (`@functional` is pure; `@data_input`
   reads; `@data_output` writes), that docstrings document the declared fields, and
   invokes the boundary functions in a sandbox to confirm real I/O
   (fixtures in `src/annotation_fixtures.py`);
2. prints each `@functional`'s source as a review snippet and **infers its formula**
   with three backends (AST rendering, SymPy symbolic execution, latexify) — this is
   where Krippendorff's α is rendered for inspection, e.g.

   ```
   alpha = 1 - (n - 1) * (n - A) / (n**2 - B)
   ```

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
maths as a pure `@functional`, let the runner render its formula for human inspection,
and pin correctness by differential testing against a trusted implementation. See
[`../rse_code_annotations/FORMULA_INFERENCE.md`](../rse_code_annotations/FORMULA_INFERENCE.md)
for the full landscape.
