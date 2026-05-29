# UI UX RULES

## 2026-05-10 Premium Üretim Ekranı Kuralları

Her sayfa kullanıcının bir sonraki üretim adımını açıkça göstermelidir. Güzel görünen ama işlem üretmeyen ekran kabul edilmez.

Genel kurallar:
- Ana buton gerçek işlem yapar; sadece toast göstermek başarı değildir.
- Teknik Mod kapalıyken JSON, X/Y, field id, template path, backend path, CDR/AI path ve debug metinleri görünmez.
- Önizleme eksikse kırık görsel yerine açıklayıcı placeholder ve çözüm butonu gösterilir.
- Model kartı, sağ panel ve Studio geçişleri aynı `selectedModel` davranışını kullanır.
- Etiket Studio'da handle görünmesi yeterli değildir; drag/resize testinde gerçek x/y/width/height/font_size değişimi doğrulanır.
- PDF/PNG ve queue zinciri tasarım polish sırasında değiştirilmez.

Sayfa standardı:
- Ana Sayfa üretim başlangıç merkezi olarak kalır.
- Etiket Modelleri premium katalog ve model yönetim ekranıdır.
- Etiket Studio canvas odaklı üretim ekranıdır.
- Toplu Etiket adım adım Excel üretim akışı olarak görünür.
- Yazdırma Sırası manuel PDF kontrolünü öne çıkarır.
- Etiket Çıktıları müşteri çıktıları ile teknik raporları ayırır.

## Genel

Normal kullanıcı teknik detay görmez:
- JSON
- X/Y
- field id
- template path
- backend
- debug
- CDR/AI path
- native editor
- render payload

## Ana Sayfa

Üretim başlangıç merkezi olmalı:
- Etiket Studio
- Toplu Etiket
- Etiket Modelleri
- Hızlı İşlemler
- Bugünkü Üretim Özeti
- Model Durumu
- Son İşler
- Yazdırma Güvenliği

Mock/stale veri gösterme. Veri yoksa "Veri yok" veya sade boş state göster.

ST/XL/MD gibi harf kısaltmaları yerine gerçek ikon veya açık kullanıcı dili kullanılmalı. Son İşler model adı, isim, ölçü ve adet gibi üretim için gerekli bilgiyi göstermeli.

## Etiket Modelleri

Güçlü model katalog ve yönetim ekranı:
- büyük model kartları
- preview veya placeholder
- model health badge
- Etiket Hazırla
- Studio'da Düzenle
- Önizle
- Görsel Bağla
- Modeli Kontrol Et
- Teknik Mod default kapalı

Her kart butonu doğru modeli taşımalıdır. Gerçek click testi şarttır.

Kart ve sağ panel aynı `selectedModel` state'inden beslenir. Buton testi sadece DOM varlığı değil, gerçek route/state değişikliğiyle doğrulanır.

## Etiket Studio

Ana üretim ekranı:
- model seçimi sağ panelde net
- canvas ana odak
- İsim/Tarih/Not canlı update
- drag, corner resize, side resize
- keyboard movement
- font/renk/hizalama
- etiket boyutu default/override
- gerçek render kontrolü
- PDF/PNG oluştur
- PDF/PNG preview
- Yazdırma Sırasına Ekle

Canvas ne gösteriyorsa PDF/PNG onu üretir.

Seçili yazı alanı badge, border ve handle gösterir; handle görünmesi tek başına başarı değildir. Drag testinde x/y değişimi, resize testinde width/height/font_size değişimi doğrulanır. Zoom modlarında koordinat dönüşümü ayrıca kontrol edilir.

## Toplu Etiket

Excel -> kontrol -> hata göster -> üret -> queue akışı net olmalı.

Hatalı satır varsa kullanıcı üretim öncesi görmeli.

## Yazdırma Sırası

Direct print yok. Kullanıcı PDF'i manuel açar ve kontrol eder.

Sıraya eklendi mesajı modern web modal olmalı:
- Devam Et
- Yazdırma Sırasına Git

## Etiket Çıktıları

Müşteri çıktıları teknik raporlardan ayrılır. PDF ve PNG preview çalışır.

## Ayarlar

Varsayılan ölçüler ve rulo ayarları güvenli kaydedilir. Etiket Studio geçici override global ayarı bozmaz.

## Genel Ürün Kontrolü

Her UI işi sonunda şu sorular yanıtlanır:
- Kullanıcı teknik bilgi olmadan akışı tamamlayabilir mi?
- Sessiz kalan buton var mı?
- Hata olduğunda sade çözüm mesajı var mı?
- Screenshot güncel mi?
- Render/output/queue etkilenmişse kalite kapısı çalıştı mı?

## macOS/iOS UI Uygulama Kuralları

Referans görseldeki tasarım dili birebir kopyalanmaz; ürünün mevcut işlevleri korunarak uyarlanır.

Uygulama kuralları:

- Sidebar açık renkli, sakin ve güven verici olmalı.
- Aktif sayfa durumu her zaman net görünmeli.
- Kartlar üretim aksiyonunu gizlememeli; ana butonlar kolay bulunmalı.
- Etiket Modelleri sayfasında model kartı, health badge ve sağ panel aynı görsel dilde olmalı.
- Etiket Studio canvas alanı editör gibi hissettirmeli; seçili yazı alanı handle'ları kolay tutulmalı.
- Modal ve empty state kullanıcıyı çözüme yönlendirmeli.
- Teknik Mod açık değilse teknik debug ve path bilgileri gösterilmemeli.
- UI polish sırasında render/output/queue işlevlerine dokunulmamalı.
