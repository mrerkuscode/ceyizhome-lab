from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from verify_corel_editor_interactions import (  # noqa: E402
    check_layout,
    run_js,
    setup_studio,
    wait,
)


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "studio_layout_stability"
RESULT_PATH = OUTPUT_DIR / "VERIFY_STUDIO_LAYOUT_STABILITY_RESULT.json"


def flush_ui(window: WebMainWindow, ms: int = 240) -> None:
    QApplication.processEvents()
    window.view.repaint()
    QApplication.processEvents()
    wait(ms)
    QApplication.processEvents()


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    flush_ui(window)
    saved = window.view.grab().save(str(path))
    assert_true(saved and path.exists() and path.stat().st_size > 0, f"Screenshot kaydedilemedi: {filename}")
    return str(path)


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def studio_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(
        window,
        """
        (() => {
          const rect = selector => {
            const el = document.querySelector(selector);
            const r = el?.getBoundingClientRect?.();
            return {
              present: Boolean(el),
              visible: Boolean(r && r.width > 20 && r.height > 20 && r.bottom > 0 && r.right > 0),
              left: r?.left || 0,
              top: r?.top || 0,
              right: r?.right || 0,
              bottom: r?.bottom || 0,
              width: r?.width || 0,
              height: r?.height || 0
            };
          };
          const sidebar = document.querySelector('.sidebar');
          const sidebarRect = sidebar?.getBoundingClientRect?.();
          const activeDock = document.querySelector('#label .corel-dock-panel.active');
          const activeDockTab = document.querySelector('#label .corel-dock-tab.active');
          return {
            activePage: document.querySelector('.page.active')?.id || '',
            htmlScrollY: window.scrollY || document.documentElement.scrollTop || 0,
            bodyScrollTop: document.body.scrollTop || 0,
            mainScrollTop: document.querySelector('.main')?.scrollTop || 0,
            htmlOverflow: getComputedStyle(document.documentElement).overflow,
            bodyOverflow: getComputedStyle(document.body).overflow,
            studioActiveClass: document.body.classList.contains('label-studio-active'),
            mainActiveClass: document.querySelector('.main')?.classList.contains('label-studio-main-active') || false,
            studio: rect('#label .corel-studio'),
            propertyBar: rect('#label .corel-property-bar'),
            quickRow: rect('#label .corel-quick-production-row'),
            leftToolbar: rect('#label .corel-left-toolbar'),
            canvasPanel: rect('#label .corel-canvas-panel'),
            liveCanvas: rect('#manualPreview .preview-label.editor-live'),
            selectedBox: rect('#manualPreview .field-box.selected'),
            inspector: rect('#label .corel-inspector'),
            dock: rect('#label .corel-dock-panel.active'),
            statusbar: rect('#label .corel-statusbar'),
            sidebarExpanded: sidebar?.classList.contains('sidebar-expanded') || false,
            sidebarWidth: sidebarRect?.width || 0,
            modalOpen: !document.getElementById('safePrintModal')?.hidden,
            comboOpenCount: [...document.querySelectorAll('.studio-combo-menu')].filter(menu => !menu.hidden).length,
            activeDockId: activeDock?.id || '',
            activeDockTab: activeDockTab?.dataset?.tab || '',
            activeDockScrollTop: activeDock?.scrollTop || 0,
            activeDockScrollHeight: activeDock?.scrollHeight || 0,
            activeDockClientHeight: activeDock?.clientHeight || 0
          };
        })()
        """,
    )


