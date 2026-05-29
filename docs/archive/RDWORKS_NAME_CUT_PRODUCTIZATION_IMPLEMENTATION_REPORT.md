# RDWorks Name Cut Productization Implementation Report

## Kısa Karar

İsim Kesim / RDWorks hazırlık hattı bu fazda ayrı bir kullanıcı ekranı olarak güçlendirildi. Sistem hâlâ güvenli sınırda çalışır: RDWorks otomatik açılmaz, lazer başlamaz, direct print kullanılmaz. Program sadece DXF öncelikli üretim paketini hazırlar ve kullanıcı RDWorks içinde manuel kontrol yapar.

## Yapılanlar

- Sol menüye normal üretim akışında erişilebilir `İsim Kesim` sayfası eklendi.
- `İsim Kesim Studio` ekranı eklendi:
  - Excel ve manuel isim işleri aynı galeride görünür.
  - Seçili isim kesim detayı sağ panelde gösterilir.
  - RDWorks benzeri çalışma alanı önizlemesi aynı state üzerinden çalışır.
  - DXF/SVG/PDF/PNG/manifest export paneli ayrı ve görünür hale getirildi.
- Manuel isim ekleme ve düzenleme modalı mevcut üretim havuzuna bağlı kalacak şekilde güçlendirildi.
- Yerleşim ayarları değiştiğinde preview artık canlı olarak tekrar hesaplanır:
  - çalışma alanı
  - kenar payı
  - isimler arası boşluk
  - satır arası boşluk
  - ayna kesim
- Çok sayfalı/plate yerleşimler için plate seçici eklendi.
- Export panelinde RDWorks layer renk standardı net gösterildi:
  - kırmızı: ana kesim
  - mavi: alt destek
  - mor: taban/plaka
  - yeşil: kalibrasyon
  - gri: kılavuz
- Export sonucu panelde DXF, SVG, PDF, PNG ve manifest dosya adları gösterilir.

## Manifest ve Güvenlik

`name_cut_manifest.json` artık şu güvenlik ve üretim alanlarını da taşır:

- `manual_control_required: true`
- `machine_automation.rdworks_auto_open: false`
- `machine_automation.laser_auto_start: false`
- `machine_automation.direct_print: false`
- `machine_automation.speed_power_exported: false`
- `rdworks_layer_contract`
- `manual_rdworks_checklist`
- item bazında:
  - `rdworks_layer`
  - `support_layer`
  - `back_plate_layer`
  - `text_to_path_status`
  - `thickening_status`

DXF birincil export olarak kalır. SVG ara/destek formatıdır. PDF/PNG kullanıcı kontrol önizlemesi içindir.

## Değişen Dosyalar

- `src/webui/index.html`
- `src/webui/app.js`
- `src/webui/styles.css`
- `src/webui_backend/combined_production_api.py`
- `tests/test_combined_production_flow.py`
- `scripts/verify_rdworks_name_cut_layout_export.py`

## Test Sonuçları

- `node --check src\webui\app.js` geçti.
- `.venv\Scripts\python.exe -m py_compile src\webui_backend\combined_production_api.py scripts\verify_rdworks_name_cut_layout_export.py` geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_combined_production_flow.py -q` geçti: 4 passed.
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py` geçti.
- `.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py` geçti.
- `.venv\Scripts\python.exe -m pytest -q` geçti: 137 passed.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` geçti.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` geçti.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` geçti.

## Üretilen Örnek Çıktılar

- DXF: `output/2026-05-14/name_cut/isim_kesim_batch_2026-05-14_224204.dxf`
- SVG: `output/2026-05-14/name_cut/isim_kesim_batch_2026-05-14_224204.svg`
- PDF preview: `output/2026-05-14/name_cut/isim_kesim_preview_2026-05-14_224204.pdf`
- PNG preview: `output/2026-05-14/name_cut/isim_kesim_preview_2026-05-14_224204.png`
- Manifest: `output/2026-05-14/name_cut/name_cut_manifest_224204.json`

## Screenshot Kanıtları

- `output/2026-05-14/rdworks_name_cut_ready/name_cut_studio.png`
- `output/2026-05-14/rdworks_name_cut_ready/manual_name_modal.png`
- `output/2026-05-14/rdworks_name_cut_ready/manual_name_saved.png`
- `output/2026-05-14/rdworks_name_cut_ready/laser_layout_preview.png`
- `output/2026-05-14/rdworks_name_cut_ready/rdworks_export_panel.png`
- `output/2026-05-14/combined_production_flow/name_cut_gallery.png`
- `output/2026-05-14/combined_production_flow/name_cut_edit_modal.png`
- `output/2026-05-14/combined_production_flow/laser_layout_preview.png`

## Kalan Riskler

- Gerçek RDWorks import davranışı farklı makinelerde manuel kontrol gerektirir.
- `fontTools` path ve `pyclipper` offset hattı testte geçiyor; yine de gerçek lazer kesimden önce RDWorks içinde layer/path/ölçü kontrolü zorunludur.
- AI/PLT export bu fazda desteklenmez; DXF birincildir.
- Speed/power gibi makine ayarları bilerek export edilmez. Kullanıcı RDWorks layer ayarlarını manuel yapmalıdır.

## Son Karar

RDWorks / Lazer İsim Kesim fazında ürünleştirme katmanı tamamlandı: ayrı Studio ekranı, canlı yerleşim, DXF öncelikli paket, manifest güvenliği ve test kanıtları var. Bu faz “dosya hazırlama” seviyesinde güvenli; otomatik RDWorks/lazer kontrolü kapsam dışı kalmaya devam ediyor.
