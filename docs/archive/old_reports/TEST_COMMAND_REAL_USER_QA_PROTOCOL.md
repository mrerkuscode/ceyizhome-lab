# Test Komutu Gerçek Kullanıcı QA Protokolü

Kullanıcı yalnızca `test` yazdığında bu komut basit unit test anlamına gelmez.

`test` komutunun anlamı:

> Projeyi gerçek kullanıcı gibi test et. Butonlara tıkla, sayfaları gez, Etiket Studio’da yazıyı taşı, resize yap, PDF/PNG oluştur, queue’ya ekle, screenshot al, hata varsa onay beklemeden düzelt, tekrar test et.

## Zorunlu Okuma

`test` komutu başladığında önce şu dosyalar okunur:

1. `START_HERE_FOR_CODEX.md`
2. `PROJECT_MASTER_CONTEXT.md`
3. `CODEX_LEAD_DEVELOPER_MANUAL.md`
4. `REAL_USER_TESTING_STANDARD.md`
5. `HUMAN_QA_PROTOCOL.md`
6. `INTERACTION_TESTING_GUIDE.md`
7. `BUTTON_CLICK_TESTING_STANDARD.md`
8. `OUTPUT_VALIDATION_STANDARD.md`
9. `VISUAL_SCREENSHOT_QA_GUIDE.md`
10. `QA_ACCEPTANCE_CHECKLIST.md`
11. `CODEX_CURRENT_PRIORITY.md`

## Zorunlu Akışlar

Ana sayfalar:

- Ana Sayfa
- Etiket Modelleri
- Etiket Studio
- Toplu Etiket
- Yazdırma Sırası
- Etiket Çıktıları
- Ayarlar

Etiket Modelleri gerçek click:

- Yenile
- Tasarım Görseli Yükle
- Yeni Model Ekle
- Kart seçimi
- Etiket Hazırla
- Studio’da Düzenle
- Önizle
- Görsel Bağla
- Filtreler
- Teknik Mod

Etiket Studio gerçek interaction:

- İsim/Tarih/Not mouse drag
- Corner resize
- Side resize
- Zoom %100/%150/%200
- Arrow, Shift+Arrow, Alt+Arrow
- Payload geometry doğrulaması

Output:

- PDF/PNG oluştur
- PDF preview aç
- PNG preview aç
- Yazdırma sırasına ekle
- Queue son doğrulanmış dosyayı alıyor mu kontrol et

## Runner

Bu protokol için yardımcı komut:

```powershell
.venv\Scripts\python.exe scripts\run_test_command_real_user_qa.py
```

Runner mevcut kalite kapılarını çalıştırır, logları saklar ve `TEST_COMMAND_REAL_USER_QA_REPORT.md` üretir.

## Hata Kuralı

Runner veya manuel gözlem P0/P1 hata bulursa:

- “Tamamlandı” denmez.
- Hata düzeltilir.
- Runner tekrar çalıştırılır.
- Screenshotlar yenilenir.
