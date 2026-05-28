# CeyizHome Lab — UI/UX Discovery & Plan

**Versiyon:** discovery v1.0 · **Tarih:** 2026-05-28 · **Kaynak:** çalışan app + GitHub main · **Hazırlayan:** Claude Chrome

## 1. Özet

CeyizHome Lab olgun bir tasarım sistemine sahip (semantik renk token'ları, focus-ring, radius ölçeği, sistem fontu — Türkçe karakter güvenli) ve bağlam dökümanının söylediğinden çok daha geniştir: 9 değil, 5 grupta ~18 sayfa/alt-sayfa var. En kritik darboğaz Yazdırma Sırası'nda: çoklu seçim var ama "PDF Aç" ve "Yazdır" eylemleri yalnızca ilk seçili öğeyi işliyor — 50+ sipariş/gün senaryosunda operatör her etiketi tek tek açıp basmak zorunda. İkinci sorun mobil değil, telefon desteğinin olmaması: en küçük breakpoint 700px, ≤480px için sıfır kural.

## 2. Sayfa Sayfa Değerlendirme

### Ana Sayfa
KPI bandı ve durum özeti net. Hazır/hata durumu renkle belirtilmiş. Eylem butonları açık.

### Etiket Modelleri
Model galerisi çalışıyor. Seçim → önizleme → düzenleme akışı tutarlı. Yedek/geri yükleme mevcut.

### Etiket Studio
Editör ağır render yapıyor (21k satır app.js). Sayfaya geçişte kısa donma var. Tooltip eksiklikleri var.

### Manuel Etiket
Alanlar çalışıyor. Sayı girişi düzgün. Önizleme bağlantısı eksik bazı durumlarda.

### Toplu Üretim Studio
Excel seçimi, satır seçimi, toplu üretim akışı mevcut. Sütun eşleme arayüzü karmaşık.

### Yazdırma Sırası (KRİTİK)
Arama, 8-durum filtresi, toplu seçim, toplu eylemler mevcut.
**Darboğaz:** PDF açma ve yazdırma sadece ilk seçili öğeyi işliyor.

### Trendyol Entegrasyonu
Sipariş senkronizasyonu, kanıt eşleştirme, ürün eşleştirme — tam akış mevcut.

### Ayarlar
Yazıcı profilleri, güvenlik, yedekleme — işlevsel. Geliştirici modülleri açık görünüyor.

### Raporlar
KPI bandı, üretim özeti. fetchMetrics bridge çağrısı ile canlı veri.

## 3. Genel UX Problemleri

- **Sembol-butonlar etiketsiz:** editör ve bazı barlarda Unicode semboller (⋮ ☰ ≣ ⌁) tooltipsiz; tutarsız ikon dili. Öncelik: Orta.
- **"Sahte HAZIR/başarı" (SYS-2):** JS ile basılıyor — durumu gerçek state'e bağlamak app.js'de küçük düzeltme gerektirir. Öncelik: Yüksek (güven sorunu).
- **Render donması:** Etiket Studio'ya geçişte sayfa kısa süre yanıt vermedi — 21k satır app.js + ağır editör render'ı. Öncelik: Orta.
- Türkçe metin genel olarak doğru ve net.

## 4. Print Queue Özel Analiz (Kritik)

Mevcut durum aslında zengin: arama, durum filtresi (8 durum), tip/kaynak filtresi, tarih filtresi, sıralama, "Tümünü seç", ve toplu eylemler (Hazır Olanları Seç, Yazdırıldı İşaretle, Teslim Et, Sıradan Kaldır).

**Asıl darboğaz (app.js fonksiyon doğrulaması):**
- `markSelectedQueuePrinted` ve `markSelectedQueueDelivered` → seçili tüm öğeler üzerinde döngü kuruyor (gerçek toplu işlem). İyi.
- `openSelectedQueuePdfs` ("İlk PDF'i Aç") ve `printSelectedQueueItems` ("İlk Seçiliyi Yazdır") → döngü YOK, yalnızca ilk öğe işleniyor.

**Sonuç:** 50 öğe seçseniz bile PDF açma ve yazdırma tek tek yapılır. 100 öğe = ~100×2 tık. Durum işaretleme topludur, ama asıl iş (aç+bas) değildir.

## 5. Mobile Responsive Strateji

Gerçek tablo: 126 max-width media query var, ama en küçüğü 700px. ≤480px (telefon) için sıfır kural; 481–768px aralığında yalnızca 9 kural.

**LEYLA KARARI: TAM TELEFON DESTEĞİ** (sadece görüntüleme değil, veri girişi de)

## 6. Öncelik Sırası — Sprint 4 (Leyla Onayladı)

1. Print Queue YARI-OTOMATİK toplu yazdır/aç (her PDF sonrası "Sonraki" butonu)
2. SYS-2 sahte "HAZIR" badge'ini gerçek state'e bağla
3. Rafta modülleri menüden gizle (Design Lab, Font Test Lab, Native AI/CDR, Lazer)
4. Sayfa konsolidasyonu (18 → 8 menü öğesi)
5. Mobile responsive TAM destek (sonraki sprint'lerde)
