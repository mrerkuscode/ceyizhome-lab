# Production Bot MVP

Bu proje, kişiye özel ürün üretimi için yerel Windows üzerinde çalışan güvenli bir MVP otomasyon aracıdır.

MVP yalnızca dosya ve rapor üretir:

- Temiz üretim Excel şemasını okur.
- Satırları `process_type` ve `personalization_type` kurallarına göre doğrular.
- PRINT ve BOTH siparişleri için baskı hazırlık dosyaları üretir.
- LASER_ENGRAVE, LASER_CUT ve BOTH siparişleri için güvenli lazer hazırlık dosyaları üretir.
- `summary_report.csv` ve `errors_report.csv` raporlarını yazar.

Bu sürüm CorelDRAW'u açmaz, yazdırma yapmaz, RDWorks'ü açmaz ve lazeri başlatmaz.

## Güvenli Üretim Motoru ve Intelligence Katmanı

Sistem iki ayrı katmandan oluşur:

1. Güvenli üretim motoru

- Excel'i okur.
- Zorunlu alanları doğrular.
- PRINT, LASER_ENGRAVE, LASER_CUT, BOTH ve NONE akışlarını deterministik kurallarla işler.
- Dosya ve rapor üretir.
- CorelDRAW, yazıcı, RDWorks veya lazer makinesini çalıştırmaz.
- Üretim için tek gerçek kaynak bu deterministik motordur.

2. Intelligence / recommendation katmanı

- Siparişleri analiz eder.
- Uyarı, öneri ve inceleme nedeni üretir.
- Belirsiz alanlarda insan kontrolü ister.
- Üretim verisini sessizce değiştirmez.
- Yazdırma veya lazer başlatma yetkisi yoktur.
- İleride OpenAI API veya yerel LLM entegrasyonu bu arayüzlere eklenebilir.

İnsan inceleme adımı kritiktir. `NEEDS_REVIEW` görülen hiçbir sipariş, Excel'de düzeltilmeden üretime alınmamalıdır.

## Kurulum

```powershell
cd "C:\Users\Pc\Documents\New project\production-bot"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ayarlar

Ana ayar dosyası:

```text
config/settings.yaml
```

Kullanıcı üretim davranışını bu dosyadan değiştirebilir; kod dosyalarını düzenlemesi gerekmez.

Önemli ayarlar:

```yaml
app:
  output_date_format: "%Y-%m-%d"
  language: "tr"

excel:
  mode: "clean_production_excel"
  input_file: "input/siparisler.xlsx"

templates:
  print_folder: "templates/print"
  laser_folder: "templates/laser"

print:
  generate_print_data_csv: true
  auto_print_enabled: false

laser:
  auto_start_laser: false
  output_format: "svg"
  plate_width_mm: 600
  plate_height_mm: 400
  margin_mm: 5
  gap_x_mm: 3
  gap_y_mm: 3
  include_order_number_guide: true

laser_text:
  laser_font_path: "assets/fonts/connected_script.ttf"
  default_font_size_mm: 28
  min_font_size_mm: 18
  max_font_size_mm: 36
  force_connected_letters: true
  convert_text_to_paths: true
  warn_if_disconnected_shapes: true
  add_bridges_for_dots_and_accents: false

reports:
  generate_errors_report: true
  generate_summary_report: true
  generate_layout_report: true
  generate_template_matching_report: true
```

Program açılışta ayarları kontrol eder, gerekli klasörler yoksa oluşturur ve terminalde kısa bir başlangıç özeti gösterir. Normal kullanıcı hatalarında karmaşık Python hata izi gösterilmez; örneğin eksik ayar, yanlış Excel yolu veya güvenlik açısından kapalı olması gereken otomatik yazdırma/lazer ayarı açıkça açıklanır.

Güvenlik nedeniyle MVP'de şu ayarlar `false` kalmalıdır:

```yaml
print:
  auto_print_enabled: false

laser:
  auto_start_laser: false
