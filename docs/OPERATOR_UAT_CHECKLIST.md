# Operatör UAT Checklist

Bu checklist CeyizHome Lab release adayı için operatör kabul testidir. Canlı yazıcı, lazer, RDWorks ve Trendyol işlemleri otomatik başlatılmamalıdır.

## 1. Excel'den Üretim Hazırlığı

- [ ] Toplu Üretim Studio açılır.
- [ ] Excel dosyası seçilir.
- [ ] Alanları Kontrol Et ekranında İsim, Tarih, Not, Adet, Etiket Modeli ve Lazer İsim alanları anlaşılır görünür.
- [ ] Eksik zorunlu alanlar kırmızı/engelleyici görünür.
- [ ] Galeride hazır, kontrol gerekli ve hatalı kayıtlar ayrılır.

## 2. Trendyol'dan Üretim Hazırlığı

- [ ] Trendyol Siparişleri ekranı açılır.
- [ ] Read-only mode rozeti görünür.
- [ ] Toplu Üretim'e Aktar aksiyonu canlı statü/kargo/fatura tetiklemez.
- [ ] Aktarım özeti aktarılan, kontrol gerekli, blocked ve duplicate kayıtları gösterir.

## 3. Kanıt Drawer ve Manuel Düzeltme

- [ ] Trendyol kaynaklı galeri kartında Kanıtı Gör açılır.
- [ ] İsim, Tarih, Not ve Lazer İsim için kanıt kaynağı görünür.
- [ ] Kanıt yoksa alan uydurulmaz.
- [ ] Operatör manuel düzeltme yapınca kayıt durumu güncellenir.
- [ ] Düzeltme Üretim Geçmişi audit kayıtlarına düşer.

## 4. Etiket Studio Preview / Output

- [ ] Studio'da Aç ile isim, tarih, not, adet ve model alanları dolar.
- [ ] Veri Hazır, Önizleme Eksik, Önizleme Hazır ve Çıktı Hazır durumları karışmaz.
- [ ] Boş isim veya eksik model üretime engel görünür.
- [ ] Gerçek PDF/PNG yoksa sahte success verilmez.

## 5. Yazdırma Sırası Manuel Print Hazırlığı

- [ ] Yazdırma Sırası kaynak rozetlerini gösterir.
- [ ] Çıktı dosyası olmayan kayıt Yazdırmaya Hazır sayılmaz.
- [ ] Yazdır butonu operatör onay modalı açar.
- [ ] Yazıcı profili seçilmeden print hazırlığı tamamlanmaz.
- [ ] Yazıcı otomatik başlamaz.

## 6. İsim Kesim Export / Manifest

- [ ] İsim Kesim ekranı 800x600 mm tabla, 80x40 mm hedef isim ve 1 mm boşluk standardını gösterir.
- [ ] Tek parça/weld, nokta/işaret bağlantısı ve collision kontrolleri görünür.
- [ ] Kalite kilidi geçmeyen kayıt export edilemez.
- [ ] SVG/PDF export gerçek dosya ve manifest üretir.
- [ ] RDWorks/lazer otomatik başlamaz.

## 7. Üretim Geçmişi Export / Deep Link

- [ ] Üretim Geçmişi ekranında eventler kaynak, durum ve severity ile görünür.
- [ ] CSV/JSON export gerçek dosya üretir.
- [ ] Event detay drawer ilgili ekrana güvenli geçiş sağlar.
- [ ] Kayıt veya dosya yoksa sahte başarı verilmez.

## 8. Backup / Restore Dry-Run

- [ ] Veri Bakımı ekranı açılır.
- [ ] Yedek oluştur gerçek manifest ve checksum üretir.
- [ ] Restore dry-run değişecek dosyaları gösterir.
- [ ] Corrupt backup restore edilmez.
- [ ] Restore öncesi snapshot alınır.

## 9. Sol Menü ve Navigasyon

- [ ] Sidebar collapsed halde ikonlar görünür.
- [ ] Mouse hover ile sidebar açılır.
- [ ] Mouse ayrılınca tekrar collapsed olur.
- [ ] Manuel pin/open state hover tarafından bozulmaz.
- [ ] Tüm menü linkleri doğru ekrana gider.
- [ ] Aktif ekran vurgusu doğru kalır.
