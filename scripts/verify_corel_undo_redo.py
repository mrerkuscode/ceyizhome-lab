from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from verify_corel_editor_interactions import (  # noqa: E402
    drag_pointer,
    field_num,
    run_js,
    save_screenshot,
    setup_studio,
    snapshot,
    wait,
)


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "report_verification"
RESULT_PATH = OUTPUT_DIR / "COREL_UNDO_REDO_VERIFICATION_RESULT.json"


def reset_history(window: WebMainWindow) -> None:
    run_js(
        window,
        """
        (() => {
          manualUndoStack = [];
          manualRedoStack = [];
          manualFieldClipboard = null;
          updateUndoRedoButtons();
          return { undo: manualUndoStack.length, redo: manualRedoStack.length };
        })()
        """,
    )
    wait(150)


def assert_close(actual: float, expected: float, label: str, tolerance: float = 0.12) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{label} expected {expected}, got {actual}")


def assert_field_matches(actual: dict, expected: dict, keys: list[str], label: str) -> None:
    for key in keys:
        assert_close(float(actual.get(key) or 0), float(expected.get(key) or 0), f"{label}.{key}")


def selected_text(window: WebMainWindow) -> str:
    return run_js(window, "(() => getCurrentFieldValues()[selectedManualField()?.excel_column || 'label_text'] || '')()")


