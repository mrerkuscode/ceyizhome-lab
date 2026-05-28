# Yaklaşım A — "Üretim Nabzı" Dashboard
# Teknik Uygulama Spec'i (A_IMPLEMENTATION_SPEC.md)

Versiyon: 1.0 | Tarih: 2026-05-28
Kapsam: SADECE Etiket Studio modülü
Kapsam Dışı: SYS-2 sahte success düzeltmesi, Lazer/DXF/RDWorks/Mochary
Kanıt kaynakları: output/2026-05-28/project_discovery/ serisi

---

## 1) AMAÇ & BAŞARI KRİTERİ

"Üretim Nabzı" Dashboard, mevcut Raporlar sayfasının üstüne sabit bir KPI bandı ekler; operatör sayfayı açtığı anda "bugün kaç etiket basıldı, hafta nasıl gidiyor, hangi modeller en çok üretiliyor, preflight ne durumda, kuyruk dolu mu" sorularını tek bakışta yanıtlar. Tek veri kaynağı data/production_history.json'dır; hiçbir üretim kodu değiştirilmez, sadece okuma yapılır.

Hedef kullanıcı: Leyla (operatör) — günde birkaç kez Raporlar sayfasını açıp "bugün ne ürettik" kontrolü yapan, teknik terimlerden uzak, hızlı kararlar alan kullanıcı.

Başarı kriteri:
- Leyla, sayfayı açar açmaz 3 saniye içinde bugünkü üretim adedini görür.
- Haftalık trend tek satır grafikle anlaşılır.
- Top-3 model adları ve adetleri doğru sıralanmış şekilde görünür.
- Preflight donut gerçek data/production_history.json değerlerini yansıtır.
- Queue progress barı anlık queue_status dağılımını gösterir.
- production_history.json boşsa ya da bugün 0 üretim varsa boş-state mesajı çıkar; hata yoktur.
- Mevcut Raporlar sayfasının geri kalanı (tablo, readiness rozeti) bozulmadan çalışır.

KAPSAM DIŞI (bu spec'te DEĞİŞTİRİLMEZ):
- SYS-2: app.js'teki hardcoded "Doğrulandı" badge → Yaklaşım C'nin işi.
- label_api.py:83 "HAZIR" default → Yaklaşım C'nin işi.
- Lazer, DXF, RDWorks, Mochary, name_cut modülleri.

---

## 2) UI WIREFRAME

Raporlar sayfası (<section id="reports">) içinde, mevcut içeriğin ÜSTÜNE eklenen sabit bant:

```
+----------------------------------------------------------+
| RAPORLAR                              [readiness badge]  |
+----------------------------------------------------------+
| +------------+ +------------+ +--------------------+    |
| | BUGÜN      | | HAFTALIK   | | TOP-3 MODEL        |    |
| | 24 etiket  | | ▂▃▅▇▆▄▅▂  | | 1. 01 Gold  ████ 9 |    |
| | ↑+6 vs dün | | Pzt-Paz    | | 2. 02 Silv  ██   4 |    |
| +------------+ +------------+ | 3. 04 QA    █    2 |    |
|                                +--------------------+    |
| +--------------------+ +---------------------------+    |
| | PREFLIGHT DURUM    | | KUYRUK DURUMU             |    |
| | (•)HAZIR  18       | | ████████████░░░  78% kuy. |    |
| | (•)UYARI   4       | | ADDED: 19 / 24            |    |
| | (•)BLOKE   2       | |                           |    |
| +--------------------+ +---------------------------+    |
+----------------------------------------------------------+
| [mevcut tablo: errors, humanSummary, labelRows ...]      |
+----------------------------------------------------------+
```

KPI kartları:
a) Bugün üretilen — büyük sayı + "↑+N vs dün" veya "↓-N vs dün" veya "= dünle aynı"
b) Haftalık sparkline — 7 bar (Pzt-Paz), bugün vurgulanmış, eksik günler gri
c) Top-3 model — yatay bar chart, model_name + quantity, sadece etiket bazlı (quantity sütunu)
d) Preflight donut — 4 renk: HAZIR #4CAF50, WARNING #FF9800, BLOKE #F44336, NO_CHECK #9E9E9E
e) Queue progress — progress bar: ADDED count / toplam × 100; "X/Y eklendi" label

