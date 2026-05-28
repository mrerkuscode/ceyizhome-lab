from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from webui_backend import combined_production_api  # noqa: E402


OUT_DIR = ROOT / "output" / date.today().isoformat() / "production_name_cut_scene_scale"
REPORT_PATH = OUT_DIR / "PRODUCTION_NAME_CUT_SCENE_SCALE_RAPORU.md"
JSON_PATH = OUT_DIR / "production_name_cut_scene_scale_gate_result.json"

CONFIG = {
    "width_mm": 800,
    "height_mm": 600,
    "target_name_width_mm": 80,
    "target_name_height_mm": 40,
    "target_gap_mm": 1.5,
    "item_gap_mm": 1.5,
    "row_gap_mm": 1.5,
    "margin_mm": 15,
    "dense_nesting": True,
    "allow_rotation": True,
    "offset_mm": 0.3,
    "font_family": "Ceyizhome Lab Script (Mochary)",
}


def make_item(item_id: str, text: str, mode: str = "single_line_text", quantity: str = "1") -> dict:
    return {
        "item_id": item_id,
        "id": item_id,
        "name_text": text,
        "text": text,
        "quantity": quantity,
        "compositionMode": mode,
        "composition_mode": mode,
        "lineBreakMode": "single_line",
        "offset_mm": 0.3,
        "style": "Ceyizhome Lab Script (Mochary)",
        "status": "READY",
    }


def check(results: list[dict], name: str, ok: bool, detail: str = "") -> None:
    results.append({"name": name, "status": "PASSED" if ok else "FAILED", "detail": detail})


def scene_for(name: str, text: str, mode: str = "single_line_text") -> dict:
    return combined_production_api.build_name_cut_production_scene([make_item(name, text, mode)], CONFIG)


def write_scene_svg(scene: dict, filename: str) -> str:
    path = OUT_DIR / filename
    groups = []
    for path_item in scene.get("paths") or []:
        if not path_item.get("path_data"):
            continue
        groups.append(
            '<g data-object-id="{object_id}" data-placement-id="{placement_id}" '
            'data-actual-path-width-mm="{w}" data-actual-path-height-mm="{h}">'
            '<path d="{d}" fill="none" stroke="#020617" stroke-width="0.15" '
            'stroke-linejoin="round" stroke-linecap="round"/></g>'.format(
                object_id=path_item.get("object_id", ""),
                placement_id=path_item.get("placement_id", ""),
                w=path_item.get("actual_path_width_mm", ""),
                h=path_item.get("actual_path_height_mm", ""),
                d=path_item.get("path_data", ""),
            )
        )
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="800mm" height="600mm" viewBox="0 0 800 600">\n'
        + "\n".join(groups)
        + "\n</svg>",
        encoding="utf-8",
    )
    return str(path)


def placement_heights(scene: dict) -> list[float]:
    return [float(p.get("actual_path_height_mm") or 0) for p in scene.get("placements") or []]


