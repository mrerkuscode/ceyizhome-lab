from __future__ import annotations

from typing import Any


TURKISH_MARK_RULES: dict[str, dict[str, Any]] = {
    "ü": {"marks": ["dot_left", "dot_right"], "bridgeWidthMm": 0.22, "owner": "self"},
    "Ü": {"marks": ["dot_left", "dot_right"], "bridgeWidthMm": 0.22, "owner": "self"},
    "ö": {"marks": ["dot_left", "dot_right"], "bridgeWidthMm": 0.22, "owner": "self"},
    "Ö": {"marks": ["dot_left", "dot_right"], "bridgeWidthMm": 0.22, "owner": "self"},
    "i": {"marks": ["dot"], "bridgeWidthMm": 0.22, "owner": "self"},
    "İ": {"marks": ["dot"], "bridgeWidthMm": 0.22, "owner": "self"},
    "ğ": {"marks": ["breve"], "bridgeWidthMm": 0.22, "owner": "self"},
    "Ğ": {"marks": ["breve"], "bridgeWidthMm": 0.22, "owner": "self"},
    "ş": {"marks": ["cedilla_tail"], "bridgeWidthMm": 0.28, "owner": "self"},
    "Ş": {"marks": ["cedilla_tail"], "bridgeWidthMm": 0.28, "owner": "self"},
    "ç": {"marks": ["cedilla_tail"], "bridgeWidthMm": 0.28, "owner": "self"},
    "Ç": {"marks": ["cedilla_tail"], "bridgeWidthMm": 0.28, "owner": "self"},
}

DOTLESS_LETTERS = {"ı", "I"}
UNMARKED_SAFETY_LETTERS = set("SMAABCDEFGHKLMNOPRSTUVYZBCDEFHIJKLMNOPQRSTUVWXYZ")


def glyph_identity_parser(word: str) -> list[dict[str, Any]]:
    glyphs: list[dict[str, Any]] = []
    for source_index, glyph in enumerate(str(word or "")):
        if not glyph.strip() or glyph == "&":
            continue
        rule = TURKISH_MARK_RULES.get(glyph) or {}
        marks = list(rule.get("marks") or [])
        glyphs.append(
            {
                "index": len(glyphs),
                "sourceIndex": source_index,
                "glyph": glyph,
                "unicode": f"U+{ord(glyph):04X}",
                "type": "marked_letter" if marks else "base_letter",
                "case": "upper" if glyph.isupper() else "lower",
                "hasMark": bool(marks),
                "marks": marks,
                "mustBeDotless": glyph in DOTLESS_LETTERS,
                "forbidsExtraMark": glyph in DOTLESS_LETTERS or glyph in UNMARKED_SAFETY_LETTERS,
            }
        )
    return glyphs


