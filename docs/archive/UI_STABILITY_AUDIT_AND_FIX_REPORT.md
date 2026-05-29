# UI Stability Audit and Fix Report

Date: 2026-05-14

## Summary

Etiket Studio'da tekrar eden iki ana UI kararsızlığı incelendi ve düzeltildi:

- Ust property bar font/preset acilir kontrolleri canvas ve hizli uretim bandinin ustune tasiyordu.
- Etiket Studio bazi kosullarda sayfa scroll'una dusup ust bar, canvas ve inspector alaninin kayboluyormus gibi davranmasina yol aciyordu.

## Fixed Issues

1. Topbar dropdown tasmasi
   - Ust bardaki arac/font/preset kontrolleri artik menu acmiyor.
   - Bu kontroller sag dock sekmesine yonlendiriyor.
   - Font ailesi secimi `Yazi` dock icindeki kompakt chip grid'e tasindi.
   - Boylece font listesi canvasin, hizli uretim satirinin veya sag panelin ustune binmiyor.

2. Scroll / kaybolma guard'i
   - Etiket Studio viewport lock davranisi tekrar dogrulandi.
   - Regression testi artik `body`, `html`, `.main` scroll kilidini ve ust uygulama barinin gizlendigini kontrol ediyor.
   - Test artik sayfa scroll'u geri gelirse hata verecek.
   - Sag dock ve canvas icin wheel/scroll containment eklendi; sag panel scroll'u body/main scroll'una sizamiyor.
   - Regression testi sag dock wheel hareketinde panelin kendi icinde kaydigini, main/window scroll'unun 0 kaldigini dogruluyor.

3. Gelecekte ayni hatanin geri gelmesini engelleyen testler
   - Custom combo kontrollerinin ust barda menu acmamasi test edildi.
   - Font combo tiklaninca `Yazi` dock'unun acildigi test edildi.
   - Body/html scroll kilidi test kapsamına alindi.

4. Yazdir akisi
   - Yazdir butonu artik eksik veya stale PDF/PNG durumunda kullaniciyi yari yolda birakmiyor.
   - Guncel PDF/PNG otomatik hazirlanir, sonra ayni guvenli yazdirma onay modalina gecilir.
   - Direct/silent print davranisi kapali kaldi; kullanici onayi olmadan yazici calismaz.

## Changed Files

- `src/webui/index.html`
- `src/webui/app.js`
- `src/webui/styles.css`
- `scripts/verify_corel_editor_interactions.py`
- `tests/test_mvp_safety.py`

## Commands Run

- `node --check src\webui\app.js` - PASSED
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py -q` - PASSED, 120 tests
- `.venv\Scripts\python.exe scripts\verify_corel_editor_interactions.py` - PASSED
- `.venv\Scripts\python.exe scripts\print_action_real_user_gate.py` - PASSED
- `.venv\Scripts\python.exe -m pytest -q` - PASSED, 137 tests
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` - PASSED
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` - PASSED
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` - PASSED

## Screenshot Evidence

- `output/2026-05-14/ui_screenshots/manuel_etiket.png`
- `output/2026-05-14/ui_screenshots/etiket_studio_kompakt_genel.png`

## Remaining Watch Points

- Sag inspector ic scroll'u bilincli olarak kaldi; body/page scroll yerine sadece panel kendi icinde kayiyor.
- Ust bardaki font/preset butonlari artik secim menusu degil, sag dock kisayolu gibi calisir.
- Daha sonra istenirse font/preset secimi icin sag dock'ta daha zengin bir mini secici eklenebilir; ust barda acilir menu tekrar kullanilmamali.

## 2026-05-14 Print Click Flicker Root Cause Fix

User-reported issue:
- `Yazdir` tiklaninca Etiket Studio tekrar yanip sonuyordu.
- Sorun tekil dropdown/scroll degil, print aksiyonunun ara PDF/PNG uretirken Studio UI state'ini yeniden cizdirmesiydi.

Root cause:
- Missing/stale output durumunda `requestManualPrint()` otomatik `renderManual()` calistiriyordu.
- Normal `renderManual()` basarili olunca `showManualOutputActions(result)` ve `refreshState()` cagiriyordu.
- Bu iki cagri yazdir modalindan hemen once output panelini ve genel uygulama state'ini degistiriyor, Studio topbar/canvas/dock alaninda layout flash etkisi uretiyordu.
- `showManualPrintMessage()` de print sirasinda `manualOutputActions` icine yeni status satiri ekleyerek layout'u oynatabiliyordu.

Fix:
- Print'e ozel sessiz render yolu eklendi:
  - `silentPreflight: true`
  - `skipStateRefresh: true`
  - `skipOutputActions: true`
  - `inline: false`
- Print icin otomatik PDF/PNG uretilirken Studio paneli, output actions ve global state refresh artik degismiyor.
- Sadece `lastManualOutput` guncelleniyor ve guvenli `Yazdirmaya Hazir` modalina geciliyor.
- `showSafePrintConfirm()` modal acarken Studio scroll clamp tekrar uygulanir.

Regression guard:
- `scripts/print_action_real_user_gate.py` artik `Yazdir` tiklamasindan once/sonra Studio, topbar, canvas, dock ve scroll koordinatlarini olcer.
- Layout top/height degeri 2px'ten fazla oynarsa test fail olur.
- `manualOutputActions` icine print sirasinda inline status enjekte edilirse test fail olur.

Latest command results:
- `node --check src\webui\app.js` - PASSED
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py -q` - PASSED, 120 tests
- `.venv\Scripts\python.exe scripts\print_action_real_user_gate.py` - PASSED, includes `print_click_layout_stable`
- `.venv\Scripts\python.exe scripts\verify_corel_editor_interactions.py` - PASSED
- `.venv\Scripts\python.exe -m pytest -q` - PASSED, 137 tests
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` - PASSED
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` - PASSED
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` - PASSED

Evidence:
- Print gate screenshot: `output/2026-05-14/print_action_gate/safe_print_modal.png`
- Print gate screenshot: `output/2026-05-14/print_action_gate/queue_safe_print_modal.png`
- Latest UI screenshots: `output/2026-05-14/ui_screenshots/`
