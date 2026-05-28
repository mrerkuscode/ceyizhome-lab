from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from intelligence.trendyol_ai_extractor import extract_with_ai_or_fallback  # noqa: E402
from intelligence.trendyol_order_extractor import extract_production_fields  # noqa: E402
from webui_backend import trendyol_api  # noqa: E402


DATA_PATH = PROJECT_ROOT / "data" / "trendyol_production_suggestions.json"
OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "trendyol_reprocess"
REPORT_JSON = OUTPUT_DIR / "REPROCESS_REPORT.json"
REPORT_MD = OUTPUT_DIR / "REPROCESS_REPORT.md"

EXTRACTION_FIELDS = [
    "person_names",
    "label_text",
    "name_cut_text",
    "date_text",
    "custom_text",
    "production_note",
    "note_text",
    "quantity",
    "confidence",
    "field_confidence",
    "field_sources",
    "evidence_spans",
    "source_evidence",
    "warnings",
    "needs_user_review",
]


def _field_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in EXTRACTION_FIELDS}


def _has_customer_message(row: dict[str, Any]) -> bool:
    if str(row.get("question_text") or "").strip():
        return True
    contexts = row.get("question_contexts") if isinstance(row.get("question_contexts"), list) else []
    return any(isinstance(item, dict) and str(item.get("question_text") or "").strip() for item in contexts)


def _is_locked(row: dict[str, Any]) -> bool:
    return bool(row.get("import_status")) or row.get("verification_status") == trendyol_api.VERIFICATION_TRANSFERRED


def _apply_reprocessed_fields(row: dict[str, Any], extracted: dict[str, Any]) -> None:
    trendyol_api._apply_extracted_fields(row, extracted)  # noqa: SLF001
    row["ai_autonomous"] = False
    row["ai_model_confidence"] = row.get("confidence") or 0
    row["verification_status"] = trendyol_api.VERIFICATION_WAITING_APPROVAL
    row["status"] = "review"
    row["user_verified"] = False
    row["verified_at"] = ""
    row["verified_by"] = ""
    row["updated_at"] = datetime.now().isoformat(timespec="seconds")


def _build_report(changes: list[dict[str, Any]], skipped: dict[str, int], total: int, backup_path: Path, mode: str) -> dict[str, Any]:
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "total_rows": total,
        "processed_rows": total - skipped["locked"] - skipped["no_message"],
        "changed_rows": len(changes),
        "skipped": skipped,
        "backup_path": str(backup_path),
        "changes": changes,
    }


def _write_report(report: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Trendyol Extraction Reprocess Report",
        "",
        f"- Created: {report['created_at']}",
        f"- Mode: {report['mode']}",
        f"- Total rows: {report['total_rows']}",
        f"- Processed rows: {report['processed_rows']}",
        f"- Changed rows: {report['changed_rows']}",
        f"- Backup: `{report['backup_path']}`",
        "",
        "## Changes",
        "",
    ]
    if not report["changes"]:
        lines.append("No extraction fields changed.")
    for item in report["changes"][:200]:
        before = item["before"]
        after = item["after"]
        lines.extend(
            [
                f"### {item.get('order_number') or '-'} / {item.get('line_id') or '-'}",
                f"- Customer: {item.get('customer_name') or '-'}",
                f"- Label: `{before.get('label_text') or ''}` -> `{after.get('label_text') or ''}`",
                f"- Laser: `{before.get('name_cut_text') or ''}` -> `{after.get('name_cut_text') or ''}`",
                f"- Date: `{before.get('date_text') or ''}` -> `{after.get('date_text') or ''}`",
                f"- Person names: `{before.get('person_names') or []}` -> `{after.get('person_names') or []}`",
                f"- Confidence: `{before.get('confidence') or 0}` -> `{after.get('confidence') or 0}`",
                "",
            ]
        )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reprocess local Trendyol extraction fields without approving or importing rows.")
    parser.add_argument("--cloud-ai", action="store_true", help="Use configured cloud AI. Default uses local learning + explicit extractor only.")
    parser.add_argument("--dry-run", action="store_true", help="Create report without writing updated suggestions.")
    args = parser.parse_args()

    if not DATA_PATH.exists():
        print(f"missing data file: {DATA_PATH}")
        return 1
    rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        print("suggestions data is not a list")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = OUTPUT_DIR / f"trendyol_production_suggestions.{datetime.now().strftime('%H%M%S')}.json"
    shutil.copy2(DATA_PATH, backup_path)

    settings = trendyol_api.get_settings(PROJECT_ROOT, masked=False) if args.cloud_ai else {"ai_enabled": False}
    changes: list[dict[str, Any]] = []
    skipped = {"locked": 0, "no_message": 0}
    next_rows: list[Any] = []
    for row in rows:
        if not isinstance(row, dict):
            next_rows.append(row)
            continue
        if _is_locked(row):
            skipped["locked"] += 1
            next_rows.append(row)
            continue
        if not _has_customer_message(row):
            skipped["no_message"] += 1
            next_rows.append(row)
            continue
        before = _field_snapshot(row)
        working = dict(row)
        mapping = trendyol_api._mapping_from_suggestion(working)  # noqa: SLF001
        deterministic = extract_production_fields(working, mapping)
        extracted = extract_with_ai_or_fallback(PROJECT_ROOT, working, mapping, deterministic, settings)
        _apply_reprocessed_fields(working, extracted)
        after = _field_snapshot(working)
        if before != after:
            changes.append(
                {
                    "id": row.get("id"),
                    "order_number": row.get("order_number"),
                    "line_id": row.get("line_id"),
                    "customer_name": row.get("customer_name"),
                    "before": before,
                    "after": after,
                }
            )
            next_rows.append(working)
        else:
            next_rows.append(row)

    report = _build_report(changes, skipped, len(rows), backup_path, "cloud-ai" if args.cloud_ai else "local")
    _write_report(report)
    if not args.dry_run:
        DATA_PATH.write_text(json.dumps(next_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"backup: {backup_path}")
    print(f"report_json: {REPORT_JSON}")
    print(f"report_md: {REPORT_MD}")
    print(f"processed: {report['processed_rows']}")
    print(f"changed: {len(changes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
