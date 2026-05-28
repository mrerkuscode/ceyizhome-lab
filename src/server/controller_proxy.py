"""
Browser mode controller proxy.
Calls backend API modules directly — no PySide6, no QApplication needed.
project_root is inferred relative to this file: src/server/ -> src/ -> production-bot/
"""
from __future__ import annotations

import json
from pathlib import Path

# Project root = production-bot/
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _root() -> Path:
    return PROJECT_ROOT


# ── Lazy imports so individual endpoint failures don't crash others ──────────

def _report_api():
    from webui_backend import report_api
    return report_api


def _template_api():
    from webui_backend import template_api
    return template_api


def _label_api():
    from webui_backend import label_api
    return label_api


def _print_queue_api():
    from webui_backend import print_queue_api
    return print_queue_api


def _production_audit_api():
    from webui_backend import production_audit_api
    return production_audit_api


def _settings_api():
    from webui_backend import settings_api
    return settings_api


def _customer_order_api():
    from webui_backend import customer_order_api
    return customer_order_api


def _printer_profile_api():
    from webui_backend import printer_profile_api
    return printer_profile_api


def _backup_api():
    from webui_backend import backup_api
    return backup_api


def _trendyol_api():
    from webui_backend import trendyol_api
    return trendyol_api


def _trendyol_mapping_api():
    from webui_backend import trendyol_mapping_api
    return trendyol_mapping_api


def _name_cut_queue_api():
    from webui_backend import name_cut_queue_api
    return name_cut_queue_api


def _live_integration_guard_api():
    from webui_backend import live_integration_guard_api
    return live_integration_guard_api


def _product_definitions_api():
    from webui_backend import product_definitions_api
    return product_definitions_api


# ── Public functions called by routes.py ────────────────────────────────────

def get_state() -> dict:
    """Simplified state object covering the fields app.js needs to render."""
    root = _root()
    ra = _report_api()
    ta = _template_api()
    la = _label_api()
    pqa = _print_queue_api()
    sa = _settings_api()
    paa = _production_audit_api()

    report_set = ra.load_reports(root)

    return {
        "selectedExcelName": "Excel seçilmedi",
        "selectedExcelPath": "",
        "readiness": ra.readiness(report_set),
        "fontOk": (root / "assets" / "fonts" / "connected_script.ttf").exists(),
        "fontText": "Lazer Fontu Hazır" if (root / "assets" / "fonts" / "connected_script.ttf").exists() else "Lazer Fontu Eksik",
        "summary": ra.summary(report_set),
        "errors": ra.first_errors(report_set),
        "activities": [],
        "outputDir": "",
        "log": "",
        "templates": ta.list_label_templates(root),
        "labelModels": ta.list_label_model_gallery(root),
        "printTemplates": ta.list_print_templates(root),
        "labelOutputs": la.list_label_outputs(root),
        "archivedLabelOutputs": la.list_archived_label_outputs(root),
        "labelOutputArchiveHistory": la.list_label_output_archive_history(root),
        "laserOutputs": la.list_laser_outputs(root),
        "printQueue": pqa.list_print_queue(root),
        "customerOrders": [],
        "trendyol": {"status": "BROWSER_MODE"},
        "bulkLabelUsage": {},
        "bulkPreviewSamples": [],
        "bulkColumnMapping": {},
        "bulkGalleryItems": [],
        "combinedProduction": {},
        "nameCutQueue": [],
        "nameCutTransferHistory": [],
        "nameCutExportHistory": [],
        "bulkSelectedRun": {"status": "IDLE", "message": "Browser mode — üretim komutları devre dışı.", "row_numbers": [], "row_count": 0},
        "commandRunning": False,
        "currentCommand": "",
        "reports": ra.report_payload(report_set),
        "qualityGateEvidence": {"status": "BROWSER_MODE"},
        "productionHistory": [],
        "productionAudit": paa.list_production_audit_events(root),
        "productionAuditSummary": paa.list_production_audit_summary(root),
        "printerProfiles": [],
        "systemBackups": [],
        "settingsBackups": sa.list_settings_backups(root),
        "liveIntegrationRegistry": {},
        "liveIntegrationSecurity": {},
        "labelDefaults": sa.get_label_defaults(root),
        "printMode": sa.get_print_mode(root),
    }


def get_metrics(date_range_json: str = "{}") -> dict:
    return _report_api().metrics_payload(date_range_json, _root())


def get_label_outputs() -> list:
    return _label_api().list_label_outputs(_root())


def get_print_queue() -> list:
    return _print_queue_api().list_print_queue(_root())


def get_label_model_gallery() -> list:
    return _template_api().list_label_model_gallery(_root())


def get_reports() -> dict:
    ra = _report_api()
    report_set = ra.load_reports(_root())
    return ra.report_payload(report_set)


