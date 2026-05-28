# UI/UX User Journey Test Plan

Tarih: 2026-05-13

## Otomatik Test Gruplari

- `verify_label_models_premium_flow.py`
- `verify_bulk_gallery_excel_flow.py`
- `verify_outputs_gallery_flow.py`
- `verify_print_queue_flow.py`
- `verify_new_model_wizard.py`
- `verify_corel_editor_interactions.py`
- `verify_corel_undo_redo.py`
- `verify_design_system_consistency.py` (eklenmeli)
- `verify_user_journey_end_to_end.py` (eklenmeli)

## Screenshot Plani

- Ana Sayfa
- Etiket Modelleri genel
- Etiket Modelleri secili model
- Etiket Modelleri gorsel eksik model
- Yeni Model Wizard adim 1
- Yeni Model Wizard gorsel adimi
- Yeni Model Wizard kaydet adimi
- Etiket Studio genel
- Etiket Studio layer/font/renk paneli
- Etiket Studio drag sonrasi
- Etiket Studio resize sonrasi
- Toplu Etiket empty state
- Toplu Etiket galeri
- Toplu Etiket edit modal
- Toplu Etiket uzun isim
- Etiket Ciktilari galeri
- Etiket Ciktilari selected preview
- Yazdirma Sirasi genel
- Yazdirma Sirasi selected job
- Yazdir modal
- Ayarlar
- Yardim / onboarding
- RDWorks isim kesim layout, ayri faz

## Manuel Kullanici Senaryolari

### Senaryo 1 - Tek Etiket Hazirla ve PDF Al

1. Ana Sayfa ac.
2. Etiket Modelleri'ne git.
3. Hazir bir model sec.
4. Etiket Hazirla ile Studio'ya gec.
5. Isim, tarih, not gir.
6. Ismi mouse ile tasi.
7. Koseden resize yap.
8. Font preset ve renk degistir.
9. Akilli Duzen calistir.
10. PDF/PNG olustur.
11. PDF'i gor ve PNG onizle.
12. Yazdir modalini ac.
13. Yazdirma Sirasina Ekle.

Kabul:

- Butonlar sessiz kalmaz.
- Canvas ile PDF/PNG ayni state'i kullanir.
- Direct print calismaz.

### Senaryo 2 - Model Ekle, Gorsel Bagla, Studio'da Ac

1. Etiket Modelleri'ne git.
2. Yeni Model Ekle'yi ac.
3. Model adi ve kategori gir.
4. Olcu gir.
5. Tasarim gorseli yukle.
6. Oran kontrolunu gor.
7. Isim/Tarih/Not alanlarini olustur.
8. Kaydet.
9. Yeni modeli listede sec.
10. Studio'da ac.

Kabul:

- Modal footer kesilmez.
- Teknik editor acilmaz.
- Model Studio'da acilir.

### Senaryo 3 - Excel'den 20 Satir Yukle

1. Toplu Etiket'e git.
2. Ornek Excel indir veya fixture yukle.
3. Kontrol et.
4. Hazir, uyarili ve hatali satirlari filtrele.
5. Hatalı satirda model secerek duzelt.
6. Uzun isimli satirda Yazilari Sigdir calistir.
7. Bir satirda Kaydet.
8. Bir satirda Vazgec.
9. Bir satirda Sil.
10. Hazir olanlari uret.
11. Yazdirma Sirasina Ekle.

Kabul:

- Hatalı satir uretilmez.
- Silinen satir uretilmez.
- Batch manifest dogru sayilari tasir.

### Senaryo 4 - Ciktiyi Bul ve Tekrar Uret

1. Etiket Ciktilari'na git.
2. Model/isim aramasi yap.
3. Bir PDF karti sec.
4. Sag preview'i kontrol et.
5. Studio'da Ac.
6. Tekrar Uret.
7. Sıraya Ekle.

Kabul:

- Teknik raporlar varsayilan listede gorunmez.
- Preview bos/kirik degilse gosterilir; yoksa cozumlu placeholder vardir.

### Senaryo 5 - Yazdirma Sirasindan PDF Ac

1. Yazdirma Sirasina git.
2. Bekleyen filtrele.
3. Preview'li bir is sec.
4. Yazdir modalini ac.
5. PDF'i Ac.
6. Yazdirildi isaretle.
7. Beklemeye Al ile geri al.

Kabul:

- Onay olmadan temizleme/yazdirma yok.
- Direct/silent print yok.
- Status sayilari guncellenir.

### Senaryo 6 - Uzun Isim ve Turkce Harf

1. Studio'da uzun isim gir.
2. Yazilari Sigdir calistir.
3. Font ve renk degistir.
4. PDF/PNG olustur.
5. Toplu Etiket'te ayni uzun isimli satiri kontrol et.

Kabul:

- Text preview disina tasmaz.
- Turkce karakter bozulmaz.
- Output validation gecer.

### Senaryo 7 - RDWorks Isim Kesim, Ayri Faz

1. Excel'de isim_kes = evet olan satirlari yukle.
2. Isim Kesim galerisini ac.
3. Sedef Sefer gibi iki isimli kaydi kontrol et.
4. Kalinlastirma ve olcu ayarlarini degistir.
5. RDWorks dosya paketi hazirla.
6. DXF/SVG/PDF/manifest dosyalarini kontrol et.

Kabul:

- RDWorks otomatik acilmaz.
- Lazer baslamaz.
- Manifest text-to-path ve offset durumunu dogru yazar.
# 2026-05-16 Geçen Kullanıcı Akışı Testleri

Geçen otomatik kullanıcı akışları:

- Studio layout stability
- Corel editor drag/resize/font/color/output
- Label Models premium flow
- Bulk Gallery Excel flow
- Outputs Gallery flow
- Print Queue flow
- New Model Wizard flow
- Clean customer demo flow
- RDWorks name cut layout/export
- Combined Excel label + name cut flow
- Real production quality gate
- Final acceptance gate

Son manuel turda kontrol edilecekler:

- Studio'da mouse hareketinde flicker yok.
- Sağ dock scroll ana sayfayı kaybettirmiyor.
- Yazdır modalı direct print yapmıyor.
- Toplu Etiket 100 satırda okunabilir.
- Queue ve Outputs varsayılan müşteri görünümü teknik dosyalarla kirlenmiyor.
