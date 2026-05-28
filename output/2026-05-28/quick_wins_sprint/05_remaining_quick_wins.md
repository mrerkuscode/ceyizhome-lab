# 05 — Kalan Quick Wins (07_quick_wins.md #5, #7, #9-14)

## QW #5 — Veri Bakımı yıkıcı confirm dialogları

**Konum:** `src/webui/app.js:746` `rebuildNameCutCorelReferenceIndex` + `src/webui/app.js:798` `migrateNameCutCorelReferenceLibrary`

**Sorun:** restore butonu confirm dialog'a sahipti ama rebuild ve migrate butonları doğrudan çalışıyordu. Yanlış tıklama → korel referans indeks veya kütüphane dosyası yerinde değişir.

**Çözüm:**

```js
// rebuildNameCutCorelReferenceIndex — eklenen guard
if (!confirm("Corel referans indeksini yeniden inşa etmek üzeresin. Mevcut indeks dosyaları üzerine yazılır (orijinal kütüphane verisi DOKUNULMAZ, sadece türetilmiş indeks). Devam edilsin mi?")) {
  return;
}

// migrateNameCutCorelReferenceLibrary — eklenen guard
if (!confirm("Corel referans kütüphanesi şema migration'ı çalıştırılacak. Yan etki: kütüphane JSON'u yerinde güncellenir. Geri alma için 'Backup Oluştur' ile snapshot al, ardından devam et. Devam edilsin mi?")) {
  return;
}
```

İki buton da artık operatöre yıkıcılık seviyesini açıkça söylüyor.

---

## QW #7 — Çıkış butonu

**Konum:** `src/webui/index.html:66` + `src/webui/app.js` + `src/webui_backend/bridge.py`

**Sorun:** "Çıkış Yap" butonu `showSystemNotice('Çıkış Yap')` çağırıyordu → rapor ekranına navigation, gerçek çıkış yok. Sahte buton.

**Çözüm:**

1. Bridge.py'ye yeni slot eklendi:
```python
@Slot(result=str)
def quitApplication(self) -> str:
    app = QApplication.instance()
    if app is None:
        return json.dumps({"status": "ERROR", "message": "Uygulama context'i bulunamadı."})
    app.quit()
    return json.dumps({"status": "OK", "message": "Çıkış sinyali gönderildi."})
```

2. Frontend wrapper `quitApplication()` eklendi. Confirm dialog → bridge çağrısı → bridge yoksa `window.close()` fallback.

3. Index.html buton bağlandı:
```html
<button class="nav-btn" onclick="quitApplication()" title="Çıkış Yap">...
```

---

## QW #9 + #10 — Yazıcı testi yanlış renk + CSS modifier

Detay: `03_fake_button_fixes.md` (yukarıdaki rapor).

Özet: testSelectedPrinterProfile artık `status` field'ına göre OK/UNSUPPORTED/ERROR tone seçiyor; CSS `.tiny-status.warn`/`.tiny-status.bad` kuralları eklendi.

---

## QW #11 — Dashboard hardcoded "Başarılı" / "Direct Print: Kapalı"

Detay: `03_fake_button_fixes.md`.

Özet: index.html'de 4 status satırına id eklendi; app.js'de updateHomeStats fonksiyonu bunları backend state'inden dolduruyor. Default fallback'lar dürüst ("Veri yok", "Kapalı", "Otomatik çalışmaz").

---

## QW #12 — AI ayarları frontend DOM (sessiz reset bitir)

**Konum:** `src/webui/index.html:3168` civarı + `src/webui/app.js:2843`

**Sorun:** `app.js:4895` save payload'ında `byId("trendyolAiEnabled")?.checked === true` çalışıyordu, ama index.html'de bu id YOKTU → `byId()` null → `null?.checked` undefined → `undefined === true` → false → her save'de `ai_enabled: false` sessizce.

**Çözüm:** Trendyol ayar kartına AI alt-bölüm eklendi (collapsible `<details>`):

```html
<details class="settings-subblock">
  <summary><b>AI Çıkarım Ayarları</b><span>Soru/mesajdan isim/tarih/not çıkarımı</span></summary>
  <div class="settings-form-grid compact">
    <label class="check"><input id="trendyolAiAutonomous" type="checkbox" /> AI otonom üretim önerisi aktif</label>
    <label class="check"><input id="trendyolAiEnabled" type="checkbox" /> Cloud AI çıkarım açık</label>
    <label>AI Provider <select id="trendyolAiProvider"><option value="openai_compatible">OpenAI uyumlu</option></select></label>
    <label>AI API Key<input id="trendyolAiApiKey" type="password" autocomplete="off" placeholder="Kayıtlıysa maskeli görünür" /></label>
    <label>Model<input id="trendyolAiModel" type="text" autocomplete="off" placeholder="gpt-5-nano" /></label>
    <label>Güven eşiği<input id="trendyolAiConfidenceThreshold" type="number" min="0" max="1" step="0.01" placeholder="0.85" /></label>
    <label>Timeout (sn)<input id="trendyolAiTimeoutSeconds" type="number" min="1" max="120" step="1" placeholder="20" /></label>
    <label class="check"><input id="trendyolAiCacheEnabled" type="checkbox" /> AI cache açık</label>
  </div>
  <p class="safe-note">AI önerileri operatör onayı olmadan üretime gitmez. Yüksek güvenli AI eşleşmeleri bile "operatör onayı bekliyor" statüsünde kalır.</p>
</details>
```

renderTrendyolSettings'e aiApiKey wiring eklendi:
```js
const aiApiKey = byId("trendyolAiApiKey");
...
if (aiApiKey && document.activeElement !== aiApiKey) aiApiKey.value = settings.ai_api_key || "";
```

Sessiz reset bitti — artık AI ayarları gerçekten render ediliyor ve kaydediliyor.

Önemli: API Key inputu **type="password"** (BUG-S1 gibi). AI API Key (OpenAI) Trendyol API Key kadar hassas.

---

## QW #13 — Reproduce auto-render kaldır

Detay: `03_fake_button_fixes.md`.

---

## QW #14 — Çoklu mesaj sessiz kayıp

Detay: `03_fake_button_fixes.md`.

---

## Atlanan / kapsam dışı

07_quick_wins.md #2 ("Kaynağa Dön") → Görev 3A ile aynı; tek değişiklik, çift sayım yok.

Hepsi 14/14 quick win tamamlandı.
