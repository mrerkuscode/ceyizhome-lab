# 03 — Yeni Ürün Tanım Sistemi (Bölüm C, v2.0)

## Konum

- Veri: `data/product_definitions.json` (0 aktif satır), `data/product_definitions_schema.json` (JSON Schema 2020-12)
- Audit: `data/product_definitions_audit_log.jsonl` (post-cleanup boş)
- Backend: `src/webui_backend/product_definitions_api.py` (654 satır, 27 KB)
- UI: Sol menü → "Ürün Tanımları" (yeni section `<section id="products">`)

Sample: `11_data_samples/product_definitions_full.json` (boş hâl)

## Durum

**Sistem kuruldu, veri boş.** Bu bilinçli: sprint hedefi infrastrüktür idi, veri girişi Leyla'nın ödevi.

## Şema özeti

```json
{
  "<SKU>": {
    "sku": "TRY-12345",
    "trendyol_sku": "TRY-12345",
    "product_name": "10 kişilik söz çikolatası seti",
    "name_config": {
      "type": "couple|single|none",
      "count": 1,
      "size_group": "auto|70x40|80x40|100x40",
      "compound_format": "joined|side_by_side",
      "test_name": "Ayşe & Mehmet"
    },
    "label_config": {
      "enabled": true,
      "model": "soz_3",
      "default_count": 10,
      "adjustable_in_production": true,
      "min_count": 5,
      "max_count": 20
    },
    "extras": {
      "special_requests_allowed": true,
      "production_notes": ""
    },
    "metadata": {
      "created_date": "...",
      "modified_date": "...",
      "usage_count": 0,
      "status": "active|archived",
      "archived_date": "",
      "source": "manual_create|manual_edit|excel_import"
    }
  }
}
```

## Backend slot'ları (`bridge.py` — 9 slot)

| Slot | Görev |
|---|---|
| `productDefinitionsList(include_archived=false)` | Liste + summary |
| `productDefinitionGet(sku)` | Tek + size_group resolution |
| `productDefinitionsSearch(query)` | SKU + product_name substring |
| `productDefinitionSave(payload_json)` | Upsert + validation |
| `productDefinitionArchive(sku)` | Soft delete (`metadata.status=archived`) |
| `productDefinitionRestore(sku)` | Aktif et |
| `productDefinitionsImportExcel(file_path, dry_run)` | Excel toplu |
| `productDefinitionResolveSizeGroup(payload_json)` | Auto size + DXF lookup |
| `productDefinitionIncrementUsage(sku)` | Kullanım sayacı |

## Validation (sahte success YOK)

Hem alan-bazlı (Python) hem JSON Schema 2020-12 iki katmanlı kontrol:
- SKU boş olamaz
- Ürün adı boş olamaz
- type ∈ {single, couple, none}
- type=none → count=0; type ∈ {single, couple} → count ≥ 1
- label.enabled=true → model zorunlu + default_count zorunlu
- min ≤ default ≤ max

Validation hata varsa `status="VALIDATION_ERROR"`, dosya yazılmaz, audit yazılmaz, frontend hata listesini gösterir.

## DXF library entegrasyonu

`product_definitions_api.resolve_size_group`:
- Auto size_group: harf sayısına göre 70/80/100x40 (`size_group_for_letter_count`)
- DXF library lookup: `test_name` → `to_ascii_name` → `find_library_entry`
- UI'da canlı preview: yeşil ✓ "kütüphanede bulundu" veya kırmızı ✗ "Leyla bu ismi çizmeli"

## Trendyol entegrasyonu

`trendyolProductBadge(row)` her sipariş kartında:
- 🟢 **Tanımlı** — barcode/merchant_sku/stock_code üründe var
- 🟡 **Eksik** — SKU var ama tanım yok, tıklayınca Ürün Tanımları'na yönlendirir, SKU pre-filled
- 🔴 **Bilinmiyor** — sipariş satırında hiç SKU yok

Boot anında bir kez `loadProductDefinitions()` çağrılır (cache warm).

## Excel import

Zorunlu kolonlar: `SKU, ProductName, NameType, NameCount, LabelEnabled, LabelModel, LabelCount`
Opsiyonel: `SizeGroup, CompoundFormat, AdjustableInProduction, MinCount, MaxCount, ProductionNotes, TestName`

Test dosyası: `output/2026-05-28/product_definitions_system/proofs/test_products.xlsx`

Akış: dry-run (önce) → preview → gerçek import. Hatalı satır atlanır, errors listesine yazılır, başarılı satırlar upsert.

## Soft delete

Asla satır silmez. Archive sadece `metadata.status="archived"` set eder + `archived_date` damgalar. UI'da "Arşiv dahil" checkbox açıkken görünür (soluk renkte).

## Audit log

`data/product_definitions_audit_log.jsonl` — her CRUD operasyonu append:
```json
{"at":"...","action":"create|update|archive|restore|excel_import","sku":"...","details":{...}}
```

Audit yazımı best-effort: hata atarsa CRUD operasyonu yine başarılı (audit ≠ blocking).

## Test sonucu

`output/2026-05-28/product_definitions_system/proofs/regression_test.py` — 6 senaryo + sahte success kontrol + regression:
- 16/16 PASS
- Validation reddi `VALIDATION_ERROR` döndürüyor (sahte success yok)
- Audit log her CRUD'a entry düşüyor
- 167 SVG ref korundu, DXF library 2 entry korundu, Trendyol approved row 1 korundu

## Veri Hacmi

- Aktif tanım: **0**
- Arşivli: 0
- Toplam: 0
- Son güncel: 2026-05-28T15:39:44 (oluşturma damgası)
- Dolu / boş: **boş** (yeni kurulan sistem)

## Bilinmeyen / test edilemedi

- Leyla 500 isim çizecek demişti — bu sistemde 500 ürün tanımı mı yoksa 50-100 mü olacak (1 isim ≠ 1 ürün)
- Compound name varyantları (joined vs side_by_side) gerçek üretimde ne kadar kullanılacak
- `usage_count` artık otomatik artıyor mu (Trendyol order processing entegrasyonu yapılmadı, sadece slot var)

## Risk / Uyarı

- 🟡 **Boş veri tabanı**: Production'a çıkmadan önce min. 20-50 SKU tanımı zorunlu, aksi halde Trendyol siparişleri 🟡 Eksik birikecek
- 🟢 Şema strict, validation iki katmanlı → veri kalitesi yüksek olacak
- 🟢 Soft delete: veri kaybı yok
- 🟡 Eksik Tanımlar bulk sayfası UI'da yok (sadece Trendyol satırlarında rozet var); operatör 100+ eksik için tek tık tanımlamak yerine bulk listesinden bakmak isteyebilir
- 🟡 Boot-time cache warm: `initBridge` callback'inde `loadProductDefinitions()` çağrısı var; rozet anında doğru görünür ama 500+ tanım olursa boot biraz yavaşlayabilir (~50-100ms)
