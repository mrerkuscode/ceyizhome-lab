@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================================
::  CeyizHome Lab -- Tek-Tikla Deploy
::  Kullanim: scripts\deploy.bat
::  Strateji: hangi branch'teysen onu main'e merge eder.
::  main'den calistirirsan hata verir.
:: ============================================================

set "PROJECT_DIR=C:\Users\Pc\Documents\New project\production-bot"
set "VENV_PY=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "GIT=C:\Program Files\Git\cmd\git.exe"
set "FLASK_PORT=8000"

echo.
echo ============================================================
echo  CeyizHome Lab -- Deploy Basliyor
echo ============================================================
echo.

:: -- 1. Repo klasorune gec -----------------------------------
echo [1/6] Proje klasorune geciliyor...
cd /d "%PROJECT_DIR%"
if errorlevel 1 (
    echo HATA: Klasor bulunamadi: %PROJECT_DIR%
    goto :FAIL
)
echo       OK: %CD%
echo.

:: -- On kosullar --------------------------------------------
if not exist "%VENV_PY%" (
    echo HATA: Sanal ortam yok: %VENV_PY%
    echo       Once start_app.bat veya setup.bat calistirin.
    goto :FAIL
)

"%GIT%" --version >nul 2>nul
if errorlevel 1 (
    echo HATA: git bulunamadi: %GIT%
    goto :FAIL
)

:: -- Mevcut branch'i tespit et ------------------------------
for /f "delims=" %%b in ('"%GIT%" rev-parse --abbrev-ref HEAD 2^>nul') do set "WORK_BRANCH=%%b"
if "%WORK_BRANCH%"=="" (
    echo HATA: Aktif branch tespit edilemedi.
    goto :FAIL
)
if /i "%WORK_BRANCH%"=="main" (
    echo HATA: Simdi main branch'tindesin.
    echo       Deploy bir feature/fix branch'inden calistirilmali.
    echo       Ornek: git checkout fix/benim-fix
    goto :FAIL
)
echo       Aktif branch: %WORK_BRANCH%
echo.

:: -- 2. Branch'i pull et ------------------------------------
echo [2/6] "%WORK_BRANCH%" pull ediliyor...
"%GIT%" pull origin "%WORK_BRANCH%"
if errorlevel 1 (
    echo HATA: git pull basarisiz. Conflict veya network sorunu olabilir.
    goto :FAIL
)
echo       OK
echo.

:: -- 3. Testleri calistir -----------------------------------
echo [3/6] Testler calistiriliyor...
echo       --------------------------------------------------------
"%VENV_PY%" -m pytest tests\ -v --tb=short --no-header -q 2>&1
set "TEST_EXIT=!errorlevel!"
echo       --------------------------------------------------------
if not "!TEST_EXIT!"=="0" (
    echo.
    echo *** TESTLER PATLADI -- DEPLOY IPTAL ***
    echo     main'e merge YAPILMADI.
    echo     Yukaridaki hatalari duzelt, tekrar dene.
    goto :FAIL
)
echo       OK: Tum testler gecti.
echo.

:: -- 4. main'e gec, merge et, push et ----------------------
echo [4/6] main'e geciliyor, "%WORK_BRANCH%" merge ediliyor...

"%GIT%" checkout main
if errorlevel 1 (
    echo HATA: main'e gecilemedi.
    goto :FAIL
)

"%GIT%" pull origin main
if errorlevel 1 (
    echo HATA: main pull basarisiz.
    goto :FAIL
)

"%GIT%" merge --no-ff "%WORK_BRANCH%" -m "deploy: merge %WORK_BRANCH% into main"
if errorlevel 1 (
    echo HATA: Merge basarisiz. Conflict var olabilir.
    echo       git merge --abort yapildi.
    "%GIT%" merge --abort >nul 2>nul
    goto :FAIL
)

"%GIT%" push origin main
if errorlevel 1 (
    echo HATA: git push basarisiz.
    goto :FAIL
)
echo       OK: main guncellendi ve push edildi.
echo.

:: -- 5. Flask kapat ve yeniden baslat ----------------------
echo [5/6] Port %FLASK_PORT% kapatiliyor...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%FLASK_PORT% " ^| findstr "LISTENING"') do (
    echo       PID %%p kapatiliyor...
    taskkill /F /PID %%p >nul 2>nul
)
timeout /t 2 /nobreak >nul

echo       Flask baslatiliyor...
start "CeyizHome Lab - Flask" /d "%PROJECT_DIR%" cmd /k ^
    ".venv\Scripts\python.exe -m src.server.flask_app"

echo       Sunucu baslayana kadar bekleniyor (max 10 sn)...
set "READY=0"
for /l %%i in (1,1,10) do (
    if "!READY!"=="0" (
        timeout /t 1 /nobreak >nul
        curl -s --max-time 1 http://localhost:%FLASK_PORT%/ >nul 2>nul
        if not errorlevel 1 (
            set "READY=1"
            echo       OK: Sunucu hazir.
        )
    )
)
if "!READY!"=="0" (
    echo       UYARI: 10 sn'de yanit yok, tarayiciyi elle yenile.
)
echo.

:: -- 6. Tarayici ac ----------------------------------------
echo [6/6] Tarayici aciliyor: http://localhost:%FLASK_PORT%
start "" "http://localhost:%FLASK_PORT%"
echo.

echo ============================================================
echo  DEPLOY TAMAMLANDI
echo  Branch : %WORK_BRANCH% -- main
echo  URL    : http://localhost:%FLASK_PORT%
echo ============================================================
echo.
pause
exit /b 0

:FAIL
echo.
echo ============================================================
echo  DEPLOY BASARISIZ -- yukaridaki hataya bak
echo ============================================================
echo.
pause
exit /b 1
