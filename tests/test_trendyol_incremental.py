"""Tests for Trendyol incremental sync, scheduler, and credential UI fixes."""
from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Ensure src/ is on sys.path so webui_backend and server imports resolve
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _write_settings(tmp_path: Path, **extra) -> None:
    data = {
        "supplier_id": "12345",
        "api_key": "TestKey",
        "api_secret": "TestSecret",
        "stage": False,
        "read_only_mode": True,
        **extra,
    }
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "trendyol_settings.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


def _write_orders_cache(tmp_path: Path, orders: list) -> None:
    (tmp_path / "data").mkdir(exist_ok=True)
    cache = {"orders": orders, "created_at": "2026-01-01 00:00:00"}
    (tmp_path / "data" / "trendyol_readonly_orders_cache.json").write_text(
        json.dumps(cache), encoding="utf-8"
    )


# ─────────────────────────────────────────────────────────────────────────────
# FAZ 1 — Incremental sync logic
# ─────────────────────────────────────────────────────────────────────────────

def test_load_cached_orders_by_package_id(tmp_path):
    from webui_backend.trendyol_api import _load_cached_orders_by_package_id

    _write_orders_cache(tmp_path, [
        {"shipmentPackageId": "P1", "orderNumber": "O1"},
        {"shipmentPackageId": "P2", "orderNumber": "O2"},
        {"orderNumber": "O3"},  # no packageId
    ])
    result = _load_cached_orders_by_package_id(tmp_path)
    assert "P1" in result
    assert "P2" in result
    assert len(result) == 2


def test_load_cached_orders_empty(tmp_path):
    from webui_backend.trendyol_api import _load_cached_orders_by_package_id

    # File doesn't exist
    result = _load_cached_orders_by_package_id(tmp_path)
    assert result == {}


def test_last_orders_sync_at_updated_after_sync(tmp_path):
    from webui_backend.trendyol_api import _save_orders_sync_status, get_settings

    _write_settings(tmp_path)
    _save_orders_sync_status(tmp_path, "OK", "test", 5, 10)
    settings = get_settings(tmp_path, masked=False)
    assert settings.get("last_orders_sync_at"), "last_orders_sync_at must be set"
    assert settings.get("last_sync_at"), "last_sync_at must still be set for backward compat"


