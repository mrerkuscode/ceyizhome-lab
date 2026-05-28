from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-22" / "production_trendyol_readonly_api_phase22"
RESULT_PATH = OUTPUT_DIR / "production_trendyol_readonly_api_phase22_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import production_audit_api, trendyol_api  # noqa: E402


DATA_FILES = [
    PROJECT_ROOT / "data" / "trendyol_settings.json",
    PROJECT_ROOT / "data" / "trendyol_production_suggestions.json",
    PROJECT_ROOT / "data" / "trendyol_questions_context.json",
    PROJECT_ROOT / "data" / "trendyol_readonly_orders_cache.json",
    PROJECT_ROOT / "data" / "production_audit_log.json",
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


def fake_orders() -> list[dict[str, object]]:
    return [
        {
            "id": "TY-P22-1001",
            "orderNumber": "TY-P22-1001",
            "shipmentPackageId": "PKG-P22-1",
            "status": "Created",
            "customerFirstName": "Ayşe",
            "customerLastName": "Mehmet",
            "customerName": "Ayşe Mehmet",
            "orderDate": 1760000000000,
            "lines": [
                {
                    "id": "LINE-P22-1",
                    "lineId": "LINE-P22-1",
                    "productName": "Kişiye Özel Söz Nişan Etiketi",
                    "barcode": "P22-BARCODE-1",
                    "merchantSku": "P22-SKU-1",
                    "quantity": 2,
                    "image_url": "https://cdn.example.test/p22.png",
                }
            ],
        }
    ]


def fake_questions() -> list[dict[str, object]]:
    return [
        {
            "id": "Q-P22-1",
            "orderNumber": "TY-P22-1001",
            "customerName": "Ayşe Mehmet",
            "productName": "Kişiye Özel Söz Nişan Etiketi",
            "barcode": "P22-BARCODE-1",
            "status": "ANSWERED",
            "questionText": "Sipariş TY-P22-1001 için isim Ayşe & Mehmet, tarih 12.05.2026 olsun.",
            "answerText": "",
            "createdDate": 1760000000000,
            "lastModifiedDate": 1760000000000,
        }
    ]


def install_readonly_fakes() -> dict[str, object]:
    originals = {
        "fetch_orders": trendyol_api.fetch_orders,
        "fetch_products": trendyol_api.fetch_products,
        "fetch_latest_questions": trendyol_api.fetch_latest_questions,
        "enrich_orders_with_product_catalog": trendyol_api.enrich_orders_with_product_catalog,
    }
    trendyol_api.fetch_orders = lambda project_root, start, end: fake_orders()
    trendyol_api.fetch_products = lambda project_root, max_pages=10, page_size=200: []
    trendyol_api.fetch_latest_questions = lambda project_root, status="": fake_questions()
    trendyol_api.enrich_orders_with_product_catalog = lambda project_root, orders, max_pages=10: orders
    return originals


def restore_readonly_fakes(originals: dict[str, object]) -> None:
    trendyol_api.fetch_orders = originals["fetch_orders"]
    trendyol_api.fetch_products = originals["fetch_products"]
    trendyol_api.fetch_latest_questions = originals["fetch_latest_questions"]
    trendyol_api.enrich_orders_with_product_catalog = originals["enrich_orders_with_product_catalog"]


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def run_backend_checks(window: WebMainWindow) -> dict[str, object]:
    checks: dict[str, object] = {}
    settings_path = PROJECT_ROOT / "data" / "trendyol_settings.json"
    if settings_path.exists():
        settings_path.unlink()
    missing = window.sync_trendyol_recent_orders(7)
    checks["missing_credentials"] = missing

    secret = "phase22-should-not-leak-secret"
    saved = window.save_trendyol_settings({
        "supplier_id": "123456",
        "api_key": "phase22-key",
        "api_secret": secret,
        "environment": "stage",
        "read_only_mode": True,
    })
    checks["saved_settings"] = saved
    sync = window.sync_trendyol_recent_orders(7)
    questions = window.sync_trendyol_questions()
    settings_masked = trendyol_api.get_settings(PROJECT_ROOT, masked=True)
    settings_raw = trendyol_api.get_settings(PROJECT_ROOT, masked=False)
    cache = json.loads(trendyol_api.readonly_orders_cache_path(PROJECT_ROOT).read_text(encoding="utf-8"))
    audit_rows = production_audit_api.list_production_audit_events(PROJECT_ROOT, {})
    audit_blob = json.dumps(audit_rows, ensure_ascii=False)
    checks.update({
        "sync": sync,
        "questions": questions,
        "settings_masked": settings_masked,
        "settings_raw_secret_saved": settings_raw.get("api_secret") == secret,
        "cache": {
            "exists": True,
            "order_count": cache.get("order_count"),
            "message_count": cache.get("message_count"),
            "read_only_mode": cache.get("read_only_mode"),
            "marketplace_status_changed": cache.get("marketplace_status_changed"),
            "cargo_invoice_triggered": cache.get("cargo_invoice_triggered"),
        },
        "audit_event_types": sorted({row.get("event_type") for row in audit_rows}),
        "secret_in_audit": secret in audit_blob,
        "secret_in_settings_masked": secret in json.dumps(settings_masked, ensure_ascii=False),
        "suggestions": len(trendyol_api.list_suggestions(PROJECT_ROOT)),
        "questions_count": len(trendyol_api.list_questions(PROJECT_ROOT)),
    })
    return checks


def run_ui_checks(window: WebMainWindow) -> dict[str, object]:
    result: dict[str, object] = {}
    window.resize(1920, 1080)
    wait(700)
    result["settings_1920"] = run_js(window, """
    (() => {
      refreshState();
      openSettingsSubpage('trendyol-api');
      const text = document.getElementById('settings')?.innerText || '';
      return {
        activePage: document.querySelector('.page.active')?.id || '',
        text,
        secretValue: document.getElementById('trendyolApiSecret')?.value || '',
        hasReadonly: /Read-only mode/.test(text),
        hasNoLiveAction: /statü\\/kargo\\/fatura|statüsü, kargo veya fatura|Canlı statü/.test(text)
      };
    })()
    """, timeout_ms=60000)
    result["settings_screenshot"] = save_screenshot(window, "trendyol-api-settings-1920.png")
    result["orders_1920"] = run_js(window, """
    (() => {
      showSection('trendyolOrders');
      updateTrendyolOrders(currentState.trendyol || {});
      const text = document.getElementById('trendyolOrders')?.innerText || '';
      return {
        activePage: document.querySelector('.page.active')?.id || '',
        text,
        hasReadonly: /Read-only mode/.test(text),
        hasLastSync: /Son sync|Son çekim/.test(text),
        hasLiveWarning: /Canlı statü\\/kargo\\/fatura|tetiklenmez/.test(text)
      };
    })()
    """, timeout_ms=60000)
    result["orders_screenshot"] = save_screenshot(window, "trendyol-readonly-orders-1920.png")
    result["audit"] = run_js(window, """
    (() => {
      showSection('productionAudit');
      updateProductionAudit(currentState.productionAudit || []);
      const text = document.getElementById('productionAudit')?.innerText || '';
      return { activePage: document.querySelector('.page.active')?.id || '', hasSyncEvent: /Trendyol read-only|trendyol_sync/.test(text), text };
    })()
    """, timeout_ms=60000)
    result["audit_screenshot"] = save_screenshot(window, "trendyol-readonly-audit-events.png")
    window.resize(1366, 768)
    wait(600)
    result["orders_1366"] = run_js(window, """
    (() => {
      showSection('trendyolOrders');
      updateTrendyolOrders(currentState.trendyol || {});
      return {
        activePage: document.querySelector('.page.active')?.id || '',
        hasReadonly: /Read-only mode/.test(document.body.innerText || ''),
        width: window.innerWidth
      };
    })()
    """, timeout_ms=60000)
    result["orders_1366_screenshot"] = save_screenshot(window, "trendyol-readonly-1366.png")
    return result


def main() -> int:
    suppress_message_boxes()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backup = backup_data()
    originals = install_readonly_fakes()
    failures: list[str] = []
    screenshots: dict[str, str] = {}
    try:
        app = QApplication.instance() or QApplication([])
        window = WebMainWindow(PROJECT_ROOT, sys.executable)
        wait(900)
        backend = run_backend_checks(window)
        ui = run_ui_checks(window)
        screenshots = {key: value for key, value in ui.items() if key.endswith("_screenshot") and isinstance(value, str)}

        assert_true(backend["missing_credentials"].get("status") == "CONFIG_MISSING", "Eksik credential sahte success verdi.", failures)
        assert_true("•" in backend["settings_masked"].get("api_secret", "") or "*" in backend["settings_masked"].get("api_secret", ""), "API secret UI/state içinde maskeli değil.", failures)
        assert_true(backend["settings_raw_secret_saved"] is True, "Gerçek secret güvenli ayar dosyasına yazılmadı.", failures)
        assert_true(backend["secret_in_audit"] is False, "Secret audit log içine sızdı.", failures)
        assert_true(backend["secret_in_settings_masked"] is False, "Masked settings gerçek secret döndürdü.", failures)
        assert_true(backend["sync"].get("status") == "OK", "Read-only order sync OK dönmedi.", failures)
        assert_true(backend["questions"].get("status") == "OK", "Read-only question sync OK dönmedi.", failures)
        assert_true(backend["cache"].get("exists") and backend["cache"].get("order_count") == 1, "Read-only local order cache oluşmadı.", failures)
        assert_true(backend["cache"].get("read_only_mode") is True, "Cache read-only mode taşımıyor.", failures)
        assert_true(backend["cache"].get("marketplace_status_changed") is False, "Marketplace status değişmiş görünüyor.", failures)
        assert_true(backend["cache"].get("cargo_invoice_triggered") is False, "Kargo/fatura tetiklenmiş görünüyor.", failures)
        assert_true(backend["suggestions"] >= 1, "Sync üretim önerisi/local kayıt oluşturmadı.", failures)
        assert_true(backend["questions_count"] >= 1, "Soru/mesaj kanıt cache'i oluşmadı.", failures)
        events = set(backend["audit_event_types"])
        for expected in ["trendyol_sync_started", "trendyol_sync_completed", "trendyol_sync_failed", "trendyol_readonly_mode_confirmed"]:
            assert_true(expected in events, f"Audit event eksik: {expected}", failures)
        assert_true(ui["settings_1920"].get("hasReadonly"), "Ayarlar ekranında read-only rozeti görünmüyor.", failures)
        assert_true(ui["settings_1920"].get("hasNoLiveAction"), "Ayarlar ekranında canlı aksiyon güvenliği görünmüyor.", failures)
        assert_true(ui["orders_1920"].get("hasReadonly"), "Trendyol ekranında read-only mode görünmüyor.", failures)
        assert_true(ui["orders_1920"].get("hasLastSync"), "Trendyol ekranında son sync görünmüyor.", failures)
        assert_true(ui["orders_1920"].get("hasLiveWarning"), "Trendyol ekranında canlı statü/kargo/fatura uyarısı görünmüyor.", failures)
        assert_true(ui["audit"].get("hasSyncEvent"), "Üretim Geçmişi'nde Trendyol sync eventleri görünmüyor.", failures)
        assert_true(ui["orders_1366"].get("hasReadonly"), "1366 görünümde read-only bilgi kayboldu.", failures)

        outcome = {
            "status": "PASSED" if not failures else "FAILED",
            "checks": {"backend": backend, "ui": ui},
            "screenshots": screenshots,
            "failures": failures,
        }
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0 if not failures else 1
    finally:
        restore_readonly_fakes(originals)
        restore_data(backup)


if __name__ == "__main__":
    raise SystemExit(main())
