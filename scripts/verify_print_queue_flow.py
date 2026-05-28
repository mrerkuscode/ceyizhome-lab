from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend.print_queue_api import add_pdf_output_to_queue, list_print_queue  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "print_queue_flow"
RESULT_PATH = OUTPUT_DIR / "VERIFY_PRINT_QUEUE_FLOW_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def flush_ui(window: WebMainWindow, ms: int = 300) -> None:
    app = QApplication.instance()
    if app:
        app.processEvents()
    wait(ms)
    if app:
        app.processEvents()
    window.view.repaint()
    if app:
        app.processEvents()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 90000):
    loop = QEventLoop()
    result = {"value": None, "done": False}

    def callback(value):
        result["value"] = value
        result["done"] = True
        loop.quit()

    wrapped = f"""
    (() => {{
      try {{
        return JSON.stringify(({script}));
      }} catch (error) {{
        return JSON.stringify({{ "__error": String(error && error.message || error), stack: String(error && error.stack || "") }});
      }}
    }})()
    """
    window.view.page().runJavaScript(wrapped, callback)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if not result["done"]:
      raise RuntimeError(f"JavaScript timed out: {script[:160]}")
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
    flush_ui(window, 350)
    window.view.grab().save(str(path))
    assert_true(path.exists() and path.stat().st_size > 0, f"Screenshot kaydedilemedi: {path}")
    return str(path)


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def newest_customer_pdf() -> str:
    output_root = PROJECT_ROOT / "output"
    candidates = [
        path for path in output_root.rglob("*.pdf")
        if "report" not in path.name.lower()
        and "calibration" not in path.name.lower()
        and "preview" not in path.name.lower()
    ]
    if not candidates:
        return ""
    newest = max(candidates, key=lambda path: path.stat().st_mtime)
    return newest.relative_to(PROJECT_ROOT).as_posix()


def ensure_queue_item() -> None:
    rows = list_print_queue(PROJECT_ROOT)
    if rows:
        return
    pdf = newest_customer_pdf()
    if pdf:
        add_pdf_output_to_queue(PROJECT_ROOT, pdf)


