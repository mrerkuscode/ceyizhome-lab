@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ilk kurulum icin setup.bat calistiriliyor...
    call setup.bat
    if errorlevel 1 exit /b 1
)

echo Cyzella Production Studio aciliyor...
".venv\Scripts\python.exe" -m src.desktop.app
if errorlevel 1 (
    echo Uygulama baslatilamadi.
    pause
    exit /b 1
)
