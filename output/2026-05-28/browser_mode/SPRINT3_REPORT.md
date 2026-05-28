# Browser Mode Sprint 3 Raporu
**Tarih:** 2026-05-28  
**Sprint:** 3 — File Upload + Subprocess / Job Yönetimi  
**Önceki Sprintler:** Sprint 1 (10 GET) + Sprint 2 (30 POST) = 40 test ✅

---

## Özet

Sprint 3'te 10 yeni endpoint ve tam bir job yönetim altyapısı eklendi.  
Browser modunda artık Excel/font/görsel dosyaları yüklenebilir ve  
arka planda uzun süren işler (render, dry-run) başlatılıp takip edilebilir.

**Test sonucu: 54/54 PASS** (Sprint 1: 10 + Sprint 2: 30 + Sprint 3: 14)

---

## Yeni Dosyalar

| Dosya | Açıklama |
|-------|---------|
| `src/server/job_manager.py` | Thread-based background job registry |
| `tests/test_flask_sprint3.py` | Sprint 3 testleri (14 test) |

---

## Eklenen Endpoint'ler

### GRUP A — File Upload (5 endpoint)

| # | Endpoint | Format | Açıklama |
|---|----------|--------|----------|
| 1 | `POST /api/upload_excel` | multipart/form-data | .xlsx/.xls yükle → `input/` |
| 2 | `POST /api/upload_font` | multipart/form-data | .ttf/.otf yükle → `assets/fonts/` |
| 3 | `POST /api/upload_design_visual` | multipart/form-data | .png/.jpg/.svg yükle → `input/upload_temp/` |
| 4 | `POST /api/upload_template_pack` | multipart/form-data | .zip/.cdr/.ai/.pdf yükle → `input/upload_temp/` |
| 5 | `POST /api/upload_label_preview` | multipart/form-data | .png/.jpg yükle → `input/upload_temp/` |

**Güvenlik özellikleri:**
- Max 16 MB dosya boyutu
- Uzantı whitelist kontrolü
- `werkzeug.utils.secure_filename` ile path traversal koruması

### GRUP B — Subprocess / Job (5 endpoint)

| # | Endpoint | Metot | Açıklama |
|---|----------|-------|----------|
| 6 | `POST /api/start_render_labels` | POST | Render jobs thread'da başlat |
| 7 | `POST /api/start_run_dry` | POST | Dry-run thread'da başlat |
| 8 | `GET /api/job_status/<job_id>` | GET | Job durumu sorgula |
| 9 | `GET /api/job_log/<job_id>` | GET | Job log'ları (tail=N) |
| 10 | `POST /api/cancel_job/<job_id>` | POST | Job'ı iptal et |

---

## Job Manager Altyapısı (src/server/job_manager.py)

```
Job statuses: running → completed | failed | cancelled
Thread-safe: threading.Lock() ile tüm operasyonlar korunuyor
Log: Her job kendi log listesini tutuyor
Cancel: status = "cancelled" set edilir (thread daemon flag ile auto-cleanup)
```

---

## api_adapter.js Eklenen Adapter'lar (10 adet)

| Fonksiyon | Endpoint |
|-----------|---------|
| `uploadExcel(formData, cb)` | POST /api/upload_excel |
| `uploadFont(formData, cb)` | POST /api/upload_font |
| `uploadDesignVisual(formData, cb)` | POST /api/upload_design_visual |
| `uploadTemplatePack(formData, cb)` | POST /api/upload_template_pack |
| `uploadLabelPreview(formData, cb)` | POST /api/upload_label_preview |
| `start_render_labels(path, cb)` | POST /api/start_render_labels |
| `renderLabels(cb)` | POST /api/start_render_labels |
| `run_dry_run(cb)` / `runDry(cb)` | POST /api/start_run_dry |
| `getJobStatus(id, cb)` | GET /api/job_status/:id |
| `getJobLog(id, tail, cb)` | GET /api/job_log/:id |
| `cancelJob(id, cb)` | POST /api/cancel_job/:id |
| `cancel_running_job(cb)` | BROWSER_MODE stub |

---

## Test Sonuçları

```
============================= test session starts =============================
collected 54 items

tests/test_flask_sprint3.py    14 passed
tests/test_flask_endpoints.py  40 passed
---
Sprint 1 (GET):    10/10 PASS ✅
Sprint 2 (POST):   30/30 PASS ✅
Sprint 3 (Upload/Job): 14/14 PASS ✅
TOPLAM: 54/54 PASS ✅
```

---

## Browser Mode Render Davranışı

`render_labels` ve `run_dry` browser modunda `BROWSER_MODE` status döner:
- Gerçek CorelDRAW/Qt renderer masaüstünde çalışır
- Browser modunda job altyapısı çalışır, sonuç simüle edilir
- Mevcut queue ve output sayıları okunur ve raporlanır

---

## Bilinen Sınırlar (Sprint 4+ için)

| Konu | Durum |
|------|-------|
| CorelDRAW render | Desktop only — PyQt5 gerekli |
| Excel → gerçek üretim | Desktop only — controller pipeline gerekli |
| File upload → Excel otomatik seç | Sprint 4 |
| Trendyol live API | Sprint 4 |
| RDWorks DXF export | Desktop only |
| WebSocket job streaming | Sprint 4 |

---

## Sprint 1+2+3 Koruma Özeti ✅

- `src/server/flask_app.py` → DOKUNULMADI
- `src/webui/app.js` (21391 satır) → DOKUNULMADI
- `src/webui_backend/bridge.py` → DOKUNULMADI
- `start_app.bat`, `start_browser_mode.bat` → DOKUNULMADI
- Sprint 1 (7 GET) + Sprint 2 (30 POST) → DOKUNULMADI

---

## Çalıştırma (Değişmedi)

```bash
start_browser_mode.bat
# → http://localhost:8000
```