Responsive:
- Desktop (≥900px): 5 kart yan yana (3+2 satır).
- Dar pencere (<900px): kart başına tam genişlik, dikey yığılmış.
- Mevcut sistem QWebEngine masaüstü uygulaması olduğundan mobil senaryo düşük öncelikli; dar QWebEngine pencere için min-width:280px kart yeterli.

---

## 3) BACKEND DEĞİŞİKLİKLERİ

Dosya: src/webui_backend/report_api.py (yalnızca ekleme, mevcut fonksiyon DEĞİŞTİRİLMEZ)
Yeni bridge slot adı: metrics_payload (bridge.py'daki @Slot dekoratörü ile kayıt edilecek)
Çağrı formatı (QWebChannel pattern, HTTP REST yok):
  bridge.metrics_payload(date_range_json, callback)
  date_range_json örneği: '{"range": "today"}' veya '{"range": "week"}'

Veri kaynağı: data/production_history.json
  - JSON array, her item: {id, created_at, model_name, model_id, quantity, preflight_status, queue_status, ...}
  - Okuma: load once per call (cache TODO: 10k+ satır için)

Pseudo-kod:

  FUNCTION metrics_payload(date_range_json):
    params = parse_json(date_range_json)
    history = load_json("data/production_history.json")  // [] if missing
    IF history is empty:
      RETURN {status:"OK", empty:true, message:"Henüz üretim verisi yok"}

    today = local_date_today()  // Windows local TZ
    yesterday = today - 1 day
    week_start = today - 6 days  // 7 günlük pencere

    today_rows = [r for r in history if date(r.created_at) == today]
    yesterday_rows = [r for r in history if date(r.created_at) == yesterday]
    week_rows = [r for r in history if date(r.created_at) >= week_start]

    today_count = sum(int(r.quantity) for r in today_rows)
    yesterday_count = sum(int(r.quantity) for r in yesterday_rows)
    delta = today_count - yesterday_count
    delta_pct = round(delta / yesterday_count * 100) if yesterday_count > 0 else null

    weekly_series = []
    FOR d IN [week_start .. today]:
      day_rows = [r for r in week_rows if date(r.created_at) == d]
      weekly_series.append({date: d.isoformat(), count: sum(qty), has_data: len(day_rows)>0})

    model_counts = groupby(history, key=model_name, value=sum(quantity))
    top3 = model_counts.sort_desc().head(3)

    preflight_dist = groupby(history, key=preflight_status, value=count)
    // Keys: OK, WARNING, BLOKE, NO_CHECK, (unknown mapped to NO_CHECK)

    queue_total = len(history)
    queue_added = count(r for r in history if r.queue_status == "ADDED")
    queue_pct = round(queue_added / queue_total * 100) if queue_total > 0 else 0

    RETURN {
      status: "OK",
      empty: false,
      today: {count: today_count, delta: delta, delta_pct: delta_pct},
      weekly: weekly_series,           // [{date, count, has_data}, ...]
      top3_models: top3,               // [{model_name, total_qty}, ...]
      preflight: preflight_dist,       // {OK: n, WARNING: n, BLOKE: n, NO_CHECK: n}
      queue: {added: queue_added, total: queue_total, pct: queue_pct}
    }

Örnek response JSON:
  {
    "status": "OK",
    "empty": false,
    "today": {"count": 24, "delta": 6, "delta_pct": 33},
    "weekly": [
      {"date": "2026-05-22", "count": 8, "has_data": true},
      {"date": "2026-05-23", "count": 12, "has_data": true},
      {"date": "2026-05-24", "count": 0, "has_data": false},
      {"date": "2026-05-25", "count": 0, "has_data": false},
      {"date": "2026-05-26", "count": 5, "has_data": true},
      {"date": "2026-05-27", "count": 18, "has_data": true},
      {"date": "2026-05-28", "count": 24, "has_data": true}
    ],
    "top3_models": [
      {"model_name": "01 A Gold Rulo Etiket", "total_qty": 9},
      {"model_name": "02 Silver Etiket", "total_qty": 4},
      {"model_name": "04_a_qa", "total_qty": 2}
    ],
    "preflight": {"OK": 18, "WARNING": 4, "BLOKE": 2, "NO_CHECK": 0},
    "queue": {"added": 19, "total": 24, "pct": 79}
  }

Mevcut fonksiyonlarla reuse stratejisi:
  - load_reports(), readiness(), summary(), report_payload() DEĞİŞTİRİLMEZ.
  - metrics_payload() bağımsız, production_history.json'u doğrudan okur.
  - Gelecekte: metrics_payload sonucu bridge.py'de cache'lenebilir (TTL: 60s).

---

## 4) FRONTEND DEĞİŞİKLİKLERİ

Dosyalar (yalnızca ekleme; mevcut içerik silinmez/taşınmaz):
  - src/webui/index.html: <section id="reports"> içine en üste <div id="kpi-band"> eklenir.
  - src/webui/app.js: 3 yeni fonksiyon eklenir (mevcut fonksiyonlar değişmez).
  - src/webui/styles.css: .kpi-card, .kpi-sparkline, .kpi-donut, .kpi-progress blokları eklenir.

CSS Sistemi: Plain CSS (Tailwind kullanılmıyor — code search 0 sonuç).
Mevcut sistemdeki pattern: CSS custom properties (:root değişkenler), class adları kebab-case.
Chart library seçimi: Vanilla SVG (sıfır dış bağımlılık).
  - Sparkline: 7 <rect> elementi, SVG viewBox.
  - Donut: 2 <circle> (stroke-dasharray tekniği), tek pasaj.
  - Horizontal bar: <div> genişliği % olarak hesaplanmış, CSS width: X%.
  - Neden Chart.js değil: Bundle boyutu (+200KB), QWebEngine cache yükü, mevcut projede hiç import yok.

HTML ekleme (minimal):

  // src/webui/index.html — <section id="reports"> içine İLK satır:
  <div id="kpi-band" class="kpi-band" style="display:none">
    <div class="kpi-card" id="kpi-today">...</div>
    <div class="kpi-card" id="kpi-weekly">...</div>
    <div class="kpi-card" id="kpi-top3">...</div>
    <div class="kpi-card" id="kpi-preflight">...</div>
    <div class="kpi-card" id="kpi-queue">...</div>
  </div>
  // (Başlangıçta gizli; data gelince görünür hale gelir)

app.js yeni fonksiyonlar (pseudo-kod):

  FUNCTION fetchMetrics():
    // QWebChannel pattern: bridge.metrics_payload(json, callback)
    payload = JSON.stringify({range: "today"})
    bridge.metrics_payload(payload, FUNCTION(raw):
      data = parseBridgeResult(raw)   // mevcut helper
      IF data.status != "OK":
        showKPIError(data.message)
        RETURN
      IF data.empty:
        showKPIEmpty()
        RETURN
      renderKPICards(data)
    )

  FUNCTION renderKPICards(data):
    renderTodayCard(data.today)       // sayı + delta badge
    renderSparkline(data.weekly)      // 7-bar SVG
    renderTop3(data.top3_models)      // yatay bar listesi
    renderPreflight(data.preflight)   // donut SVG
    renderQueueProgress(data.queue)   // progress bar
    document.getElementById("kpi-band").style.display = "block"

  FUNCTION renderSparkline(weekly):
    // SVG oluştur: viewBox="0 0 140 40", 7 <rect> 20px aralık
    maxVal = max(weekly.map(w => w.count)) OR 1
    FOR i, day IN enumerate(weekly):
      height = (day.count / maxVal) * 36
      color = day.has_data ? "#4CAF50" : "#E0E0E0"   // gri = veri yok
      // bugün (i==6) farklı renk: "#1565C0"
      <rect x=i*20 y=40-height width=14 height=height fill=color />

Çağrı noktası: showSection("reports") çağrıldığında fetchMetrics() tetiklenir (mevcut showSection fonksiyonunun reports case'ine eklemek).

---

## 5) QUERY/HESAP MANTIK

Tüm hesaplar Python'da metrics_payload() içinde yapılır; frontend yalnızca render eder.

a) Bugün adet:
   today = datetime.date.today()
   today_count = sum(int(row["quantity"]) for row in history
                     if row["created_at"][:10] == str(today))

b) Dünle kıyas:
   yesterday_count = sum(... created_at[:10] == str(today - timedelta(1)))
   delta = today_count - yesterday_count
   delta_pct = round(delta/yesterday_count*100, 1) if yesterday_count > 0 else None
   // Gösterim: delta>0 → "↑+N (%P)" yeşil; <0 → "↓N (%P)" kırmızı; ==0 → "= dünle aynı" gri

