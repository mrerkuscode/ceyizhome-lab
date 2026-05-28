# Browser Mode — Mimari Analiz ve Strateji Önerisi
**Tarih:** 2026-05-28 | **Durum:** Sadece okuma, kod değiştirilmedi

---

## 1. MEVCUT MİMARİ

```
[Leyla - Masaüstü]
        │
        ▼
[start_app.bat]
        │
        ▼
[src/desktop/app.py]  ← QApplication başlatır
        │
        ▼
[WebMainWindow]  ← QMainWindow, 1500×900, "CeyizHome Lab"
        │
        ├── QWebEngineView  ← file:// ile index.html yükler
        │       │                (src/webui/index.html — 3871 satır)
        │       │                (src/webui/app.js    — 21391 satır, tek dosya)
        │       │
        │       ▼
        │   [qrc:///qtwebchannel/qwebchannel.js]  ← Qt'nin dahili JS kütüphanesi
        │   [new QWebChannel(qt.webChannelTransport, ...)]  ← app.js satır 21269
        │
        ├── QWebChannel  ← "cyzella" adıyla register edildi
        │
        └── WebBridge(QObject)  ← src/webui_backend/bridge.py
                │
                ├── 187 @Slot (yaklaşık 95 işlevsel, kalanlar alias)
                │
                ├── controller (WebMainWindow) üzerinden:
                │       ├── report_api.py      ← CSV raporları okur
                │       ├── label_api.py       ← PDF/PNG üretir
                │       ├── template_api.py    ← JSON şablon R/W
                │       ├── print_queue_api.py ← data/print_queue.json R/W
                │       ├── production_audit_api.py
                │       ├── trendyol_api.py
                │       ├── backup_api.py
                │       ├── dxf_library_api.py
                │       ├── product_definitions_api.py
                │       └── ... (toplam 20 API modülü)
                │
                └── CommandWorker  ← src/main.py alt süreç olarak çalıştırır
```

**HTML yükleme yöntemi:** `QUrl.fromLocalFile(str(html_path))` → `file:///...src/webui/index.html`  
**Pencere:** `setWindowTitle("CeyizHome Lab")` · `resize(1500, 900)` · `setMinimumSize(1180, 720)`  
**CSS:** Plain CSS (`styles.css`) — Tailwind/Bootstrap yok  
**JS modül yapısı:** Global fonksiyonlar + tek büyük IIFE bloğu — ES modül yok  
**Kritik asset:** `qrc:///qtwebchannel/qwebchannel.js` — **Qt'ye özgü, browser'da yoktur**

---

## 2. BRIDGE @SLOT ENVANTERİ (İşlevsel Gruplar)

### Grup A — Durum & Veri Okuma (Browser'da KOLAY geçer)
| Slot | Param | Return | İş |
|---|---|---|---|
| `get_status` / `initialState` | — | str(JSON) | Tam state blob döner (~30 alan) |
| `dxfLibraryList` | — | str | DXF kütüphane listesi |
| `dxfLibrarySearch` | query:str | str | DXF arama |
| `productDefinitionsList` | include_archived:bool | str | Ürün tanım listesi |
| `productDefinitionGet` | sku:str | str | Tekil ürün tanımı |
| `productDefinitionsSearch` | query:str | str | Ürün arama |
| `list_label_templates` | — | str | Şablon JSON listesi |
| `list_label_model_gallery` | — | str | Etiket model galerisi |
| `list_label_outputs` | — | str | Çıktı PDF/PNG listesi |
| `list_archived_label_outputs` | — | str | Arşivlenmiş çıktılar |
| `list_print_queue` | — | str | Yazdırma kuyruğu |
| `list_laser_outputs` | — | str | Lazer çıktıları |
| `list_backups` | — | str | Yedek listesi |
| `list_production_audit_events` | filters_json:str | str | Audit log olayları |
| `list_production_audit_summary` | — | str | Audit özet |
| `load_reports` | — | str | CSV rapor özeti |
| `list_svg_files` | — | str | SVG dosya listesi |
| `metrics_payload` | date_range_json:str | str | KPI metrikleri |
| `list_print_templates` | — | str | Baskı şablonları |
| `list_label_model_backups` | template_path:str | str | Model yedekleri |
| `list_name_cut_queue_items` | filters_json:str | str | İsim kesim kuyruğu |
| `list_name_cut_transfer_history` | — | str | Transfer geçmişi |
| `live_integration_security_settings` | — | str | Güvenlik ayarları |
| `get_pdf_preview_payload` | relative_path:str | str | PDF önizleme |

