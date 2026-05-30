# SKILL: Context Limit Auto-Handoff

> Sohbet context'i dolmadan, KONUSMAYI UNUTMADAN yeni sohbete temiz devir.
> Bagimli dosyalar: CLAUDE.md (giris), ACTIVE_SPRINT.md (durum kaynagi).
> Amac: gecmisi kaybetmeden, fakat token israf etmeden devam etmek.

## NEDEN GEREKLI
Uzun sohbette context dolar; model erken kisimlari unutmaya baslar
(yavaslama, tekrar, eski detayi kaybetme). Cozum: DOLMADAN once "su anki an"i
ozetleyip yeni sohbete tasimak. Knowledge'daki 5 .md zaten kalici baglam verir,
bu yuzden yeni sohbete sadece ANLIK durum aktarilir.

## NE ZAMAN DEVRET
- Cevaplar yavaslar, tekrara duser veya erken detayi unutursa.
- Buyuk bir gorev bitti, yeni buyuk goreve geciliyorsa.
- Web Claude context'in dolmaya basladigini sezerse -> Leyla'ya devir sablonunu HAZIR verir.
  Yani devri kullanici hatirlamadan once Web Claude onerir.

## DEVIR SABLONU (kullanici yeni sohbete yapistirir)
```
Önceki sohbetten devam:
DURUM:
- Branch: [X]
- Son commit: [hash]
- Test: [N/N PASS]
- MVP: [%X]
SON YAPILANLAR (son 3):
1. ...
2. ...
3. ...
DEVAM EDEN İŞ (varsa):
- [İş adı] - [durum]
SIRADAKİ:
- [Plan]
NOT: Knowledge'daki 5 .md zaten bağlam veriyor, sadece 'şu anki an'ı bil yeter.
```

## NASIL DOLDURULUR (kanit-temelli)
- Branch / commit / test / MVP: ACTIVE_SPRINT.md veya Code'dan GUNCEL cek; hatirdan yazma.
- "Son yapilanlar": bu sohbette GERCEKTEN biten isler (sahte ilerleme yazma).
- "Devam eden": yarim kalan tek is + durumu.
- "Siradaki": tek net adim.

## ANTI-PATTERN (kacin)
- Tum sohbet gecmisini yeni sohbete yapistirmak -> token israfi.
- 5 .md dosyasini tekrar yapistirmak -> zaten Knowledge'da yuklu.
- Durumu hatirdan yazmak (eski hash/test) -> guncel degeri cek.
- "Devam edelim" deyip ne yapildigini yazmamak -> yeni sohbet baglamsiz baslar.
- Bitmemis isi "bitti" gostermek -> sahte basari, sonraki sohbet yanlis ilerler.
- Devri cok gec onermek (context coktan dolmus) -> erken sezip uyar.

## CIKTI
Doldurulmus sablon + tek satir: "Yeni sohbette yapistir; 5 .md otomatik yuklenecek, gerisini bu ozet verir."
