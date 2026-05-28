from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


TEMPLATE_PATH = "templates/designs/01_a_gold.json"
OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "report_verification"
RESULT_PATH = OUTPUT_DIR / "COREL_EDITOR_INTERACTION_VERIFICATION_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 60000):
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
        return JSON.stringify({{ "__error": String(error && error.message || error), stack: String(error && error.stack || "") }});
      }}
    }})()
    """
    window.view.page().runJavaScript(wrapped, callback)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if not result["done"]:
        raise RuntimeError(f"JavaScript timed out: {script[:160]}")
    value = result["value"]
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict) and parsed.get("__error"):
            raise RuntimeError(f"{parsed['__error']}\n{parsed.get('stack', '')}")
        return parsed
    return value


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    window.view.grab().save(str(path))
    return str(path)


def setup_studio(window: WebMainWindow, zoom: str = "fit", column: str = "label_text") -> dict:
    result = run_js(
        window,
        f"""
        (() => {{
          window.__corelVerificationAlerts = [];
          window.alert = (message) => {{ window.__corelVerificationAlerts.push(String(message || "")); }};
          showSection('label');
          const target = {json.dumps(TEMPLATE_PATH)};
          const model = currentLabelModels.find(item => String(item.path || '').replace(/\\\\/g, '/').endsWith(target));
          if (!model) return {{ ok: false, error: 'target model missing', modelCount: currentLabelModels.length }};
          useModelForManual(model.path);
          document.getElementById('manualText').value = 'Ayşe & Mehmet QA';
          document.getElementById('manualDateText').value = '15.05.26';
          document.getElementById('manualNoteText').value = 'Nişan hatırası';
          updateManualFieldValue('label_text', 'Ayşe & Mehmet QA');
          updateManualFieldValue('date_text', '15.05.26');
          updateManualFieldValue('note_text', 'Nişan hatırası');
          setManualZoom({json.dumps(zoom)});
          const idx = (selectedLabelModel?.fields_summary || []).findIndex(field => field.excel_column === {json.dumps(column)});
          selectField(idx >= 0 ? idx : 0);
          const defaults = {{
            label_text: {{ x_mm: 10, y_mm: 12, width_mm: 30, height_mm: 6, font_size: 14 }},
            date_text: {{ x_mm: 17, y_mm: 17, width_mm: 16, height_mm: 4, font_size: 8 }},
            note_text: {{ x_mm: 12, y_mm: 21, width_mm: 26, height_mm: 4, font_size: 8 }}
          }}[{json.dumps(column)}];
          if (defaults) {{
            applyFieldGeometry(selectedFieldIndex, {{ ...(selectedLabelModel?.fields_summary || [])[selectedFieldIndex], ...defaults }}, {{ snap: false, rerender: true }});
            selectedLabelModel.fields_summary[selectedFieldIndex].visible = true;
            selectedLabelModel.fields_summary[selectedFieldIndex].locked = false;
          }}
          showManualPreviewPlaceholder();
          document.activeElement?.blur?.();
          document.querySelector('.field-box.selected')?.focus({{ preventScroll: true }});
          return {{
            ok: true,
            modelName: selectedLabelModel?.model_name || '',
            selectedPath: selectedLabelModel?.path || '',
            selectedFieldIndex,
            selectedColumn: selectedManualField()?.excel_column || '',
            zoom: {json.dumps(zoom)}
          }};
        }})()
        """,
    )
    wait(700)
    if not result.get("ok"):
        raise AssertionError(f"Studio setup failed: {result}")
    return result


SNAPSHOT_JS = """
(() => {
  const fields = selectedLabelModel?.fields_summary || [];
  const field = fields[selectedFieldIndex] || null;
  const box = document.querySelector('.field-box.selected') || document.querySelector(`.field-box[data-field-index="${selectedFieldIndex}"]`);
  const rect = box?.getBoundingClientRect?.();
  const center = rect ? { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) } : null;
  const handleRect = (name) => {
    const item = box?.querySelector?.(`.handle-${name}`);
    if (!item) return null;
    const r = item.getBoundingClientRect();
    return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), width: r.width, height: r.height };
  };
  return {
    ok: Boolean(field && box && rect),
    selectedFieldIndex,
    field: field ? { ...field } : null,
    center,
    rect: rect ? { left: rect.left, top: rect.top, width: rect.width, height: rect.height } : null,
    handles: { se: handleRect('se'), e: handleRect('e'), s: handleRect('s') },
    payloadField: (manualPayload()._fields || []).find(item => item.excel_column === field?.excel_column) || null
  };
})()
"""


def snapshot(window: WebMainWindow) -> dict:
    result = run_js(window, SNAPSHOT_JS)
    if not result.get("ok"):
        raise AssertionError(f"Snapshot failed: {result}")
    return result


def field_num(snap: dict, key: str) -> float:
    return float((snap.get("field") or {}).get(key) or 0)


def assert_delta(before: dict, after: dict, keys: list[str], label: str, minimum: float = 0.04) -> None:
    changed = [key for key in keys if abs(field_num(after, key) - field_num(before, key)) >= minimum]
    if not changed:
        raise AssertionError(f"{label} did not change {keys}: before={before.get('field')}, after={after.get('field')}")


def drag_pointer(window: WebMainWindow, start: dict, dx: int, dy: int) -> dict:
    sx = int(start["x"])
    sy = int(start["y"])
    mx = int(sx + dx / 2)
    my = int(sy + dy / 2)
    ex = int(sx + dx)
    ey = int(sy + dy)
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
        pointerId: 91,
        pointerType: 'mouse',
        isPrimary: true,
        view: window
      }));
    """
    down = run_js(
        window,
        f"""
        (() => {{
          {event_helper}
          const target = document.elementFromPoint({sx}, {sy});
          if (!target) return {{ ok: false, error: 'no target' }};
          fire(target, 'down', {sx}, {sy});
          return {{ ok: true, hit: String(target.className || target.tagName || ''), started: Boolean(activeDrag) }};
        }})()
        """,
    )
    wait(90)
    mid = run_js(window, f"(() => {{ {event_helper} fire(window, 'move', {mx}, {my}); return {{ ok: true, moved: Boolean(activeDrag && activeDrag.moved) }}; }})()")
    wait(110)
    end = run_js(window, f"(() => {{ {event_helper} fire(window, 'move', {ex}, {ey}); return {{ ok: true, moved: Boolean(activeDrag && activeDrag.moved), field: selectedManualField() }}; }})()")
    wait(110)
    up = run_js(window, f"(() => {{ {event_helper} const beforeUp = selectedManualField(); fire(window, 'up', {ex}, {ey}); return {{ ok: true, beforeUp, afterUp: selectedManualField(), active: Boolean(activeDrag) }}; }})()")
    wait(400)
    return {"down": down, "mid": mid, "end": end, "up": up}


