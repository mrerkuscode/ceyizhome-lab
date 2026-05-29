# RDWorks Boolean Offset PoC Report

Tarih: 2026-05-13

## Kısa Karar

RDWorks / İsim Kesim export hattında gerçek polygon offset PoC uygulandı.

Önceki durumda kalınlaştırma yaklaşık contour expansion / stroke fallback olarak raporlanıyordu. Bu turda `pyclipper` geometri motoru eklendi ve `fontTools` ile çıkarılan yazı konturları gerçek polygon offset işleminden geçirilecek şekilde bağlandı.

Yeni manifest durumu:

```text
TRUE_POLYGON_OFFSET_WITH_PYCLIPPER
```

Bu hâlâ RDWorks'te kullanıcı kontrolü gerektirir; ancak önceki "yaklaşık contour expansion" P1 riski ana akışta kapatıldı.

## Yapılan Değişiklikler

### 1. Bağımlılık

`requirements.txt` içine eklendi:

```text
pyclipper>=1.4
```

### 2. Backend Export

Dosya:

- `src\webui_backend\combined_production_api.py`

Eklenen davranış:

- `pyclipper` varsa konturlar polygon offset motoruna gider.
- `pyclipper` yoksa eski güvenli fallback devreye girer.
- Offset motoru manifest ve DXF comment içinde açıkça raporlanır.
- SVG path stroke width, gerçek offset varsa hairline seviyesine düşürülür; kesim çizgisi artık offset path'in kendisidir.

Yeni status:

```text
TRUE_POLYGON_OFFSET_WITH_PYCLIPPER
```

Fallback status:

```text
P1_RISK_APPROX_CONTOUR_EXPANSION_NOT_TRUE_OFFSET
```

### 3. Testler

Güncellenen dosyalar:

- `tests\test_combined_production_flow.py`
- `scripts\verify_rdworks_name_cut_layout_export.py`

Yeni doğrulamalar:

- Manifest `TRUE_POLYGON_OFFSET_WITH_PYCLIPPER` taşıyor.
- DXF `OFFSET_ENGINE TRUE_POLYGON_OFFSET_WITH_PYCLIPPER` notunu taşıyor.
- SVG ve DXF path/layer yapısı korunuyor.
- Çoklu plate SVG path offset doğrulaması çalışmaya devam ediyor.

## Çalıştırılan Komutlar

```powershell
.venv\Scripts\python.exe -m pip install pyclipper
.venv\Scripts\python.exe -m py_compile src\webui_backend\combined_production_api.py scripts\verify_rdworks_name_cut_layout_export.py
.venv\Scripts\python.exe -m pytest tests\test_combined_production_flow.py -q
.venv\Scripts\python.exe scripts\verify_rdworks_name_cut_layout_export.py
.venv\Scripts\python.exe scripts\verify_combined_excel_label_and_name_cut_flow.py
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
```

## Komut Sonuçları

| Komut | Sonuç |
|---|---|
| `py_compile` | PASSED |
| `pytest tests\test_combined_production_flow.py -q` | PASSED, 4 passed |
| `verify_rdworks_name_cut_layout_export.py` | PASSED |
| `verify_combined_excel_label_and_name_cut_flow.py` | PASSED |
| `node --check src\webui\app.js` | PASSED |
| `pytest -q` | PASSED, 128 passed |
| `real_production_quality_gate.py` | PASSED |
| `final_acceptance_gate.py` | PASSED |

## Üretilen Son RDWorks Dosyaları

- `output\2026-05-13\name_cut\isim_kesim_batch_2026-05-13_224114.dxf`
- `output\2026-05-13\name_cut\isim_kesim_batch_2026-05-13_224114.svg`
- `output\2026-05-13\name_cut\isim_kesim_preview_2026-05-13_224114.pdf`
- `output\2026-05-13\name_cut\isim_kesim_preview_2026-05-13_224114.png`
- `output\2026-05-13\name_cut\name_cut_manifest_224114.json`

Screenshotlar:

- `output\2026-05-13\rdworks_name_cut_ready\name_cut_main.png`
- `output\2026-05-13\rdworks_name_cut_ready\manual_name_modal.png`
- `output\2026-05-13\rdworks_name_cut_ready\manual_name_saved.png`
- `output\2026-05-13\rdworks_name_cut_ready\laser_layout_preview.png`
- `output\2026-05-13\rdworks_name_cut_ready\rdworks_export_panel.png`
- `output\2026-05-13\combined_production_flow\laser_layout_preview.png`

## Güvenlik Teyidi

Bu PoC sırasında:

- RDWorks otomatik açılmadı.
- Lazer otomatik başlamadı.
- Yazıcı direct/silent çalışmadı.
- Direct print aktif edilmedi.
- CorelDRAW/Illustrator otomasyonu tetiklenmedi.
- Kaynak AI/CDR dosyaları değiştirilmedi.

## Teknik Notlar

Bu uygulama:

- Yazıyı `fontTools` ile path/outline'a çevirir.
- Flatten edilmiş polygon konturlarını `pyclipper` ile offsetler.
- DXF/SVG path export üretir.

Sınırlar:

- Bu, Bezier seviyesinde curve offset değil, flatten edilmiş polygon offsettir.
- RDWorks'te gerçek kesimden önce layer, path ve ölçü kontrolü kullanıcı tarafından yapılmalıdır.
- Harf iç delikleri ve çok karmaşık script fontlarda manuel RDWorks önizleme hâlâ önemlidir.

## Son Karar

RDWorks isim kesim kalınlaştırma işi önceki P1 risk seviyesinden üretime daha yakın bir PoC seviyesine çıkarıldı.

Ana etiket MVP tarafında bilinen P0/P1 yok.

RDWorks için kalan risk artık "offset motoru yok" değil; "polygon offset üretildi, RDWorks'te gerçek kesimden önce manuel path/layer/ölçü kontrolü gerekir" seviyesindedir.
