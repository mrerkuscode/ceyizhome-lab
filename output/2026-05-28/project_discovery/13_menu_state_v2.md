# 13 — Menü Durumu vs MD v2.0 Hedef

## Mevcut sidebar (index.html, 2026-05-28)

```
ÜRETIM:
- Ana Sayfa (home)
- Design Lab (designLab)
- Font Test Lab (fontTestLab)
- Etiket Modelleri (labelModels)
- Etiket Studio (label)
- Manuel Etiket (manualLabel)
- Toplu Üretim Studio (bulkLabel) — "Yeni" badge
- İsim Kesim Studio (nameCutStudio)
- Yazdırma Sırası (printQueue)
- Etiket Çıktıları (labelOutputs)
- Üretim Geçmişi (productionAudit)

TRENDYOL:
- Siparişler (trendyolOrders, tab=orders)
- Kontrol Kuyruğu (tab=worklist)
- Ürün Eşleştirme (tab=mapping)
- Kanıt Eşleştirme (tab=questions)
- Aktarım Geçmişi (tab=history)

VERİ:
- Genel Ayarlar (settings, general)
- Kullanıcılar (users)
- Roller (roles)
- Trendyol API (trendyol-api)
- Kargo Firmaları (shipping)
- Diğer Ayarlar (other-integrations)
- Yazıcı Profilleri (printer-profiles)
- Ürün Tanımları (products) ★ YENİ (v2.0)
- Veri Bakımı (data-maintenance) [DXF Library kartı içinde]

SİSTEM:
- Raporlar (reports)
- Loglar / Hata Kayıtları (stub)
- Çıkış Yap (quitApplication)

TEKNİK (hidden details):
- Native AI/CDR Deneme (nativeTools)
- Lazer (laser)
- Çıktı Klasörleri (folders)
```

**21 ana menü + 5 alt Trendyol + 6 alt Ayarlar + 3 teknik = ~35 navigasyon noktası.**

## Section'lar (HTML)

24 ana `<section id>` var (3133+ satır HTML):

| Section | Aktif | Notlar |
|---|---|---|
| home | ✓ | Dashboard (Quick Wins'te dinamik status'lara çevrildi) |
| fontTestLab | ✓ | Font Test Lab |
| designLab | ✓ (Phase 2 audit: mock-heavy alt-ekran) |
| labelModels | ✓ | Etiket Modelleri |
| nameCutStudio | ✓ | İsim Kesim |
| bulkLabel | ✓ | Toplu Üretim |
| label | ✓ | Etiket Studio |
| labelOutputs | ✓ | Etiket Çıktıları |
| trendyolOrders | ✓ | Trendyol (5 tab) |
| customerOrders | ? | (Sidebar'da yok ama section mevcut — kalıntı?) |
| printQueue | ✓ | Yazdırma Sırası |
| productionAudit | ✓ | Üretim Geçmişi |
| **products** | ✓ | **★ YENİ (v2.0 Bölüm 5)** |
| reports | ✓ | Raporlar |
| settings | ✓ | 6 alt sayfa + 3 kart (Veri Bakımı, DXF Kütüphane, Güvenlik) |
| nativeTools | ✓ | Teknik |
| laser | ✓ | Teknik |
| folders | ✓ | Teknik |
| bulkPreviewModalStage | ? | Modal stage (kalıntı?) |
| corelDock* (4 alt panel) | label içinde |

## MD v2.0 Hedef ile kıyaslama

(Sprint görevinde sunulan v2.0 Bölüm 5 spec'inden çıkarımla):

| MD v2.0 hedef | Mevcut | Durum |
|---|---|---|
| Ürün Tanım Sistemi menüsü | "Ürün Tanımları" | ✅ eklendi |
| Ürün listesi + Yeni Ürün modal | products page | ✅ |
| Excel toplu yükle | "Excel Yükle" modal | ✅ |
| İsim ayarları (tek/çift/yok + adet + boyut) | radio + select | ✅ |
| Etiket ayarları (model + adet + min/max + adjustable) | fieldset | ✅ |
| DXF kütüphane lookup test ismi preview | resolveProductSizeGroupPreview | ✅ |
| Trendyol siparişlerinde 🟢/🟡/🔴 rozet | trendyolProductBadge | ✅ |
| Hızlı Tanımla deep-link | openProductEditorForSku | ✅ |
| Eksik Tanımlar bulk listesi | YOK | ❌ (sonraki sprint) |
| AI parser entegrasyonu | YOK | ❌ (sonraki sprint) |
| Üretimde adet artır/azalt UI | YOK | ❌ (sonraki sprint, sadece veri var) |

**v2.0 Bölüm 5 ana kapsamın %85'i tamam, %15 sonraki sprintler için.**

## Kalan v2.0 işleri (sprint öncelikleri)

1. **Eksik Tanımlar sayfası** — Trendyol'dan gelmiş ama tanımsız SKU'ların bulk listesi (operator UX iyileştirmesi)
2. **AI parser (ChatGPT)** — ürün adından otomatik tanım önerisi
3. **Üretim ekranında adet ± butonu** — `adjustable_in_production=True` olan SKU'lar için
4. **Ürün tanım → sipariş özet entegrasyonu** — `production_notes` Trendyol sipariş kartında preview
5. **Bulk Excel export** — mevcut tanımları XLSX olarak indir

## "Çöp" veya kalıntı muhtemel section'lar

- `customerOrders` — Sidebar'da link yok ama section var (kullanılıyor mu?)
- `bulkPreviewModalStage` — modal kalıntısı olabilir
- `corelDock*` (4 panel) — Etiket Studio'nun içinde, sağlam

## Yorum

Menü yapısı temiz ve kullanılabilir. 24 section çok ama her birinin işlevi var; "ölü" section sayısı 1-2 (`customerOrders` belirsiz). Kullanıcı yolculuğu kabaca:

1. Ana Sayfa (durum özet) → 2. Trendyol Siparişleri (gelen) → 3. Ürün Tanımları (eksikleri tanımla) → 4. İsim Kesim / Etiket Studio (üret) → 5. Yazdırma Sırası (yazdır) → 6. Üretim Geçmişi (audit)

## Risk / Uyarı

- 🟢 Sidebar UX dengeli (4 grup: ÜRETIM / TRENDYOL / VERİ / SİSTEM)
- 🟡 customerOrders section'ı belirsiz — kullanılmıyorsa kaldırılabilir
- 🟢 Quick Wins'te eklenen 4 yeni section/kart (DXF Kütüphane, AI Çıkarım Ayarları collapsible, Dashboard dinamik status, Ürün Tanımları) hepsi cohesive
