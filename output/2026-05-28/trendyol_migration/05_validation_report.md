# 05 — Validation Raporu

## Schema validation pipeline

Her satır şu zincirden geçer:
1. `normalize_definition(payload, prior=None)` — type coercion, default'lar, prior `created_date` koruma
2. `validate_definition(project_root, normalized)` — alan-bazlı kurallar + JSON Schema Draft 2020-12

## Validation kuralları (uygulandı)

| Kural | Sonuç (36/36) |
|---|---|
| SKU boş olmamalı | 36 PASS |
| product_name boş olmamalı | 36 PASS |
| type ∈ {single, couple, none} | 36 PASS |
| type=single/couple → count ≥ 1 | 36 PASS (hep 1) |
| type=none → count = 0 | 0 satır, n/a |
| label.enabled=True → model zorunlu | 35 PASS (model="01") |
| label.enabled=False → model boş olabilir | 1 PASS |
| min ≤ default ≤ max | 36 PASS (1 ≤ 10 ≤ 50 etiketli için; 0/0/0 etiketsiz için) |
| JSON Schema strict additional fields | 36 PASS |

## 36 satır detay tablosu

| # | SKU | product_name (kırpılmış) | name_type | label_enabled | model | Validation |
|---|---|---|---|---|---|---|
| 1 | TYBDH9DAJH6GLWUH29 | Kutulu Cam Çikolata Kız İsteme… | single | False | (none) | ✅ |
| 2 | TYB49VPP5GQP1SX780 | Kız İsteme Çiçeği Ve Çikolata Kutusu… | couple | True | 01 | ✅ |
| 3 | CYZELKLK624455 | Kız İsteme Çikolatası 100 Adet… | couple | True | 01 | ✅ |
| 4 | CYZSELLAKJ56612 | Kişiye Özel İki Katlı Sunumluk Beyaz Tül… | couple | True | 01 | ✅ |
| 5 | cyzella6612365612 | Kişiye Özel Çift Katlı Sunumluk Tül… | couple | True | 01 | ✅ |
| 6-36 | ... (31 ek satır) | ... | couple | True | 01 | ✅ |

Detay liste `actual_result.json` (success array) içinde 36 entry olarak hazır.

## Hata olmadı

Bu sprintte hatalı satır gelmedi. Gelseydi script şöyle raporlardı:

```json
{
  "failed": [
    {
      "index": 7,
      "sku": "BAD-EXAMPLE",
      "product_name": "...",
      "errors": ["Ürün adı boş olamaz.", "Etiket aktif ise model seçilmeli."]
    }
  ],
  "counts": { "success": 35, "failed": 1, "skipped_existing": 0 }
}
```

## Re-validation kontrolü (migration sonrası)

Migration tamamlandıktan sonra `product_definitions.json`'daki **36 entry yeniden validation'dan geçirildi**. Her biri PASS — yani aktarıldıktan sonra `data/product_definitions.json` içeriği zaten geçerli (schema entegrity korunmuş).

## Bridge'den çağırılabilir mi

Yeni `productDefinitionsList(include_archived=false)` slot 36 entry döner. UI:
- Toplam: 36
- Aktif: 36
- Couple: 35, Single: 1, None: 0
- Etiketli: 35

`Ürün Tanımları` sayfası açıldığında bu 36 entry tablo halinde görünür, her birinin "Düzenle" + "Arşivle" butonu çalışır.
