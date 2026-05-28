@echo off
chcp 65001 >nul
setlocal

set "PROJECT_DIR=C:\Users\Pc\Documents\New project\production-bot"
set "TARGET=%PROJECT_DIR%\start_cyzella.bat"
set "SHORTCUT=C:\Users\Pc\Desktop\Cyzella Production Studio.lnk"

echo Masaustu kisayolu olusturuluyor...

if not exist "%TARGET%" (
    echo Baslatici dosya bulunamadi:
    echo %TARGET%
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$shortcutPath = 'C:\Users\Pc\Desktop\Cyzella Production Studio.lnk'; $targetPath = 'C:\Users\Pc\Documents\New project\production-bot\start_cyzella.bat'; $workDir = 'C:\Users\Pc\Documents\New project\production-bot'; $shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut($shortcutPath); $shortcut.TargetPath = $targetPath; $shortcut.WorkingDirectory = $workDir; $shortcut.WindowStyle = 1; $shortcut.Description = 'Cyzella Production Studio'; $shortcut.Save()"
if errorlevel 1 (
    echo Kisayol olusturulamadi.
    pause
    exit /b 1
)

echo Kisayol hazir: Cyzella Production Studio
echo Artik sadece masaustundeki kisayola cift tiklamaniz yeterli.
pause
