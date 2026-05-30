# Button Click Testing Standard

Buton testi sadece butonun DOM’da görünmesi değildir. Buton gerçek kullanıcı tıklamasıyla beklenen aksiyonu üretmelidir.

Her buton için şu doğrulanır:

1. Tıklanabilir mi?
2. Tıklanınca beklenen işlem oluyor mu?
3. Yanlış route’a gidiyor mu?
4. `selectedModel` doğru mu?
5. Modal doğru veriyle açılıyor mu?
6. Sessiz kalıyor mu?
7. Console error var mı?
8. Teknik editör yanlış açılıyor mu?
9. Kullanıcıya sade mesaj gösteriyor mu?
10. Screenshot veya state kanıtı var mı?

## Kritik Butonlar

Ana Sayfa:

- Etiket Hazırla
- Excel ile Başla
- Modelleri Yönet
- Son PDF’i Aç
- Son PNG’yi Önizle
- Yazdırma Sırasını Gör
- Yeni Model Ekle
- Ayarları Aç

Etiket Modelleri:

- Yenile
- Tasarım Görseli Yükle
- Yeni Model Ekle
- Kart seçimi
- Etiket Hazırla
- Studio’da Düzenle
- Önizle
- Görsel Bağla
- Modeli Kontrol Et
- Teknik Mod
- Filtreler

Etiket Studio:

- Model Seç
- PDF/PNG Oluştur
- PDF’i Gör
- PNG Önizle
- Yazdırma Sırasına Ekle
- Gerçek Render Kontrolü

## Başarı Kuralı

Buton ya gerçek işlem yapar ya sade kullanıcı mesajı verir. Sessiz buton başarısızdır.

## Güvenlik Kuralı

Normal kullanıcı butonları teknik editör, CorelDRAW, Illustrator, RDWorks, yazıcı, lazer veya direct print tetiklemez.
