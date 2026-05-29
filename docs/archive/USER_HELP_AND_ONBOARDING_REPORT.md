# USER HELP AND ONBOARDING REPORT

Tarih: 2026-05-13

## Görev

Aşama 14 kapsamında normal kullanıcı için yardım merkezi, ilk kullanım turu, kısayol rehberi ve hata çözüm kartları eklendi.

## Yapılan Değişiklikler

- Üst bardaki Yardım butonu artık rapor sayfasına gitmek yerine Yardım Merkezi modalını açıyor.
- İlk kullanım turu eklendi:
  - Model seç
  - Yazıya tıkla
  - Taşı ve boyutlandır
  - Font ve renk değiştir
  - PDF/PNG oluştur
  - Yazdır veya sıraya ekle
- Kısayollar paneli eklendi:
  - Arrow: 0.1 mm taşıma
  - Shift + Arrow: 1 mm taşıma
  - Alt + Arrow: 0.05 mm hassas taşıma
  - Ctrl + Z / Ctrl + Y
  - Delete
- Sorun çözüm kartları eklendi:
  - Görsel eksik
  - Yazı sığmıyor
  - PDF oluşturulamadı
  - Queue’ya eklenemedi
- Yardım turundaki “Bu adıma git” butonu ilgili sayfaya yönlendiriyor.
- Screenshot QA sırasında görülen hidden panel problemi düzeltildi. Yardım modalında kapalı sekmeler artık ekranda altta görünmüyor.

## Değiştirilen Dosyalar

- `src/webui/index.html`
- `src/webui/app.js`
- `src/webui/styles.css`
- `scripts/help_onboarding_gate.py`
- `scripts/full_real_user_e2e_smoke.py`
- `scripts/run_test_command_real_user_qa.py`
- `tests/test_mvp_safety.py`
- `CODEX_CURRENT_PRIORITY.md`
- `NEXT_AUTONOMOUS_TASKS.md`

## Testler

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m py_compile scripts\help_onboarding_gate.py`: geçti.
- `.venv\Scripts\python.exe -m pytest`: 116 passed.
- `.venv\Scripts\python.exe scripts\help_onboarding_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: geçti.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`: geçti.

## Screenshot Kanıtları

- `output/2026-05-13/help_onboarding_gate/help_tour.png`
- `output/2026-05-13/help_onboarding_gate/help_shortcuts.png`
- `output/2026-05-13/help_onboarding_gate/help_fixes.png`

## Render / Output / Queue Etkisi

Render motoru, PDF/PNG üretimi ve queue akışı değiştirilmedi. Buna rağmen kalite kapıları yeniden çalıştırıldı ve geçti.

## Güvenlik

- CorelDRAW açılmadı.
- Illustrator açılmadı.
- RDWorks açılmadı.
- Yazıcı veya lazer tetiklenmedi.
- Direct print aktif edilmedi.
- Kaynak AI/CDR dosyaları değiştirilmedi.

## Kalan Riskler

P0/P1 risk yok. Yardım turu ilk fazda modal tabanlıdır; daha ileri fazda sayfa üstü spotlight/coachmark sistemi eklenebilir.

## Son Karar

Aşama 14 tamamlandı. P0/P1 hata yok.
