@echo off
REM ============================================================================
REM  menu.cmd - launch the interactive pipeline menu (src\pipeline_menu.py).
REM  Run from anywhere; it cd's to its own folder so src\ prompts\ resolve.
REM ============================================================================
set "PY=C:\Users\julian.dehne\AppData\Local\Programs\Python\Python313\python.exe"
cd /d "%~dp0"
"%PY%" src\pipeline_menu.py %*
