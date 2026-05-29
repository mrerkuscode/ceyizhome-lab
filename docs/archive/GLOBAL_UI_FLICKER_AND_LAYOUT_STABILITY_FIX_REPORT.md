# Global UI Flicker and Layout Stability Fix Report

## Görev

Kullanıcı gözleminde Etiket Modelleri ve genel sayfalarda mouse imleci hareket ettikçe sayfanın yanıp söndüğü, üst katmanların içerik üstüne bindiği ve sağ panelin dengesiz davrandığı görüldü.

## Kök Neden

- `topbar` sticky + blur katmanı olarak sayfanın üstünde kalıyordu.
- `model-health-summary` sticky + blur katmanı olarak scroll sırasında model kartlarının üstüne biniyordu.
- Etiket Modelleri sağ detay paneli nested scrollbar ve sticky aksiyon gridiyle içerik üstüne kayan ikinci bir katman oluşturuyordu.
- Çok sayıda kart/button hover durumunda `transform: translate...` kullanıyordu. Windows WebView/Qt render ortamında bu, blur katmanlarıyla birleşince mouse hareketinde gereksiz repaint/flicker hissi yaratıyordu.

## Değiştirilen Dosyalar

- `src/webui/styles.css`
- `tests/test_mvp_safety.py`

## Yapılan Düzeltmeler

- `topbar` sticky olmaktan çıkarıldı; artık içerik üstüne binmeyen statik bir başlık alanı.
- `model-health-summary` sticky olmaktan çıkarıldı; sağlık KPI kartları sayfa akışı içinde kalıyor.
- Kart, panel, modal ve Etiket Modelleri aksiyon gridinde pahalı `backdrop-filter` kullanımına final stability override eklendi.
- Hover sırasında layout/repaint tetikleyen translate transformları devre dışı bırakıldı; hover etkisi border/shadow/background ile korunuyor.
- Etiket Modelleri sağ detay panelindeki nested scrollbar kaldırıldı; panel sayfa akışıyla birlikte ilerliyor.
- Sağ panel aksiyon gridi sticky olmaktan çıkarıldı; içerik üstüne binme sorunu giderildi.
- Sol menüde `nav-btn:hover` kaynaklı yatay translate hareketi kapatıldı.
- Sol menüde `backdrop-filter` kapatıldı ve sidebar paint alanı izole edildi; mouse hareketinde tüm sayfanın tekrar boyanma riski azaltıldı.

## Korunan Akışlar

- PDF/PNG render zincirine dokunulmadı.
- Output validation ve queue sistemi değiştirilmedi.
- selectedModel, yeni model, görsel bağlama ve Studio geçiş akışları korunarak gerçek click gate ile doğrulandı.
- Etiket Studio drag/resize/keyboard etkileşimleri tekrar doğrulandı.

## Güncellenen Testler

- Etiket Modelleri testinde eski yanlış beklenti olan sticky aksiyon gridi yerine yeni stabilite beklentileri eklendi:
  - `topbar` statik
  - `model-health-summary` statik
  - Etiket Modelleri detail panel statik
  - Sticky action grid kapalı
  - Blur/transform stabilite guard mevcut
  - Sol menü hover transform kapalı
  - Sol menü blur kapalı ve paint containment aktif

## Çalıştırılan Komutlar

- `node --check src\webui\app.js` -> Passed
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py` -> 112 passed
- `.venv\Scripts\python.exe scripts\label_models_real_click_gate.py` -> PASSED
- `.venv\Scripts\python.exe scripts\studio_canvas_interaction_gate.py` -> PASSED
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` -> PASSED
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` -> PASSED
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` -> Passed
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py` -> Passed
- Sol menü stabilite düzeltmesi sonrası tekrar:
  - `node --check src\webui\app.js` -> Passed
  - `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py` -> 112 passed
  - `.venv\Scripts\python.exe scripts\label_models_real_click_gate.py` -> PASSED
  - `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` -> Passed

## Screenshot Kanıtları

- Etiket Modelleri: `output\2026-05-11\ui_screenshots\etiket_modelleri.png`
- Etiket Modelleri seçili kart + sağ panel: `output\2026-05-11\label_models_click_gate\label_models_selected_detail.png`
- Etiket Studio canlı canvas: `output\2026-05-11\ui_screenshots\manuel_etiket.png`
- Studio drag sonrası: `output\2026-05-11\studio_interaction\studio_drag_after.png`
- Studio resize sonrası: `output\2026-05-11\studio_interaction\studio_resize_after.png`

## Sonuç

P0/P1 flicker ve overlay riski giderildi. Sayfalar mouse hareketinde sticky blur katmanlarıyla üst üste binmeyecek şekilde stabilize edildi. Sol menü hover kaynaklı yanıp sönme riski de kapatıldı. Üretim zinciri, Etiket Modelleri click akışı ve Etiket Studio drag/resize davranışı testlerden geçti.

## Kalan Riskler

- Çok eski/çok düşük GPU sürücülerinde WebView repaint performansı ortam kaynaklı değişebilir; yeni CSS katmanı bu riski azaltmak için blur ve transform kaynaklı repaint yükünü düşürdü.
- Daha ileri iyileştirme olarak gerçek browser e2e görsel diff testi eklenebilir.
