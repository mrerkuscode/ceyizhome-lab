# 04 — Gerçek Aktarım

## Komut

```bash
python output/2026-05-28/trendyol_migration/migrate_trendyol_to_product_definitions.py \
       --output output/2026-05-28/trendyol_migration/actual_result.json
```

## Tam çıktı

```
[migration] dry_run=False total_active=36 success=36 skipped_existing=0 failed=0
[migration] sonuç yazıldı: output/2026-05-28/trendyol_migration/actual_result.json
```

## Sonuç (gerçek)

| Metrik | Değer |
|---|---|
| Kaynak | `data/trendyol_product_mappings.json` |
| Toplam okuma | 36 satır |
| Aktif | 36/36 |
| Validation **PASS** | 36/36 |
| Yazıldı | **36/36** ✅ |
| Atlanan (var olan) | 0 |
| Başarısız | 0 |

## Yazılan dosya

`data/product_definitions.json` — boyut 109 byte'tan **kütüphane içine 36 entry** olarak büyüdü.

Validation:
- `summary.active = 36`
- `summary.archived = 0`
- `summary.by_name_type = {single: 1, couple: 35, none: 0}`
- `summary.with_label = 35`

## Audit log (`data/product_definitions_audit_log.jsonl`)

48 satır toplam. Bunların:
- 38 `create` action (önceki test sırasında 2 + bu migration sırasında 36)
- 1 `archive` action (önceki test temizliği)
- 9 `excel_import` action (önceki test sprintinden)

Migration sırasında her başarılı `save_definition` çağrısı için 1 entry düşürüldü. Format:

```json
{"at":"2026-05-28T16:01:23","action":"create","sku":"TRY-...",
 "details":{"product_name":"...","name_type":"couple","label_enabled":true}}
```

## Sahte başarı yok — gerçek doğrulama

Script çağrıları sonrası **manuel post-check** script çalıştırıldı:

```python
# Active count
result = pda.api_list(Path('.'))
assert result['summary']['active'] == 36  # PASS

# Re-validate every entry
for entry in result['definitions']:
    errs = pda.validate_definition(Path('.'), entry)
    assert errs == []
# Tüm 36 entry için PASS

# Eski sistem dokunulmadı
mappings = json.loads(Path('data/trendyol_product_mappings.json').read_text(encoding='utf-8'))
assert len(mappings) == 36

# 332 öneri dokunulmadı
suggestions = json.loads(Path('data/trendyol_mapping_suggestions.json').read_text(encoding='utf-8'))
assert len(suggestions) == 332

# 167 SVG ref korundu
ref_lib = json.loads(Path('assets/references/corel_name_reference_library.json').read_text(encoding='utf-8'))
assert len(ref_lib.get('references', [])) == 167

# Operator-approved Trendyol row korundu
sug = json.loads(Path('data/trendyol_production_suggestions.json').read_text(encoding='utf-8'))
assert len([r for r in sug if _is_verified_ready(r)]) >= 1
```

Tüm assertion'lar geçti.

## Eğer hata olsaydı (sahte başarı önleme örneği)

Script'in mantığı:
- `save_definition` her satır için `normalize → validate → save` zincirinden geçer
- Validation hata → satır `failed[]` listesine, dosya yazılmaz
- Bir hata olsa rapor "**N/36 başarılı**, M hata" şeklinde olurdu (örnek: 31/36, 5 hata)
- Script exit code 1 dönerdi (failed listesi boş değilse)

Bu durumda gerçek sonuç **36/36** olduğu için exit code 0, rapor temiz.

## Force-overwrite davranışı

Script'te `--force` flag'i var. Default kapalı: eğer SKU `product_definitions.json`'da zaten varsa **atlanır** (`skipped_existing[]` listesine eklenir, üzerine yazılmaz). Bu sprintte aktif değildi çünkü target dosya boştu.
