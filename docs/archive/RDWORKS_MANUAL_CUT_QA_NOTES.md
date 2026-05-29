# RDWorks Manual Cut QA Notes

Tarih: 2026-05-13

## Kısa Karar

RDWorks isim kesim paketi yeniden üretildi ve otomatik testten geçti. Dosyalar RDWorks/lazer otomasyonu başlatmadan hazırlandı. Gerçek kesim öncesi operatör RDWorks içinde dosyayı manuel açıp layer, ölçü, path ve offset görünümünü kontrol etmelidir.

## Son Üretilen Paket

- Birincil DXF: `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_232320.dxf`
- SVG: `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_232320.svg`
- PDF preview: `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_232320.pdf`
- PNG preview: `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_232320.png`
- Manifest: `output/2026-05-13/name_cut/name_cut_manifest_232320.json`

## Otomatik Doğrulama Sonucu

Komut:

```powershell
.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py
```

Sonuç: PASSED

Özet:

- Toplam isim: 50
- Toplam adet: 50
- Çalışma alanı: 600 x 400 mm
- Plate / sayfa sayısı: 6
- Kullanılan alan: %50.1
- Fire / boş alan: %49.9
- Text-to-path durumu: `OUTLINED_PATHS_WITH_FONTTOOLS`
- Kalınlaştırma durumu: `TRUE_POLYGON_OFFSET_WITH_PYCLIPPER`
- RDWorks otomatik açıldı mı: hayır
- Lazer başladı mı: hayır
- Direct print aktif mi: hayır
- Yazıcı otomatik çalıştı mı: hayır

## RDWorks İçinde Manuel Kontrol Listesi

1. DXF dosyasını RDWorks içinde manuel aç.
2. Çalışma alanı ölçüsünü 600 x 400 mm olarak kontrol et.
3. İsimlerin çalışma alanı dışına taşmadığını kontrol et.
4. İsimlerin üst üste binmediğini kontrol et.
5. Kelimeler arası boşluğun okunur olduğunu kontrol et.
6. Script/outline görünümünde bozuk harf veya kopuk contour olmadığını kontrol et.
7. Offset/kalınlaştırma görünümünü gerçek kesime uygunluk açısından kontrol et.
8. Renk/layer ayrımını kontrol et:
   - Kırmızı: ana isim kesim çizgisi
   - Mavi: destek çizgisi
   - Mor: taban/plaka
   - Yeşil: kalibrasyon
   - Gri: kılavuz/bounding box
9. RDWorks layer speed/power değerlerini makine ve malzemeye göre operatör ayarlasın.
10. Önizleme ve simülasyon RDWorks içinde kontrol edilmeden kesime başlanmasın.

## Operatör Notları

- Cyzella hız/güç parametresi göndermeyi üretim kararı olarak yapmaz; layer renklerini düzenli hazırlar.
- DXF birincil exporttur. SVG ara/ek export olarak kalır.
- PDF/PNG dosyaları sadece görsel kontrol içindir.
- Manifest teknik üretim kaydıdır; normal kullanıcıya gösterilmez.

## Güvenlik

Bu QA sırasında:

- RDWorks otomatik açılmadı.
- Lazer otomatik başlamadı.
- Yazıcı otomatik çalışmadı.
- Direct print aktif edilmedi.
- CorelDRAW/Illustrator açılmadı.
- Kaynak AI/CDR dosyaları değiştirilmedi.

## Kalan Manuel Karar

Gerçek malzeme, makine gücü, hız, odak, ayna kesim yönü ve layer işlem parametreleri operatör tarafından RDWorks içinde belirlenmelidir. Bu kararlar Cyzella tarafından otomatik verilmez.

## Son Karar

RDWorks manuel kesim QA notları tamamlandı. Dosya paketi hazırdır; gerçek kesim öncesi RDWorks içinde manuel kontrol gereklidir.
