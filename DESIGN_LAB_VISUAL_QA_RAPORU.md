# Design Lab Visual QA Raporu

## Test Tarihi

2026-05-20

## Test Edilen Ekranlar

- Etiket Studio Referans
- İsim Kesim Referans

## Çözünürlükler

- 1920x1080
- 1366x768

## Etiket Studio Görsel Kontrol

Durum: PARTIAL / PASSED

Bulgular:

- CeyizHome Lab marka kilidi, Hızlı Üretim Modu rozeti ve mock/referans etiketi net görünüyor.
- Command bar modern butonlarla çalışıyor; default HTML button görünümü yok.
- Model/ölçü satırı canvas üzerine binmiyor.
- Font toolbar, sol araç çubuğu, sağ Alanlar paneli ve canlı etiket mock alanı aynı referans ekran içinde okunabilir durumda.
- Alan sırası doğru: İsim, Tarih, Not, Adet, Lazer isim.
- Lazer isim açıklaması görünüyor.
- Renk paleti kare renk kutuları olarak tasarlanmış; siyah çizgi/slider görünümü yok.
- Sağ panel inputları ikinci düzeltmeden sonra 1366 görünümde de metni kesmeden gösteriyor.

Sorunlar:

- 1366x768 görünümde Design Lab üst başlık ve sekme alanı viewport yüksekliğinden pay aldığı için Etiket Studio referansının alt palet/status alanı ilk ekranda tamamen görünmüyor. Bu production entegrasyonunda Design Lab chrome'u olmayacağı için production riskinden çok Design Lab sunum kısıtı olarak değerlendirildi.
- Etiket canvas'ı 1366 görünümde kullanılabilir ama daha fazla dikey alan için sonraki turda Design Lab üst hero alanı daha da kompakt hale getirilebilir.

Düzeltildi:

- `.design-lab-page` kapsamındaki hero, tab, command bar, model/font satırları ve workbench ölçüleri kompaktlaştırıldı.
- Sağ Alanlar panelinde inputların kesilmemesi için alan grid ölçüleri ve input/font boyutları düzenlendi.

Screenshot yolları:

- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\design_lab_visual_qa\etiket-studio-1920.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\design_lab_visual_qa\etiket-studio-1366.png`

## İsim Kesim Görsel Kontrol

Durum: PASSED

Bulgular:

- CeyizHome Lab / İsim Kesim command bar net ve üretim odaklı görünüyor.
- Yeni, Aç, Kaydet, Geri, İleri, Yakınlaştır, Ekrana Sığdır, Otomatik Diz, Weld, Noktaları Bağla ve SVG/DXF/PDF Çıktı aksiyonları modern butonlarla gösteriliyor.
- Sol isim kaynağı paneli ve isim listesi okunur.
- 800 x 600 mm beyaz çalışma tablası, cetvel, grid ve kırmızı çalışma sınırı net.
- İsimler siyah outline/curve hissinde.
- Burak, Ceren, Serkan ve diğer isimler birbirine bağlanmadan gösteriliyor; isimler arasında köprü/weld/çizgi yok.
- İsimler birbirine yakın ama temas etmeyecek şekilde tekrar konumlandırıldı.
- Sağ panel sekmeleri ve ayar özetleri görünüyor: Yerleşim, Yazı/Stil, Boyut, Kalınlaştırma, Kontrol, Çıktı.
- Minimum boşluk 1.5 mm, font Mochary Use Personal, offset 0.30 mm ve kullanılan alan %92 bilgileri görünüyor.
- 1366x768 görünümde çalışma tablası daralmadan ana odak olarak kalıyor.

Sorunlar:

- 1366 genişlikte command bar içinde kontrollü yatay kaydırma çubuğu oluşuyor. Butonlar kesilmiyor; bu durum kompakt desktop davranışı olarak kabul edilebilir.
- Gerçek path/outline üretimi bu Design Lab mock ekranın kapsamı dışında; production entegrasyon turunda ayrıca test edilmelidir.

Düzeltildi:

- `.design-lab-page` kapsamındaki İsim Kesim grid yüksekliği ve panel ölçüleri kompaktlaştırıldı.
- Mock isimlerin font ölçeği ve x/y konumları yeniden ayarlanarak isimler arası temas riski giderildi.

Screenshot yolları:

- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\design_lab_visual_qa\isim-kesim-1920.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\design_lab_visual_qa\isim-kesim-1366.png`

## Production'a Dokunuldu mu?

Hayır.

Yapılan değişiklikler sadece:

- `production-bot/src/webui/styles.css` içindeki `.design-lab-page` scoped CSS alanı
- Bu QA raporu
- Screenshot çıktıları

Production Etiket Studio, Trendyol, Toplu Üretim, İsim Kesim ekranları ve Python bridge/backend methodları değiştirilmedi.

## Test Komutları

- `node --check src/webui/app.js`: PASSED
- `npm run test`: PASSED
- `npm run build --if-present`: PASSED / script mevcut değil
- `npm run lint --if-present`: PASSED / script mevcut değil
- `npm run typecheck --if-present`: PASSED / script mevcut değil
- `git status --short`: repo kökünde `production-bot/`, `renders/`, `scripts/`, `tools/` untracked görünüyor.

