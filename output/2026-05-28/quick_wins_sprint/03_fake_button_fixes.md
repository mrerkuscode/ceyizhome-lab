# 03 — Sahte Buton + Sahte Success Düzeltmeleri

## 3A — "Kaynağa Dön" sahte buton

**Konum:** `src/webui/app.js:19083`

**Önce:**
```html
<button class="btn" title="Kaynak ekrana dönme bağlantısı sonraki fazda genişletilecek"
        onclick="alert('Kaynağa dönme bağlantısı bu kayıt tipi için henüz production backend'e bağlı değil.')">
  Kaynağa Dön
</button>
```
Operatör butona basar → sadece `alert()` pop-up → hiçbir aksiyon yok. Sahte buton.

**Sonra:**
```html
<button class="btn" disabled aria-disabled="true"
        title="Kaynak ekrana dönüş bağlantısı bu kayıt tipi için henüz production backend'e bağlı değil — sonraki fazda etkinleşecek">
  Kaynağa Dön
</button>
```
- Buton görsel olarak disabled (CSS varsayılan gri/cursor)
- Tooltip operatöre durumu açıklar
- A11y: aria-disabled

---

## 3B — "Güvenli öneri" eşik hizalama 0.55 → 0.72

**Konumlar:**
- `src/webui_backend/trendyol_api.py:454` (production_type → "label" sınırı)
- `src/webui_backend/trendyol_api.py:460` (suggestion_status → "suggested" sınırı)
- `src/webui/app.js:3336` (frontend needsReview eşiği)

**Sorun:** Backend 0.55 skor üstüne "label" suggestion atıyordu. Frontend `confidence < 0.55` ile aynı eşiği kullanıyordu. Ama trendyol_api.py'de otonom üretim için `AI_AUTONOMOUS_MODEL_THRESHOLD = 0.72` zaten geçerliydi. İki eşik tutarsız → 0.55-0.72 arası öneriler "Güvenli öneri" yeşil rozetiyle gösteriliyor ama otonom akışta düşüyor.

**Çözüm:** Tüm 3 noktayı 0.72'ye hizaladım:

```python
# trendyol_api.py:454
production_type = "label" if model and score >= 0.72 else "review"

# trendyol_api.py:460
suggestion_status = "suggested" if model and score >= 0.72 and production_type != "review" else "needs_review"
```

```js
// app.js:3336
const needsReview = row.status === "needs_review" || row.production_type === "review" || confidence < 0.72 || labelNeedsModel;
```

**Test:**
```
backend "score >= 0.72" occurrences: 2 ✅
frontend "confidence < 0.72" occurrences: 1 ✅
backend "score >= 0.55" occurrences: 0 (cleaned) ✅
```

---

## 3C — Veri Bakımı UI etiketi düzelt

**Konum:** `src/webui/index.html:3086`

**Önce:** `<span>Queue, audit, Trendyol cache, İsim Kesim, printer profiles, settings</span>`
- "İsim Kesim" yanıltıcı — İsim Kesim'in tüm verisi yedeklenmiyordu; sadece kuyruk + history
- Backup gerçek kapsamı opak

**Sonra:**
```html
<span>İsim Kesim kuyruğu/geçmişi, yazdırma kuyruğu, sipariş geçmişi/audit,
      Trendyol mapping/AI cache/sorular, Corel referans kütüphanesi,
      yazıcı profilleri, settings.yaml —
      Trendyol API credential'ları güvenlik için yedeklenmez</span>
```

Operatör artık backup'ın ne içerdiğini ve neyi DAHİL ETMEDİĞİNİ görüyor.

---

## QW #9 — Yazıcı testi yanlış renk

**Konum:** `src/webui/app.js:20638` `testSelectedPrinterProfile`

**Önce:**
```js
setPrinterProfileStatus(result.message || "...", result.status === "UNSUPPORTED" ? "warn" : "ok");
```
`status="ERROR"` → tone="ok" → kırmızı hata mesajı yeşil görünüyor.

**Sonra:**
```js
let tone;
if (result.status === "OK") {
  tone = "ok";
} else if (result.status === "UNSUPPORTED") {
  tone = "warn";
} else {
  tone = "bad";  // ERROR vs.
}
setPrinterProfileStatus(result.message || (result.status === "OK" ? "Test başarılı." : "Test başarısız."), tone);
```

CSS modifier desteği eklendi → `.tiny-status.bad` artık kırmızı görünüyor.

---

## QW #10 — `.tiny-status.warn/.bad` CSS modifier

**Konum:** `src/webui/styles.css:6722`

**Önce:** `.tiny-status` her zaman `color: var(--green)` — uyarı veya hata için sınıf eklenebilir ama renk değişmiyordu (kural yok).

**Sonra:**
```css
.tiny-status { min-height: 18px; color: var(--green); font-size: 12px; font-weight: 800; }
.tiny-status.ok { color: var(--green); }
.tiny-status.warn { color: var(--amber, #d97706); }
.tiny-status.bad { color: var(--red, #dc2626); }
```

