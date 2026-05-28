# 06 — Eski Algoritmalar Default OFF

## Karar (Leyla, 2026-05-28)

6 ay denenmiş jeneratif name-cut algoritmaları rafa kalkıyor. Code silinmez (geri-alınabilir), sadece default davranış değişir.

Rafa kalkanlar:
- `targeted_stroke_weld` (`_targeted_stroke_weld_contours`)
- `_welded_baseline_support_contours` (support_line autonomous weld)
- `_smart_bridge_same_name_contours` (bridge engine)
- `_initial_letter_connection_reinforcement_contours`
- `_designer_letter_flow_bridge_same_name_contours`
- `_designer_mark_bridge_contours_for_text`
- `AI_LASER_QUALITY_*` candidate selection
- Contour offset cascade (0.65 algoritmik)
- `internal_corel_like_vector_engine` / `ai_designer_advisor`

## Uygulama: tek master flag

`_auto_repair_name_cut_item` başına eklendi (line 6470+):

```python
def _auto_repair_name_cut_item(item, cfg):
    legacy_enabled = _truthy_setting(
        item.get("use_legacy_name_cut_algorithms", cfg.get("use_legacy_name_cut_algorithms")),
        False,  # DEFAULT
    )
    if not legacy_enabled:
        return {
            "contours": [], "raw_contours": [], "offset_contours": [],
            "bridge_contours": [], "welded_contours": [],
            "componentCount": 0, ...
            "repair_status": "legacy_algorithms_disabled",
            "repair_messages": [
              "legacy_name_cut_algorithms_disabled_default",
              "dxf_library_is_primary_source",
            ],
            ...
        }
    # ... eski kod aynen, dokunulmadı ...
```

Bu tek değişiklik **tüm eski algoritma fonksiyonlarının** çağrı yollarını gate eder. Fonksiyonlar dosyada hâlâ duruyor (3000+ satır kod), sadece çağrılmıyor.

## Reaktivasyon

Operatör (veya QA mühendisi) eski yola geri dönmek isterse:

```python
# Tek bir item için
item["use_legacy_name_cut_algorithms"] = True

# Veya layout config'inde (tüm scene)
cfg["use_legacy_name_cut_algorithms"] = True
```

Bu kadar. Hiçbir kod restore'a gerek yok.

## Override etkileşimi

Eski algoritma OFF olsa bile:
- DXF library lookup çalışır → bulduğunda override payload üretir → readyForCut=True
- Legacy SVG/AI exact reference library çalışır (operator-approved fallback olarak) → bulduğunda override payload → readyForCut=True
- Hiçbiri bulamazsa → `dxf_library_missing_design` repair status

Algoritma OFF olduğu için "üret + uyar" yerine "üretme + bekle" yaklaşımı.

## Test sonucu

```
Test 1 (legacy default OFF):
  repair_status: 'legacy_algorithms_disabled'
  contours: []
  applied_smart_bridge: False
  applied_weld: False
  PASS

Test 2 (legacy explicit ON):
  Algoritma çalışır (eski yol aktif)
```

End-to-end:
```
Ümit:    repair=corel_reference_exact_override (DXF lib bulundu)
Mücahit: repair=dxf_library_missing_design (algoritma yok, beklemede)
```

## Etkilenmeyen kod

| Kaynak | Durum |
|---|---|
| `assets/references/corel_name_reference_library.json` (167 ref) | Korundu, lookup zinciri içinde |
| Operator-approved name_cut_exact_golden/*.svg | Korundu, fallback yolu açık |
| `_corel_exact_reference_override_for_item` legacy fallback | Korundu, style-gated (brannboll/mochary-corel-calibrated) |
| Trendyol entegrasyonu | Etkilenmedi |
| Etiket Studio | Etkilenmedi |
| Print/Queue/Audit | Etkilenmedi |

## CLAUDE.md uyumu

- Algoritma "üretimde bekle, çizilmeden lazere gitme" sözleşmesini güçlendirir
- Operatör onayı `requiresOperatorReview=True` her durumda kalır
- Sahte success yok — algoritma çıktısı varmış gibi göstermek yerine "design missing" açıkça raporlanır
