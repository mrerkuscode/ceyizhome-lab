# MODEL BACKUP VERSIONING UI REPORT

Tarih: 2026-05-08

## Görev

Etiket Modelleri sağ panelindeki backup geçmişini daha anlaşılır bir model versiyonlama görünümüne yaklaştırmak.

## Mevcut Sorun

Backup altyapısı çalışıyordu, ancak liste kullanıcıya dosya satırları gibi görünüyordu. Normal kullanıcı açısından kaç versiyon olduğu, son yedeğin ne zaman alındığı ve geri yükleme güvenliği yeterince belirgin değildi.

## Kök Neden

`loadSelectedModelBackupHistory()` sadece backup satırlarını listeliyordu. Özet ve güvenlik açıklaması yoktu; karşılaştırma ve geri yükleme aksiyonları doğruydu ama ekran ürün dili olarak “versiyon geçmişi” hissi vermiyordu.

## Değiştirilen Dosyalar

- `src/webui/app.js`
- `src/webui/styles.css`
- `tests/test_mvp_safety.py`

## Yapılan Düzeltmeler

- `modelBackupVersionSummaryHtml()` eklendi.
- Backup geçmişi üstüne özet kartları eklendi:
  - Kayıtlı versiyon sayısı
  - Son yedek zamanı
  - Toplam backup boyutu
- Her backup satırına “Son yedek” veya “Versiyon N” etiketi eklendi.
- Geri yükleme güvenlik notu görünür hale getirildi:
  - Geri yüklemeden önce mevcut model otomatik yedeklenir.
  - Kaynak AI/CDR dosyalarına dokunulmaz.
- CSS ile backup versiyon kartları ve versiyon pill görünümü eklendi.

## UI/UX Etkisi

Kullanıcı artık Etiket Modelleri sağ panelinde backup geçmişini model versiyon geçmişi gibi okuyabiliyor. Karşılaştırma ve geri yükleme aksiyonları korunurken, güvenli geri alma mantığı daha açık hale geldi.

## Render / Output / Queue Etkisi

PDF/PNG render zincirine, output validation’a ve queue sistemine dokunulmadı. Üretim kalite kapıları tekrar geçti.

## Güvenlik Etkisi

Geri yükleme davranışı değiştirilmedi; mevcut güvenlik kuralı korunuyor. Kaynak AI/CDR dosyalarına dokunulmadı, direct print veya harici uygulama çağrısı eklenmedi.

## Eklenen / Güncellenen Testler

- `tests/test_mvp_safety.py` içinde `modelBackupVersionSummaryHtml`, `backup-version-summary` ve `backup-version-pill` regression kilidine eklendi.
- Etiket Modelleri gerçek click gate tekrar çalıştırıldı; teknik editör izolasyonu ve doğru model taşıma akışları geçti.

## Çalıştırılan Komutlar

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: 110 passed.
- `.venv\Scripts\python.exe -m pytest`: 110 passed.
- `.venv\Scripts\python.exe scripts\label_models_real_click_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: geçti.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`: geçti.

## Screenshot Yolları

- `output/2026-05-08/label_models_click_gate`
- `output/2026-05-08/ui_screenshots`
- `output/2026-05-08/quality_gate`

## Kalan Riskler

- Bu adım tam kapsamlı “model versiyonlama ekranı” değildir; güvenli ve küçük bir UI güçlendirmesidir.
- İleride P3 olarak versiyon notu, versiyon adı ve iki versiyon arası seçmeli karşılaştırma eklenebilir.

## P0/P1 Durumu

Kalan P0/P1 hata görülmedi. Etiket Modelleri gerçek click testi, PDF/PNG kalite kapıları ve güvenlik kontrolleri geçti.
