# 01 — Güvenlik Düzeltmeleri

## BUG-S1 — API Key plain-text input

**Konum:** `src/webui/index.html:3153`
**Risk:** Orta (ekran paylaşımı, screenshot, omuz okuma)

**Önce:**
```html
<label>API Key<input id="trendyolApiKey" autocomplete="off" placeholder="..." /></label>
```
Tarayıcı `type` attribute olmadan default `text` varsayar → API key ekranda açık görünür.

**Sonra:**
```html
<label>API Key<input id="trendyolApiKey" type="password" autocomplete="off" placeholder="..." /></label>
```

**Test:** Visual smoke — input artık `••••••` gösterir. (Manuel görsel test gerekir; harness'ta browser yok.)

---

## BUG-S2 — Credential backup ifşası

**Konum:** `src/webui_backend/backup_api.py:12-30` (`BACKUP_RELATIVE_FILES`)
**Risk:** Yüksek (operatör backup'ı paylaşırsa credential ifşa olur)

**Sorun:** `data/trendyol_settings.json` backup listesindeydi. Bu dosya plain-text:
- `api_key` (Trendyol)
- `api_secret` (Trendyol)
- `ai_api_key` (OpenAI uyumlu cloud AI)

Operatör "Yedek Oluştur" → backup klasörü → dosya teknik servise iletilir → credential 3. tarafa açık.

**Çözüm:** Dosyayı backup listesinden çıkardım. Açıklayıcı comment eklendi:

```python
# NOTE: data/trendyol_settings.json INTENTIONALLY excluded.
# Contains api_key / api_secret / ai_api_key in plain text; backups can be
# shared off-machine (support, cloud sync) which would leak credentials.
# Operators must re-enter Trendyol credentials after a restore.
```

**Trade-off:** Restore sonrası operatör credential'ı tekrar girmek zorunda. Settings.yaml hala backup'ta, yani genel uygulama ayarları korunur. Trendyol-spesifik diğer dosyalar (mappings, suggestions, AI cache) korunur — yalnızca credential dosyası yedeklenmez.

**Test:**
```
python regression suite
→ backup_create → 15 files OK
→ trendyol_settings.json in backup: False ✅
→ no credential leak ✅
```

**Backup:** `output/2026-05-28/quick_wins_sprint/backups/backup_api.py.bak`

---

## BUG-S3 — AI ayarları frontend DOM eksik (sessiz reset)

**Konum:** `src/webui/index.html` (eski hali)
**Risk:** Orta (UX + güvenlik konfigürasyon yanlış anlaşılması)

Bu da bu sprintte çözüldü → bkz. `05_remaining_quick_wins.md` QW #12.
