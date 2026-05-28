# Yazdırma Sırası Production Entegrasyon Planı

## Mevcut Durum

CeyizHome Lab production Yazdırma Sırası ekranı aktif UI içinde `production-bot/src/webui/index.html` dosyasında `#printQueue` section olarak yer alıyor. Ekran şu anda güvenli yazdırma notu, özet kartları, filtreler, toplu seçim, ana queue listesi ve sağ seçili iş detayı içeriyor.

Aktif render ve davranış katmanı `production-bot/src/webui/app.js` içindedir. Ana render fonksiyonu `updatePrintQueue(rows)`; detay paneli `renderQueueDetail(item)`; filtreleme `filteredPrintQueueRows(rows)`; kaynak gösterimi `queueItemSourceLabel(item)` üzerinden çalışıyor.

Queue verisi Python tarafında `production-bot/src/webui_backend/print_queue_api.py` içinde `data/print_queue.json` dosyasına yazılıyor ve `list_print_queue(project_root)` ile okunuyor. PySide bridge zinciri `production-bot/src/webui_backend/bridge.py` üzerinden `production-bot/src/desktop/web_main_window.py` controller methodlarına bağlanıyor.

Design Lab Yazdırma Sırası referansı, production’a taşınacak görsel ve davranış standardını oluşturdu; ancak production ekranına doğrudan taşınmadan önce mevcut handler, source fallback, safe print ve status akışları korunarak fazlı geçiş yapılmalı.

## Mevcut Production Dosyaları

| Alan | Dosya / Fonksiyon | Not |
| --- | --- | --- |
| HTML section | `src/webui/index.html` / `section#printQueue` | Production Yazdırma Sırası ana ekranı. |
| JS state | `src/webui/app.js` / `printQueueFilterState`, `selectedPrintQueueItemId`, `selectedPrintQueueIds`, `printQueuePage` | Filtre, seçim, sayfalama ve detay state’i. |
| Render | `updatePrintQueue(rows)` | Liste, metrik, mini queue ve detay panelini günceller. |
| Detay panel | `renderQueueDetail(item)` | Seçili işin preview, metadata, validation ve aksiyonlarını gösterir. |
| Kaynak fallback | `queueItemSourceLabel(item)` | Önce `source_label`, sonra `source`, sonra path/localStorage/job_type fallback. |
| Queue backend | `src/webui_backend/print_queue_api.py` | JSON queue persistence ve status güncellemeleri. |
| Queue dosyası | `data/print_queue.json` | Kalıcı queue kayıtları. |
| Bridge | `src/webui_backend/bridge.py` | Frontend callable methodlar. |
| Controller | `src/desktop/web_main_window.py` | Bridge methodlarını backend API’ye bağlar. |

## Queue Veri Sözleşmesi

Yeni production standardı her queue satırında aşağıdaki alanları desteklemeli. Alanların hepsi zorunlu olmak zorunda değil; eski kayıtlar fallback ile çalışmaya devam etmeli.

| Alan | Kaynak | Kullanım |
| --- | --- | --- |
| `id` | Backend | Satır seçimi, silme, status update. |
| `relative_path` | Backend | PDF açma, safe print, dosya adı, preview eşleştirme. |
| `path` | Eski/alternatif | `relative_path` yoksa fallback. |
| `job_type` | Backend/eski kayıt | Eski kayıt fallback ve kaba tip ayrımı. |
| `source` | Yeni standart | `etiket_studio`, `manual_label`, `trendyol`, `bulk_production`, ileride `laser`. |
| `source_label` | Yeni standart | Kullanıcıya gösterilecek kaynak adı. |
| `rendered_source` | Önerilen gelecek alan | Çıktının hangi render motorundan geldiğini ayırmak için; bu fazda zorunlu değil. |
| `model_name` | Backend veya output history | Model adı. |
| `job_name` | Backend | Model adı yoksa iş adı fallback. |
| `label_text` | Backend veya output history | İsim/metin. |
| `date_text` | Output history | Tarih. Şu an çoğunlukla history/metadata’dan geliyor. |
| `note_text` | Output history | Not. Şu an çoğunlukla history/metadata’dan geliyor. |
| `quantity` | Backend veya metadata | Adet. |
| `status` | Backend | Beklemede, Yazdırıldı, Teslim edildi. |
| `validation_status` | Backend veya output history | Doğrulandı, kontrol gerekli, dosya yok. |
| `created_at` | Backend | Tarih filtresi ve sıralama. |
| `preview_uri` | Backend | Thumbnail/önizleme. |
| `pdf_path` | Output history | PDF eşleştirme, varsa. |
| `png_path` | Output history | PNG önizleme eşleştirme, varsa. |

