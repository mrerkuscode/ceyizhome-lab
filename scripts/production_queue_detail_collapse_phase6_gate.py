from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_queue_detail_collapse_phase6"
RESULT_PATH = OUTPUT_DIR / "production_queue_detail_collapse_phase6_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


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


def seed_rows(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      showSection("printQueue");
      currentState.printQueue = [
        {
          id: "rowdesign-studio",
          created_at: "2026-05-21 11:00:00",
          job_type: "Manuel",
          source: "etiket_studio",
          source_label: "Etiket Studio",
          relative_path: "output/2026-05-21/manual/01_a_gold_ayse_mehmet_2adet.pdf",
          file_type: "PDF",
          model_name: "01 A Gold Rulo Etiket",
          label_text: "Ayşe & Mehmet",
          date_text: "12.05.2026",
          note_text: "Söz Hatırası",
          quantity: 2,
          status: "Beklemede",
          validation_status: "OK",
          size_text: "50 x 30 mm"
        },
        {
          id: "rowdesign-manual",
          created_at: "2026-05-21 11:05:00",
          job_type: "Manuel",
          source: "manual_label",
          source_label: "Manuel Etiket",
          relative_path: "output/2026-05-21/manual/yagmur_efe_1adet.pdf",
          file_type: "PDF",
          model_name: "01 A Gold Rulo Etiket",
          label_text: "Yağmur & Efe",
          date_text: "19.05.2026",
          note_text: "Nişan Hatırası",
          quantity: 1,
          status: "Yazdırıldı",
          validation_status: "OK",
          size_text: "50 x 30 mm"
        },
        {
          id: "rowdesign-legacy",
          created_at: "2026-05-21 11:10:00",
          job_type: "Manuel",
          relative_path: "output/legacy/old_record_row_design.pdf",
          file_type: "PDF",
          model_name: "Eski Gold Şablon",
          label_text: "Eski kayıt",
          date_text: "12.05.2026",
          note_text: "Fallback kontrol",
          quantity: 1,
          status: "Beklemede",
          validation_status: "OK",
          size_text: "50 x 30 mm"
        },
        {
          id: "rowdesign-missing",
          created_at: "2026-05-21 11:15:00",
          job_type: "Manuel",
          source: "bulk_production",
          source_label: "Toplu Üretim",
          relative_path: "",
          file_type: "PDF",
          model_name: "Eksik Dosya Modeli",
          label_text: "Kontrol Gerekli",
          date_text: "",
          note_text: "PDF yolu yok",
          quantity: 3,
          status: "Beklemede",
          validation_status: "MISSING",
          size_text: "50 x 30 mm"
        }
      ];
      selectedPrintQueueIds.clear();
      if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters();
      if (typeof updatePrintQueue === "function") updatePrintQueue(currentState.printQueue);
      document.querySelector(".main")?.scrollTo({ top: 0, left: 0, behavior: "auto" });
      return { rows: currentState.printQueue.length };
    })()
    """)


def inspect_rows(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const rows = Array.from(document.querySelectorAll("#printQueueList .queue-job-card"));
      const first = rows[0];
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        rowCount: rows.length,
        firstText: first?.innerText || "",
        firstClass: first?.className || "",
        hasPreviewStack: Boolean(first?.querySelector(".queue-preview-stack")),
        hasModelKicker: Boolean(first?.querySelector(".queue-model-kicker")),
        hasLabelTitle: Boolean(first?.querySelector(".queue-label-title")),
        actionSetCount: first?.querySelectorAll(".queue-action-set").length || 0,
        sourceBadges: rows.map(row => row.querySelector(".source-badge")?.textContent.trim() || ""),
        sourceClasses: rows.map(row => row.querySelector(".source-badge")?.className || ""),
        validationTexts: rows.map(row => row.querySelector(".queue-quality")?.innerText || ""),
        actionTexts: rows.map(row => row.querySelector(".queue-actions")?.innerText || ""),
        placeholderTexts: rows.map(row => row.querySelector(".queue-thumb")?.innerText || ""),
        detailText: document.getElementById("queueDetailInfo")?.innerText || ""
      };
    })()
    """)


def focus_row(window: WebMainWindow, row_id: str) -> dict:
    return run_js(window, f"""
    (() => {{
      if (typeof selectPrintQueueItem === "function") selectPrintQueueItem("{row_id}");
      const row = document.querySelector('[data-queue-id="{row_id}"]');
      row?.scrollIntoView({{ block: "center", inline: "nearest" }});
      return {{
        text: row?.innerText || "",
        sourceClass: row?.querySelector(".source-badge")?.className || "",
        placeholder: row?.querySelector(".queue-thumb")?.innerText || "",
        actions: row?.querySelector(".queue-actions")?.innerText || "",
        detail: document.getElementById("queueDetailInfo")?.innerText || ""
      }};
    }})()
    """)


