# Performans ve Stabilite Raporu

Tarih: 2026-05-20

## Frontend Mimarisi

- Aktif UI vanilla JS/CSS ile tek WebView icinde calisiyor.
- Ana giris noktasi `src/webui/index.html`, `src/webui/app.js`, `src/webui/styles.css`.
- Buyuk operasyon ekranlari ayni `app.js` icinde render edildigi icin en kritik risk gereksiz liste re-render'lari.
- Trendyol siparis listesi ilk 50 kayda render limiti uyguluyor.
- Toplu Uretim galerisi su an mevcut UI testleri geregi 100 karti DOM'a basiyor.
- Layout tarafinda sidebar/main/drawer icin merkezi CSS override bloklari mevcut ve responsive gate ile dogrulaniyor.

## Backend Mimarisi

- Backend PySide6 WebChannel bridge uzerinden cagrilan Python servislerinden olusuyor.
- Trendyol siparis/soru senkronu `src/webui_backend/trendyol_api.py` icinde.
- Excel/toplu galeri `src/webui_backend/bulk_label_api.py` icinde.
- Etiket + isim kesim birlesik uretim ve RDWorks export `src/webui_backend/combined_production_api.py` icinde.
- Agir islemler guvenlik acisindan otomatik makine baslatmiyor; cikti dosyasi ve manifest hazirliyor.

## Bulunan Performans Riskleri

- Monolitik `src/webui/app.js` uzun vadede parcali modullere ayrilmali.
- Her tus vurusunda anlik render yapan arama alanlari kullaniciya donma hissi verebilir.
- Toplu galeri icin gercek sanallastirma henuz yok; test sozlesmesi guncellenmeden uygulanmasi mevcut akislari bozabilir.
- Trendyol sync, toplu thumbnail/render ve lazer export gibi uzun isler icin kalici job/progress altyapisi daha fazla genisletilmeli.

## Uygulanan Optimizasyonlar

- `debounceRender` ortak yardimci fonksiyonu eklendi.
- Trendyol arama inputu kisa debounce ile render ediyor.
- Toplu Uretim galeri aramasi kisa debounce ile render ediyor.
- Mevcut direkt render fonksiyonlari korundu; manuel cagri ve test akislari bozulmadi.
- `scripts/project_code_audit.py` eklendi; aktif UI, npm scriptleri, CSS layout riskleri ve backend bridge kabiliyetlerini raporluyor.

## Guvenlik Sinirlari

- Lazer otomatik baslatilmiyor.
- RDWorks otomatik kesim baslatmiyor.
- Direkt yazdirma otomatik acilmiyor.
- Trendyol uretim ve soru akislari mevcut endpoint/fonksiyonlarla korunuyor.
- Eksik `build/lint/typecheck` scriptleri varmis gibi raporlanmadi.

## Test Sonuclari

- `npm run test:project-audit`: gecti.
- `.venv\Scripts\python.exe scripts\verify_project_responsive_layout.py`: gecti.
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py`: gecti.
- `npm run test:extraction`: 16/16 gecti.
- `npm run test:trendyol`: gecti.
- `npm run test`: gecti.
- `.venv\Scripts\python.exe -m pytest -q`: 189 passed.

## Screenshot ve Audit Ciktilari

- `output/2026-05-20/project_code_audit/PROJECT_CODE_AUDIT.json`
- `output/2026-05-20/project_code_audit/PROJECT_CODE_AUDIT.md`
- `output/2026-05-20/responsive_layout/RESPONSIVE_LAYOUT_AUDIT.json`
- `output/2026-05-20/responsive_layout/trendyolOrders_1920.png`
- `output/2026-05-20/responsive_layout/trendyolOrders_1366.png`
- `output/2026-05-20/responsive_layout/bulkLabel_1920.png`
- `output/2026-05-20/responsive_layout/bulkLabel_1366.png`
- `output/2026-05-20/responsive_layout/label_1920.png`
- `output/2026-05-20/responsive_layout/label_1366.png`
- `output/2026-05-20/responsive_layout/nameCutStudio_1920.png`
- `output/2026-05-20/responsive_layout/nameCutStudio_1366.png`

## Kalan Riskler ve Devam Onerileri

- Toplu galeri icin testleri sanallastirilmis DOM davranisina gore guncelleyip virtualized grid eklemek en yuksek performans kazancidir.
- Trendyol sync ve toplu render/export islemleri icin kalici job/progress yapisi bir sonraki buyuk stabilite adimidir.
- `build`, `lint`, `typecheck` npm scriptleri eklenirse CI kalitesi daha net hale gelir.