Öneri: Production taşıma sırasında UI bu sözleşmeye göre okunmalı, fakat backend migration zorunlu yapılmamalı. Eski kayıtlar `job_type`, `relative_path`, output history ve localStorage override fallback ile görünmeye devam etmeli.

## Source Rozet Standardı

| Kaynak | `source` | `source_label` | Görsel standart |
| --- | --- | --- | --- |
| Etiket Studio | `etiket_studio` | `Etiket Studio` | Mor/mavi |
| Manuel Etiket | `manual_label` | `Manuel Etiket` | Gri/mavi |
| Trendyol | `trendyol` | `Trendyol` | Turuncu/mor |
| Toplu Üretim | `bulk_production` | `Toplu Üretim` | Yeşil/mavi |
| Lazer | `laser` önerilir | `Lazer` | Mor |
| Eski/Fallback | boş | `job_type` fallback | Gri, “Eski kayıt” notu |

Mevcut backend `SOURCE_LABELS` içinde Etiket Studio, Manuel Etiket, Trendyol ve Toplu Üretim var. Lazer source desteği bu planın dışında ayrı task olarak eklenmeli.

## Design Lab Referansından Taşınacaklar

- Kaynak rozet standardı.
- Net güvenli yazdırma uyarısı: yazıcı otomatik çalışmaz, PDF kontrolünden sonra kullanıcı manuel onaylar.
- Metrik kartlarının sade hiyerarşisi.
- Filtre satırında kaynak/tip ayrımının daha okunur hale gelmesi.
- Toplu aksiyon barında seçili iş sayısı ve pasif/aktif aksiyon ayrımı.
- Ana liste için tablo/kart hibriti: sıra, önizleme, iş bilgileri, dosya/detay, durum/kalite, aksiyonlar.
- Sağ detay panelinde büyük önizleme, kaynak, dosya, validation, queue durumu ve güvenlik notu.
- 1366 görünümde sağ panelin ana listeyi ezmemesi için kapat/aç veya alt kırılım planı.

## Taşınmayacaklar

- Mock veriler.
- Design Lab’e özel class isimlerinin kör kopyası.
- Production dışı butonlar veya gerçek backend karşılığı olmayan sahte aksiyonlar.
- Gerçek yazıcıyı otomatik başlatan herhangi bir davranış.
- Lazer/RDWorks veya Trendyol canlı aksiyonları.
- Queue backend mimarisini baştan yazan büyük refactor.

## Button / Handler / Bridge Eşleşmesi

