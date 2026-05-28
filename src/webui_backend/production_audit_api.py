from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from . import name_cut_queue_api, print_queue_api, production_safety


SOURCE_LABELS = {
    "label_studio": "Etiket Studio",
    "etiket_studio": "Etiket Studio",
    "manual_label": "Manuel Etiket",
    "bulk_production": "Toplu Üretim",
    "trendyol": "Trendyol",
    "name_cut": "İsim Kesim",
    "laser": "İsim Kesim",
    "print_queue": "Yazdırma Sırası",
    "production_history": "Etiket Çıktıları",
    "legacy": "Eski kayıt",
    "unknown": "Bilinmiyor",
    "integration_guard": "Entegrasyon Guvenligi",
}

EVENT_LABELS = {
    "bulk_import_created": "Toplu import oluşturuldu",
    "bulk_validation_completed": "Toplu doğrulama tamamlandı",
    "bulk_sent_to_print_queue": "Toplu Üretim yazdırma sırasına aktarıldı",
    "bulk_sent_to_namecut_queue": "Toplu Üretim İsim Kesim kuyruğuna aktarıldı",
    "namecut_queue_created": "İsim Kesim hazırlık kaydı oluşturuldu",
    "namecut_status_updated": "İsim Kesim durumu güncellendi",
    "namecut_export_created": "İsim Kesim export paketi oluşturuldu",
    "label_studio_session_created": "Etiket Studio oturumu oluşturuldu",
    "label_output_created": "Etiket çıktısı oluşturuldu",
    "print_queue_created": "Yazdırma sırası kaydı oluşturuldu",
    "print_queue_status_updated": "Yazdırma sırası durumu güncellendi",
    "print_confirm_opened": "Yazdırma onayı açıldı",
    "manual_print_prepared": "Manuel print hazırlığı tamamlandı",
    "printed_marked": "Yazdırıldı işaretlendi",
    "print_cancelled": "Yazdırma iptal edildi",
    "print_failed": "Yazdırma hazırlığı başarısız",
    "duplicate_detected": "Duplicate kayıt algılandı",
    "blocked_detected": "Üretime engel kayıt algılandı",
    "output_missing": "Çıktı dosyası eksik",
    "manual_review_required": "Operatör kontrolü gerekli",
}


SOURCE_LABELS["production_audit"] = "Uretim Gecmisi"
SOURCE_LABELS["backup"] = "Veri Bakımı"
EVENT_LABELS["audit_export_created"] = "Audit disa aktarimi olusturuldu"
EVENT_LABELS["audit_export_failed"] = "Audit disa aktarimi olusturulamadi"
EVENT_LABELS["backup_created"] = "Yedek oluşturuldu"
EVENT_LABELS["backup_failed"] = "Yedek oluşturulamadı"
EVENT_LABELS["backup_validated"] = "Yedek doğrulandı"
EVENT_LABELS["restore_previewed"] = "Geri yükleme önizlendi"
EVENT_LABELS["restore_completed"] = "Geri yükleme tamamlandı"
EVENT_LABELS["restore_failed"] = "Geri yükleme başarısız"
EVENT_LABELS["trendyol_sync_started"] = "Trendyol read-only senkron baslatildi"
EVENT_LABELS["trendyol_sync_completed"] = "Trendyol read-only senkron tamamlandi"
EVENT_LABELS["trendyol_sync_failed"] = "Trendyol read-only senkron basarisiz"
EVENT_LABELS["trendyol_readonly_mode_confirmed"] = "Trendyol read-only modu dogrulandi"
EVENT_LABELS["integration_action_blocked"] = "Canli entegrasyon aksiyonu engellendi"
EVENT_LABELS["integration_dry_run_started"] = "Entegrasyon dry-run baslatildi"
EVENT_LABELS["integration_dry_run_completed"] = "Entegrasyon dry-run tamamlandi"
EVENT_LABELS["integration_permission_required"] = "Entegrasyon icin yetki gerekli"
EVENT_LABELS["integration_not_configured"] = "Entegrasyon aksiyonu bagli degil"

