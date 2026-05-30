@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================================
::  CeyizHome Lab -- Tek-Tikla Deploy
::  Otomatik: merge edilmemis en yeni fix/* / design/* branch'i
::  bulur, test eder, main'e merge eder, Flask'i yeniden baslatir.
::  Bekleyen branch yoksa: main pull + test + restart.
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
if errorlevel 1 ( echo HATA: Klasor bulunamadi: %PROJECT_DIR% & goto :FAIL )
echo       OK: %CD%
echo.

:: -- On kosullar --------------------------------------------
if not exist "%VENV_PY%" (
    echo HATA: Sanal ortam yok: %VENV_PY%
    echo       Once start_app.bat veya setup.bat calistirin.
    goto :FAIL
)
"%GIT%" --version >nul 2>nul
if errorlevel 1 ( echo HATA: git bulunamadi: %GIT% & goto :FAIL )

:: -- 2. En yeni merge edilmemis fix/ veya design/ branch'ini bul
echo [2/6] Merge edilmemis fix/design branch'i aran?yor...
"%GIT%" fetch origin >nul 2>nul
set "WORK_BRANCH="
for /f "tokens=1" %%b in ('"%GIT%" branch -r --no-merged origin/main 2^>nul') do (
    if "!WORK_BRANCH!"=="" (
        echo %%b | findstr /R "origin/fix/ origin/design/" >nul 2>nul
        if not errorlevel 1 (
            set "RAW=%%b"
            set "WORK_BRANCH=!RAW:origin/=!"
        )
    )
)

if "!WORK_BRANCH!"=="" (
    echo       Bekleyen branch yok. main pull yapiliyor...
    "%GIT%" checkout main >nul 2>nul
    "%GIT%" pull origin main
    if errorlevel 1 ( echo HATA: main pull basarisiz. & goto :FAIL )
    set "MERGE_MODE=0"
) else (
    echo       Bulundu: !WORK_BRANCH!
    "%GIT%" checkout "!WORK_BRANCH!"
    if errorlevel 1 ( echo HATA: Branch'e gecilemedi: !WORK_BRANCH! & goto :FAIL )
    "%GIT%" pull origin "!WORK_BRANCH!"
    if errorlevel 1 ( echo HATA: git pull basarisiz. & goto :FAIL )
    echo       OK
    set "MERGE_MODE=1"
)
echo.

:: -- 3. Testleri calistir -----------------------------------
echo [3/6] Testler calistiriliyor...
echo       --------------------------------------------------------
"%VENV_PY%" -m pytest tests\ --ignore=tests\test_browser_smoke.py -v --tb=short --no-header -q 2>&1
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

:: -- 4. Merge (sadece bekleyen branch varsa) ----------------
if "!MERGE_MODE!"=="0" (
    echo [4/6] Bekleyen branch yoktu, merge adimi atlaniyor.
    echo.
    goto :FLASK
)

echo [4/6] main'e geciliyor, "!WORK_BRANCH!" merge ediliyor...
"%GIT%" checkout main
if errorlevel 1 ( echo HATA: main'e gecilemedi. & goto :FAIL )

"%GIT%" pull origin main
if errorlevel 1 ( echo HATA: main pull basarisiz. & goto :FAIL )

"%GIT%" merge --no-ff "!WORK_BRANCH!" -m "deploy: merge !WORK_BRANCH! into main"
if errorlevel 1 (
    echo HATA: Merge basarisiz, conflict olabilir.
    "%GIT%" merge --abort >nul 2>nul
    goto :FAIL
)
"%GIT%" push origin main
if errorlevel 1 ( echo HATA: git push basarisiz. & goto :FAIL )
echo       OK: main guncellendi ve push edildi.
echo.

:: -- 5. Flask kapat ve yeniden baslat ----------------------
:FLASK
echo [5/6] Port %FLASK_PORT% kapatiliyor...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%FLASK_PORT% " ^| findstr "LISTENING"') do (
    echo       PID %%p kapatiliyor...
    taskkill /F /PID %%p >nul 2>nul
)
timeout /t 2 /nobreak >nul

echo       Flask baslatiliyor...
start "CeyizHome Lab - Flask" /d "%PROJECT_DIR%" cmd /k ^
    ".venv\Scripts\python.exe -m src.server.flask_app"

echo       Sunucu hazir olana kadar bekleniyor (max 10 sn)...
set "READY=0"
for /l %%i in (1,1,10) do (
    if "!READY!"=="0" (
        timeout /t 1 /nobreak >nul
        curl -s --max-time 1 http://localhost:%FLASK_PORT%/ >nul 2>nul
        if not errorlevel 1 ( set "READY=1" & echo       OK: Sunucu hazir. )
    )
)
if "!READY!"=="0" ( echo       UYARI: 10 sn yanit yok, tarayiciyi elle yenile. )
echo.

:: -- 6. Tarayici ac ----------------------------------------
echo [6/6] Tarayici aciliyor: http://localhost:%FLASK_PORT%
start "" "http://localhost:%FLASK_PORT%"
echo.
if "!MERGE_MODE!"=="1" (
    echo ============================================================
    echo  DEPLOY TAMAMLANDI
    echo  Merge  : !WORK_BRANCH! -- main
    echo  URL    : http://localhost:%FLASK_PORT%
    echo ============================================================
) else (
    echo ============================================================
    echo  DEPLOY TAMAMLANDI  (bekleyen branch yoktu)
    echo  URL    : http://localhost:%FLASK_PORT%
    echo ============================================================
)
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