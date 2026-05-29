# Yazdır ve Yazdırma Sırası Akışı Raporu

## Görev

Aşama 8 kapsamında Etiket Studio, Toplu Etiket ve Yazdırma Sırası içinde kullanıcıya iki ayrı ve net aksiyon korunarak doğrulandı:

- Yazdır
- Yazdırma Sırasına Ekle

Bu akışta silent/direct print açılmadı. Kullanıcı onayı olmadan yazıcı çalıştırılmaz.

## Etiket Studio

Çıktı üretimi sonrasında kullanıcı şu aksiyonları görür:

1. PDF’i Gör
2. PNG Önizle
3. Yazdır
4. Yazdırma Sırasına Ekle

`Yazdır` butonu son doğrulanmış PDF’i kullanır. PDF yoksa, PDF güncel değilse, output validation başarısızsa veya kullanıcı üretimden sonra metin/ölçü değiştirdiyse işlem durdurulur ve sade mesaj gösterilir.

## Yazdır Butonu Davranışı

Güvenli akış:

1. Son PDF path kontrol edilir.
2. Dosya uzantısının PDF olduğu doğrulanır.
3. Manuel çıktı imzası güncel mi kontrol edilir.
4. Output validation sonucu kontrol edilir.
5. PDF preview payload ile dosya erişilebilirliği doğrulanır.
6. `Yazdırmaya Hazır` onay modalı açılır.
7. Modalda model adı, isim, tarih, not, ölçü, adet ve PDF dosya adı gösterilir.
8. Kullanıcı `Yazdır` derse PDF varsayılan görüntüleyicide açılır.

Doğrudan yazıcıya gönderim yapılmaz. `window.print` veya silent print kullanılmaz.

## Yazdırma Sırasına Ekle

Queue akışı korundu:

- Sadece doğrulanmış batch PDF queue’ya eklenir.
- Duplicate engeli korunur.
- Eski/stale output eklenmez.
- Queue ekleme sonrası modern `Yazdırma sırasına eklendi` modalı gösterilir.
- Modalda `Devam Et` ve `Yazdırma Sırasına Git` seçenekleri bulunur.

## Yazdırma Sırası Ekranı

Her queue item için aksiyonlar:

- PDF’i Aç
- Yazdır
- PNG Önizle
- Sıradan Kaldır

Queue içindeki `Yazdır` aynı güvenli onay modalını kullanır.

## Toplu Etiket

Toplu üretim sonrası son batch PDF için:

- Yazdır
- Yazdırma Sırasına Ekle

aksiyonları görünür. Bu akış da direct print yapmaz.

## Testler

Çalıştırılan komutlar:

```text
node --check src\webui\app.js
.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py -q
.venv\Scripts\python.exe scripts\print_action_real_user_gate.py
.venv\Scripts\python.exe scripts\verify_corel_editor_interactions.py
.venv\Scripts\python.exe scripts\verify_corel_undo_redo.py
.venv\Scripts\python.exe scripts\real_production_quality_gate.py
.venv\Scripts\python.exe scripts\final_acceptance_gate.py
.venv\Scripts\python.exe scripts\capture_webui_screenshots.py
.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py
```

Sonuçlar:

- `node --check`: PASSED.
- `pytest`: 116 passed.
- `print_action_real_user_gate.py`: PASSED.
- `verify_corel_editor_interactions.py`: PASSED.
- `verify_corel_undo_redo.py`: PASSED.
- `real_production_quality_gate.py`: PASSED.
- `final_acceptance_gate.py`: PASSED.
- Screenshot capture komutları tamamlandı.

## Gerçek Kullanıcı Gate Sonucu

`scripts\print_action_real_user_gate.py` şu davranışları doğruladı:

- Etiket Studio’da Yazdır butonu görünür.
- Yazdır butonu güvenli onay modalı açar.
- Modal model, isim, tarih, not, ölçü, adet ve PDF dosya adını gösterir.
- Son input değişirse stale PDF yazdırma engellenir.
- Yazdırma Sırasına Ekle doğru batch PDF’i queue’ya ekler.
- Queue item içindeki Yazdır aynı güvenli modalı açar.
- Direct/silent print tetiklenmez.

Güncel gate çıktısı:

- PDF: `output/2026-05-13/print/manual/2026-05-13_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_13.pdf`
- Queue count: 163

## Screenshot Kanıtları

- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-13\print_action_gate\studio_output_actions.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-13\print_action_gate\safe_print_modal.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-13\print_action_gate\queue_safe_print_modal.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-13\ui_screenshots\yazdirma_sirasi.png`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-13\quality_gate\quality_gate_print_queue.png`

## Güvenlik

- CorelDRAW açılmadı.
- Illustrator açılmadı.
- RDWorks açılmadı.
- Yazıcı otomatik çalıştırılmadı.
- Lazer başlatılmadı.
- Direct print aktif edilmedi.
- Kaynak AI/CDR dosyaları değiştirilmedi.

## Kalan Riskler

Sistem print dialog entegrasyonu bilinçli olarak eklenmedi. İlk güvenli fazda `Yazdır` PDF’i kullanıcı onayına sunar. Fiziksel yazdırma kullanıcı tarafından PDF görüntüleyici üzerinden yapılır.

## P0/P1 Durumu

P0/P1 hata yok. Yazdır ve Yazdırma Sırasına Ekle ayrımı net, güvenli ve testlidir.
