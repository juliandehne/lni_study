# lni_study — task log

_Last updated: 2026-06-23. This file is the durable, on-disk progress record for
the lni_study pipeline (see the `task-logging` / `recover-work` skills). It has a
**State** snapshot (overwritten each update) and an **append-only Log** (newest
first, never edited)._

## State  (current snapshot — overwrite each update)

- **CURRENT (2026-06-23, recover-work pass 2):** Recovered the in-flight `--absent-only`/`preview` work
  left half-saved by the prior session. The crash site was `src/annotate_lni.py` (10:37): `run_fill_missing`
  had drifted from the session's own logged spec — it read an **undeclared** `args.refresh_uncoded` (always
  `False` → full-refresh was dead code, `fill-gold` always gap-filled and **ignored `--absent-only`**).
  Restored to the documented design: `refresh = (not coded) and not args.absent_only` (default = full-refresh
  uncoded / coded absent-only; `--absent-only` holds everyone to gap-fill), plus matching docstring/comments/
  print. The `preview` step (`--preview-prompt`) and the `--checkpoint`/`--skip-rejected` wiring were already
  correct and untouched. **Verified offline (no token):** both files `py_compile`; `--help` shows
  `--absent-only` and no `--refresh-uncoded`; `--preview-prompt` runs clean. **NOT run live:** no SAIA call;
  the regime fix is correct-by-inspection only. See top Log entry. The earlier-today entry below is now
  historical (it describes the same features as *intended*; this pass made the code match).
- **CURRENT (2026-06-23, recover-work):** NO process is running (the round PID 25852 below is GONE —
  finished/stopped; the only live `cmd.exe` is an unrelated F-Secure browser helper). Since the prior
  notes update (06-22 16:40) exactly TWO things changed on disk, both reconciled this pass (see top Log
  entry): (1) **`fill-gold` WAS RUN LIVE on 06-22 19:54** (the prior notes called it token-blocked/not-run)
  — it populated `software_lifecycle_*` in the gold model checkpoint
  `annotations_goldconfirm_…_run_1_checkpoint.csv` and made a `.bak` of the pre-run version (11:46). It
  reached **81/100** RSE-positive gold papers, then was **INTERRUPTED** (no `--advance` cap on `:fill_gold`;
  all 19 unfilled rows have EMPTY `llm_error` = no API errors, checkpoint intact/loads fine). The 19
  unfilled = **7 human-rejected (rs=0), correctly SKIPPED by design** + **12 owed** (4 uncoded → full
  refresh, 8 coded → absent-only). **DANGLING (token-blocked):** re-run `fill-gold` with a token to finish
  the 12. **CORRECTION (06-23): a plain `fill-gold` resume DOES re-touch most of the 81** — the default
  regime full-refreshes EVERY uncoded paper (re-queries all 5 dims and OVERWRITES existing model answers,
  by design, so new subcategories are reconsidered), so ~95 papers run (~71 min), not just the 12 with a
  blank cell. Coded papers stay absent-only, so the human-baseline / ICR comparison is NOT churned (only
  uncoded model answers are, which has no ICR impact). Two ways to finish: (a) **let the full refresh run**
  — intended after the 06-23 schema edit, every uncoded gold paper gets re-annotated under the current
  schema (picks up `conceptual`, merged `performance_evaluation`, `software_lifecycle` everywhere); or
  (b) **`run_pipeline.cmd fill-gold "" absent-only`** (new flag added 06-23) → fills ONLY the ~12 genuinely
  blank cells for every paper, ~9 min, but uncoded papers keep their old answers for dims that already had
  one. NOTE: the checkpoint is written ONCE at loop end, so Ctrl-C loses the current run's progress — the
  prior 81/100 checkpoint is preserved, so aborting is safe.
  (2) **`prompts/category_schema.yaml` hand-edited 06-23 09:06** — a COMPLETE coder reconciliation, not a
  crash: added `techstack: conceptual` (coder:bob, described) and **merged the duplicate `performance
  evaluation`/`performance_evaluation` evaluation keys** into one canonical `performance_evaluation` whose
  new `examples: [performance evaluation]` alias maps the model's spaced output to the underscore key (the
  `examples:` field is a SUPPORTED schema feature — `categories.py:105`). The SAME 06-23 coder session
  also already MERGED the double key in the live coder files (uncommitted): `new_categories_alice.csv`
  collapsed the two `performance evaluation`/`performance_evaluation` rows into one canonical
  `performance_evaluation`, and `coding_alice.csv` normalized its one coded row (`lni332/paper52` evaluation:
  spaced→underscore, `is_new` True→False). `coding_bob.csv` has no performance-evaluation rows. So schema +
  coding_alice + new_categories_alice all agree on `performance_evaluation`; the spaced form survives only in
  the 06-19 backup. No coding-file merge is owed. Verified: schema loads through
  `categories.py` (5 dims, block now 10337 chars), only the SAME two human-owed empty-desc warnings remain
  (`research_position: testing` / `techstack: formal_specification_languages`). **GIT NOTE CORRECTED:** the
  methodology→software_lifecycle migration + 06-22 schema cleanup are now **COMMITTED** (HEAD
  `33a7613 "added menu and some utilities for better monitoring"`, 06-22 11:54) — the old "uncommitted vs
  ee8ba23" notes below are STALE; only today's 06-23 schema edit is uncommitted. Everything in the verbose
  pre-06-23 snapshot below is historical context; trust this paragraph where they conflict.

