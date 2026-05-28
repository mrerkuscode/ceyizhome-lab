"""Product Definitions API (v2.0, 2026-05-28).

When a Trendyol order arrives, the system needs to know without operator
intervention: how many names does this product need? what size group? does it
have a label, which model, how many copies? can the count be adjusted in
production?

This module is the persistent answer to those questions. It owns
`data/product_definitions.json`, validates writes against
`data/product_definitions_schema.json`, and exposes a small CRUD surface
plus an Excel-bulk-import path.

Design constraints (CLAUDE.md):
- Soft delete only — no physical row removal (status="archived")
- Validation rejects malformed payloads before write
- All mutations append to `data/product_definitions_audit_log.jsonl`
- Honest results: a "saved" message only appears after the file is on disk
- Operator-approved data (167 SVG refs, Trendyol approved rows) is not
  touched here; this module is read-add-edit only on its own JSON
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema import Draft202012Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    jsonschema = None
    Draft202012Validator = None
    JSONSCHEMA_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:  # pragma: no cover
    openpyxl = None
    OPENPYXL_AVAILABLE = False

# Reuse the DXF library's ASCII normalisation so the test_name lookup keys
# match exactly what the DXF lookup uses at order time.
try:
    from webui_backend.dxf_library_api import (
        to_ascii_name,
        find_library_entry,
        SIZE_GROUPS as DXF_SIZE_GROUPS,
    )
except Exception:  # pragma: no cover
    def to_ascii_name(value: str) -> str:
        return re.sub(r"[^a-z0-9_]+", "_", (value or "").lower()).strip("_")
    def find_library_entry(*_a, **_kw):
        return None
    DXF_SIZE_GROUPS = ["70x40", "80x40", "100x40"]


# --- Constants -------------------------------------------------------------

PRODUCT_DEFINITIONS_RELATIVE = "data/product_definitions.json"
PRODUCT_DEFINITIONS_SCHEMA_RELATIVE = "data/product_definitions_schema.json"
PRODUCT_DEFINITIONS_AUDIT_LOG_RELATIVE = "data/product_definitions_audit_log.jsonl"

EXCEL_REQUIRED_COLUMNS = [
    "SKU", "ProductName", "NameType", "NameCount", "LabelEnabled", "LabelModel", "LabelCount",
]

# Letter-based size group inference (used when name_config.size_group == "auto")
def size_group_for_letter_count(letter_count: int) -> str:
    if letter_count <= 0:
        return "70x40"
    if letter_count <= 5:
        return "70x40"
    if letter_count <= 9:
        return "80x40"
    return "100x40"


# --- Schema cache ----------------------------------------------------------

_schema_cache: dict[str, Any] | None = None


def _load_schema(project_root: Path) -> dict[str, Any]:
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache
    schema_path = project_root / PRODUCT_DEFINITIONS_SCHEMA_RELATIVE
    if not schema_path.exists():
        return {}
    try:
        _schema_cache = json.loads(schema_path.read_text(encoding="utf-8"))
        return _schema_cache
    except json.JSONDecodeError:
        return {}


# --- Persistence -----------------------------------------------------------

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_db(project_root: Path) -> dict[str, Any]:
    path = project_root / PRODUCT_DEFINITIONS_RELATIVE
    if not path.exists():
        return {"version": "2.0", "last_updated": "", "total_count": 0, "definitions": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"version": "2.0", "last_updated": "", "total_count": 0, "definitions": {}}
        data.setdefault("definitions", {})
        return data
    except json.JSONDecodeError:
        return {"version": "2.0", "last_updated": "", "total_count": 0, "definitions": {}}


def _save_db(project_root: Path, db: dict[str, Any]) -> None:
    path = project_root / PRODUCT_DEFINITIONS_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    db["last_updated"] = _now_iso()
    definitions = db.get("definitions") or {}
    db["total_count"] = sum(
        1 for entry in definitions.values()
        if isinstance(entry, dict) and entry.get("metadata", {}).get("status", "active") == "active"
    )
    path.write_text(
        json.dumps(db, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _audit(project_root: Path, action: str, sku: str, details: dict[str, Any] | None = None) -> None:
    """Append a JSONL audit line. Never raises."""
    path = project_root / PRODUCT_DEFINITIONS_AUDIT_LOG_RELATIVE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "at": _now_iso(),
            "action": action,
            "sku": sku,
            "details": details or {},
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        # Audit failure never blocks the operation
        pass


# --- Normalisation & validation -------------------------------------------

def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"true", "1", "evet", "yes", "y", "x", "var", "on"}:
        return True
    if text in {"false", "0", "hayir", "no", "n", "yok", "off", ""}:
        return False
    return default


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def normalize_definition(payload: dict[str, Any], *, prior: dict[str, Any] | None = None) -> dict[str, Any]:
    """Coerce arbitrary user input into the canonical schema shape.

    Does NOT validate — call validate_definition() after. Pure transform so
    that minor frontend laxity (string "1" for count, missing extras dict)
    doesn't fail validation.
    """
    payload = payload or {}
    prior = prior or {}
    sku = str(payload.get("sku") or prior.get("sku") or "").strip()
    name_cfg_in = payload.get("name_config") or {}
    label_cfg_in = payload.get("label_config") or {}
    extras_in = payload.get("extras") or {}
    metadata_in = payload.get("metadata") or {}
    prior_metadata = prior.get("metadata") or {}

    name_type = str(name_cfg_in.get("type") or "single").strip().lower()
    if name_type not in {"single", "couple", "none"}:
        name_type = "single"
    if name_type == "none":
        name_count = 0
    else:
        name_count = max(1, _coerce_int(name_cfg_in.get("count"), 1))

    size_group = str(name_cfg_in.get("size_group") or "auto").strip()
    if size_group not in {"auto", *DXF_SIZE_GROUPS}:
        size_group = "auto"

    compound_format = str(name_cfg_in.get("compound_format") or "joined").strip().lower()
    if compound_format not in {"joined", "side_by_side"}:
        compound_format = "joined"

    label_enabled = _coerce_bool(label_cfg_in.get("enabled"), False)
    label_model = str(label_cfg_in.get("model") or "").strip()
    label_default = _coerce_int(label_cfg_in.get("default_count"), 0)
    label_adjustable = _coerce_bool(label_cfg_in.get("adjustable_in_production"), False)
    label_min = _coerce_int(label_cfg_in.get("min_count"), 0)
    label_max = _coerce_int(label_cfg_in.get("max_count"), label_default)
    # Clamp min/max sanely
    if label_min < 0:
        label_min = 0
    if label_max < label_min:
        label_max = label_min
    if label_default < label_min:
        label_default = label_min
    if label_default > label_max and label_max > 0:
        label_default = label_max

    now = _now_iso()
    return {
        "sku": sku,
        "trendyol_sku": str(payload.get("trendyol_sku") or prior.get("trendyol_sku") or sku),
        "product_name": str(payload.get("product_name") or prior.get("product_name") or "").strip(),
        "name_config": {
            "type": name_type,
            "count": name_count,
            "size_group": size_group,
            "compound_format": compound_format,
            "test_name": str(name_cfg_in.get("test_name") or (prior.get("name_config") or {}).get("test_name") or "").strip(),
        },
        "label_config": {
            "enabled": label_enabled,
            "model": label_model,
            "default_count": label_default,
            "adjustable_in_production": label_adjustable,
            "min_count": label_min,
            "max_count": label_max,
        },
        "extras": {
            "special_requests_allowed": _coerce_bool(extras_in.get("special_requests_allowed"), True),
            "production_notes": str(extras_in.get("production_notes") or (prior.get("extras") or {}).get("production_notes") or "").strip(),
        },
        "metadata": {
            "created_date": prior_metadata.get("created_date") or metadata_in.get("created_date") or now,
            "modified_date": now,
            "usage_count": _coerce_int(prior_metadata.get("usage_count"), 0),
            "status": str(metadata_in.get("status") or prior_metadata.get("status") or "active"),
            "archived_date": prior_metadata.get("archived_date") or metadata_in.get("archived_date") or "",
            "source": str(metadata_in.get("source") or prior_metadata.get("source") or "manual"),
        },
    }


def validate_definition(project_root: Path, definition: dict[str, Any]) -> list[str]:
    """Return list of validation error strings. Empty list = valid."""
    schema = _load_schema(project_root)
    errors: list[str] = []
    # Field-level checks first (more readable than raw jsonschema errors)
    if not str(definition.get("sku") or "").strip():
        errors.append("SKU boş olamaz.")
    if not str(definition.get("product_name") or "").strip():
        errors.append("Ürün adı boş olamaz.")
    name_cfg = definition.get("name_config") or {}
    label_cfg = definition.get("label_config") or {}
    if name_cfg.get("type") in {"single", "couple"} and _coerce_int(name_cfg.get("count"), 0) < 1:
        errors.append("İsim tipi 'tek' veya 'çift' ise adet en az 1 olmalı.")
    if name_cfg.get("type") == "none" and _coerce_int(name_cfg.get("count"), 0) != 0:
        errors.append("İsim tipi 'yok' ise adet 0 olmalı.")
    if label_cfg.get("enabled") and not str(label_cfg.get("model") or "").strip():
        errors.append("Etiket aktif ise model seçilmeli.")
    if label_cfg.get("enabled"):
        min_c = _coerce_int(label_cfg.get("min_count"), 0)
        max_c = _coerce_int(label_cfg.get("max_count"), 0)
        default_c = _coerce_int(label_cfg.get("default_count"), 0)
        if max_c > 0 and min_c > max_c:
            errors.append("Etiket min_count, max_count'tan büyük olamaz.")
        if max_c > 0 and (default_c < min_c or default_c > max_c):
            errors.append(f"Etiket varsayılan adet ({default_c}) [min={min_c}, max={max_c}] aralığında olmalı.")
    # JSON schema check (catches anything missed above)
    if JSONSCHEMA_AVAILABLE and schema:
        validator = Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(definition), key=lambda e: e.path):
            path_str = "/".join(str(p) for p in err.path)
            errors.append(f"Şema hatası ({path_str or 'root'}): {err.message}")
    return errors


# --- Public read API -------------------------------------------------------

def list_definitions(project_root: Path, *, include_archived: bool = False) -> list[dict[str, Any]]:
    db = _load_db(project_root)
    defs = db.get("definitions", {})
    if not isinstance(defs, dict):
        return []
    rows = []
    for entry in defs.values():
        if not isinstance(entry, dict):
            continue
        status = (entry.get("metadata") or {}).get("status", "active")
        if status != "active" and not include_archived:
            continue
        rows.append(entry)
    rows.sort(key=lambda r: (r.get("sku") or "").lower())
    return rows


def get_definition(project_root: Path, sku: str) -> dict[str, Any] | None:
    db = _load_db(project_root)
    defs = db.get("definitions", {})
    if not isinstance(defs, dict):
        return None
    return defs.get(sku)


def search_definitions(project_root: Path, query: str) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return list_definitions(project_root)
    rows = list_definitions(project_root, include_archived=True)
    out = []
    for row in rows:
        name = (row.get("product_name") or "").lower()
        sku = (row.get("sku") or "").lower()
        if q in name or q in sku:
            out.append(row)
    return out


# --- Public write API ------------------------------------------------------

def save_definition(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Create or update a definition. SKU is the unique key."""
    db = _load_db(project_root)
    defs = db.setdefault("definitions", {})
    sku = str(payload.get("sku") or "").strip()
    if not sku:
        return {"status": "ERROR", "message": "SKU boş olamaz.", "errors": ["SKU boş olamaz."]}
    prior = defs.get(sku) if isinstance(defs.get(sku), dict) else None
    normalized = normalize_definition(payload, prior=prior)
    errors = validate_definition(project_root, normalized)
    if errors:
        return {
            "status": "VALIDATION_ERROR",
            "message": f"Doğrulama başarısız: {len(errors)} hata.",
            "errors": errors,
            "definition": normalized,
        }
    is_new = prior is None
    defs[sku] = normalized
    _save_db(project_root, db)
    _audit(project_root, "create" if is_new else "update", sku, {
        "product_name": normalized.get("product_name"),
        "name_type": normalized["name_config"]["type"],
        "label_enabled": normalized["label_config"]["enabled"],
    })
    return {
        "status": "OK",
        "message": f"Ürün tanımı {'oluşturuldu' if is_new else 'güncellendi'}: {sku}",
        "definition": normalized,
        "created": is_new,
    }


