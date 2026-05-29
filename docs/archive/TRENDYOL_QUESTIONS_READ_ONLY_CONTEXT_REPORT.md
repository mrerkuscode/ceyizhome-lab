# Trendyol Questions Read-only Context Report

Date: 2026-05-15

## Summary

Trendyol customer questions/messages were connected to Cyzella as a read-only production context source. The feature helps the operator see possible name/date/note evidence from customer messages, but it does not answer questions, create outputs, add queue items, or start any automation.

## What Changed

- Added `data/trendyol_questions_context.json` as the local read-only question context store.
- Added `sync_questions` and `list_questions` in `src/webui_backend/trendyol_api.py`.
- Added question normalization with deterministic field suggestions:
  - label text
  - date
  - note
  - name cut text
  - confidence and evidence
- Added desktop controller and bridge method `sync_trendyol_questions`.
- Added `Soruları Oku` button to the Trendyol page.
- Added `Sorular / Mesajlar` read-only panel to show the latest question context.

## Safety

- No automatic Trendyol answer is sent.
- No PDF/PNG generation is triggered.
- No print queue item is created.
- No RDWorks, laser, CorelDRAW, Illustrator or direct print automation is triggered.
- API credentials are still required for live fetch and are not copied from the old project.

## Tests

- `node --check src\webui\app.js` -> PASSED
- `.venv\Scripts\python.exe -m py_compile src\webui_backend\trendyol_api.py src\webui_backend\trendyol_mapping_api.py src\intelligence\trendyol_order_extractor.py src\webui_backend\bridge.py` -> PASSED
- `.venv\Scripts\python.exe -m pytest -q tests\test_trendyol_order_to_production.py` -> PASSED, 10 tests
- `.venv\Scripts\python.exe scripts\verify_trendyol_order_to_production_flow.py` -> PASSED
- `.venv\Scripts\python.exe -m pytest -q` -> PASSED, 148 tests
- `.venv\Scripts\python.exe scripts\real_production_quality_gate.py` -> PASSED
- `.venv\Scripts\python.exe scripts\final_acceptance_gate.py` -> PASSED
- `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py` -> PASSED

## Remaining Risk

- Live Trendyol question fetch needs real credentials in Cyzella settings.
- The extracted fields are suggestions only; operator review remains required.

## Decision

The old integration's questions capability is now safely represented in Cyzella without touching the old project and without adding any risky automation.