EXPORT_COLUMNS = [
    "created_at",
    "event_type",
    "event_label",
    "source_label",
    "origin_source_label",
    "status",
    "severity",
    "customer_name",
    "order_no",
    "batch_id",
    "transfer_batch_id",
    "export_batch_id",
    "queue_item_id",
    "title",
    "message",
    "file_path",
    "output_path",
]


def audit_path(project_root: Path) -> Path:
    path = project_root / "data" / "production_audit_log.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def _save_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean(value: Any) -> str:
    text = str(value or "")
    try:
        repaired = text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return repaired or text


def _normalize_source(value: Any) -> str:
    raw = _clean(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "etiket_studio": "label_studio",
        "studio": "label_studio",
        "manuel_etiket": "manual_label",
        "manuel": "manual_label",
        "manual": "manual_label",
        "toplu_uretim": "bulk_production",
        "bulk": "bulk_production",
        "isim_kesim": "name_cut",
        "namecut": "name_cut",
        "lazer": "laser",
    }
    return aliases.get(raw, raw if raw in SOURCE_LABELS else "")


def _source_label(source: Any, fallback: Any = "") -> str:
    key = _normalize_source(source)
    return SOURCE_LABELS.get(key) or _clean(fallback) or SOURCE_LABELS["unknown"]


