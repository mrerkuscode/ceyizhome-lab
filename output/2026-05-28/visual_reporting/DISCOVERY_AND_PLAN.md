# Visual Reporting System — Discovery & Plan
**Tarih:** 2026-05-28  
**Modül:** Etiket Studio (Label Designer)  
**Kapsam Dışı:** Lazer Kesim modülü (dokunulmadı)

---

## ADIM 1 — ANALİZ BULGULARI

### 1.1 Etiket Basım Kodu Nerede?

| Dosya | Satır | İşlev |
|---|---|---|
| `src/label_designer/renderer.py` | 28–47 | `render_template_to_painter()` — canvas core render |
| `src/label_designer/renderer.py` | 50–70 | `create_preview_image()` — QImage önizleme (DPI ayarlı) |
| `src/label_designer/pdf_exporter.py` | 15–35 | `export_label_pdf()` — tekli PDF (QPdfWriter) |
| `src/label_designer/pdf_exporter.py` | 38–77 | `export_roll_batch_pdf()` — çok sayfalı toplu PDF |
| `src/label_designer/label_service.py` | 34–60 | `render_labels_from_excel()` — sipariş → PDF/PNG boru hattı |
| `src/label_designer/label_service.py` | 63–100 | `label_render_report.csv` ve model bazlı raporlar üretir |
| `src/label_designer/template_schema.py` | 14–40 | `LabelTemplate` dataclass — canvas boyutları (mm, DPI) |

**Kanıt:** Tüm canvas işlemleri QPainter tabanlı; önizleme için QImage, baskı için QPdfWriter kullanılıyor.

### 1.2 Üretim Verisi Nerede Tutuluyor?

```
production-bot/data/
├── print_queue.json            ← Aktif baskı kuyruğu (status tracking)
├── production_audit_log.json   ← 20 event tipi, customer/order/batch bazlı
├── production_history.json     ← Tamamlanan işler arşivi
├── customer_orders.json        ← Trendyol siparişleri
└── name_cut_*                  ← Lazer modülü (kapsam dışı)

production-bot/output/<tarih>/
├── summary_report.csv          ← Toplam/geçerli/hatalı sayılar
├── errors_report.csv           ← Validation hataları
├── label_render_report.csv     ← Etiket bazlı render detayları
├── template_matching_report.csv← Şablon-model eşleşmeleri
└── material_efficiency_report.csv
```

**Kanıt:** `production_audit_api.py` satır 13–90; `print_queue_api.py` satır 11–40, 97, 163–168.

### 1.3 Mevcut "Raporlar" Sayfası

**`src/webui/index.html` satır 3134–3146:**
```html
<section id="reports" class="page">
  <h1 class="page-title">Raporlar</h1>
  <div id="reportSummaryCards" class="report-summary-cards"></div>
  <div class="report-tabs">
    <button onclick="selectReport('summary')">Özet</button>
    <button onclick="selectReport('errors')">Kritik Hatalar</button>
    <button onclick="selectReport('review')">Kontrol Gerekenler</button>
    <button onclick="selectReport('labels')">Etiket Çıktıları</button>
    <button onclick="selectReport('release')">Release Dashboard</button>
    <button onclick="selectReport('log')">Günlük</button>
  </div>
</section>
```

**`src/webui/app.js`:**
- Satır 20241: `updateReports()` — state değişince yenile
- Satır 20251–20344: `selectReport(name)` — 6 sekme render mantığı
- Satır 20351–20362: `renderReportSummaryCards()` — KPI kartları
- Satır 20364–20366: `reportMetric(label, value, tone)` — kart şablonu

### 1.4 Halihazırda Toplanan Metrikler

`state.summary` objesi (app.js ~satır 2254–2260):
- `total`, `valid`, `errors`, `review`, `label`, `print`, `laser` — sipariş sayaçları
- `readiness` — HAZIR / BLOKE / KONTROL_GEREKLI / NO_CHECK
- `label_model` — model bazlı kırılım

`production_audit_log.json` event tipleri (20 adet):
- `label_studio_session_created`, `label_output_created`, `print_queue_created`
- `printed_marked`, `print_cancelled`, `print_failed`
- `duplicate_detected`, `blocked_detected`, `manual_review_required`

`print_queue.json` kuyruk geçmişi (satır 163–168):
- Her item'da `queue_history[]` — max 30 giriş, timestamp + status_key

---

## ADIM 2 — 3 YAKLAŞIM ÖNERİSİ

### Yaklaşım A — Üretim İstatistikleri (Production Stats)

