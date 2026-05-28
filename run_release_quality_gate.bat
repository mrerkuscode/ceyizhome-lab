@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Python sanal ortami bulunamadi. Once setup.bat calistirin.
    pause
    exit /b 1
)

node --check src\webui\app.js
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" scripts\verify_clean_customer_demo_flow.py
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" scripts\verify_rdworks_name_cut_layout_export.py
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" scripts\verify_combined_excel_label_and_name_cut_flow.py
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" scripts\real_production_quality_gate.py
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" scripts\final_acceptance_gate.py
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" scripts\final_release_package_gate.py
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" scripts\build_release_package.py
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" scripts\verify_release_package.py
if errorlevel 1 exit /b 1

echo Release kalite kapisi ve paket dogrulamasi basarili.
pause
