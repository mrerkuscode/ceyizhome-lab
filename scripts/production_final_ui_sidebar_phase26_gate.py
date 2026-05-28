from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-22" / "production_final_ui_sidebar_phase26"
RESULT_PATH = OUTPUT_DIR / "production_final_ui_sidebar_phase26_gate_result.json"

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


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 30000):
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
    path = OUTPUT_DIR / filename
    wait(650)
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def inspect_sidebar_behavior(window: WebMainWindow) -> dict[str, object]:
    result: dict[str, object] = {}
    window.resize(1366, 768)
    wait(900)
    result["collapsed_state"] = run_js(
        window,
        """
        (() => {
          showSection('home');
          setSidebarCollapsed(true, { persist: false, pin: false });
          const sidebar = document.querySelector('.sidebar');
          return {
            bodyCollapsed: document.body.classList.contains('sidebar-collapsed'),
            bodyPinned: document.body.classList.contains('sidebar-pinned'),
            hoverExpanded: document.body.classList.contains('sidebar-hover-expanded'),
            sidebarExpanded: sidebar?.classList.contains('sidebar-expanded') || false,
            activePage: document.querySelector('.page.active')?.id || '',
            activeNav: document.querySelector('.nav-btn.active')?.dataset.page || ''
          };
        })()
        """,
        timeout_ms=60000,
    )
    result["sidebar_collapsed_1366"] = save_screenshot(window, "sidebar-collapsed-1366.png")

    result["hover_state"] = run_js(
        window,
        """
        (() => {
          const sidebar = document.querySelector('.sidebar');
          sidebar.dispatchEvent(new MouseEvent('mouseenter', { bubbles: false }));
          const shell = document.querySelector('.app-shell');
          return {
            bodyCollapsed: document.body.classList.contains('sidebar-collapsed'),
            hoverExpanded: document.body.classList.contains('sidebar-hover-expanded'),
            sidebarExpanded: sidebar?.classList.contains('sidebar-expanded') || false,
            gridColumns: getComputedStyle(shell).gridTemplateColumns,
            sidebarWidth: Math.round(sidebar.getBoundingClientRect().width)
          };
        })()
        """,
        timeout_ms=60000,
    )
    if int(result["hover_state"].get("sidebarWidth") or 0) < 220:
        run_js(
            window,
            """
            (() => {
              const sidebar = document.querySelector('.sidebar');
              sidebar.dispatchEvent(new MouseEvent('mouseenter', { bubbles: false, cancelable: true, view: window }));
              return true;
            })()
            """,
            timeout_ms=60000,
        )
        wait(450)
        result["hover_state"] = run_js(
            window,
            """
            (() => {
              const sidebar = document.querySelector('.sidebar');
              const shell = document.querySelector('.app-shell');
              return {
                bodyCollapsed: document.body.classList.contains('sidebar-collapsed'),
                hoverExpanded: document.body.classList.contains('sidebar-hover-expanded'),
                sidebarExpanded: sidebar?.classList.contains('sidebar-expanded') || false,
                gridColumns: getComputedStyle(shell).gridTemplateColumns,
                sidebarWidth: Math.round(sidebar.getBoundingClientRect().width),
                automationFallback: 'dom_mouseenter_after_qtest'
              };
            })()
            """,
            timeout_ms=60000,
        )
    result["sidebar_hover_expanded_1366"] = save_screenshot(window, "sidebar-hover-expanded-1366.png")

    result["leave_state"] = run_js(
        window,
        """
        (() => {
          const sidebar = document.querySelector('.sidebar');
          sidebar.dispatchEvent(new MouseEvent('mouseleave', { bubbles: false }));
          return {
            bodyCollapsed: document.body.classList.contains('sidebar-collapsed'),
            hoverExpanded: document.body.classList.contains('sidebar-hover-expanded'),
            sidebarExpanded: sidebar?.classList.contains('sidebar-expanded') || false,
            sidebarWidth: Math.round(sidebar.getBoundingClientRect().width)
          };
        })()
        """,
        timeout_ms=60000,
    )
    if result["leave_state"].get("hoverExpanded") or int(result["leave_state"].get("sidebarWidth") or 0) > 120:
        run_js(
            window,
            """
            (() => {
              const sidebar = document.querySelector('.sidebar');
              sidebar.dispatchEvent(new MouseEvent('mouseleave', { bubbles: false, cancelable: true, view: window }));
              return true;
            })()
            """,
            timeout_ms=60000,
        )
        wait(450)
        result["leave_state"] = run_js(
            window,
            """
            (() => {
              const sidebar = document.querySelector('.sidebar');
              return {
                bodyCollapsed: document.body.classList.contains('sidebar-collapsed'),
                hoverExpanded: document.body.classList.contains('sidebar-hover-expanded'),
                sidebarExpanded: sidebar?.classList.contains('sidebar-expanded') || false,
                sidebarWidth: Math.round(sidebar.getBoundingClientRect().width),
                automationFallback: 'dom_mouseleave_after_qtest'
              };
            })()
            """,
            timeout_ms=60000,
        )

    window.resize(1920, 1080)
    wait(800)
    result["pinned_state"] = run_js(
        window,
        """
        (() => {
          setSidebarCollapsed(false, { persist: false, pin: true });
          const sidebar = document.querySelector('.sidebar');
          sidebar.dispatchEvent(new MouseEvent('mouseleave', { bubbles: false }));
          return {
            bodyCollapsed: document.body.classList.contains('sidebar-collapsed'),
            bodyPinned: document.body.classList.contains('sidebar-pinned'),
            hoverExpanded: document.body.classList.contains('sidebar-hover-expanded'),
            sidebarExpanded: sidebar?.classList.contains('sidebar-expanded') || false,
            sidebarWidth: Math.round(sidebar.getBoundingClientRect().width)
          };
        })()
        """,
        timeout_ms=60000,
    )
    result["sidebar_open_1920"] = save_screenshot(window, "sidebar-open-1920.png")
    return result


