# Intercoder Reliability: Alice vs. Bob — where they code most differently

Comparison of the two coders (`goldstandard/coding_alice.csv` vs `goldstandard/coding_bob.csv`)
on the papers they both coded, joined on `(id, dimension)`. Multi-value cells
(semicolon-separated) are compared as sets; "exact agreement" = identical category set.

> Note: `goldstandard/icr_goldstandard.csv` compares a *backup vs. alice*, **not**
> the two coders. This report is the true Alice-vs-Bob comparison.

## Per-dimension agreement (lowest = most divergent)

| Dimension | n shared | Exact agreement |
|---|---|---|
| **evaluation** | 17 | **0.18** ← most divergent |
| **software_lifecycle** | 17 | **0.24** |
| **research_position** | 17 | **0.29** |
| software_type | 17 | 0.47 |
| techstack | 17 | 0.53 |
| label_research_software (gate) | 24 | 0.88 |

The research-software **gate** is solid. Everything downstream of it diverges — three
dimensions are below 30% exact agreement.

## Subcategories driving the disagreement

### evaluation (worst)
Bob defaults to generic **`testing`**; Alice splits it into finer buckets.
- Alice `benchmarking` → Bob `testing` (3×)
- Alice `performance_evaluation` → Bob `testing` (2×)
- `benchmarking`, `usability_study`, `performance_evaluation` disagree ~100% of appearances.
- **Granularity conflict.**

### software_lifecycle
Systematic **scope** difference — Bob adds early phases Alice omits.
- `projektdefinition` disagrees 91%, `anforderungen` 83%.
- Dominant pattern (4×): Alice `<none>` | Bob `anforderungen;projektdefinition`.
- They agree on `implementierung` (0.18), `entwurf` (0.14), `testen_qualitaetssicherung` (0.17).

### research_position
Disagreement on what the software is *for*. `product_result` disagrees 100%.
- Alice `product_result` → Bob `visualisierung_dissemination` (3×), `human_facing_intervention` (2×), `research_infrastructure_support` (2×).
- Alice → generic "product/result"; Bob → specific functional roles.

### software_type
`middleware_service` (100%) and `conceptual` (100%) are the friction points.
Alice often multi-labels (e.g. `middleware_service;plugin_extension`) where Bob gives `<none>` or `conceptual`.

### techstack (best substantive dimension)
Friction is **`insufficient_information`** (67% disagree) and **`java_jvm`** (100%).
Alice marks `insufficient_information`; Bob extracts a concrete stack (Java/C++/Python).

## Summary

Alice and Bob agree on *whether* something is research software, but diverge on *how to
characterize it*. Two recurring mechanisms:
1. **Granularity** — Alice uses finer categories (evaluation, software_type) where Bob lumps.
2. **Scope/inference** — Bob infers more (early lifecycle phases, concrete tech stacks) where
   Alice stays conservative (`<none>`, `insufficient_information`).

Reproduce with: `tmp/compare.py` logic — join on `(id, dimension)`, compare `final_category`
as semicolon-split sets, report per-dimension exact agreement and per-category symmetric-difference rates.
