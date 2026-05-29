# LABEL OUTPUT GROUP SUMMARY REPORT

Tarih: 2026-05-08

## Görev

Etiket Çıktıları sayfasında müşteri çıktılarının model bazında daha hızlı anlaşılmasını sağlamak.

## Değiştirilen Dosyalar

- `src/webui/index.html`
- `src/webui/app.js`
- `src/webui/styles.css`
- `tests/test_mvp_safety.py`

## Yapılan Düzeltmeler

- Etiket Çıktıları filtrelerinin altına “Çıktı grupları” özeti eklendi.
- Gruplar filtrelenen müşteri çıktılarından gerçek zamanlı hesaplanıyor.
- Her grup model adını, toplam çıktı sayısını, PDF/PNG/batch dağılımını ve queue ile eşleşen kayıt sayısını gösteriyor.
- Teknik raporlar müşteri çıktı gruplarına dahil edilmiyor.

## UI/UX Etkisi

Kullanıcı çok dosyalı üretim klasöründe hangi modelden kaç çıktı olduğunu ve hangi kayıtların queue ile eşleştiğini daha hızlı görebilir.

## Güvenlik Etkisi

Dosya silme, taşıma veya çıktı zinciri değişikliği yapılmadı. Bu çalışma yalnızca görünür özet üretir.

## Testler

- `node --check src\webui\app.js`: geçti.
- `.venv\Scripts\python.exe -m pytest tests\test_mvp_safety.py`: 110 passed.

## P0/P1 Durumu

Kalan P0/P1 hata görülmedi.
