# Release Launcher Gate Hardening Report

Date: 2026-05-15

## Summary

The delivery launcher path is now protected by the release quality gates.

The previous pass added a root-level `start_app.bat`. This pass made that launcher a required release gate artifact and rebuilt the release package so the latest package includes the new target-installation rehearsal report.

## Changes Made

- `scripts/final_release_package_gate.py`
  - Added root `start_app.bat` to required release paths.
  - If the root launcher is missing in the future, the final release package gate will fail.

- `scripts/build_release_package.py`
  - Added root `start_app.bat` to required copied files.
  - Added `TARGET_INSTALLATION_REHEARSAL_REPORT.md` to optional package reports.

- `scripts/verify_release_package.py`
  - Added `TARGET_INSTALLATION_REHEARSAL_REPORT.md` to optional reports that must be present in the package when present in the project root.

## New Release Package

Latest package:

```text
release\CyzellaProductionStudio_2026-05-15_182634
```

The new package contains:

- `start_app.bat`
- `run_release_quality_gate.bat`
- `TARGET_INSTALLATION_REHEARSAL_REPORT.md`
- `release_manifest.json`
- current scripts, docs, examples, tests, assets, templates, output placeholders, backups, and logs

## Verification Commands

```powershell
.venv\Scripts\python.exe -m py_compile scripts\final_release_package_gate.py scripts\build_release_package.py scripts\verify_release_package.py
.venv\Scripts\python.exe scripts\final_release_package_gate.py
.venv\Scripts\python.exe scripts\build_release_package.py
.venv\Scripts\python.exe scripts\verify_release_package.py
.venv\Scripts\python.exe -m pytest -q
node --check src\webui\app.js
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
```

## Results

- Python compile checks: PASSED
- `final_release_package_gate.py`: PASSED
- `build_release_package.py`: PASSED
- `verify_release_package.py`: PASSED
- `pytest`: 138 passed
- `node --check`: PASSED
- `real_production_quality_gate.py`: PASSED
- `final_acceptance_gate.py`: PASSED

## Safety Confirmation

Release manifest safety flags remain false:

- direct print enabled: false
- printer auto start: false
- CorelDRAW auto open: false
- Illustrator auto open: false
- RDWorks auto open: false
- laser auto start: false
- source AI/CDR modified: false

## Remaining Manual Check

The only remaining target-machine handoff step is interactive:

1. Double-click `start_app.bat`.
2. Confirm the Cyzella Production Studio window opens.
3. Run one human end-to-end smoke flow from model selection to PDF/PNG and queue.

This automation session intentionally did not leave the GUI app running.
