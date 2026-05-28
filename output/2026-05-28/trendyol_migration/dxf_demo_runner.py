"""DXF lookup end-to-end demo — captures all 7 steps into dxf_demo_steps.json."""

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from webui_backend import dxf_library_api as dxf
from webui_backend.combined_production_api import build_name_cut_production_scene


DEMO_TARGET = PROJECT_ROOT / "assets" / "dxf_library" / "80x40" / "mucahit.dxf"
SRC = PROJECT_ROOT / "assets" / "dxf_library" / "70x40" / "umit.dxf"


def find_object(scene, name):
    return next((o for o in scene["objects"] if name in (o.get("text", "") or "")), None)


def find_path(scene, name):
    return next((p for p in scene["paths"] if name in (p.get("text", "") or "")), None)


def main():
    steps = []
    # Ensure clean start
    if DEMO_TARGET.exists():
        DEMO_TARGET.unlink()

    # STEP 1
    r1 = dxf.resolve_name_for_order(PROJECT_ROOT, "Mücahit")
    steps.append({"step": 1, "label": "pre-check: Mücahit kütüphanede yok", "result": r1["status"]})

    # STEP 2
    scene_before = build_name_cut_production_scene(
        items=[{"name_text": "Mücahit", "style": "mochary-corel", "width_mm": 80, "height_mm": 40, "x_mm": 0, "y_mm": 0}],
        config={},
    )
    obj_b = find_object(scene_before, "Mücahit")
    path_b = find_path(scene_before, "Mücahit")
    steps.append({
        "step": 2,
        "label": "scene before: missing-design + readyForCut=False",
        "object.repair_status": obj_b.get("repair_status"),
        "path.ready_for_cut": path_b.get("ready_for_cut"),
        "path.repair_status": path_b.get("repair_status"),
    })

    # STEP 3
    shutil.copy(SRC, DEMO_TARGET)
    steps.append({"step": 3, "label": "operator dosya yükledi", "file_size": DEMO_TARGET.stat().st_size})

    # STEP 4
    sr = dxf.scan_library(PROJECT_ROOT)
    steps.append({"step": 4, "label": "manuel scan", "scanned": sr["scanned"], "added": sr["added"], "updated": sr["updated"]})

    # STEP 5
    r5 = dxf.resolve_name_for_order(PROJECT_ROOT, "Mücahit")
    entry = r5.get("entry") or {}
    steps.append({
        "step": 5,
        "label": "post-scan: Mücahit bulundu",
        "result": r5["status"],
        "size_group": entry.get("size_group"),
        "bbox_mm": entry.get("bbox_mm"),
    })

    # STEP 6
    scene_after = build_name_cut_production_scene(
        items=[{"name_text": "Mücahit", "style": "mochary-corel", "width_mm": 80, "height_mm": 40, "x_mm": 0, "y_mm": 0}],
        config={},
    )
    obj_a = find_object(scene_after, "Mücahit")
    path_a = find_path(scene_after, "Mücahit")
    ref_path = obj_a.get("corel_reference_path", "") or obj_a.get("corelReferencePath", "") or ""
    ref_tail = ref_path.replace("\\", "/").split("/")[-3:]
    steps.append({
        "step": 6,
        "label": "scene after: corel_reference_exact_override + readyForCut=True",
        "object.repair_status": obj_a.get("repair_status"),
        "object.override_applied": obj_a.get("corel_reference_override_applied"),
        "path.ready_for_cut": path_a.get("ready_for_cut"),
        "pathData_length": len(str(obj_a.get("corel_reference_override_path_data") or "")),
        "reference_path_tail": ref_tail,
    })

    # STEP 7 cleanup
    DEMO_TARGET.unlink()
    fr = dxf.scan_library(PROJECT_ROOT)
    r_f = dxf.resolve_name_for_order(PROJECT_ROOT, "Mücahit")
    steps.append({"step": 7, "label": "cleanup", "scan_after": fr["scanned"], "final_status": r_f["status"]})

    out = PROJECT_ROOT / "output" / "2026-05-28" / "trendyol_migration" / "dxf_demo_steps.json"
    out.write_text(json.dumps(steps, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Saved: {out}")
    for s in steps:
        print(f"  Step {s['step']}: {s['label']}")


if __name__ == "__main__":
    main()
