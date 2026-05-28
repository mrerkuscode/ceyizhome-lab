from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def create_manifest(source_path: str | Path, source_format: str, editor_engine: str, job_id: str) -> dict[str, Any]:
    return {
        "source_path": str(source_path),
        "source_format": source_format.lower(),
        "editor_engine": editor_engine,
        "job_id": job_id,
        "objects": [],
        "warnings": [],
        "errors": [],
    }


def text_object(
    object_id: str,
    source_ref: str,
    current_text: str,
    *,
    name: str = "",
    bounds: dict[str, float] | None = None,
    editable: bool = True,
    warnings: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "object_id": object_id,
        "source_ref": source_ref,
        "name": name or object_id,
        "type": "text",
        "current_text": current_text,
        "editable": editable,
        "bounds": bounds or {"x": 0, "y": 0, "width": 0, "height": 0},
        "warnings": warnings or [],
    }
    if extra:
        item.update(extra)
    return item


def add_warning(manifest: dict[str, Any], message: str) -> None:
    manifest.setdefault("warnings", []).append(message)


def add_error(manifest: dict[str, Any], message: str) -> None:
    manifest.setdefault("errors", []).append(message)


def save_manifest(manifest: dict[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def load_manifest(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
