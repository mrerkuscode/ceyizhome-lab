# ENGINEERING STANDARDS

## State

Tek güvenilir state kullan:
- `selectedModel`
- `selectedLabelModel`
- Etiket Studio current field values
- field geometry
- output paths

Kart, sağ panel, Studio ve queue aynı model/path bilgisini kullanmalıdır.

## Render Payload

PDF/PNG payload her zaman son canvas state'ini taşımalıdır:
- model id/path
- width_mm
- height_mm
- background path
- label_text
- date_text
- note_text
- visible fields
- x/y/width/height
- font_size
- font
- color
- alignment
- quantity

Backend eski/stale template değerlerine düşmemelidir.

## Output Validation

PDF/PNG sonrası kontrol:
- dosya var mı?
- dosya taze mi?
- background var mı?
- İsim/Tarih/Not görünüyor mu?
- sadece krem/bej placeholder mı?

Fail ise başarı mesajı gösterme ve queue'ya ekleme.

## Queue

Queue yalnızca doğrulanmış output alır. Duplicate engeli korunur.

Direct print kapalıdır. PDF manuel kontrol edilir.

## Backup

Model config değişirse önce backup:
- yeni model oluşturma
- preview/background bağlama
- duplicate temizleme
- varsayılan alan oluşturma
- ölçü değişikliği

Kaynak AI/CDR asla değiştirilmez.

## Event Binding

Dinamik render sonrası butonlar kopmamalı. Kritik dinamik alanlarda event delegation veya render sonrası net binding kullanılmalı.

Canvas interaction:
- pointerdown/pointermove/pointerup
- pointer capture
- handle z-index
- pointer-events
- zoom/imageRect dönüşümü

Test sadece handle varlığını değil geometry değişimini doğrulamalıdır.

## Test Standardı

Regression test gerçek bug'ı yakalamalı:
- button -> route/state değişimi
- drag -> x/y değişimi
- resize -> width/height/font_size değişimi
- render -> pixel/output validation
- queue -> doğru path

## Kod Değişiklikleri

Küçük ve güvenli değişiklik yap. Büyük refactor P3/manuel karar konusudur.
