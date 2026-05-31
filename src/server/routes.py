"""Sprint 1 + Sprint 2 + Sprint 3 — GET and POST endpoints for browser mode."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from server import controller_proxy as proxy
from server import job_manager

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Output directory served as static files
_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"
# Assets directory (label backgrounds, fonts, DXF library)
_ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"

# Sprint 3 — file upload helpers
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_UPLOAD_INPUT_DIR = _PROJECT_ROOT / "input"
_UPLOAD_FONTS_DIR = _PROJECT_ROOT / "assets" / "fonts"
_UPLOAD_TEMP_DIR = _PROJECT_ROOT / "input" / "upload_temp"
_MAX_UPLOAD_BYTES = 16 * 1024 * 1024  # 16 MB

_ALLOWED = {
    "excel":   {".xlsx", ".xls"},
    "font":    {".ttf", ".otf"},
    "visual":  {".png", ".jpg", ".jpeg", ".svg"},
    "pack":    {".zip", ".cdr", ".ai", ".pdf"},
    "preview": {".png", ".jpg", ".jpeg"},
}


def _save_upload(file_storage, dest_dir: Path, allowed_exts: set[str]) -> dict:
    """Validate and save an uploaded file. Returns {status, path, filename}."""
    if not file_storage or file_storage.filename == "":
        return {"status": "ERROR", "error": "Dosya seçilmedi"}
    suffix = Path(file_storage.filename).suffix.lower()
    if suffix not in allowed_exts:
        return {
            "status": "ERROR",
            "error": f"İzin verilmeyen format: {suffix}. Kabul edilen: {', '.join(sorted(allowed_exts))}",
        }
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > _MAX_UPLOAD_BYTES:
        return {"status": "ERROR", "error": f"Dosya çok büyük (maks {_MAX_UPLOAD_BYTES // (1024*1024)} MB)"}
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = secure_filename(file_storage.filename)
    dest = dest_dir / safe_name
    file_storage.save(str(dest))
    return {"status": "OK", "path": str(dest), "filename": safe_name, "size_bytes": size}


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
        if ".." in safe.parts:
            return jsonify({"status": "ERROR", "error": "Geçersiz dosya yolu"}), 400
        return send_from_directory(str(_OUTPUT_DIR), filepath)
    except Exception as exc:
        return _err(exc, 404)


@api_bp.route("/asset/<path:filepath>")
def serve_asset_file(filepath: str):
    """Serve project asset files (label backgrounds, fonts) for browser mode."""
    try:
        safe = Path(filepath)
        if ".." in safe.parts:
            return jsonify({"status": "ERROR", "error": "Geçersiz dosya yolu"}), 400
        return send_from_directory(str(_ASSETS_DIR), filepath)
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

@api_bp.route("/ai_connection_test", methods=["GET"])
def ai_connection_test():
    """Read-only LLM bağlantı testi — hiçbir kaydı değiştirmez."""
    try:
        from intelligence.trendyol_ai_extractor import test_ai_connection
        from webui_backend import trendyol_api as _ta
        settings = _ta.get_settings(_PROJECT_ROOT, masked=False)
        return _ok(test_ai_connection(settings, _PROJECT_ROOT))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/reanalyze_all_trendyol_suggestions", methods=["POST"])
def reanalyze_all_trendyol_suggestions():
    """Toplu AI yeniden analiz — background job başlatır, job_id döner."""
    try:
        from webui_backend import trendyol_api as _ta
        prog = _ta.get_bulk_reanalyze_progress()
        if prog.get("running"):
            return _ok({"status": "ALREADY_RUNNING", "message": "Toplu analiz zaten çalışıyor.", "progress": prog})
        job_id = job_manager.start_job(
            "reanalyze_all",
            job_manager._browser_reanalyze_all,
            str(_PROJECT_ROOT),
        )
        # job_id'yi progress tracker'a da yaz
        with _ta._bulk_reanalyze_lock:
            _ta._bulk_reanalyze_progress["job_id"] = job_id
        rows = _ta.list_suggestions(_PROJECT_ROOT)
        total = sum(1 for r in rows if not r.get("operator_corrected"))
        return _ok({"status": "STARTED", "job_id": job_id, "total": total,
                    "message": f"Toplu AI analiz başlatıldı ({total} öneri)."})
    except Exception as exc:
        return _err(exc)


@api_bp.route("/bulk_reanalyze_progress", methods=["GET"])
def bulk_reanalyze_progress():
    """Anlık ilerleme durumu — running, current, total, changed, failed."""
    try:
        from webui_backend import trendyol_api as _ta
        prog = _ta.get_bulk_reanalyze_progress()
        # job tamamlandıysa result'ı da ekle
        job_id = prog.get("job_id") or ""
        if job_id and not prog.get("running"):
            job_stat = job_manager.get_status(job_id)
            if job_stat.get("status") == "completed":
                prog["result"] = job_stat.get("result")
        return _ok(prog)
    except Exception as exc:
        return _err(exc)


@api_bp.route("/test_trendyol_connection", methods=["POST"])
def test_trendyol_connection():
    try:
        from webui_backend import trendyol_api as _ta
        return _ok(_ta.test_connection(_PROJECT_ROOT))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/sync_trendyol_recent_orders", methods=["POST"])
def sync_trendyol_recent_orders():
    try:
        from webui_backend import trendyol_api as _ta
        payload = request.get_json() or {}
        days = max(1, min(int(payload.get("days", 2)), 14))
        return _ok(_ta.sync_recent_orders(_PROJECT_ROOT, days=days))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/read_trendyol_questions", methods=["POST"])
def read_trendyol_questions():
    try:
        from webui_backend import trendyol_api as _ta
        return _ok(_ta.sync_questions(_PROJECT_ROOT))
    except Exception as exc:
        return _err(exc)


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


@api_bp.route("/trendyol_auto_sync_status", methods=["GET"])
def trendyol_auto_sync_status():
    try:
        from server import trendyol_scheduler as _sched
        return _ok(_sched.get_status())
    except Exception as exc:
        return _err(exc)


@api_bp.route("/trendyol_auto_sync_toggle", methods=["POST"])
def trendyol_auto_sync_toggle():
    try:
        from server import trendyol_scheduler as _sched
        from webui_backend import trendyol_api as _ta
        payload = request.get_json() or {}
        enabled = bool(payload.get("enabled"))
        interval = max(10, int(payload.get("interval_sec") or 30))
        # Persist to settings file
        current = _ta.get_settings(_PROJECT_ROOT, masked=False)
        current["auto_sync_enabled"] = enabled
        current["auto_sync_interval_sec"] = interval
        _ta.settings_path(_PROJECT_ROOT).write_text(
            json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if enabled:
            _sched.start(_PROJECT_ROOT, interval_sec=interval)
        else:
            _sched.stop()
        return _ok({
            "enabled": enabled,
            "interval_sec": interval,
            "scheduler": _sched.get_status(),
            "settings": _ta.get_settings(_PROJECT_ROOT),
        })
    except Exception as exc:
        return _err(exc)


@api_bp.route("/save_trendyol_operator_correction", methods=["POST"])
def save_trendyol_operator_correction():
    try:
        from webui_backend import trendyol_api as _ta
        payload = request.get_json() or {}
        suggestion_id = str(payload.pop("suggestion_id", "") or "")
        return _ok(_ta.save_trendyol_operator_correction(_PROJECT_ROOT, suggestion_id, payload))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/reanalyze_trendyol_suggestion", methods=["POST"])
def reanalyze_trendyol_suggestion():
    try:
        from webui_backend import trendyol_api as _ta
        payload = request.get_json() or {}
        suggestion_id = str(payload.get("id") or payload.get("suggestion_id") or "")
        return _ok(_ta.reanalyze_trendyol_suggestion(_PROJECT_ROOT, suggestion_id))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/reanalyze_all_trendyol_suggestions_status", methods=["GET"])
def reanalyze_all_trendyol_suggestions_status():
    """Alias for /bulk_reanalyze_progress — JS polling uyumluluğu."""
    try:
        from webui_backend import trendyol_api as _ta
        return _ok(_ta.get_bulk_reanalyze_progress())
    except Exception as exc:
        return _err(exc)


@api_bp.route("/mark_trendyol_orders_processing", methods=["POST"])
def mark_trendyol_orders_processing():
    """İnsan onaylı İşleme Al — seçili Trendyol siparişlerini İşleme Alındı statüsüne taşır.

    Güvenlik: confirmed=True olmadan hiçbir API çağrısı yapılmaz.
    Token log/audit'e ASLA yazılmaz.
    """
    try:
        from webui_backend import trendyol_api as _ta
        payload = request.get_json() or {}
        suggestion_ids = payload.get("suggestion_ids") or []
        confirmed = bool(payload.get("confirmed"))
        confirmed_by = str(payload.get("confirmed_by") or "operator")
        if not isinstance(suggestion_ids, list) or not suggestion_ids:
            return jsonify({"status": "ERROR", "message": "suggestion_ids listesi boş veya geçersiz."}), 400
        return _ok(_ta.mark_packages_as_processing(
            _PROJECT_ROOT,
            suggestion_ids,
            confirmed=confirmed,
            confirmed_by=confirmed_by,
        ))
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


@api_bp.route("/name_cut_production_scene", methods=["POST"])
def name_cut_production_scene():
    """Read-only: FontTools+pyclipper production scene (geometry, paths, placements).

    Masaüstü bridge.build_name_cut_production_scene ile aynı payload/response formatı.
    """
    try:
        from webui_backend import combined_production_api as _cpa
        payload = request.get_json() or {}
        items = payload.get("items") or []
        config = payload.get("config") or {}
        return _ok(_cpa.build_name_cut_production_scene(items, config))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/name_cut_preview_paths", methods=["POST"])
def name_cut_preview_paths():
    """Read-only: canvas önizleme için FontTools path'leri döner.

    Masaüstü bridge.preview_name_cut_paths ile aynı payload/response formatı.
    """
    try:
        from webui_backend import combined_production_api as _cpa
        payload = request.get_json() or {}
        items = payload.get("items") or []
        config = payload.get("config") or {}
        return _ok(_cpa.preview_name_cut_paths(items, config))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/name_cut_export", methods=["POST"])
def name_cut_export():
    """SVG/DXF/PDF export paketi oluşturur, export history'ye kaydeder.

    Masaüstü bridge.prepare_name_cut_files ile aynı payload/response formatı.
    RDWorks/lazer/yazıcı otomatik açılmaz.
    """
    try:
        from webui_backend import combined_production_api as _cpa
        from webui_backend import name_cut_queue_api as _ncq
        payload = request.get_json() or {}
        items = payload.get("items") or []
        config = payload.get("config") or {}
        # excel_path: manifest için; tarayıcı modunda kaynak Excel genellikle yok
        excel_path = _PROJECT_ROOT / "input" / "browser_session.xlsx"
        result = _cpa.export_name_cut_batch(_PROJECT_ROOT, excel_path, items, config)
        if result.get("status") == "OK":
            # Export history'ye kaydet
            history_entry = {
                "export_batch_id": result.get("export_batch_id", ""),
                "created_at": result.get("created_at", ""),
                "status": "OK",
                "formats": config.get("formats") or ["svg", "dxf", "pdf"],
                "quantity_total": sum(max(1, int(item.get("quantity") or 1)) for item in items),
                "cut_direction": config.get("cut_direction", ""),
                "exported_files": {
                    "manifest": result.get("manifest_path", ""),
                    "svg": result.get("svg_path", ""),
                    "dxf": result.get("dxf_path", ""),
                    "pdf": result.get("pdf_preview", ""),
                    "png": result.get("png_preview", ""),
                },
            }
            try:
                _ncq.record_name_cut_export_history(_PROJECT_ROOT, history_entry)
            except Exception:
                pass
            result["export_history"] = _ncq.list_name_cut_export_history(_PROJECT_ROOT)
        return _ok(result)
    except Exception as exc:
        return _err(exc)


@api_bp.route("/mark_name_cut_queue_item_prepared", methods=["POST"])
def mark_name_cut_queue_item_prepared():
    """Seçili İsim Kesim kuyruğu kaydını 'prepared' olarak işaretle."""
    try:
        from webui_backend import name_cut_queue_api as _ncq
        payload = request.get_json() or {}
        item_id = str(payload.get("item_id") or "")
        return _ok(_ncq.mark_name_cut_queue_item_prepared(_PROJECT_ROOT, item_id))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/save_name_cut_queue_items", methods=["POST"])
def save_name_cut_queue_items():
    """İsim Kesim hazırlık kuyruğuna toplu kayıt ekler."""
    try:
        from webui_backend import name_cut_queue_api as _ncq
        payload = request.get_json() or {}
        return _ok(_ncq.save_name_cut_queue_items(_PROJECT_ROOT, payload))
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


# ── Sprint 3 — File Upload endpoints ────────────────────────────────────────

@api_bp.route("/upload_excel", methods=["POST"])
def upload_excel():
    try:
        f = request.files.get("file")
        result = _save_upload(f, _UPLOAD_INPUT_DIR, _ALLOWED["excel"])
        return _ok(result)
    except Exception as exc:
        return _err(exc)


@api_bp.route("/upload_font", methods=["POST"])
def upload_font():
    try:
        f = request.files.get("file")
        result = _save_upload(f, _UPLOAD_FONTS_DIR, _ALLOWED["font"])
        return _ok(result)
    except Exception as exc:
        return _err(exc)


@api_bp.route("/upload_design_visual", methods=["POST"])
def upload_design_visual():
    try:
        f = request.files.get("file")
        result = _save_upload(f, _UPLOAD_TEMP_DIR, _ALLOWED["visual"])
        return _ok(result)
    except Exception as exc:
        return _err(exc)


@api_bp.route("/upload_template_pack", methods=["POST"])
def upload_template_pack():
    try:
        f = request.files.get("file")
        result = _save_upload(f, _UPLOAD_TEMP_DIR, _ALLOWED["pack"])
        return _ok(result)
    except Exception as exc:
        return _err(exc)


@api_bp.route("/upload_label_preview", methods=["POST"])
def upload_label_preview():
    try:
        f = request.files.get("file")
        result = _save_upload(f, _UPLOAD_TEMP_DIR, _ALLOWED["preview"])
        return _ok(result)
    except Exception as exc:
        return _err(exc)


# ── Sprint 3 — Subprocess / Job endpoints ───────────────────────────────────

@api_bp.route("/start_render_labels", methods=["POST"])
def start_render_labels():
    try:
        payload = request.get_json() or {}
        excel_path = payload.get("excel_path", "")
        job_id = job_manager.start_job(
            "render_labels",
            job_manager._browser_render_labels,
            excel_path,
        )
        return _ok({"status": "OK", "job_id": job_id, "message": "Render başlatıldı"})
    except Exception as exc:
        return _err(exc)


@api_bp.route("/start_run_dry", methods=["POST"])
def start_run_dry():
    try:
        payload = request.get_json() or {}
        excel_path = payload.get("excel_path", "")
        job_id = job_manager.start_job(
            "run_dry",
            job_manager._browser_run_dry,
            excel_path,
        )
        return _ok({"status": "OK", "job_id": job_id, "message": "Dry run başlatıldı"})
    except Exception as exc:
        return _err(exc)


@api_bp.route("/job_status/<job_id>")
def job_status(job_id: str):
    try:
        return _ok(job_manager.get_status(job_id))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/job_log/<job_id>")
def job_log(job_id: str):
    try:
        tail = int(request.args.get("tail", 100))
        return _ok(job_manager.get_log(job_id, tail=tail))
    except Exception as exc:
        return _err(exc)


# ── Etiket Studio — Tarayıcı modu render/preflight (P0-3, P0-4) ──────────────

@api_bp.route("/health", methods=["GET", "POST"])
@api_bp.route("/preflight/check", methods=["GET", "POST"])  # eski alias — yalnız sağlık ping'i
def health_check():
    return _ok({"ok": True, "status": "OK", "message": "Sunucu çalışıyor."})


@api_bp.route("/preflight_manual_label", methods=["POST"])
def preflight_manual_label_api():
    try:
        body = request.get_json() or {}
        template_path_str = str(body.get("template_path") or "")
        fields = {str(k): str(v) for k, v in (body.get("fields") or {}).items()}
        quantity = max(1, int(body.get("quantity") or 1))

        from webui_backend import production_safety  # lazy — Qt isteğe bağlı
        template_path = _resolve_label_template_path(template_path_str)
        result = production_safety.preflight_manual_label(
            _PROJECT_ROOT, template_path, fields, quantity
        )
        return _ok(result)
    except Exception as exc:
        return _err(exc)


@api_bp.route("/render_manual_label", methods=["POST"])
def render_manual_label_api():
    try:
        body = request.get_json() or {}
        template_path_str = str(body.get("template_path") or "")
        fields = {str(k): str(v) for k, v in (body.get("fields") or {}).items()}
        quantity = max(1, int(body.get("quantity") or 1))

        from webui_backend import production_safety, label_api  # lazy — Qt isteğe bağlı
        template_path = _resolve_label_template_path(template_path_str)

        preflight = production_safety.preflight_manual_label(
            _PROJECT_ROOT, template_path, fields, quantity
        )
        if preflight.get("status") == "ERROR":
            return _ok({**preflight, "status": "ERROR"})

        render_result = label_api.render_manual(
            _PROJECT_ROOT, template_path,
            str(fields.get("label_text") or ""),
            quantity,
            field_values=fields,
        )
        return _ok({
            "status": "OK",
            "message": f"PDF ve PNG oluşturuldu. Adet: {quantity}",
            "batch_pdf_path": str(render_result.batch_pdf_path),
            "pdf_path": str(render_result.pdf_path),
            "png_path": str(render_result.png_path),
            "output_dir": str(render_result.output_dir),
            "quantity": render_result.quantity,
            "preflight": preflight,
        })
    except Exception as exc:
        return _err(exc)


def _resolve_label_template_path(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else _PROJECT_ROOT / path_str


@api_bp.route("/cancel_job/<job_id>", methods=["POST"])
def cancel_job(job_id: str):
    try:
        return _ok(job_manager.cancel_job(job_id))
    except Exception as exc:
        return _err(exc)


# ── PART A — Font Kütüphanesi ────────────────────────────────────────────────

@api_bp.route("/fonts")
def list_fonts():
    try:
        from webui_backend import font_library_api as _fla
        return _ok(_fla.list_fonts(_PROJECT_ROOT))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/upload_font_library", methods=["POST"])
def upload_font_library():
    try:
        from webui_backend import font_library_api as _fla
        f = request.files.get("file")
        if not f or f.filename == "":
            return jsonify({"status": "ERROR", "error": "Dosya seçilmedi"}), 400
        font_type = request.form.get("tip", "label")
        laser_safe = request.form.get("laser_safe", "false").lower() in {"true", "1", "yes"}
        suffix = Path(f.filename).suffix.lower()
        if suffix not in {".ttf", ".otf"}:
            return jsonify({"status": "ERROR", "error": f"İzin verilmeyen format: {suffix}. Kabul edilen: .ttf, .otf"}), 400
        f.seek(0, 2)
        size = f.tell()
        f.seek(0)
        if size > _MAX_UPLOAD_BYTES:
            return jsonify({"status": "ERROR", "error": f"Dosya çok büyük (maks {_MAX_UPLOAD_BYTES // (1024*1024)} MB)"}), 400
        file_bytes = f.read()
        result = _fla.add_font(_PROJECT_ROOT, f.filename, file_bytes, font_type, laser_safe=laser_safe)
        return _ok(result)
    except Exception as exc:
        return _err(exc)


@api_bp.route("/font/<font_id>", methods=["DELETE"])
def delete_font(font_id: str):
    try:
        from webui_backend import font_library_api as _fla
        return _ok(_fla.delete_font(_PROJECT_ROOT, font_id))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/font_file/<font_id>")
def serve_font_file(font_id: str):
    """Serve a font file from the library for @font-face preview."""
    try:
        from webui_backend import font_library_api as _fla
        from flask import send_file
        manifest = _fla.list_fonts(_PROJECT_ROOT)
        all_fonts = manifest.get("label_fonts", []) + manifest.get("laser_fonts", [])
        entry = next((f for f in all_fonts if f.get("id") == font_id), None)
        if not entry or not entry.get("file"):
            return jsonify({"status": "ERROR", "error": "Font bulunamadı"}), 404
        font_path = _fla.library_dir(_PROJECT_ROOT) / entry["file"]
        if not font_path.exists():
            return jsonify({"status": "ERROR", "error": "Font dosyası bulunamadı"}), 404
        mime = "font/otf" if str(font_path).endswith(".otf") else "font/ttf"
        return send_file(str(font_path), mimetype=mime)
    except Exception as exc:
        return _err(exc)


# ── PART B — Trendyol Ürün Katalog Sync ─────────────────────────────────────

@api_bp.route("/sync_trendyol_products", methods=["POST"])
def sync_trendyol_products():
    try:
        from webui_backend import trendyol_api as _ta
        return _ok(_ta.sync_products(_PROJECT_ROOT))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/trendyol_products")
def trendyol_products_catalog():
    try:
        from webui_backend import recipe_api as _ra
        return _ok(_ra.list_products_with_recipe_status(_PROJECT_ROOT))
    except Exception as exc:
        return _err(exc)


# ── PART C — Reçete ──────────────────────────────────────────────────────────

@api_bp.route("/recipe/<barkod>")
def get_recipe(barkod: str):
    try:
        from webui_backend import recipe_api as _ra
        return _ok(_ra.get_recipe(_PROJECT_ROOT, barkod))
    except Exception as exc:
        return _err(exc)


@api_bp.route("/save_recipe", methods=["POST"])
def save_recipe():
    try:
        from webui_backend import recipe_api as _ra
        payload = request.get_json() or {}
        barkod = payload.get("barkod", "")
        slots = payload.get("slots", [])
        result = _ra.save_recipe(_PROJECT_ROOT, barkod, slots)
        if result.get("status") == "ERROR":
            return jsonify(result), 400
        return _ok(result)
    except Exception as exc:
        return _err(exc)


# ── PART D — Toplu Uygula ────────────────────────────────────────────────────

@api_bp.route("/bulk_apply_recipe", methods=["POST"])
def bulk_apply_recipe():
    try:
        from webui_backend import recipe_api as _ra
        payload = request.get_json() or {}
        barkodlar = payload.get("barkodlar", [])
        ayarlar = payload.get("ayarlar", {})
        result = _ra.bulk_apply_recipe(_PROJECT_ROOT, barkodlar, ayarlar)
        if result.get("status") == "ERROR":
            return jsonify(result), 400
        return _ok(result)
    except Exception as exc:
        return _err(exc)
