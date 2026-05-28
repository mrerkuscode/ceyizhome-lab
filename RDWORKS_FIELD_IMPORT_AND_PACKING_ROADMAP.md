# RDWorks Field Import and Packing Roadmap

Tarih: 2026-05-14

## Kısa Karar

RDWorks isim kesim export hattı güvenli şekilde güçlendirildi. DXF birincil export olmaya devam ediyor; SVG/PDF/PNG preview ve JSON manifest korunuyor. Packing algoritması artık basit tek satır akışı yerine `FIRST_FIT_SHELF_HEIGHT_DESC` stratejisiyle küçük işleri önceki satır boşluklarına yerleştirmeyi deniyor.

P0/P1 kalan: Yok.

Not: RDWorks gerçek import ve kesim ayarları operatör tarafından RDWorks içinde manuel kontrol edilmelidir. Program RDWorks'ü açmaz, lazeri başlatmaz.

## Yapılan Değişiklikler

- `src/webui_backend/combined_production_api.py`
  - `layout_name_cut_items()` first-fit shelf packing stratejisine taşındı.
  - Yerleşim özeti `placement_strategy`, `collision_free`, `within_work_area` ve `page_stats` alanlarını üretir.
  - Export manifest aynı alanları taşır.
  - Çalışma alanı sınırları ve çakışma durumu hesaplanır.

- `tests/test_combined_production_flow.py`
  - Packing stratejisi, çakışmasızlık, çalışma alanı sınırı ve manifest alanları test edildi.

- `scripts/verify_rdworks_name_cut_layout_export.py`
  - 50/100 isim için packing stratejisi, çakışmasız yerleşim ve manifest güvenli yerleşim alanları doğrulandı.

## RDWorks Export Durumu

Son doğrulama çıktıları:

- DXF: `output/2026-05-14/name_cut/isim_kesim_batch_2026-05-14_020049.dxf`
- SVG: `output/2026-05-14/name_cut/isim_kesim_batch_2026-05-14_020049.svg`
- PDF preview: `output/2026-05-14/name_cut/isim_kesim_preview_2026-05-14_020049.pdf`
- PNG preview: `output/2026-05-14/name_cut/isim_kesim_preview_2026-05-14_020049.png`
- Manifest: `output/2026-05-14/name_cut/name_cut_manifest_020049.json`

Birleşik Excel hattı çıktısı:

- DXF: `output/2026-05-14/name_cut/isim_kesim_batch_2026-05-14_020128.dxf`
- Manifest: `output/2026-05-14/name_cut/name_cut_manifest_020128.json`

## Manifest Kanıtları

Manifest artık şu alanları taşır:

- `primary_rdworks_export`
- `export_priority`
- `layer_color_standard`
- `text_to_path_status`
- `text_to_outline_status`
- `thickening_status`
- `placement_strategy`
- `collision_free`
- `within_work_area`
- `page_stats`

RDWorks katman/renk standardı korunur:

- `CUT_NAME_OUTLINE`: kırmızı ana kesim
- `CUT_SUPPORT_LINE`: mavi destek çizgisi
- `CUT_BACK_PLATE`: mor taban/plaka
- `CALIBRATION`: yeşil kalibrasyon
- `GUIDE_PREVIEW`: gri kılavuz

## Packing Sonucu

`verify_rdworks_name_cut_layout_export.py` 50 isimlik senaryoda:

- Placement: `FIRST_FIT_SHELF_HEIGHT_DESC`
- Collision free: true
- Within work area: true
- Text to path: `OUTLINED_PATHS_WITH_FONTTOOLS`
- Thickening: `TRUE_POLYGON_OFFSET_WITH_PYCLIPPER`

`verify_combined_excel_label_and_name_cut_flow.py` 50 isimlik birleşik üretim senaryosunda:

- 50 isim 4 plate içinde yerleşti.
- Collision free: true
- Within work area: true
- RDWorks/lazer/direct print otomatik tetiklenmedi.

## Test Sonuçları

```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_combined_production_flow.py
# 4 passed

.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py
# PASSED

.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py
# PASSED

.venv\Scripts\python.exe -m pytest -q
# 135 passed

node --check src\webui\app.js
# PASSED

.venv\Scripts\python.exe scripts\real_production_quality_gate.py
# PASSED

.venv\Scripts\python.exe scripts\final_acceptance_gate.py
# PASSED
```

## Screenshot Kanıtları

- `output/2026-05-14/rdworks_name_cut_ready/name_cut_main.png`
- `output/2026-05-14/rdworks_name_cut_ready/manual_name_modal.png`
- `output/2026-05-14/rdworks_name_cut_ready/manual_name_saved.png`
- `output/2026-05-14/rdworks_name_cut_ready/laser_layout_preview.png`
- `output/2026-05-14/rdworks_name_cut_ready/rdworks_export_panel.png`
- `output/2026-05-14/combined_production_flow/name_cut_gallery.png`
- `output/2026-05-14/combined_production_flow/laser_layout_preview.png`
- `output/2026-05-14/combined_production_flow/rdworks_export_panel.png`

## Kalan P2/P3 İyileştirmeler

- Gerçek RDWorks uygulamasında manuel import ekran görüntüsüyle saha doğrulaması yapılmalı.
- Fire azaltma için ileride gerçek bin-packing/guillotine algoritması eklenebilir.
- AI/PLT export bu fazda desteklenmiyor; DXF birincil çıktı olarak kalır.
- Operatör RDWorks içinde layer hız/güç ayarlarını manuel kontrol etmelidir.
