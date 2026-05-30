# Cyzella Production Studio — Yol Haritası (Denetim Raporu)

> **Denetim tarihi:** 2026-05-30
> **Denetleyen:** Claude Code (salt-okunur)
> **Repo:** production-bot
> **Test sonucu:** 250 passed, 7 failed (browser/playwright smoke — playwright kurulu değil). Tüm birim/entegrasyon testleri geçiyor.

## Durum işaretleri
- ○ başlanmadı / yok
- ◐ kısmen var / stub
- ● bitti, çalışıyor

## Global güvenlik değişmezleri

| Değişmez | Durum | Kanıt |
|---|---|---|
| CorelDRAW otomatik açılmaz | [x] | index.html:187 "Corel / Illustrator — Otomatik açılmaz"; bridge'de CorelDRAW çağrısı yok |
| Yazıcı otomatik çalışmaz | [x] | index.html:185 "Yazıcı — Otomatik çalışmaz"; config_loader.py:282 auto_print_enabled=False zorunlu |
| RDWorks otomatik açılmaz | [x] | main.py:322 "RDWorks açılmadı"; svg_generator.py güvenlik notu |
| Lazer otomatik başlamaz | [x] | config_loader.py:299 auto_start_laser=False zorunlu; index.html:186 "Lazer — Otomatik başlamaz" |
| allow_direct_print: false | [x] | settings.yaml:14 `allow_direct_print: false`; config_loader.py:289 false zorunlu |
| auto_print_enabled: false | [x] | settings.yaml:13 `auto_print_enabled: false`; config_loader.py:282 doğrulama |
| auto_start_laser: false | [x] | settings.yaml:34 `auto_start_laser: false`; config_loader.py:299 doğrulama |
| LASER_CUT font yoksa bloke | [x] | laser_nesting.py:214 CONNECTED_STATUS_FONT_MISSING; config_loader.py:138–143 startup uyarısı; errors_report.csv'ye yazılır |
| NEEDS_REVIEW üretimden dışlanır | [x] | validators.py:103 template_issues → continue; main.py:126 filter ile sadece geçerli siparişler |

---

## 1. Genel Bakış ●

| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Sayaç kartları (toplam/geçerli/hata/print/laser...) | [x] | - | index.html:143–150 homeTodayPdfCount vb.; report_api.py:27–41 summary() |
| Aktif output klasörü yolu | [x] | - | bridge.py:670 open_output_folder; desktop/web_main_window.py output klasörü gösterimi |
| Açılış özeti (ayar/klasör kontrolü) | [x] | - | config_loader.py:124–144 print_startup_summary(); auto_print, laser, font uyarıları |
| Son çalıştırma zamanı/durumu | [x] | - | index.html:151–152 homeLastOutput, homeQualityStatus; report_api.py readiness() |

**Sayfa durumu:** ●
**Notlar:** Ana ekranda güvenlik pilleri (Güvenli Mod, Direct Print, Yazıcı, Son Kontrol) gerçek zamanlı gösteriyor. metrics_payload() üretim geçmişi JSON'dan hesaplıyor (report_api.py:100–207).

---

## 2. Excel ●

| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Excel Seç (varsayılan input/siparisler.xlsx) | [x] | - | settings.yaml:6 `input_file: input/siparisler.xlsx`; bridge.py:175–182 select_excel/chooseExcel; index.html:870 "Excel Seç" butonu |
| Boş Excel Şablonu Oluştur | [x] | - | main.py:385–388 `--create-template`; bridge.py:744–750 create_template/createTemplate; template_writer.py create_production_template() |
| Input Klasörünü Aç | [x] | - | bridge.py:710–715 open_input_folder/openInput |
| Demo Excel oluşturma (--create-demo) | [x] | - | main.py:390–393 `--create-demo`; bridge.py:752–758 create_demo/createDemo |
| Legacy Excel dönüştürme | [x] | - | main.py:395–397 `--convert-legacy-excel`; bridge.py:760–766 convert_legacy_excel/convertLegacyExcel; legacy_converter.py mevcut |
| 0 sipariş → doğru bilgilendirme | [x] | - | main.py:300–323 _print_summary(); report_api.py:15–24 readiness() "NO_CHECK" |

