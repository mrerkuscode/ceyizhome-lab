# Rulo Yerleşim Görsel Önizleme Raporu

## Görev

Toplu Etiket ekranındaki rulo yerleşim bilgisini sadece metin satırlarıyla bırakmadan, normal kullanıcının üretimden önce satır kapasitesini ve taşma riskini hızlıca anlayacağı küçük bir görsel simülasyona dönüştürmek.

## Mevcut Sorun

Rulo bilgisi daha önce etiket ölçüsü, rulo genişliği ve toplam adet olarak metinsel görünüyordu. Bu üretim açısından doğruydu, ancak kullanıcı “bu etiket ruloda nasıl dizilecek?” sorusunun cevabını tek bakışta alamıyordu.

## Yapılan Düzeltme

- `src/webui/app.js` içine `rollLayoutVisualHtml` eklendi.
- `updateRollLayoutPreview` artık rulo ölçülerinden görsel bir satır simülasyonu üretir.
- Simülasyon gerçek `labelDefaults`, toplam sipariş adedi, etiket ölçüsü, rulo genişliği ve aralık değerlerinden beslenir.
- Taşma varsa görsel kart kırmızı uyarı tonuna geçer.
- Taşma yoksa kart güvenli üretim tonunda görünür.
- `src/webui/styles.css` içinde rulo görsel kartı, satır şeridi, mini etiket blokları ve meta alanları tasarlandı.
- `tests/test_mvp_safety.py` içinde rulo görsel önizleme fonksiyonu ve CSS sınıfları için regression kontrolü eklendi.
- Ek turda toplam satır sayısı, son satırdaki etiket adedi ve varsa boş slot bilgisi eklendi.

## UI/UX Etkisi

Toplu Etiket kullanıcısı artık rulo batch öncesinde:

- Etiketin rulo genişliğine sığıp sığmadığını,
- Satır başına yaklaşık kaç etiket geleceğini,
- Toplam adet bilgisini,
- Toplam kaç satır gerekeceğini,
- Son satırda kaç etiket ve kaç boş yer kalacağını,
- Taşma riskini

daha hızlı okuyabiliyor.

## Render / Output / Queue Etkisi

PDF/PNG render zincirine, output validation sistemine ve yazdırma sırası akışına dokunulmadı. Değişiklik sadece Toplu Etiket rulo bilgilendirme UI katmanındadır.

## Güvenlik Etkisi

- Direct print açılmadı.
- Yazıcı, lazer, RDWorks, CorelDRAW veya Illustrator çağrılmadı.
- Kaynak AI/CDR dosyalarına dokunulmadı.
- Mock veri gösterilmedi; kart mevcut state ve ayarlardan hesaplanıyor.

## Testler

Çalıştırılan komutlar:

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest`: `110 passed`.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\label_models_real_click_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\studio_canvas_interaction_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: geçti.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`: geçti.

Ek doğrulama turu:

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: `110 passed`.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\label_models_real_click_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\studio_canvas_interaction_gate.py`: PASSED.
- Screenshot scriptleri tekrar geçti.

## Screenshot Yolları

- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-08\ui_screenshots\toplu_etiket.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-08\quality_gate`

## Kalan Riskler

Bu iyileştirme tek satırlı özet simülasyondur. Çok büyük adetlerde sayfa sayfa rulo kırılımı veya fire hesabı daha ayrıntılı bir P3 işi olarak roadmap’te tutulmalıdır.

## P0/P1 Durumu

Bu görevde P0/P1 hata görülmedi. Mevcut kalite kapıları tekrar geçti.
