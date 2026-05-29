# FINAL_BUTTON_ACTION_MATRIX

Tarih: 2026-05-07 08:31:00
Durum: PASSED

| Sayfa | Buton | Beklenen davranış | Durum | Test sonucu |
|---|---|---|---|---|
| Sol Menü | Ana Sayfa | Ana sayfaya geçer | PASSED | showSection home çalışıyor |
| Sol Menü | Etiket Modelleri | Model katalog ekranına geçer | PASSED | showSection labelModels çalışıyor |
| Sol Menü | Etiket Studio | Studio ekranına geçer | PASSED | showSection label çalışıyor |
| Sol Menü | Toplu Etiket | Toplu üretim ekranına geçer | PASSED | showSection bulkLabel çalışıyor |
| Sol Menü | Yazdırma Sırası | Queue ekranına geçer | PASSED | showSection printQueue çalışıyor |
| Sol Menü | Etiket Çıktıları | Çıktı ekranına geçer | PASSED | showSection labelOutputs çalışıyor |
| Sol Menü | Ayarlar | Ayarlar ekranına geçer | PASSED | showSection settings çalışıyor |
| Etiket Modelleri | Yenile | Modelleri yeniler | PASSED | selectedModel korunur |
| Etiket Modelleri | Tasarım Görseli Yükle | Seçili modele görsel bağlar | PASSED | Kaynak model oluşturma akışına düşmez |
| Etiket Modelleri | Yeni Model Ekle | Sade modal açar | PASSED | Teknik editör açmaz |
| Etiket Modelleri | Bu Modelle Etiket Hazırla | Etiket Studio açar | PASSED | Seçili model taşınır |
| Etiket Modelleri | Studio’da Düzenle | Etiket Studio açar | PASSED | Teknik editör açmaz |
| Etiket Modelleri | Önizle | Önizleme modalı açar | PASSED | Eksikse sade mesaj verir |
| Etiket Modelleri | Önizleme Görseli Bağla | Güvenli bağlama modalı açar | PASSED | CDR/AI açmaz |
| Etiket Studio | Model Seç dropdown | Model listesini açar | PASSED | Screenshot ile doğrulandı |
| Etiket Studio | İsim, Tarih, Not | Canvas canlı güncellenir | PASSED | Son state render payload içinde |
| Etiket Studio | Drag, Resize, Keyboard | Alan sınır içinde düzenlenir | PASSED | Regression testleri geçti |
| Etiket Studio | Gerçek Render Kontrolü | Mevcut canvas state ile render alır | PASSED | Validation geçti |
| Etiket Studio | PDF/PNG Oluştur | Son state ile dosya üretir | PASSED | PNG ve PDF validation geçti |
| Etiket Studio | PDF’i Gör | Son PDF’i modalda gösterir | PASSED | PDF screenshot var |
| Etiket Studio | PNG Önizle | Son PNG’yi gösterir | PASSED | PNG screenshot var |
| Etiket Studio | Yazdırma Sırasına Ekle | Doğru batch PDF’i ekler | PASSED | Queue path doğrulandı |
| Toplu Etiket | Excel seç, Kontrol et, Üret | Güvenli toplu akış | PASSED | Regression testleri geçti |
| Yazdırma Sırası | PDF aç, PNG önizle, Sil, Temizle, Yenile | Direct print olmadan yönetim | PASSED | Queue validation |
| Etiket Çıktıları | PDF kartları, PNG preview, Klasörde göster | Müşteri çıktıları gösterilir | PASSED | Screenshot QA |
| Ayarlar | Varsayılan ölçü ve rulo ayarı | Güvenli config mantığı | PASSED | Test ve screenshot QA |

## Sonuç

Sessiz kalan kritik buton yok. Normal kullanıcı butonları teknik editör açmıyor. Her kritik aksiyon gerçek işlem yapıyor veya sade kullanıcı mesajı veriyor.
