# Proje Calisma Mantigi Raporu

Tarih: 2026-05-20  
Kapsam: Cyzella Production Studio aktif vanilla WebView uygulamasi (`src/webui`) ve Python backend koprusu (`src/webui_backend`)

## 1. Genel Amac

Cyzella Production Studio; Trendyol siparisleri, musteri mesajlari, etiket tasarimi, toplu uretim, yazdirma sirasi ve lazer isim kesim akisini tek operator uygulamasinda birlestiren bir uretim yazilimidir. Ana hedef kullanicinin isim, tarih, not, adet ve lazer isim gibi kisisellestirme alanlarini dogru yakalayip hatali kaydi uretime gondermeden etiket, yazdirma ve lazer hazirligina tasimasidir.

Aktif masaustu arayuz `src/webui/index.html`, `src/webui/app.js` ve `src/webui/styles.css` uzerinden calisiyor. Repo icindeki `src/desktop/web_ui` legacy olarak isaretlenmis ve aktif WebView girisi degil.

## 2. Ana Moduller

### Trendyol Siparisleri

Amac: Trendyol siparislerini, urun bilgisini, musteri soru/mesaj kanitini, AI alan ozetini, urun eslestirmeyi ve uretime aktarma kararini tek panelde operatorun onune getirmek.

Calisan islevler:
- Son 7 gun / siparis senaryolari icin deterministic smoke testleri var.
- Soru kanitindan isim/lazer isim uretimi test ediliyor.
- Urun gorseli/link smoke testi mevcut.
- Uretime aktarimda RDWorks/lazer/yazici otomatik baslatma guvenlik kapilari korunuyor.
- Kontrol kuyrugu, urun eslestirme, kanit eslestirme ve aktarim gecmisi UI akislari test kapsaminda.

Riskler:
- Canli Trendyol servisindeki soru senkronu kullanici tarafindan yavas/eski gorunmus; bunun icin yerel veri audit scriptleri var ama canli endpoint performansi ayrica izlenmeli.
- Bazi kargo/fatura/Trendyol durum aksiyonlari bilincli olarak pasif veya yerel durum mantiginda; sahte basari gosterilmemeli.

### Etiket Studio

Amac: Manuel veya Trendyol kaynakli isim/tarih/not/adet/lazer isim alanlariyla etiket modelini acmak, canvas uzerinde gorsel duzenleme yapmak, PDF/PNG/yazdirma/siraya ekleme akisini yurutmek.

Calisan islevler:
- Model, alan, canvas, undo/redo, guvenli alan ve render stabilitesi icin smoke testleri var.
- Trendyol alanlari Studio'ya tasinabiliyor.
- Bazi ileri araclar bagli degilse kullaniciya "henüz baglanmadi" mesaji veriliyor; bu dogru davranis, sahte basari degil.

Riskler:
- Tam Corel seviyesi tum araclar bagli degil. Normal uretim icin kritik olmayan araclar pasif/uyarili kalmali.
- PDF/PNG ve yazdirma akislari uretim oncesi kontrolle calismali; otomatik fiziksel yazdirma yapilmamali.

### Toplu Uretim Studio

Amac: Excel, Trendyol ve manuel kaynaklardan gelen coklu etiket/lazer islerini adim adim hazirlamak; kolon eslestirme, model secme, galeri onizleme, hata duzeltme ve uretime alma akisini kurmak.

Calisan islevler:
- 100 satirlik toplu galeri smoke testi gecer durumda.
- Galeri kartlari, secim, modal, duzenleme, silme, yazdirma modal akisi ve yazdirma sirasi entegrasyonu test ediliyor.
- Hazir/hata ayrimi ve bozuk gorsel gostermeme kontrolu mevcut.

Riskler:
- 500 kayit icin tam virtualization henuz kapsamli uygulanmadi; mevcut test 100 kayit DOM dogrulamasi yapiyor.
- Kargo/fatura gibi dis sistem aksiyonlari canli entegrasyon yoksa pasif kalmali.

### Isim Kesim / Lazer Kesim

Amac: Mochary/script font isimlerini 800x600 mm tabla icine RDWorks mantigina uygun, sik ama birbirine baglamadan yerlestirmek; SVG/DXF/PDF/PLT hazirlamak.

Calisan islevler:
- RDWorks uyumlu 800x600 mm layout smoke testi mevcut.
- Farkli isimleri birbirine baglamama, ayri kesim objesi olarak tutma ve lazer otomatik baslatmama guvenlik kontrolleri test ediliyor.
- Export oncesi font/path ve guvenlik kontrolleri backend tarafinda bulunuyor.

Riskler:
- Gercek font-to-curve ve offset kalitesi lazer uretiminde fiziksel numune ile ayrica dogrulanmali.
- RDWorks'e dosya hazirlanir; makine baslatma otomatik yapilmamali.

### Yazdirma Sirasi

