# SETTINGS AND SECURITY CENTER REPORT

Tarih: 2026-05-13

## Görev

Aşama 13 kapsamında Ayarlar sayfası normal kullanıcı için sade bir “Ayarlar ve Güvenlik” merkezine dönüştürüldü. Etiket ölçüsü, rulo ayarı, font/renk bilgisi, çıktı klasörleri, yedekleme ve güvenlik kararları tek ekranda görünür hale getirildi.

## Değiştirilen Dosyalar

- `src/webui/index.html`
- `src/webui/app.js`
- `src/webui/styles.css`
- `src/webui_backend/bridge.py`
- `scripts/settings_security_gate.py`
- `scripts/full_real_user_e2e_smoke.py`
- `scripts/run_test_command_real_user_qa.py`
- `tests/test_mvp_safety.py`
- `SETTINGS_AND_SECURITY_CENTER_REPORT.md`
- `CODEX_CURRENT_PRIORITY.md`
- `NEXT_AUTONOMOUS_TASKS.md`

## Yapılan Düzeltmeler

- Ayarlar sayfasının başlığı “Ayarlar ve Güvenlik” olarak netleştirildi.
- Sayfa içinden güvenli ayar kaydı eklendi.
- Etiket ölçüsü alanları eklendi:
  - Genişlik mm
  - Yükseklik mm
  - Varsayılan adet
  - DPI
  - Güvenli alan mm
  - Ölçek %
- Rulo ayarı alanları eklendi:
  - Rulo genişliği mm
  - Etiket aralığı mm
- Font ve renk bölümü normal kullanıcı dilinde bilgi kartına dönüştürüldü.
- Çıktı klasörleri bölümü güvenli proje içi yolları gösteriyor.
- Yedekleme bölümü son settings backup kayıtlarını gösteriyor.
- Güvenlik bölümü direct print, yazdırma onayı, Corel/Illustrator, RDWorks/Lazer ve kaynak AI/CDR kararlarını açık gösteriyor.
- Teknik Mod bölümü normal kullanıcı akışından ikincil ve kontrollü hale getirildi.

## Backend Güvenliği

`WebBridge.save_label_defaults_json(...)` eklendi. Bu method:

- `settings_api.save_label_defaults(...)` ile kayıt yapar.
- Kayıt öncesi `config/settings.yaml` backup zincirini kullanır.
- `allow_direct_print` değerini her kayıtta `false` tutar.
- `require_print_confirmation` değerini `true` tutar.
- Kayıt sonrası state’i yeniler.

## Backup / Versioning

Ayar kaydı sırasında `config/backups/settings_YYYYMMDD_HHMMSS.yaml` dosyası oluşturulur. Gate testi kayıt ve restore sırasında backup oluştuğunu doğruladı.

## Studio Default / Override Etkisi

Ayarlar global varsayılanı temsil eder. Etiket Studio’daki ölçü override davranışı değişmedi; Studio içindeki geçici ölçü değişiklikleri global ayarı otomatik değiştirmez. Bu bilgi Ayarlar sayfasında rulo özeti içinde açıkça gösteriliyor.

## Gerçek Kullanıcı Gate

Yeni `scripts/settings_security_gate.py` şu davranışları doğruluyor:

- Ayarlar sayfası açılıyor.
- Direct Print kapalı bilgisi görünüyor.
- Yazıcı otomatik çalışmaz bilgisi görünüyor.
- Kaynak AI/CDR değiştirilmez bilgisi görünüyor.
- Font/Renk, Çıktı Klasörleri, Yedekleme ve Güvenlik bölümleri görünüyor.
- Sayfa içi ayar kaydı backup oluşturuyor.
- Kayıt direct print’i açmıyor.
- Yazdırma onayı korunuyor.
- Test sonunda orijinal ayarlar restore ediliyor.

## Test Sonuçları

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m py_compile scripts\settings_security_gate.py src\webui_backend\bridge.py`: geçti.
- `.venv\Scripts\python.exe -m pytest`: 116 passed.
- `.venv\Scripts\python.exe scripts\settings_security_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: geçti.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`: geçti.

## Screenshot Kanıtları

- `output/2026-05-13/settings_security_gate/settings_security_center_page.png`
- `output/2026-05-13/settings_security_gate/settings_after_save.png`
- `output/2026-05-13/ui_screenshots/ayarlar.png`

## Render / Output / Queue Etkisi

PDF/PNG render motoru, output validation ve queue zinciri değiştirilmedi. Kalite kapıları tekrar çalıştırıldı ve geçti.

## Güvenlik Teyidi

- Direct print kapalı kaldı.
- Yazıcı sessiz çalıştırılmadı.
- Lazer/RDWorks tetiklenmedi.
- CorelDRAW/Illustrator açılmadı.
- Kaynak AI/CDR dosyaları değiştirilmedi.

## Kalan Riskler

Gelişmiş masaüstü ayar penceresi hâlâ Teknik Mod mantığında erişilebilir. Normal kullanıcı için ana yol yeni Ayarlar ve Güvenlik sayfasıdır; riskli direct print ayarı bu görevde aktif edilmedi.

## P0/P1 Durumu

P0/P1 hata yok.