def _parse_datetime(value: Any) -> datetime:
    text = _clean(value).strip()
    for fmt, length in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(text[:length], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.now()


def _severity_for(event_type: str, status: Any = "", flags: Any = None) -> str:
    status_text = _clean(status).lower()
    flag_text = json.dumps(flags or [], ensure_ascii=False).lower()
    if event_type in {"blocked_detected"} or "blocked" in status_text or "üretime engel" in status_text:
        return "blocked"
    if event_type in {"output_missing"} or "missing_output" in flag_text:
        return "error"
    if event_type in {"duplicate_detected", "manual_review_required"} or "review" in status_text or "needs_review" in status_text:
        return "warning"
    if event_type.endswith("_created") or event_type.endswith("_completed") or event_type.endswith("_updated"):
        return "success"
    return "info"


def _event_id(event: dict[str, Any]) -> str:
    explicit = _clean(event.get("id")).strip()
    if explicit:
        return explicit
    audit_key = _clean(event.get("audit_key")).strip()
    if audit_key:
        return f"audit-{uuid.uuid5(uuid.NAMESPACE_URL, audit_key)}"
    stable_parts = [
        event.get("event_type"),
        event.get("source"),
        event.get("source_item_id"),
        event.get("queue_item_id"),
        event.get("transfer_batch_id"),
        event.get("export_batch_id"),
        event.get("batch_id"),
        event.get("status"),
        event.get("output_path") or event.get("file_path"),
        event.get("message"),
    ]
    seed = "|".join(_clean(part) for part in stable_parts if _clean(part))
    return f"audit-{uuid.uuid5(uuid.NAMESPACE_URL, seed or _now_text())}"


def normalize_audit_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = _clean(event.get("event_type") or "manual_review_required")
    source = _normalize_source(event.get("source")) or "unknown"
    origin_source = _normalize_source(event.get("origin_source")) or ""
    normalized = {
        "id": "",
        "event_type": event_type,
        "event_label": _clean(event.get("event_label")) or EVENT_LABELS.get(event_type, event_type.replace("_", " ").title()),
        "source": source,
        "source_label": _clean(event.get("source_label")) or _source_label(source),
        "origin_source": origin_source,
        "origin_source_label": _clean(event.get("origin_source_label")) or (_source_label(origin_source) if origin_source else ""),
        "source_item_id": _clean(event.get("source_item_id")),
        "batch_id": _clean(event.get("batch_id")),
        "transfer_batch_id": _clean(event.get("transfer_batch_id")),
        "export_batch_id": _clean(event.get("export_batch_id")),
        "queue_item_id": _clean(event.get("queue_item_id")),
        "customer_name": _clean(event.get("customer_name")),
        "order_no": _clean(event.get("order_no")),
        "title": _clean(event.get("title")),
        "status": _clean(event.get("status")),
        "severity": _clean(event.get("severity")) or _severity_for(event_type, event.get("status"), event.get("safety_flags")),
        "message": _clean(event.get("message")),
        "file_path": _clean(event.get("file_path")),
        "output_path": _clean(event.get("output_path")),
        "created_at": _clean(event.get("created_at")) or _now_text(),
        "operator": _clean(event.get("operator")),
        "metadata": event.get("metadata") if isinstance(event.get("metadata"), dict) else {},
    }
    normalized["id"] = _event_id({**event, **normalized})
    return normalized


def append_production_audit_event(project_root: Path, event: dict[str, Any]) -> dict[str, Any]:
    path = audit_path(project_root)
    rows = _load_rows(path)
    normalized = normalize_audit_event(event)
    by_id = {row.get("id"): row for row in rows}
    if normalized["id"] in by_id:
        by_id[normalized["id"]].update({k: v for k, v in normalized.items() if v not in ("", {}, [])})
        status = "EXISTS"
    else:
        rows.append(normalized)
        status = "OK"
    rows = sorted({row.get("id"): row for row in rows if row.get("id")}.values(), key=lambda row: _parse_datetime(row.get("created_at")), reverse=True)
    _save_rows(path, rows)
    return {"status": status, "event": normalized, "count": len(rows)}


def create_audit_event_from_queue_item(item: dict[str, Any], event_type: str = "print_queue_created", message: str = "") -> dict[str, Any]:
    return normalize_audit_event({
        "event_type": event_type,
        "source": item.get("source") or "print_queue",
        "source_label": item.get("source_label"),
        "origin_source": item.get("origin_source"),
        "origin_source_label": item.get("origin_source_label"),
        "source_item_id": item.get("source_item_id") or item.get("bulk_row_id"),
        "queue_item_id": item.get("id") or item.get("queue_item_id"),
        "batch_id": item.get("batch_id"),
        "customer_name": item.get("customer_name"),
        "order_no": item.get("order_no"),
        "title": item.get("title") or item.get("job_name") or item.get("label_text"),
        "status": item.get("status_key") or item.get("status"),
        "message": message or item.get("message") or EVENT_LABELS.get(event_type, event_type),
        "file_path": item.get("relative_path") or item.get("output_path") or "",
        "output_path": item.get("output_path") or item.get("relative_path") or "",
        "created_at": item.get("updated_at") or item.get("created_at"),
        "metadata": {
            "quantity": item.get("quantity"),
            "model": item.get("label_model") or item.get("model_name"),
            "safety_flags": item.get("safety_flags", []),
            "duplicate_key": item.get("duplicate_key"),
        },
    })


def create_audit_event_from_namecut_item(item: dict[str, Any], event_type: str = "namecut_queue_created", message: str = "") -> dict[str, Any]:
    return normalize_audit_event({
        "event_type": event_type,
        "source": item.get("source") or "name_cut",
        "source_label": item.get("source_label"),
        "source_item_id": item.get("item_id") or item.get("bulk_row_id") or item.get("id"),
        "transfer_batch_id": item.get("transfer_batch_id"),
        "customer_name": item.get("customer_name"),
        "order_no": item.get("order_no"),
        "title": item.get("laser_name") or item.get("name_text") or item.get("title"),
        "status": item.get("status"),
        "message": message or EVENT_LABELS.get(event_type, event_type),
        "created_at": item.get("updated_at") or item.get("created_at"),
        "metadata": {
            "bulk_row_id": item.get("bulk_row_id"),
            "quantity": item.get("quantity"),
            "label_model": item.get("label_model"),
            "laser_model": item.get("laser_model"),
            "safety_flags": item.get("safety_flags", []),
            "duplicate_key": item.get("duplicate_key"),
        },
    })


def create_audit_event_from_bulk_batch(batch: dict[str, Any], event_type: str = "bulk_validation_completed", message: str = "") -> dict[str, Any]:
    return normalize_audit_event({
        "event_type": event_type,
        "source": "bulk_production",
        "source_label": "Toplu Uretim",
        "batch_id": batch.get("batch_id") or batch.get("transfer_batch_id") or batch.get("id"),
        "transfer_batch_id": batch.get("transfer_batch_id"),
        "title": batch.get("title") or "Toplu Uretim batch",
        "status": batch.get("status") or "completed",
        "severity": batch.get("severity") or ("warning" if int(batch.get("blocked") or 0) or int(batch.get("duplicate") or 0) else "success"),
        "message": message or batch.get("message") or EVENT_LABELS.get(event_type, event_type),
        "file_path": batch.get("file_path") or batch.get("path") or batch.get("selected_excel") or "",
        "created_at": batch.get("created_at") or batch.get("updated_at"),
        "metadata": batch,
    })


def create_audit_event_from_label_output(output: dict[str, Any], event_type: str = "label_output_created", message: str = "") -> dict[str, Any]:
    return normalize_audit_event({
        "event_type": event_type,
        "source": output.get("source") or "label_studio",
        "source_label": output.get("source_label") or "Etiket Studio",
        "origin_source": output.get("origin_source"),
        "origin_source_label": output.get("origin_source_label"),
        "source_item_id": output.get("source_item_id") or output.get("studio_session_id"),
        "batch_id": output.get("batch_id"),
        "customer_name": output.get("customer_name"),
        "order_no": output.get("order_no"),
        "title": output.get("label_text") or output.get("title") or output.get("model_name"),
        "status": output.get("status") or output.get("output_status") or "created",
        "message": message or output.get("message") or EVENT_LABELS.get(event_type, event_type),
        "file_path": output.get("batch_pdf_path") or output.get("pdf_path") or output.get("png_path") or output.get("output_path") or "",
        "output_path": output.get("batch_pdf_path") or output.get("pdf_path") or output.get("output_path") or "",
        "created_at": output.get("created_at") or output.get("updated_at"),
        "metadata": output,
    })


def _export_dir(project_root: Path) -> Path:
    path = project_root / "output" / datetime.now().strftime("%Y-%m-%d") / "production_audit_exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _filter_summary(filters: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "query",
        "source",
        "event_type",
        "status",
        "severity",
        "from",
        "to",
        "only_errors",
        "only_duplicate",
        "only_blocked",
        "only_review",
    ]
    return {key: filters.get(key) for key in keys if filters.get(key) not in (None, "", "all", False)}