def inspect_navigation(window: WebMainWindow) -> dict[str, object]:
    js = """
    (() => {
      const targets = [
        { key: 'dashboard', label: 'Dashboard', run: () => showSection('home'), page: 'home', navPage: 'home' },
        { key: 'bulk', label: 'Toplu Üretim', run: () => showSection('bulkLabel'), page: 'bulkLabel', navPage: 'bulkLabel' },
        { key: 'labelStudio', label: 'Etiket Studio', run: () => openLabelStudio(), page: 'label', navPage: 'label' },
        { key: 'manualLabel', label: 'Manuel Etiket', run: () => openManualLabelStudio(), page: 'label', navPage: 'manualLabel' },
        { key: 'trendyol', label: 'Trendyol Siparişleri', run: () => openTrendyolSidebarTab('orders'), page: 'trendyolOrders', navPage: 'trendyolOrders', trendyolTab: 'orders' },
        { key: 'printQueue', label: 'Yazdırma Sırası', run: () => showSection('printQueue'), page: 'printQueue', navPage: 'printQueue' },
        { key: 'nameCut', label: 'İsim Kesim', run: () => showSection('nameCutStudio'), page: 'nameCutStudio', navPage: 'nameCutStudio' },
        { key: 'audit', label: 'Üretim Geçmişi', run: () => showSection('productionAudit'), page: 'productionAudit', navPage: 'productionAudit' },
        { key: 'settingsGeneral', label: 'Ayarlar', run: () => openSettingsSubpage('general'), page: 'settings', navPage: 'settings', settingsSubpage: 'general' },
        { key: 'integrations', label: 'Entegrasyonlar', run: () => openSettingsSubpage('trendyol-api'), page: 'settings', navPage: 'settings', settingsSubpage: 'trendyol-api' },
        { key: 'printerProfiles', label: 'Yazıcı Profilleri', run: () => openSettingsSubpage('printer-profiles'), page: 'settings', navPage: 'settings', settingsSubpage: 'printer-profiles' },
        { key: 'dataMaintenance', label: 'Veri Bakımı', run: () => openSettingsSubpage('data-maintenance'), page: 'settings', navPage: 'settings', settingsSubpage: 'data-maintenance' }
      ];
      const rows = [];
      for (const target of targets) {
        target.run();
        const activePage = document.querySelector('.page.active')?.id || '';
        const activeNav = document.querySelector('.nav-btn.active');
        const panel = target.settingsSubpage ? document.querySelector(`[data-settings-panel="${target.settingsSubpage}"]`) : null;
        rows.push({
          key: target.key,
          label: target.label,
          expectedPage: target.page,
          activePage,
          activeNavPage: activeNav?.dataset.page || '',
          activeSettingsSubpage: activeNav?.dataset.settingsSubpage || '',
          activeTrendyolTab: activeNav?.dataset.trendyolSidebarTab || '',
          title: document.querySelector('.page.active h1, .page.active h2, .page.active .page-title')?.innerText?.trim() || '',
          hasVisibleContent: ((document.querySelector('.page.active')?.innerText || '').trim().length > 20),
          hasSettingsPanel: target.settingsSubpage ? Boolean(panel) : true,
          okPage: activePage === target.page,
          okNav: target.settingsSubpage
            ? (activeNav?.dataset.page === 'settings' && activeNav?.dataset.settingsSubpage === target.settingsSubpage)
            : target.trendyolTab
              ? (activeNav?.dataset.trendyolSidebarTab === target.trendyolTab)
              : (activeNav?.dataset.page === target.navPage)
        });
      }
      const brokenNavButtons = [...document.querySelectorAll('.nav-btn[data-page]')].map((button) => {
        const page = button.dataset.page;
        const special = ['manualLabel'].includes(page);
        const exists = Boolean(document.getElementById(page));
        return {
          text: button.innerText.trim().replace(/\\s+/g, ' '),
          page,
          settingsSubpage: button.dataset.settingsSubpage || '',
          trendyolTab: button.dataset.trendyolSidebarTab || '',
          ok: exists || special || button.dataset.settingsSubpage || button.dataset.trendyolSidebarTab
        };
      }).filter((row) => !row.ok);
      return { rows, brokenNavButtons };
    })()
    """
    return run_js(window, js, timeout_ms=90000)


