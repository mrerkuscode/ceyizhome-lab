from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


TEMPLATE_PATH = "templates/designs/01_a_gold.json"
OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "studio_interaction"
RESULT_PATH = OUTPUT_DIR / "STUDIO_CANVAS_INTERACTION_GATE_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 30000):
    loop = QEventLoop()
    result = {"value": None, "done": False}

    def callback(value):
        result["value"] = value
        result["done"] = True
        loop.quit()

    wrapped = f"""
    (() => {{
      try {{
        return JSON.stringify(({script}));
      }} catch (error) {{
        return JSON.stringify({{ "__error": String(error && error.message || error) }});
      }}
    }})()
    """
    window.view.page().runJavaScript(wrapped, callback)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if not result["done"]:
        raise RuntimeError(f"JavaScript timed out: {script[:120]}")
    value = result["value"]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        if isinstance(parsed, dict) and parsed.get("__error"):
            raise RuntimeError(parsed["__error"])
        return parsed
    return value


SNAPSHOT_JS = """
(() => {
  const fields = selectedLabelModel?.fields_summary || [];
  const box = document.querySelector('.field-box.selected') || document.querySelector('.field-box[data-field-index="0"]');
  if (!box || !fields[selectedFieldIndex]) return { ok: false, error: 'selected field box missing' };
  const rect = box.getBoundingClientRect();
  const handleRect = (name) => {
    const item = box.querySelector(`.handle-${name}`);
    if (!item) return null;
    const r = item.getBoundingClientRect();
    return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), width: r.width, height: r.height };
  };
  const center = { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) };
  const hit = document.elementFromPoint(center.x, center.y);
  return {
    ok: true,
    selectedFieldIndex,
    activeTag: document.activeElement?.tagName || '',
    activeClass: String(document.activeElement?.className || ''),
    field: { ...fields[selectedFieldIndex] },
    center,
    hitClass: String(hit?.className || hit?.tagName || ''),
    handles: { se: handleRect('se'), e: handleRect('e'), s: handleRect('s') }
  };
})()
"""


def setup_studio(window: WebMainWindow, zoom: str = "fit", column: str = "label_text") -> dict:
    script = f"""
    (() => {{
      try {{
      showSection('label');
      const target = {json.dumps(TEMPLATE_PATH)};
      const targetModel = currentLabelModels.find(model => String(model.path || '').replace(/\\\\/g, '/').endsWith(target));
      if (targetModel) useModelForManual(targetModel.path);
      document.getElementById('manualText').value = 'Ayşe & Mehmet QA';
      document.getElementById('manualDateText').value = '15.05.26';
      document.getElementById('manualNoteText').value = 'Nişan hatırası';
      updateManualFieldValue('label_text', 'Ayşe & Mehmet QA');
      updateManualFieldValue('date_text', '15.05.26');
      updateManualFieldValue('note_text', 'Nişan hatırası');
      setManualZoom({json.dumps(zoom)});
      const idx = (selectedLabelModel?.fields_summary || []).findIndex(f => f.excel_column === {json.dumps(column)});
      selectField(idx >= 0 ? idx : 0);
      const defaults = {{
        label_text: {{ x_mm: 10, y_mm: 12, width_mm: 30, height_mm: 6, font_size: 14 }},
        date_text: {{ x_mm: 17, y_mm: 17, width_mm: 16, height_mm: 4, font_size: 8 }},
        note_text: {{ x_mm: 12, y_mm: 21, width_mm: 26, height_mm: 4, font_size: 8 }}
      }}[{json.dumps(column)}];
      if (defaults) applyFieldGeometry(selectedFieldIndex, {{ ...(selectedLabelModel?.fields_summary || [])[selectedFieldIndex], ...defaults }}, {{ snap: false }});
      document.activeElement?.blur?.();
      document.querySelector('.field-box.selected')?.focus({{ preventScroll: true }});
      scrollSelectedFieldIntoCanvasView();
      return {{ ok: Boolean(selectedLabelModel), zoom: {json.dumps(zoom)}, column: {json.dumps(column)}, modelCount: currentLabelModels.length, selectedPath: selectedLabelModel?.path || '' }};
      }} catch (error) {{
        return {{ ok: false, error: String(error && error.message || error), stack: String(error && error.stack || '') }};
      }}
    }})()
    """
    result = run_js(window, script, timeout_ms=60000)
    wait(650)
    if not result or not result.get("ok"):
        raise RuntimeError(f"Etiket Studio model setup failed: {result}")
    return snapshot(window)