def export_production_audit_events(project_root: Path, filters: dict[str, Any] | None = None, export_format: str = "json") -> dict[str, Any]:
    filters = filters or {}
    fmt = _clean(export_format or filters.get("format") or "json").strip().lower()
    if fmt not in {"json", "csv"}:
        return {"status": "ERROR", "message": "Sadece CSV veya JSON audit export desteklenir.", "path": "", "count": 0}
    events = list_production_audit_events(project_root, filters)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = _export_dir(project_root) / f"audit_export_{timestamp}.{fmt}"
    try:
        if fmt == "json":
            payload = {
                "exported_at": _now_text(),
                "filter_summary": _filter_summary(filters),
                "total_count": len(events),
                "events": events,
            }
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            with target.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=EXPORT_COLUMNS)
                writer.writeheader()
                for event in events:
                    writer.writerow({column: _clean(event.get(column)) for column in EXPORT_COLUMNS})
    except OSError as exc:
        failure = append_production_audit_event(project_root, {
            "event_type": "audit_export_failed",
            "source": "production_audit",
            "source_label": SOURCE_LABELS["production_audit"],
            "status": "failed",
            "severity": "error",
            "message": f"Audit {fmt.upper()} export yazilamadi: {exc}",
            "metadata": {"filters": _filter_summary(filters), "format": fmt, "error": str(exc)},
        })
        return {"status": "ERROR", "message": str(failure["event"].get("message") or exc), "path": "", "count": 0, "event": failure.get("event")}

    created = append_production_audit_event(project_root, {
        "event_type": "audit_export_created",
        "source": "production_audit",
        "source_label": SOURCE_LABELS["production_audit"],
        "status": "created",
        "severity": "success",
        "message": f"{len(events)} audit kaydi {fmt.upper()} dosyasina aktarildi.",
        "file_path": str(target.relative_to(project_root)),
        "output_path": str(target.relative_to(project_root)),
        "metadata": {"filters": _filter_summary(filters), "format": fmt, "count": len(events)},
    })
    rows = list_production_audit_events(project_root)
    return {
        "status": "OK",
        "message": f"{len(events)} audit kaydi {fmt.upper()} olarak disa aktarildi.",
        "format": fmt.upper(),
        "path": str(target.relative_to(project_root)),
        "count": len(events),
        "created_at": _now_text(),
        "event": created.get("event"),
        "events": rows,
        "summary": list_production_audit_summary(project_root, rows),
    }