def archive_definition(project_root: Path, sku: str) -> dict[str, Any]:
    """Soft-delete: set status=archived. Never removes the row."""
    db = _load_db(project_root)
    defs = db.setdefault("definitions", {})
    if sku not in defs or not isinstance(defs[sku], dict):
        return {"status": "NOT_FOUND", "message": f"SKU bulunamadı: {sku}"}
    entry = defs[sku]
    metadata = entry.setdefault("metadata", {})
    if metadata.get("status") == "archived":
        return {"status": "ALREADY_ARCHIVED", "message": f"SKU zaten arşivde: {sku}"}
    metadata["status"] = "archived"
    metadata["archived_date"] = _now_iso()
    _save_db(project_root, db)
    _audit(project_root, "archive", sku, {})
    return {"status": "OK", "message": f"Ürün tanımı arşivlendi: {sku}", "definition": entry}


def restore_definition(project_root: Path, sku: str) -> dict[str, Any]:
    db = _load_db(project_root)
    defs = db.setdefault("definitions", {})
    if sku not in defs or not isinstance(defs[sku], dict):
        return {"status": "NOT_FOUND", "message": f"SKU bulunamadı: {sku}"}
    entry = defs[sku]
    metadata = entry.setdefault("metadata", {})
    if metadata.get("status") == "active":
        return {"status": "ALREADY_ACTIVE", "message": f"SKU zaten aktif: {sku}"}
    metadata["status"] = "active"
    metadata.pop("archived_date", None)
    _save_db(project_root, db)
    _audit(project_root, "restore", sku, {})
    return {"status": "OK", "message": f"Ürün tanımı aktif edildi: {sku}", "definition": entry}


