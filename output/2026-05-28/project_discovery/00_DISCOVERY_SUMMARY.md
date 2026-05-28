# 00 — Discovery Summary (Mimar İçin Tek Sayfa)

**Tarih:** 2026-05-28
**Yöntem:** Salt okuma. Kod değiştirilmedi, butona basılmadı, veri yazılmadı.
**Kanıt politikası:** her iddia → dosya:satır veya gerçek veri.

## TL;DR (3 paragraf)

**Çekirdek çalışıyor.** 185 bridge slot aktif. 522 Trendyol soru/mesaj kaydı son sync 2026-05-19'da çekildi (214 sipariş, 10 unique barcode, 43 unique product_name). 249 üretim history kaydı 2026-05-07'den 2026-05-23'e kadar. Operator-approved Trendyol satır (Ayşe & Mehmet) `_is_verified_ready=True` korunmuş. CLAUDE.md güvenlik gate'leri (`auto_print_enabled=false`, `allow_direct_print=false`, `auto_start_laser=false`) `config/settings.yaml`'de doğru. 40 backup, 167 SVG referans, Mochary font hash hepsi yerinde.

**İki paralel ürün sistemi var.** Eski: `data/trendyol_product_mappings.json` (36 satır, barcode→model/production_type eşleştirme — Trendyol senkronu için zorunlu). Yeni: `data/product_definitions.json` (0 satır — bu sprintte kuruldu, kullanıma açık ama Leyla henüz tanım girmedi). **Çakışma yok**, görevleri farklı: eski "bu barkod hangi model" der, yeni "bu ürün üretiminde kaç isim, hangi boyut, kaç etiket" der. Bridge ikisini de servisliyor: 5 mapping slot + 9 product definition slot. DXF library (2 entry) auto size_group'a bağlı, `product_definitions.test_name` ile lookup çalışıyor.

