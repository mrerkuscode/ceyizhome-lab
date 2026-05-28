# 03 — Sahte Başarı Noktaları (Konum Listesi)

**Kaynak:** Phase 2 audit master (SYS-1..8 sistemik kalıbı) + Phase 1 #1,#3,#5,#6 + yeni bulgular. Bu, "onay/kanıt bütünlüğü krizi" başlığı altında (Phase 2 master §2).

## 🔴 ACİL (CLAUDE.md ihlali — İrem/Ümit sınıfı)

| # | Konum (dosya:satır) | Sahte ne | Doğru davranış |
|---|---|---|---|
| **SYS-1** | `trendyol_api.py:1944-1950` `_initial_verification_status()` | Cloud AI confidence ≥0.85 → satır `VERIFICATION_READY`+`user_verified=True` (operatör bypass) | `VERIFICATION_WAITING_APPROVAL`, operatör butonu beklesin |
| **SYS-2** | `app.js:2195` `outputValidationState()` + `label_api.py:83` | Geçmişe bağlı her çıktı "Doğrulandı"; backend tüm dosyaları `"status":"HAZIR"` | Gerçek QC sonucundan; default `check` |
| **SYS-3** | `app.js:2371` + `index.html:100-103` | Dashboard hep "Kalite: Başarılı" (backend key yok) + hardcoded "Direct Print: Kapalı" status satırı | Gerçek backend qualityGateStatus'tan |
| **SYS-4** | `app.js:17583-17586` `reproduceOutputFromHistory` | "Tekrar Üret" 350ms sonra `renderManual()` + `sentToProduction:true, userApproved:true` (onaysız üretim) | renderManual çağrısını kaldır; operatör Studio'da bizzat üret |
| **SYS-5** | `trendyol_api.py:460` + `app.js:3335` | 0.55 skorlu öneri "Güvenli öneri" + yeşil "Onayla" (otonom eşik 0.72) | Eşik hizala: 0.72 |
| **SYS-6** | `app.js:4860-4867` | `trendyolAiEnabled/ApiKey/...` byId() okuyor ama bu id'ler index.html'de YOK → her "Kaydet"te `ai_enabled:false` sessizce; "başarılı" mesajı | index.html'e input'ları ekle |
| **SYS-7** | `app.js:20606` `testSelectedPrinterProfile()` + `styles.css` `.tiny-status.warn/.bad` tanımsız | Yazıcı testi hatası YEŞİL "ok" görünüyor (hata=başarı görsel) | `if status!="OK"` ele al; CSS modifier ekle |
| **Faz1 #1** | `index.html:1681-1688` | İsim Kesim header "Tek parça: Geçti" STATİK | (DÜZELTİLDİ 2026-05-27 — dinamik) |
| **Faz1 #3** | `app.js:19673-19679` `prepare_manual_print` | Bridge yoksa "ok" callback (yazdırma başarılı denir, hiçbir şey olmaz) | Gerçek hata göster |
| **Faz1 #4** | `app.js:19070-19072` "Kaynağa Dön" | Sadece `alert()`, backend yok (sahte buton) | Disabled yap veya gerçek navigation |
| **Faz1 #5** | `app.js:10853-10855` Etiket Studio preflight | Bridge yoksa OK callback (preflight geçti denir) | Gerçek bridge yoksa fail |
| **Faz1 #6** | `app.js:10930` PDF/PNG render | `sentToProduction:true, userApproved:true` (operatör onayı bypass) | sentToProduction:false; operatör onay ayrı |
| **Faz1 #7** | `index.html:1873` Toplu Üretim "Üretime Al" | Sadece UI step değiştir, gerçek üretim yok (sahte buton) | Gerçek bulk üretim tetikle |

## 🟡 BU AY (önemli ama acil değil)
- Faz1 #8 Toplu Üretim Trendyol import alert yönlendirme (UX) → app.js:11281-11284 → doğrudan import.
- 06 Yazdırma Sırası: prepare_manual_print bridge yok → sahte ok (yukarıda).
- 11/12 Üretim Geçmişi: BUL-11-C2 "Kaynağa Dön" (Faz1 #4 ile aynı).
- 08 Kontrol Kuyruğu: imported satırlar worklist'te hayalet görev (app.js:2938).

## ✅ ÇÖZÜLENLER (bu oturumda)
- İsim Kesim "Tek parça: Geçti" statik → dinamik (2026-05-27).
- İsim Kesim "İsimler ayrı" statik → dinamik (2026-05-27).
- "Uygun değil" gereksiz şişen sayım → `reference_missing_generated_review_required` META eklendi, "İnceleme gerekli" chip (2026-05-27).
- Corpus gate aşırı-katı reject → geometrik sağlam single-piece için review-required'a downgrade (2026-05-27).
- Filled black render (CSS fill:none bug) → fill #020617 (2026-05-28).

## Toplam sayı
- Bilinen ACİL sahte başarı: **12-14** (yukarıdaki tablodan, bazıları çözüldü).
- Çözülen: 5 (bu oturumda).
- Kalan ACİL: **~9** (SYS-1..7 + Faz1 #3, #4, #5, #6, #7 — bazıları aynı kök).
