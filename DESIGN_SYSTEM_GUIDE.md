# DESIGN SYSTEM GUIDE

## 2026-05-10 Premium UI Standardı

Bu proje artık sadece çalışan MVP değil, normal kullanıcının güvenle kullanacağı premium üretim aracı olarak tasarlanır.

Temel kararlar:
- Arayüz beyaz, ferah ve Apple/macOS hissinde kalır.
- Ana üretim aksiyonu her ekranda ilk bakışta anlaşılır.
- Teknik kavramlar normal kullanıcı modunda gizlenir.
- Kart, buton, badge, modal ve boş state dili her sayfada aynı kalır.
- Gerçek veri yoksa mock gösterilmez; sade boş state gösterilir.
- Görsel polish render/output/queue zincirini değiştirmeden yapılır.

Ortak sınıf standardı:
- Kartlar `card`, `workflow-card`, `detail-panel` ve ilgili sayfa kartları üzerinden yumuşak gölge ve net spacing kullanır.
- Ana butonlar `btn primary`, üretim/çıktı aksiyonları gerektiğinde `btn gold`, güvenli durumlar `btn green` kullanır.
- Durumlar `pill`, `status-line`, `health-kpi` ve sayfa özel badge'leriyle gösterilir.
- Modal içinde başlık kısa, açıklama sade, sol aksiyon devam/iptal, sağ aksiyon ana işlem olur.
- Seçili model/yazı alanı border, gölge ve badge ile net ayrılır.

## Görsel His

Hedef his:
- premium
- beyaz ve ferah
- Apple/macOS benzeri sakinlik
- büyük görseller
- net butonlar
- teknik karmaşadan uzak

## Layout

Ana ekranlarda:
- geniş boşluklar kontrollü kullanılmalı
- kartlar amaçlı olmalı
- iç içe kartlardan kaçınılmalı
- ana iş akışı ilk bakışta anlaşılmalı

## Renk

Ana aksiyon: mavi.  
İkincil vurgu: gold.  
Hazır/güvenli durum: yeşil.  
Uyarı: amber/gold.  
Hata: kırmızı ama abartısız.

Tek renkli, yorucu paletten kaçın.

## Butonlar

Buton adı işlemle aynı olmalı:
- Etiket Hazırla
- Studio'da Düzenle
- Önizle
- Görsel Bağla
- Yazdırma Sırasına Git

Sessiz buton yasaktır. Her buton işlem yapar veya sade mesaj verir.

## İkonlar

Harf kutuları yerine anlamlı ikonlar kullan:
- Studio: kalem/etiket
- Toplu: tablo
- Modeller: galeri/katalog
- Güvenlik: kalkan/onay

## Modal

Modern modal:
- kısa başlık
- sade açıklama
- net iki aksiyon
- sağda ana aksiyon, solda devam/iptal

Native Windows popup sadece teknik veya sistem zorunlu durumlarda kalmalı; ana kullanıcı akışında web içi modal tercih edilir.

## Senior Product Builder Standardı

Her ekran, üretimi hızlandıran bir çalışma yüzeyi gibi hissettirmelidir. Sadece güzel görünen ama kullanıcıyı sonraki adıma taşımayan UI yeterli değildir.

Değerlendirme soruları:
- Ana aksiyon ilk bakışta belli mi?
- Buton dili kullanıcı niyetine uygun mu?
- Modal açıldığında kullanıcı ne olduğunu ve ne yapacağını anlıyor mu?
- Hata mesajı çözüm sunuyor mu?
- Teknik kavramlar normal kullanıcıdan gizli mi?
- Ekran gerçek veri yoksa mock/stale veri yerine sade boş state gösteriyor mu?

Örnek ürün dili:
- Etiket Hazırla
- Studio'da Düzenle
- Görsel Bağla
- PDF/PNG Oluştur
- Yazdırma Sırasına Git
- Devam Et
- Sorunları Otomatik Düzelt

## macOS/iOS Referans Tasarım Kararları

`docs/design/macos_ui_reference.png` için verilen referans dili şu şekilde uygulanır:

- Sol sidebar açık, yumuşak, translucent ve macOS pencere hissi veren bir kabuk kullanır.
- Aktif menü mor/mavi primary gradient ile görünür.
- Kartlar büyük radius, ince border ve soft shadow kullanır.
- Ana üretim aksiyonları mor/mavi, çıktı ve dikkat aksiyonları amber, güvenli durumlar yeşil ile gösterilir.
- Model kartları preview odaklıdır; kırık görsel yerine modern placeholder gösterilir.
- Sağ detay panelleri ayrı bir üretim çalışma yüzeyi gibi görünür.
- Canvas frame beyaz, ferah ve güçlü handle görünürlüğüyle düzenlenir.
- Modal arka planı blur alır; modal kartları geniş radius ve net aksiyon hiyerarşisi kullanır.
- Teknik bölümler normal kullanıcı akışında ikincil, düşük baskınlıkta kalır.

CSS tokenları:

- `--mac-bg`
- `--mac-surface`
- `--mac-surface-strong`
- `--mac-border`
- `--mac-shadow`
- `--mac-shadow-soft`
- `--mac-purple`
- `--mac-blue`
- `--mac-green`
- `--mac-amber`
- `--mac-red`

Ortak sınıf hedefleri:

- `.app-shell`
- `.mac-sidebar`
- `.page-shell`
- `.premium-card`
- `.action-card`
- `.stat-card`
- `.status-pill`
- `.primary-button`
- `.ghost-button`
- `.model-health-badge`
- `.right-detail-panel`
- `.canvas-frame`
- `.modal-shell`
