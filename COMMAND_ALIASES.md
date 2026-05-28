# Komut Kısayolları

Bu dosya Codex'in kısa kullanıcı komutlarını nasıl yorumlayacağını tanımlar.

## test

Kullanıcı sadece:

```text
test
```

yazdığında şu anlama gelir:

"Projeyi gerçek kullanıcı gibi test et. Sayfaları gez, butonlara tıkla, Etiket Studio'da yazıyı taşı, resize yap, PDF/PNG oluştur, queue'ya ekle, screenshot al, hata varsa onay beklemeden düzelt, tekrar test et."

### test komutu çalışınca yapılacaklar

1. `START_HERE_FOR_CODEX.md` dosyasını oku.
2. `PROJECT_MASTER_CONTEXT.md` dosyasını oku.
3. `CODEX_LEAD_DEVELOPER_MANUAL.md` dosyasını oku.
4. `REAL_USER_TESTING_STANDARD.md` dosyasını oku.
5. `HUMAN_QA_PROTOCOL.md` dosyasını oku.
6. `INTERACTION_TESTING_GUIDE.md` dosyasını oku.
7. `BUTTON_CLICK_TESTING_STANDARD.md` dosyasını oku.
8. `OUTPUT_VALIDATION_STANDARD.md` dosyasını oku.
9. `VISUAL_SCREENSHOT_QA_GUIDE.md` dosyasını oku.
10. `QA_ACCEPTANCE_CHECKLIST.md` dosyasını oku.
11. `CODEX_CURRENT_PRIORITY.md` dosyasını oku.

Sonra gerçek kullanıcı QA döngüsünü çalıştır:

- Ana Sayfa açılır.
- Etiket Modelleri açılır.
- Etiket Studio açılır.
- Toplu Etiket açılır.
- Yazdırma Sırası açılır.
- Etiket Çıktıları açılır.
- Ayarlar açılır.

Etiket Modelleri'nde gerçek click testi yapılır:

- Yenile
- Tasarım Görseli Yükle
- Yeni Model Ekle
- Kart seçimi
- Etiket Hazırla
- Studio'da Düzenle
- Önizle
- Görsel Bağla
- Filtreler
- Teknik Mod

Etiket Studio'da gerçek interaction testi yapılır:

- İsim alanı mouse ile taşınır.
- Tarih alanı mouse ile taşınır.
- Not alanı mouse ile taşınır.
- Köşeden resize yapılır.
- Kenardan resize yapılır.
- Zoom %100, %150 ve %200 modlarında tekrar denenir.
- Arrow ile 0.1 mm hareket test edilir.
- Shift+Arrow ile 1 mm hareket test edilir.
- Alt+Arrow ile 0.05 mm hareket test edilir.

Output testi yapılır:

- PDF/PNG oluşturulur.
- PDF preview açılır.
- PNG preview açılır.
- Yazdırma sırasına eklenir.
- Queue'da doğru dosya olduğu doğrulanır.

Başarı için:

- Butonlar sessiz kalmamalı.
- Yanlış teknik editör açılmamalı.
- `selectedModel` doğru taşınmalı.
- Drag sonrası `x/y` değişmeli.
- Resize sonrası `width/height/font_size` değişmeli.
- PDF/PNG canvas ile aynı olmalı.
- Queue son doğrulanmış dosyayı almalı.
- Direct print kapalı kalmalı.
- CorelDRAW, Illustrator, RDWorks, yazıcı ve lazer tetiklenmemeli.

Çalıştırılacak komutlar:

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
.venv\Scripts\python.exe scripts\capture_webui_screenshots.py
.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py
```

Eğer test fail olursa:

- Durma.
- Hatayı bul.
- Kodu düzelt.
- Testi tekrar çalıştır.
- Screenshotı tekrar al.
- P0/P1 hata kalmayana kadar devam et.

Test sonunda şu raporu oluştur:

`TEST_COMMAND_REAL_USER_QA_REPORT.md`

Raporda şunlar olsun:

- Hangi sayfalar test edildi?
- Hangi butonlar test edildi?
- Hangi butonlar sorunluydu?
- Ne düzeltildi?
- Drag/resize sonucu ne?
- PDF/PNG sonucu ne?
- Queue sonucu ne?
- Çalıştırılan komutlar ve sonuçları
- Screenshot yolları
- P0/P1 kaldı mı?
- Kalan riskler

Eğer P0/P1 hata kalmadıysa şunu yaz:

"test komutu tamamlandı, P0/P1 hata yok."

Eğer P0/P1 hata kaldıysa "tamamlandı" deme. Kalan hataları açıkça yaz ve mümkünse düzeltmeye devam et.
