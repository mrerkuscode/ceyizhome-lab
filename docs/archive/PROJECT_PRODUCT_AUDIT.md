# CeyizHome Lab Proje Urun Denetimi

Tarih: 2026-05-20

## Konumlandirma

Proje adi CeyizHome Lab olarak ele alindi. Uygulama bir web paneli gibi degil, etiket, Trendyol, toplu uretim, yazdirma ve lazer isim kesim operasyonlarini yoneten profesyonel masaustu uretim uygulamasi olarak konumlandirildi.

## Ortak Mimari Gozlemi

- Aktif web arayuzu `src/webui/index.html`, `src/webui/app.js` ve `src/webui/styles.css` uzerinden calisiyor.
- Masaustu pencere katmani `src/desktop/web_main_window.py` ile bu web UI'yi yukluyor.
- Sol navigasyon, ana icerik ve operasyon sayfalari tek HTML uygulamasinda section tabanli ilerliyor.
- Daha once dogrudan production sayfalarda yapilan buyuk layout yamalari ust uste binme ve responsive riskini artirmis. Bu nedenle yeni tasarimlar once `Design Lab` sayfasinda izole edildi.

## Modul Denetimi

### Ana Sayfa

- Amac: operatoru hizli uretim akislarina yonlendirmek.
- Kullanici: uretim operatoru ve sorumlu.
- Mevcut fonksiyonlar: Etiket Studio, Toplu Uretim ve Etiket Modelleri girisleri.
- UI sorunu: eski marka dili Cyzella idi; uygulama butunuyle CeyizHome Lab hissine tasinmali.
- Iyilestirme: marka basligi ve ana aciklama CeyizHome Lab standardina cekildi.

### Etiket Studio

- Amac: tekli etiket duzenleme, model secme, alanlari doldurma, PDF/PNG, yazdirma ve siraya ekleme.
- Kullanici: uretim operatoru.
- Mevcut fonksiyonlar: model secme, canvas render, alan duzenleme, renk/font, cikti ve kuyruk akislarinin buyuk bolumu mevcut.
- UI sorunu: son degisikliklerde toolbar, model satiri, canvas ve sag panel birbirini ezebiliyor.
- Daha iyi tasarim: sol ince arac cubugu, buyuk canvas, sagda tek kaynak Alanlar paneli, altta kare renk paleti.
- Design Lab durumu: referans ekran eklendi; production entegrasyon icin once bu yapi onaylanmali.

### Trendyol Siparisleri

- Amac: Trendyol siparislerinden uretime alinacak kisilestirme islerini yonetmek.
- Kullanici: operator ve uretim sorumlusu.
- Mevcut fonksiyonlar: siparis cekme, soru/kanit akisi, AI alan ozeti, urun eslestirme, uretime aktarma ve aktarim gecmisi parcalari mevcut.
- UI sorunu: genis veri kartlari daralabiliyor, AI alan ozeti ve mesaj kolonlari sikisabiliyor.
- Daha iyi tasarim: tablo-kart hibriti, coklu mesaj kanit paneli, sag drawer ve guvenli toplu aksiyon bari.
- Kritik kural: isim/tarih/not urun adindan degil, musteri mesaji veya operator onayli veriden gelmeli.

### Toplu Uretim Studio

- Amac: Excel, Trendyol ve manuel kaynaklardan gelen etiket/lazer islerini toplu hazirlamak.
- Kullanici: toplu uretim operatoru.
- Mevcut fonksiyonlar: Excel okuma, kolon kontrolu, galeri, onizleme, rapor ve kuyruk akislari parca parca mevcut.
- UI sorunu: eski Excel paneli cok fazla bilgiyi ayni anda gosteriyor; 100% zoom'da okunabilirlik dusuyor.
- Daha iyi tasarim: 6 adimli sihirbaz, sag Uretim Ozeti, varsayilan Toplu Onizleme Galerisi.

### Isim Kesim / Lazer Kesim