- **Now / in flight:** a live `round` IS running — `confirm_positives.py --set narrow --advance 50`
  (PID 25852, started 06-22 09:52:20) with a valid token. It is **glacial but working** (~5 min/SAIA
  call on the 675B model), NOT crashed — see top Log entry (06-22 diagnosis). Do not assume a hang;
  check the narrow checkpoint mtime/row count to confirm progress. **TASKS #8–#11 BUILT AS COPIES
  + OFFLINE-TESTED while this round runs (06-22 ~10:50; see top Log entry); #8 partly SWAPPED LIVE.**
  New standalone modules (real names, inert until wired): `src/preflight.py` (#8/#9 fail-fast SAIA
  reachability+auth + path/mount checks), `src/monitor_run.py` (#10 read-only heartbeat: rows-done +
  avg s/paper + ETA, `--watch`), `src/schema_cow.py` (#11 copy-on-write + **3-way** merge keyed by
  (dim,section,key) — adds/count-bumps AND deletions/promotes, concurrent-writer-safe; tested:
  concurrent add+bump vs delete+promote, idempotent no-op). Wiring lives in `*.fix.py` copies:
  `confirm_positives.fix.py` (#8/#9), `annotate_lni.fix.py` (#8/#9), `narrow_categories.fix.py` +
  `sync_coder_categories.fix.py` (#11). **SWAP STATUS:** only `confirm_positives.py` is swapped in
  live (backup at `confirm_positives.prebak.py`) — SAFE because the running advance already loaded
  its code and the round's auto-spawned `collect`/`review` do NOT import it (only a *future* advance
  re-reads it). **HELD until a supervised `collect`:** `annotate_lni.py` (collect lazy-imports it at
  `narrow_categories.py:95`) and `narrow_categories.py` (collect+review re-read it at the 100%
  boundary) — swapping these mid-round would change THIS round's remaining steps. All `*.fix.py` +
  the 3 new modules pass `py_compile`. **SCHEMA
  CLEANUP 2026-06-22 recovered & reconciled (see top Log entry):** the only file newer than this
  notes' prior update was `prompts/category_schema.yaml` (06-22 09:08) — an unlogged hand-edit that
  (a) removed two bogus `nan` coder categories (techstack + evaluation; the exact artifact the 06-18
  `i`/INSUFFICIENT_INFO sentinel was added to prevent), and (b) added `cmd_tool` + `analysis_pipeline`
  to `software_type` active and `benchmarking` to `evaluation` active. The edit was COMPLETE and the
  schema loads/renders cleanly through `categories.py` (5 dims, prompt block 9893 chars). **One typo
  reconciled this pass:** the new `analysis_pipeline` key was written with a SPACE (`analysis pipeline`)
  — every other key is snake_case AND the model emits `analysis_pipeline` (underscore) throughout the
  mistral checkpoint data, so the space would never exact-match. Renamed to `analysis_pipeline` (safe:
  the space-key appears in NO coding CSV; `analysis_pipeline` already in the data). **Still owed (NOT a
  crash — the documented forcing function):** two active coder categories have empty descriptions and
  are therefore EXCLUDED from the prompt until a human fills them — `research_position: testing`
  (coder:alice) and `techstack: formal_specification_languages` (coder:bob). Do NOT auto-author these
  (intended meaning is the coder's to give). **Git note:** the schema is now git-TRACKED in `lni_study`
  (the old "not committed / untracked" note below is stale); HEAD `ee8ba23 "current alice coding"`
  (06-19 09:49) still carries `methodology`, so the ENTIRE methodology→software_lifecycle migration
  PLUS this cleanup are uncommitted vs HEAD. **TYPOLOGY
  MIGRATION 2026-06-19 (see Log entry):** the `methodology` dimension was replaced by
  `software_lifecycle` (6 classical SW-lifecycle phases, per `software_prozesskategorien.md`) by
  hand-editing `prompts/category_schema.yaml` (old block backed up to
  `category_schema.backup-2026-06-19.yaml`). Code-complete (categories.py derives dims from YAML;
  no `src/*.py` references methodology; `build_goldstandard` tolerates the missing model column).
  **DANGLING (token-blocked):** run the NEW `fill-gold` step (06-22, see top Log entry) so the gold
  papers get `software_lifecycle_*` model annotations under the new schema. **TARGET CORRECTED
  06-22 (see top Log entry):** fill-gold now points at the CONFIRMED gold pool
  (`.workingset\gold_confirmed`, 100 PDFs) and updates the SAME checkpoint the `gold` coding step
  reads — `annotations_goldconfirm_*` (156 rows, `software_lifecycle_category` column ABSENT). The
  earlier wiring targeted the retired raw `gold` set whose live checkpoint no longer exists (only
  `annotations_gold_*.bak1-3`), which is why the run errored "needs an existing gold checkpoint".
  Re-pointed via a new `annotate_lni.py --checkpoint PATH` override (mirrors build_goldstandard
  `--annotations`), since the folder name `gold_confirmed` would NOT derive the `goldconfirm` tag.
  Two regimes (per the
  06-22 refinement): papers NOT yet coded by either coder get a FULL REFRESH (every dimension
  re-queried, so newly-created subcategories are picked up even where a model answer already exists);
  papers already coded by a coder get ABSENT-ONLY (just the missing dims) so their coded baseline /
  ICR comparison is not churned. Either way existing/untouched answers are preserved, unlike
  `a-gold overwrite` which re-does everything. (Plain `a-gold` resume would NOT add software_lifecycle
  to papers already in the checkpoint — it skips done papers entirely — so `fill-gold` is the correct
  tool here.) Then a `gold`
  pass to actually code the new dimension (alice/bob skipped old methodology and have NOT coded
  software_lifecycle). The old gold model checkpoint still carries orphaned `methodology_*` columns
  (harmless). **NEW `--reannotate` flag / `reannotate` step
  added & offline-verified 2026-06-20** (see top Log entry): force-redo path that re-annotates the
  already-confirmed (label==1) narrow papers under the current schema so `collect` mines
  `software_lifecycle` suggestions immediately instead of waiting for `advance` to trickle in fresh
  papers. `confirm_positives.py --reannotate` drops the redo ids from the checkpoint (archives a
  `.bak`, replaces rather than duplicates), pops them from `done`, and re-runs them; `--advance N`
  caps the count (token budget). Wired as `run_pipeline.cmd reannotate <token> "" narrow [N]`.
  Token-blocked work (SAIA) so the live redo is NOT yet run; only `purge_checkpoint_ids` is
  offline-verified (268→265 rows, redo ids gone, no dup ids, columns aligned, `.bak` made).
  Recommended flow: `reannotate` → `collect "" "" "" r1` → `review` (or a full `round`).
  Earlier 06-18 state below is unchanged.
  **NEW short-paper cap added & offline-verified 2026-06-18**
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

### 2026-06-23 (later) — recover-work: code had drifted from the `--absent-only` spec; restored it
- **Why this pass.** `/recover-work` after the prior session was interrupted. Anchored on mtimes vs the
  prior notes update (10:14). Newest files were `src/annotate_lni.py` (10:37 = crash site),
  `src/pipeline_menu.py` (10:25), `prompts/rse_typology_prompt_v1.md` (10:23), `run_pipeline.cmd` (10:13)
  — all newer than the notes, i.e. the in-flight work the notes didn't yet reflect. No process running.
- **The mismatch (recovery target).** Three self-consistent layers — the argparse `--absent-only` help, the
  `run_pipeline.cmd :fill-gold` driver, AND the prior 10:14 State + the Log entry below — all describe ONE
  design: **default = full-refresh uncoded papers; `--absent-only` = gap-fill EVERY paper.** But the body of
  `run_fill_missing` had drifted to a DIFFERENT, non-functional design: `refresh = (not coded) and
  getattr(args, "refresh_uncoded", False)`. `--refresh-uncoded` was **never declared in argparse**, so the
  getattr was permanently `False` → the full-refresh branch was DEAD CODE (every paper always gap-filled)
  and the declared `--absent-only` flag was **never consumed**. So `fill-gold` ignored its flag entirely.
- **Decisive evidence it was a botch, not a redesign.** The 06-23 Log entry directly below literally
  specifies the intended line — *"Implemented via `refresh = (not coded) and not args.absent_only`"* — and
  says the `mode` label / counter / intro print "all key off `refresh` now". The on-disk body had silently
  diverged from the session's own written spec. The docstring + inline comments had been rewritten to the
  inverted (gap-fill-by-default) story too, so body and its own comments agreed with each other but
  contradicted the spec, the argparse, and the driver.
- **Fix (smallest reconciling change, matches the logged spec).** In `run_fill_missing`: line ~671
  `refresh = (not coded) and not getattr(args, "absent_only", False)`; rewrote the intro `print` block
  (line ~626) and the per-paper comment + the function docstring back to the documented semantics
  (default refresh-uncoded / coded absent-only / `--absent-only` holds everyone to gap-fill). No change to
  argparse, the driver, the menu, or `run_preview_prompt` — those were already correct.
- **Verified (NO token).** `py_compile` OK (annotate_lni.py + pipeline_menu.py); `--help` lists
  `--absent-only` and no longer any `--refresh-uncoded`; `grep` confirms `refresh_uncoded` is gone and
  `absent_only` is now consumed at the `refresh=` line + intro print (not just declared); `annotate_lni.py
  --preview-prompt` ran clean (exit 0, rewrote `results/prompt_preview.txt`). **NOT verified:** no live
  SAIA `fill-gold` run was made — the regime fix is correct by inspection + matches the prior session's
  spec, but has not been exercised against the API. The prompt's `vier`→`fünf` literal fix (flagged "NOT
  done / user's call" in the entry below) IS now present in `rse_typology_prompt_v1.md` (applied after that
  entry was written); harmless and correct (there are 5 dims).
- **Still owed (unchanged, token-blocked).** Finish the interrupted `fill-gold` (was 81/100): either let
  the default full refresh run, or `run_pipeline.cmd fill-gold "<token>" absent-only` for the ~12 blank
  cells only — the flag now actually works.

### 2026-06-23 — prompt-preview step + `--absent-only` fill regime (annotate_lni.py / run_pipeline.cmd)
- **Why.** While running `fill-gold` the user saw the bar say `refresh-all research_position,…,evaluation`
  over 100/100 papers (~71 min ETA) and was confused — they expected only the ~12 papers with a blank cell.
  Diagnosed: that IS the documented full-refresh-for-uncoded regime (`run_fill_missing`, the `dims =
  list(cat.DIMENSIONS) if refresh else _missing_dims(row)` branch). `refresh-all` = all 5 dims re-queried
  AND overwritten for that (uncoded, non-rejected) paper — by design, not a bug. Coded papers stay
  absent-only. Two follow-up asks from the user: a way to finish only the genuine gaps, and a prompt
  preview to inspect/shrink the prompts for performance.
- **`--absent-only` flag (annotate_lni.py).** New `--absent-only` (dest `absent_only`) forces the
  absent-only regime for EVERY paper, incl. uncoded ones. Implemented via `refresh = (not coded) and not
  args.absent_only`; `dims`, the `n_refresh` counter, the bar `mode` label and the intro print all key off
  `refresh` now (was `not coded`). Wired into `run_pipeline.cmd fill-gold "" absent-only` (3rd arg, like
  `a-gold overwrite`). Lets a resume fill just the ~12 blank cells (~9 min) instead of full-refreshing ~95.
- **`--preview-prompt` step (annotate_lni.py + cmd `preview`).** New corpus-free, token-free `run_preview_
  prompt(args)`: loads the template, splices bracketed placeholders for the paper body, and prints the
  SYSTEM prompt, the FULL annotation user prompt and the TARGETED fill prompt with char/token sizes + a
  size breakdown, also writing `results/prompt_preview.txt`. Dispatched EARLY in `main()` (before any
  scan/stage), so `--lni_folder` is now optional (required only for the other modes; validated explicitly).
  cmd step: `run_pipeline.cmd preview`.
- **Verified (no token).** `py_compile` OK; `--help` lists both flags; `src/annotate_lni.py --preview-prompt`
  ran and produced the breakdown. **Two findings the preview surfaced** (candidates for the user's
  "reduce/alter" goal): (1) the full annotation prompt is **17.3k chars / ~4.3k tokens** of static
  scaffolding, dominated by the **10.3k-char category catalogue block** + a **3.6k-char curated guidance
  block** — the body text adds up to 40k chars on top. (2) the prompt's Schritt-2 intro still hardcodes
  **"die folgenden vier Dimensionen"** though there are now **5** (research_position, software_lifecycle,
  software_type, techstack, evaluation) — a stale literal in `prompts/rse_typology_prompt_v1.md` worth
  fixing. The two empty-description active subcategories (`research_position: testing`,
  `techstack: formal_specification_languages`) are still EXCLUDED from the prompt (human-owed, unchanged).
- **NOT done.** No SAIA call made; prompt template text not edited (the "vier"→"fünf" fix and any
  shrinking are the user's editorial call). The interrupted `fill-gold` (81/100) was NOT resumed.

### 2026-06-23 — recover-work: reconciled the live `fill-gold` run (81/100, interrupted) + the 06-23 schema edit
- **Why this pass.** `/recover-work` after an interrupted session. Anchored on mtimes vs the prior notes
  update (06-22 16:40). No python/cmd/biber/quarto process was running (the round PID 25852 from the prior
  State is gone; the only live `cmd.exe` is an F-Secure browser helper). Exactly TWO files were newer than
  the notes: `prompts/category_schema.yaml` (06-23 09:06, the newest = crash site) and the gold model
  checkpoint `annotations_goldconfirm_…_run_1_checkpoint.csv` (06-22 19:54).
- **Finding 1 — `fill-gold` actually ran (the prior notes still called it token-blocked/not-run).** The
  goldconfirm checkpoint now CARRIES `software_lifecycle_*` columns (previously ABSENT — the exact gap
  fill-gold closes), grew 327k→339k, and a `.bak` of the pre-run state was written at 11:46. So a live,
  token-spending `fill-gold` happened ~19:54 on 06-22. **Completeness (pandas, offline):** of 100
  RSE-positive gold papers, **81 have software_lifecycle filled, 19 do not.** The 19 = **7 human-rejected
  (rs=0)** → fill-gold's default skip-rejected SKIPPED these correctly + **12 owed** (4 not-coded → full
  refresh regime, 8 coded → absent-only regime). All 19 unfilled rows have EMPTY `llm_error` (no API
  failures), and `:fill_gold` carries no `--advance` cap (run_pipeline.cmd:450) ⇒ the run was
  **INTERRUPTED ~12 papers short**, not capped and not errored. Checkpoint is intact (loads, 156 rows).
- **Finding 2 — the 06-23 09:06 schema edit is COMPLETE, not a half-migrated crash.** `git diff HEAD`
  (HEAD moved to `33a7613`, see below) shows two changes: (a) added `techstack: conceptual` (coder:bob,
  described: "No code has been written but it describes a concept"); (b) merged the two duplicate
  evaluation keys `performance evaluation` (spaced) + `performance_evaluation` into one canonical
  `performance_evaluation`, deleting the spaced key and adding `examples: [performance evaluation]` +
  a corrected, merged German description (fixed typos berzieht→bezieht, Performanzmatriken→Performanzmetriken).
  The `examples:` field is a SUPPORTED active-entry feature (`categories.py:105` reads it), so this is the
  intended fix for the space-vs-underscore alias problem the 06-22 notes flagged — handled via examples
  rather than a rename.
- **Verified (offline, NO token).** Schema loads through `categories.py`/`schema_io.py`: 5 dims
  (`research_position, software_lifecycle, software_type, techstack, evaluation`), `render_categories_block`
  builds (10337 chars, up from 9893), zero space-keys, only the SAME two human-owed empty-desc warnings
  (`research_position: testing` [alice], `techstack: formal_specification_languages` [bob] — still owed,
  left for the coder, NOT auto-authored). Goldconfirm checkpoint loads via pandas (156 rows). NOT run: any
  token/live step.
- **Git note corrected.** Contrary to the prior State's "uncommitted vs HEAD ee8ba23", the
  methodology→software_lifecycle migration + the 06-22 schema cleanup + menu/utilities + coding files are
  **COMMITTED** at HEAD `33a7613` ("added menu and some utilities for better monitoring", 06-22 11:54).
  Only today's 06-23 schema edit (conceptual + performance_evaluation merge) is uncommitted.
- **Resume / dangling (token-blocked).** Re-run `fill-gold` with a SAIA token to finish the 12 owed gold
  papers' `software_lifecycle` (resumable; absent-only for coded papers won't churn the 81 already done).
  Then the `gold` coding pass for the new dimension (per the 06-19 migration). Commit the 06-23 schema edit
  on request.

