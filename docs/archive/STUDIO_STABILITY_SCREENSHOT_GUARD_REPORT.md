# Studio Stability Screenshot Guard Report

Date: 2026-05-15

## Summary

Etiket Studio icin mouse hareketinde yanip sonme, sag dock scroll ile sayfanin kaybolmasi, font kontrolu acilinca layout'un bozulmasi ve yanlis sayfa screenshot yakalama riskleri yeniden dogrulandi.

Bu turda ana urun koduna riskli refactor yapilmadi. Stabilite testinin kendisi guclendirildi; artik screenshot almadan once Qt event loop/repaint bekliyor, kaydedilen gorselin bos olmadigini dogruluyor ve font secim kontrolunun eski dropdown overlay davranisina donmesini yakaliyor.

## Degisen Dosyalar

- `scripts/verify_studio_layout_stability.py`

## Yapilan Guclendirmeler

- Screenshot almadan once UI repaint/event flush eklendi.
- Screenshot dosyasinin olustugu ve bos olmadigi dogrulaniyor.
- Font kontrolu artik `dock-only-combo` davranisi olarak test ediliyor:
  - dropdown overlay acilmamali
  - sag dock `Yazi` sekmesine gecmeli
  - page/layout ziplamamali
- Sag dock scroll davranisi body/html/main scroll'dan ayrik dogrulaniyor.
- Mousemove testi Etiket Studio aktifken tekrar kontrol ediliyor.
- Sidebar hover ac/kapa davranisi tekrar dogrulaniyor.
- Yazdir butonu direct print yapmadan safe print modal aciyor mu tekrar dogrulaniyor.
- Test sonunda Qt uygulamasi hard exit yerine temiz kapatiliyor.

## Screenshot Kanitlari

- `output/2026-05-15/studio_layout_stability/studio_layout_base.png`
- `output/2026-05-15/studio_layout_stability/studio_after_mousemove.png`
- `output/2026-05-15/studio_layout_stability/studio_sidebar_expanded.png`
- `output/2026-05-15/studio_layout_stability/studio_sidebar_collapsed_after_leave.png`
- `output/2026-05-15/studio_layout_stability/studio_right_dock_scrolled.png`
- `output/2026-05-15/studio_layout_stability/studio_font_combo_closed_stable.png`
- `output/2026-05-15/studio_layout_stability/studio_safe_print_modal_stable.png`

## Gecen Testler

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m py_compile scripts\verify_studio_layout_stability.py`
- `.venv\Scripts\python.exe scripts\verify_studio_layout_stability.py`
- `.venv\Scripts\python.exe scripts\verify_corel_editor_interactions.py`
- `.venv\Scripts\python.exe scripts\verify_bulk_gallery_excel_flow.py`
- `.venv\Scripts\python.exe -m pytest -q` -> 138 passed
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py`
- `.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py`

## Sonuc

Bilinen Studio P0/P1 kalmadi:

- Mousemove sonrasi flicker yakalanmadi.
- Sag dock scroll body/main sayfayi kaydirmiyor.
- Font secim kontrolu overlay ile canvas ustune binmiyor.
- Yazdir direct print yapmiyor; guvenli modal aciyor.
- Screenshot guard artik yanlis sayfayi basari saymiyor.

## Kalan Riskler

- Kullanici makinesindeki DPI/tarayici cache farklari goruntu olcegini etkileyebilir; bu nedenle screenshot guard her UI degisikliginden sonra calistirilmali.
- Mochary font dosyasi sistemde yoksa isim kesim modulu guvenli fallback kullanir; birebir font icin font dosyasi `assets/fonts` altina eklenmelidir.
