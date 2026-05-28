# RDWorks Mochary Auto Connection Report

Date: 2026-05-15

## Summary

Name cutting now has a safer Mochary-style connection rule for script exports.

The app cannot honestly recreate the exact Mochary font without the actual font file. Instead:

- If `assets/fonts/Mochary Personal Use Only.ttf` exists, the real font is used for fontTools outlines.
- If the real font does not exist, the system uses a script fallback and reports the font risk in the manifest.
- Mochary-style exports now apply automatic script connection tracking, especially between the capital first letter and the following lowercase letters.

## User-Facing Behavior

Input examples:

- `sedef sefer` -> `Sedef Sefer`
- `ali ayse fatma leyla mucahit` -> `Ali Ayşe Fatma Leyla Mücahit`
- `irem oguz ilker` -> `İrem Oğuz İlker`

Rules:

- Every word starts with an uppercase letter.
- Remaining letters are lowercase.
- Turkish name corrections are applied where known.
- In `İsimleri Bitiştir` mode, words remain separate names but are placed with a small configurable gap.
- Script preview uses contextual ligature/kerning features and tighter letter spacing.
- Backend DXF/SVG/PDF outline export uses automatic script connection tracking for Mochary/script styles.

## Technical Changes

- Added script connection profiles in `combined_production_api.py`.
- Mochary style now uses `AUTO_CAPITAL_CONNECTION_TRACKING_FOR_MOCHARY_STYLE`.
- Script styles use `AUTO_SCRIPT_CONNECTION_TRACKING`.
- Manifest items now include `script_connection_status`.
- Backend outline generation reduces word-internal spacing so capital letters connect more naturally with following lowercase letters.
- Frontend preview uses tighter script letter spacing and contextual ligature settings.
- Turkish casing fallback now handles `i` correctly as `İ`.

## Files Changed

- `src/webui_backend/combined_production_api.py`
- `src/webui/app.js`
- `src/webui/styles.css`
- `tests/test_combined_production_flow.py`

## Tests Run

- `node --check src\webui\app.js` -> PASSED
- `.venv\Scripts\python.exe -m py_compile src\webui_backend\combined_production_api.py` -> PASSED
- `.venv\Scripts\python.exe -m pytest tests\test_combined_production_flow.py -q` -> 5 passed
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py` -> PASSED
- `.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py` -> PASSED
- `.venv\Scripts\python.exe -m pytest -q` -> 138 passed
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` -> PASSED
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` -> PASSED

## Latest Outputs

- `output/2026-05-15/name_cut/isim_kesim_batch_2026-05-15_001521.dxf`
- `output/2026-05-15/name_cut/isim_kesim_batch_2026-05-15_001521.svg`
- `output/2026-05-15/name_cut/isim_kesim_preview_2026-05-15_001521.pdf`
- `output/2026-05-15/name_cut/isim_kesim_preview_2026-05-15_001521.png`
- `output/2026-05-15/name_cut/name_cut_manifest_001521.json`

## Remaining Risk

For exact Mochary visual output, the actual font file is still required:

`assets/fonts/Mochary Personal Use Only.ttf`

Without that file, the system remains safe and transparent, but it is not a true Mochary outline.