```

LASER_CUT işi varsa ve `assets/fonts/connected_script.ttf` bulunmuyorsa sistem yanlış kesim dosyası üretmez; ilgili sipariş hata raporuna yazılır.

## Çalıştırma

Varsayılan gerçek çalışma:

```powershell
python src\main.py
```

Bu komut varsayılan olarak şu Excel dosyasını okur:

```text
input/siparisler.xlsx
```

Boş üretim Excel şablonu oluşturmak için:

```powershell
python src\main.py --create-template
```

Bu komut yalnızca doğru kolon başlıklarını, temel formatı ve açılır liste hazırlığını içeren boş şablonu oluşturur:

```text
input/cyzella_production_template.xlsx
```

Masaüstü uygulamasında **Boş Excel Şablonu Oluştur** düğmesine basıldığında aynı dosya oluşturulur ve Windows üzerinde açılmaya çalışılır. Excel otomatik açılmazsa `Input Klasörünü Aç` düğmesiyle dosyaya ulaşabilirsiniz.

Örnek verili demo Excel dosyası oluşturmak için:

```powershell
python src\main.py --create-demo
```

Bu komut şu dosyayı oluşturur:

```text
input/demo_siparisler.xlsx
```

Demo dosyası şu örnekleri içerir:

- Türkçe karakterli isimler: Ayşe, Gülşah, Mücahit, İrem, Çağla, Ömer, Şükran
- PRINT, LASER_ENGRAVE, LASER_CUT, BOTH ve NONE süreçleri
- Gold label print
- Silver label print
- Laser cut connected handwriting name
- Both label and laser name
- No personalization
- Extra chocolate
- Extra madlen
- Missing template
- Missing laser_text
- Long laser_text

Farklı bir Excel dosyası ile çalıştırmak için:

```powershell
python src\main.py --excel "input\siparisler.xlsx"
```

Eski uyumluluk için `--input` da desteklenir:

```powershell
python src\main.py --input "input\siparisler.xlsx"
```

Belirli bir üretim tarihi için:

```powershell
python src\main.py --date 2026-04-27
```

Sadece kontrol yapmak, üretim dosyası oluşturmadan ne olacağını görmek için:

```powershell
python src\main.py --dry-run
```

Demo dosyası ile dry-run yapmak için:

```powershell
python src\main.py --excel input\demo_siparisler.xlsx --dry-run
```

Eski Cyzella Excel dosyasını temiz üretim formatına dönüştürmek için:

```powershell
python src\main.py --convert-legacy-excel
```

Bu komut varsayılan olarak şunu okur:

```text
input/siparisler.xlsx
```

Farklı bir eski Excel dosyası dönüştürmek için:

```powershell
python src\main.py --convert-legacy-excel --excel input\eski_siparisler.xlsx
```

Legacy converter çıktıları:

```text
output/YYYY-MM-DD/converted/cyzella_clean_orders.xlsx
output/YYYY-MM-DD/converted/normalized_orders.csv
output/YYYY-MM-DD/converted/legacy_import_warnings.csv
```

Bu dönüştürücü eski manuel Excel'i üretime doğrudan sokmaz. Sadece temiz üretim şemasına yardımcı aktarım yapar. `model_no`, `template_no`, `process_type` veya `personalization_type` kesin değilse satırı `needs_review=true` yapar ve `legacy_import_warnings.csv` içine nedenini yazar.

Dry-run şunları yapar:

- Excel'i okur.
- Satırları doğrular.
- Print ve lazer iş sayılarını gösterir.
- Hata varsa `errors_report.csv` üretir.
- Print klasörleri, job dosyaları, lazer SVG dosyaları veya üretim plakaları oluşturmaz.

Gerçek çalışma için:

```powershell
python src\main.py --excel input\siparisler.xlsx
```

Komut sonunda terminalde şunlar gösterilir:

```text
Toplam sipariş
Geçerli sipariş
Hata/inceleme kaydı
Print jobs
Laser engrave jobs
Laser cut jobs
Both jobs
Output klasörü
```

Hata varsa rapor yolu ayrıca gösterilir:

```text
output/YYYY-MM-DD/reports/errors_report.csv
```

Beklenmeyen teknik hatalarda kullanıcıya sade bir mesaj gösterilir. Geliştirici logları şu dosyaya yazılır:

```text
output/YYYY-MM-DD/logs/app.log
```

Normal kullanıcı hataları için karmaşık Python hata izi gösterilmez.

## Testler

Testler standart Python `unittest` ile çalışır; ek test paketi kurmak gerekmez.

```powershell
python -m unittest discover -s tests -v
```

Testler şu güvenlik noktalarını kontrol eder:

- Excel okuma ve Türkçe karakterlerin korunması
- Zorunlu kolon doğrulama
- Geçersiz `process_type`
- Eksik `buyer_name`
- PRINT için eksik `label_text`
- LASER_CUT için eksik `laser_text`
- Çıktı klasörü oluşturma
- Print şablon eşleşmesi
- Birden fazla print şablonu çakışması
- Eksik print şablonu
- Lazer row-based nesting
- Çok uzun lazer metni
- Eksik bağlı el yazısı fontu

Bu testler üretimden önce sistemin güvenli şekilde hata verdiğini ve riskli işleri sessizce üretime almadığını kanıtlamak için eklendi.

## Temiz Üretim Excel Şeması

Varsayılan Excel dosyası:

```text
input/siparisler.xlsx
```

Ana üretim şablonu:

```text
input/cyzella_production_template.xlsx
```

Final kolonlar:

```text
order_no
buyer_name
product_name
model_no
template_no
process_type
personalization_type
label_variant
label_text
laser_text
quantity
material_type
material_thickness_mm
extra_chocolate_qty
extra_madlen_qty
production_note
needs_review
status
```

Alan anlamları:

- `buyer_name`: müşteri/alıcı takibi içindir; baskı veya lazer metninin ana kaynağı değildir.
- `label_text`: CorelDRAW ve basılı etiket çıktısı için kullanılacak metindir.
- `laser_text`: lazer kazıma/kesim hazırlığı için kullanılacak metindir.
- `label_variant`: baskı varyantını belirler.
- `production_note`: üretim ekibine not içindir.
- `needs_review`: kullanıcı veya import aşaması tarafından işaretlenebilir.
- `status`: sipariş durumunu takip eder.

Eski `gold/gümüş` gibi kolonlar ana otomasyon formatı değildir. Bunlar ileride yalnızca legacy Excel dönüştürme/import aşamasında kullanılabilir.

## Kolonları Doldurma

- `order_no`: sipariş numarası.
- `buyer_name`: müşterinin/alıcı kişinin adı.
- `product_name`: ürün adı.
- `model_no`: üretim modeli numarası.
- `template_no`: kullanılacak şablon numarası veya kodu.
- `process_type`: yapılacak üretim tipi.
- `personalization_type`: kişiselleştirme türü.
- `label_variant`: baskı etiketi varyantı.
- `label_text`: CorelDRAW/baskı etiketi üzerine gelecek metin.
- `laser_text`: lazer kesim/kazıma için kullanılacak metin.
- `quantity`: adet.
- `material_type`: lazer malzemesi.
- `material_thickness_mm`: malzeme kalınlığı.
- `extra_chocolate_qty`: ekstra çikolata adedi.
- `extra_madlen_qty`: ekstra madlen adedi.
- `production_note`: üretim ekibine not.
- `needs_review`: kontrol gerekiyorsa işaretleme alanı.
- `status`: sipariş durumu.

## Geçerli Değerler

`process_type`:

```text
PRINT
LASER_ENGRAVE
LASER_CUT
BOTH
NONE
```

`personalization_type`:

```text
LABEL
NAME
LABEL_AND_NAME
NO_PERSONALIZATION
```

`label_variant`:

```text
GOLD
SILVER
WHITE
RED
CUSTOM
NONE
```

`status`:

```text
NEW
READY
NEEDS_REVIEW
COMPLETED
CANCELLED
```

Kolon adları normalize edilir. Örneğin `Buyer Name`, `buyer-name` veya ` buyer name ` başlığı `buyer_name` olarak okunur.

## Satır Doğrulama Kuralları

PRINT için zorunlu alanlar:

```text
order_no
buyer_name
product_name
model_no
template_no
process_type
personalization_type
label_variant
quantity
```

`label_text`, `personalization_type` değeri `NO_PERSONALIZATION` değilse PRINT için zorunludur.

LASER_ENGRAVE için zorunlu alanlar:

```text
order_no
buyer_name
product_name
model_no
process_type
laser_text
quantity
```

LASER_ENGRAVE için `material_type` ve `material_thickness_mm` önerilir, ancak MVP'de satırı bloke etmez.

LASER_CUT için zorunlu alanlar:

```text
order_no
buyer_name
product_name
model_no
process_type
laser_text
quantity
material_type
material_thickness_mm
```

BOTH için:

- PRINT ve lazer hazırlık akışları birlikte çalışır.
- `personalization_type` değeri `LABEL_AND_NAME` ise hem `label_text` hem `laser_text` zorunludur.
- `personalization_type` değeri `LABEL` ise `label_text` zorunludur.
- `personalization_type` değeri `NAME` ise `laser_text` zorunludur.
- `personalization_type` değeri `NO_PERSONALIZATION` ise kişiselleştirme metni zorunlu değildir.

NONE için:

- Satır raporlara dahil edilir.
- Baskı veya lazer dosyası üretilmez.

## Baskı Şablonları

Baskı şablonları şu klasöre konur:

```text
templates/print/
```

Bu klasör **kaynak baskı şablonları** içindir. Yani üretimden önce kullanılan `.cdr`, `.ai`, `.pdf` ve `.svg` dosyaları burada saklanır. Bu dosyalar oluşturulmuş etiket çıktısı değildir.

Masaüstü uygulamasında:

- Normal kullanıcı akışında `Baskı Şablonlarını Gör` bölümü kullanılır; kaynak şablonlar uygulama içinde listelenir.
- `Baskı Şablonları Klasörünü Aç` düğmesi yalnızca teknik/ikincil seçenektir ve `templates/print/` klasörünü açar.
- `Şablon / CDR Yükle` ile yüklenen `.cdr`, `.ai`, `.pdf` ve `.svg` dosyaları `templates/print/` içine kaydedilir.
- Bu yükleme işlemi `output` klasörüne üretim çıktısı göndermez.

Program içinde baskı şablonu seçildiğinde şu bilgiler düzenlenebilir:

- Model No
- Şablon No
- Varyant
- Aktif/Pasif durumu
- Notlar
- Bağlı Label Designer JSON tasarımı

AI/CDR kaynak dosyalarının kendisi uygulama tarafından otomatik değiştirilmez. Uygulama yalnızca metadata bilgisini `templates/print/.template_metadata.json` dosyasına yazar ve gerekirse bağlı etiket tasarımı JSON dosyası oluşturur.

Şablon dosyası `model_no`, `template_no` ve `label_variant` ile eşleşmelidir.

Örnek:

```text
templates/print/02_gold_cyzella.ai
templates/print/02_gold_cyzella.cdr
templates/print/02_silver_cyzella.svg
templates/print/model_02_template_a_gold.pdf
```

Model klasörü kullanmak da mümkündür:

```text
templates/print/01/01_etiket_a_gold.cdr
```

Desteklenen baskı şablonu uzantıları:

```text
.cdr
.ai
.pdf
.svg
```

Birden fazla dosya aynı model, şablon ve varyantla eşleşirse sipariş üretime alınmaz ve `errors_report.csv` içinde `NEEDS_REVIEW` olarak işaretlenir.

Şablon eşleşmeleri ayrıca şu rapora yazılır:

```text
output/YYYY-MM-DD/print/template_matching_report.csv
```

Bu rapor her PRINT/BOTH satırı için `OK`, `MISSING` veya `NEEDS_REVIEW` durumunu gösterir.

CorelDRAW şablonlarında ileride kullanılacak önerilen yer tutucular:

```text
{{LABEL_TEXT}}
{{BUYER_NAME}}
{{ORDER_NO}}
{{DATE}}
```

## PRINT Çıktıları

PRINT ve BOTH siparişleri için çıktı yapısı:

```text
output/YYYY-MM-DD/print/model_{model_no}/
```

Bu alan **Etiket Çıktıları** içindir. Yani sistem çalıştıktan sonra oluşan PDF/PNG, rulo batch PDF, `print_data.csv` ve etiket render raporları burada bulunur.

Masaüstü uygulamasında:

- Normal kullanıcı akışında `Etiket Çıktılarını Gör` bölümü kullanılır; PDF/PNG/rulo batch çıktıları uygulama içinde listelenir.
- PNG önizlemeler uygulama içinde gösterilir.
- PDF dosyaları uygulama içinde dosya kartı olarak gösterilir; gerekirse kullanıcı açıkça harici açma/klasörde gösterme seçeneğini kullanabilir.
- `Etiket Çıktıları Klasörünü Aç` düğmesi yalnızca teknik/ikincil seçenektir.
- `Raporlar` bölümü CSV/TXT raporları uygulama içinde gösterir; `Raporlar Klasörünü Aç` yalnızca teknik/ikincil seçenektir.

Kısa ayrım:

```text
Baskı Şablonları = templates/print/ içindeki kaynak CDR/AI/PDF/SVG dosyaları
Etiket Çıktıları = output/YYYY-MM-DD/print/ içindeki oluşturulmuş PDF/PNG dosyaları
Raporlar = output/YYYY-MM-DD/reports/ içindeki sistem raporları
```

Her model klasöründe:

```text
print_data.csv
order_{order_no}_{label_text}/job_info.txt
```

PRINT kök klasöründe:

```text
template_matching_report.csv
```

`print_data.csv` alanları:

```text
order_no
buyer_name
product_name
model_no
template_no
personalization_type
label_variant
label_text
quantity
template_file
production_note
```

## Cyzella Label Designer MVP

Cyzella Label Designer, basit etiket işleri için CorelDRAW bağımlılığını azaltmak üzere eklenen güvenli iç etiket render katmanıdır.

Bu fazda sistem yalnızca PDF/PNG üretir:

- CorelDRAW otomatik açılmaz.
- Yazıcı otomatik çalışmaz.
- Direkt yazdırma yoktur.
- Mevcut `print_data.csv` hazırlık akışı kaldırılmaz.

Varsayılan ayar güvenli şekilde kapalıdır:

```yaml
print:
  mode: "data_only"
  allow_direct_print: false
  require_print_confirmation: true
  default_printer: ""
