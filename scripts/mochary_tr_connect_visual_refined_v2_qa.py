from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
REFINED = ROOT / "output" / "refined_v2"
DAY = ROOT / "output" / "2026-05-24" / "name_cut_visual_refined_v2"
FONTFORGE = Path("C:/Program Files/FontForgeBuilds/bin/fontforge.exe")
SFD = REFINED / "MocharyTRConnect-VisualRefinedV2.sfd"
OTF = REFINED / "MocharyTRConnect-VisualRefinedV2.otf"
TTF = REFINED / "MocharyTRConnect-VisualRefinedV2.ttf"
FEA = REFINED / "MocharyTRConnect-VisualRefinedV2.fea"
PROOF = REFINED / "MocharyTRConnect-VisualRefinedV2-proof.svg"
RDWORKS_SVG = REFINED / "visual-refined-v2-rdworks-like.svg"
RDWORKS_PNG = REFINED / "visual-refined-v2-rdworks-like.png"
RESULT = REFINED / "MocharyTRConnect-VisualRefinedV2-QA.json"
PROOF_SCRIPT = ROOT / "production-bot" / "scripts" / "mochary_tr_connect_visual_refined_v2_proof.py"
APP_JS = ROOT / "production-bot" / "src" / "webui" / "app.js"
BACKEND = ROOT / "production-bot" / "src" / "webui_backend" / "combined_production_api.py"

REQUIRED_TEXTS = [
    "Türkçe",
    "Görkem",
    "ÇeyizHome",
    "Aşk ile söz verdik",
    "Ayşe & Mehmet",
    "Yağmur & Efe",
    "Çağrı",
    "Özge",
    "Ümit",
    "İrem",
    "Şule",
    "Buğra",
    "Mücahit",
    "Abdurrahman",
    "Kişi",
    "Işık",
]
FORBIDDEN_ASCII_FALLBACKS = [
    "Turkce",
    "Gorkem",
    "Ayse",
    "Yagmur",
    "Cagri",
    "Ozge",
    "Umit",
    "Irem",
    "Sule",
    "Bugra",
]
TURKISH_CHARS = "çÇğĞıİöÖşŞüÜ"


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
    check_script = REFINED / "_visual_refined_v2_fontforge_open_check.py"
    check_json = REFINED / "_visual_refined_v2_fontforge_open_check.json"
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


