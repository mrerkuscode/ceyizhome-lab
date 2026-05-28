# CeyizHome Lab Design Lab Raporu

Tarih: 2026-05-20

## Neden Design Lab?

Production sayfalari daha once dogrudan buyuk UI yamalari aldiginda layout ust uste binme, panel sikisma ve canvas daralmasi riski olustu. Bu nedenle yeni masaustu uygulama dili once izole `Design Lab` sayfasinda kuruldu.

## Eklenen Ekran

Web UI icinde yeni sayfa:

- `designLab`

Sol menude ANA altina `Design Lab` girisi eklendi.

## Design Lab Sekmeleri

- Genel Bakis
- Etiket Studio
- Trendyol
- Toplu Uretim
- Isim Kesim
- Yazdirma
- Modeller
- Manuel

## Referans Icerikleri

### Genel Bakis

CeyizHome Lab masaustu uygulama standardi, renk dili, modul akisi ve responsive olcek kuralini gosterir.

### Etiket Studio

Sade ust toolbar, model/olcu satiri, font toolbar, sol arac cubugu, buyuk canvas, sag Alanlar paneli ve alt kare renk paleti referansi olusturuldu.

### Trendyol

Metrik bar, toplu aksiyon bari, tablo-kart hibriti siparis satiri ve sag musteri kanit drawer referansi olusturuldu.

### Toplu Uretim

6 adimli stepper, filtre pilleri, galeri kartlari ve sag Uretim Ozeti paneli referansi olusturuldu.

### Isim Kesim

800x600 mm RDWorks hissi veren tabla, sol isim kaynagi, sag yerlesim paneli ve script outline isim yerlesimi referansi olusturuldu. Farkli isimleri baglamama kurali tasarim metninde korunur.

### Yazdirma / Modeller / Manuel

Yazdirma sirasi veri tablosu, model galerisi ve manuel etiket hizli form referanslari eklendi.

## Production'a Tasima Kurali

1. Once Design Lab ekrani onaylanir.
2. Production sayfada ayni layout parcalari kucuk adimlarla uygulanir.
3. Var olan API/hook/bridge fonksiyonlari silinmez.
4. Fonksiyonu olmayan buton production'da pasif kalir veya acik hata mesaji verir.
5. Her tasima adimi syntax, responsive ve gercek kullanim testiyle kapanir.

## Dosyalar

- `src/webui/index.html`
- `src/webui/styles.css`
- `src/webui/app.js`
- `scripts/verify_project_responsive_layout.py`

## Dogrulama

- `node --check src\webui\app.js`: PASSED
- `.venv\Scripts\python.exe -m py_compile src\desktop\web_main_window.py src\desktop\main_window.py scripts\verify_project_responsive_layout.py`: PASSED
- `.venv\Scripts\python.exe scripts\verify_project_responsive_layout.py`: PASSED
- `.venv\Scripts\python.exe -m pytest -q`: 189 PASSED
- `npm run test`: PASSED

Screenshot kanitlari:

- `output\2026-05-20\responsive_layout\designLab_1920.png`
- `output\2026-05-20\responsive_layout\designLab_1366.png`