**Sayfa durumu:** ●

---

## 3. Kontrol ●

| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Kontrolü Tekrar Çalıştır (dry-run) | [x] | - | bridge.py:187–193 run_dry_run/runDry; main.py:109–116 dry_run dalı; index.html:910 "Alanları Kontrol Et" butonu |
| Satır doğrulama (alanlar/process_type/buyer_name...) | [x] | - | validators.py:56–110 validate_and_build_orders(); BASE_REQUIRED_FIELDS, PRINT_REQUIRED_FIELDS, process_type, personalization_type, label_variant, status, quantity |
| Hata ve needs_review listesi (Türkçe) | [x] | - | report_api.py:44–46 first_errors(); desktop/report_loader.py:33 needs_review_report.csv; text_normalizer.py friendly_error() |
| Üretim onay kutusu | [x] | - | index.html:839–841 "Üretime Al" adımı (step 6); desktop/web_main_window.py onay akışı |
| Üretim Dosyalarını Oluştur (temizse aktif) | [x] | - | bridge.py:195–201 run_production/runProduction; main.py:118–134 production flow |

**Sayfa durumu:** ●

---

## 4. Etiket ◐

### 4a. Model Kütüphanesi
| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Model kartları (önizleme görseli) | [x] | - | template_api.py:37–85 list_label_templates(); index.html:226 labelModelGallery; preview_image, health_status, model_no, label_variant alanları |
| Yeni model ekle / mevcut seç | [x] | - | template_api.py:996–1038 create_label_model_from_wizard(); bridge.py:734–738; index.html:200–204 toolbar butonları |
| Önizleme Görseli Seç → assets kopyala | [x] | - | template_api.py:602–646 set_label_model_preview(); bridge.py:812 choose_label_model_preview(); assets/label_backgrounds/ |

### 4b. Etiket Studio (canvas)
| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Üst toolbar (Yeni/Aç/Kaydet/PDF üret...) | [x] | - | index.html:356–373 studio-toolgroup; newManualWork, openManualWork, saveManualWork, renderManual |
| İsim/Tarih/Not Alanı Ekle | [x] | - | index.html:468–476 field-row isim/tarih/not; updateManualFieldValue(); template_api.py add_label_model_field() |
| Tıkla/çift tıkla → metin düzenle | [x] | - | app.js corelApplyTypography(), updateManualFieldValue() canvas event handlers |
| Sürükle-taşı, köşeden büyüt/küçült | [x] | - | app.js activeDrag, corelApplyGeometry(); index.html:379–384 X/Y/W/H inputs |
| Sağ panel: font/boyut/renk/hizalama/bold/italic | [x] | - | index.html:385–392 corelFontSize, corelColor, bold/italic butonları, align butonları; corelApplyTypography() |
| Üst altın çizgi göster/gizle + konum/genişlik/kalınlık/renk | [~] | P2 | Veri modelinde mevcut (elements array rectangle elementi) ama Studio'da ayrı UI toggle butonu yok |
| Kenarlık göster/gizle + renk/kalınlık | [~] | P2 | Şablon JSON'da stroke_color/stroke_width var ama Studio inspector'da ayrı kontrol yok |

### 4c. Şablon editörü & kaydetme
| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Etiket Şablonu Düzenle (JSON olmadan) | [x] | - | template_api.py:1111–1112 save_label_template(); save_label_model_field(); UI üzerinden alan konumu/boyutu/font |
| Kaydet → templates/designs/... | [x] | - | template_api.py:1671–1677 _write_template_json_with_backup(); templates/designs/ |
| Üzerine yazma onayı + backup | [x] | - | template_api.py:1671–1677 backup_dir oluşturur, timestamp'li kopya saklar; save_template_with_backup() |
| Validasyon (yazı içinde/font>0/çizgi sınır/bg assets) | [x] | - | production_safety.py:21–80 preflight_manual_label(); x+w≤width, y+h≤height, font_size<5 uyarısı |

