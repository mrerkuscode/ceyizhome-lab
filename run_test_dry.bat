@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=py -3"
)

%PY% src\main.py --excel input\test_siparisler.xlsx --dry-run
pause
