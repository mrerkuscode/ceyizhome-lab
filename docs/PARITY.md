# Cyzella Production Studio — Masaüstü ↔ Tarayıcı Parité Denetimi

> **Denetim tarihi:** 2026-05-30  
> **Denetleyen:** Claude Code (salt-okunur)  
> **Yöntem:** bridge.py (QWebChannel), routes.py (Flask), api_adapter.js karşılaştırmalı analizi

---

## Bölüm 1 — Ön-yüz Kopyaları

### Kaç ayrı HTML dosyası var?

**Bir tane.** `src/webui/index.html` (1 593 satır) — tek HTML dosyası.

| Mod | Nasıl yüklüyor? | Kaynak |
|---|---|---|
| Masaüstü (PySide) | `QWebEngineView.load(QUrl.fromLocalFile("…/src/webui/index.html?v=<timestamp>"))` | `desktop/web_main_window.py:154–159` |
| Tarayıcı (Flask) | `GET /` → `send_from_directory("src/webui", "index.html")` | `server/flask_app.py:33–35` |

**Aynı dosya, iki transport.** Tasarım ayrımı `api_adapter.js` (363 satır) ile yapılıyor:
`index.html` yüklendiğinde `window.qt` varsa Qt köprüsü, yoksa `window.cyzella = api_adapter` atanıyor.
`app.js` her zaman `bridge.METHOD(...)` çağırıyor; hangi nesne olduğunu bilmiyor.

```
Desktop:  index.html ──► app.js ──► bridge (window.qt → QWebChannel → Python Bridge)
Tarayıcı: index.html ──► app.js ──► bridge (window.cyzella → api_adapter.js → fetch /api/*)
```

---

## Bölüm 2 — Transport Yüzeyi Diff

### 2a. Sayısal özet

| Katman | Metod/Rota Sayısı |
|---|---|
| `bridge.py` — QWebChannel @Slot | ~155 metod |
| `routes.py` — Flask /api/ rotaları | 50 rota (12 GET + 38 POST) |
| `api_adapter.js` — tarayıcı şimi | ~50 gerçek impl + ~43 notImpl stub |

### 2b. Her iki modda çalışan özellikler (parite tam)

Bunlar `api_adapter.js`'de gerçek `fetch` implementasyonu olan ve `/api/` rotası bulunan metodlar.

| Yetenek | Bridge metodu | Flask rotası | api_adapter.js |
|---|---|---|---|
| Uygulama durumu | `get_status` | `GET /api/state` | `get_status` → fetch |
| KPI metrikleri | `metrics_payload` | `GET /api/metrics` | `metrics_payload` → fetch |
| Etiket çıktıları | `list_label_outputs` | `GET /api/label_outputs` | `list_label_outputs` → fetch |
| Baskı kuyruğu (oku) | `list_print_queue` | `GET /api/print_queue` | `list_print_queue` → fetch |
| Model galerisi | `list_label_model_gallery` | `GET /api/label_model_gallery` | `list_label_model_gallery` → fetch |
| Raporlar | `load_reports` | `GET /api/reports` | `load_reports` → fetch |
| Kuyruk öğesi işle | `mark_queue_item_printed/pending/delivered` | `POST /api/mark_queue_item_*` | eşleşiyor |
| Kuyruktan sil | `remove_from_print_queue` | `POST /api/remove_from_print_queue` | eşleşiyor |
| Kuyruğu temizle | `clear_print_queue` | `POST /api/clear_print_queue` | eşleşiyor |
| PDF kuyruğa ekle | `add_pdf_output_to_print_queue` | `POST /api/add_pdf_output_to_print_queue` | eşleşiyor |
| Etiket çıktılarını kuyruğa al | `add_label_outputs_to_print_queue` | `POST /api/add_label_outputs_to_print_queue` | eşleşiyor |
| Model alanı kaydet/ekle/sil | `save/add/remove_label_model_field` | `POST /api/*_label_model_field` | eşleşiyor |
| Rulo defaults kaydet | `save_label_defaults_json` | `POST /api/save_label_defaults_json` | eşleşiyor |
| Model varyant klon | `clone_label_model_variant` | `POST /api/clone_label_model_variant` | eşleşiyor |
| Baskı şablonu meta | `save_print_template_metadata` | `POST /api/save_print_template_metadata` | eşleşiyor |
| Ürün tanımı kaydet/arşiv/geri al | `productDefinitionSave/Archive/Restore` | `POST /api/productDefinition*` | eşleşiyor |
| Müşteri siparişi oluştur/güncelle | `create/update_customer_order` | `POST /api/create/update_customer_order*` | eşleşiyor |
| Üretim audit log | `append_production_audit_event` | `POST /api/append_production_audit_event` | eşleşiyor |
| Yedekleme oluştur/geri yükle | `create_backup`, `restore_backup` | `POST /api/create_backup`, `POST /api/restore_backup` | eşleşiyor |
| Trendyol eşleme kaydet | `upsert_trendyol_mapping` | `POST /api/upsert_trendyol_mapping` | eşleşiyor |
| Trendyol ayarları kaydet | `save_trendyol_settings` | `POST /api/save_trendyol_settings` | eşleşiyor |
| İsim kesim kuyruk durumu | `update_name_cut_queue_item_status` | `POST /api/update_name_cut_queue_item_status` | eşleşiyor |
| Canlı entegrasyon güvenlik ayarı | `save_live_integration_security_settings` | `POST /api/save_live_integration_security_settings` | eşleşiyor |
| Etiket arşiv/geri yükle | `archive/restore_label_outputs` | `POST /api/archive/restore_label_outputs` | eşleşiyor |
| Printer profili kaydet/sil | `save/delete_printer_profile` | `POST /api/save/delete_printer_profile` | eşleşiyor |
| Dry-run (async) | `run_dry_run` | `POST /api/start_run_dry` → job_id | `runDry` → fetch + poll |
| Job durumu/log | `cancel_running_job` | `GET /api/job_status`, `GET /api/job_log`, `POST /api/cancel_job` | `getJobStatus/Log/cancelJob` |
| Dosya yükle (multipart) | *(native dialog)* | `POST /api/upload_excel/font/design_visual/template_pack/label_preview` | `uploadExcel/Font/…` → fetch |

