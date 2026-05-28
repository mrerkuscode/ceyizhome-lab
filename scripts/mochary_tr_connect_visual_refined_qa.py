from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
REFINED = ROOT / "output" / "refined"
DAY = ROOT / "output" / "2026-05-24" / "name_cut_visual_refined_font"
FONTFORGE = Path("C:/Program Files/FontForgeBuilds/bin/fontforge.exe")
SFD = REFINED / "MocharyTRConnect-VisualRefined.sfd"
OTF = REFINED / "MocharyTRConnect-VisualRefined.otf"
TTF = REFINED / "MocharyTRConnect-VisualRefined.ttf"
FEA = REFINED / "MocharyTRConnect-VisualRefined.fea"
PROOF = REFINED / "MocharyTRConnect-VisualRefined-proof.svg"
RDWORKS_SVG = REFINED / "visual-refined-rdworks-like.svg"
RDWORKS_PNG = REFINED / "visual-refined-rdworks-like.png"
RESULT = REFINED / "MocharyTRConnect-VisualRefined-QA.json"

TEST_TEXTS = [
    "Türkçe",
    "Görkem",
    "CeyizHome",
    "Aşk ile söz verdik",
    "Ayşe & Mehmet",
    "Yağmur & Efe",
    "Çağrı",
    "Özge",
    "Ümit",
    "İrem",
    "Şule",
    "Buğra",
    "Mehmet",
    "Mücahit",
    "Abdurrahman",
    "Burak Ceren Serkan",
    "12.05.2026",
]
TURKISH = "çğıİöÖşŞüÜÇĞ"
DIGITS = "0123456789"
PUNCT = "&-.,'/:;!?()+_₺€$%#@*=<>[]{}°•·"


def cmap_for(font: TTFont) -> dict[int, str]:
    cmap: dict[int, str] = {}
    for table in font["cmap"].tables:
        cmap.update(table.cmap)
    return cmap


def coverage(text: str, cmap: dict[int, str]) -> dict[str, object]:
    missing = sorted({ch for ch in text if ch != " " and ord(ch) not in cmap})
    return {"ok": not missing, "missing": missing}


def fontforge_open_check() -> dict[str, object]:
    if not FONTFORGE.exists():
        return {"available": False, "sfd_opens": None, "otf_opens": None, "ttf_opens": None}
    check_script = REFINED / "_visual_refined_fontforge_open_check.py"
    check_json = REFINED / "_visual_refined_fontforge_open_check.json"
    check_script.write_text(
        "import json, sys, fontforge\n"
        "out = {}\n"
        "for label, path in [('sfd', sys.argv[1]), ('otf', sys.argv[2]), ('ttf', sys.argv[3])]:\n"
        "    try:\n"
        "        f = fontforge.open(path)\n"
        "        f.close()\n"
        "        out[label + '_opens'] = True\n"
        "    except Exception as exc:\n"
        "        out[label + '_opens'] = False\n"
        "        out[label + '_error'] = str(exc)\n"
        "json.dump(out, open(sys.argv[4], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [str(FONTFORGE), "-script", str(check_script), str(SFD), str(OTF), str(TTF), str(check_json)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=80,
    )
    result = json.loads(check_json.read_text(encoding="utf-8")) if check_json.exists() else {}
    result["available"] = True
    result["returncode"] = completed.returncode
    result["stderr_tail"] = completed.stderr[-500:]
    return result


def non_white_ratio(path: Path) -> float:
    image = Image.open(path).convert("RGB")
    pixels = image.tobytes()
    total = len(pixels) // 3
    non_white = 0
    dark = 0
    for i in range(0, len(pixels), 3):
        r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
        if (r, g, b) != (255, 255, 255):
            non_white += 1
        if r < 90 and g < 90 and b < 90:
            dark += 1
    return round(non_white / max(total, 1), 5), round(dark / max(total, 1), 5)


def bbox_quality(font: TTFont, cmap: dict[int, str]) -> dict[str, object]:
    glyf = font["glyf"] if "glyf" in font else None
    if glyf is None:
        return {"ok": True, "notes": ["CFF/OTF bbox quality not inspected through glyf table."]}
    small = []
    huge = []
    for ch in "aemnrhkygğşçiüöTGÇY":
        name = cmap.get(ord(ch))
        if not name:
            continue
        glyph = glyf[name]
        if glyph.isComposite():
            continue
        width = getattr(glyph, "xMax", 0) - getattr(glyph, "xMin", 0)
        height = getattr(glyph, "yMax", 0) - getattr(glyph, "yMin", 0)
        if height and height < 240:
            small.append({"char": ch, "height": height})
        if width > 1150:
            huge.append({"char": ch, "width": width})
    return {"ok": not small and not huge, "small_bbox": small, "huge_bbox": huge}


