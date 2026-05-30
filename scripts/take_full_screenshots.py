"""
Tüm proje sayfalarını ve sekmelerini tarayan Playwright scripti.
Output: output/2026-05-29/full_screenshots/
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("output/2026-05-29/full_screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://localhost:8000"
VIEWPORT = {"width": 1920, "height": 1080}

# (dosya_adi, js_action_str, wait_ms)
PAGES = [
    # ANA
    ("01_ana_sayfa",                  "showSection('home')",                               1200),

    # ETİKET
    ("02_etiket_modelleri",           "showSection('labelModels')",                        1500),
    ("03_etiket_studio",              "showSection('label')",                              2000),
    ("04_toplu_uretim_studio",        "showSection('bulkLabel')",                          1500),
    ("05_isim_kesim_studio",          "showSection('nameCutStudio')",                      2000),
    ("06_yazdirma_sirasi",            "showSection('printQueue')",                         1200),
    ("07_etiket_ciktilari",           "showSection('labelOutputs')",                       1200),
    ("08_uretim_gecmisi",             "showSection('productionAudit')",                    1200),

    # SİPARİŞLER
    ("09_musteri_siparisleri",        "showSection('customerOrders')",                     1200),
    ("10_trendyol_merkezi",           "showSection('trendyolOrders')",                     1800),

    # TRENDYOL ALT-SEKMELER
    ("10a_trendyol_siparisler",       "openTrendyolSidebarTab('orders')",                  1200),
    ("10b_trendyol_kontrol_kuyrugu",  "openTrendyolSidebarTab('worklist')",                1200),
    ("10c_trendyol_urun_eslestirme",  "openTrendyolSidebarTab('mapping')",                 1200),
    ("10d_trendyol_kanit_eslestirme", "openTrendyolSidebarTab('questions')",               1200),
    ("10e_trendyol_aktarim_gecmisi",  "openTrendyolSidebarTab('history')",                 1200),

    # AYARLAR
    ("11_ayarlar_genel",              "openSettingsSubpage('general')",                    1200),
    ("12_ayarlar_kullanicilar",       "openSettingsSubpage('users')",                      1200),
    ("13_ayarlar_roller",             "openSettingsSubpage('roles')",                      1200),
    ("14_ayarlar_trendyol_api",       "openSettingsSubpage('trendyol-api')",               1200),
    ("15_ayarlar_kargo",              "openSettingsSubpage('shipping')",                   1200),
    ("16_ayarlar_diger",              "openSettingsSubpage('other-integrations')",         1200),
    ("17_ayarlar_yazici",             "openSettingsSubpage('printer-profiles')",           1200),
    ("18_ayarlar_veri_bakimi",        "openSettingsSubpage('data-maintenance')",           1200),

    # ÜRÜN & SİSTEM
    ("19_urun_tanimlari",             "showSection('products')",                           1200),
    ("20_raporlar",                   "showSection('reports')",                            1200),

    # TEKNİK (dev modüller)
    ("21_native_tools",               "showSection('nativeTools')",                        1200),
    ("22_laser",                      "showSection('laser')",                              1200),
    ("23_folders",                    "showSection('folders')",                            1200),

    # DEV MODÜLLER (genellikle gizli ama deneyelim)
    ("24_design_lab",                 "showSection('designLab')",                          1200),
    ("25_font_test_lab",              "showSection('fontTestLab')",                        1200),

    # ANA SAYFA DEV MODE AÇIK
    ("26_ana_sayfa_dev_mode",         "showSection('home'); document.querySelectorAll('[data-dev-module]').forEach(el=>el.style.removeProperty('display'))", 800),

    # PRINT QUEUE SEÇİLİ DURUM
    ("27_print_queue_secili",         "showSection('printQueue')", 1200),
]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport=VIEWPORT)
        page = await context.new_page()

        # Konsol hatalarını yakala
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        print(f"Sunucuya bağlanıyor: {BASE_URL}")
        await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        print("Sayfa yüklendi, tarama başlıyor...\n")

        ok_count = 0
        fail_count = 0

        for filename, js_action, wait_ms in PAGES:
            try:
                # JS ile sayfayı aç
                await page.evaluate(f"(function(){{ try{{ {js_action} }}catch(e){{}} }})()")
                await page.wait_for_timeout(wait_ms)

                # Screenshot al
                out_path = OUTPUT_DIR / f"{filename}.png"
                await page.screenshot(path=str(out_path), full_page=False)
                size_kb = out_path.stat().st_size // 1024
                print(f"  OK  {filename}.png  ({size_kb} KB)")
                ok_count += 1

            except Exception as e:
                print(f"  ERR {filename}: {e}")
                fail_count += 1
                try:
                    err_path = OUTPUT_DIR / f"{filename}_err.png"
                    await page.screenshot(path=str(err_path), full_page=False)
                    print(f"       -> kısmi kayıt: {err_path.name}")
                except Exception:
                    pass

        # Print Queue — "tümünü seç" butonuna bas (varsa)
        try:
            await page.evaluate("showSection('printQueue')")
            await page.wait_for_timeout(800)
            sel_btn = page.locator(".print-queue-select-all, [onclick*='selectAll'], input[type='checkbox'].select-all").first
            if await sel_btn.count() > 0:
                await sel_btn.click()
                await page.wait_for_timeout(400)
                out_path = OUTPUT_DIR / "27_print_queue_secili.png"
                await page.screenshot(path=str(out_path), full_page=False)
                print(f"  OK  27_print_queue_secili.png  ({out_path.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"  SKIP print queue seçili: {e}")

        await browser.close()

        print(f"\n{'='*55}")
        print(f"TOPLAM HEDEF : {len(PAGES)} sayfa")
        print(f"BAŞARILI     : {ok_count}")
        print(f"HATA         : {fail_count}")
        print(f"KLASÖR       : {OUTPUT_DIR.resolve()}")

        # Dosya listesi
        files = sorted(OUTPUT_DIR.glob("*.png"))
        print(f"\nDosyalar ({len(files)} adet):")
        for f in files:
            print(f"  {f.name:<55} {f.stat().st_size // 1024:>5} KB")


if __name__ == "__main__":
    asyncio.run(main())
