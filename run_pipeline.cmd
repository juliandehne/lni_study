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
REM     collect       A2     - aggregate subcategory candidates from the narrow set.
REM                            Self-contained: with a token it annotates the narrow
REM                            papers itself (cached to a checkpoint, so re-runs
REM                            spend no new token), then mines candidates. Token
REM                            optional - without one it only reuses existing
REM                            annotations in results\checkpoints.
REM     review        A2     - human accept/decline -> category_whitelist.json (no token)
REM     a-gold        A      - re-annotate the gold papers w/ enriched prompt (needs token)
REM     gold          B      - interactive two-coder goldstandard (no token)
REM     icr           B      - intercoder reliability (no token)
REM     full          C      - final study: annotate the .workingset\final set the
REM                            estimate step already drew, per model (needs token).
REM
REM  Pipeline idea: the estimator STREAMS the corpus (folder-weighted draw, each PDF
REM  equally likely) and stops as soon as it has filled narrow/gold/final and a
REM  capped pool of likely-RSE papers, so neither extraction nor the SAIA API ever
REM  touches more of the corpus than necessary. 'confirm' optionally upgrades a set
REM  to LLM-confirmed positives, topping up from the pool.
REM ----------------------------------------------------------------------------
REM  EDIT THESE TWO PLACEHOLDERS before running token steps:
REM ============================================================================

set "PY=C:\Users\julian.dehne\AppData\Local\Programs\Python\Python313\python.exe"

REM  --- PLACEHOLDER 1: path to the LNI corpus (folder of lni* volume subfolders)
set "CORPUS=Z:\Publikationen\LNI\Proceedings"

REM  --- PLACEHOLDER 2: SAIA token (OPTIONAL here). Resolved in priority order:
REM      1. second argument:  run_pipeline.cmd <step> <token>
REM      2. SAIA_TOKEN environment variable (export it in your shell beforehand)
REM      3. the placeholder below (paste your token in place of <SAIA_TOKEN>)
REM      4. or leave all unset and put SAIA_API_KEY in lni_study\.env (.env.example)
REM      Token steps pass --saia_token only when a real token is resolved.
REM  Note: do NOT clobber a SAIA_TOKEN already set in the environment.
if not defined SAIA_TOKEN set "SAIA_TOKEN=<SAIA_TOKEN>"

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
set "MODEL=mistral-large-3-675b-instruct-2512"
set "CODER=alice"

REM ----------------------------------------------------------------------------
REM  Always run from the lni_study folder (so results\ .workingset\ .env resolve).
cd /d "%~dp0"

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

if "%~1"==""             goto usage
if /i "%~1"=="deps"         goto deps
if /i "%~1"=="dry"          goto dry
if /i "%~1"=="test"         goto test
if /i "%~1"=="estimate"     goto estimate
if /i "%~1"=="manifests"    goto manifests
if /i "%~1"=="confirm"      goto confirm
if /i "%~1"=="collect"      goto collect
if /i "%~1"=="review"       goto review
if /i "%~1"=="a-gold"       goto a_gold
if /i "%~1"=="gold"         goto gold
if /i "%~1"=="icr"          goto icr
if /i "%~1"=="full"         goto full
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
  --narrow %NARROW% --gold %GOLD% --final %FULL_N% --cap %CAP%
goto end

:manifests
REM  E (recovery) - rebuild .workingset\*\manifest.csv from the PDFs already copied
REM  into the sets + the score cache, WITHOUT re-scanning the corpus. Use if an
REM  'estimate' run copied the PDFs but was interrupted before writing manifests
REM  (symptom: 'No manifest at ...\manifest.csv' from confirm/full). No token.
"%PY%" src\select_candidates.py --corpus "%CORPUS%" --min_score %MIN_SCORE% ^
  --narrow %NARROW% --gold %GOLD% --final %FULL_N% --cap %CAP% --regen_manifests
goto end

