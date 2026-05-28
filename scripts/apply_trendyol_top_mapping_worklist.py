from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from intelligence.text_cleanup import repair_text  # noqa: E402
from scripts.prepare_trendyol_operator_worklist import build_worklist  # noqa: E402
from scripts.audit_trendyol_live_data_quality import run_audit  # noqa: E402
from webui_backend import trendyol_api, trendyol_mapping_api  # noqa: E402


MODEL_PATH = PROJECT_ROOT / "templates" / "designs" / "01_a_gold.json"
MODEL_KEY = "01"
MODEL_NAME = "01 A Gold Rulo Etiket"
PRODUCTION_TYPE = "label_and_name_cut"
NAME_CUT_STYLE = "Mochary Personal Use Only"
NAME_CUT_WIDTH_MM = 300.0


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _key(value: Any) -> str:
    return str(value or "").strip().lower()


def _has_question_evidence(row: dict[str, Any]) -> bool:
    if repair_text(row.get("question_text") or "") or repair_text(row.get("answer_text") or ""):
        return True
    contexts = row.get("question_contexts") if isinstance(row.get("question_contexts"), list) else []
    return any(isinstance(item, dict) and (repair_text(item.get("question_text") or "") or repair_text(item.get("answer_text") or "")) for item in contexts)


def _has_personalization(row: dict[str, Any]) -> bool:
    return bool(repair_text(row.get("label_text") or "") or repair_text(row.get("name_cut_text") or ""))


def _filtered_warnings(row: dict[str, Any]) -> list[str]:
    blocked = {
        "Bu barcode/SKU için ürün eşleştirmesi yok.",
        "Ürün eşleştirmesi üretim için aktif değil veya kontrol istiyor.",
        "Etiket üretimi için model seçilmedi.",
    }
    warnings: list[str] = []
    for item in row.get("warnings") or []:
        text = repair_text(item or "").strip()
        if text and text not in blocked and text not in warnings:
            warnings.append(text)
    return warnings


def _verification_after_mapping(row: dict[str, Any]) -> str:
    if not _has_question_evidence(row):
        return trendyol_api.VERIFICATION_WAITING_EVIDENCE
    if not _has_personalization(row):
        return trendyol_api.VERIFICATION_USER_REVIEW
    if float(row.get("confidence") or 0) < 0.7:
        return trendyol_api.VERIFICATION_USER_REVIEW
    return trendyol_api.VERIFICATION_WAITING_APPROVAL


def _mapping_payload(task: dict[str, Any]) -> dict[str, Any]:
    merchant_sku = task.get("merchant_sku") or ""
    if _key(merchant_sku) in {"merchantsku", "merchant_sku"}:
        merchant_sku = ""
    return {
        "product_name": task.get("product_name") or "",
        "barcode": task.get("barcode") or "",
        "merchant_sku": merchant_sku,
        "stock_code": merchant_sku,
        "image_url": task.get("image_url") or "",
        "production_type": PRODUCTION_TYPE,
        "model_key": MODEL_KEY,
        "model_path": str(MODEL_PATH),
        "model_name": MODEL_NAME,
        "quantity_source": "line_quantity",
        "default_note_text": "",
        "default_date_text": "",
        "name_cut_style": NAME_CUT_STYLE,
        "name_cut_width_mm": NAME_CUT_WIDTH_MM,
        "active": True,
    }


def _matches_task(row: dict[str, Any], task: dict[str, Any]) -> bool:
    barcode = _key(task.get("barcode"))
    merchant_sku = _key(task.get("merchant_sku"))
    row_barcode = _key(row.get("barcode"))
    row_sku = _key(row.get("merchant_sku") or row.get("stock_code"))
    if barcode and row_barcode == barcode:
        return True
    return bool(merchant_sku and merchant_sku not in {"merchantsku"} and row_sku == merchant_sku)


def apply_top_mappings(limit: int = 5) -> dict[str, Any]:
    audit_payload = run_audit(refresh=False)
    worklist = build_worklist(audit_payload)
    tasks = (worklist.get("mapping_tasks") or [])[:limit]
    mapping_path = trendyol_mapping_api.mappings_path(PROJECT_ROOT)
    suggestions_path = trendyol_api.suggestions_path(PROJECT_ROOT)
    backup_dir = PROJECT_ROOT / "output" / datetime.now().strftime("%Y-%m-%d") / "trendyol_mapping_apply_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backups: dict[str, str] = {}
    if mapping_path.exists():
        mapping_backup = backup_dir / f"trendyol_product_mappings_{datetime.now().strftime('%H%M%S')}.json"
        shutil.copy2(mapping_path, mapping_backup)
        backups["mappings"] = str(mapping_backup)
    if suggestions_path.exists():
        suggestions_backup = backup_dir / f"trendyol_production_suggestions_{datetime.now().strftime('%H%M%S')}.json"
        shutil.copy2(suggestions_path, suggestions_backup)
        backups["suggestions"] = str(suggestions_backup)

    upserts: list[dict[str, Any]] = []
    for task in tasks:
        result = trendyol_mapping_api.upsert_product_mapping(PROJECT_ROOT, _mapping_payload(task))
        upserts.append(
            {
                "barcode": task.get("barcode") or "",
                "merchant_sku": task.get("merchant_sku") or "",
                "row_count": task.get("row_count") or 0,
                "status": result.get("status"),
                "message": result.get("message"),
            }
        )

    rows = trendyol_api.list_suggestions(PROJECT_ROOT)
    touched = 0
    opened_rows = 0
    for row in rows:
        task = next((item for item in tasks if _matches_task(row, item)), None)
        if not task:
            continue
        touched += 1
        row["mapping_found"] = True
        row["mapping_source"] = "operator_top5_batch"
        row["production_type"] = PRODUCTION_TYPE
        row["model_key"] = MODEL_KEY
        row["model_path"] = str(MODEL_PATH)
        row["model_name"] = MODEL_NAME
        row["name_cut_style"] = row.get("name_cut_style") or NAME_CUT_STYLE
        row["name_cut_width_mm"] = row.get("name_cut_width_mm") or NAME_CUT_WIDTH_MM
        row["warnings"] = _filtered_warnings(row)
        row["verification_status"] = _verification_after_mapping(row)
        row["status"] = "review"
        row["user_verified"] = False
        row["updated_at"] = _now()
        if row["verification_status"] in {trendyol_api.VERIFICATION_WAITING_APPROVAL, trendyol_api.VERIFICATION_USER_REVIEW}:
            opened_rows += 1
    trendyol_api.save_suggestions(PROJECT_ROOT, rows)

    return {
        "status": "OK",
        "applied_mapping_count": len(upserts),
        "suggestion_rows_updated": touched,
        "rows_opened_for_operator_review": opened_rows,
        "model": {
            "production_type": PRODUCTION_TYPE,
            "model_key": MODEL_KEY,
            "model_path": str(MODEL_PATH),
            "model_name": MODEL_NAME,
        },
        "upserts": upserts,
        "backups": backups,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    result = apply_top_mappings(limit=max(1, args.limit))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
