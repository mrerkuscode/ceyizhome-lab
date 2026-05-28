@echo off
chcp 65001 >nul
setlocal

set "PROJECT_DIR=C:\Users\Pc\Documents\New project\production-bot"
cd /d "%PROJECT_DIR%"
if errorlevel 1 (
    echo Proje klasoru bulunamadi:
    echo %PROJECT_DIR%
    pause
    exit /b 1
)

set "VENV_PY=%PROJECT_DIR%\.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo Ilk kurulum hazirlaniyor...
    call :find_python
    if errorlevel 1 (
        echo Python bulunamadi. Lutfen Python kurulumunu kontrol edin.
        pause
        exit /b 1
    )

    %BASE_PY% -m venv "%PROJECT_DIR%\.venv"
    if errorlevel 1 (
        echo Sanal Python ortami olusturulamadi.
        pause
        exit /b 1
    )
)

echo Gerekli paketler kontrol ediliyor...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo pip guncellenemedi. Internet baglantisini ve Python kurulumunu kontrol edin.
    pause
    exit /b 1
)

"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Gerekli paketler kurulamadi. requirements.txt ve internet baglantisini kontrol edin.
    pause
    exit /b 1
)

"%VENV_PY%" -c "import PySide6; print('PySide6 OK')"
if errorlevel 1 (
    echo PySide6 kurulamadi. requirements.txt ve internet baglantisini kontrol edin.
    pause
    exit /b 1
)

echo Cyzella Production Studio aciliyor...
"%VENV_PY%" -m src.desktop.app
if errorlevel 1 (
    echo Cyzella Production Studio baslatilamadi.
    pause
    exit /b 1
)

exit /b 0

:find_python
set "BASE_PY="
where python >nul 2>nul
if not errorlevel 1 (
    set "BASE_PY=python"
    exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    set "BASE_PY=py -3"
    exit /b 0
)

if exist "C:\Users\Pc\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
    set "BASE_PY=C:\Users\Pc\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    exit /b 0
)

exit /b 1
