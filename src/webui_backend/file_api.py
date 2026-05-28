from __future__ import annotations

import os
import sys
from pathlib import Path

from desktop.file_actions import latest_run_dir, open_folder


def to_web_file_url(path: Path | str, project_root: Path) -> str:
    """Return a QWebEngine-safe file URL for existing project files."""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    try:
        resolved = candidate.resolve()
        root = project_root.resolve()
    except Exception:
        return ""
    if not resolved.exists() or not resolved.is_file():
        return ""
    allowed_roots = (root, root / "output", root / "assets")
    if not any(_is_relative_to(resolved, allowed_root) for allowed_root in allowed_roots):
        return ""
    return resolved.as_uri()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def open_output_folder(project_root: Path) -> tuple[bool, str]:
    return open_folder(latest_run_dir(project_root))


def open_reports_folder(project_root: Path) -> tuple[bool, str]:
    return open_folder(latest_run_dir(project_root) / "reports")


def open_print_folder(project_root: Path) -> tuple[bool, str]:
    run_dir = latest_run_dir(project_root)
    lower = run_dir / "print"
    upper = run_dir / "PRINT"
    print_dir = lower if lower.exists() else upper
    if print_dir.exists():
        rendered_dirs = sorted(print_dir.glob("model_*/rendered"))
        if len(rendered_dirs) == 1:
            return open_folder(rendered_dirs[0])
    return open_folder(print_dir)


def open_print_templates_folder(project_root: Path) -> tuple[bool, str]:
    return open_folder(project_root / "templates" / "print")


def open_laser_folder(project_root: Path) -> tuple[bool, str]:
    return open_folder(latest_run_dir(project_root) / "laser")


def open_input_folder(project_root: Path) -> tuple[bool, str]:
    return open_folder(project_root / "input")


def open_svg(path: Path) -> tuple[bool, str]:
    if not path.exists() or path.suffix.lower() != ".svg":
        return False, f"SVG dosyası bulunamadı: {path}"
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606 - user requested local file open.
        return True, f"SVG dosyası açıldı: {path}"
    return False, "SVG açma sadece Windows için hazırlandı."
