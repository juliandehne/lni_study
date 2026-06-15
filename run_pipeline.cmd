@echo off
REM ============================================================================
REM  run_pipeline.cmd - step-by-step driver for the lni_study annotation pipeline
REM ----------------------------------------------------------------------------
REM  Usage:   run_pipeline.cmd <step> [<saia_token>]
REM  Run ONE step at a time and inspect its artifact before moving on.
REM
REM  Steps (in pipeline order):
REM     deps        pip install -r requirements.txt
REM     dry         Step 0  - offline dry run, NO token (extraction + prompt)
REM     test        Step 1  - 5-paper live test (needs token)
REM     sample      Step 2  - stratified sample of %SAMPLE_N% papers (needs token)
REM     ws-narrow   W1      - copy 50-paper narrowing set -> .workingset\narrow
REM     ws-gold     W1      - copy 100-paper gold set (disjoint) -> .workingset\gold
REM     a-narrow    A       - annotate the 50 narrowing papers (needs token)
REM     collect     A2      - aggregate subcategory candidates (no token)
REM     review      A2      - human accept/decline -> category_whitelist.json (no token)
REM     a-gold      A       - re-annotate 100 gold papers w/ enriched prompt (needs token)
REM     gold        B       - interactive two-coder goldstandard (no token)
REM     icr         B       - intercoder reliability (no token)
REM     full        C       - final study: stratified sample of %FULL_N% papers, per
REM                           model (needs token); override size with a 3rd argument
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
set "SAMPLE_N=30"
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

if "%~1"==""          goto usage
if /i "%~1"=="deps"      goto deps
if /i "%~1"=="dry"       goto dry
if /i "%~1"=="test"      goto test
if /i "%~1"=="sample"    goto sample
if /i "%~1"=="ws-narrow" goto ws_narrow
if /i "%~1"=="ws-gold"   goto ws_gold
if /i "%~1"=="a-narrow"  goto a_narrow
if /i "%~1"=="collect"   goto collect
if /i "%~1"=="review"    goto review
if /i "%~1"=="a-gold"    goto a_gold
if /i "%~1"=="gold"      goto gold
if /i "%~1"=="icr"       goto icr
if /i "%~1"=="full"      goto full
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

:sample
REM  Step 2 - stratified sample of %SAMPLE_N% papers. Needs token.
"%PY%" src\annotate_lni.py --lni_folder "%CORPUS%" --sample %SAMPLE_N% %TOKEN_ARG%
goto end

:ws_narrow
REM  W1 - draw + copy the 50-paper narrowing set onto fast disc. Reads corpus once.
"%PY%" src\prepare_workingset.py --corpus "%CORPUS%" --name narrow --sample 50
goto end

:ws_gold
REM  W1 - draw + copy the 100-paper gold set, DISJOINT from the narrowing set.
"%PY%" src\prepare_workingset.py --corpus "%CORPUS%" --name gold --sample 100 ^
  --exclude .workingset\narrow\manifest.csv
goto end

:a_narrow
REM  Phase A on the 50 narrowing papers (produces new-suggestion candidates). Token.
"%PY%" src\annotate_lni.py --lni_folder .workingset\narrow %TOKEN_ARG%
goto end

:collect
REM  A2 - aggregate candidate subcategories from Phase A checkpoints. No token.
REM  Output: results\category_candidates_<corpus>.csv
"%PY%" src\narrow_categories.py --mode collect --corpus .workingset\narrow --sample 50
goto end

:review
REM  A2 - human accept/decline CLI -> prompts\category_whitelist.json. No token.
"%PY%" src\narrow_categories.py --mode review
goto end

:a_gold
REM  Phase A on the 100 gold papers, now with the enriched (whitelist) prompt. Token.
"%PY%" src\annotate_lni.py --lni_folder .workingset\gold %TOKEN_ARG%
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
REM  Phase C - final study: a stratified sample of %FULL_N% papers (each volume
REM  folder is a stratum), NOT the whole corpus. Override the size with a 3rd arg,
REM  e.g.  run_pipeline.cmd full <token> 800. Run once per model, then aggregate
REM  (majority vote): repeat with --model llama-... / gemma-... and --run run_2/3.
"%PY%" src\annotate_lni.py --lni_folder "%CORPUS%" --sample %FULL_N% --model %MODEL% --run run_1 %TOKEN_ARG%
goto end

:usage
echo.
echo   run_pipeline.cmd ^<step^> [^<saia_token^>] [^<full_sample_n^>]
echo.
echo   deps ^| dry ^| test ^| sample ^| ws-narrow ^| ws-gold ^| a-narrow ^| collect
echo   review ^| a-gold ^| gold ^| icr ^| full
echo.
echo   SAIA token: pass as 2nd arg, or set SAIA_TOKEN in the environment, or
echo   edit the placeholder at the top, or put SAIA_API_KEY in .env.
echo   3rd arg = final-study sample size for the full step (default %FULL_N%).
echo   Edit CORPUS at the top of this file if it is not already set.
goto end

:end