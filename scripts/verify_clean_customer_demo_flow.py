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
from seed_clean_customer_demo_data import seed_clean_customer_demo_data  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "clean_customer_demo_flow"
RESULT_PATH = OUTPUT_DIR / "VERIFY_CLEAN_CUSTOMER_DEMO_FLOW_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


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
    window.view.grab().save(str(path))
    return str(path)


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def outputs_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => ({
      activePage: document.querySelector('.page.active')?.id || '',
      customerCardCount: document.querySelectorAll('#labelOutputList .output-card:not(.technical-output-item)').length,
      technicalCardCount: document.querySelectorAll('#labelOutputList .technical-output-item').length,
      summaryText: document.getElementById('labelOutputSummary')?.innerText || '',
      listText: document.getElementById('labelOutputList')?.innerText || '',
      previewText: document.getElementById('labelOutputPreview')?.innerText || '',
      infoText: document.getElementById('selectedOutputInfo')?.innerText || '',
      actionText: document.getElementById('selectedOutputActions')?.innerText || '',
      selectedCard: Boolean(document.querySelector('#labelOutputList .output-card.selected')),
      hasBrokenImage: [...document.querySelectorAll('#labelOutputs img')].some(img => img.complete && img.naturalWidth === 0),
      hasTechnicalInCustomer: [...document.querySelectorAll('#labelOutputList .output-card:not(.technical-output-item)')]
        .some(card => /report|debug|manifest|quality gate|test\\/qa/i.test(card.innerText || '')),
      safePrintOpen: !document.getElementById('safePrintModal')?.hidden,
    }))()
    """)


def queue_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => ({
      activePage: document.querySelector('.page.active')?.id || '',
      renderedRows: document.querySelectorAll('#printQueueList .queue-job-card').length,
      queueTotalJobs: document.getElementById('queueTotalJobs')?.textContent || '',
      queueReview: document.getElementById('queueReview')?.textContent || '',
      bodyText: document.getElementById('printQueue')?.innerText || '',
      detailText: document.getElementById('queueDetailInfo')?.innerText || '',
      actionText: document.getElementById('queueDetailActions')?.innerText || '',
      selectedRows: document.querySelectorAll('#printQueueList .queue-job-card.selected').length,
      safePrintOpen: !document.getElementById('safePrintModal')?.hidden,
      hasBrokenImage: [...document.querySelectorAll('#printQueue img')].some(img => img.complete && img.naturalWidth === 0),
      hasDirectPrintCall: /window\\.print\\(|\\.print\\(/.test(document.documentElement.innerHTML || ''),
    }))()
    """)


