"""Sprint 1 + Sprint 2 — GET and POST endpoints for browser mode."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory

from server import controller_proxy as proxy

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Output directory served as static files
_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"


def _ok(data):
    """Return a JSON response, handling both dicts/lists and pre-serialised strings."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            pass
    return jsonify(data)


def _err(exc: Exception, status: int = 500):
    logger.exception("API error")
    return jsonify({"status": "ERROR", "error": str(exc)}), status


# ── Sprint 1 GET endpoints ────────────────────────────────────────────────────

@api_bp.route("/state")
def state():
    try:
        return _ok(proxy.get_state())
    except Exception as exc:
        return _err(exc)


@api_bp.route("/metrics")
def metrics():
    try:
        date_range_json = request.args.get("range", "{}")
        return _ok(proxy.get_metrics(date_range_json))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/label_outputs")
def label_outputs():
    try:
        return _ok(proxy.get_label_outputs())
    except Exception as exc:
        return _err(exc)


@api_bp.route("/print_queue")
def print_queue():
    try:
        return _ok(proxy.get_print_queue())
    except Exception as exc:
        return _err(exc)


@api_bp.route("/label_model_gallery")
def label_model_gallery():
    try:
        return _ok(proxy.get_label_model_gallery())
    except Exception as exc:
        return _err(exc)


@api_bp.route("/reports")
def reports():
    try:
        return _ok(proxy.get_reports())
    except Exception as exc:
        return _err(exc)


# ── Static output file server ─────────────────────────────────────────────────

@api_bp.route("/files/<path:filepath>")
def serve_output_file(filepath: str):
    """Serve PDF/PNG/CSV files from the output/ directory."""
    try:
        safe = Path(filepath)
        # Block path traversal
        if ".." in safe.parts:
            return jsonify({"status": "ERROR", "error": "Geçersiz dosya yolu"}), 400
        return send_from_directory(str(_OUTPUT_DIR), filepath)
    except Exception as exc:
        return _err(exc, 404)


# ── Sprint 2 POST endpoints ──────────────────────────────────────────────────

# GRUP 1 — Print Queue

@api_bp.route("/mark_queue_item_printed", methods=["POST"])
def mark_queue_item_printed():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.mark_queue_item_printed(payload.get("item_id", "")))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/mark_queue_item_pending", methods=["POST"])
def mark_queue_item_pending():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.mark_queue_item_pending(payload.get("item_id", "")))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/mark_queue_item_delivered", methods=["POST"])
def mark_queue_item_delivered():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.mark_queue_item_delivered(payload.get("item_id", "")))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/remove_from_print_queue", methods=["POST"])
def remove_from_print_queue():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.remove_from_print_queue(payload.get("item_id", "")))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/clear_print_queue", methods=["POST"])
def clear_print_queue():
    try:
        return _ok(proxy.clear_print_queue())
    except Exception as exc:
        return _err(exc)


@api_bp.route("/add_pdf_output_to_print_queue", methods=["POST"])
def add_pdf_output_to_print_queue():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.add_pdf_output_to_print_queue(payload.get("relative_path", "")))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/add_label_outputs_to_print_queue", methods=["POST"])
def add_label_outputs_to_print_queue():
    try:
        return _ok(proxy.add_label_outputs_to_print_queue())
    except Exception as exc:
        return _err(exc)


# GRUP 2 — Label Model Template Fields

@api_bp.route("/save_label_model_field", methods=["POST"])
def save_label_model_field():
    try:
        payload = request.get_json() or {}
        template_path = payload.get("template_path", "")
        index = int(payload.get("index", 0))
        field_data = {k: v for k, v in payload.items() if k not in ("template_path", "index")}
        return _ok(proxy.save_label_model_field(template_path, index, field_data))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/add_label_model_field", methods=["POST"])
def add_label_model_field():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.add_label_model_field(
            payload.get("template_path", ""),
            payload.get("field_type", "text"),
        ))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/remove_label_model_field", methods=["POST"])
def remove_label_model_field():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.remove_label_model_field(
            payload.get("template_path", ""),
            int(payload.get("index", 0)),
        ))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/save_label_defaults_json", methods=["POST"])
