# Studio Layout Stability Regression Report

Date: 2026-05-15

## Purpose

Kullanicinin tekrar eden sikayeti: Etiket Studio'da mouse hareketi, sag panel scroll veya Yazdir aksiyonu sirasinda sayfanin yanip sonmesi, kaybolmasi veya layout'un bozulmasi.

Bu rapor, sorunu tek tek buton bazinda degil, kalici regression testiyle yakalamak icin eklenen guvenceyi belgeler.

## Added Test

New script:

- `scripts\verify_studio_layout_stability.py`

This script opens Etiket Studio and checks:

- Base Corel-like layout remains visible.
- Repeated mouse move events do not hide/recreate Studio.
- Sidebar opens on hover and closes after pointer leaves.
- Right dock scroll stays inside the dock and does not move the whole page.
- Font combo interaction does not resize or break the property bar.
- Safe print modal opens without flicker and does not contain direct/silent print behavior.

## What It Guards

The script asserts that these key pieces remain visible after every stress step:

- `#label .corel-studio`
- `#label .corel-property-bar`
- `#label .corel-quick-production-row`
- `#label .corel-left-toolbar`
- `#label .corel-canvas-panel`
- `#manualPreview .preview-label.editor-live`
- `#label .corel-inspector`
- `#label .corel-dock-panel.active`
- `#label .corel-statusbar`

It also verifies:

- `body/html` scroll stays locked in Studio.
- `.main` does not scroll unexpectedly.
- Active page remains `label`.
- Sidebar width returns to rail size after mouse leave.
- Safe print modal says the printer is not automatic.
- No `window.print()` / direct print reference is present.

## Screenshots

Generated under:

- `output\2026-05-15\studio_layout_stability`

Important screenshots:

- `studio_layout_base.png`
- `studio_after_mousemove.png`
- `studio_sidebar_collapsed_after_leave.png`
- `studio_right_dock_scrolled.png`
- `studio_font_combo_closed_stable.png`
- `studio_safe_print_modal_stable.png`

## Commands

Passed:

- `.venv\Scripts\python.exe scripts\verify_studio_layout_stability.py`
- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m py_compile scripts\verify_studio_layout_stability.py`
- `.venv\Scripts\python.exe scripts\verify_corel_editor_interactions.py`
- `.venv\Scripts\python.exe -m pytest -q` -> 138 passed
- `.venv\Scripts\python.exe scripts\verify_clean_customer_demo_flow.py`
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`

## Remaining Risk

This test catches the known flicker/disappearing-page class in the desktop WebEngine environment. If a future UI change adds new scroll containers, native selects, fixed overlays, or hover timers, this script must be run before accepting the change.

## Decision

Status: PASSED.

Etiket Studio layout stability now has a dedicated regression gate. Future UI/UX polish should not be accepted unless this script and `verify_corel_editor_interactions.py` pass together.