### Grup B — Yazma / Durum Güncelleme (Browser'da REST ile geçer)
| Slot | Param | Return | İş |
|---|---|---|---|
| `save_label_model_field` | template_path, index, payload | str | Yazı alanı kaydeder |
| `add_label_model_field` | template_path, field_type | str | Yeni alan ekler |
| `remove_label_model_field` | template_path, index | str | Alan siler |
| `productDefinitionSave` | payload_json | str | Ürün tanımı kaydeder |
| `productDefinitionArchive` | sku | str | Ürün arşivler |
| `create_customer_order` | payload | str | Sipariş oluşturur |
| `update_customer_order_status` | order_id, status | str | Sipariş durumu günceller |
| `append_production_audit_event` | payload_json | str | Audit olay ekler |
| `mark_queue_item_printed` | item_id | str | Yazdırıldı işaretler |
| `mark_queue_item_pending` | item_id | str | Beklemede işaretler |
| `mark_queue_item_delivered` | item_id | str | Teslim edildi işaretler |
| `remove_from_print_queue` | item_id | str | Kuyruktan çıkarır |
| `save_printer_profile` | profile_json | str | Yazıcı profili kaydeder |
| `delete_printer_profile` | profile_id | str | Yazıcı profili siler |
| `upsert_trendyol_mapping` | payload | str | Trendyol eşleşme kaydeder |
| `save_trendyol_settings` | payload | str | Trendyol API ayarları |
| `update_name_cut_queue_item_status` | item_id, status | str | İsim kesim durum günceller |
| `save_live_integration_security_settings` | payload_json | str | Güvenlik ayarları kaydeder |
| `create_backup` | — | str | Yedek alır |
| `restore_backup` | backup_path, dry_run | str | Yedek geri yükler |
| `save_label_defaults_json` | payload | str | Etiket varsayılanları kaydeder |

### Grup C — QFileDialog Gerektiren (Browser'da ENGEL)
| Slot | Tetiklediği Dialog | Browser Alternatifi |
|---|---|---|
| `chooseExcel` / `select_excel` | Excel dosyası seç | `<input type="file">` + HTTP upload |
| `importTemplatePack` | ZIP/CDR/AI/PDF şablon | `<input type="file">` + HTTP upload |
| `choose_new_label_model_design_visual` | PNG/JPG/SVG görsel | `<input type="file">` + HTTP upload |
| `choose_label_model_preview` | PNG/JPG önizleme | `<input type="file">` + HTTP upload |
| `import_label_font` | TTF/OTF font | `<input type="file">` + HTTP upload |
| `import_trendyol_mappings` | JSON eşleşme | `<input type="file">` + HTTP upload |

### Grup D — OS İşlemleri / Subprocess (Browser'da TASARIM GEREKTİRİR)
| Slot | OS Bağımlılığı | Browser Alternatifi |
|---|---|---|
| `run_dry_run` / `run_production` | `src/main.py` subprocess (CommandWorker) | Server-side subprocess; SSE/WS ile log akışı |
| `render_labels` / `bulk_generate_*` | subprocess + PDF üretimi | Server-side async job |
| `render_manual_label_fields` | PDF/PNG → lokal output/ | Server-side render; indirme linki |
| `open_output_folder` / `open_*_folder` | `os.startfile()` Windows | Download link / dosya tarayıcı UI |
| `reveal_file_in_folder` | Windows Explorer | N/A (masaüstü-spesifik) |
| `quitApplication` | QApplication.quit() | Sayfa kapat / N/A |
| `create_customer_order_summary_pdf` | PDF oluştur + yerel kaydet | HTTP response ile indir |
| `test_trendyol_connection` | HTTP → dış API | Server-side proxy |
| `sync_trendyol_recent_orders` | HTTP → dış API | Server-side proxy |

---

## 3. BROWSER MODE ENGELLERİ

| Engel | Açıklama | Öncelik |
|---|---|---|
| `qrc:///qtwebchannel/qwebchannel.js` | Qt dahili resource — browser'da **tamamen yoktur** | KRİTİK |
| `QWebChannel / qt.webChannelTransport` | Qt protokolü — REST/WS ile değiştirilmeli | KRİTİK |
| `QFileDialog` (8 yer) | Natif OS dialog — browser file API ile değişmeli | ORTA |
| `os.startfile()` (3 yer) | Windows Explorer açma — N/A browser | DÜŞÜK |
| `QMessageBox` (15+ yer) | Onay dialogları — `confirm()` veya UI modal ile değişmeli | ORTA |
| `file:// preview URL`'leri | `label_api.py` PNG'yi file:// ile döner — HTTP endpoint gerekir | ORTA |
| `CommandWorker` (subprocess) | İş süreçleri arka planda çalışır; browser için async job + SSE gerekir | YÜKSEK |
| PDF/PNG output/ yolu | Çıktılar `production-bot/output/` altında — server üzerinden serve edilmeli | ORTA |

---

## 4. 3 STRATEJİ KARŞILAŞTIRMA

