"""Trendyol İşleme Al — unit + integration testleri.

Guardrail testleri:
- Onaysız (confirmed=False) → 0 API çağrısı
- Mock API: başarılı, hata, timeout, kısmi başarı
- Idempotency: çift çağrı → tek API isteği
- Token log/audit'te OLMAMALI
- >20 eşik backend'de korunmuyor (UI koruyor), ama 0 sipariş / boş liste güvenli döner
"""
from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# src/ dizinini sys.path'e ekle
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_suggestion(order_number="12345678", package_id="pkg-1", line_id="line-1", status="Created"):
    import uuid
    sid = uuid.uuid5(uuid.NAMESPACE_URL, f"{order_number}:{package_id}:{line_id}").hex
    return {
        "id": sid,
        "order_number": order_number,
        "package_id": package_id,
        "line_id": line_id,
        "customer_name": "Test Müşteri",
        "product_name": "Test Ürün",
        "trendyol_package_status": status,
        "status": "ready",
        "import_status": "imported",
        "marketplace_ready": True,
    }


def _write_settings(project_root, stage=False):
    settings = {
        "supplier_id": "99999",
        "api_key": "test-api-key",
        "api_secret": "test-api-secret",
        "stage": stage,
        "read_only_mode": True,
    }
    (project_root / "data").mkdir(parents=True, exist_ok=True)
    (project_root / "data" / "trendyol_settings.json").write_text(
        json.dumps(settings), encoding="utf-8"
    )


