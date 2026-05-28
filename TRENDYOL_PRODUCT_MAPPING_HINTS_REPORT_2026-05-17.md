# Trendyol Product Mapping Hints Report

Date: 2026-05-17

## Summary

Trendyol katalog eslestirme onerileri daha kullanilir hale getirildi. Katalogdaki urun adi `etiket`, `isim baskili`, `soz/nisan`, `kiz isteme`, `cikolata`, `mevlut` gibi uretim sinyalleri tasiyorsa sistem artik tamamen bos `review` yerine `label` uretim tipi onerir.

Bu bir otomatik uretim karari degildir. Model secimi ve kullanici onayi olmadan kayit uretime hazir sayilmaz.

## Live Catalog Result

Canli katalog onerileri yeniden olusturuldu:

- Toplam eslestirme onerisi: 332
- `label`: 327
- `label_and_name_cut`: 3
- `review`: 2
- Hepsi `needs_review` durumunda kaldı.
- Otomatik uretime hazir satir: 0

Son review Excel:

- `output/2026-05-17/trendyol/trendyol_mapping_review_134730_632064.xlsx`

## Safety

- Barkod/SKU eslestirmesi olmadan siparis uretime alinmaz.
- Model secilmeden etiket uretimi hazir sayilmaz.
- Soru/mesaj kaniti ve kullanici dogrulamasi olmadan Trendyol satiri aktarilmaz.
- Direct print yok.
- RDWorks/lazer otomatik yok.
- `C:\Users\Pc\Desktop\mucoxai1` degistirilmedi.

## Tests

Passed:

- `.venv\Scripts\python.exe -m pytest tests\test_trendyol_order_to_production.py -q`
- `.venv\Scripts\python.exe scripts\verify_trendyol_mapping_review_workflow.py`
- `.venv\Scripts\python.exe scripts\verify_trendyol_live_mapping_readiness.py`

## Next

Kullanici veya operator review Excel / Urun Eslestirme ekranindan gercek barkodlari su kararlara baglamali:

- Etiket
- Isim kesim
- Etiket + isim kesim
- Uretim yok
- Kontrol gerekli

Onaylanan eslestirmelerden sonra, soru/mesaj kaniti gelen siparis satirlari uretime hazir yapilabilir.
