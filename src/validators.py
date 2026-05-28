from __future__ import annotations

from typing import Iterable

import pandas as pd

from models import (
    AppSettings,
    BOTH,
    LASER_CUT,
    LASER_ENGRAVE,
    NONE,
    Order,
    PERSONALIZATION_LABEL,
    PERSONALIZATION_LABEL_AND_NAME,
    PERSONALIZATION_NAME,
    PERSONALIZATION_NO_PERSONALIZATION,
    PRINT,
    ValidationIssue,
)
from text_utils import clean_customer_name, normalize_cell


BASE_REQUIRED_FIELDS = [
    "order_no",
    "buyer_name",
    "product_name",
    "model_no",
    "process_type",
    "quantity",
]

PRINT_REQUIRED_FIELDS = [
    "template_no",
    "personalization_type",
    "label_variant",
]


def validate_required_columns(
    dataframe: pd.DataFrame,
    required_columns: Iterable[str],
) -> list[ValidationIssue]:
    missing = [column for column in required_columns if column not in dataframe.columns]
    return [
        ValidationIssue(
            row_number="HEADER",
            order_no="",
            field=column,
            message=f"Missing required column: {column}",
        )
        for column in missing
    ]


def validate_and_build_orders(
    dataframe: pd.DataFrame,
    settings: AppSettings,
) -> tuple[list[Order], list[ValidationIssue]]:
    column_issues = validate_required_columns(dataframe, settings.required_columns)
    if column_issues:
        return [], column_issues

    dataframe = _with_optional_columns(dataframe, settings.optional_columns)
    columns = list(dict.fromkeys([*settings.required_columns, *settings.optional_columns, *list(dataframe.columns)]))
    orders: list[Order] = []
    issues: list[ValidationIssue] = []

    for index, row in dataframe.iterrows():
        row_number = int(index) + 2
        row_data = {column: normalize_cell(row.get(column)) for column in columns}
        _normalize_row_data(row_data)
        order_no = row_data["order_no"]

        row_issues = _validate_row_fields(row_number, order_no, row_data, settings)
        if row_issues:
            issues.extend(row_issues)
            continue

        order = Order(
            row_number=row_number,
            order_no=order_no,
            buyer_name=row_data["buyer_name"],
            product_name=row_data["product_name"],
            model_no=row_data["model_no"],
            template_no=row_data["template_no"],
            process_type=row_data["process_type"],
            personalization_type=row_data["personalization_type"],
            label_variant=row_data["label_variant"],
            label_text=row_data["label_text"],
            laser_text=row_data["laser_text"],
            quantity=_parse_int(row_data["quantity"]),
            material_type=row_data["material_type"],
            material_thickness_mm=row_data["material_thickness_mm"],
            extra_chocolate_qty=_parse_optional_int(row_data["extra_chocolate_qty"]),
            extra_madlen_qty=_parse_optional_int(row_data["extra_madlen_qty"]),
            production_note=row_data["production_note"],
            needs_review=row_data["needs_review"],
            status=row_data["status"],
            source=row_data,
        )

        template_issues = _validate_templates(order, settings)
        if template_issues:
            issues.extend(template_issues)
            continue

        orders.append(order)

    return orders, issues


def _with_optional_columns(
    dataframe: pd.DataFrame,
    optional_columns: Iterable[str],
) -> pd.DataFrame:
    dataframe = dataframe.copy()
    for column in optional_columns:
        if column not in dataframe.columns:
            dataframe[column] = ""
    return dataframe


def _normalize_row_data(row_data: dict[str, str]) -> None:
    row_data["buyer_name"] = clean_customer_name(row_data["buyer_name"])
    row_data["label_text"] = clean_customer_name(row_data["label_text"])
    row_data["laser_text"] = clean_customer_name(row_data["laser_text"])
    row_data["process_type"] = row_data["process_type"].upper()
    row_data["personalization_type"] = row_data["personalization_type"].upper()
    row_data["label_variant"] = _normalize_label_variant(row_data["label_variant"])
    row_data["status"] = _normalize_status(row_data["status"])
    row_data["needs_review"] = row_data["needs_review"].strip()


