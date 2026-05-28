# 05 — Sipariş Eşleştirme

## Tek nokta entry: `resolve_name_for_order(project_root, name)`

```python
def resolve_name_for_order(project_root, requested_name):
    """
    Returns:
      {
        "status": "FOUND"|"MISSING_DESIGN"|"UNREADABLE",
        "ascii_name": str,
        "friendly_name": str,
        "entry": entry|None,
        "message": str,
      }
    """
```

Akış:
1. `to_ascii_name(name)` → normalize
2. `find_library_entry(...)` → exact ASCII lookup
3. Bulunmadıysa → `MISSING_DESIGN`
4. Bulunduysa ama `readable=False` → `UNREADABLE`
5. Aksi → `FOUND` + entry

## Üretim hattına bağlantı (`combined_production_api.py`)

`_corel_exact_reference_override_for_item` hook'una eklendi (line 5645 civarı). **DXF library PRIMARY** — diğer fallback'lerden ÖNCE çalışır:

```python
def _corel_exact_reference_override_for_item(item, cfg, style):
    if _load_exact_reference_path_data is None:
        return None
    text = ...
    if not text:
        return None
    # PRIMARY: DXF library
    if dxf_lookup_enabled and _dxf_library_api is not None:
        lookup = _dxf_library_api.resolve_name_for_order(PROJECT_ROOT, text)
        if lookup["status"] == "FOUND":
            entry = lookup["entry"]
            dxf_path = PROJECT_ROOT / entry["file_path"]
            payload = _corel_reference_override_payload(
                ...,
                reference_path=dxf_path,
                source="dxf_library",
            )
            if payload:
                return payload
    # FALLBACK: legacy SVG/AI exact-reference library (operator-approved)
    ...  # mevcut akış, dokunulmadı
```

`source="dxf_library"` parametresi `_corel_reference_override_payload`'i ezdxf yoluna yönlendirir (legacy POLYLINE-only parser SPLINE okuyamadığı için ayrı dal).

## MISSING_DESIGN ele alımı

Override None döndüğünde + legacy algoritmalar OFF + DXF library lookup MISSING_DESIGN → item:

```python
{
  "repair_status": "dxf_library_missing_design",
  "readyForCut": False,
  "requiresOperatorReview": True,
  "exactReferenceRequired": True,
  "dxf_library_status": "MISSING_DESIGN",
  "dxf_library_message": "'Mücahit' DXF kütüphanesinde yok; Leyla çizmeli.",
  "dxf_library_ascii_name": "mucahit",
  "review_warning": "'Mücahit' DXF kütüphanesinde yok. Leyla bu ismi çizip assets/dxf_library/ altına atana kadar üretime alınamaz.",
  "source": "dxf_library_missing",
  ...
}
```

UI bu alanları okuyup operatör'e "Çiz Bekliyor" durumunu gösterebilir.

## Compound isim

Yusuf Kerem → `yusuf_kerem.dxf`
Ahmet & Mehmet → `ahmet_mehmet.dxf`

**Politika** (Leyla'nın isteği): Compound isimler **tek dosya** olmalı. Leyla Corel'de birleşik tasarım yapar.

Bölme yok:
- `to_ascii_name("Yusuf Kerem")` = `"yusuf_kerem"` → tek lookup
- `yusuf_kerem.dxf` varsa FOUND
- Yoksa MISSING_DESIGN (Leyla compound çizmeli)

## Edge case'ler

| Sipariş | ASCII | Davranış |
|---|---|---|
| `"Mücahit"` | `mucahit` | normal lookup |
| `"  Ümit  "` | `umit` | trim |
| `"Yusuf Kerem"` | `yusuf_kerem` | space → underscore |
| `"D'Andre"` | `dandre` | apostrof strip |
| `"Ahmet 2"` | `ahmet_2` | rakam korunur |
| `""` | `""` | MISSING_DESIGN, "İsim boş" |
| `"123"` | `123` | ASCII alfanumeric → kabul (rakamlar serbest) |
| `"---"` | `""` | (sadece punctuation) → MISSING_DESIGN |

## Test sonuçları

```
Order matching:
  'Ümit'      → FOUND
  'Ayşe'      → FOUND
  'Mücahit'   → MISSING_DESIGN
  'umit'      → FOUND  (case-insensitive)
  'X-unknown' → MISSING_DESIGN

End-to-end pipeline (build_name_cut_production_scene):
  Ümit:    repair=corel_reference_exact_override, override=True, pathData=12561b
  Mücahit: repair=dxf_library_missing_design, override=None, pathData=0b, ready_for_cut=False
```

Üretim hattının sonu:
- Ümit → readyForCut=True, kullanıcı onayı ile lazere gidebilir
- Mücahit → readyForCut=False, operatöre uyarı; Leyla çizip eklemeden lazere gitmez

## CLAUDE.md uyumu

Lookup başarılı bile olsa:
- `requiresOperatorReview=True` korunur
- Operatör onayı olmadan fiziksel yazdırma/lazer çalışmaz
- Direct print kapalı kalır
- Lookup salt-okur: dosya sistemi okur, başka aksiyon yok