```

Etiket render modunu kullanmak için `config/settings.yaml` içinde yalnızca şu değer değiştirilir:

```yaml
print:
  mode: "label_designer"
```

JSON etiket şablonları şu klasörde durur:

```text
templates/designs/
```

Örnek şablon:

```text
templates/designs/01_a_gold.json
```

Şablonlar `model_no`, `template_no` ve `label_variant` alanlarıyla eşleştirilir. Excel içindeki `label_text`, etiket üzerinde basılacak ana metindir. `buyer_name` yalnızca sipariş takibi içindir.

Desteklenen placeholder değerleri:

```text
{{LABEL_TEXT}}
{{BUYER_NAME}}
{{ORDER_NO}}
{{DATE}}
```

Label Designer çıktıları:

```text
output/YYYY-MM-DD/print/model_{model_no}/rendered/order_{order_no}.pdf
output/YYYY-MM-DD/print/model_{model_no}/rendered/order_{order_no}.png
output/YYYY-MM-DD/print/model_{model_no}/rendered/label_render_report.csv
```

Masaüstü uygulamasında `Etiket PDF Oluştur` düğmesi bu güvenli render işlemini çalıştırır. `print.mode` değeri `data_only` ise uygulama kullanıcıya etiket tasarım modunun kapalı olduğunu bildirir.

## Rulo Etiket Varsayılan Ayarları

Cyzella üretim akışında ana etiket baskı modu **rulo etikettir**. Sistem etiketleri A4 sayfaya dizmeyi ana yöntem olarak kullanmaz. Rulo etiket akışında her PDF sayfası tek bir etiket ölçüsündedir.

Varsayılan rulo etiket ayarları `config/settings.yaml` içinde tutulur:

```yaml
label_defaults:
  media_type: "ROLL"
  label_width_mm: 50
  label_height_mm: 30
  roll_gap_mm: 3
  printer_dpi: 300
  default_copies: 1
  horizontal_offset_mm: 0
  vertical_offset_mm: 0
  scale_percent: 100
  background_enabled: true
  show_cut_boundary: false
  safe_margin_mm: 1.5
