# İsim Kesim (Lazer) Modülü — Durum Tespiti ve Plan

**Tarih:** 2026-05-28 | **Yöntem:** Salt okuma. Kod değiştirilmedi. Her bulgu kaynaklı.
**Paralel sprint:** Code Sprint 3 (Browser Mode) devam ediyor. Bu analiz bağımsız.

---

## 1. MODÜL YAPISI (Dosya Haritası)

### Çekirdek Üretim Motoru (CLI tabanlı)

| Dosya | Boyut | Görev | Kanıt |
|---|---|---|---|
| `src/laser_service.py` | ~120 satır | Ana lazer iş koordinatörü; `generate_laser_jobs()` — gruplayıp `nest_laser_orders()` çağırır, SVG + CSV + txt yazar | laser_service.py:1-120 okundu |
| `src/laser_nesting.py` | Orta boy | Row-based plaka yerleşimi; `LaserNestingResult`, `nest_laser_orders()` | src/ listing |
| `src/svg_generator.py` | 86 satır / 3.12 KB | `write_laser_plate_svg()` — plaka SVG üretici | 86 lines (74 loc) görüldü |
| `src/text_utils.py` | Yardımcı | `safe_filename()`, Türkçe karakter handling | laser_service.py import |
| `src/models.py` | Yardımcı | `Order`, `AppSettings`, `ValidationIssue` veri modelleri | laser_service.py import |

### WebUI Backend (QWebChannel @Slot'ları)

| Dosya | Boyut | Görev | Kanıt |
|---|---|---|---|
| `src/webui_backend/dxf_library_api.py` | 666 satır / 25 KB | DXF kütüphane CRUD + watcher + sipariş eşleştirme | 04_dxf_library_status.md |
| `src/webui_backend/dxf_library_watcher.py` | 168 satır | watchdog daemon; 3 klasörü izler (70x40, 80x40, 100x40) | 04_dxf_library_status.md |
| `src/webui_backend/name_cut_queue_api.py` | 446 satır / 21 KB | İsim kesim kuyruğu CRUD; status değiştirme, duplicate kontrolü | 07_queue_system.md |
| `src/webui_backend/combined_production_api.py` | ~391 KB (büyük) | `_corel_exact_reference_override_for_item()`: DXF lookup → SVG path üretim; fallback zinciri | 04_dxf_library_status.md |
| `src/webui_backend/corel_reference_importer.py` | var | 167 SVG referans kütüphanesi yönetimi (CRUD + onay zinciri) | 12_endpoints_inventory.md |
| `src/webui_backend/font_analysis.py` | var | Font bağlantı analizi (connected_status kontrolü) | bridge.py pattern |
| `src/webui_backend/ai_assisted_corel_style_glyph_intelligence.py` | 7 KB | AI destekli Corel stili glyph oluşturma — **master flag ile KAPALI** | 14_unknown_unknowns.md |
| `src/webui_backend/internal_corel_like_vector_name_cut_engine.py` | 8 KB / 170 satır | İç Corel benzeri vektör motor — **master flag ile KAPALI** | 14_unknown_unknowns.md |

### Veri Dosyaları

| Dosya | Boyut | İçerik |
|---|---|---|
| `data/dxf_library.json` | Index | 2 aktif entry (ayse 70x40 ✓, umit 70x40 ⚠️ test boyutu) |
| `data/dxf_library_ascii_to_turkish.json` | 19 entry | ASCII→Türkçe display map (ahmet→Ahmet vb.) |
| `data/name_cut_queue.json` | 2 satır | Aktif kuyruk öğeleri |
| `data/name_cut_transfer_history.json` | boş | Transfer geçmişi (export yapılmış ama transfer yok) |
| `data/name_cut_export_history.json` | 2 satır | Export audit log |
| `assets/dxf_library/70x40/` | 3 dosya | ayse.dxf ✓, ayşe.dxf ❌ (TR filename reddedildi), umit.dxf ⚠️ |
| `assets/dxf_library/80x40/` | 0 dosya | Boş |
| `assets/dxf_library/100x40/` | 0 dosya | Boş |
| `assets/references/corel_name_reference_library.json` | 167 entry | Legacy SVG ref kütüphanesi (3 approved, 164 pending/style) |

