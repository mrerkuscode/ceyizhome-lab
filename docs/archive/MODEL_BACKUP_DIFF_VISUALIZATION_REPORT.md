# Model Backup Diff Visualization Report

Tarih: 2026-05-08

## Görev

Etiket Modelleri sayfasındaki Backup Geçmişi karşılaştırmasını daha okunur hale getirmek.

## Mevcut Sorun

Backup karşılaştırması yalnızca kısa özet satırları gösteriyordu. Kullanıcı hangi model ayarının veya hangi yazı alanının değiştiğini hızlıca anlayamıyordu.

Bu P0/P1 hata değildi; güvenli P2 bakım ve model güvenliği iyileştirmesiydi.

## Değiştirilen Dosyalar

- `src/webui_backend/template_api.py`
- `src/webui/app.js`
- `src/webui/styles.css`
- `tests/test_mvp_safety.py`
- `CODEX_CURRENT_PRIORITY.md`

## Yapılan Düzeltmeler

- Backend `compare_label_model_backup` sonucu artık `setting_diffs` döndürüyor.
- Backend sonucu artık `field_diffs` ile İsim/Tarih/Not gibi alanların konum, ölçü, font, renk ve hizalama farklarını gruplayabiliyor.
- Frontend `backupCompareDetailHtml` ile farkları kart benzeri okunur satırlara çeviriyor.
- Fark yoksa sade “Alan bazlı fark bulunmadı” mesajı gösteriliyor.
- Geri yükleme akışı değiştirilmedi; mevcut güvenli backup davranışı korundu.

## UI/UX Etkisi

Kullanıcı artık backup karşılaştırmasını açtığında:

- Model ayar farklarını ayrı görür.
- Yazı alanı farklarını alan bazında görür.
- JSON okumadan hangi ayarın değiştiğini anlayabilir.
- Teknik şablon editörüne düşmeden karar verebilir.

## Render / Output / Queue Etkisi

PDF/PNG render, output validation ve queue zincirine dokunulmadı.

## Güvenlik Etkisi

- Kaynak AI/CDR dosyalarına dokunulmadı.
- Backup restore işlemi değiştirilmedi ve mevcut hal yedekleme kuralı korundu.
- CorelDRAW, Illustrator, RDWorks, yazıcı, lazer veya direct print tetiklenmedi.

## Eklenen / Güncellenen Testler

`tests/test_mvp_safety.py` içinde şu regresyon kilitleri eklendi:

- `backupCompareDetailHtml` fonksiyonu var.
- `backupDiffValue` fonksiyonu var.
- `.backup-diff-detail` ve `.backup-diff-row` stilleri var.
- Backend compare sonucunda `setting_diffs` ve `field_diffs` var.

## Çalıştırılan Komutlar

- `node --check src\webui\app.js` geçti.
- `.venv\Scripts\python.exe -m pytest` geçti: 110 passed.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` geçti: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` geçti: PASSED.
- `.venv\Scripts\python.exe scripts\label_models_real_click_gate.py` geçti: PASSED.
- `.venv\Scripts\python.exe scripts\studio_canvas_interaction_gate.py` geçti: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` geçti.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py` geçti.

## Screenshot Yolları

- `output/2026-05-08/ui_screenshots`
- `output/2026-05-08/quality_gate`
- `output/2026-05-08/label_models_click_gate`
- `output/2026-05-08/studio_interaction`

## Kalan Riskler

- Karşılaştırma mevcut backup JSON formatına bağlıdır.
- Gelecekte daha görsel “önce/sonra canvas” karşılaştırması P3 olarak değerlendirilebilir.

## P0/P1 Durumu

Kalan P0/P1 hata görülmedi.