c) Haftalık trend (7 gün):
   week_start = today - timedelta(6)
   series = []
   FOR offset IN range(7):
     day = week_start + timedelta(offset)
     day_rows = [r for r in history if r["created_at"][:10] == str(day)]
     series.append({"date": str(day), "count": sum(int(r["quantity"]) for r in day_rows),
                    "has_data": len(day_rows) > 0})

d) Top-3 model:
   from collections import Counter
   model_qty = Counter()
   for row in history:
     model_qty[row["model_name"]] += int(row.get("quantity", 1))
   top3 = [{"model_name": k, "total_qty": v}
            for k, v in model_qty.most_common(3)]

e) Preflight breakdown:
   from collections import Counter
   pf = Counter(row.get("preflight_status", "NO_CHECK") for row in history)
   result = {"OK": pf.get("OK",0), "WARNING": pf.get("WARNING",0),
             "BLOKE": pf.get("BLOKE",0), "NO_CHECK": pf.get("NO_CHECK",0)}
   // "WARNING" → production_history.json'da WARNING olarak kayıtlı
   // Bilinmeyen değerler NO_CHECK'e dahil edilir

f) Queue progress:
   total = len(history)
   added = sum(1 for r in history if r.get("queue_status") == "ADDED")
   pct = round(added / total * 100) if total > 0 else 0

