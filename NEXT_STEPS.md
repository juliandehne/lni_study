# lni_study — task log

_Last updated: 2026-06-16. This file is the durable, on-disk progress record for
the lni_study pipeline (see the `task-logging` / `recover-work` skills). It has a
**State** snapshot (overwritten each update) and an **append-only Log** (newest
first, never edited)._

## State  (current snapshot — overwrite each update)

- **Now / in flight:** nothing actively running. (An interrupted edit to the
  review CLI — explicit `[f]orward` navigation — was recovered & reconciled on
  2026-06-16; see the top Log entry. Code consistent, docs updated.) The old
  `estimate` process (PID 20484) has **finished** (no python running; score cache stopped growing at
  15:38, 1800 papers scored). Working sets are filled and **consistent** (manifest
  rows == PDFs on disk): narrow 50 / gold 100 / final 500 / pool 779. The pipeline
  was reworked into a **streaming estimator** that fills the working sets directly,
  plus an optional **LLM-confirm** step replacing the old `a-candidates` + `filter` pair.

- **Done & verified:**
  - `run_pipeline.cmd` is internally consistent — every `goto` resolves, and the
    `estimate` / `confirm` / `full` calls match the current Python arg surfaces
    (verified by grepping goto targets ↔ labels and reading each call site).

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
    New step order: `deps | dry | test | estimate | confirm | collect | review |
    a-gold | gold | icr | full`. Removed `a-candidates`, `filter`, `ws-narrow`,
    `ws-gold` (estimate fills those sets directly).

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
  4. **`confirm --set narrow`** (token) → **`collect`** → **`review`**.
  5. **`confirm --set gold --target 100`** (token) → **`a-gold` → `gold` → `icr`**.
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
  - **Not committed:** `publications` is a submodule with local changes — decide
    when to commit.

## Log  (APPEND-ONLY — newest entry at the top, never edit past entries)

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
