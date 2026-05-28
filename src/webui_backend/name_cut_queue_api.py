from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


ALLOWED_STATUSES = {"pending_preparation", "needs_review", "blocked", "prepared", "exported"}
PRODUCTION_ALLOWED_PATH_SOURCES = {
    "corel_exact_reference",
    "operator_approved_generated",
    "operator_approved_internal_generated",
}
PRODUCTION_REVIEW_PATH_SOURCES = {
    "corel_style_reproducer",
    "corel_style_ai_generated",
    "internal_ai_assisted_name_engine",
    "reference_missing_fallback_generated",
    "candidate_hint",
    "style_reference_only",
}
SOURCE_LABELS = {
    "bulk_production": "Toplu Üretim",
    "manual_label": "Manuel Etiket",
    "etiket_studio": "Etiket Studio",
    "trendyol": "Trendyol",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def queue_path(project_root: Path) -> Path:
    path = project_root / "data" / "name_cut_queue.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def history_path(project_root: Path) -> Path:
    path = project_root / "data" / "name_cut_transfer_history.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def export_history_path(project_root: Path) -> Path:
    path = project_root / "data" / "name_cut_export_history.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _save_json_list(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_source(value: object) -> str:
    source = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return source if source in SOURCE_LABELS else source


def source_label_for(source: object, fallback: object = "") -> str:
    normalized = normalize_source(source)
    return SOURCE_LABELS.get(normalized) or str(fallback or "")


def duplicate_key_for(row: dict[str, Any]) -> str:
    explicit = str(row.get("duplicate_key") or "").strip()
    if explicit:
        return explicit
    source = normalize_source(row.get("source") or "bulk_production") or "bulk_production"
    bulk_row_id = str(row.get("bulk_row_id") or row.get("item_id") or row.get("id") or "").strip()
    return f"{source}:{bulk_row_id}" if bulk_row_id else f"{source}:{uuid.uuid4().hex}"


def normalize_status(value: object) -> str:
    status = str(value or "pending_preparation").strip().lower()
    return status if status in ALLOWED_STATUSES else "needs_review"


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "yes", "evet", "passed", "ok"}