## Sonuç

- Etiket Studio Referans: production entegrasyonuna tasarım yönüyle yakın; 1366 Design Lab sunum yüksekliği nedeniyle PARTIAL/PASSED. Production'a taşımadan önce aynı layout Design Lab chrome'u olmadan bir kez daha 1366 test edilmelidir.
- İsim Kesim Referans: production entegrasyonuna görsel referans olarak hazır. Sonraki production turunda gerçek font/path/export davranışı ayrı doğrulanmalıdır.

## Sonraki Adım

Etiket Studio ve İsim Kesim görsel kalite olarak yeterli seviyeye geldi. Sıradaki Design Lab ekranı Trendyol Siparişleri olmalıdır.

## 2026-05-20 V2 Görsel Düzeltme Turu

### Neler Düzeltildi?

- Design Lab hero alanı kompaktlaştırıldı: büyük başlık küçültüldü, açıklama tek satır davranışına alındı, sekme ve üst boşluklar azaltıldı.
- Etiket Studio Referans içinde model/ölçü satırı ve font toolbar daha düşük yükseklikte tutuldu.
- Etiket canvas alanı yukarı taşındı ve 1366x768 görünümde ana çalışma alanı daha erken görünür hale getirildi.
- Etiket preview yeniden dengelendi: `Ayşe & Mehmet` tek satırda, daha okunur ve selection box tarafından boğulmadan görünüyor.
- Tarih ve not yerleşimi isim alanına göre daha dengeli hale getirildi.
- Sağ Alanlar paneli daha kompakt hale getirildi; input metinleri 1366 görünümde kesilmeden okunuyor.
- İsim Kesim Referans içinde mock tabla daha yoğun nesting görünümüne alındı.
- İsim sayısı artırılarak 800x600 tabla daha verimli dolu gösterildi.
- Burak, Ceren, Serkan gibi ayrı isimler arasında bağlantı çizgisi/köprü/weld olmadan, yakın ama temas etmeyen yerleşim korundu.
- Noktalı harf ve bağlantı uyarı rozetleri tablaya daha anlaşılır yerleştirildi.

### Etiket Studio Production Referansı Hazır mı?

Durum: HAZIR / KONTROLLÜ

V2 ekranı production entegrasyonuna tasarım referansı olarak kullanılabilir. Ana aksiyonlar, model/ölçü satırı, font toolbar, canvas, sağ Alanlar paneli ve seçili metin kutusu okunur hale geldi. 1366x768 Design Lab görünümünde alt renk paleti ilk ekranda tam görünmeyebilir; bunun ana nedeni Design Lab üst chrome ve global uygulama header alanıdır. Production'a taşınırken aynı layout chrome olmadan bir kez daha 1366 testi yapılmalıdır.

### İsim Kesim Production Referansı Hazır mı?

Durum: HAZIR

V2 ekranı lazer isim kesim referansı olarak hazırdır. 800x600 mm tabla net, beyaz tema doğru, isimler siyah outline/curve hissinde, farklı isimler birbirine bağlanmıyor ve tabla artık yoğun nesting mantığını gösteriyor. Gerçek production entegrasyonunda path/outline export, gerçek font ölçümü ve minimum boşluk kontrolü ayrıca doğrulanmalıdır.

### 1366 Görünümde Durum

- Etiket Studio: Ana canvas, sağ Alanlar paneli ve command bar okunur. Alt renk paleti/status alanı Design Lab chrome nedeniyle ilk viewport'un alt sınırına yakındır; production entegrasyonunda yeniden test edilmelidir.
- İsim Kesim: Çalışma tablası, sol isim kaynağı ve sağ ayar paneli okunur. Tabla yoğun yerleşim gösterir; command bar kompakt desktop davranışıyla yatay akışı korur.

### V2 Screenshot Yolları

- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\design_lab_visual_qa_v2\etiket-studio-v2-1920.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\design_lab_visual_qa_v2\etiket-studio-v2-1366.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\design_lab_visual_qa_v2\isim-kesim-v2-1920.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\design_lab_visual_qa_v2\isim-kesim-v2-1366.png`

### Production Ekranlara Dokunuldu mu?

Hayır.

Bu turdaki değişiklikler sadece Design Lab referans markup'ı, `.design-lab-page` scoped CSS ve rapor/screenshot çıktıları ile sınırlıdır. Production Etiket Studio, Production İsim Kesim, Trendyol, Toplu Üretim ve Python bridge/backend tarafına dokunulmadı.

### V2 Son Karar

Etiket Studio ve İsim Kesim V2 görselleri production referansı için yeterli seviyeye getirildi. Sıradaki Design Lab ekranı Trendyol Siparişleri olmalıdır. Production entegrasyonuna geçildiğinde önce Etiket Studio'nun chrome'suz 1366 testi, ardından İsim Kesim'in gerçek font/path/export testi yapılmalıdır.
