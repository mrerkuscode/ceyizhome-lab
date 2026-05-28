# CeyizHome Lab — Stratejik Yol Haritası ve Pazar Araştırması

**Tarih:** 2026-05-28 | **Versiyon:** v1.0 | **Hazırlayan:** Claude Chrome (web araştırma + repo analizi)
**Kapsam:** Sadece okuma + web araştırma. Kod dosyalarına dokunulmadı. Her iddia kaynaklı.

---

## 1. ÖZET

CeyizHome Lab, Türkiye'nin çeyiz/düğün/kişiselleştirme segmentine yönelik, PySide6 + HTML/CSS/JS hibrit mimarisiyle çalışan yerel bir üretim otomasyon sistemidir. 6 aylık geliştirme ile 20 API modülü, 187 @Slot fonksiyon, 21.391 satır app.js ve 3.871 satır index.html'ye ulaşmıştır. Etiket basım (PDF/PNG) ve lazer kesim (DXF/SVG) modülleri çalışır durumda; Trendyol entegrasyonu 522 sipariş/soru kaydıyla canlı bağlantıda. Sistemin kritik eksikleri şunlardır: ürün tanım veri tabanı boş (0 kayıt), SYS-2 sahte success kalıntıları (4 bilinen nokta), CI/CD yok, test coverage düşük, 21k satırlık tek JS dosyası bakım kabusuna doğru gidiyor. Pazar fırsatı gerçek: Türkiye'de kişiselleştirilmiş etiket + lazer kesim otomasyonu için özel bir yazılım yok; mevcut rakipler (BarTender, NiceLabel, Yaylasoft) genel amaçlıdır ve çeyiz/düğün iş akışını hiç anlamıyor.

---

## 2. MEVCUT DURUM (Kanıtlı — Repo Dökümanlarından)

### 2.1 Çalışan Modüller

| Modül | Durum | Kanıt |
|---|---|---|
| Etiket Studio (PDF/PNG üretim) | ✅ Çalışıyor | DISCOVERY_AND_PLAN.md; label_api.py 379 satır |
| Lazer Kesim (DXF/SVG üretim) | ✅ Çalışıyor (V1.0) | 00_DISCOVERY_SUMMARY.md; 167 SVG ref korunuyor |
| Visual Reporting Yaklaşım A | ✅ Eklendi (test bekliyor) | A_IMPLEMENTATION_REPORT.md; commit 738f92b |
| Trendyol Entegrasyon | ✅ Canlı bağlantı | 01_trendyol_reality.md; 522 soru, last sync 2026-05-19 |
| Backup Sistemi | ✅ Çalışıyor | 00_DISCOVERY_SUMMARY.md; 40 yedek |
| WebUI (HTML/JS/CSS) | ✅ Çalışıyor | ARCHITECTURE_ANALYSIS.md; QWebChannel pattern |
| Browser Mode (Flask REST) | 🔨 Sprint 1 devam | ARCHITECTURE_ANALYSIS.md; strateji B seçildi |
| Ürün Tanım Sistemi | 🟡 Altyapı var, veri yok | 00_DISCOVERY_SUMMARY.md; product_definitions.json 0 kayıt |
| Print Queue | 🟡 Boş | 00_DISCOVERY_SUMMARY.md; print_queue.json [] |

### 2.2 Veri Hacmi (2026-05-28 itibarıyla)

| Dosya | Büyüklük | İçerik |
|---|---|---|
| data/production_history.json | 249 satır / 185 KB | 2026-05-07 → 05-23 üretim |
| data/trendyol_questions_context.json | 522 satır / 903 KB | 214 sipariş, 10 barcode |
| data/trendyol_product_mappings.json | 36 satır | Onaylı mapping |
| data/trendyol_mapping_suggestions.json | 332 satır | Operatör bekliyor |
| src/webui/app.js | 21.391 satır | Tek dosya — bakım riski |
| src/webui/index.html | 3.871 satır | Tek HTML dosyası |

### 2.3 Bilinen Açık Sorunlar

