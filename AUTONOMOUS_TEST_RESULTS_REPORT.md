# AUTONOMOUS TEST RESULTS REPORT

Tarih: 2026-05-11

## Kapsam

Bu rapor kalan P2/P3 ürün iyileştirmeleri kapatıldıktan sonra çalıştırılan kalite komutlarını özetler.

## Çalıştırılan Komutlar ve Sonuçlar

| Komut | Sonuç |
|---|---|
| `node --check src\webui\app.js` | Geçti |
| `.venv\Scripts\python.exe -m pytest` | 114 passed |
| `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` | PASSED |
| `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` | PASSED |
| `.venv\Scripts\python.exe scripts\full_real_user_e2e_smoke.py` | PASSED |
| `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` | Geçti |
| `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py` | Geçti |

## Gerçek Kullanıcı QA Kanıtları

- Etiket Modelleri gerçek click gate, full e2e smoke içinde çalıştı ve geçti.
- Etiket Studio interaction gate, full e2e smoke içinde çalıştı ve geçti.
- Real production quality gate, PNG/PDF üzerinde background ve İsim/Tarih/Not piksellerini doğruladı.
- Final acceptance gate, hazır model, ikinci model ve yeni model senaryolarını doğruladı.
- Queue son doğrulanmış batch PDF yolunu aldı; direct print/yazıcı/lazer tetiklenmedi.

## Örnek Çıktılar

- Son kalite PNG: `output/2026-05-11/print/manual/2026-05-11_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_16.png`
- Son kalite PDF: `output/2026-05-11/print/manual/2026-05-11_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_20.pdf`
- Queue yolu: `output/2026-05-11/print/manual/2026-05-11_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_16.pdf`
- Full smoke sonucu: `output/2026-05-11/quality_gate/FULL_REAL_USER_E2E_SMOKE_RESULT.json`

## P0/P1 Durumu

Kalan P0/P1 hata yok.
