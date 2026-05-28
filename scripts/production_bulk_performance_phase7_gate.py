from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_bulk_performance_phase7"
RESULT_PATH = OUTPUT_DIR / "production_bulk_performance_phase7_gate_result.json"

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


def seed_500_items(window: WebMainWindow, width: int, height: int, reset_summary_touch: bool = False) -> dict[str, object]:
    window.resize(width, height)
    wait(800)
    reset_js = "bulkProductionSummaryCollapseTouched = false;" if reset_summary_touch else ""
    return run_js(window, f"""
    (() => {{
      showSection("bulkLabel");
      {reset_js}
      currentState.readiness = "OK";
      currentState.bulkProductionSource = "excel";
      bulkGalleryFilter = "all";
      bulkGallerySearch = "";
      bulkProductionViewMode = "gallery";
      bulkGalleryVisibleLimit = 50;
      bulkGalleryItems = Array.from({{ length: 500 }}, (_, index) => {{
        const n = index + 1;
        const isError = n % 25 === 0;
        const isWarning = !isError && n % 7 === 0;
        const hasLaser = n % 5 === 0;
        const longName = n % 11 === 0;
        const status = isError ? "ERROR" : isWarning ? "WARNING" : "READY";
        return {{
          item_id: `phase7-${{n}}`,
          row_number: n,
          source_type: n % 9 === 0 ? "trendyol" : n % 13 === 0 ? "manual" : "excel",
          source_label: n % 9 === 0 ? "Trendyol" : n % 13 === 0 ? "Manuel" : "Excel",
          label_text: longName ? `Mustafa Kemal & Yağmur Uzun İsim ${{n}}` : `Müşteri ${{String(n).padStart(3, "0")}} & Test`,
          date_text: n % 6 === 0 ? "" : `${{String((n % 27) + 1).padStart(2, "0")}}.06.2026`,
          note_text: n % 4 === 0 ? "Nişan Hatırası" : "Söz Hatırası",
          quantity: (n % 4) + 1,
          model_name: isError ? "" : n % 3 === 0 ? "02 Gold Cyzella AI Kabul Test Modeli" : "01 A Gold Rulo Etiket",
          model_key: isError ? "" : n % 3 === 0 ? "02" : "01",
          model_status: isError ? "MISSING" : "FOUND",
          size_text: n % 3 === 0 ? "40 x 40 mm" : "50 x 30 mm",
          laser_name: hasLaser ? `Müşteri ${{String(n).padStart(3, "0")}} & Test` : "",
          status,
          layout_quality_score: isError ? 35 : isWarning ? 67 : hasLaser ? 88 : 94,
          warnings: isWarning ? [n % 14 === 0 ? "Yazı taşıyor olabilir." : "Yazısı küçük görünebilir."] : [],
          errors: isError ? ["Model bulunamadı."] : [],
        }};
      }});
      selectedBulkGalleryItemId = "phase7-1";
      setBulkProductionStep(4);
      ensureBulkProductionSummaryPanelState();
      renderBulkGallery();
      const grid = document.getElementById("bulkGalleryGrid");
      const text = document.getElementById("bulkLabel")?.innerText || "";
      return {{
        activePage: document.querySelector(".page.active")?.id || "",
        activeStep: document.querySelector("#bulkLabel .bulk-wizard-step.active")?.innerText || "",
        stateCount: bulkGalleryItems.length,
        filteredCount: bulkGalleryFilteredItems().length,
        cardCount: grid?.querySelectorAll(".bulk-gallery-item").length || 0,
        loadStateText: grid?.querySelector(".bulk-gallery-load-state")?.innerText || "",
        loadMoreVisible: Boolean([...grid.querySelectorAll("button")].find(button => /Daha fazla göster/.test(button.textContent || ""))),
        summaryCollapsed: document.getElementById("bulkLabel")?.classList.contains("bulk-summary-collapsed") || false,
        summaryTabVisible: !document.getElementById("bulkSummaryCollapsedTab")?.hidden,
        hasAutoPrintText: /yazıcı otomatik başladı|direct print başlatıldı|rdworks açıldı|lazer başladı/i.test(text),
        hasPreviewButton: /Gerçek Mini Önizleme Oluştur|Tümünü Önizle/.test(text)
      }};
    }})()
    """, timeout_ms=60000)


def load_more(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      showMoreBulkGalleryItems();
      const grid = document.getElementById("bulkGalleryGrid");
      return {
        cardCount: grid?.querySelectorAll(".bulk-gallery-item").length || 0,
        loadStateText: grid?.querySelector(".bulk-gallery-load-state")?.innerText || "",
        loadMoreVisible: Boolean([...grid.querySelectorAll("button")].find(button => /Daha fazla göster/.test(button.textContent || "")))
      };
    })()
    """)


def filter_ready(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      setBulkGalleryFilter("ready");
      const grid = document.getElementById("bulkGalleryGrid");
      const cards = [...grid.querySelectorAll(".bulk-gallery-item")];
      return {
        filteredCount: bulkGalleryFilteredItems().length,
        cardCount: cards.length,
        hasErrorCard: cards.some(card => card.classList.contains("has-error")),
        loadStateText: grid?.querySelector(".bulk-gallery-load-state")?.innerText || "",
      };
    })()
    """)


