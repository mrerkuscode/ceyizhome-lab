@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo Python sanal ortamı bulunamadı.
    echo Lütfen masaüstündeki Cyzella Production Studio kısayolunu açın veya start_cyzella.bat çalıştırın.
    pause
    exit /b 1
)

echo Cyzella Production Studio HTML arayüzü açılıyor...
"%VENV_PY%" -m src.desktop.app
if errorlevel 1 (
    echo Cyzella Production Studio başlatılamadı.
    pause
    exit /b 1
)