- Amac: Mochary/script fontlu lazer isimleri 800x600 mm tabla icinde RDWorks'e uygun hazirlamak.
- Kullanici: lazer hazirlik operatoru.
- Mevcut fonksiyonlar: isim listesi, RDWorks benzeri tabla, nesting ve export hazirliklari mevcut.
- UI sorunu: teknik ayarlar normal operatoru yorabilir; laser modulu etiket editoruyle karismamali.
- Daha iyi tasarim: 800x600 tabla ana odak, sol isim kaynagi, sag yerlesim/stil/offset/kontrol paneli.
- Kritik kural: farkli isimler asla birbirine baglanmaz; weld sadece tek ismin kendi icinde uygulanir.

### Yazdirma Sirasi

- Amac: manuel, Trendyol, Excel/toplu ve lazer kaynakli uretim islerini sirada yonetmek.
- Mevcut fonksiyonlar: kuyruk ve cikti listesi mevcut.
- UI hedefi: kaynak, model, adet, durum, onizle, yazdir, sil ve hata bilgisi tek satirda okunmali.

### Etiket Modelleri

- Amac: kayitli etiket modellerini galeriyle yonetmek.
- Mevcut fonksiyonlar: model listeleme, gorsel yukleme, yeni model, varyant ve teknik mod mevcut.
- UI hedefi: normal kullanici teknik sablon alanina dusmeden model secebilmeli; teknik alan admin/gelismis modda kalmali.

### Manuel Etiket

- Amac: kucuk ve hizli isler icin isim/tarih/not/adet/lazer isim girip uretime almak.
- Mevcut durum: Etiket Studio'ya yonlenen hizli akis olarak calisiyor.
- UI hedefi: kisa form, model secimi, onizleme, Studio'da ac ve siraya ekle.

### Ayarlar / Entegrasyonlar

- Amac: teknik ayarlari production ekranlarindan ayirmak.
- Mevcut fonksiyonlar: Trendyol API ve teknik pencere acma akislari mevcut.
- UI hedefi: API key, secret, supplier ve ortam ayarlari sadece Ayarlar > Entegrasyonlar > Trendyol API altinda kalmali.

## Riskler

- Tek HTML icinde cok buyuk sayfa agaci var; buyuk production entegrasyonlari kucuk adimlarla yapilmali.
- Bazi butonlar backend fonksiyonu olmayan referans veya yarim akis olabilir; sahte basari verilmeyecek, baglanamayanlar pasif/raporlu kalacak.
- Design Lab statik referanstir; production ozelliklerini silmez veya degistirmez.

---

## 2026-05-20 Guvenli Audit Baslangici

### Proje Mimarisi

- Uygulama, PySide tabanli masaustu kabuk icinde calisan HTML/CSS/JavaScript web arayuzu ve Python bridge/backend servislerinden olusur.
- Aktif UI yolu: `production-bot/src/webui`.
- Legacy UI yolu: `production-bot/src/desktop/web_ui`.
- Python bridge/backend girisleri: `production-bot/src/desktop/web_main_window.py` ve `production-bot/src/webui_backend`.
- Aktif UI halen buyuk olcude `index.html`, `app.js` ve `styles.css` icinde monolitik ilerliyor. Bu durum hizli prototip icin pratik, ama desktop kalitesinde layout ve test edilebilir component standardi icin riskli.
- Parent git durumunda `production-bot/` untracked gorunuyor; uygulama fazlarinda buyuk refactor oncesi net checkpoint/branch stratejisi gerekli.

### Modul Audit Ozeti

