# 01 — Eski Sistem Analizi

## `data/trendyol_product_mappings.json` — 36 onaylı satır

### Alanlar (sorgulanan)

```
all_keys = ['active', 'barcode', 'created_at', 'default_date_text', 'default_note_text',
            'image_url', 'merchant_sku', 'model_key', 'model_name', 'model_path',
            'name_cut_style', 'name_cut_width_mm', 'product_name', 'production_type',
            'quantity_source', 'stock_code', 'updated_at']
```

### Alan-bazlı istatistik (36 satır)

| Alan | Doluluk | Distinct | Sample |
|---|---|---|---|
| `active` | 36/36 | 1 (`True`) | True |
| `barcode` | 36/36 | 36 unique | TYBDH9DAJH6GLWUH29 |
| `created_at` | 36/36 | 9 | 2026-05-19 23:04:50 |
| `default_date_text` | 0/36 | 1 (boş) | "" |
| `default_note_text` | 0/36 | 1 (boş) | "" |
| `image_url` | 36/36 | 36 | https://cdn.dsmcdn.com/... |
| `merchant_sku` | 10/36 | 11 | (boş veya "merchantSku") |
| `model_key` | 35/36 | 2 | "01" |
| `model_name` | 35/36 | 2 | "01 A Gold Rulo Etiket" |
| `model_path` | 35/36 | 2 | templates/designs/... |
| `name_cut_style` | 36/36 | 1 | "Mochary Personal Use Only" |
| `name_cut_width_mm` | 36/36 | 1 | 300.0 |
| `product_name` | 36/36 | 36 | Kız İsteme/Söz çikolatası vs. |
| `production_type` | 36/36 | **2** | label_and_name_cut (35) / name_cut (1) |
| `quantity_source` | 36/36 | 1 | line_quantity |
| `stock_code` | 10/36 | 11 | (boş veya "merchantSku") |
| `updated_at` | 36/36 | 9 | 2026-05-19 23:04:50 |

### Production_type × model_key dağılımı

| production_type | model_key | model_name | Sayı |
|---|---|---|---|
| `label_and_name_cut` | `01` | `01 A Gold Rulo Etiket` | 35 |
| `name_cut` | `''` (boş) | `''` | 1 |

**Yorum:** 35 ürün hem etiket hem isim kesim, hep aynı model (`01 A Gold Rulo Etiket`). 1 ürün sadece isim kesim (etiketsiz).

### Önemli gözlem

- **Hepsi `active=True`** — 36/36 onaylı
- **`name_cut_width_mm: 300.0` hep aynı** — eski sistem fixed bir kesim genişliği kullanıyor
- **`name_cut_style: "Mochary Personal Use Only"` hep aynı** — tek font/style
- **`merchant_sku` 10/36 satırda dolu** ama değerlerin yarısı "merchantSku" placeholder gibi
- `default_date_text` ve `default_note_text` hep boş — bu alanlar eski sistemde teorik olarak vardı ama hiç kullanılmadı

### Migration için ne anlam ifade ediyor?

1. **SKU = barcode**: Trendyol barcode'u unique. `barcode` field'i yeni sistemin `sku` ve `trendyol_sku` alanlarına geçer.
2. **production_type → name_config.type inference**:
   - `label_and_name_cut` → couple (default — söz çikolataları çoğu çift isim için)
   - `name_cut` → single (default)
   - Leyla sonra düzeltebilir (örneğin tek/3'lü)
3. **model_key → label_config.model**: "01" değerli model_key var, bunu doğrudan label_config.model alanına geçiriyoruz.
4. **label_config.default_count**: Eski sistemde adet bilgisi yok. Default 10 (operatör düzeltir).
5. **name_cut_width_mm, name_cut_style**: Yeni sistem bunları kullanmıyor (yeni mimari DXF kütüphane). Bilgi `extras.production_notes`'a yazıldı.
6. **default_date_text/note_text**: Boş hep, geçiş yok.
7. **created_at**: `metadata.created_date` olarak korunmuyor (yeni sistemde her create _now() damgalanır), ama notlara yazıldı (`Trendyol mapping'den aktarıldı ... created=...`).

## `data/trendyol_mapping_suggestions.json` — 332 öneri (DOKUNULMADI)

Bu sprint kapsamı dışında. Özet bilgi:
- Tümü `status="needs_review"` (operatör onaylamamış)
- 327 `production_type=label` (sadece etiket)
- 3 `production_type=label_and_name_cut`
- 2 `production_type=review`
- 332 unique barcode (her satır ayrı ürün)

Gelecekteki sprint: 332 öneriden operatör onaylanları yeni Ürün Tanım sistemine de aktarılabilir. Bu sprintte sadece 36 onaylı işlendi.
