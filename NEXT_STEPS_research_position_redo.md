# research_position re-coding — COMPLETED (tagged v0.1)

_Closed 2026-06-25. Kept as a short record; no pending steps._

## What was done
1. **Schema tightened** — `prompts/category_schema.yaml`, dimension
   `research_position`: the `question` and the `datenanalyse` description now state
   (succinct German) that the process categories (Datenerhebung, Datenanalyse,
   Simulation/Modellierung, Mensch-zugewandte Intervention, Visualisierung/
   Dissemination) apply only when the software serves an **explicitly named
   overarching research goal** — not merely because it technically could. If the
   process culminates in the software itself, it is `product_result` /
   `proof_of_concept_product`.
2. **Deprecated stale suggestions** — `src/deprecate_research_position.py --apply`
   blanked the four `research_position_*` columns for the 70 uncoded RSE rows in the
   goldconfirm checkpoint (30 coded rows left intact; other dimensions untouched).
   The script is committed for reproducibility.
3. **Re-ran fill-gold** (`absent-only`) — re-queried only `research_position` for the
   uncoded RSE rows under the updated schema; cells re-populated.

## Mechanism reference (src/annotate_lni.py)
- fill-gold = `annotate_lni.py --fill-missing`; a dimension is refilled when its
  `<dim>_category` cell is blank (`_missing_dims` / `_is_blank`).
- `--absent-only` holds every paper to gap-fill (only blank cells), so blanking one
  dimension and re-running re-queries just that dimension.
- "Coded" = id in any `goldstandard/coding_*.csv` (`_coded_paper_ids`).
