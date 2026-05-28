from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from intelligence.text_cleanup import repair_text


PRODUCTION_TYPES = {"label", "name_cut", "label_and_name_cut", "none", "review"}
MAPPING_COLUMNS = [
    "product_name",
    "barcode",
    "merchant_sku",
    "stock_code",
    "image_url",
    "production_type",
    "model_key",
    "model_path",
    "model_name",
    "quantity_source",
    "default_note_text",
    "default_date_text",
    "name_cut_style",
    "name_cut_width_mm",
    "active",
]


def mappings_path(project_root: Path) -> Path:
    path = project_root / "data" / "trendyol_product_mappings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def list_product_mappings(project_root: Path) -> list[dict[str, Any]]:
    path = mappings_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [_normalize_mapping(row) for row in data if isinstance(row, dict)]


def save_product_mappings(project_root: Path, rows: list[dict[str, Any]]) -> None:
    normalized = [_normalize_mapping(row) for row in rows]
    mappings_path(project_root).write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")


def export_product_mappings_to_excel(project_root: Path) -> dict[str, Any]:
    rows = list_product_mappings(project_root)
    export_rows = [{column: row.get(column, "") for column in MAPPING_COLUMNS} for row in rows]
    target_dir = project_root / "output" / datetime.now().strftime("%Y-%m-%d") / "trendyol"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"trendyol_urun_eslestirme_{datetime.now().strftime('%H%M%S_%f')}.xlsx"
    pd.DataFrame(export_rows, columns=MAPPING_COLUMNS).to_excel(target_path, index=False)
    return {
        "status": "OK",
        "message": f"{len(export_rows)} Trendyol urun eslestirmesi Excel dosyasina aktarildi.",
        "path": str(target_path),
        "relative_path": _relative(project_root, target_path),
        "row_count": len(export_rows),
    }


def import_product_mappings_from_file(project_root: Path, source_path: str | Path) -> dict[str, Any]:
    source = Path(source_path)
    if not source.exists():
        return {"status": "ERROR", "message": "Trendyol urun eslestirme dosyasi bulunamadi.", "imported": 0, "errors": []}
    rows, load_error = _load_mapping_rows(source)
    if load_error:
        return {"status": "ERROR", "message": load_error, "imported": 0, "errors": [load_error]}
    existing = list_product_mappings(project_root)
    by_identity = {_mapping_identity(row): row for row in existing if _mapping_identity(row)}
    imported = 0
    updated = 0
    skipped = 0
    errors: list[str] = []
    for index, raw in enumerate(rows, start=2):
        mapping = _normalize_mapping(raw)
        identity = _mapping_identity(mapping)
        if not identity:
            skipped += 1
            errors.append(f"Satir {index}: barcode, merchant_sku veya stock_code yok.")
            continue
        if identity in by_identity:
            created = by_identity[identity].get("created_at") or mapping.get("created_at") or _now()
            mapping["created_at"] = created
            mapping["updated_at"] = _now()
            by_identity[identity] = mapping
            updated += 1
        else:
            by_identity[identity] = mapping
            imported += 1
    save_product_mappings(project_root, list(by_identity.values()))
    return {
        "status": "OK",
        "message": f"{imported} yeni, {updated} guncel Trendyol urun eslestirmesi alindi. {skipped} satir atlandi.",
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:20],
        "mappings": list_product_mappings(project_root),
    }


