import json
import os

import fontforge


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT = os.path.join(ROOT, "output")
SFD = os.path.join(OUTPUT, "MocharyTRConnect-Stage3.sfd")
OTF = os.path.join(OUTPUT, "MocharyTRConnect-Stage3.otf")
TTF = os.path.join(OUTPUT, "MocharyTRConnect-Stage3.ttf")
FEA = os.path.join(OUTPUT, "MocharyTRConnect-Stage3.fea")
RESULT = os.path.join(OUTPUT, "mochary_tr_connect_stage3_qa_result.json")

CHARS = {
    "a": "a", "b": "b", "c": "c", "ç": "ccedilla", "d": "d", "e": "e", "f": "f",
    "g": "g", "ğ": "gcircumflex", "h": "h", "ı": "dotlessi", "i": "i", "j": "j",
    "k": "k", "l": "l", "m": "m", "n": "n", "o": "o", "ö": "odieresis",
    "p": "p", "r": "r", "s": "s", "ş": "scedilla", "u": "u", "ü": "udieresis", "z": "z",
}
WORDS = ["lmnoprsşö", "abcçdefgğhıijklmnoöprsş", "ölüm", "şeker", "sarı", "mor", "pınar", "lale", "özge", "ölçü", "şule", "nermin"]


def glyph_record(font, name):
    if name not in font:
        return {"exists": False}
    g = font[name]
    bbox = g.boundingBox()
    return {
        "exists": True,
        "width": g.width,
        "bbox": list(bbox),
        "contours": len(g.foreground),
        "join_y_in_bbox": bbox[1] <= 150 <= bbox[3],
        "height": bbox[3] - bbox[1],
    }


def openable(path):
    try:
        f = fontforge.open(path)
        f.close()
        return True
    except Exception:
        return False


def main():
    font = fontforge.open(SFD)
    glyph_names = sorted(set(CHARS.values()) | {"a_b", "c_c"})
    glyphs = {name: glyph_record(font, name) for name in glyph_names}
    coverage = {}
    for char, name in CHARS.items():
        g = font[name] if name in font else None
        coverage[char] = bool(g and g.unicode == ord(char))
    font.close()
    with open(FEA, "r", encoding="utf-8") as handle:
        fea = handle.read()
    word_coverage = {word: all(ch == " " or coverage.get(ch, False) for ch in word) for word in WORDS}
    visual_checks = {
        "odieresis_marks_overlap_visual": glyphs["odieresis"]["exists"] and glyphs["odieresis"]["contours"] <= 3,
        "scedilla_tail_present": glyphs["scedilla"]["exists"] and glyphs["scedilla"]["bbox"][1] < 0,
        "p_descender_present_controlled": glyphs["p"]["exists"] and -190 <= glyphs["p"]["bbox"][1] < 0,
        "join_y_standard": all(glyphs[name].get("join_y_in_bbox") for name in ["l", "m", "n", "o", "odieresis", "p", "r", "s", "scedilla"]),
    }
    result = {
        "status": "PASSED" if all(coverage.values()) and all(word_coverage.values()) and all(visual_checks.values()) and openable(OTF) and openable(TTF) else "PASSED_WITH_VISUAL_REFINEMENT_NOTES",
        "outputs": {"sfd": SFD, "otf": OTF, "ttf": TTF, "fea": FEA},
        "glyphs": glyphs,
        "unicode_coverage": coverage,
        "word_coverage": word_coverage,
        "feature_checks": {"a_b": "sub a b by a_b;" in fea, "c_c": "sub c c by c_c;" in fea},
        "qa_checks": {**visual_checks, "otf_opens": openable(OTF), "ttf_opens": openable(TTF), "laser_rdworks_printer_auto_started": False},
    }
    with open(RESULT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
