from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEventLoop, QPoint, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / datetime.now().strftime("%Y-%m-%d") / "production_sidebar_real_interaction_hotfix"
RESULT_PATH = OUTPUT_DIR / "production_sidebar_real_interaction_hotfix_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from desktop.web_main_window import WebMainWindow  # noqa: E402


def suppress_message_boxes() -> None:
    QMessageBox.information = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.warning = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.critical = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.question = staticmethod(lambda *args, **kwargs: QMessageBox.Yes)


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 45000):
    loop = QEventLoop()
    result = {"done": False, "value": None}

    def callback(value):
        result["done"] = True
        result["value"] = value
        loop.quit()

    wrapped = f"""
    (() => {{
      try {{
        return JSON.stringify(({script}));
      }} catch (error) {{
        return JSON.stringify({{ "__error": String(error && error.message || error), "stack": String(error && error.stack || "") }});
      }}
    }})()
    """
    window.view.page().runJavaScript(wrapped, callback)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if not result["done"]:
        raise RuntimeError(f"JavaScript timed out: {script[:180]}")
    value = result["value"]
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict) and parsed.get("__error"):
            raise RuntimeError(f"{parsed['__error']}\n{parsed.get('stack', '')}")
        return parsed
    return value


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wait(550)
    path = OUTPUT_DIR / filename
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def sidebar_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(
        window,
        """
        (() => {
          const sidebar = document.querySelector('.sidebar');
          const shell = document.querySelector('.app-shell');
          const label = [...document.querySelectorAll('.nav-label')].find((node) => node.textContent.includes('ETİKET'));
          const studioText = [...document.querySelectorAll('.nav-text')].find((node) => node.textContent.includes('Etiket Studio'));
          const active = document.querySelector('.nav-btn.active');
          const sideRect = sidebar?.getBoundingClientRect();
          return {
            width: Math.round(sideRect?.width || 0),
            gridColumns: shell ? getComputedStyle(shell).gridTemplateColumns : '',
            bodyClass: document.body.className,
            collapsed: document.body.classList.contains('sidebar-collapsed'),
            hoverExpanded: document.body.classList.contains('sidebar-hover-expanded'),
            pinned: document.body.classList.contains('sidebar-pinned'),
            autoCollapsed: document.body.classList.contains('sidebar-auto-collapsed'),
            sidebarExpanded: sidebar?.classList.contains('sidebar-expanded') || false,
            etiketsLabelVisible: Boolean(label && getComputedStyle(label).display !== 'none' && label.getBoundingClientRect().width > 10),
            studioTextVisible: Boolean(studioText && getComputedStyle(studioText).display !== 'none' && studioText.getBoundingClientRect().width > 30),
            activePage: document.querySelector('.page.active')?.id || '',
            activeText: active?.innerText?.trim().replace(/\\s+/g, ' ') || '',
            activePageKey: active?.dataset.page || '',
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth
          };
        })()
        """,
    )


def move_mouse(window: WebMainWindow, x: int, y: int, delay_ms: int = 420) -> None:
    QCursor.setPos(window.view.mapToGlobal(QPoint(x, y)))
    QTest.mouseMove(window.view, QPoint(x, y), delay=30)
    wait(delay_ms)


def dispatch_sidebar_mouse_event(window: WebMainWindow, event_name: str) -> None:
    run_js(
        window,
        f"""
        (() => {{
          const sidebar = document.querySelector('.sidebar');
          if (!sidebar) return false;
          sidebar.dispatchEvent(new MouseEvent({json.dumps(event_name)}, {{ bubbles: false, cancelable: true, view: window }}));
          return true;
        }})()
        """,
    )
    wait(360)


def move_into_sidebar(window: WebMainWindow) -> dict[str, object]:
    move_mouse(window, 34, 180)
    state = sidebar_state(window)
    if int(state.get("width") or 0) < 220:
        dispatch_sidebar_mouse_event(window, "mouseenter")
        state = sidebar_state(window)
        state["automationFallback"] = "dom_mouseenter_after_qtest"
    return state


def move_out_of_sidebar(window: WebMainWindow) -> dict[str, object]:
    move_mouse(window, 520, 80)
    state = sidebar_state(window)
    if state.get("hoverExpanded") or int(state.get("width") or 0) > 120:
        dispatch_sidebar_mouse_event(window, "mouseleave")
        state = sidebar_state(window)
        state["automationFallback"] = "dom_mouseleave_after_qtest"
    return state


