# Operatör Rehberi

Bu rehber CeyizHome Lab production ekranlarının güvenli kullanım akışını özetler.

## Temel Kural

CeyizHome Lab üretim hazırlık merkezidir. Yazıcı, lazer, RDWorks ve Trendyol canlı işlemleri otomatik başlatılmaz. Riskli aksiyonlar manuel onay, dry-run veya disabled guard altında kalır.

## Toplu Üretim Studio

1. Kaynak seçin: Excel, Trendyol veya manuel.
2. Alanları Kontrol Et adımında zorunlu alanları doğrulayın.
3. Model ve şablon eşleşmesini kontrol edin.
4. Toplu Önizleme Galerisi'nde hazır, kontrol gerekli ve hatalı kayıtları ayırın.
5. Hataları Düzelt panelinde üretime engel kayıtları çözün.
6. Sadece hazır kayıtları Yazdırma Sırası'na veya İsim Kesim hazırlığına alın.

## Trendyol

Trendyol entegrasyonu read-only senkron ve local production hazırlığı için kullanılır. Kargo, fatura ve statü değişiklikleri bu release'te canlı tetiklenmez.

Kişiselleştirme alanları yalnızca müşteri mesajı, soru/cevap, bağlı kanıt veya operatör manuel girişi ile doldurulur. Kanıt yoksa alan kontrol gerekli kalır.

## Etiket Studio

Etiket Studio tekil kayıtların preview/output hazırlık alanıdır. Boş isim, eksik model veya gerçek çıktı dosyası olmayan kayıtlar Yazdırma Sırası'na hazır sayılmaz.

## Yazdırma Sırası

Yazdırma Sırası tüm kaynaklardan gelen işleri kontrol eder. Yazdırma için:

- çıktı dosyası gerçek olmalı,
- adet geçerli olmalı,
- yazıcı profili seçilmeli,
- blocked flag bulunmamalı,
- operatör onayı verilmelidir.

## İsim Kesim

İsim Kesim ekranında aynı isim içindeki harfler tek parça/weld mantığında olmalı, nokta ve Türkçe işaretler ana gövdeye bağlı kalmalıdır. Farklı isimler çok yakın dizilebilir ancak temas edemez. Export yalnızca dosya hazırlığıdır; RDWorks/lazer başlatılmaz.

## Üretim Geçmişi

Üretim Geçmişi audit merkezi; kaynak, batch, queue, export ve hata kayıtlarını tek yerde gösterir. CSV/JSON export gerçek dosya üretir. Event detayından ilgili ekrana güvenli geçiş yapılabilir.

## Veri Bakımı

Yedekleme ve geri yükleme işlemlerinde önce backup doğrulanır. Restore öncesi dry-run yapılmalı ve otomatik snapshot alınmalıdır.
