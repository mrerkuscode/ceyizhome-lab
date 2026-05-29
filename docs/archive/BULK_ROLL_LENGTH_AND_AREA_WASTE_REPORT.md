# BULK ROLL LENGTH AND AREA WASTE REPORT

Tarih: 2026-05-08

## Görev

Toplu Etiket rulo yerleşim önizlemesini toplam rulo uzunluğu ve yaklaşık alan firesiyle daha üretim odaklı hale getirmek.

## Değiştirilen Dosyalar

- `src/webui/app.js`
- `tests/test_mvp_safety.py`

## Yapılan Düzeltmeler

- Rulo önizleme kartına “Toplam uzunluk” bilgisi eklendi.
- Kullanılan alan yüzdesi hesaplandı.
- Yaklaşık alan firesi yüzdesi eklendi.
- Hesaplama gerçek rulo genişliği, toplam şerit uzunluğu, etiket ölçüsü ve toplam adet üzerinden yapılıyor.
- Üretim çıktı, PDF/PNG render veya queue zincirine dokunulmadı.

## Kullanıcı Etkisi

Kullanıcı rulo batch oluşturmadan önce sadece kaç etiket sığdığını değil, yaklaşık ne kadar rulo uzunluğu ve ne kadar fire oluşacağını da görebilir.

## Testler

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: 110 passed.

## P0/P1 Durumu

Kalan P0/P1 hata görülmedi.