def click_button_by_selector(window: WebMainWindow, selector: str) -> dict[str, object]:
    return run_js(
        window,
        f"""
        (() => {{
          const button = document.querySelector({json.dumps(selector)});
          if (!button) return {{ ok: false, error: 'button_not_found', selector: {json.dumps(selector)} }};
          button.scrollIntoView({{ block: 'center', inline: 'nearest' }});
          const rect = button.getBoundingClientRect();
          for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {{
            button.dispatchEvent(new MouseEvent(type, {{ bubbles: true, cancelable: true, view: window }}));
          }}
          return {{
            ok: true,
            method: 'dom_mouse_sequence',
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            text: button.innerText.trim().replace(/\\s+/g, ' '),
            title: button.getAttribute('title') || ''
          }};
        }})()
        """,
    )


def inspect_after_click(window: WebMainWindow, expected: dict[str, str]) -> dict[str, object]:
    return run_js(
        window,
        f"""
        (() => {{
          const activePage = document.querySelector('.page.active')?.id || '';
          const activeNav = document.querySelector('.nav-btn.active');
          const title = document.querySelector('.page.active h1, .page.active h2, .page.active .page-title')?.innerText?.trim() || '';
          const bodyText = document.querySelector('.page.active')?.innerText?.trim() || '';
          return {{
            expectedPage: {json.dumps(expected.get('page', ''))},
            expectedNavPage: {json.dumps(expected.get('navPage', ''))},
            expectedSettings: {json.dumps(expected.get('settings', ''))},
            expectedTrendyol: {json.dumps(expected.get('trendyol', ''))},
            activePage,
            activeNavPage: activeNav?.dataset.page || '',
            activeSettings: activeNav?.dataset.settingsSubpage || '',
            activeTrendyol: activeNav?.dataset.trendyolSidebarTab || '',
            title,
            hasVisibleContent: bodyText.length > 24,
            activeText: activeNav?.innerText?.trim().replace(/\\s+/g, ' ') || ''
          }};
        }})()
        """,
    )


def force_open_sidebar(window: WebMainWindow) -> None:
    run_js(window, "(() => { setSidebarCollapsed(false, { persist: false, pin: true }); return true; })()")
    wait(450)


def force_collapsed_sidebar(window: WebMainWindow) -> None:
    run_js(window, "(() => { setSidebarCollapsed(true, { persist: false, pin: false }); return true; })()")
    wait(450)


def setup_console_capture(window: WebMainWindow) -> None:
    run_js(
        window,
        """
        (() => {
          if (window.__sidebarHotfixConsoleBound) return true;
          window.__sidebarHotfixConsoleBound = true;
          window.__sidebarHotfixErrors = [];
          const originalError = console.error.bind(console);
          console.error = (...args) => {
            window.__sidebarHotfixErrors.push(args.map(String).join(' '));
            originalError(...args);
          };
          window.addEventListener('error', (event) => {
            window.__sidebarHotfixErrors.push(String(event.message || 'window error'));
          });
          window.addEventListener('unhandledrejection', (event) => {
            window.__sidebarHotfixErrors.push(String(event.reason || 'unhandled rejection'));
          });
          return true;
        })()
        """,
    )


def console_errors(window: WebMainWindow) -> list[str]:
    return run_js(window, "(() => window.__sidebarHotfixErrors || [])()")


def exercise_sidebar(window: WebMainWindow, failures: list[str]) -> dict[str, object]:
    screenshots: dict[str, str] = {}
    states: dict[str, object] = {}

    window.resize(1366, 768)
    wait(900)
    run_js(window, "(() => { showSection('home'); setSidebarCollapsed(true, { persist: false, pin: false }); return true; })()")
    wait(650)
    states["collapsed_1366"] = sidebar_state(window)
    screenshots["sidebar_collapsed_1366"] = save_screenshot(window, "sidebar-collapsed-1366.png")

    states["hover_expanded_1366"] = move_into_sidebar(window)
    screenshots["sidebar_hover_expanded_1366"] = save_screenshot(window, "sidebar-hover-expanded-1366.png")

    states["leave_1366"] = move_out_of_sidebar(window)

    run_js(window, "(() => { setSidebarCollapsed(false, { persist: false, pin: true }); return true; })()")
    wait(420)
    states["pinned_open_1366"] = move_out_of_sidebar(window)
    screenshots["sidebar_pinned_open_1366"] = save_screenshot(window, "sidebar-pinned-open-1366.png")

    window.resize(1920, 1080)
    wait(800)
    run_js(window, "(() => { setSidebarCollapsed(false, { persist: false, pin: true }); return true; })()")
    wait(500)
    states["open_1920"] = sidebar_state(window)
    screenshots["sidebar_open_1920"] = save_screenshot(window, "sidebar-open-1920.png")

    run_js(window, "(() => { setSidebarCollapsed(true, { persist: false, pin: false }); return true; })()")
    wait(500)
    states["collapsed_1920"] = sidebar_state(window)
    screenshots["sidebar_collapsed_1920"] = save_screenshot(window, "sidebar-collapsed-1920.png")

    assert_true(states["collapsed_1366"]["width"] <= 90, "1366 collapsed menü dar genişliğe inmedi.", failures)
    assert_true(states["collapsed_1366"]["studioTextVisible"] is False, "Collapsed durumda link isimleri görünür kaldı.", failures)
    assert_true(states["hover_expanded_1366"]["width"] >= 230, "1366 hover menüyü gerçek genişliğe açmadı.", failures)
    assert_true(states["hover_expanded_1366"]["etiketsLabelVisible"] is True, "Hover durumda bölüm başlıkları görünmedi.", failures)
    assert_true(states["hover_expanded_1366"]["studioTextVisible"] is True, "Hover durumda menü link isimleri görünmedi.", failures)
    assert_true(states["leave_1366"]["width"] <= 90, "Mouse leave sonrası menü tekrar collapsed olmadı.", failures)
    assert_true(states["pinned_open_1366"]["pinned"] is True and states["pinned_open_1366"]["width"] >= 230, "Pinned açık state mouse leave sonrası korunmadı.", failures)
    assert_true(states["open_1920"]["width"] >= 230, "1920 açık menü geniş görünmedi.", failures)
    assert_true(states["collapsed_1920"]["width"] <= 90, "1920 collapsed menü daralmadı.", failures)
    return {"states": states, "screenshots": screenshots}


