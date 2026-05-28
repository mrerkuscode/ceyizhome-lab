# 04 — Backup: Corel Referans Kütüphanesi Eklendi

## Sorun

`assets/references/corel_name_reference_library.json` — İsim Kesim üretim akışının kalbi (167+ referans). Bu dosya yedek listesinde DEĞİLDİ → operatör veri kaybı veya yanlış migration → kütüphane gider, geri dönüş yok.

Phase 2 17_veri_bakimi KRİT-1 olarak listelenmişti.

## Çözüm

`src/webui_backend/backup_api.py:12-30` `BACKUP_RELATIVE_FILES` listesine eklendi.

**Önce:**
```python
BACKUP_RELATIVE_FILES = [
    "data/name_cut_queue.json",
    ...
    "data/trendyol_extraction_learning_examples.json",
    "config/settings.yaml",
]
```

**Sonra:**
```python
BACKUP_RELATIVE_FILES = [
    "data/name_cut_queue.json",
    ...
    "data/trendyol_extraction_learning_examples.json",
    "assets/references/corel_name_reference_library.json",   # <-- YENİ
    "config/settings.yaml",
]
```

## Beraber gelen değişiklik

Aynı liste değişikliğinde **`data/trendyol_settings.json` çıkarıldı** (BUG-S2 — credential ifşası).

Net etki:
- −1 dosya (credential)
- +1 dosya (corel ref lib)
- Toplam backup boyutu ~aynı, güvenlik + veri güvenliği iyileşti.

## Test

```
=== smoke test ===
create_backup → status: OK, 15 files
  trendyol_settings.json in backup: False ✅  (önce True'ydu)
  corel ref lib in backup: True ✅           (önce dahil değildi)
```

Konum doğrulaması: gerçek dosya yolu `assets/references/corel_name_reference_library.json` (audit'in "backup_api.py:29" referansı satır numarasında bir kayma var, ama dosya tek ve doğru yere bağlandı).

## Restore davranışı

Restore tarafı kod değişmedi — backup'taki listedeki tüm dosyalar restore edilir. corel_name_reference_library.json bundan sonra otomatik backup + restore akışına dahil. Doğrulama: `validate_backup` SHA256 check yapıyor, JSON syntax check yapıyor → bozuk dosya engellenir.

## Backup

`output/2026-05-28/quick_wins_sprint/backups/backup_api.py.bak`
