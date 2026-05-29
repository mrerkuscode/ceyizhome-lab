# Trendyol Mapping and AI Review Finalization Report

Date: 2026-05-16

## Summary

Trendyol sipariş entegrasyonunda ürün eşleştirme ve AI alan ayıklama güvenliği güçlendirildi. Eski `mucoxai1` projesi yalnızca okundu; hiçbir dosyası değiştirilmedi ve hiçbir secret/API değeri Cyzella deposuna kopyalanmadı.

Bu fazın ana kararı değişmedi: barcode/SKU eşleşmesi üretim kararında birincildir. AI sadece isim/tarih/not/adet önerisi üretir. Düşük güvenli ya da eşleşmeyen satırlar üretime otomatik alınmaz.

## Implemented

- Trendyol kullanıcı metinleri için Türkçe mojibake/bozuk karakter onarımı eklendi.
- `ayse`, `omer`, `mucahit`, `nisan`, `soz` gibi sık gelen ASCII/Türkçe eksik ad ve kelimeler güvenli biçimde Türkçeleştiriliyor.
- Trendyol AI extractor düşük güvenli öneriler için açık uyarı üretiyor.
- Backend düşük güvenli satırlara ikinci bir güvenlik uyarısı ekliyor: kullanıcı onayı olmadan üretime alınmaz.
- Trendyol Siparişleri UI filtrelerine `Düşük güven` filtresi eklendi.
- Düşük güvenli sipariş kartları amber tonlu, görsel olarak ayrıştırılmış state alıyor.
- Üretim Excel export akışı yalnızca `ready` satırları alıyor; review/low-confidence satırlar dışarıda kalıyor.
- `data/trendyol_settings.json` `.gitignore` içine alındı; yerel credential dosyası repo dışı tutuluyor.
- Yeni workflow doğrulama scripti eklendi:
  - `scripts/verify_trendyol_mapping_review_workflow.py`

## Old Project Reference

`C:\Users\Pc\Desktop\mucoxai1` projesinden sadece mimari davranış incelendi:

- Basic auth header mantığı.
- Supplier ID tabanlı User-Agent.
- V2 package + V1 enrichment yaklaşımı.
- Product/order normalization ve barcode/SKU merkezli eşleştirme fikri.

Taşınmayanlar:

- Secret/env değerleri.
- Prisma/Postgres mimarisi.
- Reklam, buybox, fiyat, stok veya otomasyon motorları.
- Eski proje dosyalarına yazma/değişiklik.

## Files Changed

- `src/intelligence/text_cleanup.py`
- `src/intelligence/trendyol_order_extractor.py`
- `src/webui_backend/trendyol_api.py`
- `src/webui_backend/trendyol_mapping_api.py`
- `src/webui/index.html`
- `src/webui/app.js`
- `src/webui/styles.css`
- `tests/test_trendyol_order_to_production.py`
- `scripts/verify_trendyol_mapping_review_workflow.py`
- `.gitignore`

## Tests Added / Updated

- Mojibake repair + low-confidence review test.
- UI hook test for `low_confidence` filter and low-confidence card class.
- Mapping review workflow script:
  - ready vs review split
  - mojibake repair
  - low-confidence warning
  - ready-only production Excel export
  - manifest safety flags

## Commands Passed

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m pytest tests\test_trendyol_order_to_production.py -q`
- `.venv\Scripts\python.exe scripts\verify_trendyol_mapping_review_workflow.py`

## Safety Confirmation

- Direct print remains disabled.
- RDWorks was not opened.
- Laser was not started.
- CorelDRAW / Illustrator were not opened.
- Old `mucoxai1` project was not modified.
- Trendyol credentials are not copied into tracked project files.

## Remaining Work

- Approve real Trendyol barcode/SKU mappings from the generated review workbook.
- Re-sync live Trendyol orders after mappings are approved.
- Run one real mapped Trendyol order through: Customer Order -> Studio -> PDF/PNG -> Queue.
- Keep Trendyol Questions HTTP 556 isolated; it does not block order sync.
