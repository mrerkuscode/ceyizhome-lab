# 01 — Trendyol Gerçeği ⭐

## Trendyol live durumu

| Alan | Değer | Kanıt |
|---|---|---|
| supplier_id | 1131960 | `data/trendyol_settings.json:2` |
| environment | live | `data/trendyol_settings.json:5` |
| stage | False | `data/trendyol_settings.json:4` |
| read_only_mode | True (implied, kod garantili) | `trendyol_api.py:156` |
| api_key | (maskelendi: `IO***Im`) | `data/trendyol_settings.json:3` |
| api_secret | (maskelendi: `8f***vA`) | `data/trendyol_settings.json:3` |
| ai_api_key | (maskelendi: `sk***UA`, OpenAI uyumlu) | `data/trendyol_settings.json:16` |
| ai_enabled | True | `data/trendyol_settings.json:14` |
| ai_provider | openai_compatible | `data/trendyol_settings.json:15` |
| ai_model | gpt-5-nano | `data/trendyol_settings.json:17` |
| ai_autonomous_production_enabled | True | `data/trendyol_settings.json:11` |
| ai_confidence_threshold | 0.85 | `data/trendyol_settings.json:18` |
| ai_autonomous_model_threshold | 0.72 | `data/trendyol_settings.json:12` |
| ai_autonomous_field_threshold | 0.65 | `data/trendyol_settings.json:13` |
| last_sync_at | 2026-05-19 22:40:51 | `data/trendyol_settings.json:7` |
| last_questions_sync_at | 2026-05-19 23:00:04 | `data/trendyol_settings.json:8` |
| last_questions_sync_status | OK | `data/trendyol_settings.json:9` |

**Credential güvenliği:** maskeleme `trendyol_api.py:123-126` ve `_mask` (`trendyol_api.py:2781-2786`). Backup'tan `data/trendyol_settings.json` çıkarıldı (`backup_api.py:13-23`, Quick Wins sprint çıktısı).

## Veri dosyaları (gerçek)

### `data/trendyol_questions_context.json` — 522 soru/mesaj

| Metrik | Değer |
|---|---|
| Toplam satır | 522 |
| Cevaplandı (`answered=True`) | 500 |
| Bekleyen (`status=WAITING_FOR_ANSWER`) | 22 |
| Unique sipariş | 214 |
| Unique barcode | 10 |
| Unique product_name | 43 |
| Tarih aralığı | 2026-05-13 → 2026-05-19 |
| Son 7 günde günlük dağılım | 13: 16, 14: 21, 15: 112, 16: 104, 17: 86, 18: 90, 19: 80 |

Sample: `11_data_samples/trendyol_questions_sample.json` (3 normal + 1 unanswered)

### `data/trendyol_product_mappings.json` — 36 ürün eşleştirme

| Metrik | Değer |
|---|---|
| Toplam | 36 |
| `production_type=name_cut` | 1 |
| `production_type=label_and_name_cut` | 35 |
| Tüm satırlar `active=true` | ✓ |
| Schema | barcode, merchant_sku, stock_code, model_key, model_path, model_name, production_type, default_*, name_cut_*, image_url |

Sample: `11_data_samples/trendyol_product_mappings_sample.json` (ilk 5)

### `data/trendyol_mapping_suggestions.json` — 332 mapping önerisi

| Metrik | Değer |
|---|---|
| Toplam | 332 |
| Tümü `status=needs_review` | ✓ |
| `production_type=label` | 327 |
| `production_type=label_and_name_cut` | 3 |
| `production_type=review` | 2 |
| Unique barcode | 332 |

Yorum: Bu, henüz operatör onaylamamış AI önerileri. 36 onaylı mapping (yukarı) ile karşılaştırınca **332 SKU henüz operatör süzgecinden geçmemiş**.

Sample: `11_data_samples/trendyol_mapping_suggestions_sample.json` (ilk 3)

### `data/trendyol_production_suggestions.json` — 3 production-ready row

| ID | Customer | Verification | user_verified | verified_by |
|---|---|---|---|---|
| ty-phase18-ready | Ayşe & Mehmet | uretime_hazir | True | None |
| ty-phase18-no-proof | Helin Cemal | kullanici_kontrol_gerekli | False | None |
| ty-phase18-model-missing | Model Eksik | kullanici_kontrol_gerekli | False | None |

**`_is_verified_ready(Ayşe & Mehmet) = True`** — operator-approved invariant korunmuş.

