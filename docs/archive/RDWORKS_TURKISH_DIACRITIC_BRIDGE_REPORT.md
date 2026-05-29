# RDWorks Turkish Diacritic Bridge Report

Date: 2026-05-15

## Summary

The RDWorks name cutting flow now handles Turkish dotted/marked characters in two places:

- Visual preview: the edit modal shows visible bridge marks over Turkish dot/mark characters.
- Export geometry: the DXF/SVG cutting outline receives automatic bridge contours before offset/thickening.

This specifically covers names such as:

- `ayse omer` -> `Ayse/Omer` with Turkish correction in the app/export as `Ayse Omer` equivalent with Turkish glyphs.
- `sedef sefer mucahit` -> `Sedef Sefer Mucahit` equivalent with `u` corrected to Turkish `u-umlaut` when matched by the correction table.
- Existing Turkish input like `mucahit` / `mücahit`, `irem`, `tugce`, `oguz`, `cagla`, `cagri`.

The important behavior is that dotted/marked Turkish characters no longer rely only on a warning badge. Bridge markers are visible in the preview and bridge contours are included in the cutting geometry.

## What Changed

- Added Turkish diacritic detection for the name-cut export path.
- Added automatic bridge contours for upper marks and lower marks in the name cutting outline pipeline.
- Added `diacritic_bridge_status` to every manifest item.
- Added polygon simplification before the pyclipper offset pass.
- Updated the name-cut UI preview so bridge markers are drawn relative to each word, including large modal preview.
- Strengthened the CSS bridge markers so they remain visible in the Mochary/script preview.
- Updated the combined Excel/name-cut verification script to type `Sedef Sefer mucahit`, assert bridge elements exist, and capture a dedicated screenshot.

## Current Behavior

When a formatted name contains Turkish dotted/marked characters, manifest items include:

```text
AUTO_TURKISH_DIACRITIC_BRIDGES_ADDED_TO_CUT_OUTLINE
```

Names without these characters include:

```text
NO_TURKISH_DIACRITIC_BRIDGE_REQUIRED
```

For `Isimleri Bitistir` / joined-name mode, the source string is split into separate name items for layout. Names are placed close together with the configured gap, but they are not merged into a single connected word.

## Latest Evidence

Latest combined-flow export:

- DXF: `output/2026-05-15/name_cut/isim_kesim_batch_2026-05-15_005923.dxf`
- SVG: `output/2026-05-15/name_cut/isim_kesim_batch_2026-05-15_005923.svg`
- PDF preview: `output/2026-05-15/name_cut/isim_kesim_preview_2026-05-15_005923.pdf`
- PNG preview: `output/2026-05-15/name_cut/isim_kesim_preview_2026-05-15_005923.png`
- Manifest: `output/2026-05-15/name_cut/name_cut_manifest_005923.json`
- Exact modal screenshot: `output/2026-05-15/combined_production_flow/name_cut_edit_modal_mucahit_bridged.png`

Latest RDWorks stress export:

- DXF: `output/2026-05-15/name_cut/isim_kesim_batch_2026-05-15_005145.dxf`
- SVG: `output/2026-05-15/name_cut/isim_kesim_batch_2026-05-15_005145.svg`
- PDF preview: `output/2026-05-15/name_cut/isim_kesim_preview_2026-05-15_005145.pdf`
- PNG preview: `output/2026-05-15/name_cut/isim_kesim_preview_2026-05-15_005145.png`
- Manifest: `output/2026-05-15/name_cut/name_cut_manifest_005145.json`

Manifest statuses confirmed:

```text
text_to_path_status: OUTLINED_PATHS_WITH_FONTTOOLS
text_to_outline_status: OUTLINED_PATHS_WITH_FONTTOOLS
thickening_status: TRUE_POLYGON_OFFSET_WITH_PYCLIPPER
diacritic_bridge_status: AUTO_TURKISH_DIACRITIC_BRIDGES_ADDED_TO_CUT_OUTLINE
```

## Safety

- RDWorks was not opened automatically.
- Laser was not started.
- Direct print remained disabled.
- Printer was not started.
- No speed/power machine settings were exported.

## Tests

Passed:

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest tests\test_combined_production_flow.py -q
.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py
.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
```

## Remaining Risk

Bridge placement is still conservative geometry derived from text layout. It is included in the exported cutting geometry, but the operator must inspect DXF/SVG in RDWorks before cutting, especially for very small names, mirror cutting, unusual font substitution, or material-specific tolerances.
