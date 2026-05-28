# Ceyizhome Lab Script Engine Raporu

Tarih: 2026-05-20

## Amaç

Mochary PERSONAL USE ONLY fontunu ticari olarak dağıtmadan, sadece yerel Ceyizhome Lab kullanımında daha doğru script önizleme, lazer isim kesim ve path tabanlı export üretimi için özel bir font/render profiline bağlamak.

## Eklenen Ana Yapı

- `Ceyizhome Lab Script` ve `Ceyizhome Lab Script (Mochary)` font profili eklendi.
- Font dosyası yerel kullanım için `assets/fonts/Mochary.ttf` konumuna kopyalandı ve `.gitignore` ile dağıtım dışı bırakıldı.
- Font coverage analyzer eklendi ve UI tarafında Font Test Lab ekranına rapor verisi bağlandı.
- Script preview alanlarında OpenType özellikleri aktif edildi:
  - `liga`
  - `clig`
  - `calt`
  - `kern`
  - `salt`
- Büyük harf bağlantı düzeltme haritası eklendi.
- Noktalama ve `₺` fallback haritası eklendi.
- ScriptTextRenderer componenti eklendi.
- İsim Kesim export motoru Ceyizhome Lab Script Engine manifest bilgisi üretir hale getirildi.

## Font Analizi

Analiz edilen font: yerel `Mochary.ttf`

Font analizi sonucu:

- GSUB: `calt`, `fina`, `init`, `liga`, `salt`
- GPOS: `kern`
- Türkçe karakter kapsamı: mevcut
- Noktalama kapsamı: büyük ölçüde mevcut
- `₺` sembolü: fontta yok
- Bağlantılı büyük harf varyantları:
  - `A_con`: var
  - `F_con`: var
  - `H_con`: var
  - `X_con`: var
  - `S_con`: yok
  - `L_con`: yok
  - `M_con`: yok

Analiz çıktıları:

- `output/2026-05-20/font_lab/ceyizhome_lab_script_font_analysis.json`
- `output/2026-05-20/font_lab/ceyizhome_lab_script_font_analysis.md`
- `src/webui/data/font_analysis_mochary.json`

## Büyük Harf Bağlantı Mantığı

Doğal font varyantı olan harfler:

- `A`
- `F`
- `H`
- `X`

Manuel bridge gerektiren başlangıç harfleri:

- `S`
- `L`
- `M`
- `C`
- `Z`

Bu düzeltme ham metni değiştirmez. Sadece preview/export aşamasında uygulanır.

Özellikle test edilen kelimeler:

- `Sedel`
- `Leyla`
- `Mücahit`

Bu üç kelimede manuel büyük harf bridge durumu manifestte doğrulandı.

## Noktalama ve ₺ Mantığı

Noktalama haritası şu karakterleri kapsar:

`. , : ; ! ? - _ / & + @ ₺ ' " ( )`

`₺` sembolü fontta olmadığı için backend export tarafında fallback path konturu üretildi. Böylece `₺250` SVG/DXF/PDF/PNG export testine path olarak girdi.

## Path / Weld / Export Durumu

İsim Kesim exportunda isimler artık text olarak bırakılmıyor.

- SVG export: `<path>` içeriyor, üretim isimlerinde `<text>` yok.
- DXF export: `POLYLINE` path içeriyor.
- Manifest: `OUTLINED_PATHS_WITH_FONTTOOLS`
- Weld kapsamı: `INSIDE_EACH_NAME_ONLY`
- İsimler arası bağlantı: yok
- Her isim ayrı obje: korunuyor

Önemli güvenlik kuralı korundu:

Farklı isimler birbirine weld/bridge ile bağlanmaz. Bridge sadece aynı ismin kendi içindeki kopuk büyük harf veya noktalı harf problemleri için uygulanır.

## UI Entegrasyonu

Font Test Lab:

- Font seçimi `Ceyizhome Lab Script` profiline bağlandı.
- OpenType toggle mantığı korundu.
- Test kelimeleri eklendi:
  - `Sedel`
  - `Leyla`
  - `Mücahit`
  - `Ceyizhome`
  - `Aşk ile söz verdik`
  - `Söz & Nişan`
  - `Ayşe & Mehmet`
  - `Zeynep’in Nişanı`
  - `Özel Tasarım`
  - `₺250`
  - `Şeyma`
  - `Çağla`
  - `Gülay`
  - `İrem`

İsim Kesim:

- Font seçimine `Ceyizhome Lab Script (Mochary)` eklendi.
- Export ayarlarına şu kontroller eklendi:
  - Weld inside name
  - Export as path
  - Büyük harf düzeltmesi
  - Noktalama düzeltmesi
  - Harf aralığı
  - Kelime aralığı

## Test Sonuçları

Geçen komutlar:

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m py_compile src\webui_backend\combined_production_api.py src\webui_backend\font_analysis.py scripts\analyze_ceyizhome_script_font.py scripts\verify_ceyizhome_script_engine.py`
- `.venv\Scripts\python.exe scripts\analyze_ceyizhome_script_font.py`
- `.venv\Scripts\python.exe scripts\verify_ceyizhome_script_engine.py`
- `.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py`
- `npm run test`

Son Ceyizhome script export testi:

- Manifest: `output/2026-05-20/name_cut/name_cut_manifest_201413.json`
- SVG: `output/2026-05-20/name_cut/isim_kesim_batch_2026-05-20_201413.svg`
- DXF: `output/2026-05-20/name_cut/isim_kesim_batch_2026-05-20_201413.dxf`
- PDF preview: `output/2026-05-20/name_cut/isim_kesim_preview_2026-05-20_201413.pdf`
- PNG preview: `output/2026-05-20/name_cut/isim_kesim_preview_2026-05-20_201413.png`

Proje sağlık testi:

- Status: `PASSED`
- Rapor: `output/2026-05-20/project_health/PROJECT_HEALTH_AUDIT.md`

## Kalan Teknik Not

Preview tarafında CSS/OpenType feature kullanımı aktiftir. Export tarafı fontTools ile path/outline üretir ve manuel bağlantı/fallback konturlarını ekler. Daha ileri kalite için sonraki aşamada HarfBuzz shaping (`uharfbuzz`) eklenerek GSUB/GPOS şekillendirme export path üretimine de birebir taşınabilir.
