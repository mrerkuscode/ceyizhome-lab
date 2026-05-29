# UI/UX Remaining Work Roadmap

## 2026-05-16 Uygulama Sonrası Durum

P0: Yok.

P1: Testlerde kalan açık P1 yok. Studio flicker/topbar overflow ve Print Queue action clipping ara sorunları düzeltildi.

P2:

- Üst KPI/header alanlarını daha da kompakt hale getirme.
- Yardım/onboarding içeriklerini kullanıcı görev kartlarına çevirme.
- Raporlar sayfasında kullanıcı/teknik ayrımını daha sadeleştirme.
- Release paketi ve temiz kurulum ekranlarını son screenshotlarla bağlama.

P3:

- RDWorks ileri text-to-path/offset kalite turu.
- Installer/release automation.
- Gelişmiş responsive overflow ve mikro animasyonlar.

Tarih: 2026-05-13

## P0

Su anda kanitlanan acik P0 UI/UX sorunu yok.

P0 olarak izlenmesi gereken durumlar:

- Studio output butonu bir viewportta hic ulasilamaz hale gelirse.
- Yeni Model wizard footer kesilir ve kaydet yapilamazsa.
- Preview bos oldugu halde "hazir" gorunurse.
- Yazdir butonu direct/silent print gibi algilanir veya otomatik print baslatirsa.
- Toplu Excel hatali satirlari sessizce uretirse.

## P1

### 1. Toplu Etiket uzun isim ve galeri viewport stabilitesi

Sorun: Uzun isimler kart preview icinde tasabiliyor; nested scroll kullaniciyi yoruyor.  
Etkisi: 100 satirlik Excel'de kullanici hangi satirin hazir/hatalı oldugunu hizli okuyamaz.  
Cözum: Kart preview icin zorunlu auto-fit; grid yogunlugunu 3 kolon sabit + pagination; sag detay sticky action.  
Kabul: 100 satir fixture'da uzun isimler preview disina tasmaz, Kaydet/Vazgec/Sil gorunur kalir.

### 2. Queue/Outputs temiz demo ve problemli kayit ayrimi

Sorun: "Onizleme yok / kontrol gerekli" kayitlar ana gorunumde ilk secili olunca final hissi bozuluyor.  
Etkisi: Kullanici urunu bozuk zannedebilir.  
Cözum: Gecerli/preview'li kayitlari varsayilan one al; problemli/Test/QA kayitlari ayri filtrede tut.  
Kabul: Varsayilan Queue ve Outputs ekranlari temiz musteri verisiyle acilir.

### 3. Yeni Model wizard'i gercek adim akisine cevirmek

Sorun: 5 adim ayni anda gorunuyor, wizard gibi degil buyuk form gibi hissettiriyor.  
Etkisi: Normal kullanici yeni model eklerken karar yuklenmesi yasar.  
Cözum: Tek aktif adim; once/sonra; sticky footer; adim ozetleri; gorsel oran kontrolunu merkezlestir.  
Kabul: Kullanici sadece bir adimin kararlarini gorur ve kaydet sonrasi modeli Studio'da acabilir.

### 4. Studio output ve inspector erisilebilirligi

Sorun: Sag inspector scroll ve output aksiyonlari ekran altinda kesilebiliyor.  
Etkisi: Kullanici PDF/PNG veya Yazdir aksiyonunu aramak zorunda kalir.  
Cözum: Sticky output footer; compact accordion; property bar compact mode; sol toolbar sadece ikon + tooltip opsiyonu.  
Kabul: 1366x768 ve 1920x1080 ekranlarda output aksiyonlari gorunur veya tek scroll icinde sabit kalir.

## P2

- Etiket Modelleri ust KPI/filtre alanini daha kompakt yapmak.
- Etiket Ciktilari kartlarini daha fazla gorsel onizleme agirlikli yapmak.
- Yazdirma Sirasi tablo kolonlarini sag panelle daralmayacak sekilde responsive yapmak.
- Ayarlar sayfasinda teknik bolumleri accordion altina almak.
- Yardim/onboarding turunu daha gorsel hale getirmek.
- Raporlar sayfasinda musteri raporu / teknik rapor ayrimini guclendirmek.
- Tasarim sistemi tokenlarini ve ortak button/card/input/badge stillerini sade hale getirmek.

## P3

- Gelismis animasyon ve mikro etkilesimler.
- Tam responsive overflow menuleri.
- RDWorks true boolean/geometric offset motoru.
- Gelismis fire optimizasyonu.
- Installer/release automation.
- AI/gorsel analiz.

## Onerilen Uygulama Sirasi

1. Global demo veri ve problemli kayit ayrimi.
2. Toplu Etiket galeri viewport ve uzun isim polish.
3. Studio sticky output + inspector compact polish.
4. Yeni Model wizard finalization.
5. Queue ve Outputs varsayilan gorsel kalite polish.
6. Etiket Modelleri KPI/filter compact polish.
7. Design system cleanup.
8. Yardim/onboarding.
9. Final visual QA.
10. RDWorks teknik offset fazi.
