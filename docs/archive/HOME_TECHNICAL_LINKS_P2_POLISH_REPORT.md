# HOME TECHNICAL LINKS P2 POLISH REPORT

Tarih: 2026-05-13

## Kısa Karar

Ana Sayfa / sidebar normal kullanıcı için daha sakin hale getirildi. Teknik araçlar artık ana navigasyon kadar baskın görünmez; kapalı bir "Teknik araçlar" disclosure içinde durur.

Bu çalışma yalnızca UI/UX polish kapsamındadır. Üretim akışları, render, queue, output validation, yazdırma güvenliği veya cihaz otomasyonlarına dokunulmadı.

## Önceki Sorun

- Sidebar'da `Native AI/CDR Deneme`, `Lazer` ve `Çıktı Klasörleri` normal üretim sayfalarıyla aynı ağırlıkta görünüyordu.
- Normal kullanıcı için bu bölüm teknik ve kafa karıştırıcı bir sinyal oluşturuyordu.
- Güvenlik sınırları zaten korunuyordu; ancak UI hiyerarşisi bunu daha sakin anlatmalıydı.

## Yapılan Değişiklik

- Teknik nav bloğu `details/summary` yapısına alındı.
- Varsayılan durumda kapalı görünür.
- Başlık: `Teknik araçlar`
- Yardımcı metin: `Normal üretimde gerekmez`
- Açıldığında teknik sayfalar hâlâ erişilebilir:
  - `Native AI/CDR Deneme`
  - `Lazer`
  - `Çıktı Klasörleri`
- Teknik butonlar daha küçük ve ikincil opacity ile gösterilir.

## Güvenlik Teyidi

- CorelDRAW otomatik açılmadı.
- Illustrator otomatik açılmadı.
- RDWorks otomatik açılmadı.
- Lazer otomatik başlamadı.
- Yazıcı direct/silent print çalıştırılmadı.
- Direct print aktif edilmedi.
- Kaynak AI/CDR dosyalarına dokunulmadı.

## Değişen Dosyalar

- `src/webui/index.html`
- `src/webui/styles.css`
- `HOME_TECHNICAL_LINKS_P2_POLISH_REPORT.md`
- `CODEX_CURRENT_PRIORITY.md`
- `NEXT_AUTONOMOUS_TASKS.md`

## Çalıştırılan Testler

Geçti:

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m pytest -q`
  - `128 passed`
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`

## Screenshot Kanıtı

- `output/2026-05-13/ui_screenshots/ana_sayfa.png`

## Kalan Riskler

Bilinen P0/P1 yok.

P2:

- Final teslim paketi ve dokümantasyon son kez birlikte kontrol edilebilir.

Teknik P1:

- RDWorks gerçek boolean/geometrik offset motoru hâlâ ayrı teknik risktir.

## Son Karar

Ana Sayfa normal kullanıcı için daha temiz hale geldi. Teknik araçlar erişilebilir kalır, ancak ana üretim akışını görsel olarak bastırmaz.
