# RDWorks Name Cut Ready Layout Export Report

Tarih: 2026-05-13

## Ã–zet

Ä°sim Kesim / RDWorks hazÄ±rlÄ±k hattÄ±, Excel veya manuel giriÅŸten gelen isimleri Ã¶lÃ§Ã¼lendirme, kompozisyon, kalÄ±nlaÅŸtÄ±rma/offset, alt destek, taban plaka, Ã§alÄ±ÅŸma alanÄ±na dizme ve SVG/DXF/PDF/PNG/manifest export akÄ±ÅŸÄ±na taÅŸÄ±yacak ÅŸekilde gÃ¼Ã§lendirildi.

GÃ¼venlik sÄ±nÄ±rÄ± korundu: RDWorks aÃ§Ä±lmadÄ±, lazer baÅŸlatÄ±lmadÄ±, direct print veya yazÄ±cÄ± tetiklenmedi.

## Uygulanan DeÄŸiÅŸiklikler

- Excel kolon desteÄŸi geniÅŸletildi:
  - `maksimum_genislik_mm`
  - `maksimum_yukseklik_mm`
  - `kompozisyon`
  - `kalinlastirma`
  - `kesim_kalinligi`
  - `offset_mm`
  - `ozel_offset_mm`
- Ä°sim Ã¶lÃ§Ã¼lendirme eklendi:
  - sadece geniÅŸlik verilirse yÃ¼kseklik otomatik hesaplanÄ±r
  - sadece yÃ¼kseklik verilirse geniÅŸlik otomatik hesaplanÄ±r
  - iki Ã¶lÃ§Ã¼ verilirse oran korunarak kutuya sÄ±ÄŸdÄ±rÄ±lÄ±r
  - maksimum geniÅŸlik/yÃ¼kseklik sÄ±nÄ±rÄ± uygulanÄ±r
- KalÄ±nlaÅŸtÄ±rma sistemi eklendi:
  - Yok: `0.0 mm`
  - Hafif: `0.4 mm`
  - Orta: `0.8 mm`
  - KalÄ±n: `1.2 mm`
  - Ã–zel offset: kullanÄ±cÄ± deÄŸeri
- SVG export artÄ±k tÃ¼m Ã§alÄ±ÅŸma alanlarÄ±nÄ±/sayfalarÄ± iÃ§erir.
- DXF export, isim layerâ€™Ä± yanÄ±nda destek/plaka layer bilgilerini ve kalÄ±nlaÅŸtÄ±rma notunu taÅŸÄ±r.
- Manifest geniÅŸletildi:
  - Ã§alÄ±ÅŸma alanÄ± Ã¶lÃ§Ã¼leri
  - margin/spacing
  - toplam isim/adet
  - kullanÄ±lan alan/fire oranÄ±
  - sayfa sayÄ±sÄ±
  - text-to-path durumu
  - thickening durumu
  - item bazlÄ± offset/kompozisyon/layer bilgileri
- UI tarafÄ±nda manuel isim ekleme ve dÃ¼zenleme gÃ¼Ã§lendirildi:
  - kompozisyon seÃ§imi
  - kesim kalÄ±nlÄ±ÄŸÄ± seÃ§imi
  - offset mm alanÄ±
  - alt destek/taban plaka
  - modal footer gÃ¶rÃ¼nÃ¼r tutuldu
  - yatay modal scroll pÃ¼rÃ¼zÃ¼ giderildi

## Export Durumu

OluÅŸan Ã¶rnek export:

- SVG: `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_102535.svg`
- DXF: `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_102535.dxf`
- PDF preview: `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_102535.pdf`
- PNG preview: `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_102535.png`
- Manifest: `output/2026-05-13/name_cut/name_cut_manifest_102535.json`
- Ã–rnek Excel: `examples/rdworks_isim_kesim_ornek.xlsx`

## Text-to-Path / Outline Durumu

Bu fazda gerÃ§ek font outline/path conversion yapÄ±lmadÄ±. SVG/DXF dosyalarÄ± Ã¼retildi, fakat manifest ÅŸu riski aÃ§Ä±kÃ§a raporlar:

