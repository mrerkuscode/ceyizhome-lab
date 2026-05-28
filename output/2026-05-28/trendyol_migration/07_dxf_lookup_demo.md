# 07 — DXF Lookup End-to-End Demo

## Senaryo

Operatör perspektifi: Trendyol'dan yeni bir sipariş geldi, AI çıkarımı "Mücahit" ismi önerdi.

- **Başta:** DXF kütüphanede `mucahit.dxf` yok → sistem "Çiz Bekliyor" der
- **Operatör hamlesi:** Leyla CorelDRAW'da `mucahit` çizimi yapar, `assets/dxf_library/80x40/mucahit.dxf` olarak dışa aktarır
- **Sistem tepkisi:** Manuel scan (üretimde watcher otomatik tetikler) → kütüphane index güncellenir → sipariş artık 🟢 Çizim Hazır

## Test komutu

```bash
python output/2026-05-28/trendyol_migration/dxf_demo_runner.py
```

Script idempotent — tekrar çalıştırılırsa aynı sonucu döndürür ve cleanup'ı her seferinde yapar.

## Tam adım çıktısı

### STEP 1: pre-check — Mücahit kütüphanede yok
```
resolve_name_for_order("Mücahit")
→ status: MISSING_DESIGN
→ KANIT: assets/dxf_library/80x40/mucahit.dxf yok
```

### STEP 2: scene öncesi — missing-design + readyForCut=False
```
build_name_cut_production_scene(items=[{"name_text":"Mücahit",...}])
→ objects.repair_status: dxf_library_missing_design
→ paths.ready_for_cut: False
→ paths.repair_status: dxf_library_missing_design
```

### STEP 3: operator dosya yükledi
```
cp assets/dxf_library/70x40/umit.dxf → assets/dxf_library/80x40/mucahit.dxf
file_size: 111071 byte
```

(Test için var olan umit.dxf'i mucahit.dxf adıyla 80x40'a kopyaladık — gerçek Leyla akışında orijinal Mücahit DXF olur)

### STEP 4: manuel scan (üretimde watcher otomatik)
```
scan_library() →
  scanned: 3 (ayse, umit, mucahit)
  added: 1 (mucahit)
  updated: 2 (ayse, umit zaten vardı)
```

### STEP 5: post-scan — Mücahit bulundu
```
resolve_name_for_order("Mücahit")
→ status: FOUND
→ entry.size_group: 80x40
→ entry.bbox_mm: [10.907, 7.212]   (test DXF, üretim ölçeği değil)
```

### STEP 6: scene sonrası — override applied
```
build_name_cut_production_scene(...)
→ objects.repair_status: corel_reference_exact_override
→ objects.override_applied: True
→ paths.ready_for_cut: True ✅
→ pathData_length: 12561 chars (gerçek DXF geometrisi)
→ reference_path tail: [..., "80x40", "mucahit.dxf"]
```

**Pipeline çalıştı:**
- DXF library lookup: hit
- ezdxf SPLINE → polyline flattening: 12.5k chars SVG path data üretti
- combined_production_api `_corel_reference_override_payload`: source="dxf_library" payload döndü
- Item readyForCut=True olarak işaretlendi (operatör onayı hâlâ gereklı — `requiresOperatorReview=True` ek koruma)

### STEP 7: cleanup
```
rm assets/dxf_library/80x40/mucahit.dxf
scan_library() → scanned: 2 (mucahit kütüphaneden çıkarıldı)
resolve_name_for_order("Mücahit") → status: MISSING_DESIGN ✓ (başlangıç durumuna döndü)
```

## Sonuç matrisi

| Adım | Sonuç |
|---|---|
| 1 | MISSING_DESIGN ✅ |
| 2 | scene `dxf_library_missing_design` + readyForCut=False ✅ |
| 3 | Dosya yüklendi (111KB) ✅ |
| 4 | scan +1 added ✅ |
| 5 | FOUND ✅ |
| 6 | override + readyForCut=True + 12.5k chars pathData ✅ |
| 7 | cleanup → MISSING_DESIGN'a döndü ✅ |

**7/7 adım PASS — end-to-end pipeline gerçek dosya sistemi kullanılarak doğrulandı.**

## Sahte başarı yok

- ✅ Step 5'te `assertion: r5['status'] == 'FOUND'` — gerçek lookup sonucu
- ✅ Step 6'da `pathData_length > 0` — gerçek dosya'dan ezdxf ile geometri çıkarıldı (12561 chars)
- ✅ Step 6'da `reference_path` filesystem path'i — UI bunu görünür şekilde gösterir
- ✅ Step 7 cleanup — dosya gerçekten silindi, scan_library tekrar 2 entry buldu
- ✅ Test idempotent — birinci ve ikinci çalıştırma aynı sonucu döndürür

## CLAUDE.md uyumu

- Salt okuma + dosya kopyalama (test amaçlı); lazer/yazıcı tetiklenmedi
- `requiresOperatorReview=True` override payload'da set ediliyor → DXF kütüphanede bulunsa bile operatör onayı zorunlu
- Cleanup test sonrası kütüphane orijinal durumuna döndü (2 entry: ayse, umit — sprint öncesi)

## Kanıt dosyası

`output/2026-05-28/trendyol_migration/dxf_demo_steps.json` — her adımın JSON ölçümü, mimar için reproduce-edilebilir.

## Üretim akışında gerçek karşılığı

1. Trendyol sipariş geldi: AI çıkarımı "Mücahit" önerdi
2. Trendyol siparişler sayfasında o sipariş için:
   - 🟢 Tanımlı (eğer ürün tanımı varsa)
   - DXF library status: 🔴 Çiz Bekliyor (eğer Mücahit kütüphanede yoksa)
3. Leyla CorelDRAW'a geçer, Mücahit ismini Mochary fontuyla çizer
4. DXF dışa aktarır, `assets/dxf_library/80x40/mucahit.dxf` klasörüne sürükler
5. Watcher (varsa) 1s debounce sonrası otomatik scan tetikler
6. Sayfa yenilenince Trendyol sipariş kartında: 🟢 Çizim Hazır
7. Operatör "Üret" butonuna basar → readyForCut=True artık → manuel yazdırma + lazer onayıyla devam
