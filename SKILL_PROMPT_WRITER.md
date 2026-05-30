# SKILL: Prompt Writer (Web Claude -> Code / Chrome)

> Web Claude'un baska araca devredilecek isi "uygulanabilir prompt" haline getirme becerisi.
> Bagimli dosyalar: WORKFLOW.md (roller), FORBIDDEN.md (yasaklar), ACTIVE_SPRINT.md (guncel durum).
> Bu dosya o dosyalari tekrar etmez; sadece prompt yazma kurallarini ekler.

## NE ZAMAN KULLANILIR
- Code'a kod / test / git gorevi devredilecekse.
- Chrome'a gorsel inceleme / click / PR gorevi devredilecekse.
- Bir isi baska Claude'a "ek soru sormadan yapabilecegi" netlikte aktarman gerekiyorsa.

## PROMPT ANATOMISI (7 zorunlu blok)
1. KIM    : Hedef arac (Code mi, Chrome mi).
2. HEDEF  : Tek cumlede ne istiyorsun.
3. BAGLAM : Hangi branch, hangi dosya, neden.
4. ADIMLAR: Sirali, kucuk, dogrulanabilir.
5. KABUL  : Ne olursa "bitti" sayilir (gercek cikti; sahte basari degil).
6. YASAK  : FORBIDDEN'dan ilgili madde (hatirlatma).
7. CIKTI  : branch adi + commit mesaji + PR/rapor formati.

## CODE ICIN SABLON
```
[KIM] Claude Code (terminal)
[HEDEF] <tek cumle>
[BRANCH] fix/<konu>   (main'e dogrudan push YOK)
[DOSYALAR] <yol/dosya>
[ADIMLAR]
1. ...
2. ...
[KABUL] pytest <N/N> PASS + node --check temiz + GERCEK cikti dosyasi var
[YASAK] git push --force / reset --hard YOK; src/server, bridge.py dokunma
[CIKTI] commit mesaji + PR aciklamasi: ne / neden / dosya / test / kalan risk
```

## CHROME ICIN SABLON
```
[KIM] Claude Chrome (tarayici)
[HEDEF] <tek cumle - gorsel/click/PR>
[ADRES] http://localhost:<port> / GitHub PR linki
[ADIMLAR]
1. <hangi tab/buton>
2. <hangi davranis: click / drag / resize>
[KABUL] gercek davranis dogrulandi + screenshot alindi (toast yeterli DEGIL)
[YASAK] kendi PR'ini merge etme; RDWorks/lazer/print tetikleme YOK
[CIKTI] screenshot + kisa gozlem raporu
```

## ANTI-PATTERN (kacin)
- "UI'yi duzelt" gibi belirsiz hedef -> hangi dosya, hangi davranis belli degil.
- KABUL kriteri yok -> arac "bitti" der, kanit yok.
- KABUL'u "toast cikti" diye yazmak -> sahte basari kapisi acik kalir.
- Branch belirtmeden "commit at" demek -> main kirlenir.
- FORBIDDEN maddesi atlamak (orn. auto_print/auto_laser'a dokunduran adim).
- Tek prompt'a 10 is yiymek -> arac kaybolur; isi bol, sirala.

## HIZLI KONTROL
Gondermeden once: 7 blok tam mi? KABUL gercek cikti mi olcuyor? Yasak hatirlatildi mi?
