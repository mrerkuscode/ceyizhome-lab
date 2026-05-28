# Browser Mode Smoke Test Raporu

**Tarih:** 2026-05-28
**Hazırlayan:** Claude Chrome (browser automation)
**Test dosyası:** `tests/test_browser_smoke.py` (commit dc33750)

---

## ⚠️ ÖNEMLİ NOT — Çalıştırma Durumu

Bu smoke test scripti **yazıldı ve commit edildi**, ancak **henüz çalıştırılmadı**.

**Neden çalıştırılmadı:** Bu testlerin koşması için yerel makinede şu adımlar gerekiyor: (1) `pip install playwright` + `playwright install chromium`, (2) Flask sunucusunun `localhost:8000`'de arka planda başlatılması, (3) `pytest` ile yürütülmesi. Bu adımlar yerel kabuk (PowerShell/terminal) erişimi gerektirir. Claude Chrome yalnızca tarayıcı üzerinden çalışır ve yerel `localhost:8000` ortamına veya Windows kabuğuna erişemez. Bu nedenle gerçek bir PASS/FAIL sonucu **gözlemlenmedi** ve uydurulmadı.

**Sonuç çalıştırmasını kim yapmalı:** Leyla veya Code, aşağıdaki komutla testi yerel olarak çalıştırmalı:

```powershell
# 1. Playwright kurulumu (ilk sefer)
.venv\Scripts\pip.exe install playwright
.venv\Scripts\python.exe -m playwright install chromium

# 2. Flask sunucuyu arka planda başlat
Start-Job -ScriptBlock {
  cd "C:\Users\Pc\Documents\New project\production-bot"
  .venv\Scripts\python.exe -m src.server.flask_app
}
Start-Sleep -Seconds 4

# 3. Smoke testi çalıştır
.venv\Scripts\python.exe -m pytest tests\test_browser_smoke.py -v

# 4. Sunucuyu durdur
Get-Job | Stop-Job
Get-Job | Remove-Job
```

---

## Sonuç: PENDING (henüz çalıştırılmadı)

| Test | Beklenen | Gerçek Sonuç |
| ---- | -------- | ------------ |
| Ana sayfa yüklenir, hata yok | ✅ | ⏳ PENDING |
| Menü navigasyonu çalışır | ✅ | ⏳ PENDING |
| Raporlar KPI bandı | ✅ | ⏳ PENDING |
| /api/state cevap verir | ✅ | ⏳ PENDING |
| /api/metrics cevap verir | ✅ | ⏳ PENDING |

## Konsol Hataları (varsa):

Test çalıştırılmadığı için konsol hatası verisi yok. `test_main_page_loads_without_errors` testi `pageerror` ve `console.error` olaylarını yakalayıp `errors` listesinde toplar; çalıştırıldığında bu bölüm doldurulmalıdır.

## Test Kapsamı (yazılan 5 senaryo)

1. **test_main_page_loads_without_errors** — Ana sayfa `networkidle` ile yüklenir; `pageerror` ve `console.error` olayları toplanır; liste boş olmalı.
2. **test_navigation_menu_clickable** — `home`, `labelStudio`, `printQueue`, `reports` sayfalarına `[data-page]` selektörüyle tıklanır.
3. **test_reports_kpi_band_present** — Raporlar sayfasında `#metricsBand / .kpi-band / [data-component="kpi-band"]` varlığı kontrol edilir.
4. **test_api_state_endpoint_responds** — `GET /api/state` → HTTP 200 beklenir.
5. **test_api_metrics_endpoint_responds** — `GET /api/metrics` → HTTP 200 beklenir.

## Sonraki Adım

- ⏳ Yerel çalıştırma sonrası bu rapor gerçek PASS/FAIL sonuçlarıyla güncellenmeli.
- Beklenti: 5/5 PASS (Sprint 1+2+3 sonrası 61/61 birim testin geçtiği bilgisiyle uyumlu).
- Eğer KPI bandı selektörü (`#metricsBand` vb.) gerçek DOM'da farklıysa `test_reports_kpi_band_present` selektörü güncellenmeli.

---

> **Şeffaflık notu:** Bu rapordaki tüm PASS/FAIL hücreleri PENDING'dir çünkü test yerel ortamda yürütülmedi. Uydurma sonuç verilmedi.