**Amaç:** Etiket işlemlerinin hacim, hız ve model dağılımını göster.

**Gösterilecek metrikler:**
- Bugün / Bu hafta / Bu ay basılan etiket sayısı
- Model bazlı dağılım (pasta/bar chart): hangi ürün modeli en çok basılıyor
- Ortalama sipariş → baskı süresi (audit log timestamp farkından)
- İptal / hata oranı (print_failed / printed_marked)

**Fayda:** Leyla hangi modellerin yoğun olduğunu, hangi günlerde üretimin arttığını görür; stok planlaması yapabilir.

**Veri kaynakları mevcut:** `production_audit_log.json` + `production_history.json` + `state.summary` — **sıfır yeni veri toplama** gerekmiyor.

**Geliştirme süresi:** ~3–4 saat (backend: audit log agregasyonu + frontend: chart render)

---

### Yaklaşım B — Kalite / QA Durum Panosu (Quality Dashboard)

**Amaç:** Her üretim seansında hangi etiketlerin sorunlu olduğunu görsel olarak işaretle.

**Gösterilecek metrikler:**
- Validation hata tipi dağılımı (errors_report.csv'den)
- "Kontrol gerekli" listesi: müşteri + model + hata sebebi
- Kalite kapısı (quality_gate) geçmiş/başarısız geçmişi
- duplicate_detected ve blocked_detected sayısı zaman içinde

**Fayda:** QA sorunu tekrar eden müşteri/model kombinasyonlarını tespit eder; aynı hatanın kaçıncı kez geldiği görünür olur.

**Veri kaynakları mevcut:** `errors_report.csv` + `needs_review_report.csv` + audit events — **mevcut CSV pipeline'a dokunmadan** aggregation yapılabilir.

**Geliştirme süresi:** ~4–5 saat (audit log filtreleme + hata kategorileme + frontend tablo)

---

### Yaklaşım C — Görsel Önizleme Grid (Preview Gallery)

**Amaç:** Basılan etiketlerin PNG önizlemelerini grid görünümünde göster; tıklayınca detay aç.

**Gösterilecek içerik:**
- Tarih bazlı gruplandırılmış etiket önizleme grid'i
- Her kartta: model adı, müşteri adı, durum badge (basıldı/bekliyor/hata)
- Tıklayınca: tam boyut önizleme + PDF indirme linki
- Filtre: tarih aralığı, model, durum

**Fayda:** Operatör gözle kontrol yapabilir; hatalı basan etiketleri görsel olarak yakalar. Fiziksel çıktıya bakmak yerine ekrandan QA yapılır.

**Veri kaynakları mevcut:** `renderer.py` satır 50–70'te `create_preview_image()` zaten PNG üretiyor; `output/` klasöründe saklanıyor.

**Geliştirme süresi:** ~5–7 saat (output klasör taraması + grid UI + lightbox)

---

## ADIM 3 — MVP TAVSİYESİ

**Tavsiye: Yaklaşım A (Üretim İstatistikleri) — MVP için en uygun.**

**Gerekçe:**
1. Veri **sıfır ek toplama** gerektirmiyor — `production_audit_log.json` zaten her event'ı timestamp'li kaydediyor.
2. Mevcut `renderReportSummaryCards()` (app.js satır 20351) genişletilerek grafik eklenebilir.
3. Kullanıcıya en yüksek "görünür değer": hangi modelden kaç etiket basıldığı soru olarak sürekli geliyor olmalı.
4. En kısa geliştirme süresi: ~3–4 saat.

**Önerilen MVP kapsam:**
- Bugünkü baskı sayısı (badge olarak zaten var → grafik olarak büyüt)
- Model bazlı top-5 bar chart (audit log'dan model_name aggregation)
- Bu hafta hata oranı (print_failed / toplam)

**Sonraki aşamada:** Yaklaşım C (Preview Gallery) — en yüksek operasyonel fayda, en çok geliştirme süresi gerektirir; A'dan sonra eklenebilir.

---

## DOSYA HARİTASI (Dokunulacak Olanlar — Gelecek Sprint)

```
src/webui/
├── app.js          → selectReport() içine 'stats' sekmesi eklenecek
├── index.html      → report-tabs'e yeni buton
└── (yeni) report_stats_api.py  →  audit log aggregation endpoint

data/
└── production_audit_log.json   (sadece okunacak, değiştirilmeyecek)
```

**Bu sprintte değiştirilen dosya: YOK.** Sadece bu keşif raporu yazıldı.
