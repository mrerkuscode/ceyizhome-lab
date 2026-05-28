# BULK ROLL WASTE PERCENT REPORT

Tarih: 2026-05-08

## Görev

Toplu Etiket rulo yerleşim önizlemesinde fire bilgisini sadece boş genişlik olarak değil, kullanıcı için daha hızlı anlaşılır yüzde oranıyla da göstermek.

## Değiştirilen Dosyalar

- `src/webui/app.js`
- `tests/test_mvp_safety.py`

## Yapılan Düzeltmeler

- Rulo yerleşim simülasyonuna “Ortalama fire” yüzdesi eklendi.
- Fire özeti tam satır ve son satır için hem mm hem yüzde değerini gösteriyor.
- Hesaplama gerçek etiket ölçüsü, rulo genişliği, aralık, satır kapasitesi ve toplam adetten besleniyor.
- Mock veya stale veri eklenmedi.

## UI/UX Etkisi

Toplu üretim öncesinde kullanıcı artık rulo yerleşiminde yaklaşık şerit uzunluğunu, satır kırılımını, boş genişliği ve fire yüzdesini aynı kartta görebiliyor.

## Render/Output/Queue Etkisi

Render, PDF/PNG üretimi ve queue zincirine dokunulmadı. Değişiklik yalnızca Toplu Etiket rulo önizleme UI hesaplamasını etkiler.

## Testler

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: 110 passed.

## P0/P1 Durumu

Kalan P0/P1 hata görülmedi.
