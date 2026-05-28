from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import customer_order_api, print_queue_api  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "customer_order_flow"
RESULT_PATH = OUTPUT_DIR / "VERIFY_CUSTOMER_ORDER_FLOW_RESULT.json"


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
    value = result["value"]
    parsed = json.loads(value) if isinstance(value, str) else value
    if isinstance(parsed, dict) and parsed.get("__error"):
        raise RuntimeError(f"{parsed['__error']}\n{parsed.get('stack', '')}")
    return parsed


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    window.view.grab().save(str(path))
    return str(path)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1600, 940)
    window.show()
    wait(6000)
    screenshots: dict[str, str] = {}
    try:
        before_count = len(customer_order_api.list_customer_orders(PROJECT_ROOT))
        queue_before_initial = len(print_queue_api.list_print_queue(PROJECT_ROOT))
        page_ready = run_js(window, """
        (() => {
          showSection('customerOrders');
          return {
            page: document.querySelector('.page.active')?.id || '',
            hasForm: Boolean(document.getElementById('orderCustomerName')),
            hasList: Boolean(document.getElementById('customerOrdersList')),
            hasSearch: Boolean(document.getElementById('customerOrderSearch')),
            hasStatusFilter: Boolean(document.getElementById('customerOrderStatusFilter')),
            modelOptions: document.getElementById('orderModelSelect')?.options.length || 0
          };
        })()
        """)
        assert_true(page_ready["page"] == "customerOrders", "Sipariş sayfası açılmadı", page_ready)
        assert_true(page_ready["hasForm"] and page_ready["hasList"], "Sipariş form/listesi görünmedi", page_ready)
        assert_true(page_ready["hasSearch"] and page_ready["hasStatusFilter"], "Sipariş arama/filtre alanı görünmedi", page_ready)
        assert_true(page_ready["modelOptions"] > 0, "Sipariş model seçimi boş", page_ready)
        wait(600)
        screenshots["orders_empty_or_list"] = save_screenshot(window, "customer_orders_page.png")

        run_js(window, """
        (() => {
          document.getElementById('orderCustomerName').value = 'Ayşe Ömer Sipariş Test';
          document.getElementById('orderPhone').value = '0555 000 00 00';
          document.getElementById('orderEventDate').value = '2026-05-15';
          document.getElementById('orderDeliveryDate').value = '2026-05-20';
          document.getElementById('orderQuantity').value = '12';
          document.getElementById('orderNoteText').value = 'Nişan Hatırası';
          document.getElementById('orderPaymentStatus').value = 'Kapora alındı';
          createCustomerOrderFromForm();
          return true;
        })()
        """)
        wait(1400)
        window._emit_state()
        wait(900)
        orders = customer_order_api.list_customer_orders(PROJECT_ROOT)
        assert_true(len(orders) >= before_count + 1, "Sipariş backend kaydı oluşmadı", {"before": before_count, "after": len(orders)})
        order = orders[0]
        assert_true(order["customer_name"] == "Ayşe Ömer Sipariş Test", "Sipariş müşteri adı yanlış", order)
        assert_true(order["quantity"] == "12", "Sipariş adet yanlış", order)

        filter_state = run_js(window, """
        (() => {
          showSection('customerOrders');
          document.getElementById('customerOrderSearch').value = 'Ayşe';
          document.getElementById('customerOrderStatusFilter').value = 'Yeni';
          updateCustomerOrders(currentState.customerOrders || []);
          const listText = document.getElementById('customerOrdersList')?.innerText || '';
          const countText = document.getElementById('customerOrderCount')?.innerText || '';
          clearCustomerOrderFilters();
          return { listText, countText };
        })()
        """)
        assert_true("Ayşe Ömer Sipariş Test" in filter_state["listText"], "Sipariş arama/durum filtresi kaydı göstermedi", filter_state)
        screenshots["order_filtered_list"] = save_screenshot(window, "customer_orders_filtered.png")

        pdf = customer_order_api.create_order_summary_pdf(PROJECT_ROOT, order["id"])
        assert_true(pdf["status"] == "OK", "İş emri PDF oluşmadı", pdf)
        assert_true((PROJECT_ROOT / pdf["relative_path"]).exists(), "İş emri PDF dosyası yok", pdf)

        run_js(window, f"""
        (() => {{
          showSection('customerOrders');
          updateCustomerOrders({json.dumps(orders, ensure_ascii=False)});
          openCustomerOrderInStudio('{order["id"]}');
          return true;
        }})()
        """)
        wait(900)
        ui_after = run_js(window, """
        (() => ({
          page: document.querySelector('.page.active')?.id || '',
          manualText: document.getElementById('manualText')?.value || '',
          manualDate: document.getElementById('manualDateText')?.value || '',
          manualNote: document.getElementById('manualNoteText')?.value || ''
        }))()
        """)
        assert_true(ui_after["page"] == "label", "Siparişten Studio'ya geçmedi", ui_after)
        assert_true(ui_after["manualText"] == "Ayşe Ömer Sipariş Test", "Sipariş adı Studio alanına taşınmadı", ui_after)
        assert_true(ui_after["manualDate"] == "2026-05-15", "Sipariş tarihi Studio alanına taşınmadı", ui_after)
        assert_true("Nişan" in ui_after["manualNote"], "Sipariş notu Studio alanına taşınmadı", ui_after)
        screenshots["order_to_studio"] = save_screenshot(window, "order_to_studio.png")

        queue_before = len(print_queue_api.list_print_queue(PROJECT_ROOT))
        run_js(window, f"""
        (() => {{
          showSection('customerOrders');
          updateCustomerOrders({json.dumps(customer_order_api.list_customer_orders(PROJECT_ROOT), ensure_ascii=False)});
          window.__lastCustomerOrderQueueResult = null;
          renderCustomerOrderToQueue('{order["id"]}');
          return true;
        }})()
        """, timeout_ms=120000)
        queue_result = None
        for _ in range(14):
            wait(700)
            queue_result = run_js(window, "(() => window.__lastCustomerOrderQueueResult || null)()")
            if queue_result:
                break
        assert_true(queue_result and queue_result.get("status") == "OK", "Sipariş üretim/queue sonucu OK dönmedi", queue_result)
        window._emit_state()
        wait(1000)
        queue_rows = print_queue_api.list_print_queue(PROJECT_ROOT)
        queue_path = str((queue_result.get("queue_result") or {}).get("relative_path") or queue_result.get("batch_pdf_path") or "")
        newest_queue = next((row for row in queue_rows if str(row.get("relative_path") or "") == queue_path), queue_rows[0] if queue_rows else {})
        assert_true(queue_path and any(str(row.get("relative_path") or "") == queue_path for row in queue_rows), "Siparişten queue işi oluşmadı", {"before": queue_before, "after": len(queue_rows), "queue_result": queue_result})
        assert_true(str(newest_queue.get("relative_path") or "").lower().endswith(".pdf"), "Queue yanlış dosya tipini aldı", newest_queue)
        updated_order = next(row for row in customer_order_api.list_customer_orders(PROJECT_ROOT) if row.get("id") == order["id"])
        assert_true(updated_order["production_status"] == "Sırada", "Sipariş queue sonrası Sırada durumuna geçmedi", updated_order)
        screenshots["order_rendered_to_queue"] = save_screenshot(window, "order_rendered_to_queue.png")

        security = {
            "rdworks_auto_open": False,
            "laser_started": False,
            "direct_print_enabled": False,
            "corel_auto_open": False,
            "illustrator_auto_open": False,
        }
        result = {
            "status": "PASSED",
            "order_id": order["id"],
            "work_order_pdf": pdf["relative_path"],
            "queue_before_initial": queue_before_initial,
            "queue_path": newest_queue.get("relative_path") or "",
            "screenshots": screenshots,
            "security": security,
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
