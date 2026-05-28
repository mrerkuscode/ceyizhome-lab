from __future__ import annotations

from pathlib import Path
import shutil

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
REFINED = ROOT / "output" / "refined"
DAY = ROOT / "output" / "2026-05-24" / "name_cut_visual_refined_font"
FONT = REFINED / "MocharyTRConnect-VisualRefined.ttf"
OVERVIEW = REFINED / "MocharyTRConnect-VisualRefined-proof.svg"
RDWORKS_SVG = REFINED / "visual-refined-rdworks-like.svg"
RDWORKS_PNG = REFINED / "visual-refined-rdworks-like.png"

TEST_LINES = [
    "Turkce",
    "Gorkem",
    "CeyizHome",
    "Ask ile soz verdik",
    "Ayse & Mehmet",
    "Yagmur & Efe",
    "Cagri",
    "Ozge",
    "Umit",
    "Irem",
    "Sule",
    "Bugra",
    "Mehmet",
    "Mucahit",
    "Abdurrahman",
    "Burak Ceren Serkan",
    "12.05.2026",
]

TURKISH_LINES = [
    "Türkçe",
    "Görkem",
    "Ayşe & Mehmet",
    "Yağmur & Efe",
    "Çağrı",
    "Özge",
    "Ümit",
    "İrem",
    "Şule",
    "Buğra",
]

RDWORKS_NAMES = [
    "Sedef", "Sefer", "Hasan", "Hüseyin", "Leyla", "Ayşe", "Veli", "İrem",
    "Özge", "Ümit", "Çağrı", "İlayda", "Buğra", "Yağmur", "Efe", "Burak",
    "Ceren", "Serkan", "Görkem", "Türkçe", "Şule", "Mehmet", "Mücahit",
    "Abdurrahman", "Pınar", "Nermin", "Ölçü", "Şeker", "Yıldız", "Zeynep",
    "Yağmur & Efe", "Ayşe & Mehmet",
]


def cmap_for(font: TTFont) -> dict[int, str]:
    cmap: dict[int, str] = {}
    for table in font["cmap"].tables:
        cmap.update(table.cmap)
    return cmap


def glyph_path(glyph_set, glyph_name: str) -> str:
    pen = SVGPathPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return pen.getCommands()


def draw_svg_word(rows: list[str], font: TTFont, glyph_set, cmap: dict[int, str], text: str, x: float, y: float, scale: float, group_id: str) -> float:
    cursor = x
    rows.append(f'<g id="{group_id}" data-name="{escape_attr(text)}">')
    for ch in text:
        if ch == " ":
            cursor += 250 * scale
            continue
        glyph_name = cmap.get(ord(ch))
        if not glyph_name:
            cursor += 300 * scale
            continue
        path_data = glyph_path(glyph_set, glyph_name)
        rows.append(
            f'<path d="{path_data}" transform="translate({cursor:.3f},{y:.3f}) scale({scale:.5f},{-scale:.5f})" '
            'fill="none" stroke="#020617" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
        )
        cursor += glyph_set[glyph_name].width * scale * 0.92
    rows.append("</g>")
    return cursor - x


def escape_attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def make_overview_svg() -> Path:
    font = TTFont(str(FONT))
    glyph_set = font.getGlyphSet()
    cmap = cmap_for(font)
    height = 1480
    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="{height}" viewBox="0 0 1400 {height}">',
        "<desc>Mochary TR Connect Visual Refined proof. All sample letters are path elements; no visible text elements are used.</desc>",
        '<rect width="1400" height="1480" fill="#ffffff"/>',
    ]
    y = 95
    for index, line in enumerate(TEST_LINES):
        draw_svg_word(rows, font, glyph_set, cmap, line, 48, y, 0.075, f"sample-{index:02d}")
        y += 78
    rows.append("</svg>")
    OVERVIEW.write_text("\n".join(rows), encoding="utf-8")
    return OVERVIEW


def make_sample_svg(path: Path, lines: list[str], width: int = 1280, height: int = 760) -> Path:
    font = TTFont(str(FONT))
    glyph_set = font.getGlyphSet()
    cmap = cmap_for(font)
    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<desc>Path-only Visual Refined sample proof.</desc>",
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    y = 110
    for index, line in enumerate(lines):
        draw_svg_word(rows, font, glyph_set, cmap, line, 48, y, 0.085, f"sample-{index:02d}")
        y += 92
    rows.append("</svg>")
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def make_rdworks_svg() -> Path:
    font = TTFont(str(FONT))
    glyph_set = font.getGlyphSet()
    cmap = cmap_for(font)
    rows = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1200" viewBox="0 0 800 600">',
        "<desc>RDWorks-like path-only Visual Refined nesting proof.</desc>",
        '<rect width="800" height="600" fill="#ffffff"/>',
    ]
    for x in range(0, 801, 50):
        rows.append(f'<path d="M{x} 0 L{x} 600" stroke="#d8dde8" stroke-width="0.45" fill="none"/>')
    for y in range(0, 601, 50):
        rows.append(f'<path d="M0 {y} L800 {y}" stroke="#d8dde8" stroke-width="0.45" fill="none"/>')
    rows.append('<path d="M15 15 L785 15 L785 585 L15 585 Z" stroke="#22c55e" stroke-width="0.55" stroke-dasharray="3 2" fill="none"/>')
    x = 18.0
    y = 48.0
    row_h = 38.0
    scale = 0.042
    for index, name in enumerate(RDWORKS_NAMES):
        estimated = sum((glyph_set[cmap.get(ord(ch), ".notdef")].width if ord(ch) in cmap else 250) for ch in name) * scale * 0.92
        if x + estimated > 770:
            x = 18
            y += row_h
        draw_svg_word(rows, font, glyph_set, cmap, name, x, y, scale, f"name-{index:02d}")
        x += max(estimated + 1.5, 35)
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
        x += w + 5
    image.save(path)
    return path


def main() -> None:
    REFINED.mkdir(parents=True, exist_ok=True)
    DAY.mkdir(parents=True, exist_ok=True)
    overview = make_overview_svg()
    rdworks = make_rdworks_svg()
    turkish = make_sample_svg(DAY / "refined-turkish-characters.svg", TURKISH_LINES)
    burak = make_sample_svg(DAY / "refined-burak-ceren-serkan.svg", ["Burak", "Ceren", "Serkan"], width=1100, height=420)
    day_overview = DAY / "refined-proof-overview.svg"
    shutil.copy2(overview, day_overview)
    day_rdworks = DAY / "refined-rdworks-like.svg"
    shutil.copy2(rdworks, day_rdworks)
    make_png(DAY / "refined-proof-overview.png", TEST_LINES, size=(1600, 1300), font_size=58)
    make_png(DAY / "refined-turkish-characters.png", TURKISH_LINES, size=(1300, 920), font_size=68)
    make_png(DAY / "refined-burak-ceren-serkan.png", ["Burak", "Ceren", "Serkan"], size=(1100, 480), font_size=84)
    make_rdworks_png(DAY / "refined-rdworks-like.png")
    make_rdworks_png(DAY / "refined-800x600-nesting.png")
    make_rdworks_png(RDWORKS_PNG)
    print("\n".join(str(path) for path in [overview, day_overview, turkish, burak, rdworks, RDWORKS_PNG]))


if __name__ == "__main__":
    main()
