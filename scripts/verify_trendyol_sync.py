"""
Playwright verification script for Trendyol incremental + auto-sync.
Screenshots written to output/verify_screenshots/.
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

OUT = Path(__file__).resolve().parents[1] / "output" / "verify_screenshots"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:8000"

def ss(page: Page, name: str) -> str:
    p = str(OUT / f"{name}.png")
    page.screenshot(path=p, full_page=False)
    print(f"[screenshot] {p}")
    return p

def nav_trendyol(page: Page):
    """Navigate to the Trendyol Merkezi section."""
    # Click the sidebar Trendyol nav item
    page.goto(BASE, wait_until="networkidle")
    time.sleep(1)
    # Try to find the Trendyol nav link
    trendyol_link = page.locator("a, button, [data-view], [onclick*='trendyol'], [onclick*='Trendyol']").filter(has_text="Trendyol").first
    if trendyol_link.count():
        trendyol_link.click()
        time.sleep(1)
    else:
        # Try sidebar navigation
        page.evaluate("if(typeof openView==='function') openView('trendyolOrders'); else if(typeof showSection==='function') showSection('trendyolOrders');")
        time.sleep(0.5)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()

        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type in ("error", "warning") else None)

        print("=== 1. Load homepage ===")
        page.goto(BASE, wait_until="networkidle")
        ss(page, "01_homepage")

        print("=== 2. Navigate to Trendyol ===")
        # Try clicking Trendyol nav
        try:
            page.click("text=Trendyol", timeout=3000)
        except Exception:
            try:
                page.evaluate("document.querySelectorAll('[data-view],[onclick]').forEach(el=>{ if((el.getAttribute('data-view')||el.getAttribute('onclick')||'').toLowerCase().includes('trendyol')) el.click(); })")
            except Exception:
                pass
        time.sleep(1.5)
        ss(page, "02_trendyol_page_initial")

        print("=== 3. Check readonly-banner credential text ===")
        banner_text = ""
        try:
            banner = page.locator(".readonly-banner, #trendyolReadonlySyncStrip").first
            banner_text = banner.inner_text()
            print(f"[banner] {banner_text!r}")
        except Exception as e:
            print(f"[banner] could not read: {e}")

        print("=== 4. Check auto-sync strip visibility ===")
        auto_strip_visible = False
        auto_strip_text = ""
        try:
            strip = page.locator("#trendyolAutoSyncStrip")
            auto_strip_visible = strip.is_visible()
            if auto_strip_visible:
                auto_strip_text = strip.inner_text()
            print(f"[autosync-strip] visible={auto_strip_visible}, text={auto_strip_text!r}")
        except Exception as e:
            print(f"[autosync-strip] error: {e}")
        ss(page, "03_trendyol_banner_and_strip")

        print("=== 5. First sync (7 günü çek) ===")
        t0 = time.time()
        try:
            btn = page.locator("button").filter(has_text="7 Günü Çek").first
            if not btn.count():
                btn = page.locator("button").filter(has_text="Çek").last
            btn.click()
            # Wait for sync to complete (status line appears and disappears or changes)
            page.wait_for_selector("#trendyolStatus:not([hidden])", timeout=5000)
            page.wait_for_selector("#trendyolStatus[hidden], #trendyolStatus.ok", timeout=120000)
        except Exception as e:
            print(f"[sync1] wait failed: {e}")
        t1 = time.time()
        sync1_time = t1 - t0
        print(f"[sync1] completed in {sync1_time:.1f}s")
        ss(page, "04_after_first_sync")

        # Read the status message
        status1 = ""
        try:
            status1 = page.locator("#trendyolStatus").inner_text()
            print(f"[sync1-status] {status1!r}")
        except Exception:
            pass

        print("=== 6. Second sync immediately (incremental test) ===")
        t2 = time.time()
        try:
            btn2 = page.locator("button").filter(has_text="7 Günü Çek").first
            if not btn2.count():
                btn2 = page.locator("button").filter(has_text="Çek").last
            btn2.click()
            page.wait_for_selector("#trendyolStatus:not([hidden])", timeout=5000)
            page.wait_for_selector("#trendyolStatus[hidden], #trendyolStatus.ok", timeout=30000)
        except Exception as e:
            print(f"[sync2] wait failed: {e}")
        t3 = time.time()
        sync2_time = t3 - t2
        print(f"[sync2] completed in {sync2_time:.1f}s")
        status2 = ""
        try:
            status2 = page.locator("#trendyolStatus").inner_text()
            print(f"[sync2-status] {status2!r}")
        except Exception:
            pass
        ss(page, "05_after_second_sync")

        print("=== 7. Read final banner state ===")
        banner2_text = ""
        try:
            cred = page.locator("#trendyolCredentialStatusBanner").first
            if cred.count():
                banner2_text = cred.inner_text()
                print(f"[credential-banner] {banner2_text!r}")
            strip2 = page.locator("#trendyolReadonlySyncStrip").first
            if strip2.count():
                print(f"[sync-strip] {strip2.inner_text()!r}")
        except Exception as e:
            print(f"[banner2] error: {e}")

        print("=== 8. Auto-sync toggle ON ===")
        toggle_checked_after = False
        try:
            toggle = page.locator("#trendyolAutoSyncToggle")
            if toggle.count() and not toggle.is_checked():
                toggle.click()
                time.sleep(0.5)
            toggle_checked_after = toggle.is_checked() if toggle.count() else False
            print(f"[autosync-toggle] checked={toggle_checked_after}")
        except Exception as e:
            print(f"[autosync-toggle] error: {e}")
        ss(page, "06_autosync_toggled_on")

        print("=== 9. Wait 38s for first poll cycle ===")
        time.sleep(38)
        ss(page, "07_after_poll_wait")
        last_run_text = ""
        try:
            lr = page.locator("#trendyolAutoSyncLastRun")
            if lr.count():
                last_run_text = lr.inner_text()
                print(f"[last-run] {last_run_text!r}")
        except Exception as e:
            print(f"[last-run] error: {e}")

        print("=== 10. Toggle OFF ===")
        toggle_off = False
        try:
            toggle = page.locator("#trendyolAutoSyncToggle")
            if toggle.count() and toggle.is_checked():
                toggle.click()
                time.sleep(0.5)
            toggle_off = not toggle.is_checked() if toggle.count() else True
            print(f"[autosync-off] toggle unchecked={toggle_off}")
        except Exception as e:
            print(f"[toggle-off] error: {e}")
        ss(page, "08_autosync_toggled_off")

        print("=== 11. Console errors ===")
        rate_limit_errors = [e for e in console_errors if any(k in e.lower() for k in ("429", "rate", "exception", "error", "traceback"))]
        print(f"[console] total msgs: {len(console_errors)}, rate-limit/errors: {len(rate_limit_errors)}")
        for e in rate_limit_errors[:5]:
            print(f"  {e}")

        # Summary
        print("\n====== SUMMARY ======")
        print(f"sync1_time:       {sync1_time:.1f}s")
        print(f"sync2_time:       {sync2_time:.1f}s  (INCREMENTAL - should be <10s)")
        print(f"sync1_status:     {status1!r}")
        print(f"sync2_status:     {status2!r}")
        print(f"credential:       {banner2_text!r}  (should NOT be 'Eksik credential')")
        print(f"autosync_on:      {toggle_checked_after}")
        print(f"autosync_off:     {toggle_off}")
        print(f"last_run:         {last_run_text!r}  (should show HH:MM:SS after 38s)")
        print(f"console_errors:   {len(rate_limit_errors)}")

        browser.close()
        print("\nDone. Screenshots:", OUT)

if __name__ == "__main__":
    main()
