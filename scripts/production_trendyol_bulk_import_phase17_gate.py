from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_trendyol_bulk_import_phase17"
RESULT_PATH = OUTPUT_DIR / "production_trendyol_bulk_import_phase17_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import production_audit_api, trendyol_api  # noqa: E402


DATA_FILES = [
    PROJECT_ROOT / "data" / "trendyol_production_suggestions.json",
    PROJECT_ROOT / "data" / "production_audit_log.json",
]


def suppress_message_boxes() -> None:
    QMessageBox.information = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.warning = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.critical = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.question = staticmethod(lambda *args, **kwargs: QMessageBox.Yes)


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 30000):
    loop = QEventLoop()
    result = {"done": False, "value": None}

    def callback(value):
        result["done"] = True
        result["value"] = value
        loop.quit()

    wrapped = f"""
    (() => {{
      try {{
        return JSON.stringify(({script}));
      }} catch (error) {{
        return JSON.stringify({{ "__error": String(error && error.message || error), "stack": String(error && error.stack || "") }});
      }}
    }})()
    """
    window.view.page().runJavaScript(wrapped, callback)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if not result["done"]:
        raise RuntimeError(f"JavaScript timed out: {script[:180]}")
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
    wait(700)
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def backup_data() -> dict[Path, str | None]:
    return {path: path.read_text(encoding="utf-8") if path.exists() else None for path in DATA_FILES}


def restore_data(backup: dict[Path, str | None]) -> None:
    for path, content in backup.items():
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def first_label_model_path() -> str:
    candidates = sorted((PROJECT_ROOT / "templates" / "designs").glob("*.json"))
    for path in candidates:
        if "01" in path.stem.lower() and "gold" in path.stem.lower():
            return str(path)
    return str(candidates[0]) if candidates else ""


