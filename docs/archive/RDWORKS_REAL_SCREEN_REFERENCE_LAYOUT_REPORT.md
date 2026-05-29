# RDWorks Real Screen Reference Layout Report

Tarih: 2026-05-13

## Referans Analizi

KullanÄ±cÄ±nÄ±n paylaÅŸtÄ±ÄŸÄ± gerÃ§ek RDWorks ekranÄ±nda Ã¼retim dosyasÄ± tek tek isim dosyalarÄ± gibi deÄŸil, tek Ã§alÄ±ÅŸma alanÄ±na sÄ±k dizilmiÅŸ isimlerden oluÅŸuyor. GÃ¶rselde beyaz Ã§alÄ±ÅŸma alanÄ±, grid/kÄ±lavuz mantÄ±ÄŸÄ±, satÄ±r satÄ±r dizilmiÅŸ Ã§ok sayÄ±da script isim, Ã§alÄ±ÅŸma alanÄ± sÄ±nÄ±rlarÄ± ve grup seÃ§imi hissi var.

Bu nedenle Cyzella isim kesim hedefi ÅŸu ÅŸekilde netleÅŸtirildi:

- Ä°simler tek plate / Ã§alÄ±ÅŸma alanÄ± iÃ§inde toplu dizilir.
- SÄ±ÄŸmayan isimler yeni satÄ±ra veya yeni plate/sayfaya geÃ§er.
- Ã‡alÄ±ÅŸma alanÄ± sÄ±nÄ±rÄ± aÅŸÄ±lmaz.
- DXF birincil RDWorks dosyasÄ±dÄ±r.
- Layer renkleri RDWorks mantÄ±ÄŸÄ±na gÃ¶re ayrÄ±lÄ±r.
- Ayna pleksi iÃ§in ayna/ters kesim modu desteklenir.
- RDWorks ve lazer otomatik aÃ§Ä±lmaz.

## Uygulanan DeÄŸiÅŸiklikler

- `LayoutConfig` iÃ§ine `mirror_cut` eklendi.
- Export config artÄ±k UIâ€™dan Ã§alÄ±ÅŸma alanÄ± Ã¶lÃ§Ã¼sÃ¼, kenar payÄ±, isim arasÄ± boÅŸluk, satÄ±r arasÄ± boÅŸluk ve ayna kesim modunu alabilir.
- UIâ€™da RDWorks export paneline ayarlar eklendi:
  - Alan W
  - Alan H
  - Kenar
  - Ä°sim arasÄ±
  - SatÄ±r arasÄ±
  - Ayna Kesim
- Cyzella iÃ§indeki lazer yerleÅŸim Ã¶nizlemesi RDWorks referansÄ±na yaklaÅŸtÄ±rÄ±ldÄ±:
  - beyaz Ã§alÄ±ÅŸma alanÄ±
  - grid
  - siyah outline gÃ¶rÃ¼nÃ¼mlÃ¼ script isimler
  - Ã§alÄ±ÅŸma alanÄ± sÄ±nÄ±rÄ±
  - ayna kesim durumu
- DXF export mirror mode bilgisini taÅŸÄ±r:
  - `MIRROR_CUT True`
  - mirrored text fallback iÃ§in `41 -1`
- SVG export mirror mode aÃ§Ä±ksa textâ€™i yatay tersleyerek yazar.
- Manifest iÃ§ine `mirror_cut` alanÄ± eklendi.

## Dizilim MantÄ±ÄŸÄ±

Mevcut yerleÅŸim algoritmasÄ± Ã¼retim iÃ§in gÃ¼venli basit shelf/bin-packing yaklaÅŸÄ±mÄ±dÄ±r:

- Ä°simler yÃ¼kseklik/geniÅŸlik deÄŸerine gÃ¶re bÃ¼yÃ¼kten kÃ¼Ã§Ã¼ÄŸe sÄ±ralanÄ±r.
- Soldan saÄŸa yerleÅŸtirilir.
- SatÄ±r dolarsa alt satÄ±ra geÃ§er.
- Plate dolarsa yeni plate/sayfa aÃ§Ä±lÄ±r.
- KullanÄ±lan alan ve fire yÃ¼zdesi hesaplanÄ±r.
- Ä°simler Ã¼st Ã¼ste bindirilmez.

## KalÄ±nlaÅŸtÄ±rma / Offset Durumu

KullanÄ±cÄ± ayarlarÄ±:

- Yok
- Hafif
- Orta
- KalÄ±n
- Ã–zel offset mm

Mevcut teknik durum:

- Offset deÄŸeri manifest ve DXF/SVG metadata iÃ§inde taÅŸÄ±nÄ±r.
- SVG tarafÄ±nda stroke fallback kullanÄ±lÄ±r.
- DXF tarafÄ±nda kalÄ±nlaÅŸtÄ±rma bilgisi `THICKENING ... OFFSET_MM ...` notu olarak taÅŸÄ±nÄ±r.

P1 risk devam eder:

- GerÃ§ek geometrik stroke-to-path / offset conversion henÃ¼z yok.
- RDWorksâ€™te Ã¼retim Ã¶ncesi offset/outline manuel kontrol edilmelidir.

