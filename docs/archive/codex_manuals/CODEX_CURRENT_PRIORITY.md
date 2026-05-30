# Codex Current Priority

Updated: 2026-05-17

## Completed Last

- Trendyol soru/mesaj kaniti dayanikliligi guclendirildi.
- Manuel `Sorulari Oku` artik bekleyen ve cevaplanmis soru durumlarini birlikte okur, dedupe eder ve sadece read-only kanit olarak saklar.
- Trendyol soru servisi kapaliysa son deneme durumu ve temizlenmis hata mesaji yerel ayarlara yazilir; UI artik bunu "kanit yok/servis yanit vermiyor" olarak acik gosterir.
- Trendyol hizli filtrelerine `Kanit Bekliyor` ve `Onay Bekliyor` eklendi.
- Trendyol katalog eslestirme onerileri iyilestirildi: kisisellestirilmis etiket/cikolata/soz/nisan urunleri `label` onerisiyle review'a dusuyor.
- Canli katalog onerileri yeniden olusturuldu: 332 onerinin 327'si `label`, 3'u `label_and_name_cut`, 2'si `review`; hepsi kullanici onayi bekliyor.
- Trendyol katalog onerileri operator kullanimi icin aranabilir/filtrelenebilir hale getirildi.
- Etiket uretimi icin model secilmeden katalog onerisi artik onaylanmaz; UI oneriyi forma alir ve model sectirir, backend de `NEEDS_MODEL` ile korur.
- Urun eslestirme kaydindan sonra siparis paneline donme aksiyonu eklendi.
- Live Trendyol safe rehearsal was run.
- Trendyol connection succeeded and recent orders generated 160 review suggestions.
- Trendyol question/message service returned `HTTP 556 Service Unavailable`; Cyzella correctly kept all rows in `kanit_bekliyor`.
- Ready export and direct import were blocked because no row had question evidence + user verification.
- Trendyol soru kanitli uretim onay akisi tamamlandi.
- Trendyol satirlari artik soru/mesaj kaniti ve kullanici dogrulamasi olmadan uretime aktarilmaz.
- Trendyol urun gorselleri yerel onbellek/preview akisi ile eslestirme panelinde gosterilir.
- Etiket Studio icin Hizli Uretim / Gelismis Duzenleme modu eklendi ve layout stabilite kapisi gecildi.
- Etiket Modelleri, Toplu Etiket, Etiket Ciktilari ve Yazdirma Sirasi kompakt UI gecisi dogrulandi.
- Atolye operasyonu, musteri siparisi, RDWorks isim kesim, birlesik Excel uretim, yeni model wizard, onboarding, release paketi ve tasarim sistemi testleri gecti.
- PDF/PNG render, output validation ve queue zinciri kalite kapilarindan gecti.

## Current Status

Known P0: none.

Known P1: none in the verified local gates.

Live marketplace note: Trendyol gercek siparislerinde soru/mesaj servisi gecici olarak yanit vermezse sistem musteri adi veya urun basligindan tahmin edilen veriyi uretime almaz.

## Kalıcı Gerçek Kullanıcı Test Kilidi

- Rapor `PASSED` yazsa bile gerçek kullanıcı akışı test edilir.
- P0/P1 kalırsa görev bitmiş sayılmaz.
- Buton görünüyorsa tıklanır; sessiz kalıyorsa hata sayılır.
- Drag, resize, PDF/PNG, queue ve yazdırma onay akışı gerçek davranışla doğrulanır.
- Kısa `test` komutu için kalıcı gerçek kullanıcı kapısı: `scripts/run_test_command_real_user_qa.py`.
- Studio mouse/drag/resize kilidi: `scripts/studio_canvas_interaction_gate.py`.
- Etiket Modelleri gerçek tıklama kilidi: `scripts/label_models_real_click_gate.py`.

## Next 3 Priorities

1. Kullanici testi: Trendyol > Urun Eslestirme tabinda arama/filtre ile 5-10 gercek urunu model veya isim kesim tipiyle eslestirmek.
2. Kullanici testi: Trendyol > Siparisler tabinda soru kaniti gorunen bir satiri `Bu metinden alanlari kullan` > `Onayla ve Uretime Hazir Yap` > `Uretime Aktar` akisiyle denemek.
3. Kullanici testi: Aktarilan satiri Studio/Toplu Etiket/Isim Kesim akisi ve PDF/PNG/Queue zincirinde gercek gozle kontrol etmek.

## Commands Passed In Latest Pass

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m pytest tests\test_trendyol_order_to_production.py -q`
- `.venv\Scripts\python.exe scripts\verify_trendyol_order_to_production_flow.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_mapping_review_workflow.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_live_mapping_readiness.py`
- Trendyol final operator handoff checks: model secilmeden katalog onerisi onayi engellendi.
- Live catalog proposal refresh: 332 suggestions, 327 label, 3 label_and_name_cut, 2 review.
- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe scripts\verify_studio_layout_stability.py`
- `.venv\Scripts\python.exe scripts\verify_corel_editor_interactions.py`
- `.venv\Scripts\python.exe scripts\verify_corel_undo_redo.py`
- `.venv\Scripts\python.exe scripts\verify_label_models_premium_flow.py`
- `.venv\Scripts\python.exe scripts\verify_bulk_gallery_excel_flow.py`
- `.venv\Scripts\python.exe scripts\verify_outputs_gallery_flow.py`
- `.venv\Scripts\python.exe scripts\verify_print_queue_flow.py`
- `.venv\Scripts\python.exe scripts\verify_clean_customer_demo_flow.py`
- `.venv\Scripts\python.exe scripts\verify_workshop_operations_flow.py`
- `.venv\Scripts\python.exe scripts\verify_customer_order_flow.py`
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py`
- `.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py`
- `.venv\Scripts\python.exe scripts\verify_new_model_wizard.py`
- `.venv\Scripts\python.exe scripts\verify_design_system_consistency.py`
- `.venv\Scripts\python.exe scripts\verify_user_onboarding_and_technical_visibility.py`
- `.venv\Scripts\python.exe scripts\verify_release_package.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_order_to_production_flow.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_mapping_review_workflow.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_live_mapping_readiness.py`
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`
- Live safe sync: `output/2026-05-17/trendyol_live_rehearsal/trendyol_live_safe_sync_summary.json`
- Live safe blocking check: `output/2026-05-17/trendyol_live_rehearsal/trendyol_live_safe_blocking_check.json`

## Safety Confirmation

- RDWorks not opened.
- Laser not started.
- Direct print not enabled.
- Printer not started silently.
- CorelDRAW / Illustrator not opened.
- Source AI/CDR files not changed.
- Old Trendyol project `C:\Users\Pc\Desktop\mucoxai1` not modified.
