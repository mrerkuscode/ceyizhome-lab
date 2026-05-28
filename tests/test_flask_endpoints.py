"""Sprint 1 — Flask endpoint smoke tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on path before importing flask_app
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pytest

from server.flask_app import app as flask_app


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