| Buton | Mevcut frontend handler | Bridge/backend karşılığı | Production davranışı | Plan |
| --- | --- | --- | --- | --- |
| Yenile | `refreshState()` | `get_state` akışı | State’i yeniden alır. | Korunacak. |
| Sırayı Temizle | `confirmClearPrintQueue()` -> `clearPrintQueueConfirmed()` | `bridge.clear_print_queue` | Confirm modal sonrası temizler. | Tehlikeli aksiyon olarak confirm korunacak. |
| Sadece Bekleyenler | `refreshPrintQueueFilters()` | Yok, frontend filter | UI filtre. | Korunacak, daha net chip yapılabilir. |
| Yazdırılanları Gizle | `refreshPrintQueueFilters()` | Yok, frontend filter | Pending filtreye indirger. | Korunacak, label netleştirilecek. |
| Test/QA Arşivi | `queueTestArchiveToggle`, `showPrintQueueTestArchive()` | Yok, frontend filter | Test/archive işleri gösterir. | Design Lab standardına göre üst aksiyon yapılabilir. |
| Tümünü Seç | `toggleAllPrintQueueSelection(checked)` | Yok, frontend selection | Filtrelenmiş işleri seçer. | Korunacak. |
| Seçilenleri Yazdır | `printSelectedQueueItems()` | `safePrint(firstSelected.id)` -> `bridge.print_queue_item_safe` | İlk seçili işi güvenli print modalına alır. | Faz 4’te çoklu davranış dili netleşmeli; otomatik toplu print yok. |
| Seçilenleri Sıradan Kaldır | `removeSelectedQueueItems()` | `bridge.remove_from_print_queue` | Confirm sonrası siler. | Korunacak, batch result error handling güçlendirilebilir. |
| Seçilenleri Yazdırıldı İşaretle | `markSelectedQueuePrinted()` | `bridge.mark_queue_item_printed` | Status günceller. | Korunacak. |
| Seçilenleri Teslim Et | `markSelectedQueueDelivered()` | `bridge.mark_queue_item_delivered` | Status günceller. | Korunacak. |
| Seçilen PDF’leri Aç | `openSelectedQueuePdfs()` | `openPdfPreview` / `get_pdf_preview_payload` | Şu an ilk seçili PDF’i açar. | Etiket “İlk seçili PDF’i aç” veya gerçek multi-open ayrı task. |
| PDF Aç | `openPdfPreview(path)` | `bridge.get_pdf_preview_payload` | App içinde PDF preview. | Korunacak. |
| PNG Aç | `selectManualPngPreview(path)` | Yok, frontend label outputs view | PNG çıktılar sayfasında açılır. | Korunacak; PNG yoksa net uyarı. |
| Yazdır | `safePrint(id)` -> `requestPdfPrint()` | `bridge.print_queue_item_safe`, `bridge.get_pdf_preview_payload`, sonra `open_project_file` sadece kullanıcı onayıyla | Yazıcı otomatik başlamaz, PDF açma onayı ister. | Kritik güvenlik davranışı korunacak. |
| Yazıldı | `markQueuePrinted(id)` | `bridge.mark_queue_item_printed` | Status “Yazdırıldı”. | Korunacak. |
| Teslim | `markQueueDelivered(id)` | `bridge.mark_queue_item_delivered` | Status “Teslim edildi”. | Korunacak. |
| Kaldır | `removeQueueItem(id)` | `bridge.remove_from_print_queue` | Confirm sonrası siler. | Korunacak. |
| Beklemeye Al | `markQueuePending(id)` | `bridge.mark_queue_item_pending` | Printed/delivered işi beklemeye alır. | Korunacak. |
| Studio’da Aç | `openQueueItemInStudio(id)` | Yok, frontend navigation/model selection | Etiket Studio’ya götürür. | Kaynak/model fallback başarısızsa uyarı iyileştirilmeli. |

## Güvenlik Kuralı

Production Yazdırma Sırası entegrasyonunda aşağıdaki kurallar değişmez:

- Yazıcı otomatik başlamaz.
- `Yazdır` butonu doğrudan yazıcıya göndermez.
- `safePrint(id)` önce `print_queue_item_safe` ile dosya ve direct print durumunu kontrol eder.
- `print_queue_item_safe(..., direct_print_enabled=False)` şu anda `MANUAL_PRINT_REQUIRED` döndürür.
- `requestPdfPrint` PDF preview payload alır ve güvenli onay modalı açar.
- Kullanıcı onaylamadan `open_project_file` çağrılmaz.
- Sırayı temizle, sıradan kaldır gibi yıkıcı aksiyonlarda confirm korunur.
- Backend sonucu yoksa success gösterilmez.

Direct print ileride açılırsa ayrı ayar, açık güvenlik metni, yazıcı seçimi, önizleme ve kullanıcı onayı olmadan devreye alınmamalı.

## Production Hedef Layout

Production hedefi Design Lab’e yaklaşacak ama mevcut handler’ları koruyacak:

