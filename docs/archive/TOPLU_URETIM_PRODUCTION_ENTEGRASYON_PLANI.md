# CeyizHome Lab - Toplu Uretim Production Entegrasyon Plani

Tarih: 2026-05-21  
Kapsam: Production Toplu Uretim Studio icin analiz ve fazli entegrasyon plani  
Karar: Bu dokuman yalnizca plandir. Production kodu, backend/bridge methodlari ve Design Lab ekranlari degistirilmemistir.

## 1. Mevcut Production Durum

Aktif Toplu Uretim ekrani `production-bot/src/webui/index.html` icinde `section#bulkLabel` olarak bulunuyor. Ekran halihazirda "Toplu Uretim Studio" adiyla calisiyor ve 6 adimli bir akisa sahip:

1. Kaynak Sec
2. Alanlari Kontrol Et
3. Model ve Sablon Sec
4. Toplu Onizleme Galerisi
5. Hatalari Duzelt
6. Uretime Al

Frontend akisi agirlikli olarak `production-bot/src/webui/app.js` icinde yonetiliyor. Ana fonksiyonlar:

- `setBulkProductionStep(step)`
- `setBulkProductionSource(source)`
- `importBulkFromTrendyol()`
- `openBulkManualEntry()`
- `setBulkProductionViewMode(mode)`
- `renderBulkProductionSummary()`
- `renderBulkGallery()`
- `renderBulkSelectedDetail()`
- `updateBulkColumnMapping(mapping)`
- `updateBulkWarnings(errors, modelRows)`
- `generateReadyBulkGalleryItems()`
- `generateSelectedBulkRowsAndQueue()`
- `renderBulkRealMiniPreviews()`
- `renderSelectedBulkMiniPreviews()`
- `sendLaserBulkItemsToNameCutQueue()`

Backend/PySide tarafinda aktif kopru `production-bot/src/webui_backend/bridge.py` ve controller `production-bot/src/desktop/web_main_window.py` uzerinden ilerliyor.

Ana backend servisleri:

- `production-bot/src/webui_backend/bulk_label_api.py`
- `production-bot/src/webui_backend/combined_production_api.py`
- `production-bot/src/webui_backend/print_queue_api.py`

Mevcut calisan cekirdek ozellikler:

- Excel dosyasi secme.
- Dry-run / alan kontrolu calistirma.
- Excel kolonlarini Turkce alan diline esleme.
- Model kullanim ozeti ve model durumu gosterebilme.
- Toplu galeri itemlarini state uzerinden render etme.
- Secili/filtreli kayitlar icin mini preview uretme.
- Hazir galeri itemlarini backend render akisiyle PDF/PNG uretime ve yazdirma sirasina alma.
- Queue tarafinda `source/source_label` standardina uyumlu `bulk_production / Toplu Uretim` kaynagi uretme.
- Name cut icin guvenli dosya hazirlama servisi bulunmasi.

Eksik veya riskli alanlar:

- Trendyol'dan Aktar butonu gercek aktarim yapmiyor; kullaniciyi Trendyol ekranina yonlendiriyor.
- Manuel kaynak frontend local item ekliyor, kalici/structured source contract henuz net degil.
- Coklu manuel giris ve kopyala/yapistir su anda bagli degil.
- Kolon eslestirme goruntuleniyor, ancak operatorun elle mapping duzenlemesi icin production UI henuz olgun degil.
- Galeri kartlari Design Lab standardina tam tasinmamis.
- `laser_text`/name-cut verisi `write_gallery_items_excel` tarafinda henuz bos yazilabiliyor; lazer pipeline icin veri sozlesmesi guclendirilmeli.
- AI duzenleme su anda frontend heuristic/smart arrange mantigi; gercek AI backend entegrasyonu gibi sunulmamali.
- Rapor indirme bagli degil.
- 500+ satirda galeri render performansi icin virtualization/lazy load gerekir.

## 2. Mevcut Akis Haritasi

### Kaynak Sec

