# 07 — Queue System (Bölüm G)

## Konum

- Backend: `src/webui_backend/print_queue_api.py` (25 KB, 582 satır) + `name_cut_queue_api.py` (21 KB, 446 satır)
- Veri: `data/print_queue.json` (boş), `data/name_cut_queue.json` (2 satır), `data/name_cut_transfer_history.json` (boş), `data/name_cut_export_history.json` (2 satır)
- UI: `<section id="printQueue">` "Yazdırma Sırası"

## Slot'lar

| Slot | Görev |
|---|---|
| `clear_print_queue` | Tümünü temizle |
| `add_pdf_output_to_print_queue` / `add_label_outputs_to_print_queue` | Manuel ekleme |
| `mark_queue_item_printed/pending/delivered` | Statü |
| `save_name_cut_queue_items(payload_json)` | İsim kesim queue persist |
| `update_name_cut_queue_item_status(item_id, status)` | Statü değiştir |
| `check_name_cut_queue_duplicate(...)` | Çift kayıt kontrolü |
| `prepare_manual_print(item_id, profile_id)` | Yazdırma hazırla |

## Veri (gerçek)

### `data/print_queue.json` — boş

```json
[]
```

### `data/name_cut_queue.json` — 2 satır

Sample: `11_data_samples/name_cut_queue_full.json`

### `data/name_cut_export_history.json` — 2 satır

Audit log'da görünen export'lara karşılık geliyor (`namecut_export_*` event türleri).

## CLAUDE.md uyumu

- Print Queue mock değil, gerçek state
- Direct print kapalı: queue'a giren bir satır otomatik yazıcıya gitmez
- "Güvenli Yazdır" butonu her satır için ayrı manuel onay

## Bypass / sahte success durumu

- **Faz1 #3 — `prepare_manual_print` bridge yoksa "ok" callback**: re-scan **CLEAN**. ✅
- "Kaynağa Dön" sahte buton (`app.js:19083`): Quick Wins sprintinde disable edildi. ✅

## Bilinmeyen / test edilemedi

- `check_name_cut_queue_duplicate` mantığı (hash karşılaştırma mı? semantic match mi?)
- Queue item history accessors (audit ile çarpışma var mı)

## Risk / Uyarı

- 🟢 Queue boş veya az satır — production'da büyüyecek
- 🟢 Direct print koruması aktif
- 🟢 Manuel onay zorunlu
- 🟡 Name cut queue 2 satır var ama transfer history boş — export edilmiş ama transfer'e geçilmemiş
