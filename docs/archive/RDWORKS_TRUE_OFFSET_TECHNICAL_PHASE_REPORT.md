# RDWORKS TRUE OFFSET TECHNICAL PHASE REPORT

Tarih: 2026-05-13

## Kısa Karar

RDWorks isim kesim export hattı tekrar doğrulandı ve güvenli sınırlar içinde bir üretim hatası kapatıldı:

- DXF zaten çoklu plate/page yerleşiminde isim konturlarına page offset uyguluyordu.
- SVG ara/export dosyasında isim path konturları çoklu plate durumunda aynı page offset ile taşınmıyordu.
- Bu düzeltildi; SVG path verisi artık ikinci ve sonraki plate koordinatlarını da taşır.
- Teste çoklu plate SVG path koordinatı kontrolü eklendi.

Gerçek boolean/geometrik offset motoru hâlâ bilinçli teknik risk olarak kalır. Mevcut sistem fontTools ile text-to-path/path outline üretir ve offset değerini kontur genişletme yaklaşımıyla geometriye yansıtır; ancak bu matematiksel olarak tam stroke-to-path / boolean offset motoru değildir.

## Değişen Teknik Davranış

### Çoklu Plate SVG Yerleşimi

Önce:

- `DXF` exportta ikinci ve sonraki plate için `page_y` uygulanıyordu.
- `SVG` exportta guide/support/back plate elemanları `page_y` alıyordu, fakat isim outline path konturları aynı offset ile aşağı taşınmayabiliyordu.

Sonra:

- `_translate_contours(...)` helper eklendi.
- `_svg_document(...)` içinde `_outline_contours_for_item(...)` sonucu SVG path'e yazılmadan önce `page_y` ile taşınıyor.
- Böylece RDWorks benzeri çoklu çalışma alanı / plate görünümünde SVG ve DXF yerleşimi aynı mantığı izliyor.

## Text-to-Path Durumu

Mevcut durum:

- Uygun font bulunduğunda fontTools ile glyph contour çıkarılır.
- SVG içinde isimler `path` olarak yazılır.
- DXF içinde isimler `POLYLINE` / `VERTEX` olarak yazılır.
- Manifest değeri: `OUTLINED_PATHS_WITH_FONTTOOLS`

Kalan risk:

- Font bulunamazsa fallback text riski korunur ve test bunu P1 olarak yakalar.
- Gerçek üretimde RDWorks tarafında font/path/layer kontrolü hâlâ önerilir.

## Kalınlaştırma / Offset Durumu

Mevcut durum:

- `Hafif`, `Orta`, `Kalın`, `Özel offset` değerleri manifest'e taşınır.
- Offset değeri contour expansion yaklaşımıyla export geometrisine yansıtılır.
- Manifest değeri offset istenen işlerde: `P1_RISK_APPROX_CONTOUR_EXPANSION_NOT_TRUE_OFFSET`

Kalan risk:

- Bu yöntem gerçek boolean/geometrik offset değildir.
- Tam üretim seviyesi için ileride Clipper/Skia/Inkscape benzeri doğrulanmış path offset motoru gerekir.
- Yeni dış bağımlılık veya harici conversion aracı kullanılacaksa ayrıca teknik karar gerekir.

## Güvenlik Teyidi

- RDWorks otomatik açılmadı.
- Lazer otomatik başlamadı.
- Direct/silent print aktif edilmedi.
- Yazıcı otomatik çalıştırılmadı.
- CorelDRAW ve Illustrator tetiklenmedi.
- Kaynak AI/CDR dosyalarına dokunulmadı.

## Değişen Dosyalar

- `src/webui_backend/combined_production_api.py`
- `scripts/verify_rdworks_name_cut_layout_export.py`
- `RDWORKS_TRUE_OFFSET_TECHNICAL_PHASE_REPORT.md`
- `CODEX_CURRENT_PRIORITY.md`
- `NEXT_AUTONOMOUS_TASKS.md`

## Çalıştırılan Testler

Geçti:

- `.venv\Scripts\python.exe -m py_compile src\webui_backend\combined_production_api.py scripts\verify_rdworks_name_cut_layout_export.py`
- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py`
- `.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py`
- `.venv\Scripts\python.exe -m pytest -q`
  - `128 passed`
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`

## Son Üretilen RDWorks Kanıtları

- DXF: `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_220718.dxf`
- SVG: `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_220718.svg`
- PDF preview: `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_220718.pdf`
- PNG preview: `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_220718.png`
- Manifest: `output/2026-05-13/name_cut/name_cut_manifest_220718.json`

Screenshotlar:

- `output/2026-05-13/rdworks_name_cut_ready/name_cut_main.png`
- `output/2026-05-13/rdworks_name_cut_ready/manual_name_modal.png`
- `output/2026-05-13/rdworks_name_cut_ready/manual_name_saved.png`
- `output/2026-05-13/rdworks_name_cut_ready/laser_layout_preview.png`
- `output/2026-05-13/rdworks_name_cut_ready/rdworks_export_panel.png`

## Son Karar

RDWorks hazırlık hattı güvenli dosya üretimi için daha tutarlı hale geldi: DXF birincil export, SVG ara/export, PDF/PNG preview ve manifest üretimi doğrulandı. Çoklu plate SVG path offset hatası kapandı.

Kalan ana teknik risk gerçek boolean/geometrik offsettir. Bu risk kapatılmadan isim kesim paketi için "tam otomatik üretime hazır" ifadesi kullanılmamalı; kullanıcıya "RDWorks'te manuel layer/path/offset kontrolü yapın" mesajı gösterilmeye devam edilmelidir.
