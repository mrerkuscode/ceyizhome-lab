# Remaining Productization Roadmap

Tarih: 2026-05-16

## P0

Bilinen açık P0 yok.

Son doğrulamada kritik üretim zincirleri geçti:

- Etiket Studio drag/resize/font/renk/canvas state
- PDF/PNG üretimi
- Output validation
- Yazdırma Sırası stale/direct print koruması
- Etiket Çıktıları müşteri/teknik arşiv ayrımı
- Toplu Etiket 100 satır galeri ve batch manifest
- RDWorks dosya hazırlama güvenlik sınırları

## P1

Bilinen teknik P1 yok.

Operasyonel karar gerektiren P1-adayı:

1. Trendyol ürün eşleştirme tablosu
   - Canlı API bağlantısı çalışıyor.
   - 333 ürün okunabiliyor.
   - 210 sipariş satırı üretim önerisine dönüşebiliyor.
   - Mapping tablosu boş olduğu için canlı satırlar güvenli şekilde `Kontrol gerekli` durumunda.
   - Mapping algoritması QA/test modellerini ve rastgele barkod son eklerini otomatik eşleştirmeyecek şekilde sıkılaştırıldı.
   - Mapping review Excel oluşturuldu: `output/2026-05-16/trendyol/trendyol_mapping_review_014610_348022.xlsx`.
   - `scripts/verify_trendyol_live_mapping_readiness.py` kalite kapısı geçti.
   - Barcode/SKU -> etiket modeli / isim kesim stili kararları ürün bazında onaylanmalı.
   - AI bu kararı otomatik geçersiz kılamaz.

## P2

1. Trendyol mapping UX hızlandırma
   - Toplu filtre, güvenli öneri, eşleşmeyen ürün ve düşük güven skorlarını daha hızlı yönetecek ekran iyileştirilebilir.

2. Temiz demo veri yönetimi
   - `scripts/verify_clean_customer_demo_flow.py` ve `scripts/seed_clean_customer_demo_data.py` çalışıyor.
   - Bu akış kullanıcı menüsünde güvenli bir bakım aksiyonuna dönüştürülebilir.

3. Yardım ve onboarding sadeleştirme
   - Ana üretim akışı hazır.
   - Son kullanıcı için yardım metinleri daha kısa, daha görsel ve görev odaklı yapılabilir.

4. Release paketi polish
   - Kullanıcı rehberi, teknik rehber ve temiz kurulum checklist'i son ekran adlarıyla tekrar hizalanabilir.

## P3

1. Installer / release automation
   - Tek tık kurulum, masaüstü kısayolu ve örnek veri paketi ayrı release fazında ele alınmalı.

2. RDWorks saha doğrulaması
   - DXF/SVG/PDF/PNG/manifest üretimi geçiyor.
   - Gerçek RDWorks import ekranında layer, ölçü, path ve offset kontrolü kullanıcı tarafından doğrulanmalı.

3. RDWorks gelişmiş nesting
   - Mevcut sistem 50 isim için çakışmasız yerleşim yapıyor.
   - Daha düşük fire için ileri bin-packing ayrı optimizasyon fazıdır.

4. Trendyol sorular/mesajlar entegrasyonu
   - Trendyol Questions servisi canlı testte HTTP 556 döndü.
   - Cyzella bunu güvenli şekilde izole ediyor.
   - Servis erişilebilir olduğunda mesaj/soru kanıtları üretim önerisine eklenebilir.

## Güvenlik Sınırları

- CorelDRAW, Illustrator, RDWorks ve lazer otomatik açılmayacak.
- Direct/silent print açılmayacak.
- Kaynak AI/CDR dosyaları değiştirilmeyecek.
- Eski Trendyol projesi değiştirilmeyecek.
- Secret/API bilgileri kaynak koda yazılmayacak.
- Final PDF/PNG çıktısına mock/stale veri karışmayacak.
