# CeyizHome Lab Kontrollu Uygulama Plani

Tarih: 2026-05-20

## Ilke

Bu proje artik CeyizHome Lab olarak ele alinacak. Production sayfalari, design-lab referanslari onaylanmadan buyuk ve riskli sekilde yeniden yazilmayacak. Calisan ozellikler korunacak, yeni layout parcalari kademeli tasinacak.

## Faz 1: Marka ve Referans Katmani

- Gorunen web marka metinleri CeyizHome Lab olarak guncellendi.
- Masaustu pencere basligi CeyizHome Lab olarak guncellendi.
- Design Lab sayfasi eklendi.
- Proje audit, design system ve design lab raporlari olusturuldu.

## Faz 2: Ortak Layout Cekirdegi

Hedef dosyalar:

- `src/webui/styles.css`
- `src/webui/index.html`
- `src/webui/app.js`

Yapilacaklar:

- OperationPageContainer davranisini netlestir.
- Sidebar/main/right-panel genisliklerini tek standarda bagla.
- Sag panelin desktop ve 1280 alti davranisini standardize et.
- Ortak button, badge, panel ve tab stillerini yavas yavas production'a tasi.

## Faz 3: Etiket Studio Production Tasima

- Mevcut kurtarma layout'u Design Lab Etiket Studio referansiyla karsilastirilacak.
- Alanlar paneli tek veri kaynagi olarak korunacak.
- Model/olcu satiri, font toolbar, canvas, sag panel ve renk paleti production'da netlestirilecek.
- Model secme, canvas render, PDF/PNG, yazdirma ve siraya ekleme fonksiyonlari korunacak.

## Faz 4: Trendyol Operasyon Paneli

- Ust sekmeler sadece Siparisler, Kontrol Kuyrugu, Urun Eslestirme, Kanit Eslestirme, Aktarim Gecmisi olacak.
- API Ayarlari yalniz Ayarlar > Entegrasyonlar > Trendyol API altinda kalacak.
- Siparis kartlari tablo-kart hibriti olarak Design Lab referansina yaklastirilacak.
- Mesaj/kanit drawer'i coklu mesaj mantigiyla baglanacak.
- AI alanlari yalniz kanit/musteri mesaji/operator verisinden beslenecek.

## Faz 5: Toplu Uretim Studio

- Excel/Trendyol/manuel kaynaklar 6 adimli akis altinda birlestirilecek.
- Eski Excel sayfasi tek ekrana yigilmaktan cikarilacak.
- Toplu Onizleme Galerisi ve sag Uretim Ozeti production'a kademeli tasinacak.
- Thumbnail lazy/cache ve buyuk liste optimizasyonu uygulanacak.

## Faz 6: Isim Kesim / Lazer Kesim

- 800x600 mm tabla, RDWorks referansi, Mochary varsayilan font ve minimum bosluk kurallari korunacak.
- Farkli isimleri baglamama kurali test standardi olacak.
- Offset, yatay/dikey olcekleme, nokta/kopuk parca kontrolleri production fonksiyonlarina zarar vermeden iyilestirilecek.

## Faz 7: Insan Gibi Test

Her modulde:

- Beklenen sonuc yazilacak.
- Gercek sonuc test edilecek.
- Hata bulunursa sebep analiz edilip duzeltilecek.
- Duzeltme tekrar test edilecek.
- Sahte basari kalmayacak.

## Gecis Kriterleri

- `node --check src/webui/app.js`
- Web UI responsive screenshot testi
- `npm run test`
- 1920x1080 ve 1366x768 screenshot
- Fonksiyon eksikleri raporlanmis olacak.
