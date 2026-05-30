"""Font Kütüphanesi API — Part A

Etiket ve lazer fontlarını yönetir.
Manifest: config/fonts/manifest.json
Font dosyaları: assets/fonts/library/
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


_ALLOWED_EXTS = {".ttf", ".otf"}


def manifest_path(project_root: Path) -> Path:
    p = project_root / "config" / "fonts" / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def library_dir(project_root: Path) -> Path:
    d = project_root / "assets" / "fonts" / "library"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_manifest(project_root: Path) -> dict[str, Any]:
    p = manifest_path(project_root)
    if not p.exists():
        return {"label_fonts": [], "laser_fonts": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"label_fonts": [], "laser_fonts": []}
        data.setdefault("label_fonts", [])
        data.setdefault("laser_fonts", [])
        return data
    except json.JSONDecodeError:
        return {"label_fonts": [], "laser_fonts": []}


def _save_manifest(project_root: Path, data: dict[str, Any]) -> None:
    manifest_path(project_root).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_fonts(project_root: Path) -> dict[str, Any]:
    """Return the font manifest."""
    return _load_manifest(project_root)


def add_font(
    project_root: Path,
    filename: str,
    file_bytes: bytes,
    font_type: str,
    *,
    laser_safe: bool = False,
) -> dict[str, Any]:
    """Save font file and register in manifest.

    font_type must be 'label' or 'laser'.
    laser_safe is only meaningful for laser fonts.
    """
    if font_type not in {"label", "laser"}:
        return {"status": "ERROR", "error": "font_type 'label' veya 'laser' olmalı"}

    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTS:
        return {"status": "ERROR", "error": f"İzin verilmeyen format: {suffix}. Kabul edilen: .ttf, .otf"}

    if len(file_bytes) < 16:
        return {"status": "ERROR", "error": "Font dosyası çok küçük veya boş"}

    font_id = str(uuid.uuid4())[:8]
    safe_name = f"{font_id}_{_safe_filename(filename)}"
    dest = library_dir(project_root) / safe_name
    dest.write_bytes(file_bytes)

    display_name = Path(filename).stem.replace("_", " ").replace("-", " ")
    uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    manifest = _load_manifest(project_root)
    entry: dict[str, Any] = {
        "id": font_id,
        "name": display_name,
        "file": safe_name,
        "uploaded_at": uploaded_at,
    }

    if font_type == "laser":
        entry["laser_safe"] = bool(laser_safe)
        manifest["laser_fonts"].append(entry)
    else:
        manifest["label_fonts"].append(entry)

    _save_manifest(project_root, manifest)
    return {"status": "OK", "font": entry, "font_type": font_type}


def delete_font(project_root: Path, font_id: str) -> dict[str, Any]:
    """Remove a font from the manifest and optionally the filesystem."""
    manifest = _load_manifest(project_root)
    deleted: dict[str, Any] | None = None
    for key in ("label_fonts", "laser_fonts"):
        before = manifest[key]
        manifest[key] = [f for f in before if f.get("id") != font_id]
        if len(manifest[key]) < len(before):
            deleted = next(f for f in before if f.get("id") == font_id)
    if not deleted:
        return {"status": "MISSING", "error": "Font bulunamadı"}

    font_file = library_dir(project_root) / (deleted.get("file") or "")
    if font_file.exists():
        font_file.unlink(missing_ok=True)

    _save_manifest(project_root, manifest)
    return {"status": "OK", "deleted": deleted}


def _safe_filename(name: str) -> str:
    safe = "".join(c for c in Path(name).name if c.isalnum() or c in "._-")
    return safe or "font"
