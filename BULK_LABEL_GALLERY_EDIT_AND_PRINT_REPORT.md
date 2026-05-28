# Bulk Label Gallery Edit And Print Report

Tarih: 2026-05-13

## Görev

Toplu Etiket ekranına Excel satırlarını galeri mantığıyla gösteren, satır bazlı hızlı düzenleme sağlayan ve hazır satırları güvenli PDF/PNG/queue üretimine bağlayan akış eklendi.

## Excel Galeri Akışı

- `examples/toplu_etiket_ornek.xlsx` oluşturuldu.
- Desteklenen kolonlar normalize ediliyor: `etiket_no`, `model_no`, `model_kodu`, `tasarım_no`, `isim`, `ad_soyad`, `tarih`, `not`, `adet` ve eşdeğerleri.
- Türkçe karakter, büyük/küçük harf, boşluk ve alt çizgi farkları tolere ediliyor.
- Her Excel satırı `bulk_label_item` yapısına dönüşüyor.

## Model Eşleşmesi

Model eşleşmesi şu alanlara göre yapılır:

- model no
- model adı
- varyant
- template adı
- template dosya adı

Örnek sonuç:

- `01` -> `01 A Gold Rulo Etiket`
- `03` -> `yesıl`
- `99` -> hatalı satır, üretime alınmaz.

## Galeri Kartları

Toplu Etiket ekranında yeni `Toplu Etiket Galerisi` bölümü eklendi.

Her kartta:

- satır no
- küçük etiket preview
- model adı
- isim
- tarih
- not
- adet
- durum badge
- Düzenle / Sil aksiyonları

Filtreler:

- Tümü
- Hazır
- Uyarılı
- Hatalı
- Düzenlenenler
- Silinenler

## Edit Modal

Karttan `Düzenle` açılınca satır bazlı modal gösterilir.

Modal içinde:

- büyük canlı preview
- model seçimi
- isim
- tarih
- not
- adet
- Yazıları Sığdır
- Otomatik Düzenle
- Üretime Hazırla
- Kaydet / Vazgeç / Sil
- Önceki / Sonraki

`Kaydet` sadece seçili item state'ini günceller. `Vazgeç` state'i değiştirmez. `Sil` item'ı üretimden çıkarır.

## Toplu Üretim

`Hazır Olanları Üret` butonu:

- silinen satırları atlar
- hatalı satırları üretime almaz
- her satırı kendi model, isim, tarih, not ve adet değeriyle üretim Excel'ine çevirir
- render zincirini mevcut `src/main.py --render-labels` akışıyla çalıştırır
- queue ekleme mantığını mevcut güvenli queue API üzerinden korur

## Batch Manifest

Her üretim denemesinde manifest yazılır.

Son örnek:

- Manifest: `output/2026-05-13/bulk_gallery/batch_manifest_050253.json`
- Hazır Excel: `output/2026-05-13/bulk_gallery/bulk_gallery_ready_050253.xlsx`
- Toplam satır: 4
- Üretime alınan hazır satır: 3
- Silinen/hatalı atlanan satır: 1
- Toplam adet: 17
- Oluşan PDF: `output/2026-05-13/print/model_03/rendered/roll_batch_03_A_GOLD.pdf`

## Değiştirilen Dosyalar

- `src/webui_backend/bulk_label_api.py`
- `src/desktop/web_main_window.py`
- `src/webui_backend/bridge.py`
- `src/webui/app.js`
- `src/webui/index.html`
- `src/webui/styles.css`
- `scripts/capture_webui_screenshots.py`
- `scripts/verify_bulk_gallery_excel_flow.py`
- `tests/test_bulk_gallery_flow.py`
- `examples/toplu_etiket_ornek.xlsx`

## Testler

- `tests/test_bulk_gallery_flow.py` eklendi.
- `scripts/verify_bulk_gallery_excel_flow.py` eklendi.
- Gerçek render ve queue doğrulaması çalıştırıldı.

## Güvenlik

- Direct print açılmadı.
- Yazıcı/lazer otomatik çalıştırılmadı.
- CorelDRAW, Illustrator ve RDWorks tetiklenmedi.
- Kaynak AI/CDR dosyaları değiştirilmedi.

## Kalan Risk

P0/P1 yok. P2 olarak galeri edit modalına ileride gerçek satır bazlı font/renk seçimi ve sayfalama/virtual grid eklenebilir.
