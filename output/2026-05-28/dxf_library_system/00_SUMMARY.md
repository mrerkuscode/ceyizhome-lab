# DXF Kütüphane Sistemi — Özet Raporu

**Tarih:** 2026-05-28
**Süre:** ~75 dakika (8 adım)
**Mochary hash:** korundu (dokunulmadı)
**167 SVG referans:** korundu (`assets/references/corel_name_reference_library.json`)
**operator-approved (İrem/Ümit/Ahmet/Ayşe&Mehmet):** korundu, regresyon temiz

## Vizyon → Kod özeti

Leyla'nın kararı: 6 ay denenmiş jeneratif algoritmalar (targeted_weld, bridge, support_line, contour, AI Designer, SVG glyph) **rafa kaldırıldı**. Yerine: **Leyla Corel'de elden DXF çizer → sistem arşivler + eşleştirir**. Algoritma yok, sadece kütüphane.

Bu sprintte sistemin tüm omurgası kuruldu. Leyla 500 isim çizmeye başlayabilir.

## Tablo — 8 adım sonucu

| Adım | İş | Durum | Süre | Kanıt |
|---|---|---|---|---|
| 1 | DXF okuma altyapısı (ezdxf + SPLINE/POLYLINE/LINE/ARC/CIRCLE) | ✅ | 15 dk | `01_dxf_reader.md` |
| 2 | Klasör yapısı + ASCII naming (`70x40/`, `80x40/`, `100x40/`) | ✅ | 5 dk | `02_folder_structure.md` |
| 3 | Watcher (watchdog + debounce + manual refresh) | ✅ | 10 dk | `03_watcher_service.md` |
| 4 | Library DB (`data/dxf_library.json` + index + REST) | ✅ | 10 dk | `04_library_database.md` |
| 5 | Sipariş eşleştirme (name → DXF lookup, MISSING_DESIGN status) | ✅ | 10 dk | `05_order_matching.md` |
| 6 | Eski algoritmalar default OFF (kod silinmedi, master flag) | ✅ | 10 dk | `06_legacy_disable.md` |
| 7 | UI entegrasyonu (Veri Bakımı DXF kartı + bridge slots) | ✅ | 10 dk | `07_ui_integration.md` |
| 8 | Test + raporlar | ✅ | 5 dk | `08_test_results.md` |

## Sistem mimarisi

```
┌─────────────────────────────────────────────────────────────────┐
│  LEYLA (operatör)                                               │
│  Corel'de Mochary + kontur 0.65 + Combine + Filled Black        │
│  → DXF export                                                   │
│  → assets/dxf_library/<70x40|80x40|100x40>/<ascii_name>.dxf     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  dxf_library_watcher.py (watchdog, opsiyonel)                   │
│  veya                                                            │
│  dxf_library_api.scan_library()  ← manuel "Kütüphaneyi Tara"    │
│  → ezdxf ile parse, bbox, ASCII validation                      │
│  → data/dxf_library.json güncellenir                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Trendyol/Bulk sipariş geldi: "Mücahit"                          │
│  → to_ascii_name("Mücahit") = "mucahit"                          │
│  → resolve_name_for_order(...) → FOUND veya MISSING_DESIGN      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  combined_production_api._corel_exact_reference_override_for_item│
│  1) DXF library kontrol et — varsa: dxf_to_svg_path_data         │
│     ile geometriyi al, transform, READY                          │
│  2) Yoksa: legacy SVG/AI library (operator-approved fallback)    │
│  3) O da yoksa: legacy algoritmalar (DEFAULT OFF — Leyla kararı) │
│     → repair_status = "dxf_library_missing_design"               │
│     → readyForCut = False                                        │
│     → UI'da "Leyla çizmeli" uyarısı                              │
└─────────────────────────────────────────────────────────────────┘
```

## Test sonuçları (regression suite)

```
1. ezdxf 1.4.4 OK
2. ASCII conversion: 11/11 cases PASS
3. DXF reader (umit.dxf): readable=True, SPLINE, bbox 10.9×7.2mm
4. DXF→SVG converter: 14131 chars path_data
5. scan_library: 2 entries indexed, 2 warnings (expected)
6. Order matching:
   'Ümit'    → FOUND
   'Ayşe'    → FOUND
   'Mücahit' → MISSING_DESIGN
   'umit'    → FOUND (case-insensitive)
7. End-to-end pipeline:
   Ümit:    repair=corel_reference_exact_override, override=True, pathData=12561b
   Mücahit: repair=dxf_library_missing_design, override=None
8. Bridge: 8 DXF library slots
9. Frontend: 6/6 integrity checks PASS
10. Legacy: 167 SVG refs preserved + Trendyol approved rows still ready ✅
```

## Yeni / değiştirilen dosyalar