def run_gate(window: WebMainWindow) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    run_js(window, """
    (() => {
      showSection('labelOutputs');
      clearLabelOutputFilters();
      updateLabelOutputs(currentState.labelOutputs || []);
      return { ok: true };
    })()
    """, timeout_ms=120000)
    wait(1500)
    first_outputs = outputs_state(window)
    assert_true(first_outputs["activePage"] == "labelOutputs", "Etiket Çıktıları sayfası açılmadı", first_outputs)
    assert_true(int(first_outputs["customerCardCount"]) >= 3, "Varsayılan müşteri galerisi temiz demo çıktılarını göstermiyor", first_outputs)
    assert_true("Elif Kaan" in str(first_outputs["listText"]) or "Burcu Baran" in str(first_outputs["listText"]), "Müşteri isimleri çıktı kartlarında görünmüyor", first_outputs)
    assert_true("Kontrol gereken çıktı" not in str(first_outputs["summaryText"]), "Varsayılan çıktı özeti kontrol gereken akışına düşmüş", first_outputs)
    assert_true(not first_outputs["hasTechnicalInCustomer"], "Teknik/test çıktı müşteri galerisine karıştı", first_outputs)
    assert_true(not first_outputs["hasBrokenImage"], "Etiket Çıktıları kırık görsel içeriyor", first_outputs)
    screenshots["outputs_customer_gallery"] = save_screenshot(window, "outputs_customer_gallery.png")
    checks.append({"name": "outputs_default_customer_gallery", "status": "PASSED", "state": first_outputs})

    run_js(window, """
    (() => {
      const card = document.querySelector('#labelOutputList .output-card:not(.technical-output-item)');
      card?.click();
      return { ok: Boolean(card), text: card?.innerText || '' };
    })()
    """)
    wait(900)
    selected_output = outputs_state(window)
    assert_true(selected_output["selectedCard"], "Çıktı kartı seçili hale gelmedi", selected_output)
    assert_true("Listeden bir çıktı seçin" not in str(selected_output["previewText"]), "Sağ çıktı preview paneli güncellenmedi", selected_output)
    action_text = str(selected_output["actionText"])
    assert_true("Studio" in action_text and ("Sıraya" in action_text or "Sırasına" in action_text), "Sağ çıktı panel aksiyonları eksik", selected_output)
    screenshots["outputs_selected_customer"] = save_screenshot(window, "outputs_selected_customer.png")
    checks.append({"name": "outputs_selected_customer_detail", "status": "PASSED", "state": selected_output})

    run_js(window, """
    (() => {
      showSection('printQueue');
      clearPrintQueueFilters();
      updatePrintQueue(currentState.printQueue || []);
      return { ok: true };
    })()
    """)
    wait(1500)
    first_queue = queue_state(window)
    assert_true(first_queue["activePage"] == "printQueue", "Yazdırma Sırası sayfası açılmadı", first_queue)
    assert_true(int(first_queue["renderedRows"]) >= 3, "Varsayılan yazdırma sırası temiz müşteri işlerini göstermiyor", first_queue)
    assert_true("Elif Kaan" in str(first_queue["bodyText"]) and "Sedef Sefer" in str(first_queue["bodyText"]), "Queue müşteri isimleri/metadatası eksik", first_queue)
    assert_true("Stale Kontrol" not in str(first_queue["bodyText"]), "Stale/test işleri varsayılan müşteri kuyruğuna karıştı", first_queue)
    assert_true("Sipariş Test" not in str(first_queue["bodyText"]), "Sipariş test işleri varsayılan müşteri kuyruğuna karıştı", first_queue)
    assert_true("Yazdırmaya hazır müşteri işi yok" not in str(first_queue["bodyText"]), "Queue hâlâ boş/uyarı state'inde", first_queue)
    assert_true(str(first_queue["queueReview"]).strip() == "0", "Test/QA işleri müşteri kuyruğunda kontrol gereken sayısını şişiriyor", first_queue)
    assert_true(not first_queue["hasDirectPrintCall"], "Direct/silent print çağrısı DOM içinde görünüyor", first_queue)
    assert_true(not first_queue["hasBrokenImage"], "Yazdırma Sırası kırık görsel içeriyor", first_queue)
    screenshots["queue_customer_ready"] = save_screenshot(window, "queue_customer_ready.png")
    checks.append({"name": "queue_default_customer_jobs", "status": "PASSED", "state": first_queue})

    run_js(window, """
    (() => {
      const row = document.querySelector('#printQueueList .queue-job-card');
      row?.click();
      return { ok: Boolean(row), text: row?.innerText || '' };
    })()
    """)
    wait(800)
    selected_queue = queue_state(window)
    assert_true(int(selected_queue["selectedRows"]) >= 1, "Queue seçili iş vurgusu oluşmadı", selected_queue)
    assert_true("Model" in str(selected_queue["detailText"]) and "Adet" in str(selected_queue["detailText"]), "Queue sağ detay paneli metadata göstermiyor", selected_queue)
    screenshots["queue_selected_customer"] = save_screenshot(window, "queue_selected_customer.png")
    checks.append({"name": "queue_selected_customer_detail", "status": "PASSED", "state": selected_queue})

    run_js(window, """
    (() => {
      const btn = [...document.querySelectorAll('#printQueueList .queue-actions button')]
        .find(button => (button.textContent || '').includes('Yazdır'));
      btn?.click();
      return { ok: Boolean(btn) };
    })()
    """)
    wait(1000)
    print_state = queue_state(window)
    assert_true(print_state["safePrintOpen"], "Queue Yazdır butonu güvenli onay modalı açmadı", print_state)
    screenshots["queue_customer_print_modal"] = save_screenshot(window, "queue_customer_print_modal.png")
    checks.append({"name": "queue_safe_print_modal", "status": "PASSED", "state": print_state})

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    seed_result = seed_clean_customer_demo_data(PROJECT_ROOT)
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1680, 980)
    window.show()
    wait(6500)
    try:
        result = run_gate(window)
        result["seed_result"] = seed_result
    finally:
        window.close()
        app.quit()
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
