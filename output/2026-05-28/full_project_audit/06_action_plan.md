# 06 — Aksiyon Planı (Önceliklendirilmiş)

**Kaynak:** Phase 2 master "En Acil 20" + bu audit cross-cutting + Leyla'nın yeni DXF-kütüphane vizyonu.

## 🔴 ÖNCELİK 1 — BU HAFTA (CLAUDE.md ihlalleri — KRİTİK)
Sahte başarı / otomatik onay bypass — İrem/Ümit krizinin tekrarını önler.

| # | İş | Konum | Süre | Risk |
|---|---|---|---|---|
| 1 | `_initial_verification_status` otomatik onay bypass | trendyol_api.py:1944-1950 | 30 dk | Düşük |
| 2 | Reproduce auto-render (renderManual çağrısını kaldır) | app.js:17583-17586 | 1 sa | Düşük |
| 3 | Fake "Doğrulandı" rozeti + backend "HAZIR" default | app.js:2195 + label_api.py:83 | 2-3 sa | Orta |
| 4 | Dashboard kalıcı "Başarılı" + hardcoded status satırı | app.js:2371 + index.html:100-103 | 45 dk | Düşük |
| 5 | "Güvenli öneri" eşik hizalama 0.55→0.72 | trendyol_api.py:460 / app.js:3335 | 30 dk | Düşük |
| 6 | AI ayarları frontend DOM ekle (sessiz reset bitsin) | app.js:4860-4867 / index.html | 2 sa | Düşük |
| 7 | "Kaynağa Dön" sahte buton disable veya gerçek navigation | app.js:19070-19072 | 10 dk | Düşük |
| 8 | Etiket Studio PDF/PNG render sentToProduction:true | app.js:10930 | 1 sa | Orta |
| 9 | Etiket Studio + Print Queue preflight bridge-yok yolu | app.js:10853 + 19673 | 1 sa | Düşük |
| 10 | Toplu Üretim "Üretime Al" gerçek aksiyon | index.html:1873 | 2-4 sa | Orta |

**ALT-TOPLAM:** ~15 saat (Öncelik 1 = "onay/kanıt bütünlüğü sprint'i"). Tek sprint olarak yapılırsa İrem/Ümit sınıfı sahte-pass'ler büyük ölçüde temizlenir.

## 🟠 ÖNCELİK 2 — BU HAFTA (Güvenlik)
| # | İş | Konum | Süre |
|---|---|---|---|
| 1 | API Key inputu type="password" | index.html:3153 | 5 dk |
| 2 | Credential backup düz metin ifşası | backup_api.py:21 | 10 dk (çıkar) veya 1-2 sa (şifrele) |

**ALT-TOPLAM:** 15 dk - 2 sa.

## 🟡 ÖNCELİK 3 — BU AY (sahte buton + UX + veri bütünlüğü)
| # | İş | Konum | Süre |
|---|---|---|---|
| 1 | Veri Bakımı: corel_name_reference_library.json'u genel backup listesine ekle + etiket düzelt | backup_api.py:29 + index.html:3086 | 15 dk |
| 2 | Veri Bakımı: migrate/rebuild yıkıcı butonlar confirm ekle | app.js:745/797 | 30 dk |
| 3 | Kontrol Kuyruğu: imported satırlar worklist'ten dışla + badge guard | app.js:2938 + 2773 | 45 dk |
| 4 | name_cut mapping model doğrulaması | app.js:5086 + trendyol_api.py:1028 | 1 sa |
| 5 | Yazıcı Profilleri: test status "ok" yanlış renk + tiny-status CSS modifier | app.js:20606 + styles.css | 45 dk |
| 6 | Yazıcı Profilleri: printer_profiles.json default oluştur | data init | 30 dk |
| 7 | Kanıt Eşleştirme: çoklu mesaj sessiz kayıp | app.js:4652 | 1 sa |
| 8 | Çıkış butonu gerçek `bridge.quit()` | index.html:65-66 + bridge | 30 dk |

**ALT-TOPLAM:** ~5-7 saat.

## 🟣 ÖNCELİK 4 — STRATEJİK (Leyla'nın yeni vizyonu: DXF kütüphane sistemi)
| # | İş | Süre |
|---|---|---|
| 1 | `corel_reference_importer.py` SPLINE desteği ekle (Cox-de Boor; bugün fizibil bulundu) | 4-6 sa |
| 2 | DXF kütüphane upload UI (Veri Bakımı altında) | 3-4 sa |
| 3 | Bulk Trendyol → kütüphane lookup → eşleşmeyenler için review | 2-3 sa |
| 4 | 500 isim importer (Leyla Corel'de hazırlar, sistem batch yükler) | 1-2 sa import + Leyla hazırlığı |
| 5 | İsim Kesim jeneratif yol → fallback (default OFF, kütüphane miss durumunda) | 2 sa |
| 6 | DXF tek-path export tutarlılık doğrulaması (welded support_line iken çift `<line>` bastır) | 1 sa |

**ALT-TOPLAM:** ~13-18 saat (Leyla DXF hazırlığı hariç).

## 🟢 ÖNCELİK 5 — TEMİZLİK (uzun vadeli)
| # | İş | Süre |
|---|---|---|
| 1 | `legacy_converter.py` + `desktop/main_window.py` kullanım analizi + temizlik | 2 sa |
| 2 | "AI" yanıltıcı isimlendirme koordineli rename (frontend+backend) | 3-4 sa |
| 3 | Bridge/support_line/contour eski algoritmalar kaldır (DXF geçişi sonrası) | 2-3 sa |
| 4 | Design Lab "üretime aktar" sahte/mock butonlar (nav'da "deneysel" uyarısı) | 1 sa |
| 5 | Loglar nav butonu → gerçek log paneli veya stub'ı kaldır | 2 sa |
| 6 | app.js (20k satır) modüler refactor — uzun vade | 30+ sa (ayrı proje) |

**ALT-TOPLAM:** 10-15 saat + uzun-vade refactor.

## GENEL TOPLAM
- **Öncelik 1+2 (bu hafta):** 17-20 saat → CLAUDE.md ihlalleri + güvenlik bitti.
- **Öncelik 3 (bu ay):** 5-7 saat → UX + veri bütünlüğü.
- **Öncelik 4 (stratejik):** 13-18 saat → DXF kütüphane sistemine geçiş.
- **Öncelik 5 (sonra):** 10-15 saat → temizlik.

**GRAND TOTAL:** ~45-60 saat odaklı iş (Phase 2 master'ın 125-180 saat'lik tüm 18 sayfa eforu daha geniş; bu plan en kritik %30'una odaklanmış).

## Önerilen sıralama (Leyla için)
1. **Bugün-Yarın:** 🟠 Öncelik 2 (güvenlik — 15 dk - 2 sa) + 🔴 Öncelik 1 ilk 5 madde (sahte success'ler — 5-7 sa).
2. **Bu hafta:** 🔴 Öncelik 1 kalanı + 🟡 Öncelik 3 ilk yarısı.
3. **Önümüzdeki hafta:** 🟣 Öncelik 4 başlangıç (DXF SPLINE + upload UI).
4. **Bu ay:** Öncelik 4 tamamla + 🟢 Öncelik 5 başlat.
