from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_trendyol_evidence_drawer_phase18"
RESULT_PATH = OUTPUT_DIR / "production_trendyol_evidence_drawer_phase18_gate_result.json"

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
        stem = path.stem.lower()
        if "01" in stem and "gold" in stem:
            return str(path)
    return str(candidates[0]) if candidates else ""


def seed_suggestions() -> dict[str, str]:
    model_path = first_label_model_path()
    now = "2026-05-22T10:30:00"
    rows = [
        {
            "id": "ty-phase18-ready",
            "source": "trendyol",
            "order_number": "TY-1801",
            "package_id": "PKT-1801",
            "line_id": "LINE-1801",
            "customer_name": "Ayşe & Mehmet",
            "product_name": "Kişiye Özel Gold Rulo Etiket",
            "barcode": "CYH-GLD-01",
            "merchant_sku": "GLD-01",
            "quantity": 2,
            "production_type": "label_and_name_cut",
            "model_key": "01",
            "model_path": model_path,
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Ayşe & Mehmet",
            "date_text": "12.05.2026",
            "note_text": "Söz Hatırası",
            "name_cut_text": "Ayşe & Mehmet",
            "question_text": "Etikete Ayşe & Mehmet, 12.05.2026, Söz Hatırası yazılsın. Lazer isim Ayşe & Mehmet olsun.",
            "question_contexts": [{"id": "q-1801", "question_text": "Etikete Ayşe & Mehmet, 12.05.2026, Söz Hatırası yazılsın. Lazer isim Ayşe & Mehmet olsun.", "answer_text": ""}],
            "selected_question_id": "q-1801",
            "field_sources": {"label_text": "question_text", "date_text": "question_text", "note_text": "question_text", "name_cut_text": "question_text"},
            "field_confidence": {"label_text": 0.96, "date_text": 0.94, "note_text": 0.92, "name_cut_text": 0.96},
            "source_evidence": ["question_text"],
            "confidence": 0.96,
            "status": "ready",
            "verification_status": "uretime_hazir",
            "user_verified": True,
            "mapping_found": True,
            "warnings": [],
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "ty-phase18-no-proof",
            "source": "trendyol",
            "order_number": "TY-1802",
            "package_id": "PKT-1802",
            "line_id": "LINE-1802",
            "customer_name": "Helin Cemal",
            "product_name": "Kişiye Özel Etiket",
            "barcode": "CYH-GLD-01",
            "merchant_sku": "GLD-01",
            "quantity": 1,
            "production_type": "label",
            "model_key": "01",
            "model_path": model_path,
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "",
            "field_sources": {},
            "confidence": 0.92,
            "status": "review",
            "verification_status": "kanit_bekliyor",
            "user_verified": False,
            "mapping_found": True,
            "warnings": ["Müşteri mesajı yok."],
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "ty-phase18-model-missing",
            "source": "trendyol",
            "order_number": "TY-1803",
            "package_id": "PKT-1803",
            "line_id": "LINE-1803",
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
            "question_contexts": [{"id": "q-1803", "question_text": "Model Eksik yazılsın.", "answer_text": ""}],
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

        import_result = window.import_trendyol_to_bulk_production([
            "ty-phase18-ready",
            "ty-phase18-no-proof",
            "ty-phase18-model-missing",
        ])
        duplicate_result = window.import_trendyol_to_bulk_production(["ty-phase18-ready"])

        gallery = run_js(window, """
        (() => {
          const items = arguments[0] || [];
          mergeTrendyolBulkItems(items);
          showSection("bulkLabel");
          setBulkGalleryFilter("all");
          return {
            active: document.querySelector(".page.active")?.id || "",
            cardCount: document.querySelectorAll("#bulkGalleryGrid .bulk-gallery-item").length,
            hasTrendyolBadge: document.body.innerText.includes("Trendyol"),
            hasEvidenceButton: document.body.innerText.includes("Kanıtı Gör"),
            readyBadge: document.body.innerText.includes("Kanıtlı"),
            noProofBadge: document.body.innerText.includes("Kanıt yok"),
            modelMissingBadge: document.body.innerText.includes("Model eksik")
          };
        })()
        """.replace("arguments[0] || []", json.dumps(import_result.get("items", []), ensure_ascii=False)))
        screenshots["gallery"] = save_screenshot(window, "trendyol-evidence-gallery-1920.png")

        drawer_no_proof = run_js(window, """
        (() => {
          openBulkTrendyolEvidenceDrawer("trendyol-ty-phase18-no-proof");
          return {
            open: document.body.classList.contains("bulk-trendyol-drawer-open"),
            text: document.body.innerText,
            hasNoProof: document.body.innerText.includes("Kanıt yok"),
            hasCorrection: document.body.innerText.includes("Operatör düzeltme"),
            noProductGuess: document.body.innerText.includes("Ürün başlığından isim, tarih, not veya lazer isim üretilmez")
          };
        })()
        """)
        screenshots["no_proof_drawer"] = save_screenshot(window, "trendyol-evidence-no-proof-review.png")

        correction_result = window.save_trendyol_operator_correction("ty-phase18-no-proof", {
            "label_text": "Helin Cemal",
            "date_text": "02.06.2026",
            "note_text": "Nişan Hatırası",
            "name_cut_text": "Helin Cemal",
            "model_path": seed["model_path"],
            "quantity": 1,
            "product_match_note": "Operatör müşteriyle teyit etti; canlı Trendyol işlemi yapılmadı.",
            "batch_id": (import_result.get("batch_id") or ""),
        })
        corrected_item = correction_result.get("item") or {}

        correction_ui = run_js(window, """
        (() => {
          const item = arguments[0] || {};
          bulkGalleryItems = bulkGalleryItems.map(row => row.item_id === item.item_id ? { ...row, ...item } : row);
          currentState.bulkGalleryItems = bulkGalleryItems;
          document.body.classList.add("bulk-trendyol-drawer-open");
          return {
            open: document.body.classList.contains("bulk-trendyol-drawer-open"),
            hasOperator: document.body.innerText.includes("Operatör düzeltildi"),
            hasManualSource: document.body.innerText.includes("Operatör manuel"),
            hasReady: document.body.innerText.includes("Hazır"),
            itemId: item.item_id,
            status: (bulkGalleryItems.find(row => row.item_id === item.item_id) || {}).status || "",
            modelStatus: (bulkGalleryItems.find(row => row.item_id === item.item_id) || {}).model_status || ""
          };
        })()
        """.replace("arguments[0] || {}", json.dumps(corrected_item, ensure_ascii=False)), timeout_ms=90000)
        screenshots["operator_correction"] = save_screenshot(window, "trendyol-evidence-operator-correction.png")

        run_js(window, "(() => { closeBulkTrendyolEvidenceDrawer(); showSection('bulkLabel'); selectedBulkGalleryItemId = 'trendyol-ty-phase18-ready'; renderBulkGallery(); return true; })()")
        screenshots["model_matched"] = save_screenshot(window, "trendyol-evidence-model-matched.png")

        model_missing = run_js(window, """
        (() => {
          closeBulkTrendyolEvidenceDrawer();
          showSection("bulkLabel");
          selectedBulkGalleryItemId = "trendyol-ty-phase18-model-missing";
          renderBulkGallery();
          const item = bulkGalleryItems.find(row => row.item_id === "trendyol-ty-phase18-model-missing") || {};
          return {
            open: true,
            blocked: String(item.model_status || "").toUpperCase() === "MISSING" && String(item.status || "").toUpperCase() === "ERROR"
          };
        })()
        """)
        screenshots["model_missing"] = save_screenshot(window, "trendyol-evidence-model-missing-blocked.png")

        run_js(window, "(() => { showSection('bulkLabel'); setBulkGalleryFilter('ready'); closeBulkTrendyolEvidenceDrawer(); return true; })()")
        screenshots["after_ready"] = save_screenshot(window, "trendyol-evidence-after-ready.png")

        audit_events = production_audit_api.list_production_audit_events(PROJECT_ROOT)
        run_js(window, "(() => { showSection('productionAudit'); updateProductionAudit(currentState.productionAudit || []); return true; })()")
        screenshots["audit"] = save_screenshot(window, "trendyol-evidence-audit-events.png")

        window.resize(1366, 768)
        wait(900)
        run_js(window, "(() => { showSection('bulkLabel'); setBulkGalleryFilter('all'); return { width: innerWidth, active: document.querySelector('.page.active')?.id || '' }; })()")
        screenshots["view_1366"] = save_screenshot(window, "trendyol-evidence-1366.png")

        window.resize(1920, 1080)
        wait(900)
        run_js(window, "(() => { showSection('bulkLabel'); setBulkGalleryFilter('all'); return { width: innerWidth, active: document.querySelector('.page.active')?.id || '' }; })()")
        screenshots["view_1920"] = save_screenshot(window, "trendyol-evidence-1920.png")

        items = import_result.get("items") or []
        ready_item = next((item for item in items if item.get("item_id") == "trendyol-ty-phase18-ready"), {})
        no_proof_item = next((item for item in items if item.get("item_id") == "trendyol-ty-phase18-no-proof"), {})
        blocked_item = next((item for item in items if item.get("item_id") == "trendyol-ty-phase18-model-missing"), {})
        event_types = {row.get("event_type") for row in audit_events}
        correction_event = next((row for row in audit_events if row.get("event_type") == "trendyol_operator_correction_saved"), {})
        correction_metadata = correction_event.get("metadata") or {}
        assertions = {
            "gallery_ready": gallery.get("active") == "bulkLabel" and gallery.get("cardCount", 0) >= 3,
            "trendyol_badges_visible": gallery.get("hasTrendyolBadge") and gallery.get("hasEvidenceButton") and gallery.get("readyBadge") and gallery.get("noProofBadge"),
            "drawer_opens": drawer_no_proof.get("open") and drawer_no_proof.get("hasCorrection"),
            "proof_sources_visible": drawer_no_proof.get("hasNoProof") and drawer_no_proof.get("noProductGuess"),
            "no_proof_not_invented": not no_proof_item.get("label_text") and "proof_missing" in (no_proof_item.get("safety_flags") or []),
            "operator_correction_saved": correction_result.get("status") in {"OK", "WARN"} and corrected_item.get("label_text") == "Helin Cemal",
            "operator_manual_source": (corrected_item.get("field_sources") or {}).get("label_text") == "operator_manual",
            "needs_review_becomes_ready": corrected_item.get("trendyol_import_status") in {"proof_confirmed", "ready"} and corrected_item.get("status") == "READY",
            "model_missing_blocked": blocked_item.get("trendyol_import_status") == "blocked" and blocked_item.get("model_status") == "MISSING" and blocked_item.get("status") == "ERROR",
            "duplicate_import_blocked": duplicate_result.get("status") == "DUPLICATE" and (duplicate_result.get("summary") or {}).get("duplicate", 0) >= 1,
            "audit_correction_events": {"trendyol_operator_correction_started", "trendyol_operator_correction_saved", "trendyol_personalization_confirmed", "trendyol_model_matched"}.issubset(event_types),
            "audit_metadata_changed_values": bool(correction_metadata.get("changed_fields")),
            "no_live_trendyol_change": (import_result.get("summary") or {}).get("live_trendyol_changed") is False and (import_result.get("summary") or {}).get("cargo_invoice_triggered") is False,
            "no_auto_start": not any(token in json.dumps([import_result, correction_result], ensure_ascii=False).lower() for token in ["rdworks başlatıldı", "lazer başlatıldı", "yazıcı başlatıldı"]),
        }
        failed = [key for key, ok in assertions.items() if not ok]
        result = {
            "status": "PASSED" if not failed else "FAILED",
            "checks": {
                "seed": seed,
                "gallery": gallery,
                "drawer_no_proof": {
                    "open": drawer_no_proof.get("open"),
                    "hasNoProof": drawer_no_proof.get("hasNoProof"),
                    "hasCorrection": drawer_no_proof.get("hasCorrection"),
                    "noProductGuess": drawer_no_proof.get("noProductGuess"),
                },
                "correction_result": correction_result,
                "correction_ui": correction_ui,
                "duplicate_result": duplicate_result,
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

