from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from seed_clean_customer_demo_data import DEMO_JOBS, SEED_MARKER  # noqa: E402
from webui_backend.print_queue_api import add_to_print_queue, list_print_queue, metadata_from_output_path, save_print_queue  # noqa: E402


def test_clean_customer_demo_jobs_do_not_use_qa_names() -> None:
    forbidden = ("qa", "test", "debug", "report")
    for job in DEMO_JOBS:
        haystack = " ".join(str(job.get(key, "")) for key in ("key", "label_text", "template")).lower()
        assert not any(token in haystack for token in forbidden)


def test_clean_customer_demo_jobs_keep_customer_facing_turkish_text() -> None:
    mojibake_markers = ("Ã", "Ä", "Å")
    expected_notes = {"Nişan Hatırası", "Söz Hatırası", "Tepsi Üzeri"}

    notes = {str(job.get("note_text", "")) for job in DEMO_JOBS}
    visible_text = " ".join(
        str(job.get(key, "")) for job in DEMO_JOBS for key in ("label_text", "note_text", "queue_status")
    )

    assert expected_notes <= notes
    assert not any(marker in visible_text for marker in mojibake_markers)


def test_clean_customer_filename_metadata_is_customer_facing() -> None:
    metadata = metadata_from_output_path(
        "output/2026-05-14/print/manual/2026-05-14_01-A-Gold-Rulo-Etiket_Elif-Kaan_50x30_10adet_batch.pdf"
    )

    assert metadata["model_name"] == "01 A Gold Rulo Etiket"
    assert metadata["label_text"] == "Elif Kaan"
    assert metadata["size_text"] == "50 x 30 mm"
    assert metadata["quantity"] == "10"


def test_demo_seed_queue_rows_can_be_replaced_without_touching_user_rows(tmp_path: Path) -> None:
    pdf = tmp_path / "output" / "2026-05-14" / "print" / "manual" / "2026-05-14_01-A-Gold-Rulo-Etiket_Elif-Kaan_50x30_10adet_batch.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\n")
    result = add_to_print_queue(
        tmp_path,
        {
            "job_name": "01 A Gold Rulo Etiket",
            "job_type": "Manuel",
            "quantity": "10",
            "file_type": "Batch PDF",
            "relative_path": pdf.relative_to(tmp_path).as_posix(),
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Elif Kaan",
            "size_text": "50 x 30 mm",
        },
    )
    rows = list_print_queue(tmp_path)
    rows[0]["demo_seed"] = SEED_MARKER
    rows.append({"id": "real-user-row", "relative_path": "output/customer.pdf", "status": "Beklemede"})
    save_print_queue(tmp_path, rows)

    filtered = [row for row in list_print_queue(tmp_path) if row.get("demo_seed") != SEED_MARKER]

    assert result["status"] == "ADDED"
    assert filtered == [{"id": "real-user-row", "relative_path": "output/customer.pdf", "status": "Beklemede"}]
