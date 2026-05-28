from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "output" / "final"
FONT = FINAL / "MocharyTRConnect-Regular.ttf"
PROOF = FINAL / "MocharyTRConnect-proof.svg"
SECTIONS = [
    ("Metadata", ["Mochary TR Connect Regular", "CeyizHome Lab original experimental font project"]),
    ("Kucuk harfler", ["abc\u00e7defg\u011fh\u0131ijklmno\u00f6prs\u015ftu\u00fcvyzxwq"]),
    ("Buyuk harfler", ["ABC\u00c7DEFG\u011eHI\u0130JKLMNO\u00d6PRS\u015eTU\u00dcVYZXWQ"]),
    ("Turkce karakterler", ["\u00e7 \u011f \u0131 \u0130 \u00f6 \u00d6 \u015f \u015e \u00fc \u00dc"]),
    ("Rakamlar", ["0123456789", "12.05.2026", "02.06.2026"]),
    ("Semboller", ["& - . , ' / : ; ! ? ( ) + _ \u20ba \u20ac $ % # @ * = < > [ ] { } \u00b0 \u2022 \u00b7"]),
    ("Connection sample", ["fi hi ij ki gg ti ri si ci ei"]),
    ("Turkce ornekler", [
        "T\u00fcrk\u00e7e",
        "G\u00f6rkem",
        "CeyizHome",
        "A\u015fk ile s\u00f6z verdik",
        "Ay\u015fe & Mehmet",
        "Ya\u011fmur & Efe",
        "\u00c7a\u011fr\u0131 \u00d6zge \u00dcmit \u0130rem \u015eule Bu\u011fra",
        "50 x 30 mm",
        "80 x 40 mm",
        "T\u00dcRK\u00c7E",
        "G\u00d6RKEM",
        "\u00c7EY\u0130ZHOME",
    ]),
    ("Lazer kesim notlari", [
        "No laser, RDWorks or printer action is triggered.",
        "Dots, tails and Turkish marks are QA checked; visual refinement may still continue.",
    ]),
]


def cmap_for(font):
    cmap = {}
    for table in font["cmap"].tables:
        cmap.update(table.cmap)
    return cmap


def draw_line(rows, glyph_set, cmap, text, x, y, scale=0.052):
    rows.append(f'<text x="{x}" y="{y-30}" font-family="Arial" font-size="12" fill="#555">{text}</text>')
    cursor = x
    for ch in text:
        if ch == " ":
            cursor += 24
            continue
        glyph_name = cmap.get(ord(ch))
        if not glyph_name:
            rows.append(f'<text x="{cursor:.2f}" y="{y:.2f}" font-family="Arial" font-size="18" fill="#c00">□</text>')
            cursor += 24
            continue
        pen = SVGPathPen(glyph_set)
        glyph_set[glyph_name].draw(pen)
        rows.append(f'<path d="{pen.getCommands()}" transform="translate({cursor:.2f},{y:.2f}) scale({scale},-{scale})" fill="#111"/>')
        cursor += glyph_set[glyph_name].width * scale * 0.8


def main():
    FINAL.mkdir(parents=True, exist_ok=True)
    font = TTFont(str(FONT))
    glyph_set = font.getGlyphSet()
    cmap = cmap_for(font)
    rows = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1900" viewBox="0 0 1440 1900">',
        '<rect width="1440" height="1900" fill="#fff"/>',
        '<text x="28" y="30" font-family="Arial" font-size="19" font-weight="700">Mochary TR Connect Regular - Final Proof</text>',
    ]
    y = 82
    for title, lines in SECTIONS:
        rows.append(f'<text x="28" y="{y}" font-family="Arial" font-size="16" font-weight="700" fill="#111">{title}</text>')
        y += 52
        for line in lines:
            draw_line(rows, glyph_set, cmap, line, 34, y)
            y += 70
        y += 18
    rows.append("</svg>")
    PROOF.write_text("\n".join(rows), encoding="utf-8")
    print(PROOF)


if __name__ == "__main__":
    main()
