@echo off
title CeyizHome Lab - Chrome Mode
chcp 65001 > nul

echo.
echo ========================================
echo   CeyizHome Lab - Chrome Modu
echo ========================================
echo.
echo Sunucu baslatiliyor...
echo Tarayici 4 saniye sonra acilacak.
echo.
echo KAPATMAK ICIN: Bu pencereyi X ile kapatin.
echo.

cd /d "%~dp0"

start "" cmd /c "timeout /t 4 /nobreak >nul && start "" "http://localhost:8000""

.venv\Scripts\python.exe -m src.server.flask_app

pause