- Üst başlık: Yazdırma Sırası.
- Güvenli yazdırma uyarısı.
- Metrik kartları: sıradaki iş, toplam iş, toplam adet, bekleyen, yazdırıldı, kontrol gerekli.
- Filtreler: arama, durum, tip/kaynak, tarih, sıralama, filtre temizle.
- Toplu aksiyon barı: seçim yoksa düşük vurgu/pasif, seçim varsa etkin.
- Ana liste: tablo/kart hibriti.
- Sağ seçili iş detayı: kapat/aç planlı, 1366’da listeyi ezmeyecek.

## Responsive Plan

### 1920x1080

- Sağ panel 340-380px bandında kalabilir.
- Ana liste genişliği rahat; 6 kolonlu satır yapısı kullanılabilir.
- Metrikler 6 kolon veya 3+3 dengeli dizilebilir.
- Filtreler tek satıra yakın kalabilir.

### 1366x768

- Sağ panel 320px üstüne çıkmamalı.
- Ana liste minimum 0 flex/grid mantığıyla kalmalı.
- Çok geniş satır kolonları yatay scroll yerine kontrollü satır içi compact düzen kullanmalı.
- Filtreler 2-3 satıra kırılabilir.
- Toplu aksiyon barı wrap olmalı; seçim sayısı solda sabit kalmalı.
- Sağ panel için faz 2’de collapse/toggle değerlendirilmelidir.

## Entegrasyon Fazları

### Faz 1 — Source / Source_Label Rozet Standardı

Yapılacaklar:
- `queueItemSourceLabel(item)` mevcut fallback’i korunarak `queueItemSourceKey(item)` gibi küçük helper planlanır.
- Production listede kaynak metni düz yazı yerine standardize rozet class’ı ile gösterilir.
- Eski source’suz kayıtlar `job_type` fallback ile gri “Eski kayıt” davranışını alır.

Dosyalar:
- `src/webui/app.js`
- `src/webui/styles.css`

Risk:
- Filtre tipi hâlâ `job_type` üzerinden çalışıyor; source bazlı filtre ayrı dikkat ister.

Test:
- Etiket Studio, Manuel Etiket ve eski kayıt fallback gate.
- `node --check src/webui/app.js`
- `npm run test`
- Production queue source persistence gate.
- 1920/1366 screenshot.

### Faz 2 — Sağ Detay Paneli

Yapılacaklar:
- Detay paneli Design Lab bilgi hiyerarşisine yaklaştırılır.
- Kaynak, dosya, validation, queue durumu ve güvenlik notu daha okunur olur.
- PDF/PNG yoksa net uyarı gösterilir.
- 1366 için panel daraltma veya collapse seçeneği hazırlanır.

Dosyalar:
- `src/webui/index.html`
- `src/webui/app.js`
- `src/webui/styles.css`

Risk:
- Mevcut `renderQueueDetail` action butonlarını kırmamak gerekir.

Test:
- PDF aç, PNG yok, safe print modal, status update.

### Faz 3 — Metrik Kartları ve Filtreler

Yapılacaklar:
- Metrik kartları Design Lab standardına göre sadeleştirilir.
- Tip filtresi source-aware hale getirilir: Etiket Studio, Manuel Etiket, Trendyol, Toplu Üretim, Lazer, eski kayıt.
- “Yazdırılanları Gizle” ve “Sadece Bekleyenler” çakışması netleştirilir.

Risk:
- Eski `job_type` filtre davranışı bozulabilir.

Test:
- Source’lu ve source’suz kayıtlarla filtre testi.

### Faz 4 — Toplu Aksiyon Barı

Yapılacaklar:
- Seçim yoksa butonlar pasif/düşük vurgu olur.
- Seçim varsa seçili sayı, hazır/kontrol gerekli ayrımı gösterilir.
- “Seçilenleri Yazdır” otomatik toplu print yapmaz; ilk seçili iş için güvenli modal veya çoklu PDF açma planı net yazılır.

Risk:
- Kullanıcı “seçilenleri yazdır” deyince otomatik yazıcı bekleyebilir; metin güvenli olmalı.

