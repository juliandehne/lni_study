# lni_study — task log

_Last updated: 2026-06-18. This file is the durable, on-disk progress record for
the lni_study pipeline (see the `task-logging` / `recover-work` skills). It has a
**State** snapshot (overwritten each update) and an **append-only Log** (newest
first, never edited)._

## State  (current snapshot — overwrite each update)

- **Now / in flight:** nothing running. **NEW short-paper cap added & offline-verified 2026-06-18**
  (see top Log entry): the `pool` reservoir AND the `confirm` top-up drawn from it are now held to
  **<=20% short papers (<6 pages)** via the new `src/paper_length.py` rule — `select_candidates`
  skips over-quota shorts while filling the pool (asserting `fraction_ok` at the end), and
  `confirm_positives` reorders the pool draw with `order_within_cap` so every top-up prefix stays
  capped; `topup_goldstandard` + `run_pipeline.cmd` (`SHORT_PAGES`/`MAX_SHORT_FRAC`) forward it.
  Verified by `tests/test_short_paper_cap.py` (23 checks incl. an end-to-end synthetic-corpus run,
  no token); a live run against the real corpus is NOT yet exercised. Still uncommitted. **NEW
  `i`=insufficient-information coder option added & offline-verified 2026-06-18** (see Log entry): a coder can press `i` at a dimension to
  record the reserved `categories.INSUFFICIENT_INFO` answer ("paper doesn't say enough to code
  this") — a REAL coded row that counts in ICR as a nominal label, distinct from `s`=skip (no
  row, undecided). Never synced as a new category. Offline-verified; the interactive prompt is
  NOT yet exercised in a real terminal. Still uncommitted. **`synccats` step + `gold`
  auto-extension added & offline-verified 2026-06-18** (see Log): coder-coined (is_new) categories are now
  merged into `prompts/category_schema.yaml` `active` as groundtruth (`source: coder:<names>`),
  with a one-line human description captured at coding time into `new_categories_<coder>.csv`;
  `gold` auto-runs `synccats` first so each coder starts from a schema that already holds the
  other coders' new categories (closing the disagreement-by-default gap that would also depress
  ICR). Offline-verified via a synthetic two-coder fixture (collect, dedup, dry-run, real merge,
  idempotency, and the `categories.py` render/exclude forcing function), real schema untouched;
  the interactive description prompt and a live `gold` cycle are NOT yet verified. Still
  uncommitted. **`topup` step added & offline-verified
  2026-06-18** (see Log): after a `gold` pass it separates human-confirmed (rs=1)
  papers from rejected (rs=0) into `goldstandard/gold_human_{confirmed,rejected}_<coder>.csv`,
  then refills `.workingset/gold_confirmed` to `%GOLD% + #rejected` (target bumped +20 when
  confirmations come within 10 of the goal) by re-invoking `confirm`. `build_goldstandard`
  now resumes at the first undecided paper so re-running `gold` lands on the freshly added
  papers. Offline-verified (py_compile + synthetic dry-run + bump-math); a live token refill
  and the interactive resume jump are NOT yet verified. Still uncommitted. — The earlier
  **RSE-human-check feature in `build_goldstandard.py` was RECOVERED & unit-verified 2026-06-18**
  (see 2nd Log entry):
  the gold session now has a human RS-boolean gate (reject cascades to skip dimensions),
  forward/back/goto navigation, and full-rewrite resumable persistence. Compiles + save/load
  round-trip tested offline; the interactive loop and a live end-to-end gold run are NOT yet
  verified. The typology now has **5 dimensions** (added `evaluation`). Still uncommitted in
  the `lni_study` repo. **RESOLVED 2026-06-18** (see top Log entry): `compute_icr` now
  restricts ICR to papers BOTH coders gated rs=1 (a single rs=0 vetoes the paper out of
  every dimension), and reports the research-software gate agreement separately. — Earlier
  state below is unchanged:
  **`a-gold` is COMPLETE** (verified 2026-06-17,
  no crash). All 100 `.workingset\gold` papers annotated with the enriched (whitelist)
  prompt: 100 PDFs / 100 manifest rows / 100 checkpoint rows, all consistent. Labels:
  60 label=1, 39 label=0. **1 straggler**: `lni52/GI.-.Proceedings.52-53.pdf` failed
  with `pdf_extraction_failed` (empty label) — NOT an API/rate-limit error.
  **Gotcha:** a plain `a-gold` re-run will NOT retry it — `annotate_lni.py:611-619`
  builds `done_ids` from the `id` column ignoring error status, so the errored id is
  skipped forever. To re-attempt: delete that one row from the gold checkpoint first,
  OR use the new `a-gold <token> overwrite` (archives the whole checkpoint → fresh run,
  see Log 2026-06-17 `--overwrite`). NOTE: `--overwrite` re-attempts lni52 too, but the
  failure is DETERMINISTIC (no short-paper fallback was added), so it fails the same way.
  DIAGNOSED 2026-06-17 (no token): it is a GENUINE 2-page German paper (paper #53 of
  vol.52; `52-NN` = volume-paper numbering, NOT a whole-volume bundle), score 4.0.
  PDF is fine — `extract_text_from_pdf` yields 4288 clean chars, text is NOT flagged
  corrupted. The failure is entirely in `extract_main_content` (`pdf_text_extraction.py:206`),
  which returns None: this short paper has none of the section anchors it keys on
  (no numbered/standalone Einleitung/Introduction, no `Abstract:`/`Zusammenfassung:`,
  no `Keywords:`), so it falls through all 6 priorities. That flips `extraction_failed`
  (`annotate_lni.py:193`). **DETERMINISTIC** → re-running `a-gold` with a token will
  NOT fix it. Real options: (a) DROP it → gold = 99 clean papers; or (b) add a
  "priority 6" short-paper fallback to `extract_main_content` (return raw body when no
  anchor found but text non-empty & non-corrupt — also helps future short papers in
  narrow/final), then re-annotate just this one paper (delete its checkpoint row first).
  The earlier `Minute limit reached (10/min). Waiting ~3 s...`
  console lines were the **client-side `RateLimiter`** (`annotate_lni.py:90`, 10/min +
  200/h) working as designed — not an error.
  (An interrupted edit to the review CLI — explicit `[f]orward` navigation — was
  recovered & reconciled on 2026-06-16; see the Log. Code consistent, docs updated.)
  The old `estimate` process (PID 20484) has **finished** (no python running; score cache stopped growing at
  15:38, 1800 papers scored). Working sets are filled and **consistent** (manifest
  rows == PDFs on disk): narrow 50 / gold 100 / final 500 / pool 779. The pipeline
  was reworked into a **streaming estimator** that fills the working sets directly,
  plus an optional **LLM-confirm** step replacing the old `a-candidates` + `filter` pair.

- **Done & verified:**
  - `run_pipeline.cmd` is internally consistent — every `goto` resolves, and the
    `estimate` / `confirm` / `full` calls match the current Python arg surfaces
    (verified by grepping goto targets ↔ labels and reading each call site).
  - **`--overwrite` for `a-gold`** (recovered 2026-06-17, see Log): `annotate_lni.py`
    `--overwrite` flag + `run_pipeline.cmd :a_gold` 3rd-arg wiring. py_compile OK,
    `--help` shows the flag, cmd arg/token order verified. NOT run live (needs token).