def assert_studio_stable(state: dict[str, object], label: str) -> None:
    visible_keys = ["studio", "propertyBar", "quickRow", "leftToolbar", "canvasPanel", "liveCanvas", "inspector", "dock", "statusbar"]
    missing = [key for key in visible_keys if not (state.get(key) or {}).get("visible")]
    assert_true(state.get("activePage") == "label", f"{label}: Etiket Studio sayfasi aktif degil", state)
    assert_true(not missing, f"{label}: Studio bolumleri kayboldu", {"missing": missing, "state": state})
    assert_true(abs(float(state.get("htmlScrollY") or 0)) <= 2, f"{label}: body/html scroll kacagi var", state)
    assert_true(abs(float(state.get("mainScrollTop") or 0)) <= 2, f"{label}: main scroll kacagi var", state)
    assert_true(state.get("studioActiveClass") and state.get("mainActiveClass"), f"{label}: Studio scroll lock class'lari kayboldu", state)
    assert_true(float((state.get("liveCanvas") or {}).get("width") or 0) >= 430, f"{label}: canvas daraldi/kayboldu", state)
    assert_true(float((state.get("inspector") or {}).get("width") or 999) <= 470, f"{label}: sag dock kontrolsuz genisledi", state)


def dispatch_mouse_storm(window: WebMainWindow) -> dict[str, object]:
    return run_js(
        window,
        """
        (() => {
          const EventClass = window.PointerEvent || MouseEvent;
          const eventName = window.PointerEvent ? 'pointermove' : 'mousemove';
          for (let i = 0; i < 32; i += 1) {
            window.dispatchEvent(new EventClass(eventName, {
              bubbles: true,
              cancelable: true,
              clientX: 120 + (i * 17) % 1200,
              clientY: 110 + (i * 23) % 720,
              pointerId: 77,
              pointerType: 'mouse',
              isPrimary: true,
              view: window
            }));
          }
          return { ok: true, moves: 32 };
        })()
        """,
    )


def exercise_sidebar_hover(window: WebMainWindow) -> dict[str, object]:
    result = run_js(
        window,
        """
        (() => {
          const sidebar = document.querySelector('.sidebar');
          if (!sidebar) return { ok: false, error: 'sidebar missing' };
          document.activeElement?.blur?.();
          const EventClass = window.PointerEvent || MouseEvent;
          const enter = window.PointerEvent ? 'pointerenter' : 'mouseenter';
          const leave = window.PointerEvent ? 'pointerleave' : 'mouseleave';
          sidebar.dispatchEvent(new EventClass(enter, { bubbles: true, clientX: 16, clientY: 220, pointerType: 'mouse' }));
          return { ok: true, afterEnter: sidebar.classList.contains('sidebar-expanded'), width: sidebar.getBoundingClientRect().width };
        })()
        """,
    )
    wait(220)
    entered = studio_state(window)
    run_js(
        window,
        """
        (() => {
          const sidebar = document.querySelector('.sidebar');
          const EventClass = window.PointerEvent || MouseEvent;
          const leave = window.PointerEvent ? 'pointerleave' : 'mouseleave';
          sidebar?.dispatchEvent?.(new EventClass(leave, { bubbles: true, clientX: 420, clientY: 220, pointerType: 'mouse' }));
          document.body.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: 760, clientY: 320, view: window }));
          return { ok: true };
        })()
        """,
    )
    wait(520)
    left = studio_state(window)
    result["enteredState"] = entered
    result["leftState"] = left
    return result


def exercise_dock_scroll(window: WebMainWindow) -> dict[str, object]:
    return run_js(
        window,
        """
        (() => {
          if (typeof selectCorelDockTab === 'function') selectCorelDockTab('layers');
          const dock = document.querySelector('#label .corel-dock-panel.active');
          if (!dock) return { ok: false, error: 'active dock missing' };
          dock.scrollTop = 0;
          const before = { dockTop: dock.scrollTop, mainTop: document.querySelector('.main')?.scrollTop || 0, bodyTop: window.scrollY || 0 };
          for (let i = 0; i < 12; i += 1) {
            dock.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true, deltaY: 380 }));
          }
          const after = { dockTop: dock.scrollTop, mainTop: document.querySelector('.main')?.scrollTop || 0, bodyTop: window.scrollY || 0 };
          return { ok: true, before, after, canScroll: dock.scrollHeight > dock.clientHeight };
        })()
        """,
    )


