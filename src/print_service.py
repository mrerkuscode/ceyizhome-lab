from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

from models import (
    AppSettings,
    LABEL_VARIANT_NONE,
    Order,
    PrintTemplateMatch,
    TEMPLATE_MISSING,
    TEMPLATE_NEEDS_REVIEW,
    TEMPLATE_OK,
    ValidationIssue,
)
from text_utils import safe_filename

PRINT_VARIANT_TOKENS = {"gold", "silver", "white", "red", "custom", "none"}
SUPPORTED_PRINT_TEMPLATE_EXTENSIONS = {".cdr", ".ai", ".pdf", ".svg"}


def find_print_template(
    print_templates_dir: Path,
    model_no: str,
    template_no: str,
    label_variant: str,
) -> PrintTemplateMatch:
    candidates = _candidate_print_template_files(print_templates_dir, model_no)
    model = _token_value(model_no)
    template = _token_value(template_no)
    variant = _token_value(label_variant)
    matches: list[Path] = []

    for path in candidates:
        tokens = _filename_tokens(path)
        has_model = model in tokens
        has_template = template in tokens
        has_variant = variant in tokens

        if not (has_model and has_template):
            continue

        if label_variant == LABEL_VARIANT_NONE:
            template_variants = tokens & PRINT_VARIANT_TOKENS
            if not template_variants or "none" in template_variants:
                matches.append(path)
        elif has_variant:
            matches.append(path)

    if not matches:
        return PrintTemplateMatch(status=TEMPLATE_MISSING, files=[])

    if len(matches) > 1:
        return PrintTemplateMatch(status=TEMPLATE_NEEDS_REVIEW, files=sorted(matches))

    return PrintTemplateMatch(status=TEMPLATE_OK, files=matches)


def generate_print_jobs(
    orders: list[Order],
    run_dir: Path,
    settings: AppSettings,
) -> tuple[list[Path], list[ValidationIssue]]:
    print_root = run_dir / "print"
    print_root.mkdir(parents=True, exist_ok=True)

    written_files: list[Path] = []
    issues: list[ValidationIssue] = []
    ready_orders_by_model: dict[str, list[tuple[Order, Path]]] = defaultdict(list)
    report_rows: list[dict[str, str]] = []

    for order in orders:
        match = find_print_template(
            settings.print_templates_dir,
            order.model_no,
            order.template_no,
            order.label_variant,
        )
        matched_files = "; ".join(str(path) for path in match.files)
        report_rows.append(
            {
                "order_no": order.order_no,
                "buyer_name": order.buyer_name,
                "model_no": order.model_no,
                "template_no": order.template_no,
                "label_variant": order.label_variant,
                "label_text": order.label_text,
                "status": match.status,
                "matched_files": matched_files,
                "message": _template_match_message(order, match),
            }
        )

        if match.status == TEMPLATE_OK:
            ready_orders_by_model[order.model_no].append((order, match.files[0]))
            continue

        issues.append(
            ValidationIssue(
                row_number=order.row_number,
                order_no=order.order_no,
                field="print_template",
                message=_template_match_message(order, match),
            )
        )

    if settings.reports.generate_template_matching_report:
        matching_report_path = print_root / "template_matching_report.csv"
        _write_template_matching_report(matching_report_path, report_rows)
        written_files.append(matching_report_path)

    for model_no, model_orders in ready_orders_by_model.items():
        model_dir = print_root / f"model_{safe_filename(model_no)}"
        model_dir.mkdir(parents=True, exist_ok=True)

        if settings.print.generate_print_data_csv:
            print_data_path = model_dir / "print_data.csv"
            _write_print_data(print_data_path, model_orders)
            written_files.append(print_data_path)

        for order, template_file in model_orders:
            job_info_path = _write_job_info(model_dir, order, template_file)
            written_files.append(job_info_path)

    return written_files, issues


def _write_template_matching_report(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "order_no",
                "buyer_name",
                "model_no",
                "template_no",
                "label_variant",
                "label_text",
                "status",
                "matched_files",
                "message",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_print_data(
    path: Path,
    orders_with_templates: list[tuple[Order, Path]],
) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "order_no",
                "buyer_name",
                "product_name",
                "model_no",
                "template_no",
                "personalization_type",
                "label_variant",
                "label_text",
                "quantity",
                "template_file",
                "production_note",
            ],
        )
        writer.writeheader()
        for order, template_file in orders_with_templates:
            writer.writerow(
                {
                    "order_no": order.order_no,
                    "buyer_name": order.buyer_name,
                    "product_name": order.product_name,
                    "model_no": order.model_no,
                    "template_no": order.template_no,
                    "personalization_type": order.personalization_type,
                    "label_variant": order.label_variant,
                    "label_text": order.label_text,
                    "quantity": order.quantity,
                    "template_file": str(template_file),
                    "production_note": order.production_note,
                }
            )


def _write_job_info(
    model_dir: Path,
    order: Order,
    template_file: Path,
) -> Path:
    order_dir = model_dir / f"order_{safe_filename(order.order_no)}_{safe_filename(order.label_text)}"
    order_dir.mkdir(parents=True, exist_ok=True)

    job_info_path = order_dir / "job_info.txt"
    job_info_path.write_text(
        "\n".join(
            [
                "PRINT JOB PREPARATION",
                "",
                "Safety:",
                "- CorelDRAW was not opened.",
                "- Nothing was sent to the printer.",
                "- This folder only contains prepared data for manual review.",
                "",
                f"Order no: {order.order_no}",
                f"Buyer name: {order.buyer_name}",
                f"Product name: {order.product_name}",
                f"Model no: {order.model_no}",
                f"Template no: {order.template_no}",
                f"Personalization type: {order.personalization_type}",
                f"Label variant: {order.label_variant}",
                f"Label text: {order.label_text}",
                f"Quantity: {order.quantity}",
                f"Template file: {template_file}",
                f"Production note: {order.production_note}",
                "",
                "CorelDRAW placeholder guidance:",
                "- {{LABEL_TEXT}}",
                "- {{BUYER_NAME}}",
                "- {{ORDER_NO}}",
                "- {{DATE}}",
            ]
        ),
        encoding="utf-8",
    )
    return job_info_path


def _template_match_message(order: Order, match: PrintTemplateMatch) -> str:
    if match.status == TEMPLATE_OK:
        return "Template matched"

    if match.status == TEMPLATE_NEEDS_REVIEW:
        matched_files = "; ".join(str(path) for path in match.files)
        return (
            "NEEDS_REVIEW: multiple print templates match "
            f"model_no {order.model_no}, template_no {order.template_no}, "
            f"label_variant {order.label_variant}: {matched_files}"
        )

    return (
        "Missing print template for "
        f"model_no {order.model_no}, template_no {order.template_no}, "
        f"label_variant {order.label_variant}"
    )


def _candidate_print_template_files(print_templates_dir: Path, model_no: str) -> list[Path]:
    candidates: list[Path] = []
    model_dir = print_templates_dir / model_no

    if model_dir.exists():
        candidates.extend(path for path in model_dir.iterdir() if _is_supported_template(path))

    if print_templates_dir.exists():
        candidates.extend(path for path in print_templates_dir.iterdir() if _is_supported_template(path))

    return sorted(set(candidates), key=lambda item: item.name.lower())


def _is_supported_template(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_PRINT_TEMPLATE_EXTENSIONS


def _filename_tokens(path: Path) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", path.stem.lower())
        if token
    }


def _token_value(value: str) -> str:
    return str(value).strip().lower()
