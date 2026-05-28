# 04 — DXF Kütüphane Durumu (Bölüm D)

## Konum

- Veri: `data/dxf_library.json` (index), `data/dxf_library_ascii_to_turkish.json` (19 entry display map)
- Klasörler: `assets/dxf_library/{70x40,80x40,100x40}/`
- Backend: `src/webui_backend/dxf_library_api.py` (666 satır, 25 KB) + `dxf_library_watcher.py` (168 satır)
- UI: Ayarlar → Veri Bakımı → "DXF Kütüphane" kartı

Sample: `11_data_samples/dxf_library_full.json`

## Klasör inventory

| Klasör | DXF Dosya |
|---|---|
| `assets/dxf_library/70x40/` | 3 (ayse.dxf, ayşe.dxf [TR isim rejected], umit.dxf) |
| `assets/dxf_library/80x40/` | 0 |
| `assets/dxf_library/100x40/` | 0 |

`ayşe.dxf` (TR karakter dosya adı) scan'de uyarı veriyor: `dosya adı ASCII değil`. Sistem reddeder, indexe almaz.

## Index durumu

`data/dxf_library.json` son güncel: 2026-05-28T15:47:47

| ASCII | Display | Grup | Bbox (mm) | Uyarı |
|---|---|---|---|---|
| ayse | Ayşe | 70x40 | 70.0 × 40.0 | — ✓ |
| umit | Ümit | 70x40 | 10.9 × 7.2 | ⚠️ Bbox grup aralığına uymuyor (test dosyası, üretim ölçeği değil) |

## Backend slot'ları (8)

| Slot | Görev |
|---|---|
| `dxfLibraryList(include_archived?)` | Liste + özet |
| `dxfLibrarySearch(query)` | Substring arama |
| `dxfLibraryFind(name)` | Exact lookup |
| `dxfLibraryRefresh()` | Manuel scan |
| `dxfLibraryResolveForOrder(name)` | Sipariş eşleştirme |
| `dxfLibraryStartWatcher` | watchdog daemon başlat |
| `dxfLibraryStopWatcher` | Daemon durdur |
| `dxfLibraryWatcherStatus` | Çalışma + watchdog availability |

## ASCII normalize kuralı

`to_ascii_name` (`dxf_library_api.py`):
- Türkçe harf mapping (ç→c, ğ→g, ı→i, İ→i, ö→o, ş→s, ü→u)
- NFKD ile diakritik atımı
- Apostrof family stripped (D'Andre → dandre)
- Geri kalan punctuation → underscore (Yusuf Kerem → yusuf_kerem)

19 entry seed mapping: `ahmet`, `ahmet_mehmet`, `ayse`, `ayse_mehmet`, `cagri`, `ekrem`, `elif`, `emre`, `eylul`, `helin`, `ilkay`, `irem`, `mehmet`, `mucahit`, `sukran`, `sumeyye`, `umit`, `yusuf_kerem`, `zeynep`.

## Watcher (watchdog)

- watchdog 6.0.0 yüklü
- 3 klasörü gözler (recursive=False)
- 1.0s debounce
- Thread-safe, hata swallow
- Default OFF; operatör "Otomatik İzlemeyi Başlat" butonu ile aktif eder
- Test edildi: 3 olay (startup, add, delete) doğru tetiklendi

## Üretim entegrasyonu (override hook)

`combined_production_api.py:_corel_exact_reference_override_for_item` (5645+):
1. **DXF library (yeni primary)** — style-agnostic; bulunduğunda override payload
2. **SVG/AI exact reference (legacy)** — style-gated fallback (brannboll / mochary-corel-calibrated)
3. **Algoritma** — `use_legacy_name_cut_algorithms` False (default), çağrılmaz

`_corel_reference_override_payload` source="dxf_library" parametresi ezdxf yoluna yönlendirir → SPLINE'lar 0.01 tolerance ile polyline'a flatten edilir → SVG path data üretilir.

## Önceki 167 SVG ref ile ilişki

`assets/references/corel_name_reference_library.json` 167 entry korunuyor:
- 3 entry `approved=true + exactNameMatch=true` (operator-approved subset)
- Geri kalan 164 entry style references veya pending review
- DXF library bulamadığında bu fallback olarak devreye girer (legacy gated)

## CLAUDE.md uyumu

- Salt okuma + index yazma (lazer tetiklemez)
- `requiresOperatorReview=True` her override payload'da set ediliyor — DXF kütüphanede bulunsa bile operatör onayı zorunlu
- Watcher arka plan thread'inde, ana UI thread'ini bloklamaz

## Veri Hacmi

- Index: 2 aktif entry, 1 reject (TR filename), 1 bbox warning (test dosyası)
- Ascii→Turkish map: 19 entry
- Son scan: 2026-05-28T15:47:47
- Dolu / boş: kısmen (2 entry, üretim için 500+ hedef)

## Bilinmeyen / test edilemedi

- Watcher uzun süreli stabilite (sadece kısa test yapıldı)
- 500+ entry'de scan süresi (şu an 2 entry, lineer ölçeklenmeli)
- Mevcut 167 SVG ref'in DXF'e dönüştürülme planı (ileride)

## Risk / Uyarı

- 🟡 Sadece 2 entry — Leyla başlamadan üretim çalışmaz
- 🟢 Override sırası doğru: DXF first, SVG fallback, algoritma OFF
- 🟢 167 SVG ref invariant'i korundu
- 🟡 umit.dxf test dosyası (10.9×7.2mm) production scale değil; gerçek dosyalar 70×40 olmalı
- 🟢 ayşe.dxf TR filename reddedildi (kural çalışıyor)
