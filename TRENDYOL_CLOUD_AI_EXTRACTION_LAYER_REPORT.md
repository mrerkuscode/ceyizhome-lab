# Trendyol Cloud AI Extraction Layer Report

## Kısa Karar

Trendyol soru/mesaj alanından isim ayıklama artık yalnızca kural tabanlı regex'e bağlı değil. Yeni bulut AI katmanı, müşteri sorusunu ana kanıt kabul eder; ürün adı, barkod, SKU ve müşteri adı yalnızca bağlam olarak kullanılır.

## Neden Değişti?

Önceki kural tabanlı ayıklama bazı ürün adlarındaki kelimeleri isim sanabiliyordu:

- `Çiçeği & Adet`
- `Nolu Siparişe...`
- `Yazılacak`

Bu yüzden Trendyol kişiselleştirme alanı için kök çözüm olarak OpenAI uyumlu cloud AI extraction katmanı eklendi.

## Eklenen Katman

Yeni modül:

- `src/intelligence/trendyol_ai_extractor.py`

Davranış:

- Müşteri soru metni ve satıcı cevabından strict JSON alan ayıklar.
- Ürün adından isim uydurmaz.
- AI API yoksa veya hata verirse sistem bozulmaz; kural tabanlı fallback çalışır.
- Aynı soru tekrar AI'a gönderilmez; cache kullanılır.
- API key raporlara, loglara ve UI state çıktısına açık yazılmaz.

## Ayarlar

Trendyol API Ayarları tabına AI alanları eklendi:

- Bulut AI ayıklamayı aç/kapat
- AI provider
- AI API key
- AI model
- AI güven eşiği
- Timeout
- Cache

Varsayılan model:

- `gpt-5-nano`

## Üretim Hazır Mantığı

Satır yalnızca şu durumda otomatik `uretime_hazir` olabilir:

- Müşteri soru/mesaj kanıtı var.
- Ürün barkod/SKU eşleştirmesi var.
- AI sonucu soru/cevap metninden geliyor.
- Güven eşiği karşılanıyor.
- AI `needs_user_review=false` döndürüyor.

Fiziksel işlemler yine otomatik başlamaz:

- Yazdırma yok.
- Direct print yok.
- RDWorks otomatik açılmaz.
- Lazer başlamaz.

## UI Değişiklikleri

Trendyol sağ panelinde AI sonucu daha net ayrıldı:

- `Bulut AI`
- `AI güvenli`
- `AI kontrol gerekli`
- kaynak etiketi
- evidence span / kaynak metin parçası

Kartlarda da bulut AI ve kontrol durumları rozet olarak görünür.

## Testler

Çalıştırılan komutlar:

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\verify_trendyol_ai_question_extraction_flow.py
.venv\Scripts\python.exe scripts\verify_trendyol_questions_to_production_flow.py
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
```

Sonuçlar:

- `node --check`: PASSED
- `pytest`: 170 passed
- `verify_trendyol_ai_question_extraction_flow.py`: PASSED
- `verify_trendyol_questions_to_production_flow.py`: PASSED
- `real_production_quality_gate.py`: PASSED
- `final_acceptance_gate.py`: PASSED

## Doğrulanan Kritik Senaryolar

- Ürün adında `Çiçeği ve 80 Adet` geçse bile isim alanına yazılmaz.
- `Bahar ♡ Yunus` soru metninden `Bahar & Yunus` olarak çıkar.
- `EMİNE & MUSTAFA yazılacak` doğru normalize edilir.
- AI product_name kaynaklı isim döndürürse reddedilir.
- AI cache aynı soruyu ikinci kez çağırmaz.
- AI API hatasında secret sızmaz.
- Yüksek güvenli, eşleşmiş ve soru kanıtlı satır üretime hazır olur.
- Soru yoksa satır kanıt bekler.
- Direct print, RDWorks ve lazer otomasyonu tetiklenmez.

## Kalan Not

Canlı bulut AI için kullanıcı AI API key'i ayarlara girmelidir. Key yoksa sistem fallback ile çalışır ve satırlar kullanıcı kontrolünde kalır. Bu bilinçli güvenlik davranışıdır.
