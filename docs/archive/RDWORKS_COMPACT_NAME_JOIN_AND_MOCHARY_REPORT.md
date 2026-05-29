# RDWorks Compact Name Join and Mochary Report

Date: 2026-05-14

## Summary

RDWorks / Isim Kesim flow now supports the requested "space separated names, compact side-by-side placement" behavior.

Example:

`ali ayse fatma leyla mucahit`

is normalized to:

`Ali Ayşe Fatma Leyla Mücahit`

When composition is set to `İsimleri Bitiştir`, the system does not merge the names into one connected word. Instead it splits each word into its own cutting unit and places them side-by-side with a small configurable gap, matching the RDWorks reference logic where names are packed close together but remain separate names.

## What Changed

- Added `Mochary Personal Use Only` as the first name cutting font preset.
- Added optional font lookup for `assets/fonts/Mochary Personal Use Only.ttf`.
- Added `joined_name_gap_mm` layout setting for compact name spacing.
- Added `İsimleri Bitiştir` composition mode to the UI.
- Manual name modal now defaults to `Mochary Personal Use Only`, `İsimleri Bitiştir`, and `Orta` thickening.
- Space-separated names are split into independent RDWorks layout/export units.
- Turkish name normalization now covers the requested examples, including `ayse`, `omer`, `mucahit`, `ali`, `fatma`, and `leyla`.
- Frontend preview and backend export use the same split-and-pack logic.
- Manifest records source text, split word order, compact spacing, text-to-path status, offset status, and font availability risk.

## Important Font Note

The Mochary font file is not currently present in the project font folder.

Expected path:

`assets/fonts/Mochary Personal Use Only.ttf`

Until that file is added or installed on Windows, backend outline export uses the safe script fallback and writes this risk into the manifest:

`P1_RISK_MOCHARY_FONT_FILE_NOT_FOUND_USING_SEGOE_SCRIPT_FALLBACK`

This is intentional. The program should not pretend the true Mochary outline was used when the font file is unavailable.

## RDWorks Safety

Confirmed safety boundaries:

- RDWorks was not opened automatically.
- Laser was not started.
- Direct print was not enabled.
- Printer was not started silently.
- CorelDRAW and Illustrator were not opened.
- Source AI/CDR files were not modified.

## Files Changed

- `src/webui_backend/combined_production_api.py`
- `src/webui/app.js`
- `src/webui/index.html`
- `src/webui/styles.css`
- `tests/test_combined_production_flow.py`
- `scripts/verify_rdworks_name_cut_layout_export.py`

## Tests Run

- `node --check src\webui\app.js` -> PASSED
- `.venv\Scripts\python.exe -m py_compile src\webui_backend\combined_production_api.py scripts\verify_rdworks_name_cut_layout_export.py` -> PASSED
- `.venv\Scripts\python.exe -m pytest tests\test_combined_production_flow.py -q` -> 5 passed
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py` -> PASSED
- `.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py` -> PASSED
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py -q` -> 120 passed
- `.venv\Scripts\python.exe -m pytest -q` -> 138 passed
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` -> PASSED
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` -> PASSED
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` -> PASSED

## Latest RDWorks Outputs

- `output/2026-05-14/name_cut/isim_kesim_batch_2026-05-14_234426.dxf`
- `output/2026-05-14/name_cut/isim_kesim_batch_2026-05-14_234426.svg`
- `output/2026-05-14/name_cut/isim_kesim_preview_2026-05-14_234426.pdf`
- `output/2026-05-14/name_cut/isim_kesim_preview_2026-05-14_234426.png`
- `output/2026-05-14/name_cut/name_cut_manifest_234426.json`

## Screenshots

- `output/2026-05-14/rdworks_name_cut_ready/name_cut_main.png`
- `output/2026-05-14/rdworks_name_cut_ready/name_cut_studio.png`
- `output/2026-05-14/rdworks_name_cut_ready/manual_name_modal.png`
- `output/2026-05-14/rdworks_name_cut_ready/manual_name_saved.png`
- `output/2026-05-14/rdworks_name_cut_ready/laser_layout_preview.png`
- `output/2026-05-14/rdworks_name_cut_ready/rdworks_export_panel.png`

## Remaining Risk

P1: True Mochary outlines require the actual Mochary font file. Add the font to `assets/fonts/Mochary Personal Use Only.ttf` before treating Mochary output as production-faithful.

