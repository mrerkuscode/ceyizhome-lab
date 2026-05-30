# FORBIDDEN — Yasak Alanlar ve Onay Gerektirenler

> Bu dosya projede ASLA otomatik yapilmamasi gereken islemleri ve insan onayi gerektiren riskli aksiyonlari listeler.
> Kaynak: docs/PRODUCTION_SAFETY_RULES.md + CLAUDE.md + START_HERE_FOR_CODEX.md + CODEX_LEAD_DEVELOPER_MANUAL.md

## ASLA Otomatik Yapma (Hard Yasak)

Bu islemler hicbir kosulda otomatik tetiklenmez:

- Yaziciyi calistirmak / direct print acmak.
- Lazeri baslatmak.
- RDWorks'u acmak veya otomasyona baglamak.
- CorelDRAW veya Illustrator'i otomatik acmak.
- Kaynak AI/CDR dosyalarini degistirmek veya overwrite etmek.
- Kullanicinin orijinal tasarim dosyalarini overwrite etmek.
- Trendyol canli statu, kargo ve fatura islemlerini otomatik tetiklemek.
- Eski Trendyol projesini (C:\Users\Pc\Desktop\mucoxai1) degistirmek.
- API secret / token'i log, audit, export veya screenshot icine duz metin olarak dusurmek.

## Sahte Basari Yasak

Su durumlar "hazir/basarili" sayilmaz:

- Gercek cikti dosyasi yoksa kayit "cikti hazir" veya "yazdirmaya hazir" sayilmaz.
- Toast cikti ama gercek islem olmadi.
- PDF olustu ama eski dosya; PNG olustu ama background yok.
- Queue'ya yanlis veya stale dosya eklendi.
- Test sadece "buton var mi" diye bakti.
- Handle gorunuyor ama drag/resize gercekten calismiyor.

## Veri Guvenligi Yasaklari

- Kisisellestirme alani kanit olmadan uydurulmaz.
- Urun basligindan isim/tarih/not/lazer isim cikarimi kesin veri gibi kullanilmaz; belirsizse needs_review kalir.
- NEEDS_REVIEW siparis Excel'de duzeltilmeden uretime alinmaz.
- Path traversal engellenir; proje klasoru disina dosya cikarilamaz.
- Corrupt JSON restore edilmez; restore oncesi otomatik snapshot alinir.
- ZIP/sablon paketinde .exe/.bat/.cmd/.ps1/.py calistirilmaz veya kopyalanmaz.

## Isim Kesim / Lazer Yasaklari

- LASER_CUT bagli el yazisi (connected script) font yoksa veya guvenli vektor dogrulanamiyorsa is bloklanir; yanlis kesim SVG'si uretilmez.
- Tek parca/weld kontrolunden gecmeyen, detached mark iceren veya collision riski olan kayit export edilmez.
- needs_offset kayitlari operator onayi olmadan export edilmez.
- RDWorks katman renkleri sabittir; degistirilmez.

## Insan Onayi Gerektirenler (Manuel Karar)

Asagidakiler otomatik yapilmaz. Dur, rapora "manuel karar gerekir" yaz ve insan onayi bekle:

- Direct print acmak veya yaziciyi otomatik calistirma onayi.
- Lazer / RDWorks otomasyonu baglamak.
- Corel/Illustrator native edit'i uretim akisina almak.
- Kaynak AI/CDR dosyasini degistirmek.
- Buyuk mimari refactor.
- Yeni framework veya buyuk teknoloji eklemek (Bootstrap, Tailwind, React, FastAPI vb. YOK).
- Master flag kapali kodlara dokunmak (AI Glyph, Internal Corel vb.) YOK.
- Riskli aksiyon registry default disabled + dry-run only kalmali; canli aksiyon yonetici + operator onayi ister.

## Git Yasaklari

- git push --force YASAK.
- git reset --hard YASAK.
- Mevcut testleri silme/bozma YASAK; yeni test ekle, mevcutlari koru.
- Claude/Codex kendi PR'ini merge etmez; merge yetkisi insandadir.

## Hatirlatma

Suphede kal ve sor. Bu dosyadaki bir kurali esnetmen gerektigini dusunuyorsan, once insana danis. Guvenlik kurallari urun hedefinden once gelir.
