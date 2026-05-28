# İnsan Gibi QA Protokolü

Bu protokol, otomatik testlerden ayrı olarak kullanıcı gözüyle doğrulanması gereken akışları tanımlar. Manuel gözlem otomatik rapordan üstündür.

## Ana Sayfa

Senaryo:

1. Program açılır.
2. Ana Sayfa görünür.
3. Etiket Hazırla tıklanır.
4. Etiket Studio’ya gidilir.
5. Geri dönülür.
6. Excel ile Başla tıklanır.
7. Toplu Etiket açılır.
8. Modelleri Yönet tıklanır.
9. Etiket Modelleri açılır.
10. Hızlı İşlemler denenir.
11. Son PDF yoksa sade boş mesaj görülür.
12. Yazdırma güvenliği bilgisi görünür.

Başarı:

- Butonlar sessiz kalmaz.
- Yanlış teknik ekran açılmaz.
- Mock veri gösterilmez.
- Türkçe karakterler düzgündür.

## Etiket Modelleri

Senaryo:

1. Sayfa açılır.
2. İlk model kartı tıklanır.
3. Sağ panel değişir.
4. Etiket Hazırla tıklanır.
5. Etiket Studio doğru modelle açılır.
6. Geri dönülür.
7. İkinci model seçilir.
8. Studio’da Düzenle tıklanır.
9. Etiket Studio ikinci modelle açılır.
10. Önizle tıklanır.
11. Modal açılır.
12. Modal kapatılır.
13. Görsel Bağla denenir.
14. Teknik editör açılmaz.
15. Yeni Model Ekle tıklanır.
16. Sade modal açılır.
17. Teknik editör açılmaz.
18. Arama ve filtreler denenir.
19. Teknik Mod kapalıyken teknik detay görünmez.
20. Teknik Mod açılınca teknik detay görünür.

Başarı:

- Her kart doğru modeli taşır.
- `selectedModel` güvenlidir.
- Butonlar gerçek işlem yapar.
- Sessiz kalan buton yoktur.
- Kırık görsel yoktur.
- Teknik editör normal kullanıcıya açılmaz.

## Etiket Studio

Senaryo:

1. Etiket Studio açılır.
2. Model Seç dropdown açılır.
3. Model seçilir.
4. Canvas güncellenir.
5. İsim inputu değiştirilir.
6. Canvas canlı güncellenir.
7. Tarih inputu değiştirilir.
8. Canvas canlı güncellenir.
9. Not inputu değiştirilir.
10. Canvas canlı güncellenir.
11. İsim alanı mouse ile taşınır.
12. Tarih alanı mouse ile taşınır.
13. Not alanı mouse ile taşınır.
14. İsim alanı köşeden resize yapılır.
15. Tarih alanı kenardan resize yapılır.
16. Zoom %150 yapılır.
17. Drag tekrar denenir.
18. Zoom %200 yapılır.
19. Resize tekrar denenir.
20. Arrow ile 0.1 mm hareket denenir.
21. Shift+Arrow ile 1 mm hareket denenir.
22. Alt+Arrow ile 0.05 mm hareket denenir.
23. PDF/PNG oluşturulur.
24. PDF preview açılır.
25. PNG preview açılır.
26. Yazdırma sırasına eklenir.
27. Queue’da doğru dosya görünür.

Başarı:

- Drag gerçek `x/y` değiştirir.
- Corner resize `width/height/font_size` değiştirir.
- Side resize `width/height` değiştirir.
- Zoom modlarında interaction bozulmaz.
- PDF/PNG yeni geometry ile oluşur.
- Canvas ile çıktı aynıdır.

## Toplu Etiket

Senaryo:

1. Excel seçilir.
2. Kontrol et çalışır.
3. Hatalı satırlar varsa görünür.
4. Model eşleşmesi kontrol edilir.
5. PDF/PNG batch oluşturulur.
6. Rulo batch oluşturulur.
7. Queue’ya eklenir.

Başarı:

- Duplicate note yoktur.
- Boş `custom_text` yoktur.
- Hatalar sade gösterilir.
- Queue doğru dosyayı alır.

## Yazdırma Sırası

Senaryo:

1. Queue açılır.
2. Bekleyen işler görünür.
3. PDF açılır.
4. PNG önizlenir.
5. İş silinir.
6. Duplicate engeli kontrol edilir.

Başarı:

- Direct print çalışmaz.
- Yazıcı otomatik çalışmaz.
- Yanlış veya boş dosya queue’ya girmez.

## Etiket Çıktıları

Senaryo:

1. Çıktılar açılır.
2. PDF kartları görünür.
3. PNG preview görünür.
4. Dosya açılır.
5. Klasörde göster çalışır.
6. Teknik raporlar müşteri çıktılarıyla karışmaz.

Başarı:

- Müşteri çıktıları nettir.
- Teknik dosyalar kullanıcıyı kirletmez.

## Ayarlar

Senaryo:

1. Varsayılan ölçü değiştirilir.
2. Kaydedilir.
3. Config backup alınır.
4. Etiket Studio default ölçüyü okur.
5. Studio override global ayarı bozmaz.

Başarı:

- Direct print kapalı kalır.
- Tehlikeli ayarlar normal kullanıcıdan gizlenir.
