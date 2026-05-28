from __future__ import annotations

import csv
from pathlib import Path

from desktop.report_loader import ReportSet, load_latest_reports

from .text_normalizer import friendly_error


def load_reports(project_root: Path) -> ReportSet:
    return load_latest_reports(project_root)


def readiness(report_set: ReportSet | None) -> str:
    if report_set is None:
        return "NO_CHECK"
    if _non_empty(report_set.error_rows):
        return "BLOKE"
    if _non_empty(report_set.review_rows):
        return "KONTROL_GEREKLI"
    if report_set.summary_rows:
        return "HAZIR"
    return "NO_CHECK"


def summary(report_set: ReportSet | None) -> dict[str, int]:
    row = report_set.summary_rows[0] if report_set and report_set.summary_rows else {}
    errors = _non_empty(report_set.error_rows if report_set else [])
    review = _non_empty(report_set.review_rows if report_set else [])
    laser_jobs = _to_int(row.get("laser_engrave_jobs_count") or row.get("laser_engrave_jobs")) + _to_int(
        row.get("laser_cut_jobs_count") or row.get("laser_cut_jobs")
    ) + _to_int(row.get("both_jobs_count") or row.get("both_jobs"))
    return {
        "valid": _to_int(row.get("valid_rows")),
        "errors": len(errors) or _to_int(row.get("invalid_rows")),
        "review": len(review),
        "label": _to_int(row.get("print_jobs_count") or row.get("print_jobs")),
        "print": _to_int(row.get("print_jobs_count") or row.get("print_jobs")),
        "laser": laser_jobs,
    }


def first_errors(report_set: ReportSet | None, limit: int = 5) -> list[dict[str, str]]:
    rows = _non_empty(report_set.error_rows if report_set else [])[:limit]
    return [friendly_error(row) for row in rows]


def report_payload(report_set: ReportSet | None) -> dict[str, object]:
    if report_set is None:
        return {}
    return {
        "humanSummary": report_set.human_summary,
        "errors": [friendly_error(row) for row in _non_empty(report_set.error_rows)],
        "reviewRows": _non_empty(report_set.review_rows),
        "warnings": _non_empty(report_set.warning_rows),
        "labelRows": _label_rows(report_set),
        "laserRows": _non_empty(report_set.material_rows),
        "svgFiles": [str(path) for path in report_set.svg_files],
    }


def _label_rows(report_set: ReportSet) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in report_set.print_data_files:
        csv_rows = _read_csv(path)
        if not csv_rows:
            rows.append({"file": str(path), "name": path.name, "status": "Rapor boş veya henüz üretilmedi"})
            continue
        for row in csv_rows[:50]:
            combined = {"file": str(path), "name": path.name}
            combined.update({str(key): str(value) for key, value in row.items()})
            rows.append(combined)
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _non_empty(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if any((value or "").strip() for value in row.values())]


def _to_int(value: object) -> int:
    try:
        return int(float(str(value or 0)))
    except ValueError:
        return 0


import json as _json
import datetime as _datetime
from collections import Counter as _Counter


def metrics_payload(date_range_json: str, project_root: "Path | None" = None) -> dict:
    """Üretim Nabzı Dashboard için KPI metriklerini döndürür.

    Veri kaynağı: data/production_history.json
    Mevcut fonksiyonlara (load_reports, readiness, summary, report_payload) DOKUNMAZ.
    """
    # --- history yükle ---
    history_path = (project_root / "data" / "production_history.json") if project_root else None
    history: list = []
    if history_path and history_path.exists():
        try:
            with history_path.open("r", encoding="utf-8") as f:
                history = _json.load(f)
            if not isinstance(history, list):
                history = []
        except (_json.JSONDecodeError, OSError):
            return {"status": "ERROR", "message": "Üretim geçmişi okunamadı", "empty": True}
    else:
        # history_override desteği (testler için)
        if hasattr(metrics_payload, "_history_override"):
            history = metrics_payload._history_override  # type: ignore[attr-defined]

    if not history:
        return {"status": "OK", "empty": True, "message": "Henüz üretim verisi bulunamadı"}

    # --- tarih hesapları ---
    today = _datetime.date.today()
    yesterday = today - _datetime.timedelta(days=1)
    week_start = today - _datetime.timedelta(days=6)

    def row_date(row: dict) -> "_datetime.date | None":
        try:
            return _datetime.date.fromisoformat(str(row.get("created_at", ""))[:10])
        except ValueError:
            return None

    def safe_qty(row: dict) -> int:
        """Bozuk quantity (None, str, negatif) → 0. Sadece geçerli pozitif int sayılır."""
        raw = row.get("quantity")
        if raw is None:
            return 0
        try:
            qty = int(raw)
            if qty < 0:
                return 0
            return qty
        except (ValueError, TypeError):
            return 0

    today_rows = [r for r in history if row_date(r) == today]
    yesterday_rows = [r for r in history if row_date(r) == yesterday]
    week_rows = [r for r in history if (d := row_date(r)) is not None and week_start <= d <= today]

    today_count = sum(safe_qty(r) for r in today_rows)
    yesterday_count = sum(safe_qty(r) for r in yesterday_rows)
    delta = today_count - yesterday_count
    delta_pct: "float | None" = round(delta / yesterday_count * 100, 1) if yesterday_count > 0 else None

    # --- haftalık seri (7 gün) ---
    weekly_series = []
    for offset in range(7):
        day = week_start + _datetime.timedelta(days=offset)
        day_rows = [r for r in week_rows if row_date(r) == day]
        weekly_series.append({
            "date": day.isoformat(),
            "count": sum(safe_qty(r) for r in day_rows),
            "has_data": len(day_rows) > 0,
        })

    # --- top-3 model ---
    model_qty: _Counter = _Counter()
    for row in history:
        name = str(row.get("model_name") or "Bilinmeyen Model").strip() or "Bilinmeyen Model"
        model_qty[name] += safe_qty(row)
    top3 = [{"model_name": k, "total_qty": v} for k, v in model_qty.most_common(3)]

    # --- preflight dağılımı ---
    pf: _Counter = _Counter()
    for row in history:
        status = str(row.get("preflight_status") or "NO_CHECK").strip().upper()
        if status not in ("OK", "WARNING", "BLOKE", "NO_CHECK"):
            status = "NO_CHECK"
        pf[status] += 1
    preflight_dist = {
        "OK": pf.get("OK", 0),
        "WARNING": pf.get("WARNING", 0),
        "BLOKE": pf.get("BLOKE", 0),
        "NO_CHECK": pf.get("NO_CHECK", 0),
    }

    # --- queue durumu ---
    total = len(history)
    added = sum(1 for r in history if str(r.get("queue_status", "")).upper() == "ADDED")
    queue_pct = round(added / total * 100) if total > 0 else 0

    return {
        "status": "OK",
        "empty": False,
        "today": {
            "count": today_count,
            "delta": delta,
            "delta_pct": delta_pct,
        },
        "weekly": weekly_series,
        "top3_models": top3,
        "preflight": preflight_dist,
        "queue": {"added": added, "total": total, "pct": queue_pct},
    }
