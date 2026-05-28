from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend import combined_production_api as api  # noqa: E402


OUT_DIR = ROOT / "output" / "2026-05-21" / "production_name_cut_rdworks_outline_preview"
APP_JS = ROOT / "src" / "webui" / "app.js"
STYLES = ROOT / "src" / "webui" / "styles.css"


def _config() -> dict[str, object]:
    return {
        "width_mm": 800,
        "height_mm": 600,
        "target_name_width_mm": 80,
        "target_name_height_mm": 40,
        "target_gap_mm": 1,
        "item_gap_mm": 1,
        "row_gap_mm": 1,
        "margin_mm": 15,
        "dense_nesting": True,
        "font_family": "Ceyizhome Lab Script (Mochary)",
        "mirror_cut": False,
    }


def _item(item_id: str, text: str) -> dict[str, object]:
    return {
        "item_id": item_id,
        "id": item_id,
        "name_text": text,
        "preview_text": text,
        "style": "Ceyizhome Lab Script (Mochary)",
        "width_mm": 80,
        "height_mm": 40,
        "offset_mm": 0.3,
        "quantity": "1",
        "operator_size_locked": True,
    }


def _assert(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def _write_preview_svg(result: dict[str, object]) -> Path:
    cfg = result["layout"]["config"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{cfg["width_mm"]}mm" height="{cfg["height_mm"]}mm" viewBox="0 0 {cfg["width_mm"]} {cfg["height_mm"]}">',
        '<rect x="0" y="0" width="800" height="600" fill="#fff"/>',
        '<g id="production-layer-only">',
    ]
    for path in result.get("paths", []):
        if path.get("path_data"):
            parts.append(f'<path d="{path["path_data"]}" fill="none" stroke="#020617" stroke-width="0.72" stroke-linejoin="round" stroke-linecap="round"/>')
    parts.extend(["</g>", "</svg>"])
    svg_path = OUT_DIR / "name-cut-rdworks-outline-preview.svg"
    svg_path.write_text("\n".join(parts), encoding="utf-8")
    return svg_path


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    warnings: list[str] = []
    cfg = _config()

    single_result = api.preview_name_cut_paths([_item("rdw-1", "Mücahit Leyla")], cfg)
    _assert(single_result.get("outlined_count") == 1, "Tek isim/couple için FontTools outline path oluşmadı.", failures)
    _assert(single_result.get("fallback_count") == 0, "Tek isim/couple fallback text'e düştü.", failures)
    first_path = ((single_result.get("paths") or [{}])[0]).get("path_data", "")
    _assert(str(first_path).startswith("M "), "Path data SVG path komutlarıyla başlamıyor.", failures)
    _assert(len(str(first_path)) > 1000, "Path data gerçek font konturu olamayacak kadar kısa.", failures)
    _assert(single_result.get("safety", {}).get("rdworks_auto_start") is False, "RDWorks auto-start güvenlik sonucu false değil.", failures)
    _assert(single_result.get("safety", {}).get("laser_auto_start") is False, "Lazer auto-start güvenlik sonucu false değil.", failures)
    _assert(single_result.get("safety", {}).get("printer_auto_start") is False, "Yazıcı auto-start güvenlik sonucu false değil.", failures)

    names = ["Sedef", "Sefer", "Hasan", "Hüseyin", "Leyla", "Ayşe", "Veli"]
    multi_result = api.preview_name_cut_paths([_item(f"rdw-{index}", name) for index, name in enumerate(names, start=1)], cfg)
    _assert(multi_result.get("outlined_count") == len(names), "7 isim testinde her isim için ayrı outline path oluşmadı.", failures)
    _assert(len(multi_result.get("paths") or []) == len(names), "7 isim testinde path sayısı isim sayısıyla eşleşmiyor.", failures)
    _assert(all(path.get("path_data") for path in multi_result.get("paths", [])), "7 isim testinde boş path var.", failures)

    app_js = APP_JS.read_text(encoding="utf-8")
    styles = STYLES.read_text(encoding="utf-8")
    render_section = app_js[app_js.find("function renderLaserLayoutPreview"): app_js.find("const selectedLayoutItem", app_js.find("function renderLaserLayoutPreview"))]
    _assert("preview_name_cut_paths" in app_js, "Frontend bridge path preview çağrısı yok.", failures)
    _assert("<path ${commonAttrs}" in app_js, "Ana canvas üretim katmanı FontTools path render etmiyor.", failures)
    _assert("lengthAdjust=\"spacingAndGlyphs\"" not in render_section, "Ana canvas üretim render'ında lengthAdjust hâlâ var.", failures)
    _assert("textLength=" not in render_section, "Ana canvas üretim render'ında textLength hâlâ var.", failures)
    _assert("fallback-text-needs-review" in app_js, "Path üretilemeyince sahte başarı yerine fallback/needs-review işareti yok.", failures)
    _assert("stroke: #020617" in styles and "fallback-text-preview" in styles, "RDWorks siyah path/fallback stilleri eksik.", failures)
    _assert("data-export-layer=\"production-only\"" in app_js, "Canvas export güvenliği için production-only katman işareti eksik.", failures)

    svg_path = _write_preview_svg(multi_result)
    svg_text = svg_path.read_text(encoding="utf-8")
    forbidden = ["safe", "selection", "handle", "ruler", "grid", "toolbar", "inspector"]
    leaked = [word for word in forbidden if word in svg_text.lower()]
    _assert(not leaked, f"Preview SVG production örneğinde UI/helper kelimeleri var: {leaked}", failures)

    result = {
        "gate": "production_name_cut_rdworks_outline_preview_gate",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "PASSED" if not failures else "FAILED",
        "failures": failures,
        "warnings": warnings,
        "single_outline_count": single_result.get("outlined_count"),
        "multi_outline_count": multi_result.get("outlined_count"),
        "fallback_count": single_result.get("fallback_count", 0) + multi_result.get("fallback_count", 0),
        "sample_svg": str(svg_path),
        "safety": single_result.get("safety", {}),
    }
    (OUT_DIR / "production_name_cut_rdworks_outline_preview_gate_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report = [
        "# Production Name Cut RDWorks Outline Preview Raporu",
        "",
        f"- Gate sonucu: **{result['status']}**",
        f"- Tek isim outline sayısı: {result['single_outline_count']}",
        f"- 7 isim outline sayısı: {result['multi_outline_count']}",
        f"- Fallback sayısı: {result['fallback_count']}",
        f"- Örnek SVG: `{svg_path}`",
        "",
        "## Doğrulananlar",
        "- Ana canvas render'ında `textLength` / `lengthAdjust` üretim sıkıştırması kaldırıldı.",
        "- Backend FontTools konturları read-only preview için dönüyor.",
        "- Frontend path varsa SVG `<path>` çiziyor; path yoksa fallback/needs-review olarak işaretliyor.",
        "- Grid, ruler, safe margin, selection ve helper katmanları örnek production SVG'ye girmiyor.",
        "- RDWorks, lazer ve yazıcı otomatik başlatılmıyor.",
        "",
        "## Hatalar",
        *(f"- {failure}" for failure in failures),
    ]
    (OUT_DIR / "PRODUCTION_NAME_CUT_RDWORKS_OUTLINE_PREVIEW_RAPORU.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