def _path_hash(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    import hashlib
    import re

    normalized = re.sub(r"\s+", " ", raw)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _production_path_source(row: dict[str, Any]) -> str:
    for key in (
        "pathSource",
        "path_source",
        "productionPathSource",
        "production_path_source",
        "corelReferenceSource",
        "corel_reference_source",
        "referenceSource",
        "reference_source",
    ):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def production_queue_gate(row: dict[str, Any]) -> dict[str, Any]:
    source = _production_path_source(row)
    reason_codes: list[str] = []
    reasons: list[str] = []

    def block(code: str, message: str) -> None:
        if code not in reason_codes:
            reason_codes.append(code)
            reasons.append(message)

    if source not in PRODUCTION_ALLOWED_PATH_SOURCES:
        if source in PRODUCTION_REVIEW_PATH_SOURCES:
            block("operator_review_required", "Operator onayı gerekiyor; review/candidate kaynak üretime alınamaz.")
        else:
            block("invalid_source", "Corel exact referansı yok veya üretim kaynağı belirsiz.")

    if not _truthy(row.get("readyForCut") if "readyForCut" in row else row.get("ready_for_cut")):
        block("not_ready_for_cut", "readyForCut true değil.")

    final_path = str(row.get("finalCutPathData") or row.get("final_cut_path_data") or row.get("pathData") or "").strip()
    if not final_path:
        block("missing_final_cut_path", "finalCutPathData yok.")
    if "<text" in final_path.lower() or _truthy(row.get("hasTextElement") or row.get("has_text_element")):
        block("text_element_found", "SVG/path içinde text elementi var.")
    if not _truthy(row.get("isPathOnly") if "isPathOnly" in row else row.get("is_path_only")):
        block("not_path_only", "Export path-only değil.")

    final_hash = _path_hash(final_path)
    canvas_hash = str(row.get("canvasPathHash") or row.get("canvas_path_hash") or final_hash)
    export_hash = str(row.get("exportPathHash") or row.get("export_path_hash") or final_hash)
    reference_hash = str(row.get("referencePathHash") or row.get("reference_path_hash") or final_hash)
    if canvas_hash != export_hash:
        block("canvas_export_mismatch", "Canvas/export path uyuşmuyor.")
    if source == "corel_exact_reference" and canvas_hash != reference_hash:
        block("reference_hash_mismatch", "Canvas/export path Corel reference hash ile uyuşmuyor.")

    if not _truthy(row.get("markOwnershipPassed") if "markOwnershipPassed" in row else row.get("mark_ownership_passed")):
        block("mark_ownership_failed", "Türkçe karakter işaret sahipliği doğrulanmadı.")
    if int(row.get("detachedMarkCount") or row.get("detached_mark_count") or 0) != 0:
        block("detached_mark", "Türkçe karakter noktası/kuyruğu kopuk.")
    if int(row.get("wrongGlyphMarkCount") or row.get("wrong_glyph_mark_count") or 0) != 0:
        block("wrong_glyph_mark", "Türkçe işaret yanlış harfe bağlı.")
    if int(row.get("extraMarkCount") or row.get("extra_mark_count") or 0) != 0:
        block("extra_mark", "Fazladan nokta/işaret algılandı.")
    if _truthy(row.get("markBlobRisk") or row.get("mark_blob_risk")):
        block("mark_blob_risk", "Türkçe karakter noktası/blob riski var.")

    if int(row.get("componentCount") or row.get("component_count") or 0) <= 0:
        block("invalid_component_count", "Path component count geçersiz.")
    if _truthy(row.get("internalGarbagePath") or row.get("internal_garbage_path")):
        block("internal_garbage_path", "Kirli iç path/overlap çizgisi var.")
    manufacturable = _truthy(row.get("manufacturabilityPassed") if "manufacturabilityPassed" in row else row.get("manufacturability_passed"))
    if not manufacturable and str(row.get("manufacturabilityStatus") or row.get("manufacturability_status") or "") != "manufacturable_passed":
        block("manufacturability_failed", "Lazer kesim riski var.")
    if _truthy(row.get("tinyHoleRisk") or row.get("tiny_hole_risk")):
        block("tiny_hole_risk", "Tiny hole riski var.")
    if _truthy(row.get("narrowNeckRisk") or row.get("narrow_neck_risk")):
        block("narrow_neck_risk", "Dar boyun/kırılma riski var.")

    if _truthy(row.get("collision") or row.get("hasCollision") or row.get("has_collision")):
        block("collision", "Çakışma var.")
    if not _truthy(row.get("withinWorkArea") if "withinWorkArea" in row else row.get("within_work_area")):
        block("outside_work_area", "Çalışma alanı dışına taşıyor.")
    if not _truthy(row.get("differentNamesNotWelded") if "differentNamesNotWelded" in row else row.get("different_names_not_welded")):
        block("different_names_welded", "Farklı isimler birbirine weld edilmiş olabilir.")
    try:
        min_gap = float(row.get("minGapMm") if row.get("minGapMm") is not None else row.get("min_gap_mm"))
    except (TypeError, ValueError):
        min_gap = -1.0
    if min_gap < 1.0:
        block("min_gap_too_small", "İsimler arası minimum boşluk 1 mm altında.")

    return {
        "passed": not reasons,
        "source": source,
        "reasonCodes": reason_codes,
        "reasons": reasons,
        "canvasPathHash": canvas_hash,
        "exportPathHash": export_hash,
        "referencePathHash": reference_hash,
    }


def normalize_queue_item(row: dict[str, Any], batch_id: str = "") -> dict[str, Any]:
    created = str(row.get("created_at") or now_iso())
    updated = str(row.get("updated_at") or now_iso())
    source = normalize_source(row.get("source") or "bulk_production") or "bulk_production"
    duplicate_key = duplicate_key_for({**row, "source": source})
    item_id = str(row.get("item_id") or row.get("id") or f"namecut-{uuid.uuid4().hex}")
    status = normalize_status(row.get("status"))
    gate = row.get("productionQueueGate") if isinstance(row.get("productionQueueGate"), dict) else production_queue_gate(row)
    return {
        "id": str(row.get("id") or item_id),
        "item_id": item_id,
        "source": source,
        "source_label": str(row.get("source_label") or source_label_for(source)),
        "bulk_row_id": str(row.get("bulk_row_id") or ""),
        "order_no": str(row.get("order_no") or ""),
        "customer_name": str(row.get("customer_name") or ""),
        "laser_name": str(row.get("laser_name") or row.get("name_text") or ""),
        "name_text": str(row.get("name_text") or row.get("laser_name") or ""),
        "preview_text": str(row.get("preview_text") or row.get("laser_name") or row.get("name_text") or ""),
        "quantity": str(row.get("quantity") or "1"),
        "label_model": str(row.get("label_model") or ""),
        "laser_model": str(row.get("laser_model") or ""),
        "note": str(row.get("note") or ""),
        "status": status,
        "safety_flags": list(row.get("safety_flags") or []),
        "warnings": list(row.get("warnings") or []),
        "errors": list(row.get("errors") or []),
        "production_queue_gate": gate,
        "production_queue_gate_passed": bool(gate.get("passed")),
        "production_queue_block_reasons": list(gate.get("reasons") or []),
        "path_source": _production_path_source(row),
        "ready_for_cut": bool(_truthy(row.get("readyForCut") if "readyForCut" in row else row.get("ready_for_cut"))),
        "final_cut_path_data": str(row.get("finalCutPathData") or row.get("final_cut_path_data") or row.get("pathData") or ""),
        "canvas_path_hash": str(row.get("canvasPathHash") or row.get("canvas_path_hash") or gate.get("canvasPathHash") or ""),
        "export_path_hash": str(row.get("exportPathHash") or row.get("export_path_hash") or gate.get("exportPathHash") or ""),
        "reference_path_hash": str(row.get("referencePathHash") or row.get("reference_path_hash") or gate.get("referencePathHash") or ""),
        "created_at": created,
        "updated_at": updated,
        "transfer_batch_id": str(row.get("transfer_batch_id") or batch_id or ""),
        "duplicate_key": duplicate_key,
        "width_mm": str(row.get("width_mm") or ""),
        "height_mm": str(row.get("height_mm") or ""),
        "style": str(row.get("style") or ""),
        "composition": str(row.get("composition") or row.get("composition_mode") or "İsimleri Bitiştir"),
        "composition_mode": str(row.get("composition_mode") or row.get("composition") or "İsimleri Bitiştir"),
        "thickening_mode": str(row.get("thickening_mode") or "Özel offset"),
        "offset_mm": row.get("offset_mm") if row.get("offset_mm") is not None else "",
        "support_line": bool(row.get("support_line") or False),
        "back_plate": bool(row.get("back_plate") or False),
        "is_deleted": bool(row.get("is_deleted") or False),
        "is_edited": bool(row.get("is_edited") or False),
    }


def list_name_cut_queue_items(project_root: Path, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = [normalize_queue_item(row) for row in _load_json_list(queue_path(project_root))]
    filters = filters or {}
    source = str(filters.get("source") or "").strip()
    status = str(filters.get("status") or "").strip()
    if source:
        rows = [row for row in rows if row.get("source") == source]
    if status:
        rows = [row for row in rows if row.get("status") == status]
    return rows


def save_name_cut_queue(project_root: Path, rows: list[dict[str, Any]]) -> None:
    _save_json_list(queue_path(project_root), rows)


def list_name_cut_transfer_history(project_root: Path) -> list[dict[str, Any]]:
    return _load_json_list(history_path(project_root))


def save_transfer_history(project_root: Path, rows: list[dict[str, Any]]) -> None:
    _save_json_list(history_path(project_root), rows)


def list_name_cut_export_history(project_root: Path) -> list[dict[str, Any]]:
    return _load_json_list(export_history_path(project_root))


def save_name_cut_export_history(project_root: Path, rows: list[dict[str, Any]]) -> None:
    _save_json_list(export_history_path(project_root), rows)


def check_name_cut_queue_duplicate(project_root: Path, duplicate_key: str) -> dict[str, Any]:
    key = str(duplicate_key or "").strip()
    existing = next((row for row in list_name_cut_queue_items(project_root) if row.get("duplicate_key") == key and not row.get("is_deleted")), None)
    return {
        "status": "DUPLICATE" if existing else "OK",
        "duplicate": bool(existing),
        "item": existing or {},
        "message": "Bu kayıt daha önce İsim Kesim hazırlık kuyruğuna gönderilmiş." if existing else "Duplicate bulunmadı.",
    }


def save_name_cut_queue_items(project_root: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
    if isinstance(payload, list):
        items = payload
        summary = {}
    else:
        items = payload.get("items") or []
        summary = payload.get("summary") or {}
    if not isinstance(items, list):
        return {"status": "ERROR", "message": "İsim Kesim queue payload geçersiz.", "items": []}
    rows = list_name_cut_queue_items(project_root)
    existing_keys = {row.get("duplicate_key") for row in rows if not row.get("is_deleted")}
    batch_id = str(summary.get("transfer_batch_id") or f"NCQ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}")
    added: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    gate_blocked: list[dict[str, Any]] = []
    skipped_blocked = 0
    for item in items:
        gate = production_queue_gate(item)
        if not gate["passed"]:
            blocked_item = normalize_queue_item({**item, "status": "blocked", "productionQueueGate": gate}, batch_id)
            blocked_item["errors"] = list(dict.fromkeys([*(blocked_item.get("errors") or []), *gate["reasons"]]))
            gate_blocked.append(blocked_item)
            continue
        normalized = normalize_queue_item(item, batch_id)
        normalized["transfer_batch_id"] = normalized.get("transfer_batch_id") or batch_id
        normalized["updated_at"] = now_iso()
        if normalized["status"] == "blocked":
            skipped_blocked += 1
            continue
        if normalized["duplicate_key"] in existing_keys:
            duplicates.append(normalized)
            continue
        rows.append(normalized)
        existing_keys.add(normalized["duplicate_key"])
        added.append(normalized)
    save_name_cut_queue(project_root, rows)

    history_entry = {
        "transfer_batch_id": batch_id,
        "created_at": now_iso(),
        "source": "bulk_production",
        "source_label": "Toplu Üretim",
        "total": int(summary.get("total") or len(items)),
        "added": len(added),
        "needs_review": sum(1 for row in added if row.get("status") == "needs_review"),
        "pending_preparation": sum(1 for row in added if row.get("status") == "pending_preparation"),
        "blocked": int(summary.get("blocked") or 0) + skipped_blocked,
        "duplicate": int(summary.get("duplicate") or 0) + len(duplicates),
    }
    history = list_name_cut_transfer_history(project_root)
    history.append(history_entry)
    save_transfer_history(project_root, history[-100:])
    result_status = "OK" if added else ("BLOCKED" if gate_blocked or skipped_blocked else "OK")
    return {
        "status": result_status,
        "message": f"{len(added)} kayıt kalıcı İsim Kesim hazırlık kuyruğuna alındı. RDWorks/lazer otomatik başlatılmadı.",
        "items": added,
        "blocked_items": gate_blocked,
        "blockedItems": gate_blocked,
        "productionQueueGate": {
            "allowedSources": sorted(PRODUCTION_ALLOWED_PATH_SOURCES),
            "blockedSources": sorted(PRODUCTION_REVIEW_PATH_SOURCES),
            "blockedCount": len(gate_blocked) + skipped_blocked,
        },
        "queue": list_name_cut_queue_items(project_root),
        "history": history[-100:],
        "transfer": history_entry,
        "added": len(added),
        "duplicate": len(duplicates),
        "blocked": skipped_blocked,
        "transfer_batch_id": batch_id,
    }


def get_name_cut_queue_item(project_root: Path, item_id: str) -> dict[str, Any]:
    item = next((row for row in list_name_cut_queue_items(project_root) if row.get("id") == item_id or row.get("item_id") == item_id), None)
    return {"status": "OK" if item else "MISSING", "item": item or {}, "message": "Kayıt bulundu." if item else "Kayıt bulunamadı."}


def update_name_cut_queue_item_status(project_root: Path, item_id: str, status: str) -> dict[str, Any]:
    normalized_status = normalize_status(status)
    rows = list_name_cut_queue_items(project_root)
    for row in rows:
        if row.get("id") == item_id or row.get("item_id") == item_id:
            row["status"] = normalized_status
            row["updated_at"] = now_iso()
            save_name_cut_queue(project_root, rows)
            return {"status": "OK", "message": "İsim Kesim hazırlık durumu güncellendi. Lazer/RDWorks başlatılmadı.", "item": row}
    return {"status": "MISSING", "message": "İsim Kesim hazırlık kaydı bulunamadı."}


def mark_name_cut_queue_item_prepared(project_root: Path, item_id: str) -> dict[str, Any]:
    return update_name_cut_queue_item_status(project_root, item_id, "prepared")


def mark_name_cut_queue_items_exported(project_root: Path, item_ids: list[str]) -> dict[str, Any]:
    wanted = {str(item_id or "").strip() for item_id in item_ids if str(item_id or "").strip()}
    if not wanted:
        return {"status": "OK", "updated": 0, "message": "Export iÃ§in kalÄ±cÄ± queue kaydÄ± seÃ§ilmedi."}
    rows = list_name_cut_queue_items(project_root)
    updated = 0
    for row in rows:
        if row.get("id") in wanted or row.get("item_id") in wanted:
            row["status"] = "exported"
            row["updated_at"] = now_iso()
            updated += 1
    save_name_cut_queue(project_root, rows)
    return {
        "status": "OK",
        "updated": updated,
        "message": f"{updated} Ä°sim Kesim kaydÄ± exported olarak iÅŸaretlendi. Lazer/RDWorks baÅŸlatÄ±lmadÄ±.",
    }


def record_name_cut_export_history(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "export_batch_id": str(payload.get("export_batch_id") or payload.get("batch_id") or f"NCE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"),
        "created_at": str(payload.get("created_at") or now_iso()),
        "operator": str(payload.get("operator") or ""),
        "source": "name_cut_studio",
        "source_label": "Ä°sim Kesim",
        "formats": list(payload.get("formats") or []),
        "item_count": int(payload.get("item_count") or 0),
        "quantity_total": int(payload.get("quantity_total") or 0),
        "plate_count": int(payload.get("plate_count") or 0),
        "cut_direction": str(payload.get("cut_direction") or ""),
        "mirror_horizontal": bool(payload.get("mirror_horizontal") or False),
        "mirror_vertical": bool(payload.get("mirror_vertical") or False),
        "quality_summary": dict(payload.get("quality_summary") or {}),
        "exported_files": dict(payload.get("exported_files") or {}),
        "manifest_path": str(payload.get("manifest_path") or ""),
        "status": str(payload.get("status") or "OK"),
        "message": str(payload.get("message") or "Ä°sim Kesim export paketi hazÄ±rlandÄ±. Lazer/RDWorks baÅŸlatÄ±lmadÄ±."),
    }
    history = list_name_cut_export_history(project_root)
    history.append(entry)
    save_name_cut_export_history(project_root, history[-100:])
    return {"status": "OK", "history": history[-100:], "entry": entry}
