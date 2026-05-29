@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM  dev_sync.bat - Once GitHub main'den guncel kodu cek, sonra baslat
REM  Kullanim: Bu dosyayi cift tiklayin (start_cyzella.bat yerine).
REM  Calisani bozmaz; mevcut start_cyzella.bat'i cagirir.
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo  Guncel kod cekiliyor (git pull origin main)...
echo ============================================================

REM Mevcut dal main mi kontrol et
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set "CURBRANCH=%%b"
echo Aktif dal: !CURBRANCH!
if /i not "!CURBRANCH!"=="main" (
    echo.
    echo [UYARI] Su an 'main' dalinda degilsiniz: !CURBRANCH!
    echo Guncel uygulama kodu 'main' dalindadir.
    choice /c EH /n /m "main dalina gecilsin mi? Gecmek icin E, kalmak icin H: "
    if errorlevel 2 (
        echo main'e gecilmedi. Mevcut dalda devam ediliyor.
    ) else (
        git checkout main
        if errorlevel 1 (
            echo.
            echo [HATA] main dalina gecilemedi. Muhtemelen commit edilmemis degisiklik var.
            echo Once degisiklikleri commit'leyin ya da: git stash
            echo.
            pause
        )
    )
)

REM Commit edilmemis lokal degisiklik var mi kontrol et
git diff --quiet
if errorlevel 1 (
    echo.
    echo [UYARI] Commit edilmemis lokal degisiklikleriniz var.
    echo Pull catismayi onlemek icin once bunlari commit'leyin ya da stash'leyin.
    choice /c EH /n /m "Devam icin E, vazgecmek icin H: "
    if errorlevel 2 (
        echo Pull atlandi. Uygulama mevcut lokal kod ile baslatiliyor...
        goto :start
    )
)

REM main dalindan kesin cekim (tracking olmasa bile calisir)
git pull origin main
if errorlevel 1 (
    echo.
    echo [HATA] git pull basarisiz oldu. Lutfen catismayi/baglantiyi kontrol edin.
    echo Uygulama YINE DE mevcut lokal kod ile baslatilacak.
    echo.
    pause
)

:start
echo.
echo ============================================================
echo  Uygulama baslatiliyor...
echo ============================================================
call start_cyzella.bat
