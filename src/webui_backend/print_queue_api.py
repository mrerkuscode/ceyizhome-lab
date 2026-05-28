from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from .file_api import to_web_file_url


DISPLAY_FIELDS = {
    "title",
    "job_name",
    "job_type",
    "file_type",
    "status",
    "status_key",
    "model_name",
    "label_model",
    "label_text",
    "size_text",
    "delivery_status",
    "source",
    "source_label",
    "origin_source",
    "origin_source_label",
    "source_item_id",
    "studio_session_id",
    "bulk_row_id",
    "order_no",
    "customer_name",
    "date_text",
    "note_text",
    "output_format",
    "output_path",
    "preview_path",
    "batch_id",
    "duplicate_key",
}

SOURCE_LABELS = {
    "label_studio": "Etiket Studio",
    "etiket_studio": "Etiket Studio",
    "manual_label": "Manuel Etiket",
    "trendyol": "Trendyol",
    "bulk_production": "Toplu Üretim",
    "name_cut": "İsim Kesim",
    "laser": "İsim Kesim",
}

STATUS_LABELS = {
    "waiting_output": "Çıktı Bekliyor",
    "output_ready": "Çıktı Hazır",
    "ready_to_print": "Yazdırmaya Hazır",
    "needs_review": "Kontrol Gerekli",
    "blocked": "Üretime Engel",
    "printed": "Yazdırıldı",
    "cancelled": "İptal Edildi",
    "failed": "Hatalı",
}


def clean_display_text(value: object) -> str:
    text = str(value or "")
    try:
        repaired = text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return repaired if repaired else text


def normalize_source(value: object) -> str:
    source = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return source if source in SOURCE_LABELS else ""


def source_label_for(source: object, fallback: object = "") -> str:
    normalized = normalize_source(source)
    return SOURCE_LABELS.get(normalized) or clean_display_text(fallback)


def status_label_for(status_key: object, fallback: object = "") -> str:
    key = str(status_key or "").strip().lower()
    return STATUS_LABELS.get(key) or clean_display_text(fallback) or STATUS_LABELS["waiting_output"]


