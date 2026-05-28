# 06 — Toplu Üretim (Bölüm F)

## Konum

- Backend: `src/webui_backend/bulk_label_api.py` (28 KB)
- UI: `<section id="bulkLabel">` "Toplu Üretim Studio" (sidebar Yeni badge'i ile)
- Sidebar: `data-page="bulkLabel"`

## Slot'lar

| Slot | Görev |
|---|---|
| `bulk_generate_and_add_to_queue()` | Tüm Excel satırlarını işle |
| `bulk_generate_selected_and_add_to_queue(row_numbers_json)` | Seçili satırlar |
| `bulk_generate_gallery_items_and_add_to_queue(items_json)` | Gallery seçim |

## Akış

1. Excel seç (`select_excel`, `set_selected_excel`)
2. Bulk Production Studio'da satırlar görünür
3. Seçili satırları kuyruğa at (gerçek print başlatmaz; sadece queue'ya ekler)
4. Print Queue'da operatör manuel "Güvenli Yazdır"a basar (her satır için ayrı onay)

## Bypass / sahte success durumu

- **Faz1 #7 — Toplu Üretim "Üretime Al" stub**: re-scan **CLEAN**. UI'da `Üretime Al` butonu bulunamadı (boş veya zaten çıkarılmış). ✅
- Bulk gallery edit + print full mode: Production_audit_log'da 1 `bulk_validation_completed` event var (`status=WARNING`, "Excel kolon eşleştirme kontrolü tamamlandı"). Çalışıyor.

## Veri Hacmi

- 3 ana slot
- Production audit log: 1 bulk_validation_completed event
- Excel input: `input/siparisler.xlsx` (settings.yaml'de tanımlı)

## Bilinmeyen / test edilemedi

- Tipik Excel satır sayısı (1 mi 100 mü?)
- Bulk gallery preview modal (`bulkPreviewModalStage`) aktif mi kalıntı mı

## Risk / Uyarı

- 🟢 "Üretime Al" sahte buton temizlendi
- 🟢 Bulk → Queue → manuel yazdır akışı CLAUDE.md uyumlu (otomatik yazdırma yok)
