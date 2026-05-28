from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from intelligence import trendyol_ai_extractor
from intelligence.trendyol_order_extractor import extract_production_fields
from intelligence.text_cleanup import repair_text


DATA_PATH = PROJECT_ROOT / "data" / "trendyol_production_suggestions.json"
BACKUP_DIR = PROJECT_ROOT / "output" / datetime.now().strftime("%Y-%m-%d") / "trendyol_repair_backups"

BAD_NAME_TOKENS = {
    "gümüş",
    "gumus",
    "hatırası",
    "hatirasi",
    "hepsi beyaz",
    "numaram",
    "numarası",
    "numarasi",
    "siparişimiz",
    "siparisimiz",
    "siparişim",
    "siparisim",
    "de ",
    "için",
    "icin",
    "kişiselleştirme",
    "kisisellestirme",
    "fotoğraftaki",
    "fotograftaki",
    "resimdeki",
    "tarihte",
    "kolay gelsin",
    "cuma gününe",
    "çift isimleri",
    "cift isimleri",
    "şeklinde",
    "seklinde",
    "yazıyor",
    "yaziyor",
    "kurdele",
    "gold yazı",
    "gold yazi",
}


def _text(value: Any) -> str:
    return repair_text(str(value or "")).strip()


def _source_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_text": _text(row.get("question_text")),
        "answer_text": _text(row.get("answer_text")),
        "question_contexts": row.get("question_contexts") if isinstance(row.get("question_contexts"), list) else [],
        "product_name": _text(row.get("product_name")),
        "barcode": _text(row.get("barcode")),
        "merchant_sku": _text(row.get("merchant_sku") or row.get("stock_code")),
        "quantity": row.get("quantity") or 1,
        "order_number": _text(row.get("order_number")),
        "line_id": _text(row.get("line_id")),
        "customer_name": _text(row.get("customer_name")),
    }


def _mapping_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "production_type": row.get("production_type") or "label_and_name_cut",
        "model_key": row.get("model_key") or "",
        "model_path": row.get("model_path") or "",
        "model_name": row.get("model_name") or "",
        "name_cut_width_mm": row.get("name_cut_width_mm") or 300,
        "name_cut_style": row.get("name_cut_style") or "Mochary Personal Use Only",
    }


def _looks_stale(row: dict[str, Any], repaired: dict[str, Any]) -> bool:
    label = _text(row.get("label_text") or row.get("name_cut_text")).casefold()
    label_key = label.replace("\u0307", "")
    has_bad_token = any(token.casefold().replace("\u0307", "") in label_key for token in BAD_NAME_TOKENS)
    has_repaired_names = bool(repaired.get("person_names"))
    changed_name = _text(row.get("label_text")) != _text(repaired.get("label_text"))
    missing_name = not bool(row.get("person_names")) and not bool(_text(row.get("label_text") or row.get("name_cut_text")))
    repaired_label = _text(repaired.get("label_text")).casefold()
    repaired_label_key = repaired_label.replace("\u0307", "")
    repaired_has_bad_token = any(token.casefold().replace("\u0307", "") in repaired_label_key for token in BAD_NAME_TOKENS)
    return bool(has_repaired_names and (has_bad_token or missing_name) and changed_name and not repaired_has_bad_token)


def _apply_repair(row: dict[str, Any], repaired: dict[str, Any]) -> dict[str, Any]:
    next_row = dict(row)
    for key in [
        "label_text",
        "name_cut_text",
        "date_text",
        "note_text",
        "person_names",
        "custom_text",
        "production_note",
        "confidence",
        "field_confidence",
        "field_sources",
        "evidence_spans",
        "source_evidence",
        "warnings",
        "name_cut_width_mm",
        "name_cut_style",
        "needs_user_review",
    ]:
        if key in repaired:
            next_row[key] = repaired[key]
    next_row["ai_autonomous"] = False
    next_row["ai_model_confidence"] = repaired.get("confidence", next_row.get("ai_model_confidence", 0))
    next_row["verification_status"] = "alanlar_onay_bekliyor"
    next_row["status"] = "review"
    next_row["user_verified"] = False
    next_row["verified_at"] = None
    next_row["verified_by"] = None
    next_row["updated_at"] = datetime.now().isoformat(timespec="seconds")
    return next_row


def main() -> int:
    if not DATA_PATH.exists():
        print(f"missing data file: {DATA_PATH}")
        return 1
    rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        print("suggestions data is not a list")
        return 1

    repaired_rows: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            repaired_rows.append(row)
            continue
        source = _source_from_row(row)
        mapping = _mapping_from_row(row)
        deterministic = extract_production_fields(source, mapping)
        repaired = trendyol_ai_extractor.extract_with_ai_or_fallback(
            PROJECT_ROOT,
            source,
            mapping,
            deterministic,
            {"ai_enabled": False},
        )
        if _looks_stale(row, repaired):
            repaired_row = _apply_repair(row, repaired)
            changes.append(
                {
                    "order_number": row.get("order_number"),
                    "before": row.get("label_text"),
                    "after": repaired_row.get("label_text"),
                    "person_names": repaired_row.get("person_names"),
                }
            )
            repaired_rows.append(repaired_row)
        else:
            repaired_rows.append(row)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"trendyol_production_suggestions.{datetime.now().strftime('%H%M%S')}.json"
    shutil.copy2(DATA_PATH, backup_path)
    DATA_PATH.write_text(json.dumps(repaired_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"backup: {backup_path}")
    print(f"repaired: {len(changes)}")
    for change in changes[:80]:
        print(json.dumps(change, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