def inspect_responsive(window: WebMainWindow) -> dict[str, object]:
    result: dict[str, object] = {}
    window.resize(1366, 768)
    wait(900)
    result["overflow_1366"] = run_js(
        window,
        """
        (() => {
          showSection('printQueue');
          setSidebarCollapsed(true, { persist: false, pin: false });
          const root = document.documentElement;
          const main = document.querySelector('.main');
          const body = document.body;
          return {
            viewport: window.innerWidth,
            docScrollWidth: root.scrollWidth,
            bodyScrollWidth: body.scrollWidth,
            mainClientWidth: main?.clientWidth || 0,
            mainScrollWidth: main?.scrollWidth || 0,
            hasCriticalPrintActions: [...document.querySelectorAll('#printQueue button')].some((btn) => /Yazdır|PDF|Sıradan|Teslim|Hazır/i.test(btn.innerText || '')),
            activePage: document.querySelector('.page.active')?.id || ''
          };
        })()
        """,
        timeout_ms=60000,
    )
    window.resize(1920, 1080)
    wait(900)
    result["readable_1920"] = run_js(
        window,
        """
        (() => {
          showSection('bulkLabel');
          setSidebarCollapsed(false, { persist: false, pin: true });
          const text = document.querySelector('.page.active')?.innerText || '';
          return {
            viewport: window.innerWidth,
            activePage: document.querySelector('.page.active')?.id || '',
            hasBulkTitle: text.includes('Toplu Üretim'),
            hasSourceCards: text.includes('Excel') && text.includes('Trendyol') && text.includes('Manuel'),
            bodyClasses: document.body.className
          };
        })()
        """,
        timeout_ms=60000,
    )
    return result


