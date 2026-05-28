# CeyizHome Lab — Local Startup Raporu
**Tarih:** 2026-05-28  
**Ortam:** Windows 11, production-bot/ klasörü

---

## ANA DOSYA

**Giriş noktası:** `src.desktop.app` (Python modülü)  
**Çalıştırma komutu:** `.venv\Scripts\python.exe -m src.desktop.app`  
**Launcher bat:** `start_app.bat` (aynı komutu çalıştırır)

`run_desktop.bat` → eski fallback (`src.desktop.fallback_app`) — kullanılmadı.

---

## KEŞIF BULGULARI

| Öğe | Durum |
|---|---|
| `.venv/` sanal ortamı | **VAR** — önceden kurulmuş |
| `requirements.txt` | **VAR** |
| `src/desktop/app.py` | **VAR** (ana giriş noktası) |
| `start_app.bat` | **VAR** (başlatma scripti) |
| `README.md` | **VAR** |

---

## BAĞIMLILIKLAR

Tüm kritik paketler `.venv/` içinde kurulu — `pip install` gerekmedi:

| Paket | Versiyon |
|---|---|
| PySide6 | 6.11.0 |
| PySide6_Addons | 6.11.0 |
| PySide6_Essentials | 6.11.0 |
| pandas | 3.0.2 |
| openpyxl | 3.1.5 |
| fonttools | 4.62.1 |
| uharfbuzz | 0.54.1 |

---

## SONUÇ: BAŞARILI

Uygulama açıldı ve tam çalışır durumda.

**Görülen ekran:** `CeyizHome Lab — İsim Kesim` modülü  
**Pencere başlığı:** `CeyizHome Lab`  
**Süreç:** Ana python (PID 13412) + uygulama penceresi (PID 31104) + QtWebEngineProcess (PID 19792)

**Görünen UI öğeleri:**
- Üst toolbar: Yeni, Aç, Kaydet, Farklı Kaydet, Manuel İsim, Excel → Toplu, Yapıştır
- Çalışma Alanı: 800.00 mm × 600.00 mm
- DXF bilgi satırı: 2/2 parçaya izin, 2/5 yerleşme adeti, Plaka 1/1, Sıkışma %, Hedef ölçü
- Sol araç çubuğu simgeleri mevcut (kalem, seçim, vs.)

**Hata logu:** Temiz (stderr çıktısı yok)

**Ekran görüntüsü:** `output/2026-05-28/local_run/screenshot_first_open.png`

---

## BUNDAN SONRA LEYLA NASIL ÇALIŞTIRACAK

**Yöntem 1 — Bat dosyası (önerilen, çift tıkla):**
```
production-bot\start_app.bat
```

**Yöntem 2 — Terminal komutu:**
```
cd "C:\Users\Pc\Documents\New project\production-bot"
.venv\Scripts\python.exe -m src.desktop.app
```

İlk açılışta 5-10 saniye bekleme normaldır (QtWebEngine yükleniyor).
