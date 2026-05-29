# Workshop Operations Center Report

Date: 2026-05-15

## Summary

The six approved workshop-operation items were completed and verified without changing the PDF/PNG render chain, output validation chain, safe print behavior, RDWorks behavior, or laser behavior.

Main result: customer-facing production screens now separate real customer work from technical/test/QA records more reliably. The home dashboard, print queue, output gallery, and production history use customer-safe filtering so stale/test records do not make the product look broken during normal use.

## Completed Items

1. Home dashboard uses customer queue rows for daily production metrics.
2. Print Queue keeps test/QA records out of the default customer queue and exposes them through the Test/QA Archive path.
3. Label Outputs already keeps technical archive separate; regression flow confirmed the default gallery shows customer outputs only.
4. Delivered status is present in queue status language and was verified through backend state transition.
5. Production history now filters technical/test records from normal customer history.
6. Regression tests were expanded and rerun.

## Files Changed

- `src/webui/app.js`
  - Added customer-safe queue filtering helpers.
  - Added customer-safe production history filtering helpers.
  - Updated Home dashboard queue metrics to ignore Test/QA archive work.
  - Updated Home recent jobs and Production History rendering to avoid showing technical/test records as normal customer jobs.
  - Expanded test/archive detection for stale-control and order-test variants.

- `scripts/verify_workshop_operations_flow.py`
  - Added permanent regression checks that workshop test jobs do not appear on the default Home/Queue customer views.
  - Added Test/QA archive classification verification.
  - Kept delivered/pending/safe-print backend verification.

## Verification

Passed:

- `node --check src\webui\app.js`
- `.venv\Scripts\python.exe -m py_compile scripts\verify_workshop_operations_flow.py scripts\verify_studio_layout_stability.py`
- `.venv\Scripts\python.exe -m pytest -q` -> 138 passed
- `.venv\Scripts\python.exe scripts\verify_workshop_operations_flow.py`
- `.venv\Scripts\python.exe scripts\verify_print_queue_flow.py`
- `.venv\Scripts\python.exe scripts\verify_outputs_gallery_flow.py`
- `.venv\Scripts\python.exe scripts\verify_clean_customer_demo_flow.py`
- `.venv\Scripts\python.exe scripts\verify_studio_layout_stability.py`
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`

## Screenshot Evidence

- `output/2026-05-15/workshop_operations/workshop_home_dashboard.png`
- `output/2026-05-15/workshop_operations/workshop_queue_detail.png`
- `output/2026-05-15/clean_customer_demo_flow/outputs_customer_gallery.png`
- `output/2026-05-15/clean_customer_demo_flow/queue_customer_ready.png`
- `output/2026-05-15/clean_customer_demo_flow/queue_customer_print_modal.png`
- `output/2026-05-15/studio_layout_stability/studio_layout_base.png`
- `output/2026-05-15/studio_layout_stability/studio_after_mousemove.png`
- `output/2026-05-15/studio_layout_stability/studio_right_dock_scrolled.png`
- `output/2026-05-15/studio_layout_stability/studio_safe_print_modal_stable.png`

## Safety Confirmation

- Direct/silent print remains disabled.
- Yazdir flow opens a user confirmation path; it does not silently print.
- RDWorks was not opened.
- Laser was not started.
- CorelDRAW and Illustrator were not opened.
- Source AI/CDR files were not modified.
- PDF/PNG output validation and queue behavior remain green.

## Remaining Risks

- Real production data can still contain old records. These are now separated from normal customer views, but a future housekeeping action can add a clearer archive management UI.
- `real_production_quality_gate.py` and `final_acceptance_gate.py` should keep running sequentially, not in parallel, because both touch shared preview/quality-gate artifacts.
- RDWorks real machine import remains a manual field-check item.

## Next Recommendation

Move to Toplu Etiket operator UX hardening: 100-row gallery review, summary synchronization, error-row exclusion, and batch/queue metadata consistency.