def exec_js(window: WebMainWindow, body: str) -> dict:
    return run_js(window, f"(() => {{ {body}; return {{ ok: true }}; }})()")


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    setup_studio(window, "fit", "label_text")
    reset_history(window)
    before_text = selected_text(window)
    exec_js(window, "updateManualFieldValue('label_text', 'Undo Redo QA Text')")
    changed_text = selected_text(window)
    if changed_text == before_text:
        raise AssertionError("Text change did not apply before undo")
    exec_js(window, "undoManualEdit()")
    wait(200)
    undone_text = selected_text(window)
    if undone_text != before_text:
        raise AssertionError(f"Text undo failed: before={before_text!r}, undone={undone_text!r}")
    exec_js(window, "redoManualEdit()")
    wait(200)
    redone_text = selected_text(window)
    if redone_text != changed_text:
        raise AssertionError(f"Text redo failed: changed={changed_text!r}, redone={redone_text!r}")
    checks.append({"name": "text_change_undo_redo", "status": "PASSED", "before": before_text, "after": redone_text})

    setup_studio(window, "fit", "label_text")
    reset_history(window)
    before_drag = snapshot(window)
    drag_pointer(window, before_drag["center"], 34, 14)
    wait(250)
    after_drag = snapshot(window)
    exec_js(window, "undoManualEdit()")
    wait(250)
    drag_undo = snapshot(window)
    exec_js(window, "redoManualEdit()")
    wait(250)
    drag_redo = snapshot(window)
    assert_field_matches(drag_undo["field"], before_drag["field"], ["x_mm", "y_mm", "width_mm", "height_mm"], "drag undo")
    assert_field_matches(drag_redo["field"], after_drag["field"], ["x_mm", "y_mm", "width_mm", "height_mm"], "drag redo")
    checks.append({"name": "drag_undo_redo", "status": "PASSED", "before": before_drag["field"], "redo": drag_redo["field"]})

    reset_history(window)
    before_resize = snapshot(window)
    drag_pointer(window, before_resize["handles"]["se"], 36, 18)
    wait(250)
    after_resize = snapshot(window)
    exec_js(window, "undoManualEdit()")
    wait(250)
    resize_undo = snapshot(window)
    exec_js(window, "redoManualEdit()")
    wait(250)
    resize_redo = snapshot(window)
    assert_field_matches(resize_undo["field"], before_resize["field"], ["width_mm", "height_mm", "font_size"], "resize undo")
    assert_field_matches(resize_redo["field"], after_resize["field"], ["width_mm", "height_mm", "font_size"], "resize redo")
    checks.append({"name": "corner_resize_undo_redo", "status": "PASSED", "before": before_resize["field"], "redo": resize_redo["field"]})

    setup_studio(window, "fit", "label_text")
    reset_history(window)
    before_style = snapshot(window)["field"]
    exec_js(window, "applyColorSwatch('#b7791f'); applyFontPreset('minimal')")
    wait(250)
    after_style = snapshot(window)["field"]
    if (
        after_style.get("color") == before_style.get("color")
        and after_style.get("font_family") == before_style.get("font_family")
        and float(after_style.get("font_size") or 0) == float(before_style.get("font_size") or 0)
    ):
        raise AssertionError(f"Style change did not apply: before={before_style}, after={after_style}")
    exec_js(window, "undoManualEdit(); undoManualEdit()")
    wait(250)
    style_undo = snapshot(window)["field"]
    exec_js(window, "redoManualEdit(); redoManualEdit()")
    wait(250)
    style_redo = snapshot(window)["field"]
    if style_undo.get("color") != before_style.get("color"):
        raise AssertionError(f"Color undo failed: before={before_style}, undo={style_undo}")
    if (
        style_redo.get("color") != after_style.get("color")
        or style_redo.get("font_family") != after_style.get("font_family")
        or abs(float(style_redo.get("font_size") or 0) - float(after_style.get("font_size") or 0)) > 0.12
    ):
        raise AssertionError(f"Style redo failed: after={after_style}, redo={style_redo}")
    checks.append({"name": "font_color_undo_redo", "status": "PASSED", "before": before_style, "redo": style_redo})

    setup_studio(window, "fit", "label_text")
    reset_history(window)
    layer_result = run_js(
        window,
        """
        (() => {
          const before = { ...selectedManualField() };
          toggleLayerVisibility(selectedFieldIndex, { stopPropagation(){} });
          const hidden = { ...selectedManualField() };
          undoManualEdit();
          const undoHidden = { ...selectedManualField() };
          redoManualEdit();
          const redoHidden = { ...selectedManualField() };
          toggleLayerLock(selectedFieldIndex, { stopPropagation(){} });
          const locked = { ...selectedManualField() };
          undoManualEdit();
          const unlockUndo = { ...selectedManualField() };
          redoManualEdit();
          const lockRedo = { ...selectedManualField() };
          return { before, hidden, undoHidden, redoHidden, locked, unlockUndo, lockRedo };
        })()
        """,
    )
    if layer_result["hidden"].get("visible") is not False or layer_result["undoHidden"].get("visible") is False or layer_result["redoHidden"].get("visible") is not False:
        raise AssertionError(f"Layer visibility undo/redo failed: {layer_result}")
    if layer_result["locked"].get("locked") is not True or layer_result["unlockUndo"].get("locked") is True or layer_result["lockRedo"].get("locked") is not True:
        raise AssertionError(f"Layer lock undo/redo failed: {layer_result}")
    checks.append({"name": "layer_visibility_lock_undo_redo", "status": "PASSED", "details": layer_result})

    setup_studio(window, "fit", "label_text")
    reset_history(window)
    before_auto = snapshot(window)
    exec_js(window, "autoArrangeManualFields()")
    wait(250)
    after_auto = snapshot(window)
    exec_js(window, "undoManualEdit()")
    wait(250)
    auto_undo = snapshot(window)
    exec_js(window, "redoManualEdit()")
    wait(250)
    auto_redo = snapshot(window)
    assert_field_matches(auto_undo["field"], before_auto["field"], ["x_mm", "y_mm", "width_mm", "height_mm"], "auto layout undo")
    assert_field_matches(auto_redo["field"], after_auto["field"], ["x_mm", "y_mm", "width_mm", "height_mm"], "auto layout redo")
    checks.append({"name": "auto_layout_undo_redo", "status": "PASSED", "before": before_auto["field"], "redo": auto_redo["field"]})

    setup_studio(window, "fit", "label_text")
    reset_history(window)
    duplicate_result = run_js(
        window,
        """
        (() => {
          const beforeCount = (selectedLabelModel?.fields_summary || []).length;
          copySelectedField();
          duplicateSelectedField();
          const duplicated = selectedManualField();
          const afterCount = (selectedLabelModel?.fields_summary || []).length;
          const payloadAfterDuplicate = manualPayload()._fields.find(item => item.excel_column === duplicated?.excel_column);
          undoManualEdit();
          const undoCount = (selectedLabelModel?.fields_summary || []).length;
          redoManualEdit();
          const redoCount = (selectedLabelModel?.fields_summary || []).length;
          const redoField = selectedManualField();
          deleteSelectedLayer();
          const deleteCount = (selectedLabelModel?.fields_summary || []).length;
          undoManualEdit();
          const deleteUndoCount = (selectedLabelModel?.fields_summary || []).length;
          return { beforeCount, afterCount, duplicated, payloadAfterDuplicate, undoCount, redoCount, redoField, deleteCount, deleteUndoCount };
        })()
        """,
    )
    if duplicate_result["afterCount"] != duplicate_result["beforeCount"] + 1:
        raise AssertionError(f"Duplicate did not add a text layer: {duplicate_result}")
    if not duplicate_result.get("payloadAfterDuplicate"):
        raise AssertionError(f"Duplicated custom text did not reach payload: {duplicate_result}")
    if duplicate_result["undoCount"] != duplicate_result["beforeCount"] or duplicate_result["redoCount"] != duplicate_result["beforeCount"] + 1:
        raise AssertionError(f"Duplicate undo/redo failed: {duplicate_result}")
    if duplicate_result["deleteCount"] != duplicate_result["beforeCount"] or duplicate_result["deleteUndoCount"] != duplicate_result["beforeCount"] + 1:
        raise AssertionError(f"Delete undo failed: {duplicate_result}")
    screenshots["undo_redo_duplicate"] = save_screenshot(window, "undo_redo_duplicate.png")
    checks.append({"name": "copy_duplicate_delete_undo_redo_payload", "status": "PASSED", "details": duplicate_result})

    run_js(window, "(() => { const index = (selectedLabelModel?.fields_summary || []).findIndex(field => field.excel_column === 'label_text'); selectField(index >= 0 ? index : 0); return selectedManualField(); })()")
    wait(200)
    payload = run_js(window, "manualPayload()")
    label_payload = next((item for item in payload.get("_fields", []) if item.get("excel_column") == "label_text"), None)
    current = snapshot(window)["field"]
    if not label_payload:
        raise AssertionError(f"Payload missing label_text after undo/redo gate: {payload}")
    for key in ["x_mm", "y_mm", "width_mm", "height_mm", "font_size"]:
        assert_close(float(label_payload.get(key) or 0), field_num({"field": current}, key), f"payload.{key}")
    checks.append({"name": "payload_after_undo_redo_is_current", "status": "PASSED", "payload": label_payload})

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots}


def main() -> int:
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1600, 950)
    window.show()

    outcome = {"status": "ERROR", "message": "not started"}

    def start() -> None:
        nonlocal outcome
        try:
            outcome = run_gate(window)
        except Exception as exc:  # noqa: BLE001 - report exact verification failure.
            outcome = {"status": "ERROR", "message": str(exc)}
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        os._exit(0 if outcome.get("status") == "PASSED" else 1)

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(5600, start))
    code = app.exec()
    return 0 if outcome.get("status") == "PASSED" and code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
