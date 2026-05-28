from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from webui_backend.font_analysis import analyze_font  # noqa: E402


def main() -> int:
    candidates = [
        PROJECT_ROOT / "assets" / "fonts" / "Mochary.ttf",
        Path(r"C:\Users\Pc\AppData\Local\Temp\Mochary.ttf"),
    ]
    font_path = next((path for path in candidates if path.exists()), candidates[-1])
    result = analyze_font(font_path)
    day_dir = PROJECT_ROOT / "output" / datetime.now().strftime("%Y-%m-%d") / "font_lab"
    day_dir.mkdir(parents=True, exist_ok=True)
    json_path = day_dir / "ceyizhome_lab_script_font_analysis.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    web_data_dir = PROJECT_ROOT / "src" / "webui" / "data"
    web_data_dir.mkdir(parents=True, exist_ok=True)
    (web_data_dir / "font_analysis_mochary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    coverage = result.get("coverage", {})
    variants = result.get("connected_capital_variants", {})
    report_lines = [
        "# Ceyizhome Lab Script Font Analysis",
        "",
        f"- Font: `{result.get('font_path', font_path)}`",
        f"- Status: `{result.get('status')}`",
        f"- Glyph count: `{result.get('glyph_count', 0)}`",
        f"- GSUB: `{', '.join(result.get('features', {}).get('GSUB', [])) or '-'}`",
        f"- GPOS: `{', '.join(result.get('features', {}).get('GPOS', [])) or '-'}`",
        f"- Turkish coverage: `{coverage.get('turkish', {}).get('coverage_percent', 0)}%`",
        f"- Punctuation coverage: `{coverage.get('punctuation', {}).get('coverage_percent', 0)}%`",
        f"- TRY glyph present: `{not result.get('try_fallback_required', True)}`",
        "",
        "## Connected Capital Variants",
        "",
    ]
    report_lines.extend([f"- `{key}`: {'var' if present else 'yok'}" for key, present in variants.items()])
    report_lines.extend([
        "",
        "## Export Rule",
        "",
        "- Preview: DOM/SVG text with OpenType CSS.",
        "- Production export: fontTools outline/path; each name remains a separate object.",
        "- Manual bridges are applied only inside the same name object.",
    ])
    md_path = day_dir / "ceyizhome_lab_script_font_analysis.md"
    md_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(json.dumps({"status": result.get("status"), "json": str(json_path), "web_data": str(web_data_dir / "font_analysis_mochary.json"), "report": str(md_path)}, ensure_ascii=False))
    return 0 if result.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