def _write_suggestions(project_root, rows):
    (project_root / "data").mkdir(parents=True, exist_ok=True)
    (project_root / "data" / "trendyol_production_suggestions.json").write_text(
        json.dumps(rows, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Test: onaysız çağrı → 0 API isteği
# ---------------------------------------------------------------------------

def test_no_api_call_without_confirmed(tmp_path):
    """confirmed=False → NOT_CONFIRMED döner, API'ye gidilmez."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    sug = _make_suggestion()
    _write_suggestions(tmp_path, [sug])

    api_call_count = []

    def fake_put(project_root, path, body, *, v2, timeout=30):
        api_call_count.append(1)
        return {}

    with patch.object(ta, "_put_json", side_effect=fake_put):
        result = ta.mark_packages_as_processing(
            tmp_path, [sug["id"]], confirmed=False
        )

    assert result["status"] == "NOT_CONFIRMED"
    assert len(api_call_count) == 0, "Onaysız çağrıda API'ye gidilmemeli!"


# ---------------------------------------------------------------------------
# Test: başarılı tek sipariş
# ---------------------------------------------------------------------------

def test_single_success(tmp_path):
    """confirmed=True, mock API 200 → OK döner."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    sug = _make_suggestion()
    _write_suggestions(tmp_path, [sug])

    with patch.object(ta, "_put_json", return_value={}):
        result = ta.mark_packages_as_processing(
            tmp_path, [sug["id"]], confirmed=True
        )

    assert result["status"] == "OK"
    assert result["success_count"] == 1
    assert result["fail_count"] == 0
    assert result["results"][0]["status"] == "OK"


# ---------------------------------------------------------------------------
# Test: API hata dönünce FAIL
# ---------------------------------------------------------------------------

def test_api_error_returns_fail(tmp_path):
    """API RuntimeError → FAIL, success_count=0."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    sug = _make_suggestion()
    _write_suggestions(tmp_path, [sug])

    def raise_error(project_root, path, body, *, v2, timeout=30):
        raise RuntimeError("HTTP 500: Trendyol sunucu hatası")

    with patch.object(ta, "_put_json", side_effect=raise_error):
        result = ta.mark_packages_as_processing(
            tmp_path, [sug["id"]], confirmed=True
        )

    assert result["status"] == "FAIL"
    assert result["fail_count"] == 1
    assert result["success_count"] == 0
    assert "HTTP 500" in result["results"][0]["message"] or "Trendyol" in result["results"][0]["message"]


# ---------------------------------------------------------------------------
# Test: kısmi başarı
# ---------------------------------------------------------------------------

def test_partial_success(tmp_path):
    """3 sipariş, 2 başarılı 1 hatalı → PARTIAL döner."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    rows = [
        _make_suggestion("1001", "pkg-1", "line-1"),
        _make_suggestion("1002", "pkg-2", "line-2"),
        _make_suggestion("1003", "pkg-3", "line-3"),
    ]
    _write_suggestions(tmp_path, rows)

    call_count = [0]

    def mixed(project_root, path, body, *, v2, timeout=30):
        call_count[0] += 1
        if "line-2" in path:
            raise RuntimeError("HTTP 400: Geçersiz statü geçişi")
        return {}

    with patch.object(ta, "_put_json", side_effect=mixed):
        result = ta.mark_packages_as_processing(
            tmp_path, [r["id"] for r in rows], confirmed=True
        )

    assert result["status"] == "PARTIAL"
    assert result["success_count"] == 2
    assert result["fail_count"] == 1
    assert call_count[0] == 3


# ---------------------------------------------------------------------------
# Test: timeout → FAIL, akış çökmez
# ---------------------------------------------------------------------------

def test_timeout_fail_no_crash(tmp_path):
    """Timeout exception → FAIL, diğer siparişler devam eder."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    rows = [
        _make_suggestion("2001", "pkg-1", "line-1"),
        _make_suggestion("2002", "pkg-2", "line-2"),
    ]
    _write_suggestions(tmp_path, rows)

    def timeout_first(project_root, path, body, *, v2, timeout=30):
        if "line-1" in path:
            raise TimeoutError("timeout")
        return {}

    with patch.object(ta, "_put_json", side_effect=timeout_first):
        result = ta.mark_packages_as_processing(
            tmp_path, [r["id"] for r in rows], confirmed=True
        )

    statuses = {r["line_id"]: r["status"] for r in result["results"]}
    assert statuses["line-1"] == "FAIL"
    assert statuses["line-2"] == "OK"


# ---------------------------------------------------------------------------
# Test: idempotency — aynı line_id iki kez gönderilmez
# ---------------------------------------------------------------------------

def test_idempotency_same_line_id(tmp_path):
    """Aynı line_id'ye sahip iki suggestion varsa, API sadece bir kez çağrılır."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    rows = [
        _make_suggestion("3001", "pkg-1", "line-SAME"),
        _make_suggestion("3002", "pkg-2", "line-SAME"),
    ]
    _write_suggestions(tmp_path, rows)

    call_count = [0]

    def count_calls(project_root, path, body, *, v2, timeout=30):
        call_count[0] += 1
        return {}

    with patch.object(ta, "_put_json", side_effect=count_calls):
        result = ta.mark_packages_as_processing(
            tmp_path, [r["id"] for r in rows], confirmed=True
        )

    assert call_count[0] == 1, "Aynı line_id iki kez API'ye gönderilmemeli!"
    dup = next(r for r in result["results"] if r["status"] == "DUPLICATE")
    assert dup is not None


# ---------------------------------------------------------------------------
# Test: zaten "Picking" olan sipariş tekrar gönderilmez
# ---------------------------------------------------------------------------

