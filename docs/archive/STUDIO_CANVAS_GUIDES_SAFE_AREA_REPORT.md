# Etiket Studio Canvas Rehber Çizgileri Raporu

## Görev

Etiket Studio’da kullanıcı yazı alanlarını taşırken merkez çizgisini ve güvenli alanı daha net görsün. Bu iş, drag/resize etkileşimlerini bozmadan yapılmalıdır.

## Mevcut Durum

Studio’da hızlı hizalama, snap altyapısı, undo/redo düğmeleri ve keyboard hareketleri zaten vardı. Canvas üzerinde ise yalnızca küçük metinsel “Merkez çizgisi / güvenli alan” bilgisi görünüyordu; gerçek çizgi ve güvenli alan sınırı yoktu.

## Yapılan Düzeltme

- `fieldOverlayHtml` içine yalnızca Etiket Studio canlı canvas için `canvas-guides` katmanı eklendi.
- Dikey merkez çizgisi eklendi.
- Yatay merkez çizgisi eklendi.
- Güvenli alanı temsil eden kesik çizgili iç çerçeve eklendi.
- Tüm rehber katmanı `pointer-events: none` olarak tasarlandı.

## Değiştirilen Dosyalar

- `src/webui/app.js`
- `src/webui/styles.css`
- `tests/test_mvp_safety.py`
- `CODEX_CURRENT_PRIORITY.md`
- `AUTONOMOUS_REMAINING_ROADMAP.md`

## UI/UX Etkisi

Kullanıcı artık yazıyı taşırken:

- Etiketin gerçek merkezini,
- Yatay/dikey orta ekseni,
- Yazının kalması gereken güvenli alanı

daha sezgisel görebilir.

## Render / Output / Queue Etkisi

Bu değişiklik sadece frontend canlı canvas overlay katmanıdır.

- PDF/PNG render payload değiştirilmedi.
- Backend render motoruna dokunulmadı.
- Queue mantığına dokunulmadı.
- Rehber çizgileri final PDF/PNG çıktısına gitmez.

## Güvenlik Etkisi

- CorelDRAW, Illustrator, RDWorks, yazıcı, lazer tetiklenmedi.
- Direct print açılmadı.
- Kaynak AI/CDR dosyalarına dokunulmadı.

## Testler

Çalıştırılan komutlar:

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: `110 passed`.
- `.venv\Scripts\python.exe scripts\studio_canvas_interaction_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: geçti.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`: geçti.

Ek olarak Studio interaction gate içine undo/redo state testi eklendi ve tekrar çalıştırıldı:

- Drag sonrası `undoManualEdit()` alanı eski `x_mm/y_mm` değerlerine döndürüyor.
- Ardından `redoManualEdit()` alanı drag sonrası yeni `x_mm/y_mm` değerlerine geri getiriyor.
- Bu kontrol `undo_redo_drag_state` adıyla PASSED sonucu verdi.

## Özellikle Doğrulanan Risk

Rehber overlay’in drag/resize eventlerini engelleme riski vardı. Bu yüzden `studio_canvas_interaction_gate.py` yeniden çalıştırıldı:

- Fit drag: PASSED.
- Corner resize: PASSED.
- Side resize: PASSED.
- `%100`, `%150`, `%200` zoom drag: PASSED.
- `%150`, `%200` corner resize: PASSED.
- Payload geometry: PASSED.

## Screenshot Yolları

- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-08\ui_screenshots\manuel_etiket.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-08\studio_interaction`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-08\quality_gate`

## Kalan Riskler

Bu ilk rehber katmanı daima görünür. İleride kullanıcı tercihine bağlı “Rehberleri göster/gizle” toggle’ı eklenebilir.

## P0/P1 Durumu

P0/P1 hata görülmedi. Drag/resize, PDF/PNG kalite kapısı ve final kabul kapısı geçti.