def _queue_event_from_row(row: dict[str, Any]) -> dict[str, Any]:
    source = _normalize_source(row.get("source")) or "legacy"
    output_path = row.get("output_path") or row.get("relative_path") or row.get("path") or ""
    flags = row.get("safety_flags") if isinstance(row.get("safety_flags"), list) else []
    event_type = "print_queue_created"
    if "missing_output_file" in flags or "missing_output_path" in flags:
        event_type = "output_missing"
    elif row.get("status_key") == "blocked":
        event_type = "blocked_detected"
    return normalize_audit_event({
        "id": f"audit-print-row-{row.get('id') or row.get('duplicate_key')}",
        "event_type": event_type,
        "source": source,
        "source_label": row.get("source_label"),
        "origin_source": row.get("origin_source"),
        "origin_source_label": row.get("origin_source_label"),
        "source_item_id": row.get("source_item_id") or row.get("bulk_row_id"),
        "queue_item_id": row.get("id"),
        "batch_id": row.get("batch_id"),
        "customer_name": row.get("customer_name"),
        "order_no": row.get("order_no"),
        "title": row.get("title") or row.get("job_name") or row.get("label_text"),
        "status": row.get("status_key") or row.get("status"),
        "severity": _severity_for(event_type, row.get("status_key") or row.get("status"), flags),
        "message": row.get("status_message") or row.get("message") or f"{_source_label(source)} queue kaydı izleniyor.",
        "file_path": output_path,
        "output_path": output_path,
        "created_at": row.get("created_at") or row.get("updated_at"),
        "metadata": {
            "quantity": row.get("quantity"),
            "model": row.get("label_model") or row.get("model_name"),
            "safety_flags": flags,
            "duplicate_key": row.get("duplicate_key"),
            "output_format": row.get("output_format") or row.get("file_type"),
        },
    })


def _queue_history_event(row: dict[str, Any], history: dict[str, Any], index: int) -> dict[str, Any]:
    action = _clean(history.get("event") or "print_queue_status_updated")
    event_type = {
        "queue_created": "print_queue_created",
        "print_confirm_opened": "print_confirm_opened",
        "print_cancelled": "print_cancelled",
        "duplicate_seen": "duplicate_detected",
    }.get(action, "print_queue_status_updated")
    return normalize_audit_event({
        "id": f"audit-print-history-{row.get('id')}-{index}-{action}-{history.get('created_at')}",
        "event_type": event_type,
        "source": row.get("source") or "legacy",
        "source_label": row.get("source_label"),
        "origin_source": row.get("origin_source"),
        "origin_source_label": row.get("origin_source_label"),
        "source_item_id": row.get("source_item_id") or row.get("bulk_row_id"),
        "queue_item_id": row.get("id"),
        "batch_id": row.get("batch_id"),
        "customer_name": row.get("customer_name"),
        "order_no": row.get("order_no"),
        "title": row.get("title") or row.get("job_name") or row.get("label_text"),
        "status": history.get("status_key") or row.get("status_key") or row.get("status"),
        "message": history.get("message") or EVENT_LABELS.get(event_type, action),
        "file_path": row.get("relative_path") or row.get("output_path") or "",
        "output_path": row.get("relative_path") or row.get("output_path") or "",
        "created_at": history.get("created_at") or row.get("updated_at") or row.get("created_at"),
        "metadata": {"history_event": action, "queue_history": history},
    })


