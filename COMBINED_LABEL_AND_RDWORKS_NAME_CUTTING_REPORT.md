# Combined Label and RDWorks Name Cutting Report

Tarih: 2026-05-13

## Ã–zet

Tek Excel dosyasÄ±ndan hem etiket Ã¼retim iÅŸleri hem de isim kesim / RDWorks hazÄ±rlÄ±k iÅŸleri ayrÄ±ÅŸtÄ±ran birleÅŸik Ã¼retim sistemi eklendi. Sistem satÄ±r bazÄ±nda `etiket_cikar` ve `isim_kes` kararlarÄ±nÄ± okur; aynÄ± satÄ±rdan sadece etiket, sadece isim kesim veya ikisi birden iÅŸ oluÅŸturabilir.

RDWorks, lazer, yazÄ±cÄ±, CorelDRAW ve Illustrator otomatik tetiklenmedi. Sistem yalnÄ±zca gÃ¼venli proje Ã§Ä±ktÄ±larÄ± hazÄ±rlar ve RDWorks tarafÄ±nda manuel kontrol gerektiÄŸini UI/manifest iÃ§inde bildirir.

## Desteklenen Excel KolonlarÄ±

Ana alanlar:

- `musteri_adi`, `isim`
- `tarih`
- `not`
- `adet`

Etiket alanlarÄ±:

- `etiket_cikar`, `etiket_var`, `etiket`, `label_required`
- `etiket_no`, `etiket_numarasÄ±`, `etiket_numarasi`, `model_no`, `model_numarasÄ±`, `model_numarasi`, `model_kodu`, `model`, `tasarÄ±m_no`, `tasarim_no`
- `etiket_adet`

Ä°sim kesim alanlarÄ±:

- `isim_kes`, `isim_kesim`, `lazer_isim`, `name_cut_required`
- `isim_kesim_adet`
- `isim_genislik_mm`, `isim_yukseklik_mm`
- `isim_font`, `isim_stil`
- `alt_destek`, `isim_destek`
- `taban_plaka`, `isim_plaka`

Evet/hayÄ±r deÄŸerleri normalize edilir. `evet/e/yes/y/true/1/x/var` evet; `hayÄ±r/hayir/h/no/false/0/boÅŸ/yok` hayÄ±r kabul edilir.

## Ãœretim AyrÄ±mÄ±

Her Excel satÄ±rÄ± `production_order_item` benzeri birleÅŸik stateâ€™e dÃ¶nÃ¼ÅŸÃ¼r:

- Etiket istenirse mevcut Toplu Etiket sistemiyle uyumlu `bulk_label_item` hattÄ±na girer.
- Ä°sim kesim istenirse ayrÄ± `name_cut_item` hattÄ±na girer.
- Ä°kisi birden istenirse aynÄ± satÄ±rdan iki Ã¼retim iÅŸi oluÅŸur.
- HiÃ§biri seÃ§ilmezse satÄ±r Ã¼retim yok uyarÄ±sÄ± alÄ±r.

Ã–nemli dÃ¼zeltme: Excelâ€™de `etiket_cikar = hayÄ±r` aÃ§Ä±kÃ§a yazÄ±lmÄ±ÅŸsa model numarasÄ± olsa bile etiket iÅŸi Ã¼retilmez. Ä°ÅŸaretleme kolonu varsa kullanÄ±cÄ± kararÄ± esas alÄ±nÄ±r.

## Ä°sim Formatlama

Ä°sim kesim hattÄ±nda isimler Ã¼retim Ã¶ncesi normalleÅŸtirilir:

- `ayse omer` -> `AyÅŸe Ã–mer`
- `cagla cagri` -> `Ã‡aÄŸla Ã‡aÄŸrÄ±`
- Her kelimenin ilk harfi bÃ¼yÃ¼k, kalan harfleri kÃ¼Ã§Ã¼k olur.
- Kelime iÃ§inde script/bitiÅŸik yazÄ± mantÄ±ÄŸÄ± korunur; kelimeler kontrollÃ¼ boÅŸlukla ayrÄ±lÄ±r.

TÃ¼rkÃ§e karakter ve nokta riski iÃ§in uyarÄ± Ã¼retilir. Alt destek veya taban plaka Ã¶nerisi UIâ€™da gÃ¶rÃ¼nÃ¼r.

## Ä°sim Kesim UI

Toplu Etiket sayfasÄ±na birleÅŸik Ã¼retim bÃ¶lÃ¼mÃ¼ eklendi:

- BirleÅŸik Ãœretim Merkezi KPI kartlarÄ±
- Etiket iÅŸleri kÄ±sa listesi
- Ä°sim Kesim Ä°ÅŸleri galerisi
- SeÃ§ili isim kesim detay paneli
- Lazer yerleÅŸim Ã¶nizlemesi
- RDWorks iÃ§in gÃ¼venli dÄ±ÅŸa aktarÄ±m paneli
- Ä°sim Kesim DÃ¼zenle modalÄ±

Modalda canlÄ± preview, stil, geniÅŸlik/yÃ¼kseklik, adet, alt destek ve taban plaka seÃ§enekleri Ã§alÄ±ÅŸÄ±r. Kaydet yalnÄ±zca seÃ§ili item stateâ€™ini gÃ¼nceller.

## Lazer YerleÅŸim

50 isimlik stres senaryosu basit shelf/bin-packing mantÄ±ÄŸÄ±yla Ã§alÄ±ÅŸma alanlarÄ±na dizildi.

VarsayÄ±lan Ã§alÄ±ÅŸma alanÄ±:

- 600 x 400 mm
- 10 mm kenar payÄ±
- 10 mm isimler arasÄ± boÅŸluk
- 10 mm satÄ±r boÅŸluÄŸu

