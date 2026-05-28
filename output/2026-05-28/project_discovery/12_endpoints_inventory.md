# 12 — Endpoint (Bridge Slot) Envanteri

**Toplam:** 185 `@Slot` decorator (`src/webui_backend/bridge.py`).
**JSON dump:** `_slot_inventory.json` (tam liste) + `_slot_groups.json` (kategorize).

## Kategoriler

### Misc / Varied (30 slot)

Genel/ortak işlemler. Önemli olanları:
- `quitApplication()` — uygulama çıkış (Quick Wins)
- `set_selected_excel(path)` — Excel dosya seçimi
- `chooseExcel()` — interaktif Excel seç
- `resolveExactReferenceByName(input_name)` — exact ref lookup
- `render_manual_label(...)`, `render_manual_label_fields(...)` — Manual etiket render
- `preflight_manual_label_fields(...)` — preflight check
- `import_template_pack` / `create_template` / `create_demo` — şablon CRUD
- `convert_legacy_excel` — eski Excel formatı dönüştürme
- `cleanup_duplicate_label_text_fields/note_fields` — temizlik

### Label model / template (26 slot)

`label_api` + `template_api` modüllerine bağlı. 5 alt-kategori:
- **Oluşturma:** `create_label_model_from_source`, `create_label_model_from_wizard`, `clone_label_model_variant`, `create_linked_label_design`
- **Alan edit:** `save_label_model_field`, `add_label_model_field`, `remove_label_model_field`
- **Backup:** `list_label_model_backups`, `compare_label_model_backup`, `compare_label_model_backup_pair`, `restore_label_model_backup`, `set_label_model_backup_note`
- **Önizleme/normalize:** `choose_label_model_preview`, `validate_label_model_preview`, `normalize_label_model_preview`
- **Çıktı:** `list_label_outputs`, `list_archived_label_outputs`, `archive_label_outputs`, `restore_label_outputs`, `add_label_outputs_to_print_queue`, `add_pdf_output_to_print_queue`

### File system / open (18 slot)

`file_api` + frontend file ops:
- `select_excel`, `reveal_file_in_folder(path)`, `open_file_safe(path)`
- `open_output_folder` / `openOutput`, `open_reports_folder` / `openReports`
- `open_print_folder` / `openPrint`, `openPrintTemplates`
- `open_laser_folder` / `openLaser`, `open_input_folder` / `openInput`
- `open_svg(path)`, `open_project_file(relative_path)`
- `open_native_edit_report`, `openErrors`

### Corel Reference (legacy SVG) (17 slot)

`corel_reference_importer.py` + ilişkili dispatcher. SVG-based 167 ref kütüphane yönetimi:
- **CRUD:** `listCorelReferences`, `getCorelReference`, `updateCorelReferenceLabel`, `saveOperatorGeneratedCorelReference`
- **Onay zinciri:** `approveCorelExactReference`, `unapproveCorelReference`, `markCorelReferenceStyleOnly`, `rejectCorelReferenceCandidate`
- **Operasyon:** `rebuildCorelReferenceIndex`, `splitCorelReference`, `searchCorelReferences`
- **Backup/migration:** `createCorelReferenceBackup`, `listCorelReferenceBackups`, `restoreCorelReferenceBackup`, `migrateCorelReferenceLibrary`, `validateCorelReferenceLibrary`
- **Security:** `corelReferenceDataSecurityStatus`

### Trendyol (10 slot)

`trendyol_api.py` + `trendyol_mapping_api.py`:
- `save_trendyol_settings(payload)`, `test_trendyol_connection`
- `sync_trendyol_recent_orders(days)`, `sync_trendyol_questions`
- `cache_trendyol_product_image(url)`
- `apply_trendyol_question_to_suggestion(id, qid)`
- `approve_trendyol_mapping_suggestion(id)`
- `upsert_trendyol_mapping(payload)`
- `verify_trendyol_suggestion(id, payload)`
- `save_trendyol_operator_correction(id, payload)`

