from __future__ import annotations

from datetime import date

from models import Order


def resolve_placeholders(value: str, order: Order, run_date: date) -> str:
    replacements = {
        "{{LABEL_TEXT}}": order.label_text,
        "{{BUYER_NAME}}": order.buyer_name,
        "{{ORDER_NO}}": order.order_no,
        "{{DATE}}": run_date.isoformat(),
        "{{DATE_TEXT}}": str(order.source.get("date_text", "")),
        "{{NOTE_TEXT}}": str(order.source.get("note_text", "")),
        "{{CUSTOM_TEXT_1}}": str(order.source.get("custom_text_1", "")),
        "{{CUSTOM_TEXT_2}}": str(order.source.get("custom_text_2", "")),
        "{{CUSTOM_TEXT_3}}": str(order.source.get("custom_text_3", "")),
    }
    for key, cell_value in order.source.items():
        replacements.setdefault("{{" + str(key).upper() + "}}", str(cell_value))
    result = value
    for placeholder, replacement in replacements.items():
        result = result.replace(placeholder, replacement)
    return result
