# AI Autonomous Production Candidate Mode Report

Updated: 2026-05-16

## Summary

AI otonom üretim adayı modu bilinçli olarak açıldı. Bu mod fiziksel üretim otomasyonu değildir.

Sistem artık Trendyol siparişinde kayıtlı barkod/SKU eşleştirmesi yoksa bile, yalnızca yüksek güvenli durumlarda üretim adayı hazırlayabilir:

- Katalogdaki güvenli etiket modeli yüksek güvenle bulunursa.
- İsim / tarih / not / adet alanları yeterli güvenle çıkarılırsa.
- Model test/QA/deneme gibi teknik model değilse.
- AI otonom ayarı açık ise.

Yazdırma, RDWorks ve lazer otomatik başlatılmaz. Kullanıcı fiziksel aksiyonları yine manuel onaylar.

## What Changed

- Trendyol ayarlarına `AI otonom üretim adaylarını aç` seçeneği eklendi.
- `sync_recent_orders` artık Label Studio model kataloğunu backend’e geçiriyor.
- `build_suggestions_from_orders` kayıtlı mapping yokken güvenli AI model tahmini deneyebiliyor.
- AI otonom öneriler UI’da `AI otonom` rozetiyle görünüyor.
- Export manifest artık AI otonom satır sayısını ve fiziksel kullanıcı onayı gerekliliğini taşıyor.
- AI otonom mod ürün eşleştirme tablosuna sessiz kayıt açmıyor.

## Decision Rules

- Model güven eşiği: `0.72`
- Alan çıkarma güven eşiği: `0.65`
- SKU/model no net eşleşmesi yüksek güven kabul edilir.
- Barkod/SKU mapping varsa yine ana otorite mapping tablosudur.
- AI düşük güvenli satırlar `review` durumunda kalır.
- AI bilinmeyen ürünü fiziksel üretime veya yazdırmaya göndermez.

## Safety

- Direct print kapalı.
- Yazıcı sessiz çalıştırılmadı.
- RDWorks otomatik açılmadı.
- Lazer otomatik başlamadı.
- CorelDRAW / Illustrator açılmadı.
- `C:\Users\Pc\Desktop\mucoxai1` değiştirilmedi.
- API key/secret rapora yazılmadı.
- `data/trendyol_settings.json` git dışı bırakıldı.

## Files Changed

- `src/webui_backend/trendyol_api.py`
- `src/desktop/web_main_window.py`
- `src/webui/index.html`
- `src/webui/app.js`
- `src/webui/styles.css`
- `tests/test_trendyol_order_to_production.py`
- `scripts/verify_trendyol_mapping_review_workflow.py`
- `scripts/verify_trendyol_live_mapping_readiness.py`

## Tests

Passed:

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m pytest tests\test_trendyol_order_to_production.py -q`
- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe scripts\verify_trendyol_order_to_production_flow.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_mapping_review_workflow.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_live_mapping_readiness.py`
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`

## Result

AI katmanı artık sadece pasif öneri değil; yüksek güvenli Trendyol satırlarını üretim adayı olarak hazırlayabiliyor. Buna rağmen sistem bilinçli güvenlik çizgisini koruyor: kullanıcı onayı olmadan PDF/PNG üretim, queue, yazdırma, RDWorks veya lazer başlatma yapılmıyor.

## Remaining Work

- Gerçek Trendyol siparişlerinde birkaç barkod/SKU için kullanıcı onaylı mapping oluşturulmalı.
- AI otonom satırların gerçek canlı siparişlerde yanlış model seçmediği kullanıcı gözüyle doğrulanmalı.
- Düşük güvenli ürünlerin kontrol kuyruğunda anlaşılır kaldığı görsel QA ile tekrar kontrol edilmeli.
