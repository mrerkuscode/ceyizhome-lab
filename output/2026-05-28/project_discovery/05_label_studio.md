# 05 — Label Studio (Bölüm E)

## Konum

- Backend: `src/webui_backend/label_api.py` (379 satır, 15 KB) + `combined_production_api.py` (391 KB — büyük)
- UI: `<section id="label">` (Etiket Studio), `<section id="manualLabel">` (Manuel)
- Template altyapı: `src/webui_backend/template_api.py` (1677 satır, 78 KB — en büyük modül)

## Slot'lar (Label model / template — 26 + Manuel — birkaç)

| Kategori | Slot örnekleri |
|---|---|
| Liste/galeri | `list_label_model_gallery`, `list_label_templates`, `list_label_outputs`, `list_archived_label_outputs` |
| Oluşturma | `create_label_model_from_source`, `create_label_model_from_wizard`, `clone_label_model_variant`, `create_linked_label_design`, `create_template` |
| Edit/alan | `save_label_model_field`, `add_label_model_field`, `remove_label_model_field`, `cleanup_duplicate_label_text_fields`, `cleanup_duplicate_note_fields` |
| Backup/restore | `list_label_model_backups`, `compare_label_model_backup`, `compare_label_model_backup_pair`, `restore_label_model_backup`, `set_label_model_backup_note` |
| Önizleme | `choose_label_model_preview`, `validate_label_model_preview`, `normalize_label_model_preview` |
| Manual render | `render_manual_label`, `render_manual_label_fields`, `preflight_manual_label_fields`, `validate_manual_label_output`, `render_manual_label_fields_to_queue` |
| Çıktı | `add_label_outputs_to_print_queue`, `archive_label_outputs`, `restore_label_outputs`, `add_pdf_output_to_print_queue` |
| Settings | `save_label_defaults_json` |

## Akış (manual)

1. Operatör Etiket Studio'yu aç (sidebar)
2. Model gallery'den template seç → `list_label_model_gallery`
3. Studio'da yazı katmanlarını düzenle
4. `preflight_manual_label_fields` → kontrol; başarısızsa hata
5. `render_manual_label_fields_to_queue` → kuyruğa al (yazıcı tetiklenmez)

## Önemli config

- `config/settings.yaml` `label_defaults`:
  - `media_type: ROLL`
  - `label_width_mm: 40`, `label_height_mm: 40`
  - `printer_dpi: 300`
  - `safe_margin_mm: 1.5`
  - `default_copies: 1`

## Bypass / sahte success durumu

- **Faz1 #5 — Etiket Studio preflight bridge yoksa OK callback**: re-scan'de hâlâ HIT görüldü. `app.js:10853-10855` (audit referansı) — bridge yoksa "preflight geçti" sahte callback'i. Quick Wins sprintinde kalan iş olarak ertelenmişti. ⚠️ TODO
- **Faz1 #6 — PDF/PNG render `sentToProduction:true, userApproved:true` literal'leri**: re-scan HIT. Operatör onayı bypass. ⚠️ TODO (Quick Wins'te ertelendi)

Eksik düzeltmeler `06_action_plan.md` Öncelik 1 listesinde (full_project_audit) duruyor.

## Veri Hacmi

- 26 label-model bridge slot — kapsamlı şablon yönetimi
- `templates/print/` ve `templates/laser/` klasörleri (`settings.yaml`'da tanımlı)
- Label backup'lar her template başına: liste/karşılaştır/restore mevcut

## Bilinmeyen / test edilemedi

- Operatör tipik kaç şablon kullanıyor — `list_label_templates` ile ölçülebilir ama bu sprint kapsamı dışı
- AI kalite skorlamanın label studio çıktısı üzerindeki etkisi (AI_LASER_QUALITY_*)
- Manual label vs. automated label kullanım oranı

## Risk / Uyarı

- 🟢 Direct print kapalı (`config/settings.yaml` `print.allow_direct_print: false`), `auto_print_enabled: false`
- 🟡 Bilinen sahte success kalıntıları (Faz1 #5, #6) — Quick Wins sonra sprintinde çözülecekti
- 🟢 Template backup sistemi var (CLAUDE.md "değişiklik öncesi snapshot" garantisi)
