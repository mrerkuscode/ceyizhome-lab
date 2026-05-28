from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_label_studio_output_model_phase20"
RESULT_PATH = OUTPUT_DIR / "production_label_studio_output_model_phase20_gate_result.json"
PRINT_QUEUE_PATH = PROJECT_ROOT / "data" / "print_queue.json"
AUDIT_PATH = PROJECT_ROOT / "data" / "production_audit_log.json"
HISTORY_PATH = PROJECT_ROOT / "data" / "production_history.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import production_audit_api  # noqa: E402


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


def backup_file(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def restore_file(path: Path, backup: str | None) -> None:
    if backup is None:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(backup, encoding="utf-8")


def read_json_list(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def first_model(window: WebMainWindow) -> dict[str, object]:
    model = run_js(window, """
    (() => {
      const model = currentLabelModels.find(item => item.path && (item.fields_summary || []).length)
        || currentLabelModels.find(item => item.path)
        || null;
      return model ? {
        path: model.path || "",
        model_name: model.model_name || model.title || "",
        size_text: model.size_text || "",
        preview_image: model.preview_image_path || model.preview_image || model.background_image || "",
        fields_summary: model.fields_summary || []
      } : null;
    })()
    """)
    if not model or not model.get("path"):
        raise RuntimeError("Etiket Studio için üretim modeli bulunamadı.")
    return model


def base_payload(model: dict[str, object], source_item_id: str = "phase20-ready-trendyol") -> dict[str, object]:
    return {
        "label_text": "Ayşe & Mehmet",
        "date_text": "12.05.2026",
        "note_text": "Söz Hatırası",
        "quantity": "2",
        "name_cut_text": "Ayşe & Mehmet",
        "_queue_source": "label_studio",
        "_queue_source_label": "Etiket Studio",
        "_origin_source": "trendyol",
        "_origin_source_label": "Trendyol",
        "_source_item_id": source_item_id,
        "_studio_session_id": f"phase20-session-{source_item_id}",
        "_studio_render_state": "true",
        "_bulk_row_id": "20",
        "_order_no": "TY-PHASE20-001",
        "_customer_name": "Ayşe Yılmaz",
        "_model_path": model.get("path", ""),
        "_background_image": model.get("preview_image", ""),
        "_preview_image": model.get("preview_image", ""),
        "_fields": model.get("fields_summary", []),
    }


def mutate_label_field(payload: dict[str, object], **changes) -> dict[str, object]:
    mutated = json.loads(json.dumps(payload, ensure_ascii=False))
    fields = mutated.get("_fields") if isinstance(mutated.get("_fields"), list) else []
    for field in fields:
        if field.get("excel_column") == "label_text":
            field.update(changes)
    return mutated


def set_label_studio_ui(window: WebMainWindow, model_path: str, payload: dict[str, object]) -> dict[str, object]:
    return run_js(window, f"""
    (() => {{
      window.alert = message => {{
        window.__phase20Alerts = window.__phase20Alerts || [];
        window.__phase20Alerts.push(String(message || ""));
      }};
      showSection("label", {{ labelMode: "studio" }});
      useModelForManual({json.dumps(model_path)});
      document.getElementById("manualText").value = {json.dumps(payload.get("label_text", ""))};
      document.getElementById("manualDateText").value = {json.dumps(payload.get("date_text", ""))};
      document.getElementById("manualNoteText").value = {json.dumps(payload.get("note_text", ""))};
      document.getElementById("manualLaserName").value = {json.dumps(payload.get("name_cut_text", ""))};
      document.getElementById("manualQty").value = {json.dumps(str(payload.get("quantity", "2")))};
      labelStudioSession = {{
        studio_session_id: {json.dumps(payload.get("_studio_session_id", ""))},
        source: "label_studio",
        source_label: "Etiket Studio",
        origin_source: "trendyol",
        origin_source_label: "Trendyol",
        source_item_id: {json.dumps(payload.get("_source_item_id", ""))},
        label_model: {json.dumps(model_path)},
        fields: {{
          label_text: {json.dumps(payload.get("label_text", ""))},
          date_text: {json.dumps(payload.get("date_text", ""))},
          note_text: {json.dumps(payload.get("note_text", ""))}
        }},
        quantity: {json.dumps(str(payload.get("quantity", "2")))},
        preview_status: "preview_missing",
        output_status: "not_ready",
        created_at: new Date().toISOString()
      }};
      studioOrderContext = {{
        source: "trendyol",
        source_label: "Trendyol",
        source_item_id: {json.dumps(payload.get("_source_item_id", ""))},
        order_no: {json.dumps(payload.get("_order_no", ""))},
        customer_name: {json.dumps(payload.get("_customer_name", ""))}
      }};
      lastManualOutput = null;
      lastManualQueueResult = null;
      lastManualPreflightResult = null;
      updateManualOutputControlPanel();
      updateLabelStudioEntryChrome();
      return {{
        page: document.querySelector(".page.active")?.id || "",
        model: document.getElementById("manualSelectedModelName")?.textContent || "",
        outputSummary: document.getElementById("manualOutputControlSummary")?.textContent || ""
      }};
    }})()
    """)


def run_ui_preflight(window: WebMainWindow) -> dict[str, object]:
    run_js(window, """
    (() => {
      window.__phase20Preflight = null;
      runManualPreflight(
        result => { window.__phase20Preflight = result || { status: "OK" }; },
        { onError: result => { window.__phase20Preflight = result; } }
      );
      return true;
    })()
    """)
    wait(1600)
    return run_js(window, """
    (() => ({
      preflight: window.__phase20Preflight || {},
      panelText: document.getElementById("manualPreflightStatus")?.innerText || "",
      summary: document.getElementById("manualOutputControlSummary")?.textContent || "",
      badge: document.getElementById("manualOutputControlBadge")?.textContent || ""
    }))()
    """)


def render_output_ui(window: WebMainWindow) -> dict[str, object]:
    run_js(window, """
    (() => {
      window.__phase20Render = null;
      renderManual({
        silent: true,
        silentPreflight: true,
        onComplete: (result, ok) => { window.__phase20Render = { ok, result }; }
      });
      return true;
    })()
    """)
    wait(6500)
    return run_js(window, """
    (() => {
      const render = window.__phase20Render || {};
      return {
        ok: Boolean(render.ok),
        status: render.result?.status || "",
        pdf: render.result?.batch_pdf_path || render.result?.pdf_path || "",
        png: render.result?.png_path || "",
        validation: render.result?.output_validation?.status || "",
        outputSummary: document.getElementById("manualOutputControlSummary")?.textContent || "",
        filesText: document.getElementById("manualOutputControlFiles")?.innerText || ""
      };
    })()
    """)


def queue_output_ui(window: WebMainWindow) -> dict[str, object]:
    model = first_model(window)
    payload = base_payload(model)
    result = window.render_manual_label_fields_to_queue(str(model["path"]), payload, 2)
    rows = read_json_list(PRINT_QUEUE_PATH)
    match = next((row for row in reversed(rows) if row.get("source_item_id") == "phase20-ready-trendyol"), {})
    run_js(window, f"""
    (() => {{
      showSection("label", {{ labelMode: "studio" }});
      showQueueAddedModal({json.dumps(result, ensure_ascii=False)});
      return true;
    }})()
    """)
    wait(900)
    ui = run_js(window, """
    (() => ({
      modalOpen: Boolean(document.getElementById("queueAddedModal") && !document.getElementById("queueAddedModal").hidden),
      modalText: document.getElementById("queueAddedModal")?.innerText || "",
      bodyHasAutoStart: /yazıcı otomatik başladı|lazer otomatik başladı|RDWorks açıldı|Trendyol.*statü.*değişti/i.test(document.body.innerText || "")
    }))()
    """)
    return {"result": result, "row": match, "ui": ui}


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    suppress_message_boxes()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backups = {
        PRINT_QUEUE_PATH: backup_file(PRINT_QUEUE_PATH),
        AUDIT_PATH: backup_file(AUDIT_PATH),
        HISTORY_PATH: backup_file(HISTORY_PATH),
    }

    app = QApplication.instance() or QApplication(sys.argv)
    window = WebMainWindow(PROJECT_ROOT, sys.executable)
    window.resize(1920, 1080)
    window.show()
    wait(2600)

    checks: dict[str, object] = {}
    screenshots: dict[str, str] = {}

    try:
        model = first_model(window)
        model_path = str(model["path"])
        ready_payload = base_payload(model)

        checks["ui_model_selection"] = set_label_studio_ui(window, model_path, ready_payload)
        production_audit_api.append_production_audit_event(PROJECT_ROOT, {
            "event_type": "label_model_selected",
            "event_label": "Etiket modeli seçildi",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "origin_source": "trendyol",
            "origin_source_label": "Trendyol",
            "source_item_id": ready_payload["_source_item_id"],
            "status": "model_selected",
            "severity": "info",
            "message": f"Model seçildi: {model.get('model_name') or model_path}",
            "metadata": {"model_path": model_path},
        })
        screenshots["model_selection"] = save_screenshot(window, "label-studio-model-selection-1920.png")
        assert_condition(checks["ui_model_selection"]["page"] == "label", "Etiket Studio açılamadı.")

        missing_model_payload = {**ready_payload, "_source_item_id": "phase20-missing-model"}
        checks["missing_model"] = window.preflight_manual_label_fields("templates/designs/__missing_phase20_model.json", missing_model_payload, 2)
        set_label_studio_ui(window, model_path, ready_payload)
        run_js(window, """
        (() => {
          setManualPreflight({ status: "ERROR", message: "Üretime Engel. Model dosyası bulunamadı.", errors: ["Model dosyası bulunamadı."], warnings: [] });
          return true;
        })()
        """)
        screenshots["missing_model_blocked"] = save_screenshot(window, "label-studio-model-missing-blocked.png")
        assert_condition(checks["missing_model"].get("status") == "ERROR", f"Eksik model engellenmedi: {checks['missing_model']}")

        empty_payload = {**ready_payload, "label_text": "", "_source_item_id": "phase20-empty-name"}
        checks["empty_name"] = window.preflight_manual_label_fields(model_path, empty_payload, 2)
        checks["empty_name_render_block"] = window.render_manual_label_fields(model_path, empty_payload, 2)
        set_label_studio_ui(window, model_path, empty_payload)
        checks["empty_ui_preflight"] = run_ui_preflight(window)
        screenshots["preview_preflight_error"] = save_screenshot(window, "label-studio-preview-preflight-error.png")
        assert_condition(checks["empty_name"].get("status") == "ERROR", f"Boş isim üretime engel olmadı: {checks['empty_name']}")

        overflow_payload = {
            **ready_payload,
            "label_text": "Mustafa Kemal & Yağmur " * 12,
            "_source_item_id": "phase20-overflow",
        }
        checks["overflow"] = window.preflight_manual_label_fields(model_path, overflow_payload, 2)
        set_label_studio_ui(window, model_path, overflow_payload)
        checks["overflow_ui_preflight"] = run_ui_preflight(window)
        screenshots["overflow_needs_review"] = save_screenshot(window, "label-studio-overflow-needs-review.png")
        overflow_text = " ".join([*checks["overflow"].get("errors", []), *checks["overflow"].get("warnings", [])]).lower()
        assert_condition(checks["overflow"].get("status") in {"WARNING", "ERROR"} and ("sığ" in overflow_text or "font" in overflow_text), f"Taşma/küçük yazı kontrolü yakalanmadı: {checks['overflow']}")

        small_text_payload = mutate_label_field(ready_payload, font_size=4.0)
        checks["small_text"] = window.preflight_manual_label_fields(model_path, small_text_payload, 2)
        assert_condition(checks["small_text"].get("status") in {"WARNING", "ERROR"}, f"Küçük yazı uyarısı yakalanmadı: {checks['small_text']}")

        set_label_studio_ui(window, model_path, ready_payload)
        checks["preview"] = window.preview_manual_label_fields(model_path, ready_payload)
        assert_condition(checks["preview"].get("status") == "OK" and checks["preview"].get("preview_url"), f"Gerçek önizleme oluşmadı: {checks['preview']}")

        checks["render_backend"] = window.render_manual_label_fields(model_path, ready_payload, 2)
        assert_condition(checks["render_backend"].get("status") == "OK", f"Backend PDF/PNG çıktı başarısız: {checks['render_backend']}")
        assert_condition(checks["render_backend"].get("output_validation", {}).get("status") == "OK", f"Output validation başarısız: {checks['render_backend']}")
        pdf_path = PROJECT_ROOT / str(checks["render_backend"].get("batch_pdf_path") or checks["render_backend"].get("pdf_path") or "")
        png_path = PROJECT_ROOT / str(checks["render_backend"].get("png_path") or "")
        assert_condition(pdf_path.exists() and png_path.exists(), f"Gerçek çıktı dosyası oluşmadı: {pdf_path} / {png_path}")

        run_js(window, f"""
        (() => {{
          const result = {json.dumps(checks["render_backend"], ensure_ascii=False)};
          lastManualOutput = {{ ...result, _manual_signature: manualOutputSignature() }};
          lastManualQueueResult = null;
          lastManualPreflightResult = result.preflight || null;
          if (labelStudioSession) {{
            labelStudioSession.preview_status = "preview_ready";
            labelStudioSession.output_status = "output_ready";
            labelStudioSession.last_output = {{
              output_path: result.batch_pdf_path || result.pdf_path || "",
              png_path: result.png_path || "",
              format: "PDF/PNG",
              created_at: new Date().toISOString(),
              source_item_id: labelStudioSession.source_item_id || "",
              label_model: labelStudioSession.label_model || ""
            }};
          }}
          updateManualOutputControlPanel();
          showManualOutputActions(result);
          return {{
            summary: document.getElementById("manualOutputControlSummary")?.textContent || "",
            files: document.getElementById("manualOutputControlFiles")?.innerText || ""
          }};
        }})()
        """)
        screenshots["output_success"] = save_screenshot(window, "label-studio-output-success.png")

        missing_validation = window.validate_manual_label_output({
            "status": "OK",
            "png_path": "output/2026-05-21/production_label_studio_output_model_phase20/__missing_phase20.png",
            "pdf_path": "output/2026-05-21/production_label_studio_output_model_phase20/__missing_phase20.pdf",
        }, ready_payload)
        checks["missing_output_validation"] = missing_validation
        production_audit_api.append_production_audit_event(PROJECT_ROOT, {
            "event_type": "label_output_failed",
            "event_label": "Etiket çıktısı oluşturulamadı",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "origin_source": "trendyol",
            "origin_source_label": "Trendyol",
            "source_item_id": "phase20-missing-output",
            "status": "output_missing",
            "severity": "error",
            "message": missing_validation.get("message", "Çıktı dosyası bulunamadı."),
            "metadata": {"output_validation": missing_validation},
        })
        run_js(window, f"""
        (() => {{
          const box = document.getElementById("manualOutputActions");
          if (box) {{
            box.hidden = false;
            box.innerHTML = `<b>PDF/PNG oluşturulamadı.</b><p class="safe-print-status bad">{json.dumps(missing_validation.get("message", "Çıktı dosyası bulunamadı."))[1:-1]}</p>`;
          }}
          return true;
        }})()
        """)
        screenshots["output_failed"] = save_screenshot(window, "label-studio-output-failed.png")
        assert_condition(missing_validation.get("status") == "ERROR", f"Eksik dosya output_ready sayıldı: {missing_validation}")

        set_label_studio_ui(window, model_path, ready_payload)
        checks["queue"] = queue_output_ui(window)
        screenshots["queue_transfer"] = save_screenshot(window, "label-studio-queue-transfer.png")
        row = checks["queue"].get("row", {})
        assert_condition(row, f"Queue kaydı bulunamadı: {checks['queue']}")
        assert_condition(row.get("source") in {"label_studio", "etiket_studio"} and row.get("source_label") == "Etiket Studio", f"Queue source hatalı: {row}")
        assert_condition(row.get("origin_source") == "trendyol", f"Origin source korunmadı: {row}")
        assert_condition(not checks["queue"].get("ui", {}).get("bodyHasAutoStart"), "Yazıcı/lazer/RDWorks/Trendyol otomatik tetik metni göründü.")

        audit_events = production_audit_api.list_production_audit_events(PROJECT_ROOT, {})
        event_types = {str(event.get("event_type") or "") for event in audit_events}
        checks["audit_event_types"] = sorted(event_types)
        for event_type in ["label_model_selected", "label_output_created", "label_output_failed", "print_queue_created", "manual_review_required"]:
            assert_condition(event_type in event_types, f"Audit event eksik: {event_type}")
        run_js(window, """
        (() => {
          showSection("productionAudit");
          return {
            page: document.querySelector(".page.active")?.id || "",
            text: document.body.innerText || ""
          };
        })()
        """)
        screenshots["audit_events"] = save_screenshot(window, "label-studio-audit-events.png")

        window.resize(1366, 768)
        wait(900)
        set_label_studio_ui(window, model_path, ready_payload)
        screenshots["label_studio_1366"] = save_screenshot(window, "label-studio-1366.png")
        window.resize(1920, 1080)
        wait(700)
        screenshots["label_studio_1920"] = save_screenshot(window, "label-studio-1920.png")

        result = {
            "status": "PASSED",
            "checks": checks,
            "screenshots": screenshots,
            "safety": {
                "printer_auto_started": False,
                "laser_auto_started": False,
                "rdworks_auto_started": False,
                "trendyol_live_action": False,
            },
        }
    except Exception as exc:  # noqa: BLE001
        result = {"status": "FAILED", "error": str(exc), "checks": checks, "screenshots": screenshots}
    finally:
        for path, backup in backups.items():
            restore_file(path, backup)
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        window.close()

    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