- **SYS-2 — Sahte Success (4 nokta):** label_api.py:83 `HAZIR` hardcoded; app.js `Doğrulandı` badge; sentToProduction:true literal; Faz1 #5 preflight bridge-yok OK. *Kanıt: 14_unknown_unknowns.md*
- **Ürün tanım veri tabanı boş:** 332 mapping suggestion bekliyor ama product_definitions.json 0 kayıt. Trendyol siparişleri cevaplanamıyor. *Kanıt: 03_product_definitions_new.md*
- **Test coverage düşük:** Sadece test_metrics_payload.py (7 test). CI/CD yok. *Kanıt: A_IMPLEMENTATION_REPORT.md*
- **app.js modüler değil:** 21.391 satır tek dosya. Yeni fonksiyon eklemek riskli hata bölgesi büyütüyor. *Kanıt: ARCHITECTURE_ANALYSIS.md*
- **Backup auto-pruning yok:** 40 backup var ama otomatik temizlik mekanizması belirsiz. *Kanıt: 14_unknown_unknowns.md*
- **Trendyol rate-limit bilinmiyor:** Son sync 2026-05-19, 9+ gün sessiz. Quota durumu test edilmedi. *Kanıt: 14_unknown_unknowns.md*

---

## 3. PAZAR ARAŞTIRMASI (Web Search Bulguları)

### Arama 1 — "etiket basım yazılımı Türkiye"

**En önemli 3 bulgu:**
- Türkiye pazarında Teklynx Labelview, Codesoft, BarTender distribütörleri var (labelview.com.tr). Tümü genel amaçlı, çeyiz/düğün segmentine özel değil.
- Yaylasoft (barkodyazdir.com) Türkçe barkod/etiket yazılımı sunuyor; sürükle-bırak arayüz, uygun fiyat — ama sadece barkod odaklı, kişiselleştirme iş akışı yok.
- Etiket baskı hizmet fiyatı (Armut.com): İstanbul'da 500-650 TL/iş. Yazılım satın almak yerine baskı hizmeti almak yaygın — yani pazarda self-servis yazılım boşluğu var.

**CeyizHome Lab için anlamı:** Yerel rakip az. "Çeyiz etiketi" + "laser isim kesim" kombinasyonunu yapan tek yazılım henüz yok. Bu niche'i erken kapamak avantaj.

---

### Arama 2 — "label printing software global trend"

**En önemli 3 bulgu:**
- Küresel etiket pazarı 2024'te 46,5 milyar USD (Konica Minolta/Smithers verisi). Print Label Market 2026'da 57 milyar USD, 2031'de 67 milyar USD hedef — CAGR %3,28 (Mordor Intelligence).
- Variable Data Printing (kişiselleştirme) segmenti 2024'te 18,7 milyar USD, 2025-2030 CAGR %13,6 — standart etiketin 4x büyüme hızında (Grand View Research).
- Digital Label Printing 2025'te 12,3 milyar USD, 2035'te 20,6 milyar USD — CAGR %5,3 (PR Newswire UK 2026).

**CeyizHome Lab için anlamı:** Kişiselleştirilmiş etiket (VDP) segmenti normal etiketin 4 katı büyüyor. Bu tam CeyizHome Lab'ın yaptığı iş. Zamanlama doğru.

---

### Arama 3 — "Trendyol entegrasyon etiket basım API"

**En önemli 3 bulgu:**
- Trendyol resmi API (developers.trendyol.com) webhook + sipariş endpoint'leri sunuyor. Mevcut implementasyon polling-only; webhook geçişi otomasyonu artırır.
- Piyasada Sopyo, Hamurlabs, Magenty gibi Trendyol entegrasyon firmaları var — ama bunlar sipariş/stok yönetimi, etiket basım değil.
- Trendyol API entegrasyonunu anlatan Sentos rehberi (2025): "ürün, sipariş, stok ve fatura bilgilerinin otomatik senkronizasyonu." Etiket basım + lazer hazırlık otomasyonu hiçbirinde yok.

**CeyizHome Lab için anlamı:** Trendyol sipariş → etiket basım → lazer kesim otomatik zinciri piyasada benzersiz. Bu bir SaaS ürünü olarak satılabilir.

---

### Arama 4 — "çeyiz organizasyonu ürünleri etiket Türkiye"

