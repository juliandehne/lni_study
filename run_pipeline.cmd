@echo off
REM ============================================================================
REM  run_pipeline.cmd - step-by-step driver for the lni_study annotation pipeline
REM ----------------------------------------------------------------------------
REM  Usage:   run_pipeline.cmd <step> [<saia_token>]
REM  Run ONE step at a time and inspect its artifact before moving on.
REM
REM  Steps (in pipeline order):
REM     deps          pip install -r requirements.txt
REM     dry           Step 0 - offline dry run, NO token (extraction + prompt)
REM     test          Step 1 - 5-paper live test (needs token)
REM     estimate      E      - non-LLM estimator STREAMS the corpus folder-balanced
REM                            and copies score>=%MIN_SCORE% papers straight into
REM                            .workingset\narrow (%NARROW%), \gold (%GOLD%),
REM                            \final (%FINAL%) and \pool (the rest, up to %CAP%
REM                            total), stopping early. NO token.
REM     manifests     E      - RECOVERY: rebuild .workingset\*\manifest.csv from the
REM                            PDFs + score cache, no corpus scan. Use if 'estimate'
REM                            was interrupted before writing manifests. NO token.
REM     confirm       E      - OPTIONAL: LLM-confirm a working set in batches of 50,
REM                            keeping label==1 and topping up from \pool until the
REM                            target is reached -> .workingset\<set>_confirmed
REM                            (merges the old a-candidates + filter). Needs token.
REM                            Set + target via 4th/5th args (default: gold 100).
REM   --- Category-narrowing LOOP (grounded-theory theoretical sampling). Repeat
REM       one round per invocation until the typology SATURATES (collect adds 0 new
REM       candidates for ~2 rounds), then lock the schema and run a-gold/gold:
REM     round         L      - ONE full loop iteration in a single command: runs
REM                            advance -> collect -> review back-to-back (aborts the
REM                            round if advance or collect fails). Needs token (only
REM                            the advance sub-step spends it). 5th arg = round label
REM                            (e.g. r2) stamped on the new candidates; advance always
REM                            walks the default %NARROW%-paper batch here. This is the
REM                            normal way to run the loop; the three steps below are
REM                            the same stages exposed individually for re-runs/debug.
REM     reannotate    L      - FORCE-REDO: re-annotate the papers ALREADY confirmed
REM                            (label==1) in a set under the CURRENT schema, instead of
REM                            waiting for 'advance' to add new ones. Run once right
REM                            after changing the typology so the next 'collect' mines
REM                            the new dimension across the whole confirmed set. Needs
REM                            token. 4th arg = set (default narrow); 5th = optional cap
REM                            on how many to redo. Old checkpoint rows archived to .bak.
REM     advance       L      - LLM-confirm the NEXT %NARROW% not-yet-annotated papers
REM                            of the narrow set (+ \pool topup), walking a cursor so
REM                            each call feeds another batch into the loop. Grows
REM                            .workingset\narrow_confirmed. Needs token. Override the
REM                            batch size with the 5th arg.
REM     collect       L      - mine the model's new_suggestion subcategories over the
REM                            (grown) narrow_confirmed set and APPEND the new ones to
REM                            the `candidates` buckets of prompts\category_schema.yaml
REM                            (merge, not clobber). No token. 5th arg = round label
REM                            (e.g. r2) for saturation tracking.
REM     review        L      - human accept/decline over the schema's pending
REM                            `candidates`: accept -> active (+German description),
REM                            decline -> rejected (+reason). Round-trips the YAML
REM                            (comments survive); re-runnable. Hand-editing
REM                            prompts\category_schema.yaml is an equivalent path. No token.
REM     a-gold        A      - re-annotate the gold papers w/ enriched prompt (needs token).
REM                            3rd arg "overwrite" re-does ALL gold papers (archives the
REM                            old checkpoint to .bak); without it, resumes/skips done ones.
REM     fill-gold     A      - INCREMENTAL, two regimes (one targeted call per paper,
REM                            merging just the queried dimensions' cells back):
REM                              * paper NOT yet coded by either human coder -> FULL
REM                                REFRESH: re-query EVERY dimension, so newly-created
REM                                subcategories are reconsidered even where a model
REM                                answer already exists.
REM                              * paper already coded by a coder -> ABSENT-ONLY: ask
REM                                only about dimensions whose category cell is missing,
REM                                so its coded baseline / ICR comparison is not churned.
REM                            Non-RSE rows and papers not in the checkpoint are left
REM                            untouched; papers a human REJECTED as not-RS (rs=0) are
REM                            skipped by default (never enter the goldstandard); the
REM                            checkpoint is backed up to .bak first.
REM                            "coded" = id appears in any goldstandard\coding_*.csv. Use
REM                            after a schema change ADDS a dimension (e.g.
REM                            software_lifecycle) or new subcategories. Token.
REM                            3rd arg "absent-only" forces ABSENT-ONLY for EVERY paper
REM                            (incl. uncoded): fills only blank cells, no full refresh
REM                            -- much faster when you just want to finish the gaps.
REM     preview       -      - PRINT every prompt (system + full annotation + targeted
REM                            fill) with char/token sizes; no corpus, no PDF, NO token.
REM                            Also written to results\prompt_preview.txt. Use to
REM                            inspect/shrink the prompts before paying for a run.
REM     gold          B      - interactive two-coder goldstandard (no token). First
REM                            runs 'synccats' so the OTHER coder's newly-coined
REM                            categories are already in the knowledge base.
REM     synccats      B      - integrate coder-created categories into the schema:
REM                            reads each coder's coding_*.csv (is_new rows) +
REM                            new_categories_*.csv sidecars and appends every new
REM                            subcategory to prompts\category_schema.yaml's `active`
REM                            bucket as groundtruth (source: coder:<names>). Run on
REM                            its own, or automatically as the first half of 'gold'.
REM                            No token. (Reason: the other coder is unlikely to
REM                            independently invent the same category AND name, so
REM                            without this it would count as pure ICR disagreement.)
REM     topup         B      - AFTER a gold pass: separate the human-confirmed (rs=1)
REM                            papers from the rejected (rs=0) into goldstandard\
REM                            gold_human_{confirmed,rejected}_<coder>.csv, then refill
REM                            .workingset\gold_confirmed back to the target so the
REM                            coder reaches %GOLD% confirmed RSE papers. Target =
REM                            %GOLD% + #rejected, and is bumped +20 once confirmations
REM                            come within 10 of %GOLD% (so enough RSE papers are
REM                            found). Spends token ONLY to annotate new pool papers,
REM                            and only when a token is given (else it prints the
REM                            command). Then re-run 'gold' to code the added papers.
REM     icr           B      - intercoder reliability (no token)
REM     full          C      - final study: annotate the .workingset\final set the
REM                            estimate step already drew, per model (needs token).
REM
REM  Pipeline idea: the estimator STREAMS the corpus (folder-weighted draw, each PDF
REM  equally likely) and stops as soon as it has filled narrow/gold/final and a
REM  capped pool of likely-RSE papers, so neither extraction nor the SAIA API ever
REM  touches more of the corpus than necessary. 'confirm' optionally upgrades a set
REM  to LLM-confirmed positives, topping up from the pool.
REM
REM  Source of truth for the typology is prompts\category_schema.yaml (read by
REM  categories.py; category_whitelist.json is retired). The narrowing loop
REM  (advance -> collect -> review) refines that schema BEFORE the goldstandard:
REM  each round confirms another %NARROW% papers, mines the subcategories the model
REM  proposed for them, and the human accepts/rejects them in the YAML. Stop when
REM  collect reports "+0 NEW candidates" for ~2 consecutive rounds (saturation).
REM ----------------------------------------------------------------------------
REM  EDIT THESE TWO PLACEHOLDERS before running token steps:
REM ============================================================================

REM  --- Python interpreter. Override with LNI_PYTHON=full\path\to\python.exe;
REM      otherwise use this user's Python 3.13 LocalAppData install, then PATH.
if defined LNI_PYTHON (
    set "PY=%LNI_PYTHON%"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
) else (
    set "PY=python"
)

REM  --- PLACEHOLDER 1: path to the LNI corpus (folder of lni* volume subfolders)
REM      An LNI_CORPUS environment variable (e.g. exported by pipeline_menu.py)
REM      overrides this placeholder, so the corpus can be affirmed/redirected the
REM      same way LNI_DATA_ROOT redirects the working dir.
set "CORPUS=Z:\Publikationen\LNI\Proceedings"
if defined LNI_CORPUS set "CORPUS=%LNI_CORPUS%"

REM  --- PLACEHOLDER 2: SAIA token (OPTIONAL here). Resolved in priority order:
REM      1. second argument:  run_pipeline.cmd <step> <token>
REM      2. SAIA_TOKEN environment variable (export it in your shell beforehand)
REM      3. the placeholder below (paste your token in place of <SAIA_TOKEN>)
REM      4. or leave all unset and put SAIA_API_KEY in lni_study\.env (.env.example)
REM      Token steps pass --saia_token only when a real token is resolved.
REM  Note: do NOT clobber a SAIA_TOKEN already set in the environment.
if not defined SAIA_TOKEN set "SAIA_TOKEN=<SAIA_TOKEN>"

REM  --- PLACEHOLDER 3: working-data root for ALL GENERATED data - results\,
REM      .workingset\ and goldstandard\.  Leave BLANK to keep generated data inside
REM      the repo (default, backward-compatible).  Set it to an external dir to
REM      redirect everything there, e.g.:
REM        set "DATA_DEFAULT=P:\24-0012_KTS_RSE-Master\05_Research\lni_study_working_files"
REM      Resolution order (first non-empty wins):
REM        1. LNI_DATA_ROOT environment variable (export it in your shell)
REM        2. the DATA_DEFAULT placeholder below
REM        3. the repo folder (this script's dir) - in-repo data
REM      Prompts/schema (prompts\category_schema.yaml) ALWAYS stay in the repo - they
REM      are committed config, never moved to the data root.
set "DATA_DEFAULT="

REM  --- Other knobs (the estimate step fills the working sets in this order).
REM  MIN_SCORE: estimator gate - a paper is a research-software candidate when its
REM  non-LLM score is >= this.  NARROW / GOLD: subcategory-narrowing + goldstandard
REM  set sizes.  FULL_N: final-study set size (.workingset\final).  CAP: stop the
REM  scan after this many estimator-positives total - the leftover
REM  (CAP - NARROW - GOLD - FULL_N) becomes the \pool reservoir 'confirm' tops up from.
set "MIN_SCORE=2.0"
set "NARROW=50"
set "GOLD=100"
REM  Final-study size. Override with a THIRD argument, see below.
set "FULL_N=500"
set "CAP=2000"
REM  Short-paper cap: a paper with fewer than SHORT_PAGES pages is "short"
REM  (abstracts / posters / front-matter the extractor + coders struggle with).
REM  At most MAX_SHORT_FRAC of the \pool reservoir AND of the 'confirm' top-up draw
REM  from it may be short - over-quota shorts are skipped so the gold pool stays
REM  >=80%% full papers (enforced by select_candidates + confirm_positives).
set "SHORT_PAGES=6"
set "MAX_SHORT_FRAC=0.20"
set "MODEL=mistral-large-3-675b-instruct-2512"
REM  ADVANCE_MODEL: model used ONLY by the narrowing-LOOP token steps - advance, the
REM  advance sub-step of 'round', and reannotate. Those steps merely MINE candidate
REM  subcategories from the model's new_suggestion fields, so a faster / smaller model
REM  is good enough and cuts the per-paper latency that dominates the loop. The
REM  final-grade steps (a-gold / full / confirm / topup) ALWAYS keep the full %MODEL%.
REM  Defaults to %MODEL% (so behaviour is unchanged until you opt in). Override here or
REM  export LNI_ADVANCE_MODEL=<faster-saia-model-id> (e.g. from pipeline_menu.py).
set "ADVANCE_MODEL=%MODEL%"
if defined LNI_ADVANCE_MODEL set "ADVANCE_MODEL=%LNI_ADVANCE_MODEL%"
set "CODER=bob"

REM ----------------------------------------------------------------------------
REM  Always run from the lni_study folder (so src\ prompts\ .env resolve).
cd /d "%~dp0"

REM  Resolve the working-data root: env var wins, then the DATA_DEFAULT placeholder,
REM  then the repo folder (in-repo data).  %DATA% is the chosen root; LNI_DATA_ROOT is
REM  EXPORTED so every Python script redirects results\ .workingset\ goldstandard\ to
REM  it (see DATA_ROOT in annotate_lni.py, confirm_positives.py, ...). Prompts stay put.
REM  Backward compatible: with neither LNI_DATA_ROOT nor DATA_DEFAULT set, %DATA%
REM  falls back to %CD% (the lni_study repo folder), i.e. the original in-repo paths.
if not defined LNI_DATA_ROOT set "LNI_DATA_ROOT=%DATA_DEFAULT%"
if "%LNI_DATA_ROOT%"=="" set "LNI_DATA_ROOT=%CD%"
set "DATA=%LNI_DATA_ROOT%"

REM  Safety: the working dir must NOT be the corpus (read-only source of the PDFs).
REM  The pipeline COPIES working sets and WRITES results/checkpoints under %DATA%;
REM  pointing it at the corpus would pollute or overwrite the source. Compare with any
REM  trailing backslash stripped so "Z:\x" and "Z:\x\" still match.
set "DATA_CHK=%DATA%"
if "%DATA_CHK:~-1%"=="\" set "DATA_CHK=%DATA_CHK:~0,-1%"
set "CORPUS_CHK=%CORPUS%"
if "%CORPUS_CHK:~-1%"=="\" set "CORPUS_CHK=%CORPUS_CHK:~0,-1%"
if /i "%DATA_CHK%"=="%CORPUS_CHK%" (
  echo.
  echo ERROR: the working dir equals the corpus ^(the read-only PDF source^):
  echo        working dir : %DATA%
  echo        corpus      : %CORPUS%
  echo        Set LNI_DATA_ROOT ^(or DATA_DEFAULT^) to a SEPARATE folder so results
  echo        and .workingset never overwrite the source PDFs.
  goto end
)

if not exist "%DATA%\.workingset"         mkdir "%DATA%\.workingset"         2>nul
if not exist "%DATA%\results\checkpoints" mkdir "%DATA%\results\checkpoints" 2>nul
if not exist "%DATA%\goldstandard"        mkdir "%DATA%\goldstandard"        2>nul

REM  A token given as the SECOND argument overrides the env var / placeholder.
if not "%~2"=="" set "SAIA_TOKEN=%~2"
REM  Pass --saia_token only when a real token was resolved (else Python uses .env).
set "TOKEN_ARG="
if not "%SAIA_TOKEN%"=="<SAIA_TOKEN>" if not "%SAIA_TOKEN%"=="" set "TOKEN_ARG=--saia_token %SAIA_TOKEN%"

REM  An optional THIRD argument overrides the final-study sample size (estimate/full).
if not "%~3"=="" set "FULL_N=%~3"

REM  confirm step: 4th arg = working set to confirm (default gold), 5th = target count
REM  (default: the size of that set's manifest, decided inside confirm_positives.py).
set "CSET=gold"
if not "%~4"=="" set "CSET=%~4"
set "CTARGET_ARG="
if not "%~5"=="" set "CTARGET_ARG=--target %~5"

REM  Narrowing LOOP knobs (steps: advance / collect):
REM   advance step: 5th arg = how many papers to walk the cursor forward (default NARROW).
REM   collect step: 5th arg = optional round label (e.g. r2) for saturation tracking.
REM   round   step: 5th arg = round label (advance is fixed at the default NARROW batch).
set "ADVANCE_N=%NARROW%"
if not "%~5"=="" set "ADVANCE_N=%~5"
set "ROUND_ARG="
if not "%~5"=="" set "ROUND_ARG=--round %~5"

if "%~1"==""             goto usage

REM  --- Active configuration, printed before EVERY step so the user always sees who
REM      is coding, which working dir is in use, and where results are written.
set "TOKEN_SHOWN=resolved (passed to LLM steps)"
if "%TOKEN_ARG%"=="" set "TOKEN_SHOWN=not set (offline / from .env)"
set "DATA_NOTE="
if /i "%DATA%"=="%CD%" set "DATA_NOTE= (in-repo default; set LNI_DATA_ROOT to redirect)"
echo.
echo ====================== lni_study pipeline - config ======================
echo   step          : %~1
echo   coder         : %CODER%
echo   model         : %MODEL%
if /i not "%ADVANCE_MODEL%"=="%MODEL%" echo   loop model    : %ADVANCE_MODEL%   [advance / round / reannotate only]
echo   corpus (PDFs) : %CORPUS%   [read-only source]
echo   working dir   : %DATA%%DATA_NOTE%
echo   - results     : %DATA%\results   [annotations, checkpoints]
echo   - workingset  : %DATA%\.workingset   [PDF sets, manifests]
echo   - goldstandard: %DATA%\goldstandard   [coding_*.csv, icr_*  - shared by coders]
echo   schema        : %~dp0prompts\category_schema.yaml   [in repo, committed]
echo   SAIA token    : %TOKEN_SHOWN%
echo =========================================================================
echo.

if /i "%~1"=="deps"         goto deps
if /i "%~1"=="dry"          goto dry
if /i "%~1"=="preview"      goto preview
if /i "%~1"=="test"         goto test
if /i "%~1"=="estimate"     goto estimate
if /i "%~1"=="manifests"    goto manifests
if /i "%~1"=="confirm"      goto confirm
if /i "%~1"=="round"        goto round
if /i "%~1"=="reannotate"   goto reannotate
if /i "%~1"=="advance"      goto advance
if /i "%~1"=="collect"      goto collect
if /i "%~1"=="review"       goto review
if /i "%~1"=="a-gold"       goto a_gold
if /i "%~1"=="fill-gold"    goto fill_gold
if /i "%~1"=="gold"         goto gold
if /i "%~1"=="synccats"     goto synccats
if /i "%~1"=="topup"        goto topup
if /i "%~1"=="icr"          goto icr
if /i "%~1"=="full"         goto full
if /i "%~1"=="export"       goto export
echo Unknown step: %~1
goto usage

REM ============================================================================
:deps
REM  One-time setup. Also: copy .env.example .env  and add your SAIA token.
"%PY%" -m pip install -r requirements.txt
goto end

:dry
REM  Step 0 - offline, NO token. Verifies PDF extraction + the exact prompt.
REM  Share: results\extraction_report_<vol>.csv + results\sample_prompt_<vol>.txt
"%PY%" src\annotate_lni.py --lni_folder "%CORPUS%" --test --dry_run
goto end

:preview
REM  Prompt preview - offline, NO token, no corpus. Prints the system prompt, the
REM  full annotation user prompt and the targeted fill prompt with char/token sizes.
REM  Share/inspect: results\prompt_preview.txt
"%PY%" src\annotate_lni.py --preview-prompt
goto end

:test
REM  Step 1 - 5-paper live test (stratified). Needs token.
REM  Share: results\checkpoints\annotations_<tag>_checkpoint.csv (5 rows)
"%PY%" src\annotate_lni.py --lni_folder "%CORPUS%" --test %TOKEN_ARG%
goto end

:estimate
REM  E - non-LLM estimator STREAMS the corpus folder-balanced and copies every
REM  score>=%MIN_SCORE% paper straight into .workingset\narrow (%NARROW%), \gold
REM  (%GOLD%), \final (%FULL_N%) and \pool (the rest, up to %CAP% positives total),
REM  stopping early. Scores cache to results\rse_scores_<corpus>.csv (re-runs are
REM  fast / resume an interrupted scan). No token.
"%PY%" src\select_candidates.py --corpus "%CORPUS%" --min_score %MIN_SCORE% ^
  --narrow %NARROW% --gold %GOLD% --final %FULL_N% --cap %CAP% ^
  --short_pages %SHORT_PAGES% --max_short_frac %MAX_SHORT_FRAC%
goto end

:manifests
REM  E (recovery) - rebuild .workingset\*\manifest.csv from the PDFs already copied
REM  into the sets + the score cache, WITHOUT re-scanning the corpus. Use if an
REM  'estimate' run copied the PDFs but was interrupted before writing manifests
REM  (symptom: 'No manifest at ...\manifest.csv' from confirm/full). No token.
"%PY%" src\select_candidates.py --corpus "%CORPUS%" --min_score %MIN_SCORE% ^
  --narrow %NARROW% --gold %GOLD% --final %FULL_N% --cap %CAP% ^
  --short_pages %SHORT_PAGES% --max_short_frac %MAX_SHORT_FRAC% --regen_manifests
goto end

:confirm
REM  E - OPTIONAL: LLM-confirm a working set (%CSET%) in batches of 50, keeping
REM  label_research_software==1 and topping up from .workingset\pool until the
REM  target is reached -> .workingset\%CSET%_confirmed (merges the old
REM  a-candidates + filter steps). Needs token. Choose set/target via 4th/5th args:
REM     run_pipeline.cmd confirm ^<token^> "" narrow 50
"%PY%" src\confirm_positives.py --set %CSET% %CTARGET_ARG% --model %MODEL% ^
  --short_pages %SHORT_PAGES% --max_short_frac %MAX_SHORT_FRAC% %TOKEN_ARG%
goto end

:round
REM  L (loop) - ONE full narrowing iteration in a single command: advance (token) ->
REM  collect (no token) -> review (no token), back-to-back. The advance sub-step is
REM  fixed at the default %NARROW%-paper batch; the 5th arg is the round label (e.g.
REM  r2) passed to collect for saturation tracking. Aborts the round if advance or
REM  collect fails, so review never runs on a half-finished batch.
REM     run_pipeline.cmd round ^<token^> "" "" r2
echo.
echo === narrowing round %~5: advance (%NARROW% papers, token) -^> collect -^> review ===
echo.
echo --- [1/3] advance: confirming the next %NARROW% narrow papers (model %ADVANCE_MODEL%) ---
"%PY%" src\confirm_positives.py --set narrow --advance %NARROW% --model %ADVANCE_MODEL% %TOKEN_ARG%
if errorlevel 1 (
  echo.
  echo *** advance failed ^(see error above^) - aborting the round, schema untouched. ***
  goto end
)
echo.
echo --- [2/3] collect: mining new_suggestion candidates into category_schema.yaml ---
"%PY%" src\narrow_categories.py --mode collect --from_set narrow --to_schema %ROUND_ARG%
if errorlevel 1 (
  echo.
  echo *** collect failed ^(see error above^) - aborting before review. Annotations are
  echo     cached, so re-running 'collect' or 'round' will not re-spend token. ***
  goto end
)
echo.
echo --- [3/3] review: accept/decline the pending candidates ^(or [q]uit to hand-edit^) ---
"%PY%" src\narrow_categories.py --mode review
echo.
echo === round done. Re-run 'round' for the next batch; stop when collect reports ===
echo ===  "+0 NEW candidates" for ~2 rounds in a row ^(saturation^), then lock + a-gold. ===
goto end

:reannotate
REM  L (loop) - FORCE-REDO: re-annotate the papers ALREADY confirmed (label==1) in a
REM  set under the CURRENT schema, instead of waiting for 'advance' to add new ones.
REM  Use once right after changing the typology (e.g. methodology -> software_lifecycle)
REM  so the next 'collect' mines the new dimension across the WHOLE confirmed set.
REM  Needs token. 4th arg = set to redo (default narrow); 5th arg = optional cap on how
REM  many are redone (bounds token spend). Old checkpoint rows are archived to a .bak.
REM     run_pipeline.cmd reannotate ^<token^> "" narrow        (redo all confirmed)
REM     run_pipeline.cmd reannotate ^<token^> "" narrow 20     (redo first 20 only)
set "RSET=narrow"
if not "%~4"=="" set "RSET=%~4"
set "RECAP_ARG="
if not "%~5"=="" set "RECAP_ARG=--advance %~5"
echo === reannotate: re-confirming already-confirmed '%RSET%' papers under the current schema (model %ADVANCE_MODEL%) ===
"%PY%" src\confirm_positives.py --set %RSET% --reannotate --model %ADVANCE_MODEL% %TOKEN_ARG% %RECAP_ARG%
if errorlevel 1 goto end
echo.
echo === reannotated. Next: 'collect' ^(no token, narrow set^) to mine the refreshed ===
echo ===  suggestions:  run_pipeline.cmd collect "" "" "" r1    ^(or run a full 'round'^). ===
goto end

:advance
REM  L (loop) - walk the cursor forward: LLM-confirm the NEXT %ADVANCE_N% papers of
REM  the narrow set that are not yet in any checkpoint, topping up from \pool. The
REM  checkpoint membership IS the cursor, so each call feeds another batch into the
REM  loop and grows .workingset\narrow_confirmed (cumulative label==1). Needs token.
REM  Override the batch size with the 5th arg:  run_pipeline.cmd advance ^<token^> "" "" 50
"%PY%" src\confirm_positives.py --set narrow --advance %ADVANCE_N% --model %ADVANCE_MODEL% %TOKEN_ARG%
goto end

:collect
REM  L (loop) - mine the model's new_suggestion subcategories over the (grown)
REM  narrow_confirmed set and APPEND the new ones to the `candidates` buckets of
REM  prompts\category_schema.yaml (merge, not clobber - active/rejected untouched).
REM  No token: reuses the annotations 'advance'/'confirm' already cached. A "+0 NEW
REM  candidates" readout for ~2 rounds in a row means the typology has SATURATED.
REM  5th arg = optional round label (e.g. r2) stamped on new candidates.
"%PY%" src\narrow_categories.py --mode collect --from_set narrow --to_schema %ROUND_ARG%
goto end

:review
REM  L (loop) - human accept/decline over the schema's pending `candidates`:
REM  accept -> active (asks a German description), decline -> rejected (asks a
REM  reason + optional move_to). Round-trips prompts\category_schema.yaml so the
REM  curator's comments survive; re-runnable (skipped candidates stay pending).
REM  Editing the YAML by hand (or via Claude) is an equivalent path. No token.
"%PY%" src\narrow_categories.py --mode review
goto end

:a_gold
REM  Phase A on the 100 gold papers, now with the enriched (whitelist) prompt. Token.
REM  --no_stage: the gold set already lives on a fast local disc.
REM  3rd arg "overwrite" (or "force") = re-annotate ALL gold papers, archiving the
REM  old checkpoint + suggestions to .bak first (else it resumes and skips them).
set "OVERWRITE_ARG="
if /i "%~3"=="overwrite" set "OVERWRITE_ARG=--overwrite"
if /i "%~3"=="force"     set "OVERWRITE_ARG=--overwrite"
"%PY%" src\annotate_lni.py --lni_folder "%DATA%\.workingset\gold" --no_stage %OVERWRITE_ARG% %TOKEN_ARG%
goto end

:fill_gold
REM  Phase A (incremental) - update the gold checkpoint with one targeted SAIA call
REM  per paper, two regimes: papers NOT yet coded by either coder get a FULL REFRESH
REM  (every dimension re-queried, so new subcategories are picked up even where a
REM  model answer exists); papers already coded by a coder get ABSENT-ONLY (just the
REM  missing dimensions) so their coded baseline / ICR comparison is not churned.
REM  Papers a human rejected as not-RS (rs=0) are skipped by default (the annotator's
REM  --no-skip-rejected overrides). Preserves untouched answers; backs the checkpoint
REM  up to .bak first. The right
REM  tool after the schema GAINS a dimension (methodology retired -> software_lifecycle
REM  added) or new subcategories, when a full 'a-gold overwrite' would needlessly redo,
REM  and possibly change, answers that are already correct. Uses the full %MODEL%
REM  (final-grade). Needs token. --no_stage: the gold set is already on a fast disc.
REM  Targets the CONFIRMED gold pool (.workingset\gold_confirmed) and updates the SAME
REM  checkpoint the `gold` coding step reads -- tag 'goldconfirm', which the folder name
REM  would NOT yield (folder is gold_confirmed), so it is named explicitly via
REM  --checkpoint (mirrors build_goldstandard --annotations). The old raw 'gold' set
REM  (.workingset\gold / annotations_gold_*) was retired when `confirm` produced the
REM  confirmed pool on 2026-06-18; its live checkpoint no longer exists (only .bak1-3).
REM  3rd arg "absent-only" forces ABSENT-ONLY for every paper (uncoded ones too):
REM  fills only the blank cells, skips the full refresh -- the fast way to finish gaps.
set "ABSENT_ARG="
if /i "%~3"=="absent-only" set "ABSENT_ARG=--absent-only"
if /i "%~3"=="absent"      set "ABSENT_ARG=--absent-only"
"%PY%" src\annotate_lni.py --lni_folder "%DATA%\.workingset\gold_confirmed" --no_stage ^
  --model %MODEL% --fill-missing %ABSENT_ARG% ^
  --checkpoint "%DATA%\results\checkpoints\annotations_goldconfirm_%MODEL%_rse_typology_prompt_v1_run_1_checkpoint.csv" ^
  %TOKEN_ARG%
goto end

:gold
REM  Phase B - interactive goldstandard coding. No token (opens PDFs in browser).
REM  Codes the CONFIRMED gold pool (100 LLM-confirmed RSE papers) produced by
REM  `confirm ... gold 100`: the original gold set yields ~60 positives, topped up
REM  from \pool to 100. --annotations points at confirm's checkpoint explicitly
REM  (its tag is 'goldconfirm', which auto-discovery by folder name would miss).
REM  To code the raw, unconfirmed gold-100 set instead, swap back to
REM  --pdf_folder .workingset\gold (auto-discovers annotations_gold_*).
REM  First integrate any categories the OTHER coder coined into the schema, so this
REM  coder sees them as first-class options (the knowledge base accumulates).
echo --- integrating coder-created categories into the schema (knowledge base) ---
"%PY%" src\sync_coder_categories.py --shared_folder "%DATA%\goldstandard"
echo.
echo --- verifying schema integrity before coding ---
"%PY%" src\check_schema_integrity.py
if errorlevel 1 (
  echo.
  echo *** schema integrity check FAILED ^(see above^) - NOT launching the coding
  echo     session. The pick-list would mix dimensions. Restore a clean schema
  echo     ^(git checkout prompts\category_schema.yaml or a backup^) and re-run 'gold'. ***
  goto end
)
echo.
REM  NOTE: keep this launch on a SINGLE physical line. build_goldstandard.py is
REM  interactive (reads stdin via input()). With ^ line continuations, cmd.exe
REM  loses its byte offset in this batch file while the child reads stdin and,
REM  after the child exits, resumes parsing mid-command - re-running the tail
REM  ("--shared_folder ...") as a standalone command. That produced the spurious
REM  '"--shared_folder" is not recognized' error right after "Done. Decisions...".
"%PY%" src\build_goldstandard.py --username %CODER% --pdf_folder "%DATA%\.workingset\gold_confirmed" --annotations "%DATA%\results\checkpoints\annotations_goldconfirm_%MODEL%_rse_typology_prompt_v1_run_1_checkpoint.csv" --shared_folder "%DATA%\goldstandard"
goto end

:synccats
REM  Phase B helper - merge coder-created categories (coding_*.csv is_new rows +
REM  new_categories_*.csv description sidecars) into prompts\category_schema.yaml's
REM  `active` bucket as groundtruth (source: coder:<names>). Round-trips the YAML.
REM  Runs automatically as the first half of 'gold'; exposed here for an explicit
REM  pass (e.g. after a coding session, before re-annotating). No token.
"%PY%" src\sync_coder_categories.py --shared_folder "%DATA%\goldstandard"
goto end

:topup
REM  Phase B - run AFTER a 'gold' coding pass. Separates the coder's human-confirmed
REM  (rs=1) papers from the rejected (rs=0) ones into
REM    goldstandard\gold_human_confirmed_%CODER%.csv  (with full typology coding)
REM    goldstandard\gold_human_rejected_%CODER%.csv
REM  then tops up .workingset\gold_confirmed so %CODER% can still reach %GOLD% confirmed
REM  RSE papers: it asks confirm for (%GOLD% + #rejected) LLM-positives, bumping the
REM  goal +20 once confirmations come within 10 of %GOLD%. The refill annotates only
REM  NEW \pool papers (cached/cumulative) and appends them to the SAME goldconfirm
REM  checkpoint 'gold' reads, so re-running 'gold' resumes on the freshly added papers.
REM  Spends token ONLY when one is resolved; without a token it just separates and
REM  prints the confirm command (no quota spent). %CSET% (4th arg) picks the set.
"%PY%" src\topup_goldstandard.py --username %CODER% --set %CSET% --target %GOLD% --model %MODEL% ^
  --short_pages %SHORT_PAGES% --max_short_frac %MAX_SHORT_FRAC% ^
  --shared_folder "%DATA%\goldstandard" --workroot "%DATA%\.workingset" %TOKEN_ARG%
goto end

:icr
REM  Phase B - intercoder reliability over the shared goldstandard\ folder. No token.
"%PY%" src\compute_icr.py --shared_folder "%DATA%\goldstandard"
goto end

:full
REM  Phase C - final study: annotate the .workingset\final set the ESTIMATE step
REM  already drew (a folder-balanced sample of likely-research-software papers),
REM  per model. Needs token. --no_stage: the set already lives on a fast local disc.
REM  Size is fixed at estimate time (--final / 3rd arg); delete .workingset\final
REM  and re-run estimate to reselect. Run once per model, then aggregate (majority
REM  vote): repeat with --model llama-... / gemma-... and --run run_2 / run_3.
if not exist "%DATA%\.workingset\final\manifest.csv" (
  echo %DATA%\.workingset\final\manifest.csv not found - run the 'estimate' step first.
  goto end
)
"%PY%" src\annotate_lni.py --lni_folder "%DATA%\.workingset\final" --no_stage ^
  --model %MODEL% --run run_1 %TOKEN_ARG%
goto end

:export
REM  Utility - copy the generated working files (.workingset, results, goldstandard)
REM  from the current working dir (%DATA%) to the shared team folder so the data is
REM  backed up / handed off (the schema in prompts\ stays in the repo and is NOT
REM  copied). Default destination is the KTS shared drive; override with a 2nd arg:
REM    run_pipeline.cmd export                         (-> default P: location)
REM    run_pipeline.cmd export "D:\some\other\dir"     (custom destination)
REM    run_pipeline.cmd export dry                     (preview, copies nothing)
REM    run_pipeline.cmd export "D:\other" dry          (preview to a custom dest)
REM  Copy is INCREMENTAL and ADDITIVE (robocopy /E): newer/changed files are copied,
REM  identical files skipped, and files only present at the destination are KEPT
REM  (so a teammate's coding_*.csv in goldstandard\ is never deleted). It is NOT a
REM  mirror - nothing at the destination is purged.
set "EXPORT_DEST=P:\24-0012_KTS_RSE-Master\05_Research\lni_study_working_files"
set "EXPORT_L="
set "EXPORT_DRYTXT="
if /i "%~2"=="dry" set "EXPORT_L=/L" & set "EXPORT_DRYTXT=   [DRY RUN - nothing copied]"
if /i "%~3"=="dry" set "EXPORT_L=/L" & set "EXPORT_DRYTXT=   [DRY RUN - nothing copied]"
if not "%~2"=="" if /i not "%~2"=="dry" set "EXPORT_DEST=%~2"

REM  Refuse to export onto itself (source == destination): nothing to do and a
REM  /MIR-free copy would still be a pointless self-copy. Compare trailing-slash-insensitive.
set "SRC_CHK=%DATA%"
if "%SRC_CHK:~-1%"=="\" set "SRC_CHK=%SRC_CHK:~0,-1%"
set "DST_CHK=%EXPORT_DEST%"
if "%DST_CHK:~-1%"=="\" set "DST_CHK=%DST_CHK:~0,-1%"
if /i "%SRC_CHK%"=="%DST_CHK%" (
  echo.
  echo ERROR: source and destination are the same folder:
  echo        %DATA%
  echo        The working dir IS the shared folder ^(LNI_DATA_ROOT points there^), so
  echo        there is nothing to export. Run this from an in-repo / local working dir.
  goto end
)

echo.
echo --- export working files -^> shared folder%EXPORT_DRYTXT% ---
echo   from : %DATA%
echo   to   : %EXPORT_DEST%
echo.
set "EXPORT_FAIL="
for %%D in (.workingset results goldstandard) do (
  echo   [%%D]
  robocopy "%DATA%\%%D" "%EXPORT_DEST%\%%D" /E %EXPORT_L% /R:1 /W:1 /NJH /NJS /NP /NDL
  if errorlevel 8 set "EXPORT_FAIL=1"
)
echo.
if defined EXPORT_FAIL (
  echo *** export FAILED for at least one folder ^(robocopy error ^>=8 above^). Check the
  echo     destination path / drive mapping ^(is P: mounted?^) and permissions. ***
) else if defined EXPORT_L (
  echo Dry run complete - the lines above are what WOULD be copied. Re-run without
  echo 'dry' to perform the copy.
) else (
  echo Export complete: .workingset, results, goldstandard copied to
  echo   %EXPORT_DEST%
)
goto end

:usage
echo.
echo   run_pipeline.cmd ^<step^> [^<saia_token^>] [^<full_sample_n^>] [^<confirm_set^>] [^<confirm_target^>]
echo.
echo   deps ^| dry ^| test ^| estimate ^| manifests ^| confirm
echo   narrowing loop:  round   (= advance -^> collect -^> review; repeat until saturated)
echo                    or run the stages individually:  advance ^| collect ^| review
echo                    reannotate  (force-redo confirmed papers under the current schema)
echo   a-gold ^| fill-gold ^(uncoded papers: refresh all dims; coded papers: fill only missing^)
echo   gold ^(auto-runs synccats first^) ^| synccats ^(coder cats -^> schema^)
echo   topup ^(separate confirmed/rejected + refill to target^) ^| icr ^| full
echo   export ^(copy .workingset/results/goldstandard -^> shared P: folder; additive^)
echo          add a 2nd arg for a custom dest, or 'dry' to preview without copying.
echo.
echo   SAIA token: pass as 2nd arg, or set SAIA_TOKEN in the environment, or
echo   edit the placeholder at the top, or put SAIA_API_KEY in .env.
echo   3rd arg = final-study sample size, used by estimate/full (default %FULL_N%).
echo   4th/5th args = confirm step's working set + target (default gold, set size).
echo   5th arg also = advance batch size (advance step) / round label (collect, round).
echo   Edit CORPUS at the top of this file if it is not already set.
goto end

:end
