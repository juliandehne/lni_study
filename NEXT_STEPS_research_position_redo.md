# Next steps — re-run fill-gold for `research_position` (uncoded papers)

> **⏸ AWAITING USER OK (recorded 2026-06-25).** The research_position workflow is
> COMPLETE — fill-gold (step 3) ran and re-populated `research_position` for the
> uncoded RSE rows under the updated schema (checkpoint mtime recent, cells filled).
> `src/deprecate_research_position.py` is now committed-to-be in the repo.
>
> **Remaining release housekeeping — DO NOT run until the user gives the OK after
> their working day (and only if no parallel work is in flight):**
> 1. Clean up / condense this notes file into a short "completed" record.
> 2. `git` commit the milestone, then create annotated tag **`v0.1`** (on `main`;
>    HEAD was `0d0916e`; no tags exist yet).
>
> **OPEN DECISION blocking the commit — ask/confirm scope:** commit the ENTIRE
> current working tree, or ONLY the research_position task files?
>   - Clearly ours: `prompts/category_schema.yaml`,
>     `results/checkpoints/…checkpoint.csv`,
>     `results/new_category_suggestions_…csv`, new `src/deprecate_research_position.py`.
>   - Modified but NOT from this task: `run_pipeline.cmd`, `src/pipeline_menu.py`,
>     `goldstandard/coding_alice.csv`.
>   - Ambiguous untracked: `prompts/.schema_work/`, `results/prompt_preview.txt`.


_2026-06-23: deprecation APPLIED (step 2 done). Only the token-blocked fill-gold
re-run (step 3) remains._

_2026-06-24 (recovery verification): on-disk state CONFIRMED against this note.
Current checkpoint (156 rows): all 126 uncoded rows have `research_position_category`
blank; all 30 coded rows still filled (0 blank). 70 RSE uncoded rows retain
`software_lifecycle`/`software_type` (70/70) — only research_position was cleared.
The 20:34 checkpoint touch did NOT re-fill research_position. fill-gold mechanism
verified wired: `run_pipeline.cmd` maps `absent-only` → `--absent-only`, implemented
in `src/annotate_lni.py`. NOTHING is broken — step 3 is purely token-blocked (needs
a live SAIA token + paid API call). NOT yet run._

## Goal
After updating the `research_position` descriptions in `prompts/category_schema.yaml`
(datenanalyse etc. now require an explicitly named overarching research goal,
otherwise product/proof-of-concept), re-query **only** the `research_position`
dimension for the **not-yet-coded** papers — without churning the other
dimensions or the human-coded baseline.

## State so far
- ✅ `prompts/category_schema.yaml` updated (dimension `question` + `datenanalyse`
  description). Saved, parses under ruamel.
- ✅ **Deprecation APPLIED 2026-06-23.** Ran
  `C:\Users\julian.dehne\.claude\jobs\6fdfa53b\tmp\deprecate_research_position.py --apply`.
  Backed the checkpoint up to `…_checkpoint.csv.predeprecate-bak`, then blanked the
  four `research_position_*` columns for **70 uncoded RSE rows**. **30 coded RSE rows
  left intact** (human baseline / ICR not churned). Other dimensions untouched
  (verified: software_lifecycle 70/70, software_type 70/70 still present on the
  uncoded rows). The backups make NO difference to "coded": the union across all
  `coding_*.csv` (incl. backups) is exactly the same 30 ids as the current two coding
  files — so the open question below is moot for this data.
- ⏸️ **REMAINING (token-blocked):** step 3 — re-run `fill-gold … absent-only` so the
  70 blanked `research_position` cells get re-queried under the updated schema.

## Mechanism (verified in src/annotate_lni.py)
- fill-gold = `annotate_lni.py --fill-missing`. A dimension is refilled when its
  `<dim>_category` cell is blank (`_missing_dims`, `_is_blank`).
- Default regime: **uncoded** papers get a FULL refresh (all dims); **coded**
  papers get absent-only. `--absent-only` holds EVERYONE to absent-only.
- "Coded" = id present in any `goldstandard/coding_*.csv` `id` column
  (`_coded_paper_ids`, globs backups too — the script matches this exactly).

## Plan to resume
1. **Dry run** (prints counts, writes nothing):
   ```
   C:\Users\julian.dehne\AppData\Local\Programs\Python\Python313\python.exe \
     C:\Users\julian.dehne\.claude\jobs\6fdfa53b\tmp\deprecate_research_position.py
   ```
   Review: # RSE rows, # uncoded target rows, # with a non-blank category to clear,
   # coded RSE rows left intact.
2. **Apply** (backs up checkpoint to `*.predeprecate-bak`, then blanks the 4
   `research_position_*` cols for uncoded RSE rows):
   ```
   ...python.exe ...\deprecate_research_position.py --apply
   ```
   Target checkpoint:
   `results/checkpoints/annotations_goldconfirm_mistral-large-3-675b-instruct-2512_rse_typology_prompt_v1_run_1_checkpoint.csv`
3. **Re-run fill-gold in absent-only mode** so ONLY the blanked research_position
   gets re-queried (other dims preserved):
   ```
   run_pipeline.cmd fill-gold <SAIA_TOKEN> absent-only
   ```
   (Costs one targeted SAIA call per uncoded RSE paper.)

## Why `absent-only` and not plain fill-gold
Plain fill-gold full-refreshes ALL dimensions for uncoded papers (re-costs &
re-churns software_lifecycle/type/techstack/evaluation). We only want
research_position redone → blank just that dim, then absent-only fills just it.

## Open question to confirm on resume
- Decide whether "uncoded" should include the `coding_*.backup-*.csv` files
  (the script currently does, matching `_coded_paper_ids`). If those backups
  should NOT count as coded, narrow the glob in the script.
