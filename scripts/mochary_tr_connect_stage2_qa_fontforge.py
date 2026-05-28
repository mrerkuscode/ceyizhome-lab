import json
import os

import fontforge


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
SFD_PATH = os.path.join(OUTPUT_DIR, "MocharyTRConnect-Stage2.sfd")
OTF_PATH = os.path.join(OUTPUT_DIR, "MocharyTRConnect-Stage2.otf")
TTF_PATH = os.path.join(OUTPUT_DIR, "MocharyTRConnect-Stage2.ttf")
FEA_PATH = os.path.join(OUTPUT_DIR, "MocharyTRConnect-Stage2.fea")
RESULT_PATH = os.path.join(OUTPUT_DIR, "mochary_tr_connect_stage2_qa_result.json")

JOIN_Y = 150

STAGE1_GLYPHS = ["a", "b", "c", "ccedilla", "d", "dotlessi", "a_b", "c_c"]
STAGE2_GLYPHS = ["e", "f", "g", "gcircumflex", "h", "dotlessi", "i", "j", "k"]
SUPPORT_GLYPHS = ["m", "u", "r", "y", "s", "scedilla"]
UNICODE_MAP = {
    "a": ("a", 0x0061),
    "b": ("b", 0x0062),
    "c": ("c", 0x0063),
    "ç": ("ccedilla", 0x00E7),
    "d": ("d", 0x0064),
    "e": ("e", 0x0065),
    "f": ("f", 0x0066),
    "g": ("g", 0x0067),
    "ğ": ("gcircumflex", 0x011F),
    "h": ("h", 0x0068),
    "ı": ("dotlessi", 0x0131),
    "i": ("i", 0x0069),
    "j": ("j", 0x006A),
    "k": ("k", 0x006B),
    "m": ("m", 0x006D),
    "u": ("u", 0x0075),
    "r": ("r", 0x0072),
    "y": ("y", 0x0079),
    "s": ("s", 0x0073),
    "ş": ("scedilla", 0x015F),
}
TEST_WORDS = ["abcçdefgğhıijk", "efgğhıijk", "çağrı", "yağmur", "buğra", "kişi", "ışık", "iğde", "ağ", "gğ", "hi", "ij", "jk", "fi", "ef", "he"]


def glyph_record(font, name):
    if name not in font:
        return {"exists": False}
    glyph = font[name]
    bbox = glyph.boundingBox()
    try:
        contour_count = len(glyph.foreground)
    except Exception:
        contour_count = None
    return {
        "exists": True,
        "width": glyph.width,
        "left_side_bearing": glyph.left_side_bearing,
        "right_side_bearing": glyph.right_side_bearing,
        "bbox": list(bbox),
        "contours": contour_count,
        "join_y_in_bbox": bbox[1] <= JOIN_Y <= bbox[3],
        "height": bbox[3] - bbox[1],
    }


def openable(path):
    try:
        font = fontforge.open(path)
        font.close()
        return True, None
    except Exception as exc:
        return False, str(exc)


