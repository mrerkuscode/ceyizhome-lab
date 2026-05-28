# 03 — Watcher (Klasör İzleme Servisi)

## Modül: `src/webui_backend/dxf_library_watcher.py`

watchdog tabanlı, **opsiyonel** daemon. Sistem watcher OLMADAN da çalışır (manuel "Kütüphaneyi Tara" butonu her zaman aktif).

## API

| Fonksiyon | Davranış |
|---|---|
| `start_watcher(project_root)` | 3 klasörü gözlemeye başlar (70x40/80x40/100x40), debounce timer + immediate startup scan |
| `stop_watcher()` | Observer'ı durdurur, debounce timer iptal |
| `is_running()` | Bool |
| `watchdog_available()` | watchdog yüklü mü |
| `register_on_scan(callback)` | Her scan sonrası callback (scan thread'inde) |
| `get_last_scan_result()` | Son scan sonucu cache |

## Davranış detayı

1. **Single Observer** — 3 klasörün hepsini izler (recursive=False)
2. **Debounce**: dosya event'i sonrası 1.0s sessizlik bekler, sonra rescan. CorelDRAW DXF export'u kısa süreli birden çok event üretebilir; debounce bunları birleştirir.
3. **Thread güvenliği** — `threading.Lock()` ile state korumalı; observer kendi thread'inde, callback'ler observer thread'inden çağrılır.
4. **Hata yutma** — scan veya callback bir exception üretirse stderr'a yazar, thread crash etmez.
5. **Startup scan** — `start_watcher` 100ms sonra ilk scan'i tetikler (index fresh kalsın).

## Test sonucu

```
watchdog_available: True
initial is_running: False

start_watcher: OK
paths_watched: assets\dxf_library\70x40, 80x40, 100x40

(2s bekle — startup scan)

Olay 1: copy umit.dxf -> 80x40/test_watcher.dxf
(debounce 1s + scan)

Olay 2: delete 80x40/test_watcher.dxf
(debounce 1s + scan)

stop_watcher: OK
is_running after stop: False

Scan events received: 3
  {scanned: 2, added: 0, updated: 2, removed: 0}    # startup
  {scanned: 3, added: 1, updated: 2, removed: 0}    # add
  {scanned: 2, added: 0, updated: 2, removed: 1}    # delete
```

Watcher add + delete'i doğru tespit ediyor.

## CLAUDE.md uyumu

Watcher salt dosya sisteminden okur, hiçbir aksiyon tetiklemez:
- Yazıcıyı çağırmaz
- Lazeri tetiklemez
- RDWorks/Trendyol live action yok
- Sadece `scan_library` çağırır → `data/dxf_library.json` index dosyasını günceller

## UI bağlantısı

Bridge slot'ları:
- `dxfLibraryStartWatcher` → start_watcher
- `dxfLibraryStopWatcher` → stop_watcher
- `dxfLibraryWatcherStatus` → is_running + watchdog_available

UI'da Veri Bakımı → DXF Kütüphane kartında "Otomatik İzlemeyi Başlat" butonu. Toggle ediyor.

## Bilinen kısıtlar

- **Qt thread integration yok**: Watcher arka plan thread'inde çalışır. UI scan tamamlandığını otomatik bilemez (Qt signal entegrasyonu sonraki sprint). Şimdilik: watcher index'i güncelliyor, kullanıcı "Kütüphaneyi Tara" basınca veya panel'i yeniden açınca güncel veriyi görüyor.
- **Network drive / Dropbox / OneDrive**: watchdog event teorisinde çalışır, ama bazı senkron klasörler debounce'tan kaçabilir. Kullanıcı bu durumda manuel "Tara" butonunu kullanmalı.