- **Done, unverified (NOT run end-to-end against the real corpus or SAIA API):**
  - `src/select_candidates.py` — **rewritten** to stream: `enumerate_volumes`
    (cheap per-volume PDF count) → `folder_weighted_order` draw → score-and-fill
    `narrow (50) → gold (100) → final (FULL_N) → pool (rest, up to --cap)` in
    order, with an append-as-you-go score cache `results/rse_scores_<corpus>.csv`
    so an interrupted scan resumes without re-extracting. New args:
    `--min_score --narrow --gold --final --cap --seed --rescore --list_only`.
    **Dropped:** `--name --sample --select --min_pool`.
  - `src/sampling.py` — **added** `folder_weighted_order(groups, seed)`: orders
    all PDFs so a streaming pass is folder-balanced (each PDF equally likely,
    every volume represented from the start), deterministic, stoppable early.
  - `src/confirm_positives.py` — **NEW** `confirm` step: batched annotate (50) +
    keep `label_research_software==1`, topping up from `pool` until `--target`
    confirmed → `.workingset/<set>_confirmed/manifest.csv`. Resumable via
    `results/checkpoints/`. Merges old `a-candidates` + `filter`.
  - `run_pipeline.cmd` — **migrated**: header, dispatch table, all step bodies.
    New step order: `deps | dry | test | estimate | manifests | confirm | advance |
    collect | review | a-gold | gold | icr | full`. Removed `a-candidates`,
    `filter`, `ws-narrow`, `ws-gold` (estimate fills those sets directly).
  - **Category schema is the SOURCE OF TRUTH** (`prompts/category_schema.yaml`):
    `categories.py` → `schema_io.py` (ruamel round-trip) derive the prompt from it;
    `category_whitelist.json` + the JSON review CLI are RETIRED. Per dimension:
    `active` / `rejected` / pre-seeded empty `candidates: []`. The narrowing LOOP
    (grounded-theory theoretical sampling): `advance` (confirm next 50, **token**) →
    `collect --to_schema` (mine + append candidates, no token) → `review`/hand-edit
    the YAML (no token) → repeat until **saturation** (~0 new candidates for ~2
    rounds) → lock → `a-gold`/`gold`. All machinery verified OFFLINE only — see the
    2026-06-17 Log entry "category schema is now the SOURCE OF TRUTH" for exactly
    what was/wasn't run.

- **Next (in order):**
  1. **Smoke-test the streaming rewrite** (no token, no slow mount): tiny fake
     corpus of a few volume folders; assert `estimate` fills
     narrow→gold→final→pool in order, respects `--cap`, and the score cache makes
     a re-run skip extraction. Confirm `folder_weighted_order` is reproducible and
     spans folders. **The streaming rewrite has NO tests yet.**
  2. **Run `estimate` on the real corpus** (`Z:\Publikationen\LNI\Proceedings`):
     `run_pipeline.cmd estimate` — the one-time heavy pass over the slow mount;
     stops early once sets + pool are full; scores cache for re-runs.
  3. **Tune `--min_score`** (default 2.0): open `results/rse_scores_<corpus>.csv`,
     eyeball high/low scorers (DE *and* EN), adjust the gate and/or weights in
     `rse_estimator.py`. Re-run `estimate` (cached / instant unless `--rescore`).
     Watch per-set `SHORT` warnings (gate too high or `--cap` too low).
  4. **Run the narrowing LOOP until saturation** (theoretical sampling): one command
     per round — `run_pipeline.cmd round <token> "" "" rN` chains `advance` (token;
     confirm next 50) → `collect --to_schema` (no token; mine + append candidates to
     the YAML) → `review` / hand-edit (no token; fill descriptions, resolve
     `pending_restructuring`, promote candidates). The three stages are also exposed
     individually (`advance`/`collect`/`review`) for re-runs. Stop when a round adds
     ~0 new candidates (~2 dry rounds). FIRST live use of the loop — all machinery is
     so far OFFLINE-verified only. Also work the `pending_restructuring`
     backlog: add `middleware_service`, rename `perl_web`→`perl` and
     `hdl_hardware_description`→`hardware_description_languages`, and fill the 10
     empty `source:added` descriptions (categories.py warns about these on load).
  5. **Lock the typology**, then **`confirm --set gold --target 100`** (token) →
     **`a-gold` → `gold` → `icr`**.
  6. **`full`** per model (`run_1`, then `run_2`/`run_3` with other models) for the
     majority vote. `.workingset/final` is reused across models (no re-selection).

- **Blocked / open questions:**
  - **`min_score = 2.0`** is the new default (was 1.0) — decide the real threshold
    after step 3 by reading the score distribution.
  - **`cap = 2000`** — is `narrow+gold+final + pool` large enough that `confirm`
    never runs the pool dry? If `confirm` warns it ran out before `--target`,
    raise `--cap` or lower `--min_score` and re-run `estimate` (cached, fast).
  - ~~**`collect` annotation reuse:** verify `narrow_categories.py --mode collect`
    reads `confirm`'s checkpoint.~~ **RESOLVED 2026-06-16:** it does. `collect`
    globs `annotations_*_checkpoint.csv` (matches confirm's
    `annotations_narrowconfirm_..._checkpoint.csv`) and keys on `paper_id` =
    corpus-relative path (matches the manifest id `select_candidates` writes). The
    "Phase A checkpoints" wording in collect's output is stale labelling only.
    **Required order: `confirm --set narrow` BEFORE `collect`** — collect makes no
    LLM calls itself; it only reuses confirm's annotations.
  - **Estimator weights/patterns** in `rse_estimator.py` are still a first cut.
  - **Optional:** wire `mupdf_warning_summary()` into `annotate_lni.py`'s end-of-run log.
  - **Superseded / now unused:** `src/filter_positives.py` and
    `prepare_workingset.py --restrict` are no longer wired in (their job moved to
    `select_candidates` + `confirm_positives`). Decide whether to delete.
  - **Retired, not deleted:** `prompts/category_whitelist.json` is no longer the
    system of record (the YAML schema is). Confirm with the user before deleting it,
    and grep for any lingering reader first.
  - **Not committed:** `publications` is a submodule with local changes — decide
    when to commit.

## Log  (APPEND-ONLY — newest entry at the top, never edit past entries)

### 2026-06-18 — short-paper cap: pool + top-up draw held to <=20% short (<6 pages)
- **What & why.** Short papers (<6 pages: abstracts, posters, front-matter — e.g. the 2-page
  `lni52/GI.-.Proceedings.52-53.pdf` straggler) lack the section anchors the extractor and the
  human coders rely on, so a goldstandard dominated by them is hard to code. New constraint: at
  most **20% of the `pool` reservoir AND of the `confirm` top-up drawn from it** may be short.