def snapshot(window: WebMainWindow) -> dict:
    result = run_js(window, SNAPSHOT_JS)
    if not result or not result.get("ok"):
        raise RuntimeError(result.get("error") if isinstance(result, dict) else "Snapshot failed")
    return result


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    window.view.grab().save(str(path))
    return str(path)



def drag_mouse(window: WebMainWindow, start: dict, dx: int, dy: int) -> None:
    sx = int(start["x"])
    sy = int(start["y"])
    mx = int(start["x"] + dx / 2)
    my = int(start["y"] + dy / 2)
    ex = int(start["x"] + dx)
    ey = int(start["y"] + dy)
    event_helper = """
      const EventClass = window.PointerEvent || MouseEvent;
      const eventName = (type) => window.PointerEvent
        ? ({ down: 'pointerdown', move: 'pointermove', up: 'pointerup' }[type])
        : ({ down: 'mousedown', move: 'mousemove', up: 'mouseup' }[type]);
      const fire = (target, type, x, y) => target.dispatchEvent(new EventClass(eventName(type), {
        bubbles: true,
        cancelable: true,
        clientX: x,
        clientY: y,
        button: 0,
        buttons: type === 'up' ? 0 : 1,
        pointerId: 17,
        pointerType: 'mouse',
        isPrimary: true,
        view: window
      }));
    """
    down = run_js(window, f"""
    (() => {{
      window.__dragErrors = [];
      window.onerror = (message, source, line, column, error) => {{
        window.__dragErrors.push(String(message || error || 'unknown'));
      }};
      {event_helper}
      const target = document.elementFromPoint({sx}, {sy});
      if (!target) return {{ ok: false, error: 'no hit target' }};
      fire(target, 'down', {sx}, {sy});
      const started = Boolean(activeDrag);
      return {{ ok: true, hit: String(target.className || target.tagName || ''), started }};
    }})()
    """)
    if not down or not down.get("ok") or not down.get("started"):
        raise RuntimeError(f"DOM pointer down failed at {start}: {down}")
    wait(90)
    mid = run_js(window, f"(() => {{ {event_helper} fire(window, 'move', {mx}, {my}); return {{ ok: true, moved: Boolean(activeDrag && activeDrag.moved), field: selectedLabelModel?.fields_summary?.[selectedFieldIndex] || null, errors: window.__dragErrors || [] }}; }})()")
    wait(140)
    end_move = run_js(window, f"(() => {{ {event_helper} fire(window, 'move', {ex}, {ey}); return {{ ok: true, moved: Boolean(activeDrag && activeDrag.moved), field: selectedLabelModel?.fields_summary?.[selectedFieldIndex] || null, errors: window.__dragErrors || [] }}; }})()")
    wait(140)
    up = run_js(window, f"(() => {{ {event_helper} const beforeUp = selectedLabelModel?.fields_summary?.[selectedFieldIndex] || null; fire(window, 'up', {ex}, {ey}); const afterUp = selectedLabelModel?.fields_summary?.[selectedFieldIndex] || null; return {{ ok: true, active: Boolean(activeDrag), beforeUp, afterUp, errors: window.__dragErrors || [] }}; }})()")
    drag_mouse.last_result = {"down": down, "mid": mid, "end_move": end_move, "up": up}
    wait(550)


drag_mouse.last_result = {}


def field_float(snapshot_data: dict, key: str) -> float:
    return float(snapshot_data["field"].get(key) or 0)


def assert_changed(before: dict, after: dict, keys: list[str], label: str) -> None:
    changed = [key for key in keys if abs(field_float(after, key) - field_float(before, key)) >= 0.05]
    if not changed:
        raise AssertionError(f"{label} geometry did not change for {keys}: event={drag_mouse.last_result}, before={before}, after={after}")