## Text-to-Path Durumu

P1 risk devam eder:

- Basarili exportta isimler DXF icinde `POLYLINE` entity olarak uretilir; font contour okunamazsa text fallback riski raporlanir.
- FontTools outline export son dogrulamada calisti; font contour okunamazsa fallback manuel kontrol riski verir.
- Bu nedenle sistem â€œtam path-ready Ã¼retimâ€ demez; â€œRDWorks kontrol gerekliâ€ der.

Manifest riskleri:

- `text_to_path_status`: `OUTLINED_PATHS_WITH_FONTTOOLS`
- `thickening_status`: `P1_RISK_APPROX_CONTOUR_EXPANSION_NOT_TRUE_OFFSET`

## Export Durumu

Birincil:

- DXF

Ek Ã§Ä±ktÄ±lar:

- SVG
- PDF preview
- PNG preview
- `name_cut_manifest.json`

Layer standardÄ±:

- `CUT_NAME_OUTLINE`: kÄ±rmÄ±zÄ± / ana kesim
- `CUT_SUPPORT_LINE`: mavi / alt destek
- `CUT_BACK_PLATE`: mor / taban/plaka
- `CALIBRATION`: yeÅŸil / kalibrasyon
- `GUIDE_PREVIEW`: gri / kÄ±lavuz

## GÃ¼venlik

DoÄŸrulanan sÄ±nÄ±rlar:

- RDWorks otomatik aÃ§Ä±lmaz.
- Lazer otomatik baÅŸlamaz.
- Direct print aktif edilmez.
- YazÄ±cÄ± sessiz Ã§alÄ±ÅŸtÄ±rÄ±lmaz.
- CorelDRAW/Illustrator Ã§aÄŸrÄ±lmaz.
- Kaynak AI/CDR dosyalarÄ± deÄŸiÅŸtirilmez.

## Testler ve SonuÃ§lar

Ã‡alÄ±ÅŸtÄ±rÄ±lan komutlar:

- `node --check src\webui\app.js`: GEÃ‡TÄ°.
- `.venv\Scripts\python.exe -m py_compile src\webui_backend\combined_production_api.py src\desktop\web_main_window.py src\webui_backend\bridge.py scripts\verify_rdworks_name_cut_layout_export.py`: GEÃ‡TÄ°.
- `.venv\Scripts\python.exe -m pytest tests\test_combined_production_flow.py -q`: 4 passed.
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py`: PASSED.
- `.venv\Scripts\python.exe -m pytest`: 124 passed.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: GEÃ‡TÄ°.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`: GEÃ‡TÄ°.

Son RDWorks export paketi:

- DXF: `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_115234.dxf`
- SVG: `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_115234.svg`
- PDF preview: `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_115234.pdf`
- PNG preview: `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_115234.png`
- Manifest: `output/2026-05-13/name_cut/name_cut_manifest_115234.json`

Son screenshot kanÄ±tlarÄ±:

- `output/2026-05-13/rdworks_name_cut_ready/name_cut_main.png`
- `output/2026-05-13/rdworks_name_cut_ready/manual_name_modal.png`
- `output/2026-05-13/rdworks_name_cut_ready/manual_name_saved.png`
- `output/2026-05-13/rdworks_name_cut_ready/laser_layout_preview.png`
- `output/2026-05-13/rdworks_name_cut_ready/rdworks_export_panel.png`
- `output/2026-05-13/quality_gate/quality_gate_live_canvas.png`
- `output/2026-05-13/quality_gate/quality_gate_pdf_preview_modal.png`
- `output/2026-05-13/quality_gate/quality_gate_png_preview.png`
- `output/2026-05-13/quality_gate/quality_gate_print_queue.png`

## Kalan Riskler

P1:

- FontTools outline export calisiyor; font contour okunamazsa fallback durumda manuel RDWorks kontrolu gerekir.
- Gercek vektor offset/stroke-to-path kalinlastirma henuz yok; mevcut kalinlastirma yaklasik contour expansion olarak uygulanir.

P2:

- YerleÅŸim algoritmasÄ± Ã¼retim iÃ§in gÃ¼venli ve deterministik, fakat daha geliÅŸmiÅŸ fire optimizasyonu yapÄ±labilir.

## 2026-05-13 FontTools Outline Guncellemesi

Gercek RDWorks referansina yaklasmak icin export pipeline guncellendi:

- Basarili exportta SVG tarafinda isimler `path`, DXF tarafinda `POLYLINE` olarak uretilir.
- Manifest `text_to_path_status` icin `OUTLINED_PATHS_WITH_FONTTOOLS` yazar.
- Offset istenirse contour noktalarina yaklasik disa genisletme uygulanir ve `P1_RISK_APPROX_CONTOUR_EXPANSION_NOT_TRUE_OFFSET` olarak raporlanir.
- Bu, stroke-only preview degildir; ancak tam geometrik offset motoru da degildir.
- RDWorks/lazer otomatik tetiklenmedi; kullanici dosyayi RDWorks'te manuel acar ve layer/offset ayarlarini kontrol eder.

