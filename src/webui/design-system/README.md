# CeyizHome Lab Design System

## Marka Konumlandirmasi

- Urun adi: CeyizHome Lab.
- Alt metin: Production & Label Studio.
- Konum: Etiket, Trendyol, toplu uretim, yazdirma ve lazer isim kesim operasyon merkezi.
- UI hissi: siradan web paneli degil; modern, hizli, okunabilir ve guven veren masaustu uretim uygulamasi.

## Renk Paleti

- Acik tema ana tema: beyaz ve acik gri zemin.
- Ana aksiyon: mor/mavi.
- Uretim / siraya ekle: turuncu.
- Hazir / basarili: yesil.
- Hata / uretime engel: kirmizi.
- Kanit / mesaj / bilgi: mavi.
- Lazer / ozel uretim: mor.
- Disabled: dusuk kontrastli gri, ama okunabilir.

## Typography

- Normal metin: 14 px civari.
- Kucuk yardim metni: 12 px altina zorunlu olmadikca dusme.
- Buton metni: 13-14 px.
- Kart basligi: 15-18 px.
- Sayfa basligi: 24-32 px.
- Canvas uzeri teknik etiketler kucuk olabilir, fakat asil uretim metni okunabilir kalmali.

## Spacing

- Operasyon sayfalari: 16-24 px responsive padding.
- Compact canvas toolbarlari: 8-12 px ic bosluk.
- Kartlar: 12-16 px ic bosluk.
- Sag panel alanlari: 12-16 px aralik.
- Bosluk azaltma responsive davranisla olur; font kucultme ile sorun gizlenmez.

## Buton Standartlari

- Primary: mor/mavi, ana islem.
- Production: turuncu, yazdirma/siraya ekle/uretime al.
- Secondary: beyaz zemin, ince border.
- Ghost: dusuk oncelikli toolbar aksiyonu.
- Danger: kirmizi, silme veya uretime engel riskli aksiyon.
- Disabled: gercek fonksiyon yoksa veya kosul saglanmiyorsa kullanilir; sahte success verilmez.

## Kart / Panel Standartlari

- Radius: 8-12 px.
- Border: ince, acik gri.
- Shadow: hafif; paneli ayirmak icin kullanilir, dekorasyon icin degil.
- Kart icinde kart kullanimi sinirli tutulur.
- Teknik bilgi normal kullanici ekraninda gomulu/gelismis modda kalir.

## Sidebar Olculeri

- Acik sidebar: 240-280 px.
- Kapali sidebar: 64-80 px.
- Desktop'ta sidebar layout parcasi; ana icerigin ustune binmez.
- Mobil/dar ekranda overlay drawer olabilir.
- Sidebar kendi icinde scroll alir.

## Sag Panel Olculeri

- Sag panel: 320-380 px.
- Canvas sayfalarinda inspector gibi davranir, canvas'i ezmez.
- 1280 px altinda collapsible veya overlay olabilir.
- Panel icinde yatay scroll olmamalidir.

## Canvas Sayfalari Standardi

- Canvas ana odaktir.
- Ust command bar compact olmalidir.
- Sol arac cubugu ikon agirlikli ve dar olmalidir.
- Alt renk paleti/dock canvas'i kapatmaz.
- Secim kutusu, handle, olcu etiketi ve guvenli alan standartlasir.
- Etiket Studio ve Isim Kesim farkli is yapar; fakat canvas ergonomisi ortak kalir.

## Operasyon Sayfalari Standardi

- Gereksiz max-width yok.
- Main content `min-width: 0` davranisini korur.
- Buyuk tablolar sadece kendi bolumlerinde yatay scroll alabilir.
- Kritik aksiyonlar her zaman gorunur kalir.
- Stepper veya tabs ile aktif is odagi korunur.

## Form / Ayar Sayfalari Standardi

- Form ve ayar ekranlari kontrollu max-width kullanabilir.
- API/entegrasyon/teknik ayarlar production operasyon ekranlarindan ayrilir.
- Kaydet/test/sifirla aksiyonlari net ve geri bildirimli olur.

## Status Badge Renkleri

- Hazir: yesil.
- Kontrol gerekli: turuncu.
- Hata / engel: kirmizi.
- Kanit / mesaj: mavi.
- Lazer / ozel uretim: mor.
- Uretime aktarildi: mor/mavi.
- Bekliyor: gri.

## Responsive Kurallar

- 1920x1080: ferah masaustu, sag panel acik olabilir.
- 1600x900: normal masaustu, compact spacing.
- 1366x768: detaylar collapse, kritik aksiyonlar gorunur.
- 1280 px: sag panel overlay/collapsible olabilir; tablolar kendi icinde scroll alir.
- Kullanici browser zoom'unu kucultmek zorunda kalmamalidir.
