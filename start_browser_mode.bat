@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Python sanal ortami bulunamadi. Once start_app.bat calistirin.
    pause
    exit /b 1
)

echo Browser Mode sunucusu baslatiliyor...
echo Tarayicidan acin: http://localhost:8000
echo Durdurmak icin: Ctrl+C
echo.
".venv\Scripts\python.exe" -m src.server.flask_app
pause
