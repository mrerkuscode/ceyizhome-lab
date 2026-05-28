# Mochary Font Render ve OpenType Raporu

Tarih: 2026-05-20

## 1. Mevcut Render Motoru Analizi

### Web / Studio Canli Preview

- Aktif arayuz `src/webui/index.html`, `src/webui/app.js`, `src/webui/styles.css` uzerinden calisiyor.
- Etiket Studio canli preview alanlari DOM text olarak render ediliyor.
- Yazilar `.field-box.text-layer` benzeri HTML elementleriyle konumlandiriliyor.
- Bu hatta canvas `fillText` ana render yolu degil; web preview DOM/CSS tabanli.

### Manuel Etiket PDF/PNG Render

- `src/label_designer/renderer.py` QPainter/QFont ile metin ciziyor.
- Font ailesi ve font yolu `_make_font` ile Qt font sistemine yukleniyor.
- Bu cikti hattinda metin path'e cevrilmiyor; QPainter text ciziyor.
- OpenType davranisi Qt font engine tarafina bagli. CSS OpenType ayarlari bu hatta dogrudan uygulanmaz.

### Lazer / Isim Kesim Export

- `src/webui_backend/combined_production_api.py` fontTools kullanarak yazi contour/path uretiyor.
- `_raw_text_contours`, `_outline_contours_for_item`, `_svg_document`, `_dxf_document` fonksiyonlari text-to-outline hattini olusturuyor.
- Manifestlerde `OUTLINED_PATHS_WITH_FONTTOOLS` durumu kullaniliyor.
- Mochary/script icin manuel capital connection tracking ve Turkish diacritic bridge mantigi zaten mevcut.

## 2. OpenType Feature Duzeltmeleri

Preview text alanlarina merkezi CSS standardi eklendi:

```css
font-kerning: normal;
text-rendering: optimizeLegibility;
font-feature-settings:
  "liga" 1,
  "clig" 1,
  "calt" 1,
  "kern" 1,
  "salt" 1;
```

Bu ayarlar su alanlara uygulandi:

- `.script-opentype-text`
- `.field-box.text-layer`
- `.name-cut-script b`
- `.laser-layout-stage span`
- `.lab-selected-text`
- `.rdworks-canvas span`

## 3. Font Test Lab

Yeni ekran eklendi:

- Sol menu: `Font Test Lab`
- Section: `fontTestLab`

Ekran ozellikleri:

- Font secimi
- Metin girisi
- Ligatures ac/kapat
- Contextual alternates ac/kapat
- Stylistic alternates ac/kapat
- Kerning ac/kapat
- Baglanti duzeltme modu
- Noktalama duzeltme modu
- Harf araligi
- Kelime araligi
- Baseline ayari
- Canli preview
- Ham OpenType preview
- Fix katmani preview
- Test cumleleri
- SVG preview export
- PNG preview export
- Lazer outline/path durumu bilgilendirmesi

Test cumleleri:

- Ceyizhome
- Ask ile soz verdik
- Soz & Nisan
- Mucahit
- Seyma
- Ozel Tasarim
- ₺250
- Ayse & Mehmet
- Zeynep'in Nisani

Not: Arayuzde Turkce karakterli orijinal test cumleleri kullanildi.

## 4. Capital Connection Fix

Runtime ve referans TS dosyasi eklendi:

- `src/webui/components/text/capitalConnectionFixMap.ts`

Uygulanan mantik:

- Ham metin degistirilmez.
- Sadece preview ve export preview katmaninda sonraki kucuk harf icin offset/baseline ayari uygulanir.
- A, B, C, C cedilla, S, S cedilla, T, Z gibi buyuk harf gecisleri icin konfigurasyon hazirlandi.

## 5. Noktalama Duzeltme

Runtime ve referans TS dosyasi eklendi:

- `src/webui/components/text/punctuationFixMap.ts`

Kontrol edilen karakterler:

`. , : ; ! ? - _ / & + @ ₺ ' " ( )`

Her karakter icin:

- onceki spacing
- sonraki spacing
- baseline adjust
- fallback adi

tanimi hazirlandi. Bu tanimlar Font Test Lab fix preview katmaninda kullaniliyor.

## 6. Script Font Preview Component

Istenen referans component dosyasi eklendi:

- `src/webui/components/text/ScriptFontPreview.tsx`

Proje su an React/Next TypeScript build hattina sahip degil; aktif UI vanilla web uygulamasi. Bu nedenle TSX dosyasi gelecekte React'e tasima icin referans component olarak eklendi, runtime uygulamasi ise `index.html + app.js + styles.css` icinde calisiyor.

## 7. Export Durumu

### SVG / PNG Preview

Font Test Lab ekraninda SVG ve PNG preview export eklendi.

- SVG preview text olarak export edilir.
- PNG preview SVG render uzerinden uretilir.
- Bu ekran lazer/path export oldugunu iddia etmez.

### Lazer Outline / Path

Gercek outline/path export mevcut Isim Kesim hattindadir:

- fontTools contour cikarimi
- SVG path
- DXF polyline/path
- PDF preview
- RDWorks uyumlu DXF oncelikli paket

Bu nedenle path/outline icin dogru production yolu Font Test Lab degil, Isim Kesim moduludur.

## 8. Kalan Teknik Sinirlar

- Web CSS OpenType ozellikleri browser font engine'e baglidir. Font dosyasinda ilgili GSUB/GPOS tablolar yoksa CSS ayari tek basina yeni alternates yaratamaz.
- QPainter PDF/PNG hattinda CSS feature settings uygulanmaz; Qt font engine davranisi kullanilir.
- fontTools outline hattinda su an tam OpenType shaping motoru degil, glyph contour + manuel spacing/connection logic kullaniliyor. Script fontlarda en guvenli lazer cikti icin bu hattin ileride HarfBuzz/uharfbuzz ile GSUB/GPOS shaping destekli hale getirilmesi onerilir.

## 9. Sonuc

- Sorunun bir kismi fontun kendi OpenType tablolarina, bir kismi da programdaki preview/export motorlarinin farkli olmasina bagli.
- Web preview alanlarinda OpenType feature ayarlari artik merkezi olarak aktif.
- Buyuk harf baglanti ve noktalama icin configurable fix map eklendi.
- Font Test Lab ile problemli karakterler operator tarafindan gozle test edilebilir.
- Lazer path export halihazirda Isim Kesim fontTools hattinda bulunur; Font Test Lab sadece preview export verir ve sahte outline basarisi gostermez.

## 10. Dogrulama

- `node --check src\webui\app.js`: PASSED
- `.venv\Scripts\python.exe -m py_compile scripts\verify_project_responsive_layout.py src\webui_backend\combined_production_api.py src\label_designer\renderer.py`: PASSED
- `.venv\Scripts\python.exe scripts\verify_project_responsive_layout.py`: PASSED
- `npm run test`: PASSED

Screenshot kanitlari:

- `output\2026-05-20\responsive_layout\fontTestLab_1920.png`
- `output\2026-05-20\responsive_layout\fontTestLab_1366.png`
