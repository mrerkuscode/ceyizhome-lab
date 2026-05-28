# 00a — VISUAL DASHBOARD (18 Menü Tek Bakışta)

**Tarih:** 2026-05-28

## Genel tablo
```
┌────┬──────────────────────────────┬────────┬───────────┬──────────┬──────────┐
│ #  │ Menü                          │ Skor   │ Buton (≈) │ Durum    │ Renk     │
├────┼──────────────────────────────┼────────┼───────────┼──────────┼──────────┤
│ 01 │ Ana Sayfa                     │ 3.75/5 │   ~10     │ Çoğu OK  │   🟡     │
│ 02 │ İsim Kesim                    │ 2.5/5  │   ~12     │ Çalışıyor│   🟣     │
│ 03 │ Etiket Studio                 │ 3.0/5  │    ~8     │ Sahte 2  │   🟡     │
│ 04 │ Toplu Üretim Studio           │ 3.0/5  │   ~10     │ Sahte 1  │   🟡     │
│ 05 │ Trendyol Siparişleri          │ 4.0/5  │   ~15     │ Güçlü    │   🟡⚠️   │
│ 06 │ Yazdırma Sırası               │ 3.0/5  │    ~9     │ Sahte 2  │   🟡     │
│ 07 │ Manuel Etiket                 │ 3.5/5  │    ~7     │ CSS bug  │   🟡     │
│ 08 │ Etiket Modelleri              │ 3.4/5  │   ~10     │ Sahte 1  │   🟡     │
│ 09 │ Kontrol Kuyruğu               │ 3.0/5  │    ~8     │ Hayalet  │   🟡     │
│ 10 │ Ürün Eşleştirme               │ 3.4/5  │   ~12     │ Eşik düşk│   🟡     │
│ 11 │ Kanıt Eşleştirme              │ 3.1/5  │   ~10     │ KRİTİK   │   🔴⚠️   │
│ 12 │ Üretim Geçmişi                │ 3.2/5  │    ~8     │ Sahte 2  │   🟡     │
│ 13 │ Etiket Çıktıları              │ 3.2/5  │    ~7     │ Sahte 1  │   🟡     │
│ 14 │ Genel Ayarlar                 │ 3.8/5  │   ~15     │ İYİ      │   🟢     │
│ 15 │ Trendyol API                  │ 3.0/5  │    ~8     │ Güv. 2   │   🟡⚠️   │
│ 16 │ Yazıcı Profilleri             │ 3.5/5  │    ~6     │ Default─ │   🟡     │
│ 17 │ Veri Bakımı                   │ 3.0/5  │    ~7     │ Backup❗ │   🟡     │
│ 18 │ Lab / Raporlar / Loglar       │ 3.3/5  │   ~10     │ Alt 3🔴  │   🟡/🔴  │
└────┴──────────────────────────────┴────────┴───────────┴──────────┴──────────┘
                                       18 sayfa ortalama: 3.3/5
```

## Buton durum tahmini (18 menü toplamı, ~160 buton)
```
✅ Çalışıyor (tam fonksiyon)        ████████████████████████████████░░░░░░░░  ~75% (~120)
⚠️ Kısmi (mesaj var aksiyon eksik)  ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ~10% (~16)
❌ Sahte (mock, hardcoded, no-op)    ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ~10% (~16)
🔵 Disabled / pasif                  █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ~3%  (~5)
❓ Belirsiz (kod var, çağrı yolu?)  █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ~2%  (~3)
```

## Renk dağılımı
```
🟢 DOKUNMAM           ▓▓▓▓▓                                          1 menü   (14)
🟡 DÜZELT             ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 14 menü   (01,03-13,15-17)
🔴 SİL/KAPAT alt      ▓▓▓                                            3 alt   (18: Design Lab, Çıkış, Loglar)
🟣 BÜYÜK DEĞİŞİM      ▓▓▓▓▓                                          1 menü   (02 — DXF geçişi)
```

## CLAUDE.md ihlal sıcaklık haritası (sahte başarı / otomatik onay)
```
KIRMIZI (KRİTİK):   11 Kanıt Eşleştirme  ████████████████████████ SYS-1 _initial_verification_status
TURUNCU (YÜKSEK):   13 Etiket Çıktıları  ████████████ SYS-2 fake "Doğrulandı" badge
                    12 Üretim Geçmişi    ████████████ SYS-4 reproduce auto-render
                    03 Etiket Studio     ████████████ Faz1 #6 sentToProduction bypass
SARI (ORTA):        04 Toplu Üretim      ████████ Faz1 #7 "Üretime Al" sahte
                    05 Trendyol          ████████ Faz1 #8 import alert
                    06 Yazdırma Sırası   ████████ Faz1 #3, #4 sahte butonlar
                    10 Ürün Eşleştirme   ████████ SYS-5 0.55 eşik
                    01 Ana Sayfa         ████████ SYS-3 hardcoded status
                    15 Trendyol API      ████████ SYS-6 AI sessiz reset
                    16 Yazıcı Profilleri ████████ SYS-7 hata yeşil
YEŞİL (TEMİZ):      14 Genel Ayarlar     ████ çift-kilit, ihlal yok
                    17 Veri Bakımı       ████ (Kritik veri kapsamı kalemi var ama sahte success değil)
                    07-09 etc.           ████ ihlal değil, sadece UI/UX/validation
```

## Güvenlik durum
```
✅ TEMİZ:  SQL injection (proje SQL kullanmıyor)
✅ TEMİZ:  Path traversal (PROJECT_ROOT guard)
✅ TEMİZ:  Direct print / lazer auto-start kapalı
✅ İYİ:    Backend credential maskeleme (trendyol_api.py)
✅ İYİ:    Log temizleyici (credential pattern silici)
🔴 ACİL:   API Key inputu plain-text (index.html:3153) → type="password"
🔴 ACİL:   Backup credential ifşası (backup_api.py:21) → çıkar veya şifrele
⚠️ ORTA:   AI ayarları sessiz reset (app.js:4860 + DOM eksik)
```

## Sonuç
- **Sistem ÇÖPE ATILMIYOR.** 14/18 menü düzeltilebilir; 1 menü stratejik geçiş (DXF); 1 menü temiz; 3 alt-ekran SİL.
- **En kritik öncelik:** Onay/Kanıt Bütünlüğü sprint'i (~15 saat) — İrem/Ümit krizinin tekrarını önler.
- **2 güvenlik bug'ı** 15 dakikada kapanır.
- **Detay:** her menü için `01_menu_details/NN_*.md`. Plan: `06_action_plan.md`. Hızlı: `07_quick_wins.md`.