Hesap kapsamı: TÜM history (tarih filtresi yok) — dashboard genel durumu gösterir.
   today kartı zaten "bugüne" odaklanıyor; sparkline 7 günü kapsıyor.
   Preflight ve queue tüm geçmişin anlık snapshot'ı.

---

## 6) VERİ AKIŞI DİYAGRAMI

```
[data/production_history.json]
         |
         v  (load + parse Python)
[metrics_payload() in report_api.py]
         |
         | @Slot / QWebChannel bridge
         v
[bridge.metrics_payload(payload, callback) in app.js]
         |
         v  parseBridgeResult(raw) → JS Object
[fetchMetrics() → renderKPICards(data)]
    /    |    \    |        \
   v     v    v    v         v
[Today] [Spark] [Top3] [Preflight] [Queue]
renderTodayCard  renderSparkline  renderPreflight
         |              |              |
         v              v              v
    DOM #kpi-today  SVG injected  SVG injected
         |              |              |
         +------+--------+------+------+
                         |
                         v
              document.getElementById("kpi-band")
                    .style.display = "block"
```

---

## 7) EDGE CASES

Her durumda UI temiz kalır; console.error ile log atılır; hata kullanıcıya Türkçe gösterilir.

| Durum | Tespit | Davranış |
|---|---|---|
| production_history.json yok | load hatası / IOError | kpi-band'da "Henüz üretim verisi bulunamadı" boş-state kartı |
| Dosya var ama boş array ([]) | len(history)==0 | "Henüz hiç üretim yapılmamış" mesajı; kpi-band görünür ama kartlar boş-state |
| Bugün 0 etiket | today_count==0 | "Bugün henüz üretim yok" — delta yok, sparkline bugün gri |
| 7 günden az veri | has_data==false bazı günlerde | Eksik günler sparkline'da gri bar (0 yükseklik), tooltip: "Veri yok" |
| JSON parse hatası (corrupted) | json.JSONDecodeError | status:"ERROR", message:"Üretim geçmişi okunamadı" → kpi-band'da hata banner |
| quantity alanı string/hatalı | int() atma | try/except: hatalı satır 0 kabul edilir, log atılır; üretim devam eder |
| production_history.json >10k satır | ölçüm: 10k row ~50ms Python | İlk sürümde inline; >500ms latency gözlemlenirse basit TTL cache (60s) eklenir |
| model_name boş string | groupby'da boş key | "Bilinmeyen Model" olarak etiketlenir |
| preflight_status bilinmeyen değer | Counter'da bilinmeyen key | NO_CHECK bucket'ına eklenir |
| Tüm queue_status NOT_QUEUED | added=0, pct=0 | Progress bar %0, "Kuyrukta bekleyen yok" |

