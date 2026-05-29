# CYZELLA PRODUCTION STUDIO — PROJE VİZYONU VE KABUL DOSYASI

Bu dosya, Cyzella Production Studio projesinin gerçek hedefini, konuşulan iş akışını, güvenlik kurallarını, eksik kalan alanları ve Codex’in bundan sonra projeyi nasıl toparlaması gerektiğini anlatır.

Bu dosya proje kök klasörüne eklenmelidir:

```text
C:\Users\Pc\Documents\New project\production-bot\CYZELLA_PROJECT_VISION.md
```

Codex bu dosyayı proje içi ana referans kabul etmeli, sonraki geliştirmelerde bu dosyadaki hedeflerden sapmamalıdır.

---

## 1. Projenin Asıl Amacı

Cyzella Production Studio, kişiye özel ürün üreten bir işletme için yerel Windows üzerinde çalışan güvenli üretim operasyon sistemidir.

Bu proje basit bir bot değildir. Amaç; Excel’den gelen siparişleri okuyup etiket, baskı ve lazer üretim dosyalarını hazırlayan, hataları kullanıcıya anlaşılır şekilde gösteren, CorelDRAW ve RDWorks yükünü azaltan, terminal gerektirmeyen, modern arayüzlü bir masaüstü uygulaması oluşturmaktır.

Kullanıcı teknik değildir. Terminal kullanmak istemez. Kod bilmek istemez. Her şeyi masaüstü uygulamasından yapmak ister.

Nihai hedef:

```text
Masaüstü kısayoluna çift tıkla
↓
Modern Cyzella arayüzü açılsın
↓
Excel seç
↓
Kontrol yap
↓
Hataları Türkçe gör
↓
Etiket PDF/PNG oluştur
↓
Gerekirse manuel etiket oluştur
↓
Kalibrasyon PDF al
↓
Lazer dosyalarını hazırla
↓
Raporları incele
↓
Çıktı klasörlerini aç
↓
Hiçbir makine otomatik çalışmasın
```

---

## 2. İşletmenin Gerçek Üretim Akışı

Kullanıcı kişiselleştirilmiş ürün satıyor.

Müşteriler sipariş verirken isim/yazı bilgisi giriyor. Bu bilgiler iki ana üretim alanında kullanılıyor:

1. Etiket / çikolata / ürün etiketi baskısı
2. Lazer kazıma veya lazer kesim isim işleri

Mevcut manuel iş akışı:

```text
Sipariş/Excel
↓
Müşteri isimlerini alma
↓
CorelDRAW’da etiket hazırlama
↓
Yazıcıdan çıktı alma
↓
Lazer işleri için isimleri hazırlama
↓
RDWorks/lazer yazılımına manuel aktarma
```

Cyzella Production Studio bu akışı sistemleştirmelidir.

---

## 3. Temel Güvenlik İlkesi

En önemli kural:

```text
Sistem üretim dosyası hazırlar, makine çalıştırmaz.
```

Şunlar ASLA otomatik yapılmamalıdır:

- CorelDRAW otomatik açılmayacak.
- Yazıcı otomatik çalışmayacak.
- RDWorks otomatik açılmayacak.
- Lazer otomatik başlamayacak.
- Direct print varsayılan olarak kapalı kalacak.
- Kullanıcı onayı olmadan Excel dosyası değiştirilmeyecek.
- Kullanıcı onayı olmadan şablon overwrite edilmeyecek.
- Hatalı veya belirsiz sipariş sessizce üretime alınmayacak.
- LASER_CUT için connected script/font/path güvenliği yoksa kesim dosyası üretilmeyecek.
- Validasyon bypass edilmeyecek.
- Hata raporları gizlenmeyecek.

Sistem, üretimden önce hata ve riskleri gösterecek; kullanıcı manuel kontrol yapacak.

---

## 4. Excel Sistemi

Mevcut eski Excel, ana üretim formatı değildir. Eski Excel sadece referans veya dönüştürme kaynağı olabilir.

Ana üretim dosyası temiz üretim Excel şemasıdır.

Gerekli kolonlar:

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

Kritik ayrım:

