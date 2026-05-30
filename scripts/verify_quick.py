import sys, time
sys.stdout.reconfigure(line_buffering=True)
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("output/verify_final")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:8000"

def p(*a): print(*a, flush=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_context(viewport={"width":1400,"height":900}).new_page()
    console_errs = []
    page.on("console", lambda m: console_errs.append(m.text) if m.type=="error" else None)

    p("loading page...")
    page.goto(BASE, wait_until="networkidle")
    time.sleep(1)
    try: page.click("text=Trendyol Merkezi", timeout=3000)
    except:
        try: page.click("text=Trendyol", timeout=2000)
        except: pass
    time.sleep(1.5)

    page.screenshot(path=str(OUT/"A_initial.png"))
    p("A_initial.png saved")

    try: cred = page.locator("#trendyolCredentialStatusBanner").inner_text()
    except: cred = "NOT FOUND"
    try: last_top = page.locator("#trendyolLastSyncAtTop").inner_text()
    except: last_top = "NOT FOUND"
    try: strip = page.locator("#trendyolReadonlySyncStrip").inner_text()
    except: strip = "NOT FOUND"
    try: auto_vis = page.locator("#trendyolAutoSyncStrip").is_visible()
    except: auto_vis = False
    p(f"cred={cred!r}")
    p(f"last_top={last_top!r}")
    p(f"strip={strip!r}")
    p(f"auto_strip_visible={auto_vis}")

    # Toggle auto-sync ON
    try:
        t = page.locator("#trendyolAutoSyncToggle")
        if t.count() and not t.is_checked():
            t.click(); time.sleep(0.5)
        p(f"toggle_on={t.is_checked() if t.count() else 'missing'}")
    except Exception as e:
        p(f"toggle err: {e}")

    page.screenshot(path=str(OUT/"B_autosync_on.png"))
    p("B_autosync_on.png saved")

    p("waiting 38s for scheduler poll...")
    time.sleep(38)

    try: lr = page.locator("#trendyolAutoSyncLastRun").inner_text()
    except: lr = "NOT FOUND"
    try: strip2 = page.locator("#trendyolReadonlySyncStrip").inner_text()
    except: strip2 = "NOT FOUND"
    try: badge = page.locator("#trendyolAutoSyncNewCount").inner_text()
    except: badge = "NOT FOUND"
    p(f"last_run={lr!r}")
    p(f"strip2={strip2!r}")
    p(f"new_badge={badge!r}")
    page.screenshot(path=str(OUT/"C_after_poll.png"))
    p("C_after_poll.png saved")

    # Toggle OFF
    try:
        t = page.locator("#trendyolAutoSyncToggle")
        if t.count() and t.is_checked():
            t.click(); time.sleep(0.8)
        try: status = page.locator("#trendyolStatus").inner_text()
        except: status = ""
        p(f"toggle_off={not t.is_checked() if t.count() else 'missing'}")
        p(f"status_bar={status!r}")
    except Exception as e:
        p(f"toggle-off err: {e}")
    page.screenshot(path=str(OUT/"D_autosync_off.png"))
    p("D_autosync_off.png saved")

    bad = [e for e in console_errs if not any(x in e for x in ("file:///","ERR_UNKNOWN","local resource"))]
    p(f"console total={len(console_errs)} bad={len(bad)}")
    for e in bad[:3]: p(f"  BAD: {e}")

    browser.close()
    p("DONE")
