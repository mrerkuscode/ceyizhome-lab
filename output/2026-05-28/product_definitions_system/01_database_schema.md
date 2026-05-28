# 01 — Database Schema

## Dosyalar

- `data/product_definitions.json` — kütüphane (UI tarafından sürekli güncellenir)
- `data/product_definitions_schema.json` — JSON Schema Draft 2020-12 (validation kaynağı)
- `data/product_definitions_audit_log.jsonl` — append-only log (her CRUD)

## Şema (product_definitions.json)

```json
{
  "version": "2.0",
  "last_updated": "2026-05-28T...",
  "total_count": 0,
  "definitions": {
    "<SKU>": {
      "sku": "TRY-12345",
      "trendyol_sku": "TRY-12345",
      "product_name": "10 kişilik söz çikolatası seti",
      "name_config": {
        "type": "couple",            // single | couple | none
        "count": 1,                   // 0..10
        "size_group": "auto",         // auto | 70x40 | 80x40 | 100x40
        "compound_format": "joined",  // joined | side_by_side
        "test_name": "Ayşe & Mehmet"  // opsiyonel; DXF lookup için
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
        "created_date": "2026-05-28T...",
        "modified_date": "2026-05-28T...",
        "usage_count": 0,
        "status": "active",            // active | archived
        "archived_date": "",
        "source": "manual_create"      // manual_create | manual_edit | excel_import
      }
    }
  }
}
```

## Validation kuralları

Hem alan-bazlı hem JSON Schema iki katmanlı kontrol:

| Kural | Hata mesajı |
|---|---|
| SKU boş | "SKU boş olamaz." |
| Ürün adı boş | "Ürün adı boş olamaz." |
| type=single/couple ile count<1 | "İsim tipi 'tek' veya 'çift' ise adet en az 1 olmalı." |
| type=none ile count≠0 | "İsim tipi 'yok' ise adet 0 olmalı." |
| label.enabled + model boş | "Etiket aktif ise model seçilmeli." |
| min > max | "Etiket min_count, max_count'tan büyük olamaz." |
| default ∉ [min, max] | "Etiket varsayılan adet [min, max] aralığında olmalı." |
| size_group ∉ {auto, 70x40, 80x40, 100x40} | normalize edilir → auto |
| compound_format ∉ {joined, side_by_side} | normalize edilir → joined |
| type ∉ {single, couple, none} | normalize edilir → single |

## ASCII normalizasyon

Test ismi → DXF lookup için `to_ascii_name()` (DXF library modülünden yeniden kullanıldı):

| Girdi | Çıktı |
|---|---|
| Mücahit | mucahit |
| Ayşe & Mehmet | ayse_mehmet |
| Yusuf Kerem | yusuf_kerem |
| Çağrı-Han | cagri_han |

Bu sayede ürün tanımındaki `test_name` ile DXF kütüphanedeki dosya adı aynı normalize kurallarıyla eşleşir.

## Şema güncellemeleri

JSON Schema 2020-12 `if/then` conditional validation kullanır:
- type=none → count=0 zorunlu
- type ∈ {single, couple} → count ≥ 1
- label_config.enabled=true → model + default_count zorunlu

Schema dosyası import edildiğinde cache'lenir; her save'de tekrar oku yapılmaz (performans).

## Audit log

Her CRUD operasyonu `data/product_definitions_audit_log.jsonl` dosyasına append:
```json
{"at":"2026-05-28T15:39:44","action":"create","sku":"MAN-001","details":{"product_name":"...","name_type":"couple","label_enabled":true}}
{"at":"2026-05-28T15:39:44","action":"update","sku":"TRY-001","details":{...}}
{"at":"2026-05-28T15:39:44","action":"archive","sku":"TRY-002","details":{}}
{"at":"2026-05-28T15:39:44","action":"excel_import","sku":"TRY-001","details":{"row":2,"is_new":true}}
```

Audit yazımı bir hata atarsa CRUD işlemi yine başarılı olur (audit failure = best-effort).
