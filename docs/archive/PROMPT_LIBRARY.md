# PROMPT LIBRARY

Bu dosya gelecekteki görevleri netleştirmek için standart şablonlar içerir.

## Bug Fix

```text
Proje: C:\Users\Pc\Documents\New project\production-bot
Sorun:
Beklenen davranış:
Güvenlik sınırları:
İlgili sayfa:
Test ve screenshot zorunlu.
P0/P1 varsa önce düzelt.
```

## UI Redesign

```text
Sadece [sayfa adı] sayfasını geliştir.
Normal kullanıcı teknik detay görmesin.
Butonlar sessiz kalmasın.
Mock/stale veri gösterme.
Test, screenshot ve kısa rapor oluştur.
```

## Page Development / Product Builder

```text
Cyzella Production Studio içinde [sayfa] ekranını normal kullanıcı için geliştir.
Önce P0/P1 riskleri kontrol et.
Sonra sayfayı üretimi hızlandıracak şekilde sadeleştir ve güçlendir.
Teknik detayları normal kullanıcıdan gizle.
Gerçek click/state testi ekle.
Screenshot al.
Rapor oluştur: [REPORT_NAME].md
```

## Button Regression

```text
[Buton adı] manuel tıklamada çalışmıyor.
Gerçek click testi yap.
Sadece fonksiyon var mı kontrolü yeterli değil.
Route/state/modal/çıktı sonucunu doğrula.
Regression test ekle.
```

## Button Regression With Proof

```text
[Sayfa] içinde [butonlar] manuel testte çalışmıyor.
Sadece fonksiyon var mı diye bakma.
Gerçek tıklama, route/state değişimi ve modal/queue/output sonucunu doğrula.
Teknik editör normal kullanıcıya açılmasın.
Regression test ekle.
Rapor oluştur: [REPORT_NAME].md
```

## Render Sync

```text
Canvas ile PDF/PNG farklı.
Payload, background path, field values, geometry ve output validation zincirini kontrol et.
Sadece krem/bej çıktı başarı sayılmasın.
Kalite kapısını çalıştır.
```

## Page Audit

```text
[Sayfa adı] sayfasını ürün, UX, buton, güvenlik ve test açısından denetle.
P0/P1/P2/P3 listesi çıkar.
P0/P1 varsa onay beklemeden düzelt.
```

## Release Check

```text
Final kalite kontrol yap.
Tüm ana sayfalar açılıyor mu?
Canvas -> PDF/PNG -> Queue zinciri çalışıyor mu?
Direct print kapalı mı?
Türkçe karakter doğru mu?
Screenshot ve test sonuçlarını raporla.
```

## Release Check With Product Review

```text
Final release öncesi P0/P1 kalite kapısını çalıştır.
Ana butonları, canvas-output uyumunu, queue doğruluğunu, Türkçe karakterleri ve güvenlik sınırlarını doğrula.
Sayfaların normal kullanıcı için üretimi hızlandırıp hızlandırmadığını değerlendir.
Screenshotları güncelle.
Kalan P0/P1 varsa bitmiş sayma.
Rapor oluştur: [REPORT_NAME].md
```
