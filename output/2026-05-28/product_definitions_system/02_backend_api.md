# 02 — Backend API

## Modül: `src/webui_backend/product_definitions_api.py`

~480 satır. Tek dosyada CRUD + validation + Excel import + DXF resolve + audit + summary.

## Public API

| Fonksiyon | Görev |
|---|---|
| `list_definitions(root, include_archived=False)` | Sıralı tanım listesi |
| `get_definition(root, sku)` | Tek tanım |
| `search_definitions(root, query)` | Substring (SKU + product_name) |
| `save_definition(root, payload)` | Upsert + normalize + validate |
| `archive_definition(root, sku)` | Soft delete |
| `restore_definition(root, sku)` | Aktif et |
| `increment_usage(root, sku, by=1)` | Kullanım sayacı +1 |
| `import_from_excel(root, file_path, dry_run=False)` | Excel toplu yükle |
| `resolve_size_group(root, definition)` | Auto size_group + DXF lookup |
| `summary(root)` | İstatistik |

## Bridge slot'ları (9, bridge.py'de)

```python
@Slot(bool, result=str) def productDefinitionsList(include_archived=False)
@Slot(str, result=str) def productDefinitionGet(sku)
@Slot(str, result=str) def productDefinitionsSearch(query="")
@Slot(str, result=str) def productDefinitionSave(payload_json)
@Slot(str, result=str) def productDefinitionArchive(sku)
@Slot(str, result=str) def productDefinitionRestore(sku)
@Slot(str, bool, result=str) def productDefinitionsImportExcel(file_path, dry_run=False)
@Slot(str, result=str) def productDefinitionResolveSizeGroup(payload_json)
@Slot(str, result=str) def productDefinitionIncrementUsage(sku)
```

Hepsi JSON string döner; frontend `parseBridgeResult` ile parse eder. Hata durumları:
- `{"status":"OK","message":"...","definition":{...}}` (başarılı)
- `{"status":"VALIDATION_ERROR","errors":[...]}` (kullanıcı hatası)
- `{"status":"NOT_FOUND","message":"..."}` (eksik SKU)
- `{"status":"ERROR","message":"..."}` (sistemik hata, ör. Excel açılamadı)

## Normalize → Validate pipeline

`save_definition` akışı:
1. `normalize_definition(payload, prior)` — type coercion (str "1" → int 1, eksik alanlar default, prior `created_date` korunur)
2. `validate_definition(root, normalized)` — alan-bazlı kurallar + JSON Schema
3. Hata varsa: VALIDATION_ERROR, dosya yazılmaz, audit yazılmaz
4. Hata yoksa: `defs[sku] = normalized` → `_save_db` → `_audit("create"|"update", sku)`

Bu sayede frontend'in gevşek input'u (string "1", boş extras dict, eksik metadata) backend'de düzgün hale gelir ama validation hâlâ koruma sağlar.

## Excel import detayı

`import_from_excel(root, file_path, dry_run)`:

**Zorunlu kolonlar:** SKU, ProductName, NameType, NameCount, LabelEnabled, LabelModel, LabelCount

**Opsiyonel kolonlar:** SizeGroup, CompoundFormat, AdjustableInProduction, MinCount, MaxCount, ProductionNotes, TestName

**Akış:**
1. openpyxl ile read_only=True modda aç
2. Header satırını oku, zorunlu kolon eksikse ERROR
3. Her satır için: payload üret → normalize → validate
4. dry_run=True ise: preview (ilk 10 satır + her satırın hata durumu) döner, yazma yok
5. dry_run=False ise: validate başarısızları errors listesine, başarılıları upsert, sonunda dosyaya yaz

**Hata raporlama:** her satırın hatası `{row, sku, error}` formatında. Frontend hatalar listesini collapsible details'te gösteriyor.

**Audit:** her başarılı satır `excel_import` action olarak audit log'a düşer.

## Bağımlılıklar

- `jsonschema 4.26.0` — Draft 2020-12 validator
- `openpyxl 3.1.5` — Excel okuma (read_only=True, data_only=True modu)
- `webui_backend.dxf_library_api` — ASCII normalize + DXF lookup (cross-modul)

Her bağımlılık `try/except ImportError` ile sarılı; modül eksik olursa `JSONSCHEMA_AVAILABLE=False` veya `OPENPYXL_AVAILABLE=False` döner ve ilgili özellik düzgün hata verir.

## CLAUDE.md uyumu

- Hiçbir slot lazer/yazıcı/RDWorks tetiklemez
- Sahte success yok: validation hata varsa `VALIDATION_ERROR` döner; "kaydedildi" mesajı yalnızca dosya yazıldıktan sonra
- Soft delete: `archive` aslında sadece `metadata.status="archived"` set eder, satır kalır
- Tüm CRUD audit log'a düşer (forensic trail)
- Path traversal koruması: `project_root / RELATIVE` pattern, mutlak yol kabul edilmez