def check_layout(window: WebMainWindow) -> dict:
    result = run_js(
        window,
        """
        (() => {
          const rect = selector => {
            const el = document.querySelector(selector);
            const r = el?.getBoundingClientRect?.();
            return { present: Boolean(el), visible: Boolean(r && r.width > 20 && r.height > 20), width: r?.width || 0, height: r?.height || 0 };
          };
          const canvas = rect('#manualPreview .preview-label.editor-live');
          const stage = rect('.corel-canvas-stage');
          const inspector = rect('.corel-inspector');
          const layerPanelEl = document.querySelector('#manualLayerPanel');
          const sizePanelEl = document.querySelector('#corelDockLayers .label-size-panel');
          const layerPanelRect = layerPanelEl?.getBoundingClientRect?.();
          const sizePanelRect = sizePanelEl?.getBoundingClientRect?.();
          const titleRect = document.querySelector('.corel-model-title')?.getBoundingClientRect?.();
          const objectRect = document.querySelector('.corel-object-controls')?.getBoundingClientRect?.();
          const propertyRect = document.querySelector('.corel-property-bar')?.getBoundingClientRect?.();
          const lastObjectRect = document.querySelector('.corel-object-controls > :last-child')?.getBoundingClientRect?.();
          const topbar = document.querySelector('.topbar');
          const main = document.querySelector('.main');
          const topbarHidden = !topbar || getComputedStyle(topbar).display === 'none';
          const pageScrollLocked = Boolean(
            document.body.classList.contains('label-studio-active') &&
            document.documentElement.classList.contains('label-studio-active') &&
            getComputedStyle(document.body).overflow === 'hidden' &&
            getComputedStyle(document.documentElement).overflow === 'hidden' &&
            main?.classList.contains('label-studio-main-active') &&
            getComputedStyle(main).overflow === 'hidden' &&
            document.documentElement.scrollHeight <= document.documentElement.clientHeight + 2
          );
          const activeDock = document.querySelector('#label .corel-dock-panel.active');
          if (activeDock) activeDock.scrollTop = 0;
          const wheelResult = activeDock?.dispatchEvent?.(new WheelEvent('wheel', { deltaY: 360, bubbles: true, cancelable: true }));
          const dockWheelContained = Boolean(
            activeDock &&
            activeDock.scrollHeight > activeDock.clientHeight &&
            activeDock.scrollTop > 0 &&
            wheelResult === false &&
            (main?.scrollTop || 0) === 0 &&
            window.scrollY === 0
          );
          const dockLayersStacked = Boolean(
            layerPanelRect &&
            sizePanelRect &&
            layerPanelRect.height > 20 &&
            sizePanelRect.height > 20 &&
            layerPanelRect.bottom <= sizePanelRect.top + 2
          );
          const modelObjectControlsSeparated = Boolean(
            titleRect &&
            objectRect &&
            titleRect.width > 30 &&
            objectRect.width > 120 &&
            titleRect.right <= objectRect.left + 2
          );
          const topbarControlsFit = Boolean(
            propertyRect &&
            lastObjectRect &&
            lastObjectRect.right <= propertyRect.right - 4
          );
          const fontCombo = document.querySelector('.studio-combo[data-select-id="corelFontFamily"]');
          const propertyHeightBeforeCombo = propertyRect?.height || 0;
          fontCombo?.querySelector?.('.studio-combo-button')?.click?.();
          const comboMenu = fontCombo?.querySelector?.('.studio-combo-menu');
          const propertyHeightAfterCombo = document.querySelector('.corel-property-bar')?.getBoundingClientRect?.()?.height || 0;
          const textDockActive = Boolean(document.querySelector('#corelDockText')?.classList.contains('active'));
          const comboMenuStable = Boolean(
            comboMenu &&
            comboMenu.hidden === true &&
            textDockActive &&
            Math.abs(propertyHeightAfterCombo - propertyHeightBeforeCombo) <= 2
          );
          if (typeof closeStudioCombos === 'function') closeStudioCombos();
          if (typeof selectCorelDockTab === 'function') selectCorelDockTab('layers');
          return {
            ok: true,
            propertyBar: rect('.corel-property-bar'),
            leftToolbar: rect('.corel-left-toolbar'),
            canvasPanel: rect('.corel-canvas-panel'),
            canvas,
            stage,
            inspector,
            layerPanel: rect('#manualLayerPanel'),
            labelSizePanel: rect('#corelDockLayers .label-size-panel'),
            bottomPanel: rect('.corel-bottom-panel'),
            statusbar: rect('.corel-statusbar'),
            canvasLargeEnough: canvas.width >= 430 && canvas.height >= 240,
            inspectorCompact: inspector.width <= 470,
            dockLayersStacked,
            dockLayerBottom: layerPanelRect?.bottom || 0,
            labelSizeTop: sizePanelRect?.top || 0,
            modelObjectControlsSeparated,
            topbarControlsFit,
            comboMenuStable,
            textDockActive,
            topbarHidden,
            pageScrollLocked,
            dockWheelContained,
            topbarRight: propertyRect?.right || 0,
            lastControlRight: lastObjectRect?.right || 0,
            studioComboCount: document.querySelectorAll('.studio-combo .studio-combo-button').length
          };
        })()
        """,
    )
    required = ["propertyBar", "leftToolbar", "canvasPanel", "canvas", "inspector", "layerPanel", "statusbar"]
    missing = [key for key in required if not result.get(key, {}).get("visible")]
    if missing or not result.get("canvasLargeEnough") or not result.get("inspectorCompact") or not result.get("dockLayersStacked") or not result.get("modelObjectControlsSeparated") or not result.get("topbarControlsFit") or not result.get("comboMenuStable") or not result.get("topbarHidden") or not result.get("pageScrollLocked") or not result.get("dockWheelContained") or result.get("studioComboCount", 0) < 3:
        raise AssertionError(f"Corel layout failed: missing={missing}, result={result}")
    return result


