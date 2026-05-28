from __future__ import annotations

from models import BOTH, LASER_CUT, PRINT, Order, ValidationIssue
from intelligence.production_analyzer import IntelligenceFinding


def build_smart_warnings(
    valid_orders: list[Order],
    issues: list[ValidationIssue],
    findings: list[IntelligenceFinding],
) -> list[IntelligenceFinding]:
    warnings: list[IntelligenceFinding] = []

    for issue in issues:
        warnings.append(
            IntelligenceFinding(
                row_number=issue.row_number,
                order_no=issue.order_no,
                severity="NEEDS_REVIEW",
                category="deterministic_rule",
                field=issue.field,
                message=_friendly_issue_message(issue.message),
                suggestion="Fix this value in Excel before production.",
            )
        )

    for finding in findings:
        if finding.severity in {"WARNING", "NEEDS_REVIEW"}:
            warnings.append(finding)

    for order in valid_orders:
        if order.process_type in {LASER_CUT, BOTH}:
            dot_count = sum(1 for char in order.laser_text if char in {"i", "j", "İ", "ö", "Ö", "ü", "Ü", "ğ", "Ğ"})
            if dot_count:
                warnings.append(
                    IntelligenceFinding(
                        row_number=order.row_number,
                        order_no=order.order_no,
                        severity="WARNING",
                        category="turkish_marks_cut_risk",
                        field="laser_text",
                        message="Türkçe karakter işareti ayrı parça çıkabilir.",
                        suggestion="Kesimden önce bağlı script path çıktısını manuel kontrol edin.",
                    )
                )

        if order.process_type == PRINT and not order.label_text:
            warnings.append(
                IntelligenceFinding(
                    row_number=order.row_number,
                    order_no=order.order_no,
                    severity="NEEDS_REVIEW",
                    category="missing_print_text",
                    field="label_text",
                    message="PRINT işi için label_text eksik.",
                    suggestion="Etikete basılacak metni Excel'de label_text alanına yazın.",
                )
            )

    return warnings


def _friendly_issue_message(message: str) -> str:
    replacements = {
        "Missing laser_text for LASER_CUT job": "LASER_CUT için laser_text boş.",
        "Missing label_text for PRINT job": "PRINT işi için label_text eksik.",
        "NEEDS_REVIEW: multiple print templates match": "Birden fazla şablon eşleşti, kontrol gerekli.",
    }
    for source, friendly in replacements.items():
        if message.startswith(source):
            return friendly
    return message
