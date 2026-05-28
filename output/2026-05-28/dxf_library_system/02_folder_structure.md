# 02 — Klasör Yapısı + ASCII Naming

## Klasör hiyerarşisi

```
assets/dxf_library/
├── 70x40/    # 3-5 harf, ~322 isim hedef (small)
├── 80x40/    # 6-9 harf, ~174 isim hedef (medium)
└── 100x40/   # 10+ harf, ~7 isim hedef (large)
```

Klasörler oluşturuldu. Leyla bu klasörlere ASCII-isimli DXF dosyaları atacak.

## Dosya adı kuralı

**Yalnızca:** `[a-z0-9_]+\.dxf`

- Küçük harf
- Rakam serbest
- Boşluk → alt çizgi
- Türkçe karakter yasak (sistem reddeder, uyarı verir)

**Mapping** (`to_ascii_name`):
| Girdi | Çıktı |
|---|---|
| `Mücahit` | `mucahit` |
| `Çağrı` | `cagri` |
| `Ümit` | `umit` |
| `Şükran` | `sukran` |
| `İlkay` | `ilkay` |
| `Ayşe & Mehmet` | `ayse_mehmet` |
| `Yusuf Kerem` | `yusuf_kerem` |
| `D'Andre` | `dandre` |
| `Ahmet 2` | `ahmet_2` |
| `İrem` | `irem` |
| `Sümeyye` | `sumeyye` |
| `Çağrı-Han` | `cagri_han` |

Kurallar:
1. Türkçe harf mapping (ç→c, ğ→g, ı→i, İ→i, ö→o, ş→s, ü→u)
2. NFKD ile diğer diakritikler atılır
3. Apostrof-family stripped (`'` `` ` `` `’` `´`) — `D'Andre` → `dandre` (alt çizgi YOK)
4. Geri kalan alfanumerik dışı karakter → alt çizgi
5. Ardışık alt çizgiler tek alt çizgiye, baş/son alt çizgi atılır

**Yasak girdi:**
- Boş veya sadece punctuation → `to_ascii_name("__")` → "" (lookup MISSING_DESIGN döner)
- Türkçe karakterli filename: `ayşe.dxf` → scan reddeder, uyarı verir, kütüphaneye eklemez

## Türkçe display map

`data/dxf_library_ascii_to_turkish.json` — ASCII'den UI'da gösterilen "güzel" Türkçe isme dönüş:

```json
{
  "umit": "Ümit",
  "mucahit": "Mücahit",
  "cagri": "Çağrı",
  "ayse_mehmet": "Ayşe & Mehmet",
  ...
}
```

19 isim seed edildi. Operatör yeni isim eklediğinde bu dosyaya da entry düşürebilir; yoksa display ASCII versiyonunu gösterir (fallback).

## Boyut grubu tolerans tablosu

Sistem bbox'ı mm cinsinden hesaplar ve aşağıdaki aralığa uymazsa "uyarı" verir, ama yine de kabul eder (folder name = source of truth):

| Grup | Genişlik | Yükseklik |
|---|---|---|
| 70x40 | 60-80 mm | 30-50 mm |
| 80x40 | 70-90 mm | 30-50 mm |
| 100x40 | 90-110 mm | 30-50 mm |

Tolerans bant ±10mm, çünkü Leyla'nın el çizimleri ufak varyasyonlar gösterebilir.

## Test çıktıları

```
seed: assets/dxf_library/70x40/{ayşe.dxf, ayse.dxf, umit.dxf}

scan:
  2 kayıt indexlendi
  warning 1: 'ayşe.dxf' — dosya adı ASCII değil (operator yeniden adlandırmalı)
  warning 2: 'umit.dxf' — bbox 10.9×7.2mm '70x40' grup aralığına uymuyor (test dosyası)
  ayse.dxf: bbox 70.0×40.0mm — DOĞRU production size ✅
```
