# BACKEND FRONTEND ANALYSIS

## 2026-05-20 Guvenli Audit Baslangici

### Python Bridge Analizi

- Aktif masaustu uygulamada frontend, PySide WebChannel ile Python bridge'e baglaniyor.
- Bridge girisi: `src/webui_backend/bridge.py`.
- Ana controller: `src/desktop/web_main_window.py`.
- Frontend yardimci fonksiyonu: `src/webui/app.js` icindeki `callBridge(name, ...args)`.
- `callBridge`, bridge method yoksa `alert("Bu islem su anda hazir degil.")` gosteriyor; bu durum button audit icin bagli degil sinyali olarak kabul edilmeli.

### web_main_window.py Analizi

`web_main_window.py` uygulamanin ana orkestrasyon noktasi gibi calisiyor:

- Etiket render: `render_manual_label_fields`, `preview_manual_label_fields`, `preflight_manual_label_fields`, `validate_manual_label_output`.
- Yazdirma sirasi: `print_queue`, `add_pdf_output_to_print_queue`, `remove_from_print_queue`, `mark_queue_item_printed`, `print_queue_item_safe`.
- Etiket modeli: `label_templates`, `label_model_gallery`, `choose_label_model_preview`, `save_label_model_field`, `add_label_model_field`, `remove_label_model_field`, backup ve restore methodlari.
- Trendyol: `trendyol_state`, `save_trendyol_settings`, `test_trendyol_connection`, `sync_trendyol_recent_orders`, `sync_trendyol_questions`, mapping ve evidence methodlari.
- Toplu uretim: `bulk_column_mapping`, `bulk_gallery_items`, `render_bulk_preview_samples`, `prepare_selected_bulk_excel`.
- Lazer/isim kesim: `prepare_name_cut_files`, `laser_outputs`.

### webui_backend Analizi

- `trendyol_api.py`: Trendyol connection, order sync, question sync, mapping suggestion, evidence ve Excel export mantigi.
- `trendyol_mapping_api.py`: urun-model mapping import/export/upsert.
- `bulk_label_api.py`: Excel kolon mapping, galeri itemlari, manifest ve secili satir export.
- `combined_production_api.py`: toplu uretim ve isim kesim layout/export; script connection, SVG/DXF/PDF hazirliklari.
- `label_api.py`: manuel label render ve output listeleri.
- `print_queue_api.py`: queue CRUD ve guvenli print methodlari.
- `template_api.py`: etiket model listesi, gorsel, alan, backup, font import ve print template islemleri.
- `production_safety.py`: label output preflight ve guvenlik kontrolleri.

### Frontend Handler Yapisi

- UI handlerlari buyuk olcude `src/webui/app.js` icinde global fonksiyonlar olarak tanimli.
- `src/webui/index.html` dogrudan `onclick` kullaniyor; bu hizli ancak button audit ve refactor icin dikkatli calisma gerektiriyor.
- Design Lab, Font Test Lab ve production ekranlari ayni app runtime icinde; design-lab mock fonksiyonlar production bridge'e baglanmamalı.

### Veri Akisi Ozeti

1. Frontend section/page state'i `showSection` ile degisir.
2. UI state `currentState`, local arrays ve bridge donusleriyle tutulur.
3. Python bridge JSON string veya dict dondurur.
4. Backend servisleri dosya tabanli state, Excel, PDF/PNG, mapping ve queue uzerinde calisir.
5. Uzun isler icin bazi akislarda sonuc dosyasi/manifest var, ama her is icin job/progress standardi yok.

### Eksik Baglantilar

- Kargo etiketi ve fatura canli entegrasyon baglantisi belirgin degil; UI pasif/uyari olarak kalmali.
- Trendyol'da isleme alma gercek marketplace status update ise ayrica dogrulanmali; aksi durumda lokal status dili kullanilmali.
- Masaustu belge komutlari Yeni/Ac/Kaydet/Farkli Kaydet icin tek standart bridge sozlesmesi net degil.
- Design Lab su anda referans/mock yuzey; production fonksiyon baglantisi amaclanmiyor.

### Performans Riskleri

- Buyuk `app.js` ve `index.html` monoliti degisim riskini artirir.
- Trendyol 400+ siparis ve Toplu Uretim 500 satir icin kart/thumbnail virtualization ihtiyaci dogabilir.
- Drawer acilislari tum listeyi tekrar render ediyorsa performans bozulabilir.
- Lazer nesting ve font/path olcumleri ana thread veya request icinde uzun surerse UI donabilir.
- PDF/PNG/SVG/DXF export icin progress/job standardi her yerde ayni degil.

### Oneri

Once rapor ve Design Lab referansi tamamlanmali. Sonra production icin bridge sozlesmesi korunarak kucuk, sayfa bazli entegrasyon yapilmali.
