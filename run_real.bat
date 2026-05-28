@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=py -3"
)

echo Bu gercek uretim modudur. CorelDRAW, yazici, RDWorks ve lazer yine otomatik acilmayacak; sadece dosya ve rapor uretilecek.
%PY% src\main.py --excel input\siparisler.xlsx
pause
