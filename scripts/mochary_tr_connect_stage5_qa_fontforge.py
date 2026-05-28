import json
import os

import fontforge


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT = os.path.join(ROOT, "output")
SFD = os.path.join(OUTPUT, "MocharyTRConnect-Stage5.sfd")
OTF = os.path.join(OUTPUT, "MocharyTRConnect-Stage5.otf")
TTF = os.path.join(OUTPUT, "MocharyTRConnect-Stage5.ttf")
FEA = os.path.join(OUTPUT, "MocharyTRConnect-Stage5.fea")
RESULT = os.path.join(OUTPUT, "mochary_tr_connect_stage5_qa_result.json")
TESTS = ["ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ", "TÜRKÇE", "GÖRKEM", "ÇEYİZHOME", "AŞK", "YAĞMUR", "ÜMİT", "İLAYDA", "ŞULE", "ÖZGE", "Buğra", "Çağrı"]
SPECIAL = {"Ç": "Ccedilla", "Ğ": "Gcircumflex", "İ": "Idotaccent", "Ö": "Odieresis", "Ş": "Scedilla", "Ü": "Udieresis", "ç": "ccedilla", "ğ": "gcircumflex", "ı": "dotlessi", "ö": "odieresis", "ş": "scedilla", "ü": "udieresis"}


def name_for(ch):
    return SPECIAL.get(ch, ch)


def main():
    f = fontforge.open(SFD)
    chars = sorted(set("ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ" + "".join(TESTS)))
    coverage = {}
    for ch in chars:
        if ch == " ":
            continue
        name = name_for(ch)
        coverage[ch] = name in f and f[name].unicode == ord(ch)
    word_coverage = {text: all(ch == " " or coverage.get(ch, False) for ch in text) for text in TESTS}
    metrics = {}
    for ch in chars:
        if ch == " ":
            continue
        name = name_for(ch)
        if name in f:
            bbox = f[name].boundingBox()
            metrics[name] = {"bbox": list(bbox), "width": f[name].width, "contours": len(f[name].foreground)}
    f.close()
    result = {
        "status": "PASSED" if all(coverage.values()) and all(word_coverage.values()) else "FAILED",
        "outputs": {"sfd": SFD, "otf": OTF, "ttf": TTF, "fea": FEA},
        "coverage": coverage,
        "word_coverage": word_coverage,
        "metrics": metrics,
        "qa_checks": {"otf_opens": bool(fontforge.open(OTF)), "ttf_opens": bool(fontforge.open(TTF)), "laser_rdworks_printer_auto_started": False},
    }
    with open(RESULT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
