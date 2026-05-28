from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
from typing import Any
import re
import unicodedata

import pandas as pd

from excel_reader import read_orders_excel
from models import BOTH, PRINT
from webui_backend.label_api import preview_manual


def _new_batch_id() -> str:
    """Return a collision-resistant local batch id for bulk gallery artifacts."""

    return datetime.now().strftime("%H%M%S_%f")


BULK_HEADER_ALIASES = {
    "etiket_no": "model_key",
    "etiket_numarasi": "model_key",
    "model_no": "model_key",
    "model_numarasi": "model_key",
    "model_kodu": "model_key",
    "model": "model_key",
    "tasarim_no": "model_key",
    "isim": "label_text",
    "ad_soyad": "label_text",
    "label_text": "label_text",
    "etiket_yazisi": "label_text",
    "musteri_adi": "label_text",
    "tarih": "date_text",
    "date": "date_text",
    "date_text": "date_text",
    "etkinlik_tarihi": "date_text",
    "not": "note_text",
    "note": "note_text",
    "note_text": "note_text",
    "aciklama": "note_text",
    "mesaj": "note_text",
    "adet": "quantity",
    "quantity": "quantity",
    "qty": "quantity",
    "miktar": "quantity",
}


def used_label_models(project_root: Path, excel_path: Path, label_models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not excel_path.exists():
        return []
    try:
        dataframe = read_orders_excel(excel_path)
    except Exception:
        return []
    model_index = {
        _key(model.get("model_no"), model.get("template_no"), model.get("label_variant")): model
        for model in label_models
    }
    grouped: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {"order_count": 0, "quantity_total": 0, "orders": []}
    )
    for index, row in dataframe.iterrows():
        process_type = str(row.get("process_type") or "").strip().upper()
        if process_type not in {PRINT, BOTH}:
            continue
        key = _key(row.get("model_no"), row.get("template_no"), row.get("label_variant"))
        quantity = _safe_int(row.get("quantity"), default=1)
        grouped[key]["order_count"] += 1
        grouped[key]["quantity_total"] += max(1, quantity)
        grouped[key]["orders"].append(
            {
                "row_number": str(index + 2),
                "order_no": str(row.get("order_no") or ""),
                "label_text": str(row.get("label_text") or ""),
                "date_text": str(row.get("date_text") or ""),
                "note_text": str(row.get("note_text") or ""),
            }
        )
    rows: list[dict[str, Any]] = []
    for (model_no, template_no, label_variant), usage in sorted(grouped.items()):
        model = model_index.get((model_no, template_no, label_variant))
        missing_model = model is None
        rows.append(
            {
                "model_no": model_no,
                "template_no": template_no,
                "label_variant": label_variant,
                "model_name": "" if missing_model else str(model.get("model_name") or model.get("title") or ""),
                "preview_image": "" if missing_model else str(model.get("preview_image") or ""),
                "size_text": "" if missing_model else str(model.get("size_text") or ""),
                "active": "false" if missing_model else str(model.get("active", "true")),
                "order_count": str(usage["order_count"]),
                "quantity_total": str(usage["quantity_total"]),
                "missing_model": missing_model,
                "missing_preview": bool(not missing_model and not model.get("preview_image")),
                "warning": _warning(missing_model, model),
                "orders": usage["orders"],
            }
        )
    return rows


def preview_samples(project_root: Path, excel_path: Path, label_models: list[dict[str, Any]], limit: int = 5) -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []
    for model in used_label_models(project_root, excel_path, label_models):
        for order in model.get("orders", []):
            samples.append(
                {
                    "model_no": str(model.get("model_no") or ""),
                    "template_no": str(model.get("template_no") or ""),
                    "label_variant": str(model.get("label_variant") or ""),
                    "model_name": str(model.get("model_name") or "Model bulunamadı"),
                    "preview_image": str(model.get("preview_image") or ""),
                    "row_number": str(order.get("row_number") or ""),
                    "order_no": str(order.get("order_no") or ""),
                    "label_text": str(order.get("label_text") or ""),
                    "date_text": str(order.get("date_text") or ""),
                    "note_text": str(order.get("note_text") or ""),
                }
            )
            if len(samples) >= limit:
                return samples
    return samples


