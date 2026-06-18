# LNI RSE-Typology Study — Task Breakdown (resumable)

This file reframes the complex study (see `../pub_rse_classification/notes.md`) as
discrete subtasks, so work can be resumed after an interruption. It mirrors the
16 steps in the notes. Status legend: ✅ done · 🔜 next · ⬜ todo.

**Study goal:** Build a typology of Research Software Engineering (RSE) in
CS-related research, limited to LNI (Lecture Notes in Informatics) publications
for availability/legal-access reasons. Target venue: ICSE 2027.

**Pipeline lineage:** This study reuses the DeLFI annotation pipeline from
`../rse-elearning-evaluation` (SAIA API client, rate limiter, JSON parsing,
checkpoint/resume, PDF text extraction, majority-vote aggregation, ICR metrics).

---

## Phase A — Machine annotation bootstrap (notes 1–7)

- ✅ **1. Reuse the SAIA annotation pipeline.** Studied
  `rse-elearning-evaluation/experiments/experiments/experiments.py`. Ported the
  `RateLimiter`, `extract_json_from_response`, classify loop, and checkpoint/
  resume logic into `src/annotate_lni.py`. Vendored `pdf_text_extraction.py`
  (already LNI-aware) into `src/`.
- ✅ **2. Working definition of RSE.** Adapted from DeLFI `prompt_template_1.md`
  into `RSE_DEFINITION` in `src/categories.py`. Used as the gate
  (`label_research_software`).
- ✅ **3. Startup annotation script.** `src/annotate_lni.py` takes
  `--lni_folder` + SAIA token (env or `--saia_token`) and runs in IntelliJ/CLI.
- ✅ **4. Typology categories with seed subcategories.** `TYPOLOGY` in
  `src/categories.py`: `research_position`, `methodology`, `software_type`,
  `techstack` — each with seed subcategories as examples. Injected into the
  prompt (`prompts/rse_typology_prompt_v1.md`).
- ✅ **5. Certainty + new-category suggestions.** Prompt asks for per-dimension
  `certainty` (0–1) and a `new_suggestion` when no seed fits.
- ✅ **6. Typology only if research software == 1.** Prompt sets `typology: null`
  when the gate is 0; `build_goldstandard.py` only iterates gate==1 papers.
- 🔜 **7. Bootstrap until ~100 papers with new suggestions.** RUN the annotator
  over the corpus and watch the cumulative counter printed at the end of
  `annotate_lni.py` (also `results/new_category_suggestions_*.csv`). Stop when
  ~100 distinct papers have produced new-subcategory suggestions, then move to
  Phase A2. **Blocked on:** a valid SAIA token (`.env` `SAIA_API_KEY` or
  `--saia_token`; endpoint defaults to KISSKI, no need to set it).
  Sampling is **stratified by LNI volume folder** (`src/sampling.py`): `--test`
  (= 5) and `--sample N` draw a proportional, largest-remainder sample across the
  volumes (lni37/lni52/lni132/lni169/lni273/lni308/lni338), so a small sample is
  balanced across the corpus rather than concentrated in one volume. The stratum
  is the **top-level `lni*` folder** even when PDFs nest in subfolders. Reproducible
  via `--shuffle_seed` (default 42). Full runs still use the deterministic
  cross-volume shuffle (`--no_shuffle` to disable).

## Local working copy (slow corpus → fast disc) — NEW

The full corpus is on a **slow mounted disc**; the human-annotation cycles open
the same PDFs repeatedly. So the sampled PDFs are copied once to a local,
gitignored `.workingset/` and every step after the draw runs against that fast
copy. The full corpus is read only **twice**: at sample-draw time and for the
final full-corpus annotation (Phase C).

