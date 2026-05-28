# ARCHITECTURE MAP

Güncel tarih: 2026-05-07

Bu harita Cyzella Production Studio / Label Studio V1 üzerinde çalışmaya başlamadan önce okunacak teknik pusuladır.

## Kök Dizin

Proje yolu:

`C:\Users\Pc\Documents\New project\production-bot`

Ana klasörler:
- `src`: uygulama kodu
- `src/webui`: ana web arayüzü
- `src/webui_backend`: web arayüzü ile Python servisleri arasındaki güvenli backend API katmanı
- `src/desktop`: PySide/PyWebView desktop pencere ve bridge kodları
- `src/label_designer`: etiket render, preview, PDF/PNG üretim ve template yükleme motoru
- `src/native_edit`: Corel/Illustrator teknik PoC alanı; normal üretim akışına bağlanmaz
- `templates/designs`: model/template JSON dosyaları
- `assets/label_backgrounds`: tasarım/preview/background görselleri
- `config`: ayarlar ve backup dosyaları
- `output`: günlük PDF/PNG, preview, quality gate, screenshot ve rapor çıktıları
- `scripts`: kalite kapıları, screenshot ve acceptance scriptleri
- `tests`: pytest regression testleri

## Frontend

Ana dosyalar:
- `src/webui/index.html`: sayfa iskeleti, modal alanları, ana UI elementleri
- `src/webui/app.js`: state yönetimi, sayfa render, buton action, canvas interaction, Studio/Models/Home akışları
- `src/webui/styles.css`: premium beyaz UI, kartlar, modal, canvas overlay, handle ve layout stilleri

Ürün standardı:
- Normal kullanıcıya JSON/X/Y/path/debug gösterilmez.
- Teknik Mod default kapalıdır.
- Dinamik render sonrası event listener kopmaması için action/state akışları korunur.

## Desktop Bridge

Ana dosyalar:
- `src/desktop/web_main_window.py`: QWebEngine pencere, web bridge, desktop shell davranışı
- `src/webui_backend/bridge.py`: JavaScript bridge slotları ve güvenli JSON sonuç dönüşleri
- `src/desktop/label_template_editor.py`: Gelişmiş Şablon Düzenleyici; normal kullanıcı akışına bağlanmaz

Güvenlik:
- CorelDRAW, Illustrator, RDWorks, yazıcı, lazer ve direct print otomatik tetiklenmez.
- Native AI/CDR yalnızca teknik PoC alanında kalır.

## Backend API

Ana dosyalar:
- `src/webui_backend/label_api.py`: Etiket Studio ve render API yüzeyi
- `src/webui_backend/template_api.py`: model/template listeleme, preview bağlama, yeni model oluşturma
- `src/webui_backend/print_queue_api.py`: Yazdırma Sırası işlemleri
- `src/webui_backend/pdf_preview_api.py`: PDF preview üretimi
- `src/webui_backend/bulk_label_api.py`: Toplu Etiket akışları
- `src/webui_backend/settings_api.py`: ayarlar okuma/yazma ve backup
- `src/webui_backend/production_safety.py`: preflight/output validation ve güvenlik kontrolleri
- `src/webui_backend/text_normalizer.py`: dosya adı ve Türkçe metin normalizasyonu

## Render Motoru

Ana dosyalar:
- `src/label_designer/manual_label_service.py`: Manuel Etiket/Studio PDF, PNG ve batch üretim servisi
- `src/label_designer/renderer.py`: background ve text layer çizimi
- `src/label_designer/pdf_exporter.py`: PDF üretimi
- `src/label_designer/preview_exporter.py`: PNG/preview üretimi
- `src/label_designer/template_loader.py`: template JSON yükleme
- `src/label_designer/settings_resolver.py`: default ölçü ve ayar çözümü
- `src/label_designer/placeholder_resolver.py`: field değer çözümleme

Kritik kural:
- Canvas'taki son state backend payload'a gider.
- Background path, label_text, date_text, note_text, field geometry, font, renk, hizalama ve ölçü override final output ile eşleşir.
- Background veya text kaybolursa başarı sayılmaz.

## Model ve Asset Yapısı

Model JSON:
- `templates/designs/01_a_gold.json`
- `templates/designs/02_a_gold.json`
- `templates/designs/03_a_gold.json`
- `templates/designs/04_a_qa.json`

Backup:
- `templates/designs/backups`

Background/preview:
- `assets/label_backgrounds`
- `assets/label_backgrounds/normalized`

Kural:
- Model config değişmeden önce backup alınır.
- Kaynak AI/CDR veya orijinal tasarım dosyası overwrite edilmez.

## Queue ve Output

Output:
- `output/YYYY-MM-DD/print/manual`
- `output/YYYY-MM-DD/preview`
- `output/YYYY-MM-DD/quality_gate`
- `output/YYYY-MM-DD/ui_screenshots`

Queue:
- `src/webui_backend/print_queue_api.py`
- Queue yalnızca doğrulanmış son PDF/batch output yolunu alır.
- Direct print kapalı kalır.
- Kullanıcı PDF'i kontrol ettikten sonra manuel yazdırır.

## Ayarlar

Ana dosyalar:
- `config/settings.yaml`
- `config/backups`
- `src/webui_backend/settings_api.py`
- `src/config_loader.py`

Kural:
- Etiket Studio ölçü override sadece o üretim içindir.
- Global ayar otomatik değişmez.
- Config değişikliklerinde backup alınır.

## Test ve Kalite Kapıları

Ana test:
- `tests/test_mvp_safety.py`

Kalite scriptleri:
- `scripts/real_production_quality_gate.py`
- `scripts/final_acceptance_gate.py`
- `scripts/label_models_real_click_gate.py`
- `scripts/studio_canvas_interaction_gate.py`
- `scripts/capture_webui_screenshots.py`
- `scripts/capture_quality_gate_screenshots.py`
- `scripts/write_final_reports.py`

Standart komutlar:

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
.venv\Scripts\python.exe scripts\capture_webui_screenshots.py
.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py
```

## Teknik PoC Alanları

- `src/native_edit`
- Native AI/CDR Deneme sayfası
- Lazer sayfası

Bu alanlar ana kullanıcı üretim akışına bağlanmaz. Otomatik Corel/Illustrator/RDWorks/lazer/yazıcı başlatılmaz.

## Bilinen Dikkat Noktaları

- Manuel kullanıcı testi rapordan üstündür.
- PowerShell bazı UTF-8 çıktıları yanlış gösterebilir; dosya içeriği Python ile `encoding='utf-8'` okunarak doğrulanır.
- Render/output/queue zinciri çalışan kritik sistemdir; gereksiz refactor yapılmaz.
