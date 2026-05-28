# RESPONSIVE LAYOUT AUDIT

## 2026-05-20 Guvenli Audit Baslangici

### AppShell / Sidebar / Main Content Analizi

- Aktif app shell `src/webui/index.html` icinde `.app.app-shell`, `aside.sidebar` ve `main.main.page-shell` yapisiyla kurulmus.
- CSS tarafinda app grid yaklasimi mevcut; sidebar yaklasik 236 px kullaniyor.
- `showSection` operasyon sayfalarini body class'lariyla isaretliyor: `operation-page-active`, `bulk-production-active`, `name-cut-page-active`, `trendyol-page-active` vb.
- Dogru hedef: sidebar layout parcasi olmali, desktop'ta icerigin ustune binmemeli; main her zaman `min-width: 0` davranisini korumali.

### Max / Min Width ve Fixed Width Riskleri

- Etiket Studio icin birden fazla CSS bloku var; yeni grid ve eski `.manual-studio` kurallari ayni sayfada kalabildigi icin toolbar/canvas/panel regresyon riski yuksek.
- Trendyol kartlari ve queue satirlari sabit/minmax kolon toplamindan dolayi 1366 px civarinda fazla sikisabilir.
- Toplu Uretim ve model galerilerinde cok sayida kart/panel ayni anda ekrana bindiginde zoom out ihtiyaci dogabilir.
- Bazi bolumlerde `minmax(860px, 1fr)` veya genis sag panel davranisi tum sayfaya yatay scroll tasiyabilir.

### Overflow / Drawer Sorunlari

- Geniş veri bolumlerinde tum sayfa degil, ilgili tablo/galeri bolumu yatay scroll almali.
- Sag drawer/panel desktop'ta layout parcasi, 1280 altinda overlay/collapsible davranisina gecmeli.
- Trendyol musteri kanit drawer'i acildiginda ana liste tamamen ezilmemeli; ana kartlarda kritik aksiyonlar gorunur kalmali.

### Sayfa Kucultme / Zoom Problemi

- Sorun font kucultmeyle cozulmeyecek.
- Operasyon sayfalarinda gereksiz max-width kaldirilmali.
- Canvas sayfalarinda toolbar yukseklikleri ve sag panel genisligi kisitlanmali.
- Toplu Uretim gibi agir ekranlarda tum paneller ayni anda degil, stepper mantigi ile aktif adim gosterilmeli.

### Test Stratejisi

| Genislik | Beklenen davranis |
| --- | --- |
| 1920x1080 | Tum ana kolonlar ferah, sag panel acik, aksiyonlar tek satir veya kontrollu grup |
| 1600x900 | Normal masaustu compact spacing, drawer/panel okunur |
| 1366x768 | Detaylar compact/collapse, canvas ana odak kalir, butonlar kesilmez |
| 1280 px | Sag panel overlay/collapsible olabilir, tablolar kendi icinde scroll alir |

### Ilk Duzeltme Onerisi

1. AppShell ve OperationPageContainer standardini yazili hale getir.
2. Etiket Studio ve Isim Kesim icin canvas-first layout standardini Design Lab'da dogrula.
3. Trendyol ve Toplu Uretim icin kart/tablo/galeri minmax kurallarini ayri responsive audit ile ele al.
