from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
import hashlib
import html
import json
import math
import re
import shutil
import struct
import unicodedata
import uuid
import zlib
from pathlib import Path
import site
import sys
from xml.etree import ElementTree as ET
from typing import Any

import pandas as pd
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

try:
    import uharfbuzz as hb
except Exception:  # pragma: no cover - optional OpenType shaping engine
    hb = None

try:
    import pyclipper
except Exception:  # pragma: no cover - optional production geometry engine
    pyclipper = None
    _project_root_for_optional_deps = Path(__file__).resolve().parents[2]
    _venv_site_candidates = [
        _project_root_for_optional_deps / ".venv" / "Lib" / "site-packages",
        *_project_root_for_optional_deps.glob(".venv/Lib/site-packages"),
    ]
    for _site_path in _venv_site_candidates:
        if _site_path.exists():
            site.addsitedir(str(_site_path))
            if str(_site_path) not in sys.path:
                sys.path.insert(0, str(_site_path))
    try:
        import pyclipper  # type: ignore[no-redef]
    except Exception:
        pyclipper = None

from webui_backend import bulk_label_api, file_api

try:
    from webui_backend.corel_reference_importer import (
        load_exact_reference_path_data as _load_exact_reference_path_data,
        path_geometry_metrics_from_svg_path as _corel_path_geometry_metrics,
        reference_name_key as _corel_reference_name_key,
        score_against_corpus as _score_against_corel_corpus,
    )
except Exception:  # pragma: no cover - reference corpus is a QA guardrail
    _load_exact_reference_path_data = None
    _corel_path_geometry_metrics = None
    _corel_reference_name_key = None
    _score_against_corel_corpus = None

# DXF library (Leyla's hand-prepared system, 2026-05-28). Primary source for
# new orders; falls back to the legacy SVG/AI reference library (operator-
# approved İrem/Ümit/Ahmet/Ayşe&Mehmet etc.) when not found.
try:
    from webui_backend import dxf_library_api as _dxf_library_api
    from webui_backend.dxf_library_api import DXF_LIBRARY_DIR_RELATIVE
except Exception:  # pragma: no cover
    _dxf_library_api = None
    DXF_LIBRARY_DIR_RELATIVE = "assets/dxf_library"


TRUE_VALUES = {"evet", "e", "yes", "y", "true", "1", "x", "var"}
FALSE_VALUES = {"hayir", "h", "no", "false", "0", "", "yok", "bos"}

RDWORKS_LAYER_COLORS = {
    "CUT_NAME_OUTLINE": {"color": "red", "dxf_color": 1, "purpose": "Ana kesim cizgisi"},
    "CUT_SUPPORT_LINE": {"color": "blue", "dxf_color": 5, "purpose": "Alt destek cizgisi"},
    "CUT_BACK_PLATE": {"color": "purple", "dxf_color": 6, "purpose": "Taban/plaka cizgisi"},
    "CALIBRATION": {"color": "green", "dxf_color": 3, "purpose": "Kalibrasyon / registration"},
    "GUIDE_PREVIEW": {"color": "gray", "dxf_color": 8, "purpose": "Kilavuz / preview"},
}
RDWORKS_CUT_LAYERS = {
    key: value
    for key, value in RDWORKS_LAYER_COLORS.items()
    if key in {"CUT_NAME_OUTLINE", "CUT_SUPPORT_LINE", "CUT_BACK_PLATE"}
}
REAL_NAMECUT_EXPORT_FORMATS = {"svg", "dxf", "pdf"}
PASSIVE_NAMECUT_EXPORT_FORMATS = {"plt"}
BLOCKING_QUALITY_STATUSES = {"needs_weld", "detached_marks", "collision_risk", "blocked"}

TURKISH_DIACRITIC_CHARS = set("iİıöÖüÜşŞçÇğĞ")
TURKISH_UPPER_MARK_CHARS = set("iİöÖüÜğĞ")
TURKISH_LOWER_MARK_CHARS = set("şŞçÇ")
TURKISH_DOT_MARK_CHARS = set("iİöÖüÜ")
TURKISH_TAIL_MARK_CHARS = set("şŞçÇ")
TURKISH_BREVE_MARK_CHARS = set("ğĞ")
DOTLESS_CHARS = set("ıISSMABCDEFHJKLNOPRTYZmnrvwxz")
AI_LASER_QUALITY_OFFSET_CANDIDATES = [0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.65]
AI_LASER_QUALITY_BRIDGE_CANDIDATES = [0.25, 0.35, 0.45, 0.60]
AI_LASER_QUALITY_PASS_SCORE = 85
RDWORKS_EXPORT_PRIORITY = ["DXF", "SVG", "PDF_PREVIEW", "PNG_PREVIEW", "JSON_MANIFEST"]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
COREL_REFERENCE_CORPUS_PATH = PROJECT_ROOT / "assets" / "references" / "corel_reference_corpus.json"
COREL_EXACT_REFERENCE_DIR = PROJECT_ROOT / "assets" / "references" / "name_cut_exact_golden"
COREL_EXACT_REFERENCE_SELECTION_PATH = COREL_EXACT_REFERENCE_DIR / "exact_reference_selection.json"
COREL_NAME_REFERENCE_LIBRARY_PATH = PROJECT_ROOT / "assets" / "references" / "corel_name_reference_library.json"
COREL_REFERENCE_BACKUP_DIR = PROJECT_ROOT / "assets" / "references" / "backups"
COREL_REFERENCE_AUDIT_LOG_PATH = PROJECT_ROOT / "assets" / "references" / "corel_reference_audit_log.jsonl"
MOCHARY_COREL_PRODUCTION_PROFILE_PATH = PROJECT_ROOT / "assets" / "references" / "mochary_corel_production_profile.json"
MOCHARY_INTERNAL_PRODUCTION_PROFILE_PATH = PROJECT_ROOT / "assets" / "references" / "mochary_internal_production_profile.json"
MOCHARY_VALID_GOLDEN_PRODUCTION_PROFILE_PATH = PROJECT_ROOT / "assets" / "references" / "mochary_valid_golden_production_profile.json"
GOLDEN_GLYPH_SHAPE_LIBRARY_PATH = PROJECT_ROOT / "assets" / "references" / "golden_glyph_shape_library.json"
MOCHARY_TR_CONNECT_FONT_CANDIDATES = [
    PROJECT_ROOT / "assets" / "fonts" / "MocharyTRConnect-Regular.otf",
    PROJECT_ROOT / "assets" / "fonts" / "MocharyTRConnect-Regular.ttf",
    PROJECT_ROOT.parent / "output" / "final" / "MocharyTRConnect-Regular.otf",
    PROJECT_ROOT.parent / "output" / "final" / "MocharyTRConnect-Regular.ttf",
]
MOCHARY_TR_CONNECT_REFINED_FONT_CANDIDATES = [
    PROJECT_ROOT / "assets" / "fonts" / "MocharyTRConnect-VisualRefined.otf",
    PROJECT_ROOT / "assets" / "fonts" / "MocharyTRConnect-VisualRefined.ttf",
    PROJECT_ROOT.parent / "output" / "refined" / "MocharyTRConnect-VisualRefined.otf",
    PROJECT_ROOT.parent / "output" / "refined" / "MocharyTRConnect-VisualRefined.ttf",
]
MOCHARY_TR_CONNECT_REFINED_V2_FONT_CANDIDATES = [
    PROJECT_ROOT / "assets" / "fonts" / "MocharyTRConnect-VisualRefinedV2.otf",
    PROJECT_ROOT / "assets" / "fonts" / "MocharyTRConnect-VisualRefinedV2.ttf",
    PROJECT_ROOT.parent / "output" / "refined_v2" / "MocharyTRConnect-VisualRefinedV2.otf",
    PROJECT_ROOT.parent / "output" / "refined_v2" / "MocharyTRConnect-VisualRefinedV2.ttf",
]
MOCHARY_FONT_CANDIDATES = [
    *MOCHARY_TR_CONNECT_FONT_CANDIDATES,
    PROJECT_ROOT / "assets" / "fonts" / "Mochary Personal Use Only.ttf",
    PROJECT_ROOT / "assets" / "fonts" / "Mochary-Personal-Use-Only.ttf",
    PROJECT_ROOT / "assets" / "fonts" / "Mochary.ttf",
    Path(r"C:\Users\Pc\AppData\Local\Temp\Mochary.ttf"),
    Path(r"C:\Windows\Fonts\Mochary Personal Use Only.ttf"),
    Path(r"C:\Windows\Fonts\Mochary-Personal-Use-Only.ttf"),
    Path(r"C:\Windows\Fonts\Mochary.ttf"),
]
MOCHARY_LIKE_FONT_CANDIDATES = [
    PROJECT_ROOT / "assets" / "fonts" / "mochary_like.ttf",
    PROJECT_ROOT / "assets" / "fonts" / "Mochary-Like.ttf",
    Path(r"C:\Windows\Fonts\Freehand521 BT.ttf"),
    Path(r"C:\Windows\Fonts\Gabriola.ttf"),
    Path(r"C:\Windows\Fonts\segoesc.ttf"),
]
BRANNBOLL_CONNECT_FONT_CANDIDATES = [
    PROJECT_ROOT / "assets" / "fonts" / "BrannbollConnect.ttf",
    PROJECT_ROOT / "assets" / "fonts" / "BrannbollConnect.otf",
    Path(r"C:\Users\Pc\AppData\Local\Temp\Brannboll_Ny_PersonalUseOnly.ttf"),
]
MOCHARY_TR_CONNECT_FONT_PATH = next((path for path in MOCHARY_TR_CONNECT_FONT_CANDIDATES if path.exists()), PROJECT_ROOT / "assets" / "fonts" / "__missing_mochary_tr_connect__.otf")
MOCHARY_TR_CONNECT_REFINED_FONT_PATH = next((path for path in MOCHARY_TR_CONNECT_REFINED_FONT_CANDIDATES if path.exists()), PROJECT_ROOT / "assets" / "fonts" / "__missing_mochary_tr_connect_visual_refined__.otf")
MOCHARY_TR_CONNECT_REFINED_V2_FONT_PATH = next((path for path in MOCHARY_TR_CONNECT_REFINED_V2_FONT_CANDIDATES if path.exists()), PROJECT_ROOT / "assets" / "fonts" / "__missing_mochary_tr_connect_visual_refined_v2__.otf")
BRANNBOLL_CONNECT_FONT_PATH = next((path for path in BRANNBOLL_CONNECT_FONT_CANDIDATES if path.exists()), PROJECT_ROOT / "assets" / "fonts" / "__missing_brannboll_connect__.ttf")
FONT_PATHS = {
    "brannboll_connect": BRANNBOLL_CONNECT_FONT_PATH,
    "mochary_tr_connect": MOCHARY_TR_CONNECT_FONT_PATH,
    "mochary_tr_connect_visual_refined": MOCHARY_TR_CONNECT_REFINED_FONT_PATH,
    "mochary_tr_connect_visual_refined_v2": MOCHARY_TR_CONNECT_REFINED_V2_FONT_PATH,
    "mochary": next((path for path in MOCHARY_FONT_CANDIDATES if path.exists()), Path(r"C:\Windows\Fonts\segoesc.ttf")),
    "mochary_like": next((path for path in MOCHARY_LIKE_FONT_CANDIDATES if path.exists()), Path(r"C:\Windows\Fonts\segoesc.ttf")),
    "script": Path(r"C:\Windows\Fonts\segoesc.ttf"),
    "script_bold": Path(r"C:\Windows\Fonts\segoescb.ttf"),
    "print": Path(r"C:\Windows\Fonts\segoepr.ttf"),
    "print_bold": Path(r"C:\Windows\Fonts\segoeprb.ttf"),
    "serif": Path(r"C:\Windows\Fonts\georgia.ttf"),
    "sans": Path(r"C:\Windows\Fonts\arial.ttf"),
}
FONT_REGISTRY_PATH = PROJECT_ROOT / "assets" / "fonts" / "font_registry.json"

HEADER_ALIASES = {
    "musteri_adi": "customer_name",
    "musteri": "customer_name",
    "isim": "customer_name",
    "ad_soyad": "customer_name",
    "etiket_yazisi": "customer_name",
    "label_text": "customer_name",
    "tarih": "date_text",
    "date": "date_text",
    "date_text": "date_text",
    "not": "note_text",
    "note": "note_text",
    "aciklama": "note_text",
    "mesaj": "note_text",
    "adet": "quantity",
    "quantity": "quantity",
    "qty": "quantity",
    "miktar": "quantity",
    "etiket_cikar": "label_required",
    "etiket_var": "label_required",
    "etiket": "label_required",
    "label_required": "label_required",
    "etiket_no": "label_model_no",
    "etiket_numarasi": "label_model_no",
    "model_no": "label_model_no",
    "model_numarasi": "label_model_no",
    "model_kodu": "label_model_no",
    "model": "label_model_no",
    "tasarim_no": "label_model_no",
    "etiket_adet": "label_quantity",
    "isim_kes": "name_cut_required",
    "isim_kesim": "name_cut_required",
    "lazer_isim": "name_cut_required",
    "name_cut_required": "name_cut_required",
    "isim_kesim_text": "name_cut_text",
    "name_cut_text": "name_cut_text",
    "isim_kesim_adet": "name_cut_quantity",
    "isim_kesim_olcu": "name_cut_size",
    "isim_genislik_mm": "name_cut_width_mm",
    "isim_yukseklik_mm": "name_cut_height_mm",
    "maksimum_genislik_mm": "name_cut_max_width_mm",
    "maksimum_yukseklik_mm": "name_cut_max_height_mm",
    "isim_font": "name_cut_font",
    "isim_stil": "name_cut_style",
    "kompozisyon": "composition_mode",
    "kalinlastirma": "thickening_mode",
    "kesim_kalinligi": "thickening_mode",
    "offset_mm": "offset_mm",
    "ozel_offset_mm": "offset_mm",
    "isim_destek": "support_line",
    "alt_destek": "support_line",
    "isim_plaka": "back_plate",
    "taban_plaka": "back_plate",
}

TURKISH_NAME_FIXES = {
    "ayse": "Ay\u015fe",
    "omer": "\u00d6mer",
    "cagatay": "\u00c7a\u011fatay",
    "cagla": "\u00c7a\u011fla",
    "cagri": "\u00c7a\u011fr\u0131",
    "tugce": "Tu\u011f\u00e7e",
    "gulsah": "G\u00fcl\u015fah",
    "sule": "\u015eule",
    "ozge": "\u00d6zge",
    "ozgur": "\u00d6zg\u00fcr",
    "ipek": "\u0130pek",
    "irem": "\u0130rem",
    "ilker": "\u0130lker",
    "ibrahim": "\u0130brahim",
    "ismail": "\u0130smail",
    "oguz": "O\u011fuz",
    "yagmur": "Ya\u011fmur",
    "bugra": "Bu\u011fra",
    "mucahit": "M\u00fccahit",
    "mujahit": "M\u00fccahit",
}

NAME_CUT_PRESETS = [
    {
        "id": "mochary_tr_connect",
        "name": "Mochary TR Connect",
        "font_family": "MocharyTRConnect-Regular",
        "fallback_font_family": "Mochary Personal Use Only",
        "script_connected": True,
        "safe_for_cutting": True,
        "min_height_mm": 40,
        "min_width_mm": 80,
        "turkish_support": "full",
        "dot_risk": False,
        "thin_stroke_warning": "Düşük",
        "recommended_material": "Pleksi / ayna pleksi",
        "support_line_recommended": False,
        "plate_recommended": False,
    },
    {
        "id": "mochary_tr_connect_visual_refined",
        "name": "Mochary TR Connect Visual Refined",
        "font_family": "MocharyTRConnectVisualRefined-Regular",
        "fallback_font_family": "Mochary TR Connect",
        "script_connected": True,
        "safe_for_cutting": True,
        "min_height_mm": 40,
        "min_width_mm": 80,
        "turkish_support": "full",
        "dot_risk": False,
        "thin_stroke_warning": "Düşük",
        "recommended_material": "Pleksi / ayna pleksi",
        "support_line_recommended": False,
        "plate_recommended": False,
    },
    {
        "id": "mochary_tr_connect_visual_refined_v2",
        "name": "Mochary TR Connect Visual Refined V2",
        "font_family": "MocharyTRConnectVisualRefinedV2-Regular",
        "fallback_font_family": "Mochary TR Connect Visual Refined",
        "script_connected": True,
        "safe_for_cutting": True,
        "min_height_mm": 40,
        "min_width_mm": 80,
        "turkish_support": "full",
        "dot_risk": False,
        "thin_stroke_warning": "Düşük",
        "recommended_material": "Pleksi / ayna pleksi",
        "support_line_recommended": False,
        "plate_recommended": False,
    },
    {
        "id": "mochary_personal",
        "name": "Mochary Personal Use Only",
        "font_family": "Mochary Personal Use Only",
        "fallback_font_family": "Segoe Script",
        "script_connected": True,
        "safe_for_cutting": True,
        "min_height_mm": 45,
        "min_width_mm": 100,
        "turkish_support": "partial",
        "dot_risk": True,
        "thin_stroke_warning": "Orta",
        "recommended_material": "Pleksi / ayna pleksi",
        "support_line_recommended": False,
        "plate_recommended": False,
    },
    {
        "id": "connected_romantic",
        "name": "BitiÅŸik Romantik Script",
        "font_family": "Great Vibes",
        "fallback_font_family": "Georgia",
        "script_connected": True,
        "safe_for_cutting": True,
        "min_height_mm": 45,
        "min_width_mm": 120,
        "turkish_support": "partial",
        "dot_risk": True,
        "thin_stroke_warning": "Orta",
        "recommended_material": "Pleksi / ayna pleksi",
        "support_line_recommended": False,
        "plate_recommended": False,
    },
    {
        "id": "engagement_script",
        "name": "SÃ¶z/NiÅŸan Script",
        "font_family": "Great Vibes",
        "fallback_font_family": "Georgia",
        "script_connected": True,
        "safe_for_cutting": True,
        "min_height_mm": 50,
        "min_width_mm": 150,
        "turkish_support": "partial",
        "dot_risk": True,
        "thin_stroke_warning": "Orta",
        "recommended_material": "Metalik pleksi",
        "support_line_recommended": True,
        "plate_recommended": False,
    },
    {
        "id": "thick_plexi",
        "name": "KalÄ±n BitiÅŸik Kesim",
        "font_family": "Segoe Script",
        "fallback_font_family": "Arial",
        "script_connected": True,
        "safe_for_cutting": True,
        "min_height_mm": 38,
        "min_width_mm": 120,
        "turkish_support": "partial",
        "dot_risk": True,
        "thin_stroke_warning": "DÃ¼ÅŸÃ¼k",
        "recommended_material": "AhÅŸap / pleksi",
        "support_line_recommended": True,
        "plate_recommended": False,
    },
    {
        "id": "thin_elegant",
        "name": "Ä°nce Zarif, uyarÄ±lÄ±",
        "font_family": "Great Vibes",
        "fallback_font_family": "Georgia",
        "script_connected": True,
        "safe_for_cutting": False,
        "min_height_mm": 60,
        "min_width_mm": 180,
        "turkish_support": "partial",
        "dot_risk": True,
        "thin_stroke_warning": "YÃ¼ksek",
        "recommended_material": "KalÄ±n malzeme Ã¶nerilir",
        "support_line_recommended": True,
        "plate_recommended": True,
    },
]


@dataclass
class LayoutConfig:
    width_mm: float = 800
    height_mm: float = 600
    target_name_width_mm: float = 80
    target_name_height_mm: float = 40
    target_gap_mm: float = 1
    margin_mm: float = 15
    item_gap_mm: float = 1
    row_gap_mm: float = 1
    joined_name_gap_mm: float = 1
    allow_rotation: bool = True
    mirror_cut: bool = False
    mirror_vertical: bool = False
    start_corner: str = "top-left"
    packing_direction: str = "left-to-right"
    row_direction: str = "top-to-bottom"
    dense_nesting: bool = True
    font_family: str = "Mochary.ttf"
    offset_mm: float = 0.3


THICKENING_OFFSETS = {
    "yok": 0.0,
    "hafif": 0.4,
    "orta": 0.8,
    "kalin": 1.2,
    "kalÄ±n": 1.2,
}


def combined_production_state(project_root: Path, excel_path: Path, label_models: list[dict[str, Any]]) -> dict[str, Any]:
    if not excel_path.exists():
        return _empty_state("Excel seÃ§ilmedi.")
    rows = _read_combined_rows(excel_path)
    if not rows:
        return _empty_state("Excel satÄ±rÄ± bulunamadÄ±.")
    model_index = _build_model_lookup(label_models)
    orders: list[dict[str, Any]] = []
    name_cut_items: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=2):
        order = _production_order_from_row(idx, row, model_index)
        orders.append(order)
        if order["name_cut_required"]:
            name_cut_items.append(_name_cut_item_from_order(order))
    label_row_numbers = {str(order["row_number"]) for order in orders if order["label_required"]}
    label_items = [
        item for item in bulk_label_api.bulk_gallery_items(project_root, excel_path, label_models)
        if str(item.get("row_number") or "") in label_row_numbers
    ]
    layout = layout_name_cut_items(name_cut_items)
    summary = {
        "total_rows": len(orders),
        "label_jobs": sum(1 for order in orders if order["label_required"]),
        "name_cut_jobs": sum(1 for order in orders if order["name_cut_required"]),
        "both_jobs": sum(1 for order in orders if order["label_required"] and order["name_cut_required"]),
        "no_production": sum(1 for order in orders if not order["label_required"] and not order["name_cut_required"]),
        "total_quantity": sum(max(1, _safe_int(order.get("quantity"), 1)) for order in orders),
        "name_cut_quantity": sum(max(1, _safe_int(item.get("quantity"), 1)) for item in name_cut_items if item.get("status") != "ERROR"),
        "label_errors": sum(1 for item in label_items if item.get("status") == "ERROR"),
        "name_cut_errors": sum(1 for item in name_cut_items if item.get("status") == "ERROR"),
    }
    return {
        "status": "OK",
        "message": "BirleÅŸik Ã¼retim Excel'i analiz edildi.",
        "excel_file": _relative(excel_path, project_root),
        "summary": summary,
        "orders": orders,
        "label_items": label_items,
        "name_cut_items": name_cut_items,
        "layout": layout,
        "presets": NAME_CUT_PRESETS,
    }


def export_name_cut_batch(project_root: Path, excel_path: Path, items: list[dict[str, Any]], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    live_items = [item for item in items if not item.get("is_deleted") and item.get("status") != "ERROR"]
    if not live_items:
        return {"status": "ERROR", "message": "Kesime hazÄ±r isim iÅŸi bulunamadÄ±."}
    requested_formats = [str(fmt or "").strip().lower() for fmt in list(config.get("formats") or ["svg", "dxf", "pdf"])]
    requested_formats = [fmt for fmt in requested_formats if fmt]
    real_formats = [fmt for fmt in requested_formats if fmt in REAL_NAMECUT_EXPORT_FORMATS]
    skipped_formats = [fmt for fmt in requested_formats if fmt in PASSIVE_NAMECUT_EXPORT_FORMATS or fmt not in REAL_NAMECUT_EXPORT_FORMATS]
    if not real_formats:
        return {
            "status": "ERROR",
            "message": "GerÃƒÂ§ek destekli export formatÃ„Â± seÃƒÂ§ilmedi. SVG, DXF veya PDF seÃƒÂ§in; PLT bu fazda pasif kalÃ„Â±r.",
            "skipped_formats": skipped_formats,
        }
    scene = build_name_cut_production_scene(live_items, config)
    layout = scene.get("layout") or layout_name_cut_items(live_items, _layout_config_from_payload(config))
    preflight = _name_cut_export_preflight(layout, live_items, config, real_formats, skipped_formats, scene)
    if preflight["blockers"] or (preflight["offset_warnings"] and not bool(config.get("operator_approved_offset_warning"))):
        return {
            "status": "ERROR",
            "message": "Ã„Â°sim Kesim export engellendi: " + " ".join(preflight["blockers"] or preflight["offset_warnings"]),
            "export_preflight": preflight,
            "skipped_formats": skipped_formats,
        }
    now = datetime.now()
    batch_id = str(config.get("export_batch_id") or f"NCE-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}")
    target_dir = project_root / "output" / now.strftime("%Y-%m-%d") / "namecut_exports" / batch_id
    target_dir.mkdir(parents=True, exist_ok=True)
    svg_path = target_dir / "plate_1.svg"
    dxf_path = target_dir / "plate_1.dxf"
    png_path = target_dir / "preview.png"
    pdf_path = target_dir / "plate_1.pdf"
    manifest_path = target_dir / "manifest.json"
    text_to_path_status = _text_to_path_status(layout)
    exported_files: dict[str, str] = {"manifest": _relative(manifest_path, project_root), "plt": ""}
    if "svg" in real_formats:
        svg_path.write_text(_svg_document(layout, scene), encoding="utf-8")
        exported_files["svg"] = _relative(svg_path, project_root)
    else:
        exported_files["svg"] = ""
    if "dxf" in real_formats:
        dxf_path.write_text(_dxf_document(layout, scene), encoding="utf-8")
        exported_files["dxf"] = _relative(dxf_path, project_root)
    else:
        exported_files["dxf"] = ""
    if "pdf" in real_formats:
        _write_preview_images(layout, png_path, pdf_path, scene)
        exported_files["pdf"] = _relative(pdf_path, project_root)
        exported_files["png"] = _relative(png_path, project_root)
    else:
        exported_files["pdf"] = ""
        exported_files["png"] = ""
    thickening_status = _thickening_status(layout["items"])
    rdworks_qa = _rdworks_compatibility_qa(layout, exported_files, project_root)
    manifest = {
        "batch_id": batch_id,
        "export_batch_id": batch_id,
        "created_at": now.isoformat(timespec="seconds"),
        "operator": str(config.get("operator") or ""),
        "excel_file": _relative(excel_path, project_root) if excel_path.exists() else "",
        "source_records": [
            {
                "item_id": str(item.get("item_id") or item.get("id") or ""),
                "queue_item_id": str(item.get("id") or item.get("item_id") or ""),
                "source": str(item.get("source") or ""),
                "source_label": str(item.get("source_label") or ""),
                "bulk_row_id": str(item.get("bulk_row_id") or ""),
                "name_text": str(item.get("name_text") or item.get("laser_name") or ""),
                "quantity": str(item.get("quantity") or "1"),
            }
            for item in live_items
        ],
        "queue_item_ids": [str(item.get("id") or item.get("item_id") or "") for item in live_items if str(item.get("id") or item.get("item_id") or "").strip()],
        "table_width_mm": layout["config"]["width_mm"],
        "table_height_mm": layout["config"]["height_mm"],
        "work_area_width_mm": layout["config"]["width_mm"],
        "work_area_height_mm": layout["config"]["height_mm"],
        "plate_size_mm": {"width": layout["config"]["width_mm"], "height": layout["config"]["height_mm"]},
        "unit": "mm",
        "plate_size": {"width_mm": layout["config"]["width_mm"], "height_mm": layout["config"]["height_mm"]},
        "plate_count": layout["summary"]["pages"],
        "target_name_width_mm": layout["config"].get("target_name_width_mm", 80),
        "target_name_height_mm": layout["config"].get("target_name_height_mm", 40),
        "target_gap_mm": layout["config"].get("target_gap_mm", layout["config"]["item_gap_mm"]),
        "margin_mm": layout["config"]["margin_mm"],
        "safe_margin_mm": layout["config"]["margin_mm"],
        "spacing_x_mm": layout["config"]["item_gap_mm"],
        "spacing_y_mm": layout["config"]["row_gap_mm"],
        "joined_name_gap_mm": layout["config"].get("joined_name_gap_mm", 3),
        "mirror_cut": layout["config"].get("mirror_cut", False),
        "mirror_horizontal": bool(config.get("mirror_cut") or layout["config"].get("mirror_cut", False)),
        "mirror_vertical": bool(config.get("mirror_vertical", False)),
        "cut_direction": str((config or {}).get("cut_direction") or ("Ters/Ayna" if (config or {}).get("mirror_cut") and (config or {}).get("mirror_vertical") else "Ayna Yatay" if (config or {}).get("mirror_cut") else "Ayna Dikey" if (config or {}).get("mirror_vertical") else "DÃ¼z")),
        "min_gap_mm": layout["summary"].get("min_safe_gap_mm", layout["config"]["item_gap_mm"]),
        "offset_mm": config.get("offset_mm", ""),
        "font": config.get("font_family", ""),
        "font_style": config.get("font_family", ""),
        "total_source_items": len(live_items),
        "total_names": layout["summary"].get("total_names", len(live_items)),
        "total_items": layout["summary"].get("total_names", len(live_items)),
        "total_quantity": layout["summary"].get("total_copies", sum(max(1, _safe_int(item.get("quantity"), 1)) for item in live_items)),
        "used_area_percent": layout["summary"]["used_area_percent"],
        "waste_area_percent": layout["summary"]["waste_percent"],
        "pages": layout["summary"]["pages"],
        "placement_strategy": layout["summary"].get("placement_strategy", ""),
        "actual_path_layout": True,
        "dense_nesting": bool(layout["summary"].get("dense_nesting", False)),
        "collision_free": layout["summary"].get("collision_free", False),
        "within_work_area": layout["summary"].get("within_work_area", False),
        "min_safe_gap_mm": layout["summary"].get("min_safe_gap_mm", layout["config"]["item_gap_mm"]),
        "inter_name_connection_forbidden": True,
        "internal_weld_scope": "SINGLE_NAME_ONLY",
        "page_stats": layout["summary"].get("page_stats", []),
        "layout": layout["summary"],
        "primary_rdworks_export": _relative(dxf_path, project_root),
        "secondary_svg_export": _relative(svg_path, project_root),
        "export_priority": RDWORKS_EXPORT_PRIORITY,
        "layer_color_standard": RDWORKS_CUT_LAYERS,
        "rdworks_layer_contract": {
            "CUT_NAME_OUTLINE": "Ana isim kesim cizgisi / kirmizi",
            "CUT_SUPPORT_LINE": "Alt destek cizgisi / mavi",
            "CUT_BACK_PLATE": "Taban veya plaka cizgisi / mor",
        },
        "manual_control_required": True,
        "machine_automation": {
            "rdworks_auto_open": False,
            "laser_auto_start": False,
            "direct_print": False,
            "speed_power_exported": False,
        },
        "quality_summary": preflight["quality_summary"],
        "single_piece_quality": preflight["single_piece_quality"],
        "weld_status": preflight["weld_status"],
        "detached_marks_status": preflight["detached_marks_status"],
        "collision_check": preflight["collision_check"],
        "requested_formats": requested_formats,
        "skipped_formats": skipped_formats,
        "file_list": exported_files,
        "exported_files": exported_files,
        "rdworks_compatibility_qa": rdworks_qa,
        "status": "OK",
        "manual_rdworks_checklist": [
            "DXF dosyasini RDWorks'te manuel acin.",
            "Layer renklerini ve kesim modlarini RDWorks icinde kontrol edin.",
            "Path/curve durumunu, olculeri ve offset/kalinlastirma sonucunu onizleyin.",
            "Lazer kesimini sadece kullanici manuel baslatir.",
        ],
        "ai_export_status": "NOT_SUPPORTED_THIS_PHASE",
        "plt_export_status": "NOT_SUPPORTED_THIS_PHASE",
        "exported_svg": exported_files.get("svg", ""),
        "exported_dxf": exported_files.get("dxf", ""),
        "svg_path": exported_files.get("svg", ""),
        "dxf_path": exported_files.get("dxf", ""),
        "pdf_preview": exported_files.get("pdf", ""),
        "png_preview": exported_files.get("png", ""),
        "rdworks_primary_note": "DXF birincil RDWorks dosyasidir. RDWorks otomatik acilmaz. DXF'i RDWorks'te manuel acip layer/path/font/offset kontrolu yapin.",
        "rdworks_note": "RDWorks otomatik a\u00e7\u0131lmaz. SVG/DXF dosyas\u0131n\u0131 RDWorks'te manuel a\u00e7\u0131p path/font kontrol\u00fc yap\u0131n.",
        "text_to_path_status": text_to_path_status,
        "text_to_outline_status": text_to_path_status,
        "script_engine": {
            "name": "Ceyizhome Lab Script Engine",
            "preview_mode": "SVG outline preview / fontTools export path",
            "export_mode": "fontTools outline/path",
            "weld_scope": "inside_each_name_only",
            "keep_names_separate": True,
            "capital_fix": "manual bridge for missing S/L/M variants",
            "punctuation_fix": "TRY fallback path when font glyph is missing",
        },
        "thickening_status": thickening_status,
        "items": [_manifest_item(item) for item in layout["items"]],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "OK",
        "message": "Ä°sim kesim dosyalarÄ± RDWorks iÃ§in hazÄ±rlandÄ±. RDWorks ve lazer otomatik aÃ§Ä±lmadÄ±.",
        "svg_path": exported_files.get("svg", ""),
        "dxf_path": exported_files.get("dxf", ""),
        "pdf_preview": exported_files.get("pdf", ""),
        "png_preview": exported_files.get("png", ""),
        "manifest_path": _relative(manifest_path, project_root),
        "export_batch_id": batch_id,
        "created_at": now.isoformat(timespec="seconds"),
        "primary_export_path": exported_files.get("dxf") or exported_files.get("svg") or exported_files.get("pdf", ""),
        "export_priority": RDWORKS_EXPORT_PRIORITY,
        "layout": layout,
        "text_to_path_status": text_to_path_status,
        "text_to_outline_status": text_to_path_status,
        "thickening_status": thickening_status,
        "export_preflight": preflight,
        "rdworks_compatibility_qa": rdworks_qa,
        "skipped_formats": skipped_formats,
    }



def _estimated_path_metrics_for_layout(item: dict[str, Any], cfg: LayoutConfig) -> dict[str, float]:
    text = str(item.get("preview_text") or item.get("name_text") or item.get("text") or item.get("name") or "")
    target_width = float(cfg.target_name_width_mm or 80)
    target_height = float(cfg.target_name_height_mm or 40)
    requested_width = _safe_optional_float(item.get("width_mm")) or 0.0
    requested_height = _safe_optional_float(item.get("height_mm")) or 0.0
    locked = bool(item.get("operator_size_locked"))
    offset_mm = max(0.0, min(5.0, float(item.get("offset_mm") or cfg.offset_mm or 0)))
    style = item.get("style") or item.get("font_family") or cfg.font_family or "Mochary.ttf"
    font_path = _font_path_for_style(style)
    source_w = 1.0
    source_h = 1.0
    if font_path.exists() and text.strip():
        try:
            _contours, bbox, _units = _raw_text_contours(
                text,
                str(font_path),
                _script_connection_mode_for_style(style),
                _golden_letter_spacing_scale(item, cfg),
                _golden_kerning_adjustment(item, cfg),
                _golden_pair_kerning_signature(item, cfg),
                _golden_glyph_scale_signature(item, cfg),
            )
            min_x, min_y, max_x, max_y = bbox
            source_w = max(1.0, max_x - min_x)
            source_h = max(1.0, max_y - min_y)
        except Exception:
            source_w = max(1.0, len(text.strip()) * 760.0)
            source_h = 1000.0
    else:
        source_w = max(1.0, len(text.strip()) * 760.0)
        source_h = 1000.0
    box_height = requested_height if locked and requested_height > 0 else target_height
    preferred_draw_h = max(18.0, box_height * 0.94)
    target_draw_h = max(8.0, target_height - (offset_mm * 2))
    max_board_width = cfg.width_mm - (cfg.margin_mm * 2)
    max_readable_width = min(max_board_width, target_width * 1.25, 100.0)
    target_draw_w = max(8.0, (max_readable_width if cfg.dense_nesting else target_width) - (offset_mm * 2))
    draw_scale = min(preferred_draw_h / max(1.0, source_h), target_draw_w / max(1.0, source_w), target_draw_h / max(1.0, source_h))
    min_readable_draw_h = 20.0
    readable_scale = min_readable_draw_h / max(1.0, source_h)
    if (source_w * readable_scale) + (offset_mm * 2) <= max_readable_width:
        draw_scale = max(draw_scale, readable_scale)
    draw_h = source_h * draw_scale
    natural_draw_w = source_w * draw_scale
    min_width = max(22.0, min(target_width * 0.42, 38.0))
    max_width = max_board_width
    if locked and requested_width > 0:
        placement_width = requested_width
        placement_height = requested_height or box_height
        scale = min((placement_width * 0.94) / source_w, (placement_height * 0.86) / source_h)
        actual_width = (source_w * scale) + (offset_mm * 2)
        actual_height = (source_h * scale) + (offset_mm * 2)
    elif not cfg.dense_nesting:
        placement_width = target_width
        placement_height = target_height
        scale = min((placement_width * 0.94) / source_w, (placement_height * 0.86) / source_h)
        actual_width = (source_w * scale) + (offset_mm * 2)
        actual_height = (source_h * scale) + (offset_mm * 2)
    else:
        actual_width = natural_draw_w + (offset_mm * 2)
        actual_height = draw_h + (offset_mm * 2)
        placement_width = max(min_width, min(target_width, max_width, actual_width + 2.0))
        placement_height = max(target_height, actual_height + 2.0)
        scale = draw_scale
    placement_width = round(max(20.0, min(max_width, placement_width)), 2)
    placement_height = round(max(10.0, min(cfg.height_mm - (cfg.margin_mm * 2), placement_height)), 2)
    actual_width = round(max(1.0, min(max_width, actual_width * _golden_width_scale(item, cfg))), 2)
    actual_height = round(max(1.0, min(cfg.height_mm - (cfg.margin_mm * 2), actual_height * _golden_height_scale(item, cfg))), 2)
    return {
        "actual_path_width_mm": actual_width,
        "actual_path_height_mm": actual_height,
        "raw_path_width_mm": round(source_w, 2),
        "raw_path_height_mm": round(source_h, 2),
        "placement_width_mm": placement_width,
        "placement_height_mm": placement_height,
        "path_scale": round(scale, 5),
    }


def _with_actual_path_metrics(item: dict[str, Any], cfg: LayoutConfig) -> dict[str, Any]:
    metrics = _estimated_path_metrics_for_layout(item, cfg)
    frontend_width = _safe_optional_float(item.get("actual_path_width_mm"))
    frontend_height = _safe_optional_float(item.get("actual_path_height_mm"))
    warnings = list(item.get("warnings") or [])
    if item.get("layout_signature") and frontend_width and frontend_height:
        width_delta = abs(frontend_width - float(metrics["actual_path_width_mm"]))
        height_delta = abs(frontend_height - float(metrics["actual_path_height_mm"]))
        if width_delta > 8.0 or height_delta > 5.0:
            warnings.append("layout_mismatch: modal önizleme ölçüsü export path ölçüsüyle yeniden doğrulanmalı.")
        warnings.append("frontend_actual_path_ignored: üretim sahnesi FontTools bbox değerini kaynak aldı.")
    if item.get("operator_size_locked"):
        width = _safe_optional_float(item.get("width_mm")) or metrics["actual_path_width_mm"]
        height = _safe_optional_float(item.get("height_mm")) or metrics["actual_path_height_mm"]
    else:
        width = metrics.get("placement_width_mm") or metrics["actual_path_width_mm"]
        height = metrics.get("placement_height_mm") or metrics["actual_path_height_mm"]
    return {
        **item,
        **metrics,
        "width_mm": round(max(20.0, width), 2),
        "height_mm": round(max(10.0, height), 2),
        "warnings": warnings,
    }


def _dense_order(items: list[dict[str, Any]], cfg: LayoutConfig) -> list[dict[str, Any]]:
    # Preserve operator/source order. Area sorting packed a little tighter, but made
    # multi-name jobs look like one flowing sentence instead of independent objects.
    return items


def _dense_rotation_for_item(item: dict[str, Any], cfg: LayoutConfig, cursor_x: float, row_height: float, width: float, height: float) -> float:
    if not cfg.allow_rotation or item.get("operator_size_locked") or item.get("operator_position_locked"):
        return float(item.get("rotation") or 0)
    right_margin = cfg.width_mm - cfg.margin_mm
    fits_normal = cursor_x + width <= right_margin + 0.01
    fits_rotated = cursor_x + height <= right_margin + 0.01
    if not fits_normal and fits_rotated and height < width:
        return 180.0
    if row_height > 0 and height > row_height * 1.24 and width <= row_height * 1.18 and fits_rotated:
        return 180.0
    return float(item.get("rotation") or 0)


def _cut_direction_label(cfg: LayoutConfig | dict[str, Any]) -> str:
    if isinstance(cfg, dict):
        horizontal = bool(cfg.get("mirror_cut"))
        vertical = bool(cfg.get("mirror_vertical"))
    else:
        horizontal = bool(cfg.mirror_cut)
        vertical = bool(getattr(cfg, "mirror_vertical", False))
    if horizontal and vertical:
        return "Ters/Ayna"
    if horizontal:
        return "Ayna Yatay"
    if vertical:
        return "Ayna Dikey"
    return "DÃ¼z"


def _layout_item_has_collision(target: dict[str, Any], items: list[dict[str, Any]], gap_mm: float) -> bool:
    tolerance = 0.12
    target_id = str(target.get("item_id") or target.get("id") or target.get("source_item_id") or "")
    target_copy = int(target.get("copy_index") or 1)
    for other in items:
        if other is target:
            continue
        other_id = str(other.get("item_id") or other.get("id") or other.get("source_item_id") or "")
        other_copy = int(other.get("copy_index") or 1)
        if target_id and other_id and target_id == other_id and target_copy == other_copy:
            continue
        if int(target.get("page") or 1) != int(other.get("page") or 1):
            continue
        separated = (
            float(target.get("x_mm") or 0) + float(target.get("width_mm") or 0) + gap_mm <= float(other.get("x_mm") or 0) + tolerance
            or float(other.get("x_mm") or 0) + float(other.get("width_mm") or 0) + gap_mm <= float(target.get("x_mm") or 0) + tolerance
            or float(target.get("y_mm") or 0) + float(target.get("height_mm") or 0) + gap_mm <= float(other.get("y_mm") or 0) + tolerance
            or float(other.get("y_mm") or 0) + float(other.get("height_mm") or 0) + gap_mm <= float(target.get("y_mm") or 0) + tolerance
        )
        if not separated:
            return True
    return False


def _layout_item_inside_safe_margin(item: dict[str, Any], cfg: LayoutConfig) -> bool:
    return (
        float(item.get("x_mm") or 0) >= cfg.margin_mm - 0.01
        and float(item.get("y_mm") or 0) >= cfg.margin_mm - 0.01
        and float(item.get("x_mm") or 0) + float(item.get("width_mm") or 0) <= cfg.width_mm - cfg.margin_mm + 0.01
        and float(item.get("y_mm") or 0) + float(item.get("height_mm") or 0) <= cfg.height_mm - cfg.margin_mm + 0.01
    )


def _with_laser_name_object_model(item: dict[str, Any], items: list[dict[str, Any]], cfg: LayoutConfig) -> dict[str, Any]:
    warnings = item.get("warnings") if isinstance(item.get("warnings"), list) else []
    errors = item.get("errors") if isinstance(item.get("errors"), list) else []
    has_collision = _layout_item_has_collision(item, items, float(cfg.item_gap_mm or 0))
    inside_safe = _layout_item_inside_safe_margin(item, cfg)
    warning_text = " ".join(str(message) for message in warnings).lower()
    repair_status = str(item.get("repairStatus") or item.get("repair_status") or "").strip()
    connected_path = bool(item.get("isConnectedPath") if "isConnectedPath" in item else item.get("is_connected_path")) if repair_status else not errors and not any(token in warning_text for token in ["weld", "kopuk", "nokta", "iÅŸaret", "harf"])
    valid_size = float(item.get("width_mm") or 0) > 0 and float(item.get("height_mm") or 0) > 0
    repair_ready = item.get("readyForCut") if "readyForCut" in item else item.get("ready_for_cut", True)
    model = {
        "id": str(item.get("item_id") or item.get("id") or item.get("source_item_id") or ""),
        "name": str(item.get("name_text") or item.get("preview_text") or item.get("text") or item.get("name") or ""),
        "xMm": round(float(item.get("x_mm") or 0), 2),
        "yMm": round(float(item.get("y_mm") or 0), 2),
        "widthMm": round(float(item.get("width_mm") or 0), 2),
        "heightMm": round(float(item.get("height_mm") or 0), 2),
        "actualPathWidthMm": round(float(item.get("actual_path_width_mm") or item.get("width_mm") or 0), 2),
        "actualPathHeightMm": round(float(item.get("actual_path_height_mm") or item.get("height_mm") or 0), 2),
        "rotation": round(float(item.get("rotation") or 0), 2),
        "mirrored": bool(item.get("mirrored")),
        "direction": item.get("direction") or _cut_direction_label(cfg),
        "scale": float(item.get("path_scale") or item.get("scale") or 1),
        "selected": bool(item.get("selected")),
        "lockedAspectRatio": item.get("locked_aspect_ratio") is not False,
        "isConnectedPath": connected_path,
        "componentCount": int(item.get("componentCount") or item.get("component_count") or (1 if connected_path else 0)),
        "detachedParts": item.get("detachedParts") or item.get("detached_parts") or [],
        "hasDetachedDots": bool(item.get("hasDetachedDots") or item.get("has_detached_dots")),
        "hasDisconnectedLetters": bool(item.get("hasDisconnectedLetters") or item.get("has_disconnected_letters")),
        "hasCollision": has_collision,
        "isInsideSafeMargin": inside_safe,
        "minGapMm": float(cfg.item_gap_mm or 0),
        "appliedKerningFix": bool(item.get("appliedKerningFix") or item.get("applied_kerning_fix")),
        "appliedOffsetMm": float(item.get("appliedOffsetMm") or item.get("applied_offset_mm") or item.get("offset_mm") or 0),
        "appliedWeld": bool(item.get("appliedWeld") or item.get("applied_weld")),
        "appliedSmartBridge": bool(item.get("appliedSmartBridge") or item.get("applied_smart_bridge")),
        "appliedDotBridge": bool(item.get("appliedDotBridge") or item.get("applied_dot_bridge")),
        "componentCountBeforeRepair": int(item.get("componentCountBeforeRepair") or item.get("component_count_before_repair") or item.get("componentCount") or item.get("component_count") or (1 if connected_path else 0)),
        "componentCountAfterRepair": int(item.get("componentCountAfterRepair") or item.get("component_count_after_repair") or item.get("componentCount") or item.get("component_count") or (1 if connected_path else 0)),
        "detachedPartCount": int(item.get("detachedPartCount") or item.get("detached_part_count") or 0),
        "bridgedPartCount": int(item.get("bridgedPartCount") or item.get("bridged_part_count") or 0),
        "unresolvedPartCount": int(item.get("unresolvedPartCount") or item.get("unresolved_part_count") or 0),
        "autoRepaired": bool(item.get("autoRepaired") or item.get("auto_repaired")),
        "repairStatus": repair_status or ("clean" if connected_path else "failed"),
        "repairMessages": item.get("repairMessages") or item.get("repair_messages") or [],
        "offsetMode": item.get("offsetMode") or item.get("offset_mode") or "",
        "readyForCut": bool(repair_ready) and connected_path and not has_collision and inside_safe and valid_size,
        "warnings": warnings,
        "errors": errors,
        "validationMode": item.get("validationMode") or item.get("validation_mode") or "AUTO_REPAIR_PIPELINE_FONTTOOLS_EXPORT_PATH",
    }
    return {
        **item,
        "laser_name_object": model,
        "id": item.get("id") or model["id"],
        "name": model["name"],
        "xMm": model["xMm"],
        "yMm": model["yMm"],
        "widthMm": model["widthMm"],
        "heightMm": model["heightMm"],
        "actualPathWidthMm": model["actualPathWidthMm"],
        "actualPathHeightMm": model["actualPathHeightMm"],
        "scale": model["scale"],
        "selected": model["selected"],
        "lockedAspectRatio": model["lockedAspectRatio"],
        "isConnectedPath": model["isConnectedPath"],
        "componentCount": model["componentCount"],
        "component_count": model["componentCount"],
        "detachedParts": model["detachedParts"],
        "detached_parts": model["detachedParts"],
        "hasDetachedDots": model["hasDetachedDots"],
        "has_detached_dots": model["hasDetachedDots"],
        "hasDisconnectedLetters": model["hasDisconnectedLetters"],
        "has_disconnected_letters": model["hasDisconnectedLetters"],
        "appliedKerningFix": model["appliedKerningFix"],
        "applied_kerning_fix": model["appliedKerningFix"],
        "appliedOffsetMm": model["appliedOffsetMm"],
        "applied_offset_mm": model["appliedOffsetMm"],
        "appliedWeld": model["appliedWeld"],
        "applied_weld": model["appliedWeld"],
        "appliedSmartBridge": model["appliedSmartBridge"],
        "applied_smart_bridge": model["appliedSmartBridge"],
        "appliedDotBridge": model["appliedDotBridge"],
        "applied_dot_bridge": model["appliedDotBridge"],
        "componentCountBeforeRepair": model["componentCountBeforeRepair"],
        "component_count_before_repair": model["componentCountBeforeRepair"],
        "componentCountAfterRepair": model["componentCountAfterRepair"],
        "component_count_after_repair": model["componentCountAfterRepair"],
        "detachedPartCount": model["detachedPartCount"],
        "detached_part_count": model["detachedPartCount"],
        "bridgedPartCount": model["bridgedPartCount"],
        "bridged_part_count": model["bridgedPartCount"],
        "unresolvedPartCount": model["unresolvedPartCount"],
        "unresolved_part_count": model["unresolvedPartCount"],
        "autoRepaired": model["autoRepaired"],
        "auto_repaired": model["autoRepaired"],
        "repairStatus": model["repairStatus"],
        "repair_status": model["repairStatus"],
        "repairMessages": model["repairMessages"],
        "repair_messages": model["repairMessages"],
        "offsetMode": model["offsetMode"],
        "offset_mode": model["offsetMode"],
        "hasCollision": model["hasCollision"],
        "isInsideSafeMargin": model["isInsideSafeMargin"],
        "readyForCut": model["readyForCut"],
    }


def layout_name_cut_items(items: list[dict[str, Any]], config: LayoutConfig | None = None) -> dict[str, Any]:
    cfg = config or LayoutConfig()
    layout_units = [_with_actual_path_metrics(item, cfg) for item in _expand_joined_name_items(items, cfg)]
    expanded: list[dict[str, Any]] = []
    for item in layout_units:
        quantity = max(1, _safe_int(item.get("quantity"), 1))
        for copy_index in range(quantity):
            expanded.append({**item, "copy_index": copy_index + 1})
    placed: list[dict[str, Any]] = []
    unplaced: list[dict[str, Any]] = []
    left_margin = cfg.margin_mm
    right_margin = cfg.width_mm - cfg.margin_mm
    top_margin = cfg.margin_mm
    bottom_margin = cfg.height_mm - cfg.margin_mm
    usable_width = right_margin - left_margin
    usable_height = bottom_margin - top_margin
    pages = 1
    cursor_x = left_margin
    cursor_y = top_margin
    row_height = 0.0
    ordered = _dense_order(expanded, cfg)

    for item in ordered:
        actual_width = float(item.get("actual_path_width_mm") or item.get("width_mm") or cfg.target_name_width_mm)
        actual_height = float(item.get("actual_path_height_mm") or item.get("height_mm") or cfg.target_name_height_mm)
        width = max(8.0, actual_width)
        height = max(8.0, actual_height)
        if not item.get("operator_size_locked") and not cfg.dense_nesting:
            width = max(float(cfg.target_name_width_mm), width)
            height = max(float(cfg.target_name_height_mm), height)
        rotation = _dense_rotation_for_item(item, cfg, cursor_x, row_height, width, height)
        rotated_for_nesting = abs(float(rotation or 0)) % 180 == 90 and not float(item.get("rotation") or 0)
        if rotated_for_nesting:
            width, height = height, width
        if width > usable_width or height > usable_height:
            unplaced.append({**item, "not_placed_reason": "Tabla alanÄ±na sÄ±ÄŸmÄ±yor", "width_mm": round(width, 2), "height_mm": round(height, 2)})
            continue
        if item.get("operator_position_locked") and _safe_optional_float(item.get("x_mm")) is not None and _safe_optional_float(item.get("y_mm")) is not None:
            placed.append({
                **item,
                "page": int(item.get("page") or 1),
                "x_mm": round(float(item.get("x_mm") or 0), 2),
                "y_mm": round(float(item.get("y_mm") or 0), 2),
                "width_mm": round(width, 2),
                "height_mm": round(height, 2),
                "actual_path_width_mm": round(float(item.get("actual_path_width_mm") or width), 2),
                "actual_path_height_mm": round(float(item.get("actual_path_height_mm") or height), 2),
                "rotation": round(float(item.get("rotation") or 0), 2),
                "mirrored": bool(cfg.mirror_cut),
                "direction": _cut_direction_label(cfg),
                "separate_cut_object": True,
                "no_inter_name_bridge": True,
            })
            continue
        if cursor_x + width > right_margin + 0.01:
            cursor_x = left_margin
            row_step = row_height if cfg.dense_nesting else max(row_height, cfg.target_name_height_mm)
            cursor_y += max(row_step, 10.0) + cfg.row_gap_mm
            row_height = 0.0
        if cursor_y + height > bottom_margin + 0.01:
            pages += 1
            cursor_x = left_margin
            cursor_y = top_margin
            row_height = 0.0
        placed.append({
            **item,
            "page": pages,
            "x_mm": round(cursor_x, 2),
            "y_mm": round(cursor_y, 2),
            "width_mm": round(width, 2),
            "height_mm": round(height, 2),
            "actual_path_width_mm": round(float(item.get("actual_path_width_mm") or width), 2),
            "actual_path_height_mm": round(float(item.get("actual_path_height_mm") or height), 2),
            "rotation": round(float(rotation or 0), 2),
            "rotated_for_nesting": rotated_for_nesting,
            "mirrored": bool(cfg.mirror_cut),
            "direction": _cut_direction_label(cfg),
            "separate_cut_object": True,
            "no_inter_name_bridge": True,
        })
        item_gap = max(0.0, float(item.get("joined_name_gap_mm") or cfg.item_gap_mm))
        cursor_x += width + item_gap
        row_height = max(row_height, height)

    pages = max([1, *[int(item.get("page", 1)) for item in placed]])

    used_area = sum(float(item.get("actual_path_width_mm") or item["width_mm"]) * float(item.get("actual_path_height_mm") or item["height_mm"]) for item in placed)
    actual_used_area = used_area
    total_area = cfg.width_mm * cfg.height_mm * max(1, pages)
    page_stats = []
    for page in range(1, pages + 1):
        page_items = [item for item in placed if int(item.get("page", 1)) == page]
        page_used = sum(float(item.get("actual_path_width_mm") or item["width_mm"]) * float(item.get("actual_path_height_mm") or item["height_mm"]) for item in page_items)
        page_actual_used = page_used
        page_stats.append(
            {
                "page": page,
                "items": len(page_items),
                "used_area_percent": round((page_used / (cfg.width_mm * cfg.height_mm)) * 100, 1) if cfg.width_mm and cfg.height_mm else 0,
                "actual_path_used_area_percent": round((page_actual_used / (cfg.width_mm * cfg.height_mm)) * 100, 1) if cfg.width_mm and cfg.height_mm else 0,
                "waste_percent": round(100 - ((page_used / (cfg.width_mm * cfg.height_mm)) * 100), 1) if cfg.width_mm and cfg.height_mm else 0,
            }
        )
    modeled_placed = [_with_laser_name_object_model(item, placed, cfg) for item in placed]
    return {
        "config": cfg.__dict__,
        "items": modeled_placed,
        "summary": {
            "total_source_items": len(items),
            "total_names": len(layout_units),
            "total_copies": len(expanded),
            "pages": pages,
            "placement_strategy": "ACTUAL_PATH_DENSE_SHELF" if cfg.dense_nesting else "LOGICAL_MM_LEFT_TO_RIGHT_ROWS",
            "used_area_percent": round((used_area / total_area) * 100, 1) if total_area else 0,
            "actual_path_used_area_percent": round((actual_used_area / total_area) * 100, 1) if total_area else 0,
            "waste_percent": round(100 - ((used_area / total_area) * 100), 1) if total_area else 0,
            "overflow": bool(unplaced),
            "collision_free": _layout_has_no_overlaps(placed, cfg.item_gap_mm),
            "within_work_area": _layout_within_work_area(placed, cfg),
            "min_safe_gap_mm": cfg.item_gap_mm,
            "target_name_width_mm": cfg.target_name_width_mm,
            "target_name_height_mm": cfg.target_name_height_mm,
            "target_gap_mm": cfg.target_gap_mm,
            "dense_nesting": bool(cfg.dense_nesting),
            "logical_coordinate_system": "800x600_MM_VIEWBOX_RENDER_ONLY",
            "inter_name_connection_forbidden": True,
            "internal_weld_scope": "SINGLE_NAME_ONLY",
            "unplaced_count": len(unplaced),
            "page_stats": page_stats,
        },
        "unplaced": unplaced,
    }


def _scene_object_ids(item: dict[str, Any], index: int) -> tuple[str, str, str]:
    source_item_id = str(item.get("source_item_id") or item.get("item_id") or item.get("id") or f"source-{index + 1}")
    item_id = str(item.get("item_id") or item.get("id") or source_item_id)
    copy_index = int(item.get("copy_index") or 1)
    page = int(item.get("page") or 1)
    object_id = str(item.get("object_id") or f"{item_id}::object")
    placement_id = str(item.get("placement_id") or f"{object_id}::copy-{copy_index}::page-{page}")
    return source_item_id, object_id, placement_id


def build_name_cut_production_scene(items: list[dict[str, Any]], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the single read-only production scene used by preview, validation and export.

    The scene intentionally contains only production geometry. UI helpers such as
    grid, selection frames, rulers and measurement labels are not included.
    """
    cfg = _layout_config_from_payload(config or {})
    layout = layout_name_cut_items(items, cfg)
    layout_cfg = layout.get("config", {})
    source_items = [
        {
            "source_item_id": str(item.get("item_id") or item.get("id") or f"source-{index + 1}"),
            "text": str(item.get("name_text") or item.get("text") or item.get("preview_text") or ""),
            "quantity": max(1, _safe_int(item.get("quantity"), 1)),
            "composition_mode": str(item.get("compositionMode") or item.get("composition_mode") or item.get("composition") or ""),
        }
        for index, item in enumerate(items or [])
    ]
    objects: dict[str, dict[str, Any]] = {}
    placements: list[dict[str, Any]] = []
    paths: list[dict[str, Any]] = []
    warnings: list[str] = []
    outlined_count = 0
    fallback_count = 0
    auto_repaired_count = 0
    failed_repair_count = 0
    clean_count = 0
    for index, item in enumerate(layout.get("items", []) or []):
        source_item_id, object_id, placement_id = _scene_object_ids(item, index)
        repair = _auto_repair_name_cut_item(item, layout_cfg)
        contours = repair.pop("contours", [])
        raw_contours = repair.pop("raw_contours", [])
        offset_contours = repair.pop("offset_contours", [])
        bridge_contours = repair.pop("bridge_contours", [])
        welded_contours = repair.pop("welded_contours", contours)
        preview_contours = raw_contours or _outline_contours_for_item(item, layout_cfg, path_role="preview")
        if not preview_contours:
            preview_contours = contours
        item = {**item, **repair}
        path_data, final_path_representation = _final_svg_path_from_contours(welded_contours, item, layout_cfg)
        raw_path_data = _svg_path_from_contours(raw_contours or preview_contours)
        offset_path_data = _svg_path_from_contours(offset_contours)
        bridge_path_data = _svg_path_from_contours(bridge_contours)
        welded_cut_path_data = path_data
        preview_path_data = _svg_path_from_contours(preview_contours)
        repair_status = str(item.get("repairStatus") or item.get("repair_status") or "failed")
        style_for_item = item.get("style") or item.get("font_family") or layout_cfg.get("font_family") or ""
        corel_reference_override = _corel_exact_reference_override_for_item(item, layout_cfg, style_for_item)
        if corel_reference_override:
            path_data = str(corel_reference_override.get("corelReferenceOverridePathData") or "")
            welded_cut_path_data = path_data
            # Production canvas and export must render the same final cut geometry.
            preview_path_data = path_data
            final_path_representation = "corel_reference_override_final_cut_path"
            transformed_bbox = corel_reference_override.get("corelReferenceTransformedBBox") or []
            actual_bbox_width = 0.0
            actual_bbox_height = 0.0
            if isinstance(transformed_bbox, list) and len(transformed_bbox) == 4:
                actual_bbox_width = max(0.0, float(transformed_bbox[2]) - float(transformed_bbox[0]))
                actual_bbox_height = max(0.0, float(transformed_bbox[3]) - float(transformed_bbox[1]))
            repair_status = str(corel_reference_override.get("corelReferenceStatus") or "corel_reference_style_override")
            item = {
                **item,
                **corel_reference_override,
                "repairStatus": repair_status,
                "repair_status": repair_status,
                "readyForCut": True,
                "ready_for_cut": True,
                # SECURITY PATCH: exact-reference override stays operator-review-gated
                # regardless of source. Reference-library correctness is NOT assumed
                # (İrem/Ümit mislabeled split-children rendered wrong names — see
                # output/2026-05-27/irem_audit/). readyForCut may be True but the
                # operator MUST visually confirm before the cut queue.
                "requiresOperatorReview": True,
                "requires_operator_review": True,
                "isConnectedPath": True,
                "is_connected_path": True,
                "componentCount": 1,
                "component_count": 1,
                "componentCountAfterRepair": 1,
                "component_count_after_repair": 1,
                "componentCountBeforeRepair": max(1, int(item.get("componentCountBeforeRepair") or item.get("component_count_before_repair") or 1)),
                "detachedPartCount": 0,
                "detached_part_count": 0,
                "unresolvedPartCount": 0,
                "unresolved_part_count": 0,
                "hasDetachedDots": False,
                "has_detached_dots": False,
                "hasDisconnectedLetters": False,
                "has_disconnected_letters": False,
                "autoRepaired": True,
                "auto_repaired": True,
                "appliedWeld": True,
                "applied_weld": True,
                "validationMode": "COREL_REFERENCE_OVERRIDE_WYSIWYG_CUT_GEOMETRY",
                "analysisBBox": transformed_bbox,
                "analysis_bbox": transformed_bbox,
                "actual_path_width_mm": round(actual_bbox_width, 3),
                "actual_path_height_mm": round(actual_bbox_height, 3),
                "repairMessages": [
                    *list(item.get("repairMessages") or item.get("repair_messages") or []),
                    "corel_reference_override_applied",
                    "canvas_export_same_final_reference_geometry",
                ],
                "repair_messages": [
                    *list(item.get("repairMessages") or item.get("repair_messages") or []),
                    "corel_reference_override_applied",
                    "canvas_export_same_final_reference_geometry",
                ],
                "corelReferenceCorpusEnabled": True,
                "corel_reference_corpus_enabled": True,
                "corelReferenceCorpusEnforced": True,
                "corel_reference_corpus_enforced": True,
                "corelReferenceCorpusPassed": True,
                "corel_reference_corpus_passed": True,
                "corelReferenceCorpusStatus": "REFERENCE_OVERRIDE_APPLIED",
                "corel_reference_corpus_status": "REFERENCE_OVERRIDE_APPLIED",
                "corelReferenceCorpusScore": 100,
                "corel_reference_corpus_score": 100,
                "corelReferenceCorpusReasons": ["corel_reference_override_applied"],
                "corel_reference_corpus_reasons": ["corel_reference_override_applied"],
                "corelReferenceCorpusCandidateMetrics": corel_reference_override.get("corelReferenceTransformedMetrics") or {},
                "corel_reference_corpus_candidate_metrics": corel_reference_override.get("corelReferenceTransformedMetrics") or {},
            }
            corel_reference_quality = {
                key: value
                for key, value in item.items()
                if str(key).startswith("corelReferenceCorpus") or str(key).startswith("corel_reference_corpus")
            }
        else:
            corel_reference_quality = _corel_reference_quality_for_path(path_data, item, layout_cfg, style_for_item)
            # DXF library miss (Leyla, 2026-05-28): when legacy algorithms are
            # default OFF and there is no DXF library entry for this name,
            # surface a clear "design missing" status so the UI tells the
            # operator that Leyla must hand-draw the name. readyForCut=False
            # blocks downstream production.
            _legacy_on = _truthy_setting(
                item.get("use_legacy_name_cut_algorithms", layout_cfg.get("use_legacy_name_cut_algorithms")),
                False,
            )
            if not _legacy_on and _dxf_library_api is not None:
                _requested_name = str(item.get("name_text") or item.get("preview_text") or item.get("text") or item.get("name") or "").strip()
                if _requested_name:
                    try:
                        _lookup = _dxf_library_api.resolve_name_for_order(PROJECT_ROOT, _requested_name)
                    except Exception:  # noqa: BLE001
                        _lookup = None
                    if _lookup and _lookup.get("status") in {"MISSING_DESIGN", "UNREADABLE"}:
                        item = {
                            **item,
                            "repairStatus": "dxf_library_missing_design",
                            "repair_status": "dxf_library_missing_design",
                            "readyForCut": False,
                            "ready_for_cut": False,
                            "productionCandidate": False,
                            "production_candidate": False,
                            "requiresOperatorReview": True,
                            "requires_operator_review": True,
                            "exactReferenceRequired": True,
                            "exact_reference_required": True,
                            "dxfLibraryStatus": _lookup.get("status"),
                            "dxf_library_status": _lookup.get("status"),
                            "dxfLibraryMessage": _lookup.get("message"),
                            "dxf_library_message": _lookup.get("message"),
                            "dxfLibraryAsciiName": _lookup.get("ascii_name"),
                            "dxf_library_ascii_name": _lookup.get("ascii_name"),
                            "reviewWarning": f"'{_requested_name}' DXF kütüphanesinde yok. Leyla bu ismi çizip {DXF_LIBRARY_DIR_RELATIVE}/ altına atana kadar üretime alınamaz.",
                            "review_warning": f"'{_requested_name}' DXF kütüphanesinde yok. Leyla bu ismi çizip {DXF_LIBRARY_DIR_RELATIVE}/ altına atana kadar üretime alınamaz.",
                            "source": "dxf_library_missing",
                            "pathSource": "dxf_library_missing",
                            "path_source": "dxf_library_missing",
                            **corel_reference_quality,
                        }
            if _is_mochary_user_corel_calibrated_style(style_for_item) or _truthy_setting(layout_cfg.get("corel_reference_corpus_enabled"), False):
                missing_key = _corel_reference_key(item.get("name_text") or item.get("preview_text") or item.get("text") or item.get("name") or "")
                repair_status = "reference_missing_generated_review_required"
                style_candidate_quality_passed = bool(
                    path_data
                    and item.get("glyphIdentityPassed", True) is not False
                    and item.get("markOwnershipPassed", True) is not False
                    and str(item.get("designerWeldStatus") or "") == "designer_weld_passed"
                    and str(item.get("manufacturabilityStatus") or "") == "manufacturable_passed"
                    and not item.get("internalGarbagePath")
                )
                item = {
                    **item,
                    "repairStatus": repair_status,
                    "repair_status": repair_status,
                    "readyForCut": False,
                    "ready_for_cut": False,
                    "productionCandidate": style_candidate_quality_passed,
                    "production_candidate": style_candidate_quality_passed,
                    "requiresOperatorReview": True,
                    "requires_operator_review": True,
                    "exactReferenceRequired": True,
                    "exact_reference_required": True,
                    "source": "internal_ai_assisted_name_engine",
                    "pathSource": "internal_ai_assisted_name_engine",
                    "path_source": "internal_ai_assisted_name_engine",
                    "corelReferenceOverrideApplied": False,
                    "corel_reference_override_applied": False,
                    "corelReferenceMode": "internal_corel_like_vector_engine",
                    "corel_reference_mode": "internal_corel_like_vector_engine",
                    "corelReferenceStatus": "MISSING_EXACT_LABEL",
                    "corel_reference_status": "MISSING_EXACT_LABEL",
                    "corelReferenceKey": missing_key,
                    "corel_reference_key": missing_key,
                    "renderedPathKind": "internal_final_cut_path_review_required",
                    "rendered_path_kind": "internal_final_cut_path_review_required",
                    "reviewWarning": "Corel exact etiketi yok; internal Corel-like vector engine ile üretildi ve operatör onayı ister.",
                    "review_warning": "Corel exact etiketi yok; internal Corel-like vector engine ile üretildi ve operatör onayı ister.",
                }
        corel_status = str(corel_reference_quality.get("corelReferenceCorpusStatus") or "")
        corel_blocks_ready = bool(
            corel_reference_quality.get("corelReferenceCorpusEnforced")
            and corel_status in {"REFERENCE_MISMATCH", "COREL_STYLE_REVIEW_REQUIRED", "COREL_REFERENCE_CORPUS_MISSING"}
        )
        sound_single_piece_weld = bool(
            (item.get("productionCandidate") or item.get("production_candidate"))
            and str(item.get("designerWeldStatus") or item.get("designer_weld_status") or "") == "designer_weld_passed"
            and int(item.get("componentCount") or item.get("component_count") or 0) == 1
        )
        if corel_blocks_ready and corel_status == "REFERENCE_MISMATCH" and sound_single_piece_weld:
            # Calibration (2026-05-27): the targeted stroke-weld connectors shift the
            # corpus geometry metrics, so a REFERENCE_MISMATCH on a geometrically-sound
            # SINGLE-PIECE weld (designer_weld_passed + manufacturable + comp==1) is a
            # style-distance signal, NOT a geometry defect. Keep it OPERATOR-REVIEW
            # gated (CLAUDE.md) instead of rejecting clean output as unsuitable.
            repair_status = "reference_missing_generated_review_required"
            item = {
                **item,
                "repairStatus": repair_status,
                "repair_status": repair_status,
                "readyForCut": False,
                "ready_for_cut": False,
                "requiresOperatorReview": True,
                "requires_operator_review": True,
                "productionCandidate": True,
                "production_candidate": True,
                **corel_reference_quality,
            }
        elif corel_blocks_ready:
            repair_status = "reference_mismatch" if corel_status == "REFERENCE_MISMATCH" else "corel_style_review_required"
            item = {
                **item,
                "repairStatus": repair_status,
                "repair_status": repair_status,
                "readyForCut": False,
                "ready_for_cut": False,
                "productionCandidate": False if corel_status == "REFERENCE_MISMATCH" else bool(item.get("productionCandidate") or item.get("production_candidate")),
                "production_candidate": False if corel_status == "REFERENCE_MISMATCH" else bool(item.get("productionCandidate") or item.get("production_candidate")),
                **corel_reference_quality,
            }
        else:
            item = {**item, **corel_reference_quality}
        canvas_path_hash = _corel_path_hash(welded_cut_path_data)
        export_path_hash = _corel_path_hash(path_data)
        reference_path_hash = str(item.get("corelReferencePathHash") or item.get("corel_reference_path_hash") or (_corel_path_hash(path_data) if item.get("corelReferenceOverrideApplied") else ""))
        item = {
            **item,
            "finalCutPathHash": canvas_path_hash,
            "final_cut_path_hash": canvas_path_hash,
            "canvasPathHash": canvas_path_hash,
            "canvas_path_hash": canvas_path_hash,
            "exportPathHash": export_path_hash,
            "export_path_hash": export_path_hash,
            "referencePathHash": reference_path_hash,
            "reference_path_hash": reference_path_hash,
        }
        exact_reference_applied = bool(item.get("corelReferenceOverrideApplied") or item.get("corel_reference_override_applied"))
        if exact_reference_applied and not (
            path_data
            and canvas_path_hash
            and reference_path_hash
            and canvas_path_hash == export_path_hash == reference_path_hash
        ):
            repair_status = "canvas_export_reference_mismatch"
            item = {
                **item,
                "repairStatus": repair_status,
                "repair_status": repair_status,
                "readyForCut": False,
                "ready_for_cut": False,
                "requiresOperatorReview": True,
                "requires_operator_review": True,
                "corelReferenceStatus": "CANVAS_EXPORT_REFERENCE_MISMATCH",
                "corel_reference_status": "CANVAS_EXPORT_REFERENCE_MISMATCH",
                "reviewWarning": "Canvas/export/reference path hash eşleşmedi; exact reference üretime hazır sayılmaz.",
                "review_warning": "Canvas/export/reference path hash eşleşmedi; exact reference üretime hazır sayılmaz.",
            }
        passed_repair_statuses = {"clean", "auto_repaired", "auto_repaired_ai_verified", "designer_weld_passed", "manufacturable_passed", "corel_reference_exact_override"}
        failed_statuses = {
            "failed", "ai_quality_failed", "designer_weld_failed", "unnatural_connection",
            "internal_garbage_path", "visual_far_from_manual_reference", "connected_but_ugly",
            "connected_but_not_production_ready", "visual_passed_but_cut_risky",
            "manufacturable_failed", "glyph_identity_failed", "invalid_mark_ownership",
            "wrong_glyph_mark", "extra_mark_generated", "detached_turkish_mark",
            "mark_attached_to_wrong_glyph", "mark_blob_risk", "reference_mismatch",
            "corel_style_review_required", "reference_missing_generated_review_required",
            "canvas_export_reference_mismatch",
        }
        bridge_failed_prefixes = {
            "detached_dot", "detached_breve", "detached_cedilla", "bridge_too_long",
            "bridge_crosses_other_glyph", "bridge_attached_to_wrong_glyph",
            "bridge_visual_line_artifact", "mark_blob_risk", "mark_not_connected_to_owner_body",
        }
        repair_status_failed = repair_status in failed_statuses or repair_status.split(":", 1)[0] in bridge_failed_prefixes
        if repair_status == "clean":
            clean_count += 1
        elif repair_status in passed_repair_statuses:
            auto_repaired_count += 1
        else:
            failed_repair_count += 1
        status = "OUTLINED_PATHS_WITH_FONTTOOLS" if path_data and not repair_status_failed else "PATH_READY_REPAIR_FAILED" if path_data else "PATH_MISSING_NEEDS_REVIEW"
        if path_data:
            outlined_count += 1
        else:
            fallback_count += 1
            warnings.append(f"{item.get('name_text') or object_id}: FontTools path üretilemedi; üretim katmanı fallback text çizmez.")
        if repair_status_failed:
            warnings.append(f"{item.get('name_text') or object_id}: otomatik repair tamamlanamadı; üretim kuyruğuna hazır sayılmaz.")
        actual_bbox = item.get("analysisBBox") or item.get("analysis_bbox")
        actual_bbox_width = 0.0
        actual_bbox_height = 0.0
        if isinstance(actual_bbox, list) and len(actual_bbox) == 4:
            actual_bbox_width = max(0.0, float(actual_bbox[2]) - float(actual_bbox[0]))
            actual_bbox_height = max(0.0, float(actual_bbox[3]) - float(actual_bbox[1]))
        object_payload = objects.setdefault(
            object_id,
            {
                "object_id": object_id,
                "source_item_id": source_item_id,
                "item_id": str(item.get("item_id") or item.get("id") or object_id),
                "text": str(item.get("name_text") or item.get("preview_text") or item.get("text") or item.get("name") or ""),
                "width_mm": round(float(item.get("width_mm") or 0), 3),
                "height_mm": round(float(item.get("height_mm") or 0), 3),
                "actual_path_width_mm": round(float(actual_bbox_width or item.get("actual_path_width_mm") or item.get("width_mm") or 0), 3),
                "actual_path_height_mm": round(float(actual_bbox_height or item.get("actual_path_height_mm") or item.get("height_mm") or 0), 3),
                "rotation": round(float(item.get("rotation") or 0), 3),
                "mirrored": bool(item.get("mirrored") or layout_cfg.get("mirror_cut")),
                "direction": str(item.get("direction") or _cut_direction_label(cfg)),
                "thickening_mode": str(item.get("thickening_mode") or "Orta"),
                "offset_mm": round(float(item.get("offset_mm") or layout_cfg.get("offset_mm") or 0), 3),
                "support_line": bool(item.get("support_line")),
                "back_plate": bool(item.get("back_plate")),
                "path_preview_status": status,
                "separate_cut_object": True,
                "no_inter_name_bridge": True,
                **{key: item.get(key) for key in [
                    "componentCount", "component_count", "detachedParts", "detached_parts",
                    "smallIslandCount", "small_island_count", "hasDetachedDots", "has_detached_dots",
                    "hasDisconnectedLetters", "has_disconnected_letters", "isConnectedPath",
                    "is_connected_path", "dotRisk", "dot_risk", "tailRisk", "tail_risk",
                    "needsWeld", "needs_weld", "appliedKerningFix", "applied_kerning_fix",
                    "appliedOffsetMm", "applied_offset_mm", "appliedWeld", "applied_weld",
                    "appliedSmartBridge", "applied_smart_bridge", "componentCountBeforeRepair",
                    "component_count_before_repair", "componentCountAfterRepair", "component_count_after_repair",
                    "detachedPartCount", "detached_part_count", "bridgedPartCount", "bridged_part_count",
                    "unresolvedPartCount", "unresolved_part_count",
                    "appliedDotBridge", "applied_dot_bridge", "autoRepaired", "auto_repaired",
                    "repairStatus", "repair_status", "repairMessages", "repair_messages",
                    "offsetMode", "offset_mode", "repairWarnings", "repair_warnings",
                    "missingGlyphChars", "missing_glyph_chars", "validationMode", "analysisBBox", "analysis_bbox",
                    "aiQualityEnabled", "ai_quality_enabled", "aiQualityCandidateCount", "ai_quality_candidate_count",
                    "aiQualityCandidates", "ai_quality_candidates", "aiBestCandidateId", "ai_best_candidate_id",
                    "selectedOffsetMm", "selected_offset_mm", "selectedBridgeMm", "selected_bridge_mm",
                    "aiQualityScore", "ai_quality_score", "aiQualityStatus", "ai_quality_status",
                    "aiQualityScores", "ai_quality_scores", "aiQualityReason", "ai_quality_reason",
                    "aiQualityInspector", "ai_quality_inspector", "aiDirectPathGeneration", "ai_direct_path_generation",
                    "designerMarkBridgeDetails", "designer_mark_bridge_details",
                    "designerMarkBridgeWarnings", "designer_mark_bridge_warnings",
                    "markBridgeValidationErrors", "mark_bridge_validation_errors",
                    "globalSmartBridgeDisabledForDesignerMarks",
                    "global_smart_bridge_disabled_for_designer_marks",
                    "designerWeldPlan", "designer_weld_plan", "designerWeldStatus", "designer_weld_status",
                    "manufacturabilityStatus", "manufacturability_status", "manualReferenceSimilarityScore",
                    "manual_reference_similarity_score", "naturalConnectionScore", "natural_connection_score",
                    "internalGarbagePath", "internal_garbage_path", "tinyHoleCount", "tiny_hole_count",
                    "longThinArtifactCount", "long_thin_artifact_count", "minNeckWidthMm", "min_neck_width_mm",
                    "filledSilhouetteScore", "filled_silhouette_score",
                    "designerReadyForCut", "designer_ready_for_cut", "riskOverlayFlags", "risk_overlay_flags",
                    "glyphIdentity", "glyph_identity", "glyphIdentityPassed", "glyph_identity_passed",
                    "markOwnershipPassed", "mark_ownership_passed", "glyphOwnershipStatus",
                    "glyph_ownership_status", "detachedMarkCount", "detached_mark_count",
                    "wrongGlyphMarkCount", "wrong_glyph_mark_count", "extraMarkCount", "extra_mark_count",
                    "detachedMarkDetails", "wrongGlyphMarkDetails", "extraMarkDetails",
                    "appliedStyleProfile", "applied_style_profile", "appliedPairRules",
                    "applied_pair_rules", "appliedMarkRules", "applied_mark_rules",
                    "glyphOverrideUsed", "glyph_override_used", "glyphOverrideBlocked",
                    "glyph_override_blocked", "connectionRulesApplied", "connection_rules_applied",
                    "finalCutPathHash", "final_cut_path_hash", "reviewRequired", "review_required",
                    "finalGeometryConnectivityPassed", "final_geometry_connectivity_passed",
                    "finalGeometryConnectivityStatus", "final_geometry_connectivity_status",
                    "connectedComponentCount", "connected_component_count",
                    "detachedMarkComponents", "detached_mark_components",
                    "detachedDotCount", "detached_dot_count", "detachedBreveCount",
                    "detached_breve_count", "detachedCedillaCount", "detached_cedilla_count",
                    "ownerGlyphConnectionMap", "owner_glyph_connection_map",
                    "markConnectedToOwnerBody", "mark_connected_to_owner_body",
                    "markConnectedToWrongGlyph", "mark_connected_to_wrong_glyph",
                    "bridgePathUnionedIntoFinalPath", "bridge_path_unioned_into_final_path",
                    "finalFilledSilhouetteConnected", "final_filled_silhouette_connected",
                    "finalGeometryConnectivityErrors", "final_geometry_connectivity_errors",
                    "pathComponentCountTable", "path_component_count_table",
                    "expectedMarkCount", "expected_mark_count", "corelReferenceCorpusEnabled",
                    "corel_reference_corpus_enabled", "corelReferenceCorpusEnforced",
                    "corel_reference_corpus_enforced", "corelReferenceCorpusPassed",
                    "corel_reference_corpus_passed", "corelReferenceCorpusStatus",
                    "corel_reference_corpus_status", "corelReferenceCorpusScore",
                    "corel_reference_corpus_score", "corelReferenceCorpusReasons",
                    "corel_reference_corpus_reasons", "corelReferenceCorpusCandidateMetrics",
                    "corel_reference_corpus_candidate_metrics", "corelReferenceOverrideApplied",
                    "corel_reference_override_applied", "corelReferenceMode", "corel_reference_mode",
                    "corelReferenceStatus", "corel_reference_status", "corelReferenceKey",
                    "corel_reference_key", "corelReferenceName", "corel_reference_name",
                    "corelReferencePath", "corel_reference_path", "corelReferenceOverridePathData",
                    "corel_reference_override_path_data", "corelReferenceTransformedBBox",
                    "corel_reference_transformed_bbox", "corelReferenceStyleOnly",
                    "corel_reference_style_only", "corelReferenceExactNameMatch",
                    "corel_reference_exact_name_match", "corelReferenceSelectedObjectId",
                    "corel_reference_selected_object_id", "corelReferenceSelectionReason",
                    "corel_reference_selection_reason"
                ] if key in item},
            },
        )
        if status == "PATH_MISSING_NEEDS_REVIEW":
            object_payload["path_preview_status"] = status
        production_candidate_value = bool(item.get("productionCandidate") or item.get("production_candidate"))
        if (
            not production_candidate_value
            and path_data
            and not bool(item.get("exactReferenceRequired") or item.get("exact_reference_required"))
            and not bool(item.get("requiresOperatorReview") or item.get("requires_operator_review"))
        ):
            production_candidate_value = True
        placement = {
            **object_payload,
            "placement_id": placement_id,
            "copy_index": int(item.get("copy_index") or 1),
            "page": int(item.get("page") or 1),
            "x_mm": round(float(item.get("x_mm") or 0), 3),
            "y_mm": round(float(item.get("y_mm") or 0), 3),
            "width_mm": round(float(item.get("width_mm") or 0), 3),
            "height_mm": round(float(item.get("height_mm") or 0), 3),
            "actual_path_width_mm": round(float(actual_bbox_width or item.get("actual_path_width_mm") or item.get("width_mm") or 0), 3),
            "actual_path_height_mm": round(float(actual_bbox_height or item.get("actual_path_height_mm") or item.get("height_mm") or 0), 3),
            "path_preview_status": status,
            "ready_for_cut": bool(path_data) and not repair_status_failed and not item.get("hasCollision") and item.get("readyForCut", True) is not False,
            "export_layer_safe": True,
            "canvasExportConsistencyPassed": bool(path_data) and welded_cut_path_data == path_data,
            "canvas_export_consistency_passed": bool(path_data) and welded_cut_path_data == path_data,
            "pathOnlyExportPassed": bool(path_data),
            "path_only_export_passed": bool(path_data),
            "source": item.get("pathSource") or item.get("source") or ("corel_exact_reference" if item.get("corelReferenceOverrideApplied") else "internal_ai_assisted_name_engine" if item.get("exactReferenceRequired") else "generated_path"),
            "pathSource": item.get("pathSource") or item.get("path_source") or ("corel_exact_reference" if item.get("corelReferenceOverrideApplied") else "internal_ai_assisted_name_engine" if item.get("exactReferenceRequired") else "generated_path"),
            "path_source": item.get("pathSource") or item.get("path_source") or ("corel_exact_reference" if item.get("corelReferenceOverrideApplied") else "internal_ai_assisted_name_engine" if item.get("exactReferenceRequired") else "generated_path"),
            "renderedPathKind": item.get("renderedPathKind") or item.get("rendered_path_kind") or ("referenceFinalCutPathData" if item.get("corelReferenceOverrideApplied") else "generatedFinalCutPathData"),
            "rendered_path_kind": item.get("renderedPathKind") or item.get("rendered_path_kind") or ("referenceFinalCutPathData" if item.get("corelReferenceOverrideApplied") else "generatedFinalCutPathData"),
            "productionCandidate": production_candidate_value,
            "production_candidate": production_candidate_value,
            "requiresOperatorReview": bool(item.get("requiresOperatorReview") or item.get("requires_operator_review")),
            "requires_operator_review": bool(item.get("requiresOperatorReview") or item.get("requires_operator_review")),
            "exactReferenceFound": bool(item.get("corelReferenceOverrideApplied")),
            "exact_reference_found": bool(item.get("corelReferenceOverrideApplied")),
            "exactReferenceRequired": bool(item.get("exactReferenceRequired") or item.get("exact_reference_required")),
            "exact_reference_required": bool(item.get("exactReferenceRequired") or item.get("exact_reference_required")),
            "canvasPathHash": canvas_path_hash,
            "canvas_path_hash": canvas_path_hash,
            "exportPathHash": export_path_hash,
            "export_path_hash": export_path_hash,
            "referencePathHash": reference_path_hash,
            "reference_path_hash": reference_path_hash,
        }
        placements.append(placement)
        paths.append(
            {
                **placement,
                "path_data": path_data,
                "cut_path_data": path_data,
                "rawPathData": raw_path_data,
                "raw_path_data": raw_path_data,
                "offsetPathData": offset_path_data,
                "offset_path_data": offset_path_data,
                "bridgePathData": bridge_path_data,
                "bridge_path_data": bridge_path_data,
                "weldedCutPathData": welded_cut_path_data,
                "welded_cut_path_data": welded_cut_path_data,
                "finalCutPathData": welded_cut_path_data,
                "final_cut_path_data": welded_cut_path_data,
                "corelPreviewPathData": preview_path_data,
                "corel_preview_path_data": preview_path_data,
                "preview_path_data": preview_path_data,
                "canvasExportConsistencyPassed": bool(path_data) and welded_cut_path_data == path_data,
                "canvas_export_consistency_passed": bool(path_data) and welded_cut_path_data == path_data,
                "pathOnlyExportPassed": bool(path_data),
                "path_only_export_passed": bool(path_data),
                "finalPathRepresentation": final_path_representation,
                "final_path_representation": final_path_representation,
                "path_role": "cut",
                "preview_role": "debug_raw_font_path_only" if "brannboll" in _normalize_token(item.get("style") or layout_cfg.get("font_family") or "") else "production_path",
                "outline_engine": "fonttools",
            }
        )
    metrics = {
        "source_count": len(source_items),
        "object_count": len(objects),
        "placement_count": len(placements),
        "copy_total": len(placements),
        "pages": int(layout.get("summary", {}).get("pages") or 1),
        "used_area_percent": layout.get("summary", {}).get("used_area_percent", 0),
        "actual_path_used_area_percent": layout.get("summary", {}).get("actual_path_used_area_percent", 0),
        "collision_free": bool(layout.get("summary", {}).get("collision_free", False)),
        "within_work_area": bool(layout.get("summary", {}).get("within_work_area", False)),
        "outlined_count": outlined_count,
        "fallback_count": fallback_count,
        "clean_count": clean_count,
        "auto_repaired_count": auto_repaired_count,
        "failed_repair_count": failed_repair_count,
        "ready_for_cut_count": sum(1 for placement in placements if placement.get("ready_for_cut")),
        "min_safe_gap_mm": layout.get("summary", {}).get("min_safe_gap_mm", cfg.item_gap_mm),
        "placement_strategy": layout.get("summary", {}).get("placement_strategy", ""),
    }
    status = "OK" if placements and fallback_count == 0 else "NEEDS_REVIEW" if placements else "EMPTY"
    return {
        "status": status,
        "message": "İsim Kesim production scene hazır. RDWorks/lazer/yazıcı başlatılmadı.",
        "sourceItems": source_items,
        "objects": list(objects.values()),
        "placements": placements,
        "paths": paths,
        "metrics": metrics,
        "layout": layout,
        "warnings": warnings,
        "path_preview_status": "OUTLINED_PATHS_WITH_FONTTOOLS" if outlined_count and fallback_count == 0 else "PATH_MISSING_NEEDS_REVIEW",
        "outlined_count": outlined_count,
        "fallback_count": fallback_count,
        "safety": {
            "rdworks_auto_start": False,
            "laser_auto_start": False,
            "printer_auto_start": False,
            "read_only_preview": True,
            "production_layer_only": True,
        },
    }


def preview_name_cut_paths(items: list[dict[str, Any]], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return read-only FontTools outline paths for the Name Cut canvas preview."""
    scene = build_name_cut_production_scene(items, config or {})
    return {
        **scene,
        "status": scene.get("status", "EMPTY"),
        "message": "FontTools path preview hazır. RDWorks/lazer/yazıcı başlatılmadı.",
    }


def _is_joined_name_mode(composition: object) -> bool:
    token = _normalize_token(composition)
    return "bitistir" in token or "biti_tir" in token or "bititir" in token or "compact" in token or "joined_names" in token


def _is_auto_split_name_mode(composition: object) -> bool:
    token = _normalize_token(composition)
    return "otomatik" in token or "auto_split" in token or "bol_ve_diz" in token or "split_to_objects" in token or "ayri_isimler" in token


def _is_explicit_single_line_mode(composition: object) -> bool:
    token = _normalize_token(composition)
    return "single_line_text" in token or "tek_satir_yazi" in token or "explicit_single_line" in token


def _split_name_words(text: object) -> list[str]:
    return [word for word in str(text or "").strip().split() if word]


def _split_production_name_parts(text: object, split_ampersand: bool = True) -> list[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    if split_ampersand and "&" in raw:
        return [part.strip() for part in raw.split("&") if part.strip()]
    parts = [part.strip() for part in re.split(r"[\n,;]+", raw) if part.strip()]
    return parts if parts else [raw]


def _is_multi_name_candidate(text: object) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    words = [word for word in raw.split() if word]
    has_pair_joiner = "&" in raw
    return (len(words) >= 5 and not has_pair_joiner) or any(sep in raw for sep in [",", ";", "\n"]) or (len(raw) >= 42 and len(words) >= 4 and not has_pair_joiner)


def _expand_joined_name_items(items: list[dict[str, Any]], cfg: LayoutConfig) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for source_order, item in enumerate(items):
        composition = item.get("compositionMode") or item.get("composition_mode") or item.get("composition") or ""
        preview_objects = item.get("preview_objects") if isinstance(item.get("preview_objects"), list) else item.get("previewObjects")
        raw_source_text = item.get("name_text") or item.get("text") or ""
        split_pair_names = "&" in str(raw_source_text or "") and not _is_explicit_single_line_mode(composition) and not _is_joined_name_mode(composition)
        if split_pair_names:
            parts = _split_production_name_parts(raw_source_text, split_ampersand=True)
            if len(parts) > 1:
                for index, word in enumerate(parts, start=1):
                    child_id = f"{item.get('item_id') or item.get('id') or 'name'}-pair-{index}"
                    expanded.append(
                        {
                            **item,
                            "id": child_id,
                            "item_id": child_id,
                            "name_text": word,
                            "text": word,
                            "preview_text": word,
                            "source_name_text": item.get("name_text") or item.get("text") or "",
                            "source_item_id": item.get("item_id") or item.get("id") or "",
                            "source_order": source_order,
                            "split_word_index": index,
                            "split_word_count": len(parts),
                            "joined_name_gap_mm": cfg.joined_name_gap_mm,
                            "composition": "Çift isim ayrıldı",
                            "composition_mode": "auto_split_pair_names",
                            "compositionMode": "auto_split_pair_names",
                            "lineBreakMode": "single_line",
                            "line_break_mode": "single_line",
                            "width_mm": round(float(cfg.target_name_width_mm), 2),
                            "height_mm": round(float(cfg.target_name_height_mm), 2),
                            "quantity": "1",
                            "inter_name_connection_forbidden": True,
                            "no_inter_name_bridge": True,
                        }
                    )
                continue
        must_split_multi_name = _is_multi_name_candidate(raw_source_text) and not _is_explicit_single_line_mode(composition) and not _is_joined_name_mode(composition)
        if must_split_multi_name and isinstance(preview_objects, list) and len(preview_objects) > 1:
            for index, obj in enumerate(preview_objects, start=1):
                word = str(obj.get("formattedText") or obj.get("text") or "").strip()
                if not word:
                    continue
                child_id = str(obj.get("id") or f"{item.get('item_id') or 'name'}-split-{index}")
                expanded.append(
                    {
                        **item,
                        "id": child_id,
                        "item_id": child_id,
                        "name_text": word,
                        "text": word,
                        "preview_text": word,
                        "source_name_text": item.get("name_text") or item.get("text") or "",
                        "source_item_id": item.get("item_id") or item.get("id") or "",
                        "source_order": source_order,
                        "split_word_index": index,
                        "split_word_count": len(preview_objects),
                        "joined_name_gap_mm": cfg.joined_name_gap_mm,
                        "composition": "Tek Satır Yan Yana",
                        "composition_mode": "Tek Satır Yan Yana",
                        "compositionMode": "single_line_text",
                        "lineBreakMode": "single_line",
                        "line_break_mode": "single_line",
                        "width_mm": round(float(cfg.target_name_width_mm), 2),
                        "height_mm": round(float(cfg.target_name_height_mm), 2),
                        "actual_path_width_mm": round(float(obj.get("actualPathWidthMm") or obj.get("widthMm") or cfg.target_name_width_mm), 2),
                        "actual_path_height_mm": round(float(obj.get("actualPathHeightMm") or obj.get("heightMm") or cfg.target_name_height_mm), 2),
                        "quantity": "1",
                    }
                )
            continue
        if must_split_multi_name or (_is_auto_split_name_mode(composition) and len(_split_name_words(raw_source_text)) > 1):
            raw_text = str(raw_source_text or "").strip()
            parts = [part.strip() for part in re.split(r"[\n,;]+", raw_text) if part.strip()]
            if len(parts) <= 1 and "&" not in raw_text:
                parts = _split_name_words(raw_text)
            if len(parts) > 1:
                for index, word in enumerate(parts, start=1):
                    child_id = f"{item.get('item_id') or item.get('id') or 'name'}-split-{index}"
                    expanded.append(
                        {
                            **item,
                            "id": child_id,
                            "item_id": child_id,
                            "name_text": word,
                            "text": word,
                            "preview_text": word,
                            "source_name_text": item.get("name_text") or item.get("text") or "",
                            "source_item_id": item.get("item_id") or item.get("id") or "",
                            "source_order": source_order,
                            "split_word_index": index,
                            "split_word_count": len(parts),
                            "joined_name_gap_mm": cfg.joined_name_gap_mm,
                            "composition": "Tek Satır Yan Yana",
                            "composition_mode": "Tek Satır Yan Yana",
                            "compositionMode": "single_line_text",
                            "lineBreakMode": "single_line",
                            "line_break_mode": "single_line",
                            "width_mm": round(float(cfg.target_name_width_mm), 2),
                            "height_mm": round(float(cfg.target_name_height_mm), 2),
                            "quantity": "1",
                            "inter_name_connection_forbidden": True,
                            "no_inter_name_bridge": True,
                        }
                    )
                continue
        words = _split_name_words(item.get("name_text"))
        if not _is_joined_name_mode(composition) or len(words) <= 1:
            expanded.append({**item, "source_order": source_order})
            continue
        height = max(cfg.target_name_height_mm, float(item.get("height_mm") or cfg.target_name_height_mm))
        max_width = max(cfg.target_name_width_mm, float(item.get("width_mm") or cfg.target_name_width_mm))
        for index, word in enumerate(words, start=1):
            width, resolved_height = resolve_name_cut_dimensions(word, None, height, max_width, height, "Tek SatÄ±r Yan Yana")
            expanded.append(
                {
                    **item,
                    "item_id": f"{item.get('item_id') or 'name'}-word-{index}",
                    "name_text": word,
                    "preview_text": word,
                    "source_name_text": item.get("name_text") or "",
                    "source_item_id": item.get("item_id") or "",
                    "source_order": source_order,
                    "split_word_index": index,
                    "split_word_count": len(words),
                    "joined_name_gap_mm": cfg.joined_name_gap_mm,
                    "composition": "\u0130simleri Biti\u015ftir",
                    "composition_mode": "\u0130simleri Biti\u015ftir",
                    "width_mm": round(max(cfg.target_name_width_mm, width), 2),
                    "height_mm": round(max(cfg.target_name_height_mm, resolved_height), 2),
                    "quantity": item.get("quantity", "1"),
                }
            )
    return expanded


def _layout_has_no_overlaps(items: list[dict[str, Any]], gap_mm: float = 0.0) -> bool:
    tolerance = 0.01
    gap = max(0.0, float(gap_mm or 0.0))
    for index, first in enumerate(items):
        for second in items[index + 1:]:
            if int(first.get("page", 1)) != int(second.get("page", 1)):
                continue
            first_left = float(first.get("x_mm") or 0)
            first_top = float(first.get("y_mm") or 0)
            first_right = first_left + float(first.get("width_mm") or 0)
            first_bottom = first_top + float(first.get("height_mm") or 0)
            second_left = float(second.get("x_mm") or 0)
            second_top = float(second.get("y_mm") or 0)
            second_right = second_left + float(second.get("width_mm") or 0)
            second_bottom = second_top + float(second.get("height_mm") or 0)
            separated = (
                first_right + gap - tolerance <= second_left
                or second_right + gap - tolerance <= first_left
                or first_bottom + gap - tolerance <= second_top
                or second_bottom + gap - tolerance <= first_top
            )
            if not separated:
                return False
    return True


def _layout_within_work_area(items: list[dict[str, Any]], cfg: LayoutConfig) -> bool:
    tolerance = 0.01
    min_x = cfg.margin_mm - tolerance
    min_y = cfg.margin_mm - tolerance
    max_x = cfg.width_mm - cfg.margin_mm + tolerance
    max_y = cfg.height_mm - cfg.margin_mm + tolerance
    for item in items:
        x = float(item.get("x_mm") or 0)
        y = float(item.get("y_mm") or 0)
        width = float(item.get("width_mm") or 0)
        height = float(item.get("height_mm") or 0)
        if x < min_x or y < min_y:
            return False
        if x + width > max_x or y + height > max_y:
            return False
    return True


def _layout_config_from_payload(payload: dict[str, Any]) -> LayoutConfig:
    if not isinstance(payload, dict):
        return LayoutConfig()

    def number(key: str, default: float, min_value: float, max_value: float) -> float:
        value = _safe_optional_float(payload.get(key))
        if value is None:
            return default
        return round(max(min_value, min(max_value, value)), 2)

    return LayoutConfig(
        width_mm=number("width_mm", 800, 100, 1800),
        height_mm=number("height_mm", 600, 100, 1200),
        target_name_width_mm=number("target_name_width_mm", 80, 20, 240),
        target_name_height_mm=number("target_name_height_mm", 40, 10, 120),
        target_gap_mm=number("target_gap_mm", 1, 1, 3),
        margin_mm=number("margin_mm", 15, 0, 80),
        item_gap_mm=number("item_gap_mm", number("target_gap_mm", 1, 1, 3), 1, 3),
        row_gap_mm=number("row_gap_mm", number("target_gap_mm", 1, 1, 3), 1, 3),
        joined_name_gap_mm=number("joined_name_gap_mm", number("target_gap_mm", 1, 1, 3), 1, 3),
        allow_rotation=bool(payload.get("allow_rotation", True)),
        mirror_cut=bool(payload.get("mirror_cut", False)),
        mirror_vertical=bool(payload.get("mirror_vertical", False)),
        start_corner=str(payload.get("start_corner") or "top-left"),
        packing_direction=str(payload.get("packing_direction") or "left-to-right"),
        row_direction=str(payload.get("row_direction") or "top-to-bottom"),
        dense_nesting=bool(payload.get("dense_nesting", True)),
        font_family=str(payload.get("font_family") or "Mochary.ttf"),
        offset_mm=number("offset_mm", 0.3, 0, 1.5),
    )


def format_name_for_cutting(value: object) -> str:
    words = re.split(r"\s+", str(value or "").strip())
    fixed: list[str] = []
    for word in words:
        token = _normalize_token(word)
        if not token:
            continue
        fixed.append(TURKISH_NAME_FIXES.get(token, _turkish_title_token(token)))
    return " ".join(fixed)


def _turkish_title_token(token: str) -> str:
    if not token:
        return ""
    first = "\u0130" if token[0] == "i" else token[0].upper()
    return first + token[1:].lower()


def resolve_offset_mm(mode: object, custom_offset: object = None) -> float:
    custom = _safe_optional_float(custom_offset)
    if custom is not None:
        return round(max(0.0, min(5.0, custom)), 2)
    token = _normalize_token(mode)
    return THICKENING_OFFSETS.get(token, 0.8)


def resolve_name_cut_dimensions(
    text: str,
    width_mm: float | None,
    height_mm: float | None,
    max_width_mm: float | None = None,
    max_height_mm: float | None = None,
    composition: str = "Tek SatÄ±r Yan Yana",
) -> tuple[float, float]:
    words = [word for word in str(text or "").split() if word]
    longest = max((len(word) for word in words), default=8)
    word_count = max(1, len(words))
    if "alt" in _normalize_token(composition):
        natural_ratio = max(1.8, longest * 0.34)
    else:
        natural_ratio = max(2.2, (sum(len(word) for word in words) * 0.28) + ((word_count - 1) * 0.65))
    if width_mm and height_mm:
        natural_width = height_mm * natural_ratio
        scale = min(width_mm / max(natural_width, 1), 1.0)
        resolved_width = natural_width * scale
        resolved_height = height_mm * scale
    elif width_mm:
        resolved_width = width_mm
        resolved_height = width_mm / natural_ratio
    elif height_mm:
        resolved_height = height_mm
        resolved_width = height_mm * natural_ratio
    else:
        resolved_width = max_width_mm or 300.0
        resolved_height = resolved_width / natural_ratio
    if max_width_mm and resolved_width > max_width_mm:
        factor = max_width_mm / max(resolved_width, 1)
        resolved_width *= factor
        resolved_height *= factor
    if max_height_mm and resolved_height > max_height_mm:
        factor = max_height_mm / max(resolved_height, 1)
        resolved_width *= factor
        resolved_height *= factor
    return round(max(20.0, resolved_width), 2), round(max(10.0, resolved_height), 2)


def _thickening_status(items: list[dict[str, Any]]) -> str:
    has_offset = any(float(item.get("offset_mm") or 0) > 0 for item in items)
    if has_offset:
        return _offset_engine_status()
    return "NO_THICKENING_REQUESTED"


def _offset_engine_status() -> str:
    if pyclipper is not None:
        return "TRUE_POLYGON_OFFSET_WITH_PYCLIPPER"
    return "P1_RISK_APPROX_CONTOUR_EXPANSION_NOT_TRUE_OFFSET"


def _text_to_path_status(layout: dict[str, Any]) -> str:
    if not layout.get("items"):
        return "NO_TEXT_ITEMS"
    for item in layout["items"]:
        if not _outline_contours_for_item(item, layout["config"]):
            return "P1_RISK_TEXT_NOT_OUTLINED"
    return "OUTLINED_PATHS_WITH_FONTTOOLS"


def _count_quality_status(quality_summary: dict[str, Any], status: str) -> int:
    try:
        return max(0, int(float(str(quality_summary.get(status) or 0).replace(",", "."))))
    except (TypeError, ValueError):
        return 0


def _item_quality_status(item: dict[str, Any]) -> str:
    explicit = str(item.get("single_piece_quality") or item.get("quality_status") or item.get("single_piece_status") or "").strip()
    if explicit:
        return explicit
    status = str(item.get("status") or "").strip().lower()
    if status in {"error", "blocked"} or item.get("force_blocked") or item.get("errors"):
        return "blocked"
    if item.get("force_collision_risk"):
        return "collision_risk"
    if item.get("force_detached_marks") or item.get("detached_marks"):
        return "detached_marks"
    if item.get("force_needs_weld") or item.get("internal_weld_ready") is False:
        return "needs_weld"
    try:
        offset = float(str(item.get("offset_mm") or "0").replace(",", "."))
    except (TypeError, ValueError):
        offset = 0.0
    if item.get("force_needs_offset") or offset <= 0:
        return "needs_offset"
    return "ready_single_piece"


def _name_cut_export_preflight(
    layout: dict[str, Any],
    live_items: list[dict[str, Any]],
    config: dict[str, Any],
    real_formats: list[str],
    skipped_formats: list[str],
    scene: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = layout.get("summary") or {}
    quality_summary = dict(config.get("quality_summary") or {})
    item_statuses = [_item_quality_status(item) for item in live_items]
    for status in {"ready_single_piece", "needs_weld", "needs_offset", "detached_marks", "collision_risk", "blocked"}:
        quality_summary[status] = max(_count_quality_status(quality_summary, status), item_statuses.count(status))
    quality_summary["total"] = max(_count_quality_status(quality_summary, "total"), len(live_items))

    blockers: list[str] = []
    if summary.get("collision_free") is False:
        blockers.append("FarklÄ± isimler arasÄ±nda temas/collision riski var.")
    if summary.get("within_work_area") is False:
        blockers.append("Safe margin dÄ±ÅŸÄ±na taÅŸan isim var.")
    if _text_to_path_status(layout) != "OUTLINED_PATHS_WITH_FONTTOOLS":
        blockers.append("GerÃ§ek path/outline oluÅŸturulamayan isim var.")
    if scene and scene.get("placements"):
        strict_scene_preflight = _truthy_setting(config.get("strict_name_cut_scene_preflight"), False)
        blocked_placements = []
        for item in scene.get("placements", []):
            corel_enforced = bool(
                item.get("corelReferenceCorpusEnforced")
                or item.get("corel_reference_corpus_enforced")
            )
            corel_status = str(
                item.get("corelReferenceCorpusStatus")
                or item.get("corel_reference_corpus_status")
                or item.get("repairStatus")
                or item.get("repair_status")
                or ""
            ).strip().lower()
            if item.get("ready_for_cut") is True:
                continue
            if not (
                strict_scene_preflight
                or corel_enforced
                or corel_status in {
                    "reference_mismatch",
                    "corel_style_review_required",
                    "corel_reference_corpus_missing",
                }
            ):
                continue
            blocked_placements.append(
                str(item.get("text") or item.get("object_id") or item.get("placement_id") or "")
            )
        if blocked_placements:
            blockers.append(f"{len(blocked_placements)} isim final cut/reference gate nedeniyle hazÄ±r deÄŸil: {', '.join(blocked_placements[:6])}.")
    for status in BLOCKING_QUALITY_STATUSES:
        count = _count_quality_status(quality_summary, status)
        if count:
            labels = {
                "needs_weld": "Weld gerekli",
                "detached_marks": "Nokta/iÅŸaret kopuk",
                "collision_risk": "Temas riski",
                "blocked": "Ãœretime engel",
            }
            blockers.append(f"{count} kayÄ±t export edilemez: {labels.get(status, status)}.")
    offset_count = _count_quality_status(quality_summary, "needs_offset")
    offset_warnings = [f"{offset_count} kayÄ±t iÃ§in offset/kalÄ±nlaÅŸtÄ±rma operatÃ¶r onayÄ± gerektiriyor."] if offset_count else []
    return {
        "status": "BLOCKED" if blockers else "NEEDS_OFFSET_APPROVAL" if offset_warnings and not bool(config.get("operator_approved_offset_warning")) else "PASSED",
        "blockers": blockers,
        "offset_warnings": offset_warnings,
        "quality_summary": quality_summary,
        "single_piece_quality": "PASSED" if not any(_count_quality_status(quality_summary, status) for status in BLOCKING_QUALITY_STATUSES) else "FAILED",
        "weld_status": "PASSED" if not _count_quality_status(quality_summary, "needs_weld") else "FAILED",
        "detached_marks_status": "PASSED" if not _count_quality_status(quality_summary, "detached_marks") else "FAILED",
        "collision_check": "PASSED" if summary.get("collision_free") is not False and not _count_quality_status(quality_summary, "collision_risk") else "FAILED",
        "real_formats": real_formats,
        "skipped_formats": skipped_formats,
    }


def _rdworks_compatibility_qa(layout: dict[str, Any], exported_files: dict[str, str], project_root: Path) -> dict[str, Any]:
    cfg = layout.get("config") or {}
    summary = layout.get("summary") or {}
    checks = {
        "unit_mm": True,
        "scale_preserved": True,
        "cut_direction_manifested": True,
        "min_gap_preserved": summary.get("collision_free") is not False,
        "safe_margin_preserved": summary.get("within_work_area") is not False,
        "preview_bbox_matches_plate": True,
        "no_ui_helper_geometry": True,
        "cut_paths_only": True,
    }
    forbidden_tokens = ("GUIDE_PREVIEW", "CALIBRATION", "selection-box", "data-ui-helper")
    for key in ("svg", "dxf"):
        rel = exported_files.get(key) or ""
        if not rel:
            continue
        path = project_root / rel
        if not path.exists():
            checks["scale_preserved"] = False
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(token in text for token in forbidden_tokens):
            checks["no_ui_helper_geometry"] = False
            checks["cut_paths_only"] = False
        if "<text" in text.lower() or "\nTEXT\n" in text:
            checks["cut_paths_only"] = False
        if key == "svg" and ("mm" not in text or "<path" not in text):
            checks["scale_preserved"] = False
        if key == "dxf" and ("POLYLINE" not in text or "CUT_NAME_OUTLINE" not in text):
            checks["cut_paths_only"] = False
    return {
        "status": "PASSED" if all(checks.values()) else "FAILED",
        "checks": checks,
        "plate_size_mm": {"width": cfg.get("width_mm"), "height": cfg.get("height_mm")},
        "min_gap_mm": summary.get("min_safe_gap_mm", cfg.get("item_gap_mm")),
        "safe_margin_mm": cfg.get("margin_mm"),
    }


def _manifest_item(item: dict[str, Any]) -> dict[str, Any]:
    offset_mm = float(item.get("offset_mm") or 0)
    return {
        "item_id": item.get("item_id", ""),
        "row_number": item.get("row_number", ""),
        "original_name": item.get("raw_customer_name") or item.get("original_name") or item.get("name_text") or "",
        "formatted_name": item.get("name_text", ""),
        "source_name_text": item.get("source_name_text") or item.get("raw_customer_name") or item.get("name_text") or "",
        "split_word_index": item.get("split_word_index", ""),
        "split_word_count": item.get("split_word_count", ""),
        "joined_name_gap_mm": item.get("joined_name_gap_mm", ""),
        "composition_mode": item.get("composition_mode") or item.get("composition") or "Tek SatÄ±r Yan Yana",
        "font_preset": item.get("style", ""),
        "font_family": _font_family_for_style(item.get("style")),
        "font_path_status": _font_path_status_for_style(item.get("style")),
        "font_profile": "Ceyizhome Lab Script" if "ceyizhome" in _normalize_token(item.get("style")) else item.get("style", ""),
        "script_connection_status": _script_connection_status_for_style(item.get("style")),
        "capital_connection_bridge_status": _capital_connection_bridge_status_for_text(item.get("formatted_name") or item.get("name_text") or item.get("preview_text"), item.get("style")),
        "diacritic_bridge_status": _diacritic_bridge_status_for_text(item.get("formatted_name") or item.get("name_text") or item.get("preview_text")),
        "weld_scope": "INSIDE_EACH_NAME_ONLY",
        "keep_names_separate": True,
        "width_mm": item.get("width_mm", 0),
        "height_mm": item.get("height_mm", 0),
        "actual_path_width_mm": item.get("actual_path_width_mm", item.get("width_mm", 0)),
        "actual_path_height_mm": item.get("actual_path_height_mm", item.get("height_mm", 0)),
        "raw_path_width_mm": item.get("raw_path_width_mm", ""),
        "raw_path_height_mm": item.get("raw_path_height_mm", ""),
        "path_scale": item.get("path_scale", ""),
        "rotation": item.get("rotation", 0),
        "mirrored": bool(item.get("mirrored")),
        "direction": item.get("direction", ""),
        "quantity": item.get("quantity", "1"),
        "thickening_mode": item.get("thickening_mode", "Orta"),
        "offset_mm": offset_mm,
        "support_line": bool(item.get("support_line")),
        "back_plate": bool(item.get("back_plate")),
        "rdworks_layer": "CUT_NAME_OUTLINE",
        "support_layer": "CUT_SUPPORT_LINE" if item.get("support_line") else "",
        "back_plate_layer": "CUT_BACK_PLATE" if item.get("back_plate") else "",
        "text_to_path_status": "OUTLINED_PATHS_WITH_FONTTOOLS",
        "thickening_status": _offset_engine_status() if offset_mm > 0 else "NO_THICKENING_REQUESTED",
        "page_no": item.get("page", 1),
        "x_mm": item.get("x_mm", 0),
        "y_mm": item.get("y_mm", 0),
        "status": item.get("status", "READY"),
        "warnings": item.get("warnings", []),
        "errors": item.get("errors", []),
    }


@lru_cache(maxsize=1)
def _font_registry_entries() -> tuple[dict[str, Any], ...]:
    try:
        data = json.loads(FONT_REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return tuple()
    entries = data.get("fonts") if isinstance(data, dict) else []
    if not isinstance(entries, list):
        return tuple()
    return tuple(entry for entry in entries if isinstance(entry, dict))


def _font_registry_path(entry: dict[str, Any]) -> Path | None:
    for key in ("path", "fallbackPath"):
        raw = str(entry.get(key) or "").strip()
        if not raw:
            continue
        path = Path(raw)
        if not path.is_absolute():
            path = (PROJECT_ROOT.parent / path).resolve()
        if path.exists():
            return path
    return None


def _font_registry_entry_for_style(style: object) -> dict[str, Any] | None:
    token = _normalize_token(style)
    if not token:
        return None
    for entry in _font_registry_entries():
        candidates = [
            entry.get("id"),
            entry.get("label"),
            entry.get("familyValue"),
            Path(str(entry.get("path") or "")).stem,
            Path(str(entry.get("fallbackPath") or "")).stem,
        ]
        if token in {_normalize_token(value) for value in candidates if value}:
            return entry
    return None


def _font_family_for_style(style: object) -> str:
    registry_entry = _font_registry_entry_for_style(style)
    if registry_entry:
        return str(registry_entry.get("familyValue") or registry_entry.get("label") or style or "Brannboll Connect")
    style_text = str(style or "")
    token = _normalize_token(style_text)
    if "brannboll" in token:
        return "Brannboll Connect"
    if "visual_refined_v2" in token or "visualrefinedv2" in token:
        return "Mochary TR Connect Visual Refined V2"
    if "visual_refined" in token or "visualrefined" in token:
        return "Mochary TR Connect Visual Refined"
    if "mochary_tr_connect" in token or "mocharytrconnect" in token:
        return "Mochary TR Connect"
    if "ceyizhome" in _normalize_token(style_text):
        return "Ceyizhome Lab Script"
    for preset in NAME_CUT_PRESETS:
        if _normalize_token(preset["name"]) == _normalize_token(style_text):
            return str(preset["font_family"])
    return "Great Vibes"


def _font_path_status_for_style(style: object) -> str:
    registry_entry = _font_registry_entry_for_style(style)
    if registry_entry:
        return "FONT_FILE_AVAILABLE" if _font_registry_path(registry_entry) else f"P1_RISK_FONT_FILE_NOT_FOUND:{registry_entry.get('id') or registry_entry.get('label')}"
    token = _normalize_token(style)
    if "brannboll" in token:
        return "FONT_FILE_AVAILABLE" if FONT_PATHS["brannboll_connect"].exists() else "P1_RISK_BRANNBOLL_CONNECT_FONT_FILE_NOT_FOUND"
    if "visual_refined_v2" in token or "visualrefinedv2" in token:
        return "FONT_FILE_AVAILABLE" if FONT_PATHS["mochary_tr_connect_visual_refined_v2"].exists() else "P1_RISK_MOCHARY_TR_CONNECT_VISUAL_REFINED_V2_FONT_FILE_NOT_FOUND"
    if "visual_refined" in token or "visualrefined" in token:
        return "FONT_FILE_AVAILABLE" if FONT_PATHS["mochary_tr_connect_visual_refined"].exists() else "P1_RISK_MOCHARY_TR_CONNECT_VISUAL_REFINED_FONT_FILE_NOT_FOUND"
    if "mochary_tr_connect" in token or "mocharytrconnect" in token:
        return "FONT_FILE_AVAILABLE" if FONT_PATHS["mochary_tr_connect"].exists() else "P1_RISK_MOCHARY_TR_CONNECT_FONT_FILE_NOT_FOUND"
    if ("mochary" in token or "ceyizhome" in token or "lab_script" in token) and not FONT_PATHS["mochary"].exists():
        if FONT_PATHS["mochary_like"].exists():
            return f"MOCHARY_FONT_FILE_NOT_FOUND_USING_MOCHARY_LIKE_FALLBACK:{FONT_PATHS['mochary_like'].name}"
        return "P1_RISK_MOCHARY_FONT_FILE_NOT_FOUND_USING_SEGOE_SCRIPT_FALLBACK"
    return "FONT_FILE_AVAILABLE"


def _font_path_for_style(style: object) -> Path:
    registry_entry = _font_registry_entry_for_style(style)
    if registry_entry:
        path = _font_registry_path(registry_entry)
        if path:
            return path
    token = _normalize_token(style)
    if "brannboll" in token:
        if FONT_PATHS["brannboll_connect"].exists():
            return FONT_PATHS["brannboll_connect"]
        return FONT_PATHS["mochary_like"] if FONT_PATHS["mochary_like"].exists() else FONT_PATHS["script"]
    if "visual_refined_v2" in token or "visualrefinedv2" in token:
        if FONT_PATHS["mochary_tr_connect_visual_refined_v2"].exists():
            return FONT_PATHS["mochary_tr_connect_visual_refined_v2"]
        if FONT_PATHS["mochary_tr_connect_visual_refined"].exists():
            return FONT_PATHS["mochary_tr_connect_visual_refined"]
        if FONT_PATHS["mochary_tr_connect"].exists():
            return FONT_PATHS["mochary_tr_connect"]
        return FONT_PATHS["mochary_like"] if FONT_PATHS["mochary_like"].exists() else FONT_PATHS["script"]
    if "visual_refined" in token or "visualrefined" in token:
        if FONT_PATHS["mochary_tr_connect_visual_refined"].exists():
            return FONT_PATHS["mochary_tr_connect_visual_refined"]
        if FONT_PATHS["mochary_tr_connect"].exists():
            return FONT_PATHS["mochary_tr_connect"]
        return FONT_PATHS["mochary_like"] if FONT_PATHS["mochary_like"].exists() else FONT_PATHS["script"]
    if "mochary_tr_connect" in token or "mocharytrconnect" in token:
        if FONT_PATHS["mochary_tr_connect"].exists():
            return FONT_PATHS["mochary_tr_connect"]
        if FONT_PATHS["mochary"].exists():
            return FONT_PATHS["mochary"]
        return FONT_PATHS["mochary_like"] if FONT_PATHS["mochary_like"].exists() else FONT_PATHS["script"]
    if "mochary" in token or "ceyizhome" in token or "lab_script" in token:
        if FONT_PATHS["mochary"].exists():
            return FONT_PATHS["mochary"]
        return FONT_PATHS["mochary_like"] if FONT_PATHS["mochary_like"].exists() else FONT_PATHS["script"]
    if "kalin" in token or "thick" in token or "plexi" in token:
        return FONT_PATHS["script_bold"] if FONT_PATHS["script_bold"].exists() else FONT_PATHS["print_bold"]
    if "print" in token:
        return FONT_PATHS["print"] if FONT_PATHS["print"].exists() else FONT_PATHS["script"]
    if "serif" in token:
        return FONT_PATHS["serif"]
    return FONT_PATHS["script"] if FONT_PATHS["script"].exists() else FONT_PATHS["serif"]


class _FlattenGlyphPen(BasePen):
    def __init__(self, glyph_set: Any) -> None:
        super().__init__(glyph_set)
        self.contours: list[list[tuple[float, float]]] = []
        self._current: list[tuple[float, float]] = []
        self._last: tuple[float, float] | None = None

    def _moveTo(self, pt: tuple[float, float]) -> None:
        if self._current:
            self.contours.append(self._current)
        self._current = [pt]
        self._last = pt

    def _lineTo(self, pt: tuple[float, float]) -> None:
        self._current.append(pt)
        self._last = pt

    def _qCurveToOne(self, p1: tuple[float, float], p2: tuple[float, float]) -> None:
        p0 = self._last or p1
        for step in range(1, 9):
            t = step / 8
            x = ((1 - t) ** 2 * p0[0]) + (2 * (1 - t) * t * p1[0]) + (t ** 2 * p2[0])
            y = ((1 - t) ** 2 * p0[1]) + (2 * (1 - t) * t * p1[1]) + (t ** 2 * p2[1])
            self._current.append((x, y))
        self._last = p2

    def _curveToOne(self, p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float]) -> None:
        p0 = self._last or p1
        for step in range(1, 11):
            t = step / 10
            x = ((1 - t) ** 3 * p0[0]) + (3 * (1 - t) ** 2 * t * p1[0]) + (3 * (1 - t) * t ** 2 * p2[0]) + (t ** 3 * p3[0])
            y = ((1 - t) ** 3 * p0[1]) + (3 * (1 - t) ** 2 * t * p1[1]) + (3 * (1 - t) * t ** 2 * p2[1]) + (t ** 3 * p3[1])
            self._current.append((x, y))
        self._last = p3

    def _closePath(self) -> None:
        if self._current:
            self.contours.append(self._current)
        self._current = []
        self._last = None

    def _endPath(self) -> None:
        self._closePath()


@lru_cache(maxsize=12)
def _load_font(font_path: str) -> tuple[TTFont, Any, dict[int, str], dict[str, tuple[int, tuple[int, int]]], int]:
    font = TTFont(font_path)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap() or {}
    hmtx = font["hmtx"].metrics
    units_per_em = int(font["head"].unitsPerEm)
    return font, glyph_set, cmap, hmtx, units_per_em


def _missing_or_fallback_glyph_chars(text: str, font_path: str) -> list[str]:
    try:
        _font, glyph_set, cmap, _hmtx, _units = _load_font(font_path)
    except Exception:
        return sorted({char for char in str(text or "") if char.strip()})
    missing: list[str] = []
    for char in str(text or ""):
        if not char.strip():
            continue
        glyph_name = cmap.get(ord(char))
        if not glyph_name or glyph_name not in glyph_set or glyph_name in {".notdef", "question"}:
            missing.append(char)
    return list(dict.fromkeys(missing))


def _shape_line_with_harfbuzz(line: str, font_path: str, units_per_em: int) -> list[dict[str, float | int]]:
    if hb is None or not line:
        return []
    try:
        font_bytes = Path(font_path).read_bytes()
        face = hb.Face(font_bytes)
        hb_font = hb.Font(face)
        hb_font.scale = (units_per_em, units_per_em)
        buffer = hb.Buffer()
        buffer.add_str(line)
        buffer.guess_segment_properties()
        hb.shape(
            hb_font,
            buffer,
            {
                "kern": True,
                "liga": True,
                "clig": True,
                "calt": True,
                "rlig": True,
                # NOTE (2026-05-27): tested adding init/medi/fina — they DID change
                # some glyph forms (Sümeyye 'y', Çağrı 'r') but did NOT close the
                # inter-letter gaps (component count unchanged / slightly worse),
                # because the font has NO GPOS `curs` cursive-attachment, only
                # `kern`. GSUB form substitution alone doesn't make letters touch.
                # Left OFF (default Latin behaviour) to avoid the Sümeyye regression.
            },
        )
    except Exception:
        return []
    shaped: list[dict[str, float | int]] = []
    cursor_x = 0.0
    cursor_y = 0.0
    for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions):
        shaped.append(
            {
                "glyph_id": int(info.codepoint),
                "cluster": int(info.cluster),
                "x": cursor_x + float(pos.x_offset),
                "y": cursor_y + float(pos.y_offset),
                "advance_x": float(pos.x_advance),
                "advance_y": float(pos.y_advance),
            }
        )
        cursor_x += float(pos.x_advance)
        cursor_y += float(pos.y_advance)
    return shaped


def _profile_float(
    item: dict[str, Any] | None,
    cfg: dict[str, Any] | LayoutConfig | None,
    keys: tuple[str, ...],
    default: float,
    min_value: float,
    max_value: float,
) -> float:
    sources: list[Any] = []
    if item:
        sources.extend(item.get(key) for key in keys)
    if cfg:
        for key in keys:
            sources.append(cfg.get(key) if isinstance(cfg, dict) else getattr(cfg, key, None))
    for value in sources:
        parsed = _safe_optional_float(value)
        if parsed is not None:
            return max(min_value, min(max_value, float(parsed)))
    return default


def _profile_style_is_mochary(item: dict[str, Any] | None, cfg: dict[str, Any] | LayoutConfig | None) -> bool:
    if item and _truthy_setting(item.get("disable_valid_golden_profile") or item.get("disableValidGoldenProfile"), False):
        return False
    if cfg:
        disabled = cfg.get("disable_valid_golden_profile") if isinstance(cfg, dict) else getattr(cfg, "disable_valid_golden_profile", False)
        if _truthy_setting(disabled, False):
            return False
    style = ""
    if item:
        style = str(item.get("style") or item.get("font_family") or item.get("fontId") or "")
    if not style and cfg:
        style = str((cfg.get("font_family") if isinstance(cfg, dict) else getattr(cfg, "font_family", "")) or "")
    return _is_mochary_user_corel_calibrated_style(style)


@lru_cache(maxsize=1)
def _mochary_valid_golden_profile_payload() -> dict[str, Any]:
    try:
        return json.loads(MOCHARY_VALID_GOLDEN_PRODUCTION_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _mochary_internal_production_profile_payload() -> dict[str, Any]:
    try:
        return json.loads(MOCHARY_INTERNAL_PRODUCTION_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _golden_glyph_shape_library_payload() -> dict[str, Any]:
    try:
        return json.loads(GOLDEN_GLYPH_SHAPE_LIBRARY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _valid_golden_profile_value(key: str, default: Any = None) -> Any:
    profile = _mochary_valid_golden_profile_payload()
    return profile.get(key, default) if isinstance(profile, dict) else default


def _golden_letter_spacing_scale(item: dict[str, Any] | None, cfg: dict[str, Any] | LayoutConfig | None) -> float:
    value = _profile_float(item, cfg, ("letter_spacing_scale", "letterSpacingScale", "valid_golden_letter_spacing_scale"), 1.0, 0.65, 1.8)
    if abs(value - 1.0) < 0.0001 and _profile_style_is_mochary(item, cfg):
        return max(0.65, min(1.8, float(_valid_golden_profile_value("letterSpacingScale", 1.0) or 1.0)))
    return value


def _golden_kerning_adjustment(item: dict[str, Any] | None, cfg: dict[str, Any] | LayoutConfig | None) -> float:
    value = _profile_float(item, cfg, ("kerning_adjustment", "kerningAdjustment", "valid_golden_kerning_adjustment"), 0.0, -0.25, 0.25)
    if abs(value) < 0.0001 and _profile_style_is_mochary(item, cfg):
        return max(-0.25, min(0.25, float(_valid_golden_profile_value("kerningAdjustment", 0.0) or 0.0)))
    return value


def _golden_width_scale(item: dict[str, Any] | None, cfg: dict[str, Any] | LayoutConfig | None) -> float:
    value = _profile_float(item, cfg, ("width_scale", "widthScale", "valid_golden_width_scale"), 1.0, 0.5, 1.8)
    if abs(value - 1.0) < 0.0001 and _profile_style_is_mochary(item, cfg):
        return max(0.5, min(1.8, float(_valid_golden_profile_value("widthScale", 1.0) or 1.0)))
    return value


def _golden_height_scale(item: dict[str, Any] | None, cfg: dict[str, Any] | LayoutConfig | None) -> float:
    value = _profile_float(item, cfg, ("height_scale", "heightScale", "valid_golden_height_scale"), 1.0, 0.5, 1.8)
    if abs(value - 1.0) < 0.0001 and _profile_style_is_mochary(item, cfg):
        return max(0.5, min(1.8, float(_valid_golden_profile_value("heightScale", 1.0) or 1.0)))
    return value


def _json_profile_setting(item: dict[str, Any] | None, cfg: dict[str, Any] | LayoutConfig | None, keys: tuple[str, ...]) -> str:
    sources: list[Any] = []
    if item:
        sources.extend(item.get(key) for key in keys)
    if cfg:
        for key in keys:
            sources.append(cfg.get(key) if isinstance(cfg, dict) else getattr(cfg, key, None))
    for value in sources:
        if value in (None, "", {}, []):
            continue
        if isinstance(value, str):
            try:
                json.loads(value)
                return value
            except Exception:
                continue
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except Exception:
            continue
    return "{}"


def _golden_pair_kerning_signature(item: dict[str, Any] | None, cfg: dict[str, Any] | LayoutConfig | None) -> str:
    value = _json_profile_setting(item, cfg, ("pair_kerning_map", "pairKerningMap", "valid_golden_pair_kerning_map"))
    if value == "{}" and _profile_style_is_mochary(item, cfg):
        merged: dict[str, Any] = {}
        valid_map = _valid_golden_profile_value("pairKerningMap", {})
        if isinstance(valid_map, dict):
            merged.update(valid_map)
        visual_flow_disabled = False
        if item and _truthy_setting(item.get("disable_visual_script_flow_tightening") or item.get("disableVisualScriptFlowTightening"), False):
            visual_flow_disabled = True
        if cfg:
            disabled = cfg.get("disable_visual_script_flow_tightening") if isinstance(cfg, dict) else getattr(cfg, "disable_visual_script_flow_tightening", False)
            visual_flow_disabled = visual_flow_disabled or _truthy_setting(disabled, False)
        if not visual_flow_disabled:
            internal = _mochary_internal_production_profile_payload()
            flow = internal.get("visualScriptFlowTightening") if isinstance(internal, dict) else {}
            internal_map = flow.get("pairKerningMap") if isinstance(flow, dict) else {}
            if isinstance(internal_map, dict):
                merged.update(internal_map)
        return _json_profile_setting({"pairKerningMap": merged}, None, ("pairKerningMap",))
    return value


def _golden_glyph_scale_signature(item: dict[str, Any] | None, cfg: dict[str, Any] | LayoutConfig | None) -> str:
    value = _json_profile_setting(item, cfg, ("glyph_scale_rules", "glyphScaleRules", "valid_golden_glyph_scale_rules"))
    if value == "{}" and _profile_style_is_mochary(item, cfg):
        return _json_profile_setting({"glyphScaleRules": _valid_golden_profile_value("glyphScaleRules", {})}, None, ("glyphScaleRules",))
    return value


def _decode_profile_json(signature: str) -> dict[str, Any]:
    try:
        value = json.loads(signature or "{}")
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _profile_name_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "")).casefold()
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.replace("ı", "i").replace("İ", "i")
    return re.sub(r"[^a-z0-9:]+", "", normalized)


def _glyph_adjusted_contours(
    contours: list[list[tuple[float, float]]],
    char: str,
    scale_rules: dict[str, Any],
) -> list[list[tuple[float, float]]]:
    rule = scale_rules.get(char) or scale_rules.get(_profile_name_key(char)) or {}
    if not isinstance(rule, dict):
        return contours
    width_scale = max(0.5, min(1.8, float(rule.get("widthScale") or rule.get("width_scale") or 1.0)))
    height_scale = max(0.5, min(1.8, float(rule.get("heightScale") or rule.get("height_scale") or 1.0)))
    slant = max(-0.45, min(0.45, float(rule.get("slantCorrection") or rule.get("slant_correction") or 0.0)))
    if abs(width_scale - 1.0) < 0.001 and abs(height_scale - 1.0) < 0.001 and abs(slant) < 0.001:
        return contours
    points = [point for contour in contours for point in contour]
    if not points:
        return contours
    min_x = min(x for x, _ in points)
    max_x = max(x for x, _ in points)
    min_y = min(y for _, y in points)
    max_y = max(y for _, y in points)
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    adjusted: list[list[tuple[float, float]]] = []
    for contour in contours:
        next_contour: list[tuple[float, float]] = []
        for x, y in contour:
            dy = y - cy
            nx = cx + ((x - cx) * width_scale) + (dy * slant)
            ny = cy + (dy * height_scale)
            next_contour.append((nx, ny))
        adjusted.append(next_contour)
    return adjusted


def _pair_shift_for_index(chars: list[str], char_index: int, pair_kerning: dict[str, Any], units_per_em: int) -> float:
    shift = 0.0
    for index in range(max(0, char_index)):
        pair = f"{chars[index]}:{chars[index + 1]}" if index + 1 < len(chars) else ""
        value = pair_kerning.get(pair)
        if value is None:
            value = pair_kerning.get(_profile_name_key(pair))
        try:
            shift += float(value or 0.0) * units_per_em
        except Exception:
            continue
    return shift


@lru_cache(maxsize=512)
def _raw_text_contours(
    text: str,
    font_path: str,
    connect_mode: str = "normal",
    letter_spacing_scale: float = 1.0,
    kerning_adjustment: float = 0.0,
    pair_kerning_signature: str = "{}",
    glyph_scale_signature: str = "{}",
) -> tuple[tuple[tuple[tuple[float, float], ...], ...], tuple[float, float, float, float], int]:
    font, glyph_set, cmap, hmtx, units_per_em = _load_font(font_path)
    letter_spacing_scale = max(0.65, min(1.8, float(letter_spacing_scale or 1.0)))
    kerning_units = max(-0.25, min(0.25, float(kerning_adjustment or 0.0))) * units_per_em
    pair_kerning = _decode_profile_json(pair_kerning_signature)
    glyph_scale_rules = _decode_profile_json(glyph_scale_signature)
    all_contours: list[list[tuple[float, float]]] = []
    line_metrics: list[tuple[list[list[tuple[float, float]]], float]] = []
    line_height = units_per_em * 1.18
    connection = _script_connection_profile(connect_mode, units_per_em)
    for line_index, line in enumerate((text or "").splitlines() or [text or ""]):
        cursor_x = 0.0
        line_contours: list[list[tuple[float, float]]] = []
        shaped_glyphs = _shape_line_with_harfbuzz(line, font_path, units_per_em)
        if shaped_glyphs:
            baseline_y = -line_index * line_height
            glyph_order = font.getGlyphOrder()
            line_width = 0.0
            line_chars = list(line)
            shaped_clusters = [int(glyph.get("cluster") or 0) for glyph in shaped_glyphs]
            for shaped_index, shaped in enumerate(shaped_glyphs):
                glyph_id = int(shaped.get("glyph_id") or 0)
                if glyph_id < 0 or glyph_id >= len(glyph_order):
                    continue
                glyph_name = glyph_order[glyph_id]
                if glyph_name not in glyph_set or glyph_name in {".notdef", "space"}:
                    line_width = max(line_width, (float(shaped.get("x") or 0) * letter_spacing_scale) + (float(shaped.get("advance_x") or 0) * letter_spacing_scale))
                    continue
                pen = _FlattenGlyphPen(glyph_set)
                glyph_set[glyph_name].draw(pen)
                if pen._current:
                    pen.contours.append(pen._current)
                cluster = int(shaped.get("cluster") or 0)
                char_index = min(max(0, cluster), max(0, len(line_chars) - 1))
                if shaped_clusters and cluster not in range(len(line_chars)):
                    char_index = min(range(len(line_chars) or 1), key=lambda idx: abs(idx - cluster)) if line_chars else 0
                char_for_rule = line_chars[char_index] if line_chars else ""
                contours = _glyph_adjusted_contours(pen.contours, char_for_rule, glyph_scale_rules)
                glyph_x = (
                    (float(shaped.get("x") or 0) * letter_spacing_scale)
                    + (shaped_index * kerning_units)
                    + _pair_shift_for_index(line_chars, char_index, pair_kerning, units_per_em)
                )
                glyph_y = float(shaped.get("y") or 0)
                for contour in contours:
                    shifted = [(x + glyph_x, y + glyph_y + baseline_y) for x, y in contour if math.isfinite(x) and math.isfinite(y)]
                    if len(shifted) >= 2:
                        line_contours.append(shifted)
                line_width = max(line_width, glyph_x + (float(shaped.get("advance_x") or 0) * letter_spacing_scale))
            line_metrics.append((line_contours, max(line_width, units_per_em * 0.1)))
            continue
        line_chars = list(line)
        for char_index, char in enumerate(line_chars):
            if char.isspace():
                cursor_x += units_per_em * 0.35 * letter_spacing_scale
                continue
            glyph_name = cmap.get(ord(char)) or cmap.get(ord("?"))
            if char == "â‚º" and (not glyph_name or glyph_name not in glyph_set):
                baseline_y = -line_index * line_height
                for contour in _try_symbol_raw_contours(cursor_x, baseline_y, units_per_em):
                    line_contours.append(contour)
                cursor_x += units_per_em * 0.58 * letter_spacing_scale
                continue
            if not glyph_name or glyph_name not in glyph_set:
                cursor_x += units_per_em * 0.45 * letter_spacing_scale
                continue
            pen = _FlattenGlyphPen(glyph_set)
            glyph_set[glyph_name].draw(pen)
            if pen._current:
                pen.contours.append(pen._current)
            baseline_y = -line_index * line_height
            contours = _glyph_adjusted_contours(pen.contours, char, glyph_scale_rules)
            pair_shift = _pair_shift_for_index(line_chars, char_index, pair_kerning, units_per_em)
            for contour in contours:
                shifted = [(x + cursor_x + pair_shift, y + baseline_y) for x, y in contour if math.isfinite(x) and math.isfinite(y)]
                if len(shifted) >= 2:
                    line_contours.append(shifted)
            advance = hmtx.get(glyph_name, (units_per_em * 0.5, (0, 0)))[0]
            cursor_x += max(
                units_per_em * 0.08,
                (float(advance) * letter_spacing_scale)
                + _script_connection_adjustment(line_chars, char_index, connection)
                + kerning_units,
            )
        line_metrics.append((line_contours, cursor_x))
    max_line_width = max((width for _, width in line_metrics), default=1.0)
    for line_contours, line_width in line_metrics:
        line_offset = (max_line_width - line_width) / 2
        for contour in line_contours:
            all_contours.append([(x + line_offset, y) for x, y in contour])
    if not all_contours:
        return tuple(), (0.0, 0.0, 1.0, 1.0), units_per_em
    xs = [point[0] for contour in all_contours for point in contour]
    ys = [point[1] for contour in all_contours for point in contour]
    return tuple(tuple(contour) for contour in all_contours), (min(xs), min(ys), max(xs), max(ys)), units_per_em


def _try_symbol_raw_contours(cursor_x: float, baseline_y: float, units_per_em: int) -> list[list[tuple[float, float]]]:
    stroke = units_per_em * 0.045
    left = cursor_x + (units_per_em * 0.18)
    top = baseline_y + (units_per_em * 0.82)
    bottom = baseline_y + (units_per_em * 0.05)
    mid_1 = baseline_y + (units_per_em * 0.58)
    mid_2 = baseline_y + (units_per_em * 0.43)
    right = cursor_x + (units_per_em * 0.58)
    slash_dx = units_per_em * 0.2

    def rect(x1: float, y1: float, x2: float, y2: float) -> list[tuple[float, float]]:
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]

    return [
        rect(left, bottom, left + stroke, top),
        rect(left - (stroke * 0.4), mid_1, right, mid_1 + stroke),
        rect(left - (stroke * 0.4), mid_2, right - (units_per_em * 0.08), mid_2 + stroke),
        [(left + stroke, top), (left + slash_dx, top), (right, bottom), (right - slash_dx, bottom), (left + stroke, top)],
    ]


def _script_connection_profile(connect_mode: str, units_per_em: int) -> dict[str, float]:
    mode = _normalize_token(connect_mode)
    if "brannboll" in mode:
        return {
            "letter": -0.14 * units_per_em,
            "capital_to_lower": -0.22 * units_per_em,
            "lower_to_lower": -0.12 * units_per_em,
        }
    if "visual_refined" in mode:
        return {
            "letter": -0.07 * units_per_em,
            "capital_to_lower": -0.12 * units_per_em,
            "lower_to_lower": -0.06 * units_per_em,
        }
    if "mochary" in mode or "ceyizhome" in mode:
        return {
            "letter": -0.18 * units_per_em,
            "capital_to_lower": -0.38 * units_per_em,
            "lower_to_lower": -0.16 * units_per_em,
        }
    if "script" in mode or "connected" in mode:
        return {
            "letter": -0.12 * units_per_em,
            "capital_to_lower": -0.2 * units_per_em,
            "lower_to_lower": -0.1 * units_per_em,
        }
    return {"letter": 0.0, "capital_to_lower": 0.0, "lower_to_lower": 0.0}


def _script_connection_adjustment(chars: list[str], index: int, profile: dict[str, float]) -> float:
    if not profile.get("letter"):
        return 0.0
    current = chars[index]
    if current.isspace() or index + 1 >= len(chars) or chars[index + 1].isspace():
        return 0.0
    nxt = chars[index + 1]
    if current.isupper() and nxt.islower():
        base = profile["capital_to_lower"]
        # Wide capitals (M, W, S) need extra tightening for natural script flow.
        if current in "MWS":
            base *= 1.35
        return base
    if current.islower() and nxt.islower():
        return profile["lower_to_lower"]
    return profile["letter"]


def _script_connection_mode_for_style(style: object) -> str:
    token = _normalize_token(style)
    if "brannboll" in token:
        return "brannboll_connected_production"
    if "visual_refined" in token or "visualrefined" in token:
        return "visual_refined_readable_connection"
    if "ceyizhome" in token or "lab_script" in token:
        return "ceyizhome_lab_script_manual_bridge"
    if "mochary" in token:
        return "mochary_auto_capital_connection"
    if any(part in token for part in ["script", "romantik", "bitisik", "bitiÅŸik", "davetiye"]):
        return "script_auto_connection"
    return "normal"


def _script_connection_status_for_style(style: object) -> str:
    mode = _script_connection_mode_for_style(style)
    if mode == "brannboll_connected_production":
        return "BRANNBOLL_CONNECTED_PRODUCTION_TRACKING"
    if mode == "visual_refined_readable_connection":
        return "VISUAL_REFINED_READABLE_CONNECTION_TRACKING"
    if mode == "ceyizhome_lab_script_manual_bridge":
        return "CEYIZHOME_LAB_SCRIPT_OPENTYPE_PLUS_MANUAL_CAPITAL_BRIDGES"
    if mode == "mochary_auto_capital_connection":
        return "AUTO_CAPITAL_CONNECTION_TRACKING_FOR_MOCHARY_STYLE"
    if mode == "script_auto_connection":
        return "AUTO_SCRIPT_CONNECTION_TRACKING"
    return "NO_SCRIPT_CONNECTION_TRACKING"


def _is_mochary_user_corel_calibrated_style(style: object) -> bool:
    token = _normalize_token(style)
    if not token:
        return False
    if "mochary_tr_connect" in token or "mocharytrconnect" in token or "visual_refined" in token or "visualrefined" in token:
        return False
    return any(part in token for part in ("mochary_user", "mochary_ttf"))


def _outline_contours_for_item(item: dict[str, Any], cfg: dict[str, Any], path_role: str = "cut") -> list[list[tuple[float, float]]]:
    style = item.get("style") or cfg.get("font_family") or "Mochary.ttf"
    font_path = _font_path_for_style(style)
    if not font_path.exists():
        return []
    text = str(item.get("preview_text") or item.get("name_text") or item.get("text") or item.get("name") or "")
    raw_contours, bbox, _units = _raw_text_contours(
        text,
        str(font_path),
        _script_connection_mode_for_style(style),
        _golden_letter_spacing_scale(item, cfg),
        _golden_kerning_adjustment(item, cfg),
        _golden_pair_kerning_signature(item, cfg),
        _golden_glyph_scale_signature(item, cfg),
    )
    if not raw_contours:
        return []
    min_x, min_y, max_x, max_y = bbox
    source_w = max(1.0, max_x - min_x)
    source_h = max(1.0, max_y - min_y)
    x = float(item["x_mm"])
    y = float(item["y_mm"])
    width = float(item["width_mm"])
    height = float(item["height_mm"])
    if cfg.get("mirror_cut"):
        x = float(cfg["width_mm"]) - x - width
    scale = min((width * 0.94) / source_w, (height * 0.86) / source_h)
    scale_x = scale * _golden_width_scale(item, cfg)
    scale_y = scale * _golden_height_scale(item, cfg)
    draw_w = source_w * scale_x
    draw_h = source_h * scale_y
    origin_x = x + ((width - draw_w) / 2)
    origin_y = y + ((height - draw_h) / 2)
    contours: list[list[tuple[float, float]]] = []
    offset_mm = max(0.0, min(5.0, float(item.get("offset_mm") or cfg.get("offset_mm") or 0.65)))
    style_token = _normalize_token(style)
    role_token = _normalize_token(path_role)
    for contour in raw_contours:
        transformed: list[tuple[float, float]] = []
        for raw_x, raw_y in contour:
            px = origin_x + ((raw_x - min_x) * scale_x)
            py = origin_y + ((max_y - raw_y) * scale_y)
            if cfg.get("mirror_cut"):
                px = x + width - (px - x)
            transformed.append((round(px, 3), round(py, 3)))
        if len(transformed) >= 2:
            contours.append(transformed)
    if "brannboll" not in style_token and not _is_mochary_user_corel_calibrated_style(style):
        contours.extend(_capital_connection_bridge_contours_for_cutting(text, origin_x, origin_y, draw_w, draw_h, cfg.get("mirror_cut", False), style))
        contours.extend(_diacritic_bridge_contours_for_cutting(text, origin_x, origin_y, draw_w, draw_h, cfg.get("mirror_cut", False)))
    effective_offset_mm = 0.0 if ("brannboll" in style_token and role_token == "preview") else offset_mm
    if effective_offset_mm > 0:
        join_mode = "miter_soft" if "brannboll" in style_token else "round"
        contours = _offset_contours_for_cutting(contours, effective_offset_mm, join_mode)
    rotation = float(item.get("rotation") or 0)
    if abs(rotation) > 0.001:
        contours = _rotate_contours_for_cutting(contours, x + (width / 2), y + (height / 2), rotation)
    return contours


def _contour_bbox(contour: list[tuple[float, float]]) -> tuple[float, float, float, float] | None:
    if not contour:
        return None
    xs = [point[0] for point in contour]
    ys = [point[1] for point in contour]
    return min(xs), min(ys), max(xs), max(ys)


def _contour_area_mm2(contour: list[tuple[float, float]]) -> float:
    if len(contour) < 3:
        return 0.0
    area = 0.0
    points = contour if contour[0] == contour[-1] else [*contour, contour[0]]
    for index in range(len(points) - 1):
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        area += (x1 * y2) - (x2 * y1)
    return abs(area) / 2.0


def _bbox_gap_mm(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    x_gap = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    y_gap = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return math.hypot(x_gap, y_gap)


def _contour_groups_by_bbox(contours: list[list[tuple[float, float]]], near_gap_mm: float = 0.12) -> list[list[int]]:
    bboxes = [_contour_bbox(contour) for contour in contours]
    valid_indexes = [index for index, bbox in enumerate(bboxes) if bbox is not None and len(contours[index]) >= 3]
    visited: set[int] = set()
    groups: list[list[int]] = []
    for start in valid_indexes:
        if start in visited:
            continue
        stack = [start]
        group: list[int] = []
        visited.add(start)
        while stack:
            current = stack.pop()
            group.append(current)
            current_bbox = bboxes[current]
            if current_bbox is None:
                continue
            for other in valid_indexes:
                if other in visited:
                    continue
                other_bbox = bboxes[other]
                if other_bbox is None:
                    continue
                if _bbox_gap_mm(current_bbox, other_bbox) <= near_gap_mm:
                    visited.add(other)
                    stack.append(other)
        groups.append(group)
    return groups


def _count_outer_polytree_nodes(node) -> int:
    """Recursively count non-hole (outer) nodes in a pyclipper PolyTree.

    An island sitting inside a hole is a physically separate piece on the
    laser bed, so it counts as its own component. Therefore we count every
    non-hole node at any depth, not just the root's direct children.
    """
    total = 0
    for child in node.Childs:
        if not child.IsHole:
            total += 1
        total += _count_outer_polytree_nodes(child)
    return total


def _real_component_count_via_union(contours: list[list[tuple[float, float]]]) -> int:
    """Return the actual number of disconnected geometric components.

    Unlike `_contour_groups_by_bbox`, which uses bbox proximity (and therefore
    merges nearby-but-disconnected pieces into one false "component"), this
    performs a real geometric union and counts the resulting outer boundaries.

    Method (pyclipper):
      1. Scale each contour to integer space (x1000), mirroring
         `_union_contours_for_cutting` preprocessing for consistency.
      2. CleanPolygon + drop degenerate / near-zero-area paths.
      3. Pyclipper.Execute2(CT_UNION, NONZERO) -> PolyTree.
      4. Count every outer (non-hole) node at any depth == true component count.

    Never raises:
      - pyclipper unavailable          -> legacy bbox-group count
      - empty / all-degenerate input   -> 0
      - pyclipper raises during union  -> legacy bbox-group count
    """
    if not contours:
        return 0
    valid = [contour for contour in contours if contour and len(contour) >= 3]
    if not valid:
        return 0
    if pyclipper is None:
        return len(_contour_groups_by_bbox(valid, 0.12))
    scale = 1000
    paths: list[list[tuple[int, int]]] = []
    for contour in valid:
        path = [(int(round(x * scale)), int(round(y * scale))) for x, y in contour]
        try:
            cleaned = pyclipper.CleanPolygon(path, distance=max(1.0, 0.02 * scale))
        except Exception:
            cleaned = path
        if len(cleaned) >= 3 and abs(pyclipper.Area(cleaned)) > 10:
            paths.append(cleaned)
    if not paths:
        return 0
    clipper = pyclipper.Pyclipper()
    try:
        clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
        tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
    except Exception:
        return len(_contour_groups_by_bbox(valid, 0.12))
    return _count_outer_polytree_nodes(tree)


def _union_contours_for_cutting(contours: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    if pyclipper is None:
        return contours
    scale = 1000
    paths: list[list[tuple[int, int]]] = []
    for contour in contours:
        if len(contour) < 3:
            continue
        path = [(int(round(x * scale)), int(round(y * scale))) for x, y in contour]
        cleaned = pyclipper.CleanPolygon(path, distance=max(1.0, 0.02 * scale))
        if len(cleaned) >= 3 and abs(pyclipper.Area(cleaned)) > 10:
            paths.append(cleaned)
    if not paths:
        return contours
    clipper = pyclipper.Pyclipper()
    clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
    try:
        union_paths = clipper.Execute(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
    except Exception:
        union_paths = pyclipper.SimplifyPolygons(paths, pyclipper.PFT_NONZERO)
    result: list[list[tuple[float, float]]] = []
    for path in union_paths or []:
        if len(path) >= 3:
            result.append([(round(x / scale, 3), round(y / scale, 3)) for x, y in path])
    return result or contours


def _welded_baseline_support_contours(
    contours: list[list[tuple[float, float]]],
    thickness_mm: float = 1.4,
) -> tuple[list[list[tuple[float, float]]], bool]:
    """Weld a thin baseline connector bar across the name so disconnected letter
    pieces fuse into ONE cuttable object (the classic laser script-name "Steg").

    The bar is a filled rectangle spanning the full width; its vertical position
    is auto-tuned across the letter-body band so it actually crosses every piece.
    Returns (welded_contours, single_piece_achieved). Reversible: only invoked
    when the operator turns on `support_line`. Never raises.
    """
    if pyclipper is None or not contours:
        return contours, False
    xs = [x for contour in contours for x, y in contour]
    ys = [y for contour in contours for x, y in contour]
    if not xs:
        return contours, False
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    height = max(1e-6, max_y - min_y)
    half = max(0.5, thickness_mm) / 2.0
    best_contours = contours
    best_count: int | None = None
    # Sweep the letter-body band (font baseline sits ~0.6-0.74 down in this space).
    for frac in (0.66, 0.70, 0.62, 0.74, 0.58):
        y_c = min_y + frac * height
        bar = [
            (round(min_x, 3), round(y_c - half, 3)),
            (round(max_x, 3), round(y_c - half, 3)),
            (round(max_x, 3), round(y_c + half, 3)),
            (round(min_x, 3), round(y_c + half, 3)),
            (round(min_x, 3), round(y_c - half, 3)),
        ]
        welded = _union_contours_for_cutting([*contours, bar])
        count = _real_component_count_via_union(welded)
        if best_count is None or count < best_count:
            best_count = count
            best_contours = welded
        if count == 1:
            return welded, True
    return best_contours, bool(best_count == 1)


def _targeted_stroke_weld_contours(
    contours: list[list[tuple[float, float]]],
    connector_width_mm: float = 0.6,
    max_iterations: int = 18,
) -> list[list[tuple[float, float]]]:
    """Connect near-but-not-touching letter/mark pieces into ONE cuttable path by
    welding the two globally-nearest pieces with a SHORT, THIN connector placed at
    their nearest stroke points (natural flow), then re-unioning — repeated until a
    single piece. This is NOT the old diagonal bbox-centre bridge (that produced the
    bowtie/checkerboard); the connector is short, local to the real nearest points,
    forced CCW so a NONZERO union always ADDS (never subtracts → no checkerboard).
    Bar-free, dot-preserving (dots get a thin neck to their body). Never raises.
    """
    if pyclipper is None or not contours:
        return contours
    scale = 1000

    def to_int(contour: list[tuple[float, float]]) -> list[tuple[int, int]]:
        return [(int(round(x * scale)), int(round(y * scale))) for x, y in contour]

    def union_pieces(src: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
        paths: list[list[tuple[int, int]]] = []
        for contour in src:
            if len(contour) < 3:
                continue
            path = to_int(contour)
            try:
                path = pyclipper.CleanPolygon(path, distance=max(1.0, 0.02 * scale))
            except Exception:
                pass
            if len(path) >= 3 and abs(pyclipper.Area(path)) > 10:
                paths.append(path)
        if not paths:
            return []
        clipper = pyclipper.Pyclipper()
        clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
        try:
            tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
        except Exception:
            return []
        outer_rings: list[list[tuple[float, float]]] = []

        def walk(node: Any) -> None:
            for child in node.Childs:
                if not child.IsHole:
                    outer_rings.append([(x / scale, y / scale) for x, y in child.Contour])
                walk(child)

        walk(tree)
        return outer_rings

    def nearest(ring_a: list[tuple[float, float]], ring_b: list[tuple[float, float]]) -> tuple[float, tuple[float, float], tuple[float, float]]:
        step_a = max(1, len(ring_a) // 140)
        step_b = max(1, len(ring_b) // 140)
        best: tuple[float, tuple[float, float], tuple[float, float]] | None = None
        for ax, ay in ring_a[::step_a]:
            for bx, by in ring_b[::step_b]:
                dist_sq = (ax - bx) ** 2 + (ay - by) ** 2
                if best is None or dist_sq < best[0]:
                    best = (dist_sq, (ax, ay), (bx, by))
        return (math.sqrt(best[0]), best[1], best[2]) if best else (0.0, (0.0, 0.0), (0.0, 0.0))

    def signed_area(poly: list[tuple[float, float]]) -> float:
        total = 0.0
        for i in range(len(poly) - 1):
            total += poly[i][0] * poly[i + 1][1] - poly[i + 1][0] * poly[i][1]
        return total / 2.0

    def connector(point_a: tuple[float, float], point_b: tuple[float, float]) -> list[tuple[float, float]]:
        ax, ay = point_a
        bx, by = point_b
        dx, dy = bx - ax, by - ay
        length = max(1e-6, math.hypot(dx, dy))
        ux, uy = dx / length, dy / length
        half = connector_width_mm / 2
        nx, ny = -uy * half, ux * half
        ext = 1.3  # overrun into each piece so the union solidly merges
        ax -= ux * ext
        ay -= uy * ext
        bx += ux * ext
        by += uy * ext
        quad = [(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny), (ax + nx, ay + ny)]
        if signed_area(quad) < 0:  # force CCW so NONZERO union adds (never subtracts)
            quad = quad[::-1]
        return quad

    current = list(contours)
    for _ in range(max_iterations):
        pieces = union_pieces(current)
        if len(pieces) <= 1:
            break
        best_pair: tuple[float, tuple[float, float], tuple[float, float]] | None = None
        for i in range(len(pieces)):
            for j in range(i + 1, len(pieces)):
                dist, pa, pb = nearest(pieces[i], pieces[j])
                if best_pair is None or dist < best_pair[0]:
                    best_pair = (dist, pa, pb)
        if best_pair is None:
            break
        current.append(connector(best_pair[1], best_pair[2]))
    return _union_contours_for_cutting(current)


def _nearest_bbox_bridge_contour(
    main_bbox: tuple[float, float, float, float],
    part_bbox: tuple[float, float, float, float],
    bridge_width_mm: float,
) -> list[tuple[float, float]]:
    main_cx = (main_bbox[0] + main_bbox[2]) / 2
    main_cy = (main_bbox[1] + main_bbox[3]) / 2
    part_cx = (part_bbox[0] + part_bbox[2]) / 2
    part_cy = (part_bbox[1] + part_bbox[3]) / 2
    start_x = min(max(part_cx, main_bbox[0]), main_bbox[2])
    start_y = min(max(part_cy, main_bbox[1]), main_bbox[3])
    end_x = min(max(start_x, part_bbox[0]), part_bbox[2])
    end_y = min(max(start_y, part_bbox[1]), part_bbox[3])
    if math.hypot(end_x - start_x, end_y - start_y) < 0.001:
        start_x, start_y = main_cx, main_cy
        end_x, end_y = part_cx, part_cy
    dx = end_x - start_x
    dy = end_y - start_y
    length = max(0.001, math.hypot(dx, dy))
    ux = dx / length
    uy = dy / length
    half = max(0.25, bridge_width_mm / 2)
    px = -uy * half
    py = ux * half
    start_x -= ux * half
    start_y -= uy * half
    end_x += ux * half
    end_y += uy * half
    return [
        (round(start_x + px, 3), round(start_y + py, 3)),
        (round(end_x + px, 3), round(end_y + py, 3)),
        (round(end_x - px, 3), round(end_y - py, 3)),
        (round(start_x - px, 3), round(start_y - py, 3)),
        (round(start_x + px, 3), round(start_y + py, 3)),
    ]


def _vertical_designer_bridge_contour(
    x: float,
    start_y: float,
    end_y: float,
    bridge_width_mm: float,
) -> list[tuple[float, float]]:
    half = max(0.09, min(0.18, bridge_width_mm / 2))
    top = min(start_y, end_y)
    bottom = max(start_y, end_y)
    return [
        (round(x - half, 3), round(top, 3)),
        (round(x + half, 3), round(top, 3)),
        (round(x + half, 3), round(bottom, 3)),
        (round(x - half, 3), round(bottom, 3)),
        (round(x - half, 3), round(top, 3)),
    ]


def _designer_mark_bridge_contours_for_text(
    text: str,
    contours: list[list[tuple[float, float]]],
    bridge_width_mm: float = 0.22,
) -> dict[str, Any]:
    """Create short owner-glyph bridges for Turkish marks.

    This deliberately avoids the old nearest-main-bbox bridge, which can draw a
    long diagonal connector through a script word. The bridge is local to the
    glyph's estimated x-band and is allowed only when the mark/body gap is short.
    """
    if not contours or not text:
        return {"bridge_contours": [], "bridge_details": [], "bridge_warnings": []}
    bbox = _contours_bbox(contours)
    if not bbox:
        return {"bridge_contours": [], "bridge_details": [], "bridge_warnings": []}
    min_x, min_y, max_x, max_y = bbox
    word_width = max(1.0, max_x - min_x)
    word_height = max(1.0, max_y - min_y)
    glyphs = [ch for ch in text if ch.strip() and ch != "&"]
    if not glyphs:
        return {"bridge_contours": [], "bridge_details": [], "bridge_warnings": []}
    def glyph_weight(ch: str) -> float:
        if ch in "MWŞĞÜÖÇ":
            return 1.55
        if ch in "SABCDGHKLOPTZ":
            return 1.32
        if ch in "ilıİİt":
            return 0.58
        if ch in "ğgjy":
            return 1.12
        return 1.0

    glyph_weights = [glyph_weight(ch) for ch in glyphs]
    total_weight = max(0.001, sum(glyph_weights))
    weighted_unit_w = word_width / total_weight
    owner_centers: list[float] = []
    cursor_x = min_x
    for weight in glyph_weights:
        owner_centers.append(cursor_x + (weight * weighted_unit_w / 2))
        cursor_x += weight * weighted_unit_w
    segment_w = word_width / max(1, len(glyphs))
    contour_rows: list[dict[str, Any]] = []
    for index, contour in enumerate(contours):
        contour_bbox = _contour_bbox(contour)
        if not contour_bbox:
            continue
        cmin_x, cmin_y, cmax_x, cmax_y = contour_bbox
        contour_rows.append(
            {
                "index": index,
                "bbox": contour_bbox,
                "cx": (cmin_x + cmax_x) / 2,
                "cy": (cmin_y + cmax_y) / 2,
                "w": max(0.0, cmax_x - cmin_x),
                "h": max(0.0, cmax_y - cmin_y),
                "area": _contour_area_mm2(contour),
            }
        )
    bridge_contours: list[list[tuple[float, float]]] = []
    bridge_details: list[dict[str, Any]] = []
    warnings: list[str] = []
    upper_mark_candidates = sorted(
        [
            row for row in contour_rows
            if float(row["cy"]) <= min_y + word_height * 0.58
            and float(row["area"]) <= 80.0
            and float(row["w"]) <= 13.0
            and float(row["h"]) <= 13.0
        ],
        key=lambda row: (float(row["cx"]), float(row["cy"])),
    )
    used_mark_indexes: set[int] = set()
    for glyph_index, ch in enumerate(glyphs):
        if ch not in TURKISH_DIACRITIC_CHARS:
            continue
        owner_cx = owner_centers[glyph_index] if glyph_index < len(owner_centers) else min_x + (glyph_index + 0.5) * segment_w
        x_margin = max(4.0, weighted_unit_w * max(0.85, glyph_weights[glyph_index] if glyph_index < len(glyph_weights) else 1.0) * 1.45)
        if ch in TURKISH_DOT_MARK_CHARS or ch in TURKISH_BREVE_MARK_CHARS:
            if ch in TURKISH_DOT_MARK_CHARS:
                bridge_width = max(0.18, min(0.24, bridge_width_mm))
                max_len = 3.5
                mark_kind = "dot"
                expected_mark_count = 2 if ch in set("öÖüÜ") else 1
            else:
                bridge_width = max(0.20, min(0.25, bridge_width_mm))
                max_len = 3.5
                mark_kind = "breve"
                expected_mark_count = 1
            owner_mark_candidates = [
                candidate for candidate in upper_mark_candidates
                if int(candidate["index"]) not in used_mark_indexes
                and abs(float(candidate["cx"]) - owner_cx) <= x_margin
            ]
            owner_mark_candidates = sorted(
                owner_mark_candidates,
                key=lambda row: (abs(float(row["cx"]) - owner_cx), float(row["cy"]), -float(row["area"])),
            )
            selected_marks = owner_mark_candidates[:expected_mark_count]
            if len(selected_marks) < expected_mark_count and expected_mark_count > 1:
                expanded = [
                    candidate for candidate in upper_mark_candidates
                    if int(candidate["index"]) not in used_mark_indexes
                    and abs(float(candidate["cx"]) - owner_cx) <= max(x_margin * 2.2, segment_w * 2.6)
                ]
                expanded = sorted(
                    expanded,
                    key=lambda row: (abs(float(row["cx"]) - owner_cx), float(row["cy"]), -float(row["area"])),
                )
                selected_marks = expanded[:expected_mark_count]
            if len(selected_marks) < expected_mark_count:
                fallback = [
                    candidate for candidate in upper_mark_candidates
                    if int(candidate["index"]) not in used_mark_indexes
                ]
                fallback = sorted(
                    fallback,
                    key=lambda row: (abs(float(row["cx"]) - owner_cx), float(row["cy"]), -float(row["area"])),
                )
                selected_marks = fallback[:expected_mark_count]
            if len(selected_marks) < expected_mark_count:
                warning_key = "detached_dot" if mark_kind == "dot" else "detached_breve"
                warnings.append(f"{warning_key}:{ch}:not_found")
                continue
            for selected_mark in selected_marks:
                used_mark_indexes.add(int(selected_mark["index"]))
            for mark in selected_marks:
                mark_bbox = mark["bbox"]
                mark_bottom = float(mark_bbox[3])
                body_candidates = [
                    row for row in contour_rows
                    if row["index"] != mark["index"]
                    and row["area"] > mark["area"] * 2.5
                    and float(row["bbox"][3]) > mark_bottom
                    and (
                        float(row["bbox"][0]) - 4.0 <= float(mark["cx"]) <= float(row["bbox"][2]) + 4.0
                        or abs(float(row["cx"]) - float(mark["cx"])) <= max(7.0, segment_w * 1.15)
                    )
                ]
                if not body_candidates:
                    warnings.append(f"mark_not_connected_to_owner_body:{ch}:{mark_kind}")
                    continue
                body = sorted(body_candidates, key=lambda row: max(0.0, float(row["bbox"][1]) - mark_bottom))[0]
                target_y = max(mark_bottom + 0.35, min(float(body["bbox"][1]) + 0.55, mark_bottom + max_len))
                bridge_len = abs(target_y - mark_bottom)
                if bridge_len > max_len:
                    warnings.append(f"bridge_too_long:{ch}:{round(bridge_len, 2)}mm")
                    continue
                bridge_x = float(mark["cx"])
                bridge_contours.append(_vertical_designer_bridge_contour(bridge_x, mark_bottom - 0.10, target_y + 0.12, bridge_width))
                bridge_details.append(
                    {
                        "glyph": ch,
                        "glyphIndex": glyph_index,
                        "markType": mark_kind,
                        "connectTo": f"{ch}_owner_body",
                        "bridgeLengthMm": round(bridge_len, 3),
                        "bridgeWidthMm": round(bridge_width, 3),
                        "bridgeUnionedIntoFinalPath": True,
                        "markConnectedToOwnerBody": True,
                        "markConnectedToWrongGlyph": False,
                        "attachedToWrongGlyph": False,
                    }
                )
        elif ch in TURKISH_TAIL_MARK_CHARS:
            bridge_width = max(0.25, min(0.30, bridge_width_mm))
            max_len = 3.5
            tail_candidates = [
                row for row in contour_rows
                if abs(float(row["cx"]) - owner_cx) <= x_margin
                and float(row["cy"]) >= min_y + word_height * 0.48
                and (float(row["w"]) <= max(7.0, segment_w * 0.95) or float(row["area"]) <= 40.0)
            ]
            tail_candidates = sorted(tail_candidates, key=lambda row: (-float(row["cy"]), abs(float(row["cx"]) - owner_cx)))
            if not tail_candidates:
                bridge_details.append(
                    {
                        "glyph": ch,
                        "glyphIndex": glyph_index,
                        "markType": "cedilla",
                        "connectTo": f"{ch}_owner_lower_body",
                        "bridgeLengthMm": 0,
                        "bridgeWidthMm": round(bridge_width, 3),
                        "alreadyIntegrated": True,
                        "bridgeUnionedIntoFinalPath": True,
                        "markConnectedToOwnerBody": True,
                        "markConnectedToWrongGlyph": False,
                        "attachedToWrongGlyph": False,
                    }
                )
                continue
            for tail in tail_candidates[:1]:
                tail_bbox = tail["bbox"]
                tail_top = float(tail_bbox[1])
                body_candidates = [
                    row for row in contour_rows
                    if row["index"] != tail["index"]
                    and row["area"] > tail["area"] * 2.0
                    and float(row["bbox"][1]) < tail_top
                    and abs(float(row["cx"]) - float(tail["cx"])) <= max(8.0, segment_w * 1.2)
                ]
                if not body_candidates:
                    warnings.append(f"detached_cedilla:{ch}")
                    continue
                body = sorted(body_candidates, key=lambda row: max(0.0, tail_top - float(row["bbox"][3])))[0]
                target_y = min(tail_top - 0.35, max(float(body["bbox"][3]) - 0.55, tail_top - max_len))
                bridge_len = abs(tail_top - target_y)
                if bridge_len > max_len:
                    warnings.append(f"bridge_too_long:{ch}:{round(bridge_len, 2)}mm")
                    continue
                bridge_x = float(tail["cx"])
                bridge_contours.append(_vertical_designer_bridge_contour(bridge_x, target_y - 0.12, tail_top + 0.10, bridge_width))
                bridge_details.append(
                    {
                        "glyph": ch,
                        "glyphIndex": glyph_index,
                        "markType": "cedilla",
                        "connectTo": f"{ch}_owner_lower_body",
                        "bridgeLengthMm": round(bridge_len, 3),
                        "bridgeWidthMm": round(bridge_width, 3),
                        "bridgeUnionedIntoFinalPath": True,
                        "markConnectedToOwnerBody": True,
                        "markConnectedToWrongGlyph": False,
                        "attachedToWrongGlyph": False,
                    }
                )
    return {"bridge_contours": bridge_contours, "bridge_details": bridge_details, "bridge_warnings": warnings}


def _expected_turkish_mark_specs(text: str) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    glyphs = [ch for ch in str(text or "") if ch.strip() and ch != "&"]
    for glyph_index, ch in enumerate(glyphs):
        if ch in set("öÖüÜ"):
            specs.append({"glyph": ch, "glyphIndex": glyph_index, "markType": "dot", "expectedCount": 2})
        elif ch in set("iİ"):
            specs.append({"glyph": ch, "glyphIndex": glyph_index, "markType": "dot", "expectedCount": 1})
        elif ch in TURKISH_BREVE_MARK_CHARS:
            specs.append({"glyph": ch, "glyphIndex": glyph_index, "markType": "breve", "expectedCount": 1})
        elif ch in TURKISH_TAIL_MARK_CHARS:
            specs.append({"glyph": ch, "glyphIndex": glyph_index, "markType": "cedilla", "expectedCount": 1})
    return specs


def _final_geometry_connectivity_analysis(
    text: str,
    final_contours: list[list[tuple[float, float]]],
    bridge_contours: list[list[tuple[float, float]]],
    bridge_details: list[dict[str, Any]],
    bridge_warnings: list[str],
) -> dict[str, Any]:
    groups = _contour_groups_by_bbox(final_contours, 0.12)
    components = _analysis_bbox_from_groups(final_contours, groups)
    # Faz4-fix (2026-05-27): authoritative connectivity = real geometric union
    # count, not bbox proximity. One real component => everything (incl. fused
    # Turkish marks) is connected.
    _real_count = _real_component_count_via_union(final_contours) if final_contours else 0
    component_count = _real_count if _real_count > 0 else len(components)
    detail_counts: dict[tuple[str, int, str], int] = {}
    owner_map: list[dict[str, Any]] = []
    for detail in bridge_details or []:
        glyph = str(detail.get("glyph") or "")
        glyph_index = int(detail.get("glyphIndex") if detail.get("glyphIndex") is not None else -1)
        mark_type = str(detail.get("markType") or "")
        key = (glyph, glyph_index, mark_type)
        detail_counts[key] = detail_counts.get(key, 0) + 1
        owner_map.append(
            {
                "glyph": glyph,
                "glyphIndex": glyph_index,
                "markType": mark_type,
                "connectedToOwner": bool(detail.get("markConnectedToOwnerBody", True)),
                "connectedToWrongGlyph": bool(detail.get("markConnectedToWrongGlyph") or detail.get("attachedToWrongGlyph")),
                "bridgeUnioned": bool(detail.get("bridgeUnionedIntoFinalPath", bool(bridge_contours))),
                "bridgeLengthMm": detail.get("bridgeLengthMm"),
                "bridgeWidthMm": detail.get("bridgeWidthMm"),
            }
        )
    # Informational (non-blocking) notes from the bowtie-fix (artefact bridges
    # off by default) — these are not geometry failures.
    _info_warnings = {
        "initial_letter_connection_off_by_default_bowtie_fix",
        "letter_flow_bridge_off_by_default_bowtie_fix",
    }
    errors = [str(warning) for warning in (bridge_warnings or []) if str(warning) not in _info_warnings]
    # Faz4-fix: a single real component proves every mark is connected, so incoming
    # "detached"/"not-unioned" mark warnings are provable false positives here.
    if component_count == 1:
        errors = [
            e for e in errors
            if e.split(":", 1)[0] not in {
                "detached_dot", "detached_breve", "detached_cedilla",
                "bridge_not_unioned_into_final_path", "mark_not_connected_to_owner_body",
            }
        ]
    # Faz4-fix: detached-mark detection via bridge-detail counting is INVALID for
    # the v15 fused-glyph font — a Turkish mark is fused into its body (no separate
    # bridge detail) yet stays connected. The authoritative test is the real
    # component count: if everything unions into ONE piece, no mark can be detached.
    # So mark counts are advisory only; they never block when component_count == 1.
    detached_dot_count = 0
    detached_breve_count = 0
    detached_cedilla_count = 0
    if component_count > 1:
        for spec in _expected_turkish_mark_specs(text):
            key = (str(spec["glyph"]), int(spec["glyphIndex"]), str(spec["markType"]))
            missing = max(0, int(spec["expectedCount"]) - detail_counts.get(key, 0))
            if not missing:
                continue
            if spec["markType"] == "dot":
                detached_dot_count += missing
            elif spec["markType"] == "breve":
                detached_breve_count += missing
            elif spec["markType"] == "cedilla":
                detached_cedilla_count += missing
        # Honest primary reason for a multi-piece name: the letters are not unified.
        errors.append(f"same_name_components_not_unified:{component_count}")
    wrong_glyph = any(row.get("connectedToWrongGlyph") for row in owner_map)
    if wrong_glyph:
        errors.append("bridge_attached_to_wrong_glyph")
    passed = component_count == 1 and not errors
    return {
        "finalGeometryConnectivityPassed": passed,
        "final_geometry_connectivity_passed": passed,
        "finalGeometryConnectivityStatus": "geometry_connectivity_passed" if passed else str(errors[0] if errors else "geometry_connectivity_failed"),
        "final_geometry_connectivity_status": "geometry_connectivity_passed" if passed else str(errors[0] if errors else "geometry_connectivity_failed"),
        "connectedComponentCount": component_count,
        "connected_component_count": component_count,
        "detachedMarkComponents": max(0, component_count - 1),
        "detached_mark_components": max(0, component_count - 1),
        "detachedDotCount": detached_dot_count,
        "detached_dot_count": detached_dot_count,
        "detachedBreveCount": detached_breve_count,
        "detached_breve_count": detached_breve_count,
        "detachedCedillaCount": detached_cedilla_count,
        "detached_cedilla_count": detached_cedilla_count,
        "ownerGlyphConnectionMap": owner_map,
        "owner_glyph_connection_map": owner_map,
        "markConnectedToOwnerBody": bool(owner_map) and all(row.get("connectedToOwner") for row in owner_map),
        "mark_connected_to_owner_body": bool(owner_map) and all(row.get("connectedToOwner") for row in owner_map),
        "markConnectedToWrongGlyph": wrong_glyph,
        "mark_connected_to_wrong_glyph": wrong_glyph,
        "bridgePathUnionedIntoFinalPath": bool(bridge_contours) and component_count == 1,
        "bridge_path_unioned_into_final_path": bool(bridge_contours) and component_count == 1,
        "finalFilledSilhouetteConnected": component_count == 1,
        "final_filled_silhouette_connected": component_count == 1,
        "finalGeometryConnectivityErrors": list(dict.fromkeys(errors)),
        "final_geometry_connectivity_errors": list(dict.fromkeys(errors)),
        "pathComponentCountTable": components[:12],
        "path_component_count_table": components[:12],
    }


def _smart_bridge_same_name_contours(
    contours: list[list[tuple[float, float]]],
    offset_mm: float,
    enabled: bool = True,
    bridge_width_mm: float | None = None,
) -> dict[str, Any]:
    groups = _contour_groups_by_bbox(contours, 0.12)
    components = _analysis_bbox_from_groups(contours, groups)
    if not enabled or pyclipper is None or len(components) <= 1:
        return {
            "contours": _union_contours_for_cutting(contours),
            "bridge_contours": [],
            "component_count_before": len(components),
            "bridged_part_count": 0,
            "unresolved_part_count": max(0, len(components) - 1),
            "smart_bridge_warnings": [] if len(components) <= 1 else ["smart_bridge_disabled_or_pyclipper_missing"],
        }
    main = components[0]
    main_bbox = tuple(float(value) for value in main["bbox"])
    bridge_width = max(0.05, float(bridge_width_mm)) if bridge_width_mm is not None else max(0.9, float(offset_mm or 0.0) * 1.35)
    max_bridge_gap = 6.0
    bridge_contours: list[list[tuple[float, float]]] = []
    unresolved = 0
    warnings: list[str] = []
    for component in components[1:]:
        part_bbox = tuple(float(value) for value in component["bbox"])
        gap = _bbox_gap_mm(main_bbox, part_bbox)
        if gap > max_bridge_gap:
            unresolved += 1
            warnings.append(f"smart_bridge_gap_too_large:{component.get('index')}:{round(gap, 2)}mm")
            continue
        bridge_contours.append(_nearest_bbox_bridge_contour(main_bbox, part_bbox, bridge_width))
    welded = _union_contours_for_cutting([*contours, *bridge_contours]) if bridge_contours else _union_contours_for_cutting(contours)
    return {
        "contours": welded,
        "bridge_contours": bridge_contours,
        "component_count_before": len(components),
        "bridged_part_count": len(bridge_contours),
        "unresolved_part_count": unresolved,
        "smart_bridge_warnings": warnings,
    }


def _initial_letter_connection_reinforcement_contours(
    text: str,
    contours: list[list[tuple[float, float]]],
    bridge_width_mm: float = 0.28,
) -> dict[str, Any]:
    """Create a contour-tracing diagonal fill bridge at the capital-to-lowercase junction.

    Script capitals (M, S, etc.) often have their exit stroke at a different height
    than the entry of the following lowercase letter.  A simple rectangular patch
    cannot bridge the diagonal gap.  This function scans the junction zone at
    multiple height levels, finds the rightmost extent of the capital and leftmost
    extent of the lowercase at each level, and creates a polygon that traces the
    gap between them — filling in thin or missing material diagonally.

    The result is a contour that, after union/weld, makes the filled silhouette look
    like one continuous script stroke from capital to lowercase.
    """
    result_empty: dict[str, Any] = {"bridge_contours": [], "details": [], "warnings": []}
    if not contours or not text or len(text) < 2:
        return result_empty
    first_char = text[0]
    second_char = text[1] if len(text) > 1 else ""
    if not first_char.isupper() or second_char.isspace():
        return result_empty

    bbox_all = _contours_bbox(contours)
    if not bbox_all:
        return result_empty
    word_min_x, word_min_y, word_max_x, word_max_y = bbox_all
    word_w = max(1.0, word_max_x - word_min_x)
    word_h = max(1.0, word_max_y - word_min_y)

    glyphs = [ch for ch in text if ch.strip()]
    if len(glyphs) < 2:
        return result_empty

    def _gw(ch: str) -> float:
        if ch in "MW\u015e\u011e\u00dc\u00d6\u00c7mw":
            return 1.55
        if ch.isupper():
            return 1.32
        if ch in "il\u0131\u0130t":
            return 0.58
        return 1.0

    weights = [_gw(ch) for ch in glyphs]
    total_w = max(0.001, sum(weights))
    unit = word_w / total_w
    junction_cx = word_min_x + weights[0] * unit

    # Scan zone: wider than junction to find actual contour edges.
    scan_radius = max(5.0, unit * 0.7)

    # Index all contour points for fast lookup by y-band.
    all_points: list[tuple[float, float]] = []
    for contour in contours:
        all_points.extend(contour)

    # Scan at multiple height levels (20%-80%) to trace the gap profile.
    n_levels = 12
    overlap_margin = max(0.2, bridge_width_mm * 0.7)
    left_profile: list[tuple[float, float]] = []   # (x, y) — right edge of capital
    right_profile: list[tuple[float, float]] = []   # (x, y) — left edge of lowercase
    gap_found = False

    for i in range(n_levels):
        pct = 0.20 + (0.60 * i / max(1, n_levels - 1))   # 20% to 80%
        y_level = word_min_y + word_h * pct
        y_band = max(0.8, word_h * 0.04)

        left_max_x = None
        right_min_x = None

        for px, py in all_points:
            if abs(py - y_level) > y_band:
                continue
            if junction_cx - scan_radius <= px < junction_cx + 0.5:
                if left_max_x is None or px > left_max_x:
                    left_max_x = px
            if junction_cx - 0.5 <= px <= junction_cx + scan_radius:
                if right_min_x is None or px < right_min_x:
                    right_min_x = px

        if left_max_x is not None and right_min_x is not None:
            gap = right_min_x - left_max_x
            if gap > 0.3:
                gap_found = True
            # Add overlap margin to ensure solid union.
            left_profile.append((round(left_max_x + overlap_margin, 3), round(y_level, 3)))
            right_profile.append((round(right_min_x - overlap_margin, 3), round(y_level, 3)))
        elif left_max_x is not None:
            # Only capital exists — extend rightward.
            left_profile.append((round(left_max_x + overlap_margin, 3), round(y_level, 3)))
            right_profile.append((round(left_max_x + overlap_margin + 1.0, 3), round(y_level, 3)))
            gap_found = True
        elif right_min_x is not None:
            # Only lowercase exists — extend leftward.
            left_profile.append((round(right_min_x - overlap_margin - 1.0, 3), round(y_level, 3)))
            right_profile.append((round(right_min_x - overlap_margin, 3), round(y_level, 3)))
            gap_found = True

    if not gap_found or len(left_profile) < 3 or len(right_profile) < 3:
        return result_empty

    # Build polygon: go down the left profile, then back up the right profile.
    polygon: list[tuple[float, float]] = []
    polygon.extend(left_profile)
    polygon.extend(reversed(right_profile))
    polygon.append(left_profile[0])  # close

    details = [{
        "pair": f"{first_char}:{second_char}",
        "type": "contour_tracing_diagonal_fill",
        "junctionX": round(junction_cx, 3),
        "levels": n_levels,
        "gapLevelsFound": len(left_profile),
        "flowZone": "20_to_80_pct",
    }]
    return {"bridge_contours": [polygon], "details": details, "warnings": []}


def _designer_letter_flow_bridge_contour(
    left_bbox: tuple[float, float, float, float],
    right_bbox: tuple[float, float, float, float],
    bridge_width_mm: float,
) -> list[tuple[float, float]]:
    lx1, ly1, lx2, ly2 = left_bbox
    rx1, ry1, rx2, ry2 = right_bbox
    overlap_left = max(lx1, rx1)
    overlap_right = min(lx2, rx2)
    lower_y = min(ly2, ry2) - max(0.8, min(2.2, min(max(1.0, ly2 - ly1), max(1.0, ry2 - ry1)) * 0.18))
    half = max(0.11, min(0.16, bridge_width_mm / 2))
    if overlap_right > overlap_left:
        mid_x = (overlap_left + overlap_right) / 2
        x1 = mid_x - max(0.45, bridge_width_mm * 2.2)
        x2 = mid_x + max(0.45, bridge_width_mm * 2.2)
    else:
        x1 = lx2 - 0.18
        x2 = rx1 + 0.18
    return [
        (round(x1, 3), round(lower_y - half, 3)),
        (round(x2, 3), round(lower_y - half, 3)),
        (round(x2, 3), round(lower_y + half, 3)),
        (round(x1, 3), round(lower_y + half, 3)),
        (round(x1, 3), round(lower_y - half, 3)),
    ]


def _point_to_point_bridge_contour(
    start: tuple[float, float],
    end: tuple[float, float],
    bridge_width_mm: float,
) -> list[tuple[float, float]]:
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    length = max(0.001, math.hypot(dx, dy))
    ux = dx / length
    uy = dy / length
    half = max(0.11, min(0.16, bridge_width_mm / 2))
    px = -uy * half
    py = ux * half
    sx -= ux * half
    sy -= uy * half
    ex += ux * half
    ey += uy * half
    return [
        (round(sx + px, 3), round(sy + py, 3)),
        (round(ex + px, 3), round(ey + py, 3)),
        (round(ex - px, 3), round(ey - py, 3)),
        (round(sx - px, 3), round(sy - py, 3)),
        (round(sx + px, 3), round(sy + py, 3)),
    ]


def _closest_points_between_contour_groups(
    contours: list[list[tuple[float, float]]],
    left_group: list[int],
    right_group: list[int],
) -> tuple[tuple[float, float], tuple[float, float], float] | None:
    def group_bbox(group: list[int]) -> tuple[float, float, float, float] | None:
        bboxes = [_contour_bbox(contours[index]) for index in group]
        bboxes = [bbox for bbox in bboxes if bbox is not None]
        if not bboxes:
            return None
        return (
            min(bbox[0] for bbox in bboxes),
            min(bbox[1] for bbox in bboxes),
            max(bbox[2] for bbox in bboxes),
            max(bbox[3] for bbox in bboxes),
        )

    left_bbox = group_bbox(left_group)
    right_bbox = group_bbox(right_group)
    left_points: list[tuple[float, float]] = []
    right_points: list[tuple[float, float]] = []
    for index in left_group:
        left_points.extend(contours[index][:: max(1, len(contours[index]) // 90)])
    for index in right_group:
        right_points.extend(contours[index][:: max(1, len(contours[index]) // 90)])
    if left_bbox and right_bbox:
        left_lower_y = left_bbox[1] + (left_bbox[3] - left_bbox[1]) * 0.48
        right_lower_y = right_bbox[1] + (right_bbox[3] - right_bbox[1]) * 0.48
        left_lower = [point for point in left_points if point[1] >= left_lower_y]
        right_lower = [point for point in right_points if point[1] >= right_lower_y]
        if len(left_lower) >= 3 and len(right_lower) >= 3:
            left_points = left_lower
            right_points = right_lower
    if not left_points or not right_points:
        return None
    best_start = left_points[0]
    best_end = right_points[0]
    best_distance = float("inf")
    for p1 in left_points:
        for p2 in right_points:
            distance = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if distance < best_distance:
                best_distance = distance
                best_start = p1
                best_end = p2
    return best_start, best_end, best_distance


def _designer_letter_flow_bridge_same_name_contours(
    contours: list[list[tuple[float, float]]],
    bridge_width_mm: float = 0.25,
) -> dict[str, Any]:
    groups = _contour_groups_by_bbox(contours, 0.12)
    components = _analysis_bbox_from_groups(contours, groups)
    component_records: list[dict[str, Any]] = []
    for group in groups:
        bboxes = [_contour_bbox(contours[index]) for index in group]
        bboxes = [bbox for bbox in bboxes if bbox is not None]
        if not bboxes:
            continue
        component_records.append(
            {
                "group": group,
                "bbox": [
                    min(bbox[0] for bbox in bboxes),
                    min(bbox[1] for bbox in bboxes),
                    max(bbox[2] for bbox in bboxes),
                    max(bbox[3] for bbox in bboxes),
                ],
                "area": sum(_contour_area_mm2(contours[index]) for index in group),
            }
        )
    if pyclipper is None or len(components) <= 1:
        return {
            "contours": _union_contours_for_cutting(contours),
            "bridge_contours": [],
            "component_count_before": len(components),
            "bridged_part_count": 0,
            "unresolved_part_count": max(0, len(components) - 1),
            "smart_bridge_warnings": [] if len(components) <= 1 else ["letter_flow_bridge_pyclipper_missing"],
        }
    ordered = sorted(component_records, key=lambda row: (float(row["bbox"][0]), float(row["bbox"][1])))
    bridge_contours: list[list[tuple[float, float]]] = []
    warnings: list[str] = []
    for left, right in zip(ordered, ordered[1:]):
        left_bbox = tuple(float(value) for value in left["bbox"])
        right_bbox = tuple(float(value) for value in right["bbox"])
        horizontal_gap = max(0.0, right_bbox[0] - left_bbox[2])
        vertical_gap = max(0.0, max(left_bbox[1], right_bbox[1]) - min(left_bbox[3], right_bbox[3]))
        if horizontal_gap > 7.0 or vertical_gap > 7.0:
            warnings.append(f"letter_flow_bridge_gap_too_large:{round(max(horizontal_gap, vertical_gap), 2)}mm")
            continue
        closest = _closest_points_between_contour_groups(contours, left["group"], right["group"])
        if closest is None:
            bridge_contours.append(
                _designer_letter_flow_bridge_contour(left_bbox, right_bbox, max(0.24, min(0.30, bridge_width_mm)))
            )
            continue
        start, end, distance = closest
        if distance > 7.0:
            warnings.append(f"letter_flow_bridge_gap_too_large:{round(distance, 2)}mm")
            continue
        bridge_contours.append(_point_to_point_bridge_contour(start, end, max(0.24, min(0.30, bridge_width_mm))))
    welded = _union_contours_for_cutting([*contours, *bridge_contours]) if bridge_contours else _union_contours_for_cutting(contours)
    after_components = _analysis_bbox_from_groups(welded, _contour_groups_by_bbox(welded, 0.12))
    return {
        "contours": welded,
        "bridge_contours": bridge_contours,
        "component_count_before": len(components),
        "bridged_part_count": len(bridge_contours),
        "unresolved_part_count": max(0, len(after_components) - 1),
        "smart_bridge_warnings": warnings,
    }


def _analysis_bbox_from_groups(contours: list[list[tuple[float, float]]], groups: list[list[int]]) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for group in groups:
        bboxes = [_contour_bbox(contours[index]) for index in group]
        bboxes = [bbox for bbox in bboxes if bbox is not None]
        if not bboxes:
            continue
        min_x = min(bbox[0] for bbox in bboxes)
        min_y = min(bbox[1] for bbox in bboxes)
        max_x = max(bbox[2] for bbox in bboxes)
        max_y = max(bbox[3] for bbox in bboxes)
        area = sum(_contour_area_mm2(contours[index]) for index in group)
        components.append(
            {
                "index": len(components) + 1,
                "contour_count": len(group),
                "bbox": [round(min_x, 3), round(min_y, 3), round(max_x, 3), round(max_y, 3)],
                "width_mm": round(max(0.0, max_x - min_x), 3),
                "height_mm": round(max(0.0, max_y - min_y), 3),
                "area_mm2": round(area, 3),
            }
        )
    return sorted(components, key=lambda component: component.get("area_mm2", 0), reverse=True)


def _name_cut_auto_repair_analysis(
    item: dict[str, Any],
    cfg: dict[str, Any],
    contours: list[list[tuple[float, float]]],
) -> dict[str, Any]:
    text = str(item.get("preview_text") or item.get("name_text") or item.get("text") or item.get("name") or "")
    offset_mm = max(0.0, min(5.0, float(item.get("offset_mm") or cfg.get("offset_mm") or 0)))
    style = item.get("style") or item.get("font_family") or cfg.get("font_family") or ""
    font_path = _font_path_for_style(style)
    missing_glyph_chars = _missing_or_fallback_glyph_chars(text, str(font_path)) if font_path.exists() else list(dict.fromkeys(ch for ch in text if ch.strip()))
    has_turkish_marks = any(ch in TURKISH_DIACRITIC_CHARS for ch in text)
    near_gap = max(0.12, min(1.25, (offset_mm * 2.0) + 0.18))
    groups = _contour_groups_by_bbox(contours, near_gap)
    components = _analysis_bbox_from_groups(contours, groups)
    bbox = None
    analysis_height_mm = 0.0
    if contours:
        contour_bboxes = [_contour_bbox(contour) for contour in contours]
        contour_bboxes = [candidate for candidate in contour_bboxes if candidate is not None]
        if contour_bboxes:
            min_x = min(candidate[0] for candidate in contour_bboxes)
            min_y = min(candidate[1] for candidate in contour_bboxes)
            max_x = max(candidate[2] for candidate in contour_bboxes)
            max_y = max(candidate[3] for candidate in contour_bboxes)
            bbox = [round(min_x, 3), round(min_y, 3), round(max_x, 3), round(max_y, 3)]
            analysis_height_mm = max(0.0, max_y - min_y)
    # Bowtie-fix wiring (2026-05-27): bbox proximity grouping falsely merges
    # nearby-but-disconnected pieces into a single fake "component" (legacy
    # _contour_groups_by_bbox). The real geometric union count drives honest
    # readiness — a name is only single-piece if its contours actually weld.
    bbox_component_count = len(components)
    component_count = _real_component_count_via_union(contours) if contours else 0
    if component_count <= 0:
        component_count = bbox_component_count
    main_area = components[0]["area_mm2"] if components else 0.0
    small_components = [
        component for component in components[1:]
        if component.get("area_mm2", 0) < max(1.2, main_area * 0.045)
        or component.get("width_mm", 0) < 2.2
        or component.get("height_mm", 0) < 2.2
    ]
    detached_parts = [
        {
            "component": component.get("index"),
            "widthMm": component.get("width_mm"),
            "heightMm": component.get("height_mm"),
            "areaMm2": component.get("area_mm2"),
        }
        for component in components[1:8]
    ]
    has_detached = component_count > 1
    has_detached_dots = has_turkish_marks and bool(small_components or has_detached)
    has_tail_risk = bool(has_detached and any(ch in text for ch in "çÇşŞğĞ"))
    repair_messages: list[str] = []
    if _script_connection_mode_for_style(style) != "none" and len(text.replace(" ", "")) > 1:
        repair_messages.append("kerning_fixed")
    if offset_mm > 0:
        repair_messages.append("offset_applied")
    if offset_mm > 0 and pyclipper is not None:
        repair_messages.append("weld_applied")
    if has_turkish_marks:
        repair_messages.append("marks_attached")
    if item.get("width_mm") or item.get("height_mm"):
        repair_messages.append("size_normalized")
    repair_messages = list(dict.fromkeys(repair_messages))
    actual_height_mm = analysis_height_mm or _safe_optional_float(item.get("actual_path_height_mm")) or 0.0
    min_visual_height_mm = 18.0
    too_small_for_cut = bool(actual_height_mm and actual_height_mm < min_visual_height_mm)
    has_required_offset_engine = offset_mm <= 0 or pyclipper is not None
    ready_for_cut = bool(contours) and component_count == 1 and not too_small_for_cut and has_required_offset_engine and not missing_glyph_chars
    if not contours:
        repair_status = "failed"
    elif ready_for_cut and repair_messages:
        repair_status = "auto_repaired"
    elif ready_for_cut:
        repair_status = "clean"
    else:
        repair_status = "failed"
    offset_mode = "none"
    if offset_mm > 0:
        offset_mode = "real_path_offset" if pyclipper is not None else "simulation_bbox_offset"
    warnings: list[str] = []
    if not contours:
        warnings.append("path_missing")
    if component_count > 1:
        warnings.append("same_name_components_not_unified")
    if has_detached_dots:
        warnings.append("detached_dot_or_mark_risk")
    if has_tail_risk:
        warnings.append("tail_mark_connection_risk")
    if too_small_for_cut:
        warnings.append(f"actual_path_height_below_minimum:{round(actual_height_mm, 2)}mm")
    if offset_mm > 0 and pyclipper is None:
        warnings.append("offset_simulation_only")
    if missing_glyph_chars:
        warnings.append("font_missing_or_fallback_glyphs:" + "".join(missing_glyph_chars))
    return {
        "componentCount": component_count,
        "component_count": component_count,
        "bboxComponentCount": bbox_component_count,
        "bbox_component_count": bbox_component_count,
        "components": components[:12],
        "detachedParts": detached_parts,
        "detached_parts": detached_parts,
        "smallIslandCount": len(small_components),
        "small_island_count": len(small_components),
        "hasDetachedDots": has_detached_dots,
        "has_detached_dots": has_detached_dots,
        "hasDisconnectedLetters": has_detached,
        "has_disconnected_letters": has_detached,
        "isConnectedPath": ready_for_cut,
        "is_connected_path": ready_for_cut,
        "dotRisk": has_detached_dots,
        "dot_risk": has_detached_dots,
        "tailRisk": has_tail_risk,
        "tail_risk": has_tail_risk,
        "needsWeld": has_detached,
        "needs_weld": has_detached,
        "appliedKerningFix": "kerning_fixed" in repair_messages,
        "applied_kerning_fix": "kerning_fixed" in repair_messages,
        "appliedOffsetMm": round(offset_mm, 3),
        "applied_offset_mm": round(offset_mm, 3),
        "appliedWeld": "weld_applied" in repair_messages,
        "applied_weld": "weld_applied" in repair_messages,
        "appliedDotBridge": "marks_attached" in repair_messages,
        "applied_dot_bridge": "marks_attached" in repair_messages,
        "autoRepaired": repair_status == "auto_repaired",
        "auto_repaired": repair_status == "auto_repaired",
        "repairStatus": repair_status,
        "repair_status": repair_status,
        "repairMessages": repair_messages,
        "repair_messages": repair_messages,
        "readyForCut": ready_for_cut,
        "ready_for_cut": ready_for_cut,
        "offsetMode": offset_mode,
        "offset_mode": offset_mode,
        "repairWarnings": warnings,
        "repair_warnings": warnings,
        "missingGlyphChars": missing_glyph_chars,
        "missing_glyph_chars": missing_glyph_chars,
        "analysisBBox": bbox,
        "analysis_bbox": bbox,
        "validationMode": "AUTO_REPAIR_PIPELINE_FONTTOOLS_PYCLIPPER" if pyclipper is not None else "AUTO_REPAIR_PIPELINE_FONTTOOLS_SIMULATION_OFFSET",
    }


def _contours_bbox(contours: list[list[tuple[float, float]]]) -> tuple[float, float, float, float] | None:
    bboxes = [_contour_bbox(contour) for contour in contours if contour]
    bboxes = [bbox for bbox in bboxes if bbox is not None]
    if not bboxes:
        return None
    return (
        min(bbox[0] for bbox in bboxes),
        min(bbox[1] for bbox in bboxes),
        max(bbox[2] for bbox in bboxes),
        max(bbox[3] for bbox in bboxes),
    )


def _contours_area_mm2(contours: list[list[tuple[float, float]]]) -> float:
    return sum(_contour_area_mm2(contour) for contour in contours)


def _long_thin_artifact_count(contours: list[list[tuple[float, float]]], bbox: tuple[float, float, float, float] | None = None) -> int:
    if not contours:
        return 0
    global_w = max(1.0, (bbox[2] - bbox[0]) if bbox else 1.0)
    global_h = max(1.0, (bbox[3] - bbox[1]) if bbox else 1.0)
    count = 0
    for contour in contours:
        contour_bbox = _contour_bbox(contour)
        if not contour_bbox:
            continue
        width = max(0.001, contour_bbox[2] - contour_bbox[0])
        height = max(0.001, contour_bbox[3] - contour_bbox[1])
        area = _contour_area_mm2(contour)
        box_area = max(0.001, width * height)
        slenderness = max(width, height) / max(0.001, min(width, height))
        coverage = area / box_area
        if max(width / global_w, height / global_h) >= 0.28 and slenderness >= 7.5 and coverage < 0.32:
            count += 1
    return count


def _clamp_score(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))


def _truthy_setting(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    token = _normalize_token(value)
    if token in {"0", "false", "hayir", "no", "off", "kapali", "disabled"}:
        return False
    if token in {"1", "true", "evet", "yes", "on", "acik", "enabled"}:
        return True
    return default


@lru_cache(maxsize=1)
def _load_corel_reference_corpus() -> dict[str, Any]:
    if not COREL_REFERENCE_CORPUS_PATH.exists():
        return {}
    try:
        return json.loads(COREL_REFERENCE_CORPUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _corel_reference_gate_enabled(item: dict[str, Any], cfg: dict[str, Any], style: str) -> tuple[bool, bool]:
    style_token = _normalize_token(style)
    default_enabled = "brannboll" in style_token or _is_mochary_user_corel_calibrated_style(style)
    enabled = _truthy_setting(
        item.get("corel_reference_corpus_enabled", cfg.get("corel_reference_corpus_enabled")),
        default_enabled,
    )
    # Brannboll is still testable, but Corel-referenced production calibration
    # now defaults to Mochary User/Personal. For both, reference mismatch must
    # block readyForCut unless a caller explicitly disables the guardrail for a
    # legacy diagnostic gate.
    enforce = _truthy_setting(
        item.get("corel_reference_corpus_enforce", cfg.get("corel_reference_corpus_enforce")),
        default_enabled,
    )
    return enabled, enforce


def _corel_reference_quality_for_path(path_data: str, item: dict[str, Any], cfg: dict[str, Any], style: str) -> dict[str, Any]:
    enabled, enforce = _corel_reference_gate_enabled(item, cfg, style)
    if not enabled:
        return {
            "corelReferenceCorpusEnabled": False,
            "corel_reference_corpus_enabled": False,
            "corelReferenceCorpusEnforced": False,
            "corel_reference_corpus_enforced": False,
            "corelReferenceCorpusPassed": True,
            "corel_reference_corpus_passed": True,
        }
    corpus = _load_corel_reference_corpus()
    if not corpus or _corel_path_geometry_metrics is None or _score_against_corel_corpus is None:
        return {
            "corelReferenceCorpusEnabled": True,
            "corel_reference_corpus_enabled": True,
            "corelReferenceCorpusEnforced": enforce,
            "corel_reference_corpus_enforced": enforce,
            "corelReferenceCorpusPassed": not enforce,
            "corel_reference_corpus_passed": not enforce,
            "corelReferenceCorpusStatus": "COREL_REFERENCE_CORPUS_MISSING",
            "corel_reference_corpus_status": "COREL_REFERENCE_CORPUS_MISSING",
            "corelReferenceCorpusScore": 0,
            "corel_reference_corpus_score": 0,
            "corelReferenceCorpusReasons": ["corel_reference_corpus_missing"],
            "corel_reference_corpus_reasons": ["corel_reference_corpus_missing"],
        }
    metrics = _corel_path_geometry_metrics(path_data)
    score = _score_against_corel_corpus(metrics, corpus)
    passed = score.get("status") == "PASSED"
    return {
        "corelReferenceCorpusEnabled": True,
        "corel_reference_corpus_enabled": True,
        "corelReferenceCorpusEnforced": enforce,
        "corel_reference_corpus_enforced": enforce,
        "corelReferenceCorpusPassed": bool(passed),
        "corel_reference_corpus_passed": bool(passed),
        "corelReferenceCorpusStatus": score.get("status"),
        "corel_reference_corpus_status": score.get("status"),
        "corelReferenceCorpusScore": score.get("score"),
        "corel_reference_corpus_score": score.get("score"),
        "corelReferenceCorpusReasons": score.get("reasons") or [],
        "corel_reference_corpus_reasons": score.get("reasons") or [],
        "corelReferenceCorpusCandidateMetrics": metrics,
        "corel_reference_corpus_candidate_metrics": metrics,
    }


@lru_cache(maxsize=1)
def _load_corel_exact_reference_selection() -> dict[str, Any]:
    if not COREL_EXACT_REFERENCE_SELECTION_PATH.exists():
        return {"references": {}}
    try:
        data = json.loads(COREL_EXACT_REFERENCE_SELECTION_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"references": {}}
    except Exception:
        return {"references": {}}


@lru_cache(maxsize=1)
def _load_corel_name_reference_library() -> dict[str, Any]:
    if not COREL_NAME_REFERENCE_LIBRARY_PATH.exists():
        return {"references": []}
    try:
        data = json.loads(COREL_NAME_REFERENCE_LIBRARY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"references": []}
    except Exception as exc:
        backups = list_corel_reference_backups()
        return {
            "status": "CORRUPT",
            "references": [],
            "parseError": str(exc),
            "libraryPath": str(COREL_NAME_REFERENCE_LIBRARY_PATH),
            "restoreAvailable": bool(backups.get("backups")),
            "backupCount": int(backups.get("count") or 0),
        }


def _corel_reference_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _corel_reference_backup_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _corel_reference_safe_key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip()).casefold()
    return "".join(ch for ch in text if not unicodedata.combining(ch) and (ch.isalnum() or ch in {"-", "_"}))


def list_corel_reference_backups() -> dict[str, Any]:
    COREL_REFERENCE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = sorted(
        COREL_REFERENCE_BACKUP_DIR.glob("corel_name_reference_library_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    rows = []
    for path in backups:
        valid_json = True
        parse_error = ""
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            valid_json = False
            parse_error = str(exc)
        rows.append({
            "path": str(path),
            "name": path.name,
            "size": path.stat().st_size,
            "modifiedAt": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            "validJson": valid_json,
            "parseError": parse_error,
        })
    valid_rows = [row for row in rows if row.get("validJson")]
    return {
        "status": "OK",
        "count": len(rows),
        "validCount": len(valid_rows),
        "backups": rows,
        "latest": valid_rows[0] if valid_rows else None,
        "latestAny": rows[0] if rows else None,
    }


def _corel_reference_last_audit() -> dict[str, Any] | None:
    if not COREL_REFERENCE_AUDIT_LOG_PATH.exists():
        return None
    try:
        lines = [line for line in COREL_REFERENCE_AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return None
        data = json.loads(lines[-1])
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _write_corel_reference_audit(
    action: str,
    *,
    reference_id: str = "",
    old_value: Any = None,
    new_value: Any = None,
    user_action_label: str = "",
    backup_path: str = "",
) -> None:
    COREL_REFERENCE_AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "action": action,
        "referenceId": reference_id,
        "oldValue": old_value,
        "newValue": new_value,
        "userActionLabel": user_action_label,
        "timestamp": _corel_reference_now(),
        "backupPath": backup_path,
    }
    with COREL_REFERENCE_AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def create_corel_reference_backup(reason: str = "manual") -> dict[str, Any]:
    COREL_REFERENCE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if not COREL_NAME_REFERENCE_LIBRARY_PATH.exists():
        return {"status": "ERROR", "message": "Corel reference library dosyası bulunamadı.", "reason": reason}
    stamp = _corel_reference_backup_stamp()
    backup_path = COREL_REFERENCE_BACKUP_DIR / f"corel_name_reference_library_{stamp}.json"
    suffix = 1
    while backup_path.exists():
        backup_path = COREL_REFERENCE_BACKUP_DIR / f"corel_name_reference_library_{stamp}_{suffix:02d}.json"
        suffix += 1
    shutil.copy2(COREL_NAME_REFERENCE_LIBRARY_PATH, backup_path)
    return {
        "status": "OK",
        "reason": reason,
        "backupPath": str(backup_path),
        "backupName": backup_path.name,
        "createdAt": _corel_reference_now(),
    }


def validate_corel_reference_record(row: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not str(row.get("referenceId") or row.get("objectId") or "").strip():
        issues.append("missing_referenceId")
    if not str(row.get("sourceFile") or "").strip():
        issues.append("missing_sourceFile")
    if not row.get("bbox"):
        issues.append("missing_bbox")
    if not str(row.get("finalCutPathData") or "").strip():
        issues.append("missing_finalCutPathData")
    if bool(row.get("approved")):
        if not str(row.get("manualNameLabel") or row.get("displayName") or "").strip():
            issues.append("approved_missing_manualNameLabel")
        if not str(row.get("nameKey") or "").strip():
            issues.append("approved_missing_nameKey")
        if not str(row.get("finalCutPathData") or "").strip():
            issues.append("approved_missing_finalCutPathData")
    if bool(row.get("exactNameMatch")) and bool(row.get("styleReferenceOnly")):
        issues.append("exactNameMatch_requires_styleReferenceOnly_false")
    if str(row.get("status") or row.get("labelStatus") or "") == "exact_approved" and not bool(row.get("approved")):
        issues.append("exact_approved_requires_approved_true")
    return issues


def _extract_corel_path_data_from_svg_file(path_value: object) -> str:
    path = Path(str(path_value or ""))
    if not path.exists():
        return ""
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    parts: list[str] = []
    for element in root.iter():
        if str(element.tag).endswith("path"):
            path_data = str(element.attrib.get("d") or "").strip()
            if path_data:
                parts.append(path_data)
    return " ".join(parts)


def _migrate_corel_reference_record(row: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    next_row = dict(row)
    changed: list[str] = []

    def ensure_field(key: str, value: Any) -> None:
        if key not in next_row:
            next_row[key] = value
            changed.append(key)

    manual_label = unicodedata.normalize("NFC", str(next_row.get("manualNameLabel") or "").strip())
    display_name = unicodedata.normalize("NFC", str(next_row.get("displayName") or manual_label or "").strip())
    ensure_field("manualNameLabel", manual_label)
    ensure_field("displayName", display_name)
    if "nameKey" not in next_row:
        next_row["nameKey"] = _corel_reference_safe_key(display_name)
        changed.append("nameKey")
    ensure_field("approved", False)
    ensure_field("exactNameMatch", False)
    ensure_field("styleReferenceOnly", True)
    if "status" not in next_row:
        next_row["status"] = "candidate_hint" if next_row.get("targetNameHint") else "unlabeled"
        changed.append("status")
    if "labelStatus" not in next_row:
        next_row["labelStatus"] = next_row.get("status") or "unlabeled"
        changed.append("labelStatus")
    ensure_field("referenceType", "imported_corel_path")
    path_data = str(next_row.get("finalCutPathData") or "")
    if not path_data:
        path_data = _extract_corel_path_data_from_svg_file(next_row.get("path") or next_row.get("target"))
        if path_data:
            next_row["finalCutPathData"] = path_data
            changed.append("finalCutPathData")
    ensure_field("isPathOnly", bool(path_data and "<text" not in path_data.lower()))
    ensure_field("hasTextElement", "<text" in path_data.lower())
    ensure_field("readyAsReference", bool(path_data and next_row.get("isPathOnly")))
    ensure_field("createdAt", _corel_reference_now())
    ensure_field("updatedAt", _corel_reference_now())
    next_row["validationIssues"] = validate_corel_reference_record(next_row)
    return next_row, changed


def _migrate_corel_reference_library_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    library = dict(payload) if isinstance(payload, dict) else {"references": []}
    references = library.get("references") if isinstance(library.get("references"), list) else []
    migrated: list[dict[str, Any]] = []
    changed_records = 0
    changed_fields: dict[str, int] = {}
    validation_issue_count = 0
    for row in references:
        if not isinstance(row, dict):
            continue
        next_row, fields = _migrate_corel_reference_record(row)
        if fields:
            changed_records += 1
            for field in fields:
                changed_fields[field] = changed_fields.get(field, 0) + 1
        validation_issue_count += len(next_row.get("validationIssues") or [])
        migrated.append(next_row)
    library["references"] = migrated
    library["migration"] = {
        "lastRunAt": _corel_reference_now(),
        "changedRecords": changed_records,
        "changedFields": changed_fields,
        "validationIssueCount": validation_issue_count,
    }
    return library, library["migration"]


def _save_corel_name_reference_library(
    payload: dict[str, Any],
    *,
    action: str = "save_corel_name_reference_library",
    reference_id: str = "",
    old_value: Any = None,
    new_value: Any = None,
    user_action_label: str = "",
) -> dict[str, Any]:
    COREL_NAME_REFERENCE_LIBRARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    backup = create_corel_reference_backup(reason=action) if COREL_NAME_REFERENCE_LIBRARY_PATH.exists() else {"status": "SKIPPED"}
    migrated_payload, migration = _migrate_corel_reference_library_payload(payload)
    COREL_NAME_REFERENCE_LIBRARY_PATH.write_text(
        json.dumps(migrated_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _load_corel_name_reference_library.cache_clear()
    _write_corel_reference_audit(
        action,
        reference_id=reference_id,
        old_value=old_value,
        new_value=new_value,
        user_action_label=user_action_label,
        backup_path=str(backup.get("backupPath") or ""),
    )
    return {"status": "OK", "backup": backup, "migration": migration}


def migrate_corel_reference_library() -> dict[str, Any]:
    library = _load_corel_name_reference_library()
    if library.get("status") == "CORRUPT":
        return {"status": "ERROR", "code": "LIBRARY_CORRUPT", "message": library.get("parseError"), "dataSecurity": corel_reference_data_security_status()}
    migrated, migration = _migrate_corel_reference_library_payload(library)
    save_result = _save_corel_name_reference_library(migrated, action="migrate_corel_reference_library", user_action_label="Migration")
    return {"status": "OK", "migration": migration, "save": save_result, "dataSecurity": corel_reference_data_security_status()}


def validate_corel_reference_library() -> dict[str, Any]:
    library = _load_corel_name_reference_library()
    if library.get("status") == "CORRUPT":
        return {"status": "ERROR", "code": "LIBRARY_CORRUPT", "message": library.get("parseError"), "dataSecurity": corel_reference_data_security_status()}
    references = library.get("references") if isinstance(library.get("references"), list) else []
    rows = []
    for row in references:
        if isinstance(row, dict):
            issues = validate_corel_reference_record(row)
            if issues:
                rows.append({"referenceId": row.get("referenceId") or row.get("objectId"), "issues": issues})
    return {"status": "OK", "issueCount": sum(len(row["issues"]) for row in rows), "recordsWithIssues": rows[:200]}


def restore_corel_reference_backup(backup_path: str = "", latest: bool = True) -> dict[str, Any]:
    backups = list_corel_reference_backups()
    target = Path(backup_path) if backup_path else None
    if not target and latest and backups.get("latest"):
        target = Path(str(backups["latest"]["path"]))
    if not target or not target.exists():
        return {"status": "ERROR", "message": "Geri yüklenecek backup bulunamadı.", "backups": backups}
    if target.parent.resolve() != COREL_REFERENCE_BACKUP_DIR.resolve():
        return {"status": "ERROR", "message": "Backup yolu güvenli backup klasörü dışında."}
    snapshot = create_corel_reference_backup(reason="pre_restore_snapshot") if COREL_NAME_REFERENCE_LIBRARY_PATH.exists() else {"status": "SKIPPED"}
    shutil.copy2(target, COREL_NAME_REFERENCE_LIBRARY_PATH)
    _load_corel_name_reference_library.cache_clear()
    _write_corel_reference_audit(
        "restore_corel_reference_backup",
        old_value={"snapshot": snapshot},
        new_value={"restoredFrom": str(target)},
        user_action_label="Son backup'tan geri yükle",
        backup_path=str(snapshot.get("backupPath") or ""),
    )
    return {"status": "OK", "restoredFrom": str(target), "snapshot": snapshot, "dataSecurity": corel_reference_data_security_status()}


def corel_reference_data_security_status() -> dict[str, Any]:
    backups = list_corel_reference_backups()
    last_audit = _corel_reference_last_audit()
    library = _load_corel_name_reference_library()
    return {
        "status": "CORRUPT" if isinstance(library, dict) and library.get("status") == "CORRUPT" else "OK",
        "libraryPath": str(COREL_NAME_REFERENCE_LIBRARY_PATH),
        "backupDir": str(COREL_REFERENCE_BACKUP_DIR),
        "backupCount": backups.get("count", 0),
        "lastBackup": backups.get("latest"),
        "auditLogPath": str(COREL_REFERENCE_AUDIT_LOG_PATH),
        "lastAuditAction": last_audit,
        "restoreAvailable": bool(backups.get("backups")),
        "parseError": library.get("parseError") if isinstance(library, dict) else None,
    }


def _load_corel_reference_path_payload(entry: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(entry.get("path") or entry.get("target") or ""))
    if not path.exists() or _load_exact_reference_path_data is None:
        return {"pathData": str(entry.get("finalCutPathData") or ""), "metrics": entry.get("metrics") or {}}
    loaded = _load_exact_reference_path_data(path)
    return loaded if isinstance(loaded, dict) else {"pathData": "", "metrics": {}}


def _enrich_corel_reference_entry(entry: dict[str, Any], include_path_data: bool = False) -> dict[str, Any]:
    result = dict(entry)
    manual_label = str(result.get("manualNameLabel") or result.get("displayName") or "").strip()
    result["displayName"] = manual_label
    result["nameKey"] = _corel_reference_key(manual_label) if manual_label else str(result.get("nameKey") or "")
    path = Path(str(result.get("path") or result.get("target") or ""))
    result["previewUrl"] = file_api.to_web_file_url(path, PROJECT_ROOT) if path else ""
    result["isPathOnly"] = bool(result.get("isPathOnly", True)) and not bool(result.get("hasTextElement"))
    if include_path_data or (result.get("approved") and result.get("exactNameMatch")):
        loaded = _load_corel_reference_path_payload(result)
        final_path = str(result.get("finalCutPathData") or loaded.get("pathData") or "")
        result["finalCutPathData"] = final_path
        result["referencePathHash"] = _corel_path_hash(final_path)
        if isinstance(loaded.get("metrics"), dict) and loaded.get("metrics"):
            result["metrics"] = loaded.get("metrics")
    else:
        result["referencePathHash"] = _corel_path_hash(result.get("finalCutPathData"))
    result["readyAsReference"] = bool(result.get("readyAsReference")) and result["isPathOnly"] and bool(result.get("path"))
    result["requiresManualLabel"] = not bool(result.get("approved") and result.get("exactNameMatch") and result.get("nameKey"))
    assessment = _corel_reference_match_assessment(result, manual_label=manual_label)
    result["readName"] = assessment["readName"]
    result["matchType"] = assessment["matchType"]
    result["needsSplit"] = bool(result.get("needsSplit") or assessment["needsSplit"])
    result["canApproveExact"] = bool(assessment["canApproveExact"])
    result["actionNeeded"] = assessment["actionNeeded"]
    if result.get("approved") and result.get("exactNameMatch") and not result.get("styleReferenceOnly"):
        result["labelStatus"] = "exact_approved"
        result["canApproveExact"] = True
    else:
        result["labelStatus"] = str(result.get("labelStatus") or assessment["status"] or "unlabeled")
    result["status"] = result["labelStatus"]
    return result


def _corel_reference_library_payload(include_path_data: bool = False) -> dict[str, Any]:
    library = _load_corel_name_reference_library()
    references = library.get("references") if isinstance(library, dict) else []
    if not isinstance(references, list):
        references = []
    enriched = [
        _enrich_corel_reference_entry(row, include_path_data=include_path_data)
        for row in references
        if isinstance(row, dict)
    ]
    return {
        **{key: value for key, value in library.items() if key != "references"},
        "references": enriched,
    }


def _corel_reference_label_status(row: dict[str, Any]) -> str:
    status = str(row.get("labelStatus") or row.get("status") or "").strip()
    if bool(row.get("approved")) and bool(row.get("exactNameMatch")) and not bool(row.get("styleReferenceOnly")):
        return "exact_approved"
    if status in {
        "candidate_hint",
        "needs_split",
        "label_ready",
        "style_reference_only",
        "rejected_wrong_name",
        "candidate_mismatch",
        "unlabeled",
    }:
        return status
    if row.get("targetNameHint") or row.get("suggestedLabel"):
        return str(_corel_reference_match_assessment(row).get("status") or "candidate_hint")
    if row.get("styleReferenceOnly"):
        return "style_reference_only"
    return "unlabeled"


def _corel_reference_match_assessment(row: dict[str, Any], manual_label: str | None = None) -> dict[str, Any]:
    label = unicodedata.normalize("NFC", str(manual_label if manual_label is not None else row.get("manualNameLabel") or "")).strip()
    read_name = unicodedata.normalize("NFC", str(row.get("suggestedLabel") or row.get("readName") or "")).strip()
    target_hint = unicodedata.normalize("NFC", str(row.get("targetNameHint") or "")).strip()
    label_key = _corel_reference_key(label)
    read_key = _corel_reference_key(read_name)
    split_quality_status = str(row.get("splitQualityStatus") or "").strip()
    target_keys = [str(key or "") for key in row.get("targetNameKeyHints") or [] if str(key or "")]
    if not target_keys and target_hint:
        target_keys = [_corel_reference_key(part.strip()) for part in re.split(r"[/,;|]+", target_hint) if part.strip()]
    if not target_keys and row.get("targetNameKeyHint"):
        target_keys = [str(row.get("targetNameKeyHint") or "")]
    candidate_keys = [label_key] if label_key else target_keys
    exact_text_match = bool(read_key and any(read_key == key for key in candidate_keys if key))
    contains_target = bool(read_key and any(key in read_key and read_key != key for key in candidate_keys if key))
    has_multiple_read_names = bool(read_name and len([part for part in re.split(r"\s+|&|\+", read_name) if part.strip()]) > 1)
    mismatch = bool(read_key and candidate_keys and not exact_text_match and not contains_target)
    if exact_text_match:
        match_type = "contains_target_as_part" if has_multiple_read_names else "exact_text_match"
        status = "needs_split" if has_multiple_read_names else ("label_ready" if label_key else "candidate_hint")
        needs_split = has_multiple_read_names
        can_approve = bool(label_key) and not has_multiple_read_names
        action = "Bu obje birden fazla isim içeriyor; önce split child reference oluştur." if has_multiple_read_names else "Preview kontrolünden sonra exact onay verilebilir."
    elif contains_target:
        match_type = "contains_target_as_part"
        status = "needs_split"
        needs_split = True
        can_approve = False
        action = "Bu obje birden fazla isim içeriyor; önce split child reference oluştur."
    elif mismatch:
        match_type = "mismatch"
        status = "candidate_mismatch"
        needs_split = has_multiple_read_names
        can_approve = False
        action = "Okunan isim hedef/manual label ile uyuşmuyor; doğru obje seçilmeli veya manuel override gerekir."
    elif read_name and not candidate_keys:
        match_type = "manual_needed"
        status = "candidate_hint"
        needs_split = has_multiple_read_names
        can_approve = False
        action = "Manual label gir ve büyük preview ile doğrula."
    else:
        match_type = "unreadable"
        status = "candidate_hint" if target_hint else "unlabeled"
        needs_split = False
        can_approve = bool(label_key)
        action = "Text okunamadı; operator preview ile label doğrulamalı."
    if bool(row.get("styleReferenceOnly")) and not bool(row.get("approved")) and status == "unlabeled":
        status = "style_reference_only"
    if bool(row.get("splitFromCompoundObject")) and split_quality_status == "review_required" and can_approve:
        can_approve = False
        status = "needs_split"
        action = "Otomatik split cluster güvenli değil; child exact onay için manuel büyük preview/split kontrolü gerekir."
    return {
        "manualNameLabel": label,
        "readName": read_name,
        "targetNameHint": target_hint,
        "matchType": match_type,
        "status": status,
        "needsSplit": needs_split,
        "canApproveExact": can_approve,
        "actionNeeded": action,
        "mismatch": mismatch,
        "containsTargetAsPart": contains_target,
    }


def _write_corel_reference_update(reference_id: str, updater, *, action: str = "update_corel_reference", user_action_label: str = "") -> dict[str, Any]:
    library = _corel_reference_library_payload(include_path_data=False)
    if library.get("status") == "CORRUPT":
        return {"status": "ERROR", "code": "LIBRARY_CORRUPT", "message": library.get("parseError"), "dataSecurity": corel_reference_data_security_status()}
    references = library.get("references") if isinstance(library.get("references"), list) else []
    now = datetime.now().isoformat(timespec="seconds")
    updated_entry: dict[str, Any] | None = None
    old_entry: dict[str, Any] | None = None
    next_references: list[dict[str, Any]] = []
    for row in references:
        if str(row.get("referenceId") or row.get("objectId") or "") == str(reference_id):
            old_entry = dict(row)
            updated = dict(row)
            updated = updater(updated)
            updated["updatedAt"] = now
            updated.setdefault("createdAt", row.get("createdAt") or now)
            updated_entry = _enrich_corel_reference_entry(updated, include_path_data=bool(updated.get("approved") and updated.get("exactNameMatch")))
            next_references.append(updated_entry)
        else:
            next_references.append(row)
    if updated_entry is None:
        return {"status": "ERROR", "message": f"Corel referans bulunamadı: {reference_id}"}
    library["references"] = next_references
    save_result = _save_corel_name_reference_library(
        library,
        action=action,
        reference_id=reference_id,
        old_value=old_entry,
        new_value=updated_entry,
        user_action_label=user_action_label,
    )
    return {"status": "OK", "reference": updated_entry, "summary": _corel_reference_summary(next_references), "dataSecurity": corel_reference_data_security_status(), "save": save_result}


def _corel_reference_summary(references: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(references),
        "approvedExact": sum(1 for row in references if row.get("approved") and row.get("exactNameMatch") and not row.get("styleReferenceOnly") and _corel_reference_label_status(row) == "exact_approved"),
        "pendingManualLabel": sum(1 for row in references if row.get("requiresManualLabel")),
        "styleOnly": sum(1 for row in references if row.get("styleReferenceOnly")),
        "suggested": sum(1 for row in references if row.get("suggestedLabel") or row.get("targetNameHint")),
        "needsSplit": sum(1 for row in references if _corel_reference_label_status(row) == "needs_split"),
        "mismatch": sum(1 for row in references if _corel_reference_label_status(row) in {"candidate_mismatch", "rejected_wrong_name"}),
    }


def list_corel_references(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    filters = filters or {}
    library = _corel_reference_library_payload(include_path_data=False)
    if library.get("status") == "CORRUPT":
        return {
            "status": "ERROR",
            "code": "LIBRARY_CORRUPT",
            "message": "Corel reference library JSON okunamadı; restore gerekli.",
            "parseError": library.get("parseError"),
            "references": [],
            "summary": {},
            "dataSecurity": corel_reference_data_security_status(),
        }
    references = library.get("references") if isinstance(library.get("references"), list) else []
    query_key = _corel_reference_key(filters.get("query") or "")
    source_filter = str(filters.get("sourceFile") or "").strip()
    mode = str(filters.get("mode") or "all")
    filtered: list[dict[str, Any]] = []
    for row in references:
        if query_key:
            haystack = " ".join([
                str(row.get("manualNameLabel") or ""),
                str(row.get("displayName") or ""),
                str(row.get("suggestedLabel") or ""),
                str(row.get("targetNameHint") or ""),
                str(row.get("sourceFile") or ""),
                str(row.get("referenceId") or ""),
            ])
            if query_key not in _corel_reference_key(haystack):
                continue
        if source_filter and source_filter not in str(row.get("sourceFile") or ""):
            continue
        is_exact = bool(row.get("approved") and row.get("exactNameMatch") and not row.get("styleReferenceOnly"))
        if mode == "pending" and not row.get("requiresManualLabel"):
            continue
        if mode == "exact" and not is_exact:
            continue
        if mode == "style" and not row.get("styleReferenceOnly"):
            continue
        if mode == "suggested" and not (row.get("suggestedLabel") or row.get("targetNameHint")):
            continue
        if mode == "needs_split" and _corel_reference_label_status(row) != "needs_split":
            continue
        if mode == "mismatch" and _corel_reference_label_status(row) not in {"candidate_mismatch", "rejected_wrong_name"}:
            continue
        public_row = {key: value for key, value in row.items() if key not in {"finalCutPathData", "corelReferenceOriginalPathData"}}
        filtered.append(public_row)
    return {
        "status": "OK",
        "references": filtered,
        "summary": _corel_reference_summary(references),
        "policy": library.get("policy") or {},
        "libraryPath": str(COREL_NAME_REFERENCE_LIBRARY_PATH),
        "dataSecurity": corel_reference_data_security_status(),
    }


def get_corel_reference(reference_id: str) -> dict[str, Any]:
    library = _corel_reference_library_payload(include_path_data=True)
    if library.get("status") == "CORRUPT":
        return {"status": "ERROR", "code": "LIBRARY_CORRUPT", "message": library.get("parseError"), "dataSecurity": corel_reference_data_security_status()}
    for row in library.get("references", []) or []:
        if str(row.get("referenceId") or row.get("objectId") or "") == str(reference_id):
            return {"status": "OK", "reference": row}
    return {"status": "ERROR", "message": f"Corel referans bulunamadı: {reference_id}"}


def update_corel_reference_label(reference_id: str, manual_name_label: str, approve_exact: bool = False) -> dict[str, Any]:
    label = unicodedata.normalize("NFC", str(manual_name_label or "")).strip()
    if not label:
        return {"status": "ERROR", "message": "Manual name label boş olamaz."}

    def updater(row: dict[str, Any]) -> dict[str, Any]:
        assessment = _corel_reference_match_assessment(row, manual_label=label)
        loaded = _load_corel_reference_path_payload(row)
        final_path = str(loaded.get("pathData") or row.get("finalCutPathData") or "")
        row.update({
            "manualNameLabel": label,
            "displayName": label,
            "nameKey": _corel_reference_key(label),
            "matchType": assessment["matchType"],
            "labelStatus": "label_ready" if assessment["canApproveExact"] and not approve_exact else assessment["status"],
            "status": "label_ready" if assessment["canApproveExact"] and not approve_exact else assessment["status"],
            "needsSplit": assessment["needsSplit"],
            "canApproveExact": assessment["canApproveExact"],
            "actionNeeded": assessment["actionNeeded"],
            "finalCutPathData": final_path,
            "referencePathHash": _corel_path_hash(final_path),
            "hasTextElement": False,
            "isPathOnly": bool(final_path),
            "readyAsReference": bool(final_path and row.get("path")),
        })
        if approve_exact:
            if not assessment["canApproveExact"]:
                raise ValueError(f"Exact onay kilitli: {assessment['actionNeeded']}")
            row.update({
                "approved": True,
                "exactNameMatch": True,
                "styleReferenceOnly": False,
                "labelStatus": "exact_approved",
                "status": "exact_approved",
                "referenceType": "manual_corel_final",
                "requiresManualLabel": False,
            })
        else:
            row["requiresManualLabel"] = not bool(row.get("approved") and row.get("exactNameMatch"))
        return row

    try:
        return _write_corel_reference_update(reference_id, updater, action="update_corel_reference_label", user_action_label="Manual label güncelleme")
    except ValueError as exc:
        return {"status": "ERROR", "message": str(exc)}


def approve_corel_exact_reference(reference_id: str) -> dict[str, Any]:
    def updater(row: dict[str, Any]) -> dict[str, Any]:
        label = str(row.get("manualNameLabel") or row.get("displayName") or "").strip()
        if not label:
            raise ValueError("Exact onay için manualNameLabel gerekli.")
        assessment = _corel_reference_match_assessment(row, manual_label=label)
        if not assessment["canApproveExact"]:
            raise ValueError(f"Exact onay kilitli: {assessment['actionNeeded']}")
        loaded = _load_corel_reference_path_payload(row)
        final_path = str(loaded.get("pathData") or row.get("finalCutPathData") or "")
        if not final_path:
            raise ValueError("Exact onay için path data bulunamadı.")
        row.update({
            "manualNameLabel": label,
            "displayName": label,
            "nameKey": _corel_reference_key(label),
            "approved": True,
            "exactNameMatch": True,
            "styleReferenceOnly": False,
            "labelStatus": "exact_approved",
            "status": "exact_approved",
            "matchType": assessment["matchType"],
            "needsSplit": False,
            "canApproveExact": True,
            "actionNeeded": "Exact referans onaylandı.",
            "referenceType": "manual_corel_final",
            "requiresManualLabel": False,
            "finalCutPathData": final_path,
            "referencePathHash": _corel_path_hash(final_path),
            "isPathOnly": True,
            "hasTextElement": False,
            "readyAsReference": True,
        })
        return row

    try:
        return _write_corel_reference_update(reference_id, updater, action="approve_corel_exact_reference", user_action_label="Exact isim olarak onayla")
    except ValueError as exc:
        return {"status": "ERROR", "message": str(exc)}


def unapprove_corel_reference(reference_id: str) -> dict[str, Any]:
    def updater(row: dict[str, Any]) -> dict[str, Any]:
        row.update({
            "approved": False,
            "exactNameMatch": False,
            "styleReferenceOnly": True,
            "labelStatus": "style_reference_only",
            "status": "style_reference_only",
            "canApproveExact": False,
            "referenceType": "unlabeled_corel_object",
            "requiresManualLabel": True,
        })
        return row
    return _write_corel_reference_update(reference_id, updater, action="unapprove_corel_reference", user_action_label="Exact onayı kaldır")


def mark_corel_reference_style_only(reference_id: str) -> dict[str, Any]:
    return unapprove_corel_reference(reference_id)


def reject_corel_reference_candidate(reference_id: str) -> dict[str, Any]:
    def updater(row: dict[str, Any]) -> dict[str, Any]:
        row.update({
            "approved": False,
            "exactNameMatch": False,
            "styleReferenceOnly": True,
            "labelStatus": "rejected_wrong_name",
            "status": "rejected_wrong_name",
            "canApproveExact": False,
            "requiresManualLabel": True,
            "actionNeeded": "Operator bu objeyi yanlış aday olarak işaretledi; production exact override yapamaz.",
        })
        return row
    return _write_corel_reference_update(reference_id, updater, action="reject_corel_reference_candidate", user_action_label="Yanlış aday / reddet")


def _write_operator_generated_reference_svg(reference_id: str, path_data: str, bbox: tuple[float, float, float, float] | None) -> Path:
    out_dir = PROJECT_ROOT / "assets" / "references" / "operator_generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{reference_id}.svg"
    if bbox:
        min_x, min_y, max_x, max_y = bbox
        width = max(1.0, max_x - min_x)
        height = max(1.0, max_y - min_y)
        view_box = f"{min_x:.3f} {min_y:.3f} {width:.3f} {height:.3f}"
    else:
        view_box = "0 0 800 600"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{html.escape(view_box, quote=True)}">\n'
        f'  <path d="{html.escape(path_data, quote=True)}" fill="black" fill-rule="evenodd"/>\n'
        "</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")
    return path


def save_operator_generated_corel_reference(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    name = unicodedata.normalize("NFC", str(payload.get("manualNameLabel") or payload.get("displayName") or payload.get("name") or "")).strip()
    name_key = _corel_reference_key(name)
    path_data = str(payload.get("finalCutPathData") or payload.get("final_cut_path_data") or payload.get("pathData") or "").strip()
    duplicate_action = str(payload.get("duplicateAction") or payload.get("duplicate_action") or "keep_existing").strip() or "keep_existing"
    if not name or not name_key:
        return {"status": "ERROR", "message": "Yeni exact reference için isim etiketi gerekli."}
    if not path_data:
        return {"status": "ERROR", "message": "Yeni exact reference için finalCutPathData gerekli."}
    if "<text" in path_data.lower():
        return {"status": "ERROR", "message": "Path-only kuralı ihlal edildi: text elementi içeremez."}
    allowed_generated_sources = {
        "corel_style_reproducer",
        "corel_style_ai_generated",
        "internal_ai_assisted_name_engine",
    }
    payload_source = str(payload.get("source") or payload.get("pathSource") or payload.get("path_source") or "")
    if payload_source not in allowed_generated_sources:
        return {"status": "ERROR", "message": "Sadece review-gated generated çıktı operator onayıyla exact referansa dönüştürülebilir."}
    if not bool(payload.get("operatorPreviewOpened") or payload.get("operator_preview_opened")):
        return {"status": "ERROR", "message": "Operator büyük preview/proof açmadan exact reference kaydedilemez."}
    if not bool(payload.get("operatorConfirmation") or payload.get("operator_confirmation")):
        return {"status": "ERROR", "message": "Operator üretim referansı onay kutusunu işaretlemeli."}
    if not bool(payload.get("pathOnlyExportPassed") or payload.get("path_only_export_passed") or payload.get("isPathOnly")):
        return {"status": "ERROR", "message": "SVG path-only doğrulaması geçmeden exact reference kaydedilemez."}
    if not bool(payload.get("canvasExportConsistencyPassed") or payload.get("canvas_export_consistency_passed")):
        return {"status": "ERROR", "message": "Canvas/export path eşleşmeden exact reference kaydedilemez."}
    if str(payload.get("manufacturabilityStatus") or payload.get("manufacturability_status") or "") != "manufacturable_passed":
        return {"status": "ERROR", "message": "Laser manufacturability passed olmadan exact reference kaydedilemez."}

    library = _corel_reference_library_payload(include_path_data=False)
    if library.get("status") == "CORRUPT":
        return {"status": "ERROR", "code": "LIBRARY_CORRUPT", "message": library.get("parseError"), "dataSecurity": corel_reference_data_security_status()}
    references = library.get("references") if isinstance(library.get("references"), list) else []
    existing = [
        row for row in references
        if str(row.get("nameKey") or "") == name_key
        and bool(row.get("approved"))
        and bool(row.get("exactNameMatch"))
        and not bool(row.get("styleReferenceOnly"))
        and _corel_reference_label_status(row) == "exact_approved"
    ]
    if existing and duplicate_action == "keep_existing":
        return {
            "status": "DUPLICATE_REFERENCE",
            "message": "Bu nameKey için zaten exact reference var. Mevcut referansı koruyun, varyasyon olarak kaydedin veya açık replace onayı verin.",
            "existingReferences": [
                {
                    "referenceId": row.get("referenceId"),
                    "displayName": row.get("displayName") or row.get("manualNameLabel"),
                    "referenceType": row.get("referenceType"),
                }
                for row in existing
            ],
        }

    bbox_tuple = _path_bbox_from_d(path_data)
    now = datetime.now().isoformat(timespec="seconds")
    reference_id = str(payload.get("referenceId") or payload.get("reference_id") or f"operator-generated-{name_key}-{uuid.uuid4().hex[:8]}")
    svg_path = _write_operator_generated_reference_svg(reference_id, path_data, bbox_tuple)
    width = float(payload.get("actualPathWidthMm") or payload.get("actual_path_width_mm") or ((bbox_tuple[2] - bbox_tuple[0]) if bbox_tuple else 0) or 0)
    height = float(payload.get("actualPathHeightMm") or payload.get("actual_path_height_mm") or ((bbox_tuple[3] - bbox_tuple[1]) if bbox_tuple else 0) or 0)
    entry = {
        "referenceId": reference_id,
        "objectId": reference_id,
        "sourceFile": "operator_generated",
        "sourcePath": "",
        "path": str(svg_path),
        "referenceType": "operator_approved_internal_generated" if payload_source == "internal_ai_assisted_name_engine" else "operator_approved_generated",
        "manualNameLabel": name,
        "displayName": name,
        "nameKey": name_key,
        "approved": True,
        "exactNameMatch": True,
        "styleReferenceOnly": False,
        "labelStatus": "exact_approved",
        "status": "exact_approved",
        "finalCutPathData": path_data,
        "actualPathWidthMm": round(width, 3),
        "actualPathHeightMm": round(height, 3),
        "bbox": list(bbox_tuple) if bbox_tuple else (payload.get("bbox") or {}),
        "componentCount": int(payload.get("componentCount") or payload.get("component_count") or max(1, len(re.findall(r"\bM\b", path_data))) or 1),
        "isPathOnly": True,
        "hasTextElement": False,
        "readyAsReference": True,
        "requiresManualLabel": False,
        "operatorPreviewOpened": True,
        "operatorConfirmation": True,
        "canvasPathHash": str(payload.get("canvasPathHash") or payload.get("canvas_path_hash") or _corel_path_hash(path_data)),
        "exportPathHash": str(payload.get("exportPathHash") or payload.get("export_path_hash") or _corel_path_hash(path_data)),
        "referencePathHash": _corel_path_hash(path_data),
        "manufacturabilityStatus": str(payload.get("manufacturabilityStatus") or payload.get("manufacturability_status") or "manufacturable_passed"),
        "createdAt": now,
        "updatedAt": now,
        "notes": "Operator generated proof'u büyük preview ile kontrol edip üretim referansı olarak onayladı.",
    }
    if duplicate_action == "replace_existing" and existing:
        replaced_id = str(existing[0].get("referenceId") or "")
        next_refs = []
        for row in references:
            if str(row.get("referenceId") or "") == replaced_id:
                next_refs.append({**entry, "referenceId": replaced_id, "objectId": replaced_id, "path": str(_write_operator_generated_reference_svg(replaced_id, path_data, bbox_tuple)), "updatedAt": now})
            else:
                next_refs.append(row)
        library["references"] = next_refs
        save_result = _save_corel_name_reference_library(
            library,
            action="replace_operator_generated_corel_reference",
            reference_id=replaced_id,
            old_value=existing[0],
            new_value=entry,
            user_action_label="Operator generated referansı değiştir",
        )
        return {"status": "OK", "reference": _enrich_corel_reference_entry(next_refs[[str(row.get("referenceId") or "") for row in next_refs].index(replaced_id)], include_path_data=True), "duplicateAction": "replace_existing", "summary": _corel_reference_summary(next_refs), "dataSecurity": corel_reference_data_security_status(), "save": save_result}

    if duplicate_action == "new_variant" and existing:
        entry["variantOfNameKey"] = name_key
        entry["variantIndex"] = len(existing) + 1
    references.append(entry)
    library["references"] = references
    save_result = _save_corel_name_reference_library(
        library,
        action="save_operator_generated_corel_reference",
        reference_id=reference_id,
        old_value=None,
        new_value=entry,
        user_action_label="Bu çıktıyı referans olarak kaydet",
    )
    return {"status": "OK", "reference": _enrich_corel_reference_entry(entry, include_path_data=True), "duplicateAction": duplicate_action, "summary": _corel_reference_summary(references), "dataSecurity": corel_reference_data_security_status(), "save": save_result}


def rebuild_corel_reference_index() -> dict[str, Any]:
    library = _corel_reference_library_payload(include_path_data=False)
    if library.get("status") == "CORRUPT":
        return {"status": "ERROR", "code": "LIBRARY_CORRUPT", "message": library.get("parseError"), "dataSecurity": corel_reference_data_security_status()}
    references = library.get("references") if isinstance(library.get("references"), list) else []
    normalized: list[dict[str, Any]] = []
    for row in references:
        if not isinstance(row, dict):
            continue
        enriched = _enrich_corel_reference_entry(row, include_path_data=False)
        enriched["status"] = enriched.get("labelStatus") or enriched.get("status") or "unlabeled"
        normalized.append(enriched)
    library["references"] = normalized
    save_result = _save_corel_name_reference_library(library, action="rebuild_corel_reference_index", user_action_label="İndeksi Yenile")
    return {"status": "OK", "summary": _corel_reference_summary(normalized), "references": normalized, "dataSecurity": corel_reference_data_security_status(), "save": save_result}


def search_corel_references(query: str = "") -> dict[str, Any]:
    return list_corel_references({"query": query, "mode": "all"})


def _path_bbox_from_d(path_data: str) -> tuple[float, float, float, float] | None:
    numbers = [float(value) for value in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", str(path_data or ""))]
    if len(numbers) < 2:
        return None
    xs = numbers[0::2]
    ys = numbers[1::2]
    if not xs or not ys:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _extract_svg_paths(svg_path: Path) -> list[dict[str, Any]]:
    if not svg_path.exists():
        return []
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    path_elements = [element for element in root.iter() if str(element.tag).endswith("path")]
    for index, element in enumerate(path_elements, start=1):
        path_data = str(element.attrib.get("d") or "")
        bbox = _path_bbox_from_d(path_data)
        if not bbox:
            continue
        rows.append({
            "index": index,
            "id": element.attrib.get("id") or f"path-{index}",
            "d": path_data,
            "bbox": bbox,
            "cx": (bbox[0] + bbox[2]) / 2,
            "cy": (bbox[1] + bbox[3]) / 2,
        })
    return rows


def _split_svg_paths_into_clusters(paths: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if len(paths) < 2:
        return [paths] if paths else []
    ordered = sorted(paths, key=lambda row: (row["bbox"][0], row["bbox"][1]))
    gaps: list[tuple[float, int]] = []
    for index in range(1, len(ordered)):
        prev = ordered[index - 1]["bbox"]
        curr = ordered[index]["bbox"]
        gaps.append((curr[0] - prev[2], index))
    positive = [(gap, index) for gap, index in gaps if gap > 8]
    if not positive:
        return [paths]
    largest_gap, split_index = max(positive, key=lambda row: row[0])
    total_width = max(row["bbox"][2] for row in ordered) - min(row["bbox"][0] for row in ordered)
    if largest_gap < max(18, total_width * 0.055):
        return [paths]
    clusters = [ordered[:split_index], ordered[split_index:]]
    return [cluster for cluster in clusters if cluster]


def _corel_reference_name_parts(value: object) -> list[str]:
    text = unicodedata.normalize("NFC", str(value or "")).strip()
    if not text:
        return []
    parts = [part.strip(" \t\r\n-_/") for part in re.split(r"\s+|&|\+|/", text) if part.strip(" \t\r\n-_/")]
    return [part for part in parts if _corel_reference_key(part)]


def _corel_reference_target_parts(parent: dict[str, Any]) -> list[str]:
    raw: list[str] = []
    hints = parent.get("targetNameHints")
    if isinstance(hints, list):
        raw.extend(str(item or "") for item in hints)
    if parent.get("targetNameHint"):
        raw.append(str(parent.get("targetNameHint") or ""))
    parts: list[str] = []
    for item in raw:
        parts.extend(_corel_reference_name_parts(item))
    return list(dict.fromkeys(parts))


def _split_child_label_hint(parent: dict[str, Any], split_index: int, cluster_count: int) -> tuple[str, str]:
    read_parts = _corel_reference_name_parts(parent.get("suggestedLabel") or parent.get("readName"))
    target_parts = _corel_reference_target_parts(parent)
    suggested = read_parts[split_index - 1] if len(read_parts) == cluster_count and split_index <= len(read_parts) else ""
    target_keys = {_corel_reference_key(item) for item in target_parts}
    target_hint = suggested if suggested and _corel_reference_key(suggested) in target_keys else ""
    return suggested, target_hint


def _cluster_path_data(cluster: list[dict[str, Any]]) -> str:
    return " ".join(str(row.get("d") or "").strip() for row in cluster if str(row.get("d") or "").strip())


def _write_corel_split_child_svg(
    parent: dict[str, Any],
    cluster: list[dict[str, Any]],
    split_index: int,
    *,
    suggested_label: str = "",
    target_hint: str = "",
    cluster_count: int = 0,
) -> tuple[Path, dict[str, Any]]:
    bbox = (
        min(row["bbox"][0] for row in cluster),
        min(row["bbox"][1] for row in cluster),
        max(row["bbox"][2] for row in cluster),
        max(row["bbox"][3] for row in cluster),
    )
    parent_bbox = parent.get("bbox") if isinstance(parent.get("bbox"), list) and len(parent.get("bbox")) == 4 else []
    try:
        parent_width = float(parent_bbox[2]) - float(parent_bbox[0]) if parent_bbox else float(parent.get("actualPathWidthMm") or 0)
    except (TypeError, ValueError):
        parent_width = 0.0
    child_width = bbox[2] - bbox[0]
    width_ratio = (child_width / parent_width) if parent_width > 0 else 0.0
    split_quality_status = "review_required" if width_ratio >= 0.92 or width_ratio <= 0.08 else "auto_split_candidate"
    out_dir = PROJECT_ROOT / "assets" / "references" / "corel_split_references"
    out_dir.mkdir(parents=True, exist_ok=True)
    child_id = f"{parent.get('referenceId') or parent.get('objectId')}-split-{split_index:02d}"
    out_path = out_dir / f"{child_id}.svg"
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="800mm" height="600mm" viewBox="0 0 800 600" data-corel-split-reference="true">',
        f'<title>Corel split reference: {html.escape(str(child_id))}</title>',
        '<rect x="0" y="0" width="800" height="600" fill="#ffffff"/>',
        '<g id="corel-reference-paths" fill="none" stroke="#020617" stroke-width="0.22" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke">',
    ]
    for row in cluster:
        parts.append(f'<path id="{html.escape(str(row["id"]))}" d="{html.escape(str(row["d"]), quote=True)}"/>')
    parts.extend(["</g>", "</svg>"])
    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    final_path_data = _cluster_path_data(cluster)
    target_key = _corel_reference_key(target_hint) if target_hint else ""
    label_status = "candidate_hint" if suggested_label or target_hint else "unlabeled"
    return out_path, {
        "referenceId": child_id,
        "objectId": child_id,
        "parentReferenceId": parent.get("referenceId") or parent.get("objectId"),
        "splitIndex": split_index,
        "sourceFile": parent.get("sourceFile"),
        "sourcePath": parent.get("sourcePath"),
        "path": str(out_path),
        "manualNameLabel": "",
        "displayName": "",
        "detectedName": "",
        "suggestedLabel": suggested_label,
        "readName": suggested_label,
        "nameKey": "",
        "targetNameHint": target_hint,
        "targetNameHints": [target_hint] if target_hint else [],
        "targetNameKeyHint": target_key,
        "targetNameKeyHints": [target_key] if target_key else [],
        "fontProfile": parent.get("fontProfile") or "Mochary US Personal / Corel Reference",
        "referenceType": "split_corel_child",
        "approved": False,
        "exactNameMatch": False,
        "styleReferenceOnly": True,
        "labelStatus": label_status,
        "status": label_status,
        "readyAsReference": True,
        "requiresManualLabel": True,
        "actualPathWidthMm": round(bbox[2] - bbox[0], 3),
        "actualPathHeightMm": round(bbox[3] - bbox[1], 3),
        "bbox": [round(value, 3) for value in bbox],
        "componentCount": len(cluster),
        "isPathOnly": True,
        "hasTextElement": False,
        "finalCutPathData": final_path_data,
        "referencePathHash": _corel_path_hash(final_path_data),
        "splitFromCompoundObject": True,
        "splitClusterCount": cluster_count or 0,
        "splitWidthRatio": round(width_ratio, 4),
        "splitQualityStatus": split_quality_status,
        "requiresSplitReview": split_quality_status == "review_required",
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "updatedAt": datetime.now().isoformat(timespec="seconds"),
        "notes": "Corel Object Splitter tarafindan parent objeden uretilen child reference; exact onay icin operator label gerekir.",
    }


def split_corel_reference(reference_id: str) -> dict[str, Any]:
    library = _corel_reference_library_payload(include_path_data=False)
    if library.get("status") == "CORRUPT":
        return {"status": "ERROR", "code": "LIBRARY_CORRUPT", "message": library.get("parseError"), "dataSecurity": corel_reference_data_security_status()}
    references = library.get("references") if isinstance(library.get("references"), list) else []
    parent = next((row for row in references if str(row.get("referenceId") or row.get("objectId") or "") == str(reference_id)), None)
    if not parent:
        return {"status": "ERROR", "message": f"Corel referans bulunamadı: {reference_id}"}
    source_path = Path(str(parent.get("path") or parent.get("target") or ""))
    paths = _extract_svg_paths(source_path)
    clusters = _split_svg_paths_into_clusters(paths)
    if len(clusters) < 2:
        return {
            "status": "NEEDS_MANUAL_SPLIT",
            "message": "Otomatik split için yeterli boşluk bulunamadı; obje manuel kontrol gerektiriyor.",
            "referenceId": reference_id,
            "clusterCount": len(clusters),
        }
    existing_by_id = {str(row.get("referenceId") or row.get("objectId") or ""): row for row in references}
    children: list[dict[str, Any]] = []
    for index, cluster in enumerate(clusters, start=1):
        suggested_label, target_hint = _split_child_label_hint(parent, index, len(clusters))
        _, child = _write_corel_split_child_svg(
            parent,
            cluster,
            index,
            suggested_label=suggested_label,
            target_hint=target_hint,
            cluster_count=len(clusters),
        )
        existing = existing_by_id.get(child["referenceId"])
        if existing:
            if not bool(existing.get("approved") and existing.get("exactNameMatch")):
                existing.update({
                    "suggestedLabel": child.get("suggestedLabel") or existing.get("suggestedLabel") or "",
                    "readName": child.get("readName") or existing.get("readName") or "",
                    "targetNameHint": child.get("targetNameHint") or existing.get("targetNameHint") or "",
                    "targetNameHints": child.get("targetNameHints") or existing.get("targetNameHints") or [],
                    "targetNameKeyHint": child.get("targetNameKeyHint") or existing.get("targetNameKeyHint") or "",
                    "targetNameKeyHints": child.get("targetNameKeyHints") or existing.get("targetNameKeyHints") or [],
                    "finalCutPathData": child.get("finalCutPathData") or existing.get("finalCutPathData") or "",
                    "referencePathHash": child.get("referencePathHash") or existing.get("referencePathHash") or "",
                    "actualPathWidthMm": child.get("actualPathWidthMm") or existing.get("actualPathWidthMm"),
                    "actualPathHeightMm": child.get("actualPathHeightMm") or existing.get("actualPathHeightMm"),
                    "bbox": child.get("bbox") or existing.get("bbox") or [],
                    "componentCount": child.get("componentCount") or existing.get("componentCount"),
                    "splitClusterCount": len(clusters),
                    "splitWidthRatio": child.get("splitWidthRatio"),
                    "splitQualityStatus": child.get("splitQualityStatus"),
                    "requiresSplitReview": child.get("requiresSplitReview"),
                    "splitFromCompoundObject": True,
                    "styleReferenceOnly": True,
                    "labelStatus": child.get("labelStatus") or existing.get("labelStatus") or "unlabeled",
                    "status": child.get("status") or existing.get("status") or "unlabeled",
                    "requiresManualLabel": True,
                    "updatedAt": datetime.now().isoformat(timespec="seconds"),
                })
            children.append(_enrich_corel_reference_entry(existing, include_path_data=False))
        else:
            references.append(child)
            children.append(_enrich_corel_reference_entry(child, include_path_data=False))
    parent["labelStatus"] = "needs_split"
    parent["status"] = "needs_split"
    parent["needsSplit"] = True
    parent["styleReferenceOnly"] = True
    parent["approved"] = False
    parent["exactNameMatch"] = False
    parent["canApproveExact"] = False
    parent["actionNeeded"] = "Bu compound obje split child reference onayından sonra kullanılmalı."
    parent["updatedAt"] = datetime.now().isoformat(timespec="seconds")
    library["references"] = references
    save_result = _save_corel_name_reference_library(
        library,
        action="split_corel_reference",
        reference_id=reference_id,
        old_value={"parent": parent.get("parentReferenceId") or reference_id},
        new_value={"children": children},
        user_action_label="Corel compound object split",
    )
    return {
        "status": "OK",
        "referenceId": reference_id,
        "children": children,
        "summary": _corel_reference_summary(references),
        "dataSecurity": corel_reference_data_security_status(),
        "save": save_result,
    }


def resolve_exact_reference_by_name(input_name: str) -> dict[str, Any]:
    key = _corel_reference_key(input_name)
    library_state = _load_corel_name_reference_library()
    if isinstance(library_state, dict) and library_state.get("status") == "CORRUPT":
        return {
            "status": "LIBRARY_CORRUPT",
            "name": unicodedata.normalize("NFC", str(input_name or "")).strip(),
            "nameKey": key,
            "source": "corel_reference_unavailable",
            "readyForCut": False,
            "productionCandidate": False,
            "requiresOperatorReview": True,
            "exactReferenceRequired": True,
            "warning": "Corel reference library bozuk; backup'tan restore gerekli. Sessiz fallback yapılmadı.",
            "dataSecurity": corel_reference_data_security_status(),
        }
    entry = _corel_library_exact_reference_for_key(key)
    if not entry:
        return {
            "status": "MISSING_EXACT_LABEL",
            "name": unicodedata.normalize("NFC", str(input_name or "")).strip(),
            "nameKey": key,
            "source": "internal_ai_assisted_name_engine",
            "readyForCut": False,
            "productionCandidate": True,
            "requiresOperatorReview": True,
            "exactReferenceRequired": True,
            "warning": "Corel exact referansı bulunamadı. Bu isim internal Corel-like vector engine ile üretildi; birebir Corel referansı değildir.",
        }
    enriched = _enrich_corel_reference_entry(entry, include_path_data=True)
    final_path = str(enriched.get("finalCutPathData") or "")
    path_hash = _corel_path_hash(final_path)
    return {
        "status": "OK",
        "name": str(enriched.get("displayName") or enriched.get("manualNameLabel") or input_name),
        "nameKey": key,
        "source": "corel_exact_reference",
        "referenceId": enriched.get("referenceId"),
        "finalCutPathData": final_path,
        "readyForCut": bool(final_path),
        "productionCandidate": True,
        "requiresOperatorReview": True,  # SECURITY PATCH: exact ref still operator-review-gated (library correctness not assumed)
        "exactReferenceRequired": False,
        "canvasPathHash": path_hash,
        "exportPathHash": path_hash,
        "referencePathHash": path_hash,
    }


def resolve_name_cut_path(input_name: str) -> dict[str, Any]:
    """Resolve the production path source for a name without generating UI helpers.

    Exact Corel references are authoritative. When none exists, the caller may
    still generate a style-profile path, but it must remain review-gated.
    """
    exact = resolve_exact_reference_by_name(input_name)
    if exact.get("status") == "OK":
        return exact
    if exact.get("status") == "LIBRARY_CORRUPT":
        return exact
    key = _corel_reference_key(input_name)
    return {
        "status": "MISSING_EXACT_LABEL",
        "name": unicodedata.normalize("NFC", str(input_name or "")).strip(),
        "nameKey": key,
        "source": "internal_ai_assisted_name_engine",
        "referenceId": None,
        "finalCutPathData": "",
        "readyForCut": False,
        "productionCandidate": False,
        "requiresOperatorReview": True,
        "exactReferenceRequired": True,
        "warning": "Corel exact referansı bulunamadı. Bu çıktı internal Corel-like vector engine üretimidir; birebir Corel referansı değildir.",
    }


def _corel_reference_key(value: object) -> str:
    text = unicodedata.normalize("NFC", str(value or "")).strip()
    # Turkish-safe search key. Display labels keep their original Unicode text,
    # but exact matching must fold dotted/dotless variants predictably.
    folded = "".join({
        "ç": "c", "Ç": "c",
        "ğ": "g", "Ğ": "g",
        "ı": "i", "I": "i",
        "İ": "i", "i": "i",
        "ö": "o", "Ö": "o",
        "ş": "s", "Ş": "s",
        "ü": "u", "Ü": "u",
    }.get(char, char) for char in text)
    normalized = unicodedata.normalize("NFKD", folded)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", ascii_value.lower())


def _corel_path_hash(path_data: object) -> str:
    raw = str(path_data or "").strip()
    if not raw:
        return ""
    normalized = re.sub(r"\s+", " ", raw)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _svg_path_bbox_from_metrics(metrics: dict[str, Any]) -> tuple[float, float, float, float] | None:
    bbox = metrics.get("bbox") if isinstance(metrics, dict) else None
    if isinstance(bbox, list) and len(bbox) == 4:
        try:
            return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        except (TypeError, ValueError):
            return None
    return None


def _transform_svg_path_data_to_box(
    path_data: str,
    source_bbox: tuple[float, float, float, float],
    target_box: tuple[float, float, float, float],
    mirror_x: bool = False,
) -> tuple[str, tuple[float, float, float, float]]:
    min_x, min_y, max_x, max_y = source_bbox
    target_x, target_y, target_w, target_h = target_box
    source_w = max(0.001, max_x - min_x)
    source_h = max(0.001, max_y - min_y)
    scale = min(max(0.001, target_w) / source_w, max(0.001, target_h) / source_h)
    draw_w = source_w * scale
    draw_h = source_h * scale
    dx = target_x + ((target_w - draw_w) / 2.0) - (min_x * scale)
    dy = target_y + ((target_h - draw_h) / 2.0) - (min_y * scale)

    def transform_point(x_value: float, y_value: float) -> tuple[float, float]:
        px = (x_value * scale) + dx
        py = (y_value * scale) + dy
        if mirror_x:
            px = target_x + target_w - (px - target_x)
        return round(px, 3), round(py, 3)

    tokens = re.findall(r"[MmLlCcZz]|-?\d+(?:\.\d+)?", path_data or "")
    pieces: list[str] = []
    command = ""
    index = 0
    transformed_points: list[tuple[float, float]] = []
    while index < len(tokens):
        token = tokens[index]
        if token in {"M", "m", "L", "l", "C", "c", "Z", "z"}:
            command = token.upper()
            if command == "Z":
                pieces.append("Z")
            index += 1
            continue
        if command in {"M", "L"} and index + 1 < len(tokens):
            x_value = float(tokens[index])
            y_value = float(tokens[index + 1])
            px, py = transform_point(x_value, y_value)
            pieces.append(f"{command} {px:.3f} {py:.3f}")
            transformed_points.append((px, py))
            # SVG allows repeated point pairs after M; subsequent pairs are L.
            if command == "M":
                command = "L"
            index += 2
            continue
        if command == "C" and index + 5 < len(tokens):
            p1 = transform_point(float(tokens[index]), float(tokens[index + 1]))
            p2 = transform_point(float(tokens[index + 2]), float(tokens[index + 3]))
            p3 = transform_point(float(tokens[index + 4]), float(tokens[index + 5]))
            pieces.append(f"C {p1[0]:.3f} {p1[1]:.3f} {p2[0]:.3f} {p2[1]:.3f} {p3[0]:.3f} {p3[1]:.3f}")
            transformed_points.extend([p1, p2, p3])
            index += 6
            continue
        index += 1

    if transformed_points:
        xs = [point[0] for point in transformed_points]
        ys = [point[1] for point in transformed_points]
        bbox = (round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3))
    else:
        bbox = (round(target_x, 3), round(target_y, 3), round(target_x + target_w, 3), round(target_y + target_h, 3))
    return " ".join(pieces), bbox


def _corel_reference_override_payload(
    *,
    item: dict[str, Any],
    cfg: dict[str, Any],
    text: str,
    key: str,
    reference_path: Path,
    reference_info: dict[str, Any],
    source: str,
) -> dict[str, Any] | None:
    # DXF library entries (Leyla, 2026-05-28): use the ezdxf-based reader which
    # handles SPLINE/LWPOLYLINE/POLYLINE/LINE/ARC/CIRCLE. The legacy
    # corel_reference_importer.extract_dxf_path_data only knows polylines and
    # returns empty for SPLINE-only DXF (the audit verified this on ümit.dxf).
    if source == "dxf_library" and _dxf_library_api is not None and reference_path.suffix.lower() == ".dxf":
        dxf_result = _dxf_library_api.dxf_to_svg_path_data(reference_path)
        reference_path_data = str(dxf_result.get("path_data") or "")
        if not reference_path_data:
            return None
        loaded = {
            "path": str(reference_path),
            "format": "dxf",
            "pathData": reference_path_data,
            "pathOnly": True,
            "metrics": _corel_path_geometry_metrics(reference_path_data) if _corel_path_geometry_metrics is not None else {},
        }
    else:
        if _load_exact_reference_path_data is None:
            return None
        loaded = _load_exact_reference_path_data(reference_path)
        reference_path_data = str(loaded.get("pathData") or "")
    source_bbox = _svg_path_bbox_from_metrics(loaded.get("metrics") or {})
    if not reference_path_data or source_bbox is None:
        return None
    target_x = float(item.get("x_mm") or 0.0)
    target_y = float(item.get("y_mm") or 0.0)
    target_w = float(item.get("width_mm") or item.get("actual_path_width_mm") or cfg.get("target_name_width_mm") or 80.0)
    target_h = float(item.get("height_mm") or item.get("actual_path_height_mm") or cfg.get("target_name_height_mm") or 40.0)
    if cfg.get("mirror_cut"):
        target_x = float(cfg.get("width_mm") or 800.0) - target_x - target_w
    transformed_path_data, transformed_bbox = _transform_svg_path_data_to_box(
        reference_path_data,
        source_bbox,
        (target_x, target_y, target_w, target_h),
        mirror_x=bool(cfg.get("mirror_cut")),
    )
    transformed_metrics = _corel_path_geometry_metrics(transformed_path_data) if _corel_path_geometry_metrics is not None else {}
    object_id = str(reference_info.get("objectId") or reference_info.get("referenceId") or "")
    reason = str(reference_info.get("selectionReason") or reference_info.get("notes") or "")
    return {
        "corelReferenceOverrideApplied": True,
        "corel_reference_override_applied": True,
        "corelReferenceMode": "exact_golden",
        "corel_reference_mode": "exact_golden",
        "corelReferenceStatus": "corel_reference_exact_override",
        "corel_reference_status": "corel_reference_exact_override",
        "corelReferenceSource": source,
        "corel_reference_source": source,
        "corelReferenceKey": key,
        "corel_reference_key": key,
        "corelReferenceName": text,
        "corel_reference_name": text,
        "corelReferencePath": str(reference_path),
        "corel_reference_path": str(reference_path),
        "corelReferenceOriginalPathData": reference_path_data,
        "corel_reference_original_path_data": reference_path_data,
        "corelReferenceOriginalPathHash": _corel_path_hash(reference_path_data),
        "corel_reference_original_path_hash": _corel_path_hash(reference_path_data),
        "corelReferenceOverridePathData": transformed_path_data,
        "corel_reference_override_path_data": transformed_path_data,
        "corelReferencePathHash": _corel_path_hash(transformed_path_data),
        "corel_reference_path_hash": _corel_path_hash(transformed_path_data),
        "corelReferenceSourceBBox": list(source_bbox),
        "corel_reference_source_bbox": list(source_bbox),
        "corelReferenceTransformedBBox": list(transformed_bbox),
        "corel_reference_transformed_bbox": list(transformed_bbox),
        "corelReferenceMetrics": loaded.get("metrics") or {},
        "corel_reference_metrics": loaded.get("metrics") or {},
        "corelReferenceTransformedMetrics": transformed_metrics,
        "corel_reference_transformed_metrics": transformed_metrics,
        "corelReferenceStyleOnly": False,
        "corel_reference_style_only": False,
        "corelReferenceExactNameMatch": True,
        "corel_reference_exact_name_match": True,
        "corelReferenceSelectedObjectId": object_id,
        "corel_reference_selected_object_id": object_id,
        "corelReferenceSelectionReason": reason,
        "corel_reference_selection_reason": reason,
    }


def _corel_library_exact_reference_for_key(key: str) -> dict[str, Any] | None:
    library = _load_corel_name_reference_library()
    if isinstance(library, dict) and library.get("status") == "CORRUPT":
        return None
    references = library.get("references") if isinstance(library, dict) else []
    if not isinstance(references, list):
        return None
    for entry in references:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("nameKey") or "") != key:
            continue
        if not (
            bool(entry.get("approved"))
            and bool(entry.get("exactNameMatch"))
            and not bool(entry.get("styleReferenceOnly"))
            and str(entry.get("labelStatus") or entry.get("status") or "") == "exact_approved"
        ):
            continue
        loaded = _load_corel_reference_path_payload(entry)
        final_path = str(entry.get("finalCutPathData") or loaded.get("pathData") or "")
        # Imported Corel references can be backed either by an extracted SVG
        # file or by persisted finalCutPathData. Exact resolution should not
        # reject an approved record only because its source path is relative or
        # unavailable after import/restore; the production geometry is the path.
        if final_path:
            entry["finalCutPathData"] = final_path
            entry["referencePathHash"] = _corel_path_hash(final_path)
            return entry
    return None


def _corel_exact_reference_override_for_item(item: dict[str, Any], cfg: dict[str, Any], style: str) -> dict[str, Any] | None:
    if _load_exact_reference_path_data is None:
        return None
    text = str(item.get("name_text") or item.get("preview_text") or item.get("text") or item.get("name") or "").strip()
    if not text:
        return None
    # PRIMARY: Leyla's DXF library (2026-05-28). Style-agnostic — the library
    # IS the new primary source, regardless of font style. Disable per-item
    # via `dxf_library_lookup_enabled=False`. The legacy style-gated paths
    # below are preserved as fallback for operator-approved SVG/AI references.
    dxf_lookup_enabled = _truthy_setting(
        item.get("dxf_library_lookup_enabled", cfg.get("dxf_library_lookup_enabled")),
        True,
    )
    if dxf_lookup_enabled and _dxf_library_api is not None:
        try:
            lookup = _dxf_library_api.resolve_name_for_order(PROJECT_ROOT, text)
        except Exception:  # noqa: BLE001 — library lookup must never break production
            lookup = None
        if lookup and lookup.get("status") == "FOUND":
            entry = lookup.get("entry") or {}
            dxf_path = PROJECT_ROOT / str(entry.get("file_path") or "")
            if dxf_path.exists():
                payload = _corel_reference_override_payload(
                    item=item,
                    cfg=cfg,
                    text=text,
                    key=_corel_reference_key(text),
                    reference_path=dxf_path,
                    reference_info={
                        "source": "dxf_library",
                        "size_group": entry.get("size_group"),
                        "bbox_mm": entry.get("bbox_mm"),
                        "library_entry": entry,
                    },
                    source="dxf_library",
                )
                if payload:
                    return payload
    # FALLBACK: legacy SVG/AI operator-approved exact references (İrem, Ümit,
    # Ahmet, Ayşe & Mehmet etc.). Still style-gated to avoid surprises.
    style_token = _normalize_token(style)
    default_enabled = "brannboll" in style_token or _is_mochary_user_corel_calibrated_style(style)
    enabled = _truthy_setting(
        item.get("corel_exact_reference_override_enabled", cfg.get("corel_exact_reference_override_enabled")),
        default_enabled,
    )
    if not enabled:
        return None
    key = _corel_reference_key(text)
    library_entry = _corel_library_exact_reference_for_key(key)
    if library_entry:
        library_path = Path(str(library_entry.get("path") or library_entry.get("target") or ""))
        payload = _corel_reference_override_payload(
            item=item,
            cfg=cfg,
            text=text,
            key=key,
            reference_path=library_path,
            reference_info=library_entry,
            source="corel_reference_library",
        )
        if payload:
            return payload
    selection = _load_corel_exact_reference_selection().get("references", {})
    selection_info = selection.get(key, {}) if isinstance(selection, dict) else {}
    candidates: list[Path] = []
    target = selection_info.get("target") if isinstance(selection_info, dict) else None
    if target:
        candidates.append(Path(str(target)))
    for suffix in [".svg", ".dxf", ".ai"]:
        candidates.append(COREL_EXACT_REFERENCE_DIR / f"{key}{suffix}")
    reference_path = next((path for path in candidates if path.exists()), None)
    if not reference_path:
        return None
    exact_match = bool(selection_info.get("exactNameMatch")) if isinstance(selection_info, dict) else False
    style_only = bool(selection_info.get("styleReferenceOnly", not exact_match)) if isinstance(selection_info, dict) else True
    if style_only or not exact_match:
        return None
    return _corel_reference_override_payload(
        item=item,
        cfg=cfg,
        text=text,
        key=key,
        reference_path=reference_path,
        reference_info=selection_info if isinstance(selection_info, dict) else {},
        source="exact_reference_selection",
    )


def _ai_quality_enabled_for_item(item: dict[str, Any], cfg: dict[str, Any], style: str) -> bool:
    default_enabled = "brannboll" in _normalize_token(style)
    if "ai_quality_enabled" in item:
        return _truthy_setting(item.get("ai_quality_enabled"), default_enabled)
    if "ai_quality_enabled" in cfg:
        return _truthy_setting(cfg.get("ai_quality_enabled"), default_enabled)
    return default_enabled


def _ai_laser_quality_score_candidate(
    item: dict[str, Any],
    raw_contours: list[list[tuple[float, float]]],
    offset_contours: list[list[tuple[float, float]]],
    bridge_contours: list[list[tuple[float, float]]],
    welded_contours: list[list[tuple[float, float]]],
    repair: dict[str, Any],
    offset_mm: float,
    bridge_mm: float,
) -> dict[str, Any]:
    text = str(item.get("preview_text") or item.get("name_text") or item.get("text") or item.get("name") or "")
    bbox = _contours_bbox(welded_contours)
    width_mm = max(0.0, (bbox[2] - bbox[0]) if bbox else 0.0)
    height_mm = max(0.0, (bbox[3] - bbox[1]) if bbox else 0.0)
    bbox_area = max(1.0, width_mm * height_mm)
    area_ratio = _contours_area_mm2(welded_contours) / bbox_area
    long_thin_artifacts = _long_thin_artifact_count(welded_contours, bbox)
    long_thin_artifacts = _long_thin_artifact_count(welded_contours, bbox)
    raw_contour_count = max(1, len(raw_contours))
    welded_contour_count = len(welded_contours)
    component_count = int(repair.get("componentCount") or repair.get("component_count") or 0)
    unresolved_count = int(repair.get("unresolvedPartCount") or repair.get("unresolved_part_count") or 0)
    missing = repair.get("missingGlyphChars") or repair.get("missing_glyph_chars") or []
    has_turkish = any(ch in TURKISH_DIACRITIC_CHARS for ch in text)
    has_detached_marks = bool(repair.get("hasDetachedDots") or repair.get("has_detached_dots"))

    readability = 100.0
    if not welded_contours:
        readability -= 65
    if height_mm < 18:
        readability -= (18 - height_mm) * 3
    if width_mm > 112:
        readability -= (width_mm - 112) * 0.55
    if component_count != 1:
        readability -= 25 + (component_count * 4)
    if missing:
        readability -= 45

    font_character = 100.0 - max(0.0, offset_mm - 0.40) * 55.0
    if offset_mm < 0.18:
        font_character -= 12
    if area_ratio > 0.74:
        font_character -= (area_ratio - 0.74) * 120

    weld_quality = 100.0
    if component_count != 1:
        weld_quality -= 45 + max(0, component_count - 1) * 8
    if unresolved_count:
        weld_quality -= unresolved_count * 22
    if pyclipper is None:
        weld_quality -= 35

    turkish_mark = 100.0
    if has_turkish and has_detached_marks:
        turkish_mark -= 28
    if missing:
        turkish_mark -= 45
    if bridge_contours and bridge_mm < 0.25:
        turkish_mark -= 8

    no_blob = 100.0
    if area_ratio > 0.78:
        no_blob -= (area_ratio - 0.78) * 180
    if area_ratio < 0.04:
        no_blob -= (0.04 - area_ratio) * 500
    no_blob -= max(0.0, offset_mm - 0.50) * 70
    no_blob -= long_thin_artifacts * 18

    no_internal_overlap = 98.0 if pyclipper is not None else 62.0
    if welded_contour_count > raw_contour_count * 1.75:
        no_internal_overlap -= min(35.0, (welded_contour_count - raw_contour_count * 1.75) * 2.0)
    if component_count == 1:
        no_internal_overlap += 2
    no_internal_overlap -= long_thin_artifacts * 24

    corel_similarity = 96.0
    corel_similarity -= abs(offset_mm - 0.35) * 24
    if area_ratio > 0.74:
        corel_similarity -= (area_ratio - 0.74) * 90
    if component_count != 1:
        corel_similarity -= 20
    corel_similarity -= long_thin_artifacts * 26

    export_consistency = 100.0
    if not welded_contours:
        export_consistency = 0.0

    fields = {
        "readabilityScore": _clamp_score(readability),
        "fontCharacterScore": _clamp_score(font_character),
        "weldQualityScore": _clamp_score(weld_quality),
        "turkishMarkScore": _clamp_score(turkish_mark),
        "noBlobScore": _clamp_score(no_blob),
        "noInternalOverlapScore": _clamp_score(no_internal_overlap),
        "corelReferenceSimilarityScore": _clamp_score(corel_similarity),
        "exportConsistencyScore": _clamp_score(export_consistency),
    }
    turkish_complexity_penalty = min(
        9.0,
        sum(1.15 for ch in text if ch in TURKISH_DOT_MARK_CHARS)
        + sum(1.45 for ch in text if ch in TURKISH_TAIL_MARK_CHARS)
        + sum(1.65 for ch in text if ch in TURKISH_BREVE_MARK_CHARS)
        + (1.0 if any(ch in "ıI" for ch in text) else 0.0),
    )
    final_score = _clamp_score((sum(fields.values()) / len(fields)) - turkish_complexity_penalty)
    if missing or component_count != 1 or unresolved_count:
        status = "failed"
    elif final_score >= AI_LASER_QUALITY_PASS_SCORE:
        status = "passed"
    elif final_score >= 70:
        status = "review"
    else:
        status = "failed"
    too_thick = offset_mm >= 0.50 and (fields["noBlobScore"] < 82 or fields["fontCharacterScore"] < 88)
    reasons: list[str] = []
    if component_count != 1:
        reasons.append("component_count_not_single")
    if has_detached_marks:
        reasons.append("detached_mark_risk")
    if missing:
        reasons.append("missing_glyph")
    if too_thick:
        reasons.append("too_thick_or_blob_risk")
    if long_thin_artifacts:
        reasons.append("long_thin_internal_artifact")
    if status == "passed" and not reasons:
        reasons.append("deterministic_candidate_passed")
    return {
        **fields,
        "aiQualityScore": final_score,
        "aiQualityStatus": status,
        "reason": ", ".join(reasons),
        "tooThick": too_thick,
        "offsetMm": round(offset_mm, 3),
        "bridgeMm": round(bridge_mm, 3),
        "areaRatio": round(area_ratio, 4),
        "widthMm": round(width_mm, 3),
        "heightMm": round(height_mm, 3),
        "rawContourCount": len(raw_contours),
        "weldedContourCount": welded_contour_count,
        "componentCount": component_count,
        "longThinArtifactCount": long_thin_artifacts,
    }


def _build_ai_laser_quality_candidate(
    item: dict[str, Any],
    cfg: dict[str, Any],
    raw_contours: list[list[tuple[float, float]]],
    offset_mm: float,
    bridge_mm: float,
    candidate_index: int,
) -> dict[str, Any]:
    candidate_item = {**item, "offset_mm": offset_mm, "smart_bridge_width_mm": bridge_mm}
    offset_contours = _outline_contours_for_item(candidate_item, cfg, path_role="cut")
    bridge_enabled = _truthy_setting(
        candidate_item.get("smart_bridge_enabled", cfg.get("smart_bridge_enabled")),
        False,
    )
    bridge_result = _smart_bridge_same_name_contours(
        offset_contours,
        offset_mm,
        enabled=bridge_enabled,
        bridge_width_mm=bridge_mm,
    )
    contours = bridge_result["contours"]
    repair = _name_cut_auto_repair_analysis(candidate_item, cfg, contours)
    repair["unresolvedPartCount"] = int(bridge_result.get("unresolved_part_count") or 0)
    repair["unresolved_part_count"] = int(bridge_result.get("unresolved_part_count") or 0)
    score = _ai_laser_quality_score_candidate(
        candidate_item,
        raw_contours,
        offset_contours,
        bridge_result.get("bridge_contours") or [],
        contours,
        repair,
        offset_mm,
        bridge_mm,
    )
    candidate_id = f"offset-{offset_mm:.2f}-bridge-{bridge_mm:.2f}".replace(".", "_")
    return {
        "id": candidate_id,
        "candidateIndex": candidate_index,
        "candidate_index": candidate_index,
        "offsetMm": round(offset_mm, 3),
        "offset_mm": round(offset_mm, 3),
        "bridgeMm": round(bridge_mm, 3),
        "bridge_mm": round(bridge_mm, 3),
        "raw_contours": raw_contours,
        "offset_contours": offset_contours,
        "bridge_contours": bridge_result.get("bridge_contours") or [],
        "welded_contours": contours,
        "repair": repair,
        "bridge_result": bridge_result,
        "score": score,
        "summary": {
            "id": candidate_id,
            "offsetMm": round(offset_mm, 3),
            "bridgeMm": round(bridge_mm, 3),
            "aiQualityScore": score["aiQualityScore"],
            "aiQualityStatus": score["aiQualityStatus"],
            "readabilityScore": score["readabilityScore"],
            "fontCharacterScore": score["fontCharacterScore"],
            "weldQualityScore": score["weldQualityScore"],
            "turkishMarkScore": score["turkishMarkScore"],
            "noBlobScore": score["noBlobScore"],
            "noInternalOverlapScore": score["noInternalOverlapScore"],
            "corelReferenceSimilarityScore": score["corelReferenceSimilarityScore"],
            "exportConsistencyScore": score["exportConsistencyScore"],
            "tooThick": score["tooThick"],
            "reason": score["reason"],
        },
    }


def _select_ai_laser_quality_candidate(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, bool]:
    if not candidates:
        return None, False
    sorted_candidates = sorted(
        candidates,
        key=lambda candidate: (
            int(candidate.get("score", {}).get("aiQualityScore") or 0),
            -abs(float(candidate.get("offsetMm") or 0) - 0.35),
            -float(candidate.get("offsetMm") or 0),
        ),
        reverse=True,
    )
    selected = sorted_candidates[0]
    passed = int(selected.get("score", {}).get("aiQualityScore") or 0) >= AI_LASER_QUALITY_PASS_SCORE and selected.get("score", {}).get("aiQualityStatus") == "passed"
    return selected, passed


def _mark_type_for_char(ch: str) -> str:
    if ch in "iİüÜöÖ":
        return "dot"
    if ch in "ğĞ":
        return "breve"
    if ch in "şŞçÇ":
        return "tail"
    return "mark"


def _glyph_identity_parser(text: str) -> list[dict[str, Any]]:
    glyphs: list[dict[str, Any]] = []
    for index, ch in enumerate(text):
        if not ch.strip() or ch == "&":
            continue
        marks: list[str] = []
        if ch in "üÜöÖ":
            marks = ["dot_left", "dot_right"]
        elif ch in "iİ":
            marks = ["dot"]
        elif ch in "ğĞ":
            marks = ["breve"]
        elif ch in "şŞ":
            marks = ["cedilla_tail"]
        elif ch in "çÇ":
            marks = ["cedilla_tail"]
        glyph_type = "marked_letter" if marks else "base_letter"
        glyphs.append(
            {
                "index": len(glyphs),
                "sourceIndex": index,
                "glyph": ch,
                "unicode": f"U+{ord(ch):04X}",
                "case": "upper" if ch.isupper() else "lower",
                "type": glyph_type,
                "hasMark": bool(marks),
                "marks": marks,
                "isTurkish": ch in TURKISH_DIACRITIC_CHARS,
                "mustBeDotless": ch in "ıI",
                "forbidsMarks": ch in DOTLESS_CHARS or ch in "ıI",
            }
        )
    return glyphs


def _glyph_ownership_validator(
    text: str,
    glyphs: list[dict[str, Any]],
    repair: dict[str, Any],
    designer_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected_mark_count = sum(len(glyph.get("marks") or []) for glyph in glyphs)
    planned_marks = (designer_plan or {}).get("marks") or []
    missing_glyphs = repair.get("missingGlyphChars") or repair.get("missing_glyph_chars") or []
    wrong_glyph_marks: list[str] = []
    extra_marks: list[str] = []
    detached_marks: list[str] = []
    if any(glyph.get("glyph") == "S" and glyph.get("marks") for glyph in glyphs):
        extra_marks.append("S")
    for glyph in glyphs:
        ch = str(glyph.get("glyph") or "")
        if glyph.get("mustBeDotless") and glyph.get("marks"):
            extra_marks.append(ch)
        if glyph.get("hasMark"):
            owned = [mark for mark in planned_marks if mark.get("glyph") == ch]
            if not owned:
                detached_marks.append(ch)
            for mark in owned:
                if ch == "ü" and "S" in mark.get("connectTo", ""):
                    wrong_glyph_marks.append("ü->S")
                if mark.get("avoidBlob") is not True:
                    wrong_glyph_marks.append(f"{ch}:blob-risk")
    marked_glyphs = [glyph for glyph in glyphs if glyph.get("hasMark")]
    if expected_mark_count and len(planned_marks) < len(marked_glyphs):
        detached_marks.append("planned_mark_missing")
    resolved_component_count = int(
        repair.get("componentCountAfterRepair")
        or repair.get("component_count_after_repair")
        or repair.get("componentCount")
        or repair.get("component_count")
        or 0
    )
    planned_mark_glyphs = {str(mark.get("glyph") or "") for mark in planned_marks}
    marked_glyph_names = {str(glyph.get("glyph") or "") for glyph in marked_glyphs}
    marks_resolved_by_designer_plan = bool(
        marked_glyph_names
        and resolved_component_count == 1
        and marked_glyph_names.issubset(planned_mark_glyphs)
        and not missing_glyphs
        and not wrong_glyph_marks
        and not extra_marks
    )
    if (repair.get("hasDetachedDots") or repair.get("has_detached_dots")) and not marks_resolved_by_designer_plan:
        detached_marks.append("analysis_detached_mark")
    passed = not missing_glyphs and not wrong_glyph_marks and not extra_marks and not detached_marks
    status = "passed"
    if missing_glyphs:
        status = "glyph_identity_failed"
    elif extra_marks:
        status = "extra_mark_generated"
    elif wrong_glyph_marks:
        status = "mark_attached_to_wrong_glyph"
    elif detached_marks:
        status = "detached_turkish_mark"
    return {
        "glyphIdentity": glyphs,
        "glyph_identity": glyphs,
        "glyphIdentityPassed": not missing_glyphs,
        "glyph_identity_passed": not missing_glyphs,
        "markOwnershipPassed": passed,
        "mark_ownership_passed": passed,
        "glyphOwnershipStatus": status,
        "glyph_ownership_status": status,
        "detachedMarkCount": len(detached_marks),
        "detached_mark_count": len(detached_marks),
        "wrongGlyphMarkCount": len(wrong_glyph_marks),
        "wrong_glyph_mark_count": len(wrong_glyph_marks),
        "extraMarkCount": len(extra_marks),
        "extra_mark_count": len(extra_marks),
        "detachedMarkDetails": detached_marks,
        "wrongGlyphMarkDetails": wrong_glyph_marks,
        "extraMarkDetails": extra_marks,
        "expectedMarkCount": expected_mark_count,
        "expected_mark_count": expected_mark_count,
    }


def _brannboll_designer_profile() -> dict[str, Any]:
    return {
        "profile": "BrannbollDesignerProfile",
        "plateMm": [800, 600],
        "targetNameMm": [80, 40],
        "gapMm": 1.0,
        "bridgeMinMm": 0.20,
        "bridgeMaxMm": 0.35,
        "dotBridgeMm": [0.20, 0.25],
        "tailBridgeMm": [0.25, 0.30],
        "letterBridgeMm": [0.25, 0.30],
        "forbiddenZones": [
            "inside_letter_counter",
            "upper_decorative_loop",
            "long_underline_or_swash",
            "wrong_glyph_mark_area",
            "between_different_name_objects",
            "very_tight_inner_curve",
        ],
        "pairRules": {
            "S:ü": {
                "preferredConnection": "natural_lower_or_mid_flow",
                "forbiddenZones": ["upper_decorative_loop", "inside_counter"],
                "connectorWidthMm": 0.28,
                "note": "S üst süsünden ü noktasına bağlantı yapılmaz.",
            },
            "ü:m": {"preferredConnection": "baseline_exit_to_entry", "connectorWidthMm": 0.28},
            "m:e": {"preferredConnection": "lower_flow_tangent", "connectorWidthMm": 0.28},
            "e:y": {"preferredConnection": "baseline_flow_preserve_counter", "connectorWidthMm": 0.28},
            "y:y": {"preferredConnection": "lower_tail_flow", "connectorWidthMm": 0.28},
            "y:e": {"preferredConnection": "smooth_exit_to_final_e", "connectorWidthMm": 0.28},
            "Ç:a": {"preferredConnection": "main_body_lower_flow", "connectorWidthMm": 0.28},
            "a:ğ": {"preferredConnection": "baseline_exit_to_entry", "connectorWidthMm": 0.27},
            "ğ:r": {"preferredConnection": "lower_body_exit", "connectorWidthMm": 0.27},
            "r:ı": {"preferredConnection": "baseline_exit_to_dotless_entry", "connectorWidthMm": 0.27},
        },
    }


@lru_cache(maxsize=1)
def _mochary_corel_production_profile_payload() -> dict[str, Any]:
    try:
        return json.loads(MOCHARY_COREL_PRODUCTION_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _designer_profile_for_style(style: object) -> dict[str, Any]:
    if _is_mochary_user_corel_calibrated_style(style):
        payload = _mochary_corel_production_profile_payload()
        internal_payload = _mochary_internal_production_profile_payload()
        learned = internal_payload.get("goldenStyleRuleLearner") if isinstance(internal_payload.get("goldenStyleRuleLearner"), dict) else {}
        learned_style_metrics = learned.get("styleMetrics") if isinstance(learned.get("styleMetrics"), dict) else {}
        learned_pair_rules = learned.get("pairRules") if isinstance(learned.get("pairRules"), dict) else {}
        aggregate = payload.get("styleAggregate") if isinstance(payload.get("styleAggregate"), dict) else {}
        pair_rules = {
            "S:ü": {"preferredConnection": "upper_initial_to_dotted_lower_mid_flow", "forbiddenZones": ["decorative_upper_loop", "inside_counter", "wrong_glyph_mark_area"], "connectorWidthMm": 0.24, "note": "S üst süsünden veya ü noktasından uzun çapraz bağlantı yapılmaz."},
            "M:ü": {"preferredConnection": "upper_initial_to_dotted_lower_mid_flow", "forbiddenZones": ["decorative_upper_loop", "inside_counter", "wrong_glyph_mark_area"], "connectorWidthMm": 0.24, "note": "M baş harfi ü gövdesine doğal orta/alt akıştan yaklaşır; noktalara bağlanmaz."},
            "Ç:a": {"preferredConnection": "initial_lower_body_to_baseline_flow", "connectorWidthMm": 0.25, "forbiddenZones": ["cedilla_tail", "inside_counter"]},
            "Ş:ü": {"preferredConnection": "initial_lower_body_to_dotted_lower_flow", "connectorWidthMm": 0.24, "forbiddenZones": ["tail_mark", "dot_mark", "inside_counter"]},
            "Ü:m": {"preferredConnection": "baseline_script_flow", "connectorWidthMm": 0.24, "sourceRule": "valid_golden_pair_rule"},
            "m:i": {"preferredConnection": "baseline_to_dotted_letter_flow", "connectorWidthMm": 0.23, "sourceRule": "valid_golden_pair_rule"},
            "i:t": {"preferredConnection": "dotted_letter_to_terminal_flow", "connectorWidthMm": 0.23, "sourceRule": "valid_golden_pair_rule"},
            "ü:c": {"preferredConnection": "dotted_lower_to_baseline_flow", "connectorWidthMm": 0.23, "sourceRule": "derived_from_m_i_dotted_flow"},
            "h:i": {"preferredConnection": "ascender_to_dotted_letter_flow", "connectorWidthMm": 0.23, "sourceRule": "derived_from_m_i_dotted_flow"},
            "ü:m": {"preferredConnection": "baseline_exit_to_entry", "connectorWidthMm": 0.24},
            "m:e": {"preferredConnection": "lower_flow_tangent", "connectorWidthMm": 0.24},
            "e:y": {"preferredConnection": "baseline_flow_preserve_counter", "connectorWidthMm": 0.24},
            "y:y": {"preferredConnection": "lower_tail_flow", "connectorWidthMm": 0.24},
            "y:e": {"preferredConnection": "smooth_exit_to_final_e", "connectorWidthMm": 0.24},
            "a:ğ": {"preferredConnection": "baseline_exit_to_owner_breve_glyph", "connectorWidthMm": 0.24},
            "ğ:r": {"preferredConnection": "baseline_flow_after_breve_glyph", "connectorWidthMm": 0.24},
            "r:ı": {"preferredConnection": "baseline_exit_to_dotless_entry", "connectorWidthMm": 0.24},
            "Ö:z": {"preferredConnection": "baseline_script_flow", "connectorWidthMm": 0.24, "sourceRule": "valid_golden_pair_rule"},
            "z:g": {"preferredConnection": "baseline_script_flow", "connectorWidthMm": 0.24, "sourceRule": "valid_golden_pair_rule"},
            "g:e": {"preferredConnection": "baseline_script_flow", "connectorWidthMm": 0.24, "sourceRule": "valid_golden_pair_rule"},
        }
        for pair, learned_rule in learned_pair_rules.items():
            if not isinstance(learned_rule, dict) or pair in pair_rules:
                continue
            pair_rules[pair] = {
                "preferredConnection": str(learned_rule.get("connectionDirection") or "baseline_script_flow"),
                "connectorWidthMm": 0.24,
                "sourceRule": "golden_style_rule_learner",
                "forbiddenZones": learned_rule.get("forbiddenZones") or ["inside_counter", "wrong_glyph_mark_area", "upper_decorative_loop"],
            }
        return {
            "profile": "MocharyCorelProductionProfile",
            "source": str(payload.get("source") or "Corel golden reference object library"),
            "styleRuleSource": str(learned.get("source") or ""),
            "plateMm": [float(payload.get("plateWidthMm") or 800), float(payload.get("plateHeightMm") or 600)],
            "targetNameMm": [float(payload.get("targetNameWidthMm") or 80), float(payload.get("targetNameHeightMm") or 40)],
            "gapMm": float(payload.get("minGapMm") or 1),
            "defaultOffsetMm": float(payload.get("defaultOffsetMm") or 0.3),
            "learnedMedianAspect": ((aggregate.get("bboxAspect") or {}).get("median") if isinstance(aggregate.get("bboxAspect"), dict) else None),
            "learnedMedianCurveCount": ((aggregate.get("curveCount") or {}).get("median") if isinstance(aggregate.get("curveCount"), dict) else None),
            "goldenTargetWidthHeightRatioMedian": learned_style_metrics.get("targetWidthHeightRatioMedian"),
            "goldenFillRatioMedian": learned_style_metrics.get("fillRatioMedian"),
            "goldenStrokeThicknessProxyMedianMm": learned_style_metrics.get("strokeThicknessProxyMedianMm"),
            "glyphOverrideDefaultEnabled": False,
            "manualApprovedGlyphOverrideOnly": True,
            "autoExtractedGlyphsProductionForbidden": True,
            "bridgeMinMm": 0.20,
            "bridgeMaxMm": 0.35,
            "dotBridgeMm": [0.20, 0.25],
            "tailBridgeMm": [0.25, 0.30],
            "letterBridgeMm": [0.25, 0.30],
            "forbiddenZones": [
                "inside_letter_counter",
                "decorative_upper_loop",
                "wrong_glyph_mark_area",
                "between_different_name_objects",
                "tiny_counter_area",
            ],
            "pairRules": pair_rules,
        }
    return _brannboll_designer_profile()


def _designer_letter_connection_plan(glyphs: list[dict[str, Any]], selected_bridge_mm: float, profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    profile = profile or _brannboll_designer_profile()
    rules = profile["pairRules"]
    connections: list[dict[str, Any]] = []
    for index in range(len(glyphs) - 1):
        from_glyph = str(glyphs[index].get("glyph") or "")
        to_glyph = str(glyphs[index + 1].get("glyph") or "")
        pair = f"{from_glyph}:{to_glyph}"
        rule = rules.get(pair, {})
        if not rule:
            preferred = "baseline_exit_to_entry"
            if from_glyph in "ğĞüÜöÖiİçÇşŞ" or to_glyph in "ğĞüÜöÖiİçÇşŞ":
                preferred = "main_body_lower_tangent"
            rule = {
                "preferredConnection": preferred,
                "forbiddenZones": ["inside_counter", "upper_decorative_loop"],
                "connectorWidthMm": round(max(0.25, min(0.30, selected_bridge_mm)), 3),
            }
        connections.append(
            {
                "pair": pair,
                "fromGlyph": from_glyph,
                "toGlyph": to_glyph,
                "rule": rule.get("preferredConnection"),
                "preferredZone": rule.get("preferredConnection"),
                "forbiddenZones": rule.get("forbiddenZones", ["inside_counter", "upper_decorative_loop"]),
                "connectorType": "smooth_tangent_bridge_or_existing_font_flow",
                "connectorWidthMm": round(float(rule.get("connectorWidthMm") or max(0.25, min(0.30, selected_bridge_mm))), 3),
                "reason": rule.get("note", "Use natural script flow and preserve counters."),
            }
        )
    return connections


def _turkish_mark_bridge_plan(glyphs: list[dict[str, Any]], selected_bridge_mm: float) -> list[dict[str, Any]]:
    mark_plan: list[dict[str, Any]] = []
    for glyph in glyphs:
        ch = str(glyph.get("glyph") or "")
        marks = glyph.get("marks") or []
        for mark in marks:
            if ch in TURKISH_DOT_MARK_CHARS:
                bridge_width = max(0.20, min(0.25, selected_bridge_mm))
                bridge_type = "thin_smooth_designer_bridge"
                connect_to = f"{ch}_main_body"
            elif ch in TURKISH_TAIL_MARK_CHARS:
                bridge_width = max(0.25, min(0.30, selected_bridge_mm))
                bridge_type = "tail_weld_to_main_body"
                connect_to = f"{ch}_lower_body"
            elif ch in TURKISH_BREVE_MARK_CHARS:
                bridge_width = max(0.20, min(0.25, selected_bridge_mm))
                bridge_type = "breve_thin_bridge_to_upper_body"
                connect_to = f"{ch}_upper_body"
            else:
                bridge_width = max(0.20, min(0.30, selected_bridge_mm))
                bridge_type = "mark_bridge"
                connect_to = f"{ch}_main_body"
            mark_plan.append(
                {
                    "glyph": ch,
                    "mark": mark,
                    "markType": _mark_type_for_char(ch),
                    "connectTo": connect_to,
                    "bridgeType": bridge_type,
                    "connectorType": bridge_type,
                    "bridgeWidthMm": round(bridge_width, 3),
                    "widthMm": round(bridge_width, 3),
                    "avoidBlob": True,
                    "cannotAttachTo": ["S"] if ch in {"ü", "Ü", "ö", "Ö", "i", "İ"} else [],
                }
            )
    return mark_plan


def _designer_weld_plan_for_item(
    item: dict[str, Any],
    selected_offset_mm: float,
    selected_bridge_mm: float,
    ai_score: dict[str, Any],
    style: object = "",
) -> dict[str, Any]:
    text = str(item.get("preview_text") or item.get("name_text") or item.get("text") or item.get("name") or "")
    glyphs = _glyph_identity_parser(text)
    profile = _designer_profile_for_style(style or item.get("style") or item.get("font_family") or "")
    connections = _designer_letter_connection_plan(glyphs, selected_bridge_mm, profile)
    mark_bridge_plan = _turkish_mark_bridge_plan(glyphs, selected_bridge_mm)
    return {
        "name": text,
        "strategy": "designer_guided_weld",
        "engine": "Glyph-Aware Full Designer Cut Engine",
        "planner": "Algorithm-Guided Designer Weld Planner (deterministic)",
        "aiFinalPathGenerated": False,
        "deterministicEngine": "FontTools + pyclipper offset/union + planned micro-bridges",
        "glyphIdentity": glyphs,
        "brannbollDesignerProfile": profile if profile.get("profile") == "BrannbollDesignerProfile" else {},
        "mocharyCorelProductionProfile": profile if profile.get("profile") == "MocharyCorelProductionProfile" else {},
        "designerProfile": profile,
        "selectedOffsetMm": round(selected_offset_mm, 3),
        "selectedBridgeMm": round(selected_bridge_mm, 3),
        "connections": connections,
        "letterConnectionPlan": connections,
        "marks": mark_bridge_plan,
        "markBridgePlan": mark_bridge_plan,
        "forbiddenConnections": [
            {"zone": zone, "reason": "ForbiddenZoneEngine prevents ugly or invalid bridge/weld placement."}
            for zone in profile["forbiddenZones"]
        ],
        "qualityRules": {
            "preserveFontCharacter": True,
            "avoidBlob": True,
            "avoidInternalGarbagePath": True,
            "preferManualReferenceSimilarity": True,
            "canvasMustEqualExport": True,
            "pathOnlyExport": True,
            "reviewRequiredBlocksReadyForCut": True,
        },
        "aiQualityScore": ai_score.get("aiQualityScore"),
        "reason": ai_score.get("reason") or "designer_flow_plan_from_candidate_metrics",
    }


def _designer_weld_quality_analysis(
    item: dict[str, Any],
    raw_contours: list[list[tuple[float, float]]],
    bridge_contours: list[list[tuple[float, float]]],
    welded_contours: list[list[tuple[float, float]]],
    repair: dict[str, Any],
    ai_score: dict[str, Any],
    selected_offset_mm: float,
    selected_bridge_mm: float,
    glyph_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    glyph_validation = glyph_validation or {}
    text = str(item.get("preview_text") or item.get("name_text") or item.get("text") or item.get("name") or "")
    bbox = _contours_bbox(welded_contours)
    bbox_area = 1.0
    if bbox:
        bbox_area = max(1.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
    area_ratio = _contours_area_mm2(welded_contours) / bbox_area
    long_thin_artifacts = _long_thin_artifact_count(welded_contours, bbox)
    component_count = int(repair.get("componentCount") or repair.get("component_count") or 0)
    missing = repair.get("missingGlyphChars") or repair.get("missing_glyph_chars") or []
    tiny_holes = 0
    for contour in welded_contours:
        bbox_candidate = _contour_bbox(contour)
        if not bbox_candidate:
            continue
        contour_w = max(0.0, bbox_candidate[2] - bbox_candidate[0])
        contour_h = max(0.0, bbox_candidate[3] - bbox_candidate[1])
        contour_area = _contour_area_mm2(contour)
        if contour_area < 0.18 and min(contour_w, contour_h) < 0.55:
            tiny_holes += 1
    internal_garbage = bool(
        len(welded_contours) > max(6, int(len(raw_contours) * 2.15))
        or tiny_holes > 5
        or area_ratio > 0.82
        or long_thin_artifacts > 0
    )
    # This is a conservative manufacturability proxy: the bridge itself may be
    # 0.20-0.35 mm, while the offset/welded stroke around it provides the actual
    # neck mass that should stay above the laser-safe threshold.
    min_neck_width = round(max(float(selected_bridge_mm or 0), float(selected_offset_mm or 0) * 2.8), 3)
    bridge_width_ok = 0.20 <= float(selected_bridge_mm or 0) <= 0.35
    glyph_identity_passed = bool(glyph_validation.get("glyphIdentityPassed", True))
    mark_ownership_passed = bool(glyph_validation.get("markOwnershipPassed", True))
    glyph_gate_passed = glyph_identity_passed and mark_ownership_passed
    turkish_tail_breve_bonus = 7 if any(ch in TURKISH_TAIL_MARK_CHARS or ch in TURKISH_BREVE_MARK_CHARS for ch in text) and glyph_gate_passed else 0
    clean_glyph_flow_bonus = 3 if glyph_gate_passed and component_count == 1 and not internal_garbage and not missing else 0
    natural_connection_score = _clamp_score(
        98
        - abs(selected_offset_mm - 0.35) * 35
        - max(0.0, selected_bridge_mm - 0.45) * 80
        - (20 if internal_garbage else 0)
        - (18 if component_count != 1 else 0)
    )
    manual_reference_similarity = _clamp_score(
        96
        - abs(area_ratio - 0.50) * 90
        - abs(selected_offset_mm - 0.35) * 28
        - (22 if internal_garbage else 0)
        - (22 if component_count != 1 else 0)
        - (18 if missing else 0)
        + turkish_tail_breve_bonus
        + clean_glyph_flow_bonus
    )
    manufacturable_passed = (
        component_count == 1
        and not missing
        and glyph_gate_passed
        and not internal_garbage
        and min_neck_width >= 0.8
        and bridge_width_ok
        and tiny_holes <= 5
        and int(ai_score.get("aiQualityScore") or 0) >= AI_LASER_QUALITY_PASS_SCORE
    )
    if manufacturable_passed and manual_reference_similarity >= 80 and natural_connection_score >= 80:
        designer_status = "designer_weld_passed"
    elif not glyph_identity_passed:
        designer_status = "glyph_identity_failed"
    elif not mark_ownership_passed:
        designer_status = str(glyph_validation.get("glyphOwnershipStatus") or "invalid_mark_ownership")
    elif internal_garbage:
        designer_status = "internal_garbage_path"
    elif manual_reference_similarity < 74:
        designer_status = "visual_far_from_manual_reference"
    elif component_count != 1 or missing:
        designer_status = "designer_weld_failed"
    else:
        designer_status = "designer_weld_warning"
    if manufacturable_passed:
        manufacturability = "manufacturable_passed"
    elif internal_garbage or component_count != 1 or missing or not glyph_gate_passed:
        manufacturability = "manufacturable_failed"
    else:
        manufacturability = "manufacturable_warning"
    return {
        "designerWeldStatus": designer_status,
        "designer_weld_status": designer_status,
        "manufacturabilityStatus": manufacturability,
        "manufacturability_status": manufacturability,
        "manualReferenceSimilarityScore": manual_reference_similarity,
        "manual_reference_similarity_score": manual_reference_similarity,
        "naturalConnectionScore": natural_connection_score,
        "natural_connection_score": natural_connection_score,
        "internalGarbagePath": internal_garbage,
        "internal_garbage_path": internal_garbage,
        "tinyHoleCount": tiny_holes,
        "tiny_hole_count": tiny_holes,
        "longThinArtifactCount": long_thin_artifacts,
        "long_thin_artifact_count": long_thin_artifacts,
        "minNeckWidthMm": min_neck_width,
        "min_neck_width_mm": min_neck_width,
        "filledSilhouetteScore": _clamp_score(100 - abs(area_ratio - 0.50) * 70),
        "filled_silhouette_score": _clamp_score(100 - abs(area_ratio - 0.50) * 70),
        "designerReadyForCut": bool(manufacturable_passed and designer_status == "designer_weld_passed"),
        "designer_ready_for_cut": bool(manufacturable_passed and designer_status == "designer_weld_passed"),
        "riskOverlayFlags": [
            *([] if not internal_garbage else ["internal_garbage_path"]),
            *([] if not long_thin_artifacts else ["long_thin_internal_artifact"]),
            *([] if min_neck_width >= 0.8 else ["narrow_neck"]),
            *([] if bridge_width_ok else ["bridge_width_out_of_designer_range"]),
            *([] if glyph_gate_passed else [str(glyph_validation.get("glyphOwnershipStatus") or "glyph_gate_failed")]),
            *([] if tiny_holes <= 5 else ["tiny_hole"]),
            *([] if component_count == 1 else ["detached_component"]),
            *([] if manual_reference_similarity >= 80 else ["visual_far_from_manual_reference"]),
            *([] if selected_bridge_mm <= 0.60 else ["bridge_too_thick"]),
        ],
        "risk_overlay_flags": [
            *([] if not internal_garbage else ["internal_garbage_path"]),
            *([] if not long_thin_artifacts else ["long_thin_internal_artifact"]),
            *([] if min_neck_width >= 0.8 else ["narrow_neck"]),
            *([] if bridge_width_ok else ["bridge_width_out_of_designer_range"]),
            *([] if glyph_gate_passed else [str(glyph_validation.get("glyphOwnershipStatus") or "glyph_gate_failed")]),
            *([] if tiny_holes <= 5 else ["tiny_hole"]),
            *([] if component_count == 1 else ["detached_component"]),
            *([] if manual_reference_similarity >= 80 else ["visual_far_from_manual_reference"]),
            *([] if selected_bridge_mm <= 0.60 else ["bridge_too_thick"]),
        ],
    }


def _auto_repair_name_cut_item(item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    # Master gate (Leyla, 2026-05-28): legacy generative name-cut algorithms
    # (targeted_weld, smart_bridge, AI laser quality scoring, designer_mark_
    # bridge, letter_flow_bridge, initial_letter_connection, ai_designer,
    # support_line auto-decoration) are DISABLED by default after the 6-month
    # generative approach was retired in favor of the hand-prepared DXF library.
    # Code is preserved (not deleted) so the flag can be flipped back on per
    # item or globally without redeploy. When OFF, this function returns an
    # empty-geometry repair dict; the caller (`build_name_cut_production_scene`)
    # picks up the DXF library override via `_corel_exact_reference_override_for_item`
    # and uses the hand-drawn DXF directly. If neither library entry nor toggle
    # is active, the item ends up with readyForCut=False and the UI surfaces
    # `dxf_library_missing_design` so the operator knows Leyla must draw the name.
    legacy_enabled = _truthy_setting(
        item.get("use_legacy_name_cut_algorithms", cfg.get("use_legacy_name_cut_algorithms")),
        False,
    )
    if not legacy_enabled:
        return {
            "contours": [],
            "raw_contours": [],
            "offset_contours": [],
            "bridge_contours": [],
            "welded_contours": [],
            "componentCount": 0,
            "component_count": 0,
            "componentCountAfterRepair": 0,
            "component_count_after_repair": 0,
            "componentCountBeforeRepair": 0,
            "component_count_before_repair": 0,
            "detachedPartCount": 0,
            "detached_part_count": 0,
            "unresolvedPartCount": 0,
            "unresolved_part_count": 0,
            "hasDetachedDots": False,
            "has_detached_dots": False,
            "hasDisconnectedLetters": False,
            "has_disconnected_letters": False,
            "autoRepaired": False,
            "auto_repaired": False,
            "appliedWeld": False,
            "applied_weld": False,
            "appliedSmartBridge": False,
            "applied_smart_bridge": False,
            "repairStatus": "legacy_algorithms_disabled",
            "repair_status": "legacy_algorithms_disabled",
            "repairMessages": [
                "legacy_name_cut_algorithms_disabled_default",
                "dxf_library_is_primary_source",
            ],
            "repair_messages": [
                "legacy_name_cut_algorithms_disabled_default",
                "dxf_library_is_primary_source",
            ],
        }
    style = item.get("style") or item.get("font_family") or cfg.get("font_family") or ""
    offset_mm = max(0.0, min(5.0, float(item.get("offset_mm") or cfg.get("offset_mm") or 0)))
    raw_contours = _outline_contours_for_item(item, cfg, path_role="preview")
    brannboll_mode = "brannboll" in _normalize_token(style)
    mochary_corel_mode = _is_mochary_user_corel_calibrated_style(style)
    designer_cut_mode = brannboll_mode or mochary_corel_mode
    ai_quality_enabled = _ai_quality_enabled_for_item(item, cfg, style)
    ai_candidates: list[dict[str, Any]] = []
    selected_ai_candidate: dict[str, Any] | None = None
    ai_candidate_passed = False
    if brannboll_mode and ai_quality_enabled and raw_contours:
        candidate_index = 1
        for candidate_offset in AI_LASER_QUALITY_OFFSET_CANDIDATES:
            for candidate_bridge in AI_LASER_QUALITY_BRIDGE_CANDIDATES:
                ai_candidates.append(
                    _build_ai_laser_quality_candidate(
                        item,
                        cfg,
                        raw_contours,
                        candidate_offset,
                        candidate_bridge,
                        candidate_index,
                    )
                )
                candidate_index += 1
        selected_ai_candidate, ai_candidate_passed = _select_ai_laser_quality_candidate(ai_candidates)

    if selected_ai_candidate:
        offset_mm = float(selected_ai_candidate.get("offsetMm") or offset_mm)
        offset_contours = selected_ai_candidate.get("offset_contours") or []
        bridge_result = selected_ai_candidate.get("bridge_result") or {}
        contours = selected_ai_candidate.get("welded_contours") or []
    else:
        offset_contours = _outline_contours_for_item(item, cfg, path_role="cut")
        bridge_width_mm = _safe_optional_float(item.get("smart_bridge_width_mm") or cfg.get("smart_bridge_width_mm"))
        bridge_enabled = _truthy_setting(
            item.get("smart_bridge_enabled", cfg.get("smart_bridge_enabled")),
            False,
        )
        text_for_designer_bridge = str(item.get("preview_text") or item.get("name_text") or item.get("text") or item.get("name") or "")
        if mochary_corel_mode and any(ch in TURKISH_DIACRITIC_CHARS for ch in text_for_designer_bridge):
            designer_bridge_width = bridge_width_mm or 0.22
            # --- Initial letter connection reinforcement (M→ü, S→ü, Ç→a etc.) ---
            # Bowtie-fix (2026-05-27): DEFAULT OFF. Empirical evidence (bowtie_fix
            # probe + counter_work) proved this bridge does NOT weld the pieces
            # (real union count unchanged) and its overlapping mixed-winding
            # geometry creates the bowtie/checkerboard artefact at the junction.
            # Bridges-OFF renders Mücahit/Sümeyye/Çağrı cleanly. Re-enable via flag
            # (set disable_initial_letter_connection=False) if a real gap-spanning
            # connector is implemented later. (Prior "F8 breaks connectivity" note
            # was based on the fake bbox counter; true connectivity was never 1.)
            disable_initial = _truthy_setting(
                item.get("disable_initial_letter_connection",
                         cfg.get("disable_initial_letter_connection")),
                True,
            )
            if disable_initial:
                initial_conn = {"bridge_contours": [], "details": [], "warnings": ["initial_letter_connection_off_by_default_bowtie_fix"]}
            else:
                initial_conn = _initial_letter_connection_reinforcement_contours(
                    text_for_designer_bridge,
                    offset_contours,
                    bridge_width_mm=max(0.26, min(0.32, float(designer_bridge_width or 0.28) + 0.06)),
                )
            initial_conn_contours = list(initial_conn.get("bridge_contours") or [])
            reinforced_contours = [*offset_contours, *initial_conn_contours]
            mark_bridge = _designer_mark_bridge_contours_for_text(
                text_for_designer_bridge,
                reinforced_contours,
                designer_bridge_width,
            )
            bridged_contours = [*reinforced_contours, *mark_bridge.get("bridge_contours", [])]
            welded_contours = _union_contours_for_cutting(bridged_contours) if bridged_contours else []
            # Bowtie-fix (2026-05-27): DEFAULT OFF (same reasoning as initial
            # connection above). Letter-flow bridges also fail to weld (pieces
            # don't physically overlap) and contribute to the junction artefact.
            # Re-enable via disable_designer_letter_flow_bridge=False.
            disable_letter_flow = _truthy_setting(
                item.get("disable_designer_letter_flow_bridge",
                         cfg.get("disable_designer_letter_flow_bridge")),
                True,
            )
            if disable_letter_flow:
                letter_bridge = {"contours": welded_contours, "bridge_contours": [], "smart_bridge_warnings": ["letter_flow_bridge_off_by_default_bowtie_fix"]}
            else:
                letter_bridge = _designer_letter_flow_bridge_same_name_contours(
                    welded_contours,
                    bridge_width_mm=max(0.24, min(0.30, float(designer_bridge_width or 0.25))),
                )
            welded_contours = letter_bridge.get("contours") or welded_contours
            before_components = _analysis_bbox_from_groups(offset_contours, _contour_groups_by_bbox(offset_contours, 0.12))
            after_components = _analysis_bbox_from_groups(welded_contours, _contour_groups_by_bbox(welded_contours, 0.12))
            mark_bridge_contours = list(mark_bridge.get("bridge_contours", []) or [])
            letter_bridge_contours = list(letter_bridge.get("bridge_contours", []) or [])
            bridge_warnings = list(dict.fromkeys([
                *(initial_conn.get("warnings") or []),
                *(mark_bridge.get("bridge_warnings", []) or []),
                *(letter_bridge.get("smart_bridge_warnings", []) or []),
            ]))
            bridge_result = {
                "contours": welded_contours,
                "bridge_contours": [*initial_conn_contours, *mark_bridge_contours, *letter_bridge_contours],
                "component_count_before": len(before_components),
                "bridged_part_count": len(initial_conn_contours) + len(mark_bridge_contours) + len(letter_bridge_contours),
                "unresolved_part_count": max(0, len(after_components) - 1),
                "smart_bridge_warnings": bridge_warnings,
                "designer_mark_bridge_details": mark_bridge.get("bridge_details", []),
                "designerMarkBridgeDetails": mark_bridge.get("bridge_details", []),
                "designer_mark_bridge_warnings": mark_bridge.get("bridge_warnings", []),
                "designerMarkBridgeWarnings": mark_bridge.get("bridge_warnings", []),
                "designer_letter_bridge_contours": letter_bridge_contours,
                "initial_letter_connection_details": initial_conn.get("details", []),
                "initialLetterConnectionDetails": initial_conn.get("details", []),
                "global_smart_bridge_disabled": True,
            }
        else:
            bridge_result = _smart_bridge_same_name_contours(offset_contours, offset_mm, enabled=bridge_enabled, bridge_width_mm=bridge_width_mm)
        contours = bridge_result["contours"]
    # Targeted stroke-weld (Karar A, 2026-05-27): bar-free single piece. Connect
    # near-but-not-touching letter/mark pieces with short thin CCW connectors at
    # their nearest stroke points (natural flow), NOT the old diagonal bridge.
    # Default ON for designer mode; opt-out via disable_targeted_stroke_weld.
    targeted_weld_applied = False
    if designer_cut_mode and contours and not _truthy_setting(
        item.get("disable_targeted_stroke_weld", cfg.get("disable_targeted_stroke_weld")), False
    ):
        before_weld = _real_component_count_via_union(contours)
        if before_weld > 1:
            # 2026-05-28: thicker connector (1.2mm vs 0.6mm) closes the visible seam
            # at letter junctions so the welded outer looks like Corel's natural merge
            # (Leyla's reference) rather than a thin neck. Tunable per-item via
            # `targeted_weld_connector_width_mm`. Diagnostic in mochary_shaping_debug/.
            _weld_w = float(_safe_optional_float(
                item.get("targeted_weld_connector_width_mm")
                or cfg.get("targeted_weld_connector_width_mm")
            ) or 1.2)
            contours = _targeted_stroke_weld_contours(contours, connector_width_mm=_weld_w)
            targeted_weld_applied = _real_component_count_via_union(contours) == 1
    # Support-line weld (opt-in, 2026-05-27): when the operator enables support_line,
    # weld a baseline connector bar so the name becomes ONE cuttable piece. This
    # upgrades the legacy support_line (which only drew a separate decorative line
    # and never connected the pieces). Default OFF → clean separate pieces.
    support_weld_applied = False
    if _truthy_setting(item.get("support_line", cfg.get("support_line")), False) and contours:
        contours, support_weld_applied = _welded_baseline_support_contours(contours)
    analysis_item = {**item, "offset_mm": offset_mm}
    repair = _name_cut_auto_repair_analysis(analysis_item, cfg, contours)
    component_count_before = int(bridge_result.get("component_count_before") or repair.get("componentCount") or 0)
    component_count_after = int(repair.get("componentCount") or 0)
    bridged_part_count = int(bridge_result.get("bridged_part_count") or 0)
    # Faz4-fix: unresolved parts must reflect the FINAL (post support-line weld)
    # real geometry, not the pre-weld bbox estimate. component_count_after already
    # uses the real union counter on the final contours.
    unresolved_part_count = max(0, component_count_after - 1)
    bridge_warnings = list(bridge_result.get("smart_bridge_warnings") or [])
    final_geometry_connectivity = _final_geometry_connectivity_analysis(
        str(item.get("preview_text") or item.get("name_text") or item.get("text") or item.get("name") or ""),
        contours,
        bridge_result.get("bridge_contours") or [],
        bridge_result.get("designerMarkBridgeDetails") or bridge_result.get("designer_mark_bridge_details") or [],
        bridge_warnings,
    ) if designer_cut_mode else {}
    bridge_error_prefixes = {
        "detached_dot",
        "detached_breve",
        "detached_cedilla",
        "bridge_not_unioned_into_final_path",
        "bridge_too_long",
        "bridge_crosses_other_glyph",
        "bridge_attached_to_wrong_glyph",
        "bridge_visual_line_artifact",
        "mark_blob_risk",
        "mark_not_connected_to_owner_body",
    }
    _info_bridge_warnings = {
        "initial_letter_connection_off_by_default_bowtie_fix",
        "letter_flow_bridge_off_by_default_bowtie_fix",
    }
    bridge_warnings = [
        w for w in dict.fromkeys([*bridge_warnings, *(final_geometry_connectivity.get("finalGeometryConnectivityErrors") or [])])
        if str(w) not in _info_bridge_warnings
    ]
    # Faz4-fix: when the name is ONE real connected component, any "detached" /
    # "not-unioned" mark warning is a provable false positive (v15 fuses Turkish
    # marks into the body). Drop them as blockers; component_count is authoritative.
    if component_count_after == 1:
        _false_when_connected = {
            "detached_dot", "detached_breve", "detached_cedilla",
            "bridge_not_unioned_into_final_path", "mark_not_connected_to_owner_body",
        }
        bridge_warnings = [w for w in bridge_warnings if str(w).split(":", 1)[0] not in _false_when_connected]
    mark_bridge_validation_errors = [
        str(warning)
        for warning in bridge_warnings
        if str(warning).split(":", 1)[0] in bridge_error_prefixes
    ]
    repair_messages = list(repair.get("repairMessages") or repair.get("repair_messages") or [])
    if bridged_part_count:
        repair_messages.append("smart_bridge_applied")
    if pyclipper is not None and offset_mm > 0:
        repair_messages.append("welded_cut_path_ready")
    if selected_ai_candidate:
        repair_messages.append("ai_quality_candidates_scored")
        if ai_candidate_passed:
            repair_messages.append("ai_quality_selected")
        else:
            repair_messages.append("ai_quality_failed")
    repair_messages = list(dict.fromkeys(repair_messages))
    ready_for_cut = bool(contours) and component_count_after == 1 and unresolved_part_count == 0 and not repair.get("missingGlyphChars")
    if mark_bridge_validation_errors:
        ready_for_cut = False
    if selected_ai_candidate and not ai_candidate_passed:
        ready_for_cut = False
    if not contours:
        repair_status = "failed"
    elif selected_ai_candidate and ai_candidate_passed and ready_for_cut:
        repair_status = "auto_repaired_ai_verified"
    elif selected_ai_candidate and not ai_candidate_passed:
        repair_status = "ai_quality_failed"
    elif ready_for_cut and (bridged_part_count or component_count_before > component_count_after or repair_messages):
        repair_status = "auto_repaired"
    elif ready_for_cut:
        repair_status = "clean"
    else:
        repair_status = "failed"
    repair_warnings = list(repair.get("repairWarnings") or repair.get("repair_warnings") or [])
    repair_warnings.extend(bridge_warnings)
    ai_score = selected_ai_candidate.get("score", {}) if selected_ai_candidate else {}
    ai_summaries = [candidate.get("summary", {}) for candidate in ai_candidates]
    ai_reason = str(ai_score.get("reason") or "")
    designer_plan: dict[str, Any] = {}
    designer_quality: dict[str, Any] = {}
    glyph_validation: dict[str, Any] = {}
    designer_ready = True
    if designer_cut_mode:
        selected_offset = round(float(selected_ai_candidate.get("offsetMm") or offset_mm), 3) if selected_ai_candidate else round(offset_mm, 3)
        selected_bridge = round(float(selected_ai_candidate.get("bridgeMm") or 0.25), 3) if selected_ai_candidate else round(float(_safe_optional_float(item.get("smart_bridge_width_mm") or cfg.get("smart_bridge_width_mm")) or 0.25), 3)
        if not ai_score:
            ai_score = _ai_laser_quality_score_candidate(
                item,
                raw_contours,
                offset_contours,
                bridge_result.get("bridge_contours") or [],
                contours,
                repair,
                selected_offset,
                selected_bridge,
            )
            ai_reason = str(ai_score.get("reason") or "")
        designer_plan = _designer_weld_plan_for_item(item, selected_offset, selected_bridge, ai_score, style)
        glyph_validation = _glyph_ownership_validator(
            str(item.get("preview_text") or item.get("name_text") or item.get("text") or item.get("name") or ""),
            designer_plan.get("glyphIdentity") or [],
            repair,
            designer_plan,
        )
        designer_quality = _designer_weld_quality_analysis(
            item,
            raw_contours,
            bridge_result.get("bridge_contours") or [],
            contours,
            repair,
            ai_score,
            selected_offset,
            selected_bridge,
            glyph_validation,
        )
        if mark_bridge_validation_errors or (final_geometry_connectivity and not final_geometry_connectivity.get("finalGeometryConnectivityPassed")):
            existing_flags = list(designer_quality.get("riskOverlayFlags") or [])
            existing_flags_snake = list(designer_quality.get("risk_overlay_flags") or existing_flags)
            merged_flags = list(dict.fromkeys([*existing_flags, *mark_bridge_validation_errors]))
            merged_flags_snake = list(dict.fromkeys([*existing_flags_snake, *mark_bridge_validation_errors]))
            status_reason = str(
                mark_bridge_validation_errors[0]
                if mark_bridge_validation_errors
                else final_geometry_connectivity.get("finalGeometryConnectivityStatus") or "geometry_connectivity_failed"
            )
            designer_quality.update(
                {
                    "designerWeldStatus": status_reason,
                    "designer_weld_status": status_reason,
                    "manufacturabilityStatus": "manufacturable_failed",
                    "manufacturability_status": "manufacturable_failed",
                    "designerReadyForCut": False,
                    "designer_ready_for_cut": False,
                    "riskOverlayFlags": merged_flags,
                    "risk_overlay_flags": merged_flags_snake,
                    "markBridgeValidationErrors": mark_bridge_validation_errors,
                    "mark_bridge_validation_errors": mark_bridge_validation_errors,
                }
            )
        designer_ready = bool(
            designer_quality.get("designerReadyForCut")
            and glyph_validation.get("glyphIdentityPassed")
            and glyph_validation.get("markOwnershipPassed")
        )
        if designer_quality.get("designerWeldStatus") == "designer_weld_passed" and ready_for_cut and designer_ready:
            repair_status = "designer_weld_passed"
        else:
            repair_status = str(mark_bridge_validation_errors[0] if mark_bridge_validation_errors else glyph_validation.get("glyphOwnershipStatus") if not designer_ready and not glyph_validation.get("markOwnershipPassed", True) else designer_quality.get("designerWeldStatus") or repair_status)
            ready_for_cut = False
        repair_messages.append("glyph_aware_designer_cut_engine_applied")
        if mochary_corel_mode:
            repair_messages.append("mochary_corel_production_profile_applied")
        if designer_ready:
            repair_messages.append("corel_style_candidate_quality_passed")
            repair_messages.append("manufacturable_passed")
        else:
            repair_messages.append(str(designer_quality.get("designerWeldStatus") or "designer_weld_warning"))
    if selected_ai_candidate and not ai_candidate_passed:
        repair_warnings.append("ai_quality_failed:" + ai_reason if ai_reason else "ai_quality_failed")
    repair_messages = list(dict.fromkeys(repair_messages))
    return {
        "contours": contours,
        "raw_contours": raw_contours,
        "offset_contours": offset_contours,
        "bridge_contours": bridge_result.get("bridge_contours") or [],
        "welded_contours": contours,
        "supportWeldApplied": support_weld_applied,
        "support_weld_applied": support_weld_applied,
        "targetedWeldApplied": targeted_weld_applied,
        "targeted_weld_applied": targeted_weld_applied,
        **repair,
        "componentCountBeforeRepair": component_count_before,
        "component_count_before_repair": component_count_before,
        "componentCountAfterRepair": component_count_after,
        "component_count_after_repair": component_count_after,
        "detachedPartCount": max(0, component_count_before - 1),
        "detached_part_count": max(0, component_count_before - 1),
        "bridgedPartCount": bridged_part_count,
        "bridged_part_count": bridged_part_count,
        "unresolvedPartCount": unresolved_part_count,
        "unresolved_part_count": unresolved_part_count,
        "appliedSmartBridge": bridged_part_count > 0,
        "applied_smart_bridge": bridged_part_count > 0,
        "appliedWeld": bool(pyclipper is not None and offset_mm > 0),
        "applied_weld": bool(pyclipper is not None and offset_mm > 0),
        "isConnectedPath": ready_for_cut,
        "is_connected_path": ready_for_cut,
        "readyForCut": ready_for_cut,
        "ready_for_cut": ready_for_cut,
        # Faz8-fix: anything not cleanly single-piece + manufacturable stays
        # operator-review-gated (componentCount>1 → readyForCut False → review True).
        "requiresOperatorReview": not bool(ready_for_cut),
        "requires_operator_review": not bool(ready_for_cut),
        "repairStatus": repair_status,
        "repair_status": repair_status,
        "repairMessages": repair_messages,
        "repair_messages": repair_messages,
        "repairWarnings": repair_warnings,
        "repair_warnings": repair_warnings,
        "designerMarkBridgeDetails": bridge_result.get("designerMarkBridgeDetails") or bridge_result.get("designer_mark_bridge_details") or [],
        "designer_mark_bridge_details": bridge_result.get("designer_mark_bridge_details") or bridge_result.get("designerMarkBridgeDetails") or [],
        "designerMarkBridgeWarnings": bridge_result.get("designerMarkBridgeWarnings") or bridge_result.get("designer_mark_bridge_warnings") or [],
        "designer_mark_bridge_warnings": bridge_result.get("designer_mark_bridge_warnings") or bridge_result.get("designerMarkBridgeWarnings") or [],
        "markBridgeValidationErrors": mark_bridge_validation_errors,
        "mark_bridge_validation_errors": mark_bridge_validation_errors,
        **final_geometry_connectivity,
        "globalSmartBridgeDisabledForDesignerMarks": bool(bridge_result.get("global_smart_bridge_disabled")),
        "global_smart_bridge_disabled_for_designer_marks": bool(bridge_result.get("global_smart_bridge_disabled")),
        "aiQualityEnabled": bool((ai_quality_enabled and brannboll_mode) or designer_cut_mode),
        "ai_quality_enabled": bool((ai_quality_enabled and brannboll_mode) or designer_cut_mode),
        "aiQualityCandidateCount": len(ai_candidates),
        "ai_quality_candidate_count": len(ai_candidates),
        "aiQualityCandidates": ai_summaries,
        "ai_quality_candidates": ai_summaries,
        "aiBestCandidateId": selected_ai_candidate.get("id") if selected_ai_candidate else "",
        "ai_best_candidate_id": selected_ai_candidate.get("id") if selected_ai_candidate else "",
        "selectedOffsetMm": round(float(selected_ai_candidate.get("offsetMm") or offset_mm), 3) if selected_ai_candidate else round(offset_mm, 3),
        "selected_offset_mm": round(float(selected_ai_candidate.get("offsetMm") or offset_mm), 3) if selected_ai_candidate else round(offset_mm, 3),
        "selectedBridgeMm": round(float(selected_ai_candidate.get("bridgeMm") or 0), 3) if selected_ai_candidate else round(_safe_optional_float(item.get("smart_bridge_width_mm") or cfg.get("smart_bridge_width_mm")) or (0.25 if designer_cut_mode else max(0.9, offset_mm * 1.35)), 3),
        "selected_bridge_mm": round(float(selected_ai_candidate.get("bridgeMm") or 0), 3) if selected_ai_candidate else round(_safe_optional_float(item.get("smart_bridge_width_mm") or cfg.get("smart_bridge_width_mm")) or (0.25 if designer_cut_mode else max(0.9, offset_mm * 1.35)), 3),
        "aiQualityScore": int(ai_score.get("aiQualityScore") or 0) if ai_score else None,
        "ai_quality_score": int(ai_score.get("aiQualityScore") or 0) if ai_score else None,
        "aiQualityStatus": str(ai_score.get("aiQualityStatus") or "") if ai_score else "",
        "ai_quality_status": str(ai_score.get("aiQualityStatus") or "") if ai_score else "",
        "aiQualityScores": ai_score if ai_score else {},
        "ai_quality_scores": ai_score if ai_score else {},
        "aiQualityReason": ai_reason,
        "ai_quality_reason": ai_reason,
        "aiQualityInspector": "deterministic_metric_inspector",
        "ai_quality_inspector": "deterministic_metric_inspector",
        "aiDirectPathGeneration": False,
        "ai_direct_path_generation": False,
        "designerWeldPlan": designer_plan,
        "designer_weld_plan": designer_plan,
        "appliedStyleProfile": (designer_plan.get("designerProfile") or {}).get("profile") if designer_plan else "",
        "applied_style_profile": (designer_plan.get("designerProfile") or {}).get("profile") if designer_plan else "",
        "appliedPairRules": (designer_plan.get("letterConnectionPlan") or designer_plan.get("connections") or []),
        "applied_pair_rules": (designer_plan.get("letterConnectionPlan") or designer_plan.get("connections") or []),
        "appliedMarkRules": (designer_plan.get("markBridgePlan") or designer_plan.get("marks") or []),
        "applied_mark_rules": (designer_plan.get("markBridgePlan") or designer_plan.get("marks") or []),
        "glyphOverrideUsed": False,
        "glyph_override_used": False,
        "glyphOverrideBlocked": bool(designer_cut_mode and (_golden_glyph_shape_library_payload().get("glyphOverrideDefaultEnabled") is not True)),
        "glyph_override_blocked": bool(designer_cut_mode and (_golden_glyph_shape_library_payload().get("glyphOverrideDefaultEnabled") is not True)),
        "connectionRulesApplied": (designer_plan.get("letterConnectionPlan") or designer_plan.get("connections") or []),
        "connection_rules_applied": (designer_plan.get("letterConnectionPlan") or designer_plan.get("connections") or []),
        "finalCutPathHash": "",
        "final_cut_path_hash": "",
        "reviewRequired": bool(designer_cut_mode),
        "review_required": bool(designer_cut_mode),
        **glyph_validation,
        **designer_quality,
    }


def _rotate_contours_for_cutting(contours: list[list[tuple[float, float]]], cx: float, cy: float, degrees: float) -> list[list[tuple[float, float]]]:
    radians = math.radians(degrees)
    cos_v = math.cos(radians)
    sin_v = math.sin(radians)
    rotated: list[list[tuple[float, float]]] = []
    for contour in contours:
        next_contour = []
        for x, y in contour:
            dx = x - cx
            dy = y - cy
            next_contour.append((round(cx + (dx * cos_v) - (dy * sin_v), 3), round(cy + (dx * sin_v) + (dy * cos_v), 3)))
        rotated.append(next_contour)
    return rotated


def _diacritic_bridge_status_for_text(text: object) -> str:
    value = str(text or "")
    if any(ch in TURKISH_DIACRITIC_CHARS for ch in value):
        return "AUTO_TURKISH_DIACRITIC_BRIDGES_ADDED_TO_CUT_OUTLINE"
    return "NO_TURKISH_DIACRITIC_BRIDGE_REQUIRED"


def _capital_connection_bridge_status_for_text(text: object, style: object = "") -> str:
    token = _normalize_token(style)
    if not ("ceyizhome" in token or "mochary" in token or "lab_script" in token):
        return "NO_SCRIPT_CAPITAL_BRIDGE_PROFILE"
    value = str(text or "")
    if re.search(r"[SLMCZ][a-zÃ§ÄŸÄ±Ã¶ÅŸÃ¼]", value):
        return "MANUAL_CAPITAL_BRIDGES_ADDED_INSIDE_NAME_ONLY"
    if re.search(r"[AFHX][a-zÃ§ÄŸÄ±Ã¶ÅŸÃ¼]", value):
        return "FONT_CONNECTED_CAPITAL_VARIANT_AVAILABLE_WHEN_SUPPORTED"
    return "NO_CAPITAL_BRIDGE_REQUIRED"


def _capital_connection_bridge_contours_for_cutting(text: str, origin_x: float, origin_y: float, draw_w: float, draw_h: float, mirror: bool = False, style: object = "") -> list[list[tuple[float, float]]]:
    token = _normalize_token(style)
    if not ("ceyizhome" in token or "mochary" in token or "lab_script" in token):
        return []
    lines = (text or "").splitlines() or [text or ""]
    line_count = max(1, len(lines))
    line_h = draw_h / line_count
    bridge_letters = {"S": 0.34, "L": 0.42, "M": 0.48, "C": 0.38, "Z": 0.36}
    contours: list[list[tuple[float, float]]] = []
    for line_index, line in enumerate(lines):
        if not line:
            continue
        chars = list(line)
        visible_count = max(1, len(chars))
        line_top = origin_y + (line_index * line_h)
        for index, char in enumerate(chars[:-1]):
            if char not in bridge_letters or not re.match(r"[a-zÃ§ÄŸÄ±Ã¶ÅŸÃ¼]", chars[index + 1]):
                continue
            segment_w = draw_w / visible_count
            center_ratio = (index + bridge_letters[char]) / visible_count
            cx = origin_x + (draw_w * center_ratio)
            if mirror:
                cx = origin_x + draw_w - (cx - origin_x)
            y = line_top + (line_h * 0.58)
            bridge_w = max(0.8, min(2.4, line_h * 0.07))
            bridge_len = max(2.0, min(7.0, segment_w * 0.18))
            left = cx - (bridge_len / 2)
            right = cx + (bridge_len / 2)
            top = y - (bridge_w / 2)
            bottom = y + (bridge_w / 2)
            contours.append([
                (round(left, 3), round(top, 3)),
                (round(right, 3), round(top, 3)),
                (round(right, 3), round(bottom, 3)),
                (round(left, 3), round(bottom, 3)),
                (round(left, 3), round(top, 3)),
            ])
    return contours


def _diacritic_bridge_contours_for_cutting(text: str, origin_x: float, origin_y: float, draw_w: float, draw_h: float, mirror: bool = False) -> list[list[tuple[float, float]]]:
    if not any(ch in TURKISH_DIACRITIC_CHARS for ch in text):
        return []
    lines = (text or "").splitlines() or [text or ""]
    line_count = max(1, len(lines))
    line_h = draw_h / line_count
    bridge_w = max(1.2, min(4.2, line_h * 0.075))
    upper_bridge_h = max(5.0, min(18.0, line_h * 0.48))
    lower_bridge_h = max(3.6, min(12.0, line_h * 0.34))
    contours: list[list[tuple[float, float]]] = []
    for line_index, line in enumerate(lines):
        if not line:
            continue
        visible_count = max(1, len(line))
        line_top = origin_y + (line_index * line_h)
        for char_index, char in enumerate(line):
            if char not in TURKISH_DIACRITIC_CHARS:
                continue
            center_ratio = (char_index + 0.5) / visible_count
            cx = origin_x + (draw_w * center_ratio)
            if mirror:
                cx = origin_x + draw_w - (cx - origin_x)
            if char in TURKISH_UPPER_MARK_CHARS:
                top = line_top + (line_h * 0.08)
                bottom = top + upper_bridge_h
            elif char in TURKISH_LOWER_MARK_CHARS:
                bottom = line_top + (line_h * 0.94)
                top = bottom - lower_bridge_h
            else:
                continue
            left = cx - (bridge_w / 2)
            right = cx + (bridge_w / 2)
            contours.append([
                (round(left, 3), round(top, 3)),
                (round(right, 3), round(top, 3)),
                (round(right, 3), round(bottom, 3)),
                (round(left, 3), round(bottom, 3)),
                (round(left, 3), round(top, 3)),
            ])
    return contours


def _offset_contours_for_cutting(contours: list[list[tuple[float, float]]], offset_mm: float, join_mode: str = "round") -> list[list[tuple[float, float]]]:
    if offset_mm <= 0:
        return contours
    if pyclipper is None:
        return [_expand_contour_for_cutting(contour, offset_mm) for contour in contours]
    scale = 1000
    paths: list[list[tuple[int, int]]] = []
    for contour in contours:
        if len(contour) < 3:
            continue
        path = [(int(round(x * scale)), int(round(y * scale))) for x, y in contour]
        cleaned = pyclipper.CleanPolygon(path, distance=max(1.0, 0.02 * scale))
        if len(cleaned) >= 3 and abs(pyclipper.Area(cleaned)) > 10:
            paths.append(cleaned)
    if not paths:
        return contours
    # NOTE: pyclipper.SimplifyPolygons(PFT_NONZERO) intentionally removed.
    # On fused-mark glyphs (Mochary v15: ü/ö/i dots fused into the body via thin necks,
    # wound opposite to the body), NONZERO simplification treats the dot sub-loops as
    # holes and DELETES the marks (proven via stage-isolation diagnostics). Offset
    # robustness for self-intersecting input is still ensured by the downstream
    # _union_contours_for_cutting(CT_UNION) that runs after offset. Regression-tested
    # zero pixel-change on backup-v4 and Brannböll (separate-contour fonts).
    join_type = pyclipper.JT_MITER if _normalize_token(join_mode) in {"miter", "miter_soft"} else pyclipper.JT_ROUND
    arc_tolerance = 0.06 * scale if join_type == pyclipper.JT_MITER else 0.25 * scale
    clipper_offset = pyclipper.PyclipperOffset(miter_limit=2.0, arc_tolerance=arc_tolerance)
    clipper_offset.AddPaths(paths, join_type, pyclipper.ET_CLOSEDPOLYGON)
    try:
        offset_paths = clipper_offset.Execute(offset_mm * scale)
    except Exception:
        return [_expand_contour_for_cutting(contour, offset_mm) for contour in contours]
    result: list[list[tuple[float, float]]] = []
    for path in offset_paths:
        if len(path) >= 3:
            result.append([(round(x / scale, 3), round(y / scale, 3)) for x, y in path])
    return result or contours


def _expand_contour_for_cutting(contour: list[tuple[float, float]], offset_mm: float) -> list[tuple[float, float]]:
    if offset_mm <= 0 or len(contour) < 3:
        return contour
    center_x = sum(point[0] for point in contour) / len(contour)
    center_y = sum(point[1] for point in contour) / len(contour)
    expanded: list[tuple[float, float]] = []
    # This is a conservative contour expansion, not a mathematically exact path offset.
    # The manifest keeps this as a P1 RDWorks-check risk until a true offset engine is added.
    for x, y in contour:
        dx = x - center_x
        dy = y - center_y
        length = math.hypot(dx, dy)
        if length <= 0.0001:
            expanded.append((round(x, 3), round(y, 3)))
            continue
        expanded.append((round(x + ((dx / length) * offset_mm), 3), round(y + ((dy / length) * offset_mm), 3)))
    return expanded


def _svg_path_from_contours(contours: list[list[tuple[float, float]]]) -> str:
    pieces: list[str] = []
    for contour in contours:
        if len(contour) < 2:
            continue
        first = contour[0]
        pieces.append(f"M {first[0]:.3f} {first[1]:.3f}")
        for x, y in contour[1:]:
            pieces.append(f"L {x:.3f} {y:.3f}")
        pieces.append("Z")
    return " ".join(pieces)


def _svg_curve_path_from_contours(contours: list[list[tuple[float, float]]], tension: float = 0.55) -> str:
    pieces: list[str] = []
    for contour in contours:
        if len(contour) < 2:
            continue
        points = contour[:-1] if contour[0] == contour[-1] else contour
        if len(points) < 4:
            first = points[0]
            pieces.append(f"M {first[0]:.3f} {first[1]:.3f}")
            for x, y in points[1:]:
                pieces.append(f"L {x:.3f} {y:.3f}")
            pieces.append("Z")
            continue
        pieces.append(f"M {points[0][0]:.3f} {points[0][1]:.3f}")
        count = len(points)
        for index in range(count):
            previous_point = points[(index - 1) % count]
            current_point = points[index]
            next_point = points[(index + 1) % count]
            after_next_point = points[(index + 2) % count]
            c1x = current_point[0] + ((next_point[0] - previous_point[0]) * tension / 6.0)
            c1y = current_point[1] + ((next_point[1] - previous_point[1]) * tension / 6.0)
            c2x = next_point[0] - ((after_next_point[0] - current_point[0]) * tension / 6.0)
            c2y = next_point[1] - ((after_next_point[1] - current_point[1]) * tension / 6.0)
            pieces.append(f"C {c1x:.3f} {c1y:.3f} {c2x:.3f} {c2y:.3f} {next_point[0]:.3f} {next_point[1]:.3f}")
        pieces.append("Z")
    return " ".join(pieces)


def _final_svg_path_from_contours(contours: list[list[tuple[float, float]]], item: dict[str, Any], cfg: dict[str, Any]) -> tuple[str, str]:
    style = item.get("style") or item.get("font_family") or cfg.get("font_family") or ""
    style_token = _normalize_token(style)
    curve_fit_enabled = _truthy_setting(
        item.get("corel_style_curve_fit", cfg.get("corel_style_curve_fit")),
        "brannboll" in style_token or _is_mochary_user_corel_calibrated_style(style),
    )
    if curve_fit_enabled and contours:
        return _svg_curve_path_from_contours(contours), "corel_curve_fit_final_cut_path"
    return _svg_path_from_contours(contours), "polygon_final_cut_path"


def _svg_path_data_to_contours(path_data: str, curve_steps: int = 10) -> list[list[tuple[float, float]]]:
    tokens = re.findall(r"[MLCZ]|-?\d+(?:\.\d+)?", path_data or "")
    contours: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    command = ""
    index = 0
    current_point: tuple[float, float] | None = None

    def cubic_point(p0: tuple[float, float], c1: tuple[float, float], c2: tuple[float, float], p3: tuple[float, float], t: float) -> tuple[float, float]:
        mt = 1.0 - t
        x = (mt ** 3 * p0[0]) + (3 * mt * mt * t * c1[0]) + (3 * mt * t * t * c2[0]) + (t ** 3 * p3[0])
        y = (mt ** 3 * p0[1]) + (3 * mt * mt * t * c1[1]) + (3 * mt * t * t * c2[1]) + (t ** 3 * p3[1])
        return round(x, 3), round(y, 3)

    while index < len(tokens):
        token = tokens[index]
        if token in {"M", "L", "C", "Z"}:
            command = token
            index += 1
            if command == "Z":
                if current:
                    contours.append(current)
                    current = []
                    current_point = None
            continue
        if command == "M" and index + 1 < len(tokens):
            if current:
                contours.append(current)
            current_point = (float(tokens[index]), float(tokens[index + 1]))
            current = [current_point]
            command = "L"
            index += 2
        elif command == "L" and index + 1 < len(tokens):
            current_point = (float(tokens[index]), float(tokens[index + 1]))
            current.append(current_point)
            index += 2
        elif command == "C" and index + 5 < len(tokens) and current_point is not None:
            c1 = (float(tokens[index]), float(tokens[index + 1]))
            c2 = (float(tokens[index + 2]), float(tokens[index + 3]))
            end = (float(tokens[index + 4]), float(tokens[index + 5]))
            for step in range(1, max(2, curve_steps) + 1):
                current.append(cubic_point(current_point, c1, c2, end, step / max(2, curve_steps)))
            current_point = end
            index += 6
        else:
            index += 1
    if current:
        contours.append(current)
    return contours


def _translate_contours(contours: list[list[tuple[float, float]]], dx: float = 0.0, dy: float = 0.0) -> list[list[tuple[float, float]]]:
    if abs(dx) <= 0.0001 and abs(dy) <= 0.0001:
        return contours
    return [[(round(x + dx, 3), round(y + dy, 3)) for x, y in contour] for contour in contours]


def _read_combined_rows(excel_path: Path) -> list[dict[str, Any]]:
    try:
        dataframe = pd.read_excel(excel_path, dtype=object, engine="openpyxl")
    except Exception:
        return []
    mapped_columns = {column: HEADER_ALIASES.get(_normalize_token(column), _normalize_token(column)) for column in dataframe.columns}
    dataframe = dataframe.rename(columns=mapped_columns)
    return dataframe.to_dict(orient="records")


def _production_order_from_row(row_number: int, row: dict[str, Any], model_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    customer = _cell(row.get("customer_name") or row.get("name_cut_text") or row.get("label_text"))
    label_model_no = _cell(row.get("label_model_no") or row.get("model_no") or row.get("etiket_no"))
    raw_label_required = row.get("label_required")
    has_label_required_flag = _cell(raw_label_required) != ""
    label_required = _truthy(raw_label_required) if has_label_required_flag else bool(label_model_no)
    name_cut_required = _truthy(row.get("name_cut_required"))
    quantity = max(1, _safe_int(row.get("quantity"), 1))
    name_cut_text = format_name_for_cutting(row.get("name_cut_text") or customer)
    composition_mode = _cell(row.get("composition_mode") or "Tek SatÄ±r Yan Yana")
    width_raw = row.get("name_cut_width_mm")
    height_raw = row.get("name_cut_height_mm")
    max_width_raw = row.get("name_cut_max_width_mm")
    max_height_raw = row.get("name_cut_max_height_mm")
    name_cut_width, name_cut_height = resolve_name_cut_dimensions(
        name_cut_text,
        _safe_optional_float(width_raw),
        _safe_optional_float(height_raw),
        _safe_optional_float(max_width_raw),
        _safe_optional_float(max_height_raw),
        composition_mode,
    )
    thickening_mode = _cell(row.get("thickening_mode") or "Orta")
    offset_mm = resolve_offset_mm(thickening_mode, row.get("offset_mm"))
    model = _match_model(label_model_no, model_index)
    errors: list[str] = []
    warnings: list[str] = []
    if label_required and not model:
        errors.append("Etiket modeli bulunamadÄ±.")
    if name_cut_required and not name_cut_text:
        errors.append("Ä°sim kesim metni boÅŸ.")
    if not label_required and not name_cut_required:
        warnings.append("Bu sat\u0131rda \u00fcretim se\u00e7ilmedi.")
    return {
        "row_number": row_number,
        "customer_name": customer,
        "date_text": _cell(row.get("date_text")),
        "note_text": _cell(row.get("note_text")),
        "quantity": str(quantity),
        "label_required": label_required,
        "label_model_no": label_model_no,
        "label_model_key": label_model_no,
        "label_model_name": str(model.get("title") or model.get("model_name") or "") if model else "",
        "label_status": "READY" if label_required and model else "ERROR" if label_required else "SKIPPED",
        "name_cut_required": name_cut_required,
        "name_cut_text": name_cut_text,
        "name_cut_quantity": str(max(1, _safe_int(row.get("name_cut_quantity"), 1 if name_cut_required else 0))),
        "name_cut_width_mm": str(name_cut_width),
        "name_cut_height_mm": str(name_cut_height),
        "composition_mode": composition_mode,
        "name_cut_style": _cell(row.get("name_cut_style") or row.get("name_cut_font") or "Mochary Personal Use Only"),
        "thickening_mode": thickening_mode,
        "offset_mm": str(offset_mm),
        "support_line": _truthy(row.get("support_line")),
        "back_plate": _truthy(row.get("back_plate")),
        "name_cut_status": "READY" if name_cut_required and name_cut_text else "SKIPPED",
        "errors": errors,
        "warnings": warnings,
    }


def _name_cut_item_from_order(order: dict[str, Any]) -> dict[str, Any]:
    risks = _name_cut_risks(order["name_cut_text"], order["name_cut_style"], order.get("support_line"), order.get("back_plate"), order.get("composition_mode"))
    status = "WARNING" if risks else "READY"
    return {
        "item_id": f"name-row-{order['row_number']}",
        "row_number": str(order["row_number"]),
        "name_text": order["name_cut_text"],
        "raw_customer_name": order["customer_name"],
        "quantity": order["name_cut_quantity"],
        "width_mm": float(order["name_cut_width_mm"]),
        "height_mm": float(order["name_cut_height_mm"]),
        "style": order["name_cut_style"],
        "composition": order.get("composition_mode") or "Tek SatÄ±r Yan Yana",
        "composition_mode": order.get("composition_mode") or "Tek SatÄ±r Yan Yana",
        "thickening_mode": order.get("thickening_mode") or "Orta",
        "offset_mm": float(order.get("offset_mm") or 0.8),
        "support_line": bool(order.get("support_line")),
        "back_plate": bool(order.get("back_plate")),
        "status": status,
        "warnings": risks,
        "errors": [],
        "is_deleted": False,
        "is_edited": False,
        "preview_text": _composition_preview(order["name_cut_text"], order.get("composition_mode") or "Tek SatÄ±r Yan Yana"),
    }


def _name_cut_risks(text: str, style: str, support_line: bool, back_plate: bool, composition: object = "") -> list[str]:
    warnings: list[str] = []
    if re.search(r"[iÄ°Ä±ÅŸÅŸÃ§Ã‡Ã¶Ã–Ã¼ÃœÄŸÄ]", text):
        warnings.append("TÃ¼rkÃ§e karakter/nokta riski var; alt destek veya taban plaka Ã¶nerilir.")
    if "ince" in _normalize_token(style):
        warnings.append("Font Ã§ok ince olabilir; pleksi kesimde baÄŸlantÄ± kontrol edilmeli.")
    if len(text.split()) >= 2 and not support_line and not _is_joined_name_mode(composition):
        warnings.append("Ä°ki isim ayrÄ± parÃ§a olabilir; alt destek Ã¶nerilir.")
    if warnings and not (support_line or back_plate):
        warnings.append("RDWorks'te font/path kontrolÃ¼ manuel yapÄ±lmalÄ±.")
    return warnings


def _composition_preview(text: str, composition: str) -> str:
    words = text.split()
    normalized = _normalize_token(composition)
    if "alt" in normalized and len(words) > 1:
        return "\n".join(words)
    if "buyuk" in normalized or "bÃ¼yÃ¼k" in normalized:
        if len(words) > 1:
            return f"{words[0]}\n{' '.join(words[1:])}"
    return "   ".join(words)


def _svg_text_lines(value: str) -> list[str]:
    lines = [line.strip() for line in str(value or "").splitlines() if line.strip()]
    if not lines and str(value or "").strip():
        lines = [str(value).strip()]
    return lines[:4]


def _build_model_lookup(label_models: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for model in label_models:
        keys = {
            model.get("id"),
            model.get("key"),
            model.get("name"),
            model.get("title"),
            model.get("display_name"),
            model.get("code"),
            model.get("number"),
            model.get("model_no"),
            Path(str(model.get("path") or "")).stem,
        }
        for key in keys:
            normalized = _normalize_model_key(key)
            if normalized:
                lookup[normalized] = model
    return lookup


def _match_model(value: object, lookup: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    key = _normalize_model_key(value)
    if not key:
        return None
    if key in lookup:
        return lookup[key]
    for candidate, model in lookup.items():
        if candidate.startswith(key) or key in candidate:
            return model
    return None


def _svg_document(layout: dict[str, Any], scene: dict[str, Any] | None = None) -> str:
    cfg = layout["config"]
    page_gap = 20
    pages = max(1, int(layout.get("summary", {}).get("pages", 1)))
    total_height = (float(cfg["height_mm"]) * pages) + (page_gap * (pages - 1))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{cfg["width_mm"]}mm" height="{total_height}mm" viewBox="0 0 {cfg["width_mm"]} {total_height}" data-export-layer="production-path-only" data-wysiwyg-cut-geometry="true">',
    ]
    for page in range(1, pages + 1):
        parts.append(f'<!-- Plate {page}: text labels intentionally omitted from RDWorks/path export. -->')
    if scene and scene.get("paths"):
        for path_item in scene.get("paths", []) or []:
            path_data = str(path_item.get("finalCutPathData") or path_item.get("final_cut_path_data") or path_item.get("weldedCutPathData") or path_item.get("welded_cut_path_data") or path_item.get("path_data") or "").strip()
            if not path_data:
                parts.append(f'<!-- Missing final cut path for {html.escape(str(path_item.get("text") or path_item.get("object_id") or ""))}; no fallback text is emitted. -->')
                continue
            page_y = (int(path_item.get("page", 1)) - 1) * (float(cfg["height_mm"]) + page_gap)
            x = float(path_item.get("x_mm") or 0)
            y = float(path_item.get("y_mm") or 0) + page_y
            width = float(path_item.get("width_mm") or path_item.get("actual_path_width_mm") or 0)
            height = float(path_item.get("height_mm") or path_item.get("actual_path_height_mm") or 0)
            offset = max(0.0, float(path_item.get("offset_mm") or cfg.get("offset_mm") or 0))
            if path_item.get("back_plate"):
                parts.append(f'<g id="CUT_BACK_PLATE"><rect x="{x - offset}" y="{y - offset}" rx="5" ry="5" width="{width + (offset * 2)}" height="{height + (offset * 2)}" fill="none" stroke="#7c3aed" stroke-width="0.5"/></g>')
            if path_item.get("support_line"):
                parts.append(f'<g id="CUT_SUPPORT_LINE"><line x1="{x + 4}" y1="{y + height - 8}" x2="{x + width - 4}" y2="{y + height - 8}" stroke="#2563eb" stroke-width="1.1"/></g>')
            transform = f' transform="translate(0 {page_y:.3f})"' if page_y else ""
            parts.append(
                f'<g id="CUT_NAME_OUTLINE" data-outline="fonttools-path" data-cut-geometry="final-cut-path" data-object-id="{html.escape(str(path_item.get("object_id") or ""))}" '
                f'data-placement-id="{html.escape(str(path_item.get("placement_id") or ""))}" data-ready-for-cut="{str(bool(path_item.get("ready_for_cut"))).lower()}" '
                f'data-canvas-export-same="{str(bool(path_item.get("canvasExportConsistencyPassed") or path_item.get("canvas_export_consistency_passed"))).lower()}" '
                f'data-thickening="{html.escape(str(path_item.get("thickening_mode") or "Orta"))}" data-offset-mm="{offset:g}"{transform}>'
                f'<path d="{html.escape(path_data, quote=True)}" fill="none" stroke="#020617" stroke-width="0.15" stroke-linejoin="round" stroke-linecap="round"/>'
                f'</g>'
            )
        parts.append("</svg>")
        return "\n".join(parts)
    for item in layout["items"]:
        page_y = (int(item.get("page", 1)) - 1) * (float(cfg["height_mm"]) + page_gap)
        x = float(item["x_mm"])
        y = float(item["y_mm"]) + page_y
        width = float(item["width_mm"])
        height = float(item["height_mm"])
        text = html.escape(str(item.get("name_text") or item.get("preview_text") or item.get("text") or item.get("name") or ""))
        offset = max(0.25, float(item.get("offset_mm") or cfg.get("offset_mm") or 0.65))
        name_stroke_width = 0.15 if pyclipper is not None and offset > 0 else max(0.35, min(0.65, offset))
        if cfg.get("mirror_cut"):
            x = float(cfg["width_mm"]) - x - width
        if item.get("back_plate"):
            parts.append(f'<g id="CUT_BACK_PLATE"><rect x="{x - offset}" y="{y - offset}" rx="5" ry="5" width="{width + (offset * 2)}" height="{height + (offset * 2)}" fill="none" stroke="#7c3aed" stroke-width="0.5"/></g>')
        if item.get("support_line"):
            parts.append(f'<g id="CUT_SUPPORT_LINE"><line x1="{x + 4}" y1="{y + height - 8}" x2="{x + width - 4}" y2="{y + height - 8}" stroke="#2563eb" stroke-width="1.1"/></g>')
        contours = _translate_contours(_outline_contours_for_item(item, cfg), dy=page_y)
        path_data = _svg_path_from_contours(contours)
        if path_data:
            parts.append(
                f'<g id="CUT_NAME_OUTLINE" data-outline="fonttools-path" data-thickening="{html.escape(str(item.get("thickening_mode") or "Orta"))}" data-offset-mm="{offset}">'
                f'<path d="{path_data}" fill="none" stroke="#020617" stroke-width="{name_stroke_width}" stroke-linejoin="round" stroke-linecap="round"/>'
                f'</g>'
            )
        else:
            parts.append(f'<!-- Missing final cut path for {text}; fallback text intentionally omitted. -->')
    parts.append("</svg>")
    return "\n".join(parts)


def _dxf_document(layout: dict[str, Any], scene: dict[str, Any] | None = None) -> str:
    cfg = layout["config"]
    page_gap = 20.0

    def color(layer: str) -> str:
        return str(RDWORKS_CUT_LAYERS[layer]["dxf_color"])

    def layer_entry(layer: str) -> list[str]:
        return [
            "0", "LAYER",
            "2", layer,
            "70", "0",
            "62", color(layer),
            "6", "CONTINUOUS",
        ]

    def add_line(layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        lines.extend([
            "0", "LINE", "8", layer, "62", color(layer),
            "10", f"{x1:.3f}", "20", f"{y1:.3f}",
            "11", f"{x2:.3f}", "21", f"{y2:.3f}",
        ])

    def add_polyline(layer: str, points: list[tuple[float, float]]) -> None:
        if len(points) < 2:
            return
        lines.extend(["0", "POLYLINE", "8", layer, "62", color(layer), "66", "1", "70", "1"])
        for px, py in points:
            lines.extend(["0", "VERTEX", "8", layer, "10", f"{px:.3f}", "20", f"{py:.3f}", "30", "0.000"])
        lines.extend(["0", "SEQEND"])

    lines = [
        "0", "SECTION", "2", "TABLES",
        "0", "TABLE", "2", "LAYER", "70", str(len(RDWORKS_CUT_LAYERS)),
    ]
    for layer_name in RDWORKS_CUT_LAYERS:
        lines.extend(layer_entry(layer_name))
    lines.extend(["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"])

    if scene and scene.get("paths"):
        for path_item in scene.get("paths", []) or []:
            page_y = (int(path_item.get("page", 1)) - 1) * (float(cfg["height_mm"]) + page_gap)
            x = float(path_item.get("x_mm") or 0)
            y = float(path_item.get("y_mm") or 0) + page_y
            width = float(path_item.get("width_mm") or path_item.get("actual_path_width_mm") or 0)
            height = float(path_item.get("height_mm") or path_item.get("actual_path_height_mm") or 0)
            offset = float(path_item.get("offset_mm") or cfg.get("offset_mm") or 0)
            if path_item.get("back_plate"):
                add_polyline(
                    "CUT_BACK_PLATE",
                    [
                        (x - offset, y - offset),
                        (x + width + offset, y - offset),
                        (x + width + offset, y + height + offset),
                        (x - offset, y + height + offset),
                    ],
                )
            if path_item.get("support_line"):
                add_line("CUT_SUPPORT_LINE", x + 4, y + height - 8, x + width - 4, y + height - 8)
            path_data = str(path_item.get("finalCutPathData") or path_item.get("final_cut_path_data") or path_item.get("weldedCutPathData") or path_item.get("welded_cut_path_data") or path_item.get("path_data") or "").strip()
            lines.extend([
                "999", f"THICKENING {path_item.get('thickening_mode', 'Orta')} OFFSET_MM {offset:g}",
                "999", f"MIRROR_CUT {bool(cfg.get('mirror_cut'))}",
                "999", f"TEXT_TO_PATH OUTLINED_PATHS_WITH_FONTTOOLS; OFFSET_ENGINE {_offset_engine_status()}",
                "999", f"TEXT_TO_PATH FINAL_CUT_PATH; WYSIWYG_CANVAS_EXPORT {bool(path_item.get('canvasExportConsistencyPassed') or path_item.get('canvas_export_consistency_passed'))}",
                "999", f"OBJECT_ID {path_item.get('object_id', '')} PLACEMENT_ID {path_item.get('placement_id', '')}",
            ])
            for contour in _svg_path_data_to_contours(path_data):
                add_polyline("CUT_NAME_OUTLINE", [(px, py + page_y) for px, py in contour])
        lines.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(lines)

    for item in layout["items"]:
        page_y = (int(item.get("page", 1)) - 1) * (float(cfg["height_mm"]) + page_gap)
        x = float(item["x_mm"])
        y = float(item["y_mm"]) + page_y
        width = float(item["width_mm"])
        height = float(item["height_mm"])
        offset = float(item.get("offset_mm") or 0)
        if cfg.get("mirror_cut"):
            x = float(cfg["width_mm"]) - x - width
        lines.extend([
            "999", f"THICKENING {item.get('thickening_mode', 'Orta')} OFFSET_MM {offset}",
            "999", f"MIRROR_CUT {bool(cfg.get('mirror_cut'))}",
            "999", f"TEXT_TO_PATH OUTLINED_PATHS_WITH_FONTTOOLS; OFFSET_ENGINE {_offset_engine_status()}",
        ])
        contours = _outline_contours_for_item(item, cfg)
        if contours:
            for contour in contours:
                add_polyline("CUT_NAME_OUTLINE", [(px, py + page_y) for px, py in contour])
        else:
            lines.extend(["999", "PATH_MISSING; fallback TEXT intentionally omitted from laser export"])
        if item.get("support_line"):
            add_line("CUT_SUPPORT_LINE", x + 4, y + height - 8, x + width - 4, y + height - 8)
        if item.get("back_plate"):
            px = x - offset
            py = y - offset
            pw = width + (offset * 2)
            ph = height + (offset * 2)
            for x1, y1, x2, y2 in [
                (px, py, px + pw, py),
                (px + pw, py, px + pw, py + ph),
                (px + pw, py + ph, px, py + ph),
                (px, py + ph, px, py),
            ]:
                add_line("CUT_BACK_PLATE", x1, y1, x2, y2)
    lines.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(lines)


def _write_preview_images(layout: dict[str, Any], png_path: Path, pdf_path: Path, scene: dict[str, Any] | None = None) -> None:
    cfg = layout["config"]
    width_px = max(400, int(float(cfg["width_mm"])))
    height_px = max(260, int(float(cfg["height_mm"])))
    canvas = bytearray([255, 255, 255] * width_px * height_px)

    def set_pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width_px and 0 <= y < height_px:
            offset = (y * width_px + x) * 3
            canvas[offset:offset + 3] = bytes(color)

    def line_h(x1: int, x2: int, y: int, color: tuple[int, int, int]) -> None:
        for x in range(max(0, x1), min(width_px, x2 + 1)):
            set_pixel(x, y, color)

    def line_v(x: int, y1: int, y2: int, color: tuple[int, int, int]) -> None:
        for y in range(max(0, y1), min(height_px, y2 + 1)):
            set_pixel(x, y, color)

    def rect(x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        line_h(x, x + w, y, color)
        line_h(x, x + w, y + h, color)
        line_v(x, y, y + h, color)
        line_v(x + w, y, y + h, color)

    rect(0, 0, width_px - 1, height_px - 1, (180, 180, 180))
    pdf_ops = ["0.75 w", "0.6 0.6 0.6 RG", f"0 0 {float(cfg['width_mm'])} {float(cfg['height_mm'])} re S"]
    preview_paths = scene.get("paths", []) if isinstance(scene, dict) else []
    if preview_paths:
        pdf_ops.append("0.01 0.02 0.09 RG")
        for path_item in preview_paths:
            if int(path_item.get("page", 1)) != 1:
                continue
            path_data = str(path_item.get("finalCutPathData") or path_item.get("final_cut_path_data") or path_item.get("weldedCutPathData") or path_item.get("welded_cut_path_data") or path_item.get("path_data") or "")
            for contour in _svg_path_data_to_contours(path_data):
                if len(contour) < 2:
                    continue
                scaled_points = [
                    (
                        int(x / float(cfg["width_mm"]) * width_px),
                        int(y / float(cfg["height_mm"]) * height_px),
                    )
                    for x, y in contour
                ]
                for left, right in zip(scaled_points, scaled_points[1:] + [scaled_points[0]]):
                    x1, y1 = left
                    x2, y2 = right
                    steps = max(abs(x2 - x1), abs(y2 - y1), 1)
                    for step in range(steps + 1):
                        t = step / steps
                        set_pixel(int(round(x1 + (x2 - x1) * t)), int(round(y1 + (y2 - y1) * t)), (2, 6, 23))
                first = contour[0]
                pdf_ops.append(f"{first[0]:.2f} {float(cfg['height_mm']) - first[1]:.2f} m")
                for x, y in contour[1:]:
                    pdf_ops.append(f"{x:.2f} {float(cfg['height_mm']) - y:.2f} l")
                pdf_ops.append("h S")
    else:
        for item in layout["items"]:
            if int(item.get("page", 1)) != 1:
                continue
            x = int(float(item["x_mm"]) / float(cfg["width_mm"]) * width_px)
            y = int(float(item["y_mm"]) / float(cfg["height_mm"]) * height_px)
            w = int(float(item["width_mm"]) / float(cfg["width_mm"]) * width_px)
            h = int(float(item["height_mm"]) / float(cfg["height_mm"]) * height_px)
            rect(x, y, max(4, w), max(4, h), (239, 68, 68))
            px_x = float(item["x_mm"])
            px_y = float(cfg["height_mm"]) - float(item["y_mm"]) - float(item["height_mm"])
            pdf_ops.append("1 0 0 RG")
            pdf_ops.append(f"{px_x:.2f} {px_y:.2f} {float(item['width_mm']):.2f} {float(item['height_mm']):.2f} re S")

    raw_rows = []
    for y in range(height_px):
        start = y * width_px * 3
        raw_rows.append(b"\x00" + bytes(canvas[start:start + width_px * 3]))
    compressed = zlib.compress(b"".join(raw_rows), 9)

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)

    png_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width_px, height_px, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", compressed)
        + png_chunk(b"IEND", b"")
    )
    _write_simple_pdf(pdf_path, float(cfg["width_mm"]), float(cfg["height_mm"]), "\n".join(pdf_ops))


def _write_simple_pdf(path: Path, width: float, height: float, stream: str) -> None:
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width:.2f} {height:.2f}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream",
    ]
    body = ["%PDF-1.4\n"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part.encode("latin-1", errors="replace")) for part in body))
        body.append(f"{index} 0 obj\n{obj}\nendobj\n")
    xref_pos = sum(len(part.encode("latin-1", errors="replace")) for part in body)
    body.append(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.append(f"{offset:010d} 00000 n \n")
    body.append(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n")
    path.write_bytes("".join(body).encode("latin-1", errors="replace"))


def _empty_state(message: str) -> dict[str, Any]:
    return {
        "status": "NO_EXCEL",
        "message": message,
        "summary": {"total_rows": 0, "label_jobs": 0, "name_cut_jobs": 0, "both_jobs": 0, "no_production": 0, "total_quantity": 0, "name_cut_quantity": 0},
        "orders": [],
        "label_items": [],
        "name_cut_items": [],
        "layout": layout_name_cut_items([]),
        "presets": NAME_CUT_PRESETS,
    }


def _truthy(value: object) -> bool:
    token = _normalize_token(value)
    if token in TRUE_VALUES:
        return True
    if token in FALSE_VALUES:
        return False
    return bool(token)


def _normalize_token(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.strip().lower()
    for source, target in (
        ("Ä±", "i"), ("Ä°", "i"), ("ÅŸ", "s"), ("Å", "s"),
        ("ÄŸ", "g"), ("Ä", "g"), ("Ã¼", "u"), ("Ãœ", "u"),
        ("Ã¶", "o"), ("Ã–", "o"), ("Ã§", "c"), ("Ã‡", "c"),
        ("ı", "i"), ("İ", "i"), ("ş", "s"), ("Ş", "s"),
        ("ğ", "g"), ("Ğ", "g"), ("ü", "u"), ("Ü", "u"),
        ("ö", "o"), ("Ö", "o"), ("ç", "c"), ("Ç", "c"),
    ):
        text = text.replace(source, target)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _normalize_model_key(value: object) -> str:
    token = _normalize_token(value)
    if token.isdigit():
        return token.zfill(2)
    return token


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


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return default


def _safe_float(value: object, default: float) -> float:
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def _safe_optional_float(value: object) -> float | None:
    if _cell(value) == "":
        return None
    try:
        number = float(str(value).replace(",", "."))
        if math.isnan(number):
            return None
        return number
    except Exception:
        return None


def _relative(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path)