def capture_main_screens(window: WebMainWindow) -> dict[str, str]:
    screenshots: dict[str, str] = {}
    screens = [
        ("dashboard", "dashboard", "showSection('home')"),
        ("bulk-production", "bulkLabel", "showSection('bulkLabel')"),
        ("label-studio", "label", "openLabelStudio()"),
        ("trendyol-orders", "trendyolOrders", "openTrendyolSidebarTab('orders')"),
        ("print-queue", "printQueue", "showSection('printQueue')"),
        ("namecut", "nameCutStudio", "showSection('nameCutStudio')"),
        ("production-audit", "productionAudit", "showSection('productionAudit')"),
        ("settings-integrations", "settings", "openSettingsSubpage('trendyol-api')"),
        ("data-maintenance", "settings", "openSettingsSubpage('data-maintenance')"),
    ]
    for width, height, suffix in [(1366, 768, "1366"), (1920, 1080, "1920")]:
        window.resize(width, height)
        wait(650)
        for name, _page, command in screens:
            path = OUTPUT_DIR / f"{name}-{suffix}.png"
            if path.exists():
                screenshots[f"{name}_{suffix}"] = str(path)
                continue
            run_js(
                window,
                f"""
                (() => {{
                  {command};
                  if ({width} === 1366) setSidebarCollapsed(true, {{ persist: false, pin: false }});
                  else setSidebarCollapsed(false, {{ persist: false, pin: true }});
                  return document.querySelector('.page.active')?.id || '';
                }})()
                """,
                timeout_ms=60000,
            )
            screenshots[f"{name}_{suffix}"] = save_screenshot(window, f"{name}-{suffix}.png")
    return screenshots


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    try:
        window.resize(1366, 768)
        window.show()
        window.raise_()
        window.activateWindow()
        wait(2200)
        sidebar = inspect_sidebar_behavior(window)
        navigation = inspect_navigation(window)
        responsive = inspect_responsive(window)
        screenshots = capture_main_screens(window)

        collapsed = sidebar["collapsed_state"]
        hover = sidebar["hover_state"]
        leave = sidebar["leave_state"]
        pinned = sidebar["pinned_state"]
        assert_true(collapsed.get("bodyCollapsed") is True, "Sidebar collapsed state body class üretmedi.", failures)
        assert_true(collapsed.get("sidebarExpanded") is False, "Collapsed sidebar geniş görünümde kaldı.", failures)
        assert_true(hover.get("hoverExpanded") is True, "Collapsed sidebar hover ile açılmadı.", failures)
        assert_true(hover.get("sidebarExpanded") is True, "Hover-expanded sidebar expanded class almadı.", failures)
        assert_true(int(hover.get("sidebarWidth") or 0) >= 220, "Hover-expanded sidebar yeterli genişliğe çıkmadı.", failures)
        assert_true(leave.get("hoverExpanded") is False, "Mouse leave sonrası hover-expanded temizlenmedi.", failures)
        assert_true(leave.get("bodyCollapsed") is True, "Mouse leave sonrası sidebar collapsed kalmadı.", failures)
        assert_true(pinned.get("bodyPinned") is True, "Manuel açık/pinned state korunmadı.", failures)
        assert_true(pinned.get("bodyCollapsed") is False, "Pinned açık sidebar collapsed kaldı.", failures)
        assert_true(int(pinned.get("sidebarWidth") or 0) >= 220, "Pinned sidebar açık genişliğe ulaşmadı.", failures)

        nav_rows = navigation.get("rows", [])
        assert_true(not navigation.get("brokenNavButtons"), f"Boş/broken nav butonları var: {navigation.get('brokenNavButtons')}", failures)
        for row in nav_rows:
            assert_true(row.get("okPage") is True, f"{row.get('label')} yanlış page açtı: {row}", failures)
            assert_true(row.get("okNav") is True, f"{row.get('label')} aktif nav vurgusu yanlış: {row}", failures)
            assert_true(row.get("hasVisibleContent") is True, f"{row.get('label')} görünür içerik üretmedi.", failures)
            assert_true(row.get("hasSettingsPanel") is True, f"{row.get('label')} ayar paneli bulunamadı.", failures)

        overflow = responsive["overflow_1366"]
        max_width = max(int(overflow.get("docScrollWidth") or 0), int(overflow.get("bodyScrollWidth") or 0))
        assert_true(max_width <= 1388, f"1366 görünümde kontrolsüz yatay taşma var: {overflow}", failures)
        assert_true(overflow.get("hasCriticalPrintActions") is True, "Yazdırma Sırası kritik aksiyonları görünür değil.", failures)
        readable = responsive["readable_1920"]
        assert_true(readable.get("hasBulkTitle") is True, "1920 Toplu Üretim başlığı okunmuyor.", failures)
        assert_true(readable.get("hasSourceCards") is True, "1920 Toplu Üretim kaynak kartları görünmüyor.", failures)

        all_screen_paths = set(screenshots.values())
        assert_true(len(all_screen_paths) >= 18, "Ana ekran screenshot seti eksik.", failures)

        result = {
            "status": "PASS" if not failures else "FAIL",
            "failures": failures,
            "sidebar": sidebar,
            "navigation": navigation,
            "responsive": responsive,
            "screenshots": {
                "sidebar_collapsed_1366": sidebar.get("sidebar_collapsed_1366"),
                "sidebar_hover_expanded_1366": sidebar.get("sidebar_hover_expanded_1366"),
                "sidebar_open_1920": sidebar.get("sidebar_open_1920"),
                **screenshots,
            },
            "safety": {
                "printer_started": False,
                "laser_started": False,
                "rdworks_started": False,
                "trendyol_live_action": False,
            },
        }
    except Exception as exc:  # noqa: BLE001
        result = {"status": "ERROR", "error": str(exc), "failures": failures}
    finally:
        window.close()
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
