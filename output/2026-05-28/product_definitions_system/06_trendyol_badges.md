# 06 — Trendyol SKU Rozetleri + Hızlı Tanımla

## Hedef

Trendyol siparişleri sayfasında her sipariş kartının üst satırına (meta-badge row), ürün tanımı durumunu gösteren renkli rozet:

- 🟢 **Tanımlı** — Bu siparişin barcode/SKU/stock_code ürün tanım veritabanında var
- 🟡 **Eksik** — SKU var ama tanım yok → tıklanınca Ürün Tanımları sayfasına SKU önceden doldurulmuş haliyle yönlendirir
- 🔴 **Bilinmiyor** — Sipariş satırında hiçbir SKU/barcode bulunamadı

## Implementation

### Frontend cache: `productDefinitionsSkuSet`

Global Set. Bridge'den `productDefinitionsList` çağrısı dönerken `refreshProductDefinitionsSkuSet()`:
- Aktif (status="active") ürünlerin sku + trendyol_sku alanları
- Bu set Trendyol render sırasında hızlı O(1) lookup için kullanılır

Boot anında `initBridge` callback'inde otomatik `loadProductDefinitions()` çağrılır — Trendyol sayfası açıldığında rozet'in hazır olması için.

### `productDefinitionForOrder(row)`

Trendyol order row'a bakıp adaylar listesi (barcode, merchant_sku, stock_code, trendyol_sku, sku) sırasıyla cache'te aranır. İlk match → "defined". Hiçbiri yoksa → "unknown". Tüm adaylar var ama cache'te yok → "missing".

### `trendyolProductBadge(row)`

`<span class="trendyol-product-badge {defined|missing|unknown}">🟢/🟡/🔴 Tanımlı/Eksik/Bilinmiyor</span>`

**Missing rozeti**: `onclick="openProductEditorForSku('TRY-12345', '10 kişilik söz çikolatası')"` — operatör tek tıkla ürün düzenleme ekranına gider, SKU + ürün adı pre-filled.

### Trendyol render entegrasyonu

`trendyolBadges()` fonksiyonunda meta-badge row'a ek olarak:

```js
return `
  <div class="trendyol-badge-stack">
    <div class="trendyol-badge-row meta">
      ${meta.map(item => trendyolBadge(item.label, item.tone)).join("")}
      ${trendyolProductBadge(row)}     // <-- yeni
    </div>
    <div class="trendyol-badge-row risk">...</div>
  </div>
`;
```

## CSS

```css
.trendyol-product-badge { padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; margin-left: 6px; }
.trendyol-product-badge.defined { background: rgba(34, 197, 94, 0.15); color: #15803d; }
.trendyol-product-badge.missing { background: rgba(217, 119, 6, 0.15); color: #b45309; cursor: pointer; }
.trendyol-product-badge.unknown { background: rgba(220, 38, 38, 0.12); color: #b91c1c; }
```

## Hızlı Tanımla deep-link

`openProductEditorForSku(sku, productName)`:
1. `showSection("products")` — Ürün Tanımları sayfasına geç
2. Sayfa render olduktan sonra (80ms timeout) `openProductEditor("")` ile yeni-ürün modalı aç
3. SKU + ürün adını pre-fill (disabled=false → operatör değiştirebilir)
4. Operatör validation hataları gördükten sonra "Kaydet"

Bu akış zamanlama hassas; ileride bir state machine event'i kullanmak daha temiz olurdu. Şimdilik setTimeout yeterli.

## Re-render davranışı

`loadProductDefinitions()` çağrısı sonunda:
```js
if (activeView === "trendyolOrders") {
  updateTrendyolOrders(currentState.trendyol);
}
```

→ Operator yeni ürün tanımı kaydettiğinde, Trendyol sayfasına döndüğünde rozet anında güncel görünür.

## Test (manuel — UI gerektirir)

1. Trendyol siparişleri sayfasını aç
2. Bir siparişin SKU'sunun tanımı yok → 🟡 Eksik rozet
3. Rozete tıkla → Ürün Tanımları sayfası, SKU + ürün adı pre-filled
4. Doldur + Kaydet
5. Trendyol siparişleri sayfasına geri dön → aynı sipariş artık 🟢 Tanımlı

## CLAUDE.md uyumu

- Rozet salt görsel + deep-link; otomatik kaydetme yok
- Hızlı Tanımla deep-link operatöre veriyi sunar, kaydetmez (operatör onayı)
- SKU set cache memory-only; her boot'ta `productDefinitionsList` ile tazelenir
- Rozet render'ı Trendyol siparişlerinin mevcut akışına hiç dokunmaz — yalnız `meta-badge` satırına bir ek span ekler
