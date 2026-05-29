# CODEX Planning Mode Remaining Work Report

Tarih: 2026-05-13

## Bu proje şu an hangi seviyede?

**MVP'ye yakın / MVP teslim adayı.** Etiket Studio, temel PDF/PNG render, output validation, güvenli yazdırma modalı ve queue zinciri için güçlü otomatik kanıt var. Release Candidate demek için hâlâ erken; çünkü bazı sayfalarda eski/test çıktı metadata'sı kullanıcı deneyimini zayıflatıyor ve RDWorks isim kesim tarafında gerçek text-to-path/offset P1 teknik risk olarak duruyor.

## Bitmiş görünen bölümler

- Etiket Studio Corel benzeri editör: drag, resize, zoom, font/renk, layer seçimi, PDF/PNG payload doğrulaması için test kanıtı var.
- Etiket Modelleri premium katalog: preview resolver, sağ panel, model health ve routing testleri mevcut.
- Yazdırma güvenliği: direct/silent print kapalı; Yazdır butonu PDF'i kullanıcı onayına sunuyor.
- RDWorks hazırlık paketi: DXF/SVG/PDF/PNG/manifest üretiyor, RDWorks/lazer otomatik açılmıyor.

## Kanıtı eksik veya yüzeysel kalan bölümler

- Toplu Etiket galeri ekranında özet kartları bazı kanıtlarda galeri state'iyle senkron görünmüyordu. Bu turda UI özet kartları galeri item state'inden beslenmeye başladı.
- Yazdırma Sırası ve Etiket Çıktıları eski/test PDF'lerde model/isim/ölçü/adet bilgisini kaçırabiliyordu. Bu turda dosya adından güvenli metadata fallback'i ve PDF-PNG preview pairing eklendi.
- Yeni Model Ekle wizard son kullanıcı screenshot seti zayıf; hedefli final doğrulama gerekiyor.
- Yardım/onboarding ve release teslim dokümanları var, fakat temiz kurulum paketi seviyesinde ayrıca doğrulanmalı.

## Kalan işler

### P1

- Toplu Etiket için 100 satırlık gerçek kullanıcı fixture'ı ve galeri/manifest/queue kanıtı.
- Yeni Model Ekle wizard için görsel yükleme, oran kontrolü, sticky footer ve Studio'da açma kanıtı.
- Final uçtan uca gerçek kullanıcı kabul döngüsü.

### P2

- Studio sağ inspector/property bar responsive polish.
- Etiket Modelleri viewport edge-case ve Varyant Oluştur doğrulaması.
- Ayarlar/Yardım ekranlarının sade teslim kalitesine getirilmesi.
- Temiz canonical screenshot setinin tek klasörde toplanması.

### P3 / ayrı faz

- RDWorks gerçek text-to-path/outline dönüşümü.
- Gerçek stroke-to-path/offset kalınlaştırma.
- 100+ isim için daha gelişmiş fire azaltma.
- Gerçek installer/release automation.

## Agent modunda uygulanacak sıra

1. Queue/Outputs metadata ve preview pairing güvenilirliği.
2. Toplu Etiket 100 satır galeri kesinleştirme.
3. Yeni Model Ekle wizard hedefli doğrulama.
4. Studio/Models son responsive polish.
5. Yardım, dokümantasyon ve final MVP kabul döngüsü.
6. RDWorks isim kesim üretim readiness ayrı fazı.

## Bu turda uygulanan ilk düzeltme

- `src/webui/app.js`: Output/Queue metadata fallback ve Toplu Etiket özet senkronu.
- `src/webui_backend/print_queue_api.py`: Queue kayıtları artık PDF dosya adından model/isim/ölçü/adet fallback'i ve eşleşen PNG preview URI'si çıkarıyor.
- `tests/test_output_queue_metadata_reliability.py`: Metadata fallback, preview pairing ve missing PDF güvenlik testi eklendi.