def _validate_row_fields(
    row_number: int,
    order_no: str,
    row_data: dict[str, str],
    settings: AppSettings,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    process_type = row_data.get("process_type", "")
    personalization_type = row_data.get("personalization_type", "")

    _append_missing_fields(issues, row_number, order_no, row_data, BASE_REQUIRED_FIELDS)

    if process_type in {PRINT, BOTH}:
        _append_missing_fields(issues, row_number, order_no, row_data, PRINT_REQUIRED_FIELDS)

    if process_type and process_type not in settings.valid_process_types:
        issues.append(
            ValidationIssue(
                row_number=row_number,
                order_no=order_no,
                field="process_type",
                message=f"Invalid process_type: {process_type}",
            )
        )

    if personalization_type and personalization_type not in settings.valid_personalization_types:
        issues.append(
            ValidationIssue(
                row_number=row_number,
                order_no=order_no,
                field="personalization_type",
                message=f"Invalid personalization_type: {personalization_type}",
            )
        )

    label_variant = row_data.get("label_variant", "")
    if label_variant and label_variant not in settings.valid_label_variants:
        issues.append(
            ValidationIssue(
                row_number=row_number,
                order_no=order_no,
                field="label_variant",
                message=f"Invalid label_variant: {label_variant}",
            )
        )

    status = row_data.get("status", "")
    if status and status not in settings.valid_statuses:
        issues.append(
            ValidationIssue(
                row_number=row_number,
                order_no=order_no,
                field="status",
                message=f"Invalid status: {status}",
            )
        )

    _validate_personalization_texts(issues, row_number, order_no, row_data)
    _validate_quantity_fields(issues, row_number, order_no, row_data)
    _validate_material_fields(issues, row_number, order_no, row_data)

    return issues


def _append_missing_fields(
    issues: list[ValidationIssue],
    row_number: int,
    order_no: str,
    row_data: dict[str, str],
    fields: Iterable[str],
) -> None:
    for field in fields:
        if not row_data.get(field):
            issues.append(
                ValidationIssue(
                    row_number=row_number,
                    order_no=order_no,
                    field=field,
                    message=f"Missing {field}",
                )
            )


def _validate_personalization_texts(
    issues: list[ValidationIssue],
    row_number: int,
    order_no: str,
    row_data: dict[str, str],
) -> None:
    process_type = row_data.get("process_type", "")
    personalization_type = row_data.get("personalization_type", "")

    if process_type == PRINT:
        if personalization_type != PERSONALIZATION_NO_PERSONALIZATION and not row_data.get("label_text"):
            _append_issue(issues, row_number, order_no, "label_text", "Missing label_text for PRINT job")

    if process_type in {LASER_ENGRAVE, LASER_CUT}:
        if not row_data.get("laser_text"):
            _append_issue(issues, row_number, order_no, "laser_text", f"Missing laser_text for {process_type} job")

    if process_type == BOTH:
        if personalization_type == PERSONALIZATION_LABEL_AND_NAME:
            if not row_data.get("label_text"):
                _append_issue(issues, row_number, order_no, "label_text", "Missing label_text for BOTH job")
            if not row_data.get("laser_text"):
                _append_issue(issues, row_number, order_no, "laser_text", "Missing laser_text for BOTH job")
        elif personalization_type == PERSONALIZATION_LABEL and not row_data.get("label_text"):
            _append_issue(issues, row_number, order_no, "label_text", "Missing label_text for BOTH LABEL job")
        elif personalization_type == PERSONALIZATION_NAME and not row_data.get("laser_text"):
            _append_issue(issues, row_number, order_no, "laser_text", "Missing laser_text for BOTH NAME job")


def _validate_quantity_fields(
    issues: list[ValidationIssue],
    row_number: int,
    order_no: str,
    row_data: dict[str, str],
) -> None:
    quantity = row_data.get("quantity", "")
    if quantity and not _is_positive_number(quantity):
        _append_issue(issues, row_number, order_no, "quantity", "Invalid quantity: must be a positive number")

    for field in ("extra_chocolate_qty", "extra_madlen_qty"):
        value = row_data.get(field, "")
        if value and not _is_non_negative_number(value):
            _append_issue(issues, row_number, order_no, field, f"Invalid {field}: must be zero or positive")


def _validate_material_fields(
    issues: list[ValidationIssue],
    row_number: int,
    order_no: str,
    row_data: dict[str, str],
) -> None:
    process_type = row_data.get("process_type", "")

    if process_type == LASER_ENGRAVE:
        return

    if process_type == LASER_CUT:
        if not row_data.get("material_type"):
            _append_issue(issues, row_number, order_no, "material_type", "Missing material_type for LASER_CUT job")
        if not row_data.get("material_thickness_mm"):
            _append_issue(
                issues,
                row_number,
                order_no,
                "material_thickness_mm",
                "Missing material_thickness_mm for LASER_CUT job",
            )

    thickness = row_data.get("material_thickness_mm", "")
    if thickness and not _is_positive_number(thickness):
        _append_issue(
            issues,
            row_number,
            order_no,
            "material_thickness_mm",
            "Invalid material_thickness_mm: must be a positive number",
        )


def _validate_templates(order: Order, settings: AppSettings) -> list[ValidationIssue]:
    return []


def _append_issue(
    issues: list[ValidationIssue],
    row_number: int,
    order_no: str,
    field: str,
    message: str,
) -> None:
    issues.append(
        ValidationIssue(
            row_number=row_number,
            order_no=order_no,
            field=field,
            message=message,
        )
    )


def _normalize_label_variant(value: str) -> str:
    variant = value.strip().upper()
    return variant or "NONE"


def _normalize_status(value: str) -> str:
    status = value.strip().upper()
    return status or "NEW"


def _is_positive_number(value: str) -> bool:
    try:
        return float(value) > 0
    except ValueError:
        return False


def _is_non_negative_number(value: str) -> bool:
    try:
        return float(value) >= 0
    except ValueError:
        return False


def _parse_int(value: str) -> int:
    return int(float(value))


def _parse_optional_int(value: str) -> int:
    return int(float(value)) if value else 0
