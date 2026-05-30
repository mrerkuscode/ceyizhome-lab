from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend import customer_order_api, trendyol_api, trendyol_mapping_api
from intelligence import trendyol_ai_extractor


def _sample_order(barcode: str = "TY-ETIKET-01") -> dict[str, object]:
    return {
        "orderNumber": "TY123",
        "shipmentPackageId": "PKG1",
        "customerFirstName": "Ayse",
        "customerLastName": "Omer",
        "lines": [
            {
                "id": "LINE1",
                "productName": "Kişiye Özel Nişan Etiketi isim: Ayşe & Ömer not: Nişan Hatırası 15.05.2026",
                "barcode": barcode,
                "merchantSku": "SKU-01",
                "images": [{"url": "https://cdn.example.test/order-etiket.png"}],
                "quantity": 10,
            }
        ],
    }


def _save_sample_question(tmp_path: Path, barcode: str = "TY-ETIKET-01", text: str = "isim: Ayşe & Ömer tarih: 15.05.2026 not: Nişan Hatırası") -> None:
    trendyol_api._save_questions(
        tmp_path,
        [
            trendyol_api._normalize_question_context(
                tmp_path,
                {
                    "id": f"Q-{barcode}",
                    "status": "WaitingForAnswer",
                    "orderNumber": "TY123",
                    "barcode": barcode,
                    "text": text,
                },
            )
        ],
    )


def test_trendyol_missing_credentials_returns_safe_error(tmp_path: Path) -> None:
    result = trendyol_api.test_connection(tmp_path)

    assert result["status"] == "CONFIG_MISSING"
    assert "api_secret" not in str(result).lower()
    assert "api_key" not in str(result).lower()


def test_trendyol_rejects_openai_key_in_trendyol_api_key(tmp_path: Path) -> None:
    trendyol_api.save_settings(
        tmp_path,
        {
            "supplier_id": "1131960",
            "api_key": "sk-proj-openai-key-in-wrong-field",
            "api_secret": "trendyol-secret",
            "ai_api_key": "sk-proj-openai-key-in-wrong-field",
            "environment": "live",
        },
    )

    result = trendyol_api.test_connection(tmp_path)
    sync = trendyol_api.sync_recent_orders(tmp_path)

    assert result["status"] == "CONFIG_INVALID"
    assert sync["status"] == "CONFIG_INVALID"
    assert "OpenAI" in result["message"]
    assert "Trendyol API Key" in result["message"]
    assert "sk-proj" not in str(result)


def test_trendyol_html_403_error_is_sanitized() -> None:
    message = trendyol_api._format_trendyol_http_error(403, "<!DOCTYPE html><html>cloudflare secret</html>", stage=True)

    assert "<!DOCTYPE" not in message
    assert "<html" not in message.lower()
    assert "secret" not in message.lower()
    assert "Stage/test" in message