def increment_usage(project_root: Path, sku: str, by: int = 1) -> dict[str, Any]:
    """Bump usage_count. Called when an order with this SKU is processed."""
    db = _load_db(project_root)
    defs = db.setdefault("definitions", {})
    if sku not in defs or not isinstance(defs[sku], dict):
        return {"status": "NOT_FOUND", "message": f"SKU bulunamadı: {sku}"}
    entry = defs[sku]
    metadata = entry.setdefault("metadata", {})
    metadata["usage_count"] = _coerce_int(metadata.get("usage_count"), 0) + max(1, by)
    _save_db(project_root, db)
    return {"status": "OK", "usage_count": metadata["usage_count"]}


# --- DXF library integration helpers --------------------------------------

def resolve_size_group(project_root: Path, definition: dict[str, Any]) -> dict[str, Any]:
    """Compute the effective size group for an item (manual override or auto).

    When 'auto', the test_name (if present) is checked against the DXF library
    so we can show the operator whether the design exists; otherwise we infer
    from letter count.
    """
    name_cfg = definition.get("name_config") or {}
    requested = str(name_cfg.get("size_group") or "auto")
    test_name = str(name_cfg.get("test_name") or "").strip()
    letter_source = test_name or definition.get("product_name") or ""
    letter_count = sum(1 for ch in letter_source if ch.isalpha())
    auto_group = size_group_for_letter_count(letter_count)
    effective = requested if requested in DXF_SIZE_GROUPS else auto_group

    dxf_status: dict[str, Any] = {"checked": False}
    if test_name:
        entry = find_library_entry(project_root, test_name)
        dxf_status = {
            "checked": True,
            "test_name": test_name,
            "ascii_name": to_ascii_name(test_name),
            "found": entry is not None,
            "size_group_in_library": entry.get("size_group") if entry else "",
            "bbox_mm": entry.get("bbox_mm") if entry else None,
        }
    return {
        "requested": requested,
        "effective": effective,
        "auto_group": auto_group,
        "letter_count": letter_count,
        "dxf_status": dxf_status,
    }


