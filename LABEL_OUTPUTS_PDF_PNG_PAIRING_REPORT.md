# Etiket Çıktıları PDF/PNG Eşleşme Raporu

## Görev

Etiket Çıktıları ekranında müşteri çıktısı kartlarını daha üretim odaklı hale getirmek ve aynı üretim geçmişinden gelen PDF/PNG dosyalarını kullanıcıya daha net göstermek.

## Mevcut Sorun

PDF ve PNG dosyaları listede ayrı kartlar olarak görünüyordu. Bu teknik olarak çalışıyordu, ancak normal kullanıcı bir PNG’nin hangi PDF’e ait olduğunu veya bir PDF’in karşılık gelen PNG önizlemesini hızlıca anlayamıyordu.

## Kök Neden

Kart render mantığı `productionHistory` verisini model/isim/ölçü/adet metası için kullanıyordu, ancak aynı geçmiş satırındaki `pdf_path`, `batch_pdf_path` ve `png_path` ilişkisini kart aksiyonlarına yansıtmıyordu.

## Değiştirilen Dosyalar

- `src/webui/app.js`
- `src/webui/styles.css`
- `tests/test_mvp_safety.py`
- `CODEX_CURRENT_PRIORITY.md`

## Yapılan Düzeltmeler

- `outputItemForPath` helper’ı eklendi.
- `outputPairForPath` helper’ı eklendi.
- Etiket Çıktıları kartlarında:
  - `PDF eşleşti`
  - `PNG eşleşti`
  - `Üretim geçmişi bağlı`
  - `Eşleşme yok`
  bilgileri gösteriliyor.
- PDF kartlarında eşleşen PNG varsa `PNG Önizle` aksiyonu eklendi.
- PNG kartlarında eşleşen PDF varsa `PDF’i Gör` ve `PDF’i Sıraya Ekle` aksiyonları eklendi.
- Sağdaki çıktı önizleme panelinde:
  - PNG seçiliyken eşleşen PDF görülebiliyor ve sıraya eklenebiliyor.
  - PDF seçiliyken eşleşen PNG önizlenebiliyor.
- Eşleşme sadece gerçek `productionHistory` / `labelOutputs` verisinden hesaplanıyor. Mock/stale veri eklenmedi.

## UI/UX Etkisi

Kullanıcı artık çıktı listesinden:

- Hangi PDF ve PNG’nin aynı üretime ait olduğunu,
- Hangi PDF’in queue’ya eklenebilir olduğunu,
- Hangi PNG’nin sadece önizleme olduğunu,
- Eşleşen PDF/PNG’ye hangi aksiyonla geçeceğini

daha net görüyor.

## Render / Output / Queue Etkisi

Render motoruna, preflight/output validation zincirine veya queue backend mantığına dokunulmadı.

Queue güvenliği korundu:

- Queue’ya yine sadece PDF ekleniyor.
- PNG kartından queue’ya ekleme yapılırken eşleşen PDF yolu kullanılıyor.
- Eşleşme yoksa PNG için kullanıcıya sade uyarı veriliyor.

## Güvenlik Etkisi

- Direct print açılmadı.
- Yazıcı otomatik çalıştırılmadı.
- CorelDRAW, Illustrator, RDWorks veya lazer çağrılmadı.
- Kaynak AI/CDR dosyalarına dokunulmadı.

## Eklenen / Güncellenen Testler

`tests/test_mvp_safety.py` içine şu regression kontrolleri eklendi:

- `outputPairForPath` helper’ı var.
- PDF/PNG eşleşme metinleri UI kaynağında var.
- Eşleşen PDF/PNG aksiyonları var.
- `.output-pair-meta` ve `.output-preview-actions` stilleri var.

## Çalıştırılan Komutlar

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: `110 passed`.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\label_models_real_click_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\studio_canvas_interaction_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: geçti.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`: geçti.

## Screenshot Yolları

- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-08\ui_screenshots\etiket_ciktilari.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-08\quality_gate`

## Kalan Riskler

Eski üretim dosyalarında üretim geçmişi ilişkisi yoksa kart `Eşleşme yok` gösterebilir. Bu beklenen güvenli davranıştır; sistem ilişkiyi tahmin etmek için mock veya stale veri üretmez.

## P0/P1 Durumu

Bu değişiklik sonrası P0/P1 hata görülmedi. Render, queue, model click ve Studio interaction kalite kapıları tekrar geçti.
