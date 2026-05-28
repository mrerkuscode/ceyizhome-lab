from __future__ import annotations

from pathlib import Path
import shutil
from datetime import datetime

import yaml


def load_config(project_root: Path) -> dict:
    path = project_root / "config" / "settings.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_config(project_root: Path, data: dict) -> None:
    path = project_root / "config" / "settings.yaml"
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, backup_dir / f"settings_{stamp}.yaml")
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def list_settings_backups(project_root: Path, limit: int = 8) -> list[dict[str, str]]:
    backup_dir = project_root / "config" / "backups"
    if not backup_dir.exists():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(backup_dir.glob("settings_*.yaml"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
        stat = path.stat()
        rows.append(
            {
                "file_name": path.name,
                "relative_path": path.relative_to(project_root).as_posix(),
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "size_kb": str(max(1, round(stat.st_size / 1024))),
            }
        )
    return rows


def get_label_defaults(project_root: Path) -> dict:
    return dict(load_config(project_root).get("label_defaults", {}) or {})


def save_label_defaults(project_root: Path, values: dict) -> None:
    data = load_config(project_root)
    defaults = data.setdefault("label_defaults", {})
    defaults.update(values)
    defaults.setdefault("media_type", "ROLL")
    print_data = data.setdefault("print", {})
    print_data["allow_direct_print"] = False
    print_data["require_print_confirmation"] = True
    save_config(project_root, data)


def get_print_mode(project_root: Path) -> str:
    return str(load_config(project_root).get("print", {}).get("mode", "data_only"))


def set_print_mode(project_root: Path, mode: str) -> None:
    if mode not in {"data_only", "label_designer"}:
        raise ValueError("print.mode sadece data_only veya label_designer olabilir.")
    data = load_config(project_root)
    print_data = data.setdefault("print", {})
    print_data["mode"] = mode
    print_data["allow_direct_print"] = False
    print_data["require_print_confirmation"] = True
    save_config(project_root, data)
