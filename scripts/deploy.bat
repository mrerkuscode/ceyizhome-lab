@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

set "PROJECT_DIR=C:\Users\Pc\Documents\New project\production-bot"
set "VENV_PY=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "GIT=C:\Program Files\Git\cmd\git.exe"
set "FLASK_PORT=8000"

echo.
echo ============================================================
echo  CeyizHome Lab -- Deploy Basliyor
echo ============================================================
echo.

echo [1/6] Proje klasorune geciliyor...
cd /d "%PROJECT_DIR%"
if errorlevel 1 ( echo HATA: Klasor bulunamadi & goto :FAIL )
echo       OK: %CD%
echo.

if not exist "%VENV_PY%" ( echo HATA: Sanal ortam yok & goto :FAIL )
"%GIT%" --version >nul 2>nul
if errorlevel 1 ( echo HATA: git bulunamadi & goto :FAIL )

:: -- main'de oldugundan emin ol ---
"%GIT%" checkout main >nul 2>nul
"%GIT%" pull origin main >nul 2>nul

echo [2/6] Merge edilmemis fix/design branch aran?yor...
"%GIT%" fetch origin >nul 2>nul

"%VENV_PY%" -c "import subprocess,sys; m=subprocess.run(['git','branch','-r','--merged','origin/main'],capture_output=True,text=True).stdout; c=subprocess.run(['git','branch','-r','--sort=-committerdate'],capture_output=True,text=True).stdout; [print(b.strip()) or sys.exit() for b in c.splitlines() if any(p in b for p in ['origin/fix/','origin/design/']) and b.strip() not in m]" > "%TEMP%\czb.txt" 2>nul

set "REMOTE_BRANCH="
set /p REMOTE_BRANCH=<"%TEMP%\czb.txt"
del "%TEMP%\czb.txt" >nul 2>nul

if "!REMOTE_BRANCH!"=="" (
    echo       Bekleyen branch yok. main zaten guncel.
    set "MERGE_MODE=0"
    goto :TESTS
)
echo       Bulundu: !REMOTE_BRANCH!
set "MERGE_MODE=1"

:: -- Deneme merge (henuz push yok) -
echo       Test merge yapiliyor...
"%GIT%" merge --no-ff "!REMOTE_BRANCH!" -m "deploy-test: merge !REMOTE_BRANCH!"
if errorlevel 1 (
    "%GIT%" merge --abort >nul 2>nul
    echo HATA: Merge conflict. Manuel coz: git mergetool
    goto :FAIL
)
echo.

:: -- 3. Testleri calistir -------
:TESTS
echo [3/6] Testler calistiriliyor...
echo       --------------------------------------------------------
"%VENV_PY%" -m pytest tests\ --ignore=tests\test_browser_smoke.py --tb=short --no-header -q 2>&1
set "TEST_EXIT=!errorlevel!"
echo       --------------------------------------------------------

if not "!TEST_EXIT!"=="0" (
    if "!MERGE_MODE!"=="1" (
        echo       Test merge geri aliniyor...
        "%GIT%" reset --hard HEAD~1 >nul 2>nul
    )
    echo.
    echo *** TESTLER PATLADI -- DEPLOY IPTAL ***
    goto :FAIL
)
echo       OK: Tum testler gecti.
echo.

:: -- 4. Push -------------------
if "!MERGE_MODE!"=="0" (
    echo [4/6] Bekleyen branch yoktu, push atlaniyor.
    echo.
    goto :FLASK
)
echo [4/6] Push ediliyor...
"%GIT%" push origin main
if errorlevel 1 ( echo HATA: Push basarisiz & goto :FAIL )
echo       OK: main push edildi.
echo.

:: -- 5. Flask ------------------
:FLASK
echo [5/6] Port %FLASK_PORT% kapatiliyor...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%FLASK_PORT% " ^| findstr "LISTENING"') do (
    echo       PID %%p kapatiliyor...
    taskkill /F /PID %%p >nul 2>nul
)
timeout /t 2 /nobreak >nul
echo       Flask baslatiliyor...
start "CeyizHome Lab" /d "%PROJECT_DIR%" cmd /k ".venv\Scripts\python.exe -m src.server.flask_app"
echo       Bekleniyor (max 10 sn)...
set "READY=0"
for /l %%i in (1,1,10) do (
    if "!READY!"=="0" (
        timeout /t 1 /nobreak >nul
        curl -s --max-time 1 http://localhost:%FLASK_PORT%/ >nul 2>nul
        if not errorlevel 1 ( set "READY=1" & echo       OK: Sunucu hazir. )
    )
)
if "!READY!"=="0" ( echo       UYARI: 10sn yanit yok. )
echo.

:: -- 6. Tarayici ---------------
echo [6/6] Tarayici aciliyor...
start "" "http://localhost:%FLASK_PORT%"
echo.
echo ============================================================
if "!MERGE_MODE!"=="1" ( echo  DEPLOY TAMAMLANDI  Merge: !REMOTE_BRANCH! ) else ( echo  DEPLOY TAMAMLANDI  Bekleyen branch yoktu )
echo  URL: http://localhost:%FLASK_PORT%
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