def test_already_picking_not_resent(tmp_path):
    """trendyol_package_status=picking → ALREADY döner, API çağrılmaz."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    sug = _make_suggestion(status="picking")
    _write_suggestions(tmp_path, [sug])

    call_count = [0]

    def count(project_root, path, body, *, v2, timeout=30):
        call_count[0] += 1
        return {}

    with patch.object(ta, "_put_json", side_effect=count):
        result = ta.mark_packages_as_processing(
            tmp_path, [sug["id"]], confirmed=True
        )

    assert call_count[0] == 0, "Zaten 'picking' olan sipariş API'ye gönderilmemeli!"
    assert result["results"][0]["status"] == "ALREADY"


# ---------------------------------------------------------------------------
# Test: token audit/log dosyasına düşmüyor
# ---------------------------------------------------------------------------

def test_token_not_in_audit_log(tmp_path):
    """Audit log dosyasında api_key veya api_secret OLMAMALI."""
    from webui_backend import trendyol_api as ta

    settings = {
        "supplier_id": "99999",
        "api_key": "SUPER_SECRET_KEY_XYZ",
        "api_secret": "SUPER_SECRET_PASSWORD_ABC",
        "stage": False,
    }
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "trendyol_settings.json").write_text(
        json.dumps(settings), encoding="utf-8"
    )
    sug = _make_suggestion()
    _write_suggestions(tmp_path, [sug])

    with patch.object(ta, "_put_json", return_value={}):
        ta.mark_packages_as_processing(tmp_path, [sug["id"]], confirmed=True)

    log_dir = tmp_path / "output"
    all_text = " ".join(
        p.read_text(encoding="utf-8")
        for p in log_dir.rglob("*.jsonl")
        if p.exists()
    )
    assert "SUPER_SECRET_KEY_XYZ" not in all_text, "API key audit log'a sızdı!"
    assert "SUPER_SECRET_PASSWORD_ABC" not in all_text, "API secret audit log'a sızdı!"


# ---------------------------------------------------------------------------
# Test: boş liste güvenli döner
# ---------------------------------------------------------------------------

def test_empty_list_safe(tmp_path):
    """Boş suggestion_ids → NOT_FOUND, çökme yok."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    _write_suggestions(tmp_path, [])

    result = ta.mark_packages_as_processing(tmp_path, [], confirmed=True)
    assert result["status"] == "NOT_FOUND"
    assert result["success_count"] == 0


# ---------------------------------------------------------------------------
# Test: line_id eksik → SKIP
# ---------------------------------------------------------------------------

def test_missing_line_id_skip(tmp_path):
    """line_id boş → SKIP döner, API çağrılmaz."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    sug = _make_suggestion()
    sug["line_id"] = ""
    _write_suggestions(tmp_path, [sug])

    call_count = [0]

    def count(project_root, path, body, *, v2, timeout=30):
        call_count[0] += 1
        return {}

    with patch.object(ta, "_put_json", side_effect=count):
        result = ta.mark_packages_as_processing(
            tmp_path, [sug["id"]], confirmed=True
        )

    assert call_count[0] == 0
    assert result["results"][0]["status"] == "SKIP"


# ---------------------------------------------------------------------------
# Test: Flask endpoint — confirmed=False → NOT_CONFIRMED
# ---------------------------------------------------------------------------

def test_flask_endpoint_no_confirm(tmp_path, monkeypatch):
    """POST /api/mark_trendyol_orders_processing confirmed=False → NOT_CONFIRMED."""
    import server.routes as routes_mod

    monkeypatch.setattr(routes_mod, "_PROJECT_ROOT", tmp_path)
    _write_settings(tmp_path)
    sug = _make_suggestion()
    _write_suggestions(tmp_path, [sug])

    from flask import Flask
    from server.routes import api_bp
    test_app = Flask(__name__)
    test_app.register_blueprint(api_bp)

    with test_app.test_client() as client:
        resp = client.post(
            "/api/mark_trendyol_orders_processing",
            json={"suggestion_ids": [sug["id"]], "confirmed": False},
        )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["status"] == "NOT_CONFIRMED"


# ---------------------------------------------------------------------------
# Test: Flask endpoint — boş suggestion_ids → 400
# ---------------------------------------------------------------------------

def test_flask_endpoint_empty_ids(tmp_path, monkeypatch):
    """POST /api/mark_trendyol_orders_processing suggestion_ids=[] → 400."""
    import server.routes as routes_mod

    monkeypatch.setattr(routes_mod, "_PROJECT_ROOT", tmp_path)
    _write_settings(tmp_path)

    from flask import Flask
    from server.routes import api_bp
    test_app = Flask(__name__)
    test_app.register_blueprint(api_bp)

    with test_app.test_client() as client:
        resp = client.post(
            "/api/mark_trendyol_orders_processing",
            json={"suggestion_ids": [], "confirmed": True},
        )
    assert resp.status_code == 400