def normalize_queue_row(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    for key in DISPLAY_FIELDS:
        if key in normalized:
            normalized[key] = clean_display_text(normalized[key])
    return normalized


def queue_path(project_root: Path) -> Path:
    path = project_root / "data" / "print_queue.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def list_print_queue(project_root: Path) -> list[dict[str, str]]:
    path = queue_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [harden_queue_row(project_root, normalize_queue_row(row), persist=False) for row in data if isinstance(row, dict)]


def save_print_queue(project_root: Path, rows: list[dict[str, str]]) -> None:
    queue_path(project_root).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _resolve_project_path(project_root: Path, path_text: object) -> Path:
    raw = str(path_text or "")
    path = Path(raw)
    return path if path.is_absolute() else project_root / raw


def _output_format(path_text: object, fallback: object = "") -> str:
    suffix = Path(str(path_text or "")).suffix.lower().lstrip(".")
    if suffix:
        return suffix.upper()
    fallback_text = str(fallback or "").upper()
    for token in ("PDF", "PNG", "SVG", "DXF", "PLT"):
        if token in fallback_text:
            return token
    return ""


def duplicate_key_for(item: dict[str, object], relative_path: str) -> str:
    explicit = str(item.get("duplicate_key") or "").strip()
    if explicit:
        return explicit
    source = normalize_source(item.get("source") or "") or "legacy"
    source_item = str(item.get("source_item_id") or item.get("bulk_row_id") or "").strip()
    if source_item:
        return f"{source}:{source_item}"
    if relative_path:
        return f"path:{relative_path}"
    title = clean_display_text(item.get("title") or item.get("job_name") or item.get("label_text") or "queue-item")
    return f"{source}:{title}:{item.get('quantity') or 1}"


def _history_event(action: str, status_key: str, message: str = "") -> dict[str, str]:
    return {
        "event": action,
        "status_key": status_key,
        "message": clean_display_text(message),
        "created_at": _now_text(),
    }


def append_queue_history(row: dict[str, object], action: str, status_key: str, message: str = "") -> None:
    history = row.get("queue_history")
    if not isinstance(history, list):
        history = []
    history.append(_history_event(action, status_key, message))
    row["queue_history"] = history[-30:]


def _legacy_status_key(row: dict[str, object]) -> str:
    explicit = str(row.get("status_key") or "").strip().lower()
    if explicit in STATUS_LABELS:
        return explicit
    status = clean_display_text(row.get("status") or "").lower()
    validation = str(row.get("validation_status") or "").lower()
    if "teslim" in status:
        return "printed"
    if "yazdırmaya hazır" in status or "yazdirmaya hazir" in status:
        return "ready_to_print"
    if "yazdır" in status or "yazdir" in status or "printed" in status:
        return "printed"
    if "iptal" in status or "cancel" in status:
        return "cancelled"
    if "hata" in status or "failed" in status:
        return "failed"
    if "engel" in status or "blocked" in status:
        return "blocked"
    if "kontrol" in status or "review" in status or validation in {"warning", "warn", "check"}:
        return "needs_review"
    if validation in {"missing", "error", "failed"}:
        return "blocked"
    if "hazır" in status or "hazir" in status or "ready" in status:
        return "ready_to_print"
    return "waiting_output"


def _safety_flags(project_root: Path, row: dict[str, object]) -> list[str]:
    flags: list[str] = []
    output_path = str(row.get("output_path") or row.get("relative_path") or "")
    quantity_raw = str(row.get("quantity") or "")
    try:
        quantity = int(float(quantity_raw.replace(",", "."))) if quantity_raw else 1
    except ValueError:
        quantity = 0
    if not output_path:
        flags.append("missing_output_path")
    elif not _resolve_project_path(project_root, output_path).exists():
        flags.append("missing_output_file")
    fmt = _output_format(output_path, row.get("file_type") or row.get("output_format") or "")
    if fmt and fmt not in {"PDF", "PNG", "SVG", "DXF", "PLT"}:
        flags.append("unsupported_format")
    if quantity <= 0:
        flags.append("invalid_quantity")
    if not str(row.get("model_name") or row.get("label_model") or "").strip():
        flags.append("missing_model")
    if str(row.get("status_key") or "").lower() in {"blocked", "failed", "cancelled"}:
        flags.append("blocked_status")
    return flags


def harden_queue_row(project_root: Path, row: dict[str, object], persist: bool = True) -> dict[str, str]:
    legacy_keys = set(row.keys())
    if legacy_keys <= {"id", "relative_path", "status", "demo_seed"}:
        return normalize_queue_row(row)  # type: ignore[arg-type]
    hardened: dict[str, object] = dict(row)
    original_status = clean_display_text(hardened.get("status") or "")
    relative_path = str(hardened.get("relative_path") or hardened.get("output_path") or "")
    source = normalize_source(hardened.get("source") or "")
    if source:
        hardened["source"] = source
        hardened["source_label"] = clean_display_text(hardened.get("source_label") or source_label_for(source))
    hardened["output_path"] = str(hardened.get("output_path") or relative_path)
    hardened["relative_path"] = relative_path
    if hardened.get("preview_uri") and not hardened.get("preview_path"):
        hardened["preview_path"] = str(hardened.get("preview_uri") or "")
    hardened["output_format"] = str(hardened.get("output_format") or _output_format(hardened.get("output_path"), hardened.get("file_type")) or "")
    hardened["title"] = clean_display_text(hardened.get("title") or hardened.get("job_name") or hardened.get("model_name") or "Etiket işi")
    if not hardened.get("label_model") and hardened.get("model_name"):
        hardened["label_model"] = str(hardened.get("model_name") or "")
    if not hardened.get("duplicate_key"):
        hardened["duplicate_key"] = duplicate_key_for(hardened, relative_path)
    status_key = _legacy_status_key(hardened)
    hardened["status_key"] = status_key
    flags = _safety_flags(project_root, hardened)
    if flags and status_key not in {"printed", "cancelled", "failed"}:
        if "missing_output_path" in flags or "missing_output_file" in flags or "invalid_quantity" in flags or "missing_model" in flags:
            if not (original_status == "Beklemede" and status_key == "needs_review"):
                status_key = "blocked"
        elif status_key == "waiting_output":
            status_key = "needs_review"
    elif not flags and status_key == "waiting_output" and hardened.get("output_path"):
        status_key = "ready_to_print"
    hardened["status_key"] = status_key
    if original_status == "Beklemede" and status_key in {"ready_to_print", "needs_review"}:
        hardened["status"] = original_status
    elif "teslim" in original_status.lower() and status_key == "printed":
        hardened["status"] = original_status
    else:
        hardened["status"] = status_label_for(status_key, hardened.get("status"))
    hardened["safety_flags"] = flags
    hardened["updated_at"] = str(hardened.get("updated_at") or hardened.get("created_at") or _now_text())
    if persist and not isinstance(hardened.get("queue_history"), list):
        hardened["queue_history"] = [_history_event("queue_created", status_key, "Yazdırma sırası kaydı oluşturuldu.")]
    return normalize_queue_row(hardened)  # type: ignore[arg-type]


def add_to_print_queue(project_root: Path, item: dict[str, str]) -> dict[str, str]:
    rows = list_print_queue(project_root)
    relative_path = str(item.get("relative_path") or "")
    incoming_duplicate_key = duplicate_key_for(item, relative_path)
    existing = next(
        (
            row for row in rows
            if row.get("status_key") != "cancelled"
            and (
                (relative_path and row.get("relative_path") == relative_path)
                or (incoming_duplicate_key and row.get("duplicate_key") == incoming_duplicate_key)
            )
        ),
        None,
    )
    if existing:
        incoming_source = normalize_source(item.get("source") or "")
        if incoming_source and not existing.get("source"):
            existing["source"] = incoming_source
            existing["source_label"] = clean_display_text(item.get("source_label") or source_label_for(incoming_source))
            existing["updated_at"] = _now_text()
            append_queue_history(existing, "duplicate_seen", existing.get("status_key") or _legacy_status_key(existing), "Aynı iş tekrar kuyruğa eklenmeye çalışıldı.")
            save_print_queue(project_root, rows)
        return {
            "status": "EXISTS",
            "message": "Bu etiket işi zaten yazdırma sırasında.",
            "id": existing.get("id", ""),
            "relative_path": existing.get("relative_path", ""),
            "source": existing.get("source", ""),
            "source_label": existing.get("source_label", ""),
        }

    metadata = metadata_from_output_path(relative_path)
    source = normalize_source(item.get("source") or "")
    source_label = clean_display_text(item.get("source_label") or source_label_for(source, ""))
    row = {
        "id": uuid.uuid4().hex,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "job_name": clean_display_text(item.get("job_name") or metadata.get("model_name") or item.get("file_name") or "Etiket işi"),
        "job_type": clean_display_text(item.get("job_type") or "Toplu"),
        "quantity": str(item.get("quantity") or metadata.get("quantity") or "1"),
        "file_type": clean_display_text(item.get("file_type") or "Rulo Batch PDF"),
        "relative_path": relative_path,
        "output_path": str(item.get("output_path") or relative_path),
        "output_format": str(item.get("output_format") or _output_format(relative_path, item.get("file_type"))),
        "preview_uri": str(item.get("preview_uri") or paired_preview_uri(project_root, relative_path) or ""),
        "preview_path": str(item.get("preview_path") or item.get("preview_uri") or paired_preview_uri(project_root, relative_path) or ""),
        "status": clean_display_text(item.get("status") or "Beklemede"),
        "duplicate_key": incoming_duplicate_key,
        "batch_id": str(item.get("batch_id") or item.get("transfer_batch_id") or ""),
    }
    if str(item.get("status_key") or "").strip().lower() in STATUS_LABELS:
        row["status_key"] = str(item.get("status_key") or "").strip().lower()
    if source:
        row["source"] = source
        row["source_label"] = source_label or source_label_for(source)
    optional_fields = [
        "origin_source",
        "origin_source_label",
        "source_item_id",
        "studio_session_id",
        "bulk_row_id",
        "order_no",
        "customer_name",
        "date_text",
        "note_text",
        "title",
        "label_model",
    ]
    for key in optional_fields:
        value = str(item.get(key) or "")
        if value:
            row[key] = clean_display_text(value)
    for key in ["model_name", "label_text", "size_text"]:
        value = str(item.get(key) or metadata.get(key) or "")
        if value:
            row[key] = clean_display_text(value)
    row = harden_queue_row(project_root, row, persist=True)
    rows.append(row)
    save_print_queue(project_root, rows)
    try:
        from . import production_audit_api

        production_audit_api.append_production_audit_event(
            project_root,
            production_audit_api.create_audit_event_from_queue_item(
                row,
                "print_queue_created",
                "Yazdırma sırası kaydı oluşturuldu.",
            ),
        )
    except Exception:
        pass
    return {
        "status": "ADDED",
        "message": "Etiket işi yazdırma sırasına eklendi.",
        "id": row["id"],
        "relative_path": row.get("relative_path", ""),
        "source": row.get("source", ""),
        "source_label": row.get("source_label", ""),
    }


def add_label_outputs_to_queue(project_root: Path, outputs: list[dict[str, str]]) -> dict[str, str]:
    added = 0
    skipped = 0
    latest_path = ""
    for output in outputs:
        name = str(output.get("file_name") or "")
        kind = str(output.get("type") or "")
        if not name.lower().endswith(".pdf"):
            continue
        if "RAPOR" in kind:
            continue
        if not (name.startswith("roll_batch") or name.startswith("manual_batch") or "RULO" in kind or "MANUEL" in kind):
            continue
        metadata = metadata_from_output_path(str(output.get("relative_path") or ""))
        is_manual = "MANUEL" in kind
        result = add_to_print_queue(
            project_root,
            {
                "job_name": metadata.get("model_name") or ("Manuel Etiket" if is_manual else "Toplu Etiket"),
                "job_type": "Manuel" if is_manual else "Toplu",
                "source": "manual_label" if is_manual else "bulk_production",
                "source_label": "Manuel Etiket" if is_manual else "Toplu Üretim",
                "quantity": metadata.get("quantity") or "1",
                "file_type": kind or "PDF",
                "relative_path": str(output.get("relative_path") or ""),
                "preview_uri": str(output.get("preview_uri") or ""),
                "model_name": metadata.get("model_name", ""),
                "label_text": metadata.get("label_text", ""),
                "size_text": metadata.get("size_text", ""),
            },
        )
        if result["status"] == "ADDED":
            added += 1
            latest_path = str(output.get("relative_path") or latest_path)
        else:
            skipped += 1
    return {
        "status": "OK",
        "message": f"{added} iş sıraya eklendi, {skipped} iş zaten vardı.",
        "added": str(added),
        "queue_path": latest_path,
    }


def add_pdf_output_to_queue(project_root: Path, relative_path: str) -> dict[str, str]:
    path = (project_root / relative_path).resolve()
    try:
        path.relative_to((project_root / "output").resolve())
    except ValueError:
        return {"status": "ERROR", "message": "Sadece etiket çıktı PDF dosyaları yazdırma sırasına eklenebilir."}
    if not path.exists() or not path.is_file() or path.suffix.lower() != ".pdf":
        return {"status": "ERROR", "message": "Yazdırma sırasına eklenecek PDF dosyası bulunamadı."}
    name = path.name.lower()
    if "report" in name:
        return {"status": "ERROR", "message": "Rapor dosyaları yazdırma sırasına eklenmez."}
    is_manual = path.parent.name.lower() == "manual" or name.startswith("manual")
    is_batch = name.startswith("roll_batch") or name.startswith("manual_batch")
    metadata = metadata_from_output_path(relative_path)
    return add_to_print_queue(
        project_root,
        {
            "job_name": metadata.get("model_name") or ("Manuel Etiket" if is_manual else "Toplu Etiket"),
            "job_type": "Manuel" if is_manual else "Toplu",
            "source": "manual_label" if is_manual else "bulk_production",
            "source_label": "Manuel Etiket" if is_manual else "Toplu Üretim",
            "quantity": metadata.get("quantity") or "1",
            "file_type": "Rulo Batch PDF" if is_batch else "PDF",
            "relative_path": relative_path,
            "preview_uri": paired_preview_uri(project_root, relative_path),
            "model_name": metadata.get("model_name", ""),
            "label_text": metadata.get("label_text", ""),
            "size_text": metadata.get("size_text", ""),
        },
    )


def remove_from_print_queue(project_root: Path, item_id: str) -> dict[str, str]:
    rows = list_print_queue(project_root)
    for row in rows:
        if row.get("id") == item_id:
            row["status_key"] = "cancelled"
            row["status"] = STATUS_LABELS["cancelled"]
            row["updated_at"] = _now_text()
            append_queue_history(row, "cancelled", "cancelled", "İş yazdırma sırasından kaldırıldı.")
            break
    rows = [row for row in rows if row.get("id") != item_id]
    save_print_queue(project_root, rows)
    return {"status": "OK", "message": "İş yazdırma sırasından silindi."}


def mark_queue_item_printed(project_root: Path, item_id: str) -> dict[str, str]:
    rows = list_print_queue(project_root)
    for row in rows:
        if row.get("id") == item_id:
            row["status_key"] = "printed"
            row["status"] = STATUS_LABELS["printed"]
            row["printed_at"] = _now_text()
            row["updated_at"] = row["printed_at"]
            append_queue_history(row, "printed_marked", "printed", "Operatör işi yazdırıldı olarak işaretledi.")
            save_print_queue(project_root, rows)
            return {"status": "OK", "message": "İş yazdırıldı olarak işaretlendi."}
    return {"status": "MISSING", "message": "Yazdırma sırasında bu iş bulunamadı."}


def mark_queue_item_pending(project_root: Path, item_id: str) -> dict[str, str]:
    rows = list_print_queue(project_root)
    for row in rows:
        if row.get("id") == item_id:
            row["status_key"] = "ready_to_print" if not _safety_flags(project_root, row) else "needs_review"
            row["status"] = "Beklemede"
            row.pop("printed_at", None)
            row.pop("delivered_at", None)
            row["delivery_status"] = "Teslim bekliyor"
            row["updated_at"] = _now_text()
            append_queue_history(row, "requeued", row["status_key"], "İş yeniden kuyruğa alındı.")
            save_print_queue(project_root, rows)
            return {"status": "OK", "message": "İş yeniden beklemeye alındı."}
    return {"status": "MISSING", "message": "Yazdırma sırasında bu iş bulunamadı."}


def clear_print_queue(project_root: Path) -> dict[str, str]:
    save_print_queue(project_root, [])
    return {"status": "OK", "message": "Yazdırma sırası temizlendi."}


def mark_queue_item_delivered(project_root: Path, item_id: str) -> dict[str, str]:
    rows = list_print_queue(project_root)
    for row in rows:
        if row.get("id") == item_id:
            row["status_key"] = "printed"
            row["status"] = "Teslim edildi"
            row["delivery_status"] = "Teslim edildi"
            row["delivered_at"] = _now_text()
            row["updated_at"] = row["delivered_at"]
            append_queue_history(row, "delivered_marked", "printed", "Operatör işi teslim edildi olarak işaretledi.")
            save_print_queue(project_root, rows)
            return {"status": "OK", "message": "\u0130\u015f teslim edildi olarak i\u015faretlendi."}
    return {"status": "MISSING", "message": "Yazd\u0131rma s\u0131ras\u0131nda bu i\u015f bulunamad\u0131."}


def print_queue_item_safe(project_root: Path, item_id: str, direct_print_enabled: bool = False) -> dict[str, str]:
    item = next((row for row in list_print_queue(project_root) if row.get("id") == item_id), None)
    if not item:
        return {"status": "MISSING", "message": "Yazd\u0131rma s\u0131ras\u0131nda bu i\u015f bulunamad\u0131."}
    relative_path = item.get("relative_path", "") or item.get("output_path", "")
    flags = item.get("safety_flags") if isinstance(item.get("safety_flags"), list) else _safety_flags(project_root, item)
    if "missing_output_file" in flags:
        return {"status": "ERROR", "message": "PDF dosyası bulunamadı. Lütfen çıktıyı yeniden oluşturun.", "relative_path": relative_path}
    if item.get("status_key") in {"blocked", "failed", "cancelled", "waiting_output"}:
        return {
            "status": "ERROR",
            "message": f"{item.get('status') or 'Bu iş'} yazdırmaya hazır değil. Çıktı, model, adet ve güvenlik kontrollerini tamamlayın.",
            "relative_path": relative_path,
        }
    pdf_path = _resolve_project_path(project_root, relative_path)
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        return {"status": "ERROR", "message": "PDF dosyası bulunamadı. Lütfen çıktıyı yeniden oluşturun.", "relative_path": relative_path}
    if not direct_print_enabled:
        return {
            "status": "MANUAL_PRINT_REQUIRED",
            "message": "Doğrudan yazdırma bu sürümde kapalıdır. PDF dosyasını açıp manuel yazdırabilirsiniz.",
            "relative_path": relative_path,
        }
    return {
        "status": "CONFIRMATION_REQUIRED",
        "message": "Doğrudan yazdırma için yazıcı seçimi, önizleme ve kullanıcı onayı gerekir.",
        "relative_path": relative_path,
    }


def metadata_from_output_path(path_or_name: str) -> dict[str, str]:
    name = Path(str(path_or_name or "")).name
    stem = re.sub(r"\.(pdf|png)$", "", name, flags=re.IGNORECASE)
    stem = re.sub(r"_batch(?:_\d+)?$", "", stem, flags=re.IGNORECASE)
    parts = [part for part in stem.split("_") if part]
    metadata = {"model_name": "", "label_text": "", "size_text": "", "quantity": ""}
    if len(parts) < 2:
        return metadata
    offset = 1 if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", parts[0]) else 0
    size_index = next((index for index, part in enumerate(parts) if re.fullmatch(r"\d+(?:[.,]\d+)?x\d+(?:[.,]\d+)?", part, re.IGNORECASE)), -1)
    if size_index > offset:
        metadata["model_name"] = _pretty_slug("_".join(parts[offset:max(offset + 1, size_index - 1)]))
        metadata["label_text"] = _pretty_slug("_".join(parts[max(offset + 1, size_index - 1):size_index]))
        metadata["size_text"] = parts[size_index].replace("x", " x ").replace("X", " x ") + " mm"
        quantity_match = re.search(r"(\d+)\s*adet", parts[size_index + 1] if len(parts) > size_index + 1 else "", re.IGNORECASE)
        if quantity_match:
            metadata["quantity"] = quantity_match.group(1)
    else:
        metadata["model_name"] = _pretty_slug("_".join(parts[offset:offset + 4]))
        metadata["label_text"] = _pretty_slug("_".join(parts[offset + 4:]))
    return metadata


def paired_preview_uri(project_root: Path, relative_path: str) -> str:
    path = project_root / str(relative_path or "")
    if path.suffix.lower() == ".png":
        return to_web_file_url(path, project_root)
    if path.suffix.lower() != ".pdf":
        return ""
    candidates = [
        path.with_suffix(".png"),
        path.with_name(re.sub(r"_batch(_\d+)?\.pdf$", r"\1.png", path.name, flags=re.IGNORECASE)),
    ]
    for candidate in candidates:
        uri = to_web_file_url(candidate, project_root)
        if uri:
            return uri
    return ""


def _pretty_slug(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("-", " ").replace("_", " ")).strip()
