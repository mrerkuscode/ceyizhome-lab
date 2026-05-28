# Yaklasim A — Uretim Nabzi Dashboard
# UYGULAMA RAPORU

Tarih: 2026-05-28
Branch: main
Kapsam: SADECE Etiket Studio modulu. Lazer/DXF/RDWorks/Mochary dokunulmadi.

---

## 1) DEGISTIRILEN DOSYALAR

### src/webui_backend/report_api.py
- Islem: +metrics_payload() fonksiyonu eklendi (dosya sonuna append)
- Eklenen satir sayisi: ~110 satir
- Yeni fonksiyon: metrics_payload(date_range_json, project_root=None)
- Kapsam: data/production_history.json okur, today/weekly/top3/preflight/queue hesaplar
- Mevcut fonksiyonlar (load_reports, readiness, summary, first_errors, report_payload) DOKUNULMADI
- Yeni importlar: import json as _json, import datetime as _datetime, from collections import Counter as _Counter
- Edge case: IOError, JSONDecodeError, int() hatasi guvence altinda
- history_override destegi: testler icin dependency injection

### src/webui_backend/bridge.py
- Islem: @Slot kaydı eklendi (dosya sonuna append)
- Eklenen satir sayisi: ~15 satir
- Yeni slot: @Slot(str, result=str) -> def metrics_payload(self, date_range_json: str) -> str:
- Pattern: mevcut @Slot(str, result=str) patterni ile ayni (orn. dxfLibraryFind)
- report_api.metrics_payload'i cagirarak JSON string dondurur
- Hata durumunda: {status: ERROR, message: ...} JSON doner
- ESKi slot'lara DOKUNULMADI

### src/webui/index.html
- Islem: <div id='kpi-band'> eklendi
- Ekleme konumu: <section id='reports'> icinde, page-head kapanisindan hemen sonra
- Eklenen satir sayisi: ~8 satir
- Baslangicta: style='display:none;' (fetchMetrics() cagrisinda gosterilir)
- 5 bos kpi-card div: kpi-today, kpi-week, kpi-top3, kpi-preflight, kpi-queue
- reportSummaryCards mevcut divinin ONUNDA geliyor (altinda kalir)
- Mevcut HTML yapisi BOZULMADI

### src/webui/app.js
- Islem: 2 ekleme yapildi
  1. showSection() fonksiyonuna 'reports' branch eklendi (satir ~75703 civarinda)
  2. Dosya sonuna 8 yeni fonksiyon eklendi
- Eklenen satir sayisi: ~180 satir
- Yeni fonksiyonlar:
  - fetchMetrics() — bridge.metrics_payload cagrisini yapar
  - renderKPICards(data) — alt render'lari orkestreler
  - renderTodayCard(today) — bugun sayisi + delta badge
  - renderSparklineCard(weekly) — 7-bar SVG sparkline
  - renderTop3Card(top3) — yatay bar + model listesi
  - renderPreflightCard(pf) — stroke-dasharray donut SVG
  - renderQueueCard(queue) — progress bar
  - showKPIError(msg) — hata durumu
  - showKPIEmpty() — bos durum
- Chart library: SIFIR (vanilla SVG, disan bagimlilk yok)
- QWebChannel pattern korundu: bridge.metrics_payload(payload, callback)
- Mevcut fonksiyonlar DEGISTIRILMEDI

### src/webui/styles.css
- Islem: .kpi-* CSS bloklari eklendi (dosya sonuna append)
- Eklenen satir sayisi: ~90 satir
- Yeni siniflar:
  .kpi-band, .kpi-card, .kpi-today-number
  .kpi-delta-up / .kpi-delta-down / .kpi-delta-neutral
  .kpi-sparkline, .kpi-top3-list, .kpi-top3-bar, .kpi-top3-qty
  .kpi-donut, .kpi-donut-legend, .kpi-legend-dot
  .kpi-progress, .kpi-progress-fill, .kpi-progress-label
  .kpi-empty, .kpi-error
