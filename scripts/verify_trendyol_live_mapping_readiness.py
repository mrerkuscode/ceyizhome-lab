from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend import trendyol_api, trendyol_mapping_api  # noqa: E402


def main() -> int:
    output_dir = PROJECT_ROOT / "output" / date.today().isoformat() / "trendyol"
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = trendyol_api.get_settings(PROJECT_ROOT, masked=True)
    mapping_suggestions = trendyol_api.list_mapping_suggestions(PROJECT_ROOT)
    production_suggestions = trendyol_api.list_suggestions(PROJECT_ROOT)
    approved_mappings = trendyol_mapping_api.list_product_mappings(PROJECT_ROOT)

    unsafe_auto_candidates = [
        row
        for row in mapping_suggestions
        if row.get("status") in {"suggested", "approved"}
        and (
            row.get("production_type") in {"review", "none", ""}
            or not row.get("barcode")
            or ("qa" in _key(row.get("model_name")) or "test" in _key(row.get("model_name")) or "kabul" in _key(row.get("model_name")))
        )
    ]
    ready_without_mapping = [
        row
        for row in production_suggestions
        if row.get("status") == "ready" and not row.get("mapping_found") and not row.get("ai_autonomous")
    ]
    ai_autonomous_ready = [
        row
        for row in production_suggestions
        if row.get("status") == "ready" and row.get("ai_autonomous")
    ]
    review_export = _write_review_excel(output_dir, mapping_suggestions)
    report = {
        "status": "PASSED" if not unsafe_auto_candidates and not ready_without_mapping else "FAILED",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "settings_configured": bool(settings.get("configured")),
        "settings_environment": settings.get("environment"),
        "approved_mapping_count": len(approved_mappings),
        "mapping_suggestion_count": len(mapping_suggestions),
        "mapping_suggestions_by_status": dict(Counter(str(row.get("status") or "") for row in mapping_suggestions)),
        "mapping_suggestions_by_type": dict(Counter(str(row.get("production_type") or "") for row in mapping_suggestions)),
        "production_suggestion_count": len(production_suggestions),
        "production_suggestions_by_status": dict(Counter(str(row.get("status") or "") for row in production_suggestions)),
        "production_suggestions_by_type": dict(Counter(str(row.get("production_type") or "") for row in production_suggestions)),
        "ai_autonomous_ready_count": len(ai_autonomous_ready),
        "unsafe_auto_candidate_count": len(unsafe_auto_candidates),
        "ready_without_mapping_count": len(ready_without_mapping),
        "review_excel": str(review_export.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "safety": {
            "secrets_printed": False,
            "direct_print": False,
            "rdworks_auto_open": False,
            "laser_auto_start": False,
            "unmapped_products_require_review_or_high_confidence_ai_candidate": True,
            "physical_action_requires_user": True,
        },
    }
    report_path = output_dir / "trendyol_live_mapping_readiness_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASSED" else 1


def _write_review_excel(output_dir: Path, rows: list[dict[str, Any]]) -> Path:
    review_rows = []
    for row in rows:
        review_rows.append(
            {
                "durum": row.get("status") or "",
                "uretim_tipi_onerisi": row.get("production_type") or "",
                "guven": row.get("confidence") or 0,
                "urun_adi": row.get("product_name") or "",
                "barcode": row.get("barcode") or "",
                "merchant_sku": row.get("merchant_sku") or "",
                "stock_code": row.get("stock_code") or "",
                "model_onerisi": row.get("model_name") or "",
                "model_path": row.get("model_path") or "",
                "nedenler": ", ".join(str(item) for item in (row.get("reasons") or [])),
                "not": "Kontrol edip Trendyol Ürün Eşleştirme ekranından onaylayın.",
            }
        )
    target = output_dir / f"trendyol_mapping_review_{datetime.now().strftime('%H%M%S_%f')}.xlsx"
    pd.DataFrame(review_rows).to_excel(target, index=False)
    return target


def _key(value: Any) -> str:
    return str(value or "").strip().lower()


if __name__ == "__main__":
    raise SystemExit(main())
