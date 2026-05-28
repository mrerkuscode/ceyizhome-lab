# CODEX LEAD DEVELOPER ONBOARDING REPORT

Tarih: 2026-05-07

## Görev Adı

Codex'in Cyzella Production Studio / Label Studio V1 için üst düzey baş geliştirici, ürün sorumlusu, UI/UX, QA ve release kalite rolüne alınması.

## Okunan Mevcut Raporlar

Raporlar `output/2026-05-07` altında incelendi:
- `FINAL_PROJECT_AUDIT_REPORT.md`
- `FINAL_FIX_IMPLEMENTATION_REPORT.md`
- `FINAL_TEST_RESULTS_REPORT.md`
- `FINAL_BUTTON_ACTION_MATRIX.md`
- `FINAL_SCREENSHOT_QA_REPORT.md`
- `FINAL_KNOWN_LIMITATIONS_AND_ROADMAP.md`
- `HOME_PAGE_PRODUCTION_CENTER_REDESIGN_REPORT.md`

Özet:
- Final raporlarda P0/P1 hata yok olarak raporlanmış.
- Canvas -> PDF/PNG -> Queue kalite kapısı geçmiş.
- Çoklu model kabul testi geçmiş.
- Ana Sayfa üretim merkezi olarak geliştirilmiş.
- Etiket Modelleri ve Etiket Studio için gerçek click/pointer kalite kapıları daha önce eklenmiş.
- Manuel kullanıcı gözleminin rapordan üstün olduğu proje standardı olarak korunmalı.

## Oluşturulan veya Güncellenen Dosyalar

Güncellenen dosyalar:
- `PROJECT_MASTER_CONTEXT.md`
- `CODEX_LEAD_DEVELOPER_MANUAL.md`
- `PRODUCT_VISION.md`
- `DESIGN_SYSTEM_GUIDE.md`
- `UI_UX_RULES.md`
- `QA_ACCEPTANCE_CHECKLIST.md`
- `PROMPT_LIBRARY.md`
- `CODEX_CURRENT_PRIORITY.md`
- `START_HERE_FOR_CODEX.md`

Yeni dosyalar:
- `ARCHITECTURE_MAP.md`
- `KNOWN_LIMITATIONS_AND_ROADMAP.md`
- `CODEX_LEAD_DEVELOPER_ONBOARDING_REPORT.md`

## Codex Bundan Sonra Nasıl Çalışacak?

Codex sadece kod yazan bir araç gibi davranmayacak. Varsayılan rol:
- Lead Software Developer
- UI/UX Designer
- Grafik üretim danışmanı
- QA/Test sorumlusu
- Ürün yöneticisi
- Release kontrol sorumlusu
- Güvenlik ve üretim kalitesi sorumlusu

Her görevde sıralama:
1. İlgili proje bağlamı ve raporları oku.
2. İşi P0/P1/P2/P3 olarak sınıflandır.
3. P0/P1 varsa önce onu düzelt.
4. Küçük, güvenli, test edilebilir değişiklik yap.
5. Test veya regression kontrolü ekle.
6. Gerçek kullanıcı davranışını simüle et.
7. Screenshot al.
8. Kalite komutlarını çalıştır.
9. Rapor oluştur.
10. Kendi çıktısını tekrar kontrol et.

## Zorunlu Kalite Kapıları

Kapsama göre çalıştırılacak komutlar:

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
.venv\Scripts\python.exe scripts\capture_webui_screenshots.py
.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py
```

Render/output/queue etkilenirse kalite kapıları zorunludur.

## Onay Beklemeden Yapılacaklar

Güvenlik sınırlarını ihlal etmeyen ve ürün hedefiyle uyumlu ise Codex onay beklemez:
- P0/P1 bug fix
- Çalışmayan buton düzeltmesi
- selectedModel, route, modal, queue veya live input regression düzeltmesi
- Normal kullanıcı için UI/UX sadeleştirme
- Teknik detayları Teknik Mod arkasına alma
- Test ve screenshot ekleme
- Rapor oluşturma

## Manuel Karar Gerektiren Konular

Şu konularda otomatik ilerlenmez:
- Direct print açmak
- Yazıcıyı otomatik çalıştırmak
- Lazer/RDWorks otomasyonu bağlamak
- Corel/Illustrator native edit'i üretim akışına almak
- Kaynak AI/CDR dosyasını değiştirmek veya overwrite etmek
- Büyük mimari refactor
- Yeni framework veya büyük teknoloji eklemek

## Kısa Lead Developer Değerlendirmesi

Mevcut durum iyi bir MVP seviyesine taşınmış görünüyor:
- Etiket Studio render/output/queue zinciri kalite kapısından geçmiş.
- PDF/PNG çıktılarında background ve İsim/Tarih/Not piksel kanıtıyla doğrulanmış.
- Queue doğrulanmış output yolu kullanıyor.
- Direct print kapalı.
- Teknik editör normal kullanıcı akışından izole edilmiş.
- Ana Sayfa daha güçlü üretim başlangıç merkezi olmuş.

Yine de ürün sorumlusu gözüyle dikkat edilmesi gerekenler:
- Kullanıcı manuel testte "çalışmıyor" diyorsa rapor sonucu geçersiz sayılmalı ve gerçek davranış tekrar test edilmeli.
- Etiket Studio drag/resize regression testleri gerçek geometry değişimini korumalı.
- Etiket Modelleri buton testleri sadece DOM veya fonksiyon varlığı değil, gerçek route/state sonucunu doğrulamalı.
- Türkçe rapor veya terminal çıktıları gerektiğinde Python ile UTF-8 okunarak kontrol edilmeli.
- P2/P3 gelişmiş özellikler P0/P1 yoksa ele alınmalı.

## Güncel Öncelikler

1. P0/P1 stabiliteyi koru.
2. Etiket Studio drag/resize/keyboard ve final render zincirini gerçek davranışla test etmeye devam et.
3. Etiket Modelleri gerçek click ve model health UX'ini güçlendir.
4. Ana Sayfa polish dışında kabul edilebilir; render/output/queue etkilenmeden korunmalı.
5. Toplu Etiket, Yazdırma Sırası, Etiket Çıktıları ve Ayarlar sayfalarında P2 ürünleşme iyileştirmelerini roadmap sırasıyla yap.

## Bu Görevde Test Durumu

Bu görev proje yönetim dokümantasyonu ve onboarding standardı oluşturma işidir. Runtime kod, frontend davranışı, backend render, output validation veya queue zinciri değiştirilmedi. Bu nedenle uygulama testleri çalıştırılmadı.

## Güvenlik Teyidi

- CorelDRAW açılmadı.
- Illustrator açılmadı.
- RDWorks açılmadı.
- Yazıcı çalıştırılmadı.
- Lazer başlatılmadı.
- Direct print aktif edilmedi.
- Kaynak AI/CDR dosyaları değiştirilmedi.
- Render/output/queue zincirine dokunulmadı.

## P0/P1 Kaldı mı?

Bu onboarding görevinde runtime akış değiştirilmediği için yeni P0/P1 risk oluşturulmadı. Mevcut raporlar P0/P1 yok diyor; ancak manuel kullanıcı gözlemi her zaman daha yüksek önceliklidir.

## Son Karar

Codex baş geliştirici ve ürün sorumlusu çalışma standardı repo içine kalıcı olarak yazıldı. Bundan sonraki görevlerde Codex, güvenlik sınırlarını koruyarak ürünü yalnızca çalışan değil, daha hızlı, daha sade, daha güvenilir ve daha premium bir üretim aracına dönüştürme sorumluluğuyla hareket edecek.