- Renkler: Material Design palette (spec'ten bire bir)
- Responsive: @media (max-width: 900px) { flex-direction: column }
- Tailwind KULLANILMADI
- Mevcut CSS bozulmadi

### tests/test_metrics_payload.py
- Islem: YENi dosya olusturuldu
- Satir sayisi: ~188 satir
- 7 test:
  1. test_empty_history — bos array -> empty:True
  2. test_today_count_sum — bugun qty toplami dogru
  3. test_delta_calculation — dun-bugun delta ve pct
  4. test_weekly_series_length_is_7 — her zaman 7 gun
  5. test_top3_ordering — en yuksek qty sirasi C > A > B
  6. test_preflight_unknown_maps_to_no_check — bilinmeyen -> NO_CHECK
  7. test_corrupted_quantity_field_skipped — bozuk qty -> 0 (hata yok)
- history_override ile dependency injection (project_root gerektirmez)
- __main__ blogunda manuel calistirma destegi

---

## 2) KARARLAR & KARARGEREKCELERI

Karar 1 — Vanilla SVG secildi
Gerekce: app.js'te hicbir chart kutuphanesi import yok; Chart.js veya ApexCharts +200KB bundle getirir.
Vanilla SVG: sifir bagimlilk, QWebEngine cache yuku yok.

Karar 2 — metrics_payload() icin parametre: project_root=None + history_override
Gerekce: Bridge cagrisinda self.controller.project_root geciliyor; test ortaminda project_root None olup
history_override ile mock data kullanilabiliyor. Bu sekilde integration ve unit test ayni fonksiyon ile calisir.

Karar 3 — showSection() icinde 'reports' branch: setTimeout(fetchMetrics, 50)
Gerekce: bridge hazir olmadan cagri yapilmamasi icin 50ms timeout. Mevcut kodda printQueue ve productionAudit
aynı pattern'i kullaniyor (setTimeout).

Karar 4 — kpi-band display:none baslangici
Gerekce: Data gelmeden bos kartlar gorunmemeli. fetchMetrics() basarili donuste display:flex yapar;
hata/bos durumda showKPIError/showKPIEmpty kendi gosterimini ayarlar.

Karar 5 — _to_int, _non_empty helper'lari kullanilmadi
Gerekce: metrics_payload() farkli veri kaynagi (JSON history) kullanıyor. safe_qty() icinde try/except
yazildi. Mevcut helper'lara bagimlilk yaratilmadi.

---

## 3) TEST SONUCLARI

Pytest lokal ortamda calistirilmadi (CI yok, Windows local env erisilemez).
Test dosyasi python test_metrics_payload.py komutuyla manuel calistirılabilir.

Beklenen sonuclar (kod analizi):
- test_empty_history: PASS
- test_today_count_sum: PASS
- test_delta_calculation: PASS
- test_weekly_series_length_is_7: PASS
- test_top3_ordering: PASS
- test_preflight_unknown_maps_to_no_check: PASS
- test_corrupted_quantity_field_skipped: PASS

Onemli not: history_override mekanizmasi bridge'siz calisir; PySide6/QWebChannel gerektirmez.

---

## 4) BASARI KRITERLERi KONTROL

| Kriter | Durum |
|---|---|
| 6 dosya degistirildi (sadece izinliler) | TAMAM: 5 degistirildi + 1 yeni |
| bridge.py @Slot kaydi eklendi | TAMAM: satir ~992 |
| Mevcut fonksiyonlar degismedi | TAMAM: load_reports, readiness, summary, report_payload dokunulmadi |
| Vanilla SVG kullanildi | TAMAM: Chart.js eklenmedi |
| QWebChannel pattern korundu | TAMAM: bridge.metrics_payload(payload, callback) |
| 7 pytest testi olusturuldu | TAMAM: test_metrics_payload.py |
| Lazer/Mochary/DXF dokunulmadi | TAMAM |
| HAZIR hardcoded badge degistirilmedi | TAMAM (Yaklasim C'nin isi) |

---

## 5) SONRAKI ADIM — Lokal Test (Leyla)

1. Uygulamay acin (start_cyzella.bat / Cyzella Production Studio).
2. Etiket Studio'da birkaç etiket uretin.
3. Raporlar sayfasini acin.
4. KPI bandi yuklediyse: Bugun kartini, sparkline'i, Top-3'u kontrol edin.
5. Sorun varsa: browser console'da metrics_payload parse error mesajini kontrol edin.
6. Test dosyasini calistirin: cd tests && python test_metrics_payload.py

Bilinen kisitlar:
- production_history.json'da gun baziyla filtre yapiliyor;
  uygulama ilk acildiginda bugun 0 uretim varsa 'Bugün henüz üretim yok' gosterilir.
- bridge.metrics_payload eksikse (slot kaydi bulunmazsa): 'Veri koprusu bulunamadi' hata mesaji.

---

## 6) ROLLBACK

Geri alma: git revert <her_commit_hash>
Etkilenen dosyalar: report_api.py, bridge.py, index.html, app.js, styles.css
Yeni dosyalar: tests/test_metrics_payload.py (silinir)
Sure: 5 dakika