```text
buyer_name = müşteri/alıcı takibi
label_text = etikete basılacak metin
laser_text = lazerde yazılacak veya kesilecek metin
```

buyer_name etikete basılacak metin değildir. Etikete basılacak metin label_text alanıdır. Lazerde kullanılacak metin laser_text alanıdır.

---

## 5. İşlem Tipleri

Geçerli işlem tipleri:

```text
PRINT
LASER_ENGRAVE
LASER_CUT
BOTH
NONE
```

Anlamları:

```text
PRINT = Etiket/baskı işi
LASER_ENGRAVE = Lazer kazıma/yüzeye yazma
LASER_CUT = Pleksiden isim kesme
BOTH = Hem etiket hem lazer işi
NONE = Üretim dosyası gerektirmeyen satır
```

Validasyon bu alanlara göre yapılmalıdır.

---

## 6. Etiket Sistemi — Ana Hedef

Etiket tarafında amaç CorelDRAW bağımlılığını azaltmaktır.

CorelDRAW’un tamamını kopyalamaya çalışmayacağız. Onun yerine, üretim için gereken kadar çalışan bir dahili etiket motoru kullanılacaktır:

```text
Cyzella Label Designer
```

Label Designer’ın görevi:

```text
Şablonu bul
↓
label_text değerini şablona yerleştir
↓
PDF üret
↓
PNG önizleme üret
↓
Rulo etiket batch PDF üret
```

Şablonlar JSON olarak tutulur:

```text
templates/designs/{model_no}_{template_no}_{label_variant}.json
```

Excel’de şu varsa:

```text
model_no: 01
template_no: A
label_variant: GOLD
label_text: Ayşe & Mehmet
```

Sistem doğru şablonu bulmalı ve etikete `Ayşe & Mehmet` yazmalıdır.

---

## 7. Rulo Etiket Mantığı

Kullanıcı rulo etiket kullanıyor. Bu yüzden A4 sticker sayfası/grid ana yöntem değildir.

Doğru mantık:

```text
Her PDF sayfası = 1 rulo etiket
```

Örnek:

```text
Etiket ölçüsü: 50 x 30 mm
PDF sayfa 1 = Ayşe & Mehmet
PDF sayfa 2 = Elif & Burak
PDF sayfa 3 = Zeynep & Ali
```

Toplu çıktı:

```text
roll_batch_{model_no}_{template_no}_{label_variant}.pdf
```

Bu PDF içinde her sayfa tek bir rulo etiket ölçüsünde olmalıdır.

---

## 8. Rulo Etiket Varsayılan Ayarları

Her şablonda tekrar ölçü girmek gerekmemelidir.

Varsayılan ayarlar config dosyasında tutulmalıdır:

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
  show_order_number_on_label: false