Amac: Manuel, Trendyol, Excel ve lazer kaynakli isleri siraya almak; onizleme, yazdirma, durum degistirme ve silme akisini operator icin guvenli hale getirmek.

Calisan islevler:
- Yazdirma sirasi akisi icin browser smoke testi mevcut.
- Secim, detay paneli, toplu secim, print modal, filtre ve temizleme modali test ediliyor.

Bulunan ve duzeltilen sorun:
- 100% zoom'da sag detay paneli acikken aksiyon butonlari liste alaninin disina tasiyordu. `src/webui/styles.css` icinde print queue grid min-width/kolon guard'i duzeltildi.

### Etiket Modelleri

Amac: Kayitli modelleri listelemek, onizlemek, eksik gorsel uyarisini gostermek ve model secimini Studio/uretim akislarina baglamak.

Calisan islevler:
- Responsive screenshot test kapsaminda.
- Model katalogu ve premium UI akislari icin onceki rapor/test altyapisi var.

Riskler:
- Model olusturma ve teknik model ayarlari normal operator ekranindan ayrik tutulmali.

### Manuel Etiket

Amac: Operatorun hizli isim/tarih/not/adet/lazer isim girerek manuel uretim baslatmasi.

Calisan islevler:
- Responsive test kapsaminda.
- Etiket Studio'ya veri tasima akisi korunuyor.

### Ayarlar / Entegrasyonlar

Amac: Teknik entegrasyonlarin operasyon ekranindan ayrilmasi. Trendyol API ayarlari uretim sekmelerinde degil, Ayarlar > Entegrasyonlar > Trendyol API altinda tutulmali.

Calisan islevler:
- Kullanici onboarding / teknik gorunurluk testleri teknik araclarin normal operatoru yormamasini kontrol ediyor.

## 3. Veri Akisi

1. Trendyol siparisi ve satir bilgisi yerel veri/API katmanina gelir.
2. Musteri sorulari ve siparis mesajlari soru kaniti olarak normalize edilir.
3. AI/explicit extractor alanlari cikarir: isim, tarih, not, adet, lazer isim.
4. Urun barkod/SKU/model eslestirmesi yapilir.
5. Kayit kontrol gerekli veya uretime hazir durumuna ayrilir.
6. Operator kanit, urun eslestirme ve AI alanlarini kontrol eder.
7. Etiket Studio / Toplu Uretim / Isim Kesim akislari dogru alanlarla acilir.
8. PDF/PNG, yazdirma sirasi, lazer kesim dosyasi ve aktarim gecmisi olusur.

## 4. Kullanici Akisi

Normal operator icin ideal akis:

1. Trendyol Siparisleri ekraninda son siparisleri ceker.
2. Kontrol gerekli ve uretime hazir metriklerini gorur.
3. Siparis kartinda musteri mesajini, AI alan ozetini, urun gorselini ve eslestirmeyi kontrol eder.
4. Eksik varsa kanit paneli, urun eslestirme veya manuel alan duzenleme ile tamamlar.
5. Uretime aktarir.
6. Etiket Studio'da son gorsel kontrolu yapar veya toplu isleri Toplu Uretim Studio'ya alir.
7. Lazer isim varsa Isim Kesim'e gonderir.
8. Yazdirma sirasi ve aktarim gecmisinden uretim durumunu takip eder.

## 5. Mevcut Calisan Ozellikler

- `.venv\Scripts\python.exe` resmi test interpreter'i olarak kullaniliyor.
- Extraction golden testleri gecer durumda.
- Trendyol smoke/test kapilari gecer durumda.
- RDWorks/lazer isim kesim cikti guvenlik kapilari gecer durumda.
- Toplu galeri ve yazdirma sirasi icin browser tabanli smoke testleri var.
- Responsive screenshot audit altyapisi var.
- API ayarlari uretim sekmelerinden ayrilmis durumda.

## 6. Eksik veya Yari Bagli Ozellikler

- `npm run build`, `npm run lint`, `npm run typecheck` scriptleri package.json icinde yok; bu nedenle build/lint sonucu raporda "yok" olarak belirtilmeli.
- Bazi ileri Studio araclari henuz cikti motoruna bagli degil; uyarili/pasif kalmali.
- Kargo/fatura canli entegrasyonlari tam bagli degilse sahte basari yerine pasif veya acik uyari gostermeli.
- 500+ kayit icin tam virtualization/caching iyilestirmesi sonraki performans isi olarak kalabilir.

## 7. Riskli Alanlar

- Canli Trendyol soru senkronunun eski soru gostermesi veya uzun tarih araliginda donmasi.
- Etiket/lazer ciktilarinda fiziksel uretim farklari; dijital smoke testin yaninda numune kesim gerekir.
- Cok buyuk Excel/toplu galeri veri setlerinde DOM/render maliyeti.
- Kullanici onayi olmadan yazici/lazer/Trendyol durum degisikligi baslatma riski; mevcut guvenlik prensibi korunmali.

