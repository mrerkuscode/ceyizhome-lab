# BUTTON AUDIT PLAN

## 2026-05-20 Ilk Button Audit Tablosu

### Yontem

- Kaynaklar: `src/webui/index.html`, `src/webui/app.js`, `src/desktop/web_main_window.py`, `src/webui_backend/bridge.py`.
- Her buton icin once HTML `onclick` veya JS event handler bulunur.
- Handler icinde `callBridge`, `bridge.*`, `window.cyzella.*` veya direkt notice/alert kullanimi kontrol edilir.
- Python karsiligi varsa `webui_backend/bridge.py` slot ve `web_main_window.py` method zinciri kontrol edilir.
- Endpoint/bridge yoksa veya sadece notice/alert varsa durum pasif/uyari olarak isaretlenir.

### Durum Sozlugu

- Calisiyor: Bridge/backend karsiligi var ve gercek yan etki uretir.
- Kismi: Akisin bir parcasi gercek, bir parcasi uyari/manuel isleme kalir.
- Bagli degil: UI var ama handler/backend karsiligi yok.
- Sahte success: Islem tamamlanmadan basarili gibi mesaj verir.
- Pasif yapilmali: Canli entegrasyon yoksa aktif gorunmemeli.
- Ayarlar'a tasinmali: Teknik ayar/entegrasyon production ekranindan ayrilmali.
- Silinmeli: Uretim akisini desteklemeyen gereksiz aksiyon.

### Ilk Kritik Buton Eslesmeleri

