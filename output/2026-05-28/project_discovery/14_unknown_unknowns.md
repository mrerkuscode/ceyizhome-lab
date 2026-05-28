# 14 — Bilinmeyen Bilinmezler

Bu raporda kanıt seviyesi yetmediği veya zaman kısıtı nedeniyle salt-okuma ile çözülemeyen sorular listelenir. Mimar için "burayı daha derin kazmak gerekir" notu.

## Trendyol entegrasyonu

- **Rate limit / quota durumu:** Son sync 2026-05-19, 9+ gündür temas yok. Trendyol API rate limit'i kaç çağrı/dakika? Token expiry var mı?
- **Stage/test environment:** `stage=False` `environment=live`. Stage modu denenmiş mi (settings'te sadece flag var)?
- **Webhook desteği:** Mevcut akış polling-only mı yoksa Trendyol webhook desteği var mı? (Salt-okuma ile kod yolundan görülemedi)
- **Order line vs package:** `package_id, line_id` fieldları var ama 1 sipariş → N package → M line ilişkisi tam haritalanmadı

## Algoritma silinme adayları

- **AI Designer (`ai_assisted_corel_style_glyph_intelligence.py`):** 7 KB, 1 referans `combined_production_api.py`'de. `use_legacy_name_cut_algorithms=False` master flag tarafından gate'lenmiş. Tek hatlık silinebilir mi? Downstream call graph kontrol edilmedi.
- **Internal Corel-like vector engine (`internal_corel_like_vector_name_cut_engine.py`):** 8 KB, 170 satır. Aynı master flag ile devre dışı. Tamamen silinebilir mi?
- **Targeted weld + bridge + support_line + initial letter connection + letter flow bridge:** Hepsi `combined_production_api.py` içinde, ~3000 satır. Master flag OFF olunca çağrılmıyor ama kod duruyor. Refactor sprint'inde temizlenebilir.

## Eski Quick Wins kalıntıları (Faz1/SYS-)

- **SYS-2 `app.js` "Doğrulandı" hardcoded badge:** Re-scan'de string var. Audit 03_fake_success_locations.md'de listelenmiş, Quick Wins'te ertelendi.
- **SYS-2 `label_api.py` "HAZIR" default status:** Aynı şekilde re-scan HIT.
- **Faz1 #5 — Etiket Studio preflight bridge-yok OK callback (`app.js:10853-10855`):** Bridge bağlantısı yokken "preflight geçti" sahte mesajı. Quick Wins kalan iş.
- **Faz1 #6 — `sentToProduction:true, userApproved:true` literal'leri (`app.js:10930`):** Operatör onayı bypass kalıntısı. 4 literal app.js'de var.

Bu 4 kalıntı bilinen ödev; tek sprint'te çözülebilir.

## UI / UX bilinmezleri

- **`customerOrders` section'ı:** Sidebar'da link yok ama HTML'de section var. Ölü kod mu yoksa indirect erişimle mi açılıyor?
- **`bulkPreviewModalStage`:** Modal stage olarak görünüyor (`<section>` ama modal-like). Gerçek modal mı yoksa eski deneme?
- **Design Lab + Font Test Lab:** Phase 2 audit'te "mock-heavy alt-ekran" olarak işaretlenmişti — re-scan ile gerçek bağlantısı kontrol edilmedi.
- **Sidebar "Loglar / Hata Kayıtları" butonu:** `showSystemNotice('Loglar / Hata Kayıtları')` — Quick Wins'te `showSystemNotice` stub kaldı (yalnız reports'a yönlendirme), gerçek log paneli yok.

## Veri Hacmi / Performance

- **332 mapping suggestion'ın geçmiş hayatı:** Tümü `status=needs_review`. Bir tanesi onaylandığında ne olur? Suggestion list'ten çıkarılıyor mu? Cache'leniyor mu?
- **102 AI extraction cache'i ne kadar büyür:** 184 KB / 102 = ~1.8 KB/entry. 10000 entry olursa 18 MB. Auto-pruning var mı?
- **40 backup ve büyüyen disk:** Eski backup'lar otomatik temizleniyor mu? Manuel temizlik gerekli mi?
- **`production_history.json` 185 KB / 249 satır:** ~700 byte/satır. Lineer ölçeklenirse 10000 satırda 7 MB — yönetilebilir ama auto-rotate planı yok.

## Print queue + name cut queue boş

- Print queue **boş** (`[]`). Hiç production satırı yok mu yoksa cleared mi? Audit log boş olduğu için karar verilemiyor.
- Name cut transfer history **boş** ama export history 2 satır var. Export edildi ama transfer'e geçilmedi — operatör neden adımı atladı?

## Test edilemedi

- Bridge slot'ların gerçek çağrılması (QWebChannel olmadan harness'ta yapılamaz)
- UI rendering (Qt ortamı yok)
- Operator workflow end-to-end (1 sipariş → tanım → DXF → üretim)
- Watchdog uzun süreli stabilite (sadece 5sn'lik kısa test yapıldı)

## Risk surface (özet)

- 🟡 **Kalıntı sahte success kalıntıları** (4 nokta) — bilinen TODO, sonraki sprint
- 🟡 **Boş veri tabanları:** product_definitions (0 entry), print_queue (boş), trendyol_extraction_learning_examples (boş)
- 🟡 **Backup auto-pruning yok** — disk şişme riski
- 🟢 **CLAUDE.md gate'leri sağlam** (auto_print + direct print + lazer hepsi false)
- 🟢 **Operator-approved Trendyol satır korundu** (`_is_verified_ready=True`)
- 🟢 **167 SVG ref invariant'i korundu**
- 🟢 **Mochary hash dokunulmadı**

## Mimar için ek araştırma önerileri

1. **AI Designer + internal_corel_like_vector_name_cut_engine kullanım grafiği** — `grep -r "ai_assisted_corel_style_glyph_intelligence\|internal_corel_like_vector_name_cut_engine"` ile tüm referansları topla, master flag ile gerçekten gate edildiğini doğrula
2. **app.js modülerleştirme** — 21391 satır tek dosya, refactor planı önümüzdeki ay'da değer üretebilir
3. **Trendyol webhook + auto-sync** — manual sync 9+ gündür yok, otomatik schedule önerilebilir
4. **AI parser (ChatGPT) entegrasyonu** — v2.0 Bölüm 5 spec'inde "Sırada" işaretlendi; Leyla onayıyla başlanabilir
5. **Print queue + name cut queue test coverage** — boş olduğu için davranış bilinmiyor; canlı veri ile test gerekli
