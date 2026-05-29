# MASTER IMPLEMENTATION PLAN

## 2026-05-20 Guvenli Temel Plani

### Faz 1 - Audit ve Haritalama

- Proje mimarisi, aktif/legacy UI ve Python bridge yapisi raporlanir.
- Moduller tek tek uretim amaci ve riskleriyle belgelenir.
- Button audit baslatilir.
- Test: `npm run test`, mevcut olmayan scriptlerin kaydi, `git status --short`.

### Faz 2 - Design System Standardi

- `src/webui/design-system/README.md` ile marka, renk, spacing, typography, panel, canvas ve responsive standardi yazilir.
- Production ekranlara baglanmaz.
- Risk: Dokuman ile mevcut CSS arasindaki fark buyuk olabilir; bu kabul edilir, hedef standardi belirler.

### Faz 3 - Design Lab Referanslari

- Mevcut `designLab` iskeleti Etiket Studio, Isim Kesim, Trendyol ve Toplu Uretim onceligiyle olgunlastirilir.
- Mock/static data kullanilir.
- Test: 1920/1366 gorsel kontrol, default HTML button yok, canvas/panel oranlari okunur.

### Faz 4 - Genel Layout / Responsive Production Hazirligi

- AppShell, sidebar, main content, operation page ve right panel kurallari kucuk adimlarla uygulanir.
- Production bridge cagrilari degistirilmez.
- Test: sol menu acik/kapali, 1920/1600/1366/1280.

### Faz 5 - Etiket Studio Kurtarma

- Design Lab referansindan sadece layout ve stil standardi production'a tasinir.
- Mevcut model secme, preview, render, PDF/PNG, yazdir, siraya ekle korunur.
- Risk: mevcut CSS tekrarlarinin temizlenmesi gerekir; kucuk patch ve screenshot gate zorunlu.

### Faz 6 - Isim Kesim / Lazer Kesim

- 800x600 canvas, compact toolbar, collapsible inspector ve path/export kontrol standardi uygulanir.
- Lazer baslatma yok; sadece dosya hazirligi.
- Test: 75/300 isim, minimum bosluk, farkli isimler baglanmaz, SVG/DXF/PDF export.

### Faz 7 - Trendyol Operasyon Paneli

- Siparis kartlari, kanit drawer, AI alan ozeti ve toplu aksiyonlar design-lab referansina gore duzenlenir.
- Kargo/fatura/canli Trendyol status gibi bagli olmayan aksiyonlar pasif/uyarili kalir.
- Test: siparis sync, soru sync, kanit bagla, Excel/toplu uretime aktar.

### Faz 8 - Toplu Uretim Studio

- Stepper ve galeri varsayilan hale getirilir.
- Excel/Trendyol/Manuel kaynak ayrimi ve Turkce kolon eslestirme korunur.
- Test: 500 satir, gallery filter, lazer aktarim, queue add.

### Ilk 10 Gorev

1. Audit raporlarini tamamla.
2. Design system README'yi tamamla.
3. Button audit tablosunu genislet.
4. Existing Design Lab sekmelerini 1920/1366'da screenshot ile kontrol et.
5. AppShell/PageContainer CSS risk listesini netlestir.
6. Etiket Studio icin CSS tekrarlarini haritala.
7. Isim Kesim icin canvas/panel oran hedefini Design Lab'da netlestir.
8. Trendyol butonlarini gercek/kismi/pasif olarak UI copy planina ayir.
9. Toplu Uretim galerisi icin virtualization/cache ihtiyacini teknik plana yaz.
10. Ilk production patch'i sadece genel layout standardi ile sinirla.

### Production Entegrasyon Stratejisi

- Her sayfa once Design Lab'da goruntu olarak oturur.
- Sonra production'a kucuk ve geri alinabilir patch ile tasinir.
- Her patch sonrasinda test ve screenshot alinmadan sonraki modüle gecilmez.
- Fake success yasak; fonksiyon yoksa pasif veya acik uyarili.

### 2026-05-20 Test Komutlari Sonucu

- `npm run test`: PASSED. Quick health audit raporu: `output/2026-05-20/project_health/PROJECT_HEALTH_AUDIT.md`.
- `npm run build`: package.json icinde mevcut degil. `npm run build --if-present` no-op olarak tamamlandi.
- `npm run lint`: package.json icinde mevcut degil. `npm run lint --if-present` no-op olarak tamamlandi.
- `npm run typecheck`: package.json icinde mevcut degil. `npm run typecheck --if-present` no-op olarak tamamlandi.
- `node --check src/webui/app.js`: PASSED.
- Production ana ekranlar yeniden tasarlanmadi; bu paket raporlar, design system dokumani ve audit baslangici ile sinirli tutuldu.