def check_layer_panel(window: WebMainWindow) -> dict:
    result = run_js(
        window,
        """
        (() => {
          const rows = [...document.querySelectorAll('.corel-layer-row')].map(row => row.innerText.trim());
          const fields = selectedLabelModel?.fields_summary || [];
          const labelIndex = fields.findIndex(field => field.excel_column === 'label_text');
          const dateIndex = fields.findIndex(field => field.excel_column === 'date_text');
          const noteIndex = fields.findIndex(field => field.excel_column === 'note_text');
          selectField(dateIndex);
          const selectedDate = selectedManualField()?.excel_column;
          selectField(noteIndex);
          const selectedNote = selectedManualField()?.excel_column;
          selectField(labelIndex);
          const beforeVisible = selectedManualField()?.visible;
          toggleLayerVisibility(labelIndex, { stopPropagation(){} });
          const afterHidden = selectedManualField()?.visible === false;
          const hiddenBox = document.querySelector(`.field-box[data-field-index="${labelIndex}"]`);
          const boxHidden = !hiddenBox || hiddenBox.hidden === true;
          toggleLayerVisibility(labelIndex, { stopPropagation(){} });
          const restoredVisible = selectedManualField()?.visible !== false;
          toggleLayerLock(labelIndex, { stopPropagation(){} });
          const locked = selectedManualField()?.locked === true;
          const before = { ...selectedManualField() };
          return { ok: true, rows, labelIndex, dateIndex, noteIndex, selectedDate, selectedNote, beforeVisible, afterHidden, boxHidden, restoredVisible, locked, before };
        })()
        """,
    )
    if result["labelIndex"] < 0 or result["dateIndex"] < 0 or result["noteIndex"] < 0:
        raise AssertionError(f"Basic layers missing: {result}")
    if result["selectedDate"] != "date_text" or result["selectedNote"] != "note_text":
        raise AssertionError(f"Layer row selection failed: {result}")
    if not result["afterHidden"] or not result["boxHidden"] or not result["restoredVisible"] or not result["locked"]:
        raise AssertionError(f"Layer visibility/lock failed: {result}")

    before_lock = snapshot(window)
    drag_event = drag_pointer(window, before_lock["center"], 42, 18)
    after_lock = snapshot(window)
    if abs(field_num(after_lock, "x_mm") - field_num(before_lock, "x_mm")) > 0.03 or abs(field_num(after_lock, "y_mm") - field_num(before_lock, "y_mm")) > 0.03:
        raise AssertionError(f"Locked layer moved: before={before_lock['field']}, after={after_lock['field']}, event={drag_event}")
    unlock = run_js(window, "(() => { toggleLayerLock(selectedFieldIndex, { stopPropagation(){} }); return { locked: selectedManualField()?.locked === true }; })()")
    if unlock.get("locked"):
        raise AssertionError(f"Layer did not unlock: {unlock}")
    result["lockedDragBlocked"] = True
    return result