```

Masaüstü uygulamasında `Etiket` adımında **Rulo Etiket Varsayılanları** bölümü bulunur. Buradan etiket genişliği, yüksekliği, DPI, kaydırma, ölçek ve güvenli iç boşluk ayarları kaydedilebilir.

Öncelik sırası:

1. Şablon içinde özel ölçü varsa o kullanılır.
2. Şablonda ölçü yoksa `label_defaults` kullanılır.
3. İkisi de yoksa render güvenli şekilde durur ve hata raporlanır.

Rulo etiket çıktıları:

```text
output/YYYY-MM-DD/print/model_{model_no}/rendered/order_{order_no}.pdf
output/YYYY-MM-DD/print/model_{model_no}/rendered/order_{order_no}.png
output/YYYY-MM-DD/print/model_{model_no}/rendered/roll_batch_{model_no}_{template_no}_{label_variant}.pdf
```

`roll_batch` PDF içinde her sayfa bir rulo etiket ölçüsündedir. Yazıcıya gönderilmeden önce PDF mutlaka kontrol edilmelidir.

Kalibrasyon için masaüstü uygulamasında:

```text
Etiket > Rulo Etiket Varsayılanları > Kalibrasyon PDF Oluştur
```

Bu PDF sınır çizgisi, orta çizgiler ve 10 mm referans cetveli içerir. Yazdırırken ölçek genelde `%100` olmalıdır.

Güvenlik:

- Direct print bu fazda kapalıdır.
- Yazıcı otomatik çalışmaz.
- CorelDRAW otomatik açılmaz.
- Önce PDF kontrol edilir, sonra kullanıcı manuel yazdırır.

## Etiket Şablonu Düzenleme

Masaüstü uygulamasındaki `Etiket Şablonu Düzenle` ekranı, JSON dosyasını elle açmadan temel etiket tasarımını değiştirmek içindir.

## Etiket Model Kütüphanesi

Etiket tarafında ana kullanım artık klasör/dosya adı değil, program içindeki **Etiket Model Kütüphanesi**dir.

Etiket modelleri şu dosyalarda saklanır:

```text
templates/designs/{model_no}_{template_no}_{label_variant}.json
```

Model JSON içinde yeni ana yapı `fields` alanıdır. Eski `elements` yapısı geriye dönük uyumluluk için desteklenir.

Örnek alan:

```json
{
  "field_name": "İsim",
  "placeholder": "{{LABEL_TEXT}}",
  "excel_column": "label_text",
  "x_mm": 10,
  "y_mm": 12,
  "width_mm": 30,
  "height_mm": 6,
  "font_family": "Segoe UI",
  "font_size": 14,
  "color": "#111111",
  "align": "center",
  "vertical_align": "middle",
  "bold": false,
  "italic": false
}
```

Desteklenen Excel alanları:

```text
label_text
date_text
note_text
custom_text_1
custom_text_2
custom_text_3
quantity
```

Türkçe başlık karşılıkları:

```text
Etiket Yazısı
Tarih Yazısı
Not Yazısı
Özel Metin 1
Özel Metin 2
Özel Metin 3
Adet
```

Model seçimi dosya adıyla yapılmaz. Uygulamadaki `Etiket Model Kütüphanesi` bölümünde model kartları önizleme görseliyle gösterilir. Dosya adı yalnızca teknik detaydır.

Önizleme görseli:

- `preview_image` varsa kartta gösterilir.
- Yoksa `Önizleme yok` uyarısı görünür.
- `Önizleme Görseli Seç` ile görsel `assets/label_backgrounds/` içine kopyalanır ve model JSON güncellenir.
- AI/CDR dosyaları program içinde doğrudan önizlenemez. Bu dosyalar kaynak tasarım olarak saklanır.
- Program içinde düzenleme ve yazı yerleşimi için aynı tasarımın PNG/JPG/PDF görseli önizleme olarak bağlanmalıdır.

CDR/AI kaynak dosyaları uygulama tarafından otomatik değiştirilmez; yalnızca model metadata ve JSON üretim ayarları güncellenir.

Bu ekranda şunlar ayarlanabilir:

- Arka plan görseli seçme, kaldırma ve açma/kapatma
- Etiket yazısının X/Y konumu, genişliği ve yüksekliği
- Font ailesi, font boyutu, renk, bold/italic
- Yatay hizalama: left, center, right
- Dikey hizalama: top, middle, bottom
- Üst altın çizgiyi gösterme/gizleme
- Üst çizgi konumu, genişliği, kalınlığı ve rengi
- Kenarlığı gösterme/gizleme
- Kenarlık rengi ve kalınlığı

Kaydetme davranışı güvenlidir:

- Şablon şu formatta kaydedilir:

```text
templates/designs/{model_no}_{template_no}_{label_variant}.json
```

- Var olan şablonun üzerine yazmadan önce kullanıcıdan onay istenir.
- Üzerine yazma öncesinde otomatik backup alınır:

```text
templates/designs/backups/
```

Validasyon kuralları:

- Yazı kutusu etiket ölçüsünün içinde kalmalıdır.
- Font boyutu 0'dan büyük olmalıdır.
- Dekoratif çizgi etiket sınırının içinde kalmalıdır.
- Arka plan görseli proje içindeki `assets` klasörü içinde olmalıdır.

Bu özellik yalnızca PDF/PNG hazırlama içindir:

- Yazıcı otomatik çalışmaz.
- CorelDRAW otomatik açılmaz.
- Şablon değişikliğinden sonra önce sample PDF/PNG kontrol edilmelidir.

## Şablon Paketi Yükleme

Label Designer şablonları ve görselleri masaüstü uygulamasından güvenli ZIP paketi olarak yüklenebilir.

Normal kullanım:

1. Masaüstü uygulamasını açın.
2. `Şablon Paketi Yükle` butonuna basın.
3. `.zip` dosyasını seçin.
4. Program izin verilen şablonları ve görselleri doğru klasörlere kopyalar.
5. ZIP içinde Excel varsa `input` klasörüne eklenir.
6. Excel dosyasını seçip dry-run yapın.
7. Etiket PDF oluşturmak için `print.mode` değeri `label_designer` olmalıdır.

ZIP içinde izin verilen klasörler:

```text
templates/designs/
assets/label_backgrounds/
input/
```

İzin verilen dosya tipleri:

```text
templates/designs/*.json
assets/label_backgrounds/*.png
assets/label_backgrounds/*.jpg
assets/label_backgrounds/*.jpeg
assets/label_backgrounds/*.webp
input/*.xlsx
```

İzin verilen kök yardımcı dosyalar:

```text
README_TEST_PACK.txt
preview_contact_sheet.png
settings_label_designer_snippet.yaml
```

Güvenlik kuralları:

- ZIP içindeki `.exe`, `.bat`, `.cmd`, `.ps1`, `.py` gibi dosyalar çalıştırılmaz ve kopyalanmaz.
- `../` veya mutlak yol içeren güvensiz dosyalar reddedilir.
- Dosyalar proje klasörü dışına çıkarılamaz.
- Var olan dosyanın üzerine yazmadan önce kullanıcıdan onay istenir.
- CorelDRAW açılmaz, yazıcı çalışmaz, RDWorks açılmaz, lazer başlamaz.

Import raporu:

```text
output/YYYY-MM-DD/reports/template_import_report.csv
```

## LASER Çıktıları

Lazer işleri tek tek dosya olarak değil, plaka bazlı SVG yerleşimleri olarak üretilir.

İşlenen süreç tipleri:

```text
LASER_ENGRAVE
LASER_CUT
BOTH
```

Lazer kişiselleştirme metni:

```text
laser_text
```

LASER_CUT için kritik bağlı el yazısı kuralı:

- Kesilecek isimler bağlı el yazısı / script font ile hazırlanmalıdır.
- Blok font veya ayrı harfler kullanılamaz; aksi halde harfler tek tek düşer.
- Varsayılan font yolu:

```text
assets/fonts/connected_script.ttf
```

Bu font yoksa veya bağlı cursive vector/path çıktısı güvenli doğrulanamıyorsa LASER_CUT siparişi durdurulur ve `errors_report.csv` içine yazılır. Üretim doğruluğu için sistem yanlış kesim SVG'si üretmez.

Font Türkçe karakterleri desteklemelidir:

```text
ç Ç ğ Ğ ı I İ ö Ö ş Ş ü Ü
```

Lazer işleri şu alanlara göre gruplanır:

```text
model_no
material_type
material_thickness_mm
process_type
```

Çıktı yapısı:

```text
output/YYYY-MM-DD/laser/model_{model_no}/plate_001.svg
output/YYYY-MM-DD/laser/model_{model_no}/plate_002.svg
```

Her plaka için rapor:

```text
plate_001_layout_report.csv
```

Her plaka için iş bilgisi:

```text
plate_001_job_info.txt
```

Her model için genel rapor:

```text
model_level_layout_report.csv
```

Lazer raporlarında connected font kontrol alanları da bulunur:

```text
font_name
font_size
connected_status
disconnected_parts_count
warning
```

`connected_status` değerleri:

```text
OK_CONNECTED
WARNING_HAS_SEPARATE_DOTS_OR_ACCENTS
ERROR_LETTERS_NOT_CONNECTED
ERROR_FONT_MISSING
ERROR_UNSUPPORTED_TURKISH_CHARACTER
```

SVG içinde şu gruplar/layer yapıları bulunur:

```text
PLATE_BOUNDARY_GUIDE_DO_NOT_CUT
ENGRAVE_TEXT
CUT_LINES
ORDER_GUIDE_DO_NOT_CUT
```

Plaka sınırı ve sipariş numarası rehberi kesim dışı guide katmanlarıdır. RDWorks açılmaz, lazer başlatılmaz; SVG dosyaları manuel kontrol için hazırlanır.

Üretimden önce kullanıcı şunları kontrol etmelidir:

- SVG plaka ölçüsü doğru mu
- Tüm isimler plaka sınırının içinde mi
- `ORDER_GUIDE_DO_NOT_CUT` ve `PLATE_BOUNDARY_GUIDE_DO_NOT_CUT` katmanları kesim dışı mı
- LASER_CUT için `connected_status` güvenli mi
- Raporda `warning` alanı boş mu veya kabul edilebilir mi

## Raporlar

Raporlar şu klasöre yazılır:

```text
output/YYYY-MM-DD/reports/
```

Dosyalar:

```text
summary_report.csv
errors_report.csv
smart_warnings_report.csv
needs_review_report.csv
production_summary_human_readable.txt
material_efficiency_report.csv
```

Örnek hata mesajları:

```text
Missing label_text for PRINT job
Missing laser_text for LASER_CUT job
Invalid personalization_type: TEXT
Invalid status: HOLD
Missing print template for model_no 07, template_no A, label_variant GOLD
NEEDS_REVIEW: multiple print templates match model_no 07, template_no A, label_variant GOLD
```

## CorelDRAW Faz 2

MVP yalnızca temiz veri ve klasör hazırlar. CorelDRAW otomasyonu daha sonra ayrı bir fazda yapılmalıdır.

Faz 2 seçenekleri:

- CorelDRAW VBA makrosu
- CorelDRAW içinde çalışan özel macro
- Windows COM otomasyonu

Faz 2'de bile önce dosya üretimi ve kullanıcı onayı korunmalıdır. Otomatik yazdırma ayrı bir güvenlik onayı olmadan eklenmemelidir.
## Windows Kolay Çalıştırma Dosyaları

Teknik olmayan kullanım için proje kökünde `.bat` dosyaları hazırdır.

Önce kurulum:

```cmd
setup.bat
```

Demo Excel ile güvenli kontrol:

```cmd
run_demo_dry.bat
```

Güvenli test Excel'i ile kontrol:

```cmd
run_test_dry.bat
```

Gerçek `input\siparisler.xlsx` dosyasını yalnızca kontrol etmek için:

```cmd
run_real_dry.bat
```

Gerçek `input\siparisler.xlsx` ile dosya ve rapor üretmek için:

```cmd
run_real.bat
```

`run_real.bat` gerçek üretim modudur; yine de CorelDRAW'u açmaz, yazıcıyı çalıştırmaz, RDWorks'ü açmaz ve lazeri başlatmaz. Sadece üretim klasörleri, CSV raporları ve güvenli hazırlık dosyaları oluşturur.

## siparisler.xlsx 0 Sipariş Gösterirse

`input\siparisler.xlsx` temiz üretim şemasına sahip boş bir şablon olabilir. Bu durumda program hatalı değildir.

Yapılacak işlem:

1. `input\cyzella_production_template.xlsx` dosyasını açın.
2. Gerçek sipariş satırlarını temiz üretim şemasına göre doldurun.
3. Dosyayı `input\siparisler.xlsx` olarak kaydedin.
4. Önce `run_real_dry.bat` ile kontrol edin.
5. Hata yoksa `run_real.bat` ile dosya ve rapor üretin.

Ana üretim formatı temiz üretim Excel şemasıdır. Eski Cyzella Excel dosyaları yalnızca referans veya dönüştürme kaynağı olarak kullanılmalıdır; doğrudan güvenli üretim kaynağı değildir.

## LASER_CUT Font Gereksinimi

LASER_CUT işleri için şu dosya gereklidir:

```text
assets/fonts/connected_script.ttf
```

Bu font birleşik el yazısı / connected script font olmalı ve Türkçe karakterleri desteklemelidir. Font yoksa sistem LASER_CUT kesim dosyası üretmez; siparişi güvenlik için `errors_report.csv` içine yazar.

Fontla ilgili kısa talimat ayrıca şu dosyadadır:

```text
assets/fonts/README_FONT.txt
```

## Windows Masaüstü Uygulaması ile Kullanım

Masaüstü uygulamasının adı:

```text
Cyzella Production Studio
```

Bu uygulama mevcut güvenli CLI üretim motorunun üstünde çalışan basit bir arayüzdür. Üretim kurallarını yeniden yazmaz ve güvenlik kontrollerini atlamaz.

Normal kullanım:

1. Masaüstündeki “Cyzella Production Studio” kısayoluna çift tıklayın.
2. Uygulama açılır.
3. Excel seçin.
4. Dry-run kontrolü yapın.
5. Hataları düzeltin.
6. Temizse üretim dosyalarını oluşturun.

Kısayol ilk açılışta gerekli kurulumu otomatik hazırlar:

- `.venv` yoksa oluşturur.
- `requirements.txt` paketlerini kurar.
- PySide6 kontrolü yapar.
- Sonra masaüstü uygulamasını açar.

Masaüstü kısayolu oluşturmak için bir kere şu dosya çalıştırılabilir:

```cmd
create_desktop_shortcut.bat
```

Kısayolun hedefi:

```text
C:\Users\Pc\Documents\New project\production-bot\start_cyzella.bat
```

Teknik/manual dosyalar hâlâ vardır, ancak normal kullanıcı akışı değildir:

```cmd
setup.bat
```

```cmd
run_desktop.bat
```

Kullanım sırası:

1. Uygulama açılınca “Excel Seç” ile üretim Excel dosyasını seçin.
2. Önce “Dry-run Kontrolü Yap” düğmesine basın.
3. Hatalar ve kontrol gereken satırlar varsa Excel içinde düzeltin.
4. Raporları uygulama içindeki sekmelerden kontrol edin.
5. Her şey temizse onay kutusunu işaretleyin.
6. “Üretim Dosyalarını Oluştur” düğmesine basın.
7. Print, Laser ve Reports klasörlerini uygulama içinden açın.

Masaüstü uygulaması da aynı güvenlik kurallarına uyar:

```text
CorelDRAW otomatik açılmaz.
Yazıcı otomatik çalışmaz.
RDWorks otomatik açılmaz.
Lazer otomatik başlamaz.
```

LASER_CUT için şu font gereklidir:

```text
assets/fonts/connected_script.ttf
```

Font yoksa LASER_CUT işleri güvenlik için bloklanır ve hata raporuna yazılır. LASER_ENGRAVE ve PRINT hazırlıkları güvenli şekilde devam edebilir.

## Yeni HTML Tabanlı Cyzella Arayüzü

Cyzella Production Studio'nun ana masaüstü arayüzü artık HTML/CSS/JS tabanlı yerel bir arayüzdür. Uygulama yine Python ve PySide6 ile açılır, ancak görsel katman modern HTML/CSS olarak çalışır.

Normal kullanıcı akışı değişmez:

1. Masaüstündeki `Cyzella Production Studio` kısayoluna çift tıklayın.
2. Uygulama açılır.
3. Excel dosyasını seçin.
4. `Kontrolü Tekrar Çalıştır` ile dry-run yapın.
5. Hatalar varsa Excel veya şablonları düzeltin.
6. Temizse etiket PDF/PNG ve lazer hazırlık dosyalarını oluşturun.
7. Çıktı ve rapor klasörlerini uygulama içinden açın.

Yeni arayüz dosyaları:

```text
src/webui/index.html
src/webui/styles.css
src/webui/app.js
src/webui_backend/
```

Eski PySide widget arayüzü tamamen silinmemiştir; teknik yedek olarak kalır:

```cmd
run_desktop.bat
```

Yeni HTML arayüzü doğrudan açmak için:

```cmd
run_web_desktop.bat
```

Normal kullanıcı yine sadece masaüstü kısayolunu kullanmalıdır. `start_cyzella.bat` yeni HTML arayüzünü açar.

Arayüz bölümleri:

- Genel Bakış
- Excel
- Kontrol
- Etiket
- Lazer
- Raporlar
- Ayarlar
- Nasıl Kullanırım

Rulo etiket iş akışı:

- Ana etiket modu rulo etikettir.
- Her PDF sayfası tek bir rulo etiket ölçüsündedir.
- A4 grid/sheet baskı ana akış değildir.
- `Etiket PDF Oluştur` toplu Excel etiketlerini hazırlar.
- `Manuel Etiket Oluştur` Excel olmadan tekil/çoklu rulo etiket PDF/PNG hazırlar.
- `Kalibrasyon PDF Oluştur` ölçü kontrolü için güvenli PDF üretir.

Güvenlik kuralları aynı kalır:

```text
CorelDRAW otomatik açılmaz.
Yazıcı otomatik çalışmaz.
RDWorks otomatik açılmaz.
Lazer otomatik başlamaz.
LASER_CUT font veya bağlı vektör güvenliği yoksa bloke edilir.
```

Doğrudan yazdırma bu fazda yoktur. Üretilen PDF/PNG/SVG dosyaları kullanıcı tarafından manuel kontrol edilmelidir.

## Güncel Ana Kullanım

Normal günlük kullanım için terminal komutu gerekmez.

1. Masaüstündeki `Cyzella Production Studio` kısayoluna çift tıklayın.
2. Ana HTML/CSS arayüz açılır.
3. Excel dosyasını seçin veya varsayılan `input/siparisler.xlsx` dosyasını kullanın.
4. `Kontrolü Tekrar Çalıştır` ile dry-run yapın.
5. Ekranda görünen Türkçe hata yönlendirmelerini düzeltin.
6. Bloke durum temizlendikten sonra etiket veya lazer çıktısı oluşturun.
7. PDF/PNG/SVG/CSV dosyalarını uygulamadaki klasör düğmelerinden açıp manuel kontrol edin.

Ana arayüz:

```text
src/webui/index.html
src/webui/styles.css
src/webui/app.js
```

Ana masaüstü kabuğu:

```text
src/desktop/web_main_window.py
```

Eski PySide widget arayüzü yalnızca teknik yedek/fallback olarak durur. Ana kullanıcı akışı HTML tabanlı arayüzdür.

## Etiket Studio Hızlı Kullanım

Normal üretim akışı terminal gerektirmez:

1. `Cyzella Production Studio` kısayolunu açın.
2. `Etiket Modelleri` ekranından yeni model ekleyin veya mevcut modeli seçin.
3. CDR/AI dosyası yüklüyorsanız bunun kaynak tasarım olduğunu unutmayın; programda görmek için PNG/JPG/WebP/SVG/PDF önizleme dosyası bağlayın.
4. JPG/PNG/WebP tasarım yüklerseniz bu görsel arka plan olarak kullanılabilir.
5. Modelde düzenlenebilir yazı yoksa `İsim Alanı Ekle`, `Tarih Alanı Ekle` veya `Not Alanı Ekle` ile yeni yazı katmanı oluşturun.
6. Etiket üzerindeki yazıya tıklayın veya çift tıklayın, metni değiştirin.
7. Yazıyı sürükleyerek taşıyın, köşesinden büyütüp küçültün.
8. Sağ panelden font, boyut, renk, hizalama, bold/italic ayarlarını değiştirin.
9. `Önizleme Oluştur` ile gerçek Label Designer render motorundan PNG önizleme alın.
10. `PDF/PNG Oluştur` ile çıktı üretin.
11. `Yazdırma Sırasına Ekle` ile işi sıraya alın.
12. Yazdırma otomatik başlamaz; PDF’i kontrol edip manuel yazdırın.

JPG/PNG/WebP içindeki eski yazı doğrudan değiştirilemez; o yazı görselin pikselidir. Bu durumda üzerine yeni düzenlenebilir yazı alanı eklenir. Gerekirse eski yazının üstü düz renkli bir maske ile kapatılıp yeni yazı katmanı yerleştirilebilir.

CDR/AI kaynak dosyalar uygulama tarafından değiştirilmez. Native AI/CDR edit sadece `Kaynak Dosyadan Gerçek Yazı Tarama` adlı izole PoC panelindedir, yalnızca kopya dosya üzerinde denenir ve ortam uygun değilse `ENGINE_MISSING` veya `PARTIAL` olarak raporlanır.

Güvenlik notu: Uygulama açılışta veya dry-run sırasında CorelDRAW, yazıcı, RDWorks ya da lazer başlatmaz. Direct print bu sürümde kapalıdır.