def upsert_product_mapping(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    rows = list_product_mappings(project_root)
    mapping = _normalize_mapping(payload)
    key = _mapping_identity(mapping)
    if not key:
        return {"status": "ERROR", "message": "Barcode veya SKU olmadan Trendyol ürün eşleştirmesi kaydedilemez."}
    for index, row in enumerate(rows):
        if _mapping_identity(row) == key:
            mapping["created_at"] = row.get("created_at") or mapping["created_at"]
            mapping["updated_at"] = _now()
            rows[index] = mapping
            save_product_mappings(project_root, rows)
            return {"status": "OK", "message": "Trendyol ürün eşleştirmesi güncellendi.", "mapping": mapping}
    rows.insert(0, mapping)
    save_product_mappings(project_root, rows)
    return {"status": "OK", "message": "Trendyol ürün eşleştirmesi kaydedildi.", "mapping": mapping}


def find_mapping_for_line(project_root: Path, line: dict[str, Any]) -> dict[str, Any] | None:
    mappings = [row for row in list_product_mappings(project_root) if row.get("active")]
    barcode = _key(line.get("barcode"))
    merchant_sku = _key(line.get("merchant_sku") or line.get("merchantSku"))
    stock_code = _key(line.get("stock_code") or line.get("stockCode"))
    product_name = _key(line.get("product_name") or line.get("productName") or line.get("name"))
    for row in mappings:
        if barcode and barcode == _key(row.get("barcode")):
            return row
        if merchant_sku and merchant_sku in {_key(row.get("merchant_sku")), _key(row.get("stock_code"))}:
            return row
        if stock_code and stock_code in {_key(row.get("merchant_sku")), _key(row.get("stock_code"))}:
            return row
    for row in mappings:
        mapped_name = _key(row.get("product_name"))
        if mapped_name and product_name and mapped_name in product_name:
            return row
    return None


def _normalize_mapping(payload: dict[str, Any]) -> dict[str, Any]:
    production_type = str(payload.get("production_type") or "review").strip() or "review"
    if production_type not in PRODUCTION_TYPES:
        production_type = "review"
    created = str(payload.get("created_at") or _now())
    return {
        "product_name": repair_text(payload.get("product_name") or ""),
        "barcode": str(payload.get("barcode") or "").strip(),
        "merchant_sku": str(payload.get("merchant_sku") or payload.get("merchantSku") or "").strip(),
        "stock_code": str(payload.get("stock_code") or payload.get("stockCode") or "").strip(),
        "image_url": str(payload.get("image_url") or payload.get("imageUrl") or "").strip(),
        "production_type": production_type,
        "model_key": str(payload.get("model_key") or "").strip(),
        "model_path": str(payload.get("model_path") or "").strip(),
        "model_name": repair_text(payload.get("model_name") or ""),
        "quantity_source": str(payload.get("quantity_source") or "line_quantity").strip(),
        "default_note_text": repair_text(payload.get("default_note_text") or ""),
        "default_date_text": repair_text(payload.get("default_date_text") or ""),
        "name_cut_style": repair_text(payload.get("name_cut_style") or "Mochary Personal Use Only"),
        "name_cut_width_mm": _safe_float(payload.get("name_cut_width_mm"), 300),
        "active": _safe_bool(payload.get("active"), True),
        "created_at": created,
        "updated_at": str(payload.get("updated_at") or created),
    }


def _mapping_identity(row: dict[str, Any]) -> str:
    return _key(row.get("barcode")) or _key(row.get("merchant_sku")) or _key(row.get("stock_code"))


def _key(value: Any) -> str:
    return str(value or "").strip().lower()


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "evet", "e", "aktif", "active"}


def _load_mapping_rows(source: Path) -> tuple[list[dict[str, Any]], str]:
    suffix = source.suffix.lower()
    try:
        if suffix in {".xlsx", ".xls"}:
            frame = pd.read_excel(source, dtype=object, engine="openpyxl")
            return frame.fillna("").to_dict(orient="records"), ""
        if suffix == ".csv":
            frame = pd.read_csv(source, dtype=object).fillna("")
            return frame.to_dict(orient="records"), ""
        if suffix == ".json":
            data = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data = data.get("mappings") or data.get("rows") or []
            if not isinstance(data, list):
                return [], "JSON dosyasi liste veya mappings/rows listesi icermiyor."
            return [row for row in data if isinstance(row, dict)], ""
    except Exception as exc:  # noqa: BLE001
        return [], f"Trendyol mapping dosyasi okunamadi: {exc}"
    return [], "Desteklenmeyen dosya turu. Excel, CSV veya JSON kullanin."


def _relative(project_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
