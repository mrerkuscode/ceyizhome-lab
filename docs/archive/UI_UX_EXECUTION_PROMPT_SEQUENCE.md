# UI/UX Execution Prompt Sequence

## 2026-05-16 Güncel Sıra

Tamamlanan promptlar:

1. Global Layout Stability and Design System Guard
2. Etiket Studio Corel Compact Final UI
3. Toplu Etiket Gallery UX Final
4. Print Queue Final UI/UX
5. Label Outputs Customer Gallery Final
6. Label Models Catalog Polish
7. New Model Wizard True Step Final

Sıradaki uygulanabilir promptlar:

1. User Onboarding and Technical Visibility
2. Final Manual Visual QA and Release Package
3. RDWorks Name Cutting Advanced Production Quality

Tarih: 2026-05-13

Bu dosya Agent modunda sirayla verilecek uygulanabilir prompt taslaklarini icerir.

## Prompt 1 - Clean Demo Data and Customer-Facing Defaults

Amaç: Queue, Outputs ve Ana Sayfa'da normal kullaniciya ilk acilista temiz musteri verisi gostermek.  
Kapsam: Queue, Etiket Ciktilari, Ana Sayfa son isler.  
Guvenlik: PDF/PNG, validation ve queue zinciri bozulmayacak; test/QA kayitlari silinmeyecek, sadece arşiv/filtre ayrimi yapilacak.  
Testler: `verify_print_queue_flow.py`, `verify_outputs_gallery_flow.py`, `real_production_quality_gate.py`, `final_acceptance_gate.py`.  
Rapor: `CLEAN_DEMO_DATA_AND_CUSTOMER_DEFAULTS_REPORT.md`  
Kabul: Varsayilan ekranlarda preview'li, dogrulanmis musteri isleri one gelir; test/QA ve teknik raporlar ayri gorunur.

## Prompt 2 - Bulk Label Gallery Viewport and Long Name Polish

Amaç: 100 satir Excel galerisini rahat taranabilir hale getirmek ve uzun isim preview tasmasini bitirmek.  
Kapsam: Toplu Etiket galeri, edit modal, sag detay paneli.  
Guvenlik: Hatalı/silinen satirlar uretilmeyecek; batch manifest ve queue korunacak.  
Testler: `verify_bulk_gallery_excel_flow.py`, yeni 100 satir fixture, screenshot capture.  
Rapor: `BULK_LABEL_UI_UX_FINAL_POLISH_REPORT.md`  
Kabul: 100 satirda kartlar okunur, uzun isimler sigar, modal Kaydet/Vazgec/Sil her zaman gorunur.

## Prompt 3 - Studio Sticky Output and Compact Inspector

Amaç: Etiket Studio'da canvas odagini korurken output aksiyonlarini her zaman erisilebilir yapmak.  
Kapsam: Studio property bar, sol toolbar, sag inspector, output controls.  
Guvenlik: Drag/resize/zoom/PDF payload bozulmayacak.  
Testler: `verify_corel_editor_interactions.py`, `verify_corel_undo_redo.py`, `pytest`, screenshot capture.  
Rapor: `STUDIO_STICKY_OUTPUT_AND_INSPECTOR_POLISH_REPORT.md`  
Kabul: 1366x768 ve 1920x1080 screenshotlarda output aksiyonlari kaybolmaz, canvas eski form gorunumune donmez.

## Prompt 4 - New Model Wizard True Step Flow

Amaç: Yeni Model Ekle modalini tek aktif adimli, ferah bir wizard haline getirmek.  
Kapsam: Yeni Model modal/wizard, image upload, oran kontrolu, kaydet sonrasi Studio akisi.  
Guvenlik: Config degisirse backup alinacak; kaynak AI/CDR degismeyecek.  
Testler: `verify_new_model_wizard.py`, `pytest`, screenshot capture.  
Rapor: `NEW_MODEL_TRUE_WIZARD_UI_UX_REPORT.md`  
Kabul: Footer kesilmez; teknik editor acilmaz; yeni model listede ve Studio'da acilir.

