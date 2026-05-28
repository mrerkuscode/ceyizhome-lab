"""Sprint 1 — 7 GET endpoints for browser mode."""
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
