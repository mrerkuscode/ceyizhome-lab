# Ürün Tanım Sistemi — Özet Raporu

**Tarih:** 2026-05-28
**Süre:** ~65 dakika (6 adım)
**Mochary hash:** korundu (dokunulmadı)
**167 SVG referans:** korundu
**operator-approved Trendyol satır:** korundu, `_is_verified_ready=True`
**DXF kütüphane sistemi:** etkilenmedi (önceki sprint korundu)

## v2.0 Bölüm 5 vizyonu → kod

Trendyol siparişi geldiğinde sistem operatöre sormadan bilmeli: kaç isim, hangi boyut grubu, kaç etiket, hangi model, üretimde adet artar mı? Bu sprintte sistemin omurgası kuruldu — Leyla Excel ile veya UI'da tek tek tanım girip kütüphane oluşturuyor; Trendyol sayfasında her sipariş için renkli rozet "Tanımlı / Eksik / Bilinmiyor" gözüküyor.

## Tablo — 6 adım sonucu

| Adım | İş | Durum | Süre | Detay |
|---|---|---|---|---|
| 1 | DB şema + ASCII normalizasyon | ✅ | 5 dk | `01_database_schema.md` |
| 2 | Backend API + 9 bridge slot | ✅ | 15 dk | `02_backend_api.md` |
| 3 | UI: menü + liste + edit panel + Excel modal | ✅ | 20 dk | `03_ui_implementation.md` |
| 4 | DXF library auto size_group + lookup preview | ✅ | 5 dk | `05_dxf_integration.md` |
| 5 | Trendyol SKU rozetleri + Hızlı Tanımla deep-link | ✅ | 10 dk | `06_trendyol_badges.md` |
| 6 | Test (6 senaryo) + 8 rapor | ✅ | 10 dk | `07_test_results.md` |

## Yeni / değiştirilen dosyalar

**Yeni:**
- `src/webui_backend/product_definitions_api.py` (~480 satır, CRUD + validation + Excel + DXF resolve)
- `data/product_definitions.json` (kütüphane index, boş başlangıç)
- `data/product_definitions_schema.json` (JSON Schema Draft 2020-12)
- `data/product_definitions_audit_log.jsonl` (her CRUD operasyonu)

**Değiştirilen:**
- `src/webui_backend/bridge.py` — 9 yeni slot (list/get/search/save/archive/restore/importExcel/resolveSizeGroup/incrementUsage)
- `src/webui/index.html` — Sol menüye "Ürün Tanımları"; yeni `<section id="products">`; Editor + Excel modalları
- `src/webui/app.js` — Tüm Product UI fonksiyonları + Trendyol rozet entegrasyonu + boot-time cache warm
- `src/webui/styles.css` — Products + modal + trendyol-product-badge CSS

**Backup'lar:** `output/2026-05-28/product_definitions_system/backups/`
- `bridge.py.bak`
- `index.html.bak`
- `app.js.bak`
- `styles.css.bak`

## Bridge slot'ları (9)

```
productDefinitionsList(includeArchived)        → liste + özet
productDefinitionGet(sku)                       → tek + size_group_resolution
productDefinitionsSearch(query)                 → arama
productDefinitionSave(payload_json)             → upsert + validate
productDefinitionArchive(sku)                   → soft delete
productDefinitionRestore(sku)                   → aktif et
productDefinitionsImportExcel(path, dry_run)    → Excel toplu yükle
productDefinitionResolveSizeGroup(payload_json) → auto size_group + DXF lookup
productDefinitionIncrementUsage(sku)            → kullanım sayacı
```

## Test sonucu (regression suite)

```
SCENARIO 1: Manual create               → PASS
SCENARIO 2: Excel bulk import           → 5 added, 2 validation errors (boş SKU, eksik model) — PASS
SCENARIO 3: Edit existing (TRY-001)     → PASS (created=False)
SCENARIO 4: Archive soft delete         → status=archived, satır silinmedi PASS
SCENARIO 5: Search                      → "kisilik" 2 hit, "TRY-00" 5 hit, "PREMIUM" 1 hit — PASS
SCENARIO 6: DXF library integration     → auto size_group 70/80/100x40 doğru; Umit FOUND, X-Unknown NOT FOUND — PASS

SAHTE BAŞARI KONTROLÜ:
  Invalid save → VALIDATION_ERROR (3 errors)
  - Ürün adı boş olamaz
  - Etiket aktif ise model seçilmeli
  - Şema hatası (product_name): '' should be non-empty
  → DOĞRU: sahte success YOK; "Kaydedildi" yalnızca gerçekten kaydedildiğinde döner

AUDIT LOG: 12 entry, son entry archive TRY-002

REGRESSION:
  corel ref library: 167 entries (korundu)
  DXF library scan: 2 entries (korundu)
  Trendyol approved rows: 1 (korundu)
```

