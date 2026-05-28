from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication

from .file_api import to_web_file_url


def get_pdf_preview_payload(project_root: Path, pdf_path: str | Path) -> dict[str, object]:
    path = _safe_output_pdf_path(project_root, pdf_path)
    if path is None:
        return {
            "status": "ERROR",
            "message": "PDF dosyası proje çıktıları içinde bulunamadı.",
            "warnings": ["Proje dışındaki PDF dosyaları program içinde görüntülenmez."],
        }
    if not path.exists() or not path.is_file():
        return {"status": "ERROR", "message": "PDF dosyası bulunamadı.", "warnings": []}
    if path.suffix.lower() != ".pdf":
        return {"status": "ERROR", "message": "Seçilen dosya PDF değil.", "warnings": []}

    warnings: list[str] = []
    file_url = to_web_file_url(path, project_root)
    page_count = _pdf_page_count(path)
    preview_pages = _render_pdf_preview_pages(project_root, path, warnings)
    if preview_pages:
        page_count = max(page_count, len(preview_pages))
    matched_png = _matching_png_preview(project_root, path)
    if not preview_pages and matched_png:
        preview_pages = [
            {
                "page": 1,
                "preview_png_path": _relative(matched_png, project_root),
                "preview_url": to_web_file_url(matched_png, project_root),
            }
        ]
        warnings.append("PDF için aynı isimli görsel önizleme gösteriliyor.")
    if not preview_pages and not file_url:
        warnings.append("PDF program içinde görüntülenemedi. Harici Aç ile kontrol edebilirsiniz.")
    return {
        "status": "OK",
        "file_path": str(path.resolve()),
        "relative_path": _relative(path, project_root),
        "file_url": file_url,
        "display_name": path.name,
        "file_type": _pdf_type(path),
        "created_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        "size_kb": max(1, round(path.stat().st_size / 1024)),
        "page_count": page_count,
        "can_inline_view": bool(file_url),
        "preview_pages": preview_pages,
        "warnings": warnings,
    }


def _safe_output_pdf_path(project_root: Path, value: str | Path) -> Path | None:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    try:
        resolved = candidate.resolve()
        output_root = (project_root / "output").resolve()
        resolved.relative_to(output_root)
    except Exception:
        return None
    return resolved


def _render_pdf_preview_pages(project_root: Path, pdf_path: Path, warnings: list[str]) -> list[dict[str, object]]:
    try:
        app = QApplication.instance() or QApplication([])
        _ = app
        doc = QPdfDocument()
        status = doc.load(str(pdf_path))
        if doc.pageCount() <= 0:
            warnings.append("PDF sayfa önizlemesi üretilemedi; dosya QtPdf ile okunamadı.")
            return []
        page_count = min(doc.pageCount(), 50)
        preview_dir = _preview_dir_for(project_root, pdf_path)
        preview_dir.mkdir(parents=True, exist_ok=True)
        pages: list[dict[str, object]] = []
        for index in range(page_count):
            page_size = doc.pagePointSize(index)
            ratio = page_size.width() / page_size.height() if page_size.height() else 1.0
            target_width = 900
            target_height = max(1, round(target_width / ratio))
            image = doc.render(index, QSize(target_width, target_height))
            if image.isNull():
                continue
            target = preview_dir / f"page_{index + 1:03d}.png"
            if image.save(str(target), "PNG"):
                pages.append(
                    {
                        "page": index + 1,
                        "preview_png_path": _relative(target, project_root),
                        "preview_url": to_web_file_url(target, project_root),
                    }
                )
        if not pages:
            warnings.append("PDF sayfa görselleri üretilemedi.")
        return pages
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"PDF sayfa önizlemesi üretilemedi: {type(exc).__name__}")
        return []


def _preview_dir_for(project_root: Path, pdf_path: Path) -> Path:
    output_root = (project_root / "output").resolve()
    try:
        relative = pdf_path.resolve().relative_to(output_root)
        date_part = relative.parts[0]
    except Exception:
        date_part = datetime.now().strftime("%Y-%m-%d")
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", pdf_path.stem).strip("_") or "pdf"
    return project_root / "output" / date_part / "preview" / "pdf" / safe_stem


def _matching_png_preview(project_root: Path, pdf_path: Path) -> Path | None:
    candidates = [
        pdf_path.with_suffix(".png"),
        pdf_path.parent / f"{pdf_path.stem}_preview.png",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and to_web_file_url(candidate, project_root):
            return candidate
    return None


def _pdf_page_count(path: Path) -> int:
    try:
        app = QApplication.instance() or QApplication([])
        _ = app
        doc = QPdfDocument()
        doc.load(str(path))
        if doc.pageCount() > 0:
            return doc.pageCount()
    except Exception:
        pass
    try:
        text = path.read_bytes().decode("latin-1", errors="ignore")
        count = len(re.findall(r"/Type\s*/Page\b", text))
        return count or 1
    except Exception:
        return 1


def _pdf_type(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("roll_batch"):
        return "Rulo Batch PDF"
    if name.startswith("manual") or path.parent.name.lower() == "manual":
        return "Manuel PDF"
    return "PDF"


def _relative(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        return path.name
