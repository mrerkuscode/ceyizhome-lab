from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import print_queue_api  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "workshop_operations"
RESULT_PATH = OUTPUT_DIR / "VERIFY_WORKSHOP_OPERATIONS_FLOW_RESULT.json"


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
        raise RuntimeError(f"JavaScript timed out: {script[:180]}")
    parsed = json.loads(result["value"]) if isinstance(result["value"], str) else result["value"]
    if isinstance(parsed, dict) and parsed.get("__error"):
        raise RuntimeError(f"{parsed['__error']}\n{parsed.get('stack', '')}")
    return parsed


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    window.view.grab().save(str(path))
    return str(path)


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def ensure_queue_item() -> str:
    pdf = PROJECT_ROOT / "output" / date.today().isoformat() / "manual" / "workshop_operation_test_50x30_1adet.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    if not pdf.exists():
        pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    relative = str(pdf.relative_to(PROJECT_ROOT)).replace("\\", "/")
    result = print_queue_api.add_to_print_queue(
        PROJECT_ROOT,
        {
            "job_name": "Atölye Operasyon Test",
            "job_type": "Manuel",
            "quantity": "3",
            "file_type": "PDF",
            "relative_path": relative,
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Ayşe Ömer",
            "size_text": "50 x 30 mm",
        },
    )
    return result.get("id") or next(row["id"] for row in print_queue_api.list_print_queue(PROJECT_ROOT) if row.get("relative_path") == relative)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    item_id = ensure_queue_item()
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1680, 940)
    window.show()
    wait(6000)
    screenshots: dict[str, str] = {}
    try:
        home = run_js(window, """
        (() => {
          showSection('home');
          updateHomeDashboard(currentState);
          return {
            page: document.querySelector('.page.active')?.id || '',
            waiting: document.getElementById('homeQueueCount')?.textContent || '',
            printed: document.getElementById('homePrintedCount')?.textContent || '',
            delivered: document.getElementById('homeDeliveredCount')?.textContent || '',
            review: document.getElementById('homeReviewCount')?.textContent || '',
            qty: document.getElementById('homeTodayQty')?.textContent || '',
            batch: document.getElementById('homeBatchCount')?.textContent || '',
            body: document.getElementById('home')?.innerText || ''
          };
        })()
        """)
        assert_true(home["page"] == "home", "Ana sayfa açılmadı", home)
        assert_true(home["waiting"] != "", "Bugünün Üretimi bekleyen metrik yok", home)
        assert_true(home["printed"] != "", "Yazdırıldı metrik yok", home)
        assert_true(home["delivered"] != "", "Teslim metrik yok", home)
        assert_true("workshop_operation_test" not in home["body"], "Ana sayfa test/QA isini musteri uretimi gibi gostermemeli", home)
        screenshots["workshop_home"] = save_screenshot(window, "workshop_home_dashboard.png")

        queue_default = run_js(window, """
        (() => {
          showSection('printQueue');
          const toggle = document.getElementById('queueTestArchiveToggle');
          if (toggle) toggle.checked = false;
          refreshPrintQueueFilters();
          return {
            page: document.querySelector('.page.active')?.id || '',
            body: document.getElementById('printQueue')?.innerText || ''
          };
        })()
        """)
        assert_true(queue_default["page"] == "printQueue", "Yazdirma sirasi acilmadi", queue_default)
        assert_true("workshop_operation_test" not in queue_default["body"], "Varsayilan queue musteri ekraninda test/QA isi gorunmemeli", queue_default)

        queue_archive = run_js(window, """
        (() => {
          showSection('printQueue');
          const toggle = document.getElementById('queueTestArchiveToggle');
          if (toggle) toggle.checked = true;
          refreshPrintQueueFilters();
          const archivedWorkshopItems = (currentState.printQueue || []).filter(item => {
            const rel = String(item.relative_path || item.file_name || item.job_name || '');
            return isQueueTestArchiveItem(item) && rel.includes('workshop_operation_test');
          });
          return {
            page: document.querySelector('.page.active')?.id || '',
            body: document.getElementById('printQueue')?.innerText || '',
            archivedWorkshopCount: archivedWorkshopItems.length
          };
        })()
        """)
        assert_true(queue_archive["archivedWorkshopCount"] > 0, "Atolye test isi Test/QA arsiv sinifinda olmali", queue_archive)

        queue_before = run_js(window, f"""
        (() => {{
          showSection('printQueue');
          const toggle = document.getElementById('queueTestArchiveToggle');
          if (toggle) toggle.checked = true;
          refreshPrintQueueFilters();
          selectPrintQueueItem('{item_id}');
          return {{
            page: document.querySelector('.page.active')?.id || '',
            detail: document.getElementById('queueDetailInfo')?.innerText || '',
            actions: document.getElementById('queueDetailActions')?.innerText || ''
          }};
        }})()
        """)
        assert_true(queue_before["page"] == "printQueue", "Yazdırma sırası açılmadı", queue_before)
        assert_true("Ayşe Ömer" in queue_before["detail"], "Queue detayında isim görünmüyor", queue_before)
        assert_true("Teslim" in queue_before["actions"], "Teslim edildi aksiyonu yok", queue_before)
        screenshots["workshop_queue"] = save_screenshot(window, "workshop_queue_detail.png")

        delivered = print_queue_api.mark_queue_item_delivered(PROJECT_ROOT, item_id)
        assert_true(delivered["status"] == "OK", "Teslim edildi backend geçişi çalışmadı", delivered)
        pending = print_queue_api.mark_queue_item_pending(PROJECT_ROOT, item_id)
        assert_true(pending["status"] == "OK", "Beklemeye al backend geçişi çalışmadı", pending)
        safe = print_queue_api.print_queue_item_safe(PROJECT_ROOT, item_id, direct_print_enabled=False)
        assert_true(safe["status"] == "MANUAL_PRINT_REQUIRED", "Yazdır direct/silent print yapmamalı", safe)
        result = {
            "status": "PASSED",
            "queue_item_id": item_id,
            "screenshots": screenshots,
            "direct_print_enabled": False,
            "rdworks_auto_open": False,
            "laser_started": False,
        }
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        window.close()
        return 0
    except Exception as exc:  # noqa: BLE001
        result = {"status": "FAILED", "error": str(exc), "screenshots": screenshots}
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        window.close()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
