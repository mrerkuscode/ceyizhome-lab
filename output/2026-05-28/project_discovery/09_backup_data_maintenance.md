# 09 — Backup + Veri Bakımı (Bölüm I)

## Konum

- Backend: `src/webui_backend/backup_api.py` (11 KB)
- Veri: `backups/` (40 backup), `config/settings.yaml`
- UI: Ayarlar → Veri Bakımı kartı + DXF Kütüphane kartı

## Backup inventory

- 3 günlük klasör: 2026-05-22, 2026-05-23, 2026-05-28
- 40 manifest.json (her backup paketi)

## BACKUP_RELATIVE_FILES (`backup_api.py:12-30`)

15 dosya yedeklenir:
```
data/name_cut_queue.json
data/name_cut_transfer_history.json
data/name_cut_export_history.json
data/print_queue.json
data/production_audit_log.json
data/customer_orders.json
data/production_history.json
data/printer_profiles.json
# trendyol_settings.json INTENTIONALLY EXCLUDED (credential leak — Quick Wins fix)
data/trendyol_questions_context.json
data/trendyol_product_mappings.json
data/trendyol_mapping_suggestions.json
data/trendyol_production_suggestions.json
data/trendyol_ai_extraction_cache.json
data/trendyol_extraction_learning_examples.json
assets/references/corel_name_reference_library.json    # Quick Wins addition
config/settings.yaml
```

## Slot'lar

| Slot | Görev |
|---|---|
| `create_backup` | Yeni snapshot |
| `list_backups` | Tüm backup listesi |
| `validate_backup(path)` | SHA256 + JSON check |
| `restore_backup(path, dry_run)` | Geri yükle (dry-run önerilir) |
| `export_backup_manifest(path?)` | Manifest export |

## Manifest yapısı

Her backup `manifest.json` içerir:
- `backup_id` — UUID
- `created_at` — ISO timestamp
- `reason` — manual / pre_restore_snapshot / vb.
- `file_count`, `missing_files`, `files: [{relative_path, size, sha256}]`
- `safety: {auto_print_started: false, laser_started: false, rdworks_started: false, trendyol_live_action: false}` — CLAUDE.md uyum

## DXF Library Kartı (yeni eklenen)

Veri Bakımı sayfasında ek kart:
- Klasör yapısı açıklaması
- "Kütüphaneyi Tara" butonu (manuel rescan)
- "Otomatik İzlemeyi Başlat" toggle
- Arama inputu
- DXF listesi (her dosya: name, group, bbox, warnings)

## Quick Wins düzeltmeleri (re-scan)

- ✅ `data/trendyol_settings.json` backup'tan çıkarıldı (BUG-S2)
- ✅ `assets/references/corel_name_reference_library.json` backup'a eklendi (Phase 2 17 KRİT-1)
- ✅ Veri Bakımı UI etiketi düzeltildi (`index.html:3086` gerçek kapsamı listeliyor)
- ✅ Migrate + rebuild yıkıcı butonlar confirm dialog'lu

## Veri Hacmi

- 40 backup (yaklaşık 7 günlük rolling)
- Dolu / boş: dolu, son backup 2026-05-28

## Bilinmeyen / test edilemedi

- Backup boyutu (örnek manifest okunmadı, klasör boyutu hesaplanmadı)
- Restore'un gerçek operatör tarafından kullanım sıklığı (audit'te restore event'i yok)
- Backup auto-pruning var mı (40 backup, sınırsız büyüyor mu?)

## Risk / Uyarı

- 🟢 Credential ifşası kapatıldı (BUG-S2 fix yerinde)
- 🟢 Corel ref library backup'a dahil (veri kaybı önleme)
- 🟢 Pre-restore snapshot otomatik alınıyor (`restore_backup` öncesi `create_backup(reason="pre_restore_snapshot")`)
- 🟡 Backup auto-pruning yok — disk şişebilir, manuel temizlik gerekli
