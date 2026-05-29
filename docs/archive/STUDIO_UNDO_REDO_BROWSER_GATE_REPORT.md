# Etiket Studio Undo / Redo Browser Gate Raporu

## Görev

Etiket Studio’da zaten var olan Undo / Redo davranışını sadece buton/fonksiyon varlığıyla değil, gerçek browser state testiyle kilitlemek.

## Kök Neden

Önceki testler `manualUndoButton`, `manualRedoButton`, `undoManualEdit` ve `redoManualEdit` varlığını kontrol ediyordu. Bu yararlıydı ama kullanıcı açısından kritik olan şey, gerçek drag sonrası state’in geri alınıp tekrar ileri alınmasıdır.

## Yapılan Düzeltme

`scripts/studio_canvas_interaction_gate.py` içine yeni kontrol eklendi:

1. Etiket Studio açılır.
2. İsim alanı gerçek pointer event ile taşınır.
3. `undoManualEdit()` çağrılır.
4. `x_mm`, `y_mm`, `width_mm`, `height_mm` eski state ile karşılaştırılır.
5. `redoManualEdit()` çağrılır.
6. Alan tekrar drag sonrası state ile karşılaştırılır.
7. Kontrol `undo_redo_drag_state` olarak raporlanır.

## Değiştirilen Dosyalar

- `scripts/studio_canvas_interaction_gate.py`
- `CODEX_CURRENT_PRIORITY.md`
- `STUDIO_CANVAS_GUIDES_SAFE_AREA_REPORT.md`

## UI/UX Etkisi

Kullanıcı yazıyı yanlışlıkla taşıdığında Geri Al / İleri Al davranışının gerçek field geometry state’i üzerinde çalıştığı artık testle kilitli.

## Render / Output / Queue Etkisi

Render/output/queue koduna dokunulmadı. Ancak `manualPayload` zaten güncel geometry state’i kullandığı için undo/redo sonrası çıktının da güncel state’i kullanması korunuyor.

## Test Sonuçları

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: `110 passed`.
- `.venv\Scripts\python.exe scripts\studio_canvas_interaction_gate.py`: PASSED.

Interaction gate içindeki yeni kontrol:

- `undo_redo_drag_state`: PASSED.

## Güvenlik

- Direct print açılmadı.
- Yazıcı/lazer/CorelDRAW/Illustrator/RDWorks tetiklenmedi.
- Kaynak AI/CDR dosyalarına dokunulmadı.

## Kalan Risk

Undo/redo artık drag için browser gate ile doğrulandı. Sonraki güvenli geliştirme olarak font, renk, hizalama ve ölçü override işlemleri için ayrı state kontrolleri eklenebilir.

## P0/P1 Durumu

P0/P1 hata görülmedi.