def assert_inside(snapshot_data: dict) -> None:
    field = snapshot_data["field"]
    model = run_js(assert_inside.window, "selectedLabelModel")  # type: ignore[attr-defined]
    width = float(model.get("label_width_mm") or 50)
    height = float(model.get("label_height_mm") or 30)
    x = float(field.get("x_mm") or 0)
    y = float(field.get("y_mm") or 0)
    w = float(field.get("width_mm") or 0)
    h = float(field.get("height_mm") or 0)
    if x < -0.01 or y < -0.01 or x + w > width + 0.01 or y + h > height + 0.01:
        raise AssertionError(f"Field left label bounds: field={field}, label={width}x{height}")


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assert_inside.window = window  # type: ignore[attr-defined]
    screenshots: dict[str, str] = {}
    checks: list[dict[str, object]] = []

    before = setup_studio(window, "fit")
    screenshots["drag_before"] = save_screenshot(window, "studio_drag_before.png")
    drag_mouse(window, before["center"], 46, 18)
    after_drag = snapshot(window)
    screenshots["drag_after"] = save_screenshot(window, "studio_drag_after.png")
    assert_changed(before, after_drag, ["x_mm", "y_mm"], "fit drag")
    assert after_drag["selectedFieldIndex"] == before["selectedFieldIndex"]
    assert_inside(after_drag)
    checks.append({"name": "fit_drag", "status": "PASSED", "before": before["field"], "after": after_drag["field"]})

    run_js(window, "(() => { undoManualEdit(); return { undo: manualUndoStack.length, redo: manualRedoStack.length, field: selectedLabelModel?.fields_summary?.[selectedFieldIndex] || null }; })()")
    wait(300)
    after_undo = snapshot(window)
    for key in ["x_mm", "y_mm", "width_mm", "height_mm"]:
        if abs(field_float(after_undo, key) - field_float(before, key)) > 0.11:
            raise AssertionError(f"Undo did not restore {key}: before={before['field']}, after_undo={after_undo['field']}")
    run_js(window, "(() => { redoManualEdit(); return { undo: manualUndoStack.length, redo: manualRedoStack.length, field: selectedLabelModel?.fields_summary?.[selectedFieldIndex] || null }; })()")
    wait(300)
    after_redo = snapshot(window)
    for key in ["x_mm", "y_mm", "width_mm", "height_mm"]:
        if abs(field_float(after_redo, key) - field_float(after_drag, key)) > 0.11:
            raise AssertionError(f"Redo did not restore {key}: after_drag={after_drag['field']}, after_redo={after_redo['field']}")
    checks.append({"name": "undo_redo_drag_state", "status": "PASSED", "before": before["field"], "undo": after_undo["field"], "redo": after_redo["field"]})

    before_resize = snapshot(window)
    drag_mouse(window, before_resize["handles"]["se"], 50, 24)
    after_resize = snapshot(window)
    screenshots["resize_after"] = save_screenshot(window, "studio_resize_after.png")
    assert_changed(before_resize, after_resize, ["width_mm", "height_mm", "font_size"], "corner resize")
    assert_inside(after_resize)
    checks.append({"name": "corner_resize", "status": "PASSED", "before": before_resize["field"], "after": after_resize["field"]})

    # Reset before side-resize checks. The preceding corner-resize intentionally
    # pushes the field near the right/bottom label bounds; testing an east/south
    # grow from that clamped position would prove only that bounds protection
    # works, not that the side handles are interactive.
    before_side = setup_studio(window, "fit")
    drag_mouse(window, before_side["handles"]["e"], 34, 0)
    after_side = snapshot(window)
    assert_changed(before_side, after_side, ["width_mm"], "side resize east")
    font_delta = abs(field_float(after_side, "font_size") - field_float(before_side, "font_size"))
    if font_delta > 0.11:
        raise AssertionError(f"Side resize changed font size aggressively: {font_delta}")
    checks.append({"name": "side_resize_width", "status": "PASSED", "before": before_side["field"], "after": after_side["field"]})

    before_bottom = setup_studio(window, "fit")
    drag_mouse(window, before_bottom["handles"]["s"], 0, 22)
    after_bottom = snapshot(window)
    assert_changed(before_bottom, after_bottom, ["height_mm"], "side resize south")
    assert_inside(after_bottom)
    checks.append({"name": "side_resize_height", "status": "PASSED", "before": before_bottom["field"], "after": after_bottom["field"]})

    for zoom in ["100", "150", "200"]:
        before_zoom = setup_studio(window, zoom)
        if zoom == "150":
            screenshots["zoom_150_before"] = save_screenshot(window, "studio_zoom_150_selected.png")
        drag_mouse(window, before_zoom["center"], 24, 12)
        after_zoom = snapshot(window)
        assert_changed(before_zoom, after_zoom, ["x_mm", "y_mm"], f"zoom {zoom} drag")
        assert_inside(after_zoom)
        checks.append({"name": f"zoom_{zoom}_drag", "status": "PASSED", "before": before_zoom["field"], "after": after_zoom["field"]})

    for zoom in ["150", "200"]:
        before_zoom_resize = setup_studio(window, zoom)
        drag_mouse(window, before_zoom_resize["handles"]["se"], 22, 14)
        after_zoom_resize = snapshot(window)
        assert_changed(before_zoom_resize, after_zoom_resize, ["width_mm", "height_mm", "font_size"], f"zoom {zoom} corner resize")
        assert_inside(after_zoom_resize)
        checks.append({"name": f"zoom_{zoom}_corner_resize", "status": "PASSED", "before": before_zoom_resize["field"], "after": after_zoom_resize["field"]})

    before_key = setup_studio(window, "fit")
    run_js(window, "(() => { const target = document.activeElement || document.querySelector('.field-box.selected') || window; target.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true, cancelable: true })); return { active: document.activeElement?.tagName || '', cls: String(document.activeElement?.className || '') }; })()")
    wait(250)
    after_key = snapshot(window)
    if abs((field_float(before_key, "x_mm") - field_float(after_key, "x_mm")) - 0.1) > 0.11:
        raise AssertionError(f"Arrow key did not move by 0.1 mm: before={before_key['field']}, after={after_key['field']}")
    run_js(window, "(() => { const target = document.activeElement || document.querySelector('.field-box.selected') || window; target.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', shiftKey: true, bubbles: true, cancelable: true })); return { active: document.activeElement?.tagName || '', cls: String(document.activeElement?.className || '') }; })()")
    wait(250)
    after_shift = snapshot(window)
    if abs((field_float(after_key, "x_mm") - field_float(after_shift, "x_mm")) - 1.0) > 0.11:
        raise AssertionError(f"Shift+Arrow did not move by 1 mm: before={after_key['field']}, after={after_shift['field']}")
    run_js(window, "(() => { const target = document.activeElement || document.querySelector('.field-box.selected') || window; target.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', altKey: true, bubbles: true, cancelable: true })); return { active: document.activeElement?.tagName || '', cls: String(document.activeElement?.className || '') }; })()")
    wait(250)
    after_alt = snapshot(window)
    if abs((field_float(after_shift, "x_mm") - field_float(after_alt, "x_mm")) - 0.05) > 0.11:
        raise AssertionError(f"Alt+Arrow did not move by 0.05 mm: before={after_shift['field']}, after={after_alt['field']}")
    checks.append({"name": "keyboard_movement", "status": "PASSED", "before": before_key["field"], "after": after_alt["field"]})

    payload = run_js(window, "manualPayload()")
    payload_fields = payload.get("_fields") or []
    if not payload_fields:
        raise AssertionError("manualPayload did not include visible fields")
    label_payload = next((item for item in payload_fields if item.get("excel_column") == "label_text"), None)
    if not label_payload:
        raise AssertionError("manualPayload did not include label_text field")
    current = snapshot(window)["field"]
    for key in ["x_mm", "y_mm", "width_mm", "height_mm", "font_size"]:
        if abs(float(label_payload.get(key) or 0) - float(current.get(key) or 0)) > 0.11:
            raise AssertionError(f"Payload geometry is stale for {key}: payload={label_payload}, current={current}")
    checks.append({"name": "payload_geometry", "status": "PASSED", "payload": label_payload})

    for column in ["date_text", "note_text"]:
        before_basic = setup_studio(window, "fit", column)
        drag_mouse(window, before_basic["center"], 18, 10)
        after_basic = snapshot(window)
        assert_changed(before_basic, after_basic, ["x_mm", "y_mm"], f"{column} drag")
        assert after_basic["selectedFieldIndex"] == before_basic["selectedFieldIndex"]
        assert_inside(after_basic)
        checks.append({"name": f"{column}_drag", "status": "PASSED", "before": before_basic["field"], "after": after_basic["field"]})

    return {"status": "PASSED", "screenshots": screenshots, "checks": checks}


def main() -> int:
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1500, 900)
    window.show()

    outcome = {"status": "ERROR", "message": "not started"}

    def start() -> None:
        nonlocal outcome
        try:
            outcome = run_gate(window)
        except Exception as exc:  # noqa: BLE001 - gate must report exact failure.
            outcome = {"status": "ERROR", "message": str(exc)}
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        window.close()
        app.quit()

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(5500, start))
    code = app.exec()
    return 0 if outcome.get("status") == "PASSED" and code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