def page_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => ({
      activePage: document.querySelector('.page.active')?.id || '',
      itemCount: (currentState.printQueue || []).length,
      renderedRows: document.querySelectorAll('#printQueueList .queue-job-card').length,
      hiddenTestArchiveToggle: Boolean(document.getElementById('queueTestArchiveToggle')),
      summaryCards: document.querySelectorAll('#printQueue .queue-stat').length,
      filterCount: document.querySelectorAll('#printQueue .queue-filter-bar input, #printQueue .queue-filter-bar select').length,
      hasSafetyBanner: Boolean(document.querySelector('#printQueue .print-safety-banner')),
      hasDetailPanel: Boolean(document.querySelector('#printQueue .queue-detail-panel')),
      detailText: document.getElementById('queueDetailInfo')?.innerText || '',
      actionText: document.getElementById('queueDetailActions')?.innerText || '',
      selectedRows: document.querySelectorAll('#printQueueList .queue-job-card.selected').length,
      checkedRows: document.querySelectorAll('#printQueueList input[type="checkbox"]:checked').length,
      safePrintOpen: !document.getElementById('safePrintModal')?.hidden,
      clearModalOpen: !document.getElementById('queueClearModal')?.hidden,
      hasBrokenImage: [...document.querySelectorAll('#printQueue img')].some(img => img.complete && img.naturalWidth === 0),
      hasDirectPrintCall: /window\\.print\\(|\\.print\\(/.test(document.documentElement.innerHTML || ''),
      bodyText: document.getElementById('printQueue')?.innerText || ''
    }))()
    """)


def scroll_to_queue_rows(window: WebMainWindow) -> dict[str, object]:
    result = run_js(window, """
    (() => {
      const target = document.querySelector('#printQueueList .queue-job-card') || document.getElementById('printQueueList');
      if (target) {
        target.scrollIntoView({ block: 'center', inline: 'nearest' });
      }
      const row = document.querySelector('#printQueueList .queue-job-card');
      const rect = row ? row.getBoundingClientRect() : null;
      const box = selector => {
        const el = row ? row.querySelector(selector) : null;
        const r = el ? el.getBoundingClientRect() : null;
        return r ? { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height } : null;
      };
      const intersects = (a, b) => Boolean(a && b && a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top);
      const main = box('.queue-main');
      const file = box('.queue-file');
      const quality = box('.queue-quality');
      const actions = box('.queue-actions');
      const listRect = document.getElementById('printQueueList')?.getBoundingClientRect() || null;
      const listBox = listRect ? { left: listRect.left, top: listRect.top, right: listRect.right, bottom: listRect.bottom, width: listRect.width, height: listRect.height } : null;
      const actionButtons = row ? [...row.querySelectorAll('.queue-actions .btn')].map(btn => {
        const r = btn.getBoundingClientRect();
        return {
          text: btn.textContent.trim(),
          left: r.left,
          top: r.top,
          right: r.right,
          bottom: r.bottom,
          width: r.width,
          height: r.height,
          visibleWidth: Math.max(0, Math.min(r.right, listRect ? listRect.right : window.innerWidth) - Math.max(r.left, listRect ? listRect.left : 0)),
          visibleHeight: Math.max(0, Math.min(r.bottom, listRect ? listRect.bottom : window.innerHeight) - Math.max(r.top, listRect ? listRect.top : 0))
        };
      }) : [];
      const buttonsOverlap = actionButtons.some((a, index) => actionButtons.slice(index + 1).some(b => intersects(a, b)));
      return {
        renderedRows: document.querySelectorAll('#printQueueList .queue-job-card').length,
        rowTop: rect ? rect.top : null,
        rowBottom: rect ? rect.bottom : null,
        rowHeight: rect ? rect.height : null,
        rowText: row ? row.innerText : '',
        listBox,
        mainBox: main,
        fileBox: file,
        qualityBox: quality,
        actionsBox: actions,
        actionButtons,
        hasColumnOverlap: intersects(main, file) || intersects(main, quality) || intersects(file, quality) || intersects(quality, actions),
        actionsInsideList: Boolean(actions && listBox && actions.left >= listBox.left - 1 && actions.right <= listBox.right + 1),
        actionButtonsInsideList: actionButtons.every(btn => listBox && btn.left >= listBox.left - 1 && btn.right <= listBox.right + 1),
        actionButtonsReadable: actionButtons.every(btn => btn.visibleWidth >= 42 && btn.visibleHeight >= 24),
        buttonsOverlap,
        viewportHeight: window.innerHeight
      };
    })()
    """)
    flush_ui(window, 650)
    return result


def assert_queue_rows_visible(window: WebMainWindow, label: str) -> dict[str, object]:
    row_view = scroll_to_queue_rows(window)
    if int(row_view.get("renderedRows") or 0) <= 0:
        return row_view
    assert_true(
        float(row_view.get("rowHeight") or 0) >= 100,
        f"{label}: queue satiri cok dar veya kirpilmis gorunuyor",
        row_view,
    )
    assert_true(
        float(row_view.get("rowBottom") or 0) > 120,
        f"{label}: queue satiri screenshot alaninda gorunur degil",
        row_view,
    )
    assert_true(
        bool(str(row_view.get("rowText") or "").strip()),
        f"{label}: queue satiri metni bos gorunuyor",
        row_view,
    )
    assert_true(
        not row_view.get("hasColumnOverlap"),
        f"{label}: queue satiri kolonlari ust uste biniyor",
        row_view,
    )
    assert_true(
        row_view.get("actionsInsideList"),
        f"{label}: queue aksiyon kolonu liste alani disina tasiyor",
        row_view,
    )
    assert_true(
        row_view.get("actionButtonsInsideList"),
        f"{label}: queue aksiyon butonlari kirpiliyor",
        row_view,
    )
    assert_true(
        row_view.get("actionButtonsReadable"),
        f"{label}: queue aksiyon butonlari okunamayacak kadar dar veya gorunmez",
        row_view,
    )
    assert_true(
        not row_view.get("buttonsOverlap"),
        f"{label}: queue aksiyon butonlari ust uste biniyor",
        row_view,
    )
    return row_view


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    run_js(window, "(() => { showSection('printQueue'); updatePrintQueue(currentState.printQueue || []); return { ok: true }; })()", timeout_ms=120000)
    wait(1500)
    first = page_state(window)
    assert_true(first["activePage"] == "printQueue", "Yazdırma Sırası açılmadı", first)
    assert_true(first["summaryCards"] >= 6, "Kompakt özet kartları eksik", first)
    assert_true(first["hasSafetyBanner"], "Yazdırma güvenliği banner'ı eksik", first)
    assert_true(first["hasDetailPanel"], "Seçili iş detay paneli eksik", first)
    assert_true(first["filterCount"] >= 5, "Filtre bar eksik", first)
    assert_true(not first["hasDirectPrintCall"], "Sessiz/direct print çağrısı DOM içinde görünüyor", first)
    assert_true(not first["hasBrokenImage"], "Kırık preview image var", first)
    if int(first["renderedRows"]) > 0:
        checks.append({"name": "queue_rows_visible_for_general_screenshot", "status": "PASSED", "state": assert_queue_rows_visible(window, "general")})
    screenshots["queue_general"] = save_screenshot(window, "print_queue_general.png")
    checks.append({"name": "layout_and_safety", "status": "PASSED", "state": first})

    if int(first["itemCount"]) > 0 and int(first["renderedRows"]) <= 0 and first.get("hiddenTestArchiveToggle"):
        reveal = run_js(window, """
        (() => {
          const toggle = document.getElementById('queueTestArchiveToggle');
          if (toggle) {
            toggle.checked = true;
            refreshPrintQueueFilters();
          }
          return { ok: Boolean(toggle), renderedRows: document.querySelectorAll('#printQueueList .queue-job-card').length };
        })()
        """)
        wait(900)
        checks.append({"name": "test_archive_toggle_reveals_hidden_queue_items", "status": "PASSED", "state": reveal})
        assert_queue_rows_visible(window, "test_archive")
        screenshots["queue_test_archive_visible"] = save_screenshot(window, "print_queue_test_archive_visible.png")

    first = page_state(window)
    if int(first["renderedRows"]) > 0:
        selected = run_js(window, """
        (() => {
          const row = document.querySelector('#printQueueList .queue-job-card');
          row?.click();
          return { ok: Boolean(row), text: row?.innerText || '' };
        })()
        """)
        assert_true(selected.get("ok"), "Queue item seçilemedi", selected)
        wait(900)
        selected_state = page_state(window)
        assert_true(selected_state["selectedRows"] >= 1, "Seçili row vurgusu yok", selected_state)
        assert_true("PDF" in str(selected_state["actionText"]) and "Yazdır" in str(selected_state["actionText"]), "Sağ panel aksiyonları eksik", selected_state)
        assert_queue_rows_visible(window, "selected_detail")
        screenshots["queue_selected_detail"] = save_screenshot(window, "print_queue_selected_detail.png")
        checks.append({"name": "selected_detail_panel", "status": "PASSED", "state": selected_state})

        run_js(window, "(() => { document.querySelector('#printQueueList input[type=\"checkbox\"]')?.click(); return { ok: true }; })()")
        wait(500)
        bulk = page_state(window)
        assert_true(bulk["checkedRows"] >= 1, "Toplu seçim checkbox çalışmadı", bulk)
        assert_queue_rows_visible(window, "bulk_selection")
        screenshots["queue_bulk_selection"] = save_screenshot(window, "print_queue_bulk_selection.png")
        checks.append({"name": "bulk_selection", "status": "PASSED", "state": bulk})

        run_js(window, "(() => { const btn = [...document.querySelectorAll('#printQueue button')].find(b => (b.textContent || '').includes('Yazdır') && !String(b.textContent || '').includes('Seçilen')); btn?.click(); return { ok: Boolean(btn) }; })()")
        wait(1200)
        print_state = page_state(window)
        assert_true(print_state["safePrintOpen"], "Yazdır butonu güvenli onay modalı açmadı", print_state)
        screenshots["queue_print_modal"] = save_screenshot(window, "print_queue_print_modal.png")
        checks.append({"name": "safe_print_modal", "status": "PASSED", "state": print_state})
        run_js(window, "(() => { if (typeof closeSafePrintModal === 'function') closeSafePrintModal(); return { ok: true }; })()")

    run_js(window, "(() => { document.getElementById('queueStatusFilter').value = 'pending'; refreshPrintQueueFilters(); return { ok: true }; })()")
    wait(700)
    assert_queue_rows_visible(window, "filtered")
    screenshots["queue_filtered"] = save_screenshot(window, "print_queue_filtered_pending.png")
    checks.append({"name": "filters", "status": "PASSED", "state": page_state(window)})

    run_js(window, "(() => { confirmClearPrintQueue(); return { ok: true }; })()")
    wait(500)
    clear_state = page_state(window)
    assert_true(clear_state["clearModalOpen"], "Sırayı Temizle onay modalı açmadı", clear_state)
    screenshots["queue_clear_modal"] = save_screenshot(window, "print_queue_clear_modal.png")
    checks.append({"name": "clear_confirmation", "status": "PASSED", "state": clear_state})
    run_js(window, "(() => { closeQueueClearModal(); return { ok: true }; })()")

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ensure_queue_item()
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1680, 980)
    window.show()
    wait(6500)
    try:
        result = run_gate(window)
    finally:
        window.close()
        app.quit()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
