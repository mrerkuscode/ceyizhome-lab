# BULK ROLL WASTE STRIP ESTIMATE REPORT

Tarih: 2026-05-08

## Görev

Toplu Etiket rulo yerleşim önizlemesine yaklaşık şerit uzunluğu ve fire/boş genişlik bilgisini eklemek.

## Mevcut Sorun

Rulo önizleme satır kırılımını gösteriyordu, ancak kullanıcı üretim öncesi yaklaşık ne kadar şerit kullanılacağını ve satır başında/son satırda ne kadar boş genişlik kalacağını göremiyordu.

## Kök Neden

Mevcut önizleme hesapları per-row yerleşimi ve satır sayısını üretiyordu; bu hesaplardan türetilebilecek şerit uzunluğu ve boş genişlik bilgileri kullanıcıya sunulmuyordu.

## Değiştirilen Dosyalar

- `src/webui/app.js`
- `src/webui/styles.css`
- `tests/test_mvp_safety.py`

## Yapılan Düzeltmeler

- Rulo yerleşim kartına “Yaklaşık şerit” bilgisi eklendi.
- Tam satır ve son satır için boş genişlik/fire özeti hesaplandı.
- Taşma varsa kullanıcıya rulo ayarını düzeltmeden üretime geçmemesi gerektiği sade mesajla gösteriliyor.
- CSS ile “Fire özeti” kartı eklendi.

## UI/UX Etkisi

Kullanıcı rulo batch üretiminden önce sadece kaç etiket sığacağını değil, yaklaşık şerit uzunluğu ve boş alan bilgisini de görebiliyor. Bu, rulo üretim kararını daha bilinçli hale getiriyor.

## Render / Output / Queue Etkisi

Render motoruna, PDF/PNG üretimine, rulo batch oluşturma algoritmasına ve queue sistemine dokunulmadı. Değişiklik yalnızca Toplu Etiket rulo analiz/önizleme UI’ında.

## Güvenlik Etkisi

CorelDRAW, Illustrator, RDWorks, yazıcı, lazer veya direct print çağrısı eklenmedi. Kaynak AI/CDR dosyalarına dokunulmadı.

## Eklenen / Güncellenen Testler

- `tests/test_mvp_safety.py` içine şu regression kilitleri eklendi:
  - `Yaklaşık şerit:`
  - `Boş genişlik:`
  - `Fire özeti`
  - `roll-waste-note`

## Çalıştırılan Komutlar

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: 110 passed.
- `.venv\Scripts\python.exe -m pytest`: 110 passed.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: geçti.

## Screenshot Yolları

- `output/2026-05-08/ui_screenshots`
- `output/2026-05-08/quality_gate`

## Kalan Riskler

- Şerit uzunluğu yaklaşık bilgi olarak gösterilir; gerçek makine/rulo besleme toleransları ayrıca sahada doğrulanmalıdır.
- İleride P3 olarak fire oranı yüzdesi ve toplam rulo uzunluğu simülasyonu genişletilebilir.

## P0/P1 Durumu

Kalan P0/P1 hata görülmedi. Pytest ve gerçek üretim kalite kapısı geçti.
