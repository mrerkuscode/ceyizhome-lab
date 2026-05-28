# AUTONOMOUS SCREENSHOT QA REPORT

Tarih: 2026-05-11

## Screenshot Klasörleri

- Ana web UI screenshotları: `output\2026-05-11\ui_screenshots`
- Quality gate screenshotları: `output\2026-05-11\quality_gate`
- Etiket Modelleri click gate screenshotları: `output\2026-05-11\label_models_click_gate`
- Etiket Studio interaction screenshotları: `output\2026-05-11\studio_interaction`

## İncelenen Kritik Screenshotlar

- `output\2026-05-11\ui_screenshots\ana_sayfa.png`
- `output\2026-05-11\ui_screenshots\etiket_modelleri.png`
- `output\2026-05-11\ui_screenshots\manuel_etiket.png`
- `output\2026-05-11\ui_screenshots\toplu_etiket.png`
- `output\2026-05-11\ui_screenshots\yazdirma_sirasi.png`
- `output\2026-05-11\ui_screenshots\etiket_ciktilari.png`
- `output\2026-05-11\ui_screenshots\ayarlar.png`
- `output\2026-05-11\quality_gate\quality_gate_live_canvas.png`
- `output\2026-05-11\quality_gate\quality_gate_pdf_preview_modal.png`
- `output\2026-05-11\quality_gate\quality_gate_png_preview.png`
- `output\2026-05-11\quality_gate\quality_gate_print_queue.png`

## Görsel QA Sonucu

- Etiket Studio canvas ana odak olarak kalıyor; selection border ve handle’lar görünür.
- Yazdırma Sırası preview kartları artık büyük ve taşan görseller yerine okunur küçük etiket thumbnail’ları gösteriyor.
- Etiket Çıktıları ekranında filtreler, çıktı grupları, güvenli arşiv önerisi ve müşteri/teknik çıktı ayrımı korunuyor.
- Toplu Etiket ekranında satır önizleme, kolon eşleştirme ve rulo yerleşim alanları görünür.
- Ana Sayfa ve Etiket Modelleri macOS tarzı sidebar/kart dilini koruyor.
- Quality gate screenshotları canlı canvas, PDF preview, PNG preview ve queue zincirini gösteriyor.

## Yeni Bu Turda Doğrulanan Görseller

- Arşiv/geri alma geçmişi ve toplu arşiv kontrolü Etiket Çıktıları akışına eklendi.
- Studio kısayol yardımı inspector içinde açılabilir durumda.
- Üretim Geçmişi tarih filtresi ve analitik barları UI seviyesinde yerleştirildi.

## P0/P1 Durumu

Screenshot QA’da kalan P0/P1 görsel veya akış hatası görülmedi.