:confirm
REM  E - OPTIONAL: LLM-confirm a working set (%CSET%) in batches of 50, keeping
REM  label_research_software==1 and topping up from .workingset\pool until the
REM  target is reached -> .workingset\%CSET%_confirmed (merges the old
REM  a-candidates + filter steps). Needs token. Choose set/target via 4th/5th args:
REM     run_pipeline.cmd confirm ^<token^> "" narrow 50
"%PY%" src\confirm_positives.py --set %CSET% %CTARGET_ARG% --model %MODEL% %TOKEN_ARG%
goto end

:collect
REM  A2 - aggregate candidate subcategories from the narrow set. Self-contained:
REM  with a token, annotates any narrow papers not already in results\checkpoints
REM  (caching them so a re-run is free) and then mines subcategory candidates - no
REM  separate 'confirm --set narrow' needed. Without a token it skips annotation
REM  and only mines whatever is already checkpointed.
set "ANNOTATE_ARG="
if not "%SAIA_TOKEN%"=="<SAIA_TOKEN>" if not "%SAIA_TOKEN%"=="" set "SAIA_API_KEY=%SAIA_TOKEN%"
if not "%SAIA_TOKEN%"=="<SAIA_TOKEN>" if not "%SAIA_TOKEN%"=="" set "ANNOTATE_ARG=--annotate_missing"
"%PY%" src\narrow_categories.py --mode collect --corpus .workingset\narrow --sample %NARROW% %ANNOTATE_ARG%
goto end

:review
REM  A2 - human accept/decline CLI -> prompts\category_whitelist.json. No token.
"%PY%" src\narrow_categories.py --mode review
goto end

:a_gold
REM  Phase A on the 100 gold papers, now with the enriched (whitelist) prompt. Token.
REM  --no_stage: the gold set already lives on a fast local disc.
"%PY%" src\annotate_lni.py --lni_folder .workingset\gold --no_stage %TOKEN_ARG%
goto end

:gold
REM  Phase B - interactive goldstandard coding. No token (opens PDFs in browser).
"%PY%" src\build_goldstandard.py --username %CODER% --pdf_folder .workingset\gold
goto end

:icr
REM  Phase B - intercoder reliability over the shared goldstandard\ folder. No token.
"%PY%" src\compute_icr.py --shared_folder goldstandard
goto end

:full
REM  Phase C - final study: annotate the .workingset\final set the ESTIMATE step
REM  already drew (a folder-balanced sample of likely-research-software papers),
REM  per model. Needs token. --no_stage: the set already lives on a fast local disc.
REM  Size is fixed at estimate time (--final / 3rd arg); delete .workingset\final
REM  and re-run estimate to reselect. Run once per model, then aggregate (majority
REM  vote): repeat with --model llama-... / gemma-... and --run run_2 / run_3.
if not exist ".workingset\final\manifest.csv" (
  echo .workingset\final\manifest.csv not found - run the 'estimate' step first.
  goto end
)
"%PY%" src\annotate_lni.py --lni_folder .workingset\final --no_stage ^
  --model %MODEL% --run run_1 %TOKEN_ARG%
goto end

:usage
echo.
echo   run_pipeline.cmd ^<step^> [^<saia_token^>] [^<full_sample_n^>] [^<confirm_set^>] [^<confirm_target^>]
echo.
echo   deps ^| dry ^| test ^| estimate ^| manifests ^| confirm ^| collect ^| review
echo   a-gold ^| gold ^| icr ^| full
echo.
echo   SAIA token: pass as 2nd arg, or set SAIA_TOKEN in the environment, or
echo   edit the placeholder at the top, or put SAIA_API_KEY in .env.
echo   3rd arg = final-study sample size, used by estimate/full (default %FULL_N%).
echo   4th/5th args = confirm step's working set + target (default gold, set size).
echo   Edit CORPUS at the top of this file if it is not already set.
goto end

:end