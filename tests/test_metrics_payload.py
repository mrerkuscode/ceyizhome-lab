from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

# Proje src/ klasorunu path'e ekle
project_root = Path(__file__).resolve().parents[1]
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from webui_backend.report_api import metrics_payload


# ---------------------------------------------------------------------------
# Test yardimcilari
# ---------------------------------------------------------------------------

def _make_row(model_name="Model A", qty=1, preflight="OK", queue="ADDED", date=None):
    """Minimal production_history row factory."""
    if date is None:
        date = datetime.date.today().isoformat()
    return {
        "id": "test_" + model_name,
        "created_at": date + " 10:00:00",
        "model_name": model_name,
        "model_id": "test_id",
        "quantity": str(qty),
        "preflight_status": preflight,
        "queue_status": queue,
    }


def _run(history, date_range="today"):
    """Override ve calistir."""
    metrics_payload._history_override = history
    try:
        result = metrics_payload(date_range_json=json.dumps({"range": date_range}))
    finally:
        if hasattr(metrics_payload, "_history_override"):
            del metrics_payload._history_override
    return result


# ---------------------------------------------------------------------------
# Test 1 — Bos history
# ---------------------------------------------------------------------------

def test_empty_history():
    result = _run([])
    assert result["status"] == "OK", f"status beklenen OK: {result}"
    assert result["empty"] is True, f"empty=True bekleniyor: {result}"
    print("PASS test_empty_history")


# ---------------------------------------------------------------------------
# Test 2 — Bugun adet toplami
# ---------------------------------------------------------------------------

def test_today_count_sum():
    today = datetime.date.today().isoformat()
    history = [
        _make_row(qty=3, date=today),
        _make_row(qty=5, date=today),
        _make_row(qty=2, date="2020-01-01"),  # gecmis, sayilmamali
    ]
    result = _run(history)
    assert result["status"] == "OK"
    assert result["today"]["count"] == 8, f"Beklenen 8: {result['today']}"
    print("PASS test_today_count_sum")


# ---------------------------------------------------------------------------
# Test 3 — Delta hesabi
# ---------------------------------------------------------------------------

def test_delta_calculation():
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    history = [
        _make_row(qty=10, date=today),
        _make_row(qty=4, date=yesterday),
    ]
    result = _run(history)
    assert result["today"]["delta"] == 6, f"Delta beklenen 6: {result['today']}"
    assert result["today"]["delta_pct"] == 150.0, f"Pct beklenen 150: {result['today']}"
    print("PASS test_delta_calculation")


# ---------------------------------------------------------------------------
# Test 4 — Haftalik seri her zaman 7 uzunlukta
# ---------------------------------------------------------------------------

def test_weekly_series_length_is_7():
    today = datetime.date.today().isoformat()
    history = [_make_row(qty=1, date=today)]
    result = _run(history)
    assert len(result["weekly"]) == 7, f"weekly 7 gun olmali: {len(result['weekly'])}"
    print("PASS test_weekly_series_length_is_7")


# ---------------------------------------------------------------------------
# Test 5 — Top-3 siralaması
# ---------------------------------------------------------------------------

def test_top3_ordering():
    today = datetime.date.today().isoformat()
    history = [
        _make_row("Model A", qty=5, date=today),
        _make_row("Model B", qty=3, date=today),
        _make_row("Model C", qty=7, date=today),
        _make_row("Model D", qty=1, date=today),
    ]
    result = _run(history)
    top3 = result["top3_models"]
    assert top3[0]["model_name"] == "Model C", f"Birinci Model C olmali: {top3}"
    assert top3[0]["total_qty"] == 7
    assert top3[1]["model_name"] == "Model A"
    assert len(top3) == 3, "Top 3 olmali"
    print("PASS test_top3_ordering")


# ---------------------------------------------------------------------------
# Test 6 — Bilinmeyen preflight -> NO_CHECK
# ---------------------------------------------------------------------------

def test_preflight_unknown_maps_to_no_check():
    today = datetime.date.today().isoformat()
    history = [
        _make_row(preflight="OK", date=today),
        _make_row(preflight="UNKNOWN_STATUS", date=today),
        _make_row(preflight="", date=today),
    ]
    result = _run(history)
    pf = result["preflight"]
    assert pf["OK"] == 1, f"OK=1 bekleniyor: {pf}"
    assert pf["NO_CHECK"] == 2, f"NO_CHECK=2 bekleniyor: {pf}"
    print("PASS test_preflight_unknown_maps_to_no_check")


# ---------------------------------------------------------------------------
# Test 7 — Bozuk quantity field atlaniyor
# ---------------------------------------------------------------------------

def test_corrupted_quantity_field_skipped():
    today = datetime.date.today().isoformat()
    history = [
        _make_row(qty=5, date=today),
        {**_make_row(date=today), "quantity": "abc"},  # bozuk
        {**_make_row(date=today), "quantity": None},   # None
    ]
    result = _run(history)
    # abc ve None -> 0 sayilir, hata olmaz
    assert result["status"] == "OK"
    assert result["today"]["count"] == 5, f"Sadece 5 sayilmali: {result['today']}"
    print("PASS test_corrupted_quantity_field_skipped")


# ---------------------------------------------------------------------------
# Calistir
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_empty_history,
        test_today_count_sum,
        test_delta_calculation,
        test_weekly_series_length_is_7,
        test_top3_ordering,
        test_preflight_unknown_maps_to_no_check,
        test_corrupted_quantity_field_skipped,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
            failed += 1
    print(f"\n=== {passed} gecti, {failed} kaldi ===")
