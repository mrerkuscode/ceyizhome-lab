# Etiket Studio — Visual Reporting System
# DISCOVERY & PLAN

Tarih: 2026-05-28
Kapsam: SADECE Etiket Studio modülü. Lazer modülüne dokunulmadı.
Yöntem: Tahmin yok. Her bulgu dosya + satır kanıtı ile.

---

## 1) ANALIZ — Mevcut Durum (Kanıtlı)

### 1.1 Etiket basım kodu nerede?

Üretim akışı iki katmandan oluşuyor: CLI/CSV motoru ve HTML webui backend.

CLI/dosya hazırlık katmanı (src/ kökü):
- src/print_service.py — PRINT işlerini üretiyor; find_print_template(), generate_print_jobs(), template_matching_report.csv ve print_data.csv yazıyor. Satır 1–120 incelendi. Template eşleşmesi TEMPLATE_OK / TEMPLATE_MISSING / TEMPLATE_NEEDS_REVIEW döndürüyor (satır 49–58).
- src/report_writer.py — write_errors_report() (satır ~12–25) ve write_summary_report() (satır ~28–67). Sadece CSV yazıyor; görsel/grafik yok. Sayım alanları: total_rows, valid_rows, invalid_rows, print_jobs_count, laser_engrave_jobs_count, laser_cut_jobs_count, both_jobs_count, none_jobs_count.
- src/svg_generator.py, src/template_writer.py, src/text_utils.py — etiket dosya üretim yardımcıları.
- src/label_designer/ — Label Designer render katmanı (PDF/PNG).

WebUI / masaüstü katmanı:
- src/webui_backend/label_api.py — 379 satır (kaynak: output/2026-05-28/project_discovery/05_label_studio.md).
- src/webui_backend/combined_production_api.py — 391 KB.
- src/webui_backend/bulk_label_api.py — Toplu Etiket Excel akışı (28 KB).
- src/webui_backend/template_api.py — 1677 satır, 78 KB.
- src/webui_backend/production_audit_api.py — 731 satır, 35 KB.
- src/webui_backend/report_api.py — Raporlar sayfasının backend'i; load_reports(), readiness(), summary(), first_errors(), report_payload().
- UI bölümleri (src/webui/index.html): <section id="label">, <section id="manualLabel">, <section id="bulkLabel">, <section id="printQueue">, <section id="labelOutputs">, <section id="reports">, <section id="productionAudit">.

Kanıt referansları:
- src/print_service.py satır 1–120.
- src/report_writer.py satır 1–67.
- src/webui_backend/report_api.py (readiness BLOKE/KONTROL_GEREKLI/HAZIR, summary dict, report_payload).
- output/2026-05-28/project_discovery/05_label_studio.md
- output/2026-05-28/project_discovery/08_history_outputs.md
- tests/test_mvp_safety.py:3495 — <section id="reports" class="page"> parse ediyor.

### 1.2 data/ altında üretim verisi tutuluyor mu?

Evet.
- data/production_history.json — 249 satır, 185 KB. Tarih aralığı: 2026-05-07 → 2026-05-23.
- data/production_audit_log.json — 13 event.
- data/customer_orders.json — 10 satır, 7 KB.
- data/print_queue.json — yazdırma kuyruğu.
- data/product_definitions.json (+ schema, audit jsonl).

