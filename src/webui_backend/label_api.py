from __future__ import annotations

from datetime import datetime
import json
import re
from pathlib import Path
import shutil

from label_designer.calibration_service import create_calibration_pdf
from label_designer.manual_label_service import render_manual_label, render_manual_preview
from desktop.file_actions import latest_run_dir

from .template_api import list_label_templates
from .file_api import to_web_file_url


def render_manual(project_root: Path, template_path: Path, label_text: str, quantity: int, field_values: dict[str, str] | None = None):
    return render_manual_label(project_root, template_path, label_text, quantity, field_values=field_values)


def preview_manual(project_root: Path, template_path: Path, field_values: dict[str, str] | None = None) -> dict[str, str]:
    field_values = field_values or {}
    label_text = str(field_values.get("label_text") or "Ayşe & Mehmet")
    result = render_manual_preview(project_root, template_path, label_text, field_values=field_values)
    return {
        "status": "OK",
        "message": "Gerçek render önizlemesi oluşturuldu.",
        "png_path": str(result.png_path.resolve()),
        "relative_path": _relative(result.png_path, project_root),
        "preview_url": to_web_file_url(result.png_path, project_root),
    }


def create_calibration(project_root: Path):
    return create_calibration_pdf(project_root)


def templates(project_root: Path) -> list[dict[str, str]]:
    return list_label_templates(project_root)


def list_label_outputs(project_root: Path) -> list[dict[str, str]]:
    run_dir = latest_run_dir(project_root)
    print_dir = run_dir / "print"
    if not print_dir.exists():
        print_dir = run_dir / "PRINT"
    if not print_dir.exists():
        return []
    rows: list[dict[str, str]] = []
    bulk_rows = _bulk_manifest_rows(run_dir)
    for path in sorted(print_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".pdf", ".png", ".csv"}:
            continue
        if path.name == "template_matching_report.csv":
            continue
        kind = "PNG" if suffix == ".png" else "PDF" if suffix == ".pdf" else "RAPOR"
        if path.name.startswith("roll_batch"):
            kind = "RULO TOPLU PDF"
        elif path.parent.name == "manual":
            kind = f"MANUEL {kind}"
        relative = _relative(path, project_root)
        model_no = _model_from_path(path)
        preview_url = to_web_file_url(path, project_root) if suffix == ".png" else ""
        bulk_meta = _bulk_metadata_for_output(path.name, bulk_rows)
        row = {
                "name": path.name,
                "file_name": path.name,
                "display_name": bulk_meta.get("model_name") or _display_name(path, kind),
                "file_path": str(path.resolve()),
                "relative_path": relative,
                "file_type": kind,
                "type": kind,
                "model_no": model_no,
                "template_no": _from_roll_batch_name(path.name, 3),
                "label_variant": _from_roll_batch_name(path.name, 4),
                "created_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "size_kb": str(max(1, round(path.stat().st_size / 1024))),
                "preview_url": preview_url,
                "preview_uri": preview_url,
                "status": "HAZIR",
            }
        if bulk_meta:
            row.update(bulk_meta)
        rows.append(row)
    return rows


