# Global Design System Cleanup Report

Tarih: 2026-05-13

## Kısa Karar

Global design system cleanup güvenli şekilde tamamlandı. Bu çalışma fonksiyonel akışları yeniden yazmadan; kart, buton, input, modal, badge/pill ve empty state stillerini ortak token mantığına yaklaştırdı.

Son karar: Ana etiket MVP tarafında yeni P0/P1 görülmedi. UI/UX tarafında proje final insan testi aşamasına geçebilir.

## Neden Yapıldı?

Önceki polishlerden sonra sayfalar tek tek iyi seviyeye gelmişti; fakat bazı ortak UI parçaları farklı sayfalarda farklı radius, shadow, input yüksekliği ve button dili kullanıyordu. Bu durum özellikle Ana Sayfa, Etiket Modelleri, Toplu Etiket, Etiket Çıktıları ve Yazdırma Sırası arasında görsel tutarlılığı zayıflatıyordu.

Amaç:

- Ortak yüzey, border, shadow ve radius hissini standardize etmek.
- Primary / secondary / danger / ghost buton ayrımını daha tutarlı yapmak.
- Empty state, modal ve inputları Mac/iOS tarzı ortak bir kaliteye yaklaştırmak.
- Çalışan PDF/PNG, queue, output validation, drag/resize ve bulk akışlarını bozmadan düşük riskli polish yapmak.

## Değişen Dosyalar

- `src/webui/styles.css`
- `scripts/verify_design_system_consistency.py`
- `GLOBAL_DESIGN_SYSTEM_CLEANUP_REPORT.md`
- `CODEX_CURRENT_PRIORITY.md`
- `NEXT_AUTONOMOUS_TASKS.md`

## Uygulanan Tasarım Sistemi Katmanı

`src/webui/styles.css` sonuna düşük riskli ortak CSS katmanı eklendi.

Eklenen ortak tokenlar:

- `--ds-control-height`
- `--ds-control-height-sm`
- `--ds-radius-card`
- `--ds-radius-control`
- `--ds-radius-pill`
- `--ds-surface`
- `--ds-surface-soft`
- `--ds-border`
- `--ds-hover-border`
- `--ds-shadow-card`
- `--ds-shadow-control`

Ortaklaştırılan bileşen aileleri:

- Kartlar ve panel yüzeyleri
- Butonlar
- Icon buttonlar
- Input, select ve textarea kontrolleri
- Status pill / badge yapıları
- Modal kartları
- Empty state blokları
- Responsive sayfa shell davranışı

## Korunan Fonksiyonlar

Aşağıdaki kritik akışlara dokunulmadı ve testler tekrar geçti:

- Etiket Studio drag/resize
- PDF/PNG üretim zinciri
- Output validation
- Yazdırma Sırası güvenli modal akışı
- Direct/silent print kapalı kalması
- Etiket Çıktıları müşteri/teknik ayrımı
- Toplu Etiket galeri ve batch manifest akışı
- Queue duplicate/stale koruması

## Görsel QA Sonucu

Kontrol edilen ana ekranlar:

- `output/2026-05-13/ui_screenshots/ana_sayfa.png`
- `output/2026-05-13/ui_screenshots/etiket_modelleri.png`
- `output/2026-05-13/ui_screenshots/manuel_etiket.png`
- `output/2026-05-13/ui_screenshots/toplu_etiket_galeri.png`
- `output/2026-05-13/ui_screenshots/etiket_ciktilari.png`
- `output/2026-05-13/ui_screenshots/yazdirma_sirasi.png`
- `output/2026-05-13/ui_screenshots/yeni_model_ekle_modal.png`
- `output/2026-05-13/ui_screenshots/ayarlar.png`

Gözlem:

- Ana ekran kartları ve büyük aksiyonlar tutarlı görünüyor.
- Etiket Modelleri katalog görünümü preview ve sağ panel mantığını koruyor.
- Etiket Studio eski form düzenine dönmemiş; canvas, toolbar ve inspector düzeni korunmuş.
- Etiket Çıktıları varsayılan müşteri galerisinde kontrol gereken çıktıları kart gibi göstermiyor.
- Yazdırma Sırası varsayılan olarak yazdırmaya hazır iş yoksa bunu açık söylüyor ve kontrol gereken kayıtları ayrı akışta tutuyor.
- Yeni Model Wizard footer kesilmeden görünüyor.

P2 görsel risk:

- Toplu Etiket seçili detay panelinde bazı viewportlarda yatay scrollbar görülebiliyor. Üretimi engellemiyor; final polish/viewport iyileştirme listesinde tutulmalı.

## Test Sonuçları

Geçen komutlar:

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe scripts\verify_design_system_consistency.py`
- `.venv\Scripts\python.exe scripts\verify_outputs_gallery_flow.py`
- `.venv\Scripts\python.exe scripts\verify_print_queue_flow.py`
- `.venv\Scripts\python.exe scripts\verify_bulk_gallery_excel_flow.py`
- `.venv\Scripts\python.exe scripts\verify_corel_editor_interactions.py`
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`

Design system guard çıktısı:

- `output/2026-05-13/design_system/VERIFY_DESIGN_SYSTEM_CONSISTENCY_RESULT.json`

Son pytest sonucu:

- `128 passed`

## Güvenlik Teyidi

- Direct print açılmadı.
- Silent print yapılmadı.
- Yazıcı otomatik çalıştırılmadı.
- CorelDRAW açılmadı.
- Illustrator açılmadı.
- RDWorks açılmadı.
- Lazer başlatılmadı.
- Kaynak AI/CDR dosyaları değiştirilmedi.

## Kalan Riskler

P0: Bilinen yok.

P1: Ana etiket MVP tarafında bilinen açık P1 yok. Final insan testi sırasında çıkarsa önce düzeltilecek.

P2:

- Toplu Etiket seçili detay panelinde yatay scrollbar azaltılmalı.
- Bazı sayfalarda çok kalın tipografi yoğunluğu kullanıcı testinde yeniden gözlenmeli.
- Küçük desktop viewportlarda Etiket Studio property bar ve sağ inspector tekrar kontrol edilmeli.

P3 / ayrı faz:

- RDWorks gerçek text-to-path / outline / offset motoru ayrı teknik fazdır.
- Mevcut RDWorks çıktısı kullanıcıya “RDWorks’te manuel kontrol gerekli” uyarısıyla sunulmalıdır.

## Sıradaki İş

Sıradaki ana iş: Final UI/UX Real User Acceptance.

Bu aşamada tek etiket, yeni model, toplu Excel, queue, outputs, settings ve help akışları temiz veriyle insan gibi uçtan uca test edilecek. P0/P1 çıkarsa önce düzeltilecek.