# ── Sprint 2 WRITE proxies ───────────────────────────────────────────────────

# GRUP 1 — Print Queue

def mark_queue_item_printed(item_id: str) -> dict:
    return _print_queue_api().mark_queue_item_printed(_root(), item_id)


def mark_queue_item_pending(item_id: str) -> dict:
    return _print_queue_api().mark_queue_item_pending(_root(), item_id)


def mark_queue_item_delivered(item_id: str) -> dict:
    return _print_queue_api().mark_queue_item_delivered(_root(), item_id)


def remove_from_print_queue(item_id: str) -> dict:
    return _print_queue_api().remove_from_print_queue(_root(), item_id)


def clear_print_queue() -> dict:
    return _print_queue_api().clear_print_queue(_root())


def add_pdf_output_to_print_queue(relative_path: str) -> dict:
    return _print_queue_api().add_pdf_output_to_queue(_root(), relative_path)


def add_label_outputs_to_print_queue() -> dict:
    return _print_queue_api().add_label_outputs_to_queue(_root(), _label_api().list_label_outputs(_root()))


# GRUP 2 — Label Model Template Fields

def save_label_model_field(template_path: str, index: int, field_data: dict) -> dict:
    from pathlib import Path as _Path
    return _template_api().save_label_model_field(_root(), _Path(template_path), index, field_data)


def add_label_model_field(template_path: str, field_type: str) -> dict:
    from pathlib import Path as _Path
    return _template_api().add_label_model_field(_root(), _Path(template_path), field_type)


def remove_label_model_field(template_path: str, index: int) -> dict:
    from pathlib import Path as _Path
    return _template_api().remove_label_model_field(_root(), _Path(template_path), index)


def save_label_defaults_json(data: dict) -> dict:
    _settings_api().save_label_defaults(_root(), data)
    return {
        "status": "OK",
        "message": "Varsayılan etiket ayarları kaydedildi.",
        "label_defaults": _settings_api().get_label_defaults(_root()),
    }


def clone_label_model_variant(template_path: str, data: dict) -> dict:
    from pathlib import Path as _Path
    return _template_api().clone_label_model_variant(_root(), _Path(template_path), data)


def save_print_template_metadata(relative_path: str, data: dict) -> dict:
    return _template_api().save_print_template_metadata(_root(), relative_path, data)


# GRUP 3 — Ürün Tanımları

def product_definition_save(payload: dict) -> dict:
    return _product_definitions_api().api_save(_root(), payload)


def product_definition_archive(sku: str) -> dict:
    return _product_definitions_api().api_archive(_root(), sku)


def product_definition_restore(sku: str) -> dict:
    return _product_definitions_api().api_restore(_root(), sku)


# GRUP 4 — Müşteri Siparişleri

def create_customer_order(payload: dict) -> dict:
    return _customer_order_api().create_customer_order(_root(), payload)


def update_customer_order_status(order_id: str, status: str) -> dict:
    return _customer_order_api().update_customer_order_status(_root(), order_id, status)


# GRUP 5 — Audit / Log

def append_production_audit_event(event: dict) -> dict:
    return _production_audit_api().append_production_audit_event(_root(), event)


def rebuild_production_audit_from_existing_sources() -> dict:
    return _production_audit_api().rebuild_production_audit_from_existing_sources(_root())


# GRUP 6 — Yazıcı Profili

def save_printer_profile(profile: dict) -> dict:
    return _printer_profile_api().save_printer_profile(_root(), profile)


def delete_printer_profile(profile_id: str) -> dict:
    return _printer_profile_api().delete_printer_profile(_root(), profile_id)


# GRUP 7 — Yedekleme

def create_backup() -> dict:
    return _backup_api().create_backup(_root())


def restore_backup(backup_path: str, dry_run: bool = True) -> dict:
    return _backup_api().restore_backup(_root(), backup_path, dry_run)


# GRUP 8 — Trendyol

def upsert_trendyol_mapping(payload: dict) -> dict:
    return _trendyol_mapping_api().upsert_product_mapping(_root(), payload)


def save_trendyol_settings(payload: dict) -> dict:
    return _trendyol_api().save_settings(_root(), payload)


# GRUP 9 — İsim Kesim

def update_name_cut_queue_item_status(item_id: str, status: str) -> dict:
    return _name_cut_queue_api().update_name_cut_queue_item_status(_root(), item_id, status)


# GRUP 10 — Güvenlik

def save_live_integration_security_settings(payload: dict) -> dict:
    return _live_integration_guard_api().save_security_settings(_root(), payload)


# Label Outputs archive/restore

def archive_label_outputs(relative_paths: list) -> dict:
    return _label_api().archive_label_outputs(_root(), relative_paths)


def restore_label_outputs(relative_paths: list) -> dict:
    return _label_api().restore_label_outputs(_root(), relative_paths)