Excel kaynagi `bridge.chooseExcel()` ile dosya secmeye bagli. Ornek Excel acma `openBulkSampleExcel()` uzerinden `bridge.open_project_file("examples/toplu_etiket_ornek.xlsx")` cagiriyor.

Trendyol kaynagi `importBulkFromTrendyol()` ile su an dogrudan import yapmiyor; `showSection("trendyolOrders")` ile Trendyol ekranina gecis yapiyor. Bu nedenle production'a tasinirken "Trendyol'dan Aktar" canli veri cekiyor gibi davranmamali.

Manuel kaynak `openBulkManualEntry()` ile frontend icinde yeni bir galeri itemi olusturuyor ve editoru aciyor. Bu akis hizli prototip olarak yararli, fakat production sozlesmesi icin `source: manual` ve kalicilik konusu ayrica ele alinmali.

### Alanlari Kontrol Et ve Kolon Esleme

`bridge.runDry()` controller tarafinda `run_dry()` methoduna gider ve secili Excel icin dry-run calistirir. Kolon esleme `bulk_label_api.column_mapping()` ile uretilir ve frontend'de `updateBulkColumnMapping(mapping)` ile gosterilir.

Mevcut alias sistemi Turkce alanlar icin iyi bir temel sunuyor:

- Isim: `label_text`
- Tarih: `date_text`
- Not: `note_text`
- Adet: `quantity`
- Model: `model_key`

Production hedefinde teknik kolon isimleri operator ekranindan gizlenmeli; "Siparis No, Musteri Adi, Urun Adi, Barkod, SKU, Etiket Modeli, Isim, Tarih, Not, Adet, Lazer Isim" dili kullanilmali.

### Model ve Sablon Sec

Model bilgisi `bulk_label_api.used_label_models()` ve `bulk_gallery_items()` tarafindan okunuyor. Ekran model durumunu, olcu bilgisini ve eksik model durumlarini gosterebiliyor.

Risk: Operatorun model secme/degiştirme islemi henuz Design Lab'deki kadar merkezi degil. Production'a tasinirken mevcut model lookup korunmali, ancak UI daha anlasilir hale getirilmeli.

### Toplu Onizleme Galerisi

Galeri state'i `currentState.bulkGalleryItems` uzerinden geliyor ve `syncBulkGallery(items)` ile frontend state'e aliniyor. `renderBulkGallery()` galeri kartlarini, `renderBulkSelectedDetail()` secili detay alanini gosteriyor.

Mevcut filtreler:

- Tumu
- Hazir
- Kontrol gerekli
- Hatali
- Lazer isimli
- Yazisi kucuk / kalite
- AI duzeltilen

Mevcut gorunum modlari:

- Galeri
- Tablo
- Rulo gorunumu
- Lazer gorunumu

Bu temel, Design Lab referansina tasimak icin uygundur.

### Hatalari Duzelt

Backend dry-run ve model kontrollerinden gelen hatalar `updateBulkWarnings(errors, modelRows)` ile listeleniyor. Galeri itemlarinda `status`, `errors`, `warnings`, `quality` benzeri frontend hesaplari var.

Production hedefinde hata kategorileri net ayrilmali:

- Model eksik
- Isim eksik
- Tarih eksik
- Yazi tasiyor
- Yazisi kucuk
- Lazer tasmasi
- PDF/PNG uretilemedi

### Uretime Al ve Yazdirma Sirasi

`generateReadyBulkGalleryItems()` hazir ve silinmemis galeri itemlarini `bridge.bulk_generate_gallery_items_and_add_to_queue(items_json)` ile backend'e yollar.

Backend'de:

- `web_main_window.bulk_generate_gallery_items_and_add_to_queue(items)`
- `bulk_label_api.write_gallery_items_excel(...)`
- `src/main.py --excel <temp_excel> --render-labels`
- Worker tamamlaninca `print_queue_api.add_label_outputs_to_queue(...)`

Yeni queue kayitlarinda non-manual batch icin `source: bulk_production`, `source_label: Toplu Uretim` standardi destekleniyor.

Yazici otomatik baslatilmiyor. Bu davranis korunmali.

### Lazer / Isim Kesim