**Mevcut sahte success cebi temizlendi ama bazı eski örüntüler kaldı.** Quick Wins'in 14/14'ü hâlâ yerinde (API Key password, credential backup exclusion, `_initial_verification_status` bypass kapalı, dashboard hardcoded statüleri dinamik, Kaynağa Dön disabled, vb.). Yeni tarama 4 nokta gösterdi: app.js'de hâlâ `sentToProduction:true` + `userApproved:true` literal'leri (Faz1 #6), label_api'de `"HAZIR"` hardcoded default, app.js'de "Doğrulandı" rozeti string'i (SYS-2), Etiket Studio preflight bridge-yok-OK pattern (Faz1 #5). Bunlar Quick Wins listesinde "kalan iş" olarak duruyordu, bilinen ödevler. AI Designer misleading isimlendirme 2 dosyada kaldı (1 occurrence each).

## Renkler (10 bölüm)

| Bölüm | Durum | Detay |
|---|---|---|
| A — Trendyol Reality | 🟢 ÇALIŞIYOR | 522 soru, 332 mapping_suggestion, 102 AI cache entry, last sync 2026-05-19. Credential maskeli backend, frontend type=password ✅ |
| B — Eski Ürün Eşleştirme | 🟢 ÇALIŞIYOR | 36 product mapping (barcode→model). Trendyol için zorunlu, korunacak. |
| C — Yeni Ürün Tanım Sistemi | 🟢 KURULDU 🟡 BOŞ | 0 aktif tanım. Sistem hazır, Leyla manuel veya Excel ile doldurmalı. |
| D — DXF Kütüphane | 🟢 ÇALIŞIYOR | 2 entry (ayse, umit), watcher aktif edilebilir, override hook bağlı. |
| E — Label Studio | 🟢 ÇALIŞIYOR | Mevcut akış sağlam, 167 SVG ref korunuyor. |
| F — Bulk Production | 🟢 ÇALIŞIYOR | bulk_label_api 4 slot. Excel→gallery→queue akışı çalışıyor. |
| G — Queue System | 🟢 ÇALIŞIYOR | print_queue=0 (boş), name_cut_queue=2 satır. CLAUDE.md güvenlik koruması aktif. |
| H — History / Outputs | 🟢 ÇALIŞIYOR | 249 üretim history, 28 günlük output klasörü, 13 audit event. |
| I — Backup / Veri Bakımı | 🟢 ÇALIŞIYOR | 40 backup, credential ifşası kapatıldı (Quick Wins sprint). |
| J — Settings / Config | 🟢 ÇALIŞIYOR | CLAUDE.md gate'leri config'te doğru. |

## En kritik bulgu

**Hiçbir kritik regresyon yok.** Quick Wins + DXF + Product Definitions sprintleri sonrası sistem tutarlı: 14 fix yerinde, 167 SVG ref + Mochary hash + operator-approved satır + Trendyol akışı korunmuş.

**Tek dikkat çekici nokta:** v2.0 Bölüm 5 (Ürün Tanım Sistemi) **infrastrüktürel olarak hazır ama veri girilmemiş**. Leyla başlamadan önce ihtiyaç var. Bu beklenen durum (sprint hedefi sistemi kurmaktı), ama mimar için: "Trendyol siparişi geldiğinde sistemin sorduğu soruları cevaplayacak veri tabanı **boş**". Test/Production'a çıkmadan önce minimum 20-50 SKU tanımlanmalı.

## Önerilen ilk adım (Leyla için)

1. **Hızlı tanım sprinti**: Trendyol'da geçen 7 gündeki 10 unique barcode → 10 ürün tanımı oluştur (UI veya Excel)
2. Trendyol siparişleri sayfasında her sipariş için 🟢 Tanımlı rozet gör
3. İlk DXF kütüphane lookup test: bir sipariş için "Mücahit" gelirse "Çiz Bekliyor" gözüksün → Leyla DXF çizip 70x40'a atsın → next reload → 🟢

Sonraki sprint adayları:
- Eksik Tanımlar sayfası (bu sprintte UI eklenmedi, sadece Trendyol satırında rozet var)
- AI parser (ChatGPT) ile ürün adından otomatik tanım önerisi
- Üretimde adet artır/azalt UI

## Veri hacmi tablosu (gerçek, 2026-05-28 itibarıyla)

| Dosya | Satır / Boyut | Son güncel |
|---|---|---|
| `data/trendyol_questions_context.json` | 522 satır / 903 KB | 2026-05-19 23:00 |
| `data/trendyol_product_mappings.json` | 36 satır / 32 KB | 2026-05-19 23:04 |
| `data/trendyol_mapping_suggestions.json` | 332 satır / 342 KB | n/a |
| `data/trendyol_production_suggestions.json` | 3 satır / 6 KB | n/a |
| `data/trendyol_ai_extraction_cache.json` | 102 entry / 184 KB | n/a |
| `data/trendyol_settings.json` | 18 alan / 916 B | 2026-05-19 |
| `data/production_history.json` | 249 satır / 185 KB | 2026-05-23 |
| `data/customer_orders.json` | 10 satır / 7 KB | n/a |
| `data/print_queue.json` | 0 satır / 2 B | boş |
| `data/name_cut_queue.json` | 2 satır / 2 KB | n/a |
| `data/name_cut_transfer_history.json` | 0 / 2 B | boş |
| `data/name_cut_export_history.json` | 2 / 3 KB | n/a |
| `data/production_audit_log.json` | 13 event / 25 KB | n/a |
| `data/dxf_library.json` | 2 entry / 2 KB | 2026-05-28 |
| `data/product_definitions.json` | 0 entry / 109 B | 2026-05-28 |
| `data/product_definitions_audit_log.jsonl` | 0 entry / 1.5 KB (post-cleanup) | 2026-05-28 |
| `assets/references/corel_name_reference_library.json` | 167 ref / büyük | (invariant) |
| `assets/dxf_library/70x40/` | 3 dosya | 2026-05-28 |
| `backups/` | 40 yedek | (rolling) |

## Endpoint envanteri (özet)

**185 bridge slot** (`@Slot` decorator) — gruplandırılmış sayı:

| Grup | Slot |
|---|---|
| Misc (varied) | 30 |
| Label model/template | 26 |
| File system / open | 18 |
| Corel Reference (legacy SVG) | 17 |
| Production audit / history / safety | ~10 |
| Trendyol | ~10 |
| Bulk production | ~5 |
| Print queue | ~5 |
| Name cut | ~5 |
| Printer profile | 5 |
| Backup / restore | 6 |
| Customer order | 4 |
| **DXF Library (yeni)** | **8** |
| **Product Definitions (yeni v2.0)** | **9** |
| Settings / state | 4 |
| Diğer kategoriler | … |

Detay: `12_endpoints_inventory.md` + `_slot_inventory.json` + `_slot_groups.json`.

## Detay raporlar

- `01_trendyol_reality.md` ⭐
- `02_product_matching_old.md`
- `03_product_definitions_new.md`
- `04_dxf_library_status.md`
- `05_label_studio.md`
- `06_bulk_production.md`
- `07_queue_system.md`
- `08_history_outputs.md`
- `09_backup_data_maintenance.md`
- `10_settings_config.md`
- `11_data_samples/` — 12 gerçek veri sample (credentials maskeli)
- `12_endpoints_inventory.md`
- `13_menu_state_v2.md`
- `14_unknown_unknowns.md`

## Bilinmeyen Bilinmezler (özet)

- Trendyol live test ortamı çağrı sayısı, rate-limit durumu (sadece son sync zaman damgası bilinir)
- Mevcut müşteri SKU stoğu büyüklüğü (10 unique barcode görünüyor ama tam katalog ne büyüklükte?)
- AI Designer kalıntıları (2 occurrence) tek hatlık silinebilir mi — emin değiliz, downstream call var mı kontrol edilmedi
- Bulk preview modal'ı (`bulkPreviewModalStage`) gerçek bir akış mı yoksa kalıntı mı

## Risk / Uyarı (özet)

- 🟡 **Ürün tanım veri tabanı boş**: production'a çıkmadan önce mutlaka doldurulmalı, yoksa Trendyol siparişleri 🟡 Eksik rozet ile birikir
- 🟡 **Bilinen sahte success kalıntıları**: `sentToProduction:true` + `userApproved:true` literal'leri (Faz1 #6), `"HAZIR"` default (SYS-2), "Doğrulandı" badge (SYS-2 frontend), preflight bridge-yok OK (Faz1 #5) — bunlar Quick Wins sprintinde "kalan iş" olarak bilinçli ertelendi
- 🟢 **DXF library test ölçeği**: umit.dxf 10.9×7.2mm (production 70×40 olmalı). Leyla canlı dosyaları doğru ölçekte gelecek; sistem zaten warning veriyor
- 🟢 **Watcher Qt thread bağlı değil**: watchdog ayrı thread, UI otomatik refresh olmuyor; manuel Tara çözüyor

## Mimar için hazır

Bu rapor mimari plan için baseline'dır. Sonraki adım: stratejik kararlar (AI parser entegrasyonu önceliği, eksik tanımlar bulk sayfası, üretimde adet UI, vb.) — şu an "her şey çalışıyor, ürün tanım veri tabanı boş, eskimiş sahte success kalıntıları biliniyor" durumundayız.