### 2c. Bridge'de var, tarayıcıda YOK (→ tarayıcıda ölü veya stub)

Bu metodlar `app.js`'de çağrılıyor ama `api_adapter.js`'de ya `notImpl` stub'ı var ya da hiç tanımlı değil.

#### 2c-i — notImpl stub (bridge?.method undefined veya NOT_IMPLEMENTED döner)

| Metod | Konu | Etki |
|---|---|---|
| `test_trendyol_connection` | Trendyol bağlantı testi | Buton tıklanır, "köprüsü hazır değil" uyarısı |
| `sync_trendyol_recent_orders` | Son N günü çek | Buton tıklanır, NOT_IMPLEMENTED |
| `select_excel` / `chooseExcel` | Native dosya seçici | Tarayıcıda yok → upload_excel multipart ile ikame mümkün |
| `run_production` / `runProduction` | Üretim başlat | NOT_IMPLEMENTED — tarayıcıda hiç üretim yok |
| `bulk_generate_and_add_to_queue` | Toplu kuyruğa al | NOT_IMPLEMENTED |
| `bulk_generate_selected_and_add_to_queue` | Seçili toplu | NOT_IMPLEMENTED |
| `render_manual_label` / `render_manual_label_fields` | Manuel etiket render | NOT_IMPLEMENTED |
| `render_manual_label_fields_to_queue` | Manuel etiket kuyruğa | NOT_IMPLEMENTED |
| `preview_manual_label_fields` | Önizleme | NOT_IMPLEMENTED |
| `preflight_manual_label_fields` | Preflight doğrulama | NOT_IMPLEMENTED |
| `validate_manual_label_output` | Çıktı doğrulama | NOT_IMPLEMENTED |
| `create_label_model_from_wizard` | Sihirbazdan model oluştur | NOT_IMPLEMENTED |
| `choose_new_label_model_design_visual` | Tasarım görseli seç | NOT_IMPLEMENTED |
| `choose_label_model_preview` | Önizleme görseli seç | NOT_IMPLEMENTED |
| `import_template_pack` / `importTemplatePack` | ZIP şablon paketi | NOT_IMPLEMENTED (web'de upload_template_pack var) |
| `import_label_font` | Font yükle | NOT_IMPLEMENTED (web'de upload_font var) |
| `validate_backup` | Yedek doğrulama | NOT_IMPLEMENTED |
| `export_production_audit_events` | Audit dışa aktar | NOT_IMPLEMENTED |
| `guard_live_integration_action` | Güvenlik onayı | NOT_IMPLEMENTED |
| `create_calibration_pdf` | Kalibrasyon PDF | NOT_IMPLEMENTED |
| Tüm `open_*_folder` / `openOutput` vb. | Klasör aç | NOT_IMPLEMENTED (beklenen) |
| `reveal_file_in_folder`, `open_file_safe` | OS dosya aç | NOT_IMPLEMENTED (beklenen) |
| `open_svg`, `open_project_file` | SVG/dosya aç | NOT_IMPLEMENTED (beklenen) |
| `quitApplication` | Uygulamayı kapat | NOT_IMPLEMENTED (beklenen) |
| `editTemplate`, `showHelp`, `showSettings` | Dialog aç | NOT_IMPLEMENTED (beklenen) |

#### 2c-ii — Hiç tanımlı değil (adapter'da stub bile yok, guard `undefined` yakalar)

| Metod | Konu | Beklenen davranış |
|---|---|---|
| `sync_trendyol_questions` | Soruları oku | `bridge?.sync_trendyol_questions` → undefined; app.js:5265 guard: "köprüsü hazır değil" |
| `dxfLibraryList/Search/Find/Refresh/…` (8 metod) | DXF kütüphanesi | Tüm DXF Studio fonksiyonu tarayıcıda sessiz fail |
| `productDefinitionGet/Search/ImportExcel/…` (5 metod) | Ürün tanımı oku | Okuma tarafı tarayıcıda yok |
| `listCorelReferences` ve 18 Corel ref metodu | Corel referans kütüphanesi | Tüm referans yönetimi tarayıcıda yok |
| `save_name_cut_queue_items` ve 6 isim kesim kuyruk metodu | İsim kesim kuyruğu | Tarayıcıda yok |
| `list_production_audit_events` ve 3 audit metodu | Audit log okuma | Tarayıcıda yok |
| `list_live_integration_registry`, `live_integration_security_settings` | Canlı entegrasyon | Tarayıcıda yok |
| `approve_trendyol_mapping_suggestion` ve 9 Trendyol iş akışı metodu | Trendyol eşleme onayı | Tarayıcıda yok |
| `prepare_name_cut_files`, `preview_name_cut_paths`, `build_name_cut_production_scene` | İsim kesim üretim | Tarayıcıda yok |
| `get_pdf_preview_payload` | PDF önizleme | Tarayıcıda yok |
| `print_queue_item_safe`, `set_default_printer_profile`, `test_printer_profile`, `prepare_manual_print` | Yazıcı kontrolü | Tarayıcıda yok |
| `list_backups`, `export_backup_manifest` | Yedek listesi/manifest | Tarayıcıda yok |
| `list_laser_outputs` | Lazer çıktıları | Tarayıcıda yok |
| `run_native_edit_poc`, `native_edit_diagnostics`, `open_native_edit_report` | Native edit | Tarayıcıda yok (beklenen) |
| `render_bulk_preview_samples`, `prepare_selected_bulk_excel` | Toplu önizleme | Tarayıcıda yok |
| `list_label_templates`, `list_label_model_backups`, `compare/restore_label_model_backup` (7 metod) | Template yönetimi | Tarayıcıda yok |
| `list_print_templates`, `get_print_template_detail`, `create_linked_label_design` | Baskı şablonu okuma | Tarayıcıda yok |
| `create_customer_order_summary_pdf` | Sipariş PDF özeti | Tarayıcıda yok |

### 2d. Flask /api/'de var ama bridge'de karşılığı olmayan (tarayıcı artığı)

| Rota | Açıklama | Not |
|---|---|---|
| `POST /api/upload_excel` | Multipart Excel yükleme | Desktop native dialog ile yapıyor; bu rota browser-only |
| `POST /api/upload_font` | Font yükleme | Desktop `import_label_font` (native dialog); bu rota browser-only |
| `POST /api/upload_design_visual` | Görsel yükleme | Desktop native dialog; bu rota browser-only |
| `POST /api/upload_template_pack` | Şablon ZIP yükleme | Desktop `import_template_pack` (native dialog); bu rota browser-only |
| `POST /api/upload_label_preview` | Etiket önizleme yükleme | Desktop native dialog; bu rota browser-only |
| `POST /api/start_render_labels` (async job) | Label render (async + job_id) | Desktop senkron bridge çağrısı kullanıyor; bu rota browser-only |
| `POST /api/start_run_dry` (async job) | Dry-run (async + job_id) | Desktop senkron çağrı; bu rota browser-only |
| `GET /api/job_status/<id>`, `GET /api/job_log/<id>`, `POST /api/cancel_job/<id>` | Arkaplan iş yönetimi | Desktop sinyallerle yapıyor; bu rotalar browser-only |

### 2e. Üç özel özellik — detay

| Özellik | Desktop | Tarayıcı | Neden çalışmıyor? |
|---|---|---|---|
| **Bağlantıyı Test Et** | ✅ Tam çalışıyor | ❌ notImpl stub | `api_adapter.js:331` notImpl listesinde; `/api/test_trendyol_connection` rotası yok; `trendyol_api.py:186` controller metodu hazır |
| **Son 7 Günü Çek** | ✅ Tam çalışıyor | ❌ notImpl stub | `api_adapter.js:331` notImpl listesinde; `/api/sync_trendyol_recent_orders` rotası yok; `trendyol_api.py:221` controller metodu hazır |
| **Soruları Oku** | ✅ Tam çalışıyor | ❌ stub bile yok | `api_adapter.js`'de hiç tanımlı değil; `bridge?.sync_trendyol_questions` undefined → `app.js:5265` guard "köprüsü hazır değil"; `/api/sync_trendyol_questions` rotası yok; `trendyol_api.py:383` controller metodu hazır |

**Ortak pattern:** Üç özellik de aynı nedenle tarayıcıda çalışmıyor — Flask rotası eksik. Python controller kodları (`trendyol_api.py`) zaten var; sadece `routes.py`'ye 3 rota ve `api_adapter.js`'e 3 fetch fonksiyonu eklenmesi yeterli.

---

## Bölüm 3 — Native-Only İşlemler (Bilinçli İstisna Adayları)

Bunlar masaüstünde yerel OS kaynaklarına erişim gerektirdiğinden tarayıcıda karşılığı olamaz veya bilinçli olarak tarayıcıya açılmamalı.

| Operasyon | Bridge metodu | Neden native-only | Öneri |
|---|---|---|---|
| Dosya seçici (Excel) | `select_excel` | OS native dialog | `/api/upload_excel` multipart ile ikame edilmiş ✅ |
| Klasör aç (output/input/print/laser) | `open_*_folder` | `os.startfile()` / `subprocess` | Tarayıcıda "Çıktılar" sayfasındaki `GET /api/files/` ile dosyalara erişilebiliyor |
| Dosyayı OS ile aç | `open_file_safe`, `open_svg` | `os.startfile()` | Tarayıcı yeni sekmede PDF/SVG açabilir (`GET /api/files/<path>`) |
| Dosyayı Explorer'da göster | `reveal_file_in_folder` | `subprocess explorer /select,` | Tarayıcıda anlamlı karşılığı yok |
| Native yazıcı komutu | `print_queue_item_safe` | Win32 print spooler | Tarayıcıda PDF indirip manuel yazdırma akışı |
| Font yükle (dialog) | `import_label_font` | OS dialog | `/api/upload_font` ile ikame edilmiş ✅ |
| Uygulamayı kapat | `quitApplication` | `QApplication.quit()` | Tarayıcıda anlamsız |
| Dialog açma (`editTemplate`, `showHelp`, `showSettings`) | bridge dialog çağrıları | Qt native dialog | Tarayıcıda HTML modal ile ikame edilebilir |
| ZIP/CDR şablon import (dialog) | `import_template_pack` | OS dialog | `/api/upload_template_pack` ile ikame edilmiş ✅ |
| QWebChannel sinyalleri | `stateChanged`, `logChanged` | Qt signal sistemi | `api_adapter.js`'de no-op stub var; tarayıcı polling veya SSE ile ikame edebilir |
| Native edit (SVG native renderer) | `run_native_edit_poc` | Win32/native renderer | Araştırma aşamasında, tarayıcı karşılığı planlanmamış |
| DXF kütüphane izleyici | `dxfLibraryStartWatcher` | OS filesystem watcher | Masaüstüne özgü; tarayıcı için polling yeterli olabilir |

---

## Bölüm 4 — "Tek Yerden Değişiklik" Önerisi

### Mevcut mimari neden iyi

Bridge → Controller → Business logic zinciri doğru kurulmuş. `trendyol_api.py`, `web_main_window.py:controller.*` gibi methodlar zaten her iki modda paylaşılabilir durumda. `routes.py` da aynı controller nesnelerini çağırıyor (örn. `routes.py:409` `save_trendyol_settings` → aynı service). Yani Python kodu değişmeden ikame mümkün.

### Tek yerden eklenebilecek en küçük yol

**Kategori A — Düşük efor, yüksek etki (3 Trendyol özelliği):**

```
routes.py → 3 yeni rota ekle:
  POST /api/test_trendyol_connection   → controller.test_trendyol_connection()
  POST /api/sync_trendyol_recent_orders → controller.sync_trendyol_recent_orders(days)
  POST /api/sync_trendyol_questions    → controller.sync_trendyol_questions()

api_adapter.js → 3 fetch fonksiyonu ekle (aynı notImpl stilinde ama gerçek fetch):
  test_trendyol_connection(cb)
  sync_trendyol_recent_orders(days, cb)
  sync_trendyol_questions(cb)
```

Controller metodları `web_main_window.py:1667/1673/1709`'da zaten var. 6 değişiklik, 3 özellik kazanılır.

**Kategori B — Orta efor, kritik eksik (üretim başlatma):**

`run_production` tarayıcıda yokken `/api/start_run_dry` zaten async job pattern kullanıyor.
`/api/start_production` aynı pattern ile `controller.run_production()` çağırılabilir.
`api_adapter.js`'deki notImpl stub gerçek fetch'e dönüştürülür.

**Kategori C — Büyük yüzey (DXF, Corel ref, isim kesim):**

Bu 40+ metod masaüstü-yoğun iş akışları. Tarayıcıya açmak yerine masaüstü zorunlu kabul edilebilir — zaten üretim ortamı masaüstü. Bilinçli istisna olarak dokümante edilmeli.

**Kategori D — Sinyal eksikliği (`stateChanged`):**

Masaüstünde Python → JS push var. Tarayıcıda `api_adapter.js` `stateChanged.connect` no-op'tur; tarayıcı durum değişikliklerini polling yapıyor (`/api/state`). Eğer gerçek zamanlı UI güncellemesi gerekiyorsa SSE (`/api/events` stream) en küçük ek.

### Özet öncelik sırası

| Öncelik | Değişiklik | Etkilenen dosya sayısı | Kazanç |
|---|---|---|---|
| P1 | 3 Trendyol rotası + adapter | 2 dosya (routes.py, api_adapter.js) | Trendyol 3 özelliği |
| P1 | `run_production` async rota + adapter | 2 dosya | Tarayıcıda üretim başlatma |
| P2 | `list_backups`, `validate_backup` rotası | 2 dosya | Yedek yönetimi |
| P2 | `list_laser_outputs` rotası | 2 dosya | Lazer çıktı listesi |
| P3 | DXF kütüphane GET rotaları | 2 dosya | DXF Studio tarayıcı read-only |
| istisna | `open_*_folder`, `reveal_file_in_folder` | — | Native-only, tarayıcıda anlamsız |
| istisna | Corel ref, native edit | — | Masaüstü iş akışı; tarayıcı hedefi değil |

---

## Ek — Teknik Referans

| Dosya | Satır | Rol |
|---|---|---|
| `src/webui/index.html` | 1 593 | Tek paylaşılan HTML |
| `src/webui/app.js` | ~21 500 | Tüm UI mantığı; `bridge.METHOD()` çağrıları |
| `src/webui/api_adapter.js` | 363 | Tarayıcı şimi; `window.cyzella` olarak yükleniyor |
| `src/webui_backend/bridge.py` | 1 007 | ~155 QWebChannel @Slot |
| `src/server/routes.py` | 572 | 50 Flask rotası |
| `src/server/flask_app.py` | 51 | Uygulama fabrikası + kök rotalar |
| `src/desktop/web_main_window.py` | — | `QWebEngineView` kurulumu + controller |
| `src/intelligence/trendyol_api.py` | — | Trendyol API implementasyonu (her iki modda paylaşılabilir) |