---

## 8) TEST PLANI

Manuel test senaryoları (Leyla gözüyle, 5 senaryo):

Senaryo 1 — Normal üretim günü:
  ADIM: Etiket Studio'da 5 etiket bas → Raporlar'a geç.
  BEKLENEN: "Bugün" kartı ≥5 gösterir; sparkline bugün bar'ı mavi/yeşil; top model güncel.
  KONTROL: data/production_history.json son satır bugünün tarihini taşıyor mu?

Senaryo 2 — Hiç üretim yok (empty state):
  ADIM: Boş production_history.json ile başlat → Raporlar aç.
  BEKLENEN: kpi-band görünür, tüm kartlarda "Henüz üretim yok" mesajı; hata yok.

Senaryo 3 — Çoklu model sıralaması:
  ADIM: A modelinden 5, B'den 3, C'den 7 etiket bas.
  BEKLENEN: Top-3 sırası C(7)→A(5)→B(3); bar uzunlukları orantılı.

Senaryo 4 — Preflight varyasyonları:
  ADIM: 3 adet OK, 2 WARNING, 1 BLOKE durumunda etiket üret.
  BEKLENEN: Donut dilimi renkler: yeşil(3), turuncu(2), kırmızı(1); toplam=6.

Senaryo 5 — Queue doluluk:
  ADIM: 5 etiketten 3'ünü kuyruğa ekle, 2'sini ekleme.
  BEKLENEN: progress bar %60, "3/5 eklendi" label.