Test:
- 0 seçim, 1 seçim, çok seçim, kontrol gerekli iş seçimi.

### Faz 5 — Satır Tasarımı

Yapılacaklar:
- Ana liste satırları Design Lab tablo/kart hibritine yaklaştırılır.
- Kaynak rozeti, dosya tipi rozeti, validation ve status birbirinden ayrılır.
- PDF/PNG/durum aksiyonları gruplandırılır.

Risk:
- Satır yüksekliği artarsa 1366’da yoğunluk düşebilir.
- PDF thumbnail hydrate performansına dikkat edilmeli.

Test:
- 20+ queue row ile scroll ve sayfalama.

### Faz 6 — Responsive ve 1366 QA

Yapılacaklar:
- 1920 ve 1366 screenshot gate.
- Sağ panel listeyi eziyorsa collapse.
- Filtre/action bar wrap davranışı.
- Yatay taşma kontrolü.

Risk:
- Monolitik CSS içinde başka sayfalara sızan selector riski.

Test:
- `node --check src/webui/app.js`
- `npm run test`
- Queue source persistence gate.
- Yeni production print queue visual gate.
- 1920/1366 screenshot.

## Test Planı

Her faz sonunda:

- `node --check src/webui/app.js`
- `npm run test`
- `npm run build --if-present`
- `npm run lint --if-present`
- `npm run typecheck --if-present`
- Queue source persistence gate
- Production Yazdırma Sırası visual/runtime gate
- Screenshot:
  - 1920x1080
  - 1366x768

Minimum kullanıcı senaryoları:

1. Etiket Studio’dan queue kaydı ekle, source rozeti Etiket Studio görünsün.
2. Manuel Etiket’ten queue kaydı ekle, source rozeti Manuel Etiket görünsün.
3. Eski source’suz kayıt job_type fallback ile görünmeye devam etsin.
4. PDF Aç çalışsın.
5. PNG yoksa net uyarı versin.
6. Yazdır safe modal açsın, yazıcı otomatik başlamasın.
7. Yazıldı/Teslim status update yapsın.
8. Kaldır confirm sonrası silsin.
9. Sırayı Temizle confirm sonrası temizlesin.

## Riskler

- Eski source’suz kayıtlar: `source_label` yoksa fallback davranışı korunmalı.
- `job_type` fallback: mevcut `Manuel` değeri Etiket Studio ve Manuel Etiket ayrımı için yetersiz; yeni source alanı varken öncelik source olmalı.
- PDF/PNG path eksik kayıtlar: aksiyonlar sahte success vermemeli, net uyarı göstermeli.
- Yazdırma güvenliği: `safePrint` ve `requestPdfPrint` zinciri bozulmamalı.
- Direct print ayarları: şu an kapalı; açılması ayrı güvenlik taskı olmalı.
- Çok fazla queue row: mevcut sayfalama var; thumbnail hydrate cache korunmalı.
- Sağ panel: 1366’da ana listeyi ezebilir; collapse planı gerekli.
- CSS sızıntısı: Design Lab class’ları production’a kör kopyalanmamalı.
- Bridge error handling: status update ve remove işlemleri callback sonucunu detaylı göstermiyor; ileride hata mesajları iyileştirilmeli.

## İlk Uygulanacak Görev

İlk production görevi düşük riskli olmalı:

**Faz 1 — Source / Source_Label Rozet Standardı**

Kapsam:
- Production queue listesinde `queueItemSourceLabel(item)` çıktısı düz metin yerine standardize source rozeti olarak gösterilecek.
- Yeni helper ile source key belirlenecek: önce `item.source`, sonra localStorage/path fallback, sonra `job_type`.
- Eski kayıtlar gri fallback rozetiyle gösterilecek.
- Tip/kaynak filtresi henüz büyük değiştirilmeyecek; yalnızca görsel ayrım ve fallback doğrulanacak.

Başarı kriteri:
- Etiket Studio ve Manuel Etiket kayıtları farklı kalıcı rozetle görünür.
- Eski kayıt bozulmaz.
- Yazdırma güvenliği değişmez.
- Testler ve screenshotlar geçer.