def save_label_defaults_json():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.save_label_defaults_json(payload))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/clone_label_model_variant", methods=["POST"])
def clone_label_model_variant():
    try:
        payload = request.get_json() or {}
        template_path = payload.pop("template_path", "")
        return _ok(proxy.clone_label_model_variant(template_path, payload))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/save_print_template_metadata", methods=["POST"])
def save_print_template_metadata():
    try:
        payload = request.get_json() or {}
        relative_path = payload.pop("relative_path", "")
        return _ok(proxy.save_print_template_metadata(relative_path, payload))
    except Exception as exc:
        return _err(exc)


# GRUP 3 — Ürün Tanımları

@api_bp.route("/productDefinitionSave", methods=["POST"])
def product_definition_save():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.product_definition_save(payload))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/productDefinitionArchive", methods=["POST"])
def product_definition_archive():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.product_definition_archive(payload.get("sku", "")))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/productDefinitionRestore", methods=["POST"])
def product_definition_restore():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.product_definition_restore(payload.get("sku", "")))
    except Exception as exc:
        return _err(exc)


# GRUP 4 — Müşteri Siparişleri

@api_bp.route("/create_customer_order", methods=["POST"])
def create_customer_order():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.create_customer_order(payload))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/update_customer_order_status", methods=["POST"])
def update_customer_order_status():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.update_customer_order_status(
            payload.get("order_id", ""),
            payload.get("status", ""),
        ))
    except Exception as exc:
        return _err(exc)


# GRUP 5 — Audit / Log

@api_bp.route("/append_production_audit_event", methods=["POST"])
def append_production_audit_event():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.append_production_audit_event(payload))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/rebuild_production_audit_from_existing_sources", methods=["POST"])
def rebuild_production_audit_from_existing_sources():
    try:
        return _ok(proxy.rebuild_production_audit_from_existing_sources())
    except Exception as exc:
        return _err(exc)


# GRUP 6 — Yazıcı Profili

@api_bp.route("/save_printer_profile", methods=["POST"])
def save_printer_profile():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.save_printer_profile(payload))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/delete_printer_profile", methods=["POST"])
def delete_printer_profile():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.delete_printer_profile(payload.get("profile_id", "")))
    except Exception as exc:
        return _err(exc)


# GRUP 7 — Yedekleme

@api_bp.route("/create_backup", methods=["POST"])
def create_backup():
    try:
        return _ok(proxy.create_backup())
    except Exception as exc:
        return _err(exc)


@api_bp.route("/restore_backup", methods=["POST"])
def restore_backup():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.restore_backup(
            payload.get("backup_path", ""),
            bool(payload.get("dry_run", True)),
        ))
    except Exception as exc:
        return _err(exc)


# GRUP 8 — Trendyol

@api_bp.route("/upsert_trendyol_mapping", methods=["POST"])
def upsert_trendyol_mapping():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.upsert_trendyol_mapping(payload))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/save_trendyol_settings", methods=["POST"])
def save_trendyol_settings():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.save_trendyol_settings(payload))
    except Exception as exc:
        return _err(exc)


# GRUP 9 — İsim Kesim

@api_bp.route("/update_name_cut_queue_item_status", methods=["POST"])
def update_name_cut_queue_item_status():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.update_name_cut_queue_item_status(
            payload.get("item_id", ""),
            payload.get("status", ""),
        ))
    except Exception as exc:
        return _err(exc)


# GRUP 10 — Güvenlik

@api_bp.route("/save_live_integration_security_settings", methods=["POST"])
def save_live_integration_security_settings():
    try:
        payload = request.get_json() or {}
        return _ok(proxy.save_live_integration_security_settings(payload))
    except Exception as exc:
        return _err(exc)


# Etiket Çıktı Arşivleme

@api_bp.route("/archive_label_outputs", methods=["POST"])
def archive_label_outputs():
    try:
        payload = request.get_json() or {}
        relative_paths = payload.get("relative_paths", [])
        return _ok(proxy.archive_label_outputs(relative_paths))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/restore_label_outputs", methods=["POST"])
def restore_label_outputs():
    try:
        payload = request.get_json() or {}
        relative_paths = payload.get("relative_paths", [])
        return _ok(proxy.restore_label_outputs(relative_paths))
    except Exception as exc:
        return _err(exc)
