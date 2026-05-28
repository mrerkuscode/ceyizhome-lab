# 01 — DXF Okuma Altyapısı (ezdxf)

## Bağımlılıklar

Sistem öncesi kurulu değildi. Bu sprintte eklendi:
- `ezdxf 1.4.4` — DXF parse + SPLINE flattening + bbox
- `watchdog 6.0.0` — opsiyonel klasör izleyici

Kurulum:
```
pip install ezdxf watchdog
```

## Modül: `src/webui_backend/dxf_library_api.py`

İki ana fonksiyon:

### `read_dxf_file(path) -> DxfReadResult`

Parse + metadata. Asla hata yükseltmez — `error` field'ına yazar.

**Desteklenen entity'ler:** SPLINE, POLYLINE, LWPOLYLINE, LINE, ARC, CIRCLE

**Header okuma:** `$INSUNITS` → mm dönüşümü
- 0 → 1.0 (unitless, mm varsay)
- 1 → 25.4 (inch)
- 4 → 1.0 (mm)
- 5 → 10.0 (cm)
- 6 → 1000.0 (meter)

**Bbox:** `ezdxf.bbox.extents(msp)` — SPLINE'ı flattening ile doğru ölçer (eski POLYLINE-only parser yapamıyordu).

**Return değer:**
```python
DxfReadResult(
    path=str,
    readable=bool,
    error=str,
    entity_types=tuple[str, ...],
    entity_count=int,
    insunits_code=int,
    mm_per_unit=float,
    bbox_mm=(width, height),
    bbox_raw=(xmin, ymin, xmax, ymax),  # raw units
    closed_paths_estimate=int,
    has_spline=bool,
)
```

### `dxf_to_svg_path_data(path) -> dict`

DXF → tek SVG path string. `_corel_reference_override_payload` bunu çağırıp transform ediyor.

**Strateji:**
- SPLINE → `entity.flattening(0.01)` ile polyline yaklaşımı (M L L … Z)
- LWPOLYLINE / POLYLINE → vertex listesinden M L … Z
- LINE → M A L B
- CIRCLE → 32-step polyline (yaklaşım)
- ARC → açı bölmesine göre polyline
- Diğer entity'ler (TEXT, HATCH) → sessizce atlanır

Bir entity parse'ında hata olursa onu atlayıp devam eder; `error` field'a not düşülür.

## Test (ümit.dxf, SPLINE-only, 589 control point)

```
Önce: extract_dxf_path_data(ümit.dxf) → "" (eski parser SPLINE'ı görmüyordu)
Sonra: read_dxf_file(ümit.dxf):
   readable=True
   entity_types=('SPLINE',)
   has_spline=True
   insunits_code=5 (cm)
   mm_per_unit=10.0
   bbox_mm=(10.907, 7.212)
   closed_paths_estimate=1

dxf_to_svg_path_data(ümit.dxf):
   path_data: 14131 char SVG path (M -9.13 14.91 L … Z, 700+ noktalar)
   mm_per_unit: 10.0
   bbox_mm: (10.907, 7.212)
   error: ""
```

ümit.dxf test ölçeği üretim için küçük (10.9×7.2mm); Leyla'nın canlı dosyaları 70×40 olacak. Sistem bbox uyarısı veriyor, kabul ediyor (operator karar verir).

## CLAUDE.md uyumu

- Modül sadece okur; lazer veya yazıcı tetiklemez
- Auto-print, auto-laser, RDWorks tetiklenmez
- Hata: error field, raise yok — production pipeline crash etmez