## Prompt 5 - Queue and Outputs Premium Polish

Amaç: Yazdirma Sirasi ve Etiket Ciktilari ekranlarini final musteri/uretim kalitesine yaklastirmak.  
Kapsam: Queue list/detail, Outputs gallery/detail, preview placeholder, filters.  
Guvenlik: Direct print yok; stale/missing PDF yazdirilmaz.  
Testler: `verify_print_queue_flow.py`, `verify_outputs_gallery_flow.py`, quality gates.  
Rapor: `QUEUE_OUTPUTS_FINAL_UI_UX_POLISH_REPORT.md`  
Kabul: Problemli kayitlar ana gorunumu bozmaz; secili preview guvenilir; yazdir modal onayli calisir.

## Prompt 6 - Label Models Compact Catalog Polish

Amaç: Etiket Modelleri sayfasinda ilk viewport ekonomisini ve katalog hissini iyilestirmek.  
Kapsam: KPI, filtre, kart grid, sag detay paneli, Teknik Mod visibility.  
Guvenlik: selectedModel ve Studio route bozulmayacak.  
Testler: `verify_label_models_premium_flow.py`, screenshot capture.  
Rapor: `LABEL_MODELS_COMPACT_CATALOG_POLISH_REPORT.md`  
Kabul: Kartlar ve sag panel ilk viewportta daha fazla gorunur; bos beyaz preview yoktur.

## Prompt 7 - Global Design System Cleanup

Amaç: Button, card, input, badge, modal, tab ve empty state stillerini ortak token mantigina cekmek.  
Kapsam: CSS tokenlari ve ortak UI class'lari.  
Guvenlik: Davranis degismeyecek; sadece gorsel/stil temizligi.  
Testler: `node --check`, `pytest`, screenshot diff/manual QA.  
Rapor: `GLOBAL_DESIGN_SYSTEM_CLEANUP_REPORT.md`  
Kabul: Ayni tip butonlar sayfalar arasinda tutarli gorunur; status renkleri tek standarda iner.

## Prompt 8 - Help and Onboarding Upgrade

Amaç: Normal kullanicinin egitim almadan ilk etiketi uretebilmesini saglamak.  
Kapsam: Yardim, onboarding turu, hata cozum kartlari, shortcut panel.  
Guvenlik: Teknik terimler normal kullaniciya acilmayacak.  
Testler: `verify_help_system.py`, user journey test.  
Rapor: `HELP_ONBOARDING_FINAL_UI_UX_REPORT.md`  
Kabul: Kullanici model secme, Studio duzenleme, PDF/PNG alma ve queue'ya ekleme adimlarini yardimla takip edebilir.

## Prompt 9 - Final Visual QA and Real User Journey Gate

Amaç: Tum UI/UX polish sonrasinda insan gibi uc uca kabul testi.  
Kapsam: Ana Sayfa, Modeller, Studio, Bulk, Queue, Outputs, Wizard, Settings, Help.  
Guvenlik: Tum kesin sinirlar tekrar dogrulanacak.  
Testler: Tum verify scriptleri, `pytest`, quality gates, screenshot capture.  
Rapor: `FINAL_UI_UX_REAL_USER_ACCEPTANCE_REPORT.md`  
Kabul: P0/P1 yok; screenshotlar temiz; ana akislar normal kullaniciya verilebilir.

## Prompt 10 - RDWorks Name Cutting Separate Technical Phase

Amaç: Ana etiket MVP sonrasinda RDWorks true offset/path teknigini ayri fazda ele almak.  
Kapsam: Name cut export, offset engine PoC, DXF/SVG/PDF/manifest.  
Guvenlik: RDWorks/lazer otomatik acilmayacak; yeni dis bagimlilik manuel karar gerektirir.  
Testler: `verify_rdworks_name_cut_layout_export.py`, 50/100 isim fixture.  
Rapor: `RDWORKS_TRUE_OFFSET_TECHNICAL_PHASE_REPORT.md`  
Kabul: Ya gercek offset dogrulanir ya da risk acik ve kullaniciya gorunur kalir.
