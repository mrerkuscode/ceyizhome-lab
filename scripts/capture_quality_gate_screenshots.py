from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


LABEL_TEXT = "Ayşe & Mehmet QA"
DATE_TEXT = "15.05.26"
NOTE_TEXT = "Nişan hatırası"
TEMPLATE_PATH = "templates/designs/01_a_gold.json"
OUTPUT_ROOT = PROJECT_ROOT / "output" / date.today().isoformat()
QUALITY_GATE_RESULT = OUTPUT_ROOT / "quality_gate" / "REAL_PRODUCTION_QUALITY_GATE_RESULT.json"


def latest_quality_gate_paths() -> tuple[str, str]:
    if not QUALITY_GATE_RESULT.exists():
        return "", ""
    result = json.loads(QUALITY_GATE_RESULT.read_text(encoding="utf-8"))
    pdf_path = Path(result.get("batch_pdf_path") or result.get("final_pdf_path") or "")
    png_path = Path(result.get("final_png_path") or "")
    pdf_relative = str(pdf_path.relative_to(PROJECT_ROOT)).replace("\\", "/") if pdf_path.exists() else ""
    png_relative = str(png_path.relative_to(PROJECT_ROOT)).replace("\\", "/") if png_path.exists() else ""
    return pdf_relative, png_relative


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def main() -> int:
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1500, 900)
    window.show()
    output_dir = OUTPUT_ROOT / "quality_gate"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_relative, png_relative = latest_quality_gate_paths()

    steps = [
        (
            "quality_gate_live_canvas.png",
            f"""
            showSection('label');
            useModelForManual({js_string(TEMPLATE_PATH)});
            document.getElementById('manualText').value = {js_string(LABEL_TEXT)};
            document.getElementById('manualDateText').value = {js_string(DATE_TEXT)};
            document.getElementById('manualNoteText').value = {js_string(NOTE_TEXT)};
            updateManualFieldValue('label_text', {js_string(LABEL_TEXT)});
            updateManualFieldValue('date_text', {js_string(DATE_TEXT)});
            updateManualFieldValue('note_text', {js_string(NOTE_TEXT)});
            """,
            1200,
        ),
        (
            "quality_gate_model_dropdown.png",
            "toggleManualModelDropdown(true);",
            900,
        ),
        (
            "quality_gate_pdf_preview_modal.png",
            f"openPdfPreview({js_string(pdf_relative)});",
            1800,
        ),
        (
            "quality_gate_png_preview.png",
            f"""
            const modal = document.getElementById('pdfPreviewModal');
            if (modal) modal.hidden = true;
            showSection('labelOutputs');
            selectLabelOutput({js_string(png_relative)});
            """,
            1200,
        ),
        (
            "quality_gate_print_queue.png",
            "showSection('printQueue');",
            900,
        ),
    ]
    index = {"value": 0}

    def run_next() -> None:
        if index["value"] >= len(steps):
            window.close()
            app.quit()
            return
        filename, script, delay = steps[index["value"]]
        window.view.page().runJavaScript(script)
        QTimer.singleShot(delay, lambda: save_current(filename))

    def save_current(filename: str) -> None:
        pixmap = window.view.grab()
        pixmap.save(str(output_dir / filename))
        index["value"] += 1
        QTimer.singleShot(350, run_next)

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(2200, run_next))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
