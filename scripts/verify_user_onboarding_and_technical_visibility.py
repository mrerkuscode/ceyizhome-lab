from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "user_onboarding_visibility"
RESULT_PATH = OUTPUT_DIR / "VERIFY_USER_ONBOARDING_AND_TECHNICAL_VISIBILITY_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 90000):
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
        return JSON.stringify({{ "__error": String(error && error.message || error), stack: String(error && error.stack || "") }});
      }}
    }})()
    """
    window.view.page().runJavaScript(wrapped, callback)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if not result["done"]:
        raise RuntimeError(f"JavaScript timed out: {script[:160]}")
    value = result["value"]
    parsed = json.loads(value) if isinstance(value, str) else value
    if isinstance(parsed, dict) and parsed.get("__error"):
        raise RuntimeError(f"{parsed['__error']}\n{parsed.get('stack', '')}")
    return parsed


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    QApplication.processEvents()
    wait(250)
    window.view.grab().save(str(path))
    if not path.exists() or path.stat().st_size <= 0:
        raise AssertionError(f"Screenshot kaydedilemedi: {filename}")
    return str(path)


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def run_gate(window: WebMainWindow) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    run_js(window, "(() => { showSection('home'); openHelpCenter('tour'); return { ok: true }; })()")
    wait(900)
    help_state = run_js(window, """
    (() => ({
      modalOpen: !document.getElementById('helpCenterModal')?.hidden,
      quickstartCount: document.querySelectorAll('.help-quickstart-strip article').length,
      tourText: document.getElementById('helpTourBody')?.innerText || '',
      helpText: document.getElementById('helpCenterModal')?.innerText || '',
      modalBottom: document.querySelector('#helpCenterModal .modal-card')?.getBoundingClientRect?.().bottom || 9999
    }))()
    """)
    assert_true(help_state["modalOpen"], "Yardım merkezi açılmadı", help_state)
    assert_true(int(help_state["quickstartCount"]) == 4, "Hızlı başlangıç şeridi eksik", help_state)
    assert_true("Model" in str(help_state["tourText"]) or "model" in str(help_state["tourText"]), "İlk kullanım turu model adımı göstermiyor", help_state)
    assert_true("otomatik" in str(help_state["helpText"]).lower() or "yazıcı" in str(help_state["helpText"]).lower(), "Yazdırma güvenliği yardımda görünmüyor", help_state)
    assert_true(float(help_state["modalBottom"]) <= 980, "Yardım modalı viewport dışına taşıyor", help_state)
    screenshots["help_tour"] = save_screenshot(window, "help_tour.png")
    checks.append({"name": "help_center_tour_and_quickstart", "status": "PASSED", "state": help_state})

    run_js(window, "(() => { selectHelpTab('shortcuts'); return { ok: true }; })()")
    wait(400)
    shortcut_state = run_js(window, """
    (() => ({
      visible: !document.getElementById('helpShortcutsPanel')?.hidden,
      shortcutCount: document.querySelectorAll('#helpShortcutsPanel .shortcut-grid div').length,
      text: document.getElementById('helpShortcutsPanel')?.innerText || ''
    }))()
    """)
    assert_true(shortcut_state["visible"], "Kısayollar sekmesi açılmadı", shortcut_state)
    assert_true(int(shortcut_state["shortcutCount"]) >= 5, "Kısayol kartları eksik", shortcut_state)
    screenshots["help_shortcuts"] = save_screenshot(window, "help_shortcuts.png")
    checks.append({"name": "help_shortcuts_panel", "status": "PASSED", "state": shortcut_state})

    run_js(window, "(() => { closeHelpCenter(); showSection('home'); return { ok: true }; })()")
    wait(500)
    technical_state = run_js(window, """
    (() => {
      const nav = document.querySelector('.technical-nav');
      const technicalButtons = [...document.querySelectorAll('.technical-nav .nav-btn.technical')];
      return {
        activePage: document.querySelector('.page.active')?.id || '',
        technicalOpen: Boolean(nav?.open),
        technicalButtonVisibleCount: technicalButtons.filter(btn => {
          const r = btn.getBoundingClientRect();
          return r.width > 10 && r.height > 10 && r.bottom > 0;
        }).length,
        safeText: document.querySelector('.system-card')?.innerText || ''
      };
    })()
    """)
    assert_true(technical_state["activePage"] == "home", "Ana sayfa aktif değil", technical_state)
    assert_true(not technical_state["technicalOpen"], "Teknik araçlar varsayılan açık kalmış", technical_state)
    assert_true(int(technical_state["technicalButtonVisibleCount"]) == 0, "Teknik butonlar varsayılan görünümde açık", technical_state)
    assert_true("Direct Print" in str(technical_state["safeText"]) and ("Kapalı" in str(technical_state["safeText"]) or "Kapal" in str(technical_state["safeText"])), "Güvenlik özeti görünmüyor", technical_state)
    screenshots["technical_collapsed"] = save_screenshot(window, "technical_collapsed.png")
    checks.append({"name": "technical_tools_collapsed_by_default", "status": "PASSED", "state": technical_state})

    run_js(window, "(() => { showSection('reports'); selectReport('release'); return { ok: true }; })()")
    wait(900)
    release_state = run_js(window, """
    (() => ({
      activePage: document.querySelector('.page.active')?.id || '',
      reportText: document.getElementById('reportBox')?.innerText || '',
      releaseCardCount: document.querySelectorAll('#reportBox .release-evidence-card').length
    }))()
    """)
    assert_true(release_state["activePage"] == "reports", "Raporlar sayfası açılmadı", release_state)
    assert_true("Release" in str(release_state["reportText"]) or int(release_state["releaseCardCount"]) >= 2, "Release dashboard kanıtları görünmüyor", release_state)
    screenshots["release_dashboard"] = save_screenshot(window, "release_dashboard.png")
    checks.append({"name": "release_dashboard_visible", "status": "PASSED", "state": release_state})

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1680, 980)
    window.show()
    wait(6500)
    try:
        result = run_gate(window)
    finally:
        window.close()
        app.quit()
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
