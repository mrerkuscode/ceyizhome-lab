# Real User Testing System Setup Report

Tarih: 2026-05-10

## Görev

Cyzella Production Studio / Label Studio V1 için kalıcı “Gerçek Kullanıcı Test Standardı” oluşturuldu. Amaç, bundan sonra her geliştirmede sadece kod testi değil, gerçek kullanıcı akışı, gerçek click, gerçek pointer/mouse interaction, gerçek output validation ve screenshot QA standardını zorunlu hale getirmektir.

## Oluşturulan/Güncellenen Kalıcı QA Dosyaları

- `REAL_USER_TESTING_STANDARD.md`
- `HUMAN_QA_PROTOCOL.md`
- `INTERACTION_TESTING_GUIDE.md`
- `BUTTON_CLICK_TESTING_STANDARD.md`
- `VISUAL_SCREENSHOT_QA_GUIDE.md`
- `OUTPUT_VALIDATION_STANDARD.md`
- `CODEX_CURRENT_PRIORITY.md`
- `START_HERE_FOR_CODEX.md`

## Bundan Sonra Codex Her Görevde Nasıl Test Yapacak?

Her görevde önce `START_HERE_FOR_CODEX.md` içindeki zorunlu okuma listesi takip edilecek:

1. `PROJECT_MASTER_CONTEXT.md`
2. `CODEX_LEAD_DEVELOPER_MANUAL.md`
3. `REAL_USER_TESTING_STANDARD.md`
4. `HUMAN_QA_PROTOCOL.md`
5. `INTERACTION_TESTING_GUIDE.md`
6. `BUTTON_CLICK_TESTING_STANDARD.md`
7. `OUTPUT_VALIDATION_STANDARD.md`
8. `VISUAL_SCREENSHOT_QA_GUIDE.md`
9. `QA_ACCEPTANCE_CHECKLIST.md`
10. `CODEX_CURRENT_PRIORITY.md`

Kapanışta:

- Gerçek kullanıcı akışı test edilecek.
- Screenshot alınacak.
- Output validation gerekiyorsa çalıştırılacak.
- P0/P1 kalırsa görev bitmiş sayılmayacak.

## Gerçek Kullanıcı Testi Ne Demek?

Gerçek kullanıcı testi şu 4 kontrolü birlikte ister:

- Gerçek aksiyon çalışıyor mu?
- Ekranda beklenen değişiklik oluyor mu?
- State/backend/output doğru güncelleniyor mu?
- Screenshot veya dosya çıktısıyla kanıt var mı?

Sadece DOM’da buton görmek, sadece fonksiyon varlığını kontrol etmek veya sadece toast göstermek başarı sayılmayacak.

## Drag/Resize Nasıl Test Edilecek?

`INTERACTION_TESTING_GUIDE.md` standardına göre:

- Drag için `pointerdown`, `pointermove`, `pointerup` uygulanır ve field `x/y` değişimi doğrulanır.
- Corner resize için `width/height/font_size` değişimi doğrulanır.
- Side resize için `width/height` değişimi doğrulanır, `font_size` agresif değişmemelidir.
- Zoom testleri Ekrana Sığdır, %100, %150 ve %200 modlarında yapılır.
- Keyboard testleri Arrow, Shift+Arrow ve Alt+Arrow hareketlerini doğrular.
- PDF/PNG payload yeni geometry değerini taşımalıdır.

Bu projedeki mevcut kanıt scripti:

- `scripts/studio_canvas_interaction_gate.py`

## Butonlar Nasıl Test Edilecek?

`BUTTON_CLICK_TESTING_STANDARD.md` standardına göre:

- Buton gerçek click almalı.
- Beklenen route/screen/modal/state değişimi olmalı.
- `selectedModel` doğru taşınmalı.
- Console error olmamalı.
- Teknik editör yanlışlıkla açılmamalı.
- Sessiz kalan buton başarısız sayılmalı.

Bu projedeki mevcut kanıt scripti:

- `scripts/label_models_real_click_gate.py`

## Output Nasıl Doğrulanacak?

`OUTPUT_VALIDATION_STANDARD.md` standardına göre:

- PDF/PNG dosyası gerçekten oluşmalı.
- Dosya taze olmalı.
- Background görünmeli.
- İsim/Tarih/Not görünmeli.
- Sadece krem/bej placeholder output başarı sayılmamalı.
- PDF preview ve PNG preview son dosyayı göstermeli.
- Queue doğrulanmış batch PDF’i almalı.

Bu projedeki mevcut kanıt scriptleri:

- `scripts/real_production_quality_gate.py`
- `scripts/final_acceptance_gate.py`

## Screenshot QA Nasıl Yapılacak?

`VISUAL_SCREENSHOT_QA_GUIDE.md` standardına göre screenshot incelenecek:

- Boş ekran var mı?
- Butonlar görünür ve anlaşılır mı?
- Teknik detaylar normal kullanıcıya görünüyor mu?
- Kırık görsel veya taşan layout var mı?
- Türkçe karakterler doğru mu?
- Canvas ve PDF/PNG preview uyumlu mu?

Screenshot kötü görünüyorsa görev kapatılmayacak.

## Eklenen/Güncellenen Testler

`tests/test_mvp_safety.py` içine `test_real_user_testing_standards_are_persistent_project_rules` eklendi.

Bu test şunları kilitler:

- Tüm yeni QA standardı dosyaları repo içinde var.
- Her dosya beklenen kritik maddeleri içeriyor.
- `START_HERE_FOR_CODEX.md` yeni zorunlu okuma listesini içeriyor.
- `CODEX_CURRENT_PRIORITY.md` gerçek kullanıcı test kilidini içeriyor.
- Mevcut click ve interaction gate scriptleri güncel önceliklerde referans ediliyor.

## Çalıştırılan Komutlar

- `node --check src\webui\app.js` -> PASSED
- `.venv\Scripts\python.exe -m pytest` -> 112 passed

## Çalıştırılmayan Komutlar

Bu görev sadece dokümantasyon/test standardı ve test kilidi ekledi. Render, output, queue veya UI davranış koduna dokunulmadığı için şu komutlar bu turda zorunlu değildi:

- `scripts\real_production_quality_gate.py`
- `scripts\final_acceptance_gate.py`
- `scripts\capture_webui_screenshots.py`
- `scripts\capture_quality_gate_screenshots.py`

Render/output/queue etkileyen sonraki görevlerde bu kapılar tekrar zorunlu çalıştırılacak.

## Kalan Riskler

- Gerçek browser e2e kapsamı mevcut scriptlerle simüle ediliyor; bağımsız Playwright test runner ayrı bir P3 kalite genişletmesi olabilir.
- Kullanıcı manuel testte “çalışmıyor” derse rapor yerine kullanıcı gözlemi esas alınacak ve yeni senaryo teste eklenecek.

## P0/P1 Durumu

Bu görevde uygulama davranışına dokunulmadı. Yeni P0/P1 risk oluşturulmadı.

Son karar:

- Kalıcı gerçek kullanıcı test standardı oluşturuldu.
- Testle kilitlendi.
- Bundan sonra “test” tanımı gerçek kullanıcı aksiyonu, state/output doğrulaması ve screenshot kanıtını kapsar.
