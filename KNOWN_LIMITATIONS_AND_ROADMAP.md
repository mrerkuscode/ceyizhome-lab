# KNOWN LIMITATIONS AND ROADMAP

Güncel tarih: 2026-05-07

Bu dosya Codex tarafından her önemli işten sonra güncel tutulur. Amaç, P0/P1 stabilite ile P2/P3 ürün gelişimini karıştırmamaktır.

## Stabilite Kilidi

P0/P1 hata varsa roadmap özelliği uygulanmaz. Öncelik sırası:
1. Çalışmayan butonlar
2. Canvas/PDF/PNG uyumu
3. Drag/resize/keyboard
4. selectedModel ve model geçişleri
5. Queue doğruluğu
6. Teknik Mod izolasyonu
7. UX sadeleştirme
8. Premium görsel kalite
9. Yeni özellikler

## Bilinen Sınırlar

- CorelDRAW, Illustrator, RDWorks, yazıcı, lazer ve direct print ana kullanıcı akışına bağlanmaz.
- Kaynak AI/CDR dosyaları değiştirilmez veya overwrite edilmez.
- JPG/PNG içindeki eski yazı doğrudan değiştirilemez; yeni düzenlenebilir text layer eklenir.
- QWebEngine ve otomatik testler önemli olsa da manuel kullanıcı gözlemi rapordan üstündür.
- Büyük mimari refactor manuel karar gerektirir.

## Yakın Dönem P2 UX İşleri

- Etiket Modelleri model health ve onarım aksiyonlarını daha görünür ama sade hale getirmek.
- Etiket Studio için yazı otomatik sığdırma uyarısı ve güvenli alan rehberleri eklemek.
- Toplu Etiket için satır satır önizleme ve hata açıklamalarını güçlendirmek.
- Yazdırma Sırası ve Etiket Çıktıları sayfalarında müşteri çıktısı/teknik çıktı ayrımını daha net yapmak.
- Ayarlar sayfasında tehlikeli veya teknik seçenekleri daha iyi izole etmek.

## P3 Büyük Fikirler

- Undo/Redo sistemi
- Snap/guides ve merkez hizalama araçları
- Üretim geçmişi
- Rulo yerleşim simülasyonu
- Canvas vs final output fark kontrolü
- Model versiyonlama ve backup geçmişi
- Gelişmiş preflight paneli
- Dosya isimlendirme standardının UI'da yönetilmesi

## Son Karar

Cyzella Production Studio için hedef, önce güvenilir üretim akışı, sonra premium ürün deneyimi, en son gelişmiş otomasyondur.