# --- Excel import ----------------------------------------------------------

def import_from_excel(project_root: Path, file_path: str, *, dry_run: bool = False) -> dict[str, Any]:
    """Read an XLSX file, upsert each row as a definition.

    Required columns (case-sensitive): SKU, ProductName, NameType, NameCount,
    LabelEnabled, LabelModel, LabelCount. Optional: SizeGroup, CompoundFormat,
    AdjustableInProduction, MinCount, MaxCount, ProductionNotes, TestName.

    Returns {"status": "OK"|"ERROR", "added":N, "updated":N, "errors":[...], "preview":[...]}.
    When dry_run=True, no writes happen but the validation pass runs and a
    preview (first 10 rows + their validation status) is returned.
    """
    if not OPENPYXL_AVAILABLE:
        return {"status": "ERROR", "message": "openpyxl modülü yüklü değil.", "added": 0, "updated": 0, "errors": []}
    src = Path(file_path)
    if not src.exists():
        return {"status": "ERROR", "message": f"Excel dosyası yok: {file_path}", "added": 0, "updated": 0, "errors": []}
    try:
        wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        return {"status": "ERROR", "message": f"Excel açılamadı: {exc}", "added": 0, "updated": 0, "errors": []}
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = list(next(rows_iter))
    except StopIteration:
        return {"status": "ERROR", "message": "Excel boş.", "added": 0, "updated": 0, "errors": []}
    header_norm = [str(h or "").strip() for h in header]
    missing_cols = [c for c in EXCEL_REQUIRED_COLUMNS if c not in header_norm]
    if missing_cols:
        return {
            "status": "ERROR",
            "message": f"Eksik kolonlar: {', '.join(missing_cols)}",
            "added": 0, "updated": 0, "errors": [],
            "header": header_norm,
        }
    col_idx = {col: header_norm.index(col) for col in header_norm if col}

    added = 0
    updated = 0
    errors: list[dict[str, Any]] = []
    preview: list[dict[str, Any]] = []
    db = _load_db(project_root)
    defs = db.setdefault("definitions", {})

    for row_no, row in enumerate(rows_iter, start=2):
        if not any(row):
            continue
        sku = str(row[col_idx["SKU"]] or "").strip()
        if not sku:
            errors.append({"row": row_no, "sku": "", "error": "SKU boş."})
            continue
        payload = {
            "sku": sku,
            "product_name": str(row[col_idx["ProductName"]] or "").strip(),
            "name_config": {
                "type": str(row[col_idx["NameType"]] or "single").strip().lower(),
                "count": _coerce_int(row[col_idx["NameCount"]], 1),
                "size_group": str(row[col_idx["SizeGroup"]] or "auto").strip() if "SizeGroup" in col_idx else "auto",
                "compound_format": str(row[col_idx["CompoundFormat"]] or "joined").strip().lower() if "CompoundFormat" in col_idx else "joined",
                "test_name": str(row[col_idx["TestName"]] or "").strip() if "TestName" in col_idx else "",
            },
            "label_config": {
                "enabled": _coerce_bool(row[col_idx["LabelEnabled"]], False),
                "model": str(row[col_idx["LabelModel"]] or "").strip(),
                "default_count": _coerce_int(row[col_idx["LabelCount"]], 0),
                "adjustable_in_production": _coerce_bool(row[col_idx["AdjustableInProduction"]], False) if "AdjustableInProduction" in col_idx else False,
                "min_count": _coerce_int(row[col_idx["MinCount"]], 0) if "MinCount" in col_idx else 0,
                "max_count": _coerce_int(row[col_idx["MaxCount"]], 0) if "MaxCount" in col_idx else 0,
            },
            "extras": {
                "production_notes": str(row[col_idx["ProductionNotes"]] or "").strip() if "ProductionNotes" in col_idx else "",
            },
            "metadata": {"source": "excel_import"},
        }
        prior = defs.get(sku) if isinstance(defs.get(sku), dict) else None
        normalized = normalize_definition(payload, prior=prior)
        row_errors = validate_definition(project_root, normalized)
        is_new = prior is None
        preview_entry = {
            "row": row_no, "sku": sku,
            "product_name": normalized.get("product_name"),
            "is_new": is_new,
            "errors": row_errors,
        }
        if len(preview) < 10:
            preview.append(preview_entry)
        if row_errors:
            errors.append({"row": row_no, "sku": sku, "error": "; ".join(row_errors)})
            continue
        if not dry_run:
            defs[sku] = normalized
            if is_new:
                added += 1
            else:
                updated += 1
            _audit(project_root, "excel_import", sku, {"row": row_no, "is_new": is_new})

    if not dry_run:
        _save_db(project_root, db)

    return {
        "status": "OK",
        "message": f"Excel içe aktarma: {added} yeni, {updated} güncel, {len(errors)} hata{' (DRY-RUN)' if dry_run else ''}",
        "added": added,
        "updated": updated,
        "errors": errors,
        "preview": preview,
        "dry_run": dry_run,
        "header": header_norm,
    }


