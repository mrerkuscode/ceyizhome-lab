# 05 — DXF Library Entegrasyonu

## Bağlantı noktaları

Önceki sprintte kurulan DXF Kütüphane Sistemi (`output/2026-05-28/dxf_library_system/`) bu modülün üzerine inşa edildi:
- ASCII normalize: `to_ascii_name` doğrudan import edildi (kural birliği — ürün test_name ile DXF file_name aynı algoritmayla ASCII'ye dönüşür)
- Lookup: `find_library_entry(root, name)` çağrısı
- Boyut grupları: `SIZE_GROUPS = ["70x40", "80x40", "100x40"]` paylaşımlı

## Auto size_group hesaplaması

`size_group_for_letter_count(n)`:
- 1-5 harf → `70x40` (kısa isimler)
- 6-9 harf → `80x40` (orta)
- 10+ harf → `100x40` (uzun)

Test:
| İsim | Harf sayısı | Grup |
|---|---|---|
| Ada | 3 | 70x40 ✓ |
| Mücahit | 7 | 80x40 ✓ |
| Muhammed Ali | 11 (boşluk hariç sayılır) | 100x40 ✓ |

## `resolve_size_group(root, definition)`

Ürün tanımındaki size_group ve test_name'i kullanarak:
- `requested`: kullanıcının seçtiği (auto veya manuel grup)
- `effective`: gerçek kullanılacak (manuel → onu, auto → letter count'tan)
- `auto_group`: harf sayısına göre hesaplanan
- `letter_count`: test_name'in (veya product_name fallback) alfa karakter sayısı
- `dxf_status`: test_name kütüphanede var mı?

Eğer test_name boşsa `dxf_status.checked=False`.

## UI canlı önizleme

Ürün düzenleme modal'da test ismi inputu değiştikçe (`oninput`) `resolveProductSizeGroupPreview()` çağrılır → bridge'e payload gider → DXF preview kutusu güncellenir:

```
✓ Hesaplanan boyut: 70x40 (otomatik: 70x40, harf: 4)
✓ DXF kütüphane: ayse.dxf bulundu (70x40)
```

Veya:
```
✓ Hesaplanan boyut: 80x40 (otomatik: 80x40, harf: 7)
✗ DXF kütüphane: mucahit.dxf yok — Leyla bu ismi çizmeli
```

Eğer kütüphanedeki boyut grubu hesaplanan effective ile uyuşmuyorsa:
```
✓ DXF kütüphane: ayse.dxf bulundu (100x40) (uyumsuz boyut)
```

## Mimari akış

```
Operatör ürün düzenliyor
  ↓
Test ismi yazıyor: "Mücahit"
  ↓
oninput → bridge.productDefinitionResolveSizeGroup(payload)
  ↓
backend: normalize_definition → resolve_size_group →
  letter_count("Mücahit") = 7
  auto_group("70-80") = "80x40"
  to_ascii_name("Mücahit") = "mucahit"
  find_library_entry(root, "mucahit") → entry or None
  ↓
UI: yeşil ✓ veya kırmızı ✗ önizleme
```

## Test sonucu

```
SCENARIO 6: DXF library integration
  3-letter Ada:           effective=70x40  (exp 70x40)  ✓
  7-letter Mucahit:       effective=80x40  (exp 80x40)  ✓
  11-letter Muhammed Ali: effective=100x40 (exp 100x40) ✓
  DXF lookup Umit:        found=True       (exp True)   ✓ (kütüphanede umit.dxf var)
  DXF lookup X-Unknown:   found=False      (exp False)  ✓
```

## CLAUDE.md uyumu

- DXF library okunur, asla yazılmaz
- "Hızlı tanımla" rozetinden gelen deep-link operatöre formu önceden doldurur ama Kaydet manuel
- Bu modül DXF library'nin watcher veya scan davranışına dokunmaz; sadece read-only lookup yapar
