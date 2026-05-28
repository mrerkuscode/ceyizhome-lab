import json
import os

import fontforge


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT = os.path.join(ROOT, "output")
SFD = os.path.join(OUTPUT, "MocharyTRConnect-Stage4.sfd")
OTF = os.path.join(OUTPUT, "MocharyTRConnect-Stage4.otf")
TTF = os.path.join(OUTPUT, "MocharyTRConnect-Stage4.ttf")
FEA = os.path.join(OUTPUT, "MocharyTRConnect-Stage4.fea")
RESULT = os.path.join(OUTPUT, "mochary_tr_connect_stage4_qa_result.json")

TESTS = ["tuüvyzxwq", "Ayşe & Mehmet", "Yağmur & Efe", "tuğçe", "ümit", "yüzük", "yıldız", "zeynep", "vefa", "query xw test", "aşk? evet!"]
EXTRA = {"ç": "ccedilla", "ğ": "gcircumflex", "ı": "dotlessi", "ö": "odieresis", "ş": "scedilla", "ü": "udieresis", "&": "ampersand", "-": "hyphen", ".": "period", ",": "comma", "'": "quotesingle", "/": "slash", ":": "colon", ";": "semicolon", "!": "exclam", "?": "question", "(": "parenleft", ")": "parenright", "+": "plus", "_": "underscore", " ": "space"}


def glyph_name(ch):
    if ch in EXTRA:
        return EXTRA[ch]
    return ch


def main():
    f = fontforge.open(SFD)
    chars = sorted(set("abcdefghijklmnopqrstuvwxyzAEMY" + "".join(TESTS) + "&-.,'/:;!?()+_ "))
    coverage = {}
    for ch in chars:
        if ch == " ":
            coverage[ch] = "space" in f
            continue
        name = glyph_name(ch)
        coverage[ch] = name in f and f[name].unicode == ord(ch)
    bboxes = {}
    for name in sorted({glyph_name(ch) for ch in chars if ch != " "}):
        if name in f:
            g = f[name]
            bbox = g.boundingBox()
            bboxes[name] = {"bbox": list(bbox), "width": g.width, "contours": len(g.foreground), "join_y": bbox[1] <= 150 <= bbox[3]}
    f.close()
    with open(FEA, "r", encoding="utf-8") as handle:
        fea = handle.read()
    word_coverage = {text: all(ch == " " or coverage.get(ch, False) for ch in text) for text in TESTS}
    result = {
        "status": "PASSED" if all(coverage.values()) and all(word_coverage.values()) else "FAILED",
        "outputs": {"sfd": SFD, "otf": OTF, "ttf": TTF, "fea": FEA},
        "coverage": coverage,
        "word_coverage": word_coverage,
        "glyph_metrics": bboxes,
        "feature_checks": {"a_b": "sub a b by a_b;" in fea, "c_c": "sub c c by c_c;" in fea},
        "qa_checks": {"otf_opens": bool(fontforge.open(OTF)), "ttf_opens": bool(fontforge.open(TTF)), "laser_rdworks_printer_auto_started": False},
    }
    with open(RESULT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
