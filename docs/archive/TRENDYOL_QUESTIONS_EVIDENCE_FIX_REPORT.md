# Trendyol Soru Kanıtı Düzeltme Raporu

Tarih: 2026-05-17 15:48

## Sorun

Trendyol sipariş kartlarında müşteri soruları görünmüyordu veya soru kanıtı yanlış/gevşek şekilde bağlanıyordu. Bazı satırlarda AI, satıcının otomatik cevabındaki standart metinlerden isim çıkarmaya çalışabiliyordu.

## Kök Neden

- Trendyol soru endpointi canlı sistemde `status=WaitingForAnswer` parametresiyle HTTP 400 dönüyordu.
- Soru-sipariş otomatik bağlama, ürün adı/soru metni benzerliğiyle fazla gevşek çalışıyordu.
- Bu gevşek eşleşme aynı ürüne ait farklı müşteri sorularını yanlış siparişlere bağlayabiliyordu.
- İsim ayıklama, soru ve satıcı cevabını birlikte değerlendirdiği için `TEDARİK VEYA DEĞİŞİM` gibi boilerplate cevap metinlerinden yanlış isim çıkarabiliyordu.

## Yapılan Düzeltmeler

- Trendyol Q&A çekimi `qna/sellers/{supplierId}/questions/filter` endpointinde status parametresiz çalışacak hale getirildi.
- Canlı soru senkronu 1000 soru/mesaj kaydı çekti.
- Otomatik soru bağlama sıkılaştırıldı:
  - Sipariş numarası doğrudan eşleşirse bağlanır.
  - Müşteri + barkod/SKU birlikte eşleşirse bağlanır.
  - Sadece ürün adı benzerliği artık otomatik bağlama yapmaz.
- Eski yanlış soru kanıtları temizlenip sıkı eşleşmeyle yeniden bağlandı.
- AI alan ayıklama müşteri sorusunu öncelikli kullanacak şekilde düzeltildi.
- Satıcı cevabındaki standart tedarik/iade/değişim metinleri isim olarak kullanılmayacak hale getirildi.
- `veya` kelimesinin yanlışlıkla `ve` bağlacı gibi parçalanması engellendi.

## Canlı Veri Sonucu

- Çekilen soru/mesaj: 1000
- Sipariş önerisi: 149
- Sıkı soru kanıtıyla bağlı satır: 105
- Kanıt bekleyen satır: 44
- Alan onayı bekleyen satır: 105

Örnekler:

- `#11243514002 ÖZDE ERDEM` sorusu ilgili siparişe bağlandı; öneri `Özde Erdem`.
- `11243047993 sipariş no ... Emine Emircan ...` sorusu ilgili siparişe bağlandı; öneri `Emine Emircan`.
- Soru bulunmayan siparişler `kanit_bekliyor` durumunda bırakıldı.

## Güvenlik

- Otomatik cevap verme eklenmedi.
- Yazdırma başlatılmadı.
- RDWorks açılmadı.
- Lazer başlatılmadı.
- CorelDRAW/Illustrator açılmadı.
- `mucoxai1` klasörüne müdahale edilmedi.

## Testler

- `node --check src\webui\app.js` geçti.
- `.venv\Scripts\python.exe -m pytest -q` geçti: 163 test.
- `.venv\Scripts\python.exe scripts\verify_trendyol_order_to_production_flow.py` geçti.
- `.venv\Scripts\python.exe scripts\verify_trendyol_questions_to_production_flow.py` geçti.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` geçti.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` geçti.

## Kullanıcı Kontrolü

Trendyol sayfasını yenileyip seçili siparişin sağ panelinde `Müşteri Soru / Mesaj Kanıtı` bölümünü kontrol edin. Soru numarası doğrudan siparişle eşleşen satırlarda soru metni görünmelidir. Soru bulunmayan satırlar bilinçli olarak `Kanıt bekliyor` kalır.
