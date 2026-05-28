# Release Notes

## CeyizHome Lab Production Release Candidate

Bu release adayı; Toplu Üretim, Trendyol read-only import, Etiket Studio, Yazdırma Sırası, İsim Kesim, Üretim Geçmişi, Backup/Restore ve final UI navigation polish fazlarını içerir.

## Öne Çıkanlar

- Yazdırma Sırası source/source_label standardı ve güvenli print hazırlığı güçlendirildi.
- Toplu Üretim Studio kaynak kartları, kolon eşleştirme, galeri, hata paneli, queue entegrasyonu ve performans davranışı tamamlandı.
- Trendyol read-only sync, kanıtlı kişiselleştirme ve operatör düzeltme akışı eklendi.
- İsim Kesim queue persistence, tek parça kalite kontrolü, export manifest ve RDWorks uyumluluk QA güçlendirildi.
- Üretim Geçmişi audit merkezi, CSV/JSON export ve deep-link navigasyonu eklendi.
- Yazıcı profilleri ve manuel print hazırlığı guard altına alındı.
- Backup/restore veri bakım ekranı eklendi.
- Sol menü collapsed hover, pinned state ve navigation active state düzeltildi.

## Güvenlik

Bu release canlı yazıcı, lazer, RDWorks veya Trendyol marketplace işlemi otomatik tetiklemez. Riskli entegrasyonlar disabled/dry-run/manual guard altındadır.

## Final Test

Final release gate:

```powershell
python scripts/production_final_regression_release_phase27_gate.py
```