def check_drag_resize(window: WebMainWindow, screenshots: dict[str, str], checks: list[dict]) -> None:
    setup_studio(window, "100", "label_text")
    before = snapshot(window)
    screenshots["selected_name_before"] = save_screenshot(window, "selected_name_before.png")
    event = drag_pointer(window, before["center"], 44, 20)
    after = snapshot(window)
    screenshots["drag_after"] = save_screenshot(window, "drag_after.png")
    assert_delta(before, after, ["x_mm", "y_mm"], "label_text drag")
    checks.append({"claim": "İsim mouse ile taşınıyor", "status": "PASSED", "before": before["field"], "after": after["field"], "event": event})

    before_corner = snapshot(window)
    drag_pointer(window, before_corner["handles"]["se"], 44, 24)
    after_corner = snapshot(window)
    screenshots["resize_after"] = save_screenshot(window, "resize_after.png")
    assert_delta(before_corner, after_corner, ["width_mm", "height_mm", "font_size"], "corner resize")
    checks.append({"claim": "Köşeden resize width/height/font_size değiştiriyor", "status": "PASSED", "before": before_corner["field"], "after": after_corner["field"]})

    setup_studio(window, "100", "label_text")
    before_side = snapshot(window)
    drag_pointer(window, before_side["handles"]["e"], 34, 0)
    after_side = snapshot(window)
    assert_delta(before_side, after_side, ["width_mm"], "side resize width")
    if abs(field_num(after_side, "font_size") - field_num(before_side, "font_size")) > 0.11:
        raise AssertionError(f"Side resize changed font aggressively: before={before_side['field']}, after={after_side['field']}")
    checks.append({"claim": "Kenardan resize width/height değiştiriyor", "status": "PASSED", "before": before_side["field"], "after": after_side["field"]})

    for zoom in ["150", "200", "fit"]:
      setup_studio(window, zoom, "label_text")
      before_zoom = snapshot(window)
      drag_pointer(window, before_zoom["center"], 24, 12)
      after_zoom = snapshot(window)
      assert_delta(before_zoom, after_zoom, ["x_mm", "y_mm"], f"zoom {zoom} drag")
      setup_studio(window, zoom, "label_text")
      before_zoom_resize = snapshot(window)
      drag_pointer(window, before_zoom_resize["handles"]["se"], 18, 12)
      after_zoom_resize = snapshot(window)
      assert_delta(before_zoom_resize, after_zoom_resize, ["width_mm", "height_mm", "font_size"], f"zoom {zoom} resize")
      if zoom == "150":
          screenshots["zoom_150_after"] = save_screenshot(window, "zoom_150_after.png")
      checks.append({"claim": f"Zoom {zoom} drag/resize", "status": "PASSED", "afterDrag": after_zoom["field"], "afterResize": after_zoom_resize["field"]})

    for column in ["date_text", "note_text"]:
        setup_studio(window, "fit", column)
        before_basic = snapshot(window)
        drag_pointer(window, before_basic["center"], 20, 10)
        after_basic = snapshot(window)
        assert_delta(before_basic, after_basic, ["x_mm", "y_mm"], f"{column} drag")
        checks.append({"claim": f"{column} mouse ile taşınıyor", "status": "PASSED", "before": before_basic["field"], "after": after_basic["field"]})