### 2026-06-22 — `fill-gold` TARGET FIXED: points at the confirmed gold pool / `goldconfirm` checkpoint
- **Symptom.** Running `fill-gold` errored: *"--fill-missing needs an existing gold checkpoint to
  update, but none was found at …\annotations_gold_…_checkpoint.csv. Run the gold annotation first."*
  User asked: "was the last goldcheckpoint moved to the backup or what happened?"
- **Diagnosis (nothing was moved by this run).** fill-gold failed at the existence check, BEFORE any
  archive step; `_archive` only ever *copies* (shutil.copy2), never moves. The live
  `annotations_gold_*_checkpoint.csv` (raw "gold" tag) is genuinely gone — only `.bak` (06-16),
  `.bak2` (06-17), `.bak3` (06-18 10:53) remain. The workflow MIGRATED off the raw `gold` set on
  06-18 when `confirm` produced the CONFIRMED pool: `.workingset\gold_confirmed\` (100 PDFs) +
  `annotations_goldconfirm_…_checkpoint.csv` (06-18 11:46, 156 rows). That `goldconfirm` checkpoint
  — NOT `gold` — is what the `gold` coding step (`build_goldstandard --annotations`) actually reads.
  fill-gold (and a-gold) were still pointed at the dead `.workingset\gold` (tag "gold").
- **Fix.** New `annotate_lni.py --checkpoint PATH` override (mirrors build_goldstandard
  `--annotations`): PDFs still come from `--lni_folder`, but the checkpoint read/updated is the named
  one — needed because the folder name `gold_confirmed` derives tag "gold_confirmed", not the live
  "goldconfirm". Re-derives the paired `new_category_suggestions_*` path from the checkpoint's own tag.
  `run_pipeline.cmd :fill_gold` now uses `--lni_folder .workingset\gold_confirmed --checkpoint
  …annotations_goldconfirm_…_checkpoint.csv`.
- **Verified (offline, no token).** `py_compile` clean; `--help` lists `--checkpoint`; gold_confirmed
  has 100 PDFs; goldconfirm checkpoint loads (156 rows, `software_lifecycle_category` column ABSENT —
  exactly the gap fill-gold closes; `run_fill_missing` adds every canonical column as blank before the
  gap scan, so the absent column is filled, not a KeyError). run_pipeline.cmd stays CRLF (539/539).
  NOT run live (token must not be spent unasked).
- **Note.** a-gold still points at the retired raw `.workingset\gold`; left as-is (it's the pre-confirm
  path and the user only runs fill-gold). Revisit if a-gold is ever re-exercised.

### 2026-06-22 — `fill-gold` now SKIPS human-rejected (rs=0) papers by default (offline-verified)
- **Why.** User asked whether running `topup` early would shrink the fill set by dropping human-rejected
  no-RS papers. It would not: `topup` *copies* coded papers into `gold_human_{confirmed,rejected}_*.csv`
  and *adds* new pool papers to refill the confirmed set to target — it never prunes the annotation
  checkpoint `fill-gold` iterates, so it would only grow the work. The real waste is that `fill-gold`
  keyed RS off the MODEL label only, so a paper the model called rs=1 but a human rejected (rs=0) still
  got its absent dims filled even though it can never enter the goldstandard. Fix: skip human-rejected
  ids in `fill-gold` directly — works regardless of how many of the 100 are coded.
- **What changed (all offline; NO SAIA call):**
  - `src/annotate_lni.py`: added `_rejected_paper_ids(goldstandard_dir)` — unions ids from
    `coding_*.csv` rows where `dimension == label_research_software` and `final_category` is 0/false,
    plus any `gold_human_rejected_*.csv`. `run_fill_missing` computes `rejected_ids` (when
    `args.skip_rejected`, default True) and skips those pids before the RS/dims checks, tracking
    `n_skip_rejected` in the progress bar + final summary. New CLI flag
    `--skip-rejected / --no-skip-rejected` (BooleanOptionalAction, default skip). Section header
    comment + `run_fill_missing` docstring updated.
  - `run_pipeline.cmd`: `fill-gold` REM doc + `:fill_gold` label comment note the rs=0 skip default.
  - `src/pipeline_menu.py`: `fill-gold` Stage description mentions "skip human-rejected (rs=0)".
- **Verified:** `py_compile` of annotate_lni passes; `argparse.BooleanOptionalAction` present on
  Python313; smoke test against the real `goldstandard/` resolved 30 coded ids and 7 rejected ids.
  **NOT run live against SAIA** (token-blocked). Uncommitted.

### 2026-06-22 — `fill-gold` refinement: full refresh for UNCODED papers, absent-only for CODED (offline-verified)
- **Why this pass.** The first `fill-gold` (entry below) only ever queried ABSENT dimensions, so a
  newly-created subcategory in a dimension that already has an answer would never be reconsidered. User
  refined: "I want this also for the subcategories that already have an answer but only for the papers
  that were not coded yet (by either coder)." So the model baselines of papers a human has already
  coded must stay stable (don't churn the ICR comparison), but uncoded gold papers should be fully
  re-annotated to pick up the new subcategories.
- **Design (two regimes, decided per paper):**
  - paper id NOT in any `goldstandard/coding_*.csv` → **full refresh**: `dims = list(cat.DIMENSIONS)`
    (re-query every dimension; the targeted prompt then renders all subcategories incl. new ones).
  - paper id present in some `coding_*.csv` → **absent-only**: `dims = _missing_dims(row)` (unchanged
    original behaviour).
  - Skip only when the chosen `dims` is empty (coded + already complete), non-RSE, or not-in-checkpoint.
- **What changed (all offline; NO SAIA call):**
  - `src/annotate_lni.py`: added `_coded_paper_ids(goldstandard_dir)` (unions the `id` column across
    `coding_*.csv`, tolerant of empty/badly-shaped files). `run_fill_missing` now computes
    `coded_ids = _coded_paper_ids(DATA_ROOT / "goldstandard")` once, picks `dims` per the two regimes,
    and reports full-refresh vs absent-only counts (`n_refresh`) in the progress bar + final summary.
    Section header comment + docstring updated.
  - `run_pipeline.cmd`: `fill-gold` REM doc + `:fill_gold` label comment + usage line updated to
    describe the two regimes. Dispatch/command unchanged.
  - `src/pipeline_menu.py`: `fill-gold` Stage description updated.
- **Verified:** `py_compile` of annotate_lni / categories / pipeline_menu all pass. **NOT run live
  against SAIA** (token-blocked by policy). Uncommitted.

### 2026-06-22 — new `fill-gold` step: incrementally fill ONLY the MISSING gold typology dimensions (offline-verified)
- **Why this pass.** After the methodology→software_lifecycle migration the gold model checkpoint has
  no `software_lifecycle_*` cells. The existing path was `a-gold overwrite`, which re-annotates EVERY
  dimension of EVERY gold paper — needlessly redoing (and possibly changing) answers that are already
  correct. User asked for a step that, for the selected papers, only the missing categories are
  suggested "without rewriting the whole thing".
- **Design (locked with the user via two questions):** (1) **Query mode = targeted per-dimension
  prompt** — the model is asked ONLY about the missing dimension(s), not the full typology; (2) **Gap
  rule = only ABSENT dimensions** — a dimension is a gap iff its `<dim>_category` cell is absent /
  NaN / blank. Stale or retired present values are left as-is (not refreshed).
- **What changed (all offline; NO SAIA call — token must not be spent unasked):**
  - `src/categories.py`: `render_categories_block()` / `render_category_guidance_block()` gained a
    `dims: list[str] | None` filter (default None = all dims, fully backward-compatible) so the
    targeted prompt renders only the missing dimensions' subcategories + rejected-key guidance.
  - `src/annotate_lni.py`: extracted the shared SAIA call+retry+parse core into
    `_complete_with_retries(...)` (classify_paper now calls it — behaviour unchanged). Added
    `build_fill_user_prompt`/`_fill_json_skeleton` (focused German prompt: "bereits als RSE
    klassifiziert" + "annotiere AUSSCHLIESSLICH die folgende(n) Dimension(en)"),
    `classify_paper_dims` (returns only the requested dims' flat cells),
    `_is_blank`/`_missing_dims`/`_is_rse`/`_archive` helpers, and `run_fill_missing` (reads the
    one-row-per-paper checkpoint as strings with `keep_default_na=False`, ensures new-dim columns
    exist, per paper fills only the absent dims via `df.at`, logs new suggestions, then backs the
    checkpoint up to `.bak` and rewrites it). New `--fill-missing` flag (mutually exclusive with
    `--overwrite`); `main()` branches to `run_fill_missing` after client creation and returns.
  - `run_pipeline.cmd`: new `fill-gold` step (dispatch + REM doc + usage line) running
    `annotate_lni.py --lni_folder %DATA%\.workingset\gold --no_stage --model %MODEL% --fill-missing`
    (full final-grade model, NOT the loop model).
  - `src/pipeline_menu.py`: new `fill-gold` Goldstandard stage (needs_token, full model — correctly
    NOT in `LOOP_MODEL_STAGES`).
- **Verified:** `py_compile` of annotate_lni / categories / pipeline_menu all pass; smoke-tested
  `_is_blank`, `_fill_json_skeleton` (single + multi dims), and `build_fill_user_prompt` render
  offline. **NOT yet run live against SAIA** (token-blocked by policy) — a real `fill-gold` pass is
  the dangling next step once a token is supplied. Uncommitted.

### 2026-06-22 — slowdown diagnosis + tweaks #2 (max_tokens cap) & #4 (faster loop model); interactive menu front door
- **Why this pass.** User asked to diagnose the ~400s/paper annotation slowdown ("prompt growth vs. SAIA
  being slow?") and then to apply two low-complexity tweaks: **#2** cap `max_tokens`, **#4** use a
  faster model for the candidate-mining loop steps. Plus earlier this pass: build the interactive
  launcher (`src/pipeline_menu.py`) + repo-root `menu.cmd`, and honor `LNI_CORPUS` in run_pipeline.cmd.
- **Diagnosis (data, not guess).** Per-paper time swings 225→662s *within a single round where the
  prompt is FIXED* (schema only changes between rounds, at review) → variance is **API/model-side**
  (prefill + queue on the 675B), NOT prompt growth. ~30% of papers hit the 300s client timeout.
  Prompt is minor: 55 active categories + ~3.6k-char template vs paper text capped at 40000 chars
  (which dominates input). Conclusion: predominantly SAIA latency-bound.
- **#2 max_tokens cap (DONE, offline-verified).** `annotate_lni.py`: new `DEFAULT_MAX_TOKENS=2048`
  constant; `classify_paper(..., max_tokens=DEFAULT_MAX_TOKENS)` passes it to the API and adds a
  **finish_reason=="length" guard** that returns `{"llm_error": "truncated ...", "llm_raw_response": ...}`
  instead of silently parsing a half-filled JSON. New `--max_tokens` CLI flag (0 = uncapped) on BOTH
  `annotate_lni.py` and `confirm_positives.py`; call sites use `(args.max_tokens or None)`;
  `confirm_positives.py` imports `DEFAULT_MAX_TOKENS`. Measured a complete output is ~885 tok median /
  ~1354 max, so 2048 ≈ 50% headroom — well-formed answers NEVER truncate; the guard only fires on
  genuinely over-long/malformed output. **HONEST CAVEAT:** outputs don't ramble to a cap, so #2 bounds
  the worst case + adds predictability but does NOT materially cut the ~400s avg. The real win is #4.
- **#4 faster loop model (DONE, offline-verified).** New `ADVANCE_MODEL` knob in `run_pipeline.cmd`
  (defaults to `%MODEL%` → **zero behavior change until opted in**; overridable inline or via
  `LNI_ADVANCE_MODEL` env). Used by ONLY the candidate-mining token steps: `advance`, the advance
  sub-step of `round`, and `reannotate` (they merely mine `new_suggestion` subcategories). The
  final-grade steps `a-gold`/`full`/`confirm`/`topup` STILL use the full `%MODEL%` (675B). Config
  banner prints a `loop model` line only when it differs from `%MODEL%`. `pipeline_menu.py` affirms the
  loop model for those 3 stages (`LOOP_MODEL_STAGES`) and exports `LNI_ADVANCE_MODEL`.
  **OPEN — the model id is the user's call:** no faster SAIA model id was hard-coded (must not spend the
  token to list models without being asked). To get the speedup, set `LNI_ADVANCE_MODEL` (or edit the
  `ADVANCE_MODEL` line) to a faster model your SAIA account offers; TASKS.md names llama/gemma as the
  majority-vote alternates. Until then the loop runs on the 675B exactly as before.
- **Interactive front door (DONE).** `src/pipeline_menu.py`: numbered stage menu (mirrors the project's
  other `input()` UIs), token prompted (getpass, hidden) ONLY if the stage needs one and none is in
  `SAIA_TOKEN`/`SAIA_API_KEY`, affirms working dir (`LNI_DATA_ROOT`) + corpus (`LNI_CORPUS`), per-stage
  extras fill run_pipeline.cmd slots 2–5, opt-in SAIA reachability check, then dispatches. Token passes
  via the child ENV (not on the launcher's command line). `menu.cmd` at repo root launches it.
  `run_pipeline.cmd` now honors `LNI_CORPUS` (overrides the CORPUS placeholder).
- **Verified:** all edited files `py_compile` clean (`MENU_OK`); `--max_tokens` shows in both `--help`
  outputs. **NOT verified:** no live SAIA run this pass (token not to be spent unasked) — #2's guard and
  #4's faster model are UNTESTED against the real API. Nothing committed.

### 2026-06-22 — built #8–#11 as copies while the round runs; swapped in the one swap-safe fix (#8 confirm_positives)
- **Why this pass.** User: "check the round.log regularly … create your fixes in copies, once you are
  finished and the round.log has not reached 100%, it should be safe to copy the new versions, right?"
  So: build the four deferred fixes (#8–#11) WITHOUT touching live files, then hot-swap only the ones
  that can't affect the in-flight round. Round was at 10→18% (9/50, ~400s/paper) throughout this pass.
- **Swap-safety analysis (the crux of "is it safe to swap while <100%?").** YES for the running
  process — it loaded its modules at import; replacing a `.py` on disk does not change PID 25852's
  behavior. The CAVEAT: a `round` is ONE cmd process running advance→collect→review back-to-back, and
  the instant advance hits 100% it auto-spawns `collect` (a FRESH Python that re-reads code from disk).
  The files that fresh `collect`/`review` re-read: `narrow_categories.py` (+ its top imports
  `categories.py`, `schema_io.py`, `sampling.py`) and `annotate_lni.py` (lazy import at
  `narrow_categories.py:95`). `confirm_positives.py` is NOT re-read by collect/review — only by a
  *future* advance. ⇒ swapping `confirm_positives.py` now is safe; swapping `annotate_lni.py` or
  `narrow_categories.py` now would change this round's remaining steps. `schema_io.py` left untouched.
- **What was built (all as new files; live files untouched except the one swap below).**
  - `src/preflight.py` (#8/#9): `check_saia(base_url, token)` fail-fast reachability+auth via a
    short-timeout `models.list()` (AuthError→fail token rejected; conn/timeout→fail unreachable;
    other HTTP status→soft-pass "reachable, auth not verified" so a `/models`-less endpoint can't
    false-fail); `check_path`/`check_paths`/`check_data_root` (LNI_DATA_ROOT + results + .workingset);
    `require(...)` prints each check and `SystemExit`s on failure. CLI for manual pre-run use.
  - `src/monitor_run.py` (#10): read-only heartbeat — parses round.log's tqdm line (UTF-16 aware) and
    cross-checks the newest checkpoint CSV (rows/confirmed/errors/mtime), prints sec/paper + ETA;
    `--watch`. Tested live against the running round.
  - `src/schema_cow.py` (#11): copy-on-write + **3-way** merge. `work_copy()` writes a numbered work
    copy AND a pristine base snapshot; `merge_back()` RE-READS the canonical fresh and 3-way-merges
    work-vs-base-vs-canonical keyed by (dim,section,key): changed-in-work-only→take work (covers adds
    AND collect's count bumps), changed-in-canonical-only→keep (concurrent writer preserved),
    deleted-in-work+untouched-canonical→delete (covers review's promote/decline), both-changed→flag
    conflict + keep canonical. Atomic write (temp + os.replace). `discard()` for no-op exits.
    **Note:** upgraded from the originally-planned purely-additive 2-way merge — additive-only would
    have LOST collect's count bumps (key already in canonical) and left review's promoted candidates
    stranded in `candidates`. The base snapshot makes updates+deletions representable.
  - `*.fix.py` wiring copies: `confirm_positives.fix.py` + `annotate_lni.fix.py` call `preflight`
    (confirm: SAIA+paths before the slow candidate load; annotate: paths up front, SAIA deferred to
    the annotation step so report-only/estimate modes don't need a token). `narrow_categories.fix.py`
    routes collect (load/save) and review (per-decision save + merge at end/on quit) through
    `schema_cow`; `sync_coder_categories.fix.py` routes its merge through `schema_cow` (discards the
    work copy on dry-run/no-op).
- **Verified (offline, NO token spent, real canonical untouched).** `py_compile` of all 3 new modules
  + all 4 `*.fix.py` + the now-live `confirm_positives.py`. schema_cow tested on TEMP copies: writer A
  (collect-style: bump c1 count 1→5, add c3) and writer B (review-style: promote c2 candidates→active)
  both made from the SAME base, merged A-then-B → final had c1=5, c3 added, c2 removed from candidates
  and present in active, no clobber; a third no-op merge changed nothing (idempotent). `.schema_work`
  left empty; real `prompts/category_schema.yaml` mtime unchanged (09:27).
- **SWAPPED LIVE (the only swap-safe one):** `confirm_positives.py` ← `confirm_positives.fix.py`
  (original backed up to `src/confirm_positives.prebak.py`). Diff is minimal: one `import preflight`
  + one `preflight.require([...])` block before the candidate load; all referenced symbols
  (`DEFAULT_SAIA_ENDPOINT`, `--saia_endpoint/--saia_token`) confirmed present. Compiles. Affects only
  the NEXT advance, not this round.
- **HELD (do NOT swap until a `collect` can be supervised):** `annotate_lni.py` and
  `narrow_categories.py` — both on this round's remaining collect/review path. Swap them only when no
  round is mid-flight (or right before deliberately starting a fresh round), then run a supervised
  `collect` once to confirm the schema_cow merge + preflight behave on real data.
- **NOT verified (honest):** no live/token run of any swapped or held fix; preflight's SAIA branch
  against the real endpoint with a real token; the interactive `review` merge-on-quit in a real TTY;
  a real two-writer concurrent schema race (only the deterministic temp-copy simulation was run).
- **Resume.** When ready to adopt #9/#11: swap `annotate_lni.py`←`.fix.py` and
  `narrow_categories.py`←`.fix.py` (back up first), `py_compile`, then a supervised `collect`/`round`.
  Optionally also `sync_coder_categories.py`←`.fix.py`. Run `python src/monitor_run.py --watch` any
  time to watch the current round. Commit only on request (per standing constraint).

### 2026-06-22 — diagnosed a `round` that "took long to start then crashed" / "isn't reacting": SAIA per-call latency, NOT the schema
- **Symptom (user).** Ran `round` to narrow the new categories (esp. `software_lifecycle`); it
  hung at startup then appeared to crash; on a retry it again "isn't reacting really."
- **Verdict: not a crash and not schema-related.** Confirmed by catching the live process in the
  act: `confirm_positives.py --set narrow --advance 50 --saia_token …` (PID 25852, started
  09:52:20) was alive 10+ min using only **1.9s CPU** (blocked on the network socket, not
  computing), and it **wrote a real, clean annotation** to the narrow checkpoint at 09:57:29
  (`id=lni195/47`, `label_research_software=0`, `llm_error=nan`). So token, schema, parsing,
  and checkpoint append all work — it is simply **glacial**: ~5 minutes per paper. At that rate
  `--advance 50` is a ~4-hour job that emits one CSV line every few minutes, which reads as frozen.
- **Ruled out, with evidence.**
  - *Schema:* startup printed only the expected "active subcategories with no description are
    EXCLUDED" warning (the two empty-desc coder cats) and nothing else; the 06-20 narrow
    checkpoint header already carries `software_lifecycle_*` (no `methodology`), so appends stay
    column-aligned. The `analysis_pipeline` rename is in place.
  - *Slow local startup:* a token-free repro (`--advance 1`, no `SAIA_API_KEY`) loaded all
    **829 candidates incl. page-counting 779 pool PDFs in ~4.2s** and stopped cleanly at the token
    guard. The local `.workingset/pool` copies (779 PDFs present) make page-counting fast, so the
    short-paper cap is NOT the bottleneck.
  - *Network/endpoint down:* `GET /v1/models` returned 401 (auth-required, as expected w/o token)
    in ~4s incl. TLS — endpoint healthy. The token was accepted (no fast 401 → no AuthError).
  - *Rate limiter:* `RateLimiter` is an in-memory deque (fresh per run), not persisted — not it.
- **Root cause.** Per-call latency of `mistral-large-3-675b-instruct-2512` on SAIA right now
  (~5 min/call, within the 300s client timeout). The earlier "crash" was most likely the same
  slowness without a token resolved: long page-count load, then `SystemExit("Missing SAIA token…")`
  at the guard (no `.env` exists; token comes from arg2 / `SAIA_TOKEN`).
- **Guidance given (no code changed; live round left running).** Safe to Ctrl-C — every paper is
  checkpointed on return and `confirm_positives` resumes from the checkpoint (the checkpoint IS the
  cursor), losing at most the in-flight paper. For a faster narrowing loop, re-run with a small
  `--advance` (5–10) — you only need a trickle of new `new_suggestion` candidates. Leave the 300s
  timeout alone (calls are succeeding, just slow; lowering it would discard slow successes).
- **Follow-up features requested (tasks #8–#10, DEFERRED until the live round finishes so we don't
  disturb PID 25852):** (8) SAIA connectivity preflight (reachable + auth ok, fail-fast) before the
  long loop; (9) mount/folder availability check (corpus Z:\ / `\\DC01` + `LNI_DATA_ROOT` dirs)
  fail-fast; (10) a passive background progress/heartbeat monitor that tails the checkpoint and
  reports rows-done + avg sec/paper + ETA so "glacial but working" is visible.

### 2026-06-22 — recover-work: reconciled the unlogged 06-22 `category_schema.yaml` hand-edit
- **Why this pass.** `/recover-work` after an interrupted session. Anchored on mtimes (notes last
  updated 06-20 12:36): the **only** file newer was `prompts/category_schema.yaml` (06-22 09:08) —
  the crash site / in-flight work. Everything else in `src/`, `tests/`, `goldstandard/` was ≤06-20
  and matched the prior State. No python/cmd/quarto process was running (nothing to interrupt).
- **What the 06-22 edit did (reconstructed via `git diff HEAD` minus the logged 06-19 migration).**
  Discovered the schema is now git-TRACKED (HEAD `ee8ba23`, 06-19 09:49, still has `methodology`),
  so `git diff HEAD` bundles the whole methodology→software_lifecycle migration with today's edit.
  Subtracting the already-logged migration, today's hand-edit = a schema cleanup: removed two bogus
  `nan` coder categories (`techstack`, `evaluation`; `key: nan, source: coder:bob, description: ''`
  — the artifact the 06-18 INSUFFICIENT_INFO sentinel was meant to replace), and added `cmd_tool`
  + `analysis_pipeline` (`software_type` active) and `benchmarking` (`evaluation` active), all with
  descriptions. The edit was COMPLETE — not a half-migrated crash.
- **The one mismatch found & fixed (the recovery target).** The newly-added software_type key was
  written `analysis pipeline` **with a space** — the only key in the whole schema not snake_case,
  and the mistral checkpoint data emits `analysis_pipeline` (underscore) everywhere, so the spaced
  key would never exact-match the model's output (it'd register as a separate category in
  `collect`/ICR). Renamed the key to **`analysis_pipeline`**. Safe: grep confirmed the spaced form
  is in NO coding CSV (coders coded under the old schema), and `analysis_pipeline` already exists in
  the checkpoint data — so the rename aligns the schema with the data, it doesn't orphan anything.
- **Verified (offline, no token, no corpus).** Schema loads through `categories.py`/`schema_io.py`:
  5 dims (`research_position, software_lifecycle, software_type, techstack, evaluation`; `methodology`
  gone), `render_categories_block()` builds (9893 chars), zero keys with spaces remain. Confirmed no
  lingering `nan` category in `coding_alice.csv`/`coding_bob.csv` (so the schema removal isn't
  silently undone by a coder file a future `synccats` would re-read). **NOT run:** any token/live
  step, the interactive coding loop.
- **Surfaced, deliberately NOT changed.** Two active coder categories still have empty descriptions
  and are therefore EXCLUDED-from-prompt + warned by `categories.py`: `research_position: testing`
  (coder:alice), `techstack: formal_specification_languages` (coder:bob). These need a HUMAN one-line
  description (the coder's intended meaning) — auto-authoring them would fabricate the typology, so
  they're left for Julian. Until filled they simply don't appear in the model prompt.
- **Carried-over dangling (unchanged, token-blocked).** The 06-19 migration's data-level work is
  still owed: `a-gold` (token) to give the gold papers `software_lifecycle_*` model annotations, then
  a `gold` coding pass for the brand-new dimension. See the 06-20 migration Log entry + State → Next.
- **Not committed.** All of the above plus the migration remain uncommitted in `lni_study` vs HEAD
  `ee8ba23`. Commit only on request.

### 2026-06-20 — added `--reannotate` force-redo flag (jump-start `software_lifecycle` mining)
- **Why.** After the 06-19 `methodology`→`software_lifecycle` migration, `collect` only sees
  the new dimension on papers annotated under the new schema. Normally those trickle in via
  `advance` (50 new papers at a time). User asked for a flag that "forces a new set of annotated
  papers to quicker start that process" — i.e. re-annotate the papers ALREADY confirmed so the
  whole narrow_confirmed set carries `software_lifecycle_new_suggestion` at once.
- **What changed.**
  - `src/confirm_positives.py`: new `--reannotate` arg + a worklist branch that selects the
    already-confirmed (label==1) candidates of `--set` (cap with `--advance N`), and a new
    `purge_checkpoint_ids()` helper that drops those ids from the checkpoint up front (archiving a
    timestamp-free `.bak`, mirroring `annotate_lni --overwrite`) and `done.pop`s them, so the
    re-run REPLACES rather than appends duplicate rows. SAIA token check runs BEFORE the purge, so
    `--reannotate` without a token exits non-destructively.
  - `run_pipeline.cmd`: new `reannotate` dispatch + `:reannotate` body + header/usage doc.
    Usage: `run_pipeline.cmd reannotate <token> "" narrow` (redo all confirmed) or
    `... narrow 20` (cap at 20). Hint points to `collect "" "" "" r1` next.
- **Why it's correct end-to-end.** Confirmed `annotate_lni.CHECKPOINT_COLUMNS` is built
  dynamically from `cat.DIMENSIONS` (`flatten_annotation({}).keys()`), so re-annotated rows AND
  the reindexed kept rows align to the CURRENT schema (`software_lifecycle_*`), and the stale
  `methodology_*` cells drop out. So `collect` (mines `_new_suggestion` from label==1 rows) sees
  the new dimension right after a `reannotate` round.
- **Verified (offline only).** `py_compile` passes. `purge_checkpoint_ids` tested on a COPY of the
  real narrow checkpoint: 268→265 rows after dropping 3 ids, redo ids absent, no duplicate ids,
  columns aligned to `CHECKPOINT_COLUMNS`, `.bak` created. **NOT verified:** the live re-annotation
  loop (needs a SAIA token) and the full `reannotate → collect → review` cycle against real data.
- **Next.** When a token is available: `reannotate narrow` (or capped) → `collect "" "" "" r1`
  → `review`; separately still owe `a-gold` + a `gold` pass for `software_lifecycle` (see State).
- **Caveat to remember.** A capped `--advance N` reannotate leaves confirmed papers beyond N with
  NaN `software_lifecycle_*` until a later round redoes them — by design (token budget), not a bug.

### 2026-06-20 — recover-work: logged the unlogged 06-19 `methodology`→`software_lifecycle` migration; no run to interrupt
- **Why this pass.** User asked to "save the current state for continuation and safely
  interrupt the run." The 2026-06-19 work was entirely UNLOGGED (this file's State said
  "Last updated 2026-06-18 / nothing running"), so recovered intent from mtimes + the new
  `software_prozesskategorien.md` note + schema backups rather than git.
- **What happened on 06-19 (reconstructed).** The `methodology` typology dimension was
  **replaced by `software_lifecycle`** — the six classical SW-lifecycle phases
  (projektdefinition_hintergrund, anforderungen, entwurf, implementierung,
  testen_qualitaetssicherung, deployment_betrieb) seeded from `software_prozesskategorien.md`
  ("Dies statt der Methodologiefrage"). Done by **hand-editing `prompts/category_schema.yaml`**
  (13:42 backup → `category_schema.backup-2026-06-19.yaml`; final edit 14:57). The old
  `methodology` block is preserved in that backup + a removal comment in the YAML.
  Also added `pipeline_workflow.qmd`/`.html` (mermaid diagram of `run_pipeline.cmd`).
- **Coders ran a gold session** (`goldstandard/coding_{alice,bob}.csv`, 15:32; pre-edit copies
  in `*.backup-2026-06-19.csv`). Both coded the gate + `research_position`, `software_type`,
  `techstack`, `evaluation` and **deliberately skipped the old `methodology` dimension** — which
  is what motivated the replacement. (alice 20 gate rows; bob 16.)
- **Consistency check after the migration (read + grep, NOT run live):**
  - `categories.py` derives `DIMENSIONS`/`TYPOLOGY` from the YAML, so the rename needed **no
    Python change**. Confirmed **no `src/*.py` references `methodology`** (grep) — the only
    `methodology` hits left are docs, the YAML backups, the old gold model-annotation checkpoint,
    and stale candidate CSVs.
  - `build_goldstandard.py` walks `cat.DIMENSIONS` dynamically and reads model columns via
    `row.get(f"{dim}_category")`, so the now-absent `software_lifecycle_category` column just
    yields `None` (no model suggestion shown) instead of crashing. **Migration is code-complete.**
- **DANGLING / data-level (the real recovery target — needs token, NOT done here):**
  1. The gold model-annotation checkpoint
     `results/checkpoints/annotations_goldconfirm_..._run_1_checkpoint.csv` still has
     `methodology_*` columns and **no `software_lifecycle_*` columns** (annotated under the old
     schema). So in the coding UI the new dimension has **no model suggestion**. Re-run **`a-gold`**
     (🔑 token) over `.workingset/gold` to annotate `software_lifecycle` under the new prompt.
     Beware the known straggler-skip gotcha (use `a-gold <token> overwrite` if a clean re-annotate
     is wanted).
  2. `software_lifecycle` is a **brand-new, never-coded** dimension — alice/bob's existing rows do
     not cover it; a follow-up `gold` coding pass is needed (resumes at first undecided paper).
  3. The old `methodology_*` data in the gold checkpoint is now orphaned (harmless; ignored by the
     new dims' `row.get`).
  4. `ideas.md` (separate, NOT started): a utility to sync coder working files (papers +
     checkpoints) to `P:\24-0012_KTS_RSE-Master\05_Research\lni_study_working_files` so the 2nd
     coder can proceed after the top-up; keep backups + git-pull in sync.
- **"Interrupt the run":** at recovery time **no python/cmd/quarto/biber process was running**
  (checked `Get-CimInstance Win32_Process` + `Get-Process`) — nothing to kill. Any interactive
  `build_goldstandard.py` session lives in a coder's own terminal and is **resumable**
  (full-rewrite persistence after every decision), so Ctrl-C there loses nothing.
- **Verified:** code-consistency by reading + grep only. **NOT** run: `py_compile`, any live/token
  step, or the interactive coding loop.

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
