from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-22" / "production_live_integration_dryrun_phase25"
RESULT_PATH = OUTPUT_DIR / "production_live_integration_dryrun_phase25_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import live_integration_guard_api, production_audit_api  # noqa: E402


DATA_FILES = [
    PROJECT_ROOT / "data" / "production_audit_log.json",
    PROJECT_ROOT / "data" / "live_integration_security.json",
]


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
    wait(700)
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def backup_data() -> dict[Path, str | None]:
    return {path: path.read_text(encoding="utf-8") if path.exists() else None for path in DATA_FILES}


def restore_data(backup: dict[Path, str | None]) -> None:
    for path, content in backup.items():
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def reset_phase25_data() -> None:
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)
    (PROJECT_ROOT / "data" / "production_audit_log.json").write_text("[]", encoding="utf-8")
    settings = live_integration_guard_api.DEFAULT_SETTINGS.copy()
    settings["updated_at"] = "2026-05-22 00:00:00"
    (PROJECT_ROOT / "data" / "live_integration_security.json").write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_backend_checks(window: WebMainWindow) -> dict[str, object]:
    reset_phase25_data()
    run_id = f"phase25-{int(time.time())}"
    registry = window.live_integration_registry()
    settings = window.live_integration_security_settings()
    saved = window.save_live_integration_security_settings({"direct_print_enabled": True, "dry_run_only": False})
    no_operator = window.guard_live_integration_action(
        "trendyol_status_update",
        {"source_item_id": f"ty-{run_id}", "order_no": "TY-25", "title": "Phase 25 Statü"},
        admin_confirmed=True,
        operator_confirmed=False,
        dry_run=True,
    )
    no_admin = window.guard_live_integration_action(
        "trendyol_shipping_label",
        {"source_item_id": f"ty-ship-{run_id}", "order_no": "TY-25", "title": "Phase 25 Kargo"},
        admin_confirmed=False,
        operator_confirmed=True,
        dry_run=True,
    )
    dry_run = window.guard_live_integration_action(
        "direct_print",
        {"source_item_id": f"queue-{run_id}", "file_path": "output/phase25.pdf", "printer_name": "Manuel PDF"},
        admin_confirmed=True,
        operator_confirmed=True,
        dry_run=True,
    )
    blocked_live = window.guard_live_integration_action(
        "laser_send",
        {"source_item_id": f"laser-{run_id}", "laser_name": "Ayse"},
        admin_confirmed=True,
        operator_confirmed=True,
        dry_run=False,
    )
    unknown = window.guard_live_integration_action(
        "unknown_live_action",
        {"source_item_id": f"unknown-{run_id}"},
        admin_confirmed=True,
        operator_confirmed=True,
        dry_run=True,
    )
    audit_rows = production_audit_api.list_production_audit_events(PROJECT_ROOT, {"source": "integration_guard"})
    return {
        "registry": registry,
        "settings": settings,
        "saved": saved,
        "no_operator": no_operator,
        "no_admin": no_admin,
        "dry_run": dry_run,
        "blocked_live": blocked_live,
        "unknown": unknown,
        "audit_event_types": [row.get("event_type") for row in audit_rows],
        "audit_blob": json.dumps(audit_rows, ensure_ascii=False),
    }