def inspect_detail_state(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const layout = document.getElementById("printQueueLayout");
      const panel = document.getElementById("queueDetailPanel");
      const rail = document.getElementById("queueDetailRail");
      const toggle = document.getElementById("queueDetailToggle");
      const row = document.querySelector("#printQueueList .queue-job-card");
      const layoutRect = layout?.getBoundingClientRect();
      const panelRect = panel?.getBoundingClientRect();
      const rowRect = row?.getBoundingClientRect();
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        layoutClass: layout?.className || "",
        panelClass: panel?.className || "",
        panelWidth: Math.round(panelRect?.width || 0),
        layoutWidth: Math.round(layoutRect?.width || 0),
        rowWidth: Math.round(rowRect?.width || 0),
        railHidden: Boolean(rail?.hidden),
        railText: rail?.innerText || "",
        toggleText: toggle?.textContent || "",
        detailText: document.getElementById("queueDetailInfo")?.innerText || "",
        detailStatus: document.getElementById("queueDetailStatus")?.innerText || ""
      };
    })()
    """)


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(500)
    outcome["checks"]["seed"] = seed_rows(window)
    outcome["checks"]["rows_1920"] = inspect_rows(window)
    outcome["screenshots"]["row_1920"] = save_screenshot(window, "queue-row-design-1920.png")

    window.resize(1366, 768)
    wait(800)
    outcome["checks"]["rows_1366"] = inspect_rows(window)
    outcome["screenshots"]["row_1366"] = save_screenshot(window, "queue-row-design-1366.png")

    window.resize(1920, 1080)
    wait(500)
    outcome["checks"]["legacy"] = focus_row(window, "rowdesign-legacy")
    outcome["screenshots"]["legacy"] = save_screenshot(window, "queue-row-design-legacy.png")

    run_js(window, """(() => { if (typeof setPrintQueueStatusFilter === "function") setPrintQueueStatusFilter("missing"); return true; })()""")
    outcome["checks"]["missing_preview"] = focus_row(window, "rowdesign-missing")
    outcome["screenshots"]["missing_preview"] = save_screenshot(window, "queue-row-design-missing-preview.png")

    rows_1920 = outcome["checks"]["rows_1920"]
    if rows_1920["activePage"] != "printQueue":
        raise AssertionError("Yazdirma Sirasi aktif degil")
    if rows_1920["rowCount"] < 3:
        raise AssertionError(f"Test satirlari render edilmedi: {json.dumps(rows_1920, ensure_ascii=False)}")
    if not rows_1920["hasPreviewStack"]:
        raise AssertionError("Satir onizleme/dosya tipi stack yapisi yok")
    if not rows_1920["hasModelKicker"] or not rows_1920["hasLabelTitle"]:
        raise AssertionError("Satir is bilgisi hiyerarsisi eksik")
    if rows_1920["actionSetCount"] < 4:
        raise AssertionError("Aksiyonlar dosya/yazdirma/durum/tehlikeli gruplarina ayrilmadi")
    joined_sources = " ".join(rows_1920["sourceBadges"])
    for label in ["Etiket Studio", "Manuel Etiket", "Manuel"]:
        if label not in joined_sources:
            raise AssertionError(f"Kaynak rozeti eksik: {label}")
    if "source-badge--legacy" not in outcome["checks"]["legacy"]["sourceClass"]:
        raise AssertionError("Eski kayit source fallback rozeti korunmadi")
    if "Önizleme yok" not in outcome["checks"]["missing_preview"]["placeholder"]:
        raise AssertionError(f"Eksik preview placeholder gorunmuyor: {json.dumps(outcome['checks']['missing_preview'], ensure_ascii=False)}")
    if "source-badge--bulk" not in outcome["checks"]["missing_preview"]["sourceClass"]:
        raise AssertionError("Eksik/kontrol gerekli satirinda Toplu Uretim source rozeti korunmadi")
    if "PDF" not in outcome["checks"]["missing_preview"]["actions"] or "Yazdır" not in outcome["checks"]["missing_preview"]["actions"]:
        raise AssertionError("Eksik dosya satirinda aksiyonlar okunabilir kalmadi")

    outcome["status"] = "PASSED"
    return outcome


def run_gate_phase6(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(500)
    outcome["checks"]["seed"] = seed_rows(window)
    run_js(window, """
    (() => {
      localStorage.setItem("ceyizhome_print_queue_detail_collapsed", "0");
      printQueueDetailCollapsed = false;
      applyPrintQueueDetailPanelState();
      selectPrintQueueItem("rowdesign-studio");
      return true;
    })()
    """)
    wait(400)
    outcome["checks"]["open_1920"] = inspect_detail_state(window)
    outcome["screenshots"]["open_1920"] = save_screenshot(window, "queue-detail-open-1920.png")

    run_js(window, """(() => { togglePrintQueueDetailPanel(false); return true; })()""")
    wait(400)
    outcome["checks"]["collapsed_1920"] = inspect_detail_state(window)
    outcome["screenshots"]["collapsed_1920"] = save_screenshot(window, "queue-detail-collapsed-1920.png")

    window.resize(1366, 768)
    wait(800)
    run_js(window, """
    (() => {
      localStorage.removeItem("ceyizhome_print_queue_detail_collapsed");
      printQueueDetailCollapsed = null;
      ensurePrintQueueDetailPanelState();
      return true;
    })()
    """)
    wait(500)
    outcome["checks"]["collapsed_1366"] = inspect_detail_state(window)
    outcome["screenshots"]["collapsed_1366"] = save_screenshot(window, "queue-detail-collapsed-1366.png")

    run_js(window, """
    (() => {
      togglePrintQueueDetailPanel(true);
      selectPrintQueueItem("rowdesign-manual");
      return true;
    })()
    """)
    wait(500)
    outcome["checks"]["open_1366"] = inspect_detail_state(window)
    outcome["screenshots"]["open_1366"] = save_screenshot(window, "queue-detail-open-1366.png")

    run_js(window, """(() => { selectPrintQueueItem("rowdesign-legacy"); return true; })()""")
    wait(300)
    outcome["checks"]["selection_change"] = inspect_detail_state(window)

    open_1920 = outcome["checks"]["open_1920"]
    collapsed_1920 = outcome["checks"]["collapsed_1920"]
    collapsed_1366 = outcome["checks"]["collapsed_1366"]
    open_1366 = outcome["checks"]["open_1366"]
    selection_change = outcome["checks"]["selection_change"]

    if open_1920["activePage"] != "printQueue":
        raise AssertionError("Yazdirma Sirasi aktif degil")
    if "detail-collapsed" in open_1920["layoutClass"] or open_1920["panelWidth"] < 280:
        raise AssertionError(f"1920 acik panel beklenen genislikte degil: {json.dumps(open_1920, ensure_ascii=False)}")
    if open_1920["railHidden"] is not True:
        raise AssertionError("Acik panelde dikey detay sekmesi gizli olmali")
    if "detail-collapsed" not in collapsed_1920["layoutClass"] or collapsed_1920["panelWidth"] > 80:
        raise AssertionError(f"1920 kapali panel compact degil: {json.dumps(collapsed_1920, ensure_ascii=False)}")
    if collapsed_1920["rowWidth"] <= open_1920["rowWidth"]:
        raise AssertionError(f"Panel kapaninca liste genislemiyor: acik={open_1920['rowWidth']} kapali={collapsed_1920['rowWidth']}")
    if collapsed_1920["railHidden"] is not False or "detay" not in collapsed_1920["railText"].lower():
        raise AssertionError("Kapali panelde Detay sekmesi erisilebilir degil")
    if "detail-collapsed" not in collapsed_1366["layoutClass"] or collapsed_1366["panelWidth"] > 80:
        raise AssertionError(f"1366 varsayilan compact/collapsed baslamadi: {json.dumps(collapsed_1366, ensure_ascii=False)}")
    if "detail-collapsed" in open_1366["layoutClass"] or open_1366["panelWidth"] < 250:
        raise AssertionError(f"1366 acik panel detaylari okunur degil: {json.dumps(open_1366, ensure_ascii=False)}")
    if "Manuel Etiket" not in open_1366["detailText"]:
        raise AssertionError("Panel acildiginda secili Manuel Etiket detayi gorunmuyor")
    if "Eski" not in selection_change["detailText"]:
        raise AssertionError("Secili is degisince sag panel yeni detayi gostermiyor")
    if "Yazıcı otomatik" not in open_1366["detailStatus"]:
        raise AssertionError("Yazdirma guvenlik notu sag panelde korunmadi")

    outcome["status"] = "PASSED"
    return outcome


def main() -> int:
    suppress_message_boxes()
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    outcome: dict[str, object] = {"status": "ERROR", "message": "not started"}
    started = {"value": False}

    def start() -> None:
        nonlocal outcome
        if started["value"]:
            return
        started["value"] = True
        try:
            outcome = run_gate_phase6(window)
        except Exception as exc:  # noqa: BLE001
            outcome = {**outcome, "status": "ERROR", "message": str(exc)}
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(outcome, ensure_ascii=True, indent=2))
        window.close()
        window.deleteLater()
        QTimer.singleShot(0, app.quit)

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(5200, start))
    QTimer.singleShot(9000, lambda: start() if outcome.get("message") == "not started" else None)
    window.show()
    QTimer.singleShot(90000, app.quit)
    code = app.exec()
    return 0 if code == 0 and outcome.get("status") == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
