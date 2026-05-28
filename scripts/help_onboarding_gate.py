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


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "help_onboarding_gate"
RESULT_PATH = OUTPUT_DIR / "HELP_ONBOARDING_GATE_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 60000):
    loop = QEventLoop()
    result = {"value": None, "done": False}

    def callback(value):
        result["value"] = value
        result["done"] = True
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
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict) and parsed.get("__error"):
            raise RuntimeError(f"{parsed['__error']}\n{parsed.get('stack', '')}")
        return parsed
    return value


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    window.view.grab().save(str(path))
    return str(path)


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def help_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => ({
      modalOpen: !document.getElementById('helpCenterModal')?.hidden,
      activePage: document.querySelector('.page.active')?.id || '',
      tourHidden: document.getElementById('helpTourPanel')?.hidden ?? true,
      shortcutsHidden: document.getElementById('helpShortcutsPanel')?.hidden ?? true,
      fixesHidden: document.getElementById('helpFixesPanel')?.hidden ?? true,
      tourTitle: document.getElementById('helpTourTitle')?.textContent || '',
      tourBody: document.getElementById('helpTourBody')?.innerText || '',
      shortcutText: document.getElementById('helpShortcutsPanel')?.innerText || '',
      fixesText: document.getElementById('helpFixesPanel')?.innerText || '',
      checklistHidden: document.getElementById('helpChecklistPanel')?.hidden ?? true,
      checklistText: document.getElementById('helpChecklistPanel')?.innerText || '',
      hasTargetButton: Boolean([...document.querySelectorAll('#helpCenterModal button')].find(button => (button.textContent || '').includes('Bu adıma git'))),
      consoleErrors: window.__helpGateErrors || []
    }))()
    """)


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    run_js(window, """
    (() => {
      window.__helpGateErrors = [];
      window.onerror = (message, source, line, column, error) => {
        window.__helpGateErrors.push(String(message || error || 'unknown'));
      };
      openHelpCenter();
      return { ok: true };
    })()
    """)
    wait(800)
    first = help_state(window)
    assert_true(first["modalOpen"], "Yardım merkezi açılmadı", first)
    assert_true(not first["tourHidden"], "İlk kullanım paneli görünmüyor", first)
    assert_true("Model seç" in str(first["tourTitle"]), "Tur ilk adımı yanlış", first)
    assert_true(first["hasTargetButton"], "Tur hedefe git butonu yok", first)
    assert_true(not first["consoleErrors"], "Yardım açılırken console error var", first)
    screenshots["help_tour"] = save_screenshot(window, "help_tour.png")
    checks.append({"name": "help_tour_opens", "status": "PASSED", "state": first})

    run_js(window, "(() => { nextHelpTourStep(); nextHelpTourStep(); return { ok: true }; })()")
    wait(400)
    next_state = help_state(window)
    assert_true("Taşı" in str(next_state["tourTitle"]) or "boyutlandır" in str(next_state["tourBody"]), "Tur sonraki adımlara ilerlemiyor", next_state)
    checks.append({"name": "help_tour_navigation", "status": "PASSED", "state": next_state})

    run_js(window, "(() => { selectHelpTab('shortcuts'); return { ok: true }; })()")
    wait(400)
    shortcuts = help_state(window)
    assert_true(not shortcuts["shortcutsHidden"], "Kısayollar paneli görünmüyor", shortcuts)
    assert_true("Ctrl + Z" in str(shortcuts["shortcutText"]) and "Shift + Arrow" in str(shortcuts["shortcutText"]), "Kısayol içerikleri eksik", shortcuts)
    screenshots["help_shortcuts"] = save_screenshot(window, "help_shortcuts.png")
    checks.append({"name": "help_shortcuts_visible", "status": "PASSED", "state": shortcuts})

    run_js(window, "(() => { selectHelpTab('fixes'); return { ok: true }; })()")
    wait(400)
    fixes = help_state(window)
    assert_true(not fixes["fixesHidden"], "Sorun çöz paneli görünmüyor", fixes)
    assert_true("Görsel eksik" in str(fixes["fixesText"]) and "Queue" in str(fixes["fixesText"]), "Hata çözüm kartları eksik", fixes)
    screenshots["help_fixes"] = save_screenshot(window, "help_fixes.png")
    checks.append({"name": "help_fix_cards_visible", "status": "PASSED", "state": fixes})

    run_js(window, "(() => { selectHelpTab('checklist'); return { ok: true }; })()")
    wait(400)
    checklist = help_state(window)
    assert_true(not checklist["checklistHidden"], "Üretim kontrolü paneli görünmüyor", checklist)
    assert_true("Tek Etiket" in str(checklist["checklistText"]) and "Yazıcı otomatik çalışmaz" in str(checklist["checklistText"]), "Üretim kontrolü içerikleri eksik", checklist)
    screenshots["help_checklist"] = save_screenshot(window, "help_checklist.png")
    checks.append({"name": "help_checklist_visible", "status": "PASSED", "state": checklist})

    run_js(window, "(() => { selectHelpTab('tour'); helpTourIndex = 1; renderHelpTour(); goHelpTarget(); return { ok: true }; })()")
    wait(600)
    target = help_state(window)
    assert_true(target["activePage"] == "label", "Tur hedef butonu Etiket Studio'ya götürmedi", target)
    assert_true(not target["modalOpen"], "Hedefe gidince modal kapanmadı", target)
    checks.append({"name": "help_target_navigation", "status": "PASSED", "state": target})

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots}


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1440, 950)
    window.show()
    wait(6500)
    try:
        result = run_gate(window)
    finally:
        window.close()
        app.quit()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