```

Öncelik sırası:

1. Şablonda özel ölçü varsa onu kullan.
2. Şablonda ölçü yoksa `label_defaults` kullan.
3. İkisi de yoksa render işlemini bloke et ve hata ver.

Müşteri etiketinde sipariş numarası varsayılan olarak görünmemelidir.

```yaml
show_order_number_on_label: false
```

Sipariş numarası raporlarda ve dosya takibinde kalabilir, ama müşteri etiketinde görünmez.

---

## 9. Kalibrasyon PDF

Rulo yazıcıda ölçü kayması olabilir. Bu yüzden sistem kalibrasyon PDF üretmelidir:

```text
roll_label_calibration_{width}x{height}.pdf
```

İçerik:

- Etiket sınırı
- Orta çizgiler
- 10 mm referans cetveli
- “Ölçek %100 olmalıdır” uyarısı

Bu PDF yazdırılıp cetvelle kontrol edilmelidir. Direct print eklenmeden önce bu kalibrasyon şarttır.

---

## 10. Manuel Etiket Oluşturma

Sistem Excel olmadan da etiket oluşturabilmelidir.

Manuel etiket akışı:

```text
Şablon seç
↓
Yazı gir
↓
Adet gir
↓
Önizle
↓
PDF/PNG oluştur
```

Örnek:

```text
Şablon: 01 A GOLD
Yazı: Ayşe & Mehmet
Adet: 20
```

Çıktı klasörü:

```text
output/YYYY-MM-DD/print/manual/
```

Bu özellik günlük hızlı işler için çok önemlidir.

---

## 11. Etiket Şablon Yönetimi

Şablon paketi yükleme ana kullanım değildir. Şablon paketi sadece dışarıdan hazır paket geldiğinde yardımcı özellik olmalıdır.

Ana kullanım:

```text
Uygulama içinden şablon oluştur
↓
Şablonu kalıcı kaydet
↓
Excel’de aynı model_no/template_no/label_variant varsa sistem otomatik seçsin
```

Etiket Şablonları ekranında şu özellikler olmalıdır:

- Şablon listesi
- Yeni şablon oluştur
- Şablon düzenle
- Şablon kopyala
- Şablon sil/pasifleştir
- Önizleme
- Arka plan görseli seçme
- Yazı alanı konumu
- Font seçimi
- Font boyutu
- Renk
- Kalın/italik
- Hizalama
- Üst çizgi aç/kapat
- Çerçeve aç/kapat
- Kaydet
- Kaydetmeden önce backup

Backup klasörü:

```text
templates/designs/backups/
```

Şablon kullanıcıdan onay almadan overwrite edilmemelidir.

---

## 12. Lazer Sistemi

Lazer tarafında kullanıcı isimleri pleksi plaka üzerinde yan yana dizmek istiyor.

Amaç:

```text
Excel’den laser_text al
↓
Lazer işlerini model/malzeme/kalınlığa göre grupla
↓
İsimleri plaka üzerine yan yana diz
↓
Plaka dolunca yeni plaka aç
↓
SVG dosyası üret
↓
Kullanıcı dosyayı lazer programına manuel aktarır
```

Lazer çıktıları:

```text
output/YYYY-MM-DD/laser/model_{model_no}/plate_001.svg
output/YYYY-MM-DD/laser/model_{model_no}/plate_001_layout_report.csv
```

LASER_ENGRAVE daha esnektir.

LASER_CUT çok kritiktir:

- Harfler birleşik el yazısı olmalıdır.
- Blok font kullanılmamalıdır.
- Harfler ayrı ayrı düşmemelidir.
- Türkçe karakterler desteklenmelidir.

Gerekli font:

```text
assets/fonts/connected_script.ttf
```

Bu font yoksa veya connected vector güvenliği garanti değilse LASER_CUT çıktı üretmemelidir.

İleride yapılabilecekler:

- text-to-path
- weld/union
- dot/accent bridge
- PDF/DXF/EPS/AI-compatible export

Bunlar güvenli şekilde uygulanmadan aktif üretime alınmamalıdır.

---

## 13. Direct Print Konusu

Direkt yazdırma şu aşamada yapılmamalıdır.

Önce:

1. PDF üret.
2. Önizle.
3. Kalibrasyon PDF yazdır.
4. %100 ölçek kontrol et.
5. Test baskısı al.
6. Sonra kontrollü direct print fazı düşün.

Varsayılan:

```text
Yazıcı otomatik çalışmaz.
Direct print kapalıdır.
```

---

## 14. Masaüstü Uygulama Hedefi

Kullanıcı terminal kullanmak istemiyor.

Normal kullanım:

```text
Masaüstündeki Cyzella Production Studio kısayoluna çift tık
↓
Uygulama açılır
↓
Excel seçersin
↓
Kontrol yaparsın
↓
Hata varsa düzeltirsin
↓
Etiket/lazer dosyalarını oluşturursun
```

PySide native widget arayüzü birçok denemeye rağmen görsel olarak istenen seviyeye gelemedi.

Bu yüzden ana arayüz:

```text
HTML/CSS/JS tabanlı yerel arayüz
+
Python backend
+
QWebEngineView veya uygun desktop shell
```

olmalıdır.

Eski PySide arayüz fallback olarak kalabilir.

---

## 15. Arayüz Tasarım Hedefi

Tasarım hedefi:

- Apple tarzı
- Beyaz / açık gri
- Az renk
- Cyzella gold aksan
- Modern kartlar
- Sade
- Türkçe
- Gündüz / Gece modu
- Kesilmeyen yazılar
- Kullanımı kolay
- Fazla teknik olmayan raporlar

İstenmeyenler:

- Neon dashboard
- Çok renkli SaaS ekranı
- Eski Windows form görünümü
- Aşırı büyük butonlar
- İngilizce UI metinleri
- Ham HTML görünümü
- Kesilen yazılar
- Yatay taşma

---

## 16. Arayüz Ana Akışı

Ana menü:

```text
Genel Bakış
Excel
Kontrol
Etiket
Lazer
Raporlar
Ayarlar
Nasıl Kullanırım?
```

Ana üretim adımları:

```text
1. Excel
2. Kontrol
3. Etiket
4. Lazer
5. Raporlar
```

Durumlar:

```text
BEKLİYOR
AKTİF
TAMAMLANDI
KONTROL GEREKLİ
BLOKE
HAZIR
```

BLOKE durumunda:

- Üretim dosyası oluşturma engellenmeli.
- İlk 5 kritik hata gösterilmeli.
- Sonraki adım net yazılmalı.

---

## 17. Hata Metinleri

Backend İngilizce/teknik hata üretse bile ana UI Türkçe göstermelidir.

Örnekler:

```text
Missing label_text for PRINT job
→ Etiket yazısı eksik. Excel’de label_text kolonunu doldurun.
```

```text
Connected script font missing for LASER_CUT
→ Lazer kesim fontu eksik. assets/fonts/connected_script.ttf dosyasını ekleyin.
```

```text
Missing print template
→ Etiket şablonu bulunamadı. Model No, Şablon No ve Varyant bilgisini kontrol edin.
```

Teknik detaylar Günlük ekranında olabilir, ana ekranda uzun Windows path görünmemelidir.

---

## 18. Raporlar

Sistem rapor üretmelidir, ama kullanıcıya ham CSV gibi değil, anlaşılır özet göstermelidir.

Rapor tipleri:

- summary_report.csv
- errors_report.csv
- needs_review_report.csv
- smart_warnings_report.csv
- production_summary_human_readable.txt
- template_matching_report.csv
- label_render_report.csv
- material_efficiency_report.csv
- layout_report.csv
- template_import_report.csv

Ana UI’da:

```text
2 kritik hata var
6 satır kontrol gerekiyor
Etiket şablonu eksik
Lazer fontu eksik
```

gibi sade gösterilmelidir.

---

## 19. Kabul Kriterleri

Proje “hazır” sayılmadan önce şunlar çalışmalıdır:

1. Masaüstü kısayolundan uygulama açılır.
2. Modern arayüz görünür.
3. Excel seçilebilir.
4. Dry-run çalışır.
5. Hatalar Türkçe görünür.
6. BLOKE durumunda üretim engellenir.
7. Etiket PDF oluşturulur.
8. Manuel etiket oluşturulur.
9. Rulo etiket ayarları kaydedilir.
10. Kalibrasyon PDF oluşturulur.
11. Lazer SVG dosyaları görüntülenir.
12. Raporlar açılır.
13. Çıktı klasörleri açılır.
14. Gündüz/gece modu çalışır.
15. Hiç terminal gerekmez.
16. Hiçbir makine otomatik çalışmaz.
17. Testler geçer.

---

## 20. Codex İçin Çalışma Talimatı

Codex bu dosyayı ana ürün vizyonu olarak kabul etmelidir.

Bundan sonra Codex:

1. Bu dosyayı okumalı.
2. Mevcut projeyi incelemeli.
3. Kabul kriterlerine göre eksikleri çıkarmalı.
4. Kullanıcıdan onay beklemeden güvenli düzeltmeleri yapmalı.
5. Testleri çalıştırmalı.
6. Eksik kalanları saklamadan raporlamalı.

Asla sadece README güncelleyip bitirmemelidir.

Gerçek çalışan sistem hedeflenmelidir.

---

## 21. Son Hedef

Son hedef tek cümle:

```text
Cyzella Production Studio; Excel’den ve manuel girişten etiket/lazer üretim dosyalarını güvenli şekilde hazırlayan, rulo etiket mantığına uygun PDF/PNG/SVG çıktıları veren, modern HTML arayüzlü, Türkçe, terminal gerektirmeyen, makineleri otomatik çalıştırmayan yerel Windows operasyon sistemidir.
```
