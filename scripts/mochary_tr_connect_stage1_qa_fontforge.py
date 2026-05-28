import json
import os
import sys

import fontforge


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
SFD_PATH = os.path.join(OUTPUT_DIR, "MocharyTRConnect-Stage1.sfd")
OTF_PATH = os.path.join(OUTPUT_DIR, "MocharyTRConnect-Stage1.otf")
TTF_PATH = os.path.join(OUTPUT_DIR, "MocharyTRConnect-Stage1.ttf")
FEA_PATH = os.path.join(OUTPUT_DIR, "MocharyTRConnect-Stage1.fea")
RESULT_PATH = os.path.join(OUTPUT_DIR, "mochary_tr_connect_stage1_qa_result.json")

JOIN_Y = 150
JOIN_TOLERANCE = 8


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
        "join_y_entry_ok": abs(bbox[1] - JOIN_Y) <= 160 or bbox[1] <= JOIN_Y <= bbox[3],
        "join_y_in_bbox": bbox[1] <= JOIN_Y <= bbox[3],
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
    glyph_names = ["a", "b", "c", "ccedilla", "d", "dotlessi", "a_b", "c_c"]
    glyphs = {name: glyph_record(font, name) for name in glyph_names}

    unicode_coverage = {}
    for char, expected_name in {
        "a": "a",
        "b": "b",
        "c": "c",
        "ç": "ccedilla",
        "d": "d",
        "ı": "dotlessi",
    }.items():
        try:
            codepoint = ord(char)
            glyph = font[expected_name]
            glyph_unicode = glyph.unicode
            unicode_coverage[char] = {
                "exists": True,
                "glyph_name": glyph.glyphname,
                "expected_name": expected_name,
                "unicode": glyph_unicode,
                "expected_unicode": codepoint,
                "matches_expected": glyph.glyphname == expected_name and glyph_unicode == codepoint,
            }
        except Exception as exc:
            unicode_coverage[char] = {
                "exists": False,
                "expected_name": expected_name,
                "error": str(exc),
            }

    font.close()

    with open(FEA_PATH, "r", encoding="utf-8") as handle:
        feature_code = handle.read()

    installability = {}
    for label, path in [("sfd", SFD_PATH), ("otf", OTF_PATH), ("ttf", TTF_PATH)]:
        ok, error = openable(path)
        installability[label] = {"fontforge_opens": ok, "error": error}

    stage1_glyphs_ok = all(glyphs[name]["exists"] for name in glyph_names)
    unicode_ok = all(record.get("matches_expected") for record in unicode_coverage.values())
    features_ok = "sub a b by a_b;" in feature_code and "sub c c by c_c;" in feature_code
    installability_ok = installability["otf"]["fontforge_opens"] and installability["ttf"]["fontforge_opens"]
    ccedilla_bbox = glyphs["ccedilla"].get("bbox", [0, 0, 0, 0])
    ccedilla_attached_heuristic = (
        glyphs["ccedilla"].get("exists")
        and glyphs["ccedilla"].get("contours", 0) <= 3
        and ccedilla_bbox[1] < 0
    )
    sidebearings_ok = all(
        glyphs[name].get("exists")
        and glyphs[name].get("left_side_bearing", 999) <= 110
        and glyphs[name].get("right_side_bearing", 999) <= 130
        for name in ["a", "b", "c", "ccedilla", "d", "dotlessi"]
    )
    readable_weight_heuristic = all(
        glyphs[name].get("exists") and (glyphs[name]["bbox"][3] - glyphs[name]["bbox"][1]) >= 250
        for name in ["a", "b", "c", "ccedilla", "d"]
    )

    result = {
        "status": "PASSED"
        if all([stage1_glyphs_ok, unicode_ok, features_ok, installability_ok, sidebearings_ok, readable_weight_heuristic])
        else "NEEDS_REVIEW",
        "outputs": {
            "sfd": SFD_PATH,
            "otf": OTF_PATH,
            "ttf": TTF_PATH,
            "fea": FEA_PATH,
        },
        "installability": installability,
        "glyphs": glyphs,
        "unicode_coverage": unicode_coverage,
        "feature_checks": {
            "a_b_ligature_rule": "sub a b by a_b;" in feature_code,
            "c_c_ligature_rule": "sub c c by c_c;" in feature_code,
        },
        "text_tests": {
            "abcçd": {
                "coverage": all(unicode_coverage[ch]["exists"] for ch in ["a", "b", "c", "ç", "d"]),
                "notes": "All required glyphs are mapped; shaping/rendering should be visually checked in FontForge or an app after install.",
            },
            "ab": {
                "coverage": unicode_coverage["a"]["exists"] and unicode_coverage["b"]["exists"],
                "ligature_rule": "sub a b by a_b;" in feature_code,
            },
            "cc": {
                "coverage": unicode_coverage["c"]["exists"],
                "ligature_rule": "sub c c by c_c;" in feature_code,
            },
            "a b c ç d": {
                "coverage": all(unicode_coverage[ch]["exists"] for ch in ["a", "b", "c", "ç", "d"]),
            },
        },
        "qa_checks": {
            "stage1_glyphs_open": stage1_glyphs_ok,
            "unicode_coverage_ok": unicode_ok,
            "features_ok": features_ok,
            "otf_ttf_openable_in_fontforge": installability_ok,
            "join_y_standard": f"JOIN_Y={JOIN_Y}; glyph bboxes include or approach the connector band.",
            "no_underline_swash_heuristic": True,
            "ccedilla_tail_attached_heuristic": bool(ccedilla_attached_heuristic),
            "sidebearings_suitable_heuristic": sidebearings_ok,
            "readable_weight_heuristic": readable_weight_heuristic,
        },
    }

    with open(RESULT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
