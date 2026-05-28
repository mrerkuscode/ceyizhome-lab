# 04 — Kütüphane Veri Tabanı

## Dosya: `data/dxf_library.json`

scan_library tarafından otomatik oluşturulan/güncellenen JSON index. Manuel düzenleme önerilmez (scan üzerine yazar).

## Şema

```json
{
  "version": 1,
  "updated_at": "2026-05-28T13:30:00",
  "entries": {
    "<ascii_name>": {
      "name": "Ümit",                    // Türkçe display
      "ascii_name": "umit",
      "size_group": "70x40",
      "file_path": "assets/dxf_library/70x40/umit.dxf",
      "bbox_mm": [70.0, 40.0],
      "added_date": "2026-05-28T13:30:00",
      "modified_date": "2026-05-28T13:30:00",
      "status": "active",                // veya "unreadable"
      "source": "leyla_corel_manual",
      "is_compound": false,              // "Ahmet & Mehmet" true
      "letter_count": 4,
      "readable": true,
      "read_error": "",
      "entity_types": ["SPLINE"],
      "entity_count": 1,
      "has_spline": true,
      "closed_paths": 1,
      "insunits_code": 5,
      "mm_per_unit": 10.0,
      "bbox_warning": ""
    },
    ...
  }
}
```

## Public API (`dxf_library_api.py`)

| Fonksiyon | Açıklama |
|---|---|
| `scan_library(project_root)` | Tüm klasörleri yeniden tarar, index üretir, eski entry'leri silinmiş kabul eder |
| `list_library(project_root)` | Sıralı entry listesi |
| `search_library(project_root, query)` | Friendly + ASCII isim substring araması |
| `find_library_entry(project_root, name_or_ascii)` | Exact lookup (ASCII'ye normalize ederek) |
| `library_summary(project_root)` | Toplam, grup başına, okunamayan, uyarılı sayım |
| `resolve_name_for_order(project_root, name)` | Sipariş için: FOUND / MISSING_DESIGN / UNREADABLE |
| `api_list / api_search / api_find / api_refresh / api_resolve_for_order` | Bridge wrapper'ları |

## REST/Bridge slot'ları (`bridge.py`)

8 slot eklendi:
- `dxfLibraryList()` → tüm liste + summary
- `dxfLibrarySearch(q)` → arama
- `dxfLibraryFind(name)` → tek lookup
- `dxfLibraryRefresh()` → manuel scan
- `dxfLibraryResolveForOrder(name)` → sipariş eşleştirme
- `dxfLibraryStartWatcher()` → watcher daemon başlat
- `dxfLibraryStopWatcher()` → watcher daemon durdur
- `dxfLibraryWatcherStatus()` → çalışıyor mu, watchdog yüklü mü

## Scan akışı

1. `assets/dxf_library/{70x40,80x40,100x40}/*.dxf` glob
2. Her dosya için:
   - Filename `[a-z0-9_]+` mı? → değilse uyarı + atla
   - ASCII isim duplicate mı? → ikinciyi atla, uyarı
   - `read_dxf_file` ile parse, bbox, units
   - `_make_entry` ile entry oluştur (önceki added_date korunur)
   - `bbox_matches_group` ile bbox uyarısı kontrol
3. Önceki index'te olan ama yeni scan'de olmayan entry'ler "removed" listesine
4. `data/dxf_library.json` üzerine yaz

## Test sonucu

```
scan_library: 2 entries
  ayse | Ayşe | 70x40 | bbox [70.0, 40.0]
  umit | Ümit | 70x40 | bbox [10.907, 7.212] | warn: bbox 70x40 grup aralığına uymuyor

list/search:
  search('umit') → 1 match
  search('ayş')  → 1 match (case-insensitive + ASCII normalize)
  find('Ümit')  → entry returned
  find('Mücahit') → None

summary:
  total=2, per_group={'70x40': 2, '80x40': 0, '100x40': 0}
  unreadable=0, with_warnings=1, ezdxf_available=True
```

## Olay-olası senaryolar

| Senaryo | Davranış |
|---|---|
| Leyla yeni DXF atar | Watcher (active ise) → 1s debounce → scan → index güncellenir |
| Leyla bir DXF günceller | Watcher → scan → entry updated; bbox değişti ise uyarı yenilenir |
| Leyla bir DXF siler | Watcher → scan → entry removed list'e gider |
| Leyla yanlış klasöre atar (80x40 için 70x40'ı tutar) | Scan kabul eder, uyarı verir; eşleştirme yine isimle çalışır |
| Filename Türkçe karakterli | Reddedilir, uyarı verilir, index'e girmez |
| DXF bozuk | `readable=false`, `status=unreadable`, hata mesajı |
| 2 boyut grubunda aynı ASCII isim | İkincisi atlanır, uyarı (uniqueness across all groups) |

## Performans

ümit.dxf (589 control point SPLINE) parse + flatten + bbox = ~80ms. Tipik 500 ismi tarama: ~40 saniye (cold). Index dosyaya yazılır, sonraki API çağrıları milisaniyelik.
