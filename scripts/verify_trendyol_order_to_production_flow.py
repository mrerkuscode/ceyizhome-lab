from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend import customer_order_api, trendyol_api, trendyol_mapping_api


def sample_order(barcode: str = "TY-ETIKET-01", line_id: str = "LINE-1", sku: str = "SKU-ETIKET-01") -> dict[str, object]:
    return {
        "orderNumber": "TY-9001",
        "shipmentPackageId": "PKG-9001",
        "customerFirstName": "Ayse",
        "customerLastName": "Omer",
        "lines": [
            {
                "id": line_id,
                "productName": "Kisiye Ozel Nisan Etiketi isim: Ayse & Omer not: Nisan Hatirasi 15.05.2026",
                "barcode": barcode,
                "merchantSku": sku,
                "quantity": 10,
            }
        ],
    }


def save_sample_question(project_root: Path, barcode: str = "TY-ETIKET-01") -> None:
    trendyol_api._save_questions(
        project_root,
        [
            trendyol_api._normalize_question_context(
                project_root,
                {
                    "id": f"Q-{barcode}",
                    "status": "WaitingForAnswer",
                    "orderNumber": "TY-9001",
                    "barcode": barcode,
                    "text": "isim: Ayşe & Ömer tarih: 15.05.2026 not: Nişan Hatırası",
                },
            )
        ],
    )