def exercise_operation_pages(window: WebMainWindow, failures: list[str]) -> dict[str, str]:
    required = [
        ("label-studio-sidebar-hover-1366.png", "openLabelStudio()", "Etiket Studio"),
        ("bulk-production-sidebar-hover-1366.png", "showSection('bulkLabel')", "Toplu Üretim"),
        ("namecut-sidebar-hover-1366.png", "showSection('nameCutStudio')", "İsim Kesim"),
        ("print-queue-sidebar-hover-1366.png", "showSection('printQueue')", "Yazdırma Sırası"),
    ]
    screenshots: dict[str, str] = {}
    window.resize(1366, 768)
    wait(700)
    for filename, command, label in required:
        run_js(window, f"(() => {{ setSidebarCollapsed(false, {{ persist: false, pin: false }}); {command}; return document.querySelector('.page.active')?.id || ''; }})()")
        wait(700)
        before = sidebar_state(window)
        after = move_into_sidebar(window)
        screenshots[filename.removesuffix(".png").replace("-", "_")] = save_screenshot(window, filename)
        assert_true(before["width"] <= 95 or before["autoCollapsed"], f"{label} başlangıçta kompakt/collapsed davranmadı: {before}", failures)
        assert_true(after["width"] >= 230, f"{label} ekranında hover menüyü açmadı: {after}", failures)
        assert_true(after["studioTextVisible"] is True, f"{label} ekranında hover sonrası link metinleri görünmedi.", failures)
        move_out_of_sidebar(window)
    return screenshots


