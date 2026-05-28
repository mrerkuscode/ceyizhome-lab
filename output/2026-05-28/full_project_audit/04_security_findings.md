# 04 — Güvenlik Bulguları

**Kaynak:** Phase 2 audit 15_diger_ayarlar + fresh grep + trendyol_api.py inceleme.

## ✅ İYİ (backend credential maskeleme — gerçek)
- `trendyol_api.py:123-126`: API key/secret/AI key **mask'leniyor display öncesi**.
- `trendyol_api.py:153-154`: payload masked-marker ise mevcut değeri koruyor (overwrite yok).
- `trendyol_api.py:2179`: Basic Auth base64 encoding üretim sırasında, log'a sızmıyor.
- `trendyol_api.py:2256`: log temizleyici (`re.sub(r"apiSecret|apiKey|api_secret|api_key", "secret", ...)`) — log'tan credential temizleniyor.

## 🔴 ACİL (güvenlik açıkları)

### BUG-S1 — API Key inputu plain-text (UI sızıntı riski)
- **Konum:** `index.html:3153` Trendyol API Key inputu `type` attribute eksik → tarayıcı `type="text"` varsayar → key ekranda açık görünür.
- **API Secret** ise `type="password"` (satır 3154) doğru. İkisi de eşit hassas; tutarsız.
- **Risk:** Orta (ekran paylaşımı, screenshot, omuz okuma).
- **Düzeltme:** `type="password"` ekle (5 dk).

### BUG-S2 — Credential'lar genel backup'a düz metin dahil
- **Konum:** `backup_api.py:21` `BACKUP_RELATIVE_FILES` listesinde `trendyol_settings.json` var (Phase 2 15_diger_ayarlar BUG-03).
- Bu dosya `api_key`, `api_secret`, `ai_api_key` düz JSON olarak içeriyor.
- "Yedek Oluştur" butonu → tüm credential'lar backup'ta düz metin → paylaşılan/buluta atılan backup ifşa eder.
- **Risk:** Yüksek (operatör backup'ı destek/teknik servise gönderirse credential ifşa olur).
- **Düzeltme:** Ya `trendyol_settings.json`'u backup'tan çıkar (10 dk), ya da credential alanlarını backup'ta mask'le/şifrele (1-2 saat).

### BUG-S3 — AI ayarları frontend'de DOM yok (sessiz reset + güvenlik tarafı)
- **Konum:** `app.js:4860-4867` AI input'ları byId ile okunuyor; index.html'de bu id'ler **yok**.
- Her "Kaydet" → `ai_api_key:""` sessizce gönderiliyor.
- **Güvenlik tarafı:** operatör API key set ettiğini sansa da kayıtlı değil. Ayrıca farkındalık sıfır → operatör "kapalı" sanır ama kayıt boş.
- **Risk:** Orta (UX + güvenlik konfigürasyon yanlış anlaşılması).

## 🟡 ORTA RİSK

- **App.js:2816-2817:** `apiKey.value = settings.api_key || ""` — backend masked döndüyse OK; backend mask'i atlamış olursa açık görünür. Backend tarafından korunuyor (trendyol_api.py mask logic). Frontend trust on backend = doğru pattern, ama backend mask bug'ı olursa frontend ekrana yazar. Düşük risk şu an.

## ✅ İYİ pattern'ler (incelendi, doğru)
- SQL injection: proje SQL kullanmıyor (JSON dosya tabanlı) → SQL injection riski yok.
- Path traversal: dosya yolları `PROJECT_ROOT`'a göre kontrol ediliyor (örn. `restore_corel_reference_backup` 4227: `target.parent.resolve() != COREL_REFERENCE_BACKUP_DIR.resolve()` → güvenli klasör dışı reddi).
- direct print + lazer auto-start kapalı (CLAUDE.md pozitifi, Phase 2 doğruladı).

## Toplam
- **ACİL: 2** (BUG-S1 plain-text input, BUG-S2 backup credential ifşa).
- **ORTA: 1** (BUG-S3 sessiz reset).
- **TEMİZ:** backend credential maskeleme, log temizleme, SQL/path traversal yok.

## Tahmini düzeltme süresi
- BUG-S1: 5 dk
- BUG-S2: 10 dk (basit çıkar) veya 1-2 saat (şifrele)
- BUG-S3: 1-2 saat (frontend DOM ekle)
- **Toplam:** ~3 saat (basit) veya 5 saat (kapsamlı).
