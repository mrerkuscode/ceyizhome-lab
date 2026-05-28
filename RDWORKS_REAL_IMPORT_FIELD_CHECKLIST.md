# RDWorks Real Import Field Checklist

Tarih: 2026-05-14

## Amaç

Bu checklist, Cyzella'nın hazırladığı isim kesim paketinin gerçek RDWorks uygulamasında manuel açılıp üretime alınmadan önce kontrol edilmesi için kullanılır.

Cyzella RDWorks'ü otomatik açmaz, lazeri başlatmaz ve makine hız/güç ayarı göndermez. Program sadece DXF/SVG/PDF/PNG/manifest paketini hazırlar. Kesim kararı ve makine parametreleri operatöre aittir.

## Son Doğrulanan Paket Örneği

Son otomatik doğrulama komutu:

```powershell
.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py
```

Sonuç: PASSED

Örnek çıktı seti:

- DXF: `output\2026-05-14\name_cut\isim_kesim_batch_2026-05-14_020808.dxf`
- SVG: `output\2026-05-14\name_cut\isim_kesim_batch_2026-05-14_020808.svg`
- PDF preview: `output\2026-05-14\name_cut\isim_kesim_preview_2026-05-14_020808.pdf`
- PNG preview: `output\2026-05-14\name_cut\isim_kesim_preview_2026-05-14_020808.png`
- Manifest: `output\2026-05-14\name_cut\name_cut_manifest_020808.json`

Otomatik doğrulamada:

- 50 isim yerleşti.
- Yerleşim stratejisi: `FIRST_FIT_SHELF_HEIGHT_DESC`
- Çakışma: yok.
- Çalışma alanı dışına taşma: yok.
- Text-to-path durumu: `OUTLINED_PATHS_WITH_FONTTOOLS`
- Kalınlaştırma/offset durumu: `TRUE_POLYGON_OFFSET_WITH_PYCLIPPER`
- Birincil RDWorks export: DXF
- RDWorks/lazer/direct print/yazıcı otomatik tetiklenmedi.

## RDWorks İçinde Açma

1. RDWorks'ü operatör manuel açar.
2. `name_cut` klasöründeki son DXF dosyasını manuel import eder.
3. RDWorks çalışma alanı ölçüsünü Cyzella manifestiyle karşılaştırır.
4. DXF import ölçeğinin 1:1 olduğunu kontrol eder.
5. Gerekirse RDWorks içinde ölçü doğrulama için bir isim bounding box'ı ölçülür.

Varsayılan çalışma alanı: 600 x 400 mm.

Manifest alanları: `work_area_width_mm`, `work_area_height_mm`, `margin_mm`, `spacing_x_mm`, `spacing_y_mm`.

## Layer / Renk Kontrolü

RDWorks renkleri işlem ayrımı için kullanır. Import sonrası şu layer/renk eşleşmeleri kontrol edilmeli:

| RDWorks Layer | Renk | Anlam |
|---|---|---|
| `CUT_NAME_OUTLINE` | Kırmızı | Ana isim kesim çizgisi |
| `CUT_SUPPORT_LINE` | Mavi | Alt destek çizgisi |
| `CUT_BACK_PLATE` | Mor | Taban / plaka çizgisi |
| `CALIBRATION` | Yeşil | Kalibrasyon / registration |
| `GUIDE_PREVIEW` | Gri | Kılavuz / bounding box |

Kabul:

- Ana kesim isimleri kırmızı layer altında görünür.
- Destek çizgisi varsa mavi layerdadır.
- Taban/plaka varsa mor layerdadır.
- Kılavuz çizgiler kesim layer'ı gibi ayarlanmamalıdır.

## Ölçü ve Yerleşim Kontrolü

Operatör RDWorks içinde şu maddeleri kontrol eder:

- Tüm isimler çalışma alanı içindedir.
- İsimler üst üste binmez.
- İsimler arasında güvenli boşluk vardır.
- İsimler satır satır ve fire azaltacak şekilde dizilmiştir.
- Sığmayan işler yeni plate/sayfaya alınmıştır.
- Ayna kesim modu gerekiyorsa yön doğru görünür.
- Her isim istenen yaklaşık genişlik/yükseklik değerindedir.
- Çok ince, kopuk veya okunaksız görünen contour yoktur.

## Path / Outline Kontrolü

