# FINAL RELEASE CHECKLIST

Tarih: 2026-05-14

## Üretim Kabul Kriterleri

- [x] Ana Sayfa açılır ve üretim merkezi görünür.
- [x] Etiket Modelleri kartları gerçek model verisiyle görünür.
- [x] Model preview resolver boş/beyaz kırık kutu göstermez.
- [x] Yeni Model Ekle teknik editör açmaz.
- [x] Görsel Bağla doğru modele bağlanır.
- [x] Etiket Studio doğru modelle açılır.
- [x] İsim/Tarih/Not canlı güncellenir.
- [x] Drag çalışır.
- [x] Corner resize width/height/font_size değiştirir.
- [x] Side resize width/height değiştirir.
- [x] Font preset ve renk paleti PDF/PNG payload’a yansır.
- [x] Akıllı Düzen gerçek geometry değiştirir.
- [x] PDF/PNG canvas ile aynı çıkar.
- [x] PDF preview son dosyayı gösterir.
- [x] PNG preview son dosyayı gösterir.
- [x] Queue son doğrulanmış batch PDF’i alır.
- [x] Queue varsayılan görünümde Test/QA kayıtlarını müşteri kuyruğundan ayırır.
- [x] Etiket Çıktıları teknik/test kayıtlarını müşteri galerisinden ayırır.
- [x] Temiz müşteri demo seed akışı release kalite kapısında doğrulanır.
- [x] Yazdır onay modalı açar, silent print yapmaz.
- [x] Direct print kapalı kalır.
- [x] CorelDRAW / Illustrator / RDWorks / yazıcı / lazer otomatik tetiklenmez.
- [x] Türkçe karakterler uygulama ve raporlarda doğru görünür.

## Toplu Üretim ve Sipariş

- [x] Toplu Etiket 100 satır galeri senaryosu geçer.
- [x] Hatalı model satırları üretime alınmaz.
- [x] Batch manifest üretilir.
- [x] Hazır batch queue’ya doğru metadata ile eklenir.
- [x] Sipariş oluşturulur.
- [x] Siparişten Studio’ya doğru model ve alanlarla geçilir.
- [x] Siparişten iş emri PDF’i oluşur.
- [x] Siparişten doğrulanmış PDF batch Yazdırma Sırasına eklenir.

## RDWorks / İsim Kesim Durumu

- [x] DXF birincil export oluşur.
- [x] SVG destek/export dosyası oluşur.
- [x] PDF/PNG preview oluşur.
- [x] `name_cut_manifest.json` oluşur.
- [x] 50 isim çalışma alanına fire azaltma mantığıyla dizilir.
- [x] RDWorks otomatik açılmaz.
- [x] Lazer otomatik başlamaz.
- [x] Text-to-path / outline conversion fontTools ile SVG path ve DXF POLYLINE olarak oluşur.
- [x] Gerçek polygon offset motoru `pyclipper` ile export hattına bağlıdır.
- [x] RDWorks isim kesim ve birleşik Excel etiket+isim kesim doğrulamaları release kalite kapısında çalışır.

RDWorks isim kesim paketi operatör kontrolü gerektirir. Gerçek kesim öncesi RDWorks içinde layer, ölçü, path ve offset görünümü manuel kontrol edilmelidir.

## Final Komutlar

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\verify_clean_customer_demo_flow.py
.venv\Scripts\python.exe scripts\verify_corel_editor_interactions.py
.venv\Scripts\python.exe scripts\verify_bulk_gallery_excel_flow.py
.venv\Scripts\python.exe scripts\verify_print_queue_flow.py
.venv\Scripts\python.exe scripts\verify_outputs_gallery_flow.py
.venv\Scripts\python.exe scripts\verify_new_model_wizard.py
.venv\Scripts\python.exe scripts\verify_customer_order_flow.py
.venv\Scripts\python.exe scripts\verify_label_models_premium_flow.py
.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py
.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py
.venv\Scripts\python.exe scripts\settings_security_gate.py
.venv\Scripts\python.exe scripts\help_onboarding_gate.py
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
.venv\Scripts\python.exe scripts\capture_webui_screenshots.py
.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py
.venv\Scripts\python.exe scripts\verify_release_package.py
```

## 2026-05-16 UI/UX ve Teslim Eki

- [x] Yardım Merkezi hızlı başlangıç şeridi gösterir.
- [x] Teknik araçlar varsayılan kapalı ve normal kullanıcı akışından geri plandadır.
- [x] Release dashboard kalite kanıtlarını gösterir.
- [x] `USER_MANUAL.md` oluşturuldu.
- [x] `TECHNICAL_MANUAL.md` oluşturuldu.
- [x] `RELEASE_NOTES.md` oluşturuldu.
- [x] `scripts\verify_user_onboarding_and_technical_visibility.py` geçer.

Ek final komut:

```powershell
.venv\Scripts\python.exe scripts\verify_user_onboarding_and_technical_visibility.py
```
