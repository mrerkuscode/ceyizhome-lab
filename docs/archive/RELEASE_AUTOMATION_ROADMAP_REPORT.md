# Release Automation Roadmap Report

Tarih: 2026-05-13

## Kısa Karar

Ana etiket üretim MVP'si manuel teslim/handoff için hazır durumdadır. Otomatik installer veya tek tık release paketleme henüz kurulmadı; bu P2/P3 release automation işi olarak bırakıldı.

Bu rapor kodu değiştirmez. Mevcut kalite kapılarını ve güvenlik sınırlarını bozmadan sonraki release otomasyon adımlarını tarif eder.

## Mevcut Teslim Durumu

Hazır olanlar:

- `USER_MANUAL.md`
- `TECHNICAL_MANUAL.md`
- `RELEASE_NOTES.md`
- `INSTALLATION_CHECKLIST.md`
- `FINAL_RELEASE_CHECKLIST.md`
- `FINAL_DELIVERY_PACKAGE_REVIEW_REPORT.md`
- `FINAL_HUMAN_QA_SIGNOFF_REPORT.md`

Hazır kalite kapıları:

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`

## Otomasyon Hedefi

Release automation ileriki fazda şu işleri tek komut veya kontrollü script ile yapmalı:

1. Testleri çalıştır.
2. Kalite kapılarını çalıştır.
3. Screenshotları üret.
4. Kullanıcı dokümanlarının varlığını doğrula.
5. Örnek Excel dosyalarını doğrula.
6. Çıktı klasör yapısını doğrula.
7. Direct print / RDWorks / lazer güvenlik bayraklarını doğrula.
8. Release klasörü oluştur.
9. Gerekli dosyaları release klasörüne kopyala.
10. Son manifest ve checksum üret.

## Önerilen Release Klasörü

```text
release/
  CyzellaProductionStudio/
    src/
    scripts/
    templates/
    assets/
    examples/
    docs/
    USER_MANUAL.md
    TECHNICAL_MANUAL.md
    RELEASE_NOTES.md
    INSTALLATION_CHECKLIST.md
    FINAL_RELEASE_CHECKLIST.md
    FINAL_HUMAN_QA_SIGNOFF_REPORT.md
    start_app.bat
    run_quality_gate.bat
```

## Önerilen Scriptler

### `scripts/build_release_package.py`

Yapacağı işler:

- Release klasörünü hazırlar.
- Kaynak dosyaları kopyalar.
- Gereksiz cache/test output dosyalarını hariç tutar.
- Dokümanları ve örnek Excel dosyalarını ekler.
- `release_manifest.json` üretir.

### `scripts/verify_release_package.py`

Yapacağı işler:

- Release klasörü eksiksiz mi kontrol eder.
- Kullanıcı dokümanları var mı kontrol eder.
- Örnek Excel dosyaları var mı kontrol eder.
- Güvenlik ayarlarında direct print kapalı mı kontrol eder.
- Ana quality gate raporları var mı kontrol eder.

### `run_release_quality_gate.bat`

Çalıştıracağı komutlar:

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
.venv\Scripts\python.exe scripts\capture_webui_screenshots.py
```

## Dikkat Edilecek Güvenlik Sınırları

Release automation kesinlikle şunları yapmamalı:

- CorelDRAW açmamalı.
- Illustrator açmamalı.
- RDWorks açmamalı.
- Lazer başlatmamalı.
- Yazıcıyı otomatik/direct/silent çalıştırmamalı.
- Kaynak AI/CDR dosyalarını değiştirmemeli.
- Proje dışı klasörleri temizlememeli.

## Kabul Kriteri

Release automation tamamlanmış sayılacaksa:

- Tek komutla kalite kapıları çalışmalı.
- Release klasörü deterministik oluşmalı.
- Kullanıcı dokümanları pakette bulunmalı.
- Örnek Excel dosyaları pakette bulunmalı.
- Güvenlik bayrakları raporlanmalı.
- Direct print kapalı kalmalı.
- RDWorks/lazer otomasyonu kapalı kalmalı.

## Kalan Durum

Bu faz uygulanmadı; roadmap olarak bırakıldı.

Öncelik: P2/P3.

Ana MVP teslimini bloklamaz.
