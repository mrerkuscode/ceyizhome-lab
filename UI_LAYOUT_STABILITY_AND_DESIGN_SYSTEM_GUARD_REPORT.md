# UI Layout Stability and Design System Guard Report

Tarih: 2026-05-16

## Kısa Karar

Etiket Studio'da daha önce görülen mouse hareketinde yanıp sönme, sağ dock scroll sırasında içerik kaybolması, native select açıldığında layout zıplaması ve sidebar hover sonrası açık kalma sınıfı hatalar için global CSS stabilite katmanı uygulandı.

Bu turda davranış mimarisi, PDF/PNG render, queue, output validation, RDWorks veya direct print akışı değiştirilmedi. Düzeltme `src/webui/styles.css` içinde UI yoğunluğu ve stabilite guard katmanı olarak yapıldı.

## Yapılanlar

- Hover sırasında transform kullanan kart ve satır efektleri azaltıldı.
- Blur/backdrop-filter kullanılan sticky ve modal yüzeyleri sadeleştirildi.
- Studio property bar, canvas panel, sağ dock ve status bar için sabit scroll sınırları tanımlandı.
- Sidebar hover kapanma davranışını bozabilecek layout genişleme etkileri sınırlandı.
- Desktop side panel davranışı 1180px altına kadar korunacak şekilde düzenlendi.
- Native select açılıp kapandığında üst barın taşmaması için Studio kontrol ölçüleri küçültüldü.
- Queue satırlarında aksiyon kolonunun kesilmemesi için grid alanları yeniden dengelendi.

## Kanıt

- `output/2026-05-16/studio_layout_stability/VERIFY_STUDIO_LAYOUT_STABILITY_RESULT.json`: PASSED
- `output/2026-05-16/report_verification/COREL_EDITOR_INTERACTION_VERIFICATION_RESULT.json`: PASSED
- `output/2026-05-16/ui_screenshots/manuel_etiket.png`
- `output/2026-05-16/ui_screenshots/yazdirma_sirasi.png`
- `output/2026-05-16/ui_screenshots/etiket_ciktilari.png`

## Kalan Risk

P0/P1 stabilite hatası testlerde tekrar etmedi. Kalan risk P2 seviyesinde görsel mikro-polish: bazı sayfalarda üst özet alanları daha da kısaltılabilir.

