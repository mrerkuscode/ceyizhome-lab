# Known Issues

- 1280 px altı viewport için bazı yoğun production ekranlarında ek overlay/drawer polish gerekebilir.
- Gerçek canlı Trendyol statü/kargo/fatura işlemleri bu release'te kapalıdır; yalnızca read-only/dry-run altyapısı vardır.
- Direct print, lazer gönderim ve RDWorks otomatik açma/gönderme bu release'te kapalıdır.
- Çok büyük veri setlerinde galeri incremental render kullanır; gerçek virtualization ileri fazda değerlendirilebilir.
- Bazı eski Excel fixture'larında pandas duplicate column uyarısı görülebilir; ilgili gate sonuçları PASS ise üretim akışını engellemez.