def main() -> None:
    REFINED.mkdir(parents=True, exist_ok=True)
    font = TTFont(str(TTF))
    otf = TTFont(str(OTF))
    cmap = cmap_for(font)
    fea = FEA.read_text(encoding="utf-8") if FEA.exists() else ""
    proof_svg = PROOF.read_text(encoding="utf-8") if PROOF.exists() else ""
    rdworks_svg = RDWORKS_SVG.read_text(encoding="utf-8") if RDWORKS_SVG.exists() else ""
    overview_ratio, overview_dark = non_white_ratio(DAY / "refined-proof-overview.png")
    rdworks_ratio, rdworks_dark = non_white_ratio(RDWORKS_PNG)
    turkish_ratio, turkish_dark = non_white_ratio(DAY / "refined-turkish-characters.png")
    fontforge_check = fontforge_open_check()
    ff_ok = all(fontforge_check.get(k) is True for k in ("sfd_opens", "otf_opens", "ttf_opens"))
    coverage_map = {text: coverage(text, cmap) for text in TEST_TEXTS}
    required_ok = all(item["ok"] for item in coverage_map.values())
    turkish_ok = all(ord(ch) in cmap for ch in TURKISH)
    digit_ok = all(ord(ch) in cmap for ch in DIGITS)
    punct_ok = all(ord(ch) in cmap for ch in PUNCT)
    bbox = bbox_quality(font, cmap)
    svg_ok = (
        "<text" not in proof_svg.lower()
        and "<text" not in rdworks_svg.lower()
        and proof_svg.count("<path") > 100
        and rdworks_svg.count("<path") > 45
    )
    visual_ok = overview_ratio > 0.008 and rdworks_ratio > 0.006 and turkish_ratio > 0.006 and overview_dark > 0.001
    tables_ok = "GSUB" in font and "GPOS" in font and "GSUB" in otf and "feature liga" in fea and "feature calt" in fea and "feature kern" in fea
    status = "PASSED" if all([ff_ok, required_ok, turkish_ok, digit_ok, punct_ok, svg_ok, visual_ok, tables_ok]) else "VISUAL_REFINEMENT_REQUIRED"
    result = {
        "status": status,
        "outputs": {
            "sfd": str(SFD),
            "otf": str(OTF),
            "ttf": str(TTF),
            "fea": str(FEA),
            "proof_svg": str(PROOF),
            "rdworks_svg": str(RDWORKS_SVG),
            "rdworks_png": str(RDWORKS_PNG),
        },
        "files_exist": {str(path): path.exists() and path.stat().st_size > 0 for path in [SFD, OTF, TTF, FEA, PROOF, RDWORKS_SVG, RDWORKS_PNG]},
        "fontforge_open": fontforge_check,
        "coverage": {
            "test_texts": coverage_map,
            "turkish": {ch: ord(ch) in cmap for ch in TURKISH},
            "digits": {ch: ord(ch) in cmap for ch in DIGITS},
            "punctuation": {ch: ord(ch) in cmap for ch in PUNCT},
        },
        "tables": {
            "ttf_GSUB": "GSUB" in font,
            "ttf_GPOS": "GPOS" in font,
            "otf_GSUB": "GSUB" in otf,
            "feature_liga": "feature liga" in fea,
            "feature_calt": "feature calt" in fea,
            "feature_kern": "feature kern" in fea,
        },
        "visual_heuristics": {
            "overview_non_white_ratio": overview_ratio,
            "overview_dark_ratio": overview_dark,
            "rdworks_non_white_ratio": rdworks_ratio,
            "rdworks_dark_ratio": rdworks_dark,
            "turkish_non_white_ratio": turkish_ratio,
            "turkish_dark_ratio": turkish_dark,
            "svg_path_only": svg_ok,
            "bbox_quality": bbox,
        },
        "device_safety": {
            "laser_auto_started": False,
            "rdworks_auto_started": False,
            "printer_auto_started": False,
            "font_auto_installed": False,
        },
        "notes": [
            "Visual Refined is intentionally a separate selectable font; existing default is unchanged.",
            "Human visual sign-off is still recommended before making it the production default.",
        ],
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if status != "PASSED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
