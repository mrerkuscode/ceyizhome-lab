"""CeyizHome Lab — Tüm sayfalar için otomatik ekran görüntüsü.

Kullanım:
  .venv\\Scripts\\python.exe scripts\\take_screenshots.py

Önkoşul: Flask sunucu http://localhost:8000'de çalışıyor olmalı.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8000"
OUTPUT_DIR = Path("output/2026-05-28/ui_screenshots")
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

PAGES = [
    ("01_ana_sayfa",        "home",            "Ana Sayfa"),
    ("02_etiket_studio",    "label",           "Etiket Studio"),
    ("03_etiket_modelleri", "labelModels",     "Etiket Modelleri"),
    ("04_print_queue",      "printQueue",      "Yazdırma Sırası"),
    ("05_reports",          "reports",         "Raporlar"),
    ("06_customer_orders",  "customerOrders",  "Müşteri Siparişleri"),
    ("07_trendyol",         "trendyolOrders",  "Trendyol Siparişleri"),
    ("08_name_cut_studio",  "nameCutStudio",   "İsim Kesim Studio"),
    ("09_settings",         "settings",        "Ayarlar"),
]


def _nav(page, page_id):
    # JS showSection() kullan — sidebar durumundan bagimsiz
    page.evaluate(f"if(typeof showSection==='function') showSection('{page_id}')")
    page.wait_for_timeout(1500)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            locale="tr-TR",
        )
        page = context.new_page()

        print(f"Ana sayfa açılıyor: {BASE_URL}")
        page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)

        # 9 ana sayfa
        for filename, page_id, page_name in PAGES:
            print(f"[SS] {page_name} ({page_id})...")
            try:
                _nav(page, page_id)
            except Exception as e:
                print(f"   WARN: Navigasyon: {e}")
            out = OUTPUT_DIR / f"{filename}.png"
            page.screenshot(path=str(out), full_page=True)
            print(f"   OK {out.name} ({out.stat().st_size // 1024} KB)")

        # Bonus: sidebar altı (Dev Mode toggle)
        print("[SS] Geliştirici Modu toggle...")
        try:
            _nav(page, "home")
            page.evaluate(
                "document.querySelector('aside,.sidebar')?.scrollTo(0, 9999)"
            )
            page.wait_for_timeout(600)
            out = OUTPUT_DIR / "10_dev_mode_toggle.png"
            page.screenshot(path=str(out), full_page=True)
            print(f"   OK {out.name} ({out.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"   WARN: {e}")

        # Bonus: Print Queue çoklu seçim
        print("[SS] Print Queue — çoklu seçim...")
        try:
            _nav(page, "printQueue")
            checkboxes = page.query_selector_all('input[type="checkbox"]')
            for cb in checkboxes[:3]:
                try:
                    cb.click()
                    page.wait_for_timeout(150)
                except Exception:
                    pass
            page.wait_for_timeout(500)
            out = OUTPUT_DIR / "11_print_queue_secili.png"
            page.screenshot(path=str(out), full_page=True)
            print(f"   OK {out.name} ({out.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"   WARN: {e}")

        browser.close()

    files = sorted(OUTPUT_DIR.glob("*.png"))
    print(f"\nDONE: Toplam {len(files)} ekran görüntüsü oluşturuldu:")
    for f in files:
        print(f"   - {f.name} ({f.stat().st_size // 1024} KB)")
    print(f"\nKlasor: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
