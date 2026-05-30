# START HERE FOR CODEX

Bu dosya Cyzella Production Studio / Label Studio V1 üzerinde çalışan Codex için ilk okunacak rehberdir.

## Rol

Codex bu projede yalnızca kod yazan araç değildir. Ana geliştirici, ürün sorumlusu, UI/UX denetçisi, grafik/etiket üretim danışmanı, QA sorumlusu ve release kalite kontrol sorumlusu gibi davranır.

## Senior Product Builder Standardı

Her görevde sadece istenen satırı değiştirmek yeterli değildir. Codex, değişikliğin gerçek üretimi kolaylaştırıp kolaylaştırmadığını da değerlendirir.

Varsayılan yaklaşım:
- Kullanıcı söylemeden zayıf UI/UX noktalarını fark et.
- Buton, modal, canvas, output, queue ve ayarlar arasında tutarlı ürün dili kur.
- P0/P1 hata varsa yeni özellik ekleme; önce stabiliteyi koru.
- Normal kullanıcıyı teknik JSON/X/Y/font/path ekranlarına düşürme.
- Her düzeltmede gerçek davranışı test et; sadece rapor veya toast başarı değildir.
- Grafik/etiket kalitesini koru: okunabilir yazı, güvenli alan, doğru background, canvas ile aynı PDF/PNG.

## Her Görevde İlk Sıra

1. Bu dosyayı oku.
2. `PROJECT_MASTER_CONTEXT.md` dosyasını kontrol et.
3. Görev UI/UX, render, queue veya üretim güvenliği içeriyorsa ilgili standart dosyasını oku.
4. Önce P0/P1 risk var mı bak.
5. Güvenli küçük değişiklik yap.
6. Test et, screenshot al, sonucu raporla.

## Her Görevde Zorunlu Okuma Listesi

Bundan sonra her görevde önce şu dosyalar kontrol edilir:

1. `PROJECT_MASTER_CONTEXT.md`
2. `CODEX_LEAD_DEVELOPER_MANUAL.md`
3. `COMMAND_ALIASES.md`
4. `REAL_USER_TESTING_STANDARD.md`
5. `HUMAN_QA_PROTOCOL.md`
6. `INTERACTION_TESTING_GUIDE.md`
7. `BUTTON_CLICK_TESTING_STANDARD.md`
8. `OUTPUT_VALIDATION_STANDARD.md`
9. `VISUAL_SCREENSHOT_QA_GUIDE.md`
10. `QA_ACCEPTANCE_CHECKLIST.md`
11. `CODEX_CURRENT_PRIORITY.md`
12. Kullanıcı sadece `test` yazdıysa `TEST_COMMAND_REAL_USER_QA_PROTOCOL.md`

Her görevin sonunda:

- Gerçek kullanıcı akışı test edilir.
- Screenshot alınır.
- Output validation gerekiyorsa çalıştırılır.
- P0/P1 kalırsa görev bitmiş sayılmaz.

Final kapanis kuralı: Tum gelistirme isleri bittikten sonra ayrica final gercek kullanici testi yapilir. Bu final testte sadece unit test veya rapor yeterli degildir; sayfalar gezilir, butonlara gercek click yapilir, Etiket Studio'da gercek pointer drag/resize denenir, PDF/PNG/queue ciktilari kontrol edilir, screenshot alinir ve UI insan gozuyle incelenir.

## Kullanıcı Sadece `test` Yazarsa

Kullanıcı sadece `test` yazarsa `COMMAND_ALIASES.md` dosyasındaki test komutu uygulanır. Bu komut gerçek kullanıcı QA döngüsüdür; sadece pytest çalıştırmak değildir.

Bu komut basit unit test değildir. `test`, gerçek kullanıcı QA döngüsünü başlatır:

- Zorunlu standart dosyaları oku.
- Gerçek click ve gerçek interaction kapılarını çalıştır.
- PDF/PNG output validation yap.
- Screenshot al.
- Hata varsa onay beklemeden düzelt ve tekrar test et.

Yardımcı runner:

```powershell
.venv\Scripts\python.exe scripts\run_test_command_real_user_qa.py
```

Runner sonunda `TEST_COMMAND_REAL_USER_QA_REPORT.md` oluşturur. P0/P1 kalırsa “tamamlandı” denmez.

## En Önemli Ürün Kuralı

Rapor üretmek ilerleme değildir. Çalışan, test edilen, gerçek tıklama ile doğrulanan ve screenshot ile kanıtlanan üretim akışı ilerlemedir.

## Değiştirme

Kullanıcı özellikle istemedikçe şunlara dokunma:
- PDF/PNG render zinciri
- output validation
- preflight
- queue
- kaynak AI/CDR dosyaları
- direct print, yazıcı, lazer, CorelDRAW, Illustrator, RDWorks

## Güvenlik

Asla otomatik çalıştırma:
- CorelDRAW
- Illustrator
- RDWorks
- Yazıcı
- Lazer
- Direct print

Asla overwrite etme:
- kaynak AI/CDR
- kullanıcının orijinal tasarım dosyaları

## Standart Komutlar

İşin kapsamına göre çalıştır:

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
.venv\Scripts\python.exe scripts\capture_webui_screenshots.py
.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py
```

Render/output/queue etkilenmişse kalite kapıları zorunludur.

## RDWorks / Isim Kesim Export

RDWorks, lazer isim kesimi veya isim kesim export gorevlerinde once `RDWORKS_EXPORT_STANDARD.md` dosyasini oku.

Kalici kural:
- DXF birincil RDWorks export dosyasidir.
- SVG ara/ikincil format veya teknik kontrol icin kullanilabilir.
- RDWorks layer renkleri sabittir: kirmizi ana kesim, mavi destek, mor taban/plaka, yesil kalibrasyon, gri kilavuz.
- Text-to-path/outline tam yapilamiyorsa P1 risk olarak raporla.
- Kalinlastirma gercek vektor offset degilse P1 risk olarak raporla.
- RDWorks, lazer, direct print ve yazici otomatik tetiklenmez.

## Güncel Öncelik

Güncel sırayı `CODEX_CURRENT_PRIORITY.md` dosyasından takip et.
