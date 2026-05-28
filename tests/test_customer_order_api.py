from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend import customer_order_api, print_queue_api


def test_customer_order_create_status_and_summary_pdf(tmp_path: Path) -> None:
    result = customer_order_api.create_customer_order(
        tmp_path,
        {
            "customer_name": "Ayşe & Mehmet",
            "phone": "0555",
            "event_date": "2026-05-15",
            "note_text": "Nişan Hatırası",
            "model_path": "templates/designs/01_a_gold.json",
            "model_name": "01 A Gold Rulo Etiket",
            "quantity": "10",
            "delivery_date": "2026-05-20",
            "payment_status": "Kapora alındı",
        },
    )

    assert result["status"] == "OK"
    orders = customer_order_api.list_customer_orders(tmp_path)
    assert len(orders) == 1
    assert orders[0]["customer_name"] == "Ayşe & Mehmet"
    assert orders[0]["quantity"] == "10"
    assert orders[0]["production_status"] == "Yeni"

    status = customer_order_api.update_customer_order_status(tmp_path, orders[0]["id"], "Hazır")
    assert status["status"] == "OK"
    assert customer_order_api.list_customer_orders(tmp_path)[0]["production_status"] == "Hazır"

    pdf = customer_order_api.create_order_summary_pdf(tmp_path, orders[0]["id"])
    assert pdf["status"] == "OK"
    assert (tmp_path / pdf["relative_path"]).exists()
    assert (tmp_path / pdf["manifest_path"]).exists()


def test_print_queue_delivered_status_round_trip(tmp_path: Path) -> None:
    pdf = tmp_path / "output" / "2026-05-13" / "manual" / "manual_batch.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    added = print_queue_api.add_pdf_output_to_queue(tmp_path, "output/2026-05-13/manual/manual_batch.pdf")
    assert added["status"] == "ADDED"

    delivered = print_queue_api.mark_queue_item_delivered(tmp_path, added["id"])
    assert delivered["status"] == "OK"
    row = print_queue_api.list_print_queue(tmp_path)[0]
    assert row["status"] == "Teslim edildi"
    assert row["delivery_status"] == "Teslim edildi"

    pending = print_queue_api.mark_queue_item_pending(tmp_path, added["id"])
    assert pending["status"] == "OK"
    row = print_queue_api.list_print_queue(tmp_path)[0]
    assert row["status"] == "Beklemede"
    assert row["delivery_status"] == "Teslim bekliyor"


def test_customer_order_ui_keeps_filters_and_real_render_state() -> None:
    app_js = (PROJECT_ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    html = (PROJECT_ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")

    assert "customerOrderSearch" in html
    assert "customerOrderStatusFilter" in html
    assert "customerOrderPaymentFilter" in html
    assert "function renderCustomerOrderToQueue" in app_js
    assert "_studio_render_state" in app_js
    assert "render_manual_label_fields_to_queue" in app_js
    assert "clearCustomerOrderFilters" in app_js