def assert_condition(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def verify_ready(project_root: Path, row: dict[str, object]) -> dict[str, object]:
    return trendyol_api.verify_suggestion(
        project_root,
        str(row.get("id") or ""),
        {
            "label_required": True,
            "name_cut_required": True,
            "label_text": row.get("label_text") or "",
            "name_cut_text": row.get("name_cut_text") or row.get("label_text") or "",
            "date_text": row.get("date_text") or "",
            "note_text": row.get("note_text") or "",
            "model_path": row.get("model_path") or "",
        },
    )


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cyzella_trendyol_verify_") as temp:
        temp_root = Path(temp)
        missing = trendyol_api.test_connection(temp_root)
        assert_condition(missing["status"] == "CONFIG_MISSING", "Missing credentials did not return a safe error.", failures)
        assert_condition("api_secret" not in json.dumps(missing).lower(), "Credential error leaked api_secret.", failures)

        trendyol_mapping_api.upsert_product_mapping(
            temp_root,
            {
                "barcode": "TY-ETIKET-01",
                "merchant_sku": "SKU-ETIKET-01",
                "production_type": "label_and_name_cut",
                "model_key": "01",
                "model_path": "templates/designs/01_a_gold.json",
                "model_name": "01 A Gold Rulo Etiket",
                "name_cut_style": "Mochary Personal Use Only",
                "name_cut_width_mm": 300,
            },
        )
        save_sample_question(temp_root)
        suggestions = trendyol_api.build_suggestions_from_orders(temp_root, [sample_order(), sample_order("UNKNOWN", "LINE-2", "UNKNOWN-SKU")])
        assert_condition(len(suggestions) == 2, "Two Trendyol order lines were not converted to suggestions.", failures)
        ready = next((row for row in suggestions if row.get("barcode") == "TY-ETIKET-01"), {})
        review = next((row for row in suggestions if row.get("barcode") == "UNKNOWN"), {})
        assert_condition(ready.get("status") == "review" and ready.get("verification_status") == "alanlar_onay_bekliyor", "Mapped line did not wait for evidence approval.", failures)
        assert_condition(ready.get("model_path") == "templates/designs/01_a_gold.json", "Mapped line did not target the correct model.", failures)
        assert_condition(ready.get("label_text") == "Ayşe & Ömer", "Question evidence did not populate label_text.", failures)
        assert_condition(ready.get("date_text") == "15.05.2026", "Question evidence did not populate date_text.", failures)
        assert_condition(review.get("status") == "review", "Unmatched barcode did not require review.", failures)

        trendyol_api.save_suggestions(temp_root, suggestions)
        verified = verify_ready(temp_root, ready)
        assert_condition(verified.get("status") == "OK", "Evidence-backed row could not be approved by user verification.", failures)
        exported = trendyol_api.export_ready_suggestions_to_excel(temp_root)
        imported = trendyol_api.import_suggestion_to_customer_order(temp_root, str(ready.get("id") or ""))
        duplicate = trendyol_api.import_suggestion_to_customer_order(temp_root, str(ready.get("id") or ""))

        mapping_export = trendyol_mapping_api.export_product_mappings_to_excel(temp_root)
        mapping_import_source = temp_root / "mapping_import.xlsx"
        pd.DataFrame(
            [
                {
                    "product_name": "Ikinci Trendyol Urunu",
                    "barcode": "TY-ETIKET-02",
                    "merchant_sku": "SKU-ETIKET-02",
                    "stock_code": "STOCK-02",
                    "production_type": "label",
                    "model_key": "01",
                    "model_path": "templates/designs/01_a_gold.json",
                    "model_name": "01 A Gold Rulo Etiket",
                    "active": "evet",
                }
            ]
        ).to_excel(mapping_import_source, index=False)
        mapping_import = trendyol_mapping_api.import_product_mappings_from_file(temp_root, mapping_import_source)
        orders = customer_order_api.list_customer_orders(temp_root)
        assert_condition(imported["status"] == "OK", "Approved Trendyol row was not imported to customer orders.", failures)
        assert_condition(duplicate["status"] == "DUPLICATE", "Same Trendyol line was imported twice.", failures)
        assert_condition(len(orders) == 1 and orders[0].get("source") == "trendyol", "Customer order does not carry Trendyol source.", failures)
        assert_condition(exported["status"] == "OK" and (temp_root / exported["relative_path"]).exists(), "Approved Trendyol row was not exported to production Excel.", failures)
        assert_condition(mapping_export["status"] == "OK" and (temp_root / mapping_export["relative_path"]).exists(), "Trendyol mapping Excel export failed.", failures)
        assert_condition(mapping_import["status"] == "OK" and len(trendyol_mapping_api.list_product_mappings(temp_root)) >= 2, "Trendyol mapping Excel import failed.", failures)

        original_fetch = trendyol_api._fetch_json
        trendyol_api.save_settings(temp_root, {"supplier_id": "123", "api_key": "key", "api_secret": "secret", "environment": "live"})

        def fake_product_fetch_json(project_root: Path, path: str, *, v2: bool, timeout: int | None = None) -> dict[str, object]:
            if "/product/sellers/123/products" in path:
                return {
                    "content": [
                        {
                            "title": "03 Yesil Geometrik Etiket",
                            "barcode": "TY-ETIKET-03",
                            "stockCode": "SKU-ETIKET-03",
                            "images": [{"url": "https://cdn.example.test/03.png"}],
                        }
                    ]
                }
            raise AssertionError(path)

        trendyol_api._fetch_json = fake_product_fetch_json
        try:
            catalog_result = trendyol_api.propose_mapping_from_catalog(
                temp_root,
                [{"model_no": "03", "model_name": "Yesil Geometrik Etiket", "path": "templates/designs/03_yesil_geometrik.json"}],
                max_pages=1,
            )
            catalog_suggestions = catalog_result.get("suggestions") or []
            catalog_before_approval = [row for row in trendyol_mapping_api.list_product_mappings(temp_root) if row.get("barcode") == "TY-ETIKET-03"]
            catalog_approved = trendyol_api.approve_mapping_suggestion(temp_root, str(catalog_suggestions[0].get("id") if catalog_suggestions else ""))
            catalog_after_approval = [row for row in trendyol_mapping_api.list_product_mappings(temp_root) if row.get("barcode") == "TY-ETIKET-03"]
        finally:
            trendyol_api._fetch_json = original_fetch
        assert_condition(catalog_result.get("status") == "OK" and catalog_suggestions, "Trendyol catalog mapping suggestion was not produced.", failures)
        assert_condition(catalog_suggestions and catalog_suggestions[0].get("model_path") == "templates/designs/03_yesil_geometrik.json", "Catalog suggestion did not map to the expected Cyzella model.", failures)
        assert_condition(not catalog_before_approval, "Catalog suggestion was silently saved before approval.", failures)
        assert_condition(catalog_approved.get("status") == "OK" and catalog_after_approval, "Catalog suggestion was not saved after approval.", failures)

        def fake_fetch_json(project_root: Path, path: str, *, v2: bool, timeout: int | None = None) -> dict[str, object]:
            if "/integration/ecgw/v2/" in path and "/packages/items" not in path:
                return {"items": [{"packageId": 7001, "trackingNumber": "TRK7001", "status": "new", "creationDate": 1770000000000}]}
            if "/integration/ecgw/v2/" in path and "/packages/items" in path:
                return {"items": [{"itemId": 701, "name": "Kisiye Ozel Nisan Etiketi isim: Sedef & Sefer not: Nisan Hatirasi 15.05.2026", "barcode": "TY-ETIKET-01", "sellerBarcode": "SKU-ETIKET-01", "newQuantity": 3}]}
            if "/order/sellers/" in path:
                return {"content": [{"orderNumber": "TY-V1-7001", "shipmentPackageId": 7001, "customerFirstName": "Sedef", "customerLastName": "Sefer", "lines": []}]}
            if "/qna/sellers/" in path and "/questions/filter" in path:
                return {"content": [{"id": 1, "orderNumber": "TY-V1-7001", "barcode": "TY-ETIKET-01", "text": "isim: Sedef Sefer"}]}
            raise AssertionError(path)

        trendyol_api._fetch_json = fake_fetch_json
        try:
            hybrid_orders = trendyol_api.fetch_orders(temp_root, pd.Timestamp("2026-05-01").to_pydatetime(), pd.Timestamp("2026-05-02").to_pydatetime())
            questions = trendyol_api.fetch_questions(temp_root)
            synced_questions = trendyol_api.sync_questions(temp_root)
        finally:
            trendyol_api._fetch_json = original_fetch
        assert_condition(hybrid_orders and hybrid_orders[0].get("source_api") == "v2_packages_with_v1_enrichment", "Legacy V2 package + V1 enrichment behavior was not preserved.", failures)
        assert_condition(hybrid_orders and hybrid_orders[0].get("customerName") == "Sedef Sefer", "V1 customer enrichment failed.", failures)
        assert_condition(questions and questions[0].get("barcode") == "TY-ETIKET-01", "Trendyol question data was not fetched read-only.", failures)
        assert_condition(synced_questions.get("status") == "OK" and trendyol_api.list_questions(temp_root), "Trendyol question data was not saved for UI state.", failures)

    html = (PROJECT_ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app_js = (PROJECT_ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    backend = (PROJECT_ROOT / "src" / "webui_backend" / "trendyol_api.py").read_text(encoding="utf-8").lower()
    assert_condition("trendyolOrders" in html, "Trendyol Orders page is missing from index.html.", failures)
    assert_condition("function updateTrendyolOrders" in app_js, "Trendyol UI render function is missing.", failures)
    assert_condition("exportTrendyolReadyToExcel" in app_js, "Ready-to-production Excel UI function is missing.", failures)
    assert_condition("applyTrendyolQuestionToSuggestion" in app_js, "Question evidence apply UI hook is missing.", failures)
    assert_condition("verifyTrendyolSuggestionFromDetail" in app_js, "User verification UI hook is missing.", failures)
    assert_condition("syncTrendyolQuestions" in app_js and "trendyolQuestionsList" in html, "Question evidence UI is missing.", failures)
    assert_condition("direct print" not in backend, "Trendyol backend mentions direct print.", failures)
    assert_condition("os.startfile" not in backend, "Trendyol backend tries to open external programs.", failures)

    result = {
        "status": "PASSED" if not failures else "FAILED",
        "failures": failures,
        "checked": [
            "missing credentials safe error",
            "barcode/SKU mapping with question evidence approval",
            "unmatched product review",
            "AI field extraction with field verification",
            "customer order import after user approval",
            "approved suggestions export to bulk/name cut Excel",
            "product mapping import/export Excel",
            "product catalog mapping suggestions",
            "legacy V2 package + V1 enrichment reuse",
            "read-only questions fetch",
            "duplicate prevention",
            "UI and bridge hooks",
            "no RDWorks/laser/direct print automation",
        ],
    }
    out_dir = PROJECT_ROOT / "output" / date.today().isoformat() / "trendyol_order_to_production"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "TRENDYOL_ORDER_TO_PRODUCTION_VERIFY_RESULT.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