### UI Giriş Noktası

`<section id="nameCutStudio">` — sidebar'da **İsim Kesim Studio** menü öğesi (`data-page="nameCutStudio"`). Teknik menüde ayrıca `<section id="laser">` de var. *Kanıt: 13_menu_state_v2.md*

---

## 2. ÇALIŞAN ÖZELLİKLER (V1.0)

| Özellik | Durum | Kanıt |
|---|---|---|
| SVG plaka üretimi (LASER_ENGRAVE + LASER_CUT) | ✅ Çalışıyor | `src/laser_service.py` + `src/svg_generator.py` aktif |
| Row-based nesting (plakalara otomatik yerleşim) | ✅ Çalışıyor | `src/laser_nesting.py`, `nest_laser_orders()` |
| DXF kütüphane lookup (birincil yol) | ✅ Çalışıyor | `dxf_library_api.py` 8 slot, 2 aktif DXF |
| ASCII normalize (Türkçe→ASCII isim dönüşümü) | ✅ Çalışıyor | `to_ascii_name()` — ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u |
| 167 SVG ref legacy fallback kütüphanesi | ✅ Korunuyor | 3 approved, 164 style; DXF bulamadığında devreye girer |
| DXF watcher (dosya izleme daemon) | ✅ Kurulu | watchdog 6.0.0; default OFF, operatör aktif eder |
| İsim kesim kuyruğu (name_cut_queue) | ✅ Çalışıyor | 2 aktif satır; status güncelleme + duplicate kontrol |
| Plaka layout raporu (CSV + job_info.txt) | ✅ Çalışıyor | `laser_service.py` `_write_plate_reports()` + `_write_plate_job_infos()` |
| Türkçe font bağlantılık kontrolü (connected_status) | ✅ Çalışıyor | `font_analysis.py`, `connected_status`: OK / WARNING / ERROR |
| Güvenlik: RDWorks açılmaz, lazer başlatılmaz | ✅ Aktif | `auto_start_laser: false` (config/settings.yaml); job_info.txt'te kanıt |
| operatör onayı zorunlu (requiresOperatorReview) | ✅ Aktif | `_corel_reference_override_payload` her override'da set eder |
| AI Glyph Engine (`use_legacy_name_cut_algorithms`) | ⛔ KAPALI | master flag False — çağrılmıyor; 14_unknown_unknowns.md |
| Internal Corel-like Engine | ⛔ KAPALI | master flag False — çağrılmıyor; 14_unknown_unknowns.md |
| Excel toplu isim girişi (LaserStudio üzerinden) | 🟡 Kısmi | Excel→LASER_CUT siparişi çalışıyor; toplu DXF eşleştirme UI kısmi |
| RDWorks export | ❌ Yok | Sadece SVG üretiliyor; RDWorks'e aktarım manuel |
| Mochary font | ⚠️ Hash korunuyor | `assets/fonts/connected_script.ttf` zorunlu; yoksa LASER_CUT bloke |

---

## 3. EKSİKLER + TODO LİSTESİ

### Kritik Eksikler (Üretimi Bloke Eden)

- **DXF kütüphane 2 entry:** ayse + umit. Gerçek üretimde yüzlerce isim gerekiyor. Leyla DXF çizmeden sistem kör çalışıyor. *Kanıt: 04_dxf_library_status.md — "🟡 Sadece 2 entry"*
- **umit.dxf test boyutu:** 10.9×7.2 mm — production 70×40 olmalı. Yanlış ölçekli dosya uyarı veriyor. *Kanıt: 04_dxf_library_status.md — "🟡 umit.dxf test dosyası"*
- **80x40 ve 100x40 klasörler boş:** Farklı ölçü siparişleri gelirse karşılık yok. *Kanıt: 04_dxf_library_status.md klasör tablosu*

### UI / UX Eksikleri

