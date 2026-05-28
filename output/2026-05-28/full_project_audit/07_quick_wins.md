# 07 — Hızlı Kazanımlar (≤1 saat, yüksek etki, düşük risk)

Tek tek yapılabilir, biri diğerini bekletmez. Hepsi geri-alınabilir, üretimi durdurmaz.

## ⏱️ 5 DAKİKA
1. **API Key plain-text fix** → `index.html:3153` Trendyol API Key inputuna `type="password"` ekle. Güvenlik. (Konum: 04_security BUG-S1)
2. **"Kaynağa Dön" sahte buton** → `app.js:19070-19072` disabled yap (önce; gerçek navigation ileri iş). Audit Faz1 #4 + Phase 2 11_uretim_gecmisi BUL-11-C2 tekrar onayladı.
3. **Veri Bakımı: corel_name_reference_library.json'u backup'a ekle** → `backup_api.py:29` listeye tek satır. Phase 2 17_veri_bakimi KRİT-1. Veri kaybı önler.
4. **Veri Bakımı UI etiketi düzelt** → `index.html:3086` "İsim Kesim" yanıltıcı → gerçek kapsam yaz.

## ⏱️ 15 DAKİKA
5. **Veri Bakımı yıkıcı confirm** → `app.js:797 migrateNameCutCorelReferenceLibrary` + `app.js:745 rebuildNameCutCorelReferenceIndex` confirm dialog ekle (restore zaten var, bu ikisi yok). CLAUDE.md operatör onayı.
6. **"Güvenli öneri" eşik hizala** → `trendyol_api.py:460` 0.55→0.72; veya `app.js:3335` "kontrol gerekli" sınırını yükselt. Tutarlı, yanıltıcı değil.
7. **Çıkış butonu** → `index.html:65-66` `bridge.quit()` veya `window.close()` bağla; şu an `showSystemNotice` stub.

## ⏱️ 30 DAKİKA
8. **`_initial_verification_status` otomatik bypass** → `trendyol_api.py:1944-1950` → `VERIFICATION_WAITING_APPROVAL` döndür (CLAUDE.md ihlali; en kritik tek değişiklik). 
9. **Yazıcı testi yanlış renk** → `app.js:20606` `result.status !== "OK"` ile yeniden değerlendir. Hata yeşil görünmesin.
10. **`testSelectedPrinterProfile` CSS modifier** → `styles.css` `.tiny-status.warn/.bad` kuralları ekle. Görsel ayrım.
11. **Dashboard hardcoded "Direct Print: Kapalı" satırı dinamik yap** → `index.html:100-103` + `app.js:2371` qualityGateStatus key'i ekle.

## ⏱️ 1 SAAT
12. **AI ayarları frontend DOM ekle** → `index.html` Trendyol API kartına AI input'ları ekle (`trendyolAiEnabled`, `trendyolAiApiKey`, vb. — app.js:4860 bunları okuyor). Sessiz reset bitsin.
13. **Reproduce auto-render** → `app.js:17583-17586` `renderManual()` çağrısını kaldır, operatör Studio'da bizzat üretsin. CLAUDE.md operatör onayı.
14. **Çoklu mesaj sessiz kayıp** → `app.js:4652 applySelectedTrendyolDrawerMessages` döngüye al veya backend multi-id endpoint. UX dürüstlük.

## Toplam etki
- **14 hızlı kazanım** → toplam ~5-6 saat.
- **5 tanesi CLAUDE.md ihlali çözümü** (sahte başarı/onay bypass).
- **2 tanesi güvenlik** (#1, #5).
- **Risk:** hepsi DÜŞÜK (UI/data, üretim akışı bozmaz; her biri geri-alınabilir).

## Bu liste neden değerli
Phase 2 master'da Acil 20 sorun var (Phase 1 + Phase 2). Bunlar TAM çözüm 125-180 saat. **Bu 14 hızlı kazanım o eforun ilk %5'i ama en GÖRÜNÜR + RİSKLİ ihlalleri kapsıyor.** Bir öğleden sonra ile sistemin "sahte başarı görüntüsü" büyük ölçüde temizlenir, güvenlik açıkları kapatılır.