def _bulk_manifest_rows(run_dir: Path) -> list[dict[str, str]]:
    manifest_dir = run_dir / "bulk_gallery"
    if not manifest_dir.exists():
        return []
    rows: list[dict[str, str]] = []
    manifests = sorted(manifest_dir.glob("batch_manifest_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for manifest in manifests:
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            continue
        created_at = str(payload.get("created_at") or "")
        for row in payload.get("rows") or []:
            if not isinstance(row, dict):
                continue
            item = {key: str(value or "") for key, value in row.items() if not isinstance(value, (list, dict))}
            item["manifest_path"] = _relative(manifest, run_dir.parents[1] if len(run_dir.parents) > 1 else run_dir)
            item["manifest_created_at"] = created_at
            rows.append(item)
    return rows


def _bulk_metadata_for_output(file_name: str, rows: list[dict[str, str]]) -> dict[str, str]:
    stem = Path(file_name).stem
    match = re.search(r"(?:order[_-])?bulk[_-]?(\d+)", stem, re.IGNORECASE)
    if not match:
        return {}
    row_number = match.group(1)
    row = next(
        (
            item for item in rows
            if str(item.get("row_number") or "").strip() == row_number
            or str(item.get("item_id") or "").lower() in {f"row-{row_number}", f"bulk-{row_number}"}
            or str(item.get("item_id") or "").lower().endswith(f"-{row_number}")
        ),
        None,
    )
    if not row:
        return {}
    return {
        "model_name": row.get("model_name", ""),
        "display_name": row.get("model_name", "") or "Toplu Etiket Çıktısı",
        "label_text": row.get("label_text", ""),
        "date_text": row.get("date_text", ""),
        "note_text": row.get("note_text", ""),
        "quantity": row.get("quantity", "") or "1",
        "bulk_row_number": row_number,
        "bulk_status": row.get("status", ""),
    }


def list_archived_label_outputs(project_root: Path) -> list[dict[str, str]]:
    archive_dir = (project_root / "output" / "archive").resolve()
    if not archive_dir.exists():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(archive_dir.rglob("*"), key=lambda item: item.stat().st_mtime if item.is_file() else 0, reverse=True):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".png"}:
            continue
        preview_url = to_web_file_url(path, project_root) if path.suffix.lower() == ".png" else ""
        rows.append(
            {
                "name": path.name,
                "file_name": path.name,
                "display_name": f"Arşiv: {_display_name(path, 'PDF' if path.suffix.lower() == '.pdf' else 'PNG')}",
                "file_path": str(path.resolve()),
                "relative_path": _relative(path, project_root),
                "file_type": "ARŞİV PNG" if path.suffix.lower() == ".png" else "ARŞİV PDF",
                "type": "ARŞİV PNG" if path.suffix.lower() == ".png" else "ARŞİV PDF",
                "created_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "size_kb": str(max(1, round(path.stat().st_size / 1024))),
                "preview_url": preview_url,
                "preview_uri": preview_url,
                "status": "ARŞİVDE",
            }
        )
    return rows


def list_label_output_archive_history(project_root: Path, limit: int = 20) -> list[dict[str, object]]:
    rows = _read_archive_history(project_root)
    return rows[: max(1, int(limit or 20))]


def archive_label_outputs(project_root: Path, relative_paths: list[str]) -> dict[str, object]:
    """Move customer output files into output/archive without deleting anything."""
    output_root = (project_root / "output").resolve()
    archive_root = output_root / "archive" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    moved: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for raw in relative_paths:
        value = str(raw or "").strip()
        if not value:
            continue
        source = (project_root / value).resolve()
        try:
            relative_to_output = source.relative_to(output_root)
        except ValueError:
            skipped.append({"path": value, "reason": "Proje output klasörü dışında."})
            continue
        if not source.exists() or not source.is_file():
            skipped.append({"path": value, "reason": "Dosya bulunamadı."})
            continue
        if "archive" in relative_to_output.parts:
            skipped.append({"path": value, "reason": "Dosya zaten arşivde."})
            continue
        if source.suffix.lower() not in {".pdf", ".png"}:
            skipped.append({"path": value, "reason": "Sadece müşteri PDF/PNG çıktıları arşivlenir."})
            continue
        target = archive_root / relative_to_output
        target.parent.mkdir(parents=True, exist_ok=True)
        target = _unique_archive_target(target)
        shutil.move(str(source), str(target))
        moved.append(
            {
                "from": _relative(source, project_root),
                "to": _relative(target, project_root),
            }
        )
    if moved:
        _append_archive_history(project_root, "archived", moved)
        return {
            "status": "OK",
            "message": f"{len(moved)} çıktı güvenli arşive taşındı.",
            "archive_dir": _relative(archive_root, project_root),
            "moved": moved,
            "skipped": skipped,
        }
    return {
        "status": "NOOP",
        "message": "Arşivlenecek uygun müşteri çıktısı bulunamadı.",
        "archive_dir": _relative(archive_root, project_root),
        "moved": moved,
        "skipped": skipped,
    }


def restore_label_outputs(project_root: Path, archived_relative_paths: list[str]) -> dict[str, object]:
    """Move archived PDF/PNG files back under output without overwriting live files."""
    output_root = (project_root / "output").resolve()
    archive_root = (output_root / "archive").resolve()
    restored: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for raw in archived_relative_paths:
        value = str(raw or "").strip()
        if not value:
            continue
        source = (project_root / value).resolve()
        try:
            relative_to_archive = source.relative_to(archive_root)
        except ValueError:
            skipped.append({"path": value, "reason": "Dosya arşiv klasörü dışında."})
            continue
        if not source.exists() or not source.is_file():
            skipped.append({"path": value, "reason": "Arşiv dosyası bulunamadı."})
            continue
        if source.suffix.lower() not in {".pdf", ".png"}:
            skipped.append({"path": value, "reason": "Sadece PDF/PNG çıktıları geri alınır."})
            continue
        parts = relative_to_archive.parts
        if len(parts) < 2:
            skipped.append({"path": value, "reason": "Arşiv yolu geri alma için uygun değil."})
            continue
        original_relative = Path(*parts[1:])
        target = output_root / original_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target = _unique_archive_target(target)
        shutil.move(str(source), str(target))
        restored.append({"from": _relative(source, project_root), "to": _relative(target, project_root)})
    if restored:
        _append_archive_history(project_root, "restored", restored)
        return {
            "status": "OK",
            "message": f"{len(restored)} çıktı arşivden geri alındı.",
            "restored": restored,
            "skipped": skipped,
        }
    return {
        "status": "NOOP",
        "message": "Geri alınacak uygun arşiv çıktısı bulunamadı.",
        "restored": restored,
        "skipped": skipped,
    }


def _unique_archive_target(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Arşiv hedefi üretilemedi: {path}")


def _archive_history_path(project_root: Path) -> Path:
    return project_root / "output" / "label_output_archive_history.json"


def _read_archive_history(project_root: Path) -> list[dict[str, object]]:
    path = _archive_history_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _write_archive_history(project_root: Path, rows: list[dict[str, object]]) -> None:
    path = _archive_history_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows[:100], ensure_ascii=False, indent=2), encoding="utf-8")


