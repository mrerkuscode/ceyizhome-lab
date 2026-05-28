# 05 — Bağımlılık Grafiği (Modül Etkileşimi)

## Yüksek-seviye akış
```
                ┌──────────────────────────┐
                │  Trendyol Siparişleri    │ ◄── trendyol_api.py
                │  (orders/worklist/       │
                │   mapping/questions)     │
                └────────┬─────────────────┘
                         │ import_trendyol_to_bulk_production
                         ▼
                ┌──────────────────────────┐
                │  Toplu Üretim Studio     │ ◄── bulk_label_api.py
                └────────┬─────────────────┘
                         │ bulk_label_to_name_cut / studio
                         ▼
            ┌────────────┴────────────┐
            ▼                         ▼
  ┌────────────────────┐   ┌────────────────────┐
  │   İsim Kesim       │   │   Etiket Studio    │ ◄── label_api.py
  │  (name_cut_*)      │   │   (manual + studio)│
  └────────┬───────────┘   └──────────┬─────────┘
           │ build_name_cut_           │
           │ production_scene          │
           ▼                           ▼
  ┌────────────────────┐   ┌────────────────────┐
  │  167-ref kütüphane │   │  Label Models      │
  │  corel_name_       │   │  (renderLabelModels)│
  │  reference_lib     │   └──────────┬─────────┘
  │  (operator-approved │              │
  │   exact-refs +     │              │
  │   style-only refs) │              │
  └─────────┬──────────┘              │
            │                          │
            └──────────┬───────────────┘
                       ▼
              ┌────────────────────┐
              │  Yazdırma Sırası   │ ◄── print_queue_api.py
              │  (printQueue)      │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │  DXF/SVG/PDF       │ ◄── _dxf_document, label render
              │  EXPORT            │
              └──────────┬─────────┘
                         ▼
              ┌────────────────────┐
              │  RDWorks (manual)  │ — auto-start KAPALI
              │  Yazıcı (manual)   │ — direct print KAPALI
              └────────────────────┘

  Ayarlar / Bakım (paralel):
  ├── Genel Ayarlar (saveSettings) → settings.json
  ├── Trendyol API → trendyol_settings.json (credential masked)
  ├── Yazıcı Profilleri → printer_profiles.json (eksik default!)
  ├── Veri Bakımı → backup/restore/migrate (corel ref lib AYRI sistem, genel backup'a dahil değil)
  └── Etiket Modelleri → models + versioning
```

## Çift sistem notu (referans kütüphanesi)
- **Corel referans kütüphanesi** (`corel_name_reference_library.json` 167 ref) → İSİM KESİM'in kalbı. **Kendi backup sistemi var** (`create_corel_reference_backup`, `assets/references/backups/`) — bugün İrem/Ümit işinde çalıştı.
- **Genel backup** (`backup_api.py:BACKUP_RELATIVE_FILES`) — bunu kapsamıyor (etiket "İsim Kesim" diyerek yanıltıcı; Phase 2 17_veri_bakimi KRİT-1).

## Hangi modül silinirse ne etkilenir
- **trendyol_api.py:** Trendyol siparişler + worklist + mapping + questions → toplu üretim akışı kesilir. KRİTİK.
- **bulk_label_api.py:** Toplu Üretim Studio çalışmaz. KRİTİK.
- **label_api.py:** Etiket Studio + manuel etiket çıktıları yok. KRİTİK.
- **print_queue_api.py:** Yazdırma sırası boş, üretim akışı kesilir. KRİTİK.
- **combined_production_api.py:** Engine — silinirse her şey çöker. KRİTİK.
- **printer_profile_api.py:** Yazıcı seçimi yok; ama default'lar yok zaten (Phase 2 16). ORTA.
- **bridge.py:** Qt ↔ JS köprüsü. Silinirse UI hiçbir backend çağrısı yapamaz. KRİTİK.
- **`legacy_converter.py`:** Kullanım belirsiz (incelenmesi gerekiyor). DÜŞÜK.
- **`desktop/main_window.py`:** `web_main_window.py` paralel var; muhtemelen biri kullanılıyor. İncelenmesi gerek.

## Frontend (app.js) modülerlik
app.js 20872 satır, monolitik. Sayfa-bazında bölümler var ama tek dosyada. Refactor önerilir uzun vadede; şimdi öncelik DEĞİL.

## DXF kütüphane geçiş planı (Leyla'nın yeni vizyonu)
Yeni yol: Trendyol → bulk → **DXF kütüphane lookup** (500 ref) → eşleşirse → print queue → DXF. İsim Kesim engine'in jeneratif tarafı (targeted-weld vs.) fallback'e çekilir. corel_reference_importer.py'a **SPLINE desteği** eklenmeli (bugün `output/2026-05-27/dxf_test/` raporunda fizibil bulundu — Cox-de Boor stdlib).
