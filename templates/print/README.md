# CorelDRAW Baskı Şablonları

Bu klasöre CorelDRAW baskı şablonları konur.

MVP sürümünde CorelDRAW otomatik açılmaz ve yazdırma yapılmaz. Sistem yalnızca temiz `print_data.csv`, `job_info.txt` ve rapor dosyaları hazırlar.

## Dosya Adlandırma

Şablon dosyası adı üretim Excel'indeki şu alanlarla eşleşmelidir:

- `model_no`
- `template_no`
- `label_variant`

Örnek:

```text
01_etiket_a_gold.cdr
01_etiket_a_silver.svg
01_etiket_a_none.pdf
```

Model klasörü kullanmak da mümkündür:

```text
templates/print/01/01_etiket_a_gold.cdr
```

Birden fazla dosya aynı model, şablon ve varyantla eşleşirse sistem siparişi üretime almaz ve `NEEDS_REVIEW` olarak `errors_report.csv` içine yazar.

## Label Variant

Geçerli varyant değerleri:

```text
GOLD
SILVER
WHITE
RED
CUSTOM
NONE
```

Eski `gold/gümüş` gibi kolonlar ana üretim formatı değildir. Bunlar ileride yalnızca legacy Excel dönüştürme/import aşamasında kullanılabilir.

## CorelDRAW Yer Tutucuları

CorelDRAW şablonlarında ileride kullanılacak önerilen yer tutucular:

```text
{{LABEL_TEXT}}
{{BUYER_NAME}}
{{ORDER_NO}}
{{DATE}}
```
