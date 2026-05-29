# UI/UX Design System Plan

Tarih: 2026-05-13

## Mevcut Durum

Uygulama genelinde Mac/iOS tarzina yaklasan bir tasarim dili var: acik zemin, soft card, yuvarlak koseler, mavi/mor primary, amber/yesil/kirmizi status renkleri. Ancak ayni tur UI bilesenleri sayfadan sayfaya farkli yogunluk, radius, font agirligi ve padding ile gorunebiliyor.

## Hedef

Tek bir sade uretim uygulamasi hissi:

- Mac uygulamasi kadar temiz.
- Canva kadar gorsel.
- Corel mantigi kadar hizli.
- Shopify admin kadar katalog/yonetim odakli.
- Uretim yazilimi kadar guvenli.

## Token Plani

### Renkler

- `--color-primary`: mavi/mor ana aksiyon.
- `--color-primary-soft`: secili kart, active tab.
- `--color-success`: dogrulandi/hazir.
- `--color-warning`: beklemede/kontrol gerekli.
- `--color-danger`: hata/sil.
- `--color-surface`: beyaz kart.
- `--color-page`: acik gri zemin.
- `--color-border`: ince border.
- `--color-muted`: ikincil metin.

### Radius

- `--radius-sm`: 8px, compact input/button.
- `--radius-md`: 12px, kart ve panel.
- `--radius-lg`: 18px, ana soft card/modal.
- `--radius-pill`: badge/button pill.

### Shadow

- `--shadow-soft`: normal kart.
- `--shadow-raised`: secili kart/modal.
- `--shadow-focus`: secili model/canvas object.

### Spacing

- 4/8/12/16/24/32 px sistemi.
- KPI ve kart paddingleri standardize edilmeli.
- Sayfa header yukseklikleri kisaltilmali.

### Typography

- Page title: 32-40px, sadece sayfa basligi.
- Section title: 18-22px.
- Card title: 15-18px.
- Body: 14-16px.
- Metadata: 12-13px.
- Font size viewport ile scale edilmemeli.

## Ortak Bilesen Planlari

### Button

Variantlar:

- Primary
- Secondary
- Ghost
- Success
- Warning
- Danger
- Icon-only

Kural:

- Sayfa basina en fazla bir ana primary aksiyon.
- Yazdir gibi guvenli ama guclu aksiyon primary/success olabilir, fakat modal onayla calisir.
- Danger aksiyonlar her zaman onay veya undo davranisi ister.

### Card

Variantlar:

- KPI card
- Gallery card
- Detail panel
- Compact row card
- Empty state card

Kural:

- Kart icinde kart kullanimi azalt.
- Katalog/galeri kartlari preview + metadata + aksiyon hiyerarsisi tasir.
- Technical/test kartlar normal musteri kartindan ayri stile sahip olur.

### Badge / Pill

Tek status dili:

- Hazir: yesil
- Uyari/Beklemede: amber
- Hata/Dosya yok: kirmizi
- Teknik/Test: gri/mor
- Secili: primary soft

### Modal

Kural:

- Footer sticky.
- Kaydet/Vazgec/Sil her zaman gorunur.
- Uzun modalda body scroll, footer sabit.
- Normal kullanici modalinda teknik path/JSON yok.

### Empty State

Kural:

- Bos beyaz kutu yasak.
- Her empty state 1 baslik, 1 aciklama, 1 ana aksiyon tasir.
- "Onizleme yok" durumunda cozum aksiyonu: PDF ac, gorsel bagla, yeniden olustur, Studio'da ac.

### Sidebar

Kural:

- Normal ana aksiyonlar belirgin.
- Teknik sayfalar soluk/ikincil.
- Teknik Mod kapaliysa teknik sayfalar pasif veya uyarili.

## Sayfa Bazli Design System Riskleri

- Etiket Studio: property bar ve toolbar kendi mini design system'ine ihtiyac duyuyor.
- Toplu Etiket: gallery card, selected detail, edit modal componentleri standardize edilmeli.
- Queue/Outputs: preview resolver ve placeholder component ortak olmali.
- Model katalog: model card ve output card arasinda preview/status/aksiyon hiyerarsisi benzer olmalı.

## Kabul Kriterleri

- Ayni variant butonlar tum sayfalarda ayni yukseklik/padding/radius ile gorunur.
- Status renkleri tum sayfalarda ayni anlama gelir.
- Modal footer hicbir ana viewportta kesilmez.
- Empty state'lerde bos beyaz kutu kalmaz.
- Teknik bilgi normal kullanici gorunumunde gorunmez.
# 2026-05-16 Uygulama Sonrası Tasarım Sistemi Notu

Global compact üretim yoğunluğu CSS katmanı uygulandı. Bundan sonra yeni UI eklenirken şu kurallar korunacak:

- Hover transform kullanılmayacak; hover sadece border, background veya shadow ile yapılacak.
- Backdrop blur/sticky blur sadece kritik olmayan yüzeylerde ve ölçülü kullanılacak.
- Sağ paneller kendi içinde scroll alacak, ana sayfa scroll'unu kırmayacak.
- Kart/KPI/header alanları ilk viewportu boğmayacak.
- Desktop sağ preview/detail paneli 1180px üstünde görünür kalacak.
- Native select açıldığında layout zıplaması kabul edilmeyecek.
