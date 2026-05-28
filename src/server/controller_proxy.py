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
