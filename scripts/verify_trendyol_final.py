"""
Final Playwright verification: Trendyol incremental + auto-sync.
Focused, fast script — captures exactly the 4 acceptance criteria.
"""
import time, json
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

OUT = Path(__file__).resolve().parents[1] / "output" / "verify_final"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:8000"

def ss(page, name):
    p = str(OUT / f"{name}.png")
    page.screenshot(path=p)
    print(f"[ss] {p}")
    return p

def wait_for_sync_done(page, timeout=150):
    """Wait until #trendyolStatus has .ok class or goes hidden."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            el = page.locator("#trendyolStatus")
            cls = el.get_attribute("class") or ""
            hidden = el.get_attribute("hidden")
            text = el.inner_text()
            if hidden is not None or "ok" in cls or not text.strip():
                return True
            if any(k in text for k in ("tamamlandı", "hazırlandı", "sipariş paketi")):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_context(viewport={"width":1400,"height":900}).new_page()

        console_errs = []
        page.on("console", lambda m: console_errs.append(m.text) if m.type == "error" else None)

        # ── 0. Load & navigate to Trendyol ──────────────────────────────────
        page.goto(BASE, wait_until="networkidle")
        time.sleep(1)
        try:
            page.click("text=Trendyol Merkezi", timeout=3000)
        except Exception:
            try:
                page.click("text=Trendyol", timeout=2000)
            except Exception:
                pass
        time.sleep(1.5)

        # ── 1. FIRST SYNC ───────────────────────────────────────────────────
        print("\n=== SYNC 1 ===")
        t0 = time.time()
        try:
            page.click("button:has-text('7 Günü Çek')", timeout=3000)
        except Exception:
            page.locator("button").filter(has_text="Çek").last.click()
        done = wait_for_sync_done(page, timeout=180)
        t1 = time.time()
        sync1 = t1 - t0
        status1 = ""
        try: status1 = page.locator("#trendyolStatus").inner_text()
        except Exception: pass
        print(f"sync1={sync1:.1f}s  done={done}  status={status1!r}")
        ss(page, "1_after_sync1")

        # ── 2. SECOND SYNC immediately ───────────────────────────────────────
        print("\n=== SYNC 2 (incremental) ===")
        time.sleep(0.5)
        t2 = time.time()
        try:
            page.click("button:has-text('7 Günü Çek')", timeout=3000)
        except Exception:
            page.locator("button").filter(has_text="Çek").last.click()
        done2 = wait_for_sync_done(page, timeout=30)
        t3 = time.time()
        sync2 = t3 - t2
        status2 = ""
        try: status2 = page.locator("#trendyolStatus").inner_text()
        except Exception: pass
        print(f"sync2={sync2:.1f}s  done={done2}  status={status2!r}")
        ss(page, "2_after_sync2")

        # ── 3. BANNER STATE ──────────────────────────────────────────────────
        print("\n=== BANNER ===")
        cred, last_sync_top, strip = "", "", ""
        try: cred = page.locator("#trendyolCredentialStatusBanner").inner_text()
        except Exception: pass
        try: last_sync_top = page.locator("#trendyolLastSyncAtTop").inner_text()
        except Exception: pass
        try: strip = page.locator("#trendyolReadonlySyncStrip").inner_text()
        except Exception: pass
        print(f"credential-banner : {cred!r}")
        print(f"last-sync-top     : {last_sync_top!r}")
        print(f"sync-strip        : {strip!r}")
        ss(page, "3_banner_state")

        # ── 4. AUTO-SYNC toggle ON ───────────────────────────────────────────
        print("\n=== AUTO-SYNC ON ===")
        try:
            toggle = page.locator("#trendyolAutoSyncToggle")
            if toggle.count() and not toggle.is_checked():
                toggle.click()
                time.sleep(0.5)
            print(f"toggle-checked={toggle.is_checked() if toggle.count() else '?'}")
        except Exception as e:
            print(f"toggle error: {e}")
        ss(page, "4_autosync_on")

        # ── 5. WAIT 38s for poll cycle ───────────────────────────────────────
        print("\n=== WAIT 38s for poll ===")
        time.sleep(38)
        last_run, new_badge = "", ""
        try: last_run = page.locator("#trendyolAutoSyncLastRun").inner_text()
        except Exception: pass
        try: new_badge = page.locator("#trendyolAutoSyncNewCount").inner_text()
        except Exception: pass
        strip2 = ""
        try: strip2 = page.locator("#trendyolReadonlySyncStrip").inner_text()
        except Exception: pass
        print(f"last-run   : {last_run!r}")
        print(f"new-badge  : {new_badge!r}")
        print(f"strip      : {strip2!r}")
        ss(page, "5_after_poll")

        # ── 6. TOGGLE OFF ────────────────────────────────────────────────────
        print("\n=== TOGGLE OFF ===")
        try:
            toggle = page.locator("#trendyolAutoSyncToggle")
            if toggle.count() and toggle.is_checked():
                toggle.click()
                time.sleep(0.8)
            print(f"toggle-unchecked={not toggle.is_checked() if toggle.count() else '?'}")
            status_bar = page.locator("#trendyolStatus").inner_text()
            print(f"status-bar: {status_bar!r}")
        except Exception as e:
            print(f"toggle-off error: {e}")
        ss(page, "6_autosync_off")

        # ── 7. CONSOLE ───────────────────────────────────────────────────────
        bad = [e for e in console_errs if not any(x in e for x in ("file:///", "ERR_UNKNOWN_URL_SCHEME", "local resource"))]
        print(f"\n=== CONSOLE ===\ntotal errors={len(console_errs)}  new/bad={len(bad)}")
        for e in bad[:5]:
            print(f"  {e}")

        # ── SUMMARY ──────────────────────────────────────────────────────────
        print("\n" + "="*60)
        print(f"SYNC1         : {sync1:.1f}s (first fetch)")
        print(f"SYNC2         : {sync2:.1f}s (incremental — target <10s)")
        print(f"SYNC2 STATUS  : {status2!r}")
        print(f"CREDENTIAL    : {cred!r}  (must NOT be 'Eksik credential')")
        print(f"LAST SYNC TOP : {last_sync_top!r}  (must NOT be '-')")
        print(f"STRIP         : {strip2!r}")
        print(f"POLL LAST RUN : {last_run!r}  (must be HH:MM:SS)")
        print(f"NEW BADGE     : {new_badge!r}")
        print(f"CONSOLE BAD   : {len(bad)}")
        print("="*60)
        print("Screenshots:", OUT)
        browser.close()

if __name__ == "__main__":
    main()