- **Name cut transfer history boş:** 2 satır export yapılmış ama transfer adımı atlanmış. Ne zaman transfer geçilmeli açık değil. *Kanıt: 07_queue_system.md — "🟡 Name cut queue 2 satır var ama transfer history boş"*
- **"check_name_cut_queue_duplicate" mantığı belirsiz:** Hash mi, semantic match mi? Test edilemedi. *Kanıt: 07_queue_system.md*
- **"Lazer" teknik menüsü:** `<section id="laser">` var ama normal kullanıcı akışında görünmüyor (teknik/hidden). Birleştirme planı yok. *Kanıt: 13_menu_state_v2.md — "Lazer (laser) — Teknik"*

### Bilinen TODO / Kalıntı Kodlar

- **AI Designer + Internal Corel Engine:** İki dosya (7 KB + 8 KB) master flag ile tamamen kapalı ama kod duruyor. Sprint planında "temizlenebilir" ama "downstream call graph kontrol edilmedi." *Kanıt: 14_unknown_unknowns.md*
- **167 SVG ref'in DXF'e dönüştürülme planı:** 3 onaylı ref DXF'e taşınabilir ama plan yok. *Kanıt: 04_dxf_library_status.md — "Mevcut 167 SVG ref'in DXF'e dönüştürülme planı (ileride)"*
- **Watcher uzun süreli stabilite:** Sadece kısa test yapıldı. *Kanıt: 14_unknown_unknowns.md*
- **500+ entry'de scan süresi bilinmiyor:** Şimdi 2 entry, lineer büyüme bekleniyor ama test edilmedi.

### Hayır Listesi (Yapılmamalı — Bu Sprint)

- AI Glyph Engine'i aktive etme (master flag açılmamalı)
- Internal Corel Engine kodu silme (downstream kontrol yapılmadan)
- 167 SVG ref'i toplu DXF'e çevirme girişimi
- RDWorks entegrasyonu (güvenlik sınırları)

---

## 4. BROWSER MODE KARARI

### Öneri: ❌ HAYIR — Lazer Masaüstüne Kalmalı (Şimdilik)

**Gerekçe (3 ana neden):**

**1. Güvenlik açısından: Lazer masaüstü-bağlı güvenlik katmanları var.**
Lazer üretimi `auto_start_laser: false`, `requiresOperatorReview: True` ve `job_info.txt` uyarıları ile çevrilmiş. Bu güvenlik katmanları kasıtlı olarak QWebChannel + masaüstü ortamına bağlı. Browser Mode'a taşımak yeni risk surface açar: dosya yolu güvenliği, path traversal, SVG/DXF indirme yetkilendirmesi yeniden tasarlanmalı. ARCHITECTURE_ANALYSIS.md'de bu "Yüksek" öncelik listesinde değil.

**2. Teknik olarak: Lazer DXF → SVG üretimi subprocess/dosya bağımlı.**
`generate_laser_jobs()` çıktıları `output/YYYY-MM-DD/laser/` dizinine yazıyor. Browser Mode için bu çıktıların HTTP üzerinden serve edilmesi, yükleme/indirme endpoint'leri ve subprocess yönetimi (CommandWorker benzeri) gerekiyor. ARCHITECTURE_ANALYSIS.md Sprint 3+ kapsamında bırakmış: "Subprocess job yönetimi (render_labels, run_dry) — sonraya."

**3. Öncelik sırası: DXF kütüphane veri boşluğu browser mode'dan önce geliyor.**
2 DXF entry ile browser mode'da lazer UI açılsa da Leyla'ya gösterilecek somut bir değer yok. Önce kütüphane büyümeli.

**Avantaj/Dezavantaj Tablosu:**

| Kriter | Browser Mode'a Al | Masaüstünde Tut |
|---|---|---|
| Güvenlik riski | YÜKSEK (yeni surface) | DÜŞÜK (mevcut korumalar çalışıyor) |
| Geliştirme efor | ~2-3 hafta (Sprint 4+5) | Sıfır ek efor |
| Kullanıcı değeri şimdi | DÜŞÜK (2 DXF) | ORTA (masaüstünde mevcut) |
| Masaüstü modu bozulur mu? | HAYIR (ayrı başlar) | ZATEN ÇALIŞIYOR |
| Kritik bloke kaldırır mı? | HAYIR | HAYIR |

### Eğer İleride Browser Mode Eklenecekse (Sprint 4+ Adayları)