production_history.json şeması (satır 1–142'den birebir okundu):
id, created_at, model_name, model_id, model_path, label_text, date_text, note_text, quantity, width_mm, height_mm, pdf_path, png_path, queue_status, preflight_status, output_validation_status.

Visual Reporting için yeterli sinyal: model, miktar, ölçü, durumlar, zaman.

### 1.3 Mevcut "Raporlar" sayfası ne durumda?

UI: src/webui/index.html'de gerçek <section id="reports" class="page"> var (tests/test_mvp_safety.py:3495 ile doğrulandı). Sol menü "SİSTEM" altında data-page="reports".

Backend (src/webui_backend/report_api.py):
- readiness(report_set) → "HAZIR" | "BLOKE" | "KONTROL_GEREKLI" | "NO_CHECK".
- summary(report_set) → {valid, errors, review, label, print, laser}.
- first_errors(report_set, limit).
- report_payload(report_set) → {humanSummary, errors, reviewRows, warnings, labelRows, laserRows, svgFiles}.

Kısıtları:
- Çıktı SADECE tablo + sayım (CSV satırlarının ekrana basılmış hâli). Grafik / trend YOK.
- Veri kaynağı yalnızca o günkü CSV raporları. data/production_history.json (249 satır) kullanılmıyor.
- Bilinen "sahte success" (08_history_outputs.md):
  - SYS-2: app.js'te "Doğrulandı" badge hardcoded.
  - SYS-2: label_api.py:83 "HAZIR" default.
- "Loglar / Hata Kayıtları" nav butonu showSystemNotice placeholder; ayrı sayfa yok.

Özet: Raporlar sayfası şu an "tek günlük CSV özetleri" gösteriyor. Görsel/zaman-serisi yok. 249 satırlık zengin geçmiş kullanılmıyor.

---

## 2) ÖNERI — Etiket Studio için 3 Visual Reporting Yaklaşımı

Her yaklaşım yalnızca okur; mevcut üretim/render/queue zincirini değiştirmez. Lazer kapsam dışı.

### Yaklaşım A — "Üretim Nabzı" Dashboard (Lightweight KPI Pano)

- Amaç: Raporlar sayfasının üstüne 4–6 kartlık "bugün/bu hafta" KPI bandı.
- Veri kaynağı: data/production_history.json + output/<date>/reports/*.csv.
- Görseller: Bugün üretilen etiket adedi; haftalık sparkline; Top-3 model (bar); preflight durum dağılımı (donut); queue ADDED/NOT_QUEUED (progress).
- Fayda: "Bugün ne oldu, dün ne oldu" sorusuna anında cevap. Mevcut "HAZIR/BLOKE" rozeti korunur.
- Geliştirme süresi: ~2 gün (backend 0.5g + frontend 1g + QA 0.5g).
- Risk: Düşük. Sadece okuma. Yazıcı/CorelDRAW dokunulmaz.

### Yaklaşım B — "Üretim Zaman Tüneli" (Time-Series Explorer)

- Amaç: 249 satırlık geçmişi gezilebilir zaman serisi; tarih aralığı + filtre (model_name, label_variant, preflight_status).
- Görseller: Stacked bar (günlük adet × preflight); heatmap (gün × saat); filtreli tablo + png thumbnail; "tekrar üretim" tespiti (aynı label_text + model_id ≥ 3 kez → uyarı).
- Fayda: Trend, reprint sebebi, model bazlı verimlilik. QA / sahte success izleme.
- Geliştirme süresi: ~5 gün (backend 1.5g + frontend 2.5g + QA 1g).
- Risk: Orta. PNG izinleri ve büyük JSON parse performansı.

### Yaklaşım C — "Kalite Kapısı Raporu" (Preflight & Output Validation Truth)

- Amaç: SYS-2 "sahte success" sorununu görünür kılmak; her etiket için gerçek preflight + output_validation + queue durumunu yan yana.
- Görseller: Sankey NEW → PREFLIGHT → OUTPUT_VALID → QUEUE; "sahte success" sayacı (hardcoded HAZIR vs gerçek status); model bazlı kalite skoru.
- Fayda: Master Context'teki "PASSED dese bile manuel doğrulama esastır" prensibinin canlı uygulaması.
- Geliştirme süresi: ~5 gün (backend 2g + frontend 2g + QA 1g).
- Risk: Orta-yüksek. SYS-2 bypass'i ifşa olur → "HAZIR" düzeltmesi gerekebilir.

### MVP'ye en yakın: Yaklaşım A — "Üretim Nabzı" Dashboard

Gerekçe:
- report_api.py zaten report_payload() döndürüyor; metrics_payload() eklemek için altyapı hazır.
- data/production_history.json 249 satırla anlamlı KPI üretmeye yeter.
- 2 günlük efor → V1 release riskinden ucuz.
- Mevcut Raporlar sayfasını yıkmıyor, üstüne ekliyor → güvenlik sınırlarına tam uyumlu.
- Sahte success'i doğrudan açmıyor; preflight donut'u dolaylı görünürlük yine sağlar.
- A'nın metrics_payload() backend'i sonraki sprintte B veya C için yeniden kullanılabilir.

---

## 3) ÇIKTI — Bu Dosya

- Yol: output/visual_reporting/DISCOVERY_AND_PLAN.md
- Branch: main
- Commit mesajı: discovery(visual_reporting): Etiket Studio için analiz ve 3 yaklaşım planı
- Kapsam dışı: Lazer / name_cut / DXF / RDWorks.

## Notlar — Güvenlik & Sınırlar

- CorelDRAW açılmaz, yazıcı tetiklenmez, RDWorks açılmaz, lazer başlatılmaz.
- Bu dosya sadece okuma + analiz çıktısıdır; üretim akışında hiçbir kod/template değiştirilmedi.
- Tüm kanıtlar dosya yolu + satır referansı veya doğrudan repo dosyası kaynak gösterilerek verildi.