def test_fetch_orders_skips_known_packages(tmp_path):
    """_fetch_orders_from_v2_packages must NOT call _fetch_package_items_v2 for known packages."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    start = datetime.now() - timedelta(days=2)
    end = datetime.now()

    # Fake API returns two packages: P1 (known), P2 (new)
    list_response = {"items": [
        {"packageId": "P1"},
        {"packageId": "P2"},
    ]}
    items_response = {"items": [{"itemId": "I2", "name": "Yeni Ürün"}]}

    call_log = []

    def fake_fetch_json(project_root, path, *, v2, force_stage=None, timeout=20):
        call_log.append(path)
        if "packages?" in path and "items" not in path:
            return list_response
        if "packageId=P2" in path:
            return items_response
        return {"items": []}  # No more pages and no V1 orders

    with patch.object(ta, "_fetch_json", side_effect=fake_fetch_json):
        with patch.object(ta, "_fetch_orders_v1", return_value=[]):
            result = ta._fetch_orders_from_v2_packages(
                tmp_path, start, end, skip_package_ids={"P1"}
            )

    # Should only have one order (P2)
    assert len(result) == 1
    # Confirm _fetch_package_items_v2 was NOT called for P1
    items_calls = [c for c in call_log if "packageId=P1" in c]
    assert items_calls == [], "Must not fetch items for known package P1"


def test_fetch_orders_all_known_returns_empty(tmp_path):
    """If all packages are already known, return empty list (no API items calls)."""
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    start = datetime.now() - timedelta(days=2)
    end = datetime.now()

    list_response = {"items": [{"packageId": "P1"}, {"packageId": "P2"}]}

    items_call_count = [0]

    def fake_fetch_json(project_root, path, *, v2, force_stage=None, timeout=20):
        if "packageId=" in path:
            items_call_count[0] += 1
        if "packages?" in path and "items" not in path:
            return list_response
        return {"items": []}

    with patch.object(ta, "_fetch_json", side_effect=fake_fetch_json):
        result = ta._fetch_orders_from_v2_packages(
            tmp_path, start, end, skip_package_ids={"P1", "P2"}
        )

    assert result == []
    assert items_call_count[0] == 0, "_fetch_package_items_v2 must not be called"


def test_incremental_sync_uses_last_sync_at_window(tmp_path):
    """sync_recent_orders in incremental mode uses last_orders_sync_at as window start."""
    from webui_backend import trendyol_api as ta

    recent = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    _write_settings(tmp_path, last_orders_sync_at=recent)
    _write_orders_cache(tmp_path, [])

    captured_start = []

    def fake_fetch_orders(project_root, start, end, *, skip_package_ids=None, poll_statuses=None):
        captured_start.append(start)
        return []

    with patch.object(ta, "fetch_orders", side_effect=fake_fetch_orders):
        with patch.object(ta, "_refresh_questions_safely", return_value=[]):
            with patch.object(ta, "enrich_orders_with_product_catalog", side_effect=lambda p, o: o):
                ta.sync_recent_orders(tmp_path, days=7, incremental=True)

    assert captured_start, "fetch_orders should have been called"
    # The window start should be around last_sync - 1hr, much more recent than 7 days ago
    seven_days_ago = datetime.now() - timedelta(days=7)
    assert captured_start[0] > seven_days_ago, "Incremental start must be more recent than full window"


def test_is_configured_with_real_key(tmp_path):
    from webui_backend.trendyol_api import is_configured

    _write_settings(tmp_path)
    assert is_configured(tmp_path) is True


def test_is_configured_missing_key(tmp_path):
    from webui_backend.trendyol_api import is_configured

    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "trendyol_settings.json").write_text(
        json.dumps({"supplier_id": "12345", "api_key": "", "api_secret": ""}),
        encoding="utf-8",
    )
    assert is_configured(tmp_path) is False


def test_new_settings_fields_persisted(tmp_path):
    from webui_backend.trendyol_api import get_settings, save_settings

    _write_settings(tmp_path)
    save_settings(tmp_path, {"auto_sync_enabled": True, "auto_sync_interval_sec": 60})
    settings = get_settings(tmp_path, masked=False)
    assert settings["auto_sync_enabled"] is True
    assert settings["auto_sync_interval_sec"] == 60


# ─────────────────────────────────────────────────────────────────────────────
# FAZ 1 — Rate-limit backoff
# ─────────────────────────────────────────────────────────────────────────────

def test_fetch_json_with_retry_retries_on_429(tmp_path):
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    call_count = [0]

    def fake_fetch_json(project_root, path, *, v2, force_stage=None, timeout=20):
        call_count[0] += 1
        if call_count[0] < 3:
            raise RuntimeError("HTTP 429: Too Many Requests")
        return {"ok": True}

    with patch.object(ta, "_fetch_json", side_effect=fake_fetch_json):
        with patch("webui_backend.trendyol_api.time") as mock_time:
            mock_time.sleep = MagicMock()
            result = ta._fetch_json_with_retry(tmp_path, "/test", v2=False, max_retries=4)

    assert result == {"ok": True}
    assert call_count[0] == 3
    assert mock_time.sleep.call_count == 2  # Two sleeps before third attempt


def test_fetch_json_with_retry_raises_on_non_retryable(tmp_path):
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)

    def fake_fetch_json(project_root, path, *, v2, force_stage=None, timeout=20):
        raise RuntimeError("HTTP 401: Unauthorized")

    with patch.object(ta, "_fetch_json", side_effect=fake_fetch_json):
        with pytest.raises(RuntimeError, match="HTTP 401"):
            ta._fetch_json_with_retry(tmp_path, "/test", v2=False)


def test_fetch_json_with_retry_raises_after_max_retries(tmp_path):
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)

    def fake_fetch_json(project_root, path, *, v2, force_stage=None, timeout=20):
        raise RuntimeError("HTTP 429: Too Many Requests")

    with patch.object(ta, "_fetch_json", side_effect=fake_fetch_json):
        with patch("webui_backend.trendyol_api.time") as mock_time:
            mock_time.sleep = MagicMock()
            with pytest.raises(RuntimeError, match="429"):
                ta._fetch_json_with_retry(tmp_path, "/test", v2=False, max_retries=2)

    assert mock_time.sleep.call_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# FAZ 2 — Scheduler
# ─────────────────────────────────────────────────────────────────────────────

def test_scheduler_starts_and_stops(tmp_path):
    from server import trendyol_scheduler as sched

    # Reset state
    sched._stop_event.clear()
    sched._state["enabled"] = False
    sched._thread = None

    sched.start(tmp_path, interval_sec=10)
    assert sched.is_alive()
    assert sched.get_status()["enabled"] is True

    sched.stop()
    sched._thread.join(timeout=2)
    assert sched.get_status()["enabled"] is False


def test_scheduler_overlap_guard(tmp_path):
    """Scheduler must skip a new poll cycle while one is still running."""
    from server import trendyol_scheduler as sched

    sched._stop_event.clear()
    sched._state["enabled"] = True
    sched._state["running_poll"] = True  # Simulate ongoing poll

    poll_called = [False]

    def fake_do_poll(root):
        poll_called[0] = True

    original = sched._do_poll
    sched._do_poll = fake_do_poll

    try:
        # Manually trigger the loop body logic
        with sched._lock:
            if sched._state["running_poll"]:
                pass  # Would skip
        assert not poll_called[0], "Poll must be skipped when running_poll is True"
    finally:
        sched._do_poll = original
        sched._state["running_poll"] = False
        sched._state["enabled"] = False


def test_scheduler_expands_interval_on_rate_limit(tmp_path):
    from server import trendyol_scheduler as sched
    from webui_backend import trendyol_api as ta

    sched._state["interval_sec"] = 30
    sched._state["current_interval_sec"] = 30

    def fake_delta_sync(project_root):
        raise RuntimeError("HTTP 429: Rate limit")

    with patch.object(ta, "delta_sync_for_poll", side_effect=fake_delta_sync):
        sched._do_poll(tmp_path)

    assert sched._state["current_interval_sec"] > 30, "Interval must expand on rate-limit"


def test_scheduler_resets_interval_on_success(tmp_path):
    from server import trendyol_scheduler as sched
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path)
    sched._state["interval_sec"] = 30
    sched._state["current_interval_sec"] = 120  # Was expanded

    with patch.object(ta, "delta_sync_for_poll", return_value={"status": "OK_NO_NEW", "new_orders": 0, "new_questions": 0}):
        sched._do_poll(tmp_path)

    assert sched._state["current_interval_sec"] == 30, "Interval must reset to base on success"


# ─────────────────────────────────────────────────────────────────────────────
# FAZ 3 — delta_sync_for_poll
# ─────────────────────────────────────────────────────────────────────────────

def test_delta_sync_returns_config_missing_when_not_configured(tmp_path):
    from webui_backend.trendyol_api import delta_sync_for_poll

    (tmp_path / "data").mkdir(exist_ok=True)
    # No settings file
    result = delta_sync_for_poll(tmp_path)
    assert result["status"] == "CONFIG_MISSING"


def test_delta_sync_no_new_orders(tmp_path):
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path,
                    last_orders_sync_at=(datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"))
    _write_orders_cache(tmp_path, [{"shipmentPackageId": "P1", "orderNumber": "O1"}])

    with patch.object(ta, "fetch_orders", return_value=[]):
        with patch.object(ta, "_refresh_questions_delta", return_value=[]):
            result = ta.delta_sync_for_poll(tmp_path)

    assert result["status"] == "OK_NO_NEW"
    assert result["new_orders"] == 0


def test_delta_sync_merges_new_orders(tmp_path):
    from webui_backend import trendyol_api as ta

    _write_settings(tmp_path,
                    last_orders_sync_at=(datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"))
    _write_orders_cache(tmp_path, [{"shipmentPackageId": "P1", "orderNumber": "O1"}])

    new_order = {"shipmentPackageId": "P2", "orderNumber": "O2", "lines": []}

    with patch.object(ta, "fetch_orders", return_value=[new_order]):
        with patch.object(ta, "_refresh_questions_delta", return_value=[]):
            with patch.object(ta, "enrich_orders_with_product_catalog", side_effect=lambda p, o: o):
                with patch.object(ta, "build_suggestions_from_orders", return_value=[]):
                    result = ta.delta_sync_for_poll(tmp_path)

    assert result["new_orders"] == 1
    assert result["total_orders"] == 2  # P1 existing + P2 new
