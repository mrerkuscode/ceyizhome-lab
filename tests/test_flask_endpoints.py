"""Sprint 1 + Sprint 2 — Flask endpoint smoke tests."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure src/ is on path before importing flask_app
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pytest

from server.flask_app import app as flask_app

# Common mock return values for write operations
_OK = {"status": "OK"}
_REMOVED = {"status": "OK", "removed": True}


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ── 7 GET endpoints ───────────────────────────────────────────────────────────

def test_state_endpoint(client):
    r = client.get("/api/state")
    assert r.status_code == 200
    assert r.is_json
    data = r.get_json()
    # Must have key fields app.js depends on
    assert "readiness" in data
    assert "summary" in data
    assert "labelModels" in data
    assert "printQueue" in data


def test_metrics_endpoint_default(client):
    r = client.get("/api/metrics")
    assert r.status_code == 200
    assert r.is_json
    data = r.get_json()
    assert "status" in data or "today" in data or "empty" in data


def test_metrics_endpoint_with_range(client):
    r = client.get("/api/metrics?range={}")
    assert r.status_code == 200
    assert r.is_json


def test_label_outputs_endpoint(client):
    r = client.get("/api/label_outputs")
    assert r.status_code == 200
    assert r.is_json
    assert isinstance(r.get_json(), list)


def test_print_queue_endpoint(client):
    r = client.get("/api/print_queue")
    assert r.status_code == 200
    assert r.is_json
    assert isinstance(r.get_json(), list)


def test_label_model_gallery_endpoint(client):
    r = client.get("/api/label_model_gallery")
    assert r.status_code == 200
    assert r.is_json
    assert isinstance(r.get_json(), list)


def test_reports_endpoint(client):
    r = client.get("/api/reports")
    assert r.status_code == 200
    assert r.is_json
    assert isinstance(r.get_json(), dict)


# ── Root and static assets ────────────────────────────────────────────────────

def test_root_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"html" in r.data.lower()


def test_adapter_js_served(client):
    r = client.get("/api_adapter.js")
    assert r.status_code == 200


# ── Path traversal protection ─────────────────────────────────────────────────

def test_files_path_traversal_blocked(client):
    r = client.get("/api/files/../../../etc/passwd")
    assert r.status_code in (400, 404)


# ── Sprint 2: POST endpoint smoke tests ───────────────────────────────────────
# Each test mocks the proxy function so tests run without real filesystem state.

_PROXY = "server.routes.proxy"


# GRUP 1 — Print Queue

def test_mark_queue_item_printed(client):
    with patch(f"{_PROXY}.mark_queue_item_printed", return_value=_OK):
        r = client.post("/api/mark_queue_item_printed", json={"item_id": "abc"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "OK"


def test_mark_queue_item_pending(client):
    with patch(f"{_PROXY}.mark_queue_item_pending", return_value=_OK):
        r = client.post("/api/mark_queue_item_pending", json={"item_id": "abc"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "OK"


def test_mark_queue_item_delivered(client):
    with patch(f"{_PROXY}.mark_queue_item_delivered", return_value=_OK):
        r = client.post("/api/mark_queue_item_delivered", json={"item_id": "abc"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "OK"


def test_remove_from_print_queue(client):
    with patch(f"{_PROXY}.remove_from_print_queue", return_value=_REMOVED):
        r = client.post("/api/remove_from_print_queue", json={"item_id": "abc"})
    assert r.status_code == 200
    assert r.is_json


def test_clear_print_queue(client):
    with patch(f"{_PROXY}.clear_print_queue", return_value=_OK):
        r = client.post("/api/clear_print_queue", json={})
    assert r.status_code == 200
    assert r.get_json()["status"] == "OK"


def test_add_pdf_output_to_print_queue(client):
    with patch(f"{_PROXY}.add_pdf_output_to_print_queue", return_value=_OK):
        r = client.post("/api/add_pdf_output_to_print_queue", json={"relative_path": "output/test.pdf"})
    assert r.status_code == 200
    assert r.is_json


def test_add_label_outputs_to_print_queue(client):
    with patch(f"{_PROXY}.add_label_outputs_to_print_queue", return_value=_OK):
        r = client.post("/api/add_label_outputs_to_print_queue", json={})
    assert r.status_code == 200
    assert r.is_json


# GRUP 2 — Label Model Fields

def test_save_label_model_field(client):
    with patch(f"{_PROXY}.save_label_model_field", return_value=_OK):
        r = client.post("/api/save_label_model_field", json={
            "template_path": "templates/test.json",
            "index": 0,
            "label": "Ürün Adı"
        })
    assert r.status_code == 200
    assert r.is_json


def test_add_label_model_field(client):
    with patch(f"{_PROXY}.add_label_model_field", return_value=_OK):
        r = client.post("/api/add_label_model_field", json={
            "template_path": "templates/test.json",
            "field_type": "text"
        })
    assert r.status_code == 200
    assert r.is_json


def test_remove_label_model_field(client):
    with patch(f"{_PROXY}.remove_label_model_field", return_value=_OK):
        r = client.post("/api/remove_label_model_field", json={
            "template_path": "templates/test.json",
            "index": 0
        })
    assert r.status_code == 200
    assert r.is_json


def test_save_label_defaults_json(client):
    with patch(f"{_PROXY}.save_label_defaults_json", return_value={**_OK, "label_defaults": {}}):
        r = client.post("/api/save_label_defaults_json", json={"roll_width_mm": 50})
    assert r.status_code == 200
    assert r.get_json()["status"] == "OK"


def test_clone_label_model_variant(client):
    with patch(f"{_PROXY}.clone_label_model_variant", return_value=_OK):
        r = client.post("/api/clone_label_model_variant", json={
            "template_path": "templates/test.json",
            "variant_name": "Test Varyant"
        })
    assert r.status_code == 200
    assert r.is_json


def test_save_print_template_metadata(client):
    with patch(f"{_PROXY}.save_print_template_metadata", return_value=_OK):
        r = client.post("/api/save_print_template_metadata", json={
            "relative_path": "templates/print/test.json",
            "description": "Test açıklama"
        })
    assert r.status_code == 200
    assert r.is_json


# GRUP 3 — Ürün Tanımları

def test_product_definition_save(client):
    with patch(f"{_PROXY}.product_definition_save", return_value=_OK):
        r = client.post("/api/productDefinitionSave", json={"sku": "TEST-001", "name": "Test Ürün"})
    assert r.status_code == 200
    assert r.is_json


def test_product_definition_archive(client):
    with patch(f"{_PROXY}.product_definition_archive", return_value=_OK):
        r = client.post("/api/productDefinitionArchive", json={"sku": "TEST-001"})
    assert r.status_code == 200
    assert r.is_json


def test_product_definition_restore(client):
    with patch(f"{_PROXY}.product_definition_restore", return_value=_OK):
        r = client.post("/api/productDefinitionRestore", json={"sku": "TEST-001"})
    assert r.status_code == 200
    assert r.is_json


# GRUP 4 — Müşteri Siparişleri

def test_create_customer_order(client):
    with patch(f"{_PROXY}.create_customer_order", return_value={**_OK, "order_id": "ORD-001"}):
        r = client.post("/api/create_customer_order", json={"customer_name": "Test Müşteri"})
    assert r.status_code == 200
    assert r.is_json


def test_update_customer_order_status(client):
    with patch(f"{_PROXY}.update_customer_order_status", return_value=_OK):
        r = client.post("/api/update_customer_order_status", json={"order_id": "ORD-001", "status": "delivered"})
    assert r.status_code == 200
    assert r.is_json


# GRUP 5 — Audit / Log

def test_append_production_audit_event(client):
    with patch(f"{_PROXY}.append_production_audit_event", return_value={**_OK, "count": 1}):
        r = client.post("/api/append_production_audit_event", json={
            "event_type": "print_queue_created",
            "source": "test"
        })
    assert r.status_code == 200
    assert r.is_json


def test_rebuild_production_audit(client):
    with patch(f"{_PROXY}.rebuild_production_audit_from_existing_sources", return_value={**_OK, "rebuilt": 0}):
        r = client.post("/api/rebuild_production_audit_from_existing_sources", json={})
    assert r.status_code == 200
    assert r.is_json


# GRUP 6 — Yazıcı Profili

def test_save_printer_profile(client):
    with patch(f"{_PROXY}.save_printer_profile", return_value=_OK):
        r = client.post("/api/save_printer_profile", json={"name": "Test Yazıcı", "paper_width_mm": 50})
    assert r.status_code == 200
    assert r.is_json


def test_delete_printer_profile(client):
    with patch(f"{_PROXY}.delete_printer_profile", return_value=_OK):
        r = client.post("/api/delete_printer_profile", json={"profile_id": "prof-001"})
    assert r.status_code == 200
    assert r.is_json


# GRUP 7 — Yedekleme

def test_create_backup(client):
    with patch(f"{_PROXY}.create_backup", return_value={**_OK, "path": "backups/test"}):
        r = client.post("/api/create_backup", json={})
    assert r.status_code == 200
    assert r.is_json


def test_restore_backup(client):
    with patch(f"{_PROXY}.restore_backup", return_value={**_OK, "dry_run": True}):
        r = client.post("/api/restore_backup", json={"backup_path": "backups/test", "dry_run": True})
    assert r.status_code == 200
    assert r.is_json


# GRUP 8 — Trendyol

def test_upsert_trendyol_mapping(client):
    with patch(f"{_PROXY}.upsert_trendyol_mapping", return_value=_OK):
        r = client.post("/api/upsert_trendyol_mapping", json={"trendyol_sku": "TY-001", "local_sku": "LOC-001"})
    assert r.status_code == 200
    assert r.is_json


def test_save_trendyol_settings(client):
    with patch(f"{_PROXY}.save_trendyol_settings", return_value=_OK):
        r = client.post("/api/save_trendyol_settings", json={"api_key": "test", "supplier_id": "123"})
    assert r.status_code == 200
    assert r.is_json


# GRUP 9 — İsim Kesim

def test_update_name_cut_queue_item_status(client):
    with patch(f"{_PROXY}.update_name_cut_queue_item_status", return_value=_OK):
        r = client.post("/api/update_name_cut_queue_item_status", json={"item_id": "nc-001", "status": "prepared"})
    assert r.status_code == 200
    assert r.is_json


# GRUP 10 — Güvenlik

def test_save_live_integration_security_settings(client):
    with patch(f"{_PROXY}.save_live_integration_security_settings", return_value=_OK):
        r = client.post("/api/save_live_integration_security_settings", json={"enabled": True})
    assert r.status_code == 200
    assert r.is_json


# Etiket Çıktı Arşivleme

def test_archive_label_outputs(client):
    with patch(f"{_PROXY}.archive_label_outputs", return_value={**_OK, "archived": 0}):
        r = client.post("/api/archive_label_outputs", json={"relative_paths": []})
    assert r.status_code == 200
    assert r.is_json


def test_restore_label_outputs(client):
    with patch(f"{_PROXY}.restore_label_outputs", return_value={**_OK, "restored": 0}):
        r = client.post("/api/restore_label_outputs", json={"relative_paths": []})
    assert r.status_code == 200
    assert r.is_json