`sendLaserBulkItemsToNameCutQueue()` su an gercek lazer/RDWorks baslatmiyor; sadece isim kesim alanina yonlendirme/uyari diliyle calisiyor.

Backend tarafinda `combined_production_api.export_name_cut_batch(...)` guvenli SVG/DXF/PDF/PNG/manifest uretimi icin temel sunuyor. Manifest icinde otomatik RDWorks acma, lazer baslatma ve direct print kapali tutuluyor.

Risk: Bulk galeri itemlarindan name-cut/lazer alanina aktarilacak `laser_name` sozlesmesi henuz yeterince net degil.

## 3. Production Veri Sozlesmesi Onerisi

Toplu Uretim satiri/karti icin hedef sozlesme:

| Alan | Aciklama | Kaynak/Fallback |
| --- | --- | --- |
| `id` | Kayit kimligi | Frontend/backend uretir |
| `row_no` | Excel veya kaynak satir no | `row_number` fallback |
| `source` | `excel`, `trendyol`, `manual`, `bulk_production`, `unknown` | Yeni standart |
| `source_label` | Okunur kaynak etiketi | Yeni standart |
| `order_no` | Siparis no | Excel/Trendyol |
| `customer_name` | Musteri adi | Excel/Trendyol |
| `product_name` | Urun adi | Excel/Trendyol |
| `barcode` | Barkod | Excel/Trendyol |
| `sku` | SKU | Excel/Trendyol |
| `model_id` | Model id/key | `model_key` |
| `model_name` | Model adi | `model_name` |
| `label_text` | Isim/etiket yazisi | Mevcut `label_text` |
| `date_text` | Tarih | Mevcut `date_text` |
| `note_text` | Not | Mevcut `note_text` |
| `quantity` | Adet | Mevcut `quantity`, gecersizse 1 |
| `laser_name` | Lazer isim | Yeni net alan; mevcut `laser_text` bos kalma riski var |
| `status` | Kart durumu | Hazir/kontrol/hata |
| `quality_score` | Kalite skoru | Frontend preflight/heuristic |
| `validation_status` | Validasyon sonucu | `ok`, `warning`, `error`, `pending` |
| `evidence_status` | Kanit/mesaj baglantisi | Trendyol icin |
| `product_match_status` | Urun eslesme durumu | Trendyol icin |
| `preview_path` | Onizleme PNG yolu | Backend preview |
| `pdf_path` | Uretilen PDF | Render sonucundan |
| `png_path` | Uretilen PNG | Render sonucundan |
| `laser_output_status` | Lazer cikti durumu | Name cut fazi |
| `queue_status` | Yazdirma sirasi durumu | Queue entegrasyonu |

Kaynak degerleri:

- `excel`
- `trendyol`
- `manual`
- `bulk_production`
- `unknown`

Durum degerleri:

- `hazir`
- `kontrol_gerekli`
- `hatali`
- `model_eksik`
- `yazi_tasiyor`
- `yazisi_kucuk`
- `lazer_var`
- `lazer_tasmasi`
- `ai_duzeltti`
- `uretime_alindi`
- `siraya_eklendi`

## 4. Buton / Handler / Bridge Eslesmesi

