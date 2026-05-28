# 03 — Dry-Run Sonuçları

## Komut

```bash
python output/2026-05-28/trendyol_migration/migrate_trendyol_to_product_definitions.py \
       --dry-run \
       --output output/2026-05-28/trendyol_migration/dry_run_result.json
```

## Tam çıktı

```
[migration] dry_run=True total_active=36 success=36 skipped_existing=0 failed=0
[migration] sonuç yazıldı: output/2026-05-28/trendyol_migration/dry_run_result.json
```

## Counts (dry_run_result.json'dan)

```json
{
  "counts": {
    "success": 36,
    "skipped_existing": 0,
    "failed": 0
  },
  "total_source": 36,
  "total_active": 36
}
```

## Önizleme örnekleri (success listesinden)

### Sample 1: standart label_and_name_cut

```
SKU = TYB49VPP5GQP1SX780
product_name = Kız İsteme Çiçeği Ve Çikolata Kutusu Kişiye Özel Isimli Dama...
preview.name_config:
  type: couple
  count: 1
  size_group: auto
  compound_format: joined
  test_name: ''
preview.label_config:
  enabled: True
  model: '01'
  default_count: 10
  adjustable_in_production: True
  min_count: 1
  max_count: 50
```

### Sample 2: tek `name_cut`-only ürün (etiketsiz)

```
SKU = TYBDH9DAJH6GLWUH29
product_name = Kutulu Cam Çikolata Kız İsteme Çikolata Tepsisi ve 41li Lale...
preview.name_config:
  type: single
  count: 1
  size_group: auto
  compound_format: joined
preview.label_config:
  enabled: False
  model: ''
  default_count: 0
  adjustable_in_production: False
  min_count: 0
  max_count: 0
```

### Sample 3 (custom barcode formatı)

```
SKU = CYZELKLK624455
product_name = Kız İsteme Çikolatası 100 Adet, Söz Çikolatası, Nişan...
preview.name_config:
  type: couple, count: 1, size_group: auto
preview.label_config:
  enabled: True, model: '01', default_count: 10, min/max=1/50
```

## Schema validation (dry-run sırasında)

Her satır `normalize_definition` → `validate_definition(strict)` kapısından geçti. Sonuç:
- **36/36 validation PASS**
- Hata listesi: boş
- Skipped: 0 (product_definitions.json zaten boştu)

## Bypass + sahte success kontrol

Dry-run modu ne yapar:
- ✅ Hiçbir dosya yazmaz
- ✅ Audit log'a entry düşmez
- ✅ `product_definitions.json` dokunulmaz
- ✅ Her satırın validation sonucu net (success vs failed listelerine ayrılır)

Dry-run sonrası `data/product_definitions.json` boş kaldı (0 entry). Gerçek aktarım Step 4'te (`04_actual_migration.md`).

## Yorumlama

Tüm 36 satır:
- ASCII-temiz SKU'lar (barcode hep alfanumerik, validation rule tarafından kabul ediliyor)
- product_name dolu (rule: not empty — PASS)
- production_type mantıklı (label_and_name_cut/name_cut — bilinen iki kategori)
- model_key tutarlı (35x "01", 1x "")

Risk yok, gerçek aktarım güvenli.