def exercise_font_combo(window: WebMainWindow) -> dict[str, object]:
    opened = run_js(
        window,
        """
        (() => {
          const combo = document.querySelector('.studio-combo[data-select-id="corelFontFamily"]');
          const property = document.querySelector('.corel-property-bar');
          const beforeHeight = property?.getBoundingClientRect?.().height || 0;
          const beforeDock = document.querySelector('#label .corel-dock-panel.active')?.id || '';
          combo?.querySelector?.('.studio-combo-button')?.click?.();
          return { ok: Boolean(combo), beforeHeight, beforeDock };
        })()
        """,
    )
    wait(260)
    measured = run_js(
        window,
        """
        (() => {
          const property = document.querySelector('.corel-property-bar');
          const opened = [...document.querySelectorAll('.studio-combo-menu')].some(menu => !menu.hidden);
          const activeDock = document.querySelector('#label .corel-dock-panel.active')?.id || '';
          const activeDockTab = document.querySelector('#label .corel-dock-tab.active')?.dataset?.tab || '';
          const afterOpenHeight = property?.getBoundingClientRect?.().height || 0;
          if (typeof closeStudioCombos === 'function') closeStudioCombos();
          const afterCloseHeight = property?.getBoundingClientRect?.().height || 0;
          return { opened, activeDock, activeDockTab, afterOpenHeight, afterCloseHeight };
        })()
        """,
    )
    return {**opened, **measured}