### 4d. Render / çıktı
| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Önizleme Oluştur (Label Designer motorundan PNG) | [x] | - | label_api.py:21–31 preview_manual(); render_manual_preview(); webui_backend |
| PDF/PNG Oluştur | [x] | - | label_designer/pdf_exporter.py export_label_pdf(); label_designer/preview_exporter.py export_label_png(); label_service.py |
| Manuel Etiket Oluştur (Excel olmadan) | [x] | - | bridge.py:621–628 render_manual_label/render_manual_label_fields(); label_designer/manual_label_service.py |
| Yazdırma Sırasına Ekle | [x] | - | bridge.py:644–650 render_manual_label_fields_to_queue(); index.html:370 "Sıraya Ekle" butonu |
| print.mode=data_only ise tasarım kapalı bildirimi | [x] | - | main.py:173–176 "Etiket tasarım modu kapalı" mesajı; settings_api.py:62–64 mode doğrulaması |

### 4e. Rulo etiket
| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Rulo Etiket Varsayılanları (genişlik/yükseklik/DPI...) | [x] | - | settings.yaml:18–32 label_defaults; config_loader.py:188–207 _load_label_defaults(); settings_api.py:43–44 get_label_defaults() |
| Kalibrasyon PDF Oluştur | [x] | - | label_designer/calibration_service.py:22–31 create_calibration_pdf(); label_designer/calibration.py export_roll_label_calibration_pdf(); bridge.py:651 |
| roll_batch PDF | [x] | - | label_designer/label_service.py:130–166 _write_roll_batches(); label_api.py list_label_outputs() "RULO TOPLU PDF" kind |

### 4f. Şablon/giriş yönetimi
| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Şablon / CDR Yükle (.cdr/.ai/.pdf/.svg) | [x] | - | template_api.py:1231–1254 import_print_template_file(); ALLOWED_PRINT_TEMPLATE_SUFFIXES |
| Şablon Paketi Yükle (güvenli ZIP; .exe reddedilir) | [x] | - | template_api.py:1227–1228 import_template_pack(); desktop/template_importer.py safe_extract_template_pack() |
| Baskı Şablonlarını Gör | [x] | - | template_api.py:438–472 list_print_templates(); bridge.py:860–863; index.html "Baskı Şablonlarını Gör" butonu |
| Etiket Çıktılarını Gör (PDF/PNG gallery) | [x] | - | label_api.py:42–88 list_label_outputs(); server/routes.py:95–100 /label_outputs; index.html raporlar sekmesi "Etiket Çıktıları" |

**Sayfa durumu:** ◐
**Notlar:** Temel akışlar tam. Altın çizgi göster/gizle ve kenarlık renk/kalınlık UI toggle'ları frontend'de ayrı kontrolörler olarak yok — veri modelinde mevcut, JSON düzeyinde ayarlanabiliyor. P2 olarak işaretlendi.

---

## 5. Lazer ◐

| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| LASER_ENGRAVE / LASER_CUT / BOTH akışları | [x] | - | laser_service.py:36–70 generate_laser_jobs(); laser_nesting.py nest_laser_orders(); main.py:126–132 process_type filtreleme |
| Plaka nesting (plate_001.svg...) | [x] | - | laser_nesting.py:46–196 nest_laser_orders(); laser_service.py _write_plates(); svg_generator.py write_laser_plate_svg(); plate_{index:03d}.svg |
| Bağlı script font kontrolü → connected_status | [x] | - | laser_nesting.py:199–242 validate_connected_cut_safety(); CONNECTED_STATUS_* sabitleri; config_loader.py:138–143 startup uyarısı |
| Türkçe karakter desteği doğrulaması | [x] | - | laser_nesting.py:378–399 _has_unsupported_turkish_character(); TURKISH_CHARACTERS set; fontTools cmap kontrolü |
| Guide katmanları (PLATE_BOUNDARY_GUIDE...) | [x] | - | svg_generator.py:32–43 PLATE_BOUNDARY_GUIDE_DO_NOT_CUT; _engrave_text_group ENGRAVE_TEXT; _cut_lines_group CUT_LINES; _order_guide_group ORDER_GUIDE_DO_NOT_CUT |
| Plaka/model layout raporları | [x] | - | laser_service.py:91–107 _write_plate_reports(); model_level_layout_report.csv; {plate_stem}_layout_report.csv |
| Font yoksa LASER_CUT bloke + errors_report.csv | [x] | - | laser_nesting.py:87–108 validate_connected_cut_safety() → issues.append(); report_writer.py write_errors_report() |

