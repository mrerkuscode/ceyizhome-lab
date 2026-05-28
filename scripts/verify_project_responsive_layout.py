from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from verify_corel_editor_interactions import run_js, wait  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "responsive_layout"
RESULT_PATH = OUTPUT_DIR / "RESPONSIVE_LAYOUT_AUDIT.json"


VIEWPORTS = [
    ("1920", 1920, 1080),
    ("1600", 1600, 900),
    ("1366", 1366, 768),
    ("1280", 1280, 800),
]

PAGES = [
    ("fontTestLab", "Font Test Lab"),
    ("designLab", "CeyizHome Lab Design Lab"),
    ("trendyolOrders", "Trendyol Siparişleri"),
    ("bulkLabel", "Toplu Üretim Studio"),
    ("label", "Etiket Studio"),
    ("labelModels", "Etiket Modelleri"),
    ("printQueue", "Yazdırma Sırası"),
    ("nameCutStudio", "İsim Kesim"),
    ("settings", "Ayarlar"),
]


def flush_ui(ms: int = 260) -> None:
    QApplication.processEvents()
    wait(ms)
    QApplication.processEvents()


def save_screenshot(window: WebMainWindow, name: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    flush_ui()
    saved = window.view.grab().save(str(path))
    if not saved or not path.exists() or path.stat().st_size <= 0:
        raise AssertionError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def audit_page(window: WebMainWindow, page_id: str) -> dict:
    return run_js(
        window,
        f"""
        (() => {{
          window.__responsiveAlerts = [];
          window.alert = message => window.__responsiveAlerts.push(String(message || ''));
          showSection({json.dumps(page_id)});
          if ({json.dumps(page_id)} === 'bulkLabel') setBulkProductionStep?.(1);
          const main = document.querySelector('.main');
          const page = document.querySelector('.page.active');
          const sidebar = document.querySelector('.sidebar');
          const rect = el => {{
            const r = el?.getBoundingClientRect?.();
            return {{
              left: Math.round(r?.left || 0),
              right: Math.round(r?.right || 0),
              top: Math.round(r?.top || 0),
              bottom: Math.round(r?.bottom || 0),
              width: Math.round(r?.width || 0),
              height: Math.round(r?.height || 0)
            }};
          }};
          const visible = el => {{
            const r = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            return r.width > 2 && r.height > 2 && style.visibility !== 'hidden' && style.display !== 'none';
          }};
          const offenders = [...document.body.querySelectorAll('*')]
            .filter(visible)
            .filter(el => {{
              if (el.closest('.trendyol-evidence-drawer')) return false;
              if (el.closest('.modal-backdrop')) return false;
              const r = el.getBoundingClientRect();
              return r.right > window.innerWidth + 6 || r.left < -6;
            }})
            .slice(0, 12)
            .map(el => {{
              const r = el.getBoundingClientRect();
              return {{
                tag: el.tagName.toLowerCase(),
                id: el.id || '',
                cls: String(el.className || '').slice(0, 120),
                left: Math.round(r.left),
                right: Math.round(r.right),
                width: Math.round(r.width),
                text: String(el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 80)
              }};
            }});
          return {{
            page: {json.dumps(page_id)},
            activePage: page?.id || '',
            viewport: {{ width: window.innerWidth, height: window.innerHeight }},
            documentScrollWidth: document.documentElement.scrollWidth,
            bodyScrollWidth: document.body.scrollWidth,
            mainClientWidth: main?.clientWidth || 0,
            mainScrollWidth: main?.scrollWidth || 0,
            pageRect: rect(page),
            mainRect: rect(main),
            sidebarRect: rect(sidebar),
            appGrid: getComputedStyle(document.querySelector('.app-shell')).gridTemplateColumns,
            bodyClasses: document.body.className,
            globalOverflowPx: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
            mainOverflowPx: (main?.scrollWidth || 0) - (main?.clientWidth || 0),
            activePageOverflowPx: page ? Math.round(page.getBoundingClientRect().right - window.innerWidth) : 0,
            visibleOffenders: offenders,
            consoleErrors: window.__responsiveAlerts || []
          }};
        }})()
        """,
    )


def main() -> int:
    app = QApplication.instance() or QApplication([])
    python_exe = Path(sys.executable)
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    results: list[dict] = []
    screenshots: dict[str, str] = {}
    failures: list[dict] = []

    for label, width, height in VIEWPORTS:
      window.resize(width, height)
      window.show()
      flush_ui(520)
      for page_id, _title in PAGES:
        state = audit_page(window, page_id)
        flush_ui(240)
        results.append({"viewport": label, **state})
        allowed_main_overflow = 40 if page_id == "label" else 8
        if state["activePage"] != page_id:
          failures.append({"viewport": label, "page": page_id, "reason": "active_page_mismatch", "state": state})
        if state["globalOverflowPx"] > 8:
          failures.append({"viewport": label, "page": page_id, "reason": "global_horizontal_overflow", "state": state})
        if state["mainOverflowPx"] > allowed_main_overflow and page_id not in {"printQueue"}:
          failures.append({"viewport": label, "page": page_id, "reason": "main_horizontal_overflow", "state": state})
        if state["visibleOffenders"]:
          failures.append({"viewport": label, "page": page_id, "reason": "visible_element_outside_viewport", "state": state})
        if label in {"1920", "1366"} and page_id in {"fontTestLab", "designLab", "trendyolOrders", "bulkLabel", "label", "labelModels", "printQueue", "nameCutStudio", "settings"}:
          screenshots[f"{page_id}_{label}"] = save_screenshot(window, f"{page_id}_{label}.png")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
      "status": "PASSED" if not failures else "FAILED",
      "viewports": VIEWPORTS,
      "pages": PAGES,
      "results": results,
      "failures": failures,
      "screenshots": screenshots,
    }
    RESULT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
      "status": report["status"],
      "failure_count": len(failures),
      "json_report": str(RESULT_PATH),
      "screenshots": screenshots,
    }, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
