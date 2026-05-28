# 02 — Eski Ürün Eşleştirme Sistemi (Bölüm B)

## Konum

- Veri: `data/trendyol_product_mappings.json` (36 satır) + `data/trendyol_mapping_suggestions.json` (332 öneri)
- Backend: `src/webui_backend/trendyol_mapping_api.py` (228 satır)
- UI: Trendyol > Ürün Eşleştirme tabı

## Şema (1 satır)

```json
{
  "active": true,
  "barcode": "TYBDH9DAJH6GLWUH29",
  "created_at": "2026-05-19 23:04:50",
  "default_date_text": "",
  "default_note_text": "",
  "image_url": "https://cdn.dsmcdn.com/...",
  "merchant_sku": "merchantSku",
  "model_key": "",
  "model_name": "",
  "model_path": "",
  "name_cut_style": "Mochary Personal Use Only",
  "name_cut_width_mm": 300.0,
  "product_name": "Kutulu Cam Çikolata Kız İsteme...",
  "production_type": "name_cut",
  "quantity_source": "line_quantity",
  "stock_code": "merchantSku",
  "updated_at": "2026-05-19 23:04:50"
}
```

Sample: `11_data_samples/trendyol_product_mappings_sample.json`

## Görev

Trendyol siparişi (barcode + merchant_sku) → **hangi label model + ne tür üretim** sorusunu cevaplar.

`production_type` 3 değer alıyor:
- `name_cut` — sadece isim kesim
- `label_and_name_cut` — etiket + isim kesim (mevcut 35/36)
- `label` — sadece etiket (mevcut mapping suggestions'da 327 öneri böyle)

`model_key` boş ise: sadece name_cut. Doluysa: label_designer template yolu (`model_path`).

## Önerilerle ilişki

`trendyol_mapping_suggestions.json` 332 satır — AI tarafından önerilen yeni mapping'ler. Hepsi `status=needs_review`, operatör onaylamamış. Operatör onay verince `trendyol_mapping_api.approve_*` ile asıl `trendyol_product_mappings.json` listesine eklenir (upsert).

## Backend slot'ları (`bridge.py`)

| Slot | Görev |
|---|---|
| `approve_trendyol_mapping_suggestion(id)` | Suggestion'ı asıl listeye al |
| `upsert_trendyol_mapping(payload)` | Doğrudan ekle/güncelle |
| `cache_trendyol_product_image(url)` | Görsel önbellek |
| `apply_trendyol_question_to_suggestion(id, qid)` | Soru kanıtını bağla |

## Bypass / sahte success geçmişi

- `_initial_verification_status` (`trendyol_api.py:1933`) eskiden mapping bulundu + AI confidence ≥0.85 → otomatik VERIFICATION_READY. **Quick Wins'te kapatıldı.** Şimdi `VERIFICATION_WAITING_APPROVAL` döner.
- 0.55 frontend "Güvenli öneri" eşik → 0.72'ye hizalandı (Quick Wins).
- "Kaynağa Dön" sahte buton (`app.js:19083`) disable edildi.

## Yeni sistem (v2.0) ile ilişki

**Çakışma yok, tamamlayıcı:**

| Soru | Cevap kaynak |
|---|---|
| "Bu barcode hangi label model?" | **Eski sistem** (`trendyol_product_mappings.json`) — model_path |
| "Bu barcode'ün üretiminde kaç isim, hangi boyut, kaç etiket adet?" | **Yeni sistem** (`product_definitions.json`) — name_config, label_config |
| "Bu sipariş için DXF kütüphanede çizim var mı?" | **DXF library** (`data/dxf_library.json`) |
| "Bu siparişi operatör onayladı mı?" | `_is_verified_ready` |

İki sistem aynı SKU'yu ortak kullanır ama farklı yönleri tanımlar:
- Eski: barcode → model + production_type (Trendyol'a özel teknik eşleştirme)
- Yeni: SKU → tüm üretim parametreleri (Trendyol'dan bağımsız, abstract ürün tanımı)

Gelecekte birleşebilir ama şu an iki tablo iyi sebepten ayrı:
- Trendyol mapping AI tarafından doldurulabilir (cache + suggestion)
- Product definition Leyla'nın manuel/Excel yetkisinde, validation strict

## Veri Hacmi

- `trendyol_product_mappings.json`: 36 onaylı + 332 önerilen
- Son güncel: 2026-05-19 23:04:50
- Dolu / boş: dolu

## Bilinmeyen / test edilemedi

- Operatör 332 öneriden kaçını onaylama eğiliminde — historical metrik yok
- AI suggestion confidence dağılımı (suggestion'lar `status=needs_review` ama confidence backed olarak görünmüyor)
- Mapping silme yolu var mı (sadece `active=false` toggle görünüyor)

## Risk / Uyarı

- 🟡 332 öneri backlog — operatör review'i gerektiriyor
- 🟢 Onaylı mapping'ler stabil, 36 satır son 1 gündür dokunulmamış
- 🟢 production_type dağılımı dengeli (label vs name_cut vs label_and_name_cut)
