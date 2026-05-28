# OUTPUT AND QUEUE METADATA RELIABILITY REPORT

Tarih: 2026-05-14

## Kısa Karar

Queue ve Etiket Çıktıları ekranları temiz müşteri demo verisiyle yeniden doğrulandı. Varsayılan kullanıcı görünümünde müşteri işleri öne çıkıyor, QA/test/teknik kayıtlar arşiv/filtre altında tutuluyor, yazdırma akışı yine kullanıcı onaylı kalıyor.

Bu aşama tamamlandı. Bilinen P0/P1 yok.

## Önceki Sorun

- Yazdırma Sırası ve Etiket Çıktıları ekranlarında eski QA/test/stale üretim kayıtları final kullanıcı deneyimini bozuyordu.
- Model adı, isim, tarih, not, ölçü ve adet bilgileri bazı eski çıktılarda dosya adından veya eksik fallback bilgisinden okunuyordu.
- `Rulo Etiket` geçen manuel batch çıktılar yanlışlıkla `Rulo Batch` gibi sınıflanabiliyordu.
- Varsayılan galeri, kontrol gereken eski dosyaların sayısını fazla öne çıkarabiliyordu.

## Yapılan Düzeltmeler

### Temiz Müşteri Demo Seed

`scripts/seed_clean_customer_demo_data.py` eklendi.

- Gerçek render zinciriyle üç temiz müşteri işi üretir.
- `render_manual_label`, `preflight_manual_label`, `validate_manual_output` ve `add_to_print_queue` hattını kullanır.
- Seed kayıtlarını `demo_seed = clean_customer_demo_v1` ile işaretler.
- Tekrar çalışınca sadece kendi önceki seed queue/history kayıtlarını değiştirir; kullanıcı kayıtlarına dokunmaz.
- PDF/PNG çıktıları final render hattından oluşur, mock/stale dosya final akışa karışmaz.

Seed müşteri işleri:

- Elif Kaan, 01 A Gold Rulo Etiket, 15.05.2026, Nişan Hatırası, 10 adet
- Burcu Baran, 03 A Gold, 20.06.2026, Söz Hatırası, 5 adet
- Sedef Sefer, 01 A Gold Rulo Etiket, 01.07.2026, Tepsi Üzeri, 2 adet

### Temiz Demo Flow Doğrulaması

`scripts/verify_clean_customer_demo_flow.py` eklendi.

Doğruladıkları:

- Etiket Çıktıları varsayılan galeri temiz müşteri kartlarını gösteriyor.
- Teknik/test çıktılar müşteri galerisine karışmıyor.
- Sağ preview paneli seçili müşteri çıktısını gösteriyor.
- Yazdırma Sırası varsayılan görünümde 3 temiz müşteri işi gösteriyor.
- Queue özetinde `Kontrol Gerekli = 0`.
- Yazdır butonu güvenli onay modalı açıyor.
- Direct/silent print çağrısı yok.
- Kırık image yok.

### UI Sınıflandırma Güvenliği

`src/webui/app.js` içinde teknik/test arşiv sınıflandırması genişletildi.

- `workshop_operation_test`, `workshop operation test`, `atölye operasyon test`, `atolye operasyon test` ve `/print/model_` üreten test kayıtları müşteri görünümünden ayrıldı.
- Varsayılan Etiket Çıktıları KPI'ları doğrulanmış/gösterilebilir müşteri çıktılarını temel alacak şekilde temizlendi.
- `Rulo Etiket` model adından dolayı manuel batch dosyanın `Rulo Batch` sanılması engellendi.
- Roll sınıflandırması artık yalnızca `roll_batch`, `rulo_batch`, `rulo-batch` veya açık `rulo batch` patternleriyle yapılır.

### Test Kapsamı

`tests/test_clean_customer_demo_seed.py` eklendi.

- Clean demo işlerinin QA/test/debug/report adı taşımadığını doğrular.
- Dosya adından temiz metadata fallback çıkarımını doğrular.
- Seed kayıtlarının sadece kendi demo kayıtlarını değiştirecek şekilde filtrelenmesini test eder.

## Komut Sonuçları

- `node --check src\webui\app.js`: PASSED
- `.venv\Scripts\python.exe -m pytest -q`: PASSED, 133 passed
- `.venv\Scripts\python.exe scripts\verify_outputs_gallery_flow.py`: PASSED
- `.venv\Scripts\python.exe scripts\verify_print_queue_flow.py`: PASSED
- `.venv\Scripts\python.exe scripts\verify_clean_customer_demo_flow.py`: PASSED
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: completed

## Screenshot Kanıtları

Temiz müşteri demo flow:

- `output/2026-05-14/clean_customer_demo_flow/outputs_customer_gallery.png`
- `output/2026-05-14/clean_customer_demo_flow/outputs_selected_customer.png`
- `output/2026-05-14/clean_customer_demo_flow/queue_customer_ready.png`
- `output/2026-05-14/clean_customer_demo_flow/queue_selected_customer.png`
- `output/2026-05-14/clean_customer_demo_flow/queue_customer_print_modal.png`

Ek regression screenshotları:

- `output/2026-05-14/outputs_gallery_flow/outputs_gallery.png`
- `output/2026-05-14/outputs_gallery_flow/outputs_review_filter.png`
- `output/2026-05-14/outputs_gallery_flow/outputs_selected_preview.png`
- `output/2026-05-14/outputs_gallery_flow/outputs_print_modal.png`
- `output/2026-05-14/outputs_gallery_flow/outputs_technical_archive.png`
- `output/2026-05-14/print_queue_flow/print_queue_general.png`
- `output/2026-05-14/print_queue_flow/print_queue_selected_detail.png`
- `output/2026-05-14/print_queue_flow/print_queue_print_modal.png`

## Güvenlik Teyidi

- CorelDRAW açılmadı.
- Illustrator açılmadı.
- RDWorks açılmadı.
- Lazer başlatılmadı.
- Direct/silent print tetiklenmedi.
- Kaynak AI/CDR dosyalarına dokunulmadı.
- Queue yanlış/stale dosya yazdırma akışına alınmadı.

## Kalan Riskler

- Eski QA/test output dosyaları disk üzerinde duruyor; varsayılan müşteri ekranından saklanıyor. Tam fiziksel arşiv/temizlik için ayrıca güvenli arşivleme işi planlanabilir.
- Clean demo seed tekrar çalıştığında yeni PDF/PNG dosya suffixleri oluşur. Bu kullanıcı verisini koruyan güvenli davranış, fakat ileride sadece seed tarafından üretilmiş eski orphan dosyaları arşivleyen yardımcı script eklenebilir.
- Demo seed preflight sonucu bazı işlerde `WARNING` verebiliyor; output validation `OK` ve görsel çıktılar geçerli. Uyarılar font auto-fit kaynaklıdır.

## Sonraki Önerilen İş

Sıradaki P1 iş: Toplu Etiket 100 satır galeri final doğrulaması.

Amaç:

- 100 satırlık Excel fixture ile galeri/özet senkronunu tekrar test etmek.
- Hatalı model satırının üretime alınmadığını doğrulamak.
- Kaydet/Vazgeç/Sil/Önceki/Sonraki modal akışını gerçek click ile kilitlemek.
- Batch manifest ve queue metadata bağlantısını yeniden doğrulamak.
