from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"
FONT = OUTPUT / "MocharyTRConnect-Stage4.ttf"
PROOF = OUTPUT / "MocharyTRConnect-Stage4-proof.svg"
LINES = ["tuüvyzxwq", "Ayşe & Mehmet", "Yağmur & Efe", "tuğçe", "ümit", "yüzük", "yıldız", "zeynep", "vefa", "query xw test", "aşk? evet!"]


def main():
    font = TTFont(str(FONT))
    glyph_set = font.getGlyphSet()
    cmap = {}
    for table in font["cmap"].tables:
        cmap.update(table.cmap)
    rows = ['<svg xmlns="http://www.w3.org/2000/svg" width="1020" height="820" viewBox="0 0 1020 820">', '<rect width="1020" height="820" fill="#fff"/>', '<text x="28" y="26" font-family="Arial" font-size="17" font-weight="700">Mochary TR Connect Stage 4</text>']
    scale = 0.08
    for idx, text in enumerate(LINES):
        y = 78 + idx * 66
        x = 28
        rows.append(f'<text x="28" y="{y-35}" font-family="Arial" font-size="12" fill="#444">{text}</text>')
        for ch in text:
            if ch == " ":
                x += 28
                continue
            name = cmap[ord(ch)]
            pen = SVGPathPen(glyph_set)
            glyph_set[name].draw(pen)
            rows.append(f'<path d="{pen.getCommands()}" transform="translate({x:.2f},{y:.2f}) scale({scale},-{scale})" fill="#111"/>')
            x += glyph_set[name].width * scale * 0.82
    rows.append("</svg>")
    PROOF.write_text("\n".join(rows), encoding="utf-8")
    print(PROOF)


if __name__ == "__main__":
    main()