## Validation kuralları (sahte başarı yok)

- SKU boş olamaz
- Ürün adı boş olamaz
- name_config.type ∈ {single, couple, none}
- type=none → count=0 zorunlu
- type ∈ {single, couple} → count ≥ 1
- label_config.enabled=True → model zorunlu, default_count zorunlu
- min_count ≤ default_count ≤ max_count (varsa)
- jsonschema Draft 2020-12 validator (data/product_definitions_schema.json)

## Sahte başarı kontrolleri

| Kontrol | Durum |
|---|---|
| "Kaydedildi" mesajı yalnızca yazma sonrası | ✅ (validation hata varsa VALIDATION_ERROR döner, dosya yazılmaz) |
| Audit log her CRUD'a yazılır | ✅ (12 entry test sonrası) |
| Soft delete (gerçek silme yok) | ✅ (`metadata.status="archived"` set edilir, satır kalır) |
| Excel dry-run + actual ayrımı | ✅ (dry_run=True yazma yapmaz, preview döner) |
| Frontend "Yükle" sonrası gerçek backend yanıtı | ✅ (added/updated/errors sayıları gerçek) |

## DXF library entegrasyonu

- Ürün düzenleme ekranında "Test ismi" alanı → DXF kütüphanede aranır
- Bulunduysa yeşil ✓ + "kütüphane boyut grubu" gösterilir
- Yoksa kırmızı uyarı: "Leyla bu ismi çizmeli"
- Auto size_group: harf sayısına göre 70/80/100x40 hesaplanır (5/9/10+ kuralı)
- Operatör manuel override yapabilir (70x40 / 80x40 / 100x40 dropdown)

## Trendyol rozet entegrasyonu

Her Trendyol sipariş kartına ürün-tanım rozeti eklendi:
- 🟢 **Tanımlı** — barcode/SKU/stock_code ürün tanım veritabanında var
- 🟡 **Eksik** — SKU var ama tanım yok; rozete tıklayınca Ürün Tanımları sayfasına SKU önceden doldurulmuş şekilde yönlendirir
- 🔴 **Bilinmiyor** — sipariş satırında SKU/barcode boş

Boot anında bir kez `loadProductDefinitions()` çağrılır → cache warm → Trendyol sayfası açılınca rozetler hazır.

## CLAUDE.md uyumu

| Garanti | Korundu mu |
|---|---|
| Operatör onayı zorunlu | ✅ — bu modül lazer/yazdırma tetiklemez, sadece veri tanımı |
| Direct print kapalı | ✅ — etkilenmedi |
| Lazer auto-start kapalı | ✅ — etkilenmedi |
| Sahte success yok | ✅ — validation hatasında VALIDATION_ERROR, "kaydedildi" sahte denmiyor |
| 167 SVG ref korundu | ✅ — corel_name_reference_library.json dokunulmadı |
| Mochary hash sabit | ✅ — font dosyası dokunulmadı |
| operator-approved Trendyol satır | ✅ — Ayşe & Mehmet hâlâ `_is_verified_ready=True` |
| DXF library sistemi korundu | ✅ — scan/lookup/watcher hepsi çalışıyor |
| Eski algoritma default OFF | ✅ — etkilenmedi |
| Geri dönülemez silme yok | ✅ — sadece soft delete (archive) |

## Sırada

Bu sprint kapsamı dışındaki işler (sonraki Leyla prompt'una):

1. **Eksik Tanımlar listesi sayfası** — Trendyol'dan gelen ama tanımı olmayan SKU'ların bulk listesi + tek tık tanımlama
2. **AI parser entegrasyonu** — ChatGPT/OpenAI ile ürün adından otomatik tanım önerisi (Leyla onayıyla)
3. **Üretimde adet artır/azalt** — Üretim ekranında her sipariş için min_count/max_count UI'ı
4. **Ürün tanımı → sipariş özet entegrasyonu** — siparişler önizleme paneline ürün tanımındaki notlar bağlanması
5. **Bulk Excel export** — mevcut tanımları XLSX olarak indirme

## Detay raporlar

- `01_database_schema.md`
- `02_backend_api.md`
- `03_ui_implementation.md`
- `04_excel_import.md`
- `05_dxf_integration.md`
- `06_trendyol_badges.md`
- `07_test_results.md`
- `proofs/test_products.xlsx` (test verisi)
- `proofs/regression_test.py` (her zaman tekrar çalıştırılabilir)
