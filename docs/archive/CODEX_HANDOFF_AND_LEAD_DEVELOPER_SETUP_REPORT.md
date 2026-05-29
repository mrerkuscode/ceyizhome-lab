# CODEX HANDOFF AND LEAD DEVELOPER SETUP REPORT

Tarih: 2026-05-07

## Görev Adı

Codex devir teslimi ve lead developer çalışma düzeni kurulumu.

## Mevcut Sorun

Kullanıcı her küçük ürün, UI/UX, QA, grafik üretim veya yazılım kararı için dışarıdan yeni prompt almak istemiyor. Proje içinde Codex'in nasıl çalışacağını kalıcı hale getiren net rehber dosyaları gerekiyordu.

## Yapılan Kurulum

Proje köküne kalıcı rehber doküman seti eklendi. Bu dosyalar bundan sonra her görevde proje bağlamı, kalite standardı, güvenlik sınırı ve ürün vizyonu olarak kullanılacak.

## Oluşturulan Dosyalar

- `START_HERE_FOR_CODEX.md`
- `PROJECT_MASTER_CONTEXT.md`
- `CODEX_LEAD_DEVELOPER_MANUAL.md`
- `PRODUCT_VISION.md`
- `DESIGN_SYSTEM_GUIDE.md`
- `UI_UX_RULES.md`
- `GRAPHIC_AND_LABEL_DESIGN_RULES.md`
- `ENGINEERING_STANDARDS.md`
- `QA_ACCEPTANCE_CHECKLIST.md`
- `PROMPT_LIBRARY.md`
- `CODEX_CURRENT_PRIORITY.md`
- `CODEX_HANDOFF_AND_LEAD_DEVELOPER_SETUP_REPORT.md`

## Codex Bundan Sonra Nasıl Çalışacak?

Codex proje içinde Lead Developer, UI/UX Designer, grafik/etiket üretim danışmanı, QA sorumlusu, ürün yöneticisi ve release kontrol sorumlusu gibi davranacak.

Her görevde:
1. Bağlam dosyaları okunacak.
2. P0/P1 riskler önce sınıflandırılacak.
3. Küçük ve güvenli değişiklik yapılacak.
4. Regression test eklenecek veya güncellenecek.
5. Gerçek kullanıcı davranışı simüle edilecek.
6. Screenshot alınacak.
7. Kalite komutları çalıştırılacak.
8. P0/P1 kalmadan iş bitmiş sayılmayacak.

## Zorunlu Kalite Kapıları

Kapsama göre:

```powershell
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
.venv\Scripts\python.exe scripts\capture_webui_screenshots.py
.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py
```

Render/output/queue etkilenirse kalite kapıları zorunludur.

## Onay Beklemeden Yapılacak İşler

- P0/P1 hata düzeltme
- çalışmayan buton fix'i
- normal kullanıcıyı teknik ekrandan çıkarma
- UI/UX sadeleştirme
- regression test ekleme
- screenshot alma
- rapor oluşturma
- kalite kapısı çalıştırma

## Manuel Karar Gerektiren İşler

- Direct print açmak
- yazıcıyı otomatik çalıştırmak
- lazer/RDWorks otomasyonu
- Corel/Illustrator native edit'i üretim akışına almak
- kaynak AI/CDR dosyalarını değiştirmek
- büyük mimari refactor
- yeni framework/teknoloji eklemek

## Güncel Proje Öncelikleri

1. Etiket Studio drag/resize davranışını gerçek pointer event ve geometry testleriyle korumak.
2. Etiket Modelleri butonlarını gerçek click testleriyle doğrulamak.
3. Ana Sayfa'yı yalnızca küçük polish seviyesinde geliştirmek.
4. Render/output/queue zincirini gereksiz değiştirmemek.
5. Direct print, yazıcı, lazer, CorelDRAW ve Illustrator güvenlik sınırlarını korumak.

## UI/UX Etkisi

Yeni dokümanlar kullanıcıya görünmez; ürün UI'ını değiştirmez. Ancak bundan sonraki UI/UX kararlarının tutarlı ve normal kullanıcı dostu yapılmasını sağlar.

## Render/Output/Queue Etkisi

Yok. Bu görev yalnızca dokümantasyon ve çalışma standardı kurulumu yaptı.

## Güvenlik Etkisi

Güvenlik sınırları proje kökünde kalıcı ve açık hale getirildi:
- CorelDRAW açılmaz.
- Illustrator açılmaz.
- RDWorks açılmaz.
- Yazıcı çalışmaz.
- Lazer başlamaz.
- Direct print aktif edilmez.
- Kaynak AI/CDR değişmez.

## Testler

Kod veya runtime akışı değiştirilmediği için test çalıştırma zorunlu değildi. Bu görev dokümantasyon/setup kapsamındadır.

## Screenshot

UI değişikliği yapılmadığı için screenshot alınmadı.

## Kalan Riskler

P0/P1 risk yok. Gelecekteki her kod/UI görevi için `QA_ACCEPTANCE_CHECKLIST.md` ve kalite kapıları uygulanmalıdır.

## Son Karar

Devir teslimi tamamlandı. Codex bundan sonra projeyi ürün sorumlusu gibi sahiplenmek için gerekli kalıcı yönergelere sahip.