| Modul | Amac | Kullanici rolu | Uretim problemi | Mevcut ozellikler | Eksik / yarim / riskli alanlar |
| --- | --- | --- | --- | --- | --- |
| Dashboard | Gunluk uretim durumunu ve hizli girisleri gostermek | Uretim sorumlusu, operator | Tum sistemin durumunu tek bakista anlamak | KPI kartlari, hizli akis kartlari, modullere gecis | Daha cok web dashboard hissi; desktop operasyon merkezi ritmi netlestirilmeli |
| Etiket Studio | Tekli etiket tasarim ve uretim hazirligi | Etiket operatoru | Isim/tarih/not/adet/lazer isim ile hizli cikti almak | Model secme, alan girisi, canvas, PDF/PNG, yazdirma/sira akislari | UI/CSS tekrarlarindan dolayi toolbar, panel, renk paleti ve canvas stabilitesi riskli |
| Etiket Modelleri | Kayitli modelleri galeri ve teknik alanlarla yonetmek | Operator, admin | Dogru modeli secmek, gorsel eksigi bulmak | Model listesi, gorsel yukleme, yeni model, alan duzenleme, backup | Teknik alanlar normal kullaniciyi yorabilir; admin/gelismis mod ayrimi netlestirilmeli |
| Manuel Etiket | Kucuk tekil isleri hizli uretmek | Operator | Excel/Trendyol gerektirmeyen isleri hizlica almak | Etiket Studio ile ortak alanlar ve render kuyrugu | Tek kaynak alan prensibi korunmali; tekrar inputlar kaldirilmali |
| Toplu Uretim Studio | Excel/Trendyol/manuel kaynakli coklu etiket ve lazer islerini hazirlamak | Uretim sorumlusu | 100-500 kaydi hata ayiklayip uretime almak | Stepper, galeri, bulk preview, Excel hazirligi, lazer aktarim baglari | Galeri/thumbnail performansi, fonksiyonlarin kismi bagli olmasi ve fazla panel kalabaligi riskli |
| Isim Kesim | Lazer isimleri 800x600 mm tabla icinde hazirlamak | Lazer operatoru | Script fontlu isimleri RDWorks uyumlu, kopmadan, sik dizmek | Isim listesi, nesting, SVG/DXF/PDF hazirliklari, Mochary/script destekleri | Gercek path/weld/offset dogrulama ve farkli isimlerin baglanmama kurali surekli test edilmeli |
| Yazdirma Sirasi | Tum kaynaklardan gelen ciktilari kuyruklamak | Operator | Neyin yazdirilacagini ve durumunu takip etmek | Kuyruk listeleme, PDF ekleme, durum degistirme, guvenli print methodlari | Uzun kuyruklarda fixed kolon ve aksiyon gorunurlugu riskli |
| Trendyol Siparisleri | Siparis, kanit, AI alan ozeti ve uretim aksiyonlarini yonetmek | Trendyol operatoru | Mesajdan dogru kisisellestirme alip hatali kaydi engellemek | Siparis sync, soru sync, mapping, kanit baglama, Excel aktarim | Kargo/fatura/Trendyol isleme gibi bazi butonlar kismi veya pasif kalmali; sahte basari verilmemeli |
| Kontrol Kuyrugu | Sorunlu Trendyol kayitlarini ayirmak | Operator | Eksik kanit/model/alan/güven sorunlarini cozmek | Trendyol sidebar tab uzerinden filtrelenen is listesi | Ayrik sayfa gibi gorunse de ayni `trendyolOrders` yuzeyi; bilgi mimarisi netlestirilmeli |
| Urun Eslestirme | Barkod/SKU ile etiket modeli eslestirmek | Admin/operator | Urun-model bagini kalici hale getirmek | Mapping import/export/upsert/propose/approve | Otomatik eslestirme guven skoru ve operator onayi daha gorunur olmali |
| Kanit Eslestirme | Musteri soru/mesajlarini siparise baglamak | Operator | AI alanlari icin guvenilir kaynak secmek | Soru sync, apply/ignore question, drawer mantigi | Birden fazla mesaj akisi ve drawer performansi test edilmeli |
| Aktarim Gecmisi | Uretime giden islerin gecmisini izlemek | Uretim sorumlusu | Kimin neyi ne zaman aktardigini bilmek | Trendyol aktarim ve output listeleri | Event tipi ve hata ayrintilari daha sistematik standarda alinmali |
| Ayarlar / Entegrasyonlar | API, kargo, sistem ve teknik ayarlari toplamak | Admin | Teknik ayarlari operator ekranlarindan ayirmak | Trendyol API ayarlari, genel/kullanici/rol sekmeleri | Production ekranlarindan teknik linkler temizlenmeli; normal kullanici teknik alana dusmemeli |

### Ilk Risk Siralamasi

1. Etiket Studio ve Isim Kesim canvas ekranlari layout regresyonuna en acik bolgeler.
2. Trendyol ekraninda gercek backend bagli aksiyonlarla referans/uyari butonlari ayni gorsel agirlikta durabiliyor.
3. Toplu Uretim galerisi ve lazer isim listesi buyuk veride virtualization/cache ihtiyaci tasiyor.
4. CSS monolitik ve tekrarli; production refactor icin once Design Lab referansi sart.