def image_ratios(path: Path) -> dict[str, float]:
    image = Image.open(path).convert("RGB")
    pixels = image.tobytes()
    total = max(len(pixels) // 3, 1)
    non_white = 0
    dark = 0
    for i in range(0, len(pixels), 3):
        r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
        if (r, g, b) != (255, 255, 255):
            non_white += 1
        if r < 90 and g < 90 and b < 90:
            dark += 1
    return {"non_white_ratio": round(non_white / total, 5), "dark_ratio": round(dark / total, 5)}


def proof_source_check() -> dict[str, object]:
    source = PROOF_SCRIPT.read_text(encoding="utf-8")
    required = {text: text in source for text in REQUIRED_TEXTS}
    forbidden = {text: text in source for text in FORBIDDEN_ASCII_FALLBACKS}
    return {
        "required_unicode_present": required,
        "forbidden_ascii_present": forbidden,
        "ok": all(required.values()) and not any(forbidden.values()),
    }


def svg_check(path: Path) -> dict[str, object]:
    content = path.read_text(encoding="utf-8")
    return {
        "exists": path.exists() and path.stat().st_size > 0,
        "path_count": content.count("<path"),
        "text_element": bool(re.search(r"<\s*text\b", content, flags=re.IGNORECASE)),
        "viewbox_present": "viewBox=" in content,
        "required_texts_in_metadata": {text: text in content for text in REQUIRED_TEXTS if text in {"Türkçe", "Görkem", "Ayşe & Mehmet", "Yağmur & Efe"}},
        "name_group_count": len(re.findall(r'<g id="name-\d+', content)),
        "sample_group_count": len(re.findall(r'<g id="sample-\d+', content)),
    }


def bbox_quality(font: TTFont, cmap: dict[int, str]) -> dict[str, object]:
    if "glyf" not in font:
        return {"ok": True, "notes": ["CFF/OTF bbox quality not inspected through glyf table."]}
    glyf = font["glyf"]
    small = []
    huge = []
    for ch in "aeygğmnrşsçüöihktTGÇYMAŞÜÖİ":
        name = cmap.get(ord(ch))
        if not name:
            small.append({"char": ch, "reason": "missing"})
            continue
        glyph = glyf[name]
        if glyph.isComposite():
            continue
        width = getattr(glyph, "xMax", 0) - getattr(glyph, "xMin", 0)
        height = getattr(glyph, "yMax", 0) - getattr(glyph, "yMin", 0)
        if height and height < 220:
            small.append({"char": ch, "height": height})
        if width > 1250:
            huge.append({"char": ch, "width": width})
    return {"ok": not small and not huge, "small_bbox": small, "huge_bbox": huge}


def main() -> None:
    REFINED.mkdir(parents=True, exist_ok=True)
    font = TTFont(str(TTF))
    otf = TTFont(str(OTF))
    cmap = cmap_for(font)
    fea = FEA.read_text(encoding="utf-8") if FEA.exists() else ""
    app_js = APP_JS.read_text(encoding="utf-8")
    backend = BACKEND.read_text(encoding="utf-8")
    source = proof_source_check()
    proof_svg = svg_check(PROOF)
    rdworks_svg = svg_check(RDWORKS_SVG)
    turkish_svg = svg_check(DAY / "refined-v2-turkish-characters.svg")
    burak_svg = svg_check(DAY / "refined-v2-burak-ceren-serkan.svg")
    ratios = {
        "overview": image_ratios(DAY / "refined-v2-proof-overview.png"),
        "turkish": image_ratios(DAY / "refined-v2-turkish-characters.png"),
        "rdworks": image_ratios(RDWORKS_PNG),
        "burak_ceren_serkan": image_ratios(DAY / "refined-v2-burak-ceren-serkan.png"),
    }
    fontforge_check = fontforge_open_check()
    ff_ok = all(fontforge_check.get(k) is True for k in ("sfd_opens", "otf_opens", "ttf_opens"))
    coverage_map = {text: coverage(text, cmap) for text in REQUIRED_TEXTS}
    turkish_ok = all(ord(ch) in cmap for ch in TURKISH_CHARS)
    tables_ok = "GSUB" in font and "GPOS" in font and "GSUB" in otf and all(token in fea for token in ("feature liga", "feature calt", "feature kern"))
    selector_ok = "MocharyTRConnectVisualRefinedV2-Regular" in app_js and "Mochary TR Connect Visual Refined V2" in app_js
    backend_ok = "mochary_tr_connect_visual_refined_v2" in backend and "MocharyTRConnectVisualRefinedV2-Regular" in backend
    svg_ok = (
        proof_svg["path_count"] > 80
        and rdworks_svg["path_count"] > 100
        and turkish_svg["path_count"] > 20
        and burak_svg["sample_group_count"] == 3
        and rdworks_svg["name_group_count"] >= 40
        and not proof_svg["text_element"]
        and not rdworks_svg["text_element"]
        and not turkish_svg["text_element"]
        and not burak_svg["text_element"]
    )
    visual_ok = (
        ratios["overview"]["non_white_ratio"] > 0.008
        and ratios["overview"]["dark_ratio"] > 0.001
        and ratios["turkish"]["non_white_ratio"] > 0.006
        and ratios["rdworks"]["non_white_ratio"] > 0.006
        and ratios["burak_ceren_serkan"]["non_white_ratio"] > 0.006
    )
    bbox = bbox_quality(font, cmap)
    status = "PASSED" if all([
        ff_ok,
        source["ok"],
        all(item["ok"] for item in coverage_map.values()),
        turkish_ok,
        tables_ok,
        selector_ok,
        backend_ok,
        svg_ok,
        visual_ok,
        bbox["ok"],
    ]) else "VISUAL_REFINEMENT_REQUIRED"
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
        "proof_source": source,
        "coverage": {
            "required_texts": coverage_map,
            "turkish_chars": {ch: ord(ch) in cmap for ch in TURKISH_CHARS},
        },
        "tables": {
            "ttf_GSUB": "GSUB" in font,
            "ttf_GPOS": "GPOS" in font,
            "otf_GSUB": "GSUB" in otf,
            "feature_liga": "feature liga" in fea,
            "feature_calt": "feature calt" in fea,
            "feature_kern": "feature kern" in fea,
        },
        "selector": {"app_js": selector_ok, "backend": backend_ok, "default_changed": "font_family: \"MocharyTRConnectVisualRefinedV2-Regular\"" in app_js},
        "svg": {"overview": proof_svg, "rdworks": rdworks_svg, "turkish": turkish_svg, "burak_ceren_serkan": burak_svg},
        "visual_heuristics": {**ratios, "bbox_quality": bbox},
        "device_safety": {
            "laser_auto_started": False,
            "rdworks_auto_started": False,
            "printer_auto_started": False,
            "font_auto_installed": False,
        },
        "notes": [
            "Visual Refined V2 is a selectable test font only; the default remains MocharyTRConnect-Regular.",
            "Human visual sign-off is still recommended before making V2 the production default.",
        ],
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if status != "PASSED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
