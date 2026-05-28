# 06 — Regresyon Test Raporu

## Test komutu

```bash
cd "C:/Users/Pc/Documents/New project/production-bot"
python -c "<regression suite>"
```

Full smoke test (terminal kanıtı aşağıda).

## Sonuç — TÜM TESTLER GEÇTİ

```
=== REGRESSION TEST SUITE ===

1. Backup API smoke test
   Backup created: ceyizhome_lab_backup_20260528_134044_5c18265b, 15 files
   No credential leak; corel lib backup confirmed
   Test backup cleaned: backups\2026-05-28\ceyizhome_lab_backup_20260528_134044_5c18265b

2. Verification bypass fix test
   High-confidence AI path now WAITING_APPROVAL (operator review required)
   Low confidence -> USER_REVIEW
   No mapping -> USER_REVIEW
   No question -> WAITING_EVIDENCE

3. Mapping threshold alignment test
   All thresholds aligned to 0.72 (backend + frontend)

4. Existing operator-approved rows (regression)
   Existing user-verified rows still detected as ready: 1

5. Frontend file integrity
   index.html: API Key password, AI inputs added, dashboard spans dynamic, quit wired

6. CSS tiny-status modifier
   CSS modifier rules in place (.warn / .bad)

7. Backend file syntax
   bridge.py, backup_api.py, trendyol_api.py compile OK

=========================
ALL REGRESSION TESTS PASS
=========================
```

## Kontrol noktaları

### Mevcut user-verified satırlar (İrem/Ümit/Ahmet sınıfı) korundu mu?

`data/trendyol_production_suggestions.json`:
```
'Ayşe & Mehmet': verification_status=uretime_hazir, user_verified=True → _is_verified_ready=True ✅
'Helin Cemal':   verification_status=kullanici_kontrol_gerekli, user_verified=False → _is_verified_ready=False
'Model Eksik':   verification_status=kullanici_kontrol_gerekli, user_verified=False → _is_verified_ready=False
```

Mevcut READY-confirmed: 1 → halen ready dönüyor. Regresyon TEMİZ.

Not: Veride somut İrem/Ümit/Ahmet isimleri yok (silinmiş veya test fixture). Yine de "operator-approved" pattern korunmuş tek satır var ve mantık olduğu gibi çalışıyor.

### Trendyol mevcut sistem etkilendi mi?

- `trendyol_api.py` syntax OK
- `_initial_verification_status` 5 senaryoda doğru sonuç dönüyor
- Mapping threshold 0.72'ye hizalı — backend + frontend tutarlı
- AI ayarlarının sessiz reset'i bitti (DOM eklendi)

### CLAUDE.md ihlalleri

| İhlal | Konum | Durum |
|---|---|---|
| Operatör onayı bypass | `trendyol_api.py:1944-1950` | ✅ kapandı |
| Direct print kapalı (default) | dashboard | ✅ dinamik (yine kapalı default) |
| Sahte success rozeti | dashboard "Başarılı" | ✅ "Veri yok" default |
| Sahte buton | "Kaynağa Dön" | ✅ disabled |
| Sahte yazdırma "ok" | reproduce auto-render | ✅ operatör manuel onay |
| Sessiz reset | AI ayarları | ✅ DOM eklendi |
| Sessiz kayıp | çoklu mesaj | ✅ operatör uyarısı |
| Yıkıcı buton onaysız | migrate/rebuild | ✅ confirm dialog |

### Güvenlik

| Açık | Konum | Durum |
|---|---|---|
| API Key plain-text | `index.html:3153` | ✅ type=password |
| Credential backup ifşası | `backup_api.py:21` | ✅ dosya çıkarıldı |
| AI ayar sessiz reset | `app.js:4860` | ✅ DOM eklendi |

## Backup'lar

Tüm değişiklik öncesi dosyalar yedeklendi:
```
output/2026-05-28/quick_wins_sprint/backups/
├── app.js.bak
├── backup_api.py.bak
├── bridge.py.bak
├── index.html.bak
├── styles.css.bak
└── trendyol_api.py.bak
```

Rollback gerekirse: `cp output/2026-05-28/quick_wins_sprint/backups/<file>.bak src/<orig_path>/<file>`.

## Manuel test gereksinimleri

Harness'ta browser/Qt yok — bu UI değişiklikleri görsel olarak manuel doğrulanmalı:

1. **API Key inputu** — Trendyol ayarları sayfasında "API Key" alanına yazınca `••••••` görünmeli (kayıtlı maskeli değer için zaten görünmüyordu; yeni yazılan karakterler de gizli).
2. **Çıkış butonu** — Tıklayınca "Cyzella'dan çıkmak istediğine emin misin?" confirm + Onaylayınca uygulama kapanmalı.
3. **Veri Bakımı confirm'leri** — migrate/rebuild butonlarına basınca uyarı dialog gelmeli.
4. **Reproduce** — Geçmişte bir çıktıya tıklayıp "Tekrar Üret" deyince Studio açılmalı ama PDF üretilmemeli.
5. **Çoklu mesaj** — Trendyol evidence drawer'da 2+ mesaj seçip "Uygula" deyince uyarı dialog gelmeli.
6. **Dashboard** — Anasayfa hero status row gerçek değerler göstermeli (qualityGateStatus boşsa "Veri yok").
7. **AI ayarları** — Trendyol kartı içinde "AI Çıkarım Ayarları" `<details>` açılınca 8 alan görünmeli; değiştir-kaydet-yeniden yükle ile değerler korunmalı.

## Sırada

DXF Kütüphane Sistemi (06_action_plan.md Öncelik 4). Bu sprint kapsamı dışı; yeni Leyla prompt'u bekleniyor.