def bulk_gallery_items(project_root: Path, excel_path: Path, label_models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Excel rows into UI-friendly bulk gallery items.

    This layer accepts normal-user column names such as etiket_no, isim, tarih,
    not and adet without changing the existing production renderer contract.
    """

    if not excel_path.exists():
        return []
    try:
        raw_dataframe = pd.read_excel(excel_path, dtype=object, engine="openpyxl")
    except Exception:
        return []
    mapped = _map_bulk_dataframe(raw_dataframe)
    model_index = _build_model_lookup(label_models)
    items: list[dict[str, Any]] = []
    for index, row in mapped.iterrows():
        row_number = index + 2
        model_key = _cell(row.get("model_key"))
        label_text = _cell(row.get("label_text"))
        date_text = _cell(row.get("date_text"))
        note_text = _cell(row.get("note_text"))
        quantity = max(1, _safe_int(row.get("quantity"), default=1))
        model = _match_gallery_model(model_key, model_index)
        errors: list[str] = []
        warnings: list[str] = []
        if not model:
            errors.append("Bu etiket numarası için model bulunamadı.")
        if not label_text:
            errors.append("İsim alanı boş.")
        if not date_text:
            warnings.append("Tarih alanı boş.")
        if quantity < 1:
            errors.append("Adet değeri geçersiz.")
        if model and not model.get("preview_image"):
            warnings.append("Model önizleme görseli eksik.")
        status = "ERROR" if errors else "WARNING" if warnings else "READY"
        item = {
            "item_id": f"row-{row_number}",
            "row_number": str(row_number),
            "model_key": model_key,
            "model_name": str(model.get("title") or model.get("model_name") or "") if model else "",
            "model_status": "FOUND" if model else "MISSING",
            "model_path": str(model.get("path") or "") if model else "",
            "model_no": str(model.get("model_no") or model_key or "") if model else model_key,
            "template_no": str(model.get("template_no") or "A") if model else "A",
            "label_variant": str(model.get("label_variant") or "GOLD") if model else "GOLD",
            "label_text": label_text,
            "date_text": date_text,
            "note_text": note_text,
            "quantity": str(quantity),
            "width_mm": str(model.get("label_width_mm") or model.get("width_mm") or "") if model else "",
            "height_mm": str(model.get("label_height_mm") or model.get("height_mm") or "") if model else "",
            "size_text": str(model.get("size_text") or "") if model else "",
            "fields": model.get("fields_summary", []) if model else [],
            "preview_png_path": str(model.get("preview_image") or "") if model else "",
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "is_deleted": False,
            "is_edited": False,
            "original_row_data": {str(key): _cell(value) for key, value in raw_dataframe.iloc[index].to_dict().items()},
        }
        items.append(item)
    return items


def bulk_gallery_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    live_items = [item for item in items if not item.get("is_deleted")]
    used_models = {str(item.get("model_name") or item.get("model_key") or "") for item in live_items if item.get("model_status") == "FOUND"}
    return {
        "total_rows": len(items),
        "ready_rows": sum(1 for item in live_items if item.get("status") == "READY"),
        "warning_rows": sum(1 for item in live_items if item.get("status") == "WARNING"),
        "error_rows": sum(1 for item in live_items if item.get("status") == "ERROR"),
        "deleted_rows": sum(1 for item in items if item.get("is_deleted")),
        "total_quantity": sum(_safe_int(item.get("quantity"), 1) for item in live_items if item.get("status") != "ERROR"),
        "used_model_count": len([model for model in used_models if model]),
    }


def write_gallery_items_excel(project_root: Path, source_excel: Path, items: list[dict[str, Any]]) -> dict[str, object]:
    ready_items = [
        item for item in items
        if _bulk_item_ready_for_queue(item)
    ]
    if not ready_items:
        return {"status": "ERROR", "message": "Üretime hazır toplu etiket satırı bulunamadı."}
    rows = []
    for index, item in enumerate(ready_items, start=1):
        rows.append(
            {
                "order_no": f"BULK-{item.get('row_number') or index}",
                "buyer_name": item.get("label_text") or "",
                "product_name": "Etiket",
                "model_no": item.get("model_no") or item.get("model_key") or "",
                "template_no": item.get("template_no") or "A",
                "process_type": PRINT,
                "personalization_type": "LABEL",
                "label_variant": item.get("label_variant") or "GOLD",
                "label_text": item.get("label_text") or "",
                "date_text": item.get("date_text") or "",
                "note_text": item.get("note_text") or "",
                "laser_text": "",
                "quantity": max(1, _safe_int(item.get("quantity"), 1)),
                "material_type": "",
                "material_thickness_mm": "",
                "extra_chocolate_qty": 0,
                "extra_madlen_qty": 0,
                "production_note": item.get("note_text") or "",
                "needs_review": "YES" if item.get("warnings") else "NO",
                "status": "READY",
            }
        )
    target_dir = project_root / "output" / datetime.now().strftime("%Y-%m-%d") / "bulk_gallery"
    target_dir.mkdir(parents=True, exist_ok=True)
    batch_id = _new_batch_id()
    target_path = target_dir / f"bulk_gallery_ready_{batch_id}.xlsx"
    pd.DataFrame(rows).to_excel(target_path, index=False)
    manifest_path = write_bulk_gallery_manifest(
        project_root,
        source_excel,
        items,
        generated_pdf="",
        generated_pngs=[],
        roll_batch_pdf="",
        queue_path="",
        batch_id=batch_id,
    )
    return {
        "status": "OK",
        "message": f"{len(rows)} hazır satır için toplu üretim Excel’i hazırlandı.",
        "row_count": len(rows),
        "path": str(target_path),
        "relative_path": _relative(target_path, project_root),
        "manifest_path": _relative(manifest_path, project_root),
        "batch_id": batch_id,
    }


def _bulk_item_ready_for_queue(item: dict[str, Any]) -> bool:
    if item.get("is_deleted"):
        return False
    if str(item.get("status") or "").upper() != "READY":
        return False
    if str(item.get("model_status") or "").upper() == "MISSING":
        return False
    if item.get("errors"):
        return False
    if not _cell(item.get("label_text")):
        return False
    if not _cell(item.get("model_no") or item.get("model_key") or item.get("model_name")):
        return False
    if _safe_int(item.get("quantity"), 0) < 1:
        return False
    return True


def write_bulk_gallery_manifest(
    project_root: Path,
    source_excel: Path,
    items: list[dict[str, Any]],
    generated_pdf: str = "",
    generated_pngs: list[str] | None = None,
    roll_batch_pdf: str = "",
    queue_path: str = "",
    batch_id: str | None = None,
) -> Path:
    target_dir = project_root / "output" / datetime.now().strftime("%Y-%m-%d") / "bulk_gallery"
    target_dir.mkdir(parents=True, exist_ok=True)
    final_batch_id = batch_id or _new_batch_id()
    path = target_dir / f"batch_manifest_{final_batch_id}.json"
    summary = bulk_gallery_summary(items)
    manifest = {
        "batch_id": final_batch_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "excel_file": _relative(source_excel, project_root) if source_excel.exists() else "",
        "total_rows": summary["total_rows"],
        "ready_rows": summary["ready_rows"],
        "warning_rows": summary["warning_rows"],
        "error_rows": summary["error_rows"],
        "deleted_rows": summary["deleted_rows"],
        "total_quantity": summary["total_quantity"],
        "used_models": sorted({str(item.get("model_name") or item.get("model_key") or "") for item in items if item.get("model_status") == "FOUND"}),
        "generated_pdf": generated_pdf,
        "generated_pngs": generated_pngs or [],
        "roll_batch_pdf": roll_batch_pdf,
        "queue_path": queue_path,
        "rows": [
            {
                "item_id": item.get("item_id"),
                "row_number": item.get("row_number"),
                "model_key": item.get("model_key"),
                "model_name": item.get("model_name"),
                "label_text": item.get("label_text"),
                "date_text": item.get("date_text"),
                "note_text": item.get("note_text"),
                "quantity": item.get("quantity"),
                "status": item.get("status"),
                "is_edited": item.get("is_edited"),
                "is_deleted": item.get("is_deleted"),
                "output_page": "",
                "errors": item.get("errors") or [],
                "warnings": item.get("warnings") or [],
            }
            for item in items
        ],
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def column_mapping(project_root: Path, excel_path: Path) -> dict[str, Any]:
    if not excel_path.exists():
        return {
            "status": "NO_EXCEL",
            "message": "Excel seçilmedi.",
            "columns": [],
            "missing_required": [],
        }
    try:
        raw_columns = [str(column) for column in pd.read_excel(excel_path, nrows=0).columns]
        normalized = read_orders_excel(excel_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "ERROR",
            "message": f"Excel kolonları okunamadı: {exc}",
            "columns": [],
            "missing_required": [],
        }
    normalized_columns = [
        _column_mapping_alias(str(raw_columns[index] if index < len(raw_columns) else ""), str(column))
        for index, column in enumerate(normalized.columns)
    ]
    required = ["order_no", "model_no", "template_no", "label_variant", "label_text", "date_text", "quantity"]
    optional = ["note_text", "process_type"]
    if len(normalized_columns) >= len(required) and any(column not in normalized_columns for column in required):
        positional = ["order_no", "model_no", "template_no", "label_variant", "label_text", "date_text", "quantity"]
        normalized_columns = [
            normalized_columns[index] if normalized_columns[index] in {*required, *optional} else positional[index]
            for index in range(len(positional))
        ] + normalized_columns[len(positional):]
    rows = []
    for index, raw in enumerate(raw_columns):
        mapped = normalized_columns[index] if index < len(normalized_columns) else ""
        role = "zorunlu" if mapped in required else "opsiyonel" if mapped in optional else "yardımcı"
        rows.append(
            {
                "source": raw,
                "mapped": mapped,
                "role": role,
                "status": "mapped" if mapped else "unmapped",
            }
        )
    missing = [column for column in required if column not in normalized_columns]
    return {
        "status": "OK" if not missing else "WARNING",
        "message": "Excel kolon eşleştirmesi hazır." if not missing else "Bazı zorunlu kolonlar eksik.",
        "columns": rows,
        "missing_required": missing,
    }


def _column_mapping_alias(raw: str, normalized: str) -> str:
    text = _normalize_header_token(raw or normalized)
    if "sipari" in text or "order" in text:
        return "order_no"
    if "model" in text:
        return "model_no"
    if "ablon" in text or "template" in text:
        return "template_no"
    if "varyant" in text or "variant" in text:
        return "label_variant"
    if text in {"sim", "isim"} or "label_text" in text or "ad_soyad" in text:
        return "label_text"
    if "tarih" in text or "date" in text:
        return "date_text"
    if text in {"not", "note", "note_text"}:
        return "note_text"
    if "adet" in text or "quantity" in text:
        return "quantity"
    aliases = {
        "siparis_no": "order_no",
        "sipari_no": "order_no",
        "order_no": "order_no",
        "model_no": "model_no",
        "sablon_no": "template_no",
        "ablon_no": "template_no",
        "template_no": "template_no",
        "varyant": "label_variant",
        "variant": "label_variant",
        "label_variant": "label_variant",
        "isim": "label_text",
        "sim": "label_text",
        "ad_soyad": "label_text",
        "label_text": "label_text",
        "tarih": "date_text",
        "date": "date_text",
        "date_text": "date_text",
        "not": "note_text",
        "note": "note_text",
        "note_text": "note_text",
        "adet": "quantity",
        "quantity": "quantity",
        "process_type": "process_type",
    }
    return aliases.get(text, normalized)


def _normalize_header_token(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .translate(str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"}))
        .replace("ı", "i")
        .replace("İ", "i")
        .replace("ş", "s")
        .replace("Ş", "s")
        .replace("ğ", "g")
        .replace("Ğ", "g")
        .replace("ü", "u")
        .replace("Ü", "u")
        .replace("ö", "o")
        .replace("Ö", "o")
        .replace("ç", "c")
        .replace("Ç", "c")
        .replace("?", "")
        .replace(" ", "_")
        .replace("-", "_")
    )


def _normalize_user_token(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.strip().lower()
    text = text.translate(str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"}))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i").replace("İ", "i")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def _cell(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    if text.endswith(".0") and text.replace(".0", "", 1).isdigit():
        return text[:-2]
    return text


def _map_bulk_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    mapped = pd.DataFrame()
    for column in dataframe.columns:
        canonical = BULK_HEADER_ALIASES.get(_normalize_user_token(column), "")
        if not canonical:
            continue
        if canonical not in mapped:
            mapped[canonical] = dataframe[column]
        else:
            mapped[canonical] = mapped[canonical].where(mapped[canonical].notna() & (mapped[canonical].astype(str).str.strip() != ""), dataframe[column])
    for column in ["model_key", "label_text", "date_text", "note_text", "quantity"]:
        if column not in mapped:
            mapped[column] = ""
    return mapped


def _build_model_lookup(label_models: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for model in label_models:
        values = [
            model.get("model_no"),
            model.get("template_no"),
            model.get("label_variant"),
            model.get("title"),
            model.get("model_name"),
            model.get("name"),
            model.get("display_name"),
            model.get("template_id"),
            model.get("path"),
        ]
        model_no = _cell(model.get("model_no"))
        template_no = _cell(model.get("template_no"))
        variant = _cell(model.get("label_variant"))
        values.extend(
            [
                f"{model_no}_{template_no}_{variant}",
                f"{model_no} {template_no} {variant}",
                f"{model_no}{template_no}{variant}",
            ]
        )
        path_text = _cell(model.get("path"))
        if path_text:
            values.append(Path(path_text).stem)
        for value in values:
            normalized = _normalize_user_token(value)
            if normalized:
                lookup.setdefault(normalized, model)
                if normalized.startswith("0"):
                    lookup.setdefault(normalized.lstrip("0"), model)
    return lookup


def _match_gallery_model(model_key: str, lookup: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    normalized = _normalize_user_token(model_key)
    if not normalized:
        return None
    candidates = [normalized, normalized.lstrip("0")]
    for candidate in candidates:
        if candidate in lookup:
            return lookup[candidate]
    for candidate in candidates:
        for key, model in lookup.items():
            if key.startswith(candidate + "_") or key.startswith(candidate):
                return model
    return None


def render_preview_samples(
    project_root: Path,
    excel_path: Path,
    label_models: list[dict[str, Any]],
    limit: int = 5,
    row_numbers: list[str] | None = None,
) -> list[dict[str, str]]:
    """Render a small set of real row previews on demand.

    This is intentionally not used in the normal state payload because real rendering is
    heavier than showing model thumbnails. The UI calls it only when the user asks for
    production-like mini previews after running Excel validation.
    """

    models_by_key = {
        _key(model.get("model_no"), model.get("template_no"), model.get("label_variant")): model
        for model in label_models
    }
    rows: list[dict[str, str]] = []
    selected_rows = {str(value).strip() for value in (row_numbers or []) if str(value).strip()}
    sample_limit = max(limit, len(selected_rows)) if selected_rows else limit
    for sample in preview_samples(project_root, excel_path, label_models, limit=sample_limit):
        if selected_rows and str(sample.get("row_number") or "") not in selected_rows:
            continue
        model = models_by_key.get(_key(sample.get("model_no"), sample.get("template_no"), sample.get("label_variant")))
        row = dict(sample)
        row["render_status"] = "PENDING"
        row["render_message"] = ""
        if not model or not model.get("path"):
            row["render_status"] = "ERROR"
            row["render_message"] = "Model bulunamadı."
            rows.append(row)
            continue
        try:
            result = preview_manual(
                project_root,
                Path(str(model.get("path"))),
                {
                    "label_text": row.get("label_text", ""),
                    "date_text": row.get("date_text", ""),
                    "note_text": row.get("note_text", ""),
                },
            )
        except Exception as exc:  # noqa: BLE001
            row["render_status"] = "ERROR"
            row["render_message"] = str(exc)
            rows.append(row)
            continue
        if result.get("status") == "OK" and result.get("preview_url"):
            row["preview_image"] = str(result.get("preview_url") or "")
            row["render_preview_path"] = str(result.get("relative_path") or result.get("png_path") or "")
            row["render_status"] = "OK"
            row["render_message"] = "Gerçek mini önizleme oluşturuldu."
        else:
            row["render_status"] = "ERROR"
            row["render_message"] = str(result.get("message") or "Mini önizleme oluşturulamadı.")
        rows.append(row)
    return rows


def write_selected_rows_excel(project_root: Path, excel_path: Path, row_numbers: list[str]) -> dict[str, object]:
    if not excel_path.exists():
        return {"status": "ERROR", "message": "Excel dosyası bulunamadı."}
    selected_rows = {str(value).strip() for value in row_numbers if str(value).strip()}
    if not selected_rows:
        return {"status": "ERROR", "message": "Üretim için en az bir satır seçin."}
    try:
        dataframe = read_orders_excel(excel_path)
    except Exception as exc:  # noqa: BLE001
        return {"status": "ERROR", "message": f"Excel okunamadı: {exc}"}

    selected_index_values = []
    selected_existing_rows: list[str] = []
    for position, index_value in enumerate(dataframe.index):
        excel_row_number = str(position + 2)
        if excel_row_number in selected_rows:
            selected_index_values.append(index_value)
            selected_existing_rows.append(excel_row_number)
    if not selected_index_values:
        return {"status": "ERROR", "message": "Seçili satırlar Excel içinde bulunamadı."}

    target_dir = project_root / "output" / datetime.now().strftime("%Y-%m-%d") / "bulk_selected"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"selected_rows_{datetime.now().strftime('%H%M%S')}.xlsx"
    dataframe.loc[selected_index_values].to_excel(target_path, index=False)
    return {
        "status": "OK",
        "message": f"{len(selected_index_values)} seçili satır için geçici üretim Excel’i hazırlandı.",
        "row_count": len(selected_index_values),
        "row_numbers": selected_existing_rows,
        "path": str(target_path),
        "relative_path": _relative(target_path, project_root),
    }


def _key(model_no: object, template_no: object, label_variant: object) -> tuple[str, str, str]:
    return (str(model_no or "").strip(), str(template_no or "").strip(), str(label_variant or "").strip().upper())


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def _warning(missing_model: bool, model: dict[str, Any] | None) -> str:
    if missing_model:
        return "Model bulunamadı. model_no/template_no/label_variant bilgisini kontrol edin."
    if not model.get("preview_image"):
        return "Önizleme eksik. Tasarım konumu onaylanmadı; AI/CDR dosyasından PNG/JPG/WebP export edip modele bağlayın."
    if str(model.get("active", "true")).lower() == "false":
        return "Model pasif görünüyor. Üretimden önce kontrol edin."
    return ""


def _relative(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except Exception:
        return path.name
