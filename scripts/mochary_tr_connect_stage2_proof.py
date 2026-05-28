from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"
FONT_PATH = OUTPUT / "MocharyTRConnect-Stage2.ttf"
PROOF_PATH = OUTPUT / "MocharyTRConnect-Stage2-proof.svg"

TEST_STRINGS = [
    "abcçdefgğhıijk",
    "efgğhıijk",
    "çağrı",
    "yağmur",
    "buğra",
    "kişi",
    "ışık",
    "iğde",
    "ağ",
    "hi jk fi",
]
MANUAL_LIGATURES = {"ab": "a_b", "cc": "c_c"}


def glyph_sequence(text, cmap):
    glyphs = []
    i = 0
    while i < len(text):
        pair = text[i : i + 2]
        if pair in MANUAL_LIGATURES:
            glyphs.append(MANUAL_LIGATURES[pair])
            i += 2
            continue
        char = text[i]
        if char == " ":
            glyphs.append("space")
        else:
            glyphs.append(cmap[ord(char)])
        i += 1
    return glyphs


def main():
    font = TTFont(str(FONT_PATH))
    glyph_set = font.getGlyphSet()
    cmap = {}
    for table in font["cmap"].tables:
        cmap.update(table.cmap)

    rows = []
    scale = 0.095
    x_start = 28
    row_height = 74
    for row_index, text in enumerate(TEST_STRINGS):
        y = 70 + row_index * row_height
        x = x_start
        row_paths = [f'<text x="28" y="{y - 38}" font-family="Arial" font-size="12" fill="#444">{text}</text>']
        for glyph_name in glyph_sequence(text, cmap):
            if glyph_name == "space":
                x += 34
                continue
            pen = SVGPathPen(glyph_set)
            glyph_set[glyph_name].draw(pen)
            d = pen.getCommands()
            row_paths.append(
                f'<path d="{d}" transform="translate({x:.2f},{y:.2f}) scale({scale},-{scale})" '
                'fill="#111" stroke="none"/>'
            )
            x += glyph_set[glyph_name].width * scale * 0.82
        rows.extend(row_paths)

    svg = "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="790" viewBox="0 0 900 790">',
            '<rect width="900" height="790" fill="#fff"/>',
            '<text x="28" y="24" font-family="Arial" font-size="16" font-weight="700" fill="#111">Mochary TR Connect Stage 2</text>',
            *rows,
            "</svg>",
        ]
    )
    PROOF_PATH.write_text(svg, encoding="utf-8")
    print(PROOF_PATH)


if __name__ == "__main__":
    main()
