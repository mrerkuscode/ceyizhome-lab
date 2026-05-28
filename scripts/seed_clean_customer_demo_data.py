from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from label_designer.manual_label_service import render_manual_label  # noqa: E402
from label_designer.template_loader import load_template  # noqa: E402
from webui_backend.file_api import to_web_file_url  # noqa: E402
from webui_backend.print_queue_api import add_to_print_queue, list_print_queue, save_print_queue  # noqa: E402
from webui_backend.production_safety import preflight_manual_label, validate_manual_output  # noqa: E402


SEED_MARKER = "clean_customer_demo_v1"

DEMO_JOBS = [
    {
        "key": "elif_kaan",
        "template": "templates/designs/01_a_gold.json",
        "label_text": "Elif Kaan",
        "date_text": "15.05.2026",
        "note_text": "Nişan Hatırası",
        "quantity": 10,
        "queue_status": "Beklemede",
        "delivery_status": "Teslim bekliyor",
    },
    {
        "key": "burcu_baran",
        "template": "templates/designs/03_a_gold.json",
        "label_text": "Burcu Baran",
        "date_text": "20.06.2026",
        "note_text": "Söz Hatırası",
        "quantity": 5,
        "queue_status": "Yazdırıldı",
        "delivery_status": "Teslim bekliyor",
    },
    {
        "key": "sedef_sefer",
        "template": "templates/designs/01_a_gold.json",
        "label_text": "Sedef Sefer",
        "date_text": "01.07.2026",
        "note_text": "Tepsi Üzeri",
        "quantity": 2,
        "queue_status": "Teslim edildi",
        "delivery_status": "Teslim edildi",
    },
]


def _relative(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _write_json_list(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _history_path(project_root: Path) -> Path:
    return project_root / "data" / "production_history.json"


def _remove_previous_seed_rows(project_root: Path) -> None:
    history_path = _history_path(project_root)
    history_rows = [row for row in _read_json_list(history_path) if row.get("demo_seed") != SEED_MARKER]
    _write_json_list(history_path, history_rows[-500:])

    queue_rows = [row for row in list_print_queue(project_root) if row.get("demo_seed") != SEED_MARKER]
    save_print_queue(project_root, queue_rows)


def _payload_for_job(template_path: Path, job: dict[str, Any]) -> dict[str, Any]:
    template = load_template(template_path)
    return {
        "label_text": job["label_text"],
        "date_text": job["date_text"],
        "note_text": job["note_text"],
        "_studio_render_state": "true",
        "_background_image": template.preview_image or template.background_image,
        "_label_width_mm": template.label_width_mm,
        "_label_height_mm": template.label_height_mm,
        "_fields": [dict(field) for field in template.fields],
    }


def _render_job(project_root: Path, job: dict[str, Any]) -> dict[str, Any]:
    template_path = project_root / job["template"]
    template = load_template(template_path)
    template_name = template.model_name or template.template_id
    payload = _payload_for_job(template_path, job)
    preflight = preflight_manual_label(project_root, template_path, payload, int(job["quantity"]))
    if preflight.get("status") == "ERROR":
        raise RuntimeError(f"Demo üretim preflight hatası: {job['label_text']} - {preflight}")

    started_at = datetime.now().timestamp()
    render_result = render_manual_label(
        project_root,
        template_path,
        str(job["label_text"]),
        int(job["quantity"]),
        date.today(),
        payload,
    )
    render_dict = {
        "output_dir": str(render_result.output_dir),
        "pdf_path": str(render_result.pdf_path),
        "png_path": str(render_result.png_path),
        "batch_pdf_path": str(render_result.batch_pdf_path),
        "quantity": render_result.quantity,
    }
    validation = validate_manual_output(project_root, render_dict, payload | {"_render_started_at": started_at})
    if validation.get("status") != "OK":
        raise RuntimeError(f"Demo üretim doğrulaması başarısız: {job['label_text']} - {validation}")

    relative_batch = _relative(render_result.batch_pdf_path, project_root)
    relative_png = _relative(render_result.png_path, project_root)
    size_text = f"{template.label_width_mm:g} x {template.label_height_mm:g} mm"
    queue_result = add_to_print_queue(
        project_root,
        {
            "job_type": "Manuel",
            "quantity": str(job["quantity"]),
            "file_type": "Batch PDF",
            "relative_path": relative_batch,
            "preview_uri": to_web_file_url(render_result.png_path, project_root),
            "job_name": template_name,
            "model_name": template_name,
            "label_text": str(job["label_text"]),
            "size_text": size_text,
            "status": str(job["queue_status"]),
        },
    )

    queue_rows = list_print_queue(project_root)
    for row in queue_rows:
        if row.get("relative_path") == relative_batch:
            row.update(
                {
                    "demo_seed": SEED_MARKER,
                    "demo_key": job["key"],
                    "date_text": str(job["date_text"]),
                    "note_text": str(job["note_text"]),
                    "validation_status": "OK",
                    "delivery_status": str(job["delivery_status"]),
                    "status": str(job["queue_status"]),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
    save_print_queue(project_root, queue_rows)

    return {
        "id": f"{SEED_MARKER}_{job['key']}",
        "demo_seed": SEED_MARKER,
        "demo_key": job["key"],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model_name": template_name,
        "model_id": template.template_id,
        "model_path": _relative(template_path, project_root),
        "label_text": str(job["label_text"]),
        "date_text": str(job["date_text"]),
        "note_text": str(job["note_text"]),
        "quantity": str(job["quantity"]),
        "width_mm": str(template.label_width_mm),
        "height_mm": str(template.label_height_mm),
        "pdf_path": relative_batch,
        "png_path": relative_png,
        "queue_status": str(queue_result.get("status") or "ADDED"),
        "preflight_status": str(preflight.get("status") or ""),
        "output_validation_status": str(validation.get("status") or ""),
    }


def seed_clean_customer_demo_data(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    _remove_previous_seed_rows(project_root)
    records = [_render_job(project_root, job) for job in DEMO_JOBS]
    history_path = _history_path(project_root)
    history_rows = _read_json_list(history_path)
    history_rows.extend(records)
    _write_json_list(history_path, history_rows[-500:])
    return {
        "status": "OK",
        "seed": SEED_MARKER,
        "records": records,
        "history_path": _relative(history_path, project_root),
        "queue_count": len([row for row in list_print_queue(project_root) if row.get("demo_seed") == SEED_MARKER]),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    result = seed_clean_customer_demo_data(PROJECT_ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