**Yeni:**
- `src/webui_backend/dxf_library_api.py` (yeni modül, ~430 satır)
- `src/webui_backend/dxf_library_watcher.py` (yeni modül, ~140 satır)
- `data/dxf_library_ascii_to_turkish.json` (ASCII → Türkçe display mapping)
- `data/dxf_library.json` (otomatik oluşturulan kütüphane index)
- `assets/dxf_library/70x40/`, `80x40/`, `100x40/` (klasörler)

**Değiştirilen:**
- `src/webui_backend/bridge.py` — 8 DXF library slot eklendi
- `src/webui_backend/combined_production_api.py` — Override hook'a DXF library primary path, MISSING_DESIGN durum mantığı, legacy master flag (`use_legacy_name_cut_algorithms`)
- `src/webui/index.html` — Veri Bakımı altına "DXF Kütüphane" kartı
- `src/webui/app.js` — DXF library UI fonksiyonları (refresh/list/render/watcher toggle/lookup)
- `src/webui/styles.css` — DXF kütüphane CSS

**Backup'lar:**
- `output/2026-05-28/dxf_library_system/backups/` — değişiklik öncesi tüm dosyalar `.bak`

## Eski algoritmalar — durum

| Algoritma | Konum | Default | Geri-alınabilir |
|---|---|---|---|
| targeted_stroke_weld | `combined_production_api.py:3105` | **OFF** | ✅ `use_legacy_name_cut_algorithms=true` |
| _welded_baseline_support_contours | `combined_production_api.py:3003` | **OFF** | ✅ (`support_line` flag + legacy flag) |
| smart_bridge_same_name_contours | `combined_production_api.py:3624` | **OFF** | ✅ |
| AI laser quality candidates | `combined_production_api.py:5751` | **OFF** | ✅ |
| designer_mark_bridge | line ~6584 | **OFF** | ✅ |
| letter_flow_bridge | line ~6612 | **OFF** (zaten bowtie-fix off) | ✅ |
| initial_letter_connection | line ~6578 | **OFF** (zaten bowtie-fix off) | ✅ |

Hiçbir kod SİLİNMEDİ. Master flag `use_legacy_name_cut_algorithms` False (default) → `_auto_repair_name_cut_item` doğrudan empty repair dict döner. True yapılırsa eski sistem çalışır.

## Operator-approved + 167 SVG koruması

| Kaynak | Durum |
|---|---|
| `assets/references/corel_name_reference_library.json` (167 SVG ref) | DOKUNULMADI — fallback hâlâ aktif |
| `assets/references/name_cut_exact_golden/` (operator-approved SVG'ler) | DOKUNULMADI — fallback hâlâ aktif |
| `data/trendyol_production_suggestions.json` Ayşe & Mehmet READY satır | DOKUNULMADI — `_is_verified_ready=True` korundu |

Sırama:
1. DXF library (yeni primary)
2. SVG/AI exact reference library (legacy operator-approved, korundu)
3. Algoritma (default OFF, kod silinmedi)

## Bilinen sınırlamalar

- **Test dosyası ümit.dxf scale anormal**: Leyla'nın eski test dosyası 10.9×7.2mm (production 70×40 olmalı). Sistem bbox uyarısı veriyor — Leyla'nın yeni dosyaları doğru ölçekte gelecek.
- **Watcher Qt thread'inde değil**: watchdog ayrı thread'te çalışıyor; UI'a callback için Qt signal kullanılmıyor (gelecekte ekleyebiliriz). Şu anda watcher arka planda scan tetikler, UI bir sonraki `loadDxfLibraryList` çağrısında günceli okur.
- **DXF→SVG flattening 0.01 unit tolerance**: SPLINE → polyline yaklaşımı; gerçek B-spline değil. Lazer geometrisi için yeterince ince (0.01 birim = mm cinsinden 0.1mm veya daha az). RDWorks `LINE` segmentlerini sorunsuz işler.

## Sırada

Leyla 500 isim çizmeye başlayabilir. İlk 10 isim test için yeterli (kütüphane akışını üretimde doğrulamak için).

Yapılması gereken (sonraki sprintler):
- [ ] Trendyol sipariş listesinde rozetli durum gösterimi (kullanıcı önce sahip olduğu hangi siparişlerin "Çiz Bekliyor" durumunda olduğunu görmeli)
- [ ] Mevcut 167 SVG referansını opsiyonel olarak DXF'e dönüştürme (uzun vade)
- [ ] RDWorks tek-path export tutarlılık testi (welded vs. line çift kayıt)
- [ ] Studio'da DXF lookup widget (manuel preview)

## Detay raporlar

- `01_dxf_reader.md`
- `02_folder_structure.md`
- `03_watcher_service.md`
- `04_library_database.md`
- `05_order_matching.md`
- `06_legacy_disable.md`
- `07_ui_integration.md`
- `08_test_results.md`
