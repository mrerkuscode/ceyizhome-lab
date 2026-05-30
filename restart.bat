@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =========================================
echo  CeyizHome Lab -- Sunucu Yeniden Baslat
echo =========================================
echo.

:: 1) Port 8000'deki sureci oldur
echo [1/3] Port 8000 kapatiliyor...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
    echo     PID %%p sonlandirildi.
)
timeout /t 1 /nobreak >nul

:: 2) Virtualenv kontrolu
if not exist ".venv\Scripts\python.exe" (
    echo HATA: .venv bulunamadi. Once start_app.bat calistirin.
    pause
    exit /b 1
)

:: 3) Flask'i arka planda baslat
echo [2/3] Flask baslatiliyor (src.server.flask_app)...
start "" /b ".venv\Scripts\python.exe" -m src.server.flask_app

:: Flask'in ayaga kalkmasini bekle
timeout /t 2 /nobreak >nul

:: 4) Tarayiciyi ac
echo [3/3] Tarayici aciliyor: http://localhost:8000
start "" "http://localhost:8000"

echo.
echo Sunucu calisiyor. Durdurmak icin: Gorev Yoneticisi ya da yeni bir restart.bat
echo =========================================