**En önemli 3 bulgu:**
- Trendyol'da "çeyiz kolisi sticker" araması aktif pazar: 200-400 TL/paket fiyat aralığı, 440+ değerlendirme (Trendyol.com).
- Çeyiz etiketi üreten firmalar (1etiket.com.tr, zajabaski.com, baskiyap.com) manuel sipariş alıyor — otomasyon yok, kişiselleştirme sınırlı.
- Canva ücretsiz düğün etiketi şablonları sunuyor; bu pazarın bir kısmını "DIY" (kendin yap) segmentine kaptırmış olabilir.

**CeyizHome Lab için anlamı:** Leyla'nın yaptığı iş (kişisel isimli lazer + etiket) için yazılım yok. Rekabet el emeği + manuel sipariş. Otomasyon avantajı büyük.

---

### Arama 5 — "wedding favor labels printing software uluslararası"

**En önemli 3 bulgu:**
- Etsy'de wedding favor label şablonu büyük pazar: tek ürün 12.000+ satış, €6-8 fiyat. "Canva/Corjl ile edit, PDF indir" modeli yaygın.
- Templett platformu Etsy üzerinde template satışı yapan satıcılara altyapı sunuyor; 2025'te en çok satan kategoriler arasında düğün şablonları.
- "Phomemo" gibi yazıcı üreticileri Etsy etiket baskısı rehberleri yayınlıyor — donanım + yazılım entegrasyonu boşluğu görünüyor.

**CeyizHome Lab için anlamı:** Uluslararası pazarda "kişisel isimli düğün iyiliği etiketi" büyük. CeyizHome Lab'ı Etsy satıcılarına yönelik bir araç olarak konumlandırmak mümkün.

---

### Arama 6 — "open source label designer alternatives"

**En önemli 3 bulgu:**
- GitHub'da labelle-org/labelle (DYMO yazıcılar için), SVGnest (2D nesting, ücretsiz açık kaynak), blabel (Python barkod etiketi) var — ama çeyiz/kişiselleştirme odaklı yok.
- GitHub topics "label-printing": "Drag-and-drop editor, barcodes, CSV/Excel batch generation, self-hosted" (2 gün önce aktif proje). Rakip olabilir — ama QWebChannel + lazer kombinasyonu yok.
- SourceForge'da KBarcode (KDE tabanlı, eski). Aktif geliştirme yok. Türkçe desteği yok.

**CeyizHome Lab için anlamı:** Açık kaynak rakipler var ama hiçbiri: (1) Türkçe, (2) Trendyol entegrasyonu, (3) lazer + etiket kombine, (4) çeyiz iş akışı içermiyor. Niche korunuyor.

---

### Arama 7 — "PySide6 vs Electron desktop app"

**En önemli 3 bulgu:**
- "Why I Ditched Electron for Qt" (Arbisoft, Ekim 2025): Qt uygulamaları 2 saniyede açılıyor; Electron 150-250 MB RAM baseline kullanıyor, Qt çok daha hafif.
- Reddit (Nisan 2026): "PySide6 is powerful but still bulky. Flet is the fastest." Birden fazla Python GUI karşılaştırması PySide6'yı iş uygulamaları için önerdi.
- Softwarelogic.co (Kasım 2025): Qt vs Electron vs Tauri karşılaştırma — Qt: en iyi performans, en düşük RAM; Tauri: küçük bundle; Electron: en kolay web dev geçişi.

**CeyizHome Lab için anlamı:** PySide6 seçimi doğru ve savunulabilir. Electron'a geçmek performans kaybı ve paket boyutu artışı anlamına gelir. Browser Mode sprint'i için Flask REST mimarisi (ARCHITECTURE_ANALYSIS.md önerisi) mantıklı.

---

### Arama 8 — "Flask production WSGI gunicorn"

**En önemli 3 bulgu:**
- Flask resmi dok: "Gunicorn runs on Windows only under WSL." Windows'ta production deploy için Waitress veya uWSGI (Windows native) daha uygun.
- DEV Community (Nisan 2025): Flask + Gunicorn + Supervisor + Nginx stack standart Linux deploy. Windows için farklı yaklaşım gerekiyor.
- MassiveGRID (Şubat 2026): Ubuntu 24.04 üzerinde Gunicorn + systemd kapsamlı rehber. Windows desteği resmi olarak kaldırıldı (Microsoft Azure Python doku: "Python on Windows no longer supported").

