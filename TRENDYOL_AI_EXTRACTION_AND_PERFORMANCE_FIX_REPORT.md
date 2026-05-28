# Trendyol AI Extraction and Performance Fix Report

## Summary

Trendyol ekranında iki kritik problem giderildi:

- Soru metninden isim ayıklama, "yazılmasını rica ediyorum" gibi istek cümlelerini isim alanına dahil ediyordu.
- Trendyol sayfası büyük soru/veri listelerinde gereksiz render ve tekrar eşleştirme yaptığı için donma hissi oluşturuyordu.

## Fixed Behavior

Örnek canlı satır:

- Soru: `11243461810 Selin & Hakan yazılmasını rica ediyorum`
- Etiket ismi: `Selin & Hakan`
- Lazer ismi: `Selin Hakan`
- Tarih: `07.06.2026`
- Durum: `alanlar_onay_bekliyor`
- Soru kanıtı: `1` bağlı soru

## What Changed

### AI Field Extraction

- `yazılmasını rica ediyorum`, `yazılmasını`, `rica`, `ediyorum` gibi istek kelimeleri artık isimden temizlenir.
- Ürün/sipariş kelimeleri isim adayından kırpılır.
- Soru metni, satıcı cevaplarından ve ürün adından daha öncelikli kanıt kabul edilir.
- Ürün adından veya müşteri adından gelen tahminler üretime hazır kabul edilmez; kullanıcı onayı bekler.

### Trendyol UI Performance

- Trendyol update sırasında artık tüm tablar aynı anda render edilmiyor.
- Sadece aktif tabın içeriği çiziliyor.
- Sipariş kartları artık her render'da tüm soru listesini potansiyel eşleşme için taramıyor.
- Potansiyel soru araması yalnızca seçili sipariş detayında gerektiğinde yapılıyor.

### Question Sync Performance

- Soru çekme endpointi `qna/sellers/{supplierId}/questions/filter` olarak korunur.
- Sayfa boyutu `100` oldu.
- Canlı sync ilk yükte en güncel `3` sayfayı çeker ve mevcut yerel soru cache'i ile birleştirir.
- Eski soru kanıtları cache'te korunur; her senkron tüm eski kanıtları silmez.

## Live Verification

Son canlı kontrol:

- Soru senkronu: `11.13s`
- Cache soru sayısı: `1000`
- Sipariş `11243461810`:
  - `label_text`: `Selin & Hakan`
  - `name_cut_text`: `Selin Hakan`
  - `date_text`: `07.06.2026`
  - `verification_status`: `alanlar_onay_bekliyor`

Önceki canlı senkron yaklaşık `62.91s` seviyesindeydi; ağır tab render ve soru tarama kaldırıldıktan sonra ekran daha hafif çalışır.

## Tests

Passed:

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe scripts\verify_trendyol_order_to_production_flow.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_questions_to_production_flow.py`
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`

Pytest result:

- `164 passed`

## Safety

No automatic action was added for:

- direct print
- printer
- RDWorks
- laser
- CorelDRAW
- Illustrator

Trendyol question data is still used only as production evidence and field suggestion. User approval remains required before production transfer.

## Remaining Risk

- Trendyol API can still be slow depending on network and API response time.
- Very old questions are preserved from local cache; if a needed old question was never cached before, the user may need a wider manual sync range in a future UI control.
- AI extraction is rule-assisted and conservative; ambiguous messages should stay in user approval flow.
