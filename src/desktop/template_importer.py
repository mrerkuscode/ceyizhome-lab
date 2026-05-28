from __future__ import annotations

import csv
import shutil
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Callable


ALLOWED_TEMPLATE_SUFFIXES = {".json"}
ALLOWED_PRINT_TEMPLATE_SUFFIXES = {".cdr", ".ai", ".pdf", ".svg"}
ALLOWED_BACKGROUND_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_INPUT_SUFFIXES = {".xlsx"}
ALLOWED_ROOT_HELPERS = {
    "README_TEST_PACK.txt",
    "preview_contact_sheet.png",
    "settings_label_designer_snippet.yaml",
}

IMPORT_REPORT_COLUMNS = [
    "source_zip",
    "source_path",
    "target_path",
    "file_type",
    "status",
    "warning",
]

ConflictHandler = Callable[[Path, Path], str]


@dataclass(frozen=True)
class TemplateImportResult:
    rows: list[dict[str, str]]
    report_path: Path
    imported_templates: int
    imported_print_templates: int
    imported_backgrounds: int
    imported_excels: int
    skipped_files: int
    error_files: int
    preview_path: Path | None


class TemplateImportError(ValueError):
    pass


def validate_zip_path(zip_path: Path) -> None:
    if not zip_path.exists():
        raise TemplateImportError(f"ZIP dosyası bulunamadı: {zip_path}")
    if zip_path.suffix.lower() != ".zip":
        raise TemplateImportError("Şablon paketi .zip uzantılı olmalıdır.")
    if not zipfile.is_zipfile(zip_path):
        raise TemplateImportError("Seçilen dosya geçerli bir ZIP paketi değil.")


def inspect_template_pack(zip_path: Path) -> list[dict[str, str]]:
    validate_zip_path(zip_path)
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            rows.append(_inspection_row(zip_path, info.filename))
    return rows


def safe_extract_template_pack(
    zip_path: Path,
    project_root: Path,
    conflict_handler: ConflictHandler | None = None,
    run_date: date | None = None,
) -> TemplateImportResult:
    validate_zip_path(zip_path)
    run_date = run_date or date.today()
    rows: list[dict[str, str]] = []
    preview_path: Path | None = None

    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            plan = _plan_target(zip_path, info.filename, project_root, run_date)
            if plan["status"] != "PENDING":
                rows.append(plan)
                continue

            target_path = Path(plan["target_path"])
            try:
                _ensure_inside(target_path, project_root)
            except TemplateImportError as exc:
                rows.append({**plan, "status": "ERROR_INVALID_PATH", "warning": str(exc)})
                continue

            if target_path.exists():
                decision = conflict_handler(zip_path, target_path) if conflict_handler else "skip"
                if decision != "overwrite":
                    rows.append({**plan, "status": "SKIPPED_EXISTS", "warning": "Dosya zaten var, atlandı."})
                    continue

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target_path.open("wb") as target:
                    shutil.copyfileobj(source, target)
                rows.append({**plan, "status": "IMPORTED", "warning": ""})
                if info.filename.replace("\\", "/").endswith("preview_contact_sheet.png"):
                    preview_path = target_path
            except OSError as exc:
                rows.append({**plan, "status": "ERROR_COPY_FAILED", "warning": str(exc)})

    report_path = write_import_report(rows, project_root / "output" / run_date.isoformat() / "reports")
    return TemplateImportResult(
        rows=rows,
        report_path=report_path,
        imported_templates=_count(rows, "template_json"),
        imported_print_templates=_count(rows, "print_template"),
        imported_backgrounds=_count(rows, "background_image"),
        imported_excels=_count(rows, "excel_input"),
        skipped_files=sum(1 for row in rows if row["status"].startswith("SKIPPED")),
        error_files=sum(1 for row in rows if row["status"].startswith("ERROR")),
        preview_path=preview_path,
    )


