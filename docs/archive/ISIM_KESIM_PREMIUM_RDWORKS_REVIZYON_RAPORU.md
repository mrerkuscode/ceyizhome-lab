# İsim Kesim Premium RDWorks Revizyon Raporu

Tarih: 2026-05-20

## Yapılan Değişiklikler

- İsim Kesim ekranı `Ceyizhome Lab · İsim Kesim` kimliğiyle yeniden düzenlendi.
- Üst açıklama alanı kompakt status chip yapısına alındı.
- İsim kaynak paneli ana canvas alanından kaldırıldı; Manuel İsim, Excel/Toplu ve Yapıştır aksiyonları command bar'a taşındı.
- Sol araç çubuğu 56 px ikon-only üretim rayına dönüştürüldü.
- Ana çalışma alanı canvas-first düzene geçirildi; sağ panel collapsible inspector olarak çalışıyor.
- Ruler yerleşimi yeniden hizalandı; sağ üst `800 / mm` çakışması engellendi.
- Çalışma alanına 15 mm safe margin eklendi ve yeşil kesikli sınır olarak gösterildi.
- Varsayılan UI ve backend nesting margin değeri 15 mm yapıldı.
- Seçili isim için modern mavi selection box, corner handle, rotate handle ve ölçü etiketi eklendi.
- OpenType preview CSS'i İsim Kesim outline yazılarına uygulandı: `liga`, `clig`, `calt`, `kern`, `salt`.
- Export önceliği ve güvenlik davranışı korundu: RDWorks/lazer otomatik başlatılmaz, sadece dosya hazırlanır.

## Düzeltilen Dosyalar

- `src/webui/index.html`
- `src/webui/app.js`
- `src/webui/styles.css`
- `src/webui_backend/combined_production_api.py`

## Üretim Güvenliği

- Farklı isimler birbirine bağlanmıyor.
- Preview objelerine `data-no-inter-name-bridge="true"` ve `data-outline-export="fonttools-path"` işaretleri eklendi.
- Backend manifest `inter_name_connection_forbidden: true` ve `internal_weld_scope: SINGLE_NAME_ONLY` üretmeye devam ediyor.
- Weld mantığı isimler arası değil, tek ismin kendi içindeki kopuk parça/nokta problemleri için korunuyor.

## Export / Path Sonucu

Son RDWorks doğrulama çıktısı:

- SVG: `output/2026-05-20/name_cut/isim_kesim_batch_2026-05-20_182358.svg`
- DXF: `output/2026-05-20/name_cut/isim_kesim_batch_2026-05-20_182358.dxf`
- PDF: `output/2026-05-20/name_cut/isim_kesim_preview_2026-05-20_182358.pdf`
- PNG: `output/2026-05-20/name_cut/isim_kesim_preview_2026-05-20_182358.png`
- Manifest: `output/2026-05-20/name_cut/name_cut_manifest_182358.json`

Manifest sonucu:

- `text_to_path_status`: `OUTLINED_PATHS_WITH_FONTTOOLS`
- `text_to_outline_status`: `OUTLINED_PATHS_WITH_FONTTOOLS`
- `thickening_status`: `TRUE_POLYGON_OFFSET_WITH_PYCLIPPER`
- `rdworks_auto_opened`: `false`
- `laser_started`: `false`

## Test Sonuçları

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m py_compile src\webui_backend\combined_production_api.py`: geçti.
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py`: geçti.

## Screenshot

- Ana İsim Kesim / Lazer preview: `output/2026-05-20/rdworks_name_cut_ready/laser_layout_preview.png`
- RDWorks export paneli: `output/2026-05-20/rdworks_name_cut_ready/rdworks_export_panel.png`

## Kalan Notlar

- Preview tarafı CSS/OpenType destekli canlı görünüm sağlar; gerçek üretim export tarafında fontTools path/outline kullanılır.
- Inspector dar ekranlarda otomatik gizlenir, masaüstü genişlikte aç/kapatılabilir.
- 15 mm safe margin artık UI ve backend export varsayılanı olarak aynı değerdedir.
