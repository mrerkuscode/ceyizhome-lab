# RDWorks Export Standardi

Bu proje RDWorks icin dogrudan lazer calistirmaz. Cyzella sadece uretime hazir dosya paketini hazirlar; kullanici dosyayi RDWorks'te manuel acar, layer ayarlarini kontrol eder ve kesimi kendisi baslatir.

## Ana Hedef

Isim kesim paketi su mantikla hazirlanir:

1. Excel veya manuel giristen isimleri al.
2. Isimleri duzelt: `ayse omer` -> `Ayse Omer` veya desteklenen Turkce duzeltmelerle `Ayse Omer` yerine `Ayse/Omer` karakterleri korunarak formatla.
3. Script/el yazisi fontla olustur.
4. Isimleri istenen olcuye gore boyutlandir.
5. Mumkunse text'i path/curve/outline'a cevir.
6. Kesim icin gercek vektor offset/kalinlastirma uygula.
7. 50-100 ismi calisma alanina fire azaltacak sekilde diz.
8. Kesim layer'larini RDWorks renk mantigina gore renklendir.
9. RDWorks icin DXF birincil dosyasini hazirla.
10. Kullaniciya RDWorks'te manuel kontrol mesaji goster.

## Export Onceligi

Birincil RDWorks dosyasi: `DXF`

Ikincil / yardimci ciktılar:
- `SVG` ara format veya teknik kontrol icin kullanilabilir.
- `PDF` kullanici kontrol onizlemesidir.
- `PNG` program ici onizlemedir.
- `JSON` teknik manifesttir.

RDWorks tarafinda SVG destegi garanti kabul edilmez. Kullaniciya final dosya olarak `DXF hazirlandi` denmelidir.

## RDWorks Layer / Renk Standardi

RDWorks renk/layer bazli calisir. Export dosyasinda renkler su amacla kullanilir:

- Kirmizi: Ana kesim cizgisi (`CUT_NAME_OUTLINE`)
- Mavi: Alt destek cizgisi (`CUT_SUPPORT_LINE`)
- Mor: Taban/plaka cizgisi (`CUT_BACK_PLATE`)
- Yesil: Kalibrasyon / registration (`CALIBRATION`)
- Gri: Kilavuz / preview (`GUIDE_PREVIEW`)

Cyzella hiz/guc gibi makine parametrelerini kesin ayar olarak gondermez. Kullanici RDWorks icinde layer renklerine gore hiz/guc/kesim modunu manuel ayarlar.

## Text To Path / Outline

Isimler RDWorks'e text/font olarak kalirsa font bagimliligi dogar. Hedef:

`Text -> path/curve/outline -> offset/thicken -> cut path`

Guncel durum:

- FontTools ile font contour okunur ve SVG tarafinda `path`, DXF tarafinda `POLYLINE` olarak export edilir.
- Manifest basarili durumda `OUTLINED_PATHS_WITH_FONTTOOLS` yazar.
- Font contour uretilmezse guvenli fallback `P1_RISK_TEXT_NOT_OUTLINED` olarak raporlanir ve kullanici RDWorks'te manuel font/path kontrolu yapar.

## Kalinlastirma / Offset

Kalinlastirma sadece ekranda gorunen stroke olmamali. Hedef, RDWorks'e giden vektor geometrisinde gercek offset/outline uygulanmasidir.

Guncel durum:

- Offset istenen isimlerde contour noktalarina yaklasik disa genisletme uygulanir.
- Bu, stroke-only preview degildir; export geometrisine yansir.
- Fakat bu henuz tam boolean/geometrik offset motoru degildir.
- Rapor `P1_RISK_APPROX_CONTOUR_EXPANSION_NOT_TRUE_OFFSET` olarak yazilir.
- Kullaniciya RDWorks'te outline/offset kontrolu yapmasi soylenir.

## Guvenlik

Asla otomatik yapilmayacaklar:

- RDWorks acma
- Lazer baslatma
- Direct print acma
- Yaziciyi sessiz calistirma
- CorelDRAW / Illustrator acma
- Kaynak AI/CDR dosyasini degistirme

Program sadece dosyalari hazirlar ve klasorde gosterebilir.
