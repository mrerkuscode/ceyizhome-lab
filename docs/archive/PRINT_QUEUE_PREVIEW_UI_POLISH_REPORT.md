# Print Queue Preview UI Polish Report

## Görev

Yazdırma Sırası ekranında önizleme görseli çok büyük ve kırpılmış görünüyordu. Kullanıcı işi, model bilgisini ve aksiyonları aynı anda rahat okuyamıyordu.

## Kök Neden

- Queue satırı eski tablo düzeninde 7 kolona bölünmüştü.
- `.queue-card { align-items: stretch; }` nedeniyle thumbnail hücresi satır yüksekliğine esniyordu.
- `.queue-thumb img { object-fit: cover; }` görseli kutuya doldururken etiketin kenarlarını kırpıyordu.
- Güvenlik notu ve aksiyonlar satır yüksekliğini büyütünce preview de büyüyüp belirsiz hale geliyordu.

## Değiştirilen Dosyalar

- `src/webui/styles.css`
- `tests/test_mvp_safety.py`

## Yapılan Düzeltmeler

- Yazdırma Sırası satırları kompakt üretim kartı görünümüne çekildi.
- Preview kutusu sabit `118 x 78 px` hale getirildi.
- Görsel `object-fit: contain` ile gösteriliyor; artık kırpılmadan bütün etiket görünüyor.
- Satır stretch davranışı kapatıldı, tüm elemanlar merkez hizaya alındı.
- Model adı, dosya adı, isim/tarih/not/ölçü/adet chipleri daha dengeli dizildi.
- Güvenlik notu ayrı yeşil bilgi bandına dönüştürüldü.
- Aksiyon butonları sağda/toparlanan grid içinde tutuldu.
- 1360 px ve 900 px altı responsive kırılımlar eklendi.

## Render / Output / Queue Etkisi

- PDF/PNG render zincirine dokunulmadı.
- Output validation sistemine dokunulmadı.
- Queue veri modeli ve backend işlemleri değiştirilmedi.
- Değişiklik yalnızca Yazdırma Sırası görsel düzenindedir.

## Testler

- `node --check src\webui\app.js` -> Passed
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py` -> 112 passed
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` -> Passed

## Screenshot

- `output\2026-05-11\ui_screenshots\yazdirma_sirasi.png`

## Sonuç

Yazdırma Sırası ekranında görsel artık aşırı büyük/kırpılmış görünmüyor. Etiket preview okunabilir, iş bilgileri daha net, butonlar daha dengeli ve kullanıcı PDF’i kontrol edip manuel yazdırma akışını daha rahat takip edebilir.

## Kalan Risk

- Çok uzun dosya adları tek satırda kısaltılır; tam yol teknik detay olarak normal kullanıcıya gösterilmez.
