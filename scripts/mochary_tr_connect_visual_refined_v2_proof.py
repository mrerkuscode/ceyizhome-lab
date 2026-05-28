from __future__ import annotations

import json
from pathlib import Path
import shutil

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
REFINED = ROOT / "output" / "refined_v2"
DAY = ROOT / "output" / "2026-05-24" / "name_cut_visual_refined_v2"
FONT = REFINED / "MocharyTRConnect-VisualRefinedV2.ttf"
OVERVIEW = REFINED / "MocharyTRConnect-VisualRefinedV2-proof.svg"
RDWORKS_SVG = REFINED / "visual-refined-v2-rdworks-like.svg"
RDWORKS_PNG = REFINED / "visual-refined-v2-rdworks-like.png"

TEST_LINES = [
    "Türkçe",
    "Görkem",
    "ÇeyizHome",
    "Aşk ile söz verdik",
    "Ayşe & Mehmet",
    "Yağmur & Efe",
    "Çağrı",
    "Özge",
    "Ümit",
    "İrem",
    "Şule",
    "Buğra",
    "Mücahit",
    "Abdurrahman",
    "Kişi",
    "Işık",
    "12.05.2026",
]

TURKISH_LINES = [
    "ç Ç",
    "ğ Ğ",
    "ı I İ i",
    "ö Ö",
    "ş Ş",
    "ü Ü",
    "Türkçe",
    "Görkem",
    "Ayşe",
    "Yağmur",
]

RDWORKS_BASE_NAMES = [
    "Sedef", "Sefer", "Vahip", "Ayşe", "Mehmet", "Leyla", "Mücahit", "Serap",
    "İrem", "Özge", "Ümit", "Çağrı", "Yağmur", "Efe", "Burak", "Ceren",
    "Serkan", "Görkem", "Türkçe", "Şule", "Buğra", "Abdurrahman", "Nermin",
    "Zeynep", "Yıldız",
]
RDWORKS_NAMES = (RDWORKS_BASE_NAMES * 2)[:50]


def escape_attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def cmap_for(font: TTFont) -> dict[int, str]:
    cmap: dict[int, str] = {}
    for table in font["cmap"].tables:
        cmap.update(table.cmap)
    return cmap


def glyph_path(glyph_set, glyph_name: str) -> str:
    pen = SVGPathPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return pen.getCommands()


def glyph_advance(glyph_set, cmap: dict[int, str], text: str, scale: float) -> float:
    total = 0.0
    for ch in text:
        if ch == " ":
            total += 250 * scale
            continue
        glyph_name = cmap.get(ord(ch))
        if not glyph_name:
            total += 300 * scale
            continue
        total += glyph_set[glyph_name].width * scale * 0.9
    return total


def draw_svg_word(rows: list[str], font: TTFont, glyph_set, cmap: dict[int, str], text: str, x: float, y: float, scale: float, group_id: str, stroke_width: float = 1.45) -> float:
    cursor = x
    rows.append(f'<g id="{group_id}" data-name="{escape_attr(text)}" data-source-text="{escape_attr(text)}">')
    for ch in text:
        if ch == " ":
            cursor += 250 * scale
            continue
        glyph_name = cmap.get(ord(ch))
        if not glyph_name:
            rows.append(f"<!-- missing glyph U+{ord(ch):04X} {escape_attr(ch)} -->")
            cursor += 300 * scale
            continue
        path_data = glyph_path(glyph_set, glyph_name)
        rows.append(
            f'<path d="{path_data}" transform="translate({cursor:.3f},{y:.3f}) scale({scale:.5f},{-scale:.5f})" '
            f'fill="none" stroke="#020617" stroke-width="{stroke_width}" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
        )
        cursor += glyph_set[glyph_name].width * scale * 0.9
    rows.append("</g>")
    return cursor - x


def svg_header(width: int, height: int, desc: str, source_texts: list[str]) -> list[str]:
    metadata = json.dumps({"source_texts": source_texts}, ensure_ascii=False)
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f"<desc>{escape_attr(desc)}</desc>",
        f"<metadata>{escape_attr(metadata)}</metadata>",
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]


def make_overview_svg() -> Path:
    font = TTFont(str(FONT))
    glyph_set = font.getGlyphSet()
    cmap = cmap_for(font)
    height = 1480
    rows = svg_header(1400, height, "Mochary TR Connect Visual Refined V2 Turkish proof. Path-only; no visible text elements.", TEST_LINES)
    y = 95
    for index, line in enumerate(TEST_LINES):
        draw_svg_word(rows, font, glyph_set, cmap, line, 48, y, 0.078, f"sample-{index:02d}", stroke_width=1.55)
        y += 78
    rows.append("</svg>")
    OVERVIEW.write_text("\n".join(rows), encoding="utf-8")
    return OVERVIEW


