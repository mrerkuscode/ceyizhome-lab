# Browser Mode Sprint 1 — Flask REST MVP Raporu
**Tarih:** 2026-05-28 | **Sonuç:** BAŞARILI — 10/10 test PASS

---

## Oluşturulan Dosyalar

| Dosya | Amaç |
|---|---|
| `src/server/__init__.py` | Python package işareti (boş) |
| `src/server/flask_app.py` | Flask uygulaması, port 8000 |
| `src/server/routes.py` | 7 GET endpoint + dosya serve Blueprint |
| `src/server/controller_proxy.py` | PySide6'sız API çağrı katmanı |
| `src/webui/api_adapter.js` | `window.cyzella` fetch-based adapter |
| `src/webui/index.html` | +5 satır eklendi (adapter yükleme + bridge wiring) |
| `start_browser_mode.bat` | Çift tık ile browser modu başlatır |
| `tests/test_flask_endpoints.py` | 10 pytest testi |
| `requirements.txt` | `flask>=3.0` eklendi |

**Değiştirilmeden bırakılan dosyalar:**
- `src/webui/app.js` (21391 satır) — DOKUNULMADI
- `src/webui_backend/bridge.py` — DOKUNULMADI
- `src/desktop/app.py` — DOKUNULMADI
- `start_app.bat` — DOKUNULMADI
- Tüm mevcut `.py` kaynak dosyaları — DOKUNULMADI

---

## Eklenen 7 Endpoint

| Method | URL | Fonksiyon | Kaynak |
|---|---|---|---|
| GET | `/api/state` | Tam state JSON | `controller_proxy.get_state()` |
| GET | `/api/metrics` | KPI metrikleri | `report_api.metrics_payload()` |
| GET | `/api/label_outputs` | Etiket çıktı listesi | `label_api.list_label_outputs()` |
| GET | `/api/print_queue` | Yazdırma kuyruğu | `print_queue_api.list_print_queue()` |
| GET | `/api/label_model_gallery` | Etiket model galerisi | `template_api.list_label_model_gallery()` |
| GET | `/api/reports` | Rapor özeti | `report_api.report_payload()` |
| GET | `/api/files/<path>` | output/ klasörü statik dosyalar | `send_from_directory()` |

Ayrıca:
- `GET /` → `index.html` serve eder
- `GET /<filename>` → tüm webui asset'leri serve eder (CSS, JS, font)
- `GET /api_adapter.js` → fetch-based bridge adapter

---

## Pytest Sonuçları: 10/10 PASS

```
tests/test_flask_endpoints.py::test_state_endpoint               PASSED
tests/test_flask_endpoints.py::test_metrics_endpoint_default     PASSED
tests/test_flask_endpoints.py::test_metrics_endpoint_with_range  PASSED
tests/test_flask_endpoints.py::test_label_outputs_endpoint       PASSED
tests/test_flask_endpoints.py::test_print_queue_endpoint         PASSED
tests/test_flask_endpoints.py::test_label_model_gallery_endpoint PASSED
tests/test_flask_endpoints.py::test_reports_endpoint             PASSED
tests/test_flask_endpoints.py::test_root_returns_html            PASSED
tests/test_flask_endpoints.py::test_adapter_js_served            PASSED
tests/test_flask_endpoints.py::test_files_path_traversal_blocked PASSED

10 passed in 0.40s
```

---

## Teknik Notlar

**PySide6 server context'te çalışıyor mu?**
Evet. `QColor`, `QImage`, `QPainter` import'ları Windows'ta display olmadan sorunsuz çalışır. `QApplication` oluşturulmadığı için GUI widget'lar açılmaz — sadece veri API'ları çağrılır.

**`initBridge()` (app.js satır 21266) mekanizması:**
`typeof QWebChannel === "undefined" || !window.qt` kontrolü browser'da true olur → erken return. Bridge null kalırdı. Çözüm: index.html sonuna eklenen inline `<script>` `bridge = window.cyzella` atar ve `refreshState()` çağırır.

**Masaüstü modu etkilendi mi?**
Hayır. Desktop modunda `window.qt` tanımlı → inline script if koşulu false olur → bridge QWebChannel üzerinden set edilir (mevcut davranış korunur). `api_adapter.js` desktop modunda yüklense de `window.cyzella`'yı set eder ama bridge değişkeni hemen üzerine yazılır.

---

## Bilinen Sınırlar (Sprint 2+ için)

| Özellik | Durum |
|---|---|
| 180 POST/yazma endpoint | ❌ Sprint 2 |
| Excel seçme (QFileDialog) | ❌ Sprint 3 — `<input type=file>` + upload |
| render_labels, run_production | ❌ Sprint 3 — server-side subprocess + SSE |
| Yazıcı entegrasyonu | ❌ Masaüstü-spesifik |
| os.startfile() (klasör aç) | ❌ Browser'da N/A |

---

## Çalıştırma Komutu

**Browser modu — çift tık:**
```
production-bot\start_browser_mode.bat
```

**Terminal:**
```
cd "production-bot"
.venv\Scripts\python.exe -m src.server.flask_app
```

Sonra tarayıcıda: **http://localhost:8000**

**Masaüstü modu (değişmedi):**
```
production-bot\start_app.bat
```

---

## Beklenenler (Tarayıcıda)

- CeyizHome Lab arayüzü görsel olarak yüklenir (HTML + CSS + JS)
- Etiket modeli galerisi görünür
- Raporlar sayfasında readiness durumu görünür
- KPI metrikleri `/api/metrics` üzerinden çalışır
- Tıklama/yazma işlemleri (üretim, Excel seç) Sprint 2+ beklenir