### DXF Library (yeni) (8 slot)

Yeni eklenen, `dxf_library_api.py` + `dxf_library_watcher.py`:
- `dxfLibraryList`, `dxfLibrarySearch(query)`, `dxfLibraryFind(name)`
- `dxfLibraryRefresh`
- `dxfLibraryResolveForOrder(requested_name)`
- `dxfLibraryStartWatcher`, `dxfLibraryStopWatcher`, `dxfLibraryWatcherStatus`

### Product Definitions (yeni v2.0) (9 slot)

Yeni eklenen, `product_definitions_api.py`:
- `productDefinitionsList(include_archived)`
- `productDefinitionGet(sku)`
- `productDefinitionsSearch(query)`
- `productDefinitionSave(payload_json)`
- `productDefinitionArchive(sku)`, `productDefinitionRestore(sku)`
- `productDefinitionsImportExcel(file_path, dry_run)`
- `productDefinitionResolveSizeGroup(payload_json)`
- `productDefinitionIncrementUsage(sku)`

### Bulk production (5 slot)

- `bulk_generate_and_add_to_queue`
- `bulk_generate_selected_and_add_to_queue(row_numbers_json)`
- `bulk_generate_gallery_items_and_add_to_queue(items_json)`
- (+ ilgili rapor/state slot'ları misc'te)

### Print queue / Name cut (~10 slot)

- `clear_print_queue`, `mark_queue_item_printed/pending/delivered`
- `prepare_manual_print(item_id, profile_id)`
- `save_name_cut_queue_items(payload_json)`
- `update_name_cut_queue_item_status(item_id, status)`
- `check_name_cut_queue_duplicate(...)`

### Printer profile (5 slot)

- `save_printer_profile(profile_json)`
- `test_printer_profile(profile_id)`
- `set_default_printer_profile(profile_id)`
- `delete_printer_profile(profile_id)`
- `list_printer_profiles`

### Production audit / history / safety (~10 slot)

- `append_production_audit_event(payload)`
- Audit list/filter/search slot'ları
- Production safety check slot'ları

### Backup (5 slot)

- `create_backup`, `list_backups`, `validate_backup(path)`
- `restore_backup(path, dry_run)`, `export_backup_manifest(path?)`

### Customer order (4 slot)

- `list_customer_orders`, `get_customer_order_detail`
- `update_customer_order_status(order_id, status)`
- `import_template_pack`

### PDF / preview (~5 slot)

- `cache_trendyol_product_image(url)` (Trendyol içinde)
- PDF preview slot'ları (pdf_preview_api)

### Native edit / experimental (1 slot)

- `run_native_edit_poc(template_path, edit)` — Native CDR/AI proof of concept

### Settings / state (4 slot)

- `get_status` / `initialState`
- `showSettings`, `showHelp`

### Run / execute (~5 slot)

- `run_dry_run` / `runDry`
- `run_production` / `runProduction`
- `render_labels` / `renderLabels`
- `cancel_running_job`

## REST eşdeğeri

Sistem QWebChannel ile çalışır; HTTP REST yok. Bridge slot'ları frontend'den `bridge.<slot_name>(args, callback)` ile çağrılır. Tüm yanıtlar `parseBridgeResult(raw)` → JSON object.

## Slot signature standardı

- Slot adı `camelCase` veya `snake_case` (proje karışık, eski snake_case + yeni camelCase)
- Tüm yanıtlar string-encoded JSON
- Standart yanıt: `{"status": "OK|ERROR|VALIDATION_ERROR|NOT_FOUND|...", "message": "...", ...}`
- Args genellikle: tek SKU/path string veya JSON-encoded payload

## Eksik / Bilinmeyen

- Bridge'in HTTP-export'u var mı (sadece QWebChannel görünüyor)
- Test/integration için mock bridge implementasyonu (yok gibi)
- Slot rate limiting (yok, frontend her tıklamada çağırır)