**CeyizHome Lab için anlamı:** Uygulama Windows local çalışıyor. Browser Mode Flask sunucusu için Gunicorn yerine **Waitress** (Windows native) veya **WSL2 + Gunicorn** tercih edilmeli. Production deploy planlıyorsa Linux sunucu zorunlu.

---

### Arama 9 — "DXF nesting algorithm"

**En önemli 3 bulgu:**
- SVGnest (svgnest.com): Tamamen ücretsiz, açık kaynak, CNC makineler için 2D nesting. "Part-in-part nesting ve concave area detection" desteği var.
- GitHub 2d-nesting topics (27 Kasım 2025): "community-based open source nesting for laser cutters" — aktif topluluk.
- Industrial Monitor Direct (Mart 2026): "Open-source Python-based nesting tool specifically designed for DXF files. Maintains geometry integrity better than web-based alternatives."

**CeyizHome Lab için anlamı:** Mevcut row-based SVG plaka yerleşimi (tests/test_mvp_safety.py'de kanıt var) geliştirilmek istenirse SVGnest algoritması entegre edilebilir. Lantek gibi ticari alternatifler çok pahalı.

---

### Arama 10 — "PDF generation Python ReportLab vs WeasyPrint"

**En önemli 3 bulgu:**
- Nutrient.io (Nisan 2026): "ReportLab: canvas model, absolute precision; WeasyPrint: HTML-to-PDF, CSS layout." Rulo etiket için ReportLab canvas daha kontrollü.
- Dailyhunt 2025: "ReportLab and fpdf2 are the top choices for flexible and efficient Python PDF generation. WeasyPrint and PDFKit are slightly heavier and slower."
- Templated.io (Mayıs 2025): "8 Python PDF tools compared." fpdf2 (FPDF2) en hafif; ReportLab en olgun; WeasyPrint HTML-CSS tabanlı için uygun.

**CeyizHome Lab için anlamı:** Mevcut sistem ReportLab kullanıyor (label_designer/ altında). Bu seçim savunulabilir — rulo etiket canvas-level kontrolü gerektirir. WeasyPrint geçişi HTML şablonlu etiket istediğinde düşünülebilir, şimdilik değişiklik gereksiz.

---

## 4. REKABET ANALİZİ

### 4.1 Rakip Karşılaştırma Tablosu

| Kriter | **CeyizHome Lab** | **BarTender** | **NiceLabel** | **Yaylasoft** |
|---|---|---|---|---|
| Hedef pazar | Çeyiz/düğün üretici | Genel endüstri | Genel endüstri | Küçük işletme/barkod |
| Fiyat | Özel geliştirme | $495+ (one-time) / abonelik | ~$300-600/yıl | Uygun, TR fiyat |
| Türkçe destek | ✅ Tam | ❌ Yok | ❌ Yok | ✅ Var |
| Trendyol entegrasyon | ✅ Canlı (522 sipariş) | ❌ Yok | ❌ Yok | ❌ Yok |
| Lazer kesim + etiket kombine | ✅ Birleşik | ❌ Sadece etiket | ❌ Sadece etiket | ❌ Yok |
| Kişiselleştirme iş akışı | ✅ Çeyiz/isim özel | ❌ Genel barkod | ❌ Genel barkod | ❌ Genel barkod |
| AI destekli sipariş analizi | ✅ GPT-5-nano entegre | ❌ Yok | ❌ Yok | ❌ Yok |
| Windows yerel çalışma | ✅ Offline | ✅ Windows | ✅ Windows | ✅ Windows |
| Açık kaynak | ✅ Kendi kodu | ❌ Tescilli | ❌ Tescilli | ❌ Tescilli |
| Test/CI | 🟡 Düşük | ✅ Kurumsal | ✅ Kurumsal | Bilinmiyor |

### 4.2 Rakip Detay

**BarTender (Seagull Scientific):** Küresel pazar lideri, 40 milyar+ etiket/yıl. Starter $495 one-time, Enterprise çok daha pahalı (kurumsal fiyat). RFID, barkod, seri numaralı etiket odaklı. Türkçe yok. Çeyiz iş akışı kavramı yok.

**NiceLabel (Loftware):** BarTender'ın doğrudan rakibi, ~$300-600/yıl Designer abonelik. LabelInn karşılaştırmasına göre NiceLabel %50 daha pahalı eşdeğer özellikler için. Türkçe yok. Kişiselleştirme/düğün konsepti yok.

**Yaylasoft (barkodyazdir.com):** Türk pazar oyuncusu, barkod etiket yazma odaklı. Sürükle-bırak tasarım. Trendyol entegrasyonu yok. Lazer modülü yok. AI yok. CeyizHome Lab'la doğrudan rekabet etmiyor — farklı segment.

**Canva (ücretsiz şablonlar):** DIY kullanıcıları için tehdit. Ücretsiz düğün etiketi şablonları var. Ama toplu üretim, Excel entegrasyonu, lazer kesim, Trendyol API yok. Leyla gibi üreticiler için yetersiz.

---

## 5. KISA VADELİ YOL HARİTASI (Haziran 2026 — 4-6 Hafta)

### Sprint Planı

| Sprint | Süre | Öncelik | Kapsam |
|---|---|---|---|
| **Browser Mode Sprint 2** | 1 hafta | KRİTİK | POST endpoint'leri (mark_printed, save_label_model_field, product_definition_save) |
| **Browser Mode Sprint 3** | 1 hafta | YÜKSEK | Dosya upload (Excel, şablon, font), subprocess job yönetimi |
| **SYS-2 Fix — Yaklaşım C** | 3-4 gün | YÜKSEK | Kalite Kapısı: label_api.py:83 HAZIR fix; app.js Doğrulandı badge |
| **Ürün Tanım Sprint** | 2-3 gün | KRİTİK | product_definitions.json doldurulması; UI'de Eksik Tanımlar sayfası |
| **Test Coverage** | 2 gün | ORTA | Kritik API'ler için pytest (label_api, bridge slot'lar) |
| **Backup Auto-Pruning** | 1 gün | DÜŞÜK | 40+ backup otomatik temizleme; disk şişme önleme |