def run_ui_checks(window: WebMainWindow) -> dict[str, object]:
    result: dict[str, object] = {}
    window.resize(1920, 1080)
    wait(900)
    result["settings"] = run_js(window, """
    (() => {
      refreshState();
      showSection('settings');
      updateSettings(currentState);
      document.querySelector('.live-integration-security-card')?.scrollIntoView({block:'center'});
      const text = document.getElementById('settings')?.innerText || '';
      return {
        activePage: document.querySelector('.page.active')?.id || '',
        hasSecurity: text.includes('Entegrasyon Güvenliği'),
        hasDryRun: text.includes('Dry-run'),
        hasLiveClosed: text.includes('Canlı entegrasyon bağlı değil'),
        registryCount: document.querySelectorAll('.integration-risk-row').length
      };
    })()
    """, timeout_ms=60000)
    result["settings_1920"] = save_screenshot(window, "integration-security-settings-1920.png")

    result["modal_open"] = run_js(window, """
    (() => {
      openIntegrationDryRunModal('trendyol_status_update', { source_item_id: 'ty-ui-25', order_no: 'TY-UI-25', title: 'UI dry-run' });
      const text = document.getElementById('integrationDryRunModal')?.innerText || '';
      return {
        hidden: document.getElementById('integrationDryRunModal')?.hidden,
        hasNoLive: text.includes('Canlı entegrasyon bağlı değil'),
        hasAdmin: text.includes('Yönetici onayı gerekli'),
        hasDryRun: text.includes('Dry-run')
      };
    })()
    """, timeout_ms=60000)
    result["dryrun_modal"] = save_screenshot(window, "integration-dryrun-modal.png")

    run_js(window, """
    (() => {
      document.getElementById('integrationDryRunOperatorApproval').checked = true;
      document.getElementById('integrationDryRunAdminApproval').checked = false;
      completeIntegrationDryRun();
      return true;
    })()
    """, timeout_ms=60000)
    wait(1400)
    result["permission_ui"] = run_js(window, """
    (() => ({
      result: document.getElementById('integrationDryRunResult')?.innerText || '',
      status: document.getElementById('liveIntegrationSecurityStatus')?.innerText || ''
    }))()
    """, timeout_ms=60000)
    result["permission_required"] = save_screenshot(window, "integration-permission-required.png")

    run_js(window, """
    (() => {
      document.getElementById('integrationDryRunOperatorApproval').checked = true;
      document.getElementById('integrationDryRunAdminApproval').checked = true;
      completeIntegrationDryRun();
      return true;
    })()
    """, timeout_ms=60000)
    wait(1600)
    result["dryrun_completed_ui"] = run_js(window, """
    (() => ({
      result: document.getElementById('integrationDryRunResult')?.innerText || '',
      status: document.getElementById('liveIntegrationSecurityStatus')?.innerText || ''
    }))()
    """, timeout_ms=60000)
    result["live_action_blocked"] = save_screenshot(window, "integration-live-action-blocked.png")

    run_js(window, """
    (() => {
      closeIntegrationDryRunModal();
      showSection('productionAudit');
      updateProductionAudit(currentState.productionAudit || [], currentState.productionAuditSummary || {});
      return true;
    })()
    """, timeout_ms=60000)
    wait(1200)
    result["audit_ui"] = run_js(window, """
    (() => {
      const text = document.getElementById('productionAudit')?.innerText || '';
      return {
        hasDryRunCompleted: text.includes('integration_dry_run_completed') || text.includes('dry-run'),
        hasIntegrationGuard: text.includes('Entegrasyon') || text.includes('integration')
      };
    })()
    """, timeout_ms=60000)
    result["audit_events"] = save_screenshot(window, "integration-audit-events.png")

    window.resize(1366, 768)
    wait(900)
    run_js(window, """
    (() => {
      showSection('settings');
      updateSettings(currentState);
      document.querySelector('.live-integration-security-card')?.scrollIntoView({block:'center'});
      return true;
    })()
    """, timeout_ms=60000)
    result["settings_1366"] = save_screenshot(window, "integration-security-1366.png")
    return result


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backup = backup_data()
    failures: list[str] = []
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    try:
        wait(1800)
        backend = run_backend_checks(window)
        window._emit_state()
        ui = run_ui_checks(window)

        required_actions = {
            "trendyol_status_update",
            "trendyol_shipping_label",
            "trendyol_invoice",
            "direct_print",
            "laser_send",
            "rdworks_open_or_send",
        }
        registry = backend["registry"]
        assert_true(required_actions.issubset(set(registry)), "Tüm riskli aksiyonlar registry içinde değil.", failures)
        for action_key in required_actions:
            action = registry.get(action_key, {})
            assert_true(action.get("default_disabled") is True, f"{action_key} default disabled değil.", failures)
            assert_true(action.get("dry_run_only") is True, f"{action_key} dry_run_only değil.", failures)
            assert_true(action.get("requires_admin") is True, f"{action_key} admin onayı gerektirmiyor.", failures)
            assert_true(action.get("requires_operator_confirmation") is True, f"{action_key} operatör onayı gerektirmiyor.", failures)
            assert_true(action.get("audit_required") is True, f"{action_key} audit_required değil.", failures)
        saved_settings = backend["saved"].get("settings", {})
        assert_true(saved_settings.get("direct_print_enabled") is False, "Direct print ayarı açık kalmış.", failures)
        assert_true(saved_settings.get("dry_run_only") is True, "Dry-run only zorlanmadı.", failures)
        assert_true(backend["no_operator"].get("status") == "PERMISSION_REQUIRED", "Operatör onayı eksikliği yakalanmadı.", failures)
        assert_true(backend["no_admin"].get("status") == "PERMISSION_REQUIRED", "Yönetici onayı eksikliği yakalanmadı.", failures)
        assert_true(backend["dry_run"].get("status") == "DRY_RUN", "Dry-run sonucu DRY_RUN değil.", failures)
        assert_true(backend["blocked_live"].get("status") == "BLOCKED", "Dry-run dışı canlı çağrı engellenmedi.", failures)
        assert_true(backend["unknown"].get("status") == "NOT_CONFIGURED", "Bağlı olmayan aksiyon not configured dönmedi.", failures)
        assert_true(not backend["dry_run"].get("auto_print_started"), "Dry-run yazıcı başlattı.", failures)
        assert_true(not backend["dry_run"].get("laser_started"), "Dry-run lazer başlattı.", failures)
        assert_true(not backend["dry_run"].get("rdworks_started"), "Dry-run RDWorks başlattı.", failures)
        audit_types = set(backend["audit_event_types"])
        for event_type in {
            "integration_dry_run_started",
            "integration_dry_run_completed",
            "integration_permission_required",
            "integration_action_blocked",
            "integration_not_configured",
        }:
            assert_true(event_type in audit_types, f"{event_type} audit event oluşmadı.", failures)
        assert_true(ui["settings"].get("hasSecurity"), "Ayarlar ekranında Entegrasyon Güvenliği görünmüyor.", failures)
        assert_true(ui["settings"].get("registryCount", 0) >= 6, "UI registry satırları eksik.", failures)
        assert_true(ui["modal_open"].get("hasNoLive"), "Dry-run modal canlı entegrasyon kapalı dilini göstermiyor.", failures)
        assert_true("PERMISSION_REQUIRED" in ui["permission_ui"].get("result", ""), "Yetki gerekli uyarısı UI’da görünmedi.", failures)
        assert_true("DRY_RUN" in ui["dryrun_completed_ui"].get("result", ""), "Dry-run tamamlandı sonucu UI’da görünmedi.", failures)
        assert_true(ui["audit_ui"].get("hasIntegrationGuard"), "Audit ekranında entegrasyon guard eventleri görünmüyor.", failures)

        result = {
            "status": "PASS" if not failures else "FAIL",
            "failures": failures,
            "backend": backend,
            "ui": ui,
            "screenshots": {
                "settings_1920": ui.get("settings_1920"),
                "dryrun_modal": ui.get("dryrun_modal"),
                "permission_required": ui.get("permission_required"),
                "live_action_blocked": ui.get("live_action_blocked"),
                "audit_events": ui.get("audit_events"),
                "settings_1366": ui.get("settings_1366"),
            },
        }
    except Exception as exc:  # noqa: BLE001
        result = {"status": "ERROR", "error": str(exc), "failures": failures}
    finally:
        window.close()
        restore_data(backup)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