Önce bunlar yapılmalı, sonra browser mode değerlendirilmeli:

| Sprint | Slot Grubu | Neden Önce |
|---|---|---|
| Sprint 4 (GET) | `dxfLibraryList`, `dxfLibrarySearch`, `dxfLibraryFind` | Görüntüleme + arama; güvenli, yazma yok |
| Sprint 4 (GET) | `list_name_cut_queue_items`, `list_name_cut_transfer_history` | Kuyruk okuma; güvenli |
| Sprint 5 (POST) | `update_name_cut_queue_item_status`, `save_name_cut_queue_items` | Yazma; dikkatli implement edilmeli |
| Sprint 5 (DOSYA) | `dxfLibraryRefresh` | Scan tetikleme; dosya sistemi bağımlı |
| Sprint 6 (SUBPROCESS) | lazer üretim çalıştırma | En son; path + subprocess güvenliği gerekli |

---

## 5. SAĞLIKLI MVP İÇİN SIRALAMA

### Bu Hafta YAPILMASI GEREKEN (Lazer için)

1. **DXF kütüphane veri girişi (Leyla yapar):**
   Trendyol'dan geçen aydaki isim listesini çıkar (14 unique barcode → isim listesi). Her isim için CorelDRAW'da 70×40 mm boyutunda bağlı el yazısı DXF çiz, ASCII dosya adıyla kaydet (`mehmet.dxf`, `zeynep.dxf` vb.). `assets/dxf_library/70x40/` klasörüne at. DXF Kütüphane panelinden "Tara" butonuna bas. Bu tek adım üretim hazırlığını %0'dan %80'e çıkarır.

2. **umit.dxf'i üretim ölçeğine çek:**
   Şu an 10.9×7.2 mm — production 70×40 olmalı. Leyla doğru ölçekte DXF üretip üzerine yazmalı.

3. **Name cut transfer akışını netleştir:**
   2 satır export yapılmış ama transfer'e geçilmemiş. Operatör akışı: export → RDWorks'e manuel yükle → "Transfer Edildi" işaretle. Bu adımın UI'da net gösterimi var mı? Kontrol et.

### Bu Hafta YAPILMAMASI GEREKEN (Lazer için)

- Browser Mode lazer entegrasyonu — kütüphane boşken değer yok, güvenlik riski ekler
- AI Glyph Engine aktive etme — master flag kapalı kalmalı, downstream kontrol yapılmadan açılmaz
- Internal Corel Engine kodu silme — güvenli silme için call graph analizi gerekli
- 167 SVG ref'i toplu DXF'e çevirme — büyük iş, şimdi değil
- RDWorks otomasyonu — güvenlik sınırları (auto_start_laser: false)

### Sağlıklı Bitirme İçin Kritik Olan

| Kriter | Açıklama | Bloke Eden mi? |
|---|---|---|
| **DXF kütüphane ≥ 20 isim** | En çok gelen Trendyol isimleri için DXF dosyaları | ✅ EVET — 2 ile üretim olmaz |
| **connected_script.ttf yerinde** | LASER_CUT için zorunlu font | ✅ EVET — yoksa tüm LASER_CUT bloke |
| **Mochary hash korunmalı** | Değiştirilmemeli | Pasif — zaten korunuyor |
| **umit.dxf düzeltilmeli** | Üretim boyutuna çekilmeli | 🟡 ORTA — sadece umit için sorun |
| **name_cut transfer akışı test** | 2 export var, transfer yok; akış doğrulanmalı | 🟡 ORTA — operatör netlik istiyor |

---

## Referans Dökümanlar

- `output/2026-05-28/project_discovery/04_dxf_library_status.md`
- `output/2026-05-28/project_discovery/07_queue_system.md`
- `output/2026-05-28/project_discovery/12_endpoints_inventory.md`
- `output/2026-05-28/project_discovery/13_menu_state_v2.md`
- `output/2026-05-28/project_discovery/14_unknown_unknowns.md`
- `output/2026-05-28/browser_mode/ARCHITECTURE_ANALYSIS.md` (Browser Mode karar gerekçesi)
- `src/laser_service.py` (satır 1-120 okundu)
