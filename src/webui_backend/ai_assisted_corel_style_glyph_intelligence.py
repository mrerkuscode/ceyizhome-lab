from __future__ import annotations

from typing import Any


TURKISH_MARK_RULES: dict[str, dict[str, Any]] = {
    "ü": {"marks": ["dot_left", "dot_right"], "owner": "self", "bridgeWidthMm": [0.20, 0.25]},
    "Ü": {"marks": ["dot_left", "dot_right"], "owner": "self", "bridgeWidthMm": [0.20, 0.25]},
    "ö": {"marks": ["dot_left", "dot_right"], "owner": "self", "bridgeWidthMm": [0.20, 0.25]},
    "Ö": {"marks": ["dot_left", "dot_right"], "owner": "self", "bridgeWidthMm": [0.20, 0.25]},
    "i": {"marks": ["dot"], "owner": "self", "bridgeWidthMm": [0.20, 0.25]},
    "İ": {"marks": ["dot"], "owner": "self", "bridgeWidthMm": [0.20, 0.25]},
    "ğ": {"marks": ["breve"], "owner": "self", "bridgeWidthMm": [0.20, 0.25]},
    "Ğ": {"marks": ["breve"], "owner": "self", "bridgeWidthMm": [0.20, 0.25]},
    "ş": {"marks": ["cedilla_tail"], "owner": "self", "bridgeWidthMm": [0.25, 0.30]},
    "Ş": {"marks": ["cedilla_tail"], "owner": "self", "bridgeWidthMm": [0.25, 0.30]},
    "ç": {"marks": ["cedilla_tail"], "owner": "self", "bridgeWidthMm": [0.25, 0.30]},
    "Ç": {"marks": ["cedilla_tail"], "owner": "self", "bridgeWidthMm": [0.25, 0.30]},
}

DOTLESS_LETTERS = set("ıI")
UNMARKED_SAFETY_LETTERS = set("SMAABCDEFGHIJKLNOPRTYZBCDEFHKLMNOPRSTVWXYZ")


def glyph_identity_for_word(word: str) -> list[dict[str, Any]]:
    glyphs: list[dict[str, Any]] = []
    for source_index, char in enumerate(str(word or "")):
        if not char.strip() or char == "&":
            continue
        rule = TURKISH_MARK_RULES.get(char, {})
        marks = list(rule.get("marks") or [])
        glyphs.append(
            {
                "index": len(glyphs),
                "sourceIndex": source_index,
                "glyph": char,
                "unicode": f"U+{ord(char):04X}",
                "type": "marked_letter" if marks else "base_letter",
                "case": "upper" if char.isupper() else "lower",
                "hasMark": bool(marks),
                "marks": marks,
                "mustBeDotless": char in DOTLESS_LETTERS,
                "forbidsExtraMark": char in DOTLESS_LETTERS or char in UNMARKED_SAFETY_LETTERS,
            }
        )
    return glyphs


