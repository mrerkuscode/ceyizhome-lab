# RDWORKS REAL IMPORT FIELD CHECKLIST REPORT

Tarih: 2026-05-14

## Kısa Karar

RDWorks gerçek saha import kontrolü için ayrı ve uygulanabilir bir operatör checklist'i oluşturuldu. Bu dosya, Cyzella'nın hazırladığı DXF/SVG/PDF/PNG/manifest paketinin RDWorks içinde manuel açıldıktan sonra nasıl kontrol edileceğini adım adım tarif eder.

## Oluşturulan Dosya

- `RDWORKS_REAL_IMPORT_FIELD_CHECKLIST.md`

## Kapsam

Checklist şu başlıkları kapsar:

- RDWorks içinde DXF dosyasını manuel açma.
- Çalışma alanı ve import ölçeği kontrolü.
- Layer/renk kontrolü.
- Ölçü ve yerleşim kontrolü.
- Text-to-path / outline kontrolü.
- Kalınlaştırma / offset kontrolü.
- Makine parametrelerinin operatör tarafından manuel ayarlanması.
- Kesim öncesi mini checklist.
- Hata durumları ve güvenli çözüm adımları.

## Teknik Manuel Bağlantısı

`TECHNICAL_MANUAL.md` içine gerçek RDWorks saha kontrolü için bu checklist'in kullanılacağı notu eklendi.

## Release Paketi

`scripts/build_release_package.py` ve `scripts/verify_release_package.py` güncellendi. Checklist artık kaynakta varsa release paketine kopyalanır ve paket doğrulaması bunu kontrol eder.

## Güvenlik Teyidi

- RDWorks otomatik açılmaz.
- Lazer otomatik başlamaz.
- Yazıcı/direct print çalışmaz.
- CorelDRAW/Illustrator açılmaz.
- Kaynak AI/CDR dosyaları değiştirilmez.
- Cyzella hız/güç parametresi göndermez; RDWorks layer hız/güç kararları operatöre aittir.

## Kalan Risk

Gerçek makine üretimi hâlâ saha operatörü tarafından RDWorks içinde manuel doğrulama gerektirir. Bu bilinçli güvenlik sınırıdır.

