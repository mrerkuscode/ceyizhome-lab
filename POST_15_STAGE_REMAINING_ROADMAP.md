# Post 15 Aşama Kalan Roadmap

Tarih: 2026-05-13

P0/P1 açık hata bulunmadı. Aşağıdaki maddeler üretimi durdurmayan P2/P3 iyileştirmelerdir.

## P2 - Yakın Sprint

1. Daha geniş Excel fixture seti
   - Hatalı tarih, boş isim, uzun not, duplicate satır ve farklı model eşleşmelerini içeren test XLSX setleri eklenebilir.

2. Wizard çok küçük ekran davranışı
   - Sticky footer düzeltildi. 768px altı ekranlarda adım kartları ve görsel yükleme alanı ayrıca optimize edilebilir.

3. Üretim geçmişi arşiv performansı
   - Çıktı sayısı büyüdükçe filtreleme ve indeksleme performansı izlenmeli.

4. Screenshot QA varyantları
   - Koyu tema, dar ekran ve yüksek zoom ekran görüntüleri ayrı kalite klasörlerinde üretilebilir.

5. Yardım sistemi mikro eğitimleri
   - Mevcut yardım akışı çalışıyor. Daha görsel tur highlight animasyonları eklenebilir.

## P3 - Sonraki Faz

1. Installer / paketleme
   - Gerçek kullanıcı teslimi için kurulum sihirbazı veya paketleme sistemi planlanabilir.

2. Gelişmiş rulo optimizasyonu
   - Fire optimizasyonu, kesim toleransı profilleri ve malzeme bazlı yerleşim stratejileri eklenebilir.

3. Model versiyonlama
   - Her model config değişikliği için görsel diff ve rollback paneli geliştirilebilir.

4. Fiziksel cihaz entegrasyonları
   - Yazıcı, lazer, RDWorks, CorelDRAW veya Illustrator otomasyonu hâlâ manuel karar gerektirir. Güvenlik sınırı gereği bu fazda yapılmadı.

5. Gelişmiş canvas araçları
   - Space + drag pan, snap ölçüleri, gelişmiş ruler ayarları ve multi-select daha sonraki editör fazında ele alınabilir.

## Son Karar

Kalan maddeler MVP final kabulünü engellemez. Güvenli üretim yolu, PDF/PNG output validation ve queue zinciri korunmaktadır.
