# Interaction Testing Guide

Etiket Studio interaction testleri gerçek pointer, mouse ve keyboard davranışını doğrular. Handle veya border görünmesi tek başına başarı değildir.

## Drag Testi

Drag testi sadece handle veya border görünüyor diye geçmez.

Başarı için:

- `pointerdown` yapılır.
- `pointermove` yapılır.
- `pointerup` yapılır.
- Field `x/y` değeri değişir.
- DOM görsel pozisyonu değişir.
- `selectedField` kaybolmaz.
- Field sınır içinde kalır.
- PDF/PNG payload yeni `x/y` değerini taşır.

## Corner Resize Testi

Başarı için:

- Köşe handle seçilir.
- `pointerdown + pointermove + pointerup` yapılır.
- `width` değişir.
- `height` değişir.
- `font_size` değişir.
- Field sınır içinde kalır.
- PDF/PNG payload yeni geometry’yi taşır.

## Side Resize Testi

Başarı için:

- Sağ, sol, üst veya alt handle seçilir.
- Pointer move sonrası `width` veya `height` değişir.
- `font_size` agresif değişmez.
- Field sınır içinde kalır.

## Zoom Testi

Şu modlarda drag ve resize tekrar denenir:

- Ekrana Sığdır
- %100
- %150
- %200

Başarı:

- Mouse delta doğru hesaplanır.
- `imageRect`, `canvasRect` ve scale hesabı doğru çalışır.
- Zoom değişince interaction bozulmaz.

## Keyboard Testi

Başarı:

- Arrow: 0.1 mm hareket ettirir.
- Shift+Arrow: 1 mm hareket ettirir.
- Alt+Arrow: 0.05 mm hareket ettirir.
- Sınır dışına taşımaz.
- Payload güncel kalır.

## Regression Kuralı

Bir interaction bug’ı düzeltildiğinde test sadece DOM’da handle aramaz. Mutlaka gerçek geometry değişimini doğrular.