# --- Summary + diagnostics -------------------------------------------------

def summary(project_root: Path) -> dict[str, Any]:
    db = _load_db(project_root)
    defs = db.get("definitions", {})
    active = 0
    archived = 0
    couple = 0
    single = 0
    none = 0
    with_label = 0
    for entry in defs.values() if isinstance(defs, dict) else []:
        if not isinstance(entry, dict):
            continue
        status = (entry.get("metadata") or {}).get("status", "active")
        if status == "active":
            active += 1
        elif status == "archived":
            archived += 1
        tp = (entry.get("name_config") or {}).get("type")
        if tp == "couple":
            couple += 1
        elif tp == "single":
            single += 1
        elif tp == "none":
            none += 1
        if (entry.get("label_config") or {}).get("enabled"):
            with_label += 1
    return {
        "total": active + archived,
        "active": active,
        "archived": archived,
        "by_name_type": {"single": single, "couple": couple, "none": none},
        "with_label": with_label,
        "jsonschema_available": JSONSCHEMA_AVAILABLE,
        "openpyxl_available": OPENPYXL_AVAILABLE,
    }


# --- API wrappers (bridge consumers) --------------------------------------

def api_list(project_root: Path, *, include_archived: bool = False) -> dict[str, Any]:
    return {
        "status": "OK",
        "summary": summary(project_root),
        "definitions": list_definitions(project_root, include_archived=include_archived),
    }


