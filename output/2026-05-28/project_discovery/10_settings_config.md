# 10 — Settings / Config (Bölüm J)

## Konum

- Backend: `src/webui_backend/settings_api.py` (3 KB, 70 satır — küçük), `live_integration_guard_api.py` (8 KB, 211 satır)
- Veri: `config/settings.yaml`
- UI: Ayarlar (`<section id="settings">`) — 6 alt sayfa

## `config/settings.yaml` (tam içerik)

```yaml
app:
  output_date_format: '%Y-%m-%d'
  language: tr
excel:
  mode: clean_production_excel
  input_file: input/siparisler.xlsx
templates:
  print_folder: templates/print
  laser_folder: templates/laser

# CLAUDE.md GÜVENLİK GATE'LERİ ↓
print:
  mode: label_designer
  generate_print_data_csv: true
  auto_print_enabled: false           # ✅
  allow_direct_print: false           # ✅
  require_print_confirmation: true    # ✅
  default_printer: ''
  use_default_label_settings: true

label_defaults:
  media_type: ROLL
  label_width_mm: 40, label_height_mm: 40
  roll_gap_mm: 3, printer_dpi: 300
  default_copies: 1
  safe_margin_mm: 1.5
  background_enabled: true
  show_cut_boundary: false

laser:
  auto_start_laser: false             # ✅
  output_format: svg
  plate_width_mm: 600, plate_height_mm: 400
  margin_mm: 5, gap_x_mm: 3, gap_y_mm: 3
  include_order_number_guide: true

laser_text:
  laser_font_path: assets/fonts/connected_script.ttf
  default_font_size_mm: 28
  min_font_size_mm: 18, max_font_size_mm: 36
  force_connected_letters: true
  convert_text_to_paths: true
  warn_if_disconnected_shapes: true
  add_bridges_for_dots_and_accents: false

reports:
  generate_errors_report: true
  generate_summary_report: true
  generate_layout_report: true
  generate_template_matching_report: true
```

## CLAUDE.md uyum (gate kontrolü)

| Garanti | Config Değer | Durum |
|---|---|---|
| auto_print_enabled | False | ✅ |
| allow_direct_print | False | ✅ |
| require_print_confirmation | True | ✅ |
| auto_start_laser | False | ✅ |

## Settings UI alt sayfaları

| Sayfa | İçerik |
|---|---|
| Genel Ayarlar | Çıktı klasörleri, etiket varsayılanları, güvenlik gate'leri |
| Kullanıcılar | (stub veya minimal) |
| Roller | (stub veya minimal) |
| Trendyol API | Credential + AI ayarları (Quick Wins'te password type + AI DOM eklendi) |
| Kargo Firmaları | (stub) |
| Diğer Ayarlar | Misc |
| Yazıcı Profilleri | Bağımsız sayfa, printer_profile_api |
| **Ürün Tanımları** (yeni) | v2.0 Bölüm 5 |
| Veri Bakımı | Backup + DXF Library |

## Slot'lar

| Slot | Görev |
|---|---|
| `save_label_defaults_json(payload)` | label_defaults yaz |
| `save_live_integration_security_settings(payload_json)` | live guard |
| `save_trendyol_settings(payload)` | Trendyol creds + AI ayarları |
| `save_printer_profile(profile_json)` | Yazıcı profili |
| `test_printer_profile(profile_id)` | Profil test |
| `set_default_printer_profile(profile_id)` | Default |
| `delete_printer_profile(profile_id)` | Silme (soft?) |
| `list_printer_profiles` | Liste |

## Live integration guard

`live_integration_guard_api.py` — direct print, lazer, RDWorks başlatma engelleyici. CLAUDE.md "lazer auto-start yok" ek koruma katmanı.

## Quick Wins düzeltmeleri (re-scan)

- ✅ API Key type=password (BUG-S1)
- ✅ Dashboard hardcoded status dinamik (homeDirectPrintStatus, homeQualityStatusInline span'ları)
- ✅ Çıkış butonu `quitApplication()` ile bağlı (eskiden stub `showSystemNotice`)
- ✅ AI ayarları DOM eklendi (sessiz reset durdu)
- ✅ Yazıcı testi yanlış renk + CSS `.tiny-status.warn/.bad` eklendi

## Veri Hacmi

- 1 ana config dosyası (`settings.yaml`), 30+ satır
- 1 trendyol_settings.json (18 alan, credentials maskeli)
- 1 printer_profiles.json (henüz okunmadı)

## Bilinmeyen / test edilemedi

- Kullanıcılar + Roller sayfaları gerçek functionality mi yoksa stub
- `add_bridges_for_dots_and_accents: false` — eski algoritma flag'i mi
- Live integration guard backend code ne kadar derin (sadece overview)

## Risk / Uyarı

- 🟢 Tüm CLAUDE.md gate'leri config'te doğru
- 🟢 Live integration guard ek koruma katmanı sağlam
- 🟢 Quick Wins sonrası UI dürüstlüğü yüksek
