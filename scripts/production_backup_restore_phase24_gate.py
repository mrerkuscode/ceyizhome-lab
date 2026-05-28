from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-22" / "production_backup_restore_phase24"
RESULT_PATH = OUTPUT_DIR / "production_backup_restore_phase24_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import backup_api, production_audit_api  # noqa: E402


DATA_FILES = [
    PROJECT_ROOT / "data" / "name_cut_queue.json",
    PROJECT_ROOT / "data" / "name_cut_transfer_history.json",
    PROJECT_ROOT / "data" / "name_cut_export_history.json",
    PROJECT_ROOT / "data" / "print_queue.json",
    PROJECT_ROOT / "data" / "production_audit_log.json",
    PROJECT_ROOT / "data" / "printer_profiles.json",
    PROJECT_ROOT / "data" / "trendyol_settings.json",
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


def seed_minimal_data() -> None:
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)
    (PROJECT_ROOT / "data" / "name_cut_queue.json").write_text("[]", encoding="utf-8")
    (PROJECT_ROOT / "data" / "name_cut_transfer_history.json").write_text("[]", encoding="utf-8")
    (PROJECT_ROOT / "data" / "name_cut_export_history.json").write_text("[]", encoding="utf-8")
    (PROJECT_ROOT / "data" / "print_queue.json").write_text("[]", encoding="utf-8")
    (PROJECT_ROOT / "data" / "production_audit_log.json").write_text("[]", encoding="utf-8")
    (PROJECT_ROOT / "data" / "trendyol_settings.json").write_text(
        json.dumps({"read_only_mode": True, "api_secret": "***"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (PROJECT_ROOT / "data" / "printer_profiles.json").write_text(
        json.dumps([{"printer_profile_id": "phase24-before", "profile_name": "Phase 24 Before"}], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def make_corrupt_backup(valid_backup_path: str) -> str:
    source = PROJECT_ROOT / valid_backup_path
    corrupt_dir = PROJECT_ROOT / "backups" / "2026-05-22" / "ceyizhome_lab_backup_phase24_corrupt"
    if corrupt_dir.exists():
        shutil.rmtree(corrupt_dir)
    shutil.copytree(source, corrupt_dir)
    corrupt_file = corrupt_dir / "data" / "printer_profiles.json"
    corrupt_file.parent.mkdir(parents=True, exist_ok=True)
    corrupt_file.write_text("{broken json", encoding="utf-8")
    return str(corrupt_dir.relative_to(PROJECT_ROOT))


def run_backend_checks(window: WebMainWindow) -> dict[str, object]:
    seed_minimal_data()
    created = window.create_backup()
    backup_path = str(created.get("backup_path") or "")
    manifest_path = PROJECT_ROOT / str(created.get("manifest_path") or "")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    (PROJECT_ROOT / "data" / "printer_profiles.json").write_text(
        json.dumps([{"printer_profile_id": "phase24-after", "profile_name": "Phase 24 After"}], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    dry_run = window.restore_backup(backup_path, True)
    restored = window.restore_backup(backup_path, False)
    restored_profiles = json.loads((PROJECT_ROOT / "data" / "printer_profiles.json").read_text(encoding="utf-8"))

    valid = window.validate_backup(backup_path)
    corrupt_path = make_corrupt_backup(backup_path)
    corrupt_validate = window.validate_backup(corrupt_path)
    corrupt_restore = window.restore_backup(corrupt_path, False)
    traversal_validate = window.validate_backup("backups/../../data")
    # The real restore intentionally restores production_audit_log too. Add fresh
    # post-restore audit events so the maintenance center reflects the latest run.
    post_restore_created = window.create_backup()
    post_restore_dry_run = window.restore_backup(backup_path, True)
    listed = window.list_backups()
    exported_manifest = window.export_backup_manifest(backup_path)
    audit_rows = production_audit_api.list_production_audit_events(PROJECT_ROOT, {"source": "backup"})

    return {
        "created": created,
        "manifest": manifest,
        "valid": valid,
        "dry_run": dry_run,
        "restored": restored,
        "restored_profiles": restored_profiles,
        "corrupt_path": corrupt_path,
        "corrupt_validate": corrupt_validate,
        "corrupt_restore": corrupt_restore,
        "traversal_validate": traversal_validate,
        "post_restore_created": post_restore_created,
        "post_restore_dry_run": post_restore_dry_run,
        "listed_count": len(listed),
        "exported_manifest": exported_manifest,
        "audit_event_types": [row.get("event_type") for row in audit_rows],
        "audit_blob": json.dumps(audit_rows, ensure_ascii=False),
    }


def run_ui_checks(window: WebMainWindow, backup_path: str, corrupt_path: str) -> dict[str, object]:
    result: dict[str, object] = {}
    window.resize(1920, 1080)
    wait(900)
    result["settings"] = run_js(window, """
    (() => {
      refreshState();
      showSection('settings');
      updateSettings(currentState);
      const text = document.getElementById('settings')?.innerText || '';
      return {
        activePage: document.querySelector('.page.active')?.id || '',
        hasDataMaintenance: /Veri Bakımı/.test(text),
        hasBackupCreate: /Yedek Oluştur/.test(text),
        hasDryRun: /Geri Yükleme Önizle/.test(text),
        hasNoLiveAction: /Yazıcı, lazer, RDWorks ve Trendyol tetiklenmez/.test(text)
      };
    })()
    """, timeout_ms=60000)
    result["maintenance_1920"] = save_screenshot(window, "data-maintenance-1920.png")

    run_js(window, "(() => { createDataBackup(); return true; })()", timeout_ms=60000)
    wait(2200)
    result["create_ui"] = run_js(window, """
    (() => ({
      status: document.getElementById('dataMaintenanceStatus')?.innerText || '',
      listText: document.getElementById('dataBackupList')?.innerText || ''
    }))()
    """, timeout_ms=60000)
    result["backup_create_success"] = save_screenshot(window, "backup-create-success.png")
    result["backup_list"] = save_screenshot(window, "backup-list.png")

    run_js(window, f"""
    (() => {{
      selectedDataBackupPath = {json.dumps(backup_path)};
      previewSelectedDataRestore();
      return true;
    }})()
    """, timeout_ms=60000)
    wait(1800)
    result["dry_run_ui"] = run_js(window, """
    (() => ({
      status: document.getElementById('dataMaintenanceStatus')?.innerText || '',
      preview: document.getElementById('dataRestorePreview')?.innerText || ''
    }))()
    """, timeout_ms=60000)
    result["restore_dry_run"] = save_screenshot(window, "restore-dry-run.png")

    run_js(window, f"""
    (() => {{
      selectedDataBackupPath = {json.dumps(corrupt_path)};
      validateSelectedDataBackup();
      return true;
    }})()
    """, timeout_ms=60000)
    wait(1800)
    result["corrupt_ui"] = run_js(window, """
    (() => ({
      status: document.getElementById('dataMaintenanceStatus')?.innerText || '',
      preview: document.getElementById('dataRestorePreview')?.innerText || ''
    }))()
    """, timeout_ms=60000)
    result["corrupt_warning"] = save_screenshot(window, "corrupt-backup-warning.png")

    restore_result = window.restore_backup(backup_path, False)
    result["restore_ui"] = run_js(window, f"""
    (() => {{
      const parsed = {json.dumps(restore_result, ensure_ascii=False)};
      renderDataRestorePreview(parsed);
      setDataMaintenanceStatus(parsed.message || 'Geri yükleme kontrol edildi.', parsed.status === 'OK' ? 'ok' : 'bad');
      return {{
        status: parsed.status,
        message: parsed.message || '',
        panel: document.getElementById('dataRestorePreview')?.innerText || ''
      }};
    }})()
    """, timeout_ms=60000)
    result["restore_success"] = save_screenshot(window, "restore-success.png")

    audit_rows = window.production_audit_events({"source": "backup"})
    audit_summary = window.production_audit_summary()
    result["audit_ui"] = run_js(window, f"""
    (() => {{
      currentState.productionAudit = {json.dumps(audit_rows, ensure_ascii=False)};
      currentState.productionAuditSummary = {json.dumps(audit_summary, ensure_ascii=False)};
      showSection('productionAudit');
      productionAuditFilterState.source = 'backup';
      productionAuditFilterState.query = '';
      updateProductionAudit(currentState.productionAudit || [], currentState.productionAuditSummary || {{}});
      const text = document.getElementById('productionAudit')?.innerText || '';
      return {{
        hasBackupCreated: /Yedek oluşturuldu|backup_created/.test(text),
        hasRestore: /Geri yükleme|restore/.test(text),
        hasAuditScreen: /Üretim Geçmişi/.test(text)
      }};
    }})()
    """, timeout_ms=60000)
    result["audit_events"] = save_screenshot(window, "backup-audit-events.png")

    window.resize(1366, 768)
    wait(900)
    run_js(window, "(() => { showSection('settings'); updateSettings(currentState); return true; })()", timeout_ms=60000)
    result["maintenance_1366"] = save_screenshot(window, "data-maintenance-1366.png")
    return result


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suppress_message_boxes()
    data_backup = backup_data()
    failures: list[str] = []
    result: dict[str, object] = {"phase": "24", "status": "RUNNING"}
    app = QApplication.instance() or QApplication(sys.argv)
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    try:
        window.show()
        wait(2000)
        backend = run_backend_checks(window)
        ui = run_ui_checks(window, str(backend["created"].get("backup_path")), str(backend["corrupt_path"]))

        manifest = backend["manifest"]
        assert_true(backend["created"].get("status") == "OK", "Backup gerçek dosya/manifest oluşturmadı.", failures)
        assert_true(bool(manifest.get("files")), "Manifest içinde dosya listesi yok.", failures)
        assert_true(all(entry.get("sha256") for entry in manifest.get("files", [])), "Checksum summary eksik.", failures)
        assert_true(backend["valid"].get("valid") is True, "Valid backup doğrulanmadı.", failures)
        assert_true(backend["dry_run"].get("status") == "DRY_RUN", "Dry-run restore çalışmadı.", failures)
        assert_true(bool(backend["dry_run"].get("changes")), "Dry-run değişecek dosya listesini üretmedi.", failures)
        assert_true(backend["restored"].get("status") == "OK", "Restore başarılı olmadı.", failures)
        assert_true(bool(backend["restored"].get("snapshot")), "Restore öncesi otomatik snapshot alınmadı.", failures)
        assert_true(backend["restored_profiles"][0].get("printer_profile_id") == "phase24-before", "Restore hedef dosyayı geri döndürmedi.", failures)
        assert_true(backend["corrupt_validate"].get("status") == "ERROR", "Corrupt backup doğrulamada yakalanmadı.", failures)
        assert_true(backend["corrupt_restore"].get("restore_status") == "BLOCKED", "Corrupt backup restore edilmemeliydi.", failures)
        assert_true(backend["traversal_validate"].get("status") == "ERROR", "Path traversal engellenmedi.", failures)
        for event_type in ["backup_created", "backup_validated", "restore_previewed", "restore_completed", "restore_failed"]:
            assert_true(event_type in backend["audit_event_types"], f"Audit event eksik: {event_type}", failures)
        assert_true(not backend["created"].get("auto_print_started"), "Yazıcı otomatik başlamış görünüyor.", failures)
        assert_true(not backend["created"].get("laser_started"), "Lazer otomatik başlamış görünüyor.", failures)
        assert_true(not backend["created"].get("rdworks_started"), "RDWorks otomatik başlamış görünüyor.", failures)
        assert_true(not backend["created"].get("trendyol_live_action"), "Trendyol canlı işlem tetiklenmiş görünüyor.", failures)

        assert_true(ui["settings"].get("hasDataMaintenance"), "Veri Bakımı ekranı görünmüyor.", failures)
        assert_true(ui["settings"].get("hasBackupCreate"), "Yedek Oluştur butonu görünmüyor.", failures)
        assert_true(ui["settings"].get("hasDryRun"), "Geri Yükleme Önizle butonu görünmüyor.", failures)
        assert_true("yedek" in ui["create_ui"].get("status", "").lower() or "backup" in ui["create_ui"].get("listText", "").lower(), "UI yedek oluşturma özeti görünmüyor.", failures)
        assert_true("dosya" in ui["dry_run_ui"].get("preview", ""), "UI dry-run dosya özeti görünmüyor.", failures)
        assert_true("doğrulanamadı" in ui["corrupt_ui"].get("status", "").lower() or "bozuk" in ui["corrupt_ui"].get("preview", "").lower(), "UI corrupt backup uyarısı görünmüyor.", failures)
        assert_true(ui["restore_ui"].get("status") == "OK", "UI restore başarı sonucu görünmüyor.", failures)
        assert_true(ui["audit_ui"].get("hasBackupCreated"), "Audit ekranında backup event görünmüyor.", failures)

        result.update({
            "status": "PASS" if not failures else "FAIL",
            "failures": failures,
            "backend": backend,
            "ui": ui,
            "screenshots": {key: value for key, value in ui.items() if isinstance(value, str) and value.endswith(".png")},
        })
    except Exception as exc:  # noqa: BLE001
        result.update({"status": "ERROR", "error": str(exc), "failures": failures})
    finally:
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        restore_data(data_backup)
        window.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