def search_items(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      setBulkGallerySearch("Müşteri 012");
      const grid = document.getElementById("bulkGalleryGrid");
      const text = grid?.innerText || "";
      return {
        filteredCount: bulkGalleryFilteredItems().length,
        cardCount: grid?.querySelectorAll(".bulk-gallery-item").length || 0,
        includesTarget: text.includes("Müşteri 012"),
        loadStateText: grid?.querySelector(".bulk-gallery-load-state")?.innerText || "",
      };
    })()
    """)


def collapse_summary(window: WebMainWindow, collapsed: bool) -> dict[str, object]:
    return run_js(window, f"""
    (() => {{
      toggleBulkProductionSummary({str(collapsed).lower()});
      const page = document.getElementById("bulkLabel");
      return {{
        collapsed: page?.classList.contains("bulk-summary-collapsed") || false,
        tabVisible: !document.getElementById("bulkSummaryCollapsedTab")?.hidden,
        shellColumns: getComputedStyle(document.querySelector("#bulkLabel .bulk-production-shell")).gridTemplateColumns,
      }};
    }})()
    """)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, sys.executable)
    window.show()
    wait(1600)

    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}
    try:
        outcome["checks"]["bulk_500_1920"] = seed_500_items(window, 1920, 1080)
        outcome["screenshots"]["bulk_500_1920"] = save_screenshot(window, "bulk-performance-500-1920.png")

        outcome["checks"]["load_more"] = load_more(window)
        outcome["screenshots"]["load_more"] = save_screenshot(window, "bulk-performance-load-more.png")

        outcome["checks"]["filter_ready"] = filter_ready(window)
        outcome["screenshots"]["filter_ready"] = save_screenshot(window, "bulk-performance-filter-ready.png")

        outcome["checks"]["search"] = search_items(window)

        outcome["checks"]["summary_collapsed_1920"] = collapse_summary(window, True)
        outcome["checks"]["summary_open_1920"] = collapse_summary(window, False)

        outcome["checks"]["bulk_500_1366"] = seed_500_items(window, 1366, 768, reset_summary_touch=True)
        outcome["screenshots"]["bulk_500_1366"] = save_screenshot(window, "bulk-performance-500-1366.png")
        outcome["checks"]["summary_collapsed_1366"] = collapse_summary(window, True)
        outcome["screenshots"]["summary_collapsed_1366"] = save_screenshot(window, "bulk-performance-summary-collapsed-1366.png")

        failures: list[str] = []
        first = outcome["checks"]["bulk_500_1920"]
        if first["stateCount"] != 500:
            failures.append("500 item state oluşmadı")
        if first["cardCount"] > 60:
            failures.append(f"İlk render çok fazla kart bastı: {first['cardCount']}")
        if not first["loadMoreVisible"]:
            failures.append("Daha fazla göster butonu görünmüyor")
        if first["hasAutoPrintText"]:
            failures.append("Otomatik yazıcı/lazer dili göründü")
        if not first["hasPreviewButton"]:
            failures.append("Önizleme manuel tetik bilgisi görünmüyor")
        if outcome["checks"]["load_more"]["cardCount"] <= first["cardCount"]:
            failures.append("Daha fazla göster kart sayısını artırmadı")
        ready = outcome["checks"]["filter_ready"]
        if ready["cardCount"] > 60 or ready["hasErrorCard"]:
            failures.append("Hazır filtresi limitli/temiz çalışmadı")
        search = outcome["checks"]["search"]
        if not search["includesTarget"] or search["cardCount"] > 60:
            failures.append("Arama hedefi bulmadı veya limitli render bozuldu")
        if not outcome["checks"]["summary_collapsed_1920"]["collapsed"]:
            failures.append("Özet paneli 1920'de kapanmadı")
        if not outcome["checks"]["bulk_500_1366"]["summaryCollapsed"]:
            failures.append("1366 görünümde özet paneli varsayılan collapsed başlamadı")
        if not outcome["checks"]["summary_collapsed_1366"]["tabVisible"]:
            failures.append("Collapsed özet sekmesi görünmüyor")

        if failures:
            outcome["status"] = "FAILED"
            outcome["failures"] = failures
            RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(outcome, ensure_ascii=False, indent=2))
            return 1

        outcome["status"] = "PASSED"
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0
    finally:
        window.close()
        app.quit()


if __name__ == "__main__":
    raise SystemExit(main())