def _append_archive_history(project_root: Path, action: str, rows: list[dict[str, str]]) -> None:
    history = _read_archive_history(project_root)
    entry = {
        "action": action,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "count": len(rows),
        "items": rows,
    }
    _write_archive_history(project_root, [entry, *history])


def list_laser_outputs(project_root: Path) -> list[dict[str, str]]:
    run_dir = latest_run_dir(project_root)
    laser_dir = run_dir / "laser"
    if not laser_dir.exists():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(laser_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".svg", ".csv", ".txt"}:
            continue
        rows.append(
            {
                "file_name": path.name,
                "relative_path": _relative(path, project_root),
                "type": "SVG PLAKA" if suffix == ".svg" else "RAPOR",
                "model_no": _model_from_path(path),
                "created_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "size_kb": str(max(1, round(path.stat().st_size / 1024))),
                "preview_uri": path.resolve().as_uri() if suffix == ".svg" else "",
                "status": "HAZIR",
            }
        )
    return rows


def _model_from_path(path: Path) -> str:
    for part in path.parts:
        if part.startswith("model_"):
            return part.replace("model_", "")
    return ""


def _from_roll_batch_name(name: str, index: int) -> str:
    if not name.startswith("roll_batch"):
        return ""
    stem = Path(name).stem
    parts = stem.split("_")
    return parts[index] if len(parts) > index else ""


def _relative(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except Exception:
        return path.name


def _display_name(path: Path, kind: str) -> str:
    stem = path.stem
    if stem.startswith("order_"):
        return f"Etiket çıktısı {stem.replace('order_', '')}"
    if stem.startswith("roll_batch"):
        return "Rulo toplu PDF"
    if path.parent.name == "manual":
        return "Manuel etiket çıktısı"
    return kind