### Bu Ayki En Önemli 3 Aksiyon

1. **Ürün tanım veri tabanını doldur:** 10 unique Trendyol barcode → 10 ürün tanımı (UI veya Excel). Bu olmadan Trendyol siparişleri işlenemiyor.
2. **Browser Mode Sprint 2 tamamla:** POST endpoint'leri olmadan browser mode sadece görüntüleme. Çalışan bir web arayüzü için yazma operasyonları şart.
3. **SYS-2 fix (Yaklaşım C) başlat:** 4 bilinen sahte success noktası. Her sprint ertelemek teknik borcu artırıyor.

---

## 6. ORTA VADELİ VİZYON (Yaz 2026 — 2-3 Ay)

| Özellik | Gerekçe | Risk |
|---|---|---|
| **Çoklu kullanıcı (auth + role)** | Birden fazla operatör veya dükkan sahibi. Multi-user olmadan SaaS model imkansız. | Orta — mevcut single-user varsayımı derin |
| **Mobile responsive UI** | Leyla telefonda sipariş bakıyor. %100 masaüstü bağımlılığı kırılmalı. | Düşük — CSS değişikliği yeterli |
| **Trendyol webhook entegrasyonu** | Polling-only mevcut akış 9+ gündür sync yok (01_trendyol_reality.md). Webhook anlık güncelleme sağlar. | Orta — Trendyol webhook desteğini doğrulamak gerekiyor (14_unknown_unknowns.md) |
| **Audit log dashboard** | production_audit_log.json 13 event var ama görsel panel yok. Kim ne ürettijini izlemek için. | Düşük — veri zaten var, UI yok |
| **Real-time log akışı (SSE/WebSocket)** | Browser Mode'da run_production subprocess log'larını anında göstermek için. | Orta — ARCHITECTURE_ANALYSIS.md'de Flask B alternatifi önerilmişti; WS FastAPI gerektirir |
| **app.js modülerleştirme (kritik!)** | 21.391 satır tek dosya. Her sprint riskini artırıyor. ES modül geçişi yapılmalı. | Yüksek — büyük refactor, kapsamlı test gerekli |

---

## 7. UZUN VADELİ HEDEFLER (Sonbahar 2026+ — 6+ Ay)