def _blocked_queue_event(row: dict[str, Any]) -> dict[str, Any]:
    return normalize_audit_event({
        "id": f"audit-blocked-row-{row.get('id') or row.get('duplicate_key')}",
        "event_type": "blocked_detected",
        "source": row.get("source") or "legacy",
        "source_label": row.get("source_label"),
        "origin_source": row.get("origin_source"),
        "origin_source_label": row.get("origin_source_label"),
        "source_item_id": row.get("source_item_id") or row.get("bulk_row_id"),
        "queue_item_id": row.get("id"),
        "batch_id": row.get("batch_id"),
        "customer_name": row.get("customer_name"),
        "order_no": row.get("order_no"),
        "title": row.get("title") or row.get("job_name") or row.get("label_text"),
        "status": row.get("status_key") or row.get("status") or "blocked",
        "severity": "blocked",
        "message": "Kayıt üretime engel durumunda. Operatör kontrolü olmadan yazdırmaya hazır sayılmaz.",
        "file_path": row.get("relative_path") or row.get("output_path") or "",
        "output_path": row.get("relative_path") or row.get("output_path") or "",
        "created_at": row.get("updated_at") or row.get("created_at"),
        "metadata": {
            "safety_flags": row.get("safety_flags", []),
            "duplicate_key": row.get("duplicate_key"),
        },
    })


def _namecut_queue_event(row: dict[str, Any]) -> dict[str, Any]:
    status = row.get("status") or "pending_preparation"
    event_type = "blocked_detected" if status == "blocked" else "namecut_queue_created"
    return normalize_audit_event({
        "id": f"audit-namecut-queue-{row.get('id') or row.get('item_id')}",
        "event_type": event_type,
        "source": row.get("source") or "name_cut",
        "source_label": row.get("source_label"),
        "source_item_id": row.get("item_id") or row.get("bulk_row_id"),
        "transfer_batch_id": row.get("transfer_batch_id"),
        "customer_name": row.get("customer_name"),
        "order_no": row.get("order_no"),
        "title": row.get("laser_name") or row.get("title"),
        "status": status,
        "message": "İsim Kesim hazırlık kuyruğu kaydı kalıcı olarak izleniyor.",
        "created_at": row.get("created_at") or row.get("updated_at"),
        "metadata": {
            "bulk_row_id": row.get("bulk_row_id"),
            "quantity": row.get("quantity"),
            "label_model": row.get("label_model"),
            "laser_model": row.get("laser_model"),
            "safety_flags": row.get("safety_flags", []),
        },
    })


def _transfer_event(row: dict[str, Any]) -> dict[str, Any]:
    return normalize_audit_event({
        "id": f"audit-namecut-transfer-{row.get('transfer_batch_id') or row.get('id')}",
        "event_type": "bulk_sent_to_namecut_queue",
        "source": "bulk_production",
        "source_label": "Toplu Üretim",
        "transfer_batch_id": row.get("transfer_batch_id") or row.get("id"),
        "title": "Toplu Üretim lazer aktarımı",
        "status": row.get("status") or "completed",
        "severity": "warning" if int(row.get("blocked") or 0) or int(row.get("duplicate") or 0) else "success",
        "message": f"{row.get('added') or row.get('prepared') or 0} kayıt İsim Kesim hazırlık kuyruğuna alındı.",
        "created_at": row.get("created_at") or row.get("updated_at"),
        "metadata": row,
    })


