# Gerçek Kullanıcı Test Standardı

Bu projede “test geçti” demek için kodun çalışması yetmez. Normal kullanıcı gibi gerçek akış denenmelidir.

## Temel Kural

Bir özellik şu 4 şeyi geçmeden tamamlanmış sayılmaz:

1. Gerçek kullanıcı aksiyonu çalışıyor mu?
2. Ekranda beklenen değişiklik oluyor mu?
3. State, backend veya output doğru güncelleniyor mu?
4. Screenshot veya dosya çıktısıyla kanıt var mı?

## Sahte Başarı Sayılmayacak Durumlar

- Buton DOM’da var ama tıklanınca işlem yok.
- Toast çıkıyor ama gerçek aksiyon yapılmıyor.
- Modal açılıyor ama yanlış veri gösteriyor.
- Kart seçiliyor gibi görünüyor ama `selectedModel` değişmiyor.
- Etiket Studio’ya gidiyor ama yanlış model açılıyor.
- Handle görünüyor ama drag/resize çalışmıyor.
- `x/y/width/height/font_size` değişmiyor.
- PDF oluşuyor ama eski veya stale dosya.
- PNG oluşuyor ama background veya yazı yok.
- Queue’ya yanlış dosya gidiyor.
- Teknik editör normal kullanıcıdan açılabiliyor.
- Screenshot alınmadı.
- Console error var.
- Test sadece “fonksiyon var mı?” diye bakıyor.

## Gerçek Kullanıcı Gibi Test Et

Her kritik akışta şu yapılmalı:

- Sayfayı aç.
- Butona gerçek click uygula.
- Route veya screen değişimini doğrula.
- Modal açıldı mı kontrol et.
- Gerekirse input yaz.
- Mouse ile sürükle.
- Mouse ile resize yap.
- Klavye ile hareket ettir.
- PDF/PNG oluştur.
- Önizleme aç.
- Queue’ya ekle.
- Screenshot al.
- Dosya çıktısını kontrol et.

## Kullanıcı Gözlemi Üstündür

Rapor veya otomatik test “PASSED” dese bile kullanıcı gerçek ekranda çalışmadığını söylüyorsa:

- Hata kabul edilir.
- Test eksik kabul edilir.
- Gerçek kullanıcı senaryosu eklenir.
- Düzeltme yapılır.

## Görev Kapanış Kuralı

P0/P1 etkileyen bir geliştirme, gerçek kullanıcı akışı ve ilgili kalite kapıları geçmeden kapatılamaz. UI işi screenshot QA olmadan bitmiş sayılmaz.

## Final Tamamlanma Testi

Tüm geliştirmeler bittiğinde iş otomatik test sonucu ile kapatılmaz. En sonda tam gerçek kullanıcı doğrulaması yapılır.

Final doğrulama şunları kapsar:

- Ana sayfalar normal kullanıcı gibi gezilir.
- Etiket Modelleri kart seçimi, sağ panel, Önizle, Etiket Hazırla ve Studio’da Düzenle gerçek click ile denenir.
- Etiket Studio’da İsim/Tarih/Not seçilir, mouse ile taşınır, köşeden ve kenardan resize yapılır.
- Font, renk, layer, Akıllı Düzen, undo/redo ve zoom modları gerçek davranışla doğrulanır.
- PDF/PNG oluşturulur ve son canvas state ile aynı mı kontrol edilir.
- Yazdır modalı açılır ama silent/direct print yapılmaz.
- Yazdırma Sırasına Ekle doğru, güncel ve doğrulanmış dosyayı alır.
- Toplu Etiket, Etiket Çıktıları, Yazdırma Sırası, Ayarlar ve Yardım akışları gerçek kullanıcı gözüyle kontrol edilir.
- Screenshotlar alınır ve insan gözüyle incelenir.
- Rapor PASSED dese bile ekran bozuksa veya kullanıcı deneyimi çalışmıyorsa iş bitmiş sayılmaz.

Final cümlesi yalnızca P0/P1 kalmadığında ve gerçek kullanıcı testi geçtiğinde yazılır.

## `test` Komutu Kuralı

Kullanıcı sadece `test` yazarsa bu komut tam gerçek kullanıcı QA döngüsü anlamına gelir.

Zorunlu kapsam:

- Ana sayfaları aç.
- Etiket Modelleri gerçek click gate çalıştır.
- Etiket Studio gerçek pointer/keyboard interaction gate çalıştır.
- PDF/PNG output validation çalıştır.
- Final acceptance gate çalıştır.
- Screenshotları üret.
- `TEST_COMMAND_REAL_USER_QA_REPORT.md` raporunu güncelle.

P0/P1 hata varsa hata düzeltilmeden `test komutu tamamlandı, P0/P1 hata yok` denmez.