- ✅ **W1. Materialize the samples.** `src/prepare_workingset.py` draws a
  stratified sample and copies the PDFs (preserving their path under the corpus
  root, so paper ids + volume strata are unchanged) into `.workingset/<name>/`,
  with a `manifest.csv`. Idempotent/resumable.
  - Narrowing set (50): `--name narrow --sample 50`.
  - Goldstandard set (100, **disjoint** from narrowing):
    `--name gold --sample 100 --exclude .workingset/narrow/manifest.csv`.
  All later steps point their folder argument at `.workingset/narrow` or
  `.workingset/gold` instead of the slow corpus.

## Phase A2 — Subcategory narrowing (notes step 7b) — NEW

Between the bootstrap and the goldstandard, a human narrows the typology so the
coders aren't chasing an ever-growing list of model-suggested subcategories.
Runs against the local `.workingset/narrow` copy (Phase A is run on those 50
papers first to produce the suggestions).

- ✅ **7b-i. Stratified 50-paper candidate collection.** `src/narrow_categories.py
  --mode collect --corpus <CORPUS> --sample 50`: draws a stratified 50-paper sample
  (volumes as strata, same principle as step 7) and aggregates the candidate
  subcategories per dimension — the seed categories plus every distinct
  `new_suggestion` the models produced for those papers (with frequency + example
  ids/rationales). By default it **reuses the Phase A checkpoints** (no token);
  `--annotate_missing` annotates sampled papers not yet in a checkpoint via SAIA.
  Output: `results/category_candidates_<corpus>.csv`.
- ✅ **7b-ii. Human accept/decline + explanation CLI.** `narrow_categories.py
  --mode review`: for each dimension and candidate, the coder chooses
  **[a]ccept / [d]ecline / [b]ack / [f]orward / [s]kip / [q]uit** and gives a
  free-text **explanation** (why keep / why drop / what to use instead). The
  candidates are flattened into one navigable list so `[b]ack`/`[f]orward` step
  between them (and re-decide earlier calls). Resumable (saves after each
  decision). Output: the explicative white/blacklist `prompts/category_whitelist.json`.
- ✅ **7b-iii. White/blacklist feeds the goldstandard creation.** The curated
  guidance is consumed in TWO places (single source: `categories.py`): it is
  injected into the annotation prompt as `{category_guidance_block}`
  (`render_category_guidance_block`), and it is shown to the human coders inside
  `build_goldstandard.py` (whitelist = prefer / blacklist = avoid, with
  explanations). Until the file exists both degrade to no-ops, so the rest of the
  pipeline is unchanged.

**End of A2 → enriched re-annotation.** Once the white/blacklist exists, the
goldstandard sample is annotated by re-running Phase A on the gold working copy
(`annotate_lni.py --lni_folder .workingset/gold`): the LLMs are now queried with
the **enriched prompt** that carries the curated white/blacklist guidance
(`{category_guidance_block}`). This is a single-pass annotation per paper (not an
iterative LLM loop) — the "iteration" is the staged, human-triggered re-run with
the narrowed scheme. The enriched guidance likewise applies to the Phase C
full-corpus annotation. The human coders in Phase B then validate this enriched
annotation against the same white/blacklist.

## Phase B — Goldstandard creation (notes 8–12)

- ✅ **8/9. Interactive coding script.** `src/build_goldstandard.py`: **needs PDFs
  only, no token** — it reads the Phase A annotation CSV (auto-discovered from the
  folder name in `results/checkpoints/`, or pass `--annotations`). Per gate==1
  paper and dimension it shows model category + certainty + suggested new category,
  opens the PDF in the browser, and lets the coder accept/replace/add a category
  (with a confirm step for spelling). Token map: Phase A = PDFs+token, Phase B =
  PDFs only, Phase C = PDFs+token.
- ✅ **10. Two-coder support.** `--username` + shared `goldstandard/` folder. New
  categories accepted by the other coder are surfaced as choices
  (`other_coder_suggestions`). Each coder writes `goldstandard/coding_<user>.csv`.
- ✅ **11. Shared results + reuse flag.** Decisions go to the shared CSV with an
  `is_new` flag (whether the chosen category was a newly-introduced one).
