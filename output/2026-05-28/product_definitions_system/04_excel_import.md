# 04 — Excel Toplu Yükleme

## Beklenen format

Test dosyası: `proofs/test_products.xlsx` (Leyla'ya örnek olarak)

**Header satırı (1. satır, zorunlu sırasız):**

| SKU | ProductName | NameType | NameCount | LabelEnabled | LabelModel | LabelCount | SizeGroup | CompoundFormat | AdjustableInProduction | MinCount | MaxCount | ProductionNotes | TestName |

İlk 7 zorunlu; geri kalan 7 opsiyonel.

**Veri satırları (2..N):**

| TRY-001 | 10 kişilik söz çikolatası seti | couple | 1 | True | soz_3 | 10 | auto | joined | True | 5 | 20 | Standart kutu | Ayşe & Mehmet |
| TRY-002 | 5 kişilik mini set | couple | 1 | True | soz_3 | 5 | auto | joined | True | 3 | 10 | | Ayşe & Mehmet |
| TRY-005 | Sadece isim plakası | single | 1 | False | | 0 | auto | joined | False | 0 | 0 | İsim plakası, etiket yok | Mucahit |

## Akış

1. Operatör "Excel Yükle" butonuna basar
2. Modal açılır, dosya yolu inputu görünür
3. "Önizle (Dry-Run)" butonu → backend dosyayı okur, her satırı validate eder, **yazma yapmaz**, preview tablosu döner
4. Operatör hataları görür, isterse Excel'i düzelt + tekrar dry-run
5. "Yükle" butonu → gerçek import; başarılı satırlar upsert, hatalı satırlar errors listesine
6. Sonuç: `5 yeni, 0 güncel, 2 hata` mesajı + preview tablosu + hata detayları (collapsible details)

## Type coercion

Excel hücreleri Python tip karmaşası getirir. `normalize_definition` bunu temizler:
- "True", "true", "1", "evet", "yes" → True
- "False", "false", "0", "hayir", "no", "" → False
- "10", 10, 10.0 → 10 (int)
- NameType eksikse → "single" default
- count yerine "1.0" yazılmışsa → 1 (int coerce)

## Test sonucu

```
DRY-RUN:
  added=0, updated=0, errors=2
  row=7, sku='': SKU bos
  row=8, sku='TRY-006-BAD': Etiket aktif ise model secilmeli

Actual import:
  added=5, updated=0, errors=2
```

5 geçerli satır eklendi, 2 invalid satır (boş SKU + eksik label model) atlandı, hata listesi rapor edildi. **Sahte success yok** — hatalı satırlar atlanır, başarılı sayısı gerçek.

## Hata raporlama detayı

Her hata `{row: int, sku: str, error: str}` formatında. Backend errors[] listesi frontend'de:
- Üstte özet: "5 yeni, 0 güncel, 2 hata"
- Tablo: ilk 10 satırın durumu (YENİ / GÜNCEL / hata mesajı)
- Collapsible details: ilk 50 hatanın tam metni

## Sınırlamalar

- 50+ hata olursa yalnızca ilk 50'si UI'da gösterilir (raw errors[] backend'de tüm hatalar var)
- Excel okuma `data_only=True` modunda → formüller değerleriyle alınır, formül stringi okunmaz
- `read_only=True` → büyük dosyalar (10000+ satır) RAM-friendly
- Header sıralaması esnek (zorunlu kolonlar herhangi bir konumda olabilir)

## CLAUDE.md uyumu

- Dry-run varsayılan olarak önerilmez ama önce dry-run akışı UI'da net (iki ayrı buton)
- Sahte başarı yok: validation hatası varsa satır atlanır, `errors[]` raporlanır, başarılı sayısı gerçek
- Audit log her başarılı satıra `excel_import` action ile düşer
