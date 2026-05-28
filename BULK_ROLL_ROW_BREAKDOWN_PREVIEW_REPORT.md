# BULK ROLL ROW BREAKDOWN PREVIEW REPORT

Tarih: 2026-05-08

## Görev

Toplu Etiket rulo yerleşim önizlemesine daha ayrıntılı satır kırılımı eklemek.

## Mevcut Sorun

Rulo yerleşim simülasyonu rulo genişliği, etiket ölçüsü, satır başına adet, toplam satır ve son satır bilgisini gösteriyordu. Ancak kullanıcı ilk satırlarda hangi etiket numaralarının hangi satıra düştüğünü hızlıca okuyamıyordu.

## Kök Neden

`rollLayoutVisualHtml()` görsel şerit ve genel meta bilgi üretiyordu, fakat satır bazlı numara aralığı ve boş yer bilgisi ayrı bir kırılım listesi olarak gösterilmiyordu.

## Değiştirilen Dosyalar

- `src/webui/app.js`
- `src/webui/styles.css`
- `tests/test_mvp_safety.py`

## Yapılan Düzeltmeler

- Rulo yerleşim kartına “Satır kırılımı” bölümü eklendi.
- İlk 6 satır için:
  - Satır numarası
  - Etiket numara aralığı
  - Satırdaki etiket adedi
  - Varsa boş yer sayısı
  gösteriliyor.
- 6 satırdan fazlası varsa “N satır daha aynı kuralla devam eder.” bilgisi gösteriliyor.
- CSS ile satır kırılımı okunur küçük satır kartlarına ayrıldı.

## UI/UX Etkisi

Kullanıcı rulo batch oluşturmadan önce sadece “kaç adet sığar?” bilgisini değil, satır satır yerleşim mantığını da görebiliyor. Bu, rulo üretim öncesi kontrolü daha anlaşılır hale getiriyor.

## Render / Output / Queue Etkisi

PDF/PNG render, rulo batch üretim algoritması ve queue zincirine dokunulmadı. Bu değişiklik yalnızca Toplu Etiket rulo önizleme UI’ını güçlendirir.

## Güvenlik Etkisi

Yazıcı, lazer, RDWorks, CorelDRAW veya Illustrator çağrısı eklenmedi. Direct print kapalı kaldı.

## Eklenen / Güncellenen Testler

- `tests/test_mvp_safety.py` içinde “Satır kırılımı”, `roll-row-breakdown` ve `roll-breakdown-row` regression kilidine eklendi.

## Çalıştırılan Komutlar

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: 110 passed.
- `.venv\Scripts\python.exe -m pytest`: 110 passed.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: geçti.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`: geçti.

## Screenshot Yolları

- `output/2026-05-08/ui_screenshots`
- `output/2026-05-08/quality_gate`

## Kalan Riskler

- Bu önizleme gerçek üretim algoritmasını değiştirmedi; yalnızca mevcut hesapların kullanıcıya daha okunur gösterimidir.
- Gelecekte P3 olarak rulo sayfası, fire oranı ve çıktı şerit uzunluğu simülasyonu eklenebilir.

## P0/P1 Durumu

Kalan P0/P1 hata görülmedi. Üretim kalite kapısı, final acceptance ve testler geçti.