DoÄŸrulama sonucu:

- 50 isim
- 50 kopya
- 4 Ã§alÄ±ÅŸma alanÄ±/sayfa
- Fire yaklaÅŸÄ±k `%42.6`

## Export Ã‡Ä±ktÄ±larÄ±

Son doÄŸrulamada Ã¼retilen dosyalar:

- `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_091222.svg`
- `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_091222.dxf`
- `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_091222.pdf`
- `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_091222.png`
- `output/2026-05-13/name_cut/name_cut_manifest_091222.json`

Layer standardÄ±:

- `CUT_NAME_OUTLINE`
- `CUT_SUPPORT_LINE`
- `CUT_BACK_PLATE`
- `GUIDE_PREVIEW`

## Text-to-Outline Durumu

Bu fazda fontTools ile SVG/DXF icinde font path/curve exportu eklendi. Manifest ve UI bunu aÃ§Ä±kÃ§a raporlar:

`OUTLINED_PATHS_WITH_FONTTOOLS`

Bu nedenle RDWorksâ€™te manuel font/path kontrolÃ¼ zorunlu uyarÄ± olarak bÄ±rakÄ±ldÄ±. RDWorks otomatik aÃ§Ä±lmaz; lazer otomatik baÅŸlamaz.

## DeÄŸiÅŸen Dosyalar

- `src/webui_backend/combined_production_api.py`
- `src/desktop/web_main_window.py`
- `src/webui_backend/bridge.py`
- `src/webui/app.js`
- `src/webui/index.html`
- `src/webui/styles.css`
- `tests/test_combined_production_flow.py`
- `scripts/verify_combined_excel_label_and_name_cut_flow.py`
- `examples/etiket_ve_isim_kesim_ornek.xlsx`
- `CODEX_CURRENT_PRIORITY.md`
- `NEXT_AUTONOMOUS_TASKS.md`

## Testler

Ã‡alÄ±ÅŸtÄ±rÄ±lan komutlar:

- `node --check src\webui\app.js` -> geÃ§ti
- `.venv\Scripts\python.exe -m py_compile src\webui_backend\combined_production_api.py src\desktop\web_main_window.py src\webui_backend\bridge.py scripts\verify_combined_excel_label_and_name_cut_flow.py` -> geÃ§ti
- `.venv\Scripts\python.exe -m pytest tests\test_combined_production_flow.py -q` -> `3 passed`
- `.venv\Scripts\python.exe -m pytest` -> `123 passed`
- `.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py` -> `PASSED`
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` -> `PASSED`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` -> `PASSED`
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` -> geÃ§ti

## Screenshot KanÄ±tlarÄ±

BirleÅŸik Ã¼retim ekranlarÄ±:

- `output/2026-05-13/combined_production_flow/combined_excel_loading.png`
- `output/2026-05-13/combined_production_flow/name_cut_gallery.png`
- `output/2026-05-13/combined_production_flow/name_cut_edit_modal.png`
- `output/2026-05-13/combined_production_flow/name_cut_saved_badge.png`
- `output/2026-05-13/combined_production_flow/laser_layout_preview.png`
- `output/2026-05-13/combined_production_flow/rdworks_export_panel.png`

Genel WebUI screenshot klasÃ¶rÃ¼:

- `output/2026-05-13/ui_screenshots/`

## GÃ¼venlik Teyidi

- RDWorks otomatik aÃ§Ä±lmadÄ±.
- Lazer otomatik baÅŸlamadÄ±.
- Direct print aktif edilmedi.
- YazÄ±cÄ± sessiz Ã§alÄ±ÅŸtÄ±rÄ±lmadÄ±.
- CorelDRAW / Illustrator tetiklenmedi.
- Kaynak AI/CDR dosyalarÄ± deÄŸiÅŸtirilmedi.

## Kalan Riskler

- P1: FontTools text-to-outline/path exportu eklendi; kalan manuel kontrol riski gercek geometrik offset icindir.
- P2: Ä°sim kesim galerisi iÃ§in daha geliÅŸmiÅŸ sayfalama/sanal grid 100+ satÄ±rlÄ± dosyalarda ileride daha iyi olur.
- P2: Dekoratif script preview ÅŸu an gÃ¼venli temsilidir; gerÃ§ek kesim kalitesi iÃ§in malzeme/font bazlÄ± ileri preflight eklenebilir.

## Son Karar

P0 hata yok. Etiket ve isim kesim iÅŸleri aynÄ± Excelâ€™den ayrÄ±labiliyor, isim kesim galerisi ve modalÄ± Ã§alÄ±ÅŸÄ±yor, 50 isimlik yerleÅŸim ve SVG/DXF/PDF/PNG/manifest export oluÅŸuyor. GÃ¼venli sÄ±nÄ±rlar korunmuÅŸtur.

## 2026-05-13 FontTools Outline Guncellemesi

RDWorks isim kesim exportu tekrar guncellendi:

- Basarili exportta SVG isimleri `path`, DXF isimleri `POLYLINE` olarak uretilir.
- Manifest `text_to_path_status` icin `OUTLINED_PATHS_WITH_FONTTOOLS` yazar.
- Font contour okunamazsa fallback `P1_RISK_TEXT_NOT_OUTLINED` olarak raporlanir ve bu durum basari sayilmaz.
- Kalinlastirma/offset artik sadece gorsel stroke degildir; contour geometrisine yaklasik genisletme uygulanir.
- Kalan P1 risk: bu yaklasim tam boolean/geometrik offset motoru degildir, bu nedenle RDWorks'te layer/offset manuel kontrolu gerekir.
- RDWorks, lazer, direct print, yazici, CorelDRAW ve Illustrator otomatik tetiklenmedi.

