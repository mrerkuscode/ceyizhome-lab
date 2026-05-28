from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from webui_backend.print_queue_api import (
    add_pdf_output_to_queue,
    list_print_queue,
    metadata_from_output_path,
    paired_preview_uri,
    print_queue_item_safe,
)


def test_output_filename_metadata_fallback_extracts_customer_fields() -> None:
    metadata = metadata_from_output_path(
        "output/2026-05-13/print/manual/2026-05-13_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_3adet_batch_41.pdf"
    )

    assert metadata["model_name"] == "01 A Gold Rulo Etiket"
    assert metadata["label_text"] == "Ayse Mehmet QA"
    assert metadata["size_text"] == "50 x 30 mm"
    assert metadata["quantity"] == "3"


def test_add_pdf_to_queue_enriches_metadata_and_preview(tmp_path: Path) -> None:
    pdf = tmp_path / "output" / "2026-05-13" / "print" / "manual" / "2026-05-13_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_41.pdf"
    png = pdf.with_name("2026-05-13_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_41.png")
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\n% safe test\n")
    png.write_bytes(b"\x89PNG\r\n\x1a\n")

    result = add_pdf_output_to_queue(tmp_path, str(pdf.relative_to(tmp_path)).replace("\\", "/"))
    rows = list_print_queue(tmp_path)

    assert result["status"] == "ADDED"
    assert len(rows) == 1
    assert rows[0]["model_name"] == "01 A Gold Rulo Etiket"
    assert rows[0]["label_text"] == "Ayse Mehmet QA"
    assert rows[0]["size_text"] == "50 x 30 mm"
    assert rows[0]["quantity"] == "1"
    assert rows[0]["preview_uri"].startswith("file:")
    assert paired_preview_uri(tmp_path, rows[0]["relative_path"]).startswith("file:")
    safe = print_queue_item_safe(tmp_path, rows[0]["id"], direct_print_enabled=False)
    assert safe["status"] == "MANUAL_PRINT_REQUIRED"


def test_print_queue_safe_print_blocks_missing_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "output" / "2026-05-13" / "print" / "manual" / "2026-05-13_01-A-Gold-Rulo-Etiket_Ayse_50x30_1adet_batch.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\n")
    result = add_pdf_output_to_queue(tmp_path, str(pdf.relative_to(tmp_path)).replace("\\", "/"))
    pdf.unlink()

    safe = print_queue_item_safe(tmp_path, result["id"], direct_print_enabled=False)

    assert safe["status"] == "ERROR"
    assert "PDF dosyası bulunamadı" in safe["message"]