**Sayfa durumu:** ◐
**Notlar:** LASER_CUT SVG çıktısı kasıtlı güvenlik stub'ı — svg_generator.py:62–69 CUT_LINES grubunda `continue` ile hiç element üretilmiyor ("Cannot guarantee connected cursive vector paths in MVP"). LASER_ENGRAVE tam çalışıyor. İsim Kesim Studio (nameCutStudio) combined_production_api.py üzerinden DXF library + weld engine pipeline'ı kullanıyor.

---

## 6. Raporlar ●

| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Uygulama içi: summary_report.csv | [x] | - | report_writer.py:28–67 write_summary_report(); main.py:241–247; settings.yaml:53 generate_summary_report: true |
| Uygulama içi: errors_report.csv | [x] | - | report_writer.py:10–25 write_errors_report(); main.py:248–249; settings.yaml:52 generate_errors_report: true |
| Uygulama içi: smart_warnings_report.csv | [x] | - | intelligence/reporting.py:20 _write_findings(); main.py:253 build_smart_warnings(); desktop/report_loader.py:34 |
| Uygulama içi: needs_review_report.csv | [x] | - | intelligence/reporting.py:21 _write_review_reasons(); main.py:254 build_review_reasons(); desktop/report_loader.py:33 |
| Uygulama içi: material_efficiency_report.csv | [x] | - | intelligence/reporting.py:22 _write_material_efficiency(); main.py:255–259 analyze_material_efficiency(); desktop/report_loader.py:35 |
| Uygulama içi: production_summary_human_readable.txt | [x] | - | intelligence/reporting.py:24; desktop/report_loader.py:39 _read_text() |
| template_matching_report.csv | [x] | - | print_service.py:130 _write_template_matching_report(); settings.yaml:55 generate_template_matching_report: true |
| template_import_report.csv | [x] | - | desktop/template_importer.py:128 write_import_report() |
| Raporlar Klasörünü Aç | [x] | - | bridge.py:678 open_reports_folder(); webui_backend/file_api.py:40 open_reports_folder(); index.html raporlar sayfası |

**Sayfa durumu:** ●
**Notlar:** Tüm rapor dosyaları gerçek implementasyona sahip. KPI band (report_api.py metrics_payload) production_history.json üzerinden haftalık seri ve top-3 model hesaplıyor.

---

## 7. Ayarlar ●

| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Genel: output_date_format, language | [x] | - | settings.yaml:2–3; config_loader.py:57–59 AppConfig; settings_api.py load_config() |
| Excel: mode, input_file | [x] | - | settings.yaml:4–6; config_loader.py:61–63 ExcelSettings; settings_api.py save_config() |
| Print: mode, allow_direct_print | [x] | - | settings.yaml:10–16; config_loader.py:64–71 PrintSettings; settings_api.py:58–70 get_print_mode/set_print_mode() |
| Laser: auto_start_laser, output_format, plaka ölçüleri | [x] | - | settings.yaml:33–41; config_loader.py:95–104 LaserSettings; plate_width_mm, plate_height_mm, margin_mm, gap_x/y_mm |
| label_defaults (rulo etiket) | [x] | - | settings.yaml:18–32; config_loader.py:188–207 _load_label_defaults(); settings_api.py:43–55 get/save_label_defaults() |
| laser_text font ayarları | [x] | - | settings.yaml:42–50; config_loader.py:105–117 LaserTextSettings; laser_font_path, font_size, force_connected_letters |
| Güvensiz ayar açılırsa uyarı | [x] | - | config_loader.py:256–304 _validate_settings(); auto_print_enabled, allow_direct_print, auto_start_laser → ConfigError fırlatır (hard-block) |

**Sayfa durumu:** ●
**Notlar:** Güvensiz ayar pasif uyarı değil, hard-block — ConfigError ile uygulama başlamaz.

---

## 8. Nasıl Kullanırım ◐

