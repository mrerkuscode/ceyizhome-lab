# PROJECT_CONTEXT — CeyizHome Lab / Cyzella Production Studio

> Bu dosya projenin genel baglamini anlatir. CLAUDE.md'den sonra okunur.
> Kaynak: README.md + CODEX manuelleri (LEAD_DEVELOPER, START_HERE, CURRENT_PRIORITY) + docs/PRODUCTION_SAFETY_RULES.md

## Proje Nedir

Cyzella Production Studio, kisiye ozel urun uretimi icin yerel Windows uzerinde calisan guvenli bir MVP otomasyon aracidir. Sistem yalnizca dosya ve rapor uretir: Excel okur, satirlari dogrular, PRINT/LASER hazirlik dosyalari ve CSV raporlari olusturur.

Kritik: Sistem CorelDRAW'u acmaz, yaziciyi calistirmaz, RDWorks'u acmaz ve lazeri baslatmaz. Sadece hazirlik dosyasi uretir; insan manuel kontrol edip yazdirir.

## Iki Katman

1. Guvenli uretim motoru (deterministik): Excel'i okur, zorunlu alanlari dogrular, PRINT / LASER_ENGRAVE / LASER_CUT / BOTH / NONE akislarini sabit kurallarla isler, dosya ve rapor uretir. Uretim icin tek gercek kaynak budur.
2. Intelligence / oneri katmani: Siparisleri analiz eder, uyari/oneri/inceleme nedeni uretir, belirsiz alanlarda insan kontrolu ister. Uretim verisini sessizce degistirmez, yazdirma/lazer baslatma yetkisi yoktur.

NEEDS_REVIEW goren hicbir siparis, Excel'de duzeltilmeden uretime alinmaz.

## Arayuz

Ana arayuz artik HTML/CSS/JS tabanli yerel arayuzdur (src/webui/), PySide6 ile acilir. Eski PySide widget arayuzu (run_desktop.bat) yalnizca teknik yedek olarak durur. Bolumler: Genel Bakis, Excel, Kontrol, Etiket, Lazer, Raporlar, Ayarlar, Nasil Kullanirim.

Ana kullanici akisi: kisayola cift tikla, Excel sec, dry-run yap, hatalari duzelt, temizse etiket PDF/PNG ve lazer hazirlik dosyalarini uret, ciktilari uygulama icinden kontrol et.

## Onemli Akislar

- Etiket: Ana mod rulo etikettir; her PDF sayfasi tek bir etiket olcusundedir. JSON sablonlar templates/designs/ icinde. Etiket Studio'da yazi alani ekleme, drag/resize, font/renk/hizalama duzenleme yapilir; render motoru PDF/PNG uretir.
- Lazer: Isler plaka bazli SVG yerlesimleri olarak uretilir. LASER_CUT icin bagli el yazisi fontu (assets/fonts/connected_script.ttf) zorunlu; yoksa is bloklanir ve errors_report.csv'ye yazilir.
- Isim Kesim / RDWorks: DXF birincil export formati, SVG ikincildir. Katman renkleri sabit (kirmizi kesim, mavi destek, mor taban, yesil kalibrasyon, gri kilavuz).
- Trendyol: Siparisler kanit (soru/mesaj) ve kullanici dogrulamasi olmadan uretime aktarilmaz. Belirsiz veri needs_review kalir.

## Excel Semasi (ozet)

Final kolonlar: order_no, buyer_name, product_name, model_no, template_no, process_type, personalization_type, label_variant, label_text, laser_text, quantity, material_type, material_thickness_mm, extra_chocolate_qty, extra_madlen_qty, production_note, needs_review, status.

Gecerli degerler:
- process_type: PRINT, LASER_ENGRAVE, LASER_CUT, BOTH, NONE
- personalization_type: LABEL, NAME, LABEL_AND_NAME, NO_PERSONALIZATION
- label_variant: GOLD, SILVER, WHITE, RED, CUSTOM, NONE
- status: NEW, READY, NEEDS_REVIEW, COMPLETED, CANCELLED

## Klasor Mantigi

- Baski sablonlari (kaynak): templates/print/ icindeki CDR/AI/PDF/SVG
- Etiket ciktilari (uretilmis): output/YYYY-MM-DD/print/
- Lazer ciktilari: output/YYYY-MM-DD/laser/
- Raporlar: output/YYYY-MM-DD/reports/
- Loglar: output/YYYY-MM-DD/logs/app.log

## Guvenlik Ozeti

Asla otomatik: yazici, lazer, RDWorks, CorelDRAW, Illustrator, direct print. Asla overwrite: kaynak AI/CDR ve kullanicinin orijinal tasarim dosyalari. Sahte success sayilmaz; gercek cikti dosyasi yoksa is hazir sayilmaz. Detaylar icin FORBIDDEN.md ve docs/PRODUCTION_SAFETY_RULES.md.

## Ilgili Dosyalar

- CLAUDE.md — ana giris
- WORKFLOW.md — multi-Claude / multi-tool calisma deseni
- FORBIDDEN.md — yasak alanlar
- ACTIVE_SPRINT.md — aktif sprint durumu
- README.md — detayli teknik dokumantasyon
- CODEX_LEAD_DEVELOPER_MANUAL.md, START_HERE_FOR_CODEX.md, CODEX_CURRENT_PRIORITY.md — Codex rehberleri
