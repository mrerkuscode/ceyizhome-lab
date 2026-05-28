"""DXF Library API — Leyla's DXF reference library system.

Architecture (2026-05-28):
- Operator (Leyla) hand-prepares names in CorelDRAW (Mochary + contour 0.65 +
  Combine + Filled Black), exports as DXF, drops into the size-group folder
  (assets/dxf_library/{70x40,80x40,100x40}/).
- This module scans, parses, indexes, and serves these files.
- No generative algorithm; the system is a librarian.
- Old generative pipelines (targeted-weld, bridge, support_line, contour,
  AI Designer) remain in code but default OFF.

CLAUDE.md compliance: lookup-only, no laser trigger, no auto-print, operator
approval still required for production. 167 SVG references untouched.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import ezdxf
    from ezdxf import bbox as ezdxf_bbox
    EZDXF_AVAILABLE = True
except ImportError:  # pragma: no cover
    ezdxf = None
    ezdxf_bbox = None
    EZDXF_AVAILABLE = False


# --- Constants -------------------------------------------------------------

DXF_LIBRARY_DIR_RELATIVE = "assets/dxf_library"
DXF_LIBRARY_INDEX_RELATIVE = "data/dxf_library.json"
ASCII_TO_TURKISH_RELATIVE = "data/dxf_library_ascii_to_turkish.json"

SIZE_GROUPS = ["70x40", "80x40", "100x40"]

# Bbox tolerance per size group (in mm). Used to flag mismatches at scan time;
# files are still accepted (folder name is source of truth).
SIZE_GROUP_RANGES = {
    "70x40":  {"w_min": 60.0, "w_max": 80.0,  "h_min": 30.0, "h_max": 50.0},
    "80x40":  {"w_min": 70.0, "w_max": 90.0,  "h_min": 30.0, "h_max": 50.0},
    "100x40": {"w_min": 90.0, "w_max": 110.0, "h_min": 30.0, "h_max": 50.0},
}

# Turkish → ASCII translit map (lowercase output).
TURKISH_ASCII_MAP = {
    "ç": "c", "Ç": "c",
    "ğ": "g", "Ğ": "g",
    "ı": "i", "I": "i", "İ": "i", "i": "i",
    "ö": "o", "Ö": "o",
    "ş": "s", "Ş": "s",
    "ü": "u", "Ü": "u",
}

# $INSUNITS code → mm conversion factor.
# Ref: ezdxf docs / AutoCAD: 0=unitless, 1=inch, 4=mm, 5=cm, 6=meter, 7=km, ...
INSUNITS_TO_MM = {
    0: 1.0,   # unitless — assume mm (Corel default for DXF export)
    1: 25.4,  # inch
    2: 304.8, # foot
    4: 1.0,   # mm
    5: 10.0,  # cm
    6: 1000.0,# meter
}


# --- ASCII naming utilities ------------------------------------------------

def to_ascii_name(name: str) -> str:
    """Convert 'Mücahit' → 'mucahit', 'Ahmet & Mehmet' → 'ahmet_mehmet'.

    Rules:
    - Turkish chars mapped (ç→c, ğ→g, ı→i, İ→i, ö→o, ş→s, ü→u)
    - Other diacritics stripped via NFKD
    - Lowercase
    - Apostrophe-like punctuation (', `, ’, ´, ") STRIPPED (no underscore inserted)
      so "D'Andre" → "dandre" rather than "d_andre"
    - Word separators (space, &, ,, ., -, etc.) → underscore
    - Collapse repeated underscores, strip leading/trailing
    """
    text = str(name or "")
    for tr, ascii_ch in TURKISH_ASCII_MAP.items():
        text = text.replace(tr, ascii_ch)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    # Strip apostrophe-family BEFORE the broad punctuation→underscore rule
    text = re.sub(r"['`\"‘’′´]+", "", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def load_ascii_to_turkish_map(project_root: Path) -> dict[str, str]:
    """Load the friendly-name (Turkish) lookup map. Auto-creates if missing."""
    path = project_root / ASCII_TO_TURKISH_RELATIVE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def save_ascii_to_turkish_map(project_root: Path, mapping: dict[str, str]) -> None:
    path = project_root / ASCII_TO_TURKISH_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def turkish_for_ascii(project_root: Path, ascii_name: str) -> str:
    mapping = load_ascii_to_turkish_map(project_root)
    return mapping.get(ascii_name, ascii_name)


# --- DXF reading -----------------------------------------------------------

@dataclass(frozen=True)
class DxfReadResult:
    """Outcome of parsing a single DXF file."""
    path: str
    readable: bool
    error: str
    entity_types: tuple[str, ...]
    entity_count: int
    insunits_code: int
    mm_per_unit: float
    bbox_mm: tuple[float, float]  # (width, height)
    bbox_raw: tuple[float, float, float, float]  # (xmin, ymin, xmax, ymax) raw units
    closed_paths_estimate: int
    has_spline: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "readable": self.readable,
            "error": self.error,
            "entity_types": list(self.entity_types),
            "entity_count": self.entity_count,
            "insunits_code": self.insunits_code,
            "mm_per_unit": self.mm_per_unit,
            "bbox_mm": list(self.bbox_mm),
            "bbox_raw": list(self.bbox_raw),
            "closed_paths_estimate": self.closed_paths_estimate,
            "has_spline": self.has_spline,
        }


SUPPORTED_DXF_ENTITIES = {"SPLINE", "POLYLINE", "LWPOLYLINE", "LINE", "ARC", "CIRCLE"}


def read_dxf_file(path: Path) -> DxfReadResult:
    """Read a DXF file via ezdxf; return geometric metadata in mm.

    Never raises — wraps errors into DxfReadResult.error.
    """
    if not EZDXF_AVAILABLE:
        return DxfReadResult(
            path=str(path),
            readable=False,
            error="ezdxf module not installed",
            entity_types=(),
            entity_count=0,
            insunits_code=0,
            mm_per_unit=1.0,
            bbox_mm=(0.0, 0.0),
            bbox_raw=(0.0, 0.0, 0.0, 0.0),
            closed_paths_estimate=0,
            has_spline=False,
        )
    try:
        doc = ezdxf.readfile(str(path))
    except Exception as exc:  # noqa: BLE001 — surface any ezdxf error
        return DxfReadResult(
            path=str(path),
            readable=False,
            error=f"ezdxf.readfile failed: {exc}",
            entity_types=(),
            entity_count=0,
            insunits_code=0,
            mm_per_unit=1.0,
            bbox_mm=(0.0, 0.0),
            bbox_raw=(0.0, 0.0, 0.0, 0.0),
            closed_paths_estimate=0,
            has_spline=False,
        )
    msp = doc.modelspace()
    entities = list(msp)
    types = tuple(sorted({e.dxftype() for e in entities}))
    insunits_code = int(doc.header.get("$INSUNITS", 0) or 0)
    mm_per_unit = INSUNITS_TO_MM.get(insunits_code, 1.0)

    # Bbox computation: use ezdxf.bbox.extents (handles SPLINE properly via flattening)
    try:
        extents = ezdxf_bbox.extents(msp)
    except Exception:  # noqa: BLE001
        extents = None
    if extents is None or extents.size.x == 0 and extents.size.y == 0:
        bbox_raw = (0.0, 0.0, 0.0, 0.0)
        bbox_mm = (0.0, 0.0)
    else:
        xmin, ymin = extents.extmin.x, extents.extmin.y
        xmax, ymax = extents.extmax.x, extents.extmax.y
        bbox_raw = (xmin, ymin, xmax, ymax)
        width_mm = (xmax - xmin) * mm_per_unit
        height_mm = (ymax - ymin) * mm_per_unit
        bbox_mm = (round(width_mm, 3), round(height_mm, 3))

    # Closed paths estimate — count splines flagged closed + polylines flagged closed.
    closed = 0
    has_spline = False
    for e in entities:
        et = e.dxftype()
        if et == "SPLINE":
            has_spline = True
            # ezdxf Spline.closed property
            if bool(getattr(e, "closed", False)) or bool(getattr(e.dxf, "flags", 0) & 1):
                closed += 1
        elif et == "POLYLINE":
            if bool(getattr(e, "is_closed", False)):
                closed += 1
        elif et == "LWPOLYLINE":
            if bool(getattr(e, "closed", False)):
                closed += 1
        elif et == "CIRCLE":
            closed += 1

    return DxfReadResult(
        path=str(path),
        readable=True,
        error="",
        entity_types=types,
        entity_count=len(entities),
        insunits_code=insunits_code,
        mm_per_unit=mm_per_unit,
        bbox_mm=bbox_mm,
        bbox_raw=bbox_raw,
        closed_paths_estimate=closed,
        has_spline=has_spline,
    )


# --- DXF → SVG path data conversion ---------------------------------------

def dxf_to_svg_path_data(path: Path) -> dict[str, Any]:
    """Convert a DXF file (SPLINE/POLYLINE/LINE/ARC/CIRCLE) into a single SVG
    path-data string suitable for the existing exact-reference override
    pipeline.

    Returns:
      {"path_data": str, "bbox_mm": (w, h), "mm_per_unit": float, "error": str}

    Splines are flattened to polylines via ezdxf's flattening (max distance
    0.01 in original units → fine for laser geometry). The SVG output uses
    the original DXF coordinate space; the override hook later transforms it
    into the target bounding box.
    """
    out = {"path_data": "", "bbox_mm": (0.0, 0.0), "mm_per_unit": 1.0, "error": ""}
    if not EZDXF_AVAILABLE:
        out["error"] = "ezdxf module not installed"
        return out
    try:
        doc = ezdxf.readfile(str(path))
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"ezdxf.readfile failed: {exc}"
        return out
    msp = doc.modelspace()
    insunits_code = int(doc.header.get("$INSUNITS", 0) or 0)
    mm_per_unit = INSUNITS_TO_MM.get(insunits_code, 1.0)
    out["mm_per_unit"] = mm_per_unit
    segments: list[str] = []

    def _emit_polyline(points: list[tuple[float, float]], close: bool) -> None:
        if len(points) < 2:
            return
        cmd = [f"M {points[0][0]:.4f} {points[0][1]:.4f}"]
        for x, y in points[1:]:
            cmd.append(f"L {x:.4f} {y:.4f}")
        if close:
            cmd.append("Z")
        segments.append(" ".join(cmd))

    for entity in msp:
        etype = entity.dxftype()
        try:
            if etype == "SPLINE":
                # ezdxf 1.x: flattening returns Vec3 generator
                vertices = list(entity.flattening(0.01))
                pts = [(v.x, v.y) for v in vertices]
                # SPLINE is closed if 'closed' flag is set OR flags bit 0
                is_closed = bool(getattr(entity, "closed", False)) or bool(getattr(entity.dxf, "flags", 0) & 1)
                _emit_polyline(pts, close=is_closed)
            elif etype == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in entity.get_points("xy")]
                _emit_polyline(pts, close=bool(getattr(entity, "closed", False)))
            elif etype == "POLYLINE":
                pts = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                _emit_polyline(pts, close=bool(getattr(entity, "is_closed", False)))
            elif etype == "LINE":
                a = entity.dxf.start
                b = entity.dxf.end
                segments.append(f"M {a.x:.4f} {a.y:.4f} L {b.x:.4f} {b.y:.4f}")
            elif etype == "CIRCLE":
                cx, cy = entity.dxf.center.x, entity.dxf.center.y
                r = float(entity.dxf.radius)
                # Approximate circle with 32 segments
                import math
                pts = []
                steps = 32
                for i in range(steps + 1):
                    a = 2 * math.pi * i / steps
                    pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                _emit_polyline(pts, close=True)
            elif etype == "ARC":
                import math
                cx, cy = entity.dxf.center.x, entity.dxf.center.y
                r = float(entity.dxf.radius)
                a0 = math.radians(float(entity.dxf.start_angle))
                a1 = math.radians(float(entity.dxf.end_angle))
                if a1 < a0:
                    a1 += 2 * math.pi
                steps = max(8, int(abs(a1 - a0) * 16 / math.pi))
                pts = []
                for i in range(steps + 1):
                    a = a0 + (a1 - a0) * i / steps
                    pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                _emit_polyline(pts, close=False)
            # else: silently skip TEXT, HATCH, etc. — not relevant for cut geometry
        except Exception as exc:  # noqa: BLE001
            # Skip the offending entity but keep processing the rest
            out["error"] = (out["error"] + f" | {etype} parse: {exc}").strip(" |")
            continue

    out["path_data"] = " ".join(segments)
    # Bbox in mm from the ezdxf extents (re-uses unit conversion)
    info = read_dxf_file(path)
    out["bbox_mm"] = info.bbox_mm
    return out


# --- Size group classification --------------------------------------------

def detect_size_group(bbox_mm: tuple[float, float]) -> str:
    """Return the size group name that best matches the bbox, or '' if none."""
    w, h = bbox_mm
    for group, rng in SIZE_GROUP_RANGES.items():
        if rng["w_min"] <= w <= rng["w_max"] and rng["h_min"] <= h <= rng["h_max"]:
            return group
    return ""


def bbox_matches_group(bbox_mm: tuple[float, float], group: str) -> bool:
    rng = SIZE_GROUP_RANGES.get(group)
    if not rng:
        return False
    w, h = bbox_mm
    return rng["w_min"] <= w <= rng["w_max"] and rng["h_min"] <= h <= rng["h_max"]


# --- Library index ---------------------------------------------------------

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_index(project_root: Path) -> dict[str, Any]:
    path = project_root / DXF_LIBRARY_INDEX_RELATIVE
    if not path.exists():
        return {"version": 1, "updated_at": "", "entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"version": 1, "updated_at": "", "entries": {}}
        data.setdefault("entries", {})
        return data
    except json.JSONDecodeError:
        return {"version": 1, "updated_at": "", "entries": {}}


def _save_index(project_root: Path, index: dict[str, Any]) -> None:
    path = project_root / DXF_LIBRARY_INDEX_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _safe_relative(project_root: Path, target: Path) -> str:
    try:
        return str(target.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(target).replace("\\", "/")


def _make_entry(project_root: Path, file_path: Path, size_group: str, ascii_name: str, dxf_info: DxfReadResult, *, is_new: bool, prior_entry: dict[str, Any] | None = None) -> dict[str, Any]:
    mapping = load_ascii_to_turkish_map(project_root)
    friendly = mapping.get(ascii_name, "")
    # Letter count: count alphabetic chars in the friendly name (or ascii fallback)
    letters_source = friendly or ascii_name
    letter_count = sum(1 for ch in letters_source if ch.isalpha())
    is_compound = "_" in ascii_name or "&" in (friendly or "")
    bbox_in_range = bbox_matches_group(dxf_info.bbox_mm, size_group)
    bbox_warning = "" if bbox_in_range or not dxf_info.readable or dxf_info.bbox_mm == (0.0, 0.0) else (
        f"Bbox {dxf_info.bbox_mm[0]:.1f}×{dxf_info.bbox_mm[1]:.1f}mm '{size_group}' grup aralığına uymuyor"
    )
    now = _now_iso()
    return {
        "name": friendly or ascii_name,
        "ascii_name": ascii_name,
        "size_group": size_group,
        "file_path": _safe_relative(project_root, file_path),
        "bbox_mm": list(dxf_info.bbox_mm),
        "added_date": (prior_entry or {}).get("added_date") or now,
        "modified_date": now,
        "status": "active" if dxf_info.readable else "unreadable",
        "source": (prior_entry or {}).get("source") or "leyla_corel_manual",
        "is_compound": is_compound,
        "letter_count": letter_count,
        "readable": dxf_info.readable,
        "read_error": dxf_info.error,
        "entity_types": list(dxf_info.entity_types),
        "entity_count": dxf_info.entity_count,
        "has_spline": dxf_info.has_spline,
        "closed_paths": dxf_info.closed_paths_estimate,
        "insunits_code": dxf_info.insunits_code,
        "mm_per_unit": dxf_info.mm_per_unit,
        "bbox_warning": bbox_warning,
    }


def scan_library(project_root: Path) -> dict[str, Any]:
    """Walk assets/dxf_library/{70x40,80x40,100x40}/ and rebuild the index.

    Returns:
      {"status":"OK", "scanned": N, "added": N, "updated": N, "removed": N,
       "warnings": [...], "entries": {ascii_name: entry, ...}}
    """
    lib_root = project_root / DXF_LIBRARY_DIR_RELATIVE
    prior = _load_index(project_root)
    prior_entries = prior.get("entries") if isinstance(prior.get("entries"), dict) else {}
    new_entries: dict[str, Any] = {}
    added = 0
    updated = 0
    warnings: list[str] = []
    seen_keys: set[str] = set()

    for group in SIZE_GROUPS:
        group_dir = lib_root / group
        if not group_dir.exists():
            warnings.append(f"Klasör yok: {_safe_relative(project_root, group_dir)} (oluşturulmadı)")
            continue
        for dxf_path in sorted(group_dir.glob("*.dxf")):
            ascii_name = dxf_path.stem.lower()
            # Reject non-ASCII filenames (operator should have renamed before drop)
            if not re.fullmatch(r"[a-z0-9_]+", ascii_name):
                warnings.append(
                    f"{_safe_relative(project_root, dxf_path)}: dosya adı ASCII değil; küçük harf+rakam+alt çizgi olmalı (ör: 'mucahit.dxf')"
                )
                continue
            if ascii_name in seen_keys:
                warnings.append(
                    f"Yinelenen ASCII isim '{ascii_name}' — {_safe_relative(project_root, dxf_path)} ihmal edildi (önceki grupta zaten var)"
                )
                continue
            seen_keys.add(ascii_name)
            dxf_info = read_dxf_file(dxf_path)
            if not dxf_info.readable:
                warnings.append(
                    f"{_safe_relative(project_root, dxf_path)}: okunamıyor ({dxf_info.error})"
                )
            entry = _make_entry(
                project_root,
                dxf_path,
                size_group=group,
                ascii_name=ascii_name,
                dxf_info=dxf_info,
                is_new=(ascii_name not in prior_entries),
                prior_entry=prior_entries.get(ascii_name) if isinstance(prior_entries.get(ascii_name), dict) else None,
            )
            if entry.get("bbox_warning"):
                warnings.append(f"{_safe_relative(project_root, dxf_path)}: {entry['bbox_warning']}")
            if ascii_name in prior_entries:
                updated += 1
            else:
                added += 1
            new_entries[ascii_name] = entry

    removed = [k for k in prior_entries.keys() if k not in new_entries]
    index = {
        "version": 1,
        "updated_at": _now_iso(),
        "entries": new_entries,
    }
    _save_index(project_root, index)
    return {
        "status": "OK",
        "scanned": len(new_entries),
        "added": added,
        "updated": updated,
        "removed": len(removed),
        "removed_keys": removed,
        "warnings": warnings,
        "entries": new_entries,
    }


def list_library(project_root: Path) -> list[dict[str, Any]]:
    index = _load_index(project_root)
    entries = index.get("entries", {})
    if not isinstance(entries, dict):
        return []
    return sorted(entries.values(), key=lambda e: (e.get("size_group", ""), e.get("ascii_name", "")))


def search_library(project_root: Path, query: str) -> list[dict[str, Any]]:
    """Fuzzy-ish substring search across friendly name + ASCII name."""
    q_ascii = to_ascii_name(query)
    q_lower = (query or "").strip().lower()
    rows = list_library(project_root)
    if not q_ascii and not q_lower:
        return rows
    out = []
    for row in rows:
        a = row.get("ascii_name", "")
        n = (row.get("name") or "").lower()
        if (q_ascii and q_ascii in a) or (q_lower and q_lower in n):
            out.append(row)
    return out


def find_library_entry(project_root: Path, name_or_ascii: str) -> dict[str, Any] | None:
    """Exact lookup by friendly name or ASCII name."""
    key = to_ascii_name(name_or_ascii)
    if not key:
        return None
    index = _load_index(project_root)
    entries = index.get("entries", {})
    if not isinstance(entries, dict):
        return None
    return entries.get(key)


def library_summary(project_root: Path) -> dict[str, Any]:
    rows = list_library(project_root)
    per_group = {g: 0 for g in SIZE_GROUPS}
    unreadable = 0
    with_warnings = 0
    for row in rows:
        g = row.get("size_group", "")
        if g in per_group:
            per_group[g] += 1
        if not row.get("readable", True):
            unreadable += 1
        if row.get("bbox_warning"):
            with_warnings += 1
    return {
        "total": len(rows),
        "per_size_group": per_group,
        "unreadable": unreadable,
        "with_warnings": with_warnings,
        "ezdxf_available": EZDXF_AVAILABLE,
    }


# --- Order matching --------------------------------------------------------

def resolve_name_for_order(project_root: Path, requested_name: str) -> dict[str, Any]:
    """Look up a customer-facing name in the library.

    Returns:
      {"status": "FOUND"|"MISSING_DESIGN"|"UNREADABLE", "ascii_name": str,
       "friendly_name": str, "entry": entry|None, "message": str}

    'MISSING_DESIGN' tells the UI to surface "Leyla X ismini çizmeli" and
    block laser-ready flagging until the design lands.
    """
    requested = (requested_name or "").strip()
    if not requested:
        return {
            "status": "MISSING_DESIGN",
            "ascii_name": "",
            "friendly_name": "",
            "entry": None,
            "message": "İsim boş; eşleştirme yapılamadı.",
        }
    ascii_name = to_ascii_name(requested)
    entry = find_library_entry(project_root, ascii_name)
    if not entry:
        return {
            "status": "MISSING_DESIGN",
            "ascii_name": ascii_name,
            "friendly_name": requested,
            "entry": None,
            "message": f"'{requested}' DXF kütüphanesinde yok; Leyla çizmeli.",
        }
    if not entry.get("readable", True):
        return {
            "status": "UNREADABLE",
            "ascii_name": ascii_name,
            "friendly_name": entry.get("name") or requested,
            "entry": entry,
            "message": f"'{requested}' kütüphanede var ama DXF okunamıyor: {entry.get('read_error') or 'bilinmeyen hata'}",
        }
    return {
        "status": "FOUND",
        "ascii_name": ascii_name,
        "friendly_name": entry.get("name") or requested,
        "entry": entry,
        "message": f"'{requested}' kütüphanede bulundu ({entry.get('size_group')}).",
    }


# --- Public API surface (called by bridge / REST) -------------------------

def api_list(project_root: Path) -> dict[str, Any]:
    return {
        "status": "OK",
        "summary": library_summary(project_root),
        "entries": list_library(project_root),
    }


def api_search(project_root: Path, query: str) -> dict[str, Any]:
    rows = search_library(project_root, query or "")
    return {"status": "OK", "query": query or "", "count": len(rows), "entries": rows}


def api_find(project_root: Path, name: str) -> dict[str, Any]:
    entry = find_library_entry(project_root, name or "")
    if not entry:
        return {
            "status": "NOT_FOUND",
            "ascii_name": to_ascii_name(name or ""),
            "message": f"'{name}' kütüphanede yok.",
        }
    return {"status": "OK", "entry": entry}


def api_refresh(project_root: Path) -> dict[str, Any]:
    """Manual rescan endpoint — called from UI 'Kütüphaneyi Tara' button or
    from the simple file-system watcher in dxf_library_watcher.py."""
    result = scan_library(project_root)
    summary = library_summary(project_root)
    return {
        "status": "OK",
        "summary": summary,
        "scanned": result["scanned"],
        "added": result["added"],
        "updated": result["updated"],
        "removed": result["removed"],
        "removed_keys": result["removed_keys"],
        "warnings": result["warnings"],
    }


def api_resolve_for_order(project_root: Path, requested_name: str) -> dict[str, Any]:
    return {"status": "OK", "lookup": resolve_name_for_order(project_root, requested_name)}
