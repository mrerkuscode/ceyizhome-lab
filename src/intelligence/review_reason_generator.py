from __future__ import annotations

from intelligence.production_analyzer import IntelligenceFinding
from models import ValidationIssue


def build_review_reasons(
    issues: list[ValidationIssue],
    warnings: list[IntelligenceFinding],
    recommendations: list[IntelligenceFinding],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for issue in issues:
        rows.append(
            {
                "row_number": str(issue.row_number),
                "order_no": issue.order_no,
                "reason": issue.message,
                "why_it_matters": "The deterministic production engine cannot safely produce this order.",
                "what_to_fix": f"Fix the {issue.field} field in Excel.",
            }
        )

    for finding in warnings + recommendations:
        if finding.severity not in {"NEEDS_REVIEW", "WARNING"}:
            continue
        rows.append(
            {
                "row_number": str(finding.row_number),
                "order_no": finding.order_no,
                "reason": finding.message,
                "why_it_matters": _why_it_matters(finding),
                "what_to_fix": finding.suggestion,
            }
        )

    return rows


def _why_it_matters(finding: IntelligenceFinding) -> str:
    if "template" in finding.category:
        return "Wrong or ambiguous templates can create incorrect production files."
    if "laser" in finding.field:
        return "Laser output can waste material or create unsafe cut results."
    if "label" in finding.field:
        return "Printed labels may show the wrong text or color variant."
    return "The order needs human confirmation before production."