- **New module `src/paper_length.py`** — the single source of the rule. Constants
  `SHORT_PAGE_THRESHOLD = 6`, `MAX_SHORT_FRACTION = 0.20`; `page_count()` (wraps
  `pdf_text_extraction.get_page_count`, None on a broken PDF); `is_short()` (None/unknown =>
  NOT short — an unmeasurable paper is not charged against the quota; 6 pages is NOT short);
  `short_allowed(n_short, n_total)` = `(n_short+1) <= frac*(n_total+1)` — a RUNNING invariant
  that keeps `short/total <= frac` after every accepted paper, so the cap holds at ANY final set
  size (even a corpus exhausted before target); `fraction_ok()`, `short_fraction()`,
  `order_within_cap()` (stable two-queue interleave; emits a short only when `short_allowed`,
  drops nothing).
- **`select_candidates.py` (pooling).** Added a `pages` column to the score cache + every
  manifest (page count computed once at extract time, cached, recovered lazily for old caches).
  The streaming gate now SKIPS an over-quota short positive for a capped set and keeps scanning
  (leaving the set possibly short of target rather than over-quota short). New flags
  `--short_pages` / `--max_short_frac` / `--short_cap_sets` (default `pool`). Final per-set
  `assert fraction_ok(...)` guards the invariant; the run reports skipped shorts + per-set short%.
- **`confirm_positives.py` (topping off).** The pool overflow is reordered with
  `order_within_cap` before the draw, so whatever prefix the top-up stops at stays <=20% short
  (the named `--set` itself is left untouched — the cap is scoped to the pool it draws from).
  New `--short_pages` / `--max_short_frac`; `topup_goldstandard.py` forwards both to `confirm`.
- **`run_pipeline.cmd`.** New `SHORT_PAGES=6` / `MAX_SHORT_FRAC=0.20` config vars wired into the
  `estimate`, `manifests`, `confirm`, and `topup` steps.
- **Verified (offline, NO token):** `tests/test_short_paper_cap.py` — 23 checks, all pass.
  Pure invariants; 300 randomized `order_within_cap` trials on <=20%-short input (every prefix
  capped, length-preserving) + over-cap degenerate inputs (nothing dropped); PyMuPDF
  `page_count` on synthesized PDFs; and an END-TO-END `select_candidates` run on a synthetic
  40-short/40-long corpus -> pool = 49 papers, **9 short (18%)**, 31 over-quota shorts skipped,
  assertion held with the corpus exhausted before target. NOT yet exercised: a live run against
  the real corpus/`confirm` (no token spent). Still uncommitted.
- **Scope note.** The cap is on `pool` only (the request: "the pool"). narrow/gold/final are
  uncapped; pass `--short_cap_sets pool,gold` (or wire it in the .cmd) to extend it to `gold`.

### 2026-06-18 — `i`=insufficient-information coder option (reserved sentinel, NOT skip)
- **What & why.** A coder needs to record "the paper does not contain enough information to
  code this dimension" as a real ANSWER — distinct from skipping the dimension. New reserved
  category `categories.INSUFFICIENT_INFO = "insufficient_information"` (a CSV-safe descriptive
  string, deliberately NOT the literal "NaN", which pandas would coerce to a missing value). In
  the goldstandard coding flow the coder presses **`i`** at a dimension to assign it.
- **Semantics.** `i`=insufficient writes a row and counts in ICR as a nominal label (two coders
  both marking it AGREE; one marks it / the other codes a real category = disagreement). This is
  intentionally different from `s`=skip, which returns nav 'skip' and writes NO row (the
  dimension stays undecided and is excluded from ICR as pairwise-incomplete). Because the
  sentinel is reserved, `is_new` is always False, so it is never recorded to the
  `new_categories_<coder>.csv` sidecar nor synced into the schema as a coder-coined category.
- **How.**
  - `categories.py`: new `INSUFFICIENT_INFO` constant + `is_reserved_category(value)` helper
    (single source of truth).
  - `build_goldstandard.py`: `prompt_decision` gains an `'i'` branch returning
    `(cat.INSUFFICIENT_INFO, False, None)`; menu text + module/function docstrings updated;
    `is_new_category` now counts the sentinel among `known` (never new).
  - `sync_coder_categories.py`: `collect_coder_categories` defensively skips any
    `is_reserved_category` token, so even a sentinel row wrongly flagged `is_new` can never be
    lifted into the schema.
  - `compute_icr.py`: unchanged — it already treats `final_category` as a nominal label, so the
    sentinel participates correctly.
- **Verified OFFLINE (no token, no TTY, no corpus):** `py_compile` of the 4 touched/related
  modules; a synthetic test asserted: `prompt_decision('i')` returns the sentinel with
  `is_new=False`/`nav=None` and is not treated as `new`; `save_decisions`→`load_decisions`
  round-trips the sentinel as a STRING (not NaN-coerced) with `is_new=False`; `sync` skips a
  sentinel row even when marked `is_new=True` while still collecting a genuinely-new category;
  and `compute_dimension_icr` scores both-insufficient as raw_agreement 1.0 and
  one-insufficient-vs-real as 0.0. **NOT verified:** the interactive prompt in a real terminal.
- **Not committed:** still uncommitted in the `lni_study` repo (commit only on request).

### 2026-06-18 — coder-coined categories merged into the schema as groundtruth (`synccats`; `gold` auto-extends)
- **What & why.** When one coder advances further during coding and INVENTS a new
  subcategory (a name the seed list and the other coder did not offer), the other coder is
  extremely unlikely to independently guess the same category AND the same name — so it would
  otherwise register as a pure disagreement in `compute_icr` and the typology would never
  accumulate the coders' findings. New step **`synccats`** lifts every coder-created (is_new)
  category out of the coding files and merges it into the SINGLE SOURCE OF TRUTH
  (`prompts/category_schema.yaml`) as **active groundtruth**, so the next coder (and the model)
  sees it as a first-class category.
