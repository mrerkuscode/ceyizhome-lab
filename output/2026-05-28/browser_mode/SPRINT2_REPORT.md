# Browser Mode Sprint 2 Raporu
**Tarih:** 2026-05-28  
**Sprint:** 2 — Yazma / POST Endpoint'leri  
**Önceki Sprint:** Sprint 1 (10/10 PASS) ✅

---

## Özet

Sprint 2'de 30 yeni POST endpoint eklendi. Tıklama işlemleri (mark printed, remove, save, vb.) artık browser modunda çalışır.

**Test sonucu: 40/40 PASS** (Sprint 1: 10 + Sprint 2: 30)

---

## Eklenen Endpoint'ler

| # | Endpoint | Grup | Açıklama |
|---|----------|------|----------|
| 1 | `POST /api/mark_queue_item_printed` | Print Queue | Kuyruktaki öğeyi "basıldı" işaretle |
| 2 | `POST /api/mark_queue_item_pending` | Print Queue | "Bekliyor" durumuna al |
| 3 | `POST /api/mark_queue_item_delivered` | Print Queue | "Teslim edildi" işaretle |
| 4 | `POST /api/remove_from_print_queue` | Print Queue | Kuyruktaki öğeyi sil |
| 5 | `POST /api/clear_print_queue` | Print Queue | Tüm kuyruğu temizle |
| 6 | `POST /api/add_pdf_output_to_print_queue` | Print Queue | PDF'i kuyruğa ekle |
| 7 | `POST /api/add_label_outputs_to_print_queue` | Print Queue | Tüm çıktıları kuyruğa ekle |
| 8 | `POST /api/save_label_model_field` | Etiket Tasarım | Alan kaydet |
| 9 | `POST /api/add_label_model_field` | Etiket Tasarım | Yeni alan ekle |
| 10 | `POST /api/remove_label_model_field` | Etiket Tasarım | Alan kaldır |
| 11 | `POST /api/save_label_defaults_json` | Etiket Tasarım | Varsayılan ayarları kaydet |
| 12 | `POST /api/clone_label_model_variant` | Etiket Tasarım | Etiket modeli kopyala |
| 13 | `POST /api/save_print_template_metadata` | Etiket Tasarım | Print şablonu metadata kaydet |
| 14 | `POST /api/productDefinitionSave` | Ürün Tanımları | Ürün tanımı kaydet |
| 15 | `POST /api/productDefinitionArchive` | Ürün Tanımları | Ürün tanımı arşivle |
| 16 | `POST /api/productDefinitionRestore` | Ürün Tanımları | Arşivden geri yükle |
| 17 | `POST /api/create_customer_order` | Müşteri Siparişleri | Sipariş oluştur |
| 18 | `POST /api/update_customer_order_status` | Müşteri Siparişleri | Sipariş durumu güncelle |
| 19 | `POST /api/append_production_audit_event` | Audit/Log | Üretim olayı ekle |
| 20 | `POST /api/rebuild_production_audit_from_existing_sources` | Audit/Log | Audit'i yeniden oluştur |
| 21 | `POST /api/save_printer_profile` | Yazıcı Profili | Profil kaydet |
| 22 | `POST /api/delete_printer_profile` | Yazıcı Profili | Profil sil |
| 23 | `POST /api/create_backup` | Yedekleme | Yedek oluştur |
| 24 | `POST /api/restore_backup` | Yedekleme | Yedekten geri yükle |
| 25 | `POST /api/upsert_trendyol_mapping` | Trendyol | SKU eşlemesi kaydet |
| 26 | `POST /api/save_trendyol_settings` | Trendyol | Trendyol ayarları kaydet |
| 27 | `POST /api/update_name_cut_queue_item_status` | İsim Kesim | İsim kesim durumu güncelle |
| 28 | `POST /api/save_live_integration_security_settings` | Güvenlik | Güvenlik ayarları kaydet |
| 29 | `POST /api/archive_label_outputs` | Etiket Çıktı | Çıktıları arşivle |
| 30 | `POST /api/restore_label_outputs` | Etiket Çıktı | Arşivden geri yükle |

---

## Test Sonuçları

```
============================= test session starts =============================
collected 40 items

tests/test_flask_endpoints.py  40 passed in 0.55s

Sprint 1 (GET): 10/10 PASS ✅
Sprint 2 (POST): 30/30 PASS ✅
TOPLAM: 40/40 PASS ✅
```

---

## Değiştirilen / Eklenen Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `src/server/routes.py` | 30 POST endpoint eklendi (Sprint 1 GET'lere dokunulmadı) |
| `src/server/controller_proxy.py` | 30 proxy fonksiyon + 8 yeni lazy import eklendi |
| `src/webui/api_adapter.js` | `postJson()` yardımcı + 30 adapter fonksiyon eklendi; stub listesi güncellendi |
| `tests/test_flask_endpoints.py` | 30 yeni POST testi eklendi |

---

## Bilinen Sınırlar (Sprint 3+ için)

| Konu | Durum |
|------|-------|
| ~150 endpoint hâlâ stub | Sprint 3+ |
| File upload (QFileDialog) | Sprint 3 — PyQt5/PySide6 gerektiriyor |
| Subprocess (render_labels, runDry) | Sprint 3 — process yönetimi gerekli |
| Trendyol canlı bağlantı testi | Sprint 3 — ağ bağlantısı gerekli |
| cancel_running_job | Sprint 3 — subprocess tracking gerekli |
| create_label_model_from_wizard | Sprint 3 — design_visual dosya seçimi gerekli |

---

## Çalıştırma (Değişmedi)

```bash
start_browser_mode.bat
# → http://localhost:8000
```

---

## Sprint 1 Koruması ✅

- `src/server/flask_app.py` → DOKUNULMADI
- `src/server/controller_proxy.py` → Sadece ekleme yapıldı
- Mevcut 7 GET endpoint → DOKUNULMADI
- `start_app.bat`, `start_browser_mode.bat` → DOKUNULMADI
- `src/webui/app.js` (21391 satır) → DOKUNULMADI
- `src/webui_backend/bridge.py` → DOKUNULMADI
