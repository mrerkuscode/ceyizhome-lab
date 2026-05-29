# DESIGN LAB IMPLEMENTATION PLAN

## 2026-05-20 Guvenli Iskelet Baslangici

### Design-lab Neden Gerekli?

- Production ekranlar hali hazirda calisan Python bridge ve dosya tabanli uretim akislariyla bagli.
- Dogrudan production sayfalari uzerinde buyuk gorsel yama yapmak Etiket Studio, Trendyol, Toplu Uretim ve Isim Kesim gibi kritik ekranlarda regresyon riski tasiyor.
- Design Lab, production'a dokunmadan masaustu uygulama standardini, panel/canvas oranlarini, buton hiyerarsisini ve responsive davranisi test etmek icin guvenli alandir.

### Mevcut Durum

- Aktif UI icinde `designLab` section mevcut.
- Mevcut sekmeler: Genel Bakis, Etiket Studio, Trendyol, Toplu Uretim, Isim Kesim, Yazdirma, Modeller, Manuel.
- Bu, istenen modül bazli iskelet icin guvenli baslangic sagliyor.

### Referans Ekranlar

| Ekran | Amac | Mock data ihtiyaci | Ortak component ihtiyaci | Production'a tasima notu |
| --- | --- | --- | --- | --- |
| Etiket Studio | Canvas-first hizli uretim referansi | Model, alanlar, renk paleti, fake label preview | CanvasShell, RightPanel, ColorPalette, PageToolbar | Mevcut render/queue bridge korunarak parca parca tasinmali |
| Isim Kesim | 800x600 RDWorks uyumlu lazer nesting referansi | 75 isim, font/offset ayarlari | CanvasShell, InspectorPanel, BottomDock | Farkli isimlerin baglanmama kurali test edilmeden production'a alinmamali |
| Trendyol Siparisleri | Operasyon karti + kanit drawer referansi | Siparis, mesaj, AI alan ozeti | DataCard, RightDrawer, MetricCard, ActionBar | API ayarlari production sekmelerinden ayrilmali |
| Toplu Uretim Studio | Excel/Trendyol/Manuel stepper + galeri | 169 kart, hazir/hata/lazer durumlari | Stepper, GalleryCard, SummaryPanel | Galeri virtualization/cache planiyla tasinmali |
| Yazdirma Sirasi | Tum kaynaklardan gelen is kuyrugu | Queue rows | DataTable, StatusBadge | Guvenli print flow korunmali |
| Etiket Modelleri | Model galeri referansi | Model kartlari, gorsel eksik | DataCard, EmptyState | Teknik/admin alanlar ayrilmali |
| Manuel Etiket | Kucuk isler icin hizli form | Isim/tarih/not/adet/lazer | FormPanel, PreviewCard | Etiket Studio ile tek alan kaynagi paylasmali |

### Oncelik Sirasi

1. Etiket Studio Referans.
2. Isim Kesim Referans.
3. Trendyol Siparisleri Referans.
4. Toplu Uretim Studio Referans.
5. Yazdirma Sirasi, Etiket Modelleri, Manuel Etiket.

### Production'a Tasima Sirasi

1. Ortak AppShell/PageContainer standardi.
2. Etiket Studio layout kurtarma.
3. Isim Kesim 800x600 canvas ve inspector standardi.
4. Trendyol operasyon paneli ve kanit drawer.
5. Toplu Uretim stepper/galeri.
6. Queue, models, manual.

### Guvenlik Kurali

Design Lab ekranlari production fonksiyonlara baglanmayacak. Butonlar mock/static olacak ve gercek lazer, yazici, RDWorks veya Trendyol operasyonu tetiklemeyecek.
