from __future__ import annotations

from pathlib import Path

from models import AppSettings, Order
from intelligence.production_analyzer import IntelligenceFinding


def build_recommendations(
    valid_orders: list[Order],
    settings: AppSettings,
) -> list[IntelligenceFinding]:
    recommendations: list[IntelligenceFinding] = []

    for order in valid_orders:
        product_text = f"{order.product_name} {order.production_note}".lower()
        if order.process_type == "NONE":
            suggested = _suggest_process_type(product_text)
            if suggested:
                recommendations.append(
                    IntelligenceFinding(
                        row_number=order.row_number,
                        order_no=order.order_no,
                        severity="SUGGESTION",
                        category="suggest_process_type",
                        field="process_type",
                        message=f"Possible process_type suggestion: {suggested}",
                        suggestion="This is only a suggestion. Confirm manually in Excel if correct.",
                    )
                )

        template_hint = _suggest_label_variant_from_templates(order, settings.print_templates_dir)
        if template_hint:
            recommendations.append(template_hint)

    return recommendations


def _suggest_process_type(text: str) -> str:
    if any(keyword in text for keyword in ("laser", "pleksi", "akrilik", "kesim")):
        return "LASER_CUT"
    if any(keyword in text for keyword in ("etiket", "çikolata", "cikolata", "baskı", "baski")):
        return "PRINT"
    return ""


def _suggest_label_variant_from_templates(order: Order, print_templates_dir: Path) -> IntelligenceFinding | None:
    if order.process_type not in {"PRINT", "BOTH"}:
        return None

    if order.label_variant != "NONE":
        return None

    if not print_templates_dir.exists():
        return None

    names = [path.name.lower() for path in print_templates_dir.iterdir() if path.is_file()]
    for variant in ("gold", "silver", "white", "red"):
        if any(order.model_no.lower() in name and variant in name for name in names):
            return IntelligenceFinding(
                row_number=order.row_number,
                order_no=order.order_no,
                severity="SUGGESTION",
                category="suggest_label_variant",
                field="label_variant",
                message=f"Template filenames suggest label_variant may be {variant.upper()}.",
                suggestion="Review template choice manually; mark NEEDS_REVIEW if uncertain.",
            )
    return None
