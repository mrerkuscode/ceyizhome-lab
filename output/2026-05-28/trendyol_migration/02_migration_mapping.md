# 02 — Migration Mapping (Eski → Yeni Şema)

## Field-by-field dönüşüm

| Eski alan | Yeni alan | Dönüşüm kuralı |
|---|---|---|
| `barcode` | `sku` | Birebir |
| `barcode` | `trendyol_sku` | Birebir (default identity) |
| `product_name` | `product_name` | Birebir, strip |
| `production_type` | `name_config.type` | label_and_name_cut → couple; name_cut → single; label → none; aksi → single |
| (yok) | `name_config.count` | Default **1** (none ise 0) |
| (yok) | `name_config.size_group` | Default **`auto`** |
| (yok) | `name_config.compound_format` | Default **`joined`** |
| (yok) | `name_config.test_name` | "" (boş, Leyla doldurur) |
| `production_type` | `label_config.enabled` | "label" substring varsa True |
| `model_key` veya `model_name` | `label_config.model` | model_key tercih edilir |
| (yok) | `label_config.default_count` | Default **10** (etiketli) / 0 (etiketsiz) |
| (yok) | `label_config.adjustable_in_production` | Default **True** (etiketli) / False (etiketsiz) |
| (yok) | `label_config.min_count` | Default **1** (etiketli) / 0 |
| (yok) | `label_config.max_count` | Default **50** (etiketli) / 0 |
| (yok) | `extras.special_requests_allowed` | Default **True** |
| `name_cut_style`, `name_cut_width_mm`, `created_at`, `merchant_sku`, `stock_code`, `production_type` | `extras.production_notes` | Birleştirilmiş açıklama notu |
| (yok) | `metadata.source` | `"trendyol_mapping_migration_2026-05-28"` |
| (yok) | `metadata.status` | `"active"` |
| (yok) | `metadata.created_date` | `_now_iso()` |
| `image_url`, `model_path`, `quantity_source`, `default_date_text`, `default_note_text`, `active`, `updated_at` | (atlandı) | Yeni şema kullanmıyor; image_url eski sistemde kalıyor, model_path zaten model_key ile temsil ediliyor |

## Default kuralı: name_config.type

```
if production_type == "name_cut":           # sadece isim kesim
    name_type = "single"
elif "label_and_name_cut" in production_type:
    name_type = "couple"                     # söz çikolatası varsayımı
elif production_type == "label":             # sadece etiket
    name_type = "none"
else:
    name_type = "single"                     # fallback
```

**Neden couple default?** Mevcut 35/36 satır `label_and_name_cut`. Söz çikolatası setleri genelde çift isim (gelin & damat) için sipariş edilir. Leyla farklı bir kategori için (örneğin doğum günü tek isim) UI'dan değiştirebilir.

## Default kuralı: label_config

Etiket etkin mi: `production_type` içinde "label" geçiyor mu?

| production_type | label.enabled | label.model | default_count | min/max | adjustable |
|---|---|---|---|---|---|
| `label_and_name_cut` | True | `model_key` ("01") | 10 | 1 / 50 | True |
| `name_cut` | False | "" | 0 | 0 / 0 | False |
| `label` | True | model_key | 10 | 1 / 50 | True |

## production_notes formatı (örnek)

Bir satır için (label_and_name_cut + model_name="01 A Gold Rulo Etiket"):

```
Eski etiket model: 01 A Gold Rulo Etiket (01)
Trendyol mapping'den aktarıldı (production_type=label_and_name_cut, name_cut_width_mm=300.0, created=2026-05-19 23:04:50).
DEFAULT değerler — Leyla düzenleyebilir.
```

Bir satır için (name_cut-only + merchant_sku boş):

```
Trendyol mapping'den aktarıldı (production_type=name_cut, name_cut_width_mm=300.0, created=2026-05-19 23:04:50).
DEFAULT değerler — Leyla düzenleyebilir.
```

## Eksik alanlar (Leyla'nın sonra düzeltmesi gerekenler)

Migration sonrası **her ürünün varsayılan değerleri vardır**, ama Leyla'nın "gerçek bilgi" girmesi gerekebilecek alanlar:

| Alan | Migration default | Gerçek değer Leyla'da |
|---|---|---|
| `name_config.count` | 1 | 1, 2, 3 olabilir (kaç isim) |
| `name_config.size_group` | auto | manuel 70x40 / 80x40 / 100x40 |
| `name_config.compound_format` | joined | tek dosya mı yan yana mı |
| `name_config.test_name` | "" | DXF lookup için tipik isim |
| `label_config.default_count` | 10 | Gerçek tipik adet (5? 20?) |
| `label_config.min/max_count` | 1 / 50 | Daha dar aralık genelde gerçekçi |

Leyla "Ürün Tanımları" sayfasında her birini açıp düzenleyebilir; **gerek olmazsa olduğu gibi bırakabilir**.

## Atlanan eski alanlar (yeni şemaya gerek yok)

- `image_url` — eski sistem mapping'inde kalıyor; yeni Ürün Tanım sistemi UI'ı görsel göstermiyor
- `model_path` — `model_key` ile yeterli (frontend mapping)
- `name_cut_style` — eski jeneratif algoritma flag'i (Mochary Personal Use Only), yeni DXF mimari bunu kullanmıyor
- `name_cut_width_mm` — fixed 300mm değer, yeni mimari bbox'tan hesaplıyor
- `quantity_source` — hep "line_quantity"; yeni sistem `label_config.default_count` üzerinden yönetir
- `default_date_text`, `default_note_text` — boş zaten
- `active` — yeni sistemde `metadata.status="active"` karşılığı

## Veri kaybı yok

Eski mapping JSON'ı dokunulmadı. Eğer yeni sistem geçişi reversible isteniyorsa, eski dosya orjinal şekilde duruyor (sample backup `backups/trendyol_product_mappings.json.bak`).