| Kriter | A: Statik Flask | B: Flask REST API | C: FastAPI + WebSocket |
|---|---|---|---|
| **Geliştirme süresi** | ~2 saat | ~1-2 gün | ~2-3 gün |
| **Tam fonksiyonalite** | ❌ Sadece görüntüleme | ✅ Tüm Slot → Route | ✅ Tüm Slot → Route |
| **Real-time log** | ❌ | ❌ (polling ile çözülür) | ✅ WebSocket stream |
| **PDF render/indir** | ❌ | ✅ server-side | ✅ server-side |
| **Dosya upload** | ❌ | ✅ multipart | ✅ multipart |
| **Masaüstü modu etkilenir** | ✅ SIFIR etki | ✅ SIFIR etki | ✅ SIFIR etki |
| **Bakım yükü** | Tek yol (statik) | +1 Flask modül | +1 FastAPI modül |
| **Mevcut bridge reuse** | ❌ | ✅ sınıf doğrudan import | ✅ sınıf doğrudan import |
| **Subprocess/job yönetimi** | ❌ | Polling + endpoint | SSE/WS ile gerçek zamanlı |

**Strateji A (Statik):** index.html + app.js'i Flask ile serve eder. `window.cyzella` objesi boş kalır, QWebChannel olmaz. Tıklamalar çalışmaz. Yalnızca statik görüntü.

**Strateji B (Flask REST):** `WebMainWindow` controller'ını aynen import eder. Her `@Slot` → `@app.route` olur. `window.cyzella.methodName(arg)` → `fetch('/api/methodName', {body: arg})` olarak rewrite edilir.

**Strateji C (FastAPI + WS):** B'nin üzerine WebSocket ekler. `CommandWorker` log'larını gerçek zamanlı browser'a iter. Karmaşıklık artar, gerçek zamanlı log akışı gerekiyorsa tercih edilir.

---

## 5. ÖNERİLEN STRATEJİ: **B — Flask REST API**

### Gerekçe

1. **Controller kodu doğrudan reuse:** `WebMainWindow` içindeki tüm iş mantığı (`label_api`, `print_queue_api`, `template_api` vb.) PySide6 olmadan da çalışır. Flask endpoint'leri aynı Python metodlarını çağırır — kod tekrarı sıfır.

2. **Masaüstü modu korunur:** `start_app.bat` → `src.desktop.app` değişmez. Yeni `src/server/flask_app.py` tamamen ayrı başlar. İki mod bağımsız.

3. **En düşük riskli MVP:** Sadece iki değişiklik gerekir: (a) `src/server/flask_app.py` yeni dosya; (b) `src/webui/app.js`'de `window.cyzella.*` çağrılarını `fetch('/api/*')` ile proxy'leyen ince bir adapter katmanı. Mevcut JS mantığı değişmez.

### Hangi Slot'lar ÖNCE Dönüştürülmeli (Öncelik Sırası)

**Sprint 1 — Temel (2-4 saat):**
1. `GET /api/state` → `get_status()` — tüm state bir kerede
2. `GET /api/metrics` → `metrics_payload()` — KPI paneli (Visual Reporting hedefi)
3. `GET /api/label_outputs` → `list_label_outputs()`
4. `GET /api/print_queue` → `list_print_queue()`
5. `GET /api/label_model_gallery` → `list_label_model_gallery()`
6. `GET /api/reports` → `load_reports()`
7. Statik dosya serve: `output/**` → `GET /files/<path>` (PDF/PNG önizleme için)

**Sprint 2 — Yazma işlemleri (yarım gün):**
8. `POST /api/mark_printed` → `mark_queue_item_printed()`
9. `POST /api/save_label_model_field` → `save_label_model_field()`
10. `POST /api/product_definition_save` → `productDefinitionSave()`

**Sonra (Sprint 3+):**
- Dosya upload endpoint'leri (Excel, şablon, font)
- Subprocess job yönetimi (render_labels, run_dry)
- Audit log yazma

### Hangileri SONRA Yapılabilir

- `chooseExcel`, `importTemplatePack`, `import_label_font` → dosya upload akışı ayrı tasarım gerektirir
- `run_production`, `render_labels` → subprocess + job ID + polling endpoint
- `reveal_file_in_folder`, `quitApplication` → masaüstüne özel, browser'da kaldırılır

---

## 6. RİSK DEĞERLENDİRMESİ

| Risk | Düzey | Önlem |
|---|---|---|
| Masaüstü modunun bozulması | **SIFIR** | `start_app.bat` ve `src.desktop.app` dokunulmaz; Flask ayrı süreç |
| Browser'da çalışmayacak özellikler (MVP) | Orta | Lazer modülü, QFileDialog, os.startfile() — tarayıcıda devre dışı bırakılır |
| Bakım yükü (iki kod yolu) | Düşük | Controller katmanı ortaktır; sadece bridge wrapper farklı |
| `qrc://` QWebChannel kaldırılması | Planlama gerekir | app.js'deki `new QWebChannel(...)` bloğu → `window.cyzella = new ApiAdapter()` ile değiştirilir |
| File path güvenliği (path traversal) | Orta | Flask'ta aynı `_resolve_audit_safe_path()` mantığı uygulanmalı |
| PDF/PNG URL'leri (`file://` → `http://`) | Planlama gerekir | `label_api.py` `preview_url` dönerken `file://` yerine `/files/...` döndürmeli |

**Masaüstü modunun bozulma riski = SIFIR.** Tüm PySide6 kodu korunur. Flask modu ayrı bir başlatma komutuyla gelir.