def _export_event(row: dict[str, Any]) -> dict[str, Any]:
    files = row.get("exported_files") if isinstance(row.get("exported_files"), list) else []
    first_file = files[0] if files else row.get("manifest_path") or row.get("output_path") or ""
    return normalize_audit_event({
        "id": f"audit-namecut-export-{row.get('export_batch_id') or row.get('id')}",
        "event_type": "namecut_export_created",
        "source": "name_cut",
        "source_label": "İsim Kesim",
        "export_batch_id": row.get("export_batch_id") or row.get("id"),
        "title": "İsim Kesim güvenli export paketi",
        "status": row.get("status") or "exported",
        "message": "Export dosyaları hazırlandı; RDWorks/lazer otomatik başlatılmadı.",
        "file_path": first_file,
        "output_path": first_file,
        "created_at": row.get("created_at") or row.get("updated_at"),
        "metadata": row,
    })


def _production_history_event(row: dict[str, Any]) -> dict[str, Any]:
    output_path = row.get("batch_pdf_path") or row.get("pdf_path") or row.get("png_path") or row.get("relative_path") or ""
    validation = row.get("output_validation") if isinstance(row.get("output_validation"), dict) else {}
    status = validation.get("status") or row.get("status") or "created"
    event_type = "manual_review_required" if str(status).upper() not in {"OK", "PASSED", "CREATED"} and status else "label_output_created"
    return normalize_audit_event({
        "id": f"audit-label-output-{row.get('id') or output_path or row.get('created_at')}",
        "event_type": event_type,
        "source": row.get("source") or "label_studio",
        "source_label": row.get("source_label") or "Etiket Studio",
        "origin_source": row.get("origin_source"),
        "origin_source_label": row.get("origin_source_label"),
        "source_item_id": row.get("source_item_id") or row.get("studio_session_id"),
        "customer_name": row.get("customer_name"),
        "order_no": row.get("order_no"),
        "title": row.get("label_text") or row.get("title") or row.get("model_name"),
        "status": status,
        "message": row.get("message") or "Etiket Studio çıktısı üretim geçmişine kaydedildi.",
        "file_path": output_path,
        "output_path": output_path,
        "created_at": row.get("created_at") or row.get("updated_at"),
        "metadata": row,
    })


def rebuild_production_audit_from_existing_sources(project_root: Path) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for row in print_queue_api.list_print_queue(project_root):
        events.append(_queue_event_from_row(row))
        if row.get("status_key") == "blocked":
            events.append(_blocked_queue_event(row))
        for index, history in enumerate(row.get("queue_history") if isinstance(row.get("queue_history"), list) else []):
            if isinstance(history, dict):
                events.append(_queue_history_event(row, history, index))
    for row in name_cut_queue_api.list_name_cut_queue_items(project_root):
        events.append(_namecut_queue_event(row))
    for row in name_cut_queue_api.list_name_cut_transfer_history(project_root):
        events.append(_transfer_event(row))
    for row in name_cut_queue_api.list_name_cut_export_history(project_root):
        events.append(_export_event(row))
    for row in production_safety.list_production_history(project_root):
        events.append(_production_history_event(row))

    current_rows = _load_rows(audit_path(project_root))
    by_id = {row.get("id"): row for row in current_rows if row.get("id")}
    before_count = len(by_id)
    for event in events:
        by_id[event["id"]] = {**by_id.get(event["id"], {}), **event}
    rows = sorted(by_id.values(), key=lambda row: _parse_datetime(row.get("created_at")), reverse=True)
    _save_rows(audit_path(project_root), rows)
    return {
        "status": "OK",
        "count": len(rows),
        "added": max(0, len(rows) - before_count),
        "events": rows,
        "summary": list_production_audit_summary(project_root, rows),
        "message": "Üretim geçmişi mevcut kalıcı kayıtlardan yeniden tarandı. Yazıcı, lazer ve RDWorks başlatılmadı.",
    }


