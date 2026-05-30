# SKILL: Mockup Generator (Web Claude)

> Web Claude'un INCELEME amacli HTML/CSS/JS mockup uretme becerisi.
> Bagimli dosyalar: PROJECT_CONTEXT.md (arayuz = HTML/CSS/JS + PySide6), FORBIDDEN.md (yeni framework YOK).
> Mockup uretim degildir; karar/onay aracidir.

## NE ZAMAN KULLANILIR
- Yeni UI bolumu/duzeni Code'a yaptirilmadan once gozle gorulecekse.
- Layout veya etkilesim fikri hizli denenecekse.
- Leyla'dan tasarim onayi alinacaksa.

## KURALLAR
- SADECE vanilla HTML + CSS + JS. Bootstrap / Tailwind / React / Vue YASAK (FORBIDDEN).
- Mevcut src/webui/ stiline yakin dur; yeni bagimlilik / build adimi ekleme.
- Tek .html dosyasi tercih et (inline <style> + <script>) -> kolay incelenir.
- Gercek veri, gercek Excel, gercek render, gercek queue BAGLAMA. Statik ornek veri kullan.
- Turkce karakter UTF-8, BOM yok.

## CIKTI FORMATI
- Tek HTML dosyasi.
- En ustte yorum: amac + hangi bolum + "MOCKUP - URETIM DEGIL".
- Calismayan butonlar net isaretli (disabled veya "ornek" etiketi).

```html
<!-- MOCKUP - URETIM DEGIL. Bolum: Etiket Studio yeni panel. Gercek veri baglanmadi. -->
<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><style>/* inline */</style></head>
<body><!-- statik ornek veri --></body>
<script>/* inline, sadece gosterim */</script></html>
```

## ANTI-PATTERN (kacin)
- Tailwind class'i veya CDN linki koymak -> FORBIDDEN ihlali.
- React/JSX component yazmak.
- Mockup'a gercek output/ veya Excel baglamak.
- Mockup'i "uretime hazir" sunmak -> sahte basari.
- Cok dosyali, npm/build gerektiren yapi -> inceleme zorlasir.

## TESLIM
Mockup onaylaninca, Code'a "bunu src/webui'ye gercek bagla" prompt'unu
SKILL_PROMPT_WRITER kalibiyla yaz. Mockup -> kod gecisi tek adimda yapilmaz; once onay.
