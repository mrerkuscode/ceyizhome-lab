# RDWorks Boolean Offset Research Report

Tarih: 2026-05-13

## Kısa Karar

RDWorks / İsim Kesim export hattında text-to-path tarafı `fontTools` ile doğrulanmış durumda: `OUTLINED_PATHS_WITH_FONTTOOLS`.

Ancak gerçek boolean/geometrik offset veya stroke-to-path conversion bu ortamda güvenli şekilde tamamlanmadı. Mevcut sistem yaklaşık contour expansion / stroke fallback mantığıyla çalışıyor ve bu yüzden P1 teknik risk notu korunmalıdır.

Bu işte sahte başarı üretilmedi: gerçek offset motoru yokken "tam üretime hazır offset" denmedi.

## İncelenen Mevcut Durum

Kod:

- `src\webui_backend\combined_production_api.py`
- `_outline_contours_for_item(...)`
- `_expand_contour_for_cutting(...)`
- `_svg_document(...)`
- `_dxf_document(...)`

Mevcut davranış:

- Yazı konturları `fontTools` ile path/outline olarak çıkarılıyor.
- DXF birincil export olarak üretiliyor.
- SVG, PDF preview, PNG preview ve manifest üretiliyor.
- Çoklu plate/page yerleşimi DXF ve SVG tarafında hizalı.
- Layer renk standardı korunuyor:
  - Kırmızı: ana kesim çizgisi
  - Mavi: destek çizgisi
  - Mor: taban/plaka
  - Yeşil: kalibrasyon
  - Gri: kılavuz

Mevcut kalınlaştırma davranışı:

- Offset değerleri manifest'e yazılıyor.
- Konturlar yaklaşık merkezden dışa genişletiliyor.
- SVG tarafında stroke fallback ile görsel kalınlık var.
- Bu gerçek boolean offset/stroke-to-path değildir.

## Kurulu Kütüphane Kontrolü

Kontrol edilen modüller:

| Modül | Durum |
|---|---|
| `fontTools` | Kurulu |
| `shapely` | Kurulu değil |
| `pyclipper` | Kurulu değil |
| `svgpathtools` | Kurulu değil |
| `skia_pathops` | Kurulu değil |
| `cairo` | Kurulu değil |
| `cairocffi` | Kurulu değil |

Sonuç:

- Mevcut ortamda text outline alınabiliyor.
- Mevcut ortamda güvenilir boolean offset/union/difference motoru yok.

## Neden Yeni Kodla Sahte Offset Yapılmadı?

Script font konturları çoğu zaman çok parçalı, kıvrımlı ve kendi içinde delikli yapılardır.

Basit normal/miter offset algoritması:

- Delik yönlerini yanlış genişletebilir.
- Konturları self-intersection durumuna sokabilir.
- İnce script bağlantılarını bozabilir.
- RDWorks'te beklenmeyen kesim çizgileri üretebilir.
- Kullanıcıya üretime hazır gibi görünen ama kesimde riskli dosya verebilir.

Bu nedenle yeni dış motor olmadan "true offset" başarı sayılmadı.

## Önerilen Güvenli Seçenekler

### Seçenek 1: `pyclipper`

Artıları:

- Polygon offset için pratik ve hızlı.
- DXF/SVG polygon path üretimiyle uyumlu olabilir.

Eksileri:

- Cubic bezier konturlar önce yeterli çözünürlükle flatten edilmeli.
- Script fontlardaki iç/dış contour ayrımı ve union/cleanup dikkat ister.
- Yeni dış bağımlılık ekler.

Karar:

- En uygulanabilir Python içi seçenek.
- Eklenirse ayrı teknik fazda, fixture ve görsel RDWorks QA ile yapılmalı.

### Seçenek 2: Inkscape CLI

Artıları:

- Text-to-path ve stroke-to-path akışını gerçek vektör araçlarıyla yapabilir.
- Kullanıcı RDWorks'e benzer vektör çıktısı alabilir.

Eksileri:

- Makinede Inkscape kurulumu gerekir.
- Harici uygulama çağrısı ve path yönetimi gerekir.
- Yeni operasyonel bağımlılık oluşturur.

Karar:

- Kuruluysa opsiyonel advanced export olarak değerlendirilebilir.
- Otomatik RDWorks/lazer açma ile karıştırılmamalı.

### Seçenek 3: `shapely`

Artıları:

- Geometry buffer ile offset/union yapılabilir.

Eksileri:

- Font contour flattening ve hole/orientation yönetimi yine gerekir.
- Kurulu değil.
- DXF path kalitesi ayrıca kontrol edilmeli.

Karar:

- Araştırılabilir, fakat ilk tercih `pyclipper` kadar net değil.

### Seçenek 4: Mevcut fallback'i koru

Artıları:

- Yeni bağımlılık yok.
- Mevcut testler ve güvenlik kapıları geçiyor.
- Kullanıcıya "RDWorks'te kontrol gerekli" uyarısı veriliyor.

Eksileri:

- Tam üretime hazır offset değildir.
- Kalınlaştırma gerçek boolean offset olarak garanti edilemez.

Karar:

- MVP etiket üretimi için güvenli.
- RDWorks üretim seviyesi için P1 risk açık kalır.

## Güvenlik Teyidi

Bu araştırma sırasında:

- RDWorks otomatik açılmadı.
- Lazer otomatik başlamadı.
- Direct print aktif edilmedi.
- Yazıcı otomatik çalıştırılmadı.
- CorelDRAW/Illustrator otomasyonu tetiklenmedi.
- Kaynak AI/CDR dosyaları değiştirilmedi.

## Kabul Durumu

Tamamlanan:

- Mevcut offset riskinin gerçek olduğu kanıtlandı.
- Kurulu bağımlılıklar kontrol edildi.
- Sahte "tam offset tamamlandı" kararı verilmedi.
- RDWorks mevcut export zinciri testlerle çalışır durumda bırakıldı.

Tamamlanmayan:

- Gerçek boolean offset/stroke-to-path uygulanmadı.

Neden:

- Güvenilir motor kurulu değil.
- Yeni dış bağımlılık teknik karar gerektirir.
- Basit yerel offset algoritması üretim dosyasını riskli hale getirebilir.

## Sonraki Uygulama Kararı

Önerilen sıradaki teknik faz:

1. `pyclipper` PoC için ayrı branch/faz aç.
2. FontTools konturlarını yüksek çözünürlüklü polygon'a flatten et.
3. İç/dış contour orientation ve union/cleanup testlerini kur.
4. `offset_mm` için gerçek polygon offset uygula.
5. DXF/SVG export'u offset contour ile üret.
6. RDWorks benzeri 50/100 isim screenshot ve manifest testleriyle doğrula.
7. Başarılı olursa P1 risk kapatılır.

Bu karar verilene kadar UI/rapor dili şöyle kalmalı:

> "Dosya RDWorks için hazırlandı. RDWorks'te manuel açıp path, layer ve offset/kalınlık kontrolü yaptıktan sonra kesime başlayın."