def extract_corel_glyph_patterns(profile: dict[str, Any], reference_summary: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    aggregate = profile.get("styleAggregate") if isinstance(profile.get("styleAggregate"), dict) else {}
    curve_density = (aggregate.get("curveDensity") or {}).get("median") if isinstance(aggregate.get("curveDensity"), dict) else None
    closed_ratio = (aggregate.get("closedRatio") or {}).get("median") if isinstance(aggregate.get("closedRatio"), dict) else None
    source_count = int((reference_summary or {}).get("referenceCount") or 0)
    base = {
        "profileId": profile.get("id") or "mochary_user_corel_calibrated",
        "sourceReferenceCount": source_count,
        "medianCurveDensity": curve_density,
        "medianClosedRatio": closed_ratio,
        "forbiddenZones": ["inside_counter", "wrong_glyph_mark_area", "decorative_upper_loop", "between_different_name_objects"],
    }
    return [
        {
            **base,
            "patternId": "upper_initial_to_lowercase",
            "connectionType": "natural_mid_or_lower_flow",
            "bridgeWidthMm": 0.26,
            "visualQualityScore": 0.90,
        },
        {
            **base,
            "patternId": "lowercase_to_lowercase",
            "connectionType": "baseline_script_flow",
            "bridgeWidthMm": 0.25,
            "visualQualityScore": 0.91,
        },
        {
            **base,
            "patternId": "dotted_mark_bridge",
            "connectionType": "thin_smooth_mark_to_owner_body",
            "bridgeWidthMm": 0.22,
            "visualQualityScore": 0.88,
        },
        {
            **base,
            "patternId": "double_dot_bridge",
            "connectionType": "two_thin_smooth_mark_bridges_to_owner_body",
            "bridgeWidthMm": 0.22,
            "visualQualityScore": 0.88,
        },
        {
            **base,
            "patternId": "cedilla_bridge",
            "connectionType": "tail_weld_to_owner_lower_body",
            "bridgeWidthMm": 0.28,
            "visualQualityScore": 0.87,
        },
        {
            **base,
            "patternId": "breve_bridge",
            "connectionType": "thin_breve_to_owner_upper_body",
            "bridgeWidthMm": 0.22,
            "visualQualityScore": 0.86,
        },
        {
            **base,
            "patternId": "preserve_inner_counter",
            "connectionType": "forbidden_inside_counter",
            "bridgeWidthMm": 0.0,
            "visualQualityScore": 1.0,
        },
    ]


def ai_designer_connection_advice(word: str, row: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    glyphs = glyph_identity_for_word(word)
    plan = row.get("designerWeldPlan") if isinstance(row.get("designerWeldPlan"), dict) else {}
    letter_connections = plan.get("letterConnectionPlan") or plan.get("connections") or []
    mark_connections = plan.get("markBridgePlan") or plan.get("marks") or []
    return {
        "word": word,
        "fontProfile": "MocharyCorelProductionProfile",
        "aiFinalPathGenerated": False,
        "aiRole": "connection_planner_and_visual_inspector",
        "glyphIdentity": glyphs,
        "learnedPatternIds": [pattern.get("patternId") for pattern in patterns],
        "letterConnections": letter_connections,
        "markConnections": mark_connections,
        "forbiddenConnections": plan.get("forbiddenConnections") or [
            {"zone": "wrong_glyph_mark_area", "reason": "Marks cannot attach to another glyph."},
            {"zone": "inside_letter_counter", "reason": "Creates internal garbage path."},
        ],
        "decision": "apply_vector_engine",
    }


def visual_cut_inspection(row: dict[str, Any]) -> dict[str, Any]:
    score = int(row.get("aiQualityScore") or row.get("ai_quality_score") or 0)
    mark_ok = bool(row.get("markOwnershipPassed") or row.get("mark_ownership_passed"))
    glyph_ok = bool(row.get("glyphIdentityPassed") or row.get("glyph_identity_passed"))
    internal_garbage = bool(row.get("internalGarbagePath") or row.get("internal_garbage_path"))
    manufacturable = str(row.get("manufacturabilityStatus") or row.get("manufacturability_status") or "") == "manufacturable_passed"
    corel_status = str(row.get("corelReferenceCorpusStatus") or row.get("corel_reference_corpus_status") or "")
    problems: list[str] = []
    if not glyph_ok:
        problems.append("glyph_identity_failed")
    if not mark_ok:
        problems.append("mark_ownership_failed")
    if internal_garbage:
        problems.append("internal_garbage_path")
    if not manufacturable:
        problems.append("manufacturability_not_passed")
    if corel_status == "REFERENCE_MISMATCH":
        problems.append("corel_reference_mismatch")
    if score < 85:
        problems.append("visual_score_below_pass")
    status = "passed"
    if problems:
        status = "failed" if any(problem in problems for problem in ["glyph_identity_failed", "mark_ownership_failed", "internal_garbage_path"]) else "review_required"
    return {
        "visualStatus": status,
        "designerScore": score,
        "problems": problems,
        "readyForOperatorReview": True,
        "readyForCut": False,
        "aiFinalPathGenerated": False,
    }
