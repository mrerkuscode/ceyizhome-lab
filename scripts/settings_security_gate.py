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
from webui_backend import settings_api  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "settings_security_gate"
RESULT_PATH = OUTPUT_DIR / "SETTINGS_SECURITY_GATE_RESULT.json"


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


def page_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => ({
      activePage: document.querySelector('.page.active')?.id || '',
      safetyText: document.getElementById('settingsSafetyStrip')?.innerText || '',
      securityText: document.getElementById('settingsSecurityList')?.innerText || '',
      backupText: document.getElementById('settingsBackupInfo')?.innerText || '',
      folderText: document.getElementById('settingsOutputFolders')?.innerText || '',
      fontColorText: document.getElementById('settingsFontColorInfo')?.innerText || '',
      widthInput: document.getElementById('settingsWidthMm')?.value || '',
      heightInput: document.getElementById('settingsHeightMm')?.value || '',
      rollWidthInput: document.getElementById('settingsRollWidthMm')?.value || '',
      rollGapInput: document.getElementById('settingsRollGapMm')?.value || '',
      saveStatus: document.getElementById('settingsSaveStatus')?.textContent || '',
      hasSaveButton: Boolean([...document.querySelectorAll('#settings button')].find(button => (button.textContent || '').includes('Ayarları Kaydet'))),
      hasAdvancedButton: Boolean([...document.querySelectorAll('#settings button')].find(button => (button.textContent || '').includes('Gelişmiş Ayar'))),
      directPrintAllowed: Boolean((currentState.print || {}).allow_direct_print),
      defaults: currentState.labelDefaults || {}
    }))()
    """)


def save_center_settings(window: WebMainWindow, payload: dict[str, object]) -> dict[str, object]:
    run_js(
        window,
        f"""
        (() => {{
          window.__settingsGateResult = null;
          bridge.save_label_defaults_json({json.dumps(json.dumps(payload, ensure_ascii=False))}, raw => {{
            try {{ window.__settingsGateResult = JSON.parse(raw); }}
            catch (error) {{ window.__settingsGateResult = {{ status: 'ERROR', message: String(raw || error) }}; }}
          }});
          return {{ started: true }};
        }})()
        """,
        timeout_ms=60000,
    )
    for _ in range(80):
        wait(250)
        result = run_js(window, "(() => window.__settingsGateResult || null)()", timeout_ms=10000)
        if result:
            return result
    return {"status": "ERROR", "message": "Ayar kayıt cevabı zamanında dönmedi."}


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}
    original = settings_api.get_label_defaults(PROJECT_ROOT)
    original_backups = settings_api.list_settings_backups(PROJECT_ROOT, limit=50)

    run_js(window, "(() => { showSection('settings'); updateSettings(currentState); return { ok: true }; })()", timeout_ms=60000)
    wait(1200)
    first = page_state(window)
    assert_true(first["activePage"] == "settings", "Ayarlar sayfası açılmadı", first)
    assert_true(first["hasSaveButton"], "Sayfa içi Ayarları Kaydet butonu yok", first)
    assert_true("Direct Print" in str(first["safetyText"]) and "Kapalı" in str(first["safetyText"]), "Direct print güvenlik satırı yok", first)
    assert_true("Yazıcı otomatik çalışmaz" in str(first["safetyText"]), "Yazıcı güvenlik mesajı yok", first)
    assert_true("AI/CDR" in str(first["securityText"]) and "Değiştirilmez" in str(first["securityText"]), "Kaynak dosya güvenliği görünmüyor", first)
    assert_true("Çıktı klasörü" in str(first["folderText"]), "Çıktı klasörü bölümü yok", first)
    assert_true("Varsayılan font" in str(first["fontColorText"]), "Font ve renk bölümü yok", first)
    screenshots["settings_page"] = save_screenshot(window, "settings_security_center_page.png")
    checks.append({"name": "settings_security_center_visible", "status": "PASSED", "state": first})

    trial = {
        **original,
        "media_type": "ROLL",
        "label_width_mm": float(original.get("label_width_mm") or 40),
        "label_height_mm": float(original.get("label_height_mm") or 40),
        "roll_width_mm": float(original.get("roll_width_mm") or original.get("label_width_mm") or 40),
        "roll_gap_mm": float(original.get("roll_gap_mm") or 3),
        "printer_dpi": int(original.get("printer_dpi") or 300),
        "default_copies": int(original.get("default_copies") or 1),
        "scale_percent": float(original.get("scale_percent") or 100),
        "safe_margin_mm": float(original.get("safe_margin_mm") or 1.5),
        "background_enabled": bool(original.get("background_enabled", True)),
        "show_cut_boundary": bool(original.get("show_cut_boundary", False)),
        "show_order_number_on_label": bool(original.get("show_order_number_on_label", False)),
    }
    trial["safe_margin_mm"] = round(float(trial["safe_margin_mm"]) + 0.1, 1)
    saved = save_center_settings(window, trial)
    assert_true(saved.get("status") == "OK", "Ayar kaydı başarısız", saved)
    wait(900)
    after_save = page_state(window)
    backups_after_save = settings_api.list_settings_backups(PROJECT_ROOT, limit=50)
    config_after_save = settings_api.load_config(PROJECT_ROOT)
    assert_true(len(backups_after_save) >= len(original_backups) + 1, "Ayar kaydı backup oluşturmadı", backups_after_save)
    assert_true(config_after_save.get("print", {}).get("allow_direct_print") is False, "Direct print kapalı kalmadı", config_after_save.get("print"))
    assert_true(config_after_save.get("print", {}).get("require_print_confirmation") is True, "Yazdırma onayı korunmadı", config_after_save.get("print"))
    assert_true(abs(float(settings_api.get_label_defaults(PROJECT_ROOT).get("safe_margin_mm") or 0) - float(trial["safe_margin_mm"])) < 0.001, "Inline ayar kaydı config'e yazılmadı", settings_api.get_label_defaults(PROJECT_ROOT))
    screenshots["settings_after_save"] = save_screenshot(window, "settings_after_save.png")
    checks.append({"name": "settings_save_creates_backup_and_preserves_safety", "status": "PASSED", "state": after_save})

    restored = save_center_settings(window, original)
    assert_true(restored.get("status") == "OK", "Ayar restore başarısız", restored)
    wait(900)
    restored_config = settings_api.load_config(PROJECT_ROOT)
    assert_true(restored_config.get("print", {}).get("allow_direct_print") is False, "Restore sonrası direct print kapalı kalmadı", restored_config.get("print"))
    assert_true(restored_config.get("print", {}).get("require_print_confirmation") is True, "Restore sonrası yazdırma onayı korunmadı", restored_config.get("print"))
    checks.append({"name": "settings_restore_preserves_safety", "status": "PASSED", "state": page_state(window)})

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
