from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from webui_backend import combined_production_api  # noqa: E402


OUT_DIR = ROOT / "output" / date.today().isoformat() / "production_name_cut_production_scene"
REPORT_PATH = OUT_DIR / "PRODUCTION_NAME_CUT_PRODUCTION_SCENE_RAPORU.md"
JSON_PATH = OUT_DIR / "production_name_cut_production_scene_gate_result.json"


BASE_CONFIG = {
    "width_mm": 800,
    "height_mm": 600,
    "target_name_width_mm": 80,
    "target_name_height_mm": 40,
    "target_gap_mm": 1,
    "item_gap_mm": 1,
    "row_gap_mm": 1,
    "margin_mm": 15,
    "dense_nesting": True,
    "allow_rotation": True,
    "offset_mm": 0.3,
    "font_family": "Ceyizhome Lab Script (Mochary)",
}


def item(item_id: str, text: str, composition: str = "auto_split_and_nest", quantity: str = "1") -> dict:
    return {
        "item_id": item_id,
        "id": item_id,
        "name_text": text,
        "text": text,
        "quantity": quantity,
        "compositionMode": composition,
        "composition_mode": composition,
        "lineBreakMode": "single_line",
        "offset_mm": 0.3,
        "style": "Ceyizhome Lab Script (Mochary)",
    }


def assert_check(checks: list[dict], name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "status": "PASSED" if ok else "FAILED", "detail": detail})


def min_gap_ok(placements: list[dict], gap: float = 1.0) -> bool:
    for index, first in enumerate(placements):
        for second in placements[index + 1 :]:
            if int(first.get("page") or 1) != int(second.get("page") or 1):
                continue
            separated = (
                float(first["x_mm"]) + float(first["width_mm"]) + gap <= float(second["x_mm"]) + 0.02
                or float(second["x_mm"]) + float(second["width_mm"]) + gap <= float(first["x_mm"]) + 0.02
                or float(first["y_mm"]) + float(first["height_mm"]) + gap <= float(second["y_mm"]) + 0.02
                or float(second["y_mm"]) + float(second["height_mm"]) + gap <= float(first["y_mm"]) + 0.02
            )
            if not separated:
                return False
    return True


def run() -> dict:
    checks: list[dict] = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    multi = item("multi-1", "Sedef Sefer Vahip Ayşe Mehmet Leyla Mücahit Serap")
    scene = combined_production_api.build_name_cut_production_scene([multi], BASE_CONFIG)
    placements = scene.get("placements") or []
    paths = scene.get("paths") or []
    assert_check(checks, "auto_split_scene_creates_separate_objects", len(placements) >= 8, f"placements={len(placements)}")
    assert_check(checks, "all_placements_have_unique_ids", len({p.get("placement_id") for p in placements}) == len(placements), "")
    assert_check(checks, "scene_paths_are_fonttools_paths", len([p for p in paths if p.get("path_data")]) >= 8, f"paths={len(paths)} fallback={scene.get('fallback_count')}")
    assert_check(checks, "multiname_gap_collision_safe", min_gap_ok(placements, 1.0), "")
    assert_check(checks, "no_auto_device_start_in_scene", not scene.get("safety", {}).get("rdworks_auto_start") and not scene.get("safety", {}).get("laser_auto_start") and not scene.get("safety", {}).get("printer_auto_start"), json.dumps(scene.get("safety", {}), ensure_ascii=False))

    couple_scene = combined_production_api.build_name_cut_production_scene([item("couple-1", "Ayşe & Mehmet", "single_line_text")], BASE_CONFIG)
    assert_check(checks, "couple_single_line_stays_one_object", len(couple_scene.get("placements") or []) == 1, f"placements={len(couple_scene.get('placements') or [])}")

    names = ["Sedef", "Sefer", "Hasan", "Hüseyin", "Leyla", "Ayşe", "Veli", "Mücahit", "Serap", "Songül"]
    many_items = [item(f"n-{idx}", names[idx % len(names)], "single_line_text") for idx in range(60)]
    dense_scene = combined_production_api.build_name_cut_production_scene(many_items, BASE_CONFIG)
    dense_placements = dense_scene.get("placements") or []
    rows = {round(float(p.get("y_mm") or 0), 1) for p in dense_placements if int(p.get("page") or 1) == 1}
    assert_check(checks, "dense_scene_fills_multiple_rows", len(rows) >= 4, f"rows={len(rows)} placements={len(dense_placements)}")
    assert_check(checks, "dense_scene_collision_safe", min_gap_ok(dense_placements, 1.0), "")

    app_js = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    start = app_js.find("function renderLaserLayoutPreview")
    end = app_js.find("function toggleNameCutInspector", start)
    render_segment = app_js[start:end]
    assert_check(checks, "frontend_uses_backend_scene_bridge", "build_name_cut_production_scene" in app_js and "requestNameCutProductionScene" in render_segment, "")
    assert_check(checks, "production_render_has_no_fallback_text_element", "<text " not in render_segment and "fallbackTransforms" not in render_segment, "")
    assert_check(checks, "selection_targets_placement_id", "selectedNameCutPlacementId" in app_js and "data-namecut-placement-id" in render_segment, "")

    svg_sample = OUT_DIR / "scene_sample.svg"
    svg_paths = "\n".join(
        f'<path d="{p.get("path_data", "")}" fill="none" stroke="#020617" stroke-width="0.15"/>'
        for p in paths
        if p.get("path_data")
    )
    svg_sample.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">\n{svg_paths}\n</svg>', encoding="utf-8")
    sample_text = svg_sample.read_text(encoding="utf-8")
    assert_check(checks, "sample_svg_contains_only_paths", "<text" not in sample_text and "safe" not in sample_text.lower() and "selection" not in sample_text.lower(), str(svg_sample))

    failed = [check for check in checks if check["status"] != "PASSED"]
    result = {
        "status": "PASSED" if not failed else "FAILED",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "total_checks": len(checks),
        "passed_checks": len(checks) - len(failed),
        "failed_checks": failed,
        "scene_metrics": scene.get("metrics", {}),
        "dense_metrics": dense_scene.get("metrics", {}),
        "sample_svg": str(svg_sample),
        "safety": {
            "rdworks_auto_start": False,
            "laser_auto_start": False,
            "printer_auto_start": False,
        },
        "checks": checks,
    }
    JSON_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(
        "# Production Name Cut Production Scene Gate\n\n"
        "## Sorun\n"
        "Modal/frontend/backend arasında farklı geometri üretilmesi isimleri tek grup, fallback text veya yanlış selection frame olarak gösteriyordu.\n\n"
        "## Düzeltme\n"
        "Backend `build_name_cut_production_scene` tek üretim sahnesi üretir; frontend production layer yalnız bu sahnedeki FontTools pathlerini çizer.\n\n"
        "## Sonuç\n"
        f"- Gate: {result['status']}\n"
        f"- Passed: {result['passed_checks']} / {result['total_checks']}\n"
        f"- Sample SVG: `{svg_sample}`\n"
        "- RDWorks/lazer/yazıcı otomatik başlatılmadı.\n\n"
        "## Kontroller\n"
        + "\n".join(f"- {c['status']}: {c['name']} {c.get('detail') or ''}" for c in checks)
        + "\n",
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