Automated test önerisi (tests/test_mvp_safety.py'a ekleme):

  TEST 1 — metrics_payload empty:
    history = []
    result = metrics_payload('{"range":"today"}', history_override=history)
    ASSERT result["empty"] == True
    ASSERT result["status"] == "OK"

  TEST 2 — metrics_payload top3 sıralaması:
    history = [fake_rows: A×5, B×3, C×7]
    result = metrics_payload(...)
    ASSERT result["top3_models"][0]["model_name"] == "C"
    ASSERT result["top3_models"][0]["total_qty"] == 7

  TEST 3 — metrics_payload preflight dağılımı:
    history = [3 OK, 2 WARNING, 1 BLOKE]
    result = metrics_payload(...)
    ASSERT result["preflight"]["OK"] == 3
    ASSERT result["preflight"]["BLOKE"] == 1

Backend unit test (pytest):
  tests/test_metrics_payload.py
    test_empty_history()
    test_today_count_sum()
    test_delta_calculation()
    test_weekly_series_length_is_7()
    test_top3_ordering()
    test_preflight_unknown_maps_to_no_check()
    test_corrupted_quantity_field_skipped()

---

## 9) TAHMİNİ EFOR (Saatlik Kırılım)

| Görev | Süre | Notlar |
|---|---|---|
| Backend: metrics_payload() yazma | 3 saat | report_api.py yeni fonksiyon + bridge.py @Slot kaydı |
| Backend: edge case + hata yönetimi | 1 saat | IOError, JSONDecodeError, int() guard |
| Backend: pytest unit tests | 1 saat | 7 test, mevcut test pattern |
| Frontend: HTML kpi-band div + yapı | 1 saat | index.html minimal ekleme |
| Frontend: plain CSS kartlar | 1 saat | styles.css yeni .kpi-* bloklar |
| Frontend: JS fetchMetrics + render | 3 saat | app.js 3 yeni fonksiyon + SVG üretimi |
| Frontend: showSection entegrasyonu | 0.5 saat | reports case'ine fetchMetrics() ekle |
| Browser (QWebEngine) manuel test | 1 saat | 5 senaryo + screenshot kanıtı |
| QA: Leyla gözüyle kontrol | 0.5 saat | Türkçe label, renk, boş-state |
| **TOPLAM** | **12 saat** | **= 1.5–2 gün** |

Kritik yol: Backend (5s) → Frontend JS (3s) → Manuel test (1s). Paralel yapılabilir: CSS ve HTML eşzamanlı yazılabilir.

---

## 10) RİSK & ROLLBACK

Riskler ve önlemler:

R1 — production_history.json çok büyürse (10k+ satır):
  Etki: metrics_payload() 500ms+ süre, Raporlar sayfası yavaş açılır.
  Önlem: İlk sürümde inline. 249 satır ~5ms. 1000 satır ~15ms. Eşiği geçince in-memory TTL cache (60s) eklemek için hazır hook bırakılır.

R2 — Mevcut Raporlar sayfası layout bozulması:
  Etki: Mevcut tablo, readiness rozeti, humanSummary kısmı bozulur.
  Önlem: kpi-band tamamen izole <div>; flexbox'ta kendi bloğu; overflow:hidden; mevcut elemanlara CSS cascade yok.

R3 — Chart library bundle boyutu (eğer Chart.js seçilseydi):
  Önlem: Vanilla SVG seçildi (0 bağımlılık). Bu risk ortadan kalktı.

R4 — Görsel kalite Leyla'ya uymayabilir:
  Etki: Renk/font/boyut geri bildirimi.
  Önlem: İlk deploy sonrası 1 iterasyon revize hakkı planlanmıştır.

R5 — QWebChannel'da metrics_payload slot kaydı gözden kaçarsa:
  Etki: bridge.metrics_payload undefined hatası, kpi-band hata durumu gösterir.
  Önlem: Slot ismini bridge.py register listesine eklemek ayrı adım olarak işaretlenir; missing slot → hata state (session kırılmaz).

Rollback planı:
- Yeni dosyalar (sadece ekleme, mevcut dosya değişikliği): git revert <commit_hash>
- Etkilenen dosyalar: report_api.py (+metrics_payload), bridge.py (+1 @Slot kaydı), index.html (+kpi-band div), app.js (+3 fonksiyon), styles.css (+.kpi-* bloklar).
- Geri alma süresi: < 5 dakika (git revert + uygulama yeniden başlatma).
- Mevcut Raporlar akışı bağımsız; rollback sonrası readiness/summary/errors aynen çalışmaya devam eder.

---

## Ek: Dosya Değişiklik Özeti

| Dosya | İşlem | Mevcut kod dokunuluyor mu? |
|---|---|---|
| src/webui_backend/report_api.py | +metrics_payload() fonksiyon | HAYIR (sadece ekleme) |
| src/webui_backend/bridge.py | +@Slot kaydı | EVET (tek satır, append) |
| src/webui/index.html | +<div id="kpi-band"> | EVET (section içi, en üste) |
| src/webui/app.js | +3 fonksiyon | EVET (dosya sonu append) |
| src/webui/styles.css | +.kpi-* bloklar | EVET (dosya sonu append) |
| tests/test_metrics_payload.py | YENİ dosya | — |

Lazer/DXF/RDWorks/Mochary/mucox dosyalarına dokunulmaz.
SYS-2 sahte success badge'leri bu spec kapsamında değiştirilmez.