QW #9 ile birlikte: yazıcı testi hatası artık kırmızı görünür.

---

## QW #11 — Dashboard hardcoded "Direct Print: Kapalı" + "Başarılı"

**Konumlar:** `src/webui/index.html:99-104` + `src/webui/app.js:2399`

**Önce (index.html):**
```html
<span><b>Güvenli Mod:</b> Aktif</span>
<span><b>Direct Print:</b> Kapalı</span>
<span><b>Son kalite kontrol:</b> Başarılı</span>
<span><b>Yazıcı:</b> Otomatik çalışmaz</span>
```
- Statik metin. Backend ne olursa olsun "Başarılı" diyordu.
- `homeQualityStatus` id'si vardı ama HTML'de span'a sarılmamıştı; ayrıca diğer 3 satır id'siz.

**Sonra (index.html):**
```html
<span><b>Güvenli Mod:</b> <span id="homeSafetyModeStatus">Aktif</span></span>
<span><b>Direct Print:</b> <span id="homeDirectPrintStatus">Kapalı</span></span>
<span><b>Son kalite kontrol:</b> <span id="homeQualityStatusInline">—</span></span>
<span><b>Yazıcı:</b> <span id="homePrinterAutoStatus">Otomatik çalışmaz</span></span>
```

**Sonra (app.js:2399 yakın):**
```js
const qualityStatus = state.qualityGateStatus || state.lastQualityGateStatus || "Veri yok";
setText("homeQualityStatus", qualityStatus);
setText("homeQualityStatusInline", qualityStatus);
setText("homeSafetyModeStatus", state.safetyMode === false ? "Pasif" : "Aktif");
const directPrintOn = state.directPrintEnabled === true;
setText("homeDirectPrintStatus", directPrintOn ? "Açık (DİKKAT)" : "Kapalı");
setText("homePrinterAutoStatus", state.autoPrintStarted === true ? "Otomatik çalışıyor (DİKKAT)" : "Otomatik çalışmaz");
```

**Davranış:**
- Backend `qualityGateStatus` boş → "Veri yok" (önceki "Başarılı" sahte success kaldırıldı).
- Backend hiç direct print expose etmezse default "Kapalı" (CLAUDE.md garantisi).
- Backend `directPrintEnabled=true` set ederse → "Açık (DİKKAT)" gözüyle uyarı.

---

## QW #13 — Reproduce auto-render kaldır

**Konum:** `src/webui/app.js:17623` `reproduceOutputFromHistory`

**Önce:**
```js
openOutputHistoryInStudio(path);
window.setTimeout(() => {
  showLabelOutputStatus("...", "ok");
  renderManual();  // <-- 350ms sonra otomatik render
}, 350);
```
Geçmişten çıktı seçildiğinde, Studio açılıp 350ms sonra otomatik render başlıyor. Operatör onay vermeden PDF/PNG üretiliyor. CLAUDE.md ihlali (sentToProduction:true, userApproved:true downstream).

**Sonra:**
```js
openOutputHistoryInStudio(path);
showLabelOutputStatus(
  "Geçmiş bilgiler Studio'ya alındı. PDF/PNG üretmek için Studio'da 'Üret' butonuna basın (operatör onayı gerekli).",
  "ok"
);
```

Geçmiş veriler Studio'ya yüklenir, operatör manuel olarak "Üret"e basar. Operatör onayı geri geldi.

---

## QW #14 — Çoklu mesaj sessiz kayıp

**Konum:** `src/webui/app.js:4682` `applySelectedTrendyolDrawerMessages`

**Önce:**
```js
const ids = Array.from(trendyolEvidenceDrawerState.selectedIds || []);
if (!ids.length) {
  showTrendyolStatus("Önce en az bir müşteri mesajı seçin.", "warn");
  return;
}
applyTrendyolQuestionToSuggestion(rowId, ids[0]);  // <-- sadece ilki
closeTrendyolEvidenceDrawer();
```
Operatör 3 mesaj seçer → sadece 1'i uygulanır → diğer 2 sessiz kayıp. Operatör hiç fark etmez.

**Sonra:**
```js
if (ids.length > 1) {
  if (!confirm(`Şu an bir siparişe yalnızca tek müşteri mesajı kanıt olarak bağlanabiliyor. ${ids.length} mesaj seçtin; sadece ilki uygulanacak ve diğerleri YOK SAYILACAK. Devam etmek istiyor musun?`)) {
    return;
  }
  showTrendyolStatus(`${ids.length} mesaj seçildi; yalnızca ilki uygulandı, geri kalan ${ids.length - 1} mesaj ihmal edildi.`, "warn");
}
applyTrendyolQuestionToSuggestion(rowId, ids[0]);
closeTrendyolEvidenceDrawer();
```

Operatör açıkça uyarılır + onaylar + sonuç şeffaf. Backend multi-id endpoint eklenirse buradan upgrade kolay.
