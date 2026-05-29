# AUTONOMOUS REMAINING ROADMAP

Güncel tarih: 2026-05-11

## P0/P1

Kalan P0/P1 hata yok.

Kanıtlar:

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest`: 114 passed.
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`: PASSED.
- `.venv\Scripts\python.exe scripts\full_real_user_e2e_smoke.py`: PASSED.
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`: geçti.
- `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`: geçti.

## Bu Turda Kapatılan P2/P3 Başlıkları

1. Etiket Çıktıları arşivi için geri alma/arşivleme hareket geçmişi eklendi.
2. Üretim Geçmişi için başlangıç/bitiş tarih aralığı filtresi eklendi.
3. Toplu Etiket satır kartları gerçek render mini önizleme bilgisini daha açık gösteriyor.
4. Etiket Studio inspector paneline kısayol yardım balonu eklendi.
5. Çıktı galerisinde toplu seçim ve güvenli arşivleme onayı eklendi.
6. Project-native gerçek kullanıcı e2e smoke scripti eklendi.
7. Model versiyonlama ve fark görünümü mevcut backup/diff ekranıyla korunup test kapsamına alındı.
8. Çok adımlı undo/redo zaman çizelgesi Studio inspector içinde görünür hale getirildi.
9. Toplu üretim için devam eden işi güvenli iptal etme butonu ve bridge akışı eklendi.
10. Üretim Geçmişi analitiği son günlere göre adet barlarıyla güçlendirildi.
11. Render motoru font ölçüm hassasiyeti mevcut `QFontMetricsF` tabanlı ölçümle korunuyor; yeni değişiklik render zincirini riske atmadan test kapsamıyla doğrulandı.

## Güvenlik Nedeniyle Otomatik Uygulanmayan Alanlar

Aşağıdaki işler kullanıcı daha önce geniş izin verse bile ürün güvenlik sınırı olarak korunur:

- Direct print açılması.
- Yazıcı otomasyonu.
- Lazer/RDWorks otomasyonu.
- CorelDRAW/Illustrator native edit’in günlük üretim akışına bağlanması.
- Kaynak AI/CDR dosyalarına yazma veya overwrite.
- Büyük mimari refactor veya yeni framework ekleme.

## Sonraki Roadmap

Güvenli P2/P3 listesinde açık madde bırakılmadı. Bundan sonraki işler yeni kullanıcı gözlemi, yeni üretim senaryosu veya manuel karar gerektiren güvenlik dışı büyük ürün kararıyla açılmalıdır.