Sample: `11_data_samples/trendyol_production_suggestions_full.json` (tam)

### `data/trendyol_ai_extraction_cache.json` — 102 entry

SHA256-keyed cache. Her entry: `label_text`, `date_text`, `note_text`, `quantity`, `name_cut_text`, `name_cut_width_mm`, `name_cut_style`, `confidence`, `warnings`, `source_evidence`. Tipik confidence değerleri 0.7-0.95 arası.

Sample: `11_data_samples/trendyol_ai_extraction_cache_sample.json` (1 entry)

### `data/trendyol_extraction_learning_examples.json` — boş

64 byte. Sadece `schema_version`, `updated_at`, `examples=[]`. Operatör düzeltmeleri yazılınca dolacak.

## Backend reach (`trendyol_api.py`)

| Slot | Görev |
|---|---|
| `get_trendyol_state` | Dashboard verileri |
| `save_trendyol_settings(payload)` | Settings yaz (mask koruma var) |
| `test_trendyol_connection` | API ping |
| `sync_trendyol_recent_orders(days)` | Read-only sipariş çek |
| `sync_trendyol_questions` | Read-only soru/mesaj çek |
| `cache_trendyol_product_image(url)` | Ürün görsel önbellek |
| `apply_trendyol_question_to_suggestion(id, qid)` | Operatör kanıt bağla |
| `approve_trendyol_mapping_suggestion(id)` | Mapping onayla |
| `verify_trendyol_suggestion(id, payload)` | Üretim sat. onayla |
| `save_trendyol_operator_correction(id, payload)` | Operatör düzeltme kaydet (öğrenme |
| `upsert_trendyol_mapping(payload)` | Direkt mapping ekle/güncelle |

## Frontend reach (`index.html`)

5 sidebar nav-sublink:
- Siparişler (`#trendyolOrders`, `tab=orders`)
- Kontrol Kuyruğu (`tab=worklist`) — bekleyen review
- Ürün Eşleştirme (`tab=mapping`) — onaysız 332 SKU buradan yönetilir
- Kanıt Eşleştirme (`tab=questions`) — soru-sipariş bağlama
- Aktarım Geçmişi (`tab=history`)

3 badge counter dinamik: `sidebarBadgeReview`, `sidebarBadgeMapping`, `sidebarBadgeEvidence`.

## Bypass durumu (Quick Wins sonrası kontrol)

- `_initial_verification_status` (`trendyol_api.py:1933-1947`) **artık `VERIFICATION_READY` döndürmez**. Yüksek-güvenli AI önerileri operatör onayı bekler. ✅
- Frontend mapping eşiği 0.55 → 0.72 hizalı (`app.js:3336`, `trendyol_api.py:454,460`). ✅
- Çoklu mesaj sessiz kayıp düzeltildi (`app.js:applySelectedTrendyolDrawerMessages` operatör uyarısı). ✅

## Veri Hacmi

- Kayıt sayısı: 522 soru, 36 mapping, 332 öneri, 3 production_suggestion, 102 AI cache entry — toplam ~1000 kayıt
- Son kayıt tarihi: 2026-05-19
- Dolu / boş: dolu (gerçek müşteri data)

## Bilinmeyen / test edilemedi

- Rate-limit durumu (son sync 2026-05-19, daha sonra çağrılmadı)
- Trendyol catalog gerçek boyutu (522 soru / 214 sipariş / 10 unique barcode oranı → barcode başına ortalama 21 sipariş; toplam ürün sayısı belirsiz)
- AI cache hit oranı (102 entry, 332 mapping suggestion — yaklaşık %31 cache, ama bu metrik istatistiksel değil pure count)
- Stage/test endpoint'i hiç denenmiş mi (stage=False, environment=live)

## Risk / Uyarı

- 🟢 Credential maskeli, backup'tan çıkarıldı
- 🟡 332 mapping suggestion onaysız bekliyor — operatör review backlog'u var
- 🟡 22 soru/mesaj cevaplanmamış (`status=WAITING_FOR_ANSWER`) — müşteri iletişimi açık
- 🟢 Operator-approved Ayşe & Mehmet satır `_is_verified_ready=True` korunmuş

## Önemli kodlar

- `src/webui_backend/trendyol_api.py` (2810 satır, 140 KB)
- `_initial_verification_status` (1933-1947) — bypass kapatılan kritik fonksiyon
- `_is_verified_ready` (1950-1954) — production-ready kontrolü
- `save_settings` (139+) — credential mask koruma