Cyzella'nın hedefi isimleri text olarak değil path/curve/outline olarak üretmektir. Son doğrulanan hatta FontTools outline export geçmiştir.

RDWorks içinde yine şu kontrol yapılmalı:

- İsimler fonta bağımlı editable text gibi davranmamalı.
- İsimler contour/path olarak seçilebilir görünmelidir.
- Script harf bağlantıları kelime içinde kopuk olmamalıdır.
- Türkçe karakter noktaları ve işaretleri küçük ayrı parça riski açısından kontrol edilmelidir.
- Eğer RDWorks importu isimleri text/font olarak algılarsa üretime geçmeden önce object/path conversion yapılmalıdır.

## Kalınlaştırma / Offset Kontrolü

Son doğrulanan export hattında kalınlaştırma `pyclipper` ile gerçek polygon offset olarak manifestlenmiştir.

Kontrol:

- Hafif / Orta / Kalın / Özel offset ayarları beklenen görünüme yakın mı?
- İnce script bağlantıları malzemede kırılmayacak kadar kalın mı?
- Offset yüzünden harf iç boşlukları kapanmış mı?
- Alt destek çizgisi gerekiyorsa isimle doğru temas ediyor mu?
- Taban/plaka varsa isimle hizalı mı?

Gerçek kesimden önce küçük bir test parçası önerilir.

## Makine Parametreleri

Cyzella hız/güç/tekrar sayısı/air assist gibi makine parametrelerini üretim kararı olarak göndermez.

RDWorks içinde operatör şunları malzemeye göre manuel ayarlar:

- Kırmızı layer için kesim hızı/gücü.
- Mavi destek çizgisi için işlem tipi.
- Mor taban/plaka için kesim veya çizim tipi.
- Yeşil kalibrasyon layer'ının kesilip kesilmeyeceği.
- Gri kılavuz layer'ının kapalı veya non-output olması.

## Kesim Öncesi Zorunlu Mini Checklist

- [ ] DXF dosyası doğru klasörden açıldı.
- [ ] Çalışma alanı ölçüsü doğru.
- [ ] Import ölçeği 1:1.
- [ ] İsimler çalışma alanı dışına taşmıyor.
- [ ] İsimler üst üste binmiyor.
- [ ] Layer renkleri doğru.
- [ ] Kılavuz layer kesim ayarında değil.
- [ ] İsimler path/curve görünümünde.
- [ ] Offset/kalınlaştırma gerçek kesim için uygun.
- [ ] Türkçe karakter ve nokta riskleri kontrol edildi.
- [ ] Ayna kesim gerekiyorsa yön kontrol edildi.
- [ ] RDWorks preview/simulation temiz.
- [ ] Hız/güç ayarları operatör tarafından malzemeye göre yapıldı.
- [ ] Lazer başlatma kararı operatör tarafından manuel verilecek.

## Hata Durumları

| Durum | Yapılacak |
|---|---|
| İsimler text/font gibi açıldı | RDWorks içinde path/curve conversion yap; Cyzella manifestini kontrol et. |
| Ölçü yanlış görünüyor | Import scale ve çalışma alanını kontrol et; DXF'i yeniden export et. |
| Layer renkleri karıştı | DXF yerine SVG/PDF ile görsel kıyas yap; export tekrar alın. |
| İsimler üst üste biniyor | Cyzella'da çalışma alanı/gap ayarlarını artır; yeniden export et. |
| Offset çok kalın | Kalınlaştırmayı Hafif/Orta seviyeye düşür; yeniden export et. |
| Offset çok ince | Kalınlaştırmayı artır; küçük test kesimi yap. |
| Türkçe karakter küçük parça riski var | Alt destek veya taban plaka aç; yeniden export et. |

## Güvenlik Sınırı

Bu checklist kapsamında:

- RDWorks otomatik açılmaz.
- Lazer otomatik başlamaz.
- Yazıcı/direct print çalışmaz.
- CorelDRAW/Illustrator açılmaz.
- Kaynak AI/CDR dosyaları değiştirilmez.

## Son Karar

RDWorks isim kesim paketi otomatik testlerle hazırlanabilir durumdadır. Gerçek saha üretimi için RDWorks içinde bu checklist ile manuel import, layer, ölçü, path, offset ve makine ayarı kontrolü yapılmadan kesime geçilmemelidir.

