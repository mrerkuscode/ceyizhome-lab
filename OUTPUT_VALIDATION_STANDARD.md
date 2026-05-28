# Output Validation Standard

PDF/PNG çıktı başarı sayılması için gerçek dosya ve görsel içerik doğrulanmalıdır.

## Başarı Şartları

- Dosya gerçekten oluşmalı.
- Dosya yeni ve taze olmalı.
- Dosya boyutu makul olmalı.
- Background görünmeli.
- İsim görünmeli.
- Tarih görünmeli.
- Not görünmeli.
- PDF preview son dosyayı göstermeli.
- PNG preview son dosyayı göstermeli.
- Queue son doğrulanmış batch PDF’i almalı.

## Başarısız Sayılacak Durumlar

- Sadece krem/bej zemin + çizgi.
- Background yok.
- Yazılar yok.
- Eski veya stale dosya açılıyor.
- Queue farklı dosya alıyor.
- PDF/PNG canvas’tan farklı.
- Output validation yapılmadan başarı mesajı veriliyor.

## Zorunlu Kontroller

- `real_production_quality_gate.py` tekli üretim için çalıştırılır.
- `final_acceptance_gate.py` çoklu model ve yeni model kabul senaryolarını doğrular.
- Dosya tazeliği ve field pixel kontrolleri yapılır.
- Queue path’i output path ile eşleşir.

## Güvenlik

Output validation hiçbir zaman yazıcı, direct print, lazer, CorelDRAW, Illustrator veya RDWorks tetiklemez.