| Buton | Frontend handler | Bridge/backend | Durum | Production aksiyonu |
| --- | --- | --- | --- | --- |
| Excel Dosyasi Sec | `bridge.chooseExcel()` | `choose_excel()` | Calisiyor | Korunacak |
| Ornek Excel Indir | `downloadBulkSampleExcel()` | `open_project_file(...)` | Kismi | "Ac/indir" dili netlestirilecek |
| Trendyol'dan Aktar | `importBulkFromTrendyol()` | Yok, sayfa yonlendirme | Kismi | Gercek import yoksa pasif/uyarili kalacak |
| Manuel Ekle | `openBulkManualEntry()` | Frontend local | Kismi | `source: manual` sozlesmesiyle guclendirilecek |
| Coklu giris | `showBulkFeatureNotConnected(...)` | Yok | Bagli degil | Pasif/uyarili |
| Kopyala/Yapistir | `showBulkFeatureNotConnected(...)` | Yok | Bagli degil | Pasif/uyarili |
| Alanlari Kontrol Et | `bridge.runDry()` | `run_dry()` | Calisiyor | Korunacak |
| Kolon Eslestir | `updateBulkColumnMapping(...)` | `bulk_label_api.column_mapping()` | Kismi | Elle mapping UI faz 2 |
| Model Sec | `showSection('labelModels')` / model state | `used_label_models`, `bulk_gallery_items` | Kismi | Model secici sadeleştirilecek |
| Galeri Olustur | `syncBulkGallery`, `renderBulkGallery` | `bulk_gallery_items()` | Calisiyor | Design Lab standardina yaklastirilacak |
| Hazir olanlari sec | `prepareBulkGalleryItems()` | Frontend | Kismi | Secim davranisi netlestirilecek |
| Secili olanlari uretime al | `generateReadyBulkGalleryItems()` | `bulk_generate_gallery_items_and_add_to_queue` | Calisiyor | Queue source ile korunacak |
| AI ile duzenle | `smartArrangeVisibleBulkItems(...)` | Yok/heuristic | Kismi | "AI onerisi" dili, fake AI yok |
| Lazer Kesime Gonder | `sendLaserBulkItemsToNameCutQueue()` | Su an gercek queue yok | Kismi | Faz 6'ya kadar pasif/uyarili |
| Hatali olanlari goster | `setBulkGalleryFilter('error')` | Frontend | Calisiyor | Korunacak |
| Rapor indir | `showBulkFeatureNotConnected('Rapor indirme')` | Yok | Bagli degil | Pasif/uyarili |
| Studio'da Ac | Henuz net production handler yok | Etiket Studio entegrasyonu gerekir | Bagli degil | Faz 4/sonrasi |
| Lazer Kesim'de Ac | Scroll/name-cut panel | `prepare_name_cut_files` ileride | Kismi | Otomatik lazer yok |
| Onayla | `saveBulkGalleryDraft()` benzeri | Frontend state | Kismi | Kart onay state'i standardize edilecek |
| Siraya Ekle | `generateReadyBulkGalleryItems()` / selected bridge | `print_queue_api.add_label_outputs_to_queue` | Calisiyor | `source: bulk_production` ile korunacak |
| Cikti Olustur | `bridge.render_labels()` | `render_labels()` | Calisiyor | Preflight/validation gorunur olacak |

## 5. Design Lab'den Production'a Tasinacaklar

- 6 adimli stepper dili ve kompakt gorsel hiyerarsi.
- Excel / Trendyol / Manuel kaynak kartlari.
- Sag Uretim Ozeti paneli.
- Toplu Onizleme Galerisi odakli ana ekran.
- Galeri filtreleri: Tumu, Hazir, Kontrol gerekli, Hatali, Lazer isimli, Yazi tasiyan, Yazisi kucuk, AI duzeltilen.
- Galeri / Tablo / Rulo / Lazer gorunum secenekleri.
- Galeri kartlarinda thumbnail, satir no, kaynak no, isim, tarih, not, adet, lazer rozeti, model, kalite skoru ve durum rozeti.
- Etiket Onizleme + Lazer Onizleme modal/drawer standardi.
- Hatalari Duzelt paneli.
- Uretime Al on kontrol ekrani.

## 6. Production'a Kor Kopyalanmayacaklar

- Mock kayitlar.
- Design Lab class'larinin dogrudan production'a yapistirilmasi.
- Sahte buton success mesajlari.
- Backend karsiligi olmayan aktif butonlar.
- Lazer/RDWorks otomatik baslatan davranis.
- Yaziciyi otomatik calistiran davranis.
- Trendyol canli aksiyonlari.
- "AI" olarak sunulan ama sadece frontend heuristic olan islemler.

## 7. Fazli Uygulama Plani

### Faz 1 - Kaynak kartlari ve stepper iskeleti

Yapilacaklar:

