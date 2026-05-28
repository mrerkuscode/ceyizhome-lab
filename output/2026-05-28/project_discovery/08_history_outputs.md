# 08 — Üretim Geçmişi + Çıktılar (Bölüm H)

## Konum

- Backend: `src/webui_backend/production_audit_api.py` (35 KB, 731 satır), `report_api.py` (3 KB)
- Veri: `data/production_history.json` (249 satır, 185 KB), `data/production_audit_log.json` (13 event, 25 KB), `data/customer_orders.json` (10 satır, 7 KB)
- UI: `<section id="productionAudit">` "Üretim Geçmişi", `<section id="labelOutputs">` "Etiket Çıktıları", `<section id="reports">` "Raporlar"

## Üretim history detayı

| Metrik | Değer |
|---|---|
| Toplam satır | 249 |
| Tarih aralığı | 2026-05-07 → 2026-05-23 |
| Dated rows | 249 |

Schema (ilk satır): `id, created_at, model_name, model_id, model_path, label_text, date_text, note_text, quantity, width_mm, height_mm, pdf_path, png_path, queue_status, preflight_status, ...`

Sample: `11_data_samples/production_history_last3.json` (son 3)

## Audit log

13 event total. Event türleri:

| Event Type | Sayı |
|---|---|
| `namecut_export_preflight_failed` | 4 |
| `namecut_export_preflight_passed` | 2 |
| `namecut_export_manifest_created` | 2 |
| `namecut_export_format_skipped` | 2 |
| `namecut_export_created` | 2 |
| `bulk_validation_completed` | 1 |

Statü dağılımı: `OK: 4, blocked: 4, passed: 2, skipped: 2, WARNING: 1`.

Sample: `11_data_samples/production_audit_log_last3.json`

## Customer orders

10 satır, 7 KB. Sample: `11_data_samples/customer_orders_full.json`

## Output klasörleri

28 günlük klasör (2026-04-27 → 2026-05-28). Tipik içerik:
- `output/<date>/name_cut/` — DXF/SVG/PDF batch'leri
- `output/<date>/namecut_exports/` — RDWorks-ready exports
- `output/<date>/full_project_audit/`, `quick_wins_sprint/`, `dxf_library_system/`, `product_definitions_system/`, `project_discovery/` — sprint raporları

`output/2026-05-13/` özellikle yoğun: 20+ batch DXF (eski jeneratif algoritma denemeleri).

## Slot'lar (audit + reports)

| Slot | Görev |
|---|---|
| `load_reports` | Rapor verilerini çek |
| `list_svg_files` | SVG çıktı listesi |
| `list_laser_outputs` | Lazer SVG çıktı listesi |
| `list_label_outputs` / `list_archived_label_outputs` | Etiket çıktıları |
| `archive_label_outputs(relative_paths_json)` | Toplu arşivle |
| `restore_label_outputs(relative_paths_json)` | Geri al |
| `append_production_audit_event(payload)` | Manuel audit entry |

## Bypass / sahte success durumu

- **SYS-2 — `outputValidationState` "Doğrulandı" hardcoded**: re-scan HIT — `app.js` "Doğrulandı" string'i var. Audit'te SYS-2 olarak listelenmiş, Quick Wins'te ertelendi. ⚠️ TODO
- **SYS-2 — `label_api.py:83` "HAZIR" default**: re-scan HIT. ⚠️ TODO (Quick Wins sonra)

## Veri Hacmi

- 249 üretim history row (2.5 hafta veri)
- 13 audit event (audit modülü görece az kullanılıyor, çoğu name_cut export ile sınırlı)
- 10 customer order
- 28 günlük output klasörü

## Bilinmeyen / test edilemedi

- 249 history satırın kaçı gerçek production (canlı sipariş) kaçı test
- Audit modülünün neden sadece name_cut + bulk validation event'leri yakaladığı (etiket render event'i yok)
- Rapor sayfasında hangi rapor türleri aktif

## Risk / Uyarı

- 🟡 Bilinen sahte success: "Doğrulandı" hardcoded badge, "HAZIR" default status — Quick Wins kalan iş
- 🟢 Audit log soft delete uyumlu (append-only)
- 🟢 Output arşivleme sistemi var, restore yapılabiliyor
