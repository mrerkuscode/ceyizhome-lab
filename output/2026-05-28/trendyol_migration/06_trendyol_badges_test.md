# 06 — Trendyol Sayfası Rozet Testi

## Yöntem

Frontend `productDefinitionForOrder(row)` ile aynı mantığı Python'da çalıştırarak `data/trendyol_questions_context.json` (522 satır) üzerinde rozet dağılımı sayıldı. Tanımlı SKU listesi `data/product_definitions.json` (migrasyon sonrası 36 entry).

## Sonuçlar (522 question_context satırı)

| Rozet | Satır | Unique sipariş | Unique barcode |
|---|---|---|---|
| 🟢 **Tanımlı** | 73 (%13) | 32 | 2 |
| 🟡 **Eksik** | 449 (%86) | 183 | 8 |
| 🔴 **Bilinmiyor** | 0 (%0) | 0 | — |

## Yorum

- 36 SKU aktarıldı ama Trendyol soru/mesaj verisinde **sadece 10 unique barcode** geçiyor (önceki Discovery raporundan da bilinen sayı)
- Bu 10 barcode'un **2'si** migration sonrası tanımlı set içinde (`CYZOHMELKJK612` ve benzeri)
- **8 barcode tanımsız** kalıyor — bunlar Trendyol'dan gelmiş ama eski mapping listesinde yokmuş

## Tanımsız 8 barcode (Leyla'nın tanımlaması gerekenler)

Soru satırlarında geçenler:
- `CYZELLAKJ5K12355123` — 41 Karışık şakayık isteme çiçeği & 100 adet söz çikolata
- (8 - 1 = 7 diğer barkod — `badge_scan_result.json`'da detay)

## Operatör akışı (Leyla için)

1. Trendyol Siparişleri sayfasını aç
2. Her sipariş kartında rozet görünür:
   - 🟢 Tanımlı (CYZOHMELKJK612 vs.) — devam edebilir
   - 🟡 Eksik (CYZELLAKJ5K12355123 vs.) — tıkla
3. 🟡 rozet tıklayınca: Ürün Tanımları sayfasına yönlendirilir; SKU + ürün adı otomatik doldurulur (`openProductEditorForSku()`)
4. Leyla name_config + label_config defaultlarını gözden geçirir → Kaydet
5. Trendyol sayfasına geri döner → o sipariş artık 🟢 Tanımlı

## Frontend kod doğrulaması

`src/webui/app.js`'de:
- `productDefinitionForOrder(row)` — barcode, merchant_sku, stock_code, trendyol_sku, sku adaylarını sırayla cache'te arar; ilk match → defined; hiç aday yok → unknown; aday var ama match yok → missing
- `trendyolProductBadge(row)` — `<span class="trendyol-product-badge {defined|missing|unknown}">` render eder
- `openProductEditorForSku(sku, productName)` — deep-link
- `loadProductDefinitions()` SKU set'ini cache'liyor (boot anında bir kez + her sayfa açılışında)
- Trendyol sayfası açılınca `loadProductDefinitions()` re-fetch yapar ki rozetler taze olsun

## Sahte başarı yok kontrolleri

- ✅ Sayım gerçek (522 satır iterate edildi, her birinin barcode/merchant_sku/stock_code'una bakıldı)
- ✅ Cache `defined_skus` set'i migration sonrası 36 SKU içeriyor
- ✅ Trendyol sipariş satırlarına dokunulmadı (read-only iterate)
- ✅ Rozet kararı `defined_skus.contains()` ile O(1) match — boş SKU "unknown" olarak işaretlenir, hiç "fake defined" durumu yok

## Üretim suggestion satırları (3 satır) — özel kontrol

| Customer | barcode | Rozet |
|---|---|---|
| Ayşe & Mehmet | (boş) | unknown (eski test fixture, gerçek Trendyol sipariş değil) |
| Helin Cemal | (boş) | unknown |
| Model Eksik | (boş) | unknown |

Üretim suggestion'lar eski Phase 18 test fixture'ları, gerçek müşteri verisi değil. Rozet kontrolü için question_context (522 satır) daha temsil edici.

## Kanıt

`output/2026-05-28/trendyol_migration/badge_scan_result.json` — tam dağılım + sample SKU'lar.
