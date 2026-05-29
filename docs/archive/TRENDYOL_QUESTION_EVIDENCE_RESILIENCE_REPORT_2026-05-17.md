# Trendyol Question Evidence Resilience Report

Date: 2026-05-17

## Summary

Trendyol soru/mesaj kaniti akisi guclendirildi. Sistem artik soru servisi calistiginda hem bekleyen hem cevaplanmis sorulari read-only kanit olarak toplar; servis yanit vermediginde ise bu durumu yerel ayarlara ve UI'a acik bicimde yazar.

Bu degisiklik uretim zincirini degistirmez. Soru kaniti ve kullanici dogrulamasi olmayan Trendyol satirlari uretime aktarilmaz.

## Changes

- `sync_questions` artik `WaitingForAnswer` ve `Answered` durumlarini birlikte okur.
- Ayni soru kayitlari dedupe edilir.
- Soru servisi kapaliysa `last_questions_sync_status`, `last_questions_sync_message` ve `last_questions_sync_at` kaydedilir.
- Siparis senkronundaki best-effort soru yenileme basarisiz olursa siparisleri bozmaz, ancak son hata durumunu saklar.
- Trendyol UI soru kaniti listesi servis kapali / kanit yok durumlarini ayri gosterir.
- Trendyol hizli filtrelerine `Kanit Bekliyor` ve `Onay Bekliyor` eklendi.

## Files Changed

- `src/webui_backend/trendyol_api.py`
- `src/webui/app.js`
- `tests/test_trendyol_order_to_production.py`
- `CODEX_CURRENT_PRIORITY.md`
- `NEXT_AUTONOMOUS_TASKS.md`

## Tests

Passed:

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m pytest tests\test_trendyol_order_to_production.py -q`
- `.venv\Scripts\python.exe scripts\verify_trendyol_order_to_production_flow.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_mapping_review_workflow.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_live_mapping_readiness.py`

## Safety

- Trendyol sorulari read-only cekilir.
- Otomatik cevap verilmez.
- Kullanici onayi olmadan uretime aktarim yapilmaz.
- Direct print tetiklenmez.
- RDWorks/lazer otomatik acilmaz veya baslamaz.
- CorelDRAW/Illustrator acilmadi.
- `C:\Users\Pc\Desktop\mucoxai1` degistirilmedi.

## Remaining

- Trendyol soru/mesaj servisi yeniden erisilebilir oldugunda canli kanitli bir satir secilip kullanici gibi dogrulanmali.
- Gercek barkod/SKU urun eslestirmeleri temizlenmeli.
- Onayli tek bir Trendyol satiri Siparisler -> Studio -> PDF/PNG -> Queue akisiyle son kez denenmeli.
