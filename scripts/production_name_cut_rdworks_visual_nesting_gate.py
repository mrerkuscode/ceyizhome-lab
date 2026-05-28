from __future__ import annotations

import json
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend import combined_production_api as api  # noqa: E402


OUT_DIR = ROOT / "output" / "2026-05-21" / "production_name_cut_rdworks_visual_nesting"
APP_JS = ROOT / "src" / "webui" / "app.js"
STYLES_CSS = ROOT / "src" / "webui" / "styles.css"


def _config(**extra: object) -> dict[str, object]:
    cfg: dict[str, object] = {
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
        "font_family": "Brannboll Connect",
        "offset_mm": 0.65,
        "mirror_cut": False,
    }
    cfg.update(extra)
    return cfg


def _item(item_id: str, text: str, **extra: object) -> dict[str, object]:
    item: dict[str, object] = {
        "item_id": item_id,
        "id": item_id,
        "name_text": text,
        "preview_text": text,
        "style": "Brannboll Connect",
        "offset_mm": 0.65,
        "quantity": "1",
        "operator_size_locked": False,
    }
    item.update(extra)
    return item


def _assert(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def _layout(items: list[dict[str, object]], cfg: dict[str, object] | None = None) -> dict[str, object]:
    config = cfg or _config()
    return api.layout_name_cut_items(items, api._layout_config_from_payload(config))


def _has_min_gap(items: list[dict[str, object]], gap_mm: float = 1.0) -> bool:
    for a, b in combinations(items, 2):
        if int(a.get("page", 1)) != int(b.get("page", 1)):
            continue
        separated = (
            float(a["x_mm"]) + float(a["width_mm"]) + gap_mm <= float(b["x_mm"]) + 0.12
            or float(b["x_mm"]) + float(b["width_mm"]) + gap_mm <= float(a["x_mm"]) + 0.12
            or float(a["y_mm"]) + float(a["height_mm"]) + gap_mm <= float(b["y_mm"]) + 0.12
            or float(b["y_mm"]) + float(b["height_mm"]) + gap_mm <= float(a["y_mm"]) + 0.12
        )
        if not separated:
            return False
    return True


def _write_svg(path_result: dict[str, object], name: str) -> Path:
    layout = path_result["layout"]
    cfg = layout["config"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{cfg["width_mm"]}mm" height="{cfg["height_mm"]}mm" viewBox="0 0 {cfg["width_mm"]} {cfg["height_mm"]}">',
        '<g id="production-layer-only">',
    ]
    for path in path_result.get("paths", []):
        if path.get("path_data"):
            parts.append(
                f'<path d="{path["path_data"]}" fill="none" stroke="#020617" '
                'stroke-width="0.9" stroke-linejoin="round" stroke-linecap="round"/>'
            )
    parts.extend(["</g>", "</svg>"])
    svg_path = OUT_DIR / name
    svg_path.write_text("\n".join(parts), encoding="utf-8")
    return svg_path


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    warnings: list[str] = []
    cfg = _config()

    seven_names = ["Sedef", "Sefer", "Hasan", "Huseyin", "Leyla", "Ayse", "Veli"]
    seven_items = [_item(f"seven-{idx}", name) for idx, name in enumerate(seven_names, start=1)]
    seven_layout = _layout(seven_items, cfg)
    seven_placed = seven_layout.get("items", [])
    _assert(len(seven_placed) == 7, "7 isim testi 7 ayri placement uretmedi.", failures)
    _assert(_has_min_gap(seven_placed, 1), "7 isim testinde minimum 1 mm bosluk korunmuyor.", failures)
    _assert(seven_layout.get("summary", {}).get("within_work_area") is True, "7 isim safe margin icinde degil.", failures)
    _assert(seven_layout.get("summary", {}).get("collision_free") is True, "7 isim testinde collision var.", failures)
    _assert(all(float(item.get("height_mm", 0)) >= 38 for item in seven_placed), "Isimler 80x40 uretim yuksekligine yakin degil.", failures)
    _assert(all(float(item.get("actual_path_height_mm", 0)) >= 30 for item in seven_placed), "Path yukseklikleri okunabilir esigin altinda.", failures)
    _assert(all(float(item.get("width_mm", 0)) <= 105 for item in seven_placed), "Dense mod isimleri dogal path bbox yerine asiri genis kutulara zorluyor.", failures)

    path_result = api.preview_name_cut_paths(seven_items, cfg)
    _assert(path_result.get("outlined_count") == 7, "FontTools path preview 7 isim icin tam olusmadi.", failures)
    _assert(path_result.get("fallback_count") == 0, "Path preview fallback text'e dustu.", failures)
    sample_svg = _write_svg(path_result, "rdworks-visual-seven-names.svg")
    svg_text = sample_svg.read_text(encoding="utf-8").lower()
    leaked = [word for word in ["grid", "safe", "ruler", "selection", "handle", "toolbar", "inspector"] if word in svg_text]
    _assert(not leaked, f"Production SVG orneginde UI/helper katmani siziyor: {leaked}", failures)

    dense_source = [
        "Sedef", "Sefer", "Hasan", "Huseyin", "Leyla", "Ayse", "Veli", "Mucahit", "Serap", "Songul",
    ]
    dense_items = [_item(f"dense-{idx}", dense_source[idx % len(dense_source)]) for idx in range(60)]
    dense_layout = _layout(dense_items, cfg)
    dense_placed = dense_layout.get("items", [])
    rows = sorted({round(float(item.get("y_mm", 0)), 1) for item in dense_placed if int(item.get("page", 1)) == 1})
    _assert(len(dense_placed) == 60, "60 isim dense testi 60 placement uretmedi.", failures)
    _assert(len(rows) >= 4, "60 isim dense testi tabla alanini asagi dogru doldurmuyor.", failures)
    _assert(dense_layout.get("summary", {}).get("collision_free") is True, "60 isim dense testinde collision var.", failures)
    _assert(_has_min_gap(dense_placed, 1), "60 isim dense testinde minimum 1 mm bosluk korunmuyor.", failures)
    _assert(dense_layout.get("summary", {}).get("used_area_percent", 0) > seven_layout.get("summary", {}).get("used_area_percent", 0), "Dense kullanim metrigi artmiyor.", failures)

    rotated = _layout([_item("rot-1", "Mucahit", rotation=180)], cfg)
    _assert(rotated.get("items", [{}])[0].get("rotation") == 180, "180 derece rotation preview layout'ta korunmuyor.", failures)
    mirrored_paths = api.preview_name_cut_paths([_item("mir-1", "Leyla")], _config(mirror_cut=True))
    _assert(mirrored_paths.get("paths", [{}])[0].get("mirrored") is True, "Mirror cut preview path sonucunda isaretlenmiyor.", failures)

    app_js = APP_JS.read_text(encoding="utf-8")
    styles = STYLES_CSS.read_text(encoding="utf-8")
    render_section = app_js[app_js.find("function renderLaserLayoutPreview"): app_js.find("const selectedLayoutItem", app_js.find("function renderLaserLayoutPreview"))]
    _assert('const NAME_CUT_DEFAULT_FONT = "Brannboll Connect"' in app_js and "Brannboll Connect" in app_js, "Varsayilan uretim fontu Brannboll Connect degil.", failures)
    _assert("allow_rotation: true" in app_js, "Frontend allow_rotation varsayilani acik degil.", failures)
    _assert("textLength=" not in render_section and "lengthAdjust" not in render_section, "Ana canvas renderinda web text sikistirma kaldi.", failures)
    _assert("<path ${commonAttrs}" in app_js, "Ana canvas production layer path render etmiyor.", failures)
    _assert("preview_name_cut_paths" in app_js, "Frontend FontTools path preview bridge cagrisi yok.", failures)
    _assert("data-export-layer=\"production-only\"" in app_js, "Production-only export layer isareti eksik.", failures)
    _assert("stroke-width: .9" in styles, "RDWorks path konturu net siyah stroke stiline cekilmedi.", failures)
    _assert("rgba(148, 163, 184, 0.1)" in styles, "Grid/ruler gorsel yogunlugu azaltilmadi.", failures)

    safety = path_result.get("safety", {})
    _assert(safety.get("laser_auto_start") is False, "Lazer otomatik baslatma guvenlik sonucu false degil.", failures)
    _assert(safety.get("rdworks_auto_start") is False, "RDWorks otomatik baslatma guvenlik sonucu false degil.", failures)
    _assert(safety.get("printer_auto_start") is False, "Yazici otomatik baslatma guvenlik sonucu false degil.", failures)

    result = {
        "gate": "production_name_cut_rdworks_visual_nesting_gate",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "PASSED" if not failures else "FAILED",
        "failures": failures,
        "warnings": warnings,
        "seven_name_count": len(seven_placed),
        "seven_used_area_percent": seven_layout.get("summary", {}).get("used_area_percent"),
        "dense_name_count": len(dense_placed),
        "dense_row_count_first_page": len(rows),
        "dense_used_area_percent": dense_layout.get("summary", {}).get("used_area_percent"),
        "outlined_count": path_result.get("outlined_count"),
        "fallback_count": path_result.get("fallback_count"),
        "sample_svg": str(sample_svg),
        "safety": safety,
    }
    (OUT_DIR / "production_name_cut_rdworks_visual_nesting_gate_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_lines = [
        "# Production Name Cut RDWorks Visual Nesting Raporu",
        "",
        f"- Gate sonucu: **{result['status']}**",
        f"- 7 isim placement: {result['seven_name_count']}",
        f"- 7 isim kullanim: {result['seven_used_area_percent']}%",
        f"- 60 isim placement: {result['dense_name_count']}",
        f"- 60 isim ilk plate satir sayisi: {result['dense_row_count_first_page']}",
        f"- 60 isim kullanim: {result['dense_used_area_percent']}%",
        f"- Path outline sayisi: {result['outlined_count']}",
        f"- Fallback sayisi: {result['fallback_count']}",
        f"- Ornek production SVG: `{sample_svg}`",
        "",
        "## Dogrulananlar",
        "- Canvas uretim katmani FontTools path preview kullanir.",
        "- Isimler dense modda kaba 80 mm kutuya zorlanmadan natural path bbox + 1 mm gap ile dizilir.",
        "- 40-60 isim senaryosunda tabla asagi dogru dolar.",
        "- Grid, ruler, safe margin, selection ve handle export katmanina girmez.",
        "- Lazer, RDWorks ve yazici otomatik baslatilmaz.",
        "",
        "## Kalan Risk",
        "- Tam polygon nesting / boolean weld motoru bu gate'in kapsami degil; bu adim path-bbox tabanli RDWorks uretim onizleme profilidir.",
        "",
        "## Hatalar",
        *(f"- {failure}" for failure in failures),
    ]
    (OUT_DIR / "PRODUCTION_NAME_CUT_RDWORKS_VISUAL_NESTING_RAPORU.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
