import json
import os

import fontforge


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT = os.path.join(ROOT, "output")
SFD = os.path.join(OUTPUT, "MocharyTRConnect-Stage6.sfd")
OTF = os.path.join(OUTPUT, "MocharyTRConnect-Stage6.otf")
TTF = os.path.join(OUTPUT, "MocharyTRConnect-Stage6.ttf")
RESULT = os.path.join(OUTPUT, "mochary_tr_connect_stage6_qa_result.json")
TESTS = ["0123456789", "12.05.2026", "02.06.2026", "50 x 30 mm", "80 x 40 mm", "₺100", "%50", "Ayşe & Mehmet 12.05.2026", "Yağmur & Efe 02.06.2026"]
SPECIAL = {"₺": "uni20BA", "€": "Euro", "$": "dollar", "%": "percent", "#": "numbersign", "@": "at", "*": "asterisk", "=": "equal", "<": "less", ">": "greater", "[": "bracketleft", "]": "bracketright", "{": "braceleft", "}": "braceright", "°": "degree", "•": "bullet", "·": "periodcentered", "♥": "heart", "★": "star", "&": "ampersand", ".": "period", " ": "space", "ç": "ccedilla", "ğ": "gcircumflex", "ş": "scedilla"}


def name_for(ch):
    return SPECIAL.get(ch, ch)


def main():
    f = fontforge.open(SFD)
    chars = sorted(set("".join(TESTS) + "€$#@*=<>[]{}°•·♥★"))
    coverage = {}
    for ch in chars:
        name = name_for(ch)
        coverage[ch] = name in f and (ch == " " or f[name].unicode == ord(ch))
    word_coverage = {text: all(coverage.get(ch, False) for ch in text) for text in TESTS}
    f.close()
    result = {
        "status": "PASSED" if all(coverage.values()) and all(word_coverage.values()) else "FAILED",
        "outputs": {"sfd": SFD, "otf": OTF, "ttf": TTF},
        "coverage": coverage,
        "word_coverage": word_coverage,
        "qa_checks": {"otf_opens": bool(fontforge.open(OTF)), "ttf_opens": bool(fontforge.open(TTF)), "laser_rdworks_printer_auto_started": False},
    }
    with open(RESULT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
