# Target Installation Rehearsal Report

Date: 2026-05-15

## Summary

This pass focused on the user handoff path: setup, launch entry point, release package verification, and the safety gates around production output.

The root project already had `setup.bat` and `run_release_quality_gate.bat`, but it did not have a root-level `start_app.bat`. The release package already generated a launcher, but the working project folder now also has the same direct launcher so the target-machine flow is clearer:

1. Run `setup.bat` if needed.
2. Run `start_app.bat` to open Cyzella Production Studio.
3. Run `run_release_quality_gate.bat` to verify the delivery package.

## Change Made

- Added `start_app.bat` at the project root.
- The launcher:
  - switches to the project folder,
  - runs `setup.bat` automatically if `.venv\Scripts\python.exe` is missing,
  - starts `src.desktop.app` through the local virtual environment,
  - does not trigger CorelDRAW, Illustrator, RDWorks, printer, direct print, or laser automation.

## Verification

Commands run:

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -c "import importlib; importlib.import_module('src.desktop.app'); print('desktop app module import OK')"
cmd /c "if exist start_app.bat (echo root start_app.bat OK) else (echo MISSING& exit /b 1)"
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\final_release_package_gate.py
.venv\Scripts\python.exe scripts\verify_release_package.py
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
```

Results:

- `node --check`: PASSED
- Desktop app module import: PASSED
- Root `start_app.bat` exists: PASSED
- `pytest`: 138 passed
- `final_release_package_gate.py`: PASSED
- `verify_release_package.py`: PASSED
- `real_production_quality_gate.py`: PASSED
- `final_acceptance_gate.py`: PASSED

## Latest Release Package

Latest package from `release\latest_release.json`:

```text
release\CyzellaProductionStudio_2026-05-15_133030
```

Package verification passed and confirmed:

- `start_app.bat` exists in the release package.
- `run_release_quality_gate.bat` exists in the release package.
- Release docs are present.
- Web UI, backend, scripts, examples, tests, outputs, backups, and logs are included.
- Quality gate scripts are registered.

## Safety Confirmation

Verified release safety state:

- Direct print: disabled
- Printer auto start: false
- CorelDRAW auto open: false
- Illustrator auto open: false
- RDWorks auto open: false
- Laser auto start: false
- Source AI/CDR modified: false

## Remaining Risk

- This pass did not open the GUI through `start_app.bat` to avoid leaving a blocking desktop app process running in the automation session.
- The module import and release package verification passed; a final human target-machine rehearsal should run `start_app.bat` interactively and confirm the window opens correctly.

## Next Recommended Step

Run a final human-style delivery rehearsal:

1. Open `start_app.bat`.
2. Produce one label from Etiket Studio.
3. Add it to Yazdırma Sırası.
4. Verify Etiket Çıktıları shows the output.
5. Confirm no direct print, RDWorks, laser, CorelDRAW, or Illustrator automation is triggered.
