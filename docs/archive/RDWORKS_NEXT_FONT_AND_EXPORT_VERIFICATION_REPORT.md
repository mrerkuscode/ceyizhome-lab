# RDWorks Next Font And Export Verification Report

Date: 2026-05-15

## Summary

Sıradaki RDWorks / İsim Kesim doğrulaması tamamlandı. Sistem, RDWorks için otomatik program açmadan DXF birincil export, SVG, PDF/PNG preview ve manifest üretmeye devam ediyor. 50 isimlik layout ve birleşik Excel etiket + isim kesim akışı tekrar geçti.

## Mochary Font Check

Known project/system paths checked:

- `assets\fonts\Mochary Personal Use Only.ttf` -> missing
- `assets\fonts\Mochary-Personal-Use-Only.ttf` -> missing
- `assets\fonts\Mochary.ttf` -> missing
- `C:\Windows\Fonts\Mochary Personal Use Only.ttf` -> missing
- `C:\Windows\Fonts\Mochary-Personal-Use-Only.ttf` -> missing
- `C:\Windows\Fonts\Mochary.ttf` -> missing

Result: Real Mochary file is still not available in the expected locations. The RDWorks export path remains functional with available/fallback script font handling, but exact Mochary visual matching cannot be certified until the real font file is provided or installed.

## RDWorks Export Verification

Command:

- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py` -> PASSED

Produced package:

- DXF: `output/2026-05-15/name_cut/isim_kesim_batch_2026-05-15_132636.dxf`
- SVG: `output/2026-05-15/name_cut/isim_kesim_batch_2026-05-15_132636.svg`
- PDF preview: `output/2026-05-15/name_cut/isim_kesim_preview_2026-05-15_132636.pdf`
- PNG preview: `output/2026-05-15/name_cut/isim_kesim_preview_2026-05-15_132636.png`
- Manifest: `output/2026-05-15/name_cut/name_cut_manifest_132636.json`

Manifest highlights:

- `text_to_path_status`: `OUTLINED_PATHS_WITH_FONTTOOLS`
- `thickening_status`: `TRUE_POLYGON_OFFSET_WITH_PYCLIPPER`
- `total_names`: 50
- `pages`: 5
- collision-free layout: passed by test
- within work area: passed by test

## Combined Excel + Name Cut Verification

Command:

- `.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py` -> PASSED

Produced package:

- DXF: `output/2026-05-15/name_cut/isim_kesim_batch_2026-05-15_132815.dxf`
- SVG: `output/2026-05-15/name_cut/isim_kesim_batch_2026-05-15_132815.svg`
- PDF preview: `output/2026-05-15/name_cut/isim_kesim_preview_2026-05-15_132815.pdf`
- PNG preview: `output/2026-05-15/name_cut/isim_kesim_preview_2026-05-15_132815.png`
- Manifest: `output/2026-05-15/name_cut/name_cut_manifest_132815.json`

Screenshots:

- Combined Excel loading: `output\2026-05-15\combined_production_flow\combined_excel_loading.png`
- Name cut gallery: `output\2026-05-15\combined_production_flow\name_cut_gallery.png`
- Name cut edit modal: `output\2026-05-15\combined_production_flow\name_cut_edit_modal.png`
- Turkish bridge / Mücahit modal: `output\2026-05-15\combined_production_flow\name_cut_edit_modal_mucahit_bridged.png`
- Saved badge: `output\2026-05-15\combined_production_flow\name_cut_saved_badge.png`
- Laser layout preview: `output\2026-05-15\combined_production_flow\laser_layout_preview.png`
- Export panel: `output\2026-05-15\combined_production_flow\rdworks_export_panel.png`

## Safety Confirmation

- RDWorks was not automatically opened.
- Laser was not started.
- Direct print remained disabled.
- Printer was not started.
- CorelDRAW and Illustrator were not opened.

## Remaining Risk

- P2/P3 visual fidelity risk: Exact Mochary appearance cannot be certified because the real Mochary font file is missing from expected project/system locations.
- RDWorks import remains a manual shop-floor check. The generated DXF should be opened manually in RDWorks to confirm layer colors, path/outline behavior, dimensions and cut preview before production.

## Next Step

Proceed to release / installation package verification. If the real Mochary font is later provided at `assets\fonts\Mochary Personal Use Only.ttf`, rerun:

- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py`
- `.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py`
