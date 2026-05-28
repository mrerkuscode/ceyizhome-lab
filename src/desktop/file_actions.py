from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path


def open_folder(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"Klasör bulunamadı: {path}"
    if not path.is_dir():
        return False, f"Bu bir klasör değil: {path}"

    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606 - user-requested local folder opening.
        return True, f"Klasör açıldı: {path}"

    return False, "Klasör açma sadece Windows için hazırlandı."


def latest_run_dir(project_root: Path) -> Path:
    output_dir = project_root / "output"
    if not output_dir.exists():
        return output_dir

    dated_dirs = [path for path in output_dir.iterdir() if path.is_dir() and _is_date_dir(path)]
    if not dated_dirs:
        return output_dir
    return sorted(dated_dirs, key=lambda item: item.stat().st_mtime)[-1]


def _is_date_dir(path: Path) -> bool:
    try:
        date.fromisoformat(path.name)
    except ValueError:
        return False
    return True
