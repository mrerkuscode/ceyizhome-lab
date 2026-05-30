# INSTALLATION CHECKLIST

## Temiz Kurulum Kontrol Listesi

- [ ] Proje klasörü doğru yerde: `C:\Users\Pc\Documents\New project\production-bot`
- [ ] Python sanal ortamı mevcut: `.venv`
- [ ] Web UI dosyaları mevcut: `src/webui`
- [ ] Backend helper dosyaları mevcut: `src/webui_backend`
- [ ] Etiket model configleri mevcut: `templates/designs`
- [ ] Tasarım görselleri mevcut: `assets/label_backgrounds`
- [ ] Örnek Excel dosyaları mevcut:
  - `examples/toplu_etiket_ornek.xlsx`
  - `examples/toplu_etiket_100_ornek.xlsx`
  - `examples/etiket_ve_isim_kesim_ornek.xlsx`
- [ ] Output klasörü mevcut: `output`
- [ ] Backup klasörü mevcut: `backups`
- [ ] Log klasörü mevcut: `logs`
- [ ] Direct print kapalı.
- [ ] Yazıcı otomatik çalışmaz.
- [ ] RDWorks otomatik açılmaz.
- [ ] Lazer otomatik başlamaz.
- [ ] CorelDRAW / Illustrator üretim akışına bağlı değildir.
- [ ] Kaynak AI/CDR dosyaları değiştirilmez.
- [ ] Temiz müşteri demo verisi gerektiğinde `scripts\seed_clean_customer_demo_data.py` ile oluşturulabilir.
- [ ] Eski Test/QA kayıtları müşteri çıktıları ve müşteri queue görünümünden ayrı tutulur.

## Kurulum Sonrası Hızlı Test

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\verify_clean_customer_demo_flow.py
.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py
.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
```

## Kullanıcıya Teslim Öncesi Görsel Kontrol

```powershell
.venv\Scripts\python.exe scripts\capture_webui_screenshots.py
.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py
```

Son screenshot klasörleri:

- `output/YYYY-MM-DD/ui_screenshots/`
- `output/YYYY-MM-DD/quality_gate/`

## 2026-05-16 Teslim Dosyası Kontrolü

- [ ] Kullanıcı kılavuzu mevcut: `USER_MANUAL.md`
- [ ] Teknik kılavuz mevcut: `TECHNICAL_MANUAL.md`
- [ ] Release notları mevcut: `RELEASE_NOTES.md`
- [ ] Yardım/onboarding gate geçer:

```powershell
.venv\Scripts\python.exe scripts\verify_user_onboarding_and_technical_visibility.py
```