- **How.**
  - `src/sync_coder_categories.py` (NEW): `collect_coder_categories(shared)` reads every
    `coding_<coder>.csv`, keeps `is_new==True` rows (RS-gate rows are is_new=False so they
    never leak), splits multi-value (techstack) `final_category` on ';', and returns
    `{dim: {key: {coders, count}}}`. `load_sidecar_descriptions(shared)` reads the optional
    `new_categories_<coder>.csv` sidecars for human one-line definitions.
    `merge_coder_categories_into_schema(shared, bucket="active", dry_run, schema_path)` appends
    each genuinely-new key to `dimensions.<dim>.active` as
    `{key, source: "coder:<names>", description: <sidecar or "">}`, deduped against the
    dimension's active/rejected/candidate keys AND the alias (`examples`) names — mirrors
    `narrow_categories.merge_candidates_into_schema`. `--bucket candidates` routes them through
    the normal `review` inbox instead of trusting them directly; `--dry_run` reports without
    writing. Default target is `active` ("as groundtruth", the intent).
  - `src/build_goldstandard.py`: when a coder applies a new category, `record_new_category(...)`
    now prompts once for a one-line description and persists it to a per-coder
    `new_categories_<coder>.csv` sidecar (cols `dimension,key,description,coder`). This supplies
    the human DEFINITION so the merged category is immediately usable — an active entry with an
    EMPTY description is excluded from the model prompt (the existing `categories.py` forcing
    function) until one is written.
  - `run_pipeline.cmd`: new `synccats` dispatch + step body; **`gold` now auto-runs `synccats`
    first** (the "gold step needs an extension that includes the other coders' input into the
    knowledge base" ask) so each session starts from a schema that already contains the other
    coders' new categories. Header REM + usage updated.
- **Provenance, not silent trust.** Merged entries carry `source: "coder:<names>"` so a curator
  can see exactly which coder(s) coined each one and reconcile in the YAML.
- **Verified OFFLINE (no token, no TTY, no corpus):** `py_compile` of both changed scripts; a
  synthetic two-coder fixture (alice+bob both coin `NEW_A` with a sidecar description; bob alone
  coins `NEW_B` with NO description; alice also "uses" an existing seed key that must be ignored)
  asserted: collect returns exactly `{NEW_A, NEW_B}` with the right coder sets, the existing seed
  does NOT leak in, `--dry_run` writes nothing, the real merge adds `NEW_A` (described,
  `source: coder:alice,bob`) and `NEW_B` (empty desc, `source: coder:bob`) to `active` without
  duplicating the seed, a second merge is idempotent (adds nothing), and `categories.py` loading
  the merged temp schema RENDERS `NEW_A` while EXCLUDING+warning on the undescribed `NEW_B`. All
  GREEN; the real `prompts/category_schema.yaml` was untouched (test merged against a temp copy
  via the `schema_path` param). **NOT verified:** the interactive description-capture prompt in a
  real terminal, and a live `gold`→`synccats`→`gold` cycle with real coder CSVs.
- **Not committed:** still uncommitted in the `lni_study` repo (commit only on request).

### 2026-06-18 — `compute_icr` restricted to the human-confirmed goldstandard (RS veto)
- **What & why.** ICR must describe only papers that actually contain research software.
  `src/compute_icr.py` now includes a paper in the dimension reliability **only when BOTH
  coders set the research-software gate to rs=1**; a single rs=0 from either coder is a
  **veto** that removes the paper from every dimension. This resolves the prior open design
  call ("`compute_icr` does NOT yet score the human RS gate").
- **How.** New helpers `confirmed_rs_ids(state_a, state_b)` (returns `confirmed` = both rs=1,
  `vetoed` = one rs=1/other rs=0) and `gate_agreement(...)` (raw agreement over papers both
  coders decided). `main()` loads each coder's `coding_<name>.csv` via
  `build_goldstandard.load_decisions`, computes `confirmed`/`vetoed`, filters both coder
  dataframes to `confirmed` ids **before** the dimension loop, and exits early if no paper is
  both-confirmed. The gate is reported separately (console + a line in `icr_goldstandard.md`),
  NOT as a typology dimension. RS_DIM rows never enter the dimension loop (not in
  `cat.DIMENSIONS`).
- **Verified (offline).** `py_compile` + a synthetic two-coder fixture: P1/P2 both rs=1
  (kept), P3 rs=1 vs rs=0 (vetoed, excluded), P4 both rs=0 (gate-only). Asserted
  `confirmed={P1,P2}`, `vetoed={P3}`, gate agreement 0.75 over 4 jointly-decided papers, and
  end-to-end `n_shared==2` on every dimension (P3 absent), eval raw_agreement 0.5,
  research_position 1.0, plus the gate line in the `.md`. NOT yet run on real coder data
  (only one coder file exists so far). Still uncommitted in the `lni_study` repo.

### 2026-06-18 — new `topup` step: separate human-confirmed from rejected + refill the gold set
- **What & why.** After a `gold` coding pass the human rejects some LLM-confirmed papers
  (rs=0), which shrinks the usable goldstandard below the target. New step **`topup`**
  (`src/topup_goldstandard.py` + `run_pipeline.cmd :topup`, dispatch + header + usage)
  runs AFTER `gold` and:
  1. reads `goldstandard/coding_<coder>.csv` via `build_goldstandard.load_decisions`,
     **partitions** confirmed (rs=1) / rejected (rs=0) / uncoded, and writes two shareable
     CSVs: `gold_human_confirmed_<coder>.csv` (one row per confirmed paper WITH its full
     per-dimension typology coding — the actual goldstandard slice) and
     `gold_human_rejected_<coder>.csv`.
  2. computes `effective_target = bump(target=%GOLD%)` — grown by **+20** each time the
     human-confirmed count comes within **10** of it (so as confirmations approach e.g.
     90/100 the goal becomes 120, making it likely enough real-RSE papers are found), then
     `confirm_target = effective_target + #rejected`.
  3. tops `.workingset/gold_confirmed` up to `confirm_target` by invoking
     `confirm_positives.py --set gold --target <confirm_target>` — which is cumulative +
     cached, so it only annotates NEW `pool` papers and appends them to the SAME
     `goldconfirm` checkpoint the `gold` step reads.
- **Resume-aware (the "continue where the coder came" ask).** `build_goldstandard.run_session`
  now **starts at the first undecided paper** (rs is None) instead of paper 1, so after a
  top-up appends fresh papers to the end of the worklist, re-running `gold` lands the coder
  directly on the new ones (earlier papers still reachable via p/g).
- **Token discipline.** The top-up only spends SAIA quota when a token is resolved AND
  `--dry_run` is not set; otherwise it just writes the separation CSVs and PRINTS the exact
  `confirm` command (token value redacted as `<TOKEN>`). The `:topup` cmd step passes the
  token only when one is resolved, same as the other token steps.
- **Verified OFFLINE (no token, no live API):** py_compile of both changed scripts; a dry-run
  over synthetic fixtures (90 confirmed / 30 rejected / 120 LLM-confirmed) produced the right
  partition counts, the +20 bump (→120), `confirm_target=150`, `need=30`, and the redacted
  command; the prompt-template default resolves to `rse_typology_prompt_v1.md` (so the refill
  appends to the same checkpoint `gold` reads); the no-bump and already-enough (need≤0) branches
  and 6 bump-math edge cases all pass. **NOT verified:** a live token refill end-to-end, and the
  interactive resume jump in a real terminal.
- **Still open (unchanged):** `compute_icr.py` does not score the human RS gate. Still
  uncommitted in the `lni_study` repo (commit only on request).

### 2026-06-18 — `recover-work` pass: recovered the RSE-human-check rewrite of `build_goldstandard.py`
- **Anchor this time was git, not just mtimes.** `lni_study` turned out to be its OWN
  git repo (a gitlink inside `publications`, hence the parent's `AM lni_study`). HEAD =
  `c120823 "current changes to pipeline -pre RSE human check"`, committed 2026-06-18 13:34.
  That checkpoint captured the whole 06-18 13:12–13:15 file cluster (run_pipeline.cmd,
  select_candidates, annotate_lni, confirm_positives, narrow_categories, compute_icr) AND
  the earlier `evaluation` dimension (`da38f4f`). The ONLY uncommitted change vs HEAD was
  `src/build_goldstandard.py` (+205/−66) — which is also the newest file on disk (13:41,
  7 min AFTER the checkpoint commit). So: session committed a "pre-feature" checkpoint,
  started the RSE-human-check feature, crashed before committing or documenting it.
  NEXT_STEPS.md (last touched 06-17 19:18) described NONE of the 06-18 work.
- **The in-flight feature (now recovered, was already complete on disk):** a human
  RS-boolean gate in the goldstandard session. `prompt_decision` now returns a 3-tuple
  `(final, is_new, nav)` with nav ∈ {None, skip, back, quit} and takes `current=` to KEEP
  a prior decision. New `load_decisions`/`save_decisions` keep the whole decisions file as
  in-memory state and REWRITE it on every decision (resumable AND editable, not append-only).
  New `run_session` driver: per paper the coder re-validates `label_research_software` by
  hand; rejecting (rs=0) CASCADES — dimensions skipped, only the RS row written. Navigation
  p/x/g/q + b/s. `main()` rewired to `load_decisions` → `run_session`. Decisions CSV now
  carries one `label_research_software` row per coded paper plus one row per dimension.
- **NOT a half-migrated crash** — every `prompt_decision` return is the new 3-tuple, its
  sole caller (run_session, l.355) unpacks 3, the old append loop in `main()` is fully
  removed, nothing else imports the module. Both halves consistent.
- **Verified (no token, no TTY, no corpus):** `py_compile` OK; `categories` surface intact
  (`DIMENSIONS` now = research_position/methodology/software_type/techstack/**evaluation**;
  `dimension_guidance`, `TYPOLOGY` present) and run_session/save_decisions iterate
  `cat.DIMENSIONS` so they pick up `evaluation` automatically. **Unit-tested the riskiest new
  logic offline:** a save→load round-trip on a fake 2-paper frame confirmed rs=1 with two dim
  rows round-trips, rs=0 writes ONLY the RS row (cascade holds), and `is_new`/`_to_bool`
  survive the CSV. **NOT verified:** the interactive `run_session` loop (needs a TTY) and a
  real end-to-end gold run (needs PDFs + a Phase-A annotation CSV).
- **Reconciled the one straggler doc:** the module docstring at the top of
  `build_goldstandard.py` still described the OLD append-only flow — rewrote it to describe
  the RS gate + cascade, forward/back/goto navigation, and full-rewrite persistence.
- **Open design call (surfaced, NOT silently changed):** `compute_icr.py` loops the 5 real
  `cat.DIMENSIONS`, so it silently IGNORES the new `label_research_software` rows — ICR is
  NOT computed on the human RS gate. No crash (rows just don't match), but if you want
  intercoder agreement on the RS boolean too, `compute_icr` needs a row added for it. Decide
  before the gold/icr run.
- **Not committed:** `build_goldstandard.py` (feature + docstring) is still uncommitted in
  the `lni_study` repo; `lni_study` itself is an uncommitted gitlink in `publications`. Commit
  only on request.
- Resume: from State → Next. The gold session is ready to RUN (`run_pipeline.cmd gold`) once a
  Phase-A annotation CSV for `.workingset/gold` exists; first live use is still unverified.

### 2026-06-17 — `recover-work` pass: recovered & verified the `a-gold --overwrite` feature
- Crash-site signal: two files newer than this notes file (18:12) — `src/annotate_lni.py`
  (18:24) and `run_pipeline.cmd` (18:28, newest). Everything else in `src/` was ≤18:12
  and matched the notes. The 18:24/18:28 edits were undocumented in-flight work.
- The in-flight change (motivated by the 18:12 prompt rewrite — re-annotate gold with the
  new enriched/no-speculation prompt, which plain `a-gold` skips because it resumes):
  - `annotate_lni.py`: new `--overwrite` arg + a block (right before `done_ids` is built)
    that renames the existing checkpoint AND new-suggestions CSV to `.bak` (`.bak2`, `.bak3`
    on collision). Originals gone → empty `done_ids` → fresh header, no skips, no dup rows.
  - `run_pipeline.cmd :a_gold`: 3rd arg `overwrite` (or `force`) sets `OVERWRITE_ARG=--overwrite`,
    passed before `%TOKEN_ARG%`. REM header + step comment updated.
- **NOT a half-migrated crash** — both halves were already complete and consistent. Verified
  (no token, no corpus): `checkpoint_path`/`suggestions_path` defined (l.599-600) before the
  new block; cmd token is `%~2` so `overwrite` lands in `%~3` as the code expects; `py_compile`
  passes; `--help` lists `--overwrite`. Only the docs were missing — now reconciled (State + this).
- **Honest caveat:** `--overwrite` re-attempts the lni52 straggler too, but its failure is
  DETERMINISTIC (`extract_main_content` → None; the short-paper fallback, option b, was NOT
  added — `pdf_text_extraction.py` untouched since 06-15), so `a-gold <token> overwrite` still
  lands 99/100 with lni52 failing. Not run live (needs token).
- Resume: unchanged — State → Next. To refresh gold with the new prompt: `run_pipeline.cmd a-gold <token> overwrite`.

### 2026-06-17 — merged subcategories become `examples` (synonym whitelist), not rejections
- **New schema shape:** an `active` entry may carry an optional `examples:` list of
  alternate subcategory NAMES that were merged into it. They render in the prompt
  after the description as a synonym hint — e.g.
  `` - `middleware_service`: … (auch: `middleware_service_integration`, `middleware_integration_tool`) ``.
- **Removed the 16 auto "merged into X (same subcategory, different wording)."
  rejections** (15 in software_type, 1 in techstack) and re-attached each removed
  key as an `examples` alias under its former `move_to` target. The human-reasoned
  `move_to` rejections (e.g. web_service_api, integration_extension) were KEPT as
  rejections — only the boilerplate merge entries moved.
- **categories.py:** `_build` collects each active entry's `examples` into
  `TYPOLOGY[dim]["aliases"]`; `render_categories_block` appends them as `(auch: …)`.
  `TYPOLOGY[dim]["examples"]` (the `{key:desc}` map other code relies on) is
  unchanged in shape.
- **narrow_categories.py:** the `[m]erge` review action now appends the candidate
  to the chosen active entry's `examples` list (was: a `rejected`+`move_to` entry),
  so future rounds don't recreate the merge boilerplate. `merge_candidates_into_schema`
  dedup now also skips any name already in an active `examples` list, so a merged
  alias is never re-offered as a fresh candidate.
- **Verified:** 0 leftover "merged into" rejections; all 10 alias groups render as
  `(auch: …)`; `schema_io` round-trips; a temp-copy test confirmed a re-suggested
  alias (`testing_framework`) is skipped by collect while a genuinely new key is
  added. Real schema untouched by the test; UTF-8 intact.

### 2026-06-17 — post-round cleanup of category_schema.yaml + no-speculation prompt rule
- **Backup first.** Copied the live schema to
  `prompts/category_schema.backup-2026-06-17.yaml` BEFORE editing (the working
  copy is `prompts/category_schema.yaml`; both untracked in git, so the .bak is
  the only restore point).
- **Cleaned the working copy** (reflecting the first loop round's accept/merge
  decisions):
  - Filled every empty `source:added` description — the WARNING that excluded
    them from the prompt is gone (`schema_io` round-trip confirms 0 empty active
    descriptions). For the heavily-merged categories the description is the
    *common denominator* of what was merged in: `middleware_service` (absorbed
    web_service_api / proxy_server_application / workflow_management_system /
    middleware_integration + 2 more), `test_automation_framework` (testing_framework,
    test_code_generator), `data_exchange_standard` (schema_definition_tool).
  - Applied the two `pending_restructuring` renames: techstack `perl_web -> perl`,
    `hdl_hardware_description -> hardware_description_languages` (dropped the
    now-satisfied `rename_to` notes).
  - Replaced two verbose model-rationale "descriptions" (flash_animation_tools,
    visual_basic) with concise category definitions.
  - Trimmed `pending_restructuring` to just the still-open Math-RSE grouping
    question; removed the resolved add_category/rename/fill_descriptions items
    and the stale "target group does not exist yet" note on `web_service_api`.
  - **Judgment-call descriptions I authored** (standard SE/RSE concepts, derived
    from key name since no human definition existed yet — review & adjust if the
    intended meaning differs): methodology commercial_software_adaptation /
    standardization_driven / model_driven_optimization; software_type
    domain_specific_language / deep_learning_model. Kept the rejected keys intact
    (the loop dedups new candidates against them).
- **Prompt template** (`prompts/rse_typology_prompt_v1.md`, Schritt 2): added a
  "WICHTIG — keine Spekulation" paragraph. A subcategory / new_suggestion may
  only be assigned when the publication's text EXPLICITLY supports it; the model
  must not infer from context what is "typischerweise/üblicherweise/vermutlich"
  used, and must justify each category with the concrete textual evidence. This
  matches the `Spekulation`/`fehlende explizite Nennung` rejection reasons the
  human gave in techstack.
- **Verified:** `categories.render_categories_block()` renders all keys with no
  exclusions; `schema_io.load_schema()` round-trips with 0 empty descriptions and
  the renamed keys present; UTF-8 intact (console mojibake only). NOT re-run
  against SAIA/the corpus — re-annotation with the new prompt is the next step.

### 2026-06-17 — one-command `round`; review CLI gains `[m]erge` + rationale fallback
- **`run_pipeline.cmd round`** — single command that runs the loop iteration
  `advance -> collect -> review` back-to-back (aborts the round if advance or
  collect fails, so review never runs on a half-finished batch; only advance
  spends token). 5th arg = round label (advance fixed at the default %NARROW%
  batch). The three stages stay exposed individually. REM header + usage updated.
  Usage path re-run to confirm the batch still parses.
- **`narrow_categories.py` review CLI, two additions** (py_compile OK; surfaced 32
  real pending candidates live, then stopped before any decision so the schema is
  untouched):
  - `[m]erge->existing`: lists the dimension's `active` subcategories with numbered
    quick-keys; picking one records the candidate under `rejected` + `move_to:<key>`
    (renders as "use X instead"). `[b]`/blank backs out and re-prompts the SAME
    candidate — the per-candidate decision was restructured into one `while action
    is None` loop so a sub-menu/invalid input no longer skips the candidate.
  - Accept with an empty description now FALLS BACK to the candidate's model
    `rationale` as the description (only stays pending if neither exists).
  - **Both write paths verified END-TO-END** (not just compile): a throwaway-copy
    harness drove accept-empty (→ rationale written to `active`, source:added) and
    merge (→ `rejected` + `move_to:<picked key>`), confirming consumed candidates
    are removed and the YAML round-trips with comments + UTF-8 umlauts intact. Real
    schema untouched. Caveat: rationale-as-description is verbose (model hedging) —
    tighten accepted ones in the YAML.
- **Heads-up:** `prompts/category_schema.yaml` already holds 32 pending candidates
  from a pre-compaction `collect` — `review` (or `round`) has material to work now.
- Submodule still uncommitted. No token spent this pass.

### 2026-06-17 — category schema is now the SOURCE OF TRUTH; narrowing LOOP wired
- **Architecture flip.** `prompts/category_schema.yaml` is now the single source of
  truth for the typology. `src/categories.py` derives RSE_DEFINITION / TYPOLOGY /
  prompt guidance from it (via the new `src/schema_io.py` ruamel round-trip layer),
  so every consumer reads the YAML through `categories.py`'s public surface — no
  call-site changes were needed to flip the pipeline. **Retired:**
  `prompts/category_whitelist.json` + the JSON review CLI are no longer the system
  of record (file not deleted yet — see State → open questions).
- **Per-dimension shape** in the YAML: `active` (offered to the model; an active
  entry with an empty `description:` is EXCLUDED + warned), `rejected` (human ruled
  out, with reason/move_to → "do not use" guidance), `candidates` (merge-not-clobber
  inbox the loop appends to). Each dimension was pre-seeded with an empty
  `candidates: []` bucket (NO end-of-line comment) right after its `rejected:` list —
  this is a CONVENTION, not optional: it forces ruamel to land appended candidates in
  place instead of after the trailing `pending_restructuring` banner.
- **The narrowing LOOP (grounded-theory theoretical sampling), now a real cmd flow:**
  `advance` (confirm the next 50 papers, **token**) → `collect --to_schema` (mine each
  paper's `new_suggestion` and append to the YAML `candidates`, **no token**) →
  `review` or hand-edit the YAML (promote candidates to active/rejected, fill
  descriptions, **no token**) → repeat until **saturation** (collect adds ~0 new
  candidates for ~2 rounds) → lock → `a-gold`/`gold`. Stopping rule documented in
  the cmd header.
- **Code touched:** `schema_io.py` (NEW; indent matched to hand-authored style so
  appends don't reflow the file). `narrow_categories.py::merge_candidates_into_schema`
  (positional-insert fallback for a missing bucket; dedup + freq bump in place).
  `confirm_positives.py` (new `--advance N` mode: confirm next N without a `--target`
  top-up; summary handles `target=None`). `run_pipeline.cmd` (header + dispatch +
  `:advance`/`:collect`/`:review` step bodies + usage). `requirements.txt`
  (`ruamel.yaml>=0.18.0`).
- **Verified OFFLINE only (no token, no SAIA, no corpus scan):** real schema loads
  through `categories.py` (DIMENSIONS = research_position/methodology/software_type/
  techstack; rse_def len 362; block style preserved); `merge` lands candidates in the
  right bucket and round-trips comments; `review` reports "No pending candidates" on
  empty `[]` buckets; `confirm --advance` argparse; `collect --from_set narrow` mines
  48 suggestions (dry). **NOT yet run live** — no `advance`/`collect` against SAIA has
  happened (consistent with "don't spend token without being asked").
- **Bugs fixed this pass:** schema_io `offset=0` churned every dash → `offset=2`;
  techstack candidates landed after the `pending_restructuring` banner (ruamel binds
  that comment to the last `rejected` item) → pre-seeded empty buckets; an eol comment
  on `candidates:` re-broke placement → removed (header documents the bucket instead);
  a `collect` dispatch test accidentally appended 15 candidates to the untracked schema
  → restored via Write.
- **Submodule still uncommitted** (`publications`) — not to be committed without an
  explicit request.
- Resume: from State → Next. The loop machinery is ready; first live use is
  `advance` (token) on the narrow set, then `collect --to_schema`, then `review`.

### 2026-06-17 — `recover-work` pass: no crash; `a-gold` already complete (99/100)
- The State said `a-gold` was "in flight". Disk says otherwise: no python running,
  nothing newer than NEXT_STEPS.md, and the gold annotation finished 2026-06-16 19:24.
  The "in flight" line was stale — corrected in State above.
- Verified from disk (no token, no corpus scan): gold = 100 PDFs / 100 manifest rows /
  100 checkpoint rows (consistent). Annotations 99/100 clean (60 label=1, 39 label=0).
- One straggler: `lni52/GI.-.Proceedings.52-53.pdf` → `pdf_extraction_failed`, empty
  label. Resume won't retry it (id is in `done_ids` regardless of error,
  `annotate_lni.py:611-619`).
- Diagnosed it fully (no token): genuine 2-page German paper, PDF + raw text fine
  (4288 chars, not corrupted). Failure is `extract_main_content` returning None — the
  paper lacks every section anchor it keys on (Einleitung/Abstract:/Keywords:), so it
  falls through all 6 priorities (`pdf_text_extraction.py:206`). DETERMINISTIC: a token
  re-run won't fix it. Documented the two real options in State (drop → gold=99, or add
  a short-paper fallback then re-annotate just this id).
- Resume: from State → Next. Decide the lni52 row (drop vs short-paper fallback), then
  proceed to `gold` (build goldstandard) → `icr`.

### 2026-06-16 — recovered an in-flight edit: review CLI gained explicit `[f]orward`
- `recover-work` pass. Crash-site signal: `src/narrow_categories.py` (18:34) was
  newer than `NEXT_STEPS.md` (18:32) — an edit made AFTER the notes were written.
  Sequence on disk: review run saved `category_whitelist.json` (18:31) → candidates
  regenerated + notes updated (18:32) → `narrow_categories.py` edited (18:34).
- The in-flight change (already on disk, complete): `run_review`'s prompt is now
  `[a]ccept / [d]ecline / [b]ack / [f]orward / [s]kip / [q]uit`. `[f]orward` was
  added as an explicit synonym of `[s]kip` (both advance the cursor without
  changing a decision), symmetric to `[b]ack`. Input validation, the branch, and
  the explanatory comment all agree — nothing half-done in the code.
- Reconciled the stale docs the notes/code drift left behind: `TASKS.md` 7b-ii and
  `narrow_categories.py`'s module docstring both still listed only the old
  `[a]/[d]/[s]/[q]` prompt; updated both to include `[b]ack`/`[f]orward`.
- Verified: `py_compile` passes; every prompt-string ↔ validation-tuple ↔ branch
  triplet matches. **Not** run interactively (review needs a TTY). No token spent,
  no corpus scanned.
- Resume: unchanged from below — `run_pipeline.cmd review` to keep narrowing
  (software_type + techstack still untouched; revisit the missed methodology
  category via `[b]ack`).

### 2026-06-16 — fixed bogus `''`/`nan` candidate in `collect` (review showed empty key)
- Bug: review displayed a candidate with key `''` and a `nan || nan || ...` rationale,
  one per dimension (freq 50/44/36/37). Root cause in `collect_candidates`: pandas
  reads a blank `<dim>_new_suggestion` as float NaN, and `str(NaN) == "nan"` is a
  truthy non-empty string, so the old guard `if sugg is not None and str(sugg).strip()`
  let every empty suggestion through as a literal `"nan"` key (same for explanations).
  `to_csv` wrote `"nan"`; `read_csv` parsed it back to NaN; review's `.fillna("")`
  rendered it as `''`.
- Fix: new `clean_cell(v)` helper (None for NaN/blank/`"nan"`/`"none"`), used for the
  chosen category, the suggestion key, AND the explanations. Also a defensive skip in
  `run_review` so a stale CSV can't resurface the blank key.
- Cleaned artifacts: removed the 2 bogus `''` decisions the user had recorded in the
  whitelist (research_position + methodology blacklists). Regenerated
  `results/category_candidates_narrow.csv` from cached annotations (no token): **66 → 62
  rows**, 0 bogus, 29 seed + 33 genuine suggestions. Real prior decisions preserved
  (all on seed keys that still exist): research_position 5 acc/1 dec, methodology 3 acc/5 dec.
- Verified: `py_compile` passes; `collect` re-run live (cache-only, no token) and the
  CSV confirmed clean. Review not re-run interactively (needs a TTY).
- Resume: `run_pipeline.cmd review` to continue narrowing (software_type + techstack
  still untouched; revisit the missed methodology category via `[b]ack`).

### 2026-06-16 — review CLI: added [b]ack navigation + re-decide
- `narrow_categories.py --mode review` now flattens all candidates (across the 4
  dimensions) into one navigable list with a movable cursor and a `[b]ack` option,
  so you can step to the previous candidate and CHANGE an earlier decision. Old
  code skipped any already-decided key, so a missed/wrong call could not be fixed
  without hand-editing the JSON.
- New helpers: `current_decision(entry,key)` (accepted/declined/None) and
  `set_decision(...)` (drops any prior entry in either list, then appends — so
  re-deciding overwrites cleanly, no dupes). Replaced `decided_keys`.
- Resume: opens at the FIRST still-undecided candidate; already-decided ones show
  `(currently accepted/declined — re-decide to change)` and can be revisited via
  `[b]`. Each candidate shows `[i/total]`. Saves after every decision (still fully
  resumable). Prompt is now `[a]ccept / [d]ecline / [s]kip / [b]ack / [q]uit`.
- Current on-disk progress (from the cancelled run): research_position 5 acc/2 dec,
  methodology 3 acc/6 dec; software_type + techstack not started. Candidates CSV:
  results/category_candidates_narrow.csv (66 rows). Re-run `review` to continue.
- Verified: `py_compile` passes. **Not** run interactively (needs a TTY).

### 2026-06-16 — confirm tqdm bar now starts at set size, grows only on top-up
- The bar starts sized to the named set (`total=len(primary)`, e.g. /50) so it
  matches "confirm the set first". It grows to the full candidate count
  (set + pool) ONLY when the set is exhausted before `--target` and top-up begins,
  printing `'<set>' exhausted at X/target confirmed -> topping up from 'pool'`.
  Removes the confusion of the bar reading /829 up front.
- Confirmed PDF source: `confirm` reads the LOCAL `.workingset` copies (manifest
  `dst`, fast disc); the `\\DC01` network `src` is only a fallback if a local copy
  is missing. "Slow startup" = the first LLM round-trip (bar sits at 0 until the
  first paper's model call returns); RateLimiter caps at 10 calls/min thereafter.
- NOTE on intent: `--target N` means "N LLM-confirmed (label==1) papers". With
  `--set narrow --target 50`, if any of the 50 narrow papers are label==0 it WILL
  top up from the pool to reach 50 confirmed. If the goal is just "annotate the 50
  narrow and see which are RSE" (no top-up), use `collect` (annotates exactly the
  set) or set a smaller `--target`.

### 2026-06-16 — added per-paper tqdm progress bar to `confirm`
- `confirm_positives.py` now shows a paper-level `tqdm` bar (`desc="Confirming
  <set>"`, `unit="paper"`) with live postfix `confirmed=X/target, annotated,
  reused, errors`. The per-batch summary still prints, via `tqdm.write` so it
  doesn't tear the bar. Matches the bar style already in `annotate_lni.py`.
- Clarified a user misunderstanding (no code implied it, just doc): `--batch` is
  ONLY a target-check + summary cadence — papers are annotated one at a time
  regardless. Top-up from the pool is driven by `--target` (walk narrow-set then
  pool until target label==1 reached), NOT by `--batch`.
- Verified: `py_compile` passes. **Not** run live (needs token).

### 2026-06-16 — recovered stale pool manifest after PID 20484 finished
- `recover-work` pass. No python running anymore → PID 20484 (old in-memory code)
  finished, score cache last written 15:38 (1800 rows). Crash-site signal: the
  score cache (15:38) was newer than NEXT_STEPS.md (15:31).
- Inconsistency found: `.workingset/pool` had **779 PDFs on disk but only 267
  manifest rows**. Cause: the 15:08 `--regen_manifests` snapshotted pool at 267
  while it was mid-growth; the old process then copied PDFs up to 779 but (running
  the OLD code that writes manifests only at the very end, or stopped before that
  write) never refreshed pool/manifest.csv. narrow/gold/final were already stable.
- Fix: ran `select_candidates.py --regen_manifests` (no corpus scan, no token) →
  pool manifest rebuilt to 779 rows (763 with cached score, 16 on disk but absent
  from the 1800-row cache — harmless, they're still pool members). narrow/gold/
  final regenerated identically (50/100/500).
- Verified: manifest rows == PDFs on disk for all four sets. **Not** run live
  (no confirm/collect/annotate executed; no token spent).
- Resume: sets are stable and consistent — proceed to State → Next step 3 (tune
  `--min_score` by reading `results/rse_scores_Proceedings.csv`) then step 4
  (`confirm --set narrow` <token> → `collect` → `review`). `confirm` now sees all
  779 pool papers when topping up.

### 2026-06-16 — "no manifest" from confirm: estimate was STILL RUNNING + durability fix
- Symptom: `confirm` failed with `No manifest at ...\gold\manifest.csv` though sets
  existed (narrow 50, gold 100, final 500, pool growing). Root cause: the OLD
  `select_candidates.py` wrote ALL manifests only at the very END of the scan, and
  the `estimate` process (PID 20484, started 15:02) was **still running**, slowly
  filling the large `pool` target (cap 2000 - 650 = 1350) — so manifests didn't
  exist yet. Not a crash, not an old/new compat issue.
- Durability fix in `select_candidates.py`: `write_manifest()` is now called the
  moment each set fills (not just at the end), so an interrupted/long pool scan no
  longer loses narrow/gold/final manifests.
- Recovery tool added: `select_candidates.py --regen_manifests` (cmd step
  `manifests`) rebuilds every `.workingset/<set>/manifest.csv` from the copied PDFs
  + score cache, NO corpus scan. Ran it: narrow 50 / gold 100 / final 500 / pool
  267 manifests written (pool was mid-growth). Verified row counts match PDF counts
  for the stable sets.
- NOTE: the code fixes apply to FUTURE runs only — PID 20484 holds the old code in
  memory and will still write its manifests at the end (harmless overwrite).
- Resume: gold/narrow/final are stable — `confirm`/`collect`/`gold` can run now.
  For pool: either let PID 20484 finish, or stop it and re-run `manifests`.

### 2026-06-16 — made `collect` self-contained (no separate confirm needed)
- `run_pipeline.cmd :collect` now exports `SAIA_API_KEY` from the resolved token
  and passes `--annotate_missing`, so `collect <token>` annotates the narrow set
  itself and then mines candidates in one command. Without a token it behaves as
  before (reuses existing checkpoints only).
- `narrow_categories.py::annotate_missing` now **persists** its annotations to
  `results/checkpoints/annotations_narrowcollect_checkpoint.csv` (merged + deduped
  by id). Previously it only returned an in-memory frame, so every `collect` re-ran
  the SAIA calls; now a re-run reuses the cache and spends no new token.
- Verified: `py_compile` passes. **Not** run live (needs token + corpus).
- Resume command: `run_pipeline.cmd collect <token>` (annotates exactly the 50
  narrow papers — does NOT top up from pool, unlike `confirm`).

### 2026-06-16 — verified confirm→collect wiring (collect returned 0 candidates)
- User ran `collect` straight after `estimate` and got `0/50 in checkpoints`,
  `29 seed + 0 model-suggested` — confusing because no LLM calls fired.
- Diagnosis: not a bug. `collect` makes no LLM calls; it reuses annotation
  checkpoints. The narrow set was never annotated, so there was nothing to mine.
- Verified (code read, not run) that `confirm --set narrow` → `collect` is wired
  correctly: matching checkpoint glob + matching `paper_id` keys. Resolved the
  long-standing "collect annotation reuse" open question.
- Resume command: `run_pipeline.cmd confirm <token> "" narrow 50` then
  `run_pipeline.cmd collect`.

### 2026-06-16 — converted this file to State+Log task-log shape
- Restructured `NEXT_STEPS.md` into the `task-logging` skill's two-part shape
  (overwritable **State** snapshot + append-only **Log**). No content lost — the
  prior "Where we are / Next steps / Open questions" sections folded into State.
- Verified: file edit only; nothing run.

### 2026-06-16 — recovered the streaming-refactor crash; finished run_pipeline.cmd
- Recovered an OOM-interrupted refactor (per the `recover-work` skill, no git).
  mtimes showed `select_candidates.py` / `sampling.py` / `confirm_positives.py`
  (Jun 16) already migrated to the streaming + confirm architecture, but
  `run_pipeline.cmd` was half-migrated: header rewritten while the dispatch
  table + step bodies still ran the OLD flow, and `:estimate` passed removed args
  (`--name/--sample`) → the pipeline was broken.
- Fixed `run_pipeline.cmd`: new dispatch (`deps|dry|test|estimate|confirm|collect|
  review|a-gold|gold|icr|full`), `:estimate` uses the real arg surface, added
  `:confirm` (set/target via 4th/5th args), rewrote `:full` to just annotate the
  pre-drawn `.workingset\final`, dropped dead `a-candidates/filter/ws-narrow/
  ws-gold` steps.
- Verified: internal consistency only (goto↔label, call signatures). **Not** run
  end-to-end; the streaming rewrite still has no tests (see State → Next step 1).
