# Visual Screenshot QA Guide

Her UI geliştirme sonrası screenshot alınır ve insan gözüyle incelenir.

## Kontrol Listesi

- Sayfa boş mu?
- Butonlar görünür mü?
- Butonlar anlaşılır mı?
- Teknik detaylar normal kullanıcıya görünüyor mu?
- Kartlar düzenli mi?
- Sağ panel pasif mi?
- Placeholder veya kırık görsel var mı?
- Türkçe karakterler doğru mu?
- Modal düzgün mü?
- Canvas görünür mü?
- Selection ve handle anlaşılır mı?
- PDF/PNG preview canvas ile aynı mı?

## Başarısız Screenshot Örnekleri

- Boş/beyaz ekran.
- Kırık görsel.
- Taşan filtre veya buton.
- Üst üste binen metin.
- Teknik debug bilgisinin normal kullanıcıya görünmesi.
- Yanlış dosya preview’i.
- Canvas ve PDF/PNG arasında belirgin fark.

## Kural

Screenshot kötü görünüyorsa:

- “PASSED” deme.
- UI’yi düzelt.
- Screenshotı tekrar al.

## Kanıt

Raporlarda screenshot klasörü veya kritik ekran screenshot path’i yazılır. UI işi screenshot kanıtı olmadan kapanmaz.
