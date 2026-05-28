from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from models import BOTH, LASER_CUT, LASER_ENGRAVE, PRINT, AppSettings, Order


@dataclass(frozen=True)
class IntelligenceFinding:
    row_number: int | str
    order_no: str
    severity: str
    category: str
    field: str
    message: str
    suggestion: str


LEGACY_HINT_COLUMNS = {"gold", "gümüş", "gumus", "silver", "altın", "altin"}
NOTE_WORDS = {"acil", "rush", "not", "dikkat", "renk", "gold", "silver", "gümüş", "altın"}


def analyze_orders(
    dataframe: pd.DataFrame,
    valid_orders: list[Order],
    settings: AppSettings,
) -> list[IntelligenceFinding]:
    findings: list[IntelligenceFinding] = []
    findings.extend(_analyze_raw_rows(dataframe, settings))
    findings.extend(_analyze_valid_orders(valid_orders))
    return findings


def _analyze_raw_rows(dataframe: pd.DataFrame, settings: AppSettings) -> list[IntelligenceFinding]:
    findings: list[IntelligenceFinding] = []
    legacy_columns = sorted(set(dataframe.columns) & LEGACY_HINT_COLUMNS)
    for column in legacy_columns:
        findings.append(
            IntelligenceFinding(
                row_number="HEADER",
                order_no="",
                severity="WARNING",
                category="possible_legacy_excel_issue",
                field=column,
                message=f"Legacy column detected: {column}",
                suggestion="Use the clean production columns instead; legacy columns should only be handled by a future converter.",
            )
        )

    for index, row in dataframe.iterrows():
        row_number = int(index) + 2
        order_no = str(row.get("order_no", "")).strip()
        process_type = str(row.get("process_type", "")).strip().upper()
        label_variant = str(row.get("label_variant", "")).strip().upper()
        production_note = str(row.get("production_note", "")).strip().lower()

        for field in ("model_no", "template_no", "label_text", "laser_text"):
            value = str(row.get(field, "")).strip()
            if not value:
                findings.append(
                    IntelligenceFinding(
                        row_number=row_number,
                        order_no=order_no,
                        severity="INFO",
                        category=f"missing_{field}",
                        field=field,
                        message=f"{field} is empty.",
                        suggestion="Check whether this is valid for the selected process_type and personalization_type.",
                    )
                )

        if process_type and process_type not in settings.valid_process_types:
            findings.append(
                IntelligenceFinding(
                    row_number=row_number,
                    order_no=order_no,
                    severity="NEEDS_REVIEW",
                    category="unclear_process_type",
                    field="process_type",
                    message=f"Unclear process_type: {process_type}",
                    suggestion="Select one of the allowed process_type values from the dropdown.",
                )
            )

        if label_variant and label_variant not in settings.valid_label_variants:
            findings.append(
                IntelligenceFinding(
                    row_number=row_number,
                    order_no=order_no,
                    severity="NEEDS_REVIEW",
                    category="possible_wrong_label_variant",
                    field="label_variant",
                    message=f"Possible wrong label_variant: {label_variant}",
                    suggestion="Use GOLD, SILVER, WHITE, RED, CUSTOM, or NONE.",
                )
            )

        if any(word in production_note for word in NOTE_WORDS):
            findings.append(
                IntelligenceFinding(
                    row_number=row_number,
                    order_no=order_no,
                    severity="WARNING",
                    category="suspicious_note",
                    field="production_note",
                    message="Production note may contain production instructions that should be structured.",
                    suggestion="Move color, process, or urgency decisions into the correct clean schema fields.",
                )
            )

    return findings


def _analyze_valid_orders(valid_orders: list[Order]) -> list[IntelligenceFinding]:
    findings: list[IntelligenceFinding] = []
    for order in valid_orders:
        if order.process_type in {LASER_CUT, BOTH} and len(order.laser_text) > 24:
            findings.append(
                IntelligenceFinding(
                    row_number=order.row_number,
                    order_no=order.order_no,
                    severity="WARNING",
                    category="long_laser_text",
                    field="laser_text",
                    message="Name may be long for laser cutting layout.",
                    suggestion="Review final plate layout before production.",
                )
            )

        if order.process_type in {PRINT, BOTH} and order.label_variant == "NONE" and order.label_text:
            findings.append(
                IntelligenceFinding(
                    row_number=order.row_number,
                    order_no=order.order_no,
                    severity="WARNING",
                    category="possible_wrong_label_variant",
                    field="label_variant",
                    message="Printable label text exists but label_variant is NONE.",
                    suggestion="Confirm whether the label should use GOLD, SILVER, WHITE, RED, or CUSTOM.",
                )
            )

    return findings