def write_import_report(rows: list[dict[str, str]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "template_import_report.csv"
    with report_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=IMPORT_REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return report_path


def _inspection_row(zip_path: Path, source_path: str) -> dict[str, str]:
    return _plan_target(zip_path, source_path, Path("."), date.today())


def _plan_target(zip_path: Path, source_path: str, project_root: Path, run_date: date) -> dict[str, str]:
    normalized = source_path.replace("\\", "/")
    base_row = {
        "source_zip": str(zip_path),
        "source_path": source_path,
        "target_path": "",
        "file_type": "",
        "status": "PENDING",
        "warning": "",
    }

    if _is_unsafe_zip_path(normalized):
        return {**base_row, "status": "ERROR_INVALID_PATH", "warning": "ZIP içinde güvenli olmayan dosya yolu var."}

    path = PurePosixPath(normalized)
    suffix = path.suffix.lower()
    parts = path.parts

    if len(parts) >= 3 and parts[0] == "templates" and parts[1] == "designs":
        if suffix not in ALLOWED_TEMPLATE_SUFFIXES:
            return {**base_row, "file_type": "template_json", "status": "SKIPPED_INVALID_TYPE", "warning": "Sadece .json şablon kabul edilir."}
        target = project_root / "templates" / "designs" / Path(*parts[2:])
        return {**base_row, "target_path": str(target), "file_type": "template_json"}

    if len(parts) >= 3 and parts[0] == "templates" and parts[1] == "print":
        if suffix not in ALLOWED_PRINT_TEMPLATE_SUFFIXES:
            return {**base_row, "file_type": "print_template", "status": "SKIPPED_INVALID_TYPE", "warning": "Baskı şablonu için sadece .cdr/.ai/.pdf/.svg kabul edilir."}
        target = project_root / "templates" / "print" / Path(*parts[2:])
        return {**base_row, "target_path": str(target), "file_type": "print_template"}

    if len(parts) >= 3 and parts[0] == "assets" and parts[1] == "label_backgrounds":
        if suffix not in ALLOWED_BACKGROUND_SUFFIXES:
            return {**base_row, "file_type": "background_image", "status": "SKIPPED_INVALID_TYPE", "warning": "Sadece .png/.jpg/.jpeg/.webp görsel kabul edilir."}
        target = project_root / "assets" / "label_backgrounds" / Path(*parts[2:])
        return {**base_row, "target_path": str(target), "file_type": "background_image"}

    if len(parts) == 2 and parts[0] == "input":
        if suffix not in ALLOWED_INPUT_SUFFIXES:
            return {**base_row, "file_type": "excel_input", "status": "SKIPPED_INVALID_TYPE", "warning": "Input klasöründe sadece .xlsx kabul edilir."}
        target = project_root / "input" / parts[1]
        return {**base_row, "target_path": str(target), "file_type": "excel_input"}

    if len(parts) == 1 and parts[0] in ALLOWED_ROOT_HELPERS:
        target = project_root / "output" / run_date.isoformat() / "imports" / zip_path.stem / parts[0]
        file_type = "preview" if parts[0] == "preview_contact_sheet.png" else "helper"
        return {**base_row, "target_path": str(target), "file_type": file_type}

    return {**base_row, "status": "SKIPPED_INVALID_TYPE", "warning": "Bu dosya tipi veya klasör şablon paketi için izinli değil."}


def _is_unsafe_zip_path(path: str) -> bool:
    if path.startswith("/") or path.startswith("\\"):
        return True
    if ":" in path:
        return True
    parts = PurePosixPath(path).parts
    return any(part in {"..", ""} for part in parts)


def _ensure_inside(target_path: Path, project_root: Path) -> None:
    project_root_resolved = project_root.resolve()
    target_resolved = target_path.resolve()
    try:
        target_resolved.relative_to(project_root_resolved)
    except ValueError as exc:
        raise TemplateImportError(f"Hedef yol proje klasörü dışında: {target_path}") from exc


def _count(rows: list[dict[str, str]], file_type: str) -> int:
    return sum(1 for row in rows if row["file_type"] == file_type and row["status"] == "IMPORTED")