- Mevcut `section#bulkLabel` icinde layout standardi toparlanir.
- Excel, Trendyol ve Manuel kaynak kartlari production diline cekilir.
- Gercek handler'a bagli butonlar korunur.
- Bagli olmayan butonlar pasif/uyarili hale getirilir.

Etkilenecek dosyalar:

- `production-bot/src/webui/index.html`
- `production-bot/src/webui/app.js`
- `production-bot/src/webui/styles.css`

Risk:

- Mevcut Excel secme ve dry-run akisini bozmamak.

Test:

- Excel secme, dry-run, state refresh, 1920/1366 screenshot.

### Faz 2 - Turkce kolon eslestirme ve Alanlari Kontrol Et

Yapilacaklar:

- Kolon eslestirme paneli operator diline tasinir.
- Teknik kolonlar gizlenir.
- Zorunlu alanlar: Isim, Adet, Model.
- Opsiyonel alanlar: Tarih, Not, Lazer Isim, Siparis No, Musteri Adi, Barkod, SKU.
- Elle mapping duzenleme gerekiyorsa mevcut backend alias sistemi bozulmadan eklenir.

Risk:

- Mevcut `bulk_label_api.column_mapping()` sonucu ile UI arasinda sozlesme kaymasi.

Test:

- Ornek Excel, eksik kolonlu Excel, Turkce kolon aliaslari.

### Faz 3 - Toplu Onizleme Galerisi

Yapilacaklar:

- Production galeri kartlari Design Lab standardina yaklastirilir.
- Thumbnail, kalite skoru, durum rozeti ve kaynak rozeti netlestirilir.
- Uzun isim ve eksik model durumlari kartta gorunur.
- 500 satir icin lazy render/virtualization plani uygulanir veya raporlanir.

Risk:

- Buyuk Excel dosyalarinda DOM sismesi.

Test:

- 50/500 satir simülasyonu, filtreler, arama, view mode.

### Faz 4 - Etiket/Lazer onizleme modalı

Yapilacaklar:

- Kart seciminde buyuk onizleme drawer/modal acilir.
- Etiket Onizleme ve Lazer Onizleme sekmeleri ayrilir.
- Studio'da Ac, Lazer Kesim'de Ac, Onayla aksiyonlari gercek/pasif olarak ayrilir.

Risk:

- Lazer onizlemenin gercek lazer/RDWorks baslatmasi gibi algilanmasi.

Test:

- PDF/PNG preview var/yok, lazer isim var/yok.

### Faz 5 - Hatalari Duzelt

Yapilacaklar:

- Hatalar kategori bazli gruplanir.
- Yazisi kucuk, yazi tasiyor, model eksik, lazer tasmasi, isim eksik ayrilir.
- Hatalilar AI ile duzelt butonu gercek backend yoksa pasif/uyarili kalir.

Risk:

- Hatalari otomatik duzeltilmis gibi gostermek.

Test:

- Model eksik, uzun isim, bos isim, adet 0.

### Faz 6 - Uretime Al / Yazdirma Sirasi entegrasyonu

Yapilacaklar:

- Hazir kayitlar `bulk_generate_gallery_items_and_add_to_queue` ile uretime alinir.
- Queue kayitlari `source: bulk_production`, `source_label: Toplu Uretim` tasir.
- Hatalilar kullanici onayi olmadan uretime alinmaz.
- Lazer isimler ayri isim kesim hazirlik sozlesmesine aktarilir.
- Yazici/lazer otomatik baslamaz.

Risk:

- `laser_text`/`laser_name` alaninin backend Excel yaziminda bos kalmasi.

Test:

- Hazir kartlari siraya ekle, hatalilari disarida birak, queue source kontrolu.

### Faz 7 - Responsive / 1366 QA / Performance

Yapilacaklar:

- Sag ozet paneli 1366'da collapse edilebilir hale getirilir.
- Galeri 1920'de 3+ kolon, 1366'da 2 kolon hedefler.
- 500 satir icin lazy/virtualized grid uygulanir.
- Progress ve cancel davranisi netlestirilir.

Risk:

- Sag panelin galeriyi ezmesi.
- Worker progress bilgisinin yetersiz kalmasi.

Test:

