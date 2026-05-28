# Clean Demo Data and Customer-Facing Defaults Report

Tarih: 2026-05-13

## Kısa Sonuç

İlk UI/UX uygulama dilimi tamamlandı. Eski/test/problemli queue ve output kayıtları silinmeden normal müşteri görünümünden ayrıldı; Etiket Çıktıları ve Yazdırma Sırası sayfalarında kullanıcıya daha dürüst, temiz ve güvenli varsayılan state gösteriliyor.

Bu çalışma PDF/PNG render zincirini, output validation mantığını ve queue güvenliğini değiştirmedi.

## Neden Yapıldı?

UI/UX planında en yakın P1 risk şuydu:

- Yazdırma Sırası ve Etiket Çıktıları sayfalarında eski/test/problemli kayıtlar varsayılan ekranda öne çıkıyor.
- Bu durum final ürünü bozuk gibi gösteriyor.
- Bazı bulk output dosyalarında model/isim/tarih/not/adet metadata eksik görünüyor.
- Queue’da doğrulanmamış veya dosyası eksik işler, kullanıcı açısından “yazdırılabilir iş” gibi algılanabiliyor.

## Yapılan Değişiklikler

### Etiket Çıktıları

- Müşteri çıktıları artık varsayılan görünümde daha iyi metadata ve daha güvenilir önizleme sinyaline göre sıralanıyor.
- Bulk gallery manifest kayıtları backend tarafında okunuyor.
- `order_BULK-N` gibi batch çıktılar için model, isim, tarih, not ve adet bilgisi manifest satırlarından geri dolduruluyor.
- Teknik/test dosyalarının müşteri galerisi görünümünü kirletmemesi için mevcut teknik arşiv ayrımı korunuyor.

### Yazdırma Sırası

- Varsayılan queue görünümünde `Kontrol gerekli`, `Dosya yok` veya review/missing durumundaki işler normal müşteri yazdırma listesine alınmıyor.
- Bu işler silinmedi; “Kontrol Gerekenleri Göster” ile erişilebilir kaldı.
- Eğer yazdırmaya hazır müşteri işi yoksa ekran artık bunu açıkça söylüyor:
  - “Yazdırmaya hazır müşteri işi yok.”
  - “Kontrol gerekli durumundaki işler doğrulanmadan yazdırma akışına alınmaz.”
- Sıradaki iş kartı artık sadece gerçekten bekleyen/güvenli queue item varsa doluyor.
- Pending sayısı review item’ları bekleyen gibi saymıyor.

### Ana Sayfa

- Son işler ve son çıktı kartlarında test/demo/QA ağırlıklı kayıtların normal müşteri akışını bozması azaltıldı.
- Son müşteri output seçimi, sadece tarihe değil müşteri gösterim kalitesine göre de sıralanıyor.

### Güvenlik

- Direct print kapalı kaldı.
- Silent print eklenmedi.
- CorelDRAW, Illustrator, RDWorks, lazer veya yazıcı otomasyonu tetiklenmedi.
- Problemli/stale queue item’ları varsayılan yazdırma akışından uzak tutuldu.

## Değişen Dosyalar

- `src/webui/app.js`
- `src/webui_backend/label_api.py`
- `CODEX_CURRENT_PRIORITY.md`
- `NEXT_AUTONOMOUS_TASKS.md`
- `CLEAN_DEMO_DATA_AND_CUSTOMER_DEFAULTS_REPORT.md`

## Test Sonuçları

Çalıştırılan komutlar:

- `node --check src\webui\app.js` - PASSED
- `.venv\Scripts\python.exe -m pytest -q` - PASSED, 128 passed
- `.venv\Scripts\python.exe scripts\verify_outputs_gallery_flow.py` - PASSED
- `.venv\Scripts\python.exe scripts\verify_print_queue_flow.py` - PASSED
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` - PASSED
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` - PASSED
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` - PASSED
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py` - PASSED

Öne çıkan doğrulama:

- Outputs gallery seçili preview artık bulk output için `01 A Gold Rulo Etiket`, `Ayşe & Mehmet QA`, `15.05.2026`, `Nişan Hatırası`, `Adet 10` bilgisini gösterebiliyor.
- Queue default görünüm doğrulanmamış işleri yazdırılabilir müşteri işi gibi göstermiyor.
- Queue test scripti direct/silent print davranışı olmadığını doğruluyor.

## Screenshot Kanıtları

- `output/2026-05-13/ui_screenshots/etiket_ciktilari.png`
- `output/2026-05-13/ui_screenshots/yazdirma_sirasi.png`
- `output/2026-05-13/outputs_gallery_flow/outputs_selected_preview.png`
- `output/2026-05-13/print_queue_flow/print_queue_general.png`
- `output/2026-05-13/quality_gate/`

Not: En güncel varsayılan Yazdırma Sırası kanıtı `output/2026-05-13/ui_screenshots/yazdirma_sirasi.png` dosyasıdır. `print_queue_flow` scripti test içinde Test/QA arşivini de açtığı için bazı test screenshotlarında arşiv kayıtları görünebilir.

## Kalan Riskler

- Queue içinde hâlâ eski Test/QA ve kontrol gerekli kayıtlar var; bunlar silinmedi, varsayılan müşteri görünümünden ayrıldı.
- Bazı eski batch manifestlerinde ölçü bilgisi eksikse Etiket Çıktıları panelinde ölçü `-` kalabilir.
- Bu dilim görsel polish değil; asıl sonraki iş Toplu Etiket galeri viewport ve uzun isim düzenidir.

## Sonraki Önerilen İş

Sıradaki en doğru adım:

1. Toplu Etiket galeri viewport ve uzun isim polish.
2. Studio sticky output ve compact inspector polish.
3. Yeni Model Wizard gerçek adım akışı doğrulaması.

