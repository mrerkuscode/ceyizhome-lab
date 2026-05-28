# 07 — UI Entegrasyonu

## Yeni: Veri Bakımı → DXF Kütüphane kartı

Konum: `src/webui/index.html` (Veri Bakımı kartının altına `<article class="card dxf-library-card">`)

Bölümler:
- **Açıklayıcı badge'ler**: Klasör yapısı, dosya adı kuralı, "Algoritma yok", "Operatör onayı zorunlu"
- **Toolbar**: 
  - "Kütüphaneyi Tara" (manual rescan)
  - "Otomatik İzlemeyi Başlat" (watcher toggle)
  - Arama inputu
- **Summary tablosu**: Toplam, 70x40, 80x40, 100x40, Okunamayan, Uyarılı, ezdxf availability
- **Liste**: her DXF için isim, boyut grubu, bbox, entity türü, uyarı satırı (varsa)

## JavaScript fonksiyonları (`src/webui/app.js`)

Eklenen fonksiyonlar:
| Fonksiyon | Görev |
|---|---|
| `setDxfLibraryStatus(msg, tone)` | Üst durum çubuğu |
| `refreshDxfLibrary()` | Bridge'e refresh, tarama sonrası yeniden list |
| `loadDxfLibraryList()` | Bridge'den listeyi çek, render |
| `renderDxfLibraryList()` | DOM'a list render (search filter dahil) |
| `toggleDxfLibraryWatcher()` | Watcher toggle (start/stop) |
| `dxfLibraryLookupForName(name, cb)` | Tek isim için lookup helper (Studio'da, Trendyol'da kullanılabilir) |

State: `dxfLibraryState = { entries, summary, watcherRunning, lastError }`

İlk load: `openSettingsSubpage('data-maintenance')` çağrıldığında otomatik `loadDxfLibraryList()` tetiklenir.

## Bridge slot'ları (`src/webui_backend/bridge.py`)

8 yeni slot:
```python
@Slot(result=str) def dxfLibraryList()           # tüm liste + özet
@Slot(str, result=str) def dxfLibrarySearch(q)   # arama
@Slot(str, result=str) def dxfLibraryFind(name)  # tek lookup
@Slot(result=str) def dxfLibraryRefresh()        # manuel scan
@Slot(str, result=str) def dxfLibraryResolveForOrder(name)  # sipariş için
@Slot(result=str) def dxfLibraryStartWatcher()   # watcher başlat
@Slot(result=str) def dxfLibraryStopWatcher()    # watcher durdur
@Slot(result=str) def dxfLibraryWatcherStatus()  # is_running + available
```

## CSS (`src/webui/styles.css`)

Eklendi:
- `.dxf-library-card` toolbar layout
- `.dxf-library-summary` grid (auto-fit 120px+ kolonlar)
- `.dxf-library-stat` kart (ok / warn / bad tone)
- `.dxf-library-list` scroll'lu container (max 360px)
- `.dxf-library-row` her DXF için satır (ok / warn / bad arkaplan)
- `.dxf-library-group` boyut grubu chip
- `.dxf-library-warn` uyarı satırı (amber)
- `.dxf-library-empty` boş durum placeholder

## Test (manuel, browser'sız harness'ta otomatize edilemez)

Frontend integrity check'leri PASS:
- `data-settings-panel="dxf-library"` HTML'de ✅
- `refreshDxfLibrary()` HTML butonunda ✅
- `toggleDxfLibraryWatcher()` HTML butonunda ✅
- `function refreshDxfLibrary` JS'de ✅
- `function dxfLibraryLookupForName` JS'de ✅
- `.dxf-library-card` CSS'te ✅

## Bilinen sınırlamalar (sonraki sprintler)

1. **Studio (İsim Kesim) sayfasında lookup widget yok** — `dxfLibraryLookupForName` helper'ı ekli ama Studio'ya tüketici eklenmedi. Bu, mevcut name-cut sayfasının yeniden mimarisi gerektiriyor; Step 7 dışına çıkacak iş.
2. **Trendyol sipariş satırlarında rozet yok** — sipariş listesinde her satır için "DXF kütüphanede" / "Çiz bekliyor" rozetleri sonraki sprintte. Backend kısmı hazır (`build_name_cut_production_scene` `dxf_library_status` döndürüyor); frontend render entegrasyonu kaldı.
3. **DXF Upload UI yok** — operatör şu an dosyaları manuel olarak `assets/dxf_library/<grup>/` klasörüne atıyor. Sürükle-bırak yükleme widget'i sonraki sprintte. Bu kasıtlı; Leyla zaten Corel'den export ediyor, klasöre kopyalama tek tıklama.
4. **Watcher Qt signal entegrasyonu yok** — watcher arka planda çalışıyor, UI eski state'i gösterebilir. "Kütüphaneyi Tara" tekrar tıklamak hep güncel veriyi getiriyor.