- `text_to_path_status`: `OUTLINED_PATHS_WITH_FONTTOOLS`
- `thickening_status`: `P1_RISK_APPROX_CONTOUR_EXPANSION_NOT_TRUE_OFFSET`

Yani kalÄ±nlaÅŸtÄ±rma SVG stroke fallback ile temsil edilir. RDWorksâ€™te Ã¼retimden Ã¶nce font/path/outline ve offset kontrolÃ¼ manuel yapÄ±lmalÄ±dÄ±r. Bunu â€œtam path-ready Ã¼retimâ€ diye iÅŸaretlemedim.

## Testler

Ã‡alÄ±ÅŸtÄ±rÄ±lan komutlar:

- `node --check src\webui\app.js` â†’ PASSED
- `.venv\Scripts\python.exe -m py_compile src\webui_backend\combined_production_api.py src\desktop\web_main_window.py src\webui_backend\bridge.py scripts\verify_rdworks_name_cut_layout_export.py` â†’ PASSED
- `.venv\Scripts\python.exe -m pytest tests\test_combined_production_flow.py -q` â†’ 4 passed
- `.venv\Scripts\python.exe -m pytest` â†’ 124 passed
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py` â†’ PASSED
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` â†’ PASSED
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` â†’ PASSED
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` â†’ PASSED
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py` â†’ PASSED

Yeni script:

- `scripts/verify_rdworks_name_cut_layout_export.py`

Bu script ÅŸunlarÄ± doÄŸrular:

- `ayse omer` â†’ `AyÅŸe Ã–mer`
- `sedef sefer` alt alta kompozisyonu
- Ã¶zel offset Excelâ€™den alÄ±nÄ±r
- 50 isim Ã§alÄ±ÅŸma alanÄ±na yerleÅŸtirilir
- kullanÄ±lan alan/fire oranÄ± hesaplanÄ±r
- SVG/DXF/PDF/PNG/manifest oluÅŸur
- SVG `CUT_NAME_OUTLINE`, `CUT_SUPPORT_LINE`, `CUT_BACK_PLATE` taÅŸÄ±r
- manifest offset ve thickening bilgisini taÅŸÄ±r
- RDWorks/lazer/direct print/yazÄ±cÄ± tetiklenmez

## Screenshot KanÄ±tlarÄ±

- Ana Ä°sim Kesim ekranÄ±: `output/2026-05-13/rdworks_name_cut_ready/name_cut_main.png`
- Manuel isim modalÄ±: `output/2026-05-13/rdworks_name_cut_ready/manual_name_modal.png`
- Manuel isim kaydetme sonrasÄ±: `output/2026-05-13/rdworks_name_cut_ready/manual_name_saved.png`
- Lazer yerleÅŸim preview: `output/2026-05-13/rdworks_name_cut_ready/laser_layout_preview.png`
- RDWorks export paneli: `output/2026-05-13/rdworks_name_cut_ready/rdworks_export_panel.png`

## GÃ¼venlik Teyidi

- RDWorks otomatik aÃ§Ä±lmadÄ±.
- Lazer otomatik baÅŸlamadÄ±.
- YazÄ±cÄ±/direct print tetiklenmedi.
- CorelDRAW/Illustrator Ã§aÄŸrÄ±lmadÄ±.
- Kaynak AI/CDR dosyalarÄ± deÄŸiÅŸtirilmedi.

## Kalan Riskler

P1:

- FontTools outline export eklendi; fallback durumda manuel RDWorks kontrolu gerekir.
- GerÃ§ek geometrik offset/path offset henÃ¼z yok; stroke fallback kullanÄ±lÄ±yor.
- RDWorksâ€™te font/path/outline kontrolÃ¼ manuel yapÄ±lmalÄ±.

P2:

- Ä°sim kesim preview gÃ¶rsel olarak yeterli, ama gerÃ§ek font outline Ã¶nizlemesi kadar kesin deÄŸil.
- YerleÅŸim algoritmasÄ± basit shelf/bin-packing yaklaÅŸÄ±mÄ±dÄ±r; daha ileri fire optimizasyonu yapÄ±labilir.

## 2026-05-13 DXF-First Guncellemesi

Kullanicinin net RDWorks karari kalici hale getirildi:

- RDWorks icin birincil export hedefi `DXF` olarak isaretlendi.
- `SVG` artik ara/ikincil export veya teknik kontrol formatidir.
- Manifest alanlari eklendi:
  - `primary_rdworks_export`
  - `secondary_svg_export`
  - `export_priority`
  - `layer_color_standard`
  - `ai_export_status`
  - `plt_export_status`
  - `rdworks_primary_note`
- Return payload alanlari eklendi:
  - `primary_export_path`
  - `export_priority`
- DXF icine RDWorks layer tablosu ve renk kodlari eklendi:
  - `CUT_NAME_OUTLINE`: red / DXF color 1
  - `CUT_SUPPORT_LINE`: blue / DXF color 5
  - `CUT_BACK_PLATE`: purple / DXF color 6
  - `CALIBRATION`: green / DXF color 3
  - `GUIDE_PREVIEW`: gray / DXF color 8
- Calisma alani kilavuzu ve kalibrasyon cizgileri DXF'e eklendi.
- UI butonu `DXF/PDF Kesim Paketi Hazirla` mantigina tasindi.
- Kalici proje standardi olarak `RDWORKS_EXPORT_STANDARD.md` olusturuldu.

Son export kaniti:

- DXF: `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_111531.dxf`
- SVG: `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_111531.svg`
- PDF preview: `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_111531.pdf`
- PNG preview: `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_111531.png`
- Manifest: `output/2026-05-13/name_cut/name_cut_manifest_111531.json`

Teknik sinir acik kalir:

- `text_to_path_status`: `OUTLINED_PATHS_WITH_FONTTOOLS`
- `thickening_status`: `P1_RISK_APPROX_CONTOUR_EXPANSION_NOT_TRUE_OFFSET`

Yani DXF paketi RDWorks layer/renk/yerlesim mantigina gore hazirdir; fakat gercek text-to-path ve gercek vektor offset henuz tam uretim garantisi olarak isaretlenmez. RDWorks'te manuel font/path/offset kontrolu zorunludur.

## Son Karar

RDWorks iÃ§in gÃ¼venli dosya hazÄ±rlama akÄ±ÅŸÄ± Ã§alÄ±ÅŸÄ±yor: isimler Ã¶lÃ§Ã¼lendiriliyor, kalÄ±nlaÅŸtÄ±rma/offset bilgisi taÅŸÄ±nÄ±yor, 50 isim Ã§alÄ±ÅŸma alanÄ±na diziliyor, SVG/DXF/PDF/PNG/manifest Ã¼retiliyor.

FontTools outline export eklendigi icin son dogrulamada SVG `path` ve DXF `POLYLINE` uretilmistir. Kalan P1 risk gercek boolean/geometrik offset motorudur; mevcut kalinlastirma yaklasik contour expansion olarak export geometrisine yansir. RDWorks'te layer/offset manuel kontrolu onerilir. Lazer veya RDWorks otomasyonu baslatilmadi.

## 2026-05-13 FontTools Outline Guncellemesi

- Son dogrulanan `text_to_path_status`: `OUTLINED_PATHS_WITH_FONTTOOLS`
- Son dogrulanan offsetli akista `thickening_status`: `P1_RISK_APPROX_CONTOUR_EXPANSION_NOT_TRUE_OFFSET`
- SVG isimleri `CUT_NAME_OUTLINE` altinda `path` olarak uretilir.
- DXF isimleri `CUT_NAME_OUTLINE` layer'inda `POLYLINE` olarak uretilir.
- Font contour okunamazsa fallback olarak `P1_RISK_TEXT_NOT_OUTLINED` raporlanir; bu fallback basari sayilmaz.
- Gercek offset/stroke-to-path icin ileride boolean offset motoru veya dogrulanmis dis arac gerekir.

