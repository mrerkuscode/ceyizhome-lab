@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo Python sanal ortamı bulunamadı.
    echo Önce start_cyzella.bat çalıştırın.
    pause
    exit /b 1
)

echo Eski PySide yedek arayüzü açılıyor...
"%VENV_PY%" -m src.desktop.fallback_app
if errorlevel 1 (
    echo Eski PySide yedek arayüz başlatılamadı.
    pause
    exit /b 1
)
