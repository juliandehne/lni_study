@echo off
REM ============================================================================
REM  menu.cmd - launch the interactive pipeline menu (src\pipeline_menu.py).
REM  Run from anywhere; it cd's to its own folder so src\ prompts\ resolve.
REM ============================================================================
REM  Python interpreter. Override with LNI_PYTHON=full\path\to\python.exe;
REM  otherwise use this user's Python 3.13 LocalAppData install, then PATH.
if defined LNI_PYTHON (
    set "PY=%LNI_PYTHON%"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
) else (
    set "PY=python"
)
cd /d "%~dp0"
"%PY%" src\pipeline_menu.py %*
