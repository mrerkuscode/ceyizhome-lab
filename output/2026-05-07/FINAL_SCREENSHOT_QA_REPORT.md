# FINAL_SCREENSHOT_QA_REPORT

Tarih: 2026-05-07 08:31:00
Durum: PASSED

## İncelenen Screenshotlar

- Ana Sayfa: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\ui_screenshots\ana_sayfa.png`
- Etiket Modelleri: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\ui_screenshots\etiket_modelleri.png`
- Yeni Model Ekle modal: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\ui_screenshots\yeni_model_ekle_modal.png`
- Etiket Modelleri Önizle modal: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\ui_screenshots\etiket_modelleri_onizle_modal.png`
- Etiket Studio canlı canvas: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\quality_gate\quality_gate_live_canvas.png`
- Etiket Studio Model Seç dropdown: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\quality_gate\quality_gate_model_dropdown.png`
- PDF Önizleme modal: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\quality_gate\quality_gate_pdf_preview_modal.png`
- PNG Önizleme: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\quality_gate\quality_gate_png_preview.png`
- Yazdırma Sırası: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\quality_gate\quality_gate_print_queue.png`
- Toplu Etiket: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\ui_screenshots\toplu_etiket.png`
- Etiket Çıktıları: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\ui_screenshots\etiket_ciktilari.png`
- Ayarlar: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\ui_screenshots\ayarlar.png`
- Raporlar: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\ui_screenshots\raporlar.png`

## Görsel QA Sonucu

- Etiket Modelleri normal görünüm temiz.
- Yeni Model Ekle modalı teknik editör yerine sade kullanıcı akışı gösteriyor.
- Önizleme modalı yakalandı.
- Etiket Studio canlı canvas, Model Seç dropdown, PDF Önizleme ve PNG Önizleme yakalandı.
- Yazdırma Sırası doğru son batch PDF ile doğrulandı.
- Etiket Çıktıları müşteri dosyalarını teknik raporlardan ayırıyor.
- Türkçe karakterler raporlarda ve kullanıcı metinlerinde doğru.


## Final Üretim Kanıtı

- Kalite kapısı durumu: `PASSED`
- Çoklu model kabul testi: `PASSED`
- Model: `01 A Gold Rulo Etiket`
- Template: `C:\Users\Pc\Documents\New project\production-bot\templates\designs\01_a_gold.json`
- İsim: `Ayşe & Mehmet QA`
- Tarih: `15.05.26`
- Not: `Nişan hatırası`
- Background: `C:\Users\Pc\Documents\New project\production-bot\assets\label_backgrounds\normalized\01_a_gold_preview_50x30.png`
- Final PNG: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\print\manual\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_9.png`
- Final PDF: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\print\manual\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_9.pdf`
- Queue PDF: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\print\manual\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_9.pdf`
- Queue relative path: `output/2026-05-07/print/manual/2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_9.pdf`
- PDF page preview: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\quality_gate\quality_gate_pdf_page.png`

## Output Validation

- PNG: `PASSED`, boyut `138866`, ölçü `591 x 354`, renkli piksel `678`, yazı pikselleri `{'label_text': 57, 'date_text': 15, 'note_text': 63}`
- PDF page: `PASSED`, boyut `302158`, ölçü `900 x 539`, renkli piksel `582`, yazı pikselleri `{'label_text': 37, 'date_text': 7, 'note_text': 52}`
- Gerçek Önizleme: `PASSED`, boyut `138866`, ölçü `591 x 354`, renkli piksel `678`, yazı pikselleri `{'label_text': 57, 'date_text': 15, 'note_text': 63}`
- Taze dosya kontrolü: `PASSED`

## Çoklu Model Kabul Senaryoları

- A - Hazır model: PASSED · 01 A Gold Rulo Etiket
- B - İkinci mevcut model: PASSED · yesıl
- C - Yeni model: PASSED · Final QA Kabul Modeli
