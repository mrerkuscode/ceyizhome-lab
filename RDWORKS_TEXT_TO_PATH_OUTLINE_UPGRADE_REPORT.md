# RDWorks Text-to-Path Outline Upgrade Report

Tarih: 2026-05-13

## Özet

RDWorks / İsim Kesim modülündeki önceki en büyük P1 risklerden biri, isimlerin export içinde text/font bağımlı kalabilmesiydi. Bu turda bu risk fontTools tabanlı outline üretimiyle kapatıldı.

Sistem artık uygun Windows fontu bulunduğunda:

- SVG export içinde isimleri `<text>` yerine path olarak üretir.
- DXF export içinde isimleri `TEXT` yerine `POLYLINE` / `VERTEX` contour olarak üretir.
- Manifest içinde `text_to_path_status: OUTLINED_PATHS_WITH_FONTTOOLS` yazar.

RDWorks otomatik açılmadı, lazer otomatik başlamadı, direct print aktif edilmedi.

## Ne Değişti?

Dosya: `src/webui_backend/combined_production_api.py`

Eklenen ana parçalar:

- `fontTools.ttLib.TTFont` ile font dosyası okuma.
- Windows font resolver:
  - `segoesc.ttf`
  - `segoescb.ttf`
  - `segoepr.ttf`
  - `segoeprb.ttf`
  - `georgia.ttf`
  - `arial.ttf`
- Glyph contour çıkarma için `_FlattenGlyphPen`.
- Text contour hesaplama ve mm ölçüsüne scale etme.
- SVG path üretimi.
- DXF POLYLINE üretimi.
- Manifest text-to-path durumunu gerçek contour sonucu üzerinden hesaplama.

## SVG Davranışı

Başarılı durumda:

- `CUT_NAME_OUTLINE` layer altında path üretilir.
- Path üzerinde `data-outline="fonttools-path"` işareti bulunur.
- Text fallback yalnızca contour üretimi başarısız olursa kullanılır.

## DXF Davranışı

Başarılı durumda:

- `CUT_NAME_OUTLINE` layer altında `POLYLINE` / `VERTEX` contour yazılır.
- DXF içinde `TEXT_TO_PATH OUTLINED_PATHS_WITH_FONTTOOLS` açıklaması bulunur.
- Text fallback yalnızca contour üretimi başarısız olursa kullanılır.

## Kalınlaştırma / Offset Durumu

Kalan P1 teknik risk:

- `P1_RISK_APPROX_CONTOUR_EXPANSION_NOT_TRUE_OFFSET`

Yani yazı artık outline/path olarak üretilebiliyor ve offset değeri contour noktalarına yaklaşık dışa genişletme olarak uygulanıyor. Ancak bu matematiksel olarak gerçek geometrik offset/stroke-to-path motoru değildir. Bu yüzden kullanıcı RDWorks’te layer, path ve offset etkisini manuel kontrol etmelidir.

## Test Güncellemeleri

Güncellenen test ve scriptler:

- `tests/test_combined_production_flow.py`
- `scripts/verify_rdworks_name_cut_layout_export.py`
- `scripts/verify_combined_excel_label_and_name_cut_flow.py`

Doğrulananlar:

- `text_to_path_status` artık `OUTLINED_PATHS_WITH_FONTTOOLS`.
- SVG içinde `data-outline="fonttools-path"` var.
- DXF içinde `POLYLINE` var.
- DXF içinde `TEXT_TO_PATH OUTLINED_PATHS_WITH_FONTTOOLS` var.
- RDWorks otomatik açılmadı.
- Lazer otomatik başlamadı.
- Direct print aktif edilmedi.

## Çalışan Komutlar

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m pytest -q` -> 128 passed
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py` -> PASSED
- `.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py` -> PASSED
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` -> PASSED
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` -> PASSED

## Üretilen Örnek Paket

Son doğrulamada örnek çıktı paketi:

- `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_162742.dxf`
- `output/2026-05-13/name_cut/isim_kesim_batch_2026-05-13_162742.svg`
- `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_162742.pdf`
- `output/2026-05-13/name_cut/isim_kesim_preview_2026-05-13_162742.png`
- `output/2026-05-13/name_cut/name_cut_manifest_162742.json`

## Güvenlik Teyidi

- RDWorks otomatik açılmadı.
- Lazer otomatik başlamadı.
- Yazıcı otomatik çalışmadı.
- Direct print aktif edilmedi.
- CorelDRAW / Illustrator çağrılmadı.
- Kaynak AI/CDR dosyaları değiştirilmedi.

## Kalan Risk

Tek kalan RDWorks P1 teknik risk gerçek geometrik offset/stroke-to-path dönüşümüdür. Yaklaşık contour expansion uygulanır, fakat bu tamamlanana kadar isim kesim paketi “RDWorks’te manuel kontrol gerekli” uyarısıyla kullanılmalıdır.