- ✅ **12. Intercoder reliability.** `src/compute_icr.py` merges the two coder
  files and reports Krippendorff's alpha (nominal), Cohen's kappa, and raw
  agreement per dimension → `goldstandard/icr_goldstandard.{csv,md}`.
- ✅ **11b. Top-up to keep the goldstandard at target.** `src/topup_goldstandard.py`
  (pipeline step `topup`, run AFTER a `gold` pass): separates the coder's human-confirmed
  (rs=1) papers from the rejected (rs=0) into `goldstandard/gold_human_{confirmed,rejected}_
  <coder>.csv`, then refills `.workingset/gold_confirmed` to `target + #rejected` LLM-positives
  (`target` bumped +20 once confirmations come within 10 of it) by re-invoking
  `confirm_positives.py` — so the coder can still reach ~100 *human-confirmed* RSE papers.
  `build_goldstandard.py` resumes at the first undecided paper, landing the coder on the
  freshly added papers. Token spent only to annotate new pool papers, and only when given.
- ✅ **11c. Coder-coined categories become schema groundtruth.** When a coder invents a
  new subcategory during coding, the other coder is unlikely to guess the same name — so it
  would read as a pure disagreement and never enter the typology. Pipeline step `synccats`
  (`src/sync_coder_categories.py`) lifts every `is_new` category out of `coding_<coder>.csv`
  and merges it into `prompts/category_schema.yaml` `active` as groundtruth
  (`source: coder:<names>`); `build_goldstandard.py` captures a one-line human description at
  coding time into a `new_categories_<coder>.csv` sidecar so the merged category is immediately
  renderable (an undescribed active entry stays excluded by `categories.py`'s forcing function).
  **`gold` auto-runs `synccats` first**, so each coder's session starts from a knowledge base
  that already holds the other coders' new categories. `--bucket candidates` routes them through
  the `review` inbox instead; `--dry_run` previews. Offline-verified via a synthetic two-coder
  fixture (collect/dedup/dry-run/merge/idempotency + the render-vs-exclude check), real schema
  untouched. **12. ICR** (`compute_icr.py`) is restricted to papers BOTH coders gate rs=1.
- ✅ **11d. `i`=insufficient-information coding option.** In `build_goldstandard.py` a coder can
  press `i` at a dimension to record the reserved `categories.INSUFFICIENT_INFO`
  (`"insufficient_information"`) answer — "the paper does not contain enough information to code
  this category". It writes a real row and counts in ICR as a nominal label (both coders marking
  it = agreement), unlike `s`=skip which leaves the dimension undecided (no row, excluded from
  ICR). The sentinel is reserved (`is_new` always False), so it is never written to the
  new-category sidecar nor synced into the schema (`sync_coder_categories` skips it defensively).
  Offline-verified (prompt → sentinel, save/load round-trip as a string, sync ignores it, ICR
  scores it as nominal).
- ✅ **11e. Short-paper cap on the pool + top-up draw (≤20% short, <6 pages).** The rule lives in
  one module, `src/paper_length.py` (`SHORT_PAGE_THRESHOLD=6`, `MAX_SHORT_FRACTION=0.20`,
  `is_short`/`short_allowed`/`fraction_ok`/`order_within_cap`). **Pooling:** `select_candidates.py`
  counts each candidate's pages (PyMuPDF, cached in a new `pages` column of the score cache /
  manifest) and, while filling the `pool` set, skips a short paper whenever placing it would push
  the running short ratio over the cap (`short_allowed`), then asserts the final manifest with
  `fraction_ok`. **Topping off:** `confirm_positives.py` reorders the pool overflow with
  `order_within_cap` so the LLM-confirmed draw is itself ≤20% short; `topup_goldstandard.py` and
  `run_pipeline.cmd` (`SHORT_PAGES`/`MAX_SHORT_FRAC` config vars) forward the thresholds. Capped
  set is `pool` by default; `--short_cap_sets pool,gold` extends it. Offline-verified end-to-end via
  `tests/test_short_paper_cap.py` (23 checks: pure invariants, 300 randomized `order_within_cap`
  trials, PyMuPDF page counting, and a real `select_candidates` subprocess run on a synthetic
  40-short/40-long corpus — no SAIA token, no real corpus).
