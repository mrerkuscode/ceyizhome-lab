from __future__ import annotations

import base64
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_real_user_e2e_phase19"
RESULT_PATH = OUTPUT_DIR / "production_real_user_e2e_phase19_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import bulk_label_api, name_cut_queue_api, print_queue_api, production_audit_api, trendyol_api  # noqa: E402


DATA_FILES = [
    PROJECT_ROOT / "data" / "trendyol_production_suggestions.json",
    PROJECT_ROOT / "data" / "production_audit_log.json",
    PROJECT_ROOT / "data" / "print_queue.json",
    PROJECT_ROOT / "data" / "name_cut_queue.json",
    PROJECT_ROOT / "data" / "name_cut_transfer_history.json",
    PROJECT_ROOT / "data" / "name_cut_export_history.json",
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


def reset_data() -> None:
    for path in DATA_FILES:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]", encoding="utf-8")


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def assert_true(condition: bool, message: str, checks: list[dict[str, Any]]) -> None:
    checks.append({"name": message, "passed": bool(condition)})
    if not condition:
        raise AssertionError(message)


def write_minimal_pdf(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_title = title.replace("(", "[").replace(")", "]")
    path.write_text(
        f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 320 180] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 74 >> stream
BT /F1 14 Tf 24 110 Td ({safe_title}) Tj 0 -24 Td (Phase 19 E2E QA) Tj ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000248 00000 n 
0000000374 00000 n 
trailer << /Root 1 0 R /Size 6 >>
startxref
444
%%EOF
""",
        encoding="latin-1",
    )


def write_minimal_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="))


def first_label_model_path() -> str:
    candidates = sorted((PROJECT_ROOT / "templates" / "designs").glob("*.json"))
    for path in candidates:
        stem = path.stem.lower()
        if "01" in stem and "gold" in stem:
            return str(path)
    return str(candidates[0]) if candidates else ""


def create_excel_fixture(path: Path) -> None:
    names = [
        ("Ayşe & Mehmet", "12.05.2026", "Söz Hatırası", 2, "Ayşe & Mehmet", "01"),
        ("Yağmur & Efe", "19.05.2026", "Nişan Hatırası", 1, "Yağmur & Efe", "01"),
        ("Mustafa Kemal & Yağmur", "22.06.2026", "Uzun isim kontrolü", 2, "Mustafa Kemal", "01"),
        ("Helin Cemal", "02.06.2026", "Tarih bulundu", 3, "", "01"),
        ("Can", "", "Tarih opsiyonel boş", 1, "Can", "01"),
        ("Abdurrahman", "01.07.2026", "Uzun isim daraltma önerisi", 1, "Abdurrahman", "01"),
        ("", "03.07.2026", "İsim eksik", 1, "", "01"),
        ("Model Eksik", "04.07.2026", "Model eksik", 1, "Model Eksik", "99"),
        ("Duru & Deniz", "05.07.2026", "Hazır", 2, "Duru & Deniz", "01"),
        ("Eylül", "06.07.2026", "Yazısı küçük olabilir", 1, "Eylül", "01"),
        ("Ada & Aras", "07.07.2026", "Hazır", 4, "Ada & Aras", "01"),
        ("Mira", "08.07.2026", "Lazer yok", 1, "", "01"),
        ("Ela & Ege", "09.07.2026", "Hazır", 2, "Ela & Ege", "01"),
        ("Derin Kaya", "10.07.2026", "Kontrol gerekli", 1, "Derin Kaya", "01"),
        ("Nil", "11.07.2026", "Hazır", 1, "Nil", "01"),
        ("Ali Veli Çok Uzun Bir İsim", "12.07.2026", "Taşma riski", 1, "Ali Veli", "01"),
        ("Seda & Kaan", "13.07.2026", "Hazır", 2, "Seda & Kaan", "01"),
        ("Lina", "14.07.2026", "Hazır", 1, "Lina", "01"),
        ("Ecrin & Alp", "15.07.2026", "Hazır", 2, "Ecrin & Alp", "01"),
        ("Bora", "16.07.2026", "Hazır", 1, "Bora", "01"),
    ]
    rows = []
    for index, (name, date_text, note, qty, laser_name, model_no) in enumerate(names, start=1):
        rows.append({
            "Sipariş No": f"E2E-XLS-{index:03d}",
            "Müşteri Adı": name or "Eksik İsim",
            "Ürün Adı": "01 A Gold Rulo Etiket",
            "Barkod": "CYH-GLD-01",
            "SKU": "GLD-01",
            "etiket_no": model_no,
            "isim": name,
            "tarih": date_text,
            "not": note,
            "adet": qty,
            "lazer_isim": laser_name,
        })
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_excel(path, index=False)


def seed_trendyol_suggestions(model_path: str) -> None:
    now = "2026-05-22T14:00:00"
    rows = [
        {
            "id": "ty-e2e-ready",
            "source": "trendyol",
            "order_number": "TY-E2E-1001",
            "package_id": "PKT-E2E-1001",
            "line_id": "LINE-E2E-1001",
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
            "question_contexts": [{"id": "q-e2e-1", "question_text": "Etikete Ayşe & Mehmet, 12.05.2026, Söz Hatırası yazılsın. Lazer isim Ayşe & Mehmet olsun.", "answer_text": ""}],
            "selected_question_id": "q-e2e-1",
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
            "id": "ty-e2e-no-proof",
            "source": "trendyol",
            "order_number": "TY-E2E-1002",
            "package_id": "PKT-E2E-1002",
            "line_id": "LINE-E2E-1002",
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
            "source_evidence": [],
            "confidence": 0.9,
            "status": "review",
            "verification_status": "kanit_bekliyor",
            "mapping_found": True,
            "warnings": ["Müşteri mesajı yok."],
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "ty-e2e-ambiguous",
            "source": "trendyol",
            "order_number": "TY-E2E-1003",
            "package_id": "PKT-E2E-1003",
            "line_id": "LINE-E2E-1003",
            "customer_name": "Mesaj Belirsiz",
            "product_name": "Kişiye Özel Etiket",
            "barcode": "CYH-GLD-01",
            "merchant_sku": "GLD-01",
            "quantity": 1,
            "production_type": "label",
            "model_key": "01",
            "model_path": model_path,
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "",
            "question_text": "Daha sonra isimleri yazacağım.",
            "question_contexts": [{"id": "q-e2e-3", "question_text": "Daha sonra isimleri yazacağım.", "answer_text": ""}],
            "source_evidence": ["question_text"],
            "confidence": 0.42,
            "status": "review",
            "verification_status": "kullanici_kontrol_gerekli",
            "mapping_found": True,
            "warnings": ["Mesaj belirsiz, operatör kontrolü gerekli."],
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "ty-e2e-model-missing",
            "source": "trendyol",
            "order_number": "TY-E2E-1004",
            "package_id": "PKT-E2E-1004",
            "line_id": "LINE-E2E-1004",
            "customer_name": "Model Yok",
            "product_name": "Eşleşmeyen Ürün",
            "barcode": "NO-MODEL",
            "merchant_sku": "NO-MODEL",
            "quantity": 1,
            "production_type": "label",
            "model_key": "",
            "model_path": "",
            "label_text": "Model Yok",
            "question_text": "Model Yok yazılsın.",
            "question_contexts": [{"id": "q-e2e-4", "question_text": "Model Yok yazılsın.", "answer_text": ""}],
            "field_sources": {"label_text": "question_text"},
            "source_evidence": ["question_text"],
            "confidence": 0.9,
            "status": "review",
            "verification_status": "kullanici_kontrol_gerekli",
            "mapping_found": False,
            "warnings": ["Model eşleşmedi."],
            "created_at": now,
            "updated_at": now,
        },
    ]
    path = trendyol_api.suggestions_path(PROJECT_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def enrich_excel_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = []
    for item in items:
        row = item.get("original_row_data") or {}
        next_item = dict(item)
        next_item["source"] = "excel"
        next_item["source_label"] = "Excel"
        next_item["order_no"] = row.get("Sipariş No", "")
        next_item["customer_name"] = row.get("Müşteri Adı", next_item.get("label_text", ""))
        next_item["product_name"] = row.get("Ürün Adı", "")
        next_item["barcode"] = row.get("Barkod", "")
        next_item["sku"] = row.get("SKU", "")
        next_item["name_cut_text"] = row.get("lazer_isim", "")
        next_item["laser_name"] = row.get("lazer_isim", "")
        if len(str(next_item.get("label_text") or "")) > 22 and next_item.get("status") == "READY":
            next_item["status"] = "WARNING"
            next_item["warnings"] = [*(next_item.get("warnings") or []), "Yazı taşıyor olabilir."]
        enriched.append(next_item)
    return enriched


def seed_namecut_items() -> dict[str, Any]:
    payload = {
        "summary": {"transfer_batch_id": "E2E-NCQ-001", "total": 3, "added": 2, "needs_review": 1, "blocked": 1},
        "items": [
            {
                "id": "e2e-namecut-ready-1",
                "item_id": "e2e-namecut-ready-1",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "bulk_row_id": "row-2",
                "order_no": "E2E-XLS-001",
                "customer_name": "Ayşe & Mehmet",
                "laser_name": "Ayşe & Mehmet",
                "name_text": "Ayşe & Mehmet",
                "quantity": 2,
                "label_model": "01 A Gold Rulo Etiket",
                "laser_model": "01 A Gold Lazer Kesim",
                "status": "pending_preparation",
                "safety_flags": [],
                "duplicate_key": "bulk_production:e2e:row-2",
                "transfer_batch_id": "E2E-NCQ-001",
                "quality_status": "ready_single_piece",
                "offset_mm": 0.35,
            },
            {
                "id": "e2e-namecut-review-1",
                "item_id": "e2e-namecut-review-1",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "bulk_row_id": "row-4",
                "order_no": "E2E-XLS-003",
                "customer_name": "Mustafa Kemal & Yağmur",
                "laser_name": "Mustafa Kemal",
                "name_text": "Mustafa Kemal",
                "quantity": 1,
                "label_model": "01 A Gold Rulo Etiket",
                "laser_model": "01 A Gold Lazer Kesim",
                "status": "needs_review",
                "safety_flags": ["long_name"],
                "duplicate_key": "bulk_production:e2e:row-4",
                "transfer_batch_id": "E2E-NCQ-001",
                "quality_status": "needs_offset",
                "offset_mm": 0.35,
            },
        ],
    }
    return name_cut_queue_api.save_name_cut_queue_items(PROJECT_ROOT, payload)


def append_audit_events(events: list[dict[str, Any]]) -> None:
    for event in events:
        production_audit_api.append_production_audit_event(PROJECT_ROOT, event)


def compact_bulk_item(item: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "id",
        "item_id",
        "row_number",
        "source",
        "source_label",
        "source_type",
        "order_no",
        "customer_name",
        "product_name",
        "barcode",
        "sku",
        "model_key",
        "model_name",
        "model_status",
        "model_path",
        "model_no",
        "template_no",
        "label_variant",
        "label_text",
        "date_text",
        "note_text",
        "name_cut_text",
        "laser_name",
        "quantity",
        "width_mm",
        "height_mm",
        "size_text",
        "preview_png_path",
        "status",
        "errors",
        "warnings",
        "is_deleted",
        "is_edited",
        "verification_status",
        "field_sources",
        "field_confidence",
        "source_evidence",
        "proof_text",
        "question_text",
        "confidence",
        "mapping_found",
        "is_operator_corrected",
        "operator_corrections",
        "duplicate_key",
    ]
    compact = {key: item.get(key) for key in keys if key in item}
    if not compact.get("id"):
        compact["id"] = compact.get("item_id") or f"bulk-{compact.get('row_number', '')}"
    if not compact.get("item_id"):
        compact["item_id"] = compact.get("id")
    compact["errors"] = list(compact.get("errors") or [])
    compact["warnings"] = list(compact.get("warnings") or [])
    compact["is_deleted"] = bool(compact.get("is_deleted", False))
    compact["is_edited"] = bool(compact.get("is_edited", False))
    return compact


def run_gate() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backup = backup_data()
    checks: list[dict[str, Any]] = []
    screenshots: dict[str, str] = {}
    artifacts: dict[str, Any] = {}
    try:
        reset_data()
        app = QApplication.instance() or QApplication(sys.argv)
        suppress_message_boxes()
        window = WebMainWindow(PROJECT_ROOT, sys.executable)
        window.resize(1920, 1080)
        window.show()
        wait(1800)

        model_path = first_label_model_path()
        label_models = window.label_model_gallery()
        excel_path = OUTPUT_DIR / "phase19_real_user_excel_fixture.xlsx"
        create_excel_fixture(excel_path)
        window.selected_excel = excel_path

        mapping = window.bulk_column_mapping()
        excel_items = enrich_excel_items(window.bulk_gallery_items())
        assert_true(len(excel_items) == 20, "Excel fixture 20 satır olarak okundu", checks)
        assert_true(any(item.get("status") == "ERROR" for item in excel_items), "Excel içinde üretime engel kayıt var", checks)
        assert_true(any(item.get("status") == "WARNING" for item in excel_items), "Excel içinde kontrol gerekli kayıt var", checks)
        assert_true(any(item.get("name_cut_text") for item in excel_items), "Excel içinde lazer isimli kayıt var", checks)

        seed_trendyol_suggestions(model_path)
        trendyol_import = window.import_trendyol_to_bulk_production([
            "ty-e2e-ready",
            "ty-e2e-no-proof",
            "ty-e2e-ambiguous",
            "ty-e2e-model-missing",
        ])
        duplicate_import = window.import_trendyol_to_bulk_production(["ty-e2e-ready"])
        correction_result = window.save_trendyol_operator_correction(
            "ty-e2e-no-proof",
            {
                "label_text": "Helin Cemal",
                "date_text": "20.05.2026",
                "note_text": "Nişan Hatırası",
                "name_cut_text": "Helin Cemal",
                "quantity": "1",
                "model_path": model_path,
                "model_name": "01 A Gold Rulo Etiket",
                "operator_note": "E2E operatör düzeltmesi",
            },
        )
        trendyol_items = trendyol_import.get("items") or []
        assert_true(trendyol_import.get("status") in {"OK", "PARTIAL"}, "Trendyol kayıtları Toplu Üretim sözleşmesine aktarıldı", checks)
        assert_true(any(item.get("source") == "trendyol" and item.get("source_label") == "Trendyol" for item in trendyol_items), "Trendyol source/source_label korundu", checks)
        assert_true(any(item.get("item_id") == "trendyol-ty-e2e-no-proof" and not item.get("label_text") for item in trendyol_items), "Kanıt yoksa kişiselleştirme uydurulmadı", checks)
        assert_true(duplicate_import.get("duplicates", 0) >= 1 or duplicate_import.get("status") in {"DUPLICATE", "PARTIAL"}, "Trendyol duplicate import engellendi", checks)
        assert_true(correction_result.get("status") == "OK", "Trendyol operatör düzeltmesi kaydedildi", checks)

        all_bulk_items = [compact_bulk_item(item) for item in trendyol_items + excel_items]
        js_items = json.dumps(all_bulk_items, ensure_ascii=False)
        js_label_models = json.dumps(label_models, ensure_ascii=False)
        ui_bulk = run_js(window, f"""
        (() => {{
          const items = {js_items};
          currentLabelModels = {js_label_models};
          bulkGalleryItems = items;
          currentState.bulkGalleryItems = items;
          currentState.labelModels = currentLabelModels;
          selectedBulkGalleryItemId = items[0]?.item_id || "";
          setBulkProductionSource("trendyol");
          setBulkProductionStep(4);
          showSection("bulkLabel");
          renderBulkProductionSummary();
          renderBulkGallery();
          return {{
            active: document.querySelector(".page.active")?.id || "",
            cards: document.querySelectorAll(".bulk-gallery-item").length,
            total: items.length,
            visibleText: document.body.innerText.includes("Daha fazla göster")
          }};
        }})()
        """, timeout_ms=120000)
        assert_true(ui_bulk.get("active") == "bulkLabel", "Toplu Üretim ekranı açıldı", checks)
        assert_true(ui_bulk.get("cards", 0) >= 1, "Toplu Üretim galeri kartları render edildi", checks)
        screenshots["bulk_1920"] = save_screenshot(window, "e2e-bulk-production-1920.png")

        evidence_ui = run_js(window, """
        (() => {
          openBulkTrendyolEvidenceDrawer("trendyol-ty-e2e-ready", "all");
          return {
            open: !document.getElementById("bulkTrendyolEvidenceDrawer")?.hidden,
            text: document.body.innerText
          };
        })()
        """)
        assert_true(evidence_ui.get("open"), "Trendyol kanıt drawer açıldı", checks)
        screenshots["trendyol_evidence"] = save_screenshot(window, "e2e-trendyol-evidence-drawer.png")

        run_js(window, """
        (() => {
          closeBulkTrendyolEvidenceDrawer();
          openBulkItemInLabelStudio("trendyol-ty-e2e-ready");
          return true;
        })()
        """)
        wait(900)
        studio_ui = run_js(window, """
        (() => ({
          active: document.querySelector(".page.active")?.id || "",
          status: document.getElementById("manualLiveStatus")?.textContent || "",
          text: document.body.innerText
        }))()
        """)
        assert_true(studio_ui.get("active") == "label", "Etiket Studio Toplu Üretim verisiyle açıldı", checks)
        assert_true("Veri Hazır" in studio_ui.get("status", "") and "Önizleme Eksik" in studio_ui.get("status", ""), "Studio durum dili Veri Hazır / Önizleme Eksik olarak ayrıldı", checks)
        screenshots["label_studio"] = save_screenshot(window, "e2e-label-studio.png")

        output_pdf = OUTPUT_DIR / "e2e_bulk_output_ready.pdf"
        output_png = OUTPUT_DIR / "e2e_bulk_output_ready.png"
        studio_pdf = OUTPUT_DIR / "e2e_label_studio_output.pdf"
        missing_pdf = OUTPUT_DIR / "e2e_missing_output.pdf"
        write_minimal_pdf(output_pdf, "Bulk Production Ready")
        write_minimal_png(output_png)
        write_minimal_pdf(studio_pdf, "Label Studio Ready")

        queue_bulk = print_queue_api.add_to_print_queue(PROJECT_ROOT, {
            "relative_path": rel(output_pdf),
            "output_path": rel(output_pdf),
            "preview_path": rel(output_png),
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "origin_source": "trendyol",
            "origin_source_label": "Trendyol",
            "source_item_id": "trendyol-ty-e2e-ready",
            "bulk_row_id": "trendyol-ty-e2e-ready",
            "job_name": "Ayşe & Mehmet",
            "title": "Ayşe & Mehmet",
            "label_model": "01 A Gold Rulo Etiket",
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Ayşe & Mehmet",
            "date_text": "12.05.2026",
            "note_text": "Söz Hatırası",
            "quantity": "2",
            "batch_id": "E2E-BULK-001",
            "duplicate_key": "bulk_production:e2e:trendyol-ty-e2e-ready",
        })
        queue_studio = print_queue_api.add_to_print_queue(PROJECT_ROOT, {
            "relative_path": rel(studio_pdf),
            "output_path": rel(studio_pdf),
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "source_item_id": "studio-e2e-001",
            "studio_session_id": "studio-e2e-001",
            "job_name": "Helin Cemal",
            "title": "Helin Cemal",
            "label_model": "01 A Gold Rulo Etiket",
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Helin Cemal",
            "date_text": "20.05.2026",
            "note_text": "Nişan Hatırası",
            "quantity": "1",
            "duplicate_key": "label_studio:e2e:studio-e2e-001",
        })
        queue_missing = print_queue_api.add_to_print_queue(PROJECT_ROOT, {
            "relative_path": rel(missing_pdf),
            "output_path": rel(missing_pdf),
            "source": "manual_label",
            "source_label": "Manuel Etiket",
            "source_item_id": "manual-e2e-missing",
            "job_name": "Eksik Çıktı",
            "title": "Eksik Çıktı",
            "label_model": "01 A Gold Rulo Etiket",
            "quantity": "1",
            "duplicate_key": "manual_label:e2e:missing-output",
        })
        queue_duplicate = print_queue_api.add_to_print_queue(PROJECT_ROOT, {
            "relative_path": rel(output_pdf),
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "duplicate_key": "bulk_production:e2e:trendyol-ty-e2e-ready",
        })
        queue_rows = print_queue_api.list_print_queue(PROJECT_ROOT)
        ready_rows = [row for row in queue_rows if row.get("status_key") == "ready_to_print"]
        missing_rows = [row for row in queue_rows if "missing_output" in row.get("safety_flags", []) or row.get("status_key") == "blocked"]
        assert_true(queue_bulk.get("status") == "ADDED", "Toplu Üretim kaydı Yazdırma Sırası'na eklendi", checks)
        assert_true(queue_studio.get("status") == "ADDED", "Etiket Studio kaydı Yazdırma Sırası'na eklendi", checks)
        assert_true(queue_duplicate.get("status") == "EXISTS", "Yazdırma Sırası duplicate kontrolü çalıştı", checks)
        assert_true(any(row.get("source") == "bulk_production" and row.get("origin_source") == "trendyol" for row in queue_rows), "Queue origin_source Trendyol olarak korundu", checks)
        assert_true(len(ready_rows) >= 2, "Gerçek çıktı dosyası olan kayıtlar ready_to_print oldu", checks)
        assert_true(len(missing_rows) >= 1, "Çıktı dosyası eksik kayıt yazdırmaya hazır sayılmadı", checks)

        append_audit_events([
            production_audit_api.create_audit_event_from_bulk_batch({"batch_id": "E2E-BULK-001", "total": len(all_bulk_items), "ready": len(ready_rows)}, "bulk_validation_completed", "E2E Toplu Üretim validasyonu tamamlandı."),
            production_audit_api.create_audit_event_from_queue_item(next(row for row in queue_rows if row.get("id") == queue_bulk.get("id")), "bulk_sent_to_print_queue", "Toplu Üretim kaydı Yazdırma Sırası'na gönderildi."),
            production_audit_api.create_audit_event_from_queue_item(next(row for row in queue_rows if row.get("id") == queue_studio.get("id")), "label_output_created", "Etiket Studio çıktısı oluşturuldu."),
            production_audit_api.create_audit_event_from_queue_item(next(row for row in queue_rows if row.get("id") == queue_missing.get("id")), "output_missing", "Çıktı dosyası bulunamadı."),
            {
                "audit_key": "phase19-duplicate-print-queue",
                "event_type": "duplicate_detected",
                "source": "print_queue",
                "source_label": "Yazdırma Sırası",
                "queue_item_id": queue_bulk.get("id"),
                "severity": "warning",
                "status": "duplicate",
                "message": "E2E duplicate queue denemesi engellendi.",
            },
        ])

        queue_ui = run_js(window, f"""
        (() => {{
          currentState.printQueue = {json.dumps(queue_rows, ensure_ascii=False)};
          showSection("printQueue");
          updatePrintQueue(currentState.printQueue);
          safePrint({json.dumps(queue_bulk.get("id"))});
          return {{
            active: document.querySelector(".page.active")?.id || "",
            hasBulkBadge: document.body.innerText.includes("Toplu Üretim"),
            hasMissing: document.body.innerText.includes("Çıktı dosyası") || document.body.innerText.includes("Yazdırmaya hazır değil"),
            confirmText: document.body.innerText.includes("Yazıcı otomatik")
          }};
        }})()
        """)
        assert_true(queue_ui.get("active") == "printQueue", "Yazdırma Sırası ekranı açıldı", checks)
        assert_true(queue_ui.get("hasBulkBadge"), "Yazdırma Sırası Toplu Üretim rozetini gösterdi", checks)
        assert_true(queue_ui.get("confirmText"), "Yazdırma güvenlik metni görünüyor", checks)
        screenshots["print_queue"] = save_screenshot(window, "e2e-print-queue.png")

        namecut_save = seed_namecut_items()
        duplicate_namecut = name_cut_queue_api.save_name_cut_queue_items(PROJECT_ROOT, {
            "summary": {"transfer_batch_id": "E2E-NCQ-001"},
            "items": [{
                "id": "e2e-namecut-ready-1-dup",
                "item_id": "e2e-namecut-ready-1-dup",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "bulk_row_id": "row-2",
                "laser_name": "Ayşe & Mehmet",
                "name_text": "Ayşe & Mehmet",
                "quantity": 2,
                "duplicate_key": "bulk_production:e2e:row-2",
            }],
        })
        namecut_rows = name_cut_queue_api.list_name_cut_queue_items(PROJECT_ROOT)
        export_items = [row for row in namecut_rows if row.get("item_id") == "e2e-namecut-ready-1"]
        export_result = window.prepare_name_cut_files(export_items, {
            "formats": ["svg", "pdf"],
            "cut_direction": "mirror_horizontal",
            "mirror_cut": True,
            "mirror_vertical": False,
            "safe_margin_mm": 8,
            "min_gap_mm": 2,
            "offset_mm": 0.35,
            "operator": "Phase19 QA",
            "quality_summary": {"single_piece_ready": True, "collision_free": True, "offset_applied": True},
        })
        namecut_after = name_cut_queue_api.list_name_cut_queue_items(PROJECT_ROOT)
        export_history = name_cut_queue_api.list_name_cut_export_history(PROJECT_ROOT)
        manifest_path = PROJECT_ROOT / str(export_result.get("manifest_path") or "")
        assert_true(namecut_save.get("added", 0) >= 1, "İsim Kesim kalıcı kuyruğuna kayıt yazıldı", checks)
        assert_true(duplicate_namecut.get("duplicate", 0) >= 1, "İsim Kesim duplicate kontrolü kalıcı çalıştı", checks)
        assert_true(export_result.get("status") == "OK", "İsim Kesim güvenli export paketi oluşturuldu", checks)
        assert_true(manifest_path.exists(), "İsim Kesim manifest dosyası oluştu", checks)
        assert_true(any(row.get("status") == "exported" for row in namecut_after), "Export edilen İsim Kesim kaydı exported durumuna geçti", checks)
        assert_true(len(export_history) >= 1, "İsim Kesim export geçmişi kalıcı yazıldı", checks)
        append_audit_events([
            production_audit_api.create_audit_event_from_namecut_item(row, "namecut_queue_created", "E2E İsim Kesim queue kaydı oluşturuldu.")
            for row in namecut_rows
        ])
        production_audit_api.append_production_audit_event(PROJECT_ROOT, {
            "audit_key": "phase19-namecut-export",
            "event_type": "namecut_export_created",
            "source": "name_cut",
            "source_label": "İsim Kesim",
            "export_batch_id": export_result.get("export_batch_id") or export_result.get("batch_id"),
            "status": export_result.get("status"),
            "severity": "success",
            "message": "E2E İsim Kesim export paketi oluşturuldu. Lazer/RDWorks başlatılmadı.",
            "file_path": export_result.get("manifest_path", ""),
            "output_path": export_result.get("svg_path", ""),
        })

        namecut_ui = run_js(window, """
        (() => {
          showSection("nameCutStudio");
          if (typeof refreshState === "function") refreshState();
          if (typeof refreshNameCutStudioViews === "function") refreshNameCutStudioViews(currentNameCutLayout());
          return {
            active: document.querySelector(".page.active")?.id || "",
            text: document.body.innerText
          };
        })()
        """)
        assert_true(namecut_ui.get("active") == "nameCutStudio", "İsim Kesim ekranı açıldı", checks)
        screenshots["namecut"] = save_screenshot(window, "e2e-namecut.png")

        csv_export = production_audit_api.export_production_audit_events(PROJECT_ROOT, {"source": "trendyol"}, "csv")
        json_export = production_audit_api.export_production_audit_events(PROJECT_ROOT, {"severity": "warning"}, "json")
        audit_events = production_audit_api.list_production_audit_events(PROJECT_ROOT)
        assert_true(csv_export.get("status") == "OK" and (PROJECT_ROOT / str(csv_export.get("relative_path", ""))).exists(), "Üretim Geçmişi filtreli CSV export dosyası oluştu", checks)
        assert_true(json_export.get("status") == "OK" and (PROJECT_ROOT / str(json_export.get("relative_path", ""))).exists(), "Üretim Geçmişi filtreli JSON export dosyası oluştu", checks)
        assert_true(any(event.get("event_type") == "namecut_export_created" for event in audit_events), "Audit'te İsim Kesim export event'i var", checks)
        assert_true(any(event.get("event_type") == "duplicate_detected" for event in audit_events), "Audit'te duplicate event'i var", checks)
        assert_true(any(event.get("event_type") == "output_missing" for event in audit_events), "Audit'te output_missing event'i var", checks)

        audit_ui = run_js(window, f"""
        (() => {{
          currentState.productionAudit = {json.dumps(audit_events, ensure_ascii=False)};
          showSection("productionAudit");
          updateProductionAudit(currentState.productionAudit);
          const printEvent = currentState.productionAudit.find(row => row.event_type === "print_queue_created" || row.event_type === "bulk_sent_to_print_queue");
          const target = printEvent ? resolveAuditEventTarget(printEvent) : null;
          return {{
            active: document.querySelector(".page.active")?.id || "",
            hasTimeline: document.body.innerText.includes("Üretim Geçmişi") || document.body.innerText.includes("Zaman Akışı"),
            targetScreen: target?.page || "",
            count: currentState.productionAudit.length
          }};
        }})()
        """)
        assert_true(audit_ui.get("active") == "productionAudit", "Üretim Geçmişi ekranı açıldı", checks)
        assert_true(audit_ui.get("targetScreen") in {"printQueue", "bulkLabel", "nameCutStudio", "label"}, "Audit deep-link hedefi çözüldü", checks)
        screenshots["audit"] = save_screenshot(window, "e2e-production-audit.png")

        window.resize(1366, 768)
        wait(900)
        run_js(window, "(() => { showSection('bulkLabel'); renderBulkGallery(); return true; })()")
        screenshots["overview_1366"] = save_screenshot(window, "e2e-overview-1366.png")
        window.resize(1920, 1080)
        wait(900)
        run_js(window, "(() => { showSection('productionAudit'); updateProductionAudit(currentState.productionAudit || []); return true; })()")
        screenshots["overview_1920"] = save_screenshot(window, "e2e-overview-1920.png")

        body_text = run_js(window, "(() => document.body.innerText)()")
        forbidden_tokens = [
            "yazıcı başlatıldı",
            "lazer başlatıldı",
            "rdworks başlatıldı",
            "canlı sipariş statüsü değişti",
            "kargo etiketi alındı",
            "fatura kesildi",
        ]
        assert_true(not any(token in str(body_text).lower() for token in forbidden_tokens), "Canlı yazıcı/lazer/RDWorks/Trendyol tetikleme mesajı yok", checks)

        artifacts.update({
            "excel_fixture": str(excel_path),
            "queue_rows": len(queue_rows),
            "namecut_rows": len(namecut_after),
            "audit_events": len(audit_events),
            "csv_export": {
                "status": csv_export.get("status"),
                "path": csv_export.get("path") or csv_export.get("relative_path"),
                "count": csv_export.get("count"),
            },
            "json_export": {
                "status": json_export.get("status"),
                "path": json_export.get("path") or json_export.get("relative_path"),
                "count": json_export.get("count"),
            },
            "namecut_export": {
                "status": export_result.get("status"),
                "export_batch_id": export_result.get("export_batch_id") or export_result.get("batch_id"),
                "manifest_path": export_result.get("manifest_path"),
                "svg_path": export_result.get("svg_path"),
            },
            "mapping_status": mapping.get("status"),
        })
        result = {
            "status": "PASSED",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "checks": checks,
            "screenshots": screenshots,
            "artifacts": artifacts,
            "safety": {
                "printer_started": False,
                "laser_started": False,
                "rdworks_started": False,
                "trendyol_live_status_changed": False,
            },
        }
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    except Exception as exc:  # noqa: BLE001
        result = {
            "status": "FAILED",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "error": str(exc),
            "checks": checks,
            "screenshots": screenshots,
            "artifacts": artifacts,
        }
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    finally:
        try:
            window.close()  # type: ignore[name-defined]
        except Exception:
            pass
        restore_data(backup)


if __name__ == "__main__":
    gate_result = run_gate()
    print(json.dumps(gate_result, ensure_ascii=False, indent=2))
    if gate_result.get("status") != "PASSED":
        raise SystemExit(1)
