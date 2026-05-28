# Production Safety Rules

## Değişmez Kurallar

- Yazıcı otomatik başlamaz.
- Lazer otomatik başlamaz.
- RDWorks otomatik başlamaz.
- Trendyol canlı statü, kargo ve fatura işlemleri otomatik tetiklenmez.
- Sahte success gösterilmez.
- Gerçek çıktı dosyası yoksa kayıt çıktı hazır veya yazdırmaya hazır sayılmaz.
- API secret log, audit, export veya screenshot içine düz metin düşmez.

## Queue Güvenliği

Yazdırma Sırası item'ları source/source_label standardı taşımalıdır. Duplicate kayıtlar engellenmeli, blocked veya output_missing durumları operatöre açık gösterilmelidir.

## İsim Kesim Güvenliği

Tek parça/weld kontrolünden geçmeyen, detached mark içeren veya collision riski olan kayıt export edilemez. `needs_offset` kayıtları operatör onayı olmadan export edilemez.

## Trendyol Güvenliği

Kişiselleştirme alanı kanıt olmadan uydurulmaz. Ürün başlığından isim/tarih/not/lazer isim çıkarımı kesin veri gibi kullanılmaz. Belirsiz veri `needs_review` kalır.

## Backup Güvenliği

Path traversal engellenir. Corrupt JSON restore edilmez. Restore öncesi otomatik snapshot alınır.

## Canlı Entegrasyon Hazırlığı

Riskli aksiyon registry default disabled ve dry-run only olmalıdır. Yönetici ve operatör onayı olmadan canlı aksiyon yapılamaz.
