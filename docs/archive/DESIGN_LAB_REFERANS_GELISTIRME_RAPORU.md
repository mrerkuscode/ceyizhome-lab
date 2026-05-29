# DESIGN LAB REFERANS GELISTIRME RAPORU

## 2026-05-20

### Kapsam

Bu calisma production ekranlari yeniden tasarlanmadan, mevcut `designLab` section icindeki referans ekranlarini profesyonel tasarim hedeflerine yaklastirmak icin yapildi.

### Gelistirilen Design Lab Ekranlari

- Etiket Studio Referans: profesyonel command bar, model/olcu satiri, font toolbar, ince sol arac cubugu, buyuk canvas, sag Alanlar inspector paneli, kare renk paleti ve status bar ile yeniden duzenlendi.
- Isim Kesim Referans: 800 x 600 mm lazer nesting calisma alani, sol isim kaynagi, ince arac rayi, sag ayar/kontrol paneli, katman paleti ve kapali object inspector bar mantigi ile yeniden duzenlendi.

### Degisen Dosyalar

- `src/webui/index.html`
  - Sadece `designLab` section icindeki `etiket` ve `isim` referans view markup'i guncellendi.
  - Yeni butonlar mock/static referans butonlari olarak eklendi; production fonksiyonlara `onclick` ile baglanmadi.
- `src/webui/styles.css`
  - Sadece `.design-lab-page` altinda scoped premium referans CSS eklendi.
  - Production Etiket Studio, Trendyol, Toplu Uretim, Isim Kesim veya backend bridge secicileri degistirilmedi.

### Production Ekranlara Dokunuldu mu?

Hayir. Production sayfa sectionlari, Python bridge/backend methodlari ve gercek aksiyon handlerlari degistirilmedi. Bu turda yalnizca Design Lab referans yuzeyi ve bu rapor eklendi.

### Etiket Studio Referansinda Neler Var?

- CeyizHome Lab marka kilidi ve "Hizli Uretim Modu" bilgisi.
- Yeni, Ac, Kaydet, Farkli Kaydet, Geri, Ileri, PDF/PNG, Yazdir ve Siraya Ekle komutlari mock command bar icinde.
- Model, Model Sec, Etiket Boyutu, Genislik, Yukseklik, Ozel Boyut satiri.
- Font, boyut, B/I/U, hizalama ve renk toolbar'i.
- Sol 70 px civari ikon agirlikli arac cubugu.
- Grid/cetvelli buyuk canvas ve guvenli alanli etiket preview.
- Secili isim alani icin mavi selection box, corner handle ve rotate handle mock'u.
- Sag panelde Alanlar, Stil, Yerlesim, Siparis / Kanit sekmeleri.
- Alan sirasi: Isim, Tarih, Not, Adet, Lazer isim.
- Lazer isim aciklamasi: "Lazer kesim alanina otomatik gonderilir."
- Bozulmayan kare renk paleti ve status bar.

### Isim Kesim Referansinda Neler Var?

- CeyizHome Lab / Isim Kesim command bar.
- Yeni, Ac, Kaydet, Geri, Ileri, Yakinlastir, Ekrana Sigdir, Otomatik Diz, Weld / Birlestir, Noktalari Bagla, SVG/DXF/PDF Cikti mock komutlari.
- Sol isim kaynagi: Manuel, Excel, Kopyala/Yapistir, Toplu Uretim, Trendyol.
- Ornek isimler: Irem, Ozge, Umit, Bugra, Burak, Ceren, Serkan, Can, Abdurrahman, Yagmur, Efe, Ayse, Mehmet.
- 800 x 600 mm beyaz tabla, cetvel, grid, kirmizi calisma siniri ve guvenli margin.
- Isimler siyah outline/curve hissinde, birbirine baglanmadan ve minimum bosluk mantigiyle gosterildi.
- Noktali harf/kopma kontrol rozetleri icin mock uyarilar.
- Sag panelde Yerlesim, Yazi/Stil, Boyut, Kalinlastirma, Kontrol, Cikti sekmeleri.
- Minimum bosluk 1.5 mm, font Mochary Use Personal, offset 0.30 mm, kullanilan alan %92.
- Katman paleti: Kesim, Isaretleme, Gravur, Yardimci.

### Sonraki Tura Kalanlar

- Trendyol Siparisleri referans ekranini ayni kalite seviyesine cikarmak.
- Toplu Uretim Studio referansinda stepper + galeri + sag ozet panelini daha profesyonel hale getirmek.
- Yazdirma Sirasi, Etiket Modelleri ve Manuel Etiket referanslarini compact desktop standardina almak.
- Design Lab icin 1920x1080 ve 1366x768 screenshot gate eklemek.

### Test Sonuclari

- `node --check src/webui/app.js`: PASSED.
- `npm run test`: PASSED. Quick health audit raporu: `output/2026-05-20/project_health/PROJECT_HEALTH_AUDIT.md`.
- `npm run build --if-present`: package.json icinde build scripti olmadigi icin no-op tamamlandi.
- `npm run lint --if-present`: package.json icinde lint scripti olmadigi icin no-op tamamlandi.
- `npm run typecheck --if-present`: package.json icinde typecheck scripti olmadigi icin no-op tamamlandi.
- `git status --short`: parent repo halen `production-bot/`, `renders/`, `scripts/`, `tools/` dizinlerini untracked gosteriyor; bu onceki repo durumuyla uyumlu.

### Screenshot

- Bu turda ekran goruntusu alinmadi. Degisiklikler Design Lab mock markup/CSS ve raporla sinirli tutuldu.
