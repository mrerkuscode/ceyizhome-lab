@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  dev_sync.bat - Once GitHub'dan guncel kodu cek, sonra uygulamayi baslat
REM  Kullanim: Bu dosyayi cift tiklayin (start_cyzella.bat yerine).
REM  Calisani bozmaz; mevcut start_cyzella.bat'i cagirir.
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo  Guncel kod cekiliyor (git pull)...
echo ============================================================

REM Commit edilmemis lokal degisiklik var mi kontrol et
git diff --quiet
if errorlevel 1 (
    echo.
    echo [UYARI] Commit edilmemis lokal degisiklikleriniz var.
    echo Pull catismayi onlemek icin once bunlari commit'leyin ya da stash'leyin.
    echo Devam edilsin mi?
    choice /c EH /n /m "Devam icin E, vazgecmek icin H: "
    if errorlevel 2 (
        echo Pull atlandi. Uygulama mevcut lokal kod ile baslatiliyor...
        goto :start
    )
)

git pull
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
