# 03 — UI Uygulaması

## Yeni menü

`src/webui/index.html:60-61` aralığında "VERİ" navigasyon bölümüne eklendi:

```html
<button class="nav-btn" data-page="products" onclick="showSection('products')" title="Ürün Tanımları">
  <span class="nav-icon">◳</span><span class="nav-text">Ürün Tanımları</span>
</button>
```

Konum: "Yazıcı Profilleri" ile "Veri Bakımı" arasında (spec'te istenildiği gibi Veri Bakımı'nın üstünde).

## `<section id="products">` ana sayfa

3 ana parça:
1. **Toolbar:** + Yeni Ürün, Excel Yükle, Arama input, Arşiv dahil checkbox, Yenile
2. **Summary grid:** Toplam, Aktif, Arşivli, Etiketli, Çift İsim, Tek İsim, İsim Yok (per-stat tile)
3. **Tablo:** SKU, Ürün Adı, İsim, Etiket, Boyut, Durum (pill), Kullanım, İşlemler (Düzenle / Arşivle veya Aktif Et)

## Düzenleme modalı

```
┌─────────────────────────────────────────────┐
│ Yeni Ürün / Ürün Düzenle: TRY-12345         │
├─────────────────────────────────────────────┤
│ SKU: [_______]    (mevcut ürünse disabled)  │
│ Ürün Adı: [_____________________________]   │
│                                             │
│ ▣ İsim Ayarları                             │
│ (●) Tek isim  (○) Çift isim  (○) İsim yok   │
│ Adet: [1 ▼]   Boyut: [Otomatik ▼]           │
│ Format: [Tek dosya ▼]                       │
│ Test ismi: [Ayşe & Mehmet___]               │
│ ✓ DXF kütüphane: ayse_mehmet.dxf bulundu    │
│                                             │
│ ▣ Etiket Ayarları                           │
│ ☐ Etiket var                                │
│ Model: [soz_3]    Varsayılan: [10]          │
│ ☐ Üretimde adet artır/azalt                 │
│ Min: [5]  Max: [20]                         │
│                                             │
│ ▣ Üretim Notları                            │
│ [Notlar textarea]                           │
│ ✓ Müşteri özel istekleri kabul              │
│                                             │
│ [Hatalar buraya — validation_error listesi] │
├─────────────────────────────────────────────┤
│              [İptal]  [Kaydet]              │
└─────────────────────────────────────────────┘
```

Test ismi alanı `oninput="resolveProductSizeGroupPreview()"` → frontend hesaplanan size_group + DXF library durumunu canlı gösterir.

## Excel modalı

```
┌─────────────────────────────────────────────┐
│ Excel Toplu Yükle                            │
├─────────────────────────────────────────────┤
│ Beklenen kolonlar: SKU, ProductName, ...     │
│ Excel dosyası (.xlsx): [_____________]       │
│ [Önizle (Dry-Run)]  [Yükle]                  │
│ ----------------------------                 │
│ Önizleme tablosu (ilk 10 satır)              │
│ Hatalı satır listesi (varsa)                 │
└─────────────────────────────────────────────┘
```

## JavaScript fonksiyonları (app.js)

| Fonksiyon | Görev |
|---|---|
| `setProductsStatus(msg, tone)` | Üst durum çubuğu |
| `loadProductDefinitions()` | Bridge'den listeyi çek, SKU set güncelle, render |
| `renderProductList()` | DOM'a list + summary render |
| `refreshProductDefinitionsSkuSet()` | Trendyol rozet cache'i |
| `openProductEditor(sku?)` | Modal aç (yeni veya düzenleme); var olansa bridge.get çağrılır |
| `closeProductEditor()` | Modal kapat |
| `collectProductEditorPayload()` | Form → JSON |
| `saveProductDefinition()` | Bridge.save; hata varsa errors div'e basar |
| `archiveProductDefinition(sku)` | confirm + bridge.archive |
| `restoreProductDefinition(sku)` | bridge.restore |
| `resolveProductSizeGroupPreview()` | Canlı DXF lookup |
| `openProductExcelImport()` / `closeProductExcelImport()` | Excel modal |
| `runProductExcelImport(dryRun)` | Bridge.importExcel + sonuç render |
| `productDefinitionForOrder(row)` | Trendyol row → "defined/missing/unknown" |
| `trendyolProductBadge(row)` | Rozet HTML |
| `openProductEditorForSku(sku, productName)` | Trendyol rozetten deep-link |

State: `productState = { definitions, summary, editingSku }` + `productDefinitionsSkuSet`

## CSS (styles.css)

Yeni sınıflar:
- `.products-toolbar`, `.products-summary`, `.products-stat`, `.products-table`, `.products-empty`
- `.status-pill.active`, `.status-pill.archived`
- `.product-editor-modal` (overlay + center), `.product-editor-card` (kart), `.narrow` (Excel modalı)
- `.product-editor-section` (fieldset), `.product-editor-field` (grid)
- `.prod-edit-error` (kırmızı sol-çizgi)
- `.prod-edit-dxf-preview` + `.dxf-check.ok/.bad/.warn`
- `.product-excel-result`, `.prod-excel-summary`, `.prod-excel-errors`
- `.trendyol-product-badge.defined/.missing/.unknown` (Trendyol rozet renkleri)

## Frontend integrity testi

```
✓ Menu entry
✓ Products section
✓ Editor modal
✓ Excel modal
✓ loadProductDefinitions fn
✓ renderProductList fn
✓ openProductEditor fn
✓ saveProductDefinition fn
✓ archive fn
✓ Excel import fn
✓ resolveSizeGroup fn
✓ showSection products hook
✓ CSS products-toolbar
✓ CSS product-editor-modal
✓ CSS trendyol-product-badge
```

15/15 PASS.

## CLAUDE.md uyumu

- Modal'lar overlay + click-outside kapatılır ama veri kaybı kontrolü yok (bilinçli; sadece "İptal" net yol)
- Arşivle butonu `confirm()` ile onay alır
- Kaydet butonu validation hata varsa hata listesini gösterir, modal kapanmaz (operator hatasını düzeltebilir)
- Excel "Yükle" butonu önce dry-run önerilir; gerçek yükleme de net hata raporu döner
- Trendyol rozetinden "Hızlı Tanımla" deep-link operatöre formu önceden doldurur ama Kaydet manuel
