LASER_CUT font talimati

RDWorks / Isim Kesim icin varsayilan proje fontu:

- assets/fonts/MocharyTRConnect-Regular.otf
- assets/fonts/MocharyTRConnect-Regular.ttf

Mochary TR Connect, CeyizHome Lab icin uretilen ozgun ve proje icinden yuklenen
fonttur. Sistem font klasorune otomatik kurulum yapilmaz. Isim Kesim path
uretimi bu fontu FontTools ile outline/path'e cevirir; SVG export font
bagimliligi veya <text> elementi tasimamali.

Geriye uyumlu eski adaylar:

- assets/fonts/Mochary Personal Use Only.ttf
- assets/fonts/Mochary-Personal-Use-Only.ttf
- assets/fonts/Mochary.ttf

Mochary TR Connect bulunamazsa sistem eski Mochary / Mochary-like fallback
adaylarini kullanabilir ve durum rapora/manifest'e yazilir. Eksik font veya
path uretim hatasinda sahte basari verilmez; kayit needs_review olarak
isaretlenmelidir.

LASER_CUT kurallari:

- Harfler path/outline olarak export edilir.
- Turkce karakterler desteklenmelidir.
- Farkli isimler birbirine baglanmaz.
- Lazer, RDWorks ve yazici otomatik baslatilmaz.
- Grid, ruler, safe margin, selection ve handle katmanlari export'a girmez.
