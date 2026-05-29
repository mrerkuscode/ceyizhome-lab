# CeyizHome Lab Design System Raporu

Tarih: 2026-05-20

## Marka Standardi

- Uygulama adi: CeyizHome Lab
- Alt kimlik: Production & Label Studio
- Ana aciklama: Etiket, Trendyol, toplu uretim ve lazer isim kesim operasyon merkezi.
- His: sicak ama teknik olmayan, profesyonel masaustu uretim uygulamasi.

## Renk Standardi

- Ana aksiyon: mor/mavi `#4f46e5` ve `#2563eb`
- Uretim/siraya ekle: turuncu `#f97316`
- Hazir/basarili: yesil `#16a34a`
- Hata/engel: kirmizi `#ef4444`
- Kanit/bilgi: mavi `#0ea5e9`
- Zemin: beyaz ve acik gri tonlari

## Layout Standardi

- Sol sidebar acik: 240-280 px
- Sol sidebar kapali: 64-80 px
- Ana alan: kalan genislik, `min-width: 0`
- Sag panel/drawer: 320-380 px
- Operasyon sayfalari gereksiz `max-width` ile daraltilmayacak.
- Canvas sayfalarinda canvas ana alan olarak kalacak; sag panel canvas'i ezmeyecek.

## Ortak Component Hedefleri

- AppShell
- Sidebar
- PageHeader
- PageToolbar
- OperationPageContainer
- MetricCard
- StatusBadge
- ActionButton
- DataCard
- DataTable
- Drawer
- Modal
- Stepper
- CanvasShell
- RightPanel
- BottomDock
- ColorPalette
- EmptyState
- ErrorState
- LoadingState

Bu calismada bu componentlerin production'a zorla tasinmasi yapilmadi. Once `Design Lab` icinde referans component davranislari olusturuldu.

## Responsive Kural

- 1920x1080: ferah, sag panel acik olabilir.
- 1600x900: normal masaustu, kolonlar okunur.
- 1366x768: compact, detaylar kisalir ama ana aksiyonlar gorunur.
- 1280 px: sag panel gerekirse alt/drawer davranisina gecer.
- Problem font kuculterek veya sayfa zoom taklit edilerek cozulmeyecek.

## Sayfa Tipleri

- Operasyon sayfalari: Trendyol, Toplu Uretim, Etiket Studio, Isim Kesim, Yazdirma Sirasi.
- Form/ayar sayfalari: Ayarlar, Entegrasyonlar, kullanici/rol ayarlari.
- Teknik/gelismis sayfalar: normal operator ekranindan gizli veya Ayarlar/Sistem altinda kapali grup.

## Kabul Kriteri

- Default HTML buton gorunumu yok.
- Paneller ust uste binmez.
- Ana canvas/listeler kullanilabilir alani doldurur.
- Sag panelde yatay scroll yok.
- Renk paletleri kare swatch olarak gorunur.
- Butonlar gercek fonksiyona bagli degilse production'da sahte basari vermez.
