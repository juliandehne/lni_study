# Code annotations (rse_code_annotations testbed)

This branch (`feat/rse-code-annotations`) uses `lni_study` as a **testbed** for the
[`rse_code_annotations`](../rse_code_annotations) framework: role annotations for
(generated) code plus a runner that checks they hold and helps review the maths.

The dependency is deliberately **optional**. `src/rse_annotations_shim.py` imports the
real decorators when the framework is importable (installed, or found in the sibling
submodule checkout) and otherwise falls back to **no-op** decorators — so the pipeline
runs unchanged with or without it. Nothing in the main pipeline breaks if the framework
is absent.

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

From the `lni_study` repo root:

```bash
python check_annotations.py          # text report + Krippendorff verification
python check_annotations.py --json   # machine-readable
python check_annotations.py --stubs  # also ask Fable for pytest stubs (needs ANTHROPIC_API_KEY)
```

On Windows you can use `check_annotations.cmd` instead.

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

3. runs the **differential verification** of the reference implementation against the
   `krippendorff` library on random reliability matrices (worst |Δ| ≈ 1e-16).

## Formula inference vs. formal verification

Symbolic backends recover a closed form only for *scalar arithmetic on the parameters*.
They cannot infer α straight from `compute_dimension_icr` (it flows through a library
call + dataframes). Formal verifiers (Dafny/Why3/Coq/CBMC) *check code against a spec*
— they do not *infer* the formula either. The honest pipeline is therefore: isolate the
maths as a pure `@functional`, let the runner render its formula for human inspection,
and pin correctness by differential testing against a trusted implementation. See
[`../rse_code_annotations/FORMULA_INFERENCE.md`](../rse_code_annotations/FORMULA_INFERENCE.md)
for the full landscape.
