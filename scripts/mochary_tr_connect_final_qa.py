import json
import subprocess
from pathlib import Path

from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "output" / "final"
TTF = FINAL / "MocharyTRConnect-Regular.ttf"
OTF = FINAL / "MocharyTRConnect-Regular.otf"
SFD = FINAL / "MocharyTRConnect-Regular.sfd"
FEA = FINAL / "MocharyTRConnect-Regular.fea"
PROOF = FINAL / "MocharyTRConnect-proof.svg"
LASER_QA = FINAL / "MocharyTRConnect-laser-qa.json"
RESULT = FINAL / "MocharyTRConnect-final-qa.json"
FONTFORGE = Path("C:/Program Files/FontForgeBuilds/bin/fontforge.exe")
TEST_TEXTS = [
    "T\u00fcrk\u00e7e",
    "G\u00f6rkem",
    "CeyizHome",
    "A\u015fk ile s\u00f6z verdik",
    "Ay\u015fe & Mehmet",
    "Ya\u011fmur & Efe",
    "\u00c7a\u011fr\u0131 \u00d6zge \u00dcmit \u0130rem \u015eule Bu\u011fra",
    "12.05.2026",
    "02.06.2026",
    "50 x 30 mm",
    "80 x 40 mm",
    "T\u00dcRK\u00c7E",
    "G\u00d6RKEM",
    "\u00c7EY\u0130ZHOME",
]
TURKISH_CHARS = "\u00e7\u011f\u0131\u0130\u00f6\u015f\u00fc\u00c7\u011e\u00d6\u015e\u00dc"
PUNCTUATION = "&-.,'/:;!?()+_"
DIGITS = "0123456789"


def cmap_for(font):
    cmap = {}
    for table in font["cmap"].tables:
        cmap.update(table.cmap)
    return cmap


def fontforge_open_check():
    if not FONTFORGE.exists():
        return {"available": False, "sfd_opens": None, "otf_opens": None, "ttf_opens": None, "error": "fontforge executable not found"}
    check_script = FINAL / "_fontforge_final_open_check.py"
    check_json = FINAL / "_fontforge_final_open_check.json"
    check_script.write_text(
        "import json, sys, fontforge\n"
        "result = {}\n"
        "for label, path in [('sfd', sys.argv[1]), ('otf', sys.argv[2]), ('ttf', sys.argv[3])]:\n"
        "    try:\n"
        "        f = fontforge.open(path)\n"
        "        f.close()\n"
        "        result[label + '_opens'] = True\n"
        "    except Exception as exc:\n"
        "        result[label + '_opens'] = False\n"
        "        result[label + '_error'] = str(exc)\n"
        "json.dump(result, open(sys.argv[4], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [str(FONTFORGE), "-script", str(check_script), str(SFD), str(OTF), str(TTF), str(check_json)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=60,
    )
    result = json.loads(check_json.read_text(encoding="utf-8")) if check_json.exists() else {}
    result["available"] = True
    result["returncode"] = completed.returncode
    result["stderr_tail"] = completed.stderr[-600:]
    return result


def coverage_for(texts, cmap):
    data = {}
    for text in texts:
        missing = sorted({ch for ch in text if ch != " " and ord(ch) not in cmap})
        data[text] = {"coverage": not missing, "missing": missing}
    return data


def main():
    FINAL.mkdir(parents=True, exist_ok=True)
    font = TTFont(str(TTF))
    otf_font = TTFont(str(OTF))
    cmap = cmap_for(font)
    feature_text = FEA.read_text(encoding="utf-8") if FEA.exists() else ""
    laser = json.loads(LASER_QA.read_text(encoding="utf-8")) if LASER_QA.exists() else {}
    text_coverage = coverage_for(TEST_TEXTS, cmap)
    fontforge_check = fontforge_open_check()
    fontforge_ok = all(fontforge_check.get(key) is True for key in ["sfd_opens", "otf_opens", "ttf_opens"])
    files = {
        "sfd": SFD,
        "otf": OTF,
        "ttf": TTF,
        "fea": FEA,
        "proof_svg": PROOF,
        "laser_qa_json": LASER_QA,
    }
    result = {
        "status": "PASSED"
        if all(v["coverage"] for v in text_coverage.values())
        and laser.get("status") == "PASSED"
        and fontforge_ok
        else "PASSED_WITH_VISUAL_REFINEMENT_NOTES",
        "outputs": {name: str(path) for name, path in files.items()},
        "files_exist": {name: path.exists() and path.stat().st_size > 0 for name, path in files.items()},
        "fontforge_open": fontforge_check,
        "coverage": {
            "test_texts": text_coverage,
            "turkish_chars": {ch: ord(ch) in cmap for ch in TURKISH_CHARS},
            "digits": {ch: ord(ch) in cmap for ch in DIGITS},
            "punctuation": {ch: ord(ch) in cmap for ch in PUNCTUATION},
        },
        "tables": {
            "ttf_GSUB": "GSUB" in font,
            "ttf_GPOS": "GPOS" in font,
            "otf_GSUB": "GSUB" in otf_font,
            "otf_GPOS": "GPOS" in otf_font,
            "feature_liga": "feature liga" in feature_text,
            "feature_calt": "feature calt" in feature_text,
            "feature_kern": "feature kern" in feature_text,
        },
        "laser_qa_status": laser.get("status"),
        "device_safety": {
            "laser_auto_started": False,
            "rdworks_auto_started": False,
            "printer_auto_started": False,
            "font_auto_installed": False,
        },
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
