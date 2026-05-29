# STUDIO MULTI LINE TEXT FIT REPORT

Tarih: 2026-05-08

## Görev

Etiket Studio yazı sığdırma akışını sadece iki satıra bölme ile sınırlı bırakmadan, uzun metinlerde kutu genişliği ve yüksekliğine göre daha dengeli çok satırlı kırılım önerecek hale getirmek.

## Değiştirilen Dosyalar

- `src/webui/app.js`
- `tests/test_mvp_safety.py`

## Yapılan Düzeltmeler

- `bestMultiLineSplitForField` eklendi.
- Uzun metinler için 2, 3 ve 4 satırlı aday kırılımlar ölçülüyor.
- Her aday gerçek canvas text ölçümüyle değerlendirilip genişlik taşması, yükseklik taşması ve satır dengesi skorlanıyor.
- Seçili alan paneline “Çok Satıra Böl” butonu eklendi.
- Çıktı Kontrolü içindeki yazı sığdırma önerilerine “Çok Satıra Böl” aksiyonu eklendi.
- Aksiyon undo stack ile uyumlu çalışıyor ve canvas/payload state’ini güncelliyor.

## UI/UX Etkisi

Kullanıcı uzun isim veya not metninde yalnızca font küçültmek zorunda kalmaz; metni daha okunur şekilde çok satıra bölebilir.

## Render/Output/Queue Etkisi

PDF/PNG render zinciri değiştirilmedi. Metin değeri güncel Studio state’i üzerinden payload’a gittiği için final çıktı yeni satır kırılımını kullanır.

## Testler

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: 110 passed.

## Kalan Riskler

- Çok satırlı kırılım görsel olarak en iyi öneriyi seçer; tam tipografik satır sonu kontrolü P3 gelişmiş metin motoru konusu olarak kalır.

## P0/P1 Durumu

Kalan P0/P1 hata görülmedi.