def seed_suggestions() -> dict[str, str]:
    model_path = first_label_model_path()
    now = "2026-05-22T10:00:00"
    rows = [
        {
            "id": "ty-phase17-ready",
            "source": "trendyol",
            "order_number": "TY-1001",
            "package_id": "PKT-1001",
            "line_id": "LINE-1",
            "customer_name": "Yağmur Efe",
            "product_name": "Kişiye Özel Gold Rulo Etiket",
            "barcode": "CYH-GLD-01",
            "merchant_sku": "GLD-01",
            "quantity": 2,
            "production_type": "label_and_name_cut",
            "model_key": "01",
            "model_path": model_path,
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Yağmur & Efe",
            "date_text": "19.05.2026",
            "note_text": "Nişan Hatırası",
            "name_cut_text": "Yağmur & Efe",
            "question_text": "Siparişime Yağmur & Efe, 19.05.2026, Nişan Hatırası yazılsın. Lazer isim de Yağmur & Efe olsun.",
            "question_contexts": [{"id": "q-ready", "question_text": "Siparişime Yağmur & Efe, 19.05.2026, Nişan Hatırası yazılsın. Lazer isim de Yağmur & Efe olsun.", "answer_text": ""}],
            "selected_question_id": "q-ready",
            "field_sources": {"label_text": "question_text", "date_text": "question_text", "note_text": "question_text", "name_cut_text": "question_text"},
            "field_confidence": {"label_text": 0.94, "date_text": 0.92, "note_text": 0.9, "name_cut_text": 0.94},
            "source_evidence": ["cloud_ai_extract", "question_text"],
            "confidence": 0.94,
            "status": "ready",
            "verification_status": "uretime_hazir",
            "user_verified": True,
            "mapping_found": True,
            "warnings": [],
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "ty-phase17-no-proof",
            "source": "trendyol",
            "order_number": "TY-1002",
            "package_id": "PKT-1002",
            "line_id": "LINE-2",
            "customer_name": "Helin Cemal",
            "product_name": "Kişiye Özel Etiket",
            "barcode": "CYH-GLD-01",
            "merchant_sku": "GLD-01",
            "quantity": 1,
            "production_type": "label",
            "model_key": "01",
            "model_path": model_path,
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Helin Cemal",
            "field_sources": {"label_text": "product_name"},
            "confidence": 0.5,
            "status": "review",
            "verification_status": "kanit_bekliyor",
            "user_verified": False,
            "mapping_found": True,
            "warnings": ["Müşteri mesajı yok."],
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "ty-phase17-ambiguous",
            "source": "trendyol",
            "order_number": "TY-1003",
            "package_id": "PKT-1003",
            "line_id": "LINE-3",
            "customer_name": "Ayşe Kaya",
            "product_name": "Özel Etiket",
            "barcode": "CYH-GLD-01",
            "merchant_sku": "GLD-01",
            "quantity": 1,
            "production_type": "label",
            "model_key": "01",
            "model_path": model_path,
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Ayşe",
            "question_text": "İsim yazılacak mı acaba? Ayşe olabilir.",
            "question_contexts": [{"id": "q-ambiguous", "question_text": "İsim yazılacak mı acaba? Ayşe olabilir.", "answer_text": ""}],
            "selected_question_id": "q-ambiguous",
            "field_sources": {"label_text": "question_text"},
            "source_evidence": ["question_text"],
            "confidence": 0.45,
            "status": "review",
            "verification_status": "kullanici_kontrol_gerekli",
            "user_verified": False,
            "mapping_found": True,
            "warnings": ["Mesaj belirsiz."],
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "ty-phase17-blocked",
            "source": "trendyol",
            "order_number": "TY-1004",
            "package_id": "PKT-1004",
            "line_id": "LINE-4",
            "customer_name": "Model Eksik",
            "product_name": "Eşleşmeyen Ürün",
            "barcode": "NO-MODEL",
            "merchant_sku": "NO-MODEL",
            "quantity": 1,
            "production_type": "label",
            "model_key": "",
            "model_path": "",
            "label_text": "Model Eksik",
            "question_text": "Model Eksik yazılsın.",
            "question_contexts": [{"id": "q-blocked", "question_text": "Model Eksik yazılsın.", "answer_text": ""}],
            "field_sources": {"label_text": "question_text"},
            "source_evidence": ["question_text"],
            "confidence": 0.9,
            "status": "review",
            "verification_status": "kullanici_kontrol_gerekli",
            "user_verified": False,
            "mapping_found": False,
            "warnings": ["Model eşleşmedi."],
            "created_at": now,
            "updated_at": now,
        },
    ]
    path = trendyol_api.suggestions_path(PROJECT_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    production_audit_api.audit_path(PROJECT_ROOT).write_text("[]", encoding="utf-8")
    return {"model_path": model_path}


def run_gate() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backup = backup_data()
    screenshots: dict[str, str] = {}
    try:
        seed = seed_suggestions()
        app = QApplication.instance() or QApplication(sys.argv)
        suppress_message_boxes()
        window = WebMainWindow(PROJECT_ROOT, sys.executable)
        window.resize(1920, 1080)
        window.show()
        wait(1800)

        before = run_js(window, """
        (() => {
          showSection("trendyolOrders");
          showTrendyolTab("orders");
          selectedTrendyolSuggestionId = "ty-phase17-ready";
          updateTrendyolOrders(currentState.trendyol || {});
          return {
            active: document.querySelector(".page.active")?.id || "",
            cardCount: document.querySelectorAll(".trendyol-suggestion-card").length,
            hasBulkImport: document.body.innerText.includes("Toplu Üretim’e Aktar"),
            hasNoLiveStatusText: document.body.innerText.includes("canlı sipariş durumu değişmez") || document.body.innerText.includes("canlı sipariş durumunu otomatik değiştirmez") || Array.from(document.querySelectorAll("button[title]")).some(button => button.title.includes("canlı sipariş durumu değişmez"))
          };
        })()
        """)
        screenshots["trendyol_before"] = save_screenshot(window, "trendyol-bulk-import-before-1920.png")

        evidence = run_js(window, """
        (() => {
          openTrendyolEvidenceDrawer("ty-phase17-ready", "all");
          return {
            open: document.body.classList.contains("trendyol-drawer-open"),
            text: document.body.innerText,
            hasProof: document.body.innerText.includes("Yağmur & Efe")
          };
        })()
        """)
        screenshots["evidence"] = save_screenshot(window, "trendyol-bulk-import-evidence.png")
        run_js(window, "(() => { closeTrendyolEvidenceDrawer(); return true; })()")

        import_result = window.import_trendyol_to_bulk_production([
            "ty-phase17-ready",
            "ty-phase17-no-proof",
            "ty-phase17-ambiguous",
            "ty-phase17-blocked",
        ])
        duplicate_result = window.import_trendyol_to_bulk_production(["ty-phase17-ready"])

        ui_import = run_js(window, """
        (() => {
          const items = arguments[0] || [];
          mergeTrendyolBulkItems(items);
          showSection("bulkLabel");
          setBulkGalleryFilter("all");
          return {
            active: document.querySelector(".page.active")?.id || "",
            cardCount: document.querySelectorAll("#bulkGalleryGrid .bulk-gallery-item").length,
            trendyolText: document.body.innerText.includes("Trendyol"),
            proofText: document.body.innerText.includes("Trendyol kanıtı") || document.querySelectorAll("#bulkGalleryGrid .bulk-gallery-proof").length > 0,
            readyItem: bulkGalleryItems.find(item => item.item_id === "trendyol-ty-phase17-ready"),
            noProofItem: bulkGalleryItems.find(item => item.item_id === "trendyol-ty-phase17-no-proof"),
            blockedItem: bulkGalleryItems.find(item => item.item_id === "trendyol-ty-phase17-blocked")
          };
        })()
        """.replace("arguments[0] || []", json.dumps(import_result.get("items", []), ensure_ascii=False)))
        screenshots["bulk_summary"] = save_screenshot(window, "trendyol-bulk-import-summary.png")

        run_js(window, "(() => { showSection('trendyolOrders'); showTrendyolTab('orders'); showTrendyolStatus('Bu Trendyol sipariş satırı daha önce Toplu Üretim’e aktarılmış.', 'warn'); return true; })()")
        screenshots["duplicate"] = save_screenshot(window, "trendyol-bulk-import-duplicate.png")

        run_js(window, "(() => { showSection('bulkLabel'); setBulkGalleryFilter('warning'); return true; })()")
        screenshots["missing_personalization"] = save_screenshot(window, "trendyol-bulk-import-missing-personalization.png")

        run_js(window, "(() => { showSection('bulkLabel'); setBulkGalleryFilter('all'); return true; })()")
        screenshots["bulk_badge"] = save_screenshot(window, "trendyol-bulk-gallery-badge.png")

        audit_events = production_audit_api.list_production_audit_events(PROJECT_ROOT)
        run_js(window, "(() => { showSection('productionAudit'); updateProductionAudit(currentState.productionAudit || []); return true; })()")
        screenshots["audit"] = save_screenshot(window, "trendyol-bulk-import-audit-events.png")

        window.resize(1366, 768)
        wait(900)
        run_js(window, "(() => { showSection('bulkLabel'); setBulkGalleryFilter('all'); return { active: document.querySelector('.page.active')?.id || '', width: innerWidth }; })()")
        screenshots["view_1366"] = save_screenshot(window, "trendyol-bulk-import-1366.png")

        window.resize(1920, 1080)
        wait(900)
        run_js(window, "(() => { showSection('trendyolOrders'); return { active: document.querySelector('.page.active')?.id || '', width: innerWidth }; })()")
        screenshots["view_1920"] = save_screenshot(window, "trendyol-bulk-import-1920.png")

        items = import_result.get("items") or []
        ready_item = next((item for item in items if item.get("item_id") == "trendyol-ty-phase17-ready"), {})
        no_proof_item = next((item for item in items if item.get("item_id") == "trendyol-ty-phase17-no-proof"), {})
        ambiguous_item = next((item for item in items if item.get("item_id") == "trendyol-ty-phase17-ambiguous"), {})
        blocked_item = next((item for item in items if item.get("item_id") == "trendyol-ty-phase17-blocked"), {})
        event_types = {row.get("event_type") for row in audit_events}
        assertions = {
            "trendyol_screen_ready": before.get("active") == "trendyolOrders" and before.get("cardCount", 0) >= 4,
            "safe_button_language": before.get("hasBulkImport") and before.get("hasNoLiveStatusText"),
            "evidence_visible": evidence.get("open") and evidence.get("hasProof"),
            "source_contract": ready_item.get("source") == "trendyol" and ready_item.get("source_label") == "Trendyol",
            "order_fields_moved": all(ready_item.get(key) for key in ["order_no", "customer_name", "product_name", "barcode", "sku"]),
            "proof_personalization": ready_item.get("label_text") == "Yağmur & Efe" and bool(ready_item.get("proof_text")),
            "no_proof_not_invented": not no_proof_item.get("label_text") and "proof_missing" in (no_proof_item.get("safety_flags") or []),
            "ambiguous_needs_review": ambiguous_item.get("trendyol_import_status") == "needs_review",
            "blocked_model_missing": blocked_item.get("trendyol_import_status") == "blocked" and blocked_item.get("model_status") == "MISSING",
            "duplicate_blocked": duplicate_result.get("status") == "DUPLICATE" and (duplicate_result.get("summary") or {}).get("duplicate", 0) >= 1,
            "bulk_gallery_badge": ui_import.get("trendyolText") and ui_import.get("proofText"),
            "audit_events": {"trendyol_import_started", "trendyol_sent_to_bulk_production", "trendyol_personalization_extracted", "trendyol_missing_personalization", "duplicate_detected", "blocked_detected", "manual_review_required"}.issubset(event_types),
            "no_live_trendyol_change": (import_result.get("summary") or {}).get("live_trendyol_changed") is False and (import_result.get("summary") or {}).get("cargo_invoice_triggered") is False,
            "no_auto_start": not any(token in json.dumps(import_result, ensure_ascii=False).lower() for token in ["rdworks başlatıldı", "lazer başlatıldı", "yazıcı başlatıldı"]),
        }
        failed = [key for key, ok in assertions.items() if not ok]
        result = {
            "status": "PASSED" if not failed else "FAILED",
            "checks": {
                "seed": seed,
                "before": before,
                "evidence": {"open": evidence.get("open"), "hasProof": evidence.get("hasProof")},
                "import": import_result,
                "duplicate": duplicate_result,
                "ui_import": ui_import,
                "audit_event_types": sorted(event_types),
                "assertions": assertions,
                "failed_assertions": failed,
            },
            "screenshots": screenshots,
        }
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    finally:
        restore_data(backup)


if __name__ == "__main__":
    result = run_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") != "PASSED":
        raise SystemExit(1)
