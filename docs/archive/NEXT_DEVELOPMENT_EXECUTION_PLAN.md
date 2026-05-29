# Next Development Execution Plan

Date: 2026-05-15

## Current Mode

Autonomous implementation may continue without waiting for approval, as long as the project safety boundaries are respected.

## Phase 1 - Workshop Operations Center

Priority: P1

Goal: Make the app feel like a daily production center, not separate isolated pages.

Files likely touched:

- `src\webui\app.js`
- `src\webui\styles.css`
- queue/output/history helper sections
- `scripts\verify_workshop_operations_flow.py`
- `scripts\verify_print_queue_flow.py`
- `scripts\verify_outputs_gallery_flow.py`

Work:

- Unify statuses: Hazir, Sirada, Yazdirildi, Teslim Edildi, Kontrol Gerekli.
- Keep technical/test/archive records out of default customer views.
- Add or strengthen daily production KPIs: bugunku is, bekleyen, yazdirildi, kontrol gereken, toplam adet, batch sayisi.
- Make "Teslim Edildi" visible but not confusing with printed.
- Keep print modal safe; no direct/silent print.

Tests:

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe scripts\verify_workshop_operations_flow.py`
- `.venv\Scripts\python.exe scripts\verify_print_queue_flow.py`
- `.venv\Scripts\python.exe scripts\verify_outputs_gallery_flow.py`
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`

Report:

- `WORKSHOP_OPERATIONS_CENTER_REPORT.md`

Acceptance:

- User can understand today's production from one screen.
- Queue does not show stale/test records in default mode.
- Wrong/stale PDF cannot be printed or queued as a customer job.

## Phase 2 - Studio Flicker and Layout Regression Guard

Priority: P1/P2

Goal: Prevent the mouse-move/scroll flicker and disappearing-page regressions from returning.

Files likely touched:

- `src\webui\app.js`
- `src\webui\styles.css`
- new or updated verification script

Work:

- Add a focused Playwright verification for Studio scroll, sidebar hover open/close, font dropdown, print modal, right dock scroll, and canvas persistence.
- Assert the Studio root, canvas, selected handles, right dock, top quick bar and print modal remain visible after mouse movement and scrolling.
- Avoid layout rerender loops on hover/mousemove.

Tests:

- `scripts\verify_studio_layout_stability.py` if created
- `scripts\verify_corel_editor_interactions.py`
- `scripts\verify_corel_undo_redo.py`

Report:

- `STUDIO_LAYOUT_STABILITY_REGRESSION_REPORT.md`

Acceptance:

- Moving the mouse does not recreate or hide the page.
- Right dock scrolling does not shift the entire Studio out of view.
- Print button opens safe modal without flicker.

## Phase 3 - Bulk Label Operator UX

Priority: P2 with P1 verification coverage.

Goal: Keep the 100-row Excel flow usable for real production.

Work:

- Reduce visual density in Toplu Etiket where needed.
- Ensure summary cards, gallery filters, selected item and manifest counts are always synchronized.
- Keep invalid model rows excluded from production.

Tests:

- `scripts\verify_bulk_gallery_excel_flow.py`
- 100-row fixture
- output/queue manifest checks

Report:

- `BULK_LABEL_OPERATOR_UX_FINAL_REPORT.md`

## Phase 4 - RDWorks Field Import Checklist

Priority: P2/P3, with P1 technical risk if real font/outline mismatches appear.

Goal: Prepare a clear real-world RDWorks import validation flow.

Work:

- Create or update `RDWORKS_REAL_IMPORT_FIELD_CHECKLIST.md`.
- Record expected DXF layer colors and manual checks.
- Keep RDWorks/lazer automation disabled.
- If Mochary font file is supplied, rerun real font outline tests.

Report:

- `RDWORKS_REAL_IMPORT_FIELD_CHECKLIST_REPORT.md`