| Sayfa | Buton | Frontend handler | Python bridge method | Gercek yan etki | Durum | Not | Onerilen aksiyon |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Etiket Studio | PDF/PNG | `renderManualLabelFields()` / output flow varyantlari | `render_manual_label_fields` | Manuel alanlardan PDF/PNG uretir | Calisiyor | Preflight/validate akislari mevcut | Yeni UI'ye baglanirken ayni bridge korunmali |
| Etiket Studio | Yazdir | `requestPdfPrint(relativePath)` | `print_queue_item_safe` veya PDF harici print akisi | Guvenli yazdirma/queue uzerinden islem | Kismi | Gercek yazici tetikleme guvenlik ayarina bagli | Kullanici onayi ve preflight gorunur olmali |
| Etiket Studio | Siraya Ekle | `render_manual_label_fields_to_queue` bagli akis | `render_manual_label_fields_to_queue` | Render sonucu yazdirma sirasina eklenir | Calisiyor | Queue API mevcut | Production degisiminde korunmali |
| Etiket Studio | Yeni / Ac / Farkli Kaydet | Cesitli UI/local state handlerlari | Net tek bridge karsiligi yok | Calisma dosyasi akisi sinirli | Kismi | Desktop belge mantigi tam standarda bagli degil | Design Lab'da command bar olarak dursun, production audit sonrasi netlestirilsin |
| Etiket Studio | Model Sec | model selection UI | `label_templates`, `label_model_gallery` | Kayitli model listesi/galeri gelir | Calisiyor | Model secimi mevcut | Yeni inspector'a baglanirken mevcut state korunmali |
| Etiket Studio | Studio'da Ac | `openHistoryInStudio`, `openQueueItemInStudio`, `openTrendyolSuggestionInStudio` | Duruma gore customer/trendyol/output verisi | Kayitli veriyi Studio state'ine tasir | Kismi | Kaynak bazli birden fazla giris var | Tek standart "context open" planlanmali |
| Trendyol | Baglantiyi Test Et | `testTrendyolConnection()` | `test_trendyol_connection` | Trendyol API ayarlarini test eder | Calisiyor | Hata mesajlari backend'den gelir | Settings ayrimi korunmali |
| Trendyol | Son 7 Gunu Cek | `syncTrendyolOrders(days)` | `sync_trendyol_recent_orders` | Siparisleri ceker, suggestion state gunceller | Calisiyor | Uzun is olabilir | Progress/job planina alinmali |
| Trendyol | Sorulari Oku | `syncTrendyolQuestions()` | `sync_trendyol_questions` | Musteri sorularini ceker | Calisiyor | Evidence akisi icin kritik | Drawer lazy load ile desteklenmeli |
| Trendyol | Uretime Aktar / Toplu Etiket'e Aktar | `exportTrendyolReadyToExcel()` | `export_trendyol_ready_to_excel` | Hazir suggestionlari Excel/toplu uretime aktarir | Calisiyor | Uretim aktarimi Excel tabanli | Yeni UI'de kosullar net gosterilmeli |
| Trendyol | Urun Eslestir | mapping handlers | `upsert_trendyol_mapping`, `approve_trendyol_mapping_suggestion` | Urun-model eslesmesi kaydeder | Calisiyor | Mapping backend mevcut | Barkod/SKU filtre UI iyilestirilmeli |
| Trendyol | Kanit bagla | `applySelectedTrendyolDrawerMessages()` / evidence handlers | `apply_trendyol_question_to_suggestion` | Mesaji suggestion kaniti yapar | Calisiyor | Coklu mesaj secimi dikkatli test edilmeli | Drawer audit sonrasi optimize |
| Trendyol | Trendyol'da Isleme Al | `bulkMarkTrendyolProcessed()` / marketplace status notices | Yok veya lokal status sinirli | Trendyol API durum degisimi net degil | Kismi | Sahte canli Trendyol basarisi verilmemeli | API yoksa pasif/uyari kalmali |
| Trendyol | Kargo Etiketi | Toplu barda disabled | Yok | Canli kargo etiketi yok | Pasif yapilmali | Zaten disabled title mevcut | Disabled tasarimi daha net yapilmali |
| Trendyol | Fatura | Toplu barda disabled | Yok | Canli fatura entegrasyonu yok | Pasif yapilmali | Zaten disabled title mevcut | Ayarlar/roadmap notu eklenmeli |
| Toplu Uretim | Excel Sec | bridge select/set excel akislari | `select_excel`, `set_selected_excel` | Excel kaynagi secilir | Calisiyor | PySide file picker kullanir | Stepper kaynak adiminda korunmali |
| Toplu Uretim | Kolon Eslestir | `bulk_column_mapping` state render | `bulk_column_mapping` | Kolon mapping ozeti dondurur | Calisiyor | Turkce alias backend'de var | UI teknik kolonlari gizlemeli |
| Toplu Uretim | Secili olanlari uretime al | `startBulkGalleryProduction()` benzeri akis | `bulk_generate_gallery_items_and_add_to_queue` | Hazir kartlari kuyruğa ekler | Calisiyor | Status hata/basari ayrimi korunmali | Progress ve kismi basari raporu eklenmeli |
| Toplu Uretim | Lazer Kesime Gonder | `sendLaserBulkItemsToNameCutQueue()` | `prepare_name_cut_files` | Lazer isim dosyalari hazirlar | Calisiyor | Lazer baslatmaz, dosya hazirlar | Guvenlik metni korunmali |
| Isim Kesim | SVG/DXF/PDF export | name cut export/download handlers | `prepare_name_cut_files` | SVG/DXF/PDF/CSV benzeri dosyalar hazirlar | Calisiyor | RDWorks start yok | Path/outline audit devam etmeli |
| Isim Kesim | Lazer Kesim'de Ac | open folder/file notice varyantlari | `open_laser_folder` olabilir | Klasor/dosya acma ile sinirli | Kismi | Makine baslatmaz | Uyari metni net kalmali |
| Yazdirma Sirasi | Yazdir | queue row print handler | `print_queue_item_safe` | Guvenli print akisi | Calisiyor | Direct print ayarina bagli | Onay/preflight zorunlu gosterilmeli |
| Yazdirma Sirasi | Sil | queue remove handler | `remove_from_print_queue` | Kuyruktan siler | Calisiyor | Yanlis silmeye karsi confirm kontrol edilmeli | Confirm standardi eklenmeli |
| Sistem | Loglar / Cikis Yap | `showSystemNotice` | Yok | Bilgilendirme/notice | Bagli degil | Gercek log viewer/cikis yok | Pasif veya roadmap etiketi |

### Ilk Kritik Tespitler

1. Kargo etiketi ve fatura aksiyonlari canli entegrasyona bagli degil; aktif production butonu gibi davranmamali.
2. Trendyol'da isleme alma gercek Trendyol status update degilse kullaniciya acik "lokal/isaretleme" dili kullanilmali.
3. Yeni/Ac/Kaydet/Farkli Kaydet masaustu belge modeli icin daha net bir state ve bridge sozlesmesine ihtiyac duyuyor.
4. Queue ve render butonlari backend bagli; yeni tasarimda korunacak en kritik akislardir.