| Özellik | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Adım adım kullanım akışı | [x] | - | index.html:846–853 6-adım bulk wizard stepper; index.html:91–122 Ana Sayfa workflow kartları (Etiket Studio / Toplu Etiket / Etiket Modelleri) |
| Güvenlik notları (manuel yazdırma, PDF kontrolü) | [x] | - | index.html:480 "Gerçek Render Kontrolü çalıştırın" notu; index.html:672 "Değerler RDWorks'e otomatik gönderilmez" notu; main.py güvenlik mesajları |
| Sık karşılaşılan durumlar (0 sipariş, eksik font...) | [~] | P2 | main.py:296–323 _print_summary() mesajlar; config_loader.py:138–143 font uyarısı; ancak UI'de ayrı "Yardım / Rehber" sayfası yok; index.html:816–826 helpCenterModal sadece klavye kısayollarını gösteriyor |

**Sayfa durumu:** ◐
**Notlar:** Yardım içeriği kısayol tablosu düzeyinde. Sık karşılaşılan durumlar (0 sipariş, eksik font, boş laser_text, wrong process_type) hata mesajı olarak çıktıya yazılıyor ama UI'de ayrı bir rehber sayfası yok.

---

## Özet Tablo

| Sayfa | Durum | P0 | P1 | P2 |
|---|---|---|---|---|
| 1. Genel Bakış | ● | 0 | 0 | 0 |
| 2. Excel | ● | 0 | 0 | 0 |
| 3. Kontrol | ● | 0 | 0 | 0 |
| 4. Etiket | ◐ | 0 | 0 | 2 |
| 5. Lazer | ◐ | 0 | 0 | 0 |
| 6. Raporlar | ● | 0 | 0 | 0 |
| 7. Ayarlar | ● | 0 | 0 | 0 |
| 8. Nasıl Kullanırım | ◐ | 0 | 0 | 1 |
| **Toplam** | | **0** | **0** | **3** |

---

## Test Sonuçları

```
python -m unittest discover -s tests
→ 250 PASSED, 7 FAILED

Başarı oranı: 250/257 (%97.3)

Başarısız testler — yalnızca playwright/browser smoke (playwright kurulu değil):
  - test_main_page_loads_without_errors
  - test_navigation_menu_clickable
  - test_reports_kpi_band_present
  - test_print_queue_bulk_pdf_workflow
  - test_dev_mode_toggle_hides_modules
  - test_api_state_endpoint_responds
  - test_api_metrics_endpoint_responds

Birim ve entegrasyon testlerinin tamamı (250) geçiyor.
```

---

## Ek Bulgular

### LASER_CUT SVG çıktısı — kasıtlı güvenlik stub'ı
`src/svg_generator.py:62–69` — CUT_LINES grubu `continue` ile boş bırakılıyor.
Güvenlik kararı: *"Cannot guarantee connected cursive vector paths/welded cut shape in MVP"*
LASER_CUT siparişleri errors_report.csv'ye yazılıp üretimden dışlanıyor.
**İsim Kesim Studio** (`nameCutStudio`) bu işlevi `combined_production_api.py` üzerinden DXF library + weld engine ile karşılıyor — bu yol production-ready.

### DXF Library sistemi aktif
`combined_production_api.py:65–73` — Leyla'nın hazırladığı DXF kütüphanesi primary source; operator-approved SVG/AI referans kütüphanesi fallback. `dxf_library_api.py` + `dxf_library_watcher.py` mevcut.

### P2 eksiklikler (4. Etiket sayfası)
1. **Altın çizgi göster/gizle + konum/genişlik/kalınlık/renk:** Veri modelinde mevcut (elements array'de rectangle elementi), Etiket Studio'da ayrı UI toggle butonu yok.
2. **Kenarlık göster/gizle + renk/kalınlık toggle:** Şablon JSON'da `stroke_color`, `stroke_width` alanları var ama Studio inspector'da ayrı kontrol yok.

### P2 eksiklik (8. Nasıl Kullanırım)
3. **Sık karşılaşılan durumlar UI rehberi:** helpCenterModal sadece klavye kısayollarını gösteriyor; 0 sipariş / eksik font / wrong process_type senaryoları için inline rehber yok.
