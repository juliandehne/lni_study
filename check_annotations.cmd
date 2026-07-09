@echo off
REM Convenience wrapper for the rse_code_annotations checker.
REM Runs from the lni_study repo root; forwards any flags (e.g. --json, --stubs).
setlocal
set PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
if not exist "%PY%" set PY=python
"%PY%" "%~dp0check_annotations.py" %*
endlocal