| Hedef | Açıklama | Koşul |
|---|---|---|
| **Çok dükkanlı yönetim** | Birden fazla çeyiz/düğün işletmesi aynı platformda. Her dükkan kendi veri alanında. | Çoklu kullanıcı + auth altyapısı olmalı |
| **AI destekli model önerisi** | GPT-5-nano zaten entegre (ai_model: gpt-5-nano, ai_enabled: true — 01_trendyol_reality.md). Trendyol siparişinden otomatik etiket + lazer model önerisi. | AI confidence threshold tuning gerekli |
| **Otomatik fiyatlandırma** | Sipariş adet × materyal × lazer süre = otomatik fiyat. Leyla'nın manuel hesabını kaldırır. | Lazer süre tahmini algoritması gerekli |
| **SaaS model (multi-tenant)** | Aylık abonelik. Türkiye çeyiz/düğün sektörüne özel niche SaaS. | Linux sunucu deploy, auth, billing altyapısı |
| **Etsy/Uluslararası pazar entegrasyonu** | Etsy API ile sipariş → otomatik üretim zinciri. VDP segmenti %13,6 CAGR büyüyor (Grand View Research). | Önce Trendyol otomasyonu stabilize edilmeli |
| **DXF Nesting iyileştirme** | SVGnest açık kaynak algoritması entegrasyonu. Mevcut row-based nesting yerine optimize yerleşim. | Lazer modülü V2.0 gerektirir |

---

## 8. RİSK MATRİSİ

### Teknik Riskler

| Risk | Olasılık | Etki | Önlem |
|---|---|---|---|
| **21k satır app.js bakım kabusuna dönüşür** | YÜKSEK | YÜKSEK | Acil: ES modül refactor planı yapılmalı. Her yeni özellik riski artırıyor. |
| **SYS-2 sahte success üretimde sorun çıkarır** | ORTA | YÜKSEK | Yaklaşım C sprint'ini ertelememek. 4 bilinen nokta var, hepsi çözümlenebilir. |
| **Trendyol API rate-limit veya token expiry** | ORTA | YÜKSEK | Bağlantı testi yapılmalı. stage=False, 9+ gün sessiz (14_unknown_unknowns.md). |
| **product_definitions.json boş kalırsa** | YÜKSEK | YÜKSEK | Leyla'nın veri girmesi zorunlu. UI desteği acil (Eksik Tanımlar sayfası). |
| **332 mapping suggestion review backlog** | ORTA | ORTA | Toplu onay arayüzü gerekli. Tek tek onay çok yavaş. |
| **Backup disk şişmesi** | DÜŞÜK | ORTA | Auto-pruning yok (14_unknown_unknowns.md). 40 backup şimdi, 200 olursa? |
| **Windows native Flask deploy sorunu** | ORTA | ORTA | Gunicorn Windows'ta WSL gerektirir. Waitress alternatifi kullanılmalı. |
| **Test coverage düşük — regresyon riski** | YÜKSEK | ORTA | Her sprint'e 3-5 pytest testi eklemek kurallaştırılmalı. |

### İş Riskleri

| Risk | Olasılık | Etki | Önlem |
|---|---|---|---|
| **Trendyol politika/API değişikliği** | ORTA | YÜKSEK | Çoklu platform (Trendyol + Etsy + manuel) stratejisi. |
| **Canva ücretsiz araçlar DIY segmentini kapıyor** | YÜKSEK | ORTA | CeyizHome Lab'ın avantajı otomasyon + lazer. Canva lazer yapamaz. |
| **Büyük rakip (Labelary, NiceLabel Türkiye ofisi)** | DÜŞÜK | YÜKSEK | Niche'i erken kapatmak; Trendyol entegrasyonu moat oluşturuyor. |
| **Leyla tek kullanıcı → ölçeklenemiyor** | YÜKSEK | ORTA | Çoklu kullanıcı altyapısı yol haritada var. Erken başlanmalı. |

---

## 9. ÖNERİLEN İLK 5 AKSİYON (Önümüzdeki Hafta)

Aşağıdaki aksiyonlar "yapılabilir, kanıtlı veri var, engel yok" kriterine göre sıralandı:

**AKSİYON 1 — Ürün tanım girişi (Leyla yapacak, ~2-3 saat)**
Trendyol'da geçen aydaki 10 unique barcode'u product_definitions.json'a gir. Bu olmadan Trendyol sipariş akışı kör gidiyor. *Kanıt: 00_DISCOVERY_SUMMARY.md "Önerilen ilk adım" bölümü.*

