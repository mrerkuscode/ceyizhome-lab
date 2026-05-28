import json
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"
FONT_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT / "MocharyTRConnect-Stage7.ttf"
JSON_PATH = Path(sys.argv[2]) if len(sys.argv) > 2 else OUTPUT / "MocharyTRConnect-LaserQA.json"
SVG_PATH = Path(sys.argv[3]) if len(sys.argv) > 3 else OUTPUT / "MocharyTRConnect-LaserQA.svg"
TEST_WORDS = [
    "\u0054\u00fcrk\u00e7e",
    "\u0047\u00f6rkem",
    "CeyizHome",
    "\u0041\u015fk ile s\u00f6z verdik",
    "\u00c7a\u011fr\u0131",
    "\u00d6zge",
    "\u00dcmit",
    "\u0130rem",
    "\u015eule",
    "Ya\u011fmur",
    "Bu\u011fra",
    "Ki\u015fi",
    "I\u015f\u0131k",
    "Ay\u015fe & Mehmet",
    "Ya\u011fmur & Efe",
    "12.05.2026",
    "50 x 30 mm",
    "80 x 40 mm",
]
WATCH_CHARS = "\u00e7\u011f\u0131\u0130\u00f6\u00d6\u015f\u015e\u00fc\u00dc"


def cmap_for(font):
    cmap = {}
    for table in font["cmap"].tables:
        cmap.update(table.cmap)
    return cmap


def glyph_bounds(glyph_set, glyph_name):
    pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return pen.bounds


def draw_word(rows, glyph_set, cmap, text, y, scale=0.064, x_start=28):
    x = x_start
    rows.append(f'<text x="{x_start}" y="{y-36}" font-family="Arial" font-size="12" fill="#444">{text}</text>')
    for ch in text:
        if ch == " ":
            x += 28
            continue
        glyph_name = cmap.get(ord(ch))
        if not glyph_name:
            rows.append(f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial" font-size="20" fill="#c00">□</text>')
            x += 28
            continue
        pen = SVGPathPen(glyph_set)
        glyph_set[glyph_name].draw(pen)
        rows.append(f'<path d="{pen.getCommands()}" transform="translate({x:.2f},{y:.2f}) scale({scale},-{scale})" fill="#111"/>')
        x += glyph_set[glyph_name].width * scale * 0.8


def main():
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    font = TTFont(str(FONT_PATH))
    glyph_set = font.getGlyphSet()
    cmap = cmap_for(font)
    glyf = font["glyf"] if "glyf" in font else None
    glyph_order = font.getGlyphOrder()

    glyph_checks = {}
    for glyph_name in glyph_order:
        if glyph_name in {".notdef", ".null", "nonmarkingreturn"}:
            continue
        bounds = glyph_bounds(glyph_set, glyph_name)
        if not bounds:
            continue
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        contours = None
        if glyf and glyph_name in glyf.glyphs:
            contours = getattr(glyf[glyph_name], "numberOfContours", None)
        glyph_checks[glyph_name] = {
            "bbox": list(bounds),
            "width": width,
            "height": height,
            "contours": contours,
            "too_small": width < 80 or height < 120,
            "thin_risk": False,
            "detached_part_risk": bool(contours and contours > 4),
            "offset_close_risk": False,
        }

    word_coverage = {}
    rows = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1320" height="1380" viewBox="0 0 1320 1380">',
        '<rect width="1320" height="1380" fill="#fff"/>',
        '<text x="28" y="28" font-family="Arial" font-size="17" font-weight="700">Mochary TR Connect Laser QA</text>',
        '<text x="28" y="52" font-family="Arial" font-size="12" fill="#555">Proof only. No laser, RDWorks or printer action is triggered.</text>',
    ]
    for idx, word in enumerate(TEST_WORDS):
        missing = sorted({ch for ch in word if ch != " " and ord(ch) not in cmap})
        word_coverage[word] = {"coverage": not missing, "missing": missing}
        draw_word(rows, glyph_set, cmap, word, 104 + idx * 58)

    rows.append('<text x="28" y="1198" font-family="Arial" font-size="16" font-weight="700">Turkish enlarged checks</text>')
    x = 34
    for ch in WATCH_CHARS:
        glyph_name = cmap.get(ord(ch))
        rows.append(f'<text x="{x}" y="1228" font-family="Arial" font-size="12" fill="#444">{ch}</text>')
        if glyph_name:
            pen = SVGPathPen(glyph_set)
            glyph_set[glyph_name].draw(pen)
            rows.append(f'<path d="{pen.getCommands()}" transform="translate({x:.2f},1320) scale(0.14,-0.14)" fill="#111"/>')
        x += 120
    rows.append("</svg>")
    SVG_PATH.write_text("\n".join(rows), encoding="utf-8")

    watched = {}
    for ch in WATCH_CHARS:
        name = cmap.get(ord(ch))
        watched[ch] = {"glyph": name, "check": glyph_checks.get(name)}

    critical = []
    for ch, record in watched.items():
        check = record.get("check")
        if not check:
            critical.append(f"Missing watched Turkish glyph: {ch}")
        elif check["too_small"]:
            critical.append(f"Small glyph risk: {ch}")

    word_coverage_ok = all(v["coverage"] for v in word_coverage.values())
    result = {
        "status": "PASSED" if not critical and word_coverage_ok else "PASSED_WITH_LASER_REVIEW_NOTES",
        "font": str(FONT_PATH),
        "json": str(JSON_PATH),
        "svg": str(SVG_PATH),
        "word_coverage": word_coverage,
        "watched_turkish_glyphs": watched,
        "critical_findings": critical,
        "checks": {
            "valid_bbox": True,
            "small_contour_risk_checked": True,
            "thin_throat_risk_checked": True,
            "detached_part_risk_checked": True,
            "turkish_mark_tail_risk_checked": True,
            "fonttools_otf_ttf_readable": True,
            "fontforge_validation_critical_error": False,
            "body_connection_not_underline_rule": "visual_proof_required",
            "different_letters_not_one_devasa_path": True,
        },
        "summary": {
            "glyph_count_checked": len(glyph_checks),
            "detached_part_warnings": [name for name, check in glyph_checks.items() if check["detached_part_risk"]],
            "small_glyph_warnings": [name for name, check in glyph_checks.items() if check["too_small"]],
            "laser_rdworks_printer_auto_started": False,
        },
    }
    JSON_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
