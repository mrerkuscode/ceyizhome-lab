# COMMAND ALIASES SETUP REPORT

## Görev

Cyzella Production Studio / Label Studio V1 içinde kısa kullanıcı komutları için kalıcı yorumlama kuralı oluşturuldu.

Bu görev yalnızca komut kısayolu standardını, başlangıç rehberini, lead developer manuelini ve regression testini etkiledi. PDF/PNG render zinciri, output validation, queue, fiziksel cihazlar ve kaynak tasarım dosyalarına dokunulmadı.

## COMMAND_ALIASES.md

`COMMAND_ALIASES.md` oluşturuldu.

Bu dosyada `test` komutu şu anlama sabitlendi:

> Projeyi gerçek kullanıcı gibi test et. Sayfaları gez, butonlara tıkla, Etiket Studio'da yazıyı taşı, resize yap, PDF/PNG oluştur, queue'ya ekle, screenshot al, hata varsa onay beklemeden düzelt, tekrar test et.

## `test` Komutu Ne Anlama Geliyor?

Kullanıcı sadece `test` yazdığında bu artık basit unit test değildir.

Çalıştırılacak kalite döngüsü:

- Zorunlu proje bağlamı ve QA standart dosyaları okunur.
- Ana Sayfa, Etiket Modelleri, Etiket Studio, Toplu Etiket, Yazdırma Sırası, Etiket Çıktıları ve Ayarlar akışları kontrol edilir.
- Etiket Modelleri'nde gerçek click testi yapılır.
- Etiket Studio'da gerçek drag, resize, zoom ve keyboard interaction testi yapılır.
- PDF/PNG oluşturma, preview ve queue zinciri doğrulanır.
- Screenshot alınır.
- Hata varsa onay beklemeden düzeltme ve tekrar test döngüsü başlatılır.
- Sonuç `TEST_COMMAND_REAL_USER_QA_REPORT.md` dosyasına yazılır.

## START_HERE_FOR_CODEX.md Güncellemesi

`START_HERE_FOR_CODEX.md` güncellendi.

Eklenen kural:

- Kullanıcı sadece `test` yazarsa `COMMAND_ALIASES.md` dosyasındaki test komutu uygulanır.
- Bu komut gerçek kullanıcı QA döngüsüdür; sadece pytest çalıştırmak değildir.
- `COMMAND_ALIASES.md` zorunlu okuma listesine eklendi.

## CODEX_LEAD_DEVELOPER_MANUAL.md Güncellemesi

`CODEX_LEAD_DEVELOPER_MANUAL.md` güncellendi.

Eklenen bölüm:

- `Kısa Komutlar`

Bu bölümde `test` komutunun tam gerçek kullanıcı kalite kontrol döngüsü olduğu ve P0/P1 hata bulunursa Codex'in onay beklemeden düzeltmeye devam edeceği yazıldı.

## Regression Test

`tests/test_mvp_safety.py` güncellendi.

Eklenen kontroller:

- `COMMAND_ALIASES.md` dosyası var ve gerekli test komutu metinlerini içeriyor.
- `START_HERE_FOR_CODEX.md` içinde `COMMAND_ALIASES.md` referansı var.
- `CODEX_LEAD_DEVELOPER_MANUAL.md` içinde kısa komut ve tam gerçek kullanıcı kalite kontrol döngüsü kuralı var.

## Çalıştırılan Komutlar

```powershell
node --check src\webui\app.js
```

Sonuç: Başarılı.

```powershell
.venv\Scripts\python.exe -m pytest
```

Sonuç:

```text
112 passed in 4.20s
```

## Güvenlik Etkisi

Güvenlik sınırları korundu.

- CorelDRAW açılmadı.
- Illustrator açılmadı.
- RDWorks açılmadı.
- Yazıcı çalıştırılmadı.
- Lazer başlatılmadı.
- Direct print aktif edilmedi.
- Kaynak AI/CDR dosyaları değiştirilmedi.
- Render/output/queue zincirine dokunulmadı.

## Son Karar

Komut kısayolu sistemi kalıcı hale getirildi.

Bundan sonra kullanıcı sadece `test` yazdığında Codex bunu tam gerçek kullanıcı QA döngüsü olarak yorumlayacak.

P0/P1: Yok.
