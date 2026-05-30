# Cyzella Production Studio - Teknik Kılavuz

## Proje Yapısı

- `src/webui`: Web arayüzü.
- `src/webui_backend`: Üretim, model, queue, çıktı, Trendyol ve RDWorks yardımcı API katmanları.
- `templates/designs`: Etiket model konfigürasyonları.
- `assets/label_backgrounds`: Etiket önizleme ve arka plan görselleri.
- `examples`: Örnek Excel dosyaları.
- `scripts`: Doğrulama, screenshot ve kalite gate scriptleri.
- `output`: Üretilen çıktı, screenshot ve test kanıtları.

## Güvenlik Sınırları

Kod hiçbir koşulda şu eylemleri otomatik yapmamalıdır:

- Direct print başlatmak.
- Yazıcıyı sessiz çalıştırmak.
- RDWorks açmak.
- Lazer başlatmak.
- CorelDRAW veya Illustrator açmak.
- Kaynak AI/CDR dosyalarını değiştirmek.

## Kritik Zincirler

PDF/PNG üretim zinciri:

1. Studio state / payload
2. Render preview
3. Final PNG
4. Final PDF / batch PDF
5. Output validation
6. Queue add

Queue güvenliği:

- Dosya varlığı kontrol edilir.
- Stale/bozuk çıktı yazdırmaya alınmaz.
- Yazdır butonu kullanıcı onay modalı açar.

RDWorks isim kesim:

- Birincil export: DXF.
- Destek export: SVG, PDF preview, PNG preview, `name_cut_manifest.json`.
- Layer renkleri: kırmızı ana kesim, mavi destek, mor plaka, yeşil kalibrasyon, gri kılavuz.
- Text-to-path ve offset durumları manifest içinde raporlanır.

## Final Test Komutları

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\verify_studio_layout_stability.py
.venv\Scripts\python.exe scripts\verify_corel_editor_interactions.py
.venv\Scripts\python.exe scripts\verify_label_models_premium_flow.py
.venv\Scripts\python.exe scripts\verify_bulk_gallery_excel_flow.py
.venv\Scripts\python.exe scripts\verify_outputs_gallery_flow.py
.venv\Scripts\python.exe scripts\verify_print_queue_flow.py
.venv\Scripts\python.exe scripts\verify_new_model_wizard.py
.venv\Scripts\python.exe scripts\verify_clean_customer_demo_flow.py
.venv\Scripts\python.exe scripts\verify_user_onboarding_and_technical_visibility.py
.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py
.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
.venv\Scripts\python.exe scripts\capture_webui_screenshots.py
```

## Release Notu

Release paketine `.venv`, `.pytest_cache`, `__pycache__` ve eski proje klasörleri dahil edilmemelidir.

