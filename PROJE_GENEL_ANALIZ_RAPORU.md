# Proje Genel Analiz Raporu

Tarih: 2026-05-20

## Mimari

- Aktif uygulama `src/webui/index.html`, `src/webui/app.js`, `src/webui/styles.css` üzerinden PySide6 WebEngine içinde çalışıyor.
- JS tarafı vanilla WebView yapısında; React/TSX aktif değil.
- Backend fonksiyonları `src/webui_backend/bridge.py` ile Qt WebChannel üzerinden UI'ya açılıyor.
- Trendyol, toplu üretim, isim kesim, yazdırma sırası ve model yönetimi ayrı Python servis modüllerinde tutuluyor.
- Eski `src/desktop/web_ui` klasörü `LEGACY_NOT_USED.md` ile pasif işaretli; aktif WebView burayı kullanmıyor.

## Ana Modüller

- Trendyol Siparişleri: `trendyol_api.py` ve `trendyol_mapping_api.py` ile sipariş, soru, kanıt, ürün eşleştirme ve üretime aktarım akışı var.
- Etiket Studio: `app.js`, `label_api.py`, `template_api.py`, `label_designer/*` üzerinden model seçimi, canlı alanlar, PDF/PNG ve queue akışları var.
- Toplu Üretim Studio: `bulk_label_api.py` ve `combined_production_api.py` ile Excel satırları, galeri, seçili üretim ve isim kesim entegrasyonu var.
- İsim Kesim: `combined_production_api.py` içinde 800x600 mm layout/export, SVG/DXF/PDF/PNG manifest ve RDWorks güvenlik bilgisi var.
- Yazdırma Sırası: `print_queue_api.py` ve frontend queue UI ile güvenli yazdırma akışı var.

## Layout Bulguları

- Proje tek dosyalı büyük WebView UI kullandığı için layout kuralları çoğunlukla `styles.css` sonunda merkezi override olarak uygulanıyor.
- Ana kabuk `.app-shell`, `.sidebar`, `.main` ve sayfa özel body class'larıyla yönetiliyor.
- Operasyon sayfalarında `max-width` daraltması büyük ölçüde kaldırılmış.
- Sidebar desktop'ta grid alanı olarak yer kaplıyor; mobilde overlay/drawer mantığına geçiyor.
- Trendyol, Toplu Üretim, Etiket Studio ve İsim Kesim için ayrı responsive override blokları mevcut.

## Performans Bulguları

- `src/webui/app.js` monolitik ve büyük; bu yüzden liste render yolları limitli/debounce'lu kalmalı.
- Trendyol sipariş listesinde `TRENDYOL_ORDER_RENDER_LIMIT = 50` ile DOM şişmesi sınırlandırılmış.
- Toplu Üretim galerisinde test sözleşmesi 100 kartın DOM'a basılmasını bekliyor; gerçek virtualization daha sonra test sözleşmesiyle birlikte yapılmalı.
- İsim Kesim ve RDWorks export tarafı backend'de gerçek dosya hazırlıyor; lazer/RDWorks otomatik başlatılmıyor.

## Yapılan Analiz Otomasyonu

- `scripts/project_code_audit.py` eklendi.
- Çıktı: `output/2026-05-20/project_code_audit/PROJECT_CODE_AUDIT.json`
- Markdown çıktı: `output/2026-05-20/project_code_audit/PROJECT_CODE_AUDIT.md`
- NPM script: `npm run test:project-audit`

## Git Durumu

- Mevcut git deposunda commit geçmişi yok.
- `production-bot` klasörü git tarafından untracked görünüyor.
- Bu nedenle değişiklikler commit/diff geçmişine göre değil, dosya bazında raporlandı.

## Test Script Durumu

- Var olan scriptler: `test`, `test:unit`, `test:extraction`, `test:trendyol`, `test:trendyol-live-audit`, `test:trendyol-operator-worklist`, `test:release`, `test:long`.
- Eklenen script: `test:project-audit`.
- `build`, `lint`, `typecheck` scriptleri package.json içinde yok.
