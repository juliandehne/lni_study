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
REM     estimate      E      - non-LLM estimator: score the corpus + copy the
REM                            %CAND_N% likeliest research-software papers ->
REM                            .workingset\candidates (NO token)
REM     a-candidates  E      - LLM-annotate the %CAND_N% candidates (needs token)
REM     filter        E      - keep label==1 -> .workingset\positives (NO token)
REM     ws-narrow     W1     - draw 50-paper narrowing set from the positives ->
REM                            .workingset\narrow (NO token)
REM     ws-gold       W1     - draw 100-paper gold set from the positives, disjoint
REM                            from narrow -> .workingset\gold (NO token)
REM     collect       A2     - aggregate subcategory candidates, REUSING the
REM                            candidate annotations (NO token)
REM     review        A2     - human accept/decline -> category_whitelist.json (no token)
REM     a-gold        A      - re-annotate 100 gold papers w/ enriched prompt (needs token)
REM     gold          B      - interactive two-coder goldstandard (no token)
REM     icr           B      - intercoder reliability (no token)
REM     full          C      - final study via the estimator: stratified RANDOM
REM                            sample of %FULL_N% papers from the likely-RSE pool,
REM                            per model (needs token); override size with a 3rd arg.
REM                            Prompts if the estimator pool has < 2000 papers.
REM
REM  Pipeline idea: the estimator pre-filters the corpus to %CAND_N% likely-RSE
REM  papers so the SAIA API only sees those; after annotation we keep the label==1
REM  positives, and BOTH the narrowing and goldstandard sets are drawn from them.
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

REM  --- Other knobs
REM  CAND_N: how many estimator-selected candidate papers to LLM-annotate (the
REM  pool the narrowing + goldstandard sets are later drawn from).
set "CAND_N=500"
REM  Final-study size: the full step annotates a stratified sample of FULL_N papers
REM  (each volume folder is a stratum). Override with a THIRD argument, see below.
set "FULL_N=500"
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

REM  An optional THIRD argument overrides the final-study sample size (full step).
if not "%~3"=="" set "FULL_N=%~3"

if "%~1"==""             goto usage
if /i "%~1"=="deps"         goto deps
if /i "%~1"=="dry"          goto dry
if /i "%~1"=="test"         goto test
if /i "%~1"=="estimate"     goto estimate
if /i "%~1"=="a-candidates" goto a_candidates
if /i "%~1"=="filter"       goto filter
if /i "%~1"=="ws-narrow"    goto ws_narrow
if /i "%~1"=="ws-gold"      goto ws_gold
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
REM  E - non-LLM estimator: score the WHOLE corpus (reads the mount once; scores
REM  cached to results\rse_scores_<corpus>.csv) and copy the %CAND_N% likeliest
REM  research-software papers to .workingset\candidates. No token.
"%PY%" src\select_candidates.py --corpus "%CORPUS%" --name candidates --sample %CAND_N%
goto end

:a_candidates
REM  E - LLM-annotate the %CAND_N% candidates (base prompt). Needs token.
REM  --no_stage: the candidates already live on a fast local disc.
"%PY%" src\annotate_lni.py --lni_folder .workingset\candidates --no_stage %TOKEN_ARG%
goto end

:filter
REM  E - keep only label_research_software==1 -> .workingset\positives\manifest.csv.
REM  These positives are the pool the narrow + gold sets are drawn from. No token.
"%PY%" src\filter_positives.py
goto end

:ws_narrow
REM  W1 - draw the 50-paper narrowing set from the positives (local copy, no token).
"%PY%" src\prepare_workingset.py --corpus .workingset\candidates --name narrow --sample 50 ^
  --restrict .workingset\positives\manifest.csv
goto end

:ws_gold
REM  W1 - draw the 100-paper gold set from the positives, DISJOINT from narrow.
"%PY%" src\prepare_workingset.py --corpus .workingset\candidates --name gold --sample 100 ^
  --restrict .workingset\positives\manifest.csv ^
  --exclude .workingset\narrow\manifest.csv
goto end

:collect
REM  A2 - aggregate candidate subcategories. REUSES the candidate annotations from
REM  the a-candidates step (the 50 narrow papers are already annotated), so NO token.
"%PY%" src\narrow_categories.py --mode collect --corpus .workingset\narrow --sample 50
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
REM  Phase C - final study, drawn THROUGH THE ESTIMATOR: a stratified RANDOM sample
REM  of %FULL_N% papers from the likely-research-software pool (not the whole corpus,
REM  not just top scorers). The pool is selected ONCE into .workingset\final (reusing
REM  the cached estimate scores); if it holds < 2000 papers you are prompted first.
REM  Then annotate per model. Override the size with a 3rd arg, e.g.
REM     run_pipeline.cmd full <token> 800
REM  (size applies when the pool is first selected; delete .workingset\final to
REM  reselect). Run once per model, then aggregate (majority vote): repeat with
REM  --model llama-... / gemma-... and --run run_2/3 (selection is reused, no re-prompt).
if exist ".workingset\final\manifest.csv" goto full_annotate
"%PY%" src\select_candidates.py --corpus "%CORPUS%" --name final --sample %FULL_N% ^
  --select random --min_pool 2000
if errorlevel 1 goto end
:full_annotate
"%PY%" src\annotate_lni.py --lni_folder .workingset\final --no_stage ^
  --model %MODEL% --run run_1 %TOKEN_ARG%
goto end

:usage
echo.
echo   run_pipeline.cmd ^<step^> [^<saia_token^>] [^<full_sample_n^>]
echo.
echo   deps ^| dry ^| test ^| estimate ^| a-candidates ^| filter ^| ws-narrow
echo   ws-gold ^| collect ^| review ^| a-gold ^| gold ^| icr ^| full
echo.
echo   SAIA token: pass as 2nd arg, or set SAIA_TOKEN in the environment, or
echo   edit the placeholder at the top, or put SAIA_API_KEY in .env.
echo   3rd arg = final-study sample size for the full step (default %FULL_N%).
echo   Edit CORPUS at the top of this file if it is not already set.
goto end

:end