def exercise_print_modal(window: WebMainWindow) -> dict[str, object]:
    result = run_js(
        window,
        """
        (() => {
          if (typeof showSafePrintConfirm !== 'function') return { ok: false, error: 'showSafePrintConfirm missing' };
          if (typeof closeSafePrintModal === 'function') closeSafePrintModal();
          showSafePrintConfirm({
            relativePath: 'output/2026-05-15/print/manual/stability_guard.pdf',
            payload: { status: 'OK', preview_pages: [] },
            modelName: selectedLabelModel?.model_name || 'Stability Guard',
            labelText: document.getElementById('manualText')?.value || '',
            dateText: document.getElementById('manualDateText')?.value || '',
            noteText: document.getElementById('manualNoteText')?.value || '',
            sizeText: '50 x 30 mm',
            quantity: document.getElementById('manualQuantity')?.value || '1',
            fileName: 'stability_guard.pdf',
            source: 'manual',
            validationStatus: 'OK'
          });
          return {
            ok: true,
            modalOpen: !document.getElementById('safePrintModal')?.hidden,
            modalText: document.getElementById('safePrintModal')?.innerText || '',
            directPrintReference: /window\\.print\\(|\\.print\\(/.test(document.documentElement.innerHTML || '')
          };
        })()
        """,
    )
    wait(220)
    return result


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    screenshots: dict[str, str] = {}
    checks: list[dict[str, object]] = []

    setup_studio(window, "fit", "label_text")
    flush_ui(window, 650)
    layout = check_layout(window)
    checks.append({"name": "base_corel_layout", "status": "PASSED", "state": layout})
    base_state = studio_state(window)
    assert_studio_stable(base_state, "base")
    screenshots["base"] = save_screenshot(window, "studio_layout_base.png")

    move_result = dispatch_mouse_storm(window)
    wait(300)
    after_moves = studio_state(window)
    assert_studio_stable(after_moves, "mousemove storm")
    checks.append({"name": "mousemove_no_flicker", "status": "PASSED", "state": after_moves, "event": move_result})
    screenshots["after_mousemove"] = save_screenshot(window, "studio_after_mousemove.png")

    sidebar = exercise_sidebar_hover(window)
    assert_true(bool(sidebar.get("afterEnter")), "Sidebar mouse enter ile acilmadi", sidebar)
    assert_studio_stable(sidebar["enteredState"], "sidebar expanded")
    assert_studio_stable(sidebar["leftState"], "sidebar collapsed")
    assert_true(not sidebar["leftState"].get("sidebarExpanded"), "Sidebar mouse ayrilinca kapanmadi", sidebar)
    assert_true(float(sidebar["leftState"].get("sidebarWidth") or 999) <= 110, "Sidebar rail genis kaldi", sidebar)
    checks.append({"name": "sidebar_hover_open_close", "status": "PASSED", "state": sidebar})
    screenshots["sidebar_collapsed_after_leave"] = save_screenshot(window, "studio_sidebar_collapsed_after_leave.png")

    dock = exercise_dock_scroll(window)
    wait(260)
    after_dock = studio_state(window)
    assert_true(dock.get("ok"), "Sag dock scroll test baslatilamadi", dock)
    assert_true(float((dock.get("after") or {}).get("dockTop") or 0) > 0, "Sag dock kendi icinde scroll olmadi", dock)
    assert_true(abs(float((dock.get("after") or {}).get("mainTop") or 0)) <= 2, "Sag dock scroll main sayfaya tasti", dock)
    assert_true(abs(float((dock.get("after") or {}).get("bodyTop") or 0)) <= 2, "Sag dock scroll body/html sayfaya tasti", dock)
    assert_studio_stable(after_dock, "dock scroll")
    checks.append({"name": "right_dock_scroll_contained", "status": "PASSED", "state": dock})
    screenshots["right_dock_scrolled"] = save_screenshot(window, "studio_right_dock_scrolled.png")

    combo = exercise_font_combo(window)
    wait(220)
    after_combo = studio_state(window)
    assert_true(combo.get("ok"), "Font combosu bulunamadi", combo)
    assert_true(not combo.get("opened"), "Dock-only font kontrolu overlay menu acarak layout'u riske atti", combo)
    assert_true(combo.get("activeDockTab") == "text" or combo.get("activeDock") == "corelDockText", "Font kontrolu Yazı dock'una gecmedi", combo)
    assert_true(abs(float(combo.get("afterOpenHeight") or 0) - float(combo.get("beforeHeight") or 0)) <= 4, "Font menu property bar'i buyuttu", combo)
    assert_true(abs(float(combo.get("afterCloseHeight") or 0) - float(combo.get("beforeHeight") or 0)) <= 4, "Font menu kapaninca layout eski haline donmedi", combo)
    assert_studio_stable(after_combo, "font combo")
    checks.append({"name": "font_combo_overlay_stable", "status": "PASSED", "state": combo})
    screenshots["font_combo_closed_stable"] = save_screenshot(window, "studio_font_combo_closed_stable.png")

    print_modal = exercise_print_modal(window)
    wait(300)
    after_print = studio_state(window)
    assert_true(print_modal.get("ok") and print_modal.get("modalOpen"), "Yazdir modal stabil acilmadi", print_modal)
    assert_true("otomatik" in str(print_modal.get("modalText") or "").lower(), "Yazdir modal guvenlik mesaji eksik", print_modal)
    assert_true(not print_modal.get("directPrintReference"), "Direct/silent print referansi gorundu", print_modal)
    assert_studio_stable(after_print, "print modal")
    checks.append({"name": "safe_print_modal_no_flicker", "status": "PASSED", "state": print_modal})
    screenshots["safe_print_modal"] = save_screenshot(window, "studio_safe_print_modal_stable.png")

    if os.environ.get("CYZELLA_KEEP_MODAL_OPEN") != "1":
        run_js(window, "(() => { if (typeof closeSafePrintModal === 'function') closeSafePrintModal(); return { ok: true }; })()")

    return {"status": "PASSED", "screenshots": screenshots, "checks": checks}


def main() -> int:
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1600, 950)
    window.show()

    outcome = {"status": "ERROR", "message": "not started"}
    exit_code = {"value": 1}

    def start() -> None:
        nonlocal outcome
        try:
            outcome = run_gate(window)
        except Exception as exc:  # noqa: BLE001
            outcome = {"status": "ERROR", "message": str(exc)}
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        exit_code["value"] = 0 if outcome.get("status") == "PASSED" else 1
        window.close()
        QApplication.processEvents()
        app.quit()

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(5600, start))
    app.exec()
    return exit_code["value"]


if __name__ == "__main__":
    raise SystemExit(main())
