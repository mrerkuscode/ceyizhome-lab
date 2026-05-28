@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
set "TEMP=%CD%\.tmp"
set "TMP=%CD%\.tmp"
if not exist "%TEMP%" mkdir "%TEMP%"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        where python >nul 2>nul
        if errorlevel 1 (
            echo Python bulunamadi. Lutfen Python 3 kurun ve tekrar deneyin.
            pause
            exit /b 1
        )
        python -m venv .venv
    )
    if errorlevel 1 (
        echo Sanal ortam olusturulamadi.
        pause
        exit /b 1
    )
    set "PY=.venv\Scripts\python.exe"
)

"%PY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo pip guncellenemedi.
    pause
    exit /b 1
)

"%PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo requirements.txt kurulumu basarisiz oldu.
    pause
    exit /b 1
)

"%PY%" -m pip install pytest
if errorlevel 1 (
    echo pytest kurulumu basarisiz oldu.
    pause
    exit /b 1
)

"%PY%" -c "import sys; import win32com.client; print('pywin32 COM OK')" >nul 2>nul
if errorlevel 1 (
    echo pywin32 COM dogrulamasi basarisiz oldu. Illustrator/Corel native edit PoC calismayabilir.
) else (
    echo pywin32 COM dogrulamasi basarili.
)

echo Kurulum tamamlandi. Artik dry-run dosyalarini calistirabilirsiniz.
pause