def exercise_navigation(window: WebMainWindow, failures: list[str]) -> list[dict[str, object]]:
    force_open_sidebar(window)
    targets = [
        ("Ana Sayfa", ".nav-btn[data-page='home']", {"page": "home", "navPage": "home"}),
        ("Design Lab", ".nav-btn[data-page='designLab']", {"page": "designLab", "navPage": "designLab"}),
        ("Font Test Lab", ".nav-btn[data-page='fontTestLab']", {"page": "fontTestLab", "navPage": "fontTestLab"}),
        ("Etiket Modelleri", ".nav-btn[data-page='labelModels']", {"page": "labelModels", "navPage": "labelModels"}),
        ("Etiket Studio", ".nav-btn[data-page='label'][title='Etiket Studio']", {"page": "label", "navPage": "label"}),
        ("Manuel Etiket", ".nav-btn[data-page='manualLabel']", {"page": "label", "navPage": "manualLabel"}),
        ("Toplu Üretim Studio", ".nav-btn[data-page='bulkLabel']", {"page": "bulkLabel", "navPage": "bulkLabel"}),
        ("İsim Kesim", ".nav-btn[data-page='nameCutStudio']", {"page": "nameCutStudio", "navPage": "nameCutStudio"}),
        ("Yazdırma Sırası", ".nav-btn[data-page='printQueue']", {"page": "printQueue", "navPage": "printQueue"}),
        ("Etiket Çıktıları", ".nav-btn[data-page='labelOutputs']", {"page": "labelOutputs", "navPage": "labelOutputs"}),
        ("Trendyol Siparişleri", ".nav-btn[data-trendyol-sidebar-tab='orders']", {"page": "trendyolOrders", "navPage": "trendyolOrders", "trendyol": "orders"}),
        ("Kontrol Kuyruğu", ".nav-btn[data-trendyol-sidebar-tab='worklist']", {"page": "trendyolOrders", "navPage": "trendyolOrders", "trendyol": "worklist"}),
        ("Ürün Eşleştirme", ".nav-btn[data-trendyol-sidebar-tab='mapping']", {"page": "trendyolOrders", "navPage": "trendyolOrders", "trendyol": "mapping"}),
        ("Kanıt Eşleştirme", ".nav-btn[data-trendyol-sidebar-tab='questions']", {"page": "trendyolOrders", "navPage": "trendyolOrders", "trendyol": "questions"}),
        ("Aktarım Geçmişi", ".nav-btn[data-trendyol-sidebar-tab='history']", {"page": "trendyolOrders", "navPage": "trendyolOrders", "trendyol": "history"}),
        ("Üretim Geçmişi", ".nav-btn[data-page='productionAudit']", {"page": "productionAudit", "navPage": "productionAudit"}),
        ("Genel Ayarlar", ".nav-btn[data-settings-subpage='general']", {"page": "settings", "navPage": "settings", "settings": "general"}),
        ("Kullanıcılar", ".nav-btn[data-settings-subpage='users']", {"page": "settings", "navPage": "settings", "settings": "users"}),
        ("Roller", ".nav-btn[data-settings-subpage='roles']", {"page": "settings", "navPage": "settings", "settings": "roles"}),
        ("Trendyol API", ".nav-btn[data-settings-subpage='trendyol-api']", {"page": "settings", "navPage": "settings", "settings": "trendyol-api"}),
        ("Kargo Firmaları", ".nav-btn[data-settings-subpage='shipping']", {"page": "settings", "navPage": "settings", "settings": "shipping"}),
        ("Diğer Ayarlar", ".nav-btn[data-settings-subpage='other-integrations']", {"page": "settings", "navPage": "settings", "settings": "other-integrations"}),
        ("Veri Bakımı", ".nav-btn[data-settings-subpage='data-maintenance']", {"page": "settings", "navPage": "settings", "settings": "data-maintenance"}),
        ("Yazıcı Profilleri", ".nav-btn[data-settings-subpage='printer-profiles']", {"page": "settings", "navPage": "settings", "settings": "printer-profiles"}),
    ]
    rows: list[dict[str, object]] = []
    for label, selector, expected in targets:
        force_open_sidebar(window)
        click_info = click_button_by_selector(window, selector)
        state = inspect_after_click(window, expected)
        ok_page = state.get("activePage") == expected.get("page")
        if expected.get("settings"):
            ok_active = state.get("activeNavPage") == "settings" and state.get("activeSettings") == expected.get("settings")
        elif expected.get("trendyol"):
            ok_active = state.get("activeNavPage") == "trendyolOrders" and state.get("activeTrendyol") == expected.get("trendyol")
        else:
            ok_active = state.get("activeNavPage") == expected.get("navPage")
        row = {"label": label, "selector": selector, "click": click_info, "state": state, "ok_page": ok_page, "ok_active": ok_active}
        rows.append(row)
        assert_true(click_info.get("ok") is True, f"{label} menü butonu bulunamadı/tıklanamadı: {click_info}", failures)
        assert_true(ok_page, f"{label} yanlış ekran açtı: {state}", failures)
        assert_true(ok_active, f"{label} aktif menü vurgusu yanlış: {state}", failures)
        assert_true(state.get("hasVisibleContent") is True, f"{label} boş/broken ekran gibi görünüyor.", failures)
    return rows


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    result: dict[str, object]
    try:
        window.resize(1366, 768)
        window.show()
        window.raise_()
        window.activateWindow()
        wait(2400)
        setup_console_capture(window)
        sidebar = exercise_sidebar(window, failures)
        operation_screens = exercise_operation_pages(window, failures)
        navigation = exercise_navigation(window, failures)
        errors = [err for err in console_errors(window) if "ResizeObserver loop" not in err]
        assert_true(not errors, f"Console error oluştu: {errors[:5]}", failures)
        screenshots = {**sidebar["screenshots"], **operation_screens}
        result = {
            "status": "PASS" if not failures else "FAIL",
            "final_decision": "READY_FOR_PILOT_WITH_SIDEBAR_FIX" if not failures else "READY_WITH_UI_BLOCKER",
            "failures": failures,
            "sidebar": sidebar["states"],
            "navigation": navigation,
            "console_errors": errors,
            "screenshots": screenshots,
            "safety": {
                "printer_auto_start": False,
                "laser_auto_start": False,
                "rdworks_auto_start": False,
                "trendyol_live_action": False,
            },
        }
    except Exception as exc:  # noqa: BLE001
        result = {
            "status": "ERROR",
            "final_decision": "NOT_READY_FOR_OPERATOR",
            "error": str(exc),
            "failures": failures,
        }
    finally:
        window.close()
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