def run() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []
    outputs: dict[str, str] = {}

    cases = {
        "scene-scale-single-ayse.svg": scene_for("ayse", "Ayşe"),
        "scene-scale-can.svg": scene_for("can", "Can"),
        "scene-scale-abdurrahman.svg": scene_for("abdurrahman", "Abdurrahman"),
        "scene-scale-multiname.svg": scene_for("multi", "Sedef Sefer Vahip Ayşe Mehmet Leyla Mücahit Serap", "auto_split_and_nest"),
        "scene-scale-burak-ceren-serkan.svg": scene_for("three", "Burak Ceren Serkan", "auto_split_and_nest"),
    }
    for filename, scene in cases.items():
        outputs[filename] = write_scene_svg(scene, filename)

    all_placements = [p for scene in cases.values() for p in scene.get("placements", [])]
    ready_placements = [p for p in all_placements if p.get("path_preview_status") == "OUTLINED_PATHS_WITH_FONTTOOLS"]
    heights = [float(p.get("actual_path_height_mm") or 0) for p in ready_placements]
    widths = [float(p.get("actual_path_width_mm") or 0) for p in ready_placements]
    check(checks, "actual_path_height_uses_target_40mm", bool(heights) and min(heights) >= 18 and max(heights) <= 42, f"heights={heights}")
    check(checks, "actual_path_width_does_not_exceed_target_too_much", bool(widths) and max(widths) <= 90, f"widths={widths}")
    check(checks, "can_is_not_tiny", min(placement_heights(cases["scene-scale-can.svg"]) or [0]) >= 18, str(cases["scene-scale-can.svg"].get("placements")))
    check(checks, "abdurrahman_readable_or_review", max(placement_heights(cases["scene-scale-abdurrahman.svg"]) or [0]) >= 18, str(cases["scene-scale-abdurrahman.svg"].get("placements")))
    multi_count = len(cases["scene-scale-multiname.svg"].get("placements") or [])
    check(checks, "multiname_has_separate_placements", multi_count >= 8, f"placements={multi_count}")
    three_count = len(cases["scene-scale-burak-ceren-serkan.svg"].get("placements") or [])
    check(checks, "three_names_split_to_three_objects", three_count == 3, f"placements={three_count}")
    check(checks, "usage_metric_available_from_actual_bbox", cases["scene-scale-multiname.svg"].get("metrics", {}).get("actual_path_used_area_percent", 0) > 0.5, json.dumps(cases["scene-scale-multiname.svg"].get("metrics", {}), ensure_ascii=False))
    for filename, output in outputs.items():
        svg = Path(output).read_text(encoding="utf-8")
        check(checks, f"{filename}_contains_paths_only", "<path" in svg and "<text" not in svg and "selection" not in svg.lower() and "safe" not in svg.lower(), output)

    app_js = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    check(checks, "frontend_does_not_use_text_length_squeeze", "textLength" not in app_js and "lengthAdjust" not in app_js, "")
    check(checks, "selection_uses_actual_bbox", "actual_path_width_mm" in app_js and "actualLeftMm" in app_js and "actualTopMm" in app_js, "")
    safety = cases["scene-scale-multiname.svg"].get("safety", {})
    check(checks, "no_machine_auto_start", not safety.get("rdworks_auto_start") and not safety.get("laser_auto_start") and not safety.get("printer_auto_start"), json.dumps(safety, ensure_ascii=False))

    failed = [item for item in checks if item["status"] != "PASSED"]
    result = {
        "status": "PASSED" if not failed else "FAILED",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "passed_checks": len(checks) - len(failed),
        "total_checks": len(checks),
        "failed_checks": failed,
        "outputs": outputs,
        "metrics": {name: scene.get("metrics", {}) for name, scene in cases.items()},
        "checks": checks,
    }
    JSON_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(
        "# Production Name Cut Scene Scale Raporu\n\n"
        "## Önceki scene gate neyi çözmüştü?\n"
        "Tek backend production scene, ayrı placement id ve production-layer path render hattı kuruldu.\n\n"
        "## Bu fazdaki sorun\n"
        "Frontend kaynaklı actual bbox değerleri backend FontTools ölçeğini ezebiliyor, isimler hedef 80 x 40 mm yerine küçük görünüyordu.\n\n"
        "## Düzeltme\n"
        "Backend actual path ölçüsü FontTools raw bbox ve 80 x 40 hedef ölçeğinden hesaplanır; frontend actual değerleri yalnız mismatch uyarısıdır. Selection bbox actual path ölçüsünü takip eder.\n\n"
        f"## Gate sonucu\n- {result['status']}\n- Passed: {result['passed_checks']} / {result['total_checks']}\n\n"
        "## Çıktılar\n"
        + "\n".join(f"- `{path}`" for path in outputs.values())
        + "\n\n## Kontroller\n"
        + "\n".join(f"- {c['status']}: {c['name']} {c.get('detail') or ''}" for c in checks)
        + "\n\n## Kalan risk\nTam polygon nesting / boolean weld bu fazın kapsamı değildir; scene path bbox tabanlı gerçek ölçek kullanır.\n",
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    summary = run()
    print(json.dumps({
        "status": summary["status"],
        "passed": summary["passed_checks"],
        "total": summary["total_checks"],
        "report": str(REPORT_PATH),
        "json": str(JSON_PATH),
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0 if summary["status"] == "PASSED" else 1)
