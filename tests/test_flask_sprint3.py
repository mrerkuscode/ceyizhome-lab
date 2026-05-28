"""Sprint 3 — File upload + subprocess/job endpoint tests."""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

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


def _xlsx_file(name: str = "test.xlsx") -> tuple:
    """Return (BytesIO, filename, content_type) for a fake xlsx — werkzeug order."""
    return (io.BytesIO(b"PK\x03\x04fake_xlsx_content"), name, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _ttf_file(name: str = "test.ttf") -> tuple:
    return (io.BytesIO(b"\x00\x01\x00\x00fake_ttf"), name, "font/ttf")


def _png_file(name: str = "test.png") -> tuple:
    # Minimal 1×1 PNG
    png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return (io.BytesIO(png), name, "image/png")


def _zip_file(name: str = "pack.zip") -> tuple:
    return (io.BytesIO(b"PK\x05\x06" + b"\x00" * 18), name, "application/zip")


# ── GRUP A — File Upload ──────────────────────────────────────────────────────

def test_upload_excel_ok(client, tmp_path):
    """Valid .xlsx upload should return status OK."""
    with patch("server.routes._UPLOAD_INPUT_DIR", tmp_path):
        r = client.post(
            "/api/upload_excel",
            data={"file": _xlsx_file()},
            content_type="multipart/form-data",
        )
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "OK"
    assert "filename" in data


def test_upload_excel_bad_extension(client, tmp_path):
    """Wrong extension should return ERROR."""
    with patch("server.routes._UPLOAD_INPUT_DIR", tmp_path):
        r = client.post(
            "/api/upload_excel",
            data={"file": (io.BytesIO(b"hello"), "notexcel.txt", "text/plain")},
            content_type="multipart/form-data",
        )
    assert r.status_code == 200
    assert r.get_json()["status"] == "ERROR"


def test_upload_excel_no_file(client):
    """Missing file field should return ERROR."""
    r = client.post("/api/upload_excel", data={}, content_type="multipart/form-data")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ERROR"


def test_upload_font_ok(client, tmp_path):
    with patch("server.routes._UPLOAD_FONTS_DIR", tmp_path):
        r = client.post(
            "/api/upload_font",
            data={"file": _ttf_file()},
            content_type="multipart/form-data",
        )
    assert r.status_code == 200
    assert r.get_json()["status"] == "OK"


def test_upload_design_visual_ok(client, tmp_path):
    with patch("server.routes._UPLOAD_TEMP_DIR", tmp_path):
        r = client.post(
            "/api/upload_design_visual",
            data={"file": _png_file()},
            content_type="multipart/form-data",
        )
    assert r.status_code == 200
    assert r.get_json()["status"] == "OK"


def test_upload_template_pack_ok(client, tmp_path):
    with patch("server.routes._UPLOAD_TEMP_DIR", tmp_path):
        r = client.post(
            "/api/upload_template_pack",
            data={"file": _zip_file()},
            content_type="multipart/form-data",
        )
    assert r.status_code == 200
    assert r.get_json()["status"] == "OK"


def test_upload_label_preview_ok(client, tmp_path):
    with patch("server.routes._UPLOAD_TEMP_DIR", tmp_path):
        r = client.post(
            "/api/upload_label_preview",
            data={"file": _png_file("preview.png")},
            content_type="multipart/form-data",
        )
    assert r.status_code == 200
    assert r.get_json()["status"] == "OK"


# ── GRUP B — Subprocess / Job endpoints ───────────────────────────────────────

def test_start_render_labels_returns_job_id(client):
    r = client.post("/api/start_render_labels", json={})
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "OK"
    assert "job_id" in data


def test_start_run_dry_returns_job_id(client):
    r = client.post("/api/start_run_dry", json={"excel_path": ""})
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "OK"
    assert "job_id" in data


def test_job_status_after_start(client):
    """Start a job, then poll its status."""
    start = client.post("/api/start_run_dry", json={})
    job_id = start.get_json()["job_id"]

    # Poll until not running (max ~2 s)
    for _ in range(20):
        r = client.get(f"/api/job_status/{job_id}")
        assert r.status_code == 200
        data = r.get_json()
        assert data["job_id"] == job_id
        if data["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)
    assert data["status"] in ("completed", "failed", "running")


def test_job_log_after_start(client):
    """Start a job and retrieve its log."""
    start = client.post("/api/start_render_labels", json={})
    job_id = start.get_json()["job_id"]
    time.sleep(0.5)

    r = client.get(f"/api/job_log/{job_id}?tail=50")
    assert r.status_code == 200
    data = r.get_json()
    assert data["job_id"] == job_id
    assert isinstance(data["lines"], list)


def test_cancel_job(client):
    """Cancel a running job."""
    from server import job_manager

    # Create a slow job
    import threading
    started = threading.Event()

    def slow():
        started.set()
        time.sleep(60)

    job_id = job_manager.start_job("slow_test", slow)
    started.wait(timeout=2)

    r = client.post(f"/api/cancel_job/{job_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "OK"
    assert data["job_id"] == job_id

    # Confirm cancelled
    status_r = client.get(f"/api/job_status/{job_id}")
    assert status_r.get_json()["status"] == "cancelled"


def test_job_status_not_found(client):
    r = client.get("/api/job_status/nonexistent")
    assert r.status_code == 200
    assert r.get_json()["status"] == "NOT_FOUND"


def test_cancel_nonexistent_job(client):
    r = client.post("/api/cancel_job/nonexistent")
    assert r.status_code == 200
    assert r.get_json()["status"] == "NOT_FOUND"
