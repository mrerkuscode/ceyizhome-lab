# Clean Demo Data and Archive Separation Report

Tarih: 2026-05-14

## Kısa Karar

Temiz müşteri demo akışı doğrulandı. Etiket Çıktıları ve Yazdırma Sırası varsayılan kullanıcı görünümünde doğrulanmış müşteri işleri öne çıkıyor; test/QA ve kontrol gereken eski kayıtlar kullanıcı KPI'larını şişirmiyor.

P0/P1 kalan: Yok.

## Yapılan Düzeltmeler

- `src/webui/app.js` içinde Yazdırma Sırası üst özet kartları varsayılan müşteri görünümündeki filtreli liste ile senkronlandı.
- Eski test/QA veya kontrol gereken kayıtlar varsayılan müşteri kuyruğu dışında tutulduğunda `Toplam İş`, `Toplam Adet`, `Bekleyen`, `Yazdırıldı` ve `Kontrol Gerekli` sayıları da aynı kullanıcı görünümünü yansıtıyor.
- `tests/test_clean_customer_demo_seed.py` içine temiz demo verisinde Türkçe metin/mojibake kontrolü eklendi.

## Temiz Demo Seed

Tek komut:

```powershell
.venv\Scripts\python.exe scripts\verify_clean_customer_demo_flow.py
```

Bu komut önce `scripts/seed_clean_customer_demo_data.py` ile gerçek PDF/PNG ve queue kayıtları üretir, sonra uygulamayı kullanıcı gibi açıp Etiket Çıktıları ve Yazdırma Sırası ekranlarını doğrular.

Demo müşteri işleri:

- Elif Kaan, 01 A Gold Rulo Etiket, 10 adet, Nişan Hatırası
- Burcu Baran, 03 A Gold/yesıl, 5 adet, Söz Hatırası
- Sedef Sefer, 01 A Gold Rulo Etiket, 2 adet, Tepsi Üzeri

Seed sadece `demo_seed = clean_customer_demo_v1` kayıtlarını yeniler. Kullanıcıya ait diğer kayıtları silmez.

## Arşiv Ayrımı

- Etiket Çıktıları varsayılan müşteri galerisi teknik/test çıktıları göstermiyor.
- Yazdırma Sırası varsayılan müşteri listesi test/QA arşiv kayıtlarını ve doğrulanmamış eski kayıtları KPI içinde büyütmüyor.
- Kullanıcı isterse Test/QA Arşivi filtresiyle arşiv kayıtlarını ayrı olarak görebilir.

## Test Sonuçları

```powershell
node --check src\webui\app.js
# PASSED

.venv\Scripts\python.exe -m pytest -q tests\test_clean_customer_demo_seed.py
# 4 passed

.venv\Scripts\python.exe scripts\verify_clean_customer_demo_flow.py
# PASSED

.venv\Scripts\python.exe -m pytest -q
# 135 passed

.venv\Scripts\python.exe scripts\real_production_quality_gate.py
# PASSED

.venv\Scripts\python.exe scripts\final_acceptance_gate.py
# PASSED
```

## Screenshot Kanıtları

- `output/2026-05-14/clean_customer_demo_flow/outputs_customer_gallery.png`
- `output/2026-05-14/clean_customer_demo_flow/outputs_selected_customer.png`
- `output/2026-05-14/clean_customer_demo_flow/queue_customer_ready.png`
- `output/2026-05-14/clean_customer_demo_flow/queue_selected_customer.png`
- `output/2026-05-14/clean_customer_demo_flow/queue_customer_print_modal.png`

## Doğrulanan Kritik Davranışlar

- Etiket Çıktıları müşteri galerisi doğrulanmış müşteri dosyalarını gösterir.
- Teknik/test çıktılar varsayılan müşteri galerisine karışmaz.
- Yazdırma Sırası müşteri görünümünde `Kontrol Gerekli = 0` olduğunda eski arşiv/test kayıtları sayıyı şişirmez.
- Queue seçili iş detayında model, isim, tarih, not, ölçü, adet ve dosya bilgisi görünür.
- Yazdır butonu güvenli onay modalı açar.
- Direct/silent print çağrısı yoktur.
- Kırık görsel yoktur.

## Kalan Riskler

- Eski test/QA kayıtları arşivde durmaya devam ediyor; bu bilinçli tercih. Kullanıcı çıktıları kirletmiyor.
- Temiz demo reset daha sonra release paketinde tek menü aksiyonu veya bakım komutu olarak daha görünür hale getirilebilir.