def _matches_query(row: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        _clean(row.get(key))
        for key in (
            "customer_name",
            "order_no",
            "batch_id",
            "transfer_batch_id",
            "export_batch_id",
            "queue_item_id",
            "file_path",
            "output_path",
            "source_item_id",
            "message",
            "title",
        )
    )
    haystack += " " + json.dumps(row.get("metadata", {}), ensure_ascii=False)
    return query.lower() in haystack.lower()


def list_production_audit_events(project_root: Path, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = _load_rows(audit_path(project_root))
    filters = filters or {}
    query = _clean(filters.get("query")).strip()
    source = _clean(filters.get("source")).strip()
    event_type = _clean(filters.get("event_type")).strip()
    status = _clean(filters.get("status")).strip().lower()
    severity = _clean(filters.get("severity")).strip().lower()
    batch = _clean(filters.get("batch")).strip()
    order_no = _clean(filters.get("order_no")).strip().lower()
    customer = _clean(filters.get("customer_name")).strip().lower()
    file_path = _clean(filters.get("file_path")).strip().lower()
    from_text = _clean(filters.get("from")).strip()
    to_text = _clean(filters.get("to")).strip()
    from_dt = _parse_datetime(from_text) if from_text else None
    to_dt = _parse_datetime(to_text) + timedelta(days=1) if to_text else None
    result: list[dict[str, Any]] = []
    for row in rows:
        created = _parse_datetime(row.get("created_at"))
        if from_dt and created < from_dt:
            continue
        if to_dt and created >= to_dt:
            continue
        if source and source != "all" and row.get("source") != source:
            continue
        if event_type and event_type != "all" and row.get("event_type") != event_type:
            continue
        if status and status != "all" and status not in _clean(row.get("status")).lower():
            continue
        if severity and severity != "all" and row.get("severity") != severity:
            continue
        if batch and batch.lower() not in " ".join(_clean(row.get(k)).lower() for k in ("batch_id", "transfer_batch_id", "export_batch_id")):
            continue
        if order_no and order_no not in _clean(row.get("order_no")).lower():
            continue
        if customer and customer not in _clean(row.get("customer_name")).lower():
            continue
        if file_path and file_path not in " ".join([_clean(row.get("file_path")).lower(), _clean(row.get("output_path")).lower()]):
            continue
        if filters.get("only_errors") and row.get("severity") not in {"error", "blocked"}:
            continue
        if filters.get("only_duplicate") and row.get("event_type") != "duplicate_detected":
            continue
        if filters.get("only_blocked") and row.get("severity") != "blocked" and row.get("event_type") != "blocked_detected":
            continue
        if filters.get("only_review") and row.get("event_type") != "manual_review_required" and row.get("severity") != "warning":
            continue
        if not _matches_query(row, query):
            continue
        result.append(row)
    return sorted(result, key=lambda row: _parse_datetime(row.get("created_at")), reverse=True)


def get_production_audit_event(project_root: Path, event_id: str) -> dict[str, Any]:
    for row in _load_rows(audit_path(project_root)):
        if row.get("id") == event_id:
            return row
    return {}


def list_production_audit_summary(project_root: Path, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else _load_rows(audit_path(project_root))
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "today": sum(1 for row in rows if _clean(row.get("created_at")).startswith(today)),
        "print_queue": sum(1 for row in rows if row.get("event_type") in {"print_queue_created", "bulk_sent_to_print_queue"}),
        "namecut": sum(1 for row in rows if row.get("event_type") in {"bulk_sent_to_namecut_queue", "namecut_queue_created"}),
        "exports": sum(1 for row in rows if row.get("event_type") == "namecut_export_created"),
        "review": sum(1 for row in rows if row.get("severity") == "warning" or row.get("event_type") == "manual_review_required"),
        "blocked": sum(1 for row in rows if row.get("severity") == "blocked" or row.get("event_type") == "blocked_detected"),
        "duplicate": sum(1 for row in rows if row.get("event_type") == "duplicate_detected"),
        "missing_output": sum(1 for row in rows if row.get("event_type") == "output_missing"),
        "total": len(rows),
    }