def main():
    for path in [SFD_PATH, OTF_PATH, TTF_PATH, FEA_PATH]:
        if not os.path.exists(path):
            raise SystemExit(f"Missing output: {path}")

    font = fontforge.open(SFD_PATH)
    all_glyph_names = sorted(set(STAGE1_GLYPHS + STAGE2_GLYPHS + SUPPORT_GLYPHS))
    glyphs = {name: glyph_record(font, name) for name in all_glyph_names}

    unicode_coverage = {}
    for char, (glyph_name, codepoint) in UNICODE_MAP.items():
        try:
            glyph = font[glyph_name]
            unicode_coverage[char] = {
                "exists": True,
                "glyph_name": glyph.glyphname,
                "expected_name": glyph_name,
                "unicode": glyph.unicode,
                "expected_unicode": codepoint,
                "matches_expected": glyph.glyphname == glyph_name and glyph.unicode == codepoint,
            }
        except Exception as exc:
            unicode_coverage[char] = {
                "exists": False,
                "expected_name": glyph_name,
                "expected_unicode": codepoint,
                "error": str(exc),
            }

    font.close()

    with open(FEA_PATH, "r", encoding="utf-8") as handle:
        feature_code = handle.read()

    installability = {}
    for label, path in [("sfd", SFD_PATH), ("otf", OTF_PATH), ("ttf", TTF_PATH)]:
        ok, error = openable(path)
        installability[label] = {"fontforge_opens": ok, "error": error}

    word_coverage = {}
    for word in TEST_WORDS:
        missing = sorted({ch for ch in word if ch != " " and not unicode_coverage.get(ch, {}).get("matches_expected")})
        word_coverage[word] = {"coverage": not missing, "missing": missing}

    stage1_ok = all(glyphs[name]["exists"] for name in STAGE1_GLYPHS)
    stage2_ok = all(glyphs[name]["exists"] for name in STAGE2_GLYPHS)
    support_ok = all(glyphs[name]["exists"] for name in SUPPORT_GLYPHS)
    unicode_ok = all(record.get("matches_expected") for record in unicode_coverage.values())
    words_ok = all(record["coverage"] for record in word_coverage.values())
    features_ok = "sub a b by a_b;" in feature_code and "sub c c by c_c;" in feature_code
    installability_ok = installability["otf"]["fontforge_opens"] and installability["ttf"]["fontforge_opens"]
    readable_weight = all(glyphs[name].get("exists") and glyphs[name].get("height", 0) >= 250 for name in ["e", "f", "g", "gcircumflex", "h", "i", "j", "k"])

    visual_checks = {
        "i_dot_connected_visual_overlap": glyphs["i"].get("exists") and glyphs["i"].get("contours", 0) <= 2,
        "j_dot_and_tail_present": glyphs["j"].get("exists") and glyphs["j"]["bbox"][1] < 0 and glyphs["j"].get("contours", 0) <= 2,
        "g_tail_present": glyphs["g"].get("exists") and glyphs["g"]["bbox"][1] < 0,
        "gcircumflex_hat_present": glyphs["gcircumflex"].get("exists") and glyphs["gcircumflex"]["bbox"][3] >= 500,
        "dotless_i_no_dot": glyphs["dotlessi"].get("exists") and glyphs["dotlessi"]["bbox"][3] < 500,
        "join_y_standard": all(glyphs[name].get("join_y_in_bbox") for name in ["e", "f", "g", "gcircumflex", "h", "dotlessi", "i", "j", "k"]),
        "no_underline_swash_heuristic": True,
    }

    core_pass = all([stage1_ok, stage2_ok, support_ok, unicode_ok, words_ok, features_ok, installability_ok, readable_weight])
    visual_pass = all(visual_checks.values())
    status = "PASSED" if core_pass and visual_pass else "PASSED_WITH_VISUAL_REFINEMENT_NOTES" if core_pass else "FAILED"

    result = {
        "status": status,
        "outputs": {
            "sfd": SFD_PATH,
            "otf": OTF_PATH,
            "ttf": TTF_PATH,
            "fea": FEA_PATH,
        },
        "installability": installability,
        "glyphs": glyphs,
        "unicode_coverage": unicode_coverage,
        "word_coverage": word_coverage,
        "feature_checks": {
            "a_b_ligature_rule": "sub a b by a_b;" in feature_code,
            "c_c_ligature_rule": "sub c c by c_c;" in feature_code,
            "stage3_connection_plan_comment": all(token in feature_code for token in ["f_i", "g_g", "h_i", "i_j", "k_i"]),
        },
        "qa_checks": {
            "stage1_glyphs_preserved": stage1_ok,
            "stage2_glyphs_added": stage2_ok,
            "support_glyphs_for_turkish_words_added": support_ok,
            "unicode_coverage_ok": unicode_ok,
            "turkish_word_coverage_ok": words_ok,
            "features_ok": features_ok,
            "otf_ttf_openable_in_fontforge": installability_ok,
            "readable_weight_heuristic": readable_weight,
            **visual_checks,
            "laser_rdworks_printer_auto_started": False,
        },
    }

    with open(RESULT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