def build_internal_engine_blueprint(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or {}
    bridge_rules = profile.get("bridgeRules") if isinstance(profile.get("bridgeRules"), dict) else {}
    return {
        "engineId": "internal_corel_like_vector_name_cut_engine",
        "font": profile.get("font") or "Mochary.ttf",
        "corelRuntimeUsed": False,
        "aiFinalPathGenerated": False,
        "targetNameWidthMm": profile.get("targetNameWidthMm", 80),
        "targetNameHeightMm": profile.get("targetNameHeightMm", 40),
        "defaultOffsetMm": profile.get("defaultOffsetMm", 0.3),
        "dotBridgeMm": bridge_rules.get("dotBridgeMm", [0.2, 0.25]),
        "tailBridgeMm": bridge_rules.get("tailBridgeMm", [0.25, 0.3]),
        "upperMarkBridgeMm": bridge_rules.get("upperMarkBridgeMm", [0.2, 0.25]),
        "letterConnectionBridgeMm": bridge_rules.get("letterConnectionBridgeMm", [0.25, 0.3]),
        "forbiddenZones": [
            "inside_counter",
            "wrong_glyph_mark_area",
            "decorative_upper_loop",
            "between_different_name_objects",
            "dotless_letter_mark_area",
        ],
    }


def ai_designer_advisor_plan(word: str, row: dict[str, Any], blueprint: dict[str, Any]) -> dict[str, Any]:
    glyphs = glyph_identity_parser(word)
    existing_plan = row.get("designerWeldPlan") if isinstance(row.get("designerWeldPlan"), dict) else {}
    letter_connections = list(existing_plan.get("letterConnectionPlan") or existing_plan.get("connections") or [])
    mark_connections = list(existing_plan.get("markBridgePlan") or existing_plan.get("marks") or [])
    if not letter_connections:
        for left, right in zip(glyphs, glyphs[1:]):
            letter_connections.append(
                {
                    "pair": f"{left['glyph']}:{right['glyph']}",
                    "rule": "natural_mid_or_lower_script_flow" if left["index"] == 0 else "baseline_script_flow",
                    "connectorWidthMm": blueprint.get("letterConnectionBridgeMm", [0.25, 0.3])[0],
                    "avoidZones": ["inside_counter", "decorative_upper_loop", "wrong_glyph_mark_area"],
                }
            )
    if not mark_connections:
        for glyph in glyphs:
            for mark in glyph.get("marks") or []:
                rule = TURKISH_MARK_RULES.get(str(glyph.get("glyph"))) or {}
                mark_connections.append(
                    {
                        "glyph": glyph.get("glyph"),
                        "mark": mark,
                        "connectTo": f"{glyph.get('glyph')}_main_body",
                        "bridgeWidthMm": rule.get("bridgeWidthMm", 0.22),
                        "avoidBlob": True,
                    }
                )
    return {
        "word": word,
        "fontProfile": "MocharyInternalProductionProfile",
        "aiRole": "designer_advisor_only",
        "aiFinalPathGenerated": False,
        "glyphIdentity": glyphs,
        "letterConnections": letter_connections,
        "markConnections": mark_connections,
        "forbiddenConnections": [
            {"zone": zone, "reason": "Vector engine must not place bridge geometry in this area."}
            for zone in blueprint.get("forbiddenZones", [])
        ],
        "decision": "apply_internal_vector_engine",
    }


def internal_visual_cut_inspection(row: dict[str, Any]) -> dict[str, Any]:
    score = int(row.get("aiQualityScore") or row.get("ai_quality_score") or 0)
    glyph_ok = bool(row.get("glyphIdentityPassed") or row.get("glyph_identity_passed"))
    mark_ok = bool(row.get("markOwnershipPassed") or row.get("mark_ownership_passed"))
    path_only = bool(row.get("pathOnlyExportPassed") or row.get("path_only_export_passed"))
    canvas_export = bool(row.get("canvasExportConsistencyPassed") or row.get("canvas_export_consistency_passed"))
    manufacturable = str(row.get("manufacturabilityStatus") or row.get("manufacturability_status") or "") == "manufacturable_passed"
    internal_garbage = bool(row.get("internalGarbagePath") or row.get("internal_garbage_path"))
    bridge_errors = list(row.get("markBridgeValidationErrors") or row.get("mark_bridge_validation_errors") or [])
    if not bridge_errors:
        bridge_error_prefixes = {
            "detached_dot",
            "detached_breve",
            "detached_cedilla",
            "bridge_too_long",
            "bridge_crosses_other_glyph",
            "bridge_attached_to_wrong_glyph",
            "bridge_visual_line_artifact",
            "mark_blob_risk",
            "mark_not_connected_to_owner_body",
        }
        bridge_errors = [
            str(warning)
            for warning in list(row.get("designerMarkBridgeWarnings") or row.get("designer_mark_bridge_warnings") or [])
            if str(warning).split(":", 1)[0] in bridge_error_prefixes
        ]
    problems: list[str] = []
    if not glyph_ok:
        problems.append("glyph_identity_failed")
    if not mark_ok:
        problems.append("mark_ownership_failed")
    if internal_garbage:
        problems.append("internal_garbage_path")
    if not manufacturable:
        problems.append("manufacturability_not_passed")
    if not path_only:
        problems.append("path_only_not_verified")
    if not canvas_export:
        problems.append("canvas_export_mismatch")
    problems.extend(str(error) for error in bridge_errors)
    if score < 80:
        problems.append("visual_score_review_required")
    visual_status = "passed" if not problems and score >= 85 else "review_required"
    if any(problem in problems for problem in ["glyph_identity_failed", "mark_ownership_failed", "internal_garbage_path", "canvas_export_mismatch"]) or bridge_errors:
        visual_status = "failed"
    return {
        "visualStatus": visual_status,
        "designerScore": score,
        "problems": problems,
        "readyForOperatorReview": True,
        "readyForCut": False,
        "aiFinalPathGenerated": False,
    }