def test_trendyol_stage_connection_reports_live_environment_mismatch(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(
        tmp_path,
        {
            "supplier_id": "123",
            "api_key": "key",
            "api_secret": "secret",
            "environment": "stage",
        },
    )

    def fake_fetch_json(project_root: Path, path: str, *, v2: bool, force_stage: bool | None = None, timeout: int | None = None) -> dict[str, object]:
        if force_stage is False:
            return {"totalElements": 4} if not v2 else {"totalItemCount": 2}
        raise RuntimeError("HTTP 403: <!DOCTYPE html><html>blocked</html>")

    monkeypatch.setattr(trendyol_api, "_fetch_json", fake_fetch_json)
    result = trendyol_api.test_connection(tmp_path)

    assert result["status"] == "ENV_MISMATCH"
    assert result["ok"] is False
    assert "Stage/test" in result["message"]
    assert "<!DOCTYPE" not in result["message"]
    assert result["products"] == 4
    assert result["packages"] == 2


def test_trendyol_barcode_mapping_waits_for_question_or_user_approval(tmp_path: Path) -> None:
    mapping = trendyol_mapping_api.upsert_product_mapping(
        tmp_path,
        {
            "barcode": "TY-ETIKET-01",
            "merchant_sku": "SKU-01",
            "production_type": "label_and_name_cut",
            "model_key": "01",
            "model_path": "templates/designs/01_a_gold.json",
            "model_name": "01 A Gold Rulo Etiket",
            "name_cut_style": "Mochary Personal Use Only",
            "name_cut_width_mm": 300,
        },
    )
    assert mapping["status"] == "OK"

    suggestions = trendyol_api.build_suggestions_from_orders(tmp_path, [_sample_order()])

    assert len(suggestions) == 1
    row = suggestions[0]
    assert row["status"] == "review"
    assert row["verification_status"] == "kanit_bekliyor"
    assert row["user_verified"] is False
    assert row["production_type"] == "label_and_name_cut"
    assert row["model_path"] == "templates/designs/01_a_gold.json"
    assert row["quantity"] == 10
    assert row["image_url"] == "https://cdn.example.test/order-etiket.png"
    assert row["label_text"] == ""
    assert row["date_text"] == ""
    assert row["note_text"] == ""
    assert "barcode_match" in row["source_evidence"]
    assert any("soru/mesaj" in warning.lower() for warning in row["warnings"])


def test_trendyol_question_context_extracts_personalization_for_mapped_order(tmp_path: Path) -> None:
    trendyol_mapping_api.upsert_product_mapping(
        tmp_path,
        {
            "barcode": "TY-QUESTION-01",
            "merchant_sku": "SKU-Q",
            "production_type": "label_and_name_cut",
            "model_key": "01",
            "model_path": "templates/designs/01_a_gold.json",
            "model_name": "01 A Gold Rulo Etiket",
            "name_cut_style": "Mochary Personal Use Only",
            "name_cut_width_mm": 300,
        },
    )
    question = {
        "id": "Q1",
        "status": "WaitingForAnswer",
        "orderNumber": "TY123",
        "barcode": "TY-QUESTION-01",
        "customerName": "Fatma Yılmaz",
        "productName": "Kişiye Özel Çikolata",
        "text": "Merhaba isim: Sedef & Sefer tarih: 12.06.2026 not: Söz Hatırası olacak.",
    }
    trendyol_api._save_questions(tmp_path, [trendyol_api._normalize_question_context(tmp_path, question)])
    order = _sample_order("TY-QUESTION-01")
    order["lines"][0]["productName"] = "Kişiye Özel Çikolata"
    order["lines"][0]["merchantSku"] = "SKU-Q"

    row = trendyol_api.build_suggestions_from_orders(tmp_path, [order])[0]

    assert row["status"] == "review"
    assert row["verification_status"] == "alanlar_onay_bekliyor"
    assert row["label_text"] == "Sedef & Sefer"
    assert row["date_text"] == "12.06.2026"
    assert row["note_text"] == "Söz Hatırası olacak."
    assert row["question_contexts"][0]["question_text"].startswith("Merhaba isim")
    assert "question_context" in row["source_evidence"]
    assert row["field_sources"]["label_text"] == "question_text"
    assert row["field_sources"]["date_text"] == "question_text"

    trendyol_api.save_suggestions(tmp_path, [row])
    verified = trendyol_api.verify_suggestion(
        tmp_path,
        row["id"],
        {
            "label_required": True,
            "name_cut_required": True,
            "label_text": row["label_text"],
            "name_cut_text": row["name_cut_text"],
            "date_text": row["date_text"],
            "note_text": row["note_text"],
            "model_path": row["model_path"],
        },
    )
    assert verified["status"] == "OK"
    assert verified["suggestion"]["status"] == "ready"
    assert verified["suggestion"]["verification_status"] == "uretime_hazir"


def test_trendyol_verify_saves_learning_example(tmp_path: Path) -> None:
    row = {
        "id": "LEARN-1",
        "question_text": "isimler: Aleyna ve Özcan İsteme tarihi: 31.05.2026 Tül seçimimiz: siyah",
        "answer_text": "",
        "question_contexts": [],
        "production_type": "label_and_name_cut",
        "model_path": "templates/designs/01_a_gold.json",
        "model_name": "01 A Gold Rulo Etiket",
        "label_text": "Aleyna & Özcan",
        "name_cut_text": "Aleyna & Özcan",
        "date_text": "31.05.2026",
        "note_text": "Tül seçimi siyah olacak.",
        "quantity": 1,
        "warnings": [],
    }
    trendyol_api.save_suggestions(tmp_path, [row])

    result = trendyol_api.verify_suggestion(
        tmp_path,
        "LEARN-1",
        {
            "label_required": True,
            "name_cut_required": True,
            "label_text": "Aleyna & Özcan",
            "name_cut_text": "Aleyna & Özcan",
            "date_text": "31.05.2026",
            "note_text": "Tül seçimi siyah olacak.",
            "model_path": "templates/designs/01_a_gold.json",
        },
    )

    assert result["status"] == "OK"
    payload = json.loads(trendyol_ai_extractor.learning_examples_path(tmp_path).read_text(encoding="utf-8"))
    examples = payload["examples"]
    assert examples[-1]["result"]["personNames"] == ["Aleyna", "Özcan"]
    assert examples[-1]["result"]["labelName"] == "Aleyna & Özcan"
    assert result["suggestion"]["learning_example_id"] == examples[-1]["id"]


def test_trendyol_learning_examples_are_included_in_ai_prompt(tmp_path: Path, monkeypatch) -> None:
    trendyol_ai_extractor.record_learning_example(
        tmp_path,
        {"question_text": "isimler: Aleyna ve Özcan İsteme tarihi: 31.05.2026 Tül seçimimiz: siyah"},
        {
            "person_names": ["Aleyna", "Özcan"],
            "label_text": "Aleyna & Özcan",
            "name_cut_text": "Aleyna & Özcan",
            "date_text": "31.05.2026",
            "production_note": "Tül seçimi siyah olacak.",
        },
    )
    seen = {"prompt": ""}

    def fake_post_json(url, headers, payload, timeout):
        seen["prompt"] = json.dumps(payload, ensure_ascii=False)
        return {
            "output_text": json.dumps(
                {
                    "personNames": ["Aleyna", "Özcan"],
                    "labelName": "Aleyna & Özcan",
                    "laserName": "Aleyna & Özcan",
                    "eventDate": "31.05.2026",
                    "productionNote": "Tül seçimi siyah olacak.",
                    "quantity": 1,
                    "confidence": 93,
                    "fieldConfidence": {"personNames": 94, "labelName": 94, "laserName": 94, "eventDate": 90, "productionNote": 85, "quantity": 90},
                    "sources": {"personNames": "isimler: aleyna ve Özcan", "quantity": "sipariş satırından"},
                    "warnings": [],
                },
                ensure_ascii=False,
            )
        }

    monkeypatch.setattr(trendyol_ai_extractor, "_post_json", fake_post_json)
    result = trendyol_ai_extractor.extract_with_ai_or_fallback(
        tmp_path,
        {"question_text": "#11245257456 isimler: aleyna ve Özcan İsteme tarihi: 31.05.2026 Tül seçimimiz: siyah", "quantity": 1},
        {"production_type": "label_and_name_cut"},
        {"quantity": 1},
        {"ai_enabled": True, "ai_api_key": "test-key", "ai_model": "test-model", "ai_cache_enabled": False},
    )

    assert result["label_text"] == "Aleyna & Özcan"
    assert "Benzer kullanıcı onaylı doğru örnekler" in seen["prompt"]
    assert "Aleyna & Özcan" in seen["prompt"]


def test_trendyol_question_context_stores_evidence_without_rule_name_preview(tmp_path: Path) -> None:
    question = trendyol_api._normalize_question_context(
        tmp_path,
        {
            "id": "Q-COLOR-ONLY",
            "orderNumber": "11242658230",
            "text": "Merhaba, 6 tane sipariş verdim. Sipariş numarası 11242658230. Hepsi BEYAZ olsun istiyorum. Teşekkür ederim.",
            "productName": "3 Adet Kızisteme Söz Nişan Anne Baldız Gülü",
        },
    )
    question_with_custom_text = trendyol_api._normalize_question_context(
        tmp_path,
        {
            "id": "Q-HATIRA",
            "orderNumber": "11242760731",
            "text": "#11242760731 nolu sipariş çikolataların üzerine yazılacak tarih 30.05.2026 nişan hatırası yazılacak isimler Derya ve M.Şerif",
            "productName": "Kişiye Özel Çikolata",
        },
    )

    assert question["question_text"].startswith("Merhaba")
    assert question["label_text"] == ""
    assert question["name_cut_text"] == ""
    assert question["date_text"] == ""
    assert question["note_text"] == ""
    assert question["evidence_spans"] == {}
    assert question_with_custom_text["label_text"] == ""
    assert question_with_custom_text["name_cut_text"] == ""


def test_trendyol_order_sync_enriches_missing_order_image_from_catalog(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(
        tmp_path,
        {
            "supplier_id": "123",
            "api_key": "key",
            "api_secret": "secret",
            "environment": "live",
        },
    )
    order = _sample_order("TY-CATALOG-IMAGE")
    order["lines"][0].pop("images", None)
    catalog = [
        {
            "title": "01 A Gold Rulo Etiket",
            "barcode": "TY-CATALOG-IMAGE",
            "stockCode": "SKU-CATALOG-IMAGE",
            "images": [{"url": "https://cdn.example.test/catalog-image.png"}],
            "productUrl": "https://www.trendyol.com/urun",
        }
    ]

    monkeypatch.setattr(trendyol_api, "fetch_orders", lambda project_root, start, end: [order])
    monkeypatch.setattr(trendyol_api, "fetch_products", lambda project_root, max_pages=10, page_size=200: catalog)

    result = trendyol_api.sync_recent_orders(tmp_path, days=2)
    row = result["suggestions"][0]

    assert result["status"] == "OK"
    assert row["image_url"] == "https://cdn.example.test/catalog-image.png"
    assert row["product_url"] == "https://www.trendyol.com/urun"


def test_trendyol_existing_suggestions_use_cached_catalog_image(tmp_path: Path) -> None:
    cached_catalog = [
        {
            "product_name": "Gold Çerçeveli Cam Sunumluk Kapaklı Sandık 25x15cm CYZOHMELKJK612",
            "barcode": "CYZOHMELKJK612",
            "image_url": "https://cdn.example.test/cached-catalog.png",
            "product_url": "https://www.trendyol.com/cached",
        }
    ]
    existing_suggestion = {
        "id": "row-1",
        "order_number": "TY-CACHED",
        "package_id": "PKG-CACHED",
        "line_id": "LINE-CACHED",
        "customer_name": "Ayşe Şahin",
        "product_name": "Gold Çerçeveli Cam Sunumluk Kapaklı Sandık 25x15cm CYZOHMELKJK612, one size",
        "barcode": "CYZOHMELKJK612",
        "merchant_sku": "merchantSku",
        "stock_code": "merchantSku",
        "status": "review",
    }
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "trendyol_mapping_suggestions.json").write_text(json.dumps(cached_catalog, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "data" / "trendyol_production_suggestions.json").write_text(json.dumps([existing_suggestion], ensure_ascii=False), encoding="utf-8")

    row = trendyol_api.list_suggestions(tmp_path)[0]

    assert row["image_url"] == "https://cdn.example.test/cached-catalog.png"
    assert row["product_url"] == "https://www.trendyol.com/cached"


def test_trendyol_fuzzy_catalog_match_does_not_copy_product_url(tmp_path: Path) -> None:
    cached_catalog = [
        {
            "product_name": "Gold Çerçeveli Cam Sunumluk Kapaklı Sandık 25x15cm CYZOHMELKJK612",
            "barcode": "DIFFERENT-BARCODE",
            "image_url": "https://cdn.example.test/fuzzy-catalog.png",
            "product_url": "https://www.trendyol.com/wrong-product",
        }
    ]
    existing_suggestion = {
        "id": "row-1",
        "order_number": "TY-FUZZY",
        "package_id": "PKG-FUZZY",
        "line_id": "LINE-FUZZY",
        "customer_name": "Ayşe Şahin",
        "product_name": "Gold Çerçeveli Cam Sunumluk Kapaklı Sandık 25x15cm CYZOHMELKJK612, one size",
        "barcode": "UNMATCHED-BARCODE",
        "merchant_sku": "merchantSku",
        "stock_code": "merchantSku",
        "status": "review",
    }
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "trendyol_mapping_suggestions.json").write_text(json.dumps(cached_catalog, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "data" / "trendyol_production_suggestions.json").write_text(json.dumps([existing_suggestion], ensure_ascii=False), encoding="utf-8")

    row = trendyol_api.list_suggestions(tmp_path)[0]

    assert row["image_url"] == "https://cdn.example.test/fuzzy-catalog.png"
    assert row["image_url_source"] == "catalog_name"
    assert row.get("product_url", "") == ""
    assert row.get("product_url_source", "") == ""


def test_trendyol_product_image_cache_returns_file_url(tmp_path: Path, monkeypatch) -> None:
    class _FakeHeaders:
        def get(self, key, default=None):
            return "image/jpeg" if key == "Content-Type" else default

    class _FakeResponse:
        headers = _FakeHeaders()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"\xff\xd8" + (b"fake-jpeg-bytes" * 20) + b"\xff\xd9"

    def fake_urlopen(request, timeout=20):
        assert "trendyol.com" in request.headers.get("Referer", "")
        return _FakeResponse()

    monkeypatch.setattr(trendyol_api.urllib.request, "urlopen", fake_urlopen)

    result = trendyol_api.cache_product_image(tmp_path, "https://cdn.dsmcdn.com/ty1/prod/item/1_org_zoom.jpg")

    assert result["status"] == "OK"
    assert result["preview_url"].startswith("file:///")
    cached_path = Path(result["cached_path"])
    assert cached_path.exists()
    assert cached_path.parent.name == "trendyol_image_cache"


def test_trendyol_unmatched_barcode_requires_review(tmp_path: Path) -> None:
    suggestions = trendyol_api.build_suggestions_from_orders(tmp_path, [_sample_order("UNKNOWN-BARCODE")])

    assert suggestions[0]["status"] == "review"
    assert suggestions[0]["mapping_found"] is False
    assert any("eşleştirmesi" in warning.lower() for warning in suggestions[0]["warnings"])


def test_trendyol_ai_autonomous_mode_can_prepare_high_confidence_order_without_saved_mapping(tmp_path: Path) -> None:
    order = _sample_order("UNKNOWN-AI")
    label_models = [
        {
            "model_no": "01",
            "template_no": "A",
            "model_name": "01 A Gold Rulo Etiket",
            "path": "templates/designs/01_a_gold.json",
        }
    ]

    suggestions = trendyol_api.build_suggestions_from_orders(tmp_path, [order], label_models=label_models)
    row = suggestions[0]

    assert row["status"] == "review"
    assert row["verification_status"] == "kanit_bekliyor"
    assert row["user_verified"] is False
    assert row["ai_autonomous"] is True
    assert row["mapping_source"] == "ai_autonomous"
    assert row["model_path"] == "templates/designs/01_a_gold.json"
    assert row["label_text"] == ""
    assert any("soru/mesaj" in warning.lower() for warning in row["warnings"])
    assert trendyol_mapping_api.list_product_mappings(tmp_path) == []


def test_trendyol_repairs_mojibake_and_flags_low_confidence_review(tmp_path: Path) -> None:
    orders = [
        {
            "orderNumber": "TY-MOJI",
            "shipmentPackageId": "PKG-MOJI",
            "customerName": "ebubekir gÃ¶rdegir",
            "lines": [
                {
                    "id": "LINE-MOJI",
                    "productName": "KiÅŸiye Ã–zel Nisan Etiketi not: Nisan Hatirasi",
                    "barcode": "UNKNOWN-MOJI",
                    "merchantSku": "SKU-MOJI",
                    "quantity": 1,
                }
            ],
        }
    ]

    suggestions = trendyol_api.build_suggestions_from_orders(tmp_path, orders)
    row = suggestions[0]

    assert row["status"] == "review"
    assert row["customer_name"] == "Ebubekir Gördegir"
    assert "Ã" not in row["product_name"]
    assert "Å" not in row["product_name"]
    assert any("düşük güven" in warning.lower() for warning in row["warnings"])


def test_trendyol_ready_suggestion_imports_once_to_customer_order(tmp_path: Path) -> None:
    _save_sample_question(tmp_path)
    trendyol_mapping_api.upsert_product_mapping(
        tmp_path,
        {
            "barcode": "TY-ETIKET-01",
            "production_type": "label",
            "model_path": "templates/designs/01_a_gold.json",
            "model_name": "01 A Gold Rulo Etiket",
        },
    )
    suggestions = trendyol_api.build_suggestions_from_orders(tmp_path, [_sample_order()])
    trendyol_api.save_suggestions(tmp_path, suggestions)
    verified = trendyol_api.verify_suggestion(
        tmp_path,
        suggestions[0]["id"],
        {
            "label_required": True,
            "name_cut_required": False,
            "label_text": suggestions[0]["label_text"],
            "date_text": suggestions[0]["date_text"],
            "note_text": suggestions[0]["note_text"],
            "model_path": suggestions[0]["model_path"],
        },
    )
    assert verified["status"] == "OK"

    first = trendyol_api.import_suggestion_to_customer_order(tmp_path, suggestions[0]["id"])
    second = trendyol_api.import_suggestion_to_customer_order(tmp_path, suggestions[0]["id"])

    assert first["status"] == "OK"
    assert second["status"] == "DUPLICATE"
    orders = customer_order_api.list_customer_orders(tmp_path)
    assert len(orders) == 1
    assert orders[0]["source"] == "trendyol"
    assert orders[0]["trendyol_order_number"] == "TY123"
    assert orders[0]["trendyol_line_id"] == "LINE1"
    assert "explicit_name_pattern" in orders[0]["trendyol_source_evidence"]


def test_trendyol_ready_suggestions_export_to_bulk_excel(tmp_path: Path) -> None:
    _save_sample_question(tmp_path)
    trendyol_mapping_api.upsert_product_mapping(
        tmp_path,
        {
            "barcode": "TY-ETIKET-01",
            "production_type": "label_and_name_cut",
            "model_key": "01",
            "model_path": "templates/designs/01_a_gold.json",
            "model_name": "01 A Gold Rulo Etiket",
        },
    )
    suggestions = trendyol_api.build_suggestions_from_orders(tmp_path, [_sample_order()])
    trendyol_api.save_suggestions(tmp_path, suggestions)
    verified = trendyol_api.verify_suggestion(
        tmp_path,
        suggestions[0]["id"],
        {
            "label_required": True,
            "name_cut_required": True,
            "label_text": suggestions[0]["label_text"],
            "name_cut_text": suggestions[0]["name_cut_text"],
            "date_text": suggestions[0]["date_text"],
            "note_text": suggestions[0]["note_text"],
            "model_path": suggestions[0]["model_path"],
        },
    )
    assert verified["status"] == "OK"

    result = trendyol_api.export_ready_suggestions_to_excel(tmp_path)

    assert result["status"] == "OK"
    assert (tmp_path / result["relative_path"]).exists()
    assert (tmp_path / result["manifest_path"]).exists()
    frame = pd.read_excel(tmp_path / result["relative_path"])
    assert "trendyol_soru" in frame.columns
    assert "ai_kanit" in frame.columns
    assert "trendyol_dogrulama_durumu" in frame.columns
    assert "ai_kaynak_label_text" in frame.columns
    assert frame.iloc[0]["ai_guven"] >= 0.7
    saved = trendyol_api.list_suggestions(tmp_path)
    assert saved[0]["import_status"] == "production_excel"
    assert saved[0]["production_excel_path"] == result["relative_path"]


def test_trendyol_fetch_orders_uses_v2_packages_with_v1_enrichment(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, bool]] = []

    def fake_fetch_json(project_root: Path, path: str, *, v2: bool, timeout: int | None = None) -> dict[str, object]:
        calls.append((path, v2))
        if "/integration/ecgw/v2/" in path and "/packages/items" not in path:
            return {
                "items": [
                    {
                        "packageId": 777,
                        "trackingNumber": "TRK777",
                        "status": "new",
                        "totalBuyingPrice": 120,
                        "creationDate": 1770000000000,
                        "cargos": [{"codes": ["CARGO777"], "provider": "TY Express"}],
                    }
                ]
            }
        if "/integration/ecgw/v2/" in path and "/packages/items" in path:
            return {
                "items": [
                    {
                        "itemId": 55,
                        "name": "Kisiye Ozel Etiket isim: Sedef Sefer not: Nisan 15.05.2026",
                        "barcode": "TY-ETIKET-01",
                        "sellerBarcode": "SKU-01",
                        "newQuantity": 2,
                        "unitBuyingPrice": 60,
                    }
                ]
            }
        if "/order/sellers/" in path:
            return {
                "content": [
                    {
                        "orderNumber": "TY-V1-777",
                        "shipmentPackageId": 777,
                        "customerFirstName": "Sedef",
                        "customerLastName": "Sefer",
                        "shipmentAddress": {"city": "Istanbul"},
                        "lines": [],
                    }
                ]
            }
        raise AssertionError(path)

    monkeypatch.setattr(trendyol_api, "_fetch_json", fake_fetch_json)
    orders = trendyol_api.fetch_orders(tmp_path, pd.Timestamp("2026-05-01").to_pydatetime(), pd.Timestamp("2026-05-02").to_pydatetime())

    assert orders[0]["source_api"] == "v2_packages_with_v1_enrichment"
    assert orders[0]["orderNumber"] == "TY-V1-777"
    assert orders[0]["customerName"] == "Sedef Sefer"
    assert orders[0]["lines"][0]["barcode"] == "TY-ETIKET-01"
    assert orders[0]["lines"][0]["quantity"] == 2
    assert any(v2 for _, v2 in calls)
    assert any("packages?" in path and "page=1" in path for path, v2 in calls if v2)
    assert any("packages/items" in path and "page=1" in path for path, v2 in calls if v2)


def test_trendyol_questions_are_read_only_context(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(
        tmp_path,
        {
            "supplier_id": "123",
            "api_key": "key",
            "api_secret": "secret",
            "environment": "live",
        },
    )

    seen_calls: list[str] = []

    def fake_fetch_json(project_root: Path, path: str, *, v2: bool, timeout: int | None = None) -> dict[str, object]:
        assert "/qna/sellers/123/questions/filter" in path
        assert "orderByField=LastModifiedDate" in path
        assert "orderByDirection=DESC" in path
        if "status=" in path:
            assert "WAITING_FOR_ANSWER" in path or "ANSWERED" in path
        assert v2 is False
        seen_calls.append(path)
        return {
            "content": [
                {
                    "id": 12,
                    "productName": "Kisiye Ozel Etiket",
                    "barcode": "TY-ETIKET-01",
                    "text": "isim: Ayse Omer tarih 15.05.2026",
                    "answered": False,
                },
                {
                    "id": 13,
                    "productName": "Kisiye Ozel Etiket",
                    "barcode": "TY-ETIKET-01",
                    "text": "isim: Sedef Sefer",
                    "answer": {"text": "Tamamdır."},
                }
            ]
        }

    monkeypatch.setattr(trendyol_api, "_fetch_json", fake_fetch_json)
    rows = trendyol_api.fetch_questions(tmp_path)
    synced = trendyol_api.sync_questions(tmp_path)
    stored = trendyol_api.list_questions(tmp_path)

    assert len(rows) == 2
    assert rows[0]["id"] == 12
    assert synced["status"] == "OK"
    assert len(stored) == 2
    assert seen_calls
    stored_by_id = {row["id"]: row for row in stored}
    assert stored_by_id["12"]["barcode"] == "TY-ETIKET-01"
    assert stored_by_id["12"]["question_text"] == "isim: Ayse Omer tarih 15.05.2026"
    assert stored_by_id["12"]["label_text"] == ""
    assert stored_by_id["12"]["name_cut_text"] == ""
    assert stored_by_id["12"]["evidence_spans"] == {}
    assert stored_by_id["13"]["question_text"] == "isim: Sedef Sefer"
    assert len([path for path in seen_calls if "status=" in path]) >= 2
    settings = trendyol_api.get_settings(tmp_path, masked=False)
    assert settings["last_questions_sync_status"] == "OK"


def test_trendyol_question_phrase_extracts_name_from_order_number_text() -> None:
    from intelligence.trendyol_order_extractor import extract_production_fields

    result = extract_production_fields(
        {
            "question_text": "3248924141 sipariş numaralı ürünüme ayse ali yazılsın",
            "quantity": 1,
        },
        {"production_type": "label_and_name_cut"},
    )

    assert result["label_text"] == "Ayşe Ali"
    assert result["name_cut_text"] == "Ayşe Ali"
    assert result["field_sources"]["label_text"] == "question_text"


def test_trendyol_question_ignores_seller_boilerplate_answer_for_name() -> None:
    from intelligence.trendyol_order_extractor import extract_production_fields

    result = extract_production_fields(
        {
            "question_text": "11243047993 sipariş no çiçeğin üzerinde Emine Emircan çikolata Emine Emircan Allah'ın emri yazısı",
            "answer_text": "Tamamdır efendim. TEDARİK VEYA DEĞİŞİM YAPILMAKTADIR.",
            "quantity": 1,
        },
        {},
    )

    assert result["label_text"] == "Emine Emircan"
    assert result["name_cut_text"] == "Emine Emircan"
    assert "Tedarik" not in result["label_text"]


def test_trendyol_question_trims_request_words_from_name() -> None:
    from intelligence.trendyol_order_extractor import extract_production_fields

    result = extract_production_fields(
        {
            "question_text": "11243461810 Selin & Hakan yazılmasını rica ediyorum 07.06.2026",
            "quantity": 1,
        },
        {},
    )

    assert result["label_text"] == "Selin & Hakan"
    assert result["name_cut_text"] == "Selin & Hakan"
    assert result["date_text"] == "07.06.2026"


def test_trendyol_question_trims_order_reference_and_yazilacak_suffix() -> None:
    from intelligence.trendyol_order_extractor import extract_production_fields

    result = extract_production_fields(
        {
            "question_text": "11242010676 nolu siparişe EMINE & MUSTAFA yazılacak",
            "quantity": 1,
        },
        {"production_type": "label_and_name_cut"},
    )

    assert result["label_text"] == "Emine & Mustafa"
    assert result["name_cut_text"] == "Emine & Mustafa"
    assert "Nolu" not in result["label_text"]
    assert "Yazılacak" not in result["label_text"]


def test_trendyol_question_normalizes_uppercase_dotted_i_names() -> None:
    from intelligence.trendyol_order_extractor import extract_production_fields

    result = extract_production_fields(
        {
            "question_text": "11242010676 nolu siparişe EMİNE & MUSTAFA yazılacak",
            "quantity": 1,
        },
        {"production_type": "label_and_name_cut"},
    )

    assert result["label_text"] == "Emine & Mustafa"
    assert result["name_cut_text"] == "Emine & Mustafa"
    assert "\u0307" not in result["label_text"]


def test_trendyol_question_extracts_names_inside_loose_sentences() -> None:
    from intelligence.trendyol_order_extractor import extract_production_fields

    cases = [
        ("Merhaba ürün üzerine Ayşe ve Mehmet yazılsın lütfen", "Ayşe & Mehmet", ""),
        ("isimler ayşe mehmet olacak tarih 12.06.2026", "Ayşe Mehmet", "12.06.2026"),
        ("Merhaba isim kısmına Zeynep - Burak yazabilir misiniz", "Zeynep & Burak", ""),
        ("Üzerine Elif Kerem yazılacak görseldeki gibi", "Elif Kerem", ""),
        ("Çiçeğin üzerine Fatma Ahmet yazılmasını istiyorum", "Fatma Ahmet", ""),
        ("Nikah tarihimiz 20.08.2026 isimler Sude Can yazılsın", "Sude Can", "20.08.2026"),
        ("Bahar ♡ Yunus ürün görseldeki aynı olacak", "Bahar & Yunus", ""),
        ("#11240585004 nolu sipariş isimler Esra Nur & Yunus Emre olacak", "Esra Nur & Yunus Emre", ""),
        ("10471684817 önce Bahar sonra Faysal yazabilir misiniz", "Bahar & Faysal", ""),
        ("#11243696200 İKBAL. ALİ yazacak üstünde", "İkbal Ali", ""),
    ]

    for question, expected_name, expected_date in cases:
        result = extract_production_fields(
            {"question_text": question, "quantity": 1},
            {"production_type": "label_and_name_cut"},
        )
        assert result["label_text"] == expected_name
        assert result["name_cut_text"] == expected_name
        assert result["date_text"] == expected_date


def test_trendyol_personalization_parser_blocks_visual_instruction_as_name() -> None:
    from intelligence.trendyol_order_extractor import extract_production_fields

    cases = [
        {
            "input": "Görseldekinin aynısı olsun tülü siyah şekilde üzerine elif sonsuzluk işareti Muhammed olacak şekilde yaparsanız sevinirim Allah’ın emri ile kızımızı istemeye geldik olacak çikolatalı tepsi",
            "label": "Elif ♾ Muhammed",
            "laser": "Elif ♾ Muhammed",
            "date": "",
            "note": "Görseldekinin aynısı isteniyor. Tülü siyah olacak. “Allah’ın emri ile kızımızı istemeye geldik” yazısı kullanılacak. Çikolatalı tepsi için uygulanacak.",
        },
        {
            "input": "Üzerine Ayşe ve Mehmet yazılsın tarih 12.05.2026 olsun",
            "label": "Ayşe & Mehmet",
            "laser": "Ayşe & Mehmet",
            "date": "12.05.2026",
        },
        {
            "input": "Görseldeki gibi olsun sadece tülü beyaz yapalım",
            "label": "",
            "laser": "",
            "date": "",
        },
        {
            "input": "Etikette Zeynep Emir yazsın 15 Mayıs 2026 tarihli olsun",
            "label": "Zeynep & Emir",
            "laser": "Zeynep & Emir",
            "date": "15 Mayıs 2026",
        },
        {
            "input": "Allah’ın emri ile kızımızı istemeye geldik yazısı olsun",
            "label": "",
            "laser": "",
            "date": "",
        },
    ]

    for case in cases:
        result = extract_production_fields(
            {"question_text": case["input"], "quantity": 1},
            {"production_type": "label_and_name_cut"},
        )
        assert result["label_text"] == case["label"]
        assert result["name_cut_text"] == case["laser"]
        assert result["date_text"] == case["date"]
        assert result["quantity"] == 1
        if case.get("note"):
            assert result["note_text"] == case["note"]
            assert result["confidence"] >= 0.85
            assert result["field_sources"]["note_text"] == "question_text"
        assert "Görseldekinin Aynısı" not in result["label_text"]


def test_trendyol_cloud_ai_sanitizer_keeps_turkish_names_and_heart_separator(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(tmp_path, {"ai_enabled": True, "ai_api_key": "should-not-leak", "ai_model": "test-model", "ai_cache_enabled": False})

    def fake_post_json(url, headers, payload, timeout):
        return {
            "output_text": json.dumps(
                {
                    "labelName": "Ayşe & Mehmet",
                    "laserName": "Ayşe & Mehmet",
                    "confidence": 91,
                    "fieldConfidence": {"labelName": 94, "laserName": 94, "date": 0, "note": 0, "quantity": 90},
                    "sources": {"labelName": "Ayşe ♡ Mehmet", "laserName": "Ayşe ♡ Mehmet", "quantity": "sipariş satırından"},
                    "warnings": [],
                },
                ensure_ascii=False,
            )
        }

    monkeypatch.setattr(trendyol_ai_extractor, "_post_json", fake_post_json)
    result = trendyol_ai_extractor.extract_with_ai_or_fallback(
        tmp_path,
        {"question_text": "Ayşe ♡ Mehmet ürün görseldeki aynı olacak", "quantity": 1},
        {"production_type": "label_and_name_cut"},
        {"quantity": 1, "warnings": [], "source_evidence": [], "field_sources": {}},
    )

    assert result["label_text"] == "Ayşe & Mehmet"
    assert result["name_cut_text"] == "Ayşe & Mehmet"
    assert result["field_confidence"]["labelName"] == 94


def test_trendyol_cloud_ai_is_source_of_truth_for_elvida_omer(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(tmp_path, {"ai_enabled": True, "ai_api_key": "should-not-leak", "ai_model": "test-model", "ai_cache_enabled": False})

    def fake_post_json(url, headers, payload, timeout):
        prompt = json.dumps(payload, ensure_ascii=False)
        assert "elvida ömer olacak isimler" in prompt
        assert "Ürün başlığı" in prompt
        return {
            "output_text": json.dumps(
                {
                    "labelName": "Elvida & Ömer",
                    "laserName": "Elvida & Ömer",
                    "date": None,
                    "note": None,
                    "quantity": 1,
                    "confidence": 92,
                    "fieldConfidence": {"labelName": 94, "laserName": 94, "date": 0, "note": 0, "quantity": 90},
                    "sources": {
                        "labelName": "elvida ömer",
                        "laserName": "elvida ömer",
                        "date": None,
                        "note": None,
                        "quantity": "sipariş satırından",
                    },
                    "warnings": ["Tarih müşteri mesajında bulunamadı."],
                },
                ensure_ascii=False,
            )
        }

    monkeypatch.setattr(trendyol_ai_extractor, "_post_json", fake_post_json)
    result = trendyol_ai_extractor.extract_with_ai_or_fallback(
        tmp_path,
        {
            "question_text": "elvida ömer olacak isimler",
            "product_name": "41’li Kızisteme Çiçeği ve 150 Adet Söz Çikolatası",
            "barcode": "cyzella793574937",
            "merchant_sku": "cyzelaI8034578037405",
            "quantity": 1,
        },
        {"production_type": "label_and_name_cut"},
        {
            "label_text": "Elvida Ömer Olacak İsimler",
            "name_cut_text": "Elvida Ömer Olacak İsimler",
            "quantity": 1,
            "confidence": 0.88,
            "warnings": [],
            "source_evidence": ["ai_text_extract"],
            "field_sources": {"label_text": "question_text", "name_cut_text": "question_text"},
        },
    )

    assert result["label_text"] == "Elvida & Ömer"
    assert result["name_cut_text"] == "Elvida & Ömer"
    assert result["date_text"] == ""
    assert result["note_text"] == ""
    assert result["quantity"] == 1
    assert result["confidence"] == 0.92
    assert result["field_confidence"]["labelName"] == 94
    assert result["evidence_spans"]["label_text"] == "elvida ömer"
    assert "Olacak İsimler" not in result["label_text"]


def test_trendyol_cloud_ai_extracts_names_date_custom_text_and_production_note(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(tmp_path, {"ai_enabled": True, "ai_api_key": "should-not-leak", "ai_model": "test-model", "ai_cache_enabled": False})
    message = (
        "#11242760731 nolu sipariş çikolataların üzerine yazılacak tarih 30.05.2026 "
        "nişan hatırası yazılacak isimler Derya ve M.Şerif lütfen ürünü doğru eksiksiz "
        "bir şekilde teslimatını yapın teslim etmeden önce ürünün fotoğrafını mesaj yoluyla "
        "bana atar mısınız elinize emeğinize sağlık"
    )

    def fake_post_json(url, headers, payload, timeout):
        prompt = json.dumps(payload, ensure_ascii=False)
        assert message in prompt
        assert "Ürün başlığı" in prompt
        return {
            "output_text": json.dumps(
                {
                    "personNames": ["Derya", "M. Şerif"],
                    "labelName": "Derya & M. Şerif",
                    "laserName": "Derya & M. Şerif",
                    "eventDate": "30.05.2026",
                    "customText": "Nişan hatırası",
                    "productionNote": "Çikolataların üzerine tarih ve “Nişan hatırası” yazılacak. Teslim etmeden önce ürün fotoğrafı mesaj yoluyla gönderilmeli.",
                    "quantity": 1,
                    "confidence": 93,
                    "fieldConfidence": {
                        "personNames": 96,
                        "labelName": 95,
                        "laserName": 95,
                        "eventDate": 94,
                        "customText": 90,
                        "productionNote": 90,
                        "quantity": 90,
                    },
                    "sources": {
                        "personNames": "isimler Derya ve M.Şerif",
                        "labelName": "isimler Derya ve M.Şerif",
                        "laserName": "isimler Derya ve M.Şerif",
                        "eventDate": "tarih 30.05.2026",
                        "customText": "nişan hatırası",
                        "productionNote": "çikolataların üzerine yazılacak / teslim etmeden önce ürünün fotoğrafını mesaj yoluyla bana atar mısınız",
                        "quantity": "sipariş satırından",
                    },
                    "warnings": [],
                },
                ensure_ascii=False,
            )
        }

    monkeypatch.setattr(trendyol_ai_extractor, "_post_json", fake_post_json)
    result = trendyol_ai_extractor.extract_with_ai_or_fallback(
        tmp_path,
        {
            "question_text": message,
            "product_name": "41 Karışık Şakayık İsteme Çiçeği Buketi & Kişiye Özel 100 Adet Isimli Söz Nişan Kız Isteme Çikolatası",
            "quantity": 1,
        },
        {"production_type": "label_and_name_cut"},
        {
            "label_text": "Hatırası",
            "name_cut_text": "Hatırası",
            "date_text": "30.05.2026",
            "quantity": 1,
            "confidence": 0.87,
            "warnings": [],
            "source_evidence": ["ai_text_extract"],
            "field_sources": {"label_text": "question_text", "name_cut_text": "question_text", "date_text": "question_text"},
        },
    )

    assert result["person_names"] == ["Derya", "M. Şerif"]
    assert result["label_text"] == "Derya & M. Şerif"
    assert result["name_cut_text"] == "Derya & M. Şerif"
    assert result["date_text"] == "30.05.2026"
    assert result["custom_text"] == "Nişan hatırası"
    assert result["production_note"] == "Çikolataların üzerine tarih ve “Nişan hatırası” yazılacak. Teslim etmeden önce ürün fotoğrafı mesaj yoluyla gönderilmeli."
    assert result["note_text"] == result["production_note"]
    assert result["field_confidence"]["personNames"] == 96
    assert "Hatırası" not in result["label_text"]


def test_trendyol_cloud_ai_keeps_name_empty_for_color_only_instruction(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(tmp_path, {"ai_enabled": True, "ai_api_key": "should-not-leak", "ai_model": "test-model", "ai_cache_enabled": False})
    message = "Merhaba, 6 tane sipariş verdim. Sipariş numarası 11242658230. Hepsi BEYAZ olsun istiyorum. Teşekkür ederim."

    def fake_post_json(url, headers, payload, timeout):
        prompt = json.dumps(payload, ensure_ascii=False)
        assert message in prompt
        return {
            "output_text": json.dumps(
                {
                    "containsPersonName": False,
                    "containsDate": False,
                    "containsCustomText": False,
                    "containsProductionInstruction": True,
                    "personNames": None,
                    "labelName": "Hepsi Beyaz",
                    "laserName": "Hepsi Beyaz",
                    "eventDate": None,
                    "customText": None,
                    "productionNote": "Hepsi beyaz olacak.",
                    "quantity": None,
                    "confidence": 70,
                    "fieldConfidence": {
                        "personNames": 60,
                        "labelName": 60,
                        "laserName": 60,
                        "eventDate": 0,
                        "customText": 0,
                        "productionNote": 90,
                        "quantity": 50,
                    },
                    "sources": {
                        "labelName": "Hepsi BEYAZ",
                        "laserName": "Hepsi BEYAZ",
                        "productionNote": "Hepsi BEYAZ olsun istiyorum.",
                        "quantity": "sipariş satırından",
                    },
                    "warnings": ["Müşteri mesajında kişi ismi bulunamadı."],
                },
                ensure_ascii=False,
            )
        }

    monkeypatch.setattr(trendyol_ai_extractor, "_post_json", fake_post_json)
    result = trendyol_ai_extractor.extract_with_ai_or_fallback(
        tmp_path,
        {
            "question_text": message,
            "product_name": "3 Adet Kızisteme Söz Nişan Anne Baldız Gülü 984357934675",
            "quantity": 2,
        },
        {"production_type": "label_and_name_cut"},
        {
            "label_text": "Hepsi Beyaz",
            "name_cut_text": "Hepsi Beyaz",
            "quantity": 2,
            "confidence": 0.88,
            "warnings": [],
            "source_evidence": ["ai_text_extract"],
            "field_sources": {"label_text": "question_text", "name_cut_text": "question_text"},
        },
    )

    assert result["person_names"] == []
    assert result["label_text"] == ""
    assert result["name_cut_text"] == ""
    assert result["date_text"] == ""
    assert result["custom_text"] == ""
    assert result["production_note"] == "Hepsi beyaz olacak."
    assert result["note_text"] == "Hepsi beyaz olacak."
    assert result["quantity"] == 2
    assert result["confidence"] <= 0.78
    assert result["needs_user_review"] is True
    assert result["field_confidence"]["personNames"] == 0
    assert result["field_confidence"]["labelName"] == 0
    assert result["field_confidence"]["laserName"] == 0
    assert result["field_confidence"]["quantity"] == 90
    assert result["field_sources"]["quantity"] == "order_line"
    assert any("kişi ismi bulunamadı" in warning.lower() for warning in result["warnings"])
    assert any("isim alanına aktarılmamalı" in warning.lower() for warning in result["warnings"])
    assert "Hepsi Beyaz" not in result["label_text"]
    assert "Hepsi Beyaz" not in result["name_cut_text"]


def test_trendyol_does_not_guess_name_without_question_or_answer() -> None:
    from intelligence.trendyol_order_extractor import extract_production_fields

    result = extract_production_fields(
        {
            "customer_name": "Hamide Kahraman",
            "product_name": "Kişiye Özel İki Katlı Sunumluk 80 Adet Söz Nişan Kız İsteme Çikolatası",
            "quantity": 1,
        },
        {"production_type": "label"},
    )

    assert result["label_text"] == ""
    assert result["name_cut_text"] == ""
    assert result["field_sources"]["label_text"] == "unknown"


def test_trendyol_cloud_ai_extracts_question_name_and_ignores_product_words(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(
        tmp_path,
        {
            "ai_enabled": True,
            "ai_api_key": "should-not-leak",
            "ai_model": "test-model",
            "ai_cache_enabled": False,
        },
    )
    trendyol_mapping_api.upsert_product_mapping(
        tmp_path,
        {
            "barcode": "TY-AI-01",
            "production_type": "label_and_name_cut",
            "model_path": "templates/designs/01_a_gold.json",
            "model_name": "01 A Gold Rulo Etiket",
        },
    )

    def fake_post_json(url, headers, payload, timeout):
        assert "should-not-leak" in headers["Authorization"]
        return {
            "output_text": json.dumps(
                {
                    "label_text": "Bahar & Yunus",
                    "name_cut_text": "Bahar Yunus",
                    "date_text": "",
                    "note_text": "",
                    "confidence": 0.93,
                    "field_sources": {
                        "label_text": "question_text",
                        "name_cut_text": "question_text",
                        "date_text": "empty",
                        "note_text": "empty",
                        "quantity": "order_line",
                    },
                    "evidence_spans": {"label_text": "Bahar ♡ Yunus"},
                    "warnings": [],
                    "needs_user_review": False,
                },
                ensure_ascii=False,
            )
        }

    monkeypatch.setattr(trendyol_ai_extractor, "_post_json", fake_post_json)
    question = trendyol_api._normalize_question_context(
        tmp_path,
        {
            "id": "Q-AI-01",
            "orderNumber": "TY123",
            "barcode": "TY-AI-01",
            "text": "Merhaba, sipariş no: TY123 Bahar ♡ Yunus ürün görseldeki aynı olacak detaylar gümüş renk olsun",
        },
    )
    trendyol_api._save_questions(tmp_path, [question])
    order = _sample_order("TY-AI-01")
    order["lines"][0]["productName"] = "41’li Kırmızı Kızisteme Çiçeği ve 80 Adet Söz Çikolatası"

    row = trendyol_api.build_suggestions_from_orders(tmp_path, [order])[0]

    assert row["label_text"] == "Bahar & Yunus"
    assert row["name_cut_text"] == "Bahar & Yunus"
    assert "Çiçeği" not in row["label_text"]
    assert row["verification_status"] == "alanlar_onay_bekliyor"
    assert row["user_verified"] is False
    assert row["needs_user_review"] is True
    assert "cloud_ai_extract" in row["source_evidence"]


def test_trendyol_cloud_ai_rejects_product_name_as_personalization_source(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(tmp_path, {"ai_enabled": True, "ai_api_key": "should-not-leak", "ai_model": "test-model", "ai_cache_enabled": False})

    def fake_post_json(url, headers, payload, timeout):
        return {
            "output_text": json.dumps(
                {
                    "label_text": "Çiçeği & Adet",
                    "name_cut_text": "Çiçeği Adet",
                    "confidence": 0.9,
                    "field_sources": {"label_text": "product_name", "name_cut_text": "product_name", "quantity": "order_line"},
                    "evidence_spans": {"label_text": "Çiçeği ve 80 Adet"},
                    "warnings": [],
                    "needs_user_review": False,
                },
                ensure_ascii=False,
            )
        }

    monkeypatch.setattr(trendyol_ai_extractor, "_post_json", fake_post_json)
    result = trendyol_ai_extractor.extract_with_ai_or_fallback(
        tmp_path,
        {"question_text": "Merhaba görseldeki gibi olsun", "product_name": "41’li Kırmızı Kızisteme Çiçeği ve 80 Adet Söz Çikolatası", "quantity": 1},
        {"production_type": "label_and_name_cut"},
        {"quantity": 1, "confidence": 0.4, "warnings": [], "source_evidence": [], "field_sources": {}},
    )

    assert result["label_text"] == ""
    assert result["name_cut_text"] == ""
    assert result["needs_user_review"] is True
    assert any("ürün" in warning.lower() for warning in result["warnings"])


def test_trendyol_cloud_ai_cache_reuses_question_without_second_call(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(tmp_path, {"ai_enabled": True, "ai_api_key": "should-not-leak", "ai_model": "test-model", "ai_cache_enabled": True})
    calls = {"count": 0}

    def fake_post_json(url, headers, payload, timeout):
        calls["count"] += 1
        return {
            "output_text": json.dumps(
                {
                    "label_text": "Emine & Mustafa",
                    "name_cut_text": "Emine Mustafa",
                    "confidence": 0.91,
                    "field_sources": {"label_text": "question_text", "name_cut_text": "question_text", "quantity": "order_line"},
                    "evidence_spans": {"label_text": "EMİNE & MUSTAFA"},
                    "warnings": [],
                    "needs_user_review": False,
                },
                ensure_ascii=False,
            )
        }

    monkeypatch.setattr(trendyol_ai_extractor, "_post_json", fake_post_json)
    source = {"question_text": "11242010676 nolu siparişe EMİNE & MUSTAFA yazılacak", "quantity": 1}
    first = trendyol_ai_extractor.extract_with_ai_or_fallback(tmp_path, source, {"production_type": "label"}, {"quantity": 1})
    second = trendyol_ai_extractor.extract_with_ai_or_fallback(tmp_path, source, {"production_type": "label"}, {"quantity": 1})

    assert first["label_text"] == "Emine & Mustafa"
    assert second["label_text"] == "Emine & Mustafa"
    assert calls["count"] == 1
    assert "cloud_ai_cache" in second["source_evidence"]


def test_trendyol_ai_secret_is_masked_and_not_leaked_on_failure(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(tmp_path, {"ai_enabled": True, "ai_api_key": "should-not-leak", "ai_model": "test-model"})
    masked = trendyol_api.get_settings(tmp_path, masked=True)
    assert masked["ai_api_key"] != "should-not-leak"
    assert masked["ai_configured"] is True

    def fake_post_json(url, headers, payload, timeout):
        raise RuntimeError("authorization bearer should-not-leak failed")

    monkeypatch.setattr(trendyol_ai_extractor, "_post_json", fake_post_json)
    result = trendyol_ai_extractor.extract_with_ai_or_fallback(
        tmp_path,
        {"question_text": "isim: Ayşe Ali", "quantity": 1},
        {},
        {"label_text": "Ayşe Ali", "quantity": 1, "warnings": [], "source_evidence": [], "field_sources": {"label_text": "question_text"}},
    )

    assert "should-not-leak" not in str(result)
    assert "rule_fallback_ai_error" in result["source_evidence"]


def test_trendyol_ai_error_fallback_does_not_publish_deterministic_name_guess(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(tmp_path, {"ai_enabled": True, "ai_api_key": "should-not-leak", "ai_model": "test-model", "ai_cache_enabled": False})

    def fake_post_json(url, headers, payload, timeout):
        raise TimeoutError("AI timeout")

    monkeypatch.setattr(trendyol_ai_extractor, "_post_json", fake_post_json)
    result = trendyol_ai_extractor.extract_with_ai_or_fallback(
        tmp_path,
        {
            "question_text": "Merhaba, 6 tane sipariş verdim. Sipariş numarası 11242658230. Hepsi BEYAZ olsun istiyorum.",
            "quantity": 2,
        },
        {"production_type": "label_and_name_cut"},
        {
            "label_text": "Hepsi Beyaz",
            "name_cut_text": "Hepsi Beyaz",
            "date_text": "",
            "quantity": 2,
            "confidence": 0.88,
            "warnings": [],
            "source_evidence": ["ai_text_extract"],
            "field_sources": {"label_text": "question_text", "name_cut_text": "question_text", "quantity": "order_line"},
            "evidence_spans": {"label_text": "Hepsi BEYAZ", "name_cut_text": "Hepsi BEYAZ"},
        },
    )

    assert "rule_fallback_ai_error" in result["source_evidence"]
    assert result["label_text"] == ""
    assert result["name_cut_text"] == ""
    assert result["person_names"] == []
    assert result["field_sources"]["label_text"] == "empty"
    assert result["field_sources"]["name_cut_text"] == "empty"
    assert result["field_confidence"]["labelName"] == 0
    assert result["field_confidence"]["laserName"] == 0
    assert result["quantity"] == 2
    assert result["needs_user_review"] is True
    assert any("manuel doğrulayın" in warning.lower() for warning in result["warnings"])


def test_trendyol_question_context_detects_order_number_for_matching(tmp_path: Path) -> None:
    question = trendyol_api._normalize_question_context(
        tmp_path,
        {
            "id": "Q-ORDER-NO",
            "status": "WaitingForAnswer",
            "text": "3248924141 sipariş numaralı ürünüme ayse ali yazılsın",
            "productName": "Kişiye Özel Etiket",
        },
    )
    index = trendyol_api._question_context_index([question])
    line = {
        "order_number": "3248924141",
        "product_name": "Kişiye Özel Etiket",
        "barcode": "",
        "merchant_sku": "",
    }
    attached = trendyol_api._attach_question_context(line, index)

    assert question["order_number"] == "3248924141"
    assert attached["question_contexts"][0]["question_text"].startswith("3248924141")
    assert attached["question_text"].startswith("3248924141")


def test_trendyol_question_context_does_not_auto_attach_product_only_question(tmp_path: Path) -> None:
    question = trendyol_api._normalize_question_context(
        tmp_path,
        {
            "id": "Q-PRODUCT-ONLY",
            "status": "WaitingForAnswer",
            "barcode": "TY-SAME-PRODUCT",
            "customerName": "Başka Müşteri",
            "text": "isim: Sedef Sefer yazılsın",
        },
    )
    index = trendyol_api._question_context_index([question])
    attached = trendyol_api._attach_question_context(
        {
            "order_number": "1122334455",
            "product_name": "Aynı ürün",
            "barcode": "TY-SAME-PRODUCT",
            "customer_name": "Farklı Müşteri",
        },
        index,
    )

    assert "question_contexts" not in attached


def test_trendyol_questions_service_unavailable_does_not_break_orders(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(
        tmp_path,
        {
            "supplier_id": "123",
            "api_key": "key",
            "api_secret": "secret",
            "environment": "live",
        },
    )

    def fake_fetch_questions(project_root: Path, status: str = "WaitingForAnswer") -> list[dict[str, object]]:
        raise RuntimeError('HTTP 556: {"message":"Service Unavailable","apiSecret":"should-not-leak"}')

    monkeypatch.setattr(trendyol_api, "fetch_questions", fake_fetch_questions)
    result = trendyol_api.sync_questions(tmp_path)

    assert result["status"] == "UNAVAILABLE"
    assert result["questions"] == []
    assert "sipariş" in result["message"].lower()
    assert "should-not-leak" not in str(result)
    assert "apiSecret" not in str(result)
    settings = trendyol_api.get_settings(tmp_path, masked=False)
    assert settings["last_questions_sync_status"] == "UNAVAILABLE"
    assert "should-not-leak" not in str(settings)
    assert "apiSecret" not in str(settings)


def test_trendyol_mapping_import_export_excel_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "mapping.xlsx"
    pd.DataFrame(
        [
            {
                "product_name": "Nisan Etiketi",
                "barcode": "TY-ETIKET-01",
                "merchant_sku": "SKU-01",
                "stock_code": "STOCK-01",
                "production_type": "label_and_name_cut",
                "model_key": "01",
                "model_path": "templates/designs/01_a_gold.json",
                "model_name": "01 A Gold Rulo Etiket",
                "name_cut_style": "Mochary Personal Use Only",
                "name_cut_width_mm": 300,
                "active": "evet",
            }
        ]
    ).to_excel(source, index=False)

    imported = trendyol_mapping_api.import_product_mappings_from_file(tmp_path, source)
    exported = trendyol_mapping_api.export_product_mappings_to_excel(tmp_path)
    rows = trendyol_mapping_api.list_product_mappings(tmp_path)

    assert imported["status"] == "OK"
    assert imported["imported"] == 1
    assert rows[0]["barcode"] == "TY-ETIKET-01"
    assert rows[0]["production_type"] == "label_and_name_cut"
    assert (tmp_path / exported["relative_path"]).exists()
    assert exported["row_count"] == 1


def test_trendyol_catalog_mapping_suggestions_require_user_approval(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(
        tmp_path,
        {
            "supplier_id": "123",
            "api_key": "key",
            "api_secret": "secret",
            "environment": "live",
        },
    )

    def fake_fetch_json(project_root: Path, path: str, *, v2: bool, timeout: int | None = None) -> dict[str, object]:
        assert "/product/sellers/123/products" in path
        assert v2 is False
        return {
            "content": [
                {
                    "title": "01 A Gold Rulo Etiket Lazer Isim Kesim",
                    "barcode": "TY-CATALOG-01",
                    "stockCode": "SKU-CATALOG-01",
                    "images": [{"url": "https://cdn.example.test/etiket.png"}],
                }
            ]
        }

    monkeypatch.setattr(trendyol_api, "_fetch_json", fake_fetch_json)
    label_models = [
        {
            "model_no": "01",
            "model_name": "01 A Gold Rulo Etiket",
            "path": "templates/designs/01_a_gold.json",
        }
    ]

    result = trendyol_api.propose_mapping_from_catalog(tmp_path, label_models, max_pages=1)
    saved_mappings_before_approval = trendyol_mapping_api.list_product_mappings(tmp_path)
    approved = trendyol_api.approve_mapping_suggestion(tmp_path, result["suggestions"][0]["id"])
    saved_mappings_after_approval = trendyol_mapping_api.list_product_mappings(tmp_path)

    assert result["status"] == "OK"
    assert result["product_count"] == 1
    assert result["suggestions"][0]["barcode"] == "TY-CATALOG-01"
    assert result["suggestions"][0]["production_type"] == "label_and_name_cut"
    assert result["suggestions"][0]["model_path"] == "templates/designs/01_a_gold.json"
    assert result["suggestions"][0]["image_url"] == "https://cdn.example.test/etiket.png"
    assert saved_mappings_before_approval == []
    assert approved["status"] == "OK"
    assert saved_mappings_after_approval[0]["barcode"] == "TY-CATALOG-01"
    assert saved_mappings_after_approval[0]["image_url"] == "https://cdn.example.test/etiket.png"


def test_trendyol_catalog_mapping_ignores_random_barcode_suffix_and_qa_models(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(
        tmp_path,
        {
            "supplier_id": "123",
            "api_key": "key",
            "api_secret": "secret",
            "environment": "live",
        },
    )

    def fake_fetch_json(project_root: Path, path: str, *, v2: bool, timeout: int | None = None) -> dict[str, object]:
        assert "/product/sellers/123/products" in path
        return {
            "content": [
                {
                    "title": "Kız Isteme Çikolatası, Söz, Nişan Çikolatası",
                    "barcode": "TYBMYE3QOO0GE7MX04",
                    "stockCode": "",
                }
            ]
        }

    monkeypatch.setattr(trendyol_api, "_fetch_json", fake_fetch_json)
    label_models = [
        {
            "model_no": "04",
            "model_name": "Final QA Kabul Modeli",
            "path": "templates/designs/04_a_qa.json",
        },
        {
            "model_no": "01",
            "model_name": "01 A Gold Rulo Etiket",
            "path": "templates/designs/01_a_gold.json",
        },
    ]

    result = trendyol_api.propose_mapping_from_catalog(tmp_path, label_models, max_pages=1)
    suggestion = result["suggestions"][0]

    assert suggestion["status"] == "needs_review"
    assert suggestion["production_type"] == "label"
    assert suggestion["model_path"] == ""
    assert any("model kullanıcı" in reason.lower() for reason in suggestion["reasons"])

    approved = trendyol_api.approve_mapping_suggestion(tmp_path, suggestion["id"])
    assert approved["status"] == "NEEDS_MODEL"
    assert trendyol_mapping_api.list_product_mappings(tmp_path) == []


def test_trendyol_name_cut_catalog_keyword_still_requires_model_or_mapping_review(tmp_path: Path, monkeypatch) -> None:
    trendyol_api.save_settings(
        tmp_path,
        {
            "supplier_id": "123",
            "api_key": "key",
            "api_secret": "secret",
            "environment": "live",
        },
    )

    def fake_fetch_json(project_root: Path, path: str, *, v2: bool, timeout: int | None = None) -> dict[str, object]:
        return {
            "content": [
                {
                    "title": "Pleksi lazer isim kesim kişiye özel dekor",
                    "barcode": "NAME-CUT-ONLY",
                    "stockCode": "NAME-CUT-ONLY",
                }
            ]
        }

    monkeypatch.setattr(trendyol_api, "_fetch_json", fake_fetch_json)

    result = trendyol_api.propose_mapping_from_catalog(tmp_path, [], max_pages=1)
    suggestion = result["suggestions"][0]

    assert suggestion["production_type"] == "name_cut"
    assert suggestion["status"] == "needs_review"
    assert trendyol_mapping_api.list_product_mappings(tmp_path) == []


def test_trendyol_ui_and_bridge_hooks_exist() -> None:
    html = (PROJECT_ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app_js = (PROJECT_ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    bridge = (PROJECT_ROOT / "src" / "webui_backend" / "bridge.py").read_text(encoding="utf-8")

    assert "trendyolOrders" in html
    assert "Trendyol Siparişleri" in html
    assert "trendyol-tabs" in html
    assert "trendyolTabOrders" in html
    assert "trendyolTabMapping" in html
    assert "trendyolTabQuestions" in html
    assert "trendyolTabApi" not in html
    assert "API Ayarları" not in html
    assert "Kontrol Kuyruğu" in html
    assert "Kanıt Eşleştirme" in html
    assert "trendyolTabHistory" in html
    assert "openTrendyolSidebarTab" in app_js
    assert 'data-trendyol-sidebar-tab="worklist"' in html
    assert "sidebarBadgeReview" in html
    assert 'data-settings-subpage="trendyol-api"' in html
    assert '<details class="nav-section technical-nav" hidden>' in html
    assert "setupSidebarLayout" in app_js
    assert "setupSidebarRailHover" not in app_js
    assert "trendyolSelectedDetail" in html
    assert "function updateTrendyolOrders" in app_js
    assert "function showTrendyolTab" in app_js
    assert "renderTrendyolSelectedDetail" in app_js
    assert "renderTrendyolQuickFilters" in app_js
    assert "importTrendyolSuggestionToCustomerOrder" in app_js
    # exportTrendyolReadyToExcel removed as dead code
    assert "importTrendyolMappings" in app_js
    assert "exportTrendyolMappings" in app_js
    assert "proposeTrendyolMappingsFromCatalog" in app_js
    assert "approveTrendyolMappingSuggestion" in app_js
    assert "syncTrendyolQuestions" in app_js
    assert "trendyolQuestionsList" in html
    assert "trendyolMappingSuggestionsList" in html
    assert "Eşleşmeyen ürünler" in html
    assert 'statusFilter === "unmatched"' in app_js
    assert 'value="low_confidence"' in html
    assert 'statusFilter === "low_confidence"' in app_js
    assert "low-confidence" in app_js
    assert "trendyolAiAutonomous" not in html
    assert "trendyolBulkActionBar" in html
    assert "trendyolEvidenceDrawer" in app_js
    assert "tsc-card" in app_js
    assert "trendyolMapImageUrl" in html
    assert "trendyolMappingImagePreview" in html
    assert "trendyolMappingSearch" in html
    assert "trendyolMappingTypeFilter" in html
    assert "trendyolMappingSuggestionStatusFilter" in html
    assert "clearTrendyolMappingSuggestionFilters" in app_js
    assert "Kaydet ve Siparişe Dön" in html
    assert "model seçilmemiş" in app_js
    assert "updateTrendyolMappingPreview" in app_js
    assert "cache_trendyol_product_image" in app_js
    assert "cache_trendyol_product_image" in bridge
    assert "#trendyolSuggestionsList .order-product-thumb-wrap" in app_js
    assert "trendyol-question-evidence" in app_js
    assert "Müşteri Soru / Mesaj Kanıtı" in app_js
    assert "Bu siparişe benzeyen müşteri soruları" in app_js
    assert "Soruları Oku" in app_js
    assert "Kanıt Eşleştirme tabını aç" in app_js
    assert "trendyolPotentialQuestionsForSuggestion" in app_js
    assert "Onayla ve Üretime Hazır Yap" in app_js
    assert "applyTrendyolQuestionToSuggestion" in app_js
    assert "ignoreTrendyolQuestionForSuggestion" in app_js
    assert "verifyTrendyolSuggestionFromDetail" in app_js
    assert "save_trendyol_settings" in bridge
    assert "sync_trendyol_recent_orders" in bridge
    assert "export_trendyol_ready_to_excel" in bridge
    assert "import_trendyol_mappings" in bridge
    assert "export_trendyol_mappings" in bridge
    assert "propose_trendyol_mappings_from_catalog" in bridge
    assert "approve_trendyol_mapping_suggestion" in bridge
    assert "sync_trendyol_questions" in bridge
    assert "verify_trendyol_suggestion" in bridge
    assert "apply_trendyol_question_to_suggestion" in bridge
    assert "ignore_trendyol_question_for_suggestion" in bridge