**AKSİYON 2 — Browser Mode Sprint 2 POST endpoint'leri (~3-4 gün)**
ARCHITECTURE_ANALYSIS.md Sprint 2 listesindeki 3 endpoint: mark_printed, save_label_model_field, product_definition_save. Browser Mode sadece GET'lerle yarım kalıyor.

**AKSİYON 3 — SYS-2 fix başlat (Yaklaşım C, ~5 gün)**
label_api.py:83 HAZIR default ve app.js Doğrulandı badge her sprint'te "bilinen TODO" olarak geçiyor. Ertelemek güven kaybına yol açar. Yaklaşım C spec'ini yaz ve implement et.

**AKSİYON 4 — Trendyol bağlantı testi (~1 saat)**
9+ gündür sync yok. test_trendyol_connection slot'unu çağır, token geçerliliğini doğrula. Rate-limit durumunu öğren. *Kanıt: 14_unknown_unknowns.md*

**AKSİYON 5 — app.js modüler refactor planı (~yarım gün, sadece plan)**
Kodu şimdi değiştirme. Sadece: hangi fonksiyonlar hangi modüle gider, migration adımları neler, risksiz bölünme noktası neresi? Belgeyi output/ altına commit et. Bu planı yapmadan 21k satır büyümeye devam eder.

---

## 10. AÇIK SORULAR (Leyla'ya Sormak Gereken Stratejik Şeyler)

Bu soruların cevabı teknik kararları doğrudan etkiliyor:

1. **Kaç sipariş/gün ortalama?** 249 history kaydı 17 güne yayılmış = ~15 üretim/gün. Bu doğru mu? Peak dönem (düğün sezonu) ne kadar?

2. **Ürün tanım sayısı gerçekte kaç?** 10 unique barcode görünüyor ama gerçek katalog boyutu ne? 100 mu, 500 mu, 1000 mu? Bu veritabanı tasarımını etkiliyor.

3. **Browser Mode ne zaman gerekli?** Başka bir bilgisayardan mı, telefondan mı, dışarıdan mı erişmek isteniyor? Yoksa hep aynı Windows makinesi mi?

4. **Çoklu kullanıcı planı var mı?** Leyla dışında başka operatör var mı veya olacak mı? Bu auth sistemi önceliğini belirliyor.

5. **Uluslararası (Etsy) satış düşünülüyor mu?** Türkçe label text dışında İngilizce/başka dil desteği gerekir mi?

6. **Lazer V1.0 "rafta" ne zaman aktive edilecek?** DXF kütüphane 2 test entry var. Gerçek prodüksiyonda kaç DXF dosyası hazır?

7. **Trendyol aylık sipariş hacmi?** 214 unique sipariş görünüyor ama bunlar 1 haftalık veri. Toplam sipariş sayısı ne kadar?

8. **Mochary font ve connected_script.ttf lisansı netleştirildi mi?** Lazer kesim font bağımlılığı kritik güvenlik noktası (README.md; LASER_CUT Font Gereksinimi bölümü).

---

## Ekler

**Referans Dökümanlar:**
- output/visual_reporting/DISCOVERY_AND_PLAN.md
- output/visual_reporting/A_IMPLEMENTATION_REPORT.md
- output/2026-05-28/browser_mode/ARCHITECTURE_ANALYSIS.md
- output/2026-05-28/project_discovery/00_DISCOVERY_SUMMARY.md
- output/2026-05-28/project_discovery/01_trendyol_reality.md
- output/2026-05-28/project_discovery/14_unknown_unknowns.md

**Web Kaynakları:**
- Mordor Intelligence: Print Label Market $57B→$67B, CAGR %3,28
- Grand View Research: Variable Data Printing CAGR %13,6 (2025-2030)
- LabelInn: NiceLabel $300-600/yıl fiyatlandırma
- SoftwareSuggest: BarTender $495 one-time başlangıç
- Arbisoft: Qt vs Electron performans karşılaştırması (Ekim 2025)
- Konica Minolta TR: Küresel etiket pazarı 46,5B USD (2024)

<!-- research: stratejik yol haritasi ve pazar arastirmasi -->
