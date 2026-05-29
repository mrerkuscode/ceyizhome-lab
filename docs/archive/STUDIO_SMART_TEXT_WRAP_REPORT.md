# STUDIO SMART TEXT WRAP REPORT

Tarih: 2026-05-08

## Görev

Etiket Studio’daki “Satıra Böl” aksiyonunu daha akıllı hale getirmek.

## Mevcut Sorun

Önceki “Satıra Böl” davranışı metni yaklaşık orta noktadan ayırıyordu. Bu bazı uzun isim/not metinlerinde iki satırın görsel dengesi iyi olmadığı için kullanıcıya ek düzeltme yükü çıkarabiliyordu.

## Kök Neden

Metin kırılımı kutu genişliği ve gerçek font ölçümü hesaba katılmadan yalnızca karakter orta noktasına göre yapılıyordu.

## Değiştirilen Dosyalar

- `src/webui/app.js`
- `tests/test_mvp_safety.py`

## Yapılan Düzeltmeler

- `bestTwoLineSplitForField()` eklendi.
- Satıra bölme artık:
  - Metindeki tüm boşluk noktalarını aday olarak inceler.
  - Her aday için iki satırın gerçek canvas text ölçümünü hesaplar.
  - Kutu genişliğini dikkate alır.
  - En dengeli ve taşma riski en düşük iki satır kırılımını seçer.
- Mevcut `splitSelectedFieldTextLine()` bu yeni algoritmayı kullanacak şekilde güncellendi.

## UI/UX Etkisi

Kullanıcı uzun metinlerde daha dengeli satır kırılımı alır. Bu, özellikle isim ve not alanlarında manuel düzeltme ihtiyacını azaltır.

## Render / Output / Queue Etkisi

PDF/PNG render, output validation ve queue zincirine dokunulmadı. Metin değeri canvas state içinde güncellenir; mevcut payload zinciri son state’i taşımaya devam eder.

## Güvenlik Etkisi

Harici uygulama, yazıcı, lazer veya direct print çağrısı eklenmedi. Kaynak AI/CDR dosyalarına dokunulmadı.

## Eklenen / Güncellenen Testler

- `tests/test_mvp_safety.py` içine `bestTwoLineSplitForField` ve `overflowPenalty` regression kilidi eklendi.
- Studio browser interaction gate tekrar çalıştırıldı; drag/resize/zoom/payload geometry davranışı bozulmadı.

## Çalıştırılan Komutlar

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: 110 passed.
- `.venv\Scripts\python.exe scripts\studio_canvas_interaction_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: geçti.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`: geçti.

## Screenshot Yolları

- `output/2026-05-08/studio_interaction`
- `output/2026-05-08/ui_screenshots`
- `output/2026-05-08/quality_gate`

## Kalan Riskler

- Algoritma iki satır kırılımına odaklıdır. Çok uzun notlarda üç veya daha fazla satıra otomatik bölme ileride P3 olarak eklenebilir.

## P0/P1 Durumu

Kalan P0/P1 hata görülmedi. Studio interaction gate, kalite kapısı ve final acceptance geçti.