- 1920x1080, 1600x900, 1366x768, 1280 genislik.

## 8. Guvenlik Kurallari

Production'da su kurallar korunacak:

- Sahte success yok.
- Eksik fonksiyon aktif production butonu gibi gorunmez.
- Yazici otomatik baslamaz.
- Lazer/RDWorks otomatik baslamaz.
- Trendyol canli durum guncellemesi yoksa lokal isaretleme dili kullanilir.
- Uretime alma oncesi preflight/validation gorunur olur.
- Hatali kayitlar kullanici onayi olmadan uretime alinmaz.
- Direct print, RDWorks acma veya lazer baslatma ancak ayri onayli task ile ele alinir.

## 9. Responsive Plan

1920x1080:

- Sag uretim ozeti acik kalabilir.
- Galeri 3 veya 4 kolon olabilir.
- Stepper tek satir compact kalmali.

1600x900:

- Sag ozet 320px civarinda tutulmali.
- Galeri 3 kolon hedeflenmeli.

1366x768:

- Sag ozet 300-320px araliginda kalmali veya collapse edilebilir olmali.
- Kaynak kartlari compact olmali.
- Stepper fazla yukseklik kaplamamali.
- Galeri 2 kolon hedeflenmeli.

500 satir:

- Tum kartlar ayni anda render edilmemeli.
- Lazy/virtualized grid veya sayfali galeri gerekir.
- Thumbnail uretimi cache/progress ile yonetilmeli.

## 10. Test Plani

Her production fazinda:

- `node --check src/webui/app.js`
- `npm run test`
- `npm run build --if-present`
- `npm run lint --if-present`
- `npm run typecheck --if-present`
- Ilgili Python gate script
- 1920 screenshot
- 1366 screenshot

Kullanici senaryolari:

1. Excel sec.
2. Kolonlari eslestir.
3. Model sec.
4. Galeri olustur.
5. Hatalilari goster.
6. Hazir kayitlari uretime al.
7. Yazdirma sirasina ekle.
8. Lazer isimleri Isim Kesim'e gonderme akisini veri hazirligi olarak test et.
9. Hatalilari uretim disinda birak.
10. Rapor indir butonu bagli degilse pasif/uyarili kaldigini dogrula.

## 11. Riskler

- Eski Excel dosyalarinda kolon adlari farkli olabilir; alias sistemi genisletilebilir ama mevcut mapping bozulmamali.
- `laser_name` sozlesmesi backend yaziminda guclendirilmeden lazer entegrasyonu guvenilir olmaz.
- Trendyol kaynagi henuz dogrudan Toplu Uretim'e aktarim yapmiyor.
- Manuel kaynak local state ile sinirli kalabilir; refresh sonrasi davranis netlestirilmeli.
- Galeri buyuk veri setlerinde performans riski tasir.
- Worker tek is calistiriyorsa toplu preview/render islemlerinde bekleme ve cancel dili net olmali.
- `AI ile duzenle` gercek AI backend'e bagli degilse heuristic olarak adlandirilmali.
- Rapor indir ve coklu manuel giris bagli degil; aktif success vermemeli.
- Production'a Design Lab class'larini dogrudan kopyalamak CSS borcunu buyutur.

## 12. Ilk Uygulanacak Gorev

Ilk production gorevi:

**Faz 1 - Toplu Uretim kaynak kartlari ve stepper iskeleti.**

Baslangic kapsamı:

- Sadece `section#bulkLabel` layout/chrome toparlanacak.
- Excel/Trendyol/Manuel kaynak kartlari netlestirilecek.
- Gercek handler'a bagli butonlar korunacak.
- Bagli olmayan butonlar pasif/uyarili hale getirilecek.
- Design Lab mock verisi production'a tasinmayacak.
- Backend/bridge imzasi degismeyecek.

Basari kriteri:

- Excel secme ve dry-run akisi bozulmaz.
- Trendyol ve manuel kaynaklar canli entegrasyon gibi davranmaz.
- Stepper daha okunur olur.
- 1920 ve 1366 gorunumleri bozulmaz.
- Testler gecer.