- 🔜 **Run B:** Have two coders run `build_goldstandard.py`, then `compute_icr.py`.
  Iterate the seed categories in `categories.py` to fold in agreed new
  subcategories before the full-corpus run.

## Phase C — Full corpus annotation + analysis (notes 13–15)

- ⬜ **13. Annotate the whole corpus with the finalized goldstandard categories.**
  Once `categories.py` reflects the consolidated subcategories, re-run
  `annotate_lni.py` across the full corpus with **3 models** (mirror DeLFI:
  e.g. mistral, llama, gemma) × repeated runs, then apply **majority voting** to
  pick final labels. *Reuse* the intra/inter aggregation approach from
  `rse-elearning-evaluation/analysis/label_aggregation/`. New code needed:
  `src/aggregate_labels.py` (port of `label_aggregation_inter_LLM.py`, adapted to
  the categorical typology rather than the DeLFI binary/ordinal labels).
- ⬜ **14. Descriptive statistics.** `src/descriptive_stats.py`: distribution of
  RSE categories across the corpus (counts/percentages per dimension and
  subcategory), with emphasis on the *position in the research process*
  dimension. Output CSV + markdown tables.
- ⬜ **15. Method chapter.** Grow `METHOD.md` into the paper's method section.
  Emphasize the `research_position` dimension per the notes. Already scaffolded.

## Phase D — Housekeeping

- ⬜ Confirm corpus location & licensing. PDFs currently live in
  `../rse-elearning-evaluation/data/data/lni*` (volumes lni37, lni52, lni132,
  lni169, lni273, lni308, lni338). Decide the canonical corpus path and whether
  `year` can be recovered per volume (annotate_lni currently leaves `year` blank
  because folder names are LNI volume numbers, not years).
- ⬜ Decide whether to vendor `pdf_text_extraction.py` (current choice, for a
  self-contained repo) or import it from the sibling submodule.
- ✅ **Paper-id is collision-free.** The id is the PDF's path relative to the
  corpus/working root, minus `.pdf` (e.g. `lni132/SimpleArchiveFormat/item_10/125`),
  computed in one place (`sampling.paper_id`) and used by `annotate_lni.py`,
  `narrow_categories.py` and `prepare_workingset.py`. This avoids collisions when
  several volumes export PDFs under an identical DSpace `SimpleArchiveFormat/item_N/`
  tree, and — because the working copy preserves the relative path — the id is
  identical on the full corpus and the local copy. `annotate_lni` also stores the
  `rel_path` so `build_goldstandard.py` can reopen PDFs nested in subfolders.
- ⬜ First commit of the `lni_study` submodule + bump the parent pointer.

---

## Stepwise testing protocol (coder runs everything; no token/PDF access shared)

The corpus folder and SAIA token stay on the coder's machine. Each step produces a
small, shareable artifact (derived metadata only, no paper body) to verify before
spending API quota.

1. `cd publications/lni_study`; `pip install -r requirements.txt` (Python313 cmd).
2. **Step 0 — offline dry run (NO token):**
   `python src/annotate_lni.py --lni_folder <CORPUS> --test --dry_run`
   → share `results/extraction_report_<vol>.csv` + `results/sample_prompt_<vol>.txt`.
   Verifies PDF extraction quality + the exact prompt. Self-tested on lni132: 5/5 ok.
3. Copy `.env.example` → `.env`, add the SAIA token.
4. **Step 1 — 5-paper live test:**
   `python src/annotate_lni.py --lni_folder <CORPUS> --test`
   → share `results/checkpoints/annotations_<tag>_checkpoint.csv` (5 rows) to verify
   JSON parsing, labels, certainties, and new-category suggestions.
5. **Step 2 — scale up** per volume; watch the cumulative new-suggestions counter
   (notes step 7, ~100 papers). Then Phase B (goldstandard) and Phase C.
