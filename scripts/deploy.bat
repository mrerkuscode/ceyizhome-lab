@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================================
::  CeyizHome Lab — Tek-Tikla Deploy
::  Kullanim: scripts\deploy.bat (ya da masaustu kisayolu)
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

:: ── 1. Repo klasorune gec ────────────────────────────────────
echo [1/6] Repo klasorune geciliyor...
cd /d "%PROJECT_DIR%"
if errorlevel 1 (
    echo HATA: Proje klasoru bulunamadi:
    echo        %PROJECT_DIR%
    goto :FAIL
)
echo       OK: %PROJECT_DIR%
echo.

:: ── Onkosullar ──────────────────────────────────────────────
if not exist "%VENV_PY%" (
    echo HATA: Sanal ortam bulunamadi: %VENV_PY%
    echo       Once start_app.bat veya setup.bat calistirin.
    goto :FAIL
)

"%GIT%" --version >nul 2>nul
if errorlevel 1 (
    echo HATA: git bulunamadi: %GIT%
    goto :FAIL
)

:: ── Mevcut branch'i tespit et ───────────────────────────────
for /f "delims=" %%b in ('"%GIT%" rev-parse --abbrev-ref HEAD 2^>nul') do set "WORK_BRANCH=%%b"
if "%WORK_BRANCH%"=="" (
    echo HATA: Mevcut branch tespit edilemedi.
    goto :FAIL
)
if "%WORK_BRANCH%"=="main" (
    echo HATA: Simdi main branch'tindesin.
    echo       Deploy, bir ozellik/duzeltme branch'inden calistirilmalidir.
    echo       Ornek: git checkout fix/benim-duzeltmem
    goto :FAIL
)
echo       Aktif branch: %WORK_BRANCH%
echo.

:: ── 2. Calisilan branch'i pull et ───────────────────────────
echo [2/6] "%WORK_BRANCH%" branch'i guncelleniyor (pull)...
"%GIT%" pull origin "%WORK_BRANCH%"
if errorlevel 1 (
    echo HATA: git pull basarisiz oldu.
    echo       Cakisma var olabilir veya remote'a erisim saglanamadi.
    goto :FAIL
)
echo       OK: branch guncel.
echo.

:: ── 3. Testleri calistir ────────────────────────────────────
echo [3/6] Testler calistiriliyor (pytest)...
echo       --------------------------------------------------------
"%VENV_PY%" -m pytest tests\ -v --tb=short --no-header -q 2>&1
set "TEST_EXIT=%errorlevel%"
echo       --------------------------------------------------------
if not "%TEST_EXIT%"=="0" (
    echo.
    echo *** TESTLER PATLADI — DEPLOY IPTAL ***
    echo     Yukaridaki hatalari duzelt, sonra tekrar dene.
    echo     main'e merge YAPILMADI.
    goto :FAIL
)
echo       OK: Tum testler gecti.
echo.

:: ── 4. main'e gec, merge et, push et ───────────────────────
echo [4/6] main'e geciliyor ve "%WORK_BRANCH%" merge ediliyor...

"%GIT%" checkout main
if errorlevel 1 (
    echo HATA: main branch'ine gecilemedi.
    goto :FAIL
)

"%GIT%" pull origin main
if errorlevel 1 (
    echo HATA: main pull basarisiz.
    goto :FAIL
)

"%GIT%" merge --no-ff "%WORK_BRANCH%" -m "deploy: merge %WORK_BRANCH% into main"
if errorlevel 1 (
    echo HATA: Merge basarisiz. Muhtemelen cakisma var.
    echo       Cakismalari manuel coz: git mergetool
    echo       Sonra: git merge --continue
    "%GIT%" merge --abort >nul 2>nul
    goto :FAIL
)

"%GIT%" push origin main
if errorlevel 1 (
    echo HATA: git push basarisiz.
    echo       Remote erisim sorununu kontrol et.
    goto :FAIL
)
echo       OK: main guncellendi ve push edildi.
echo.

:: ── 5. Flask'i kapat ve yeniden baslat ─────────────────────
echo [5/6] Port %FLASK_PORT% kapatiliyor ve Flask yeniden baslatiliyor...

:: 8000 portundaki prosesleri bul ve kapat
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%FLASK_PORT% " ^| findstr LISTENING') do (
    echo       PID %%p kapatiliyor...
    taskkill /F /PID %%p >nul 2>nul
)
:: Kapanis icin kisa bekleme
timeout /t 2 /nobreak >nul

:: Flask'i yeni pencerede baslat (deploy penceresi bloke olmaz)
echo       Flask baslatiliyor (yeni pencere)...
start "CeyizHome Lab - Flask" /d "%PROJECT_DIR%" cmd /k ^
    "title CeyizHome Lab - Flask Server && echo. && echo  CeyizHome Lab -- Flask Sunucu && echo  Durdurmak icin: Ctrl+C && echo. && .venv\Scripts\python.exe -m src.server.flask_app"

:: Sunucunun ayaga kalkmasini bekle (max 10 saniye)
set "READY=0"
for /l %%i in (1,1,10) do (
    if "!READY!"=="0" (
        timeout /t 1 /nobreak >nul
        curl -s -o nul -w "%%{http_code}" http://localhost:%FLASK_PORT%/ 2>nul | findstr "200" >nul 2>nul
        if not errorlevel 1 (
            set "READY=1"
            echo       OK: Sunucu hazir ^(%%i. saniyede^).
        )
    )
)
if "!READY!"=="0" (
    echo       UYARI: Sunucu 10 saniyede yanit vermedi.
    echo              Flask penceresi acildi, biraz bekle ve tarayiciyi elle yenile.
)
echo.

:: ── 6. Tarayiciyi ac ────────────────────────────────────────
echo [6/6] Tarayici aciliyor: http://localhost:%FLASK_PORT%
start "" "http://localhost:%FLASK_PORT%"
echo.

echo ============================================================
echo  DEPLOY TAMAMLANDI
echo  Branch : %WORK_BRANCH%  ->  main
echo  URL    : http://localhost:%FLASK_PORT%
echo ============================================================
echo.
pause
exit /b 0

:: ── Hata cikisi ─────────────────────────────────────────────
:FAIL
echo.
echo ============================================================
echo  DEPLOY BASARISIZ -- yukaridaki hataya bak
echo ============================================================
echo.
pause
exit /b 1
