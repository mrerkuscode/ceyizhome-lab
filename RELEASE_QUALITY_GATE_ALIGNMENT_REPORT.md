# RELEASE QUALITY GATE ALIGNMENT REPORT

Tarih: 2026-05-14

## Kısa Karar

Release kalite kapısı güncel MVP kabul seviyesine hizalandı. Paket tesliminden önce artık sadece genel `pytest`, üretim kalite kapısı ve final kabul kapısı değil; temiz müşteri demo akışı, RDWorks isim kesim export kapısı ve birleşik Excel etiket + isim kesim kapısı da çalıştırılıyor.

## Neden Gerekliydi?

Önceki release kapısı çekirdek üretim zincirini koruyordu; ancak son eklenen kritik kabul alanları paket kapısına bağlı değildi:

- Temiz müşteri demo görünümü ve Test/QA arşiv ayrımı.
- RDWorks için DXF birincil export, SVG/PDF/PNG preview ve manifest doğrulaması.
- Birleşik Excel akışında etiket üretimi + isim kesim ayrımı.

Bu eksik, proje kökünde testleri geçen bir özelliğin release paketinde kalite kapısına dahil olmaması riskini taşıyordu.

## Yapılan Değişiklikler

- `run_release_quality_gate.bat` güncellendi.
  - `scripts\verify_clean_customer_demo_flow.py`
  - `scripts\verify_rdworks_name_cut_layout_export.py`
  - `scripts\verify_combined_excel_label_and_name_cut_flow.py`
  artık release kapısında çalışıyor.
- `scripts\build_release_package.py` güncellendi.
  - Paket içine yazılan `run_release_quality_gate.bat` aynı yeni kapıları içeriyor.
  - Yeni teslim raporları opsiyonel release dosyaları arasına eklendi.
- `scripts\verify_release_package.py` güçlendirildi.
  - Release paketindeki kalite kapısı batch dosyasında güncel komutların bulunduğunu doğruluyor.
  - Temiz demo, RDWorks packing ve kullanıcı teslim raporları varsa pakete kopyalandığını doğruluyor.
- `FINAL_RELEASE_CHECKLIST.md` güncellendi.
  - Temiz demo seed, RDWorks ve birleşik Excel doğrulamaları final checklist içine alındı.
- `INSTALLATION_CHECKLIST.md` güncellendi.
  - Temiz demo seed ve Test/QA arşiv ayrımı kurulum sonrası kontrol maddelerine eklendi.

## Oluşturulan Release Paketi

- Son release klasörü `release\latest_release.json` içinde kayıtlıdır.
- Manifest:
  - Son paket klasörü içindeki `release_manifest.json`
- Manifest dosya sayısı:
  - 223

## Güvenlik Teyidi

Release manifest güvenlik bayrakları:

- `direct_print_enabled`: false
- `printer_auto_start`: false
- `coreldraw_auto_open`: false
- `illustrator_auto_open`: false
- `rdworks_auto_open`: false
- `laser_auto_start`: false
- `source_ai_cdr_modified`: false

RDWorks/lazer/yazıcı otomatik tetiklenmedi. Program dosya hazırlar, kullanıcı manuel kontrol eder.

## Çalıştırılan Komutlar

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe scripts\final_release_package_gate.py
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py
.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py
.venv\Scripts\python.exe scripts\verify_clean_customer_demo_flow.py
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
.venv\Scripts\python.exe scripts\build_release_package.py
.venv\Scripts\python.exe scripts\verify_release_package.py
```

## Komut Sonuçları

- `node --check src\webui\app.js`: PASSED
- `final_release_package_gate.py`: PASSED
- `pytest -q`: 135 passed
- `verify_rdworks_name_cut_layout_export.py`: PASSED
- `verify_combined_excel_label_and_name_cut_flow.py`: PASSED
- `verify_clean_customer_demo_flow.py`: PASSED
- `real_production_quality_gate.py`: PASSED
- `final_acceptance_gate.py`: PASSED
- `build_release_package.py`: PASSED
- `verify_release_package.py`: PASSED

## Önemli Kanıt Çıktıları

- Temiz müşteri screenshotları:
  - `output\2026-05-14\clean_customer_demo_flow\outputs_customer_gallery.png`
  - `output\2026-05-14\clean_customer_demo_flow\queue_customer_ready.png`
  - `output\2026-05-14\clean_customer_demo_flow\queue_customer_print_modal.png`
- RDWorks export örneği:
  - `output\2026-05-14\name_cut\isim_kesim_batch_2026-05-14_020808.dxf`
  - `output\2026-05-14\name_cut\isim_kesim_batch_2026-05-14_020808.svg`
  - `output\2026-05-14\name_cut\isim_kesim_preview_2026-05-14_020808.pdf`
  - `output\2026-05-14\name_cut\isim_kesim_preview_2026-05-14_020808.png`
  - `output\2026-05-14\name_cut\name_cut_manifest_020808.json`

## Kalan Riskler

- Bilinen P0/P1 yok.
- RDWorks gerçek makine/saha doğrulaması hâlâ manuel operatör kontrolü gerektirir.
- Release paketi temiz kuruluma hazırdır; ilk çalıştırmada kullanıcı `setup.bat` ile sanal ortamı kurmalıdır.