def api_get(project_root: Path, sku: str) -> dict[str, Any]:
    entry = get_definition(project_root, sku)
    if not entry:
        return {"status": "NOT_FOUND", "message": f"SKU bulunamadı: {sku}"}
    return {"status": "OK", "definition": entry, "size_group_resolution": resolve_size_group(project_root, entry)}


def api_search(project_root: Path, query: str) -> dict[str, Any]:
    rows = search_definitions(project_root, query)
    return {"status": "OK", "query": query or "", "count": len(rows), "definitions": rows}


def api_save(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return save_definition(project_root, payload)


def api_archive(project_root: Path, sku: str) -> dict[str, Any]:
    return archive_definition(project_root, sku)


def api_restore(project_root: Path, sku: str) -> dict[str, Any]:
    return restore_definition(project_root, sku)


def api_import_excel(project_root: Path, file_path: str, *, dry_run: bool = False) -> dict[str, Any]:
    return import_from_excel(project_root, file_path, dry_run=dry_run)


def api_resolve_size_group(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Compute size_group + DXF status for a draft definition (used in UI live preview)."""
    normalized = normalize_definition(payload, prior=None)
    return {"status": "OK", "resolution": resolve_size_group(project_root, normalized)}


def api_increment_usage(project_root: Path, sku: str) -> dict[str, Any]:
    return increment_usage(project_root, sku)