def make_sample_svg(path: Path, lines: list[str], width: int = 1280, height: int = 760, scale: float = 0.09) -> Path:
    font = TTFont(str(FONT))
    glyph_set = font.getGlyphSet()
    cmap = cmap_for(font)
    rows = svg_header(width, height, "Path-only Visual Refined V2 sample proof.", lines)
    y = 115
    for index, line in enumerate(lines):
        draw_svg_word(rows, font, glyph_set, cmap, line, 48, y, scale, f"sample-{index:02d}", stroke_width=1.55)
        y += 94
    rows.append("</svg>")
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def make_rdworks_svg() -> Path:
    font = TTFont(str(FONT))
    glyph_set = font.getGlyphSet()
    cmap = cmap_for(font)
    rows = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1200" viewBox="0 0 800 600">',
        "<desc>RDWorks-like path-only Visual Refined V2 nesting proof.</desc>",
        f"<metadata>{escape_attr(json.dumps({'source_texts': RDWORKS_NAMES}, ensure_ascii=False))}</metadata>",
        '<rect width="800" height="600" fill="#ffffff"/>',
    ]
    for x in range(0, 801, 50):
        rows.append(f'<path d="M{x} 0 L{x} 600" stroke="#d8dde8" stroke-width="0.45" fill="none"/>')
    for y in range(0, 601, 50):
        rows.append(f'<path d="M0 {y} L800 {y}" stroke="#d8dde8" stroke-width="0.45" fill="none"/>')
    rows.append('<path d="M15 15 L785 15 L785 585 L15 585 Z" stroke="#22c55e" stroke-width="0.55" stroke-dasharray="3 2" fill="none"/>')
    x = 18.0
    y = 49.0
    row_h = 39.0
    scale = 0.040
    for index, name in enumerate(RDWORKS_NAMES):
        estimated = glyph_advance(glyph_set, cmap, name, scale)
        if x + estimated > 770:
            x = 18.0
            y += row_h
        draw_svg_word(rows, font, glyph_set, cmap, name, x, y, scale, f"name-{index:02d}", stroke_width=0.95)
        x += max(estimated + 2.0, 32.0)
    rows.append("</svg>")
    RDWORKS_SVG.write_text("\n".join(rows), encoding="utf-8")
    return RDWORKS_SVG


def make_png(path: Path, lines: list[str], size=(1500, 1000), font_size=58) -> Path:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    fnt = ImageFont.truetype(str(FONT), font_size)
    y = 40
    for line in lines:
        draw.text((42, y), line, font=fnt, fill=(3, 7, 18))
        y += int(font_size * 1.55)
    image.save(path)
    return path


def make_rdworks_png(path: Path) -> Path:
    image = Image.new("RGB", (1600, 1200), "white")
    draw = ImageDraw.Draw(image)
    sx = sy = 2
    for x in range(0, 801, 50):
        draw.line((x * sx, 0, x * sx, 600 * sy), fill=(218, 223, 232), width=1)
    for y in range(0, 601, 50):
        draw.line((0, y * sy, 800 * sx, y * sy), fill=(218, 223, 232), width=1)
    draw.rectangle((30, 30, 1570, 1170), outline=(34, 197, 94), width=1)
    fnt = ImageFont.truetype(str(FONT), 54)
    x = 36
    y = 62
    for name in RDWORKS_NAMES:
        bbox = draw.textbbox((0, 0), name, font=fnt)
        w = bbox[2] - bbox[0]
        if x + w > 1540:
            x = 36
            y += 76
        draw.text((x, y), name, font=fnt, fill=(3, 7, 18))
        x += max(w + 7, 58)
    image.save(path)
    return path


def main() -> None:
    REFINED.mkdir(parents=True, exist_ok=True)
    DAY.mkdir(parents=True, exist_ok=True)
    overview = make_overview_svg()
    rdworks = make_rdworks_svg()
    turkish = make_sample_svg(DAY / "refined-v2-turkish-characters.svg", TURKISH_LINES, width=1250, height=960, scale=0.105)
    burak = make_sample_svg(DAY / "refined-v2-burak-ceren-serkan.svg", ["Burak", "Ceren", "Serkan"], width=1100, height=420, scale=0.12)
    day_overview = DAY / "refined-v2-proof-overview.svg"
    day_rdworks = DAY / "refined-v2-rdworks-like.svg"
    shutil.copy2(overview, day_overview)
    shutil.copy2(rdworks, day_rdworks)
    make_png(DAY / "refined-v2-proof-overview.png", TEST_LINES, size=(1600, 1300), font_size=60)
    make_png(DAY / "refined-v2-turkish-characters.png", TURKISH_LINES, size=(1300, 980), font_size=74)
    make_png(DAY / "refined-v2-burak-ceren-serkan.png", ["Burak", "Ceren", "Serkan"], size=(1100, 480), font_size=86)
    make_rdworks_png(DAY / "refined-v2-rdworks-like.png")
    make_rdworks_png(DAY / "refined-v2-800x600-nesting.png")
    make_rdworks_png(RDWORKS_PNG)
    print("\n".join(str(path) for path in [overview, day_overview, turkish, burak, rdworks, RDWORKS_PNG]))


if __name__ == "__main__":
    main()
