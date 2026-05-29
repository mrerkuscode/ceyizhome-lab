# Design Lab Toplu Üretim Referans Raporu

## Test Tarihi

2026-05-20

## Kapsam

Bu çalışma yalnızca aktif web UI içindeki Design Lab `Toplu Üretim` sekmesini kapsar. Production Toplu Üretim/Toplu Etiket ekranına, Python bridge/backend methodlarına, gerçek Excel okuma/yazdırma/lazer/RDWorks/üretim işlemlerine dokunulmadı.

## Yapılanlar

- `Toplu Üretim Studio` başlığı ve açıklaması CeyizHome Lab üretim merkezi diliyle yeniden kurgulandı.
- Üst komut alanına mock `Örnek Excel İndir`, `Rehber Video`, `Geçmiş İşlemler` ve son işlem saati eklendi.
- 6 adımlı stepper eklendi:
  - Kaynak Seç
  - Alanları Kontrol Et
  - Model ve Şablon Seç
  - Toplu Önizleme Galerisi
  - Hataları Düzelt
  - Üretime Al
- Kaynak kartları eklendi:
  - Excel’den Yükle
  - Trendyol’dan Al
  - Manuel Satır Ekle
- Sağda sabit üretim özeti paneli eklendi.
- Galeri odaklı Toplu Önizleme bölümü eklendi.
- Filtreler, görünüm seçenekleri ve toplu aksiyonlar mock olarak tasarlandı.
- Hata kontrol özeti ve büyük önizleme modal mock’u eklendi.
- Tüm yeni stiller `.design-lab-page` kapsamıyla sınırlı tutuldu.

## Kullanılan Mock Kayıtlar

- Ayşe & Mehmet: hazır, kalite `%92`, lazer var.
- Yağmur & Efe: hazır, kalite `%88`, lazer var.
- Mustafa Kemal & Yağmur: yazı taşıyor, kalite `%48`, AI önerilir.
- Helin Cemal: tarih bulundu, kalite `%95`, lazer var.
- Can: yazısı küçük, AI büyütme önerisi.
- Abdurrahman: uzun isim, otomatik daralt/lazer kontrol önerisi.

## Toplu Önizleme Galerisi

Var. Varsayılan görünüm galeri olarak tasarlandı. Kartlarda thumbnail, satır/kaynak no, isim, tarih, not, adet/model bilgisi, kalite skoru, durum rozeti, lazer rozeti ve hızlı aksiyonlar gösteriliyor.

## Sağ Üretim Özeti

Var. Kaynak, toplam kayıt, hazır/kontrol/hatalı/lazer sayıları, toplam adet, seçili etiket modeli, seçili lazer modeli, çıktı durumu ve yazdırma sırası görünüyor.

## Hata Paneli

Var. Hatalı kayıt, yazı taşıyor, yazısı küçük, lazer taşması ve model eksik özetleri ile mock aksiyonlar eklendi.

## Görsel QA

- 1920x1080: PASSED. Stepper, kaynak kartları, sağ özet ve galeri kartları ferah şekilde görünüyor.
- 1366x768: PASSED. Üst chrome çalışma alanını ezmiyor; kaynaklar, stepper, sağ özet ve galeri başlangıcı okunabilir.

## Screenshot Yolları

- `output/2026-05-20/design_lab_toplu_uretim_reference/toplu-uretim-reference-1920.png`
- `output/2026-05-20/design_lab_toplu_uretim_reference/toplu-uretim-reference-1366.png`

## Production'a Dokunuldu mu?

Hayır. Production Toplu Üretim/Toplu Etiket ekranı ve backend/bridge tarafı değiştirilmedi.

## Sonraki Adım

Toplu Üretim referansı üretim merkezi yönüyle güçlü görünüyor. Sıradaki Design Lab ekranı olarak `Yazdırma Sırası` referansının profesyonel seviyeye çıkarılması önerilir.
