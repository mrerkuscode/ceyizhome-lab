# DESIGN UX AUDIT

## 2026-05-20 Guvenli Audit Baslangici

### Marka Standardi

- Uygulama adi: CeyizHome Lab.
- Alt metin: Production & Label Studio.
- Konumlandirma: CeyizHome'un etiket, Trendyol, toplu uretim, yazdirma ve lazer isim kesim operasyonlarini tek merkezden yoneten profesyonel masaustu uretim uygulamasi.
- Hedef his: web paneli degil; sade, hizli, guvenilir, masaustu uygulamasi gibi calisan uretim merkezi.

### Mevcut Tasarim Sorunlari

- Aktif UI monolitik HTML/CSS/JS icinde oldugu icin ayni sayfa uzerinde eski ve yeni layout kurallari bir arada yasiyor.
- Bazi ekranlarda butonlar modern component standardinda, bazi alanlarda ise eski form/button hissi suruyor.
- Canvas ekranlari, sag panel ve toolbar yukseklikleri birbiriyle rekabet ettiginde ana calisma alani kuculuyor.
- Production kullanicisinin ana aksiyonu ile referans/yardim/teknik aksiyonlar bazi ekranlarda ayni gorunurluk seviyesinde.
- Bazi bos durum kartlari ve yardim panelleri, uretim akisini desteklemek yerine ekrani kalabaliklastiriyor.

### Renk Sorunlari

- Ana mor/mavi renk korunmali, ancak kritik uretim aksiyonlari ile referans aksiyonlari ayrismali.
- Turuncu sadece uretim/siraya ekle/dikkat aksiyonlarinda kullanilmali.
- Yesil hazir/basarili, kirmizi hata/engelleyici, mavi kanit/mesaj, mor lazer/ozel uretim anlaminda sabitlenmeli.
- Tek hue etrafinda donen ekranlar masaustu uretim hissini zayiflatiyor; durum renkleri anlamli kullanilmali.

### Spacing ve Boyut Sorunlari

- Operasyon sayfalarinda gereksiz dar max-width kullanimi olmamali.
- Panel ve kart paddingleri sayfa turune gore standarda baglanmali: canvas ekranlari daha kompakt toolbar, veri ekranlari daha okunabilir satir araligi kullanmali.
- 1366 px genislikte font kucultmek yerine detaylar collapse edilmeli veya ilgili bolum kendi icinde scroll almali.

### Buton Standardi Sorunlari

- Buton hiyerarsisi net olmali: primary, production/orange, secondary, ghost, danger, disabled.
- Fonksiyonu olmayan butonlar aktif gorunmemeli.
- Sahte success yasak: endpoint/bridge yoksa pasif veya acik uyarili olmalı.
- Ikon + kisa metin masaustu uygulama hissini artirir; uzun buton metinleri compact gorunumde kisaltilmali.

### Panel ve Canvas Sorunlari

- Sag paneller canvas'tan rol calmamali; 320-380 px araliginda inspector gibi davranmali.
- Canvas sayfalarinda sol arac cubugu global sidebar ile karismamali.
- Renk paleti ve alt dock, canvas'i kapatmayan ince ve stabil bolumler olmali.
- Secim kutusu, handle, olcu etiketi ve guvenli alan standardi Etiket Studio ile Isim Kesim arasinda tutarli olmali.

### Yeni CeyizHome Lab Tasarim Dili

- Acik tema ana tema.
- Mor/mavi: ana aksiyon ve secili durum.
- Turuncu: uretim, siraya ekle, cikti hazirla.
- Yesil: hazir ve basarili.
- Kirmizi: hata ve uretime engel.
- Mavi: kanit, mesaj, bilgi.
- Mor: lazer, ozel uretim, script isim.
- Kartlar: 8-12 px radius, ince border, hafif golge, okunabilir ic bosluk.
- Masaustu hissi: compact command bar, inspector panel, dock/status bar, grid/canvas disiplini.

### Tasarim Karari

Production ekranlara direkt yama yapmadan once Design Lab referanslari uzerinde Etiket Studio, Isim Kesim, Trendyol ve Toplu Uretim icin temiz layout dogrulanacak.