def check_font_color_payload(window: WebMainWindow, screenshots: dict[str, str]) -> dict:
    setup_studio(window, "fit", "label_text")
    font_results = run_js(
        window,
        """
        (() => {
          const results = [];
          ['romantic', 'luxury', 'minimal'].forEach(preset => {
            applyFontPreset(preset);
            const field = { ...selectedManualField() };
            const payload = manualPayload()._fields.find(item => item.excel_column === 'label_text');
            results.push({ preset, field, payload });
          });
          const presetMeta = LABEL_FONT_PRESETS.map(item => ({
            id: item.id,
            name: item.name,
            category: item.category,
            target: item.target,
            fallback: item.fallback_font_family,
            recommended_for: item.recommended_for
          }));
          const recommendation = recommendedFontPresetForModel(selectedLabelModel);
          renderManualColorPanel();
          const colorGroups = MANUAL_COLOR_GROUPS.map(group => ({
            id: group.id,
            title: group.title,
            colors: group.colors.map(item => typeof item === 'string' ? item : item.value),
            names: group.colors.map(item => typeof item === 'string' ? item : item.name)
          }));
          applyColorSwatch('#b7791f');
          const gold = { field: { ...selectedManualField() }, payload: manualPayload()._fields.find(item => item.excel_column === 'label_text'), recent: [...recentManualColors] };
          applyColorSwatch('#5a351f');
          const brown = { field: { ...selectedManualField() }, payload: manualPayload()._fields.find(item => item.excel_column === 'label_text'), recent: [...recentManualColors] };
          applyColorSwatch('#7f1d1d');
          const burgundy = { field: { ...selectedManualField() }, payload: manualPayload()._fields.find(item => item.excel_column === 'label_text'), recent: [...recentManualColors] };
          applyColorSwatch('#fff8e6');
          const weakContrast = manualColorContrastResult(selectedManualField()?.color);
          const warningVisible = !document.getElementById('corelContrastWarning')?.hidden;
          suggestReadableTextColor();
          const suggested = { field: { ...selectedManualField() }, payload: manualPayload()._fields.find(item => item.excel_column === 'label_text'), contrast: manualColorContrastResult(selectedManualField()?.color) };
          const beforeInvalid = selectedManualField()?.color;
          applyColorSwatch('not-a-hex');
          const afterInvalid = selectedManualField()?.color;
          return { ok: true, fontResults: results, presetMeta, recommendation, colorGroups, gold, brown, burgundy, weakContrast, warningVisible, suggested, invalidKeptColor: beforeInvalid === afterInvalid, alerts: window.__corelVerificationAlerts || [] };
        })()
        """,
    )
    if len(font_results["presetMeta"]) < 10 or not all(row.get("fallback") and row.get("target") for row in font_results["presetMeta"]):
        raise AssertionError(f"Font preset metadata is incomplete: {font_results['presetMeta']}")
    if not font_results.get("recommendation"):
        raise AssertionError(f"Model font recommendation missing: {font_results}")
    for row in font_results["fontResults"]:
        if not row["payload"] or row["payload"].get("font_family") != row["field"].get("font_family"):
            raise AssertionError(f"Font preset did not reach payload: {row}")
        if row["payload"].get("font_preset_id") != row["preset"]:
            raise AssertionError(f"Font preset id did not reach payload: {row}")
    for color_row in [font_results["gold"], font_results["brown"], font_results["burgundy"]]:
        if color_row["payload"].get("color") != color_row["field"].get("color"):
            raise AssertionError(f"Color did not reach payload: {color_row}")
    brand_group = next((row for row in font_results["colorGroups"] if row["id"] == "brand"), None)
    if not brand_group or "Cyzella Gold" not in brand_group["names"] or "#b9973e" not in brand_group["colors"]:
        raise AssertionError(f"Brand colors missing from color panel metadata: {font_results['colorGroups']}")
    if font_results["weakContrast"]["ok"] or not font_results["warningVisible"]:
        raise AssertionError(f"Weak color contrast was not detected: {font_results}")
    if font_results["suggested"]["payload"].get("color") != "#111111" or not font_results["suggested"]["contrast"]["ok"]:
        raise AssertionError(f"Readable color suggestion failed: {font_results['suggested']}")
    if not font_results["invalidKeptColor"] or not any("#RRGGBB" in item for item in font_results["alerts"]):
        raise AssertionError(f"Invalid hex did not show safe validation: {font_results}")
    screenshots["color_panel"] = save_screenshot(window, "color_panel.png")
    return font_results


def check_smart_layout(window: WebMainWindow) -> dict:
    setup_studio(window, "fit", "label_text")
    result = run_js(
        window,
        """
        (() => {
          const fieldsBefore = (selectedLabelModel?.fields_summary || []).map(field => ({ ...field }));
          autoArrangeManualFields();
          const afterAuto = (selectedLabelModel?.fields_summary || []).map(field => ({ ...field }));
          const labelIndex = afterAuto.findIndex(field => field.excel_column === 'label_text');
          selectField(labelIndex);
          document.getElementById('manualText').value = 'Ayşe Mehmet Çok Uzun Kabul Testi İçin Gerçekten Çok Uzun Nişan Hatırası İsim Alanı';
          updateManualFieldValue('label_text', document.getElementById('manualText').value);
          applyFieldGeometry(labelIndex, { ...selectedManualField(), width_mm: 24, height_mm: 5, font_size: 18, min_font_size: 6 }, { snap: false });
          const beforeFit = { ...selectedManualField() };
          fitAllManualText();
          const afterFit = { ...selectedManualField() };
          applyFieldGeometry(labelIndex, { ...afterFit, x_mm: -8, y_mm: -5, width_mm: 999, height_mm: 999 }, { snap: false });
          const beforeSafe = { ...selectedManualField() };
          moveAllFieldsIntoSafeArea();
          const afterSafe = { ...selectedManualField() };
          prepareManualForProduction();
          const payload = manualPayload()._fields.find(item => item.excel_column === 'label_text');
          const engineNames = [
            'auto_layout_label',
            'auto_fit_text_field',
            'clamp_field_inside_label',
            'center_field_horizontally',
            'distribute_fields_vertically',
            'detect_text_overflow',
            'reduce_font_to_fit',
            'expand_field_to_fit',
            'normalize_label_fields',
            'apply_safe_area'
          ];
          const engineFunctions = Object.fromEntries(engineNames.map(name => [name, typeof window[name] === 'function' || typeof eval(name) === 'function']));
          const overflow = detect_text_overflow(beforeFit, document.getElementById('manualText').value);
          return { ok: true, fieldsBefore, afterAuto, beforeFit, afterFit, beforeSafe, afterSafe, payload, engineFunctions, overflow };
        })()
        """,
    )
    wait(1600)
    result["preflight"] = run_js(window, "(() => document.getElementById('manualPreflightStatus')?.innerText || '')()")
    before_label = next(item for item in result["fieldsBefore"] if item.get("excel_column") == "label_text")
    after_label = next(item for item in result["afterAuto"] if item.get("excel_column") == "label_text")
    if abs(float(after_label.get("x_mm") or 0) - float(before_label.get("x_mm") or 0)) < 0.05:
        raise AssertionError(f"Auto arrange did not move label_text: {result}")
    if float(result["afterFit"].get("font_size") or 0) >= float(result["beforeFit"].get("font_size") or 0):
        raise AssertionError(f"Fit text did not shrink long text: {result}")
    if not result["overflow"].get("width_overflow") and not result["overflow"].get("height_overflow"):
        raise AssertionError(f"Overflow detector did not flag long text: {result}")
    if not all(result["engineFunctions"].values()):
        raise AssertionError(f"Smart production engine functions missing: {result['engineFunctions']}")
    if float(result["afterSafe"].get("x_mm") or -1) < 0 or float(result["afterSafe"].get("y_mm") or -1) < 0:
        raise AssertionError(f"Safe area did not clamp field: {result}")
    if not result.get("preflight"):
        raise AssertionError(f"Prepare for production did not update preflight: {result}")
    return result


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    screenshots: dict[str, str] = {}
    checks: list[dict[str, object]] = []

    setup_studio(window, "fit", "label_text")
    layout = check_layout(window)
    screenshots["studio_general"] = save_screenshot(window, "studio_general.png")
    checks.append({"claim": "Corel benzeri layout bölümleri görünür", "status": "PASSED", "details": layout})

    layer_result = check_layer_panel(window)
    screenshots["layer_panel"] = save_screenshot(window, "layer_panel.png")
    checks.append({"claim": "Layer panel gerçek state değiştirir", "status": "PASSED", "details": layer_result})

    check_drag_resize(window, screenshots, checks)

    font_color = check_font_color_payload(window, screenshots)
    checks.append({"claim": "Font presetleri ve renkler payload'a yansır", "status": "PASSED", "details": font_color})

    smart = check_smart_layout(window)
    screenshots["smart_layout_after"] = save_screenshot(window, "smart_layout_after.png")
    checks.append({"claim": "Akıllı Düzen gerçek geometry/preflight değiştirir", "status": "PASSED", "details": smart})

    payload = run_js(window, "manualPayload()")
    if not payload.get("_fields"):
        raise AssertionError(f"manualPayload fields missing: {payload}")
    checks.append({"claim": "PDF/PNG payload son canvas state'i taşır", "status": "PASSED", "details": {"fieldCount": len(payload["_fields"]), "label": payload["_fields"][0]}})

    security = run_js(
        window,
        """
        (() => ({
          ok: true,
          directPrintReferences: String(requestPdfPrint).includes('window.print') || String(confirmSafePrintOpen).includes('window.print'),
          dangerousProcessWords: document.body.innerText.includes('CorelDRAW') || document.body.innerText.includes('RDWorks') || document.body.innerText.includes('Illustrator')
        }))()
        """,
    )
    if security.get("directPrintReferences"):
        raise AssertionError(f"Silent print reference detected: {security}")
    checks.append({"claim": "Direct/silent print tetiklenmez", "status": "PASSED", "details": security})

    return {"status": "PASSED", "screenshots": screenshots, "checks": checks}


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
        except Exception as exc:  # noqa: BLE001
            outcome = {"status": "ERROR", "message": str(exc)}
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        os._exit(0 if outcome.get("status") == "PASSED" else 1)

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(5600, start))
    code = app.exec()
    return 0 if outcome.get("status") == "PASSED" and code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
