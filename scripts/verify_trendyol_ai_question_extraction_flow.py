from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from intelligence import trendyol_ai_extractor
from webui_backend import trendyol_api, trendyol_mapping_api


def main() -> int:
    temp_root = Path(tempfile.mkdtemp(prefix="cyzella_trendyol_ai_"))
    try:
        _run(temp_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    print("OK: Trendyol bulut AI soru ayıklama akışı güvenli ve deterministik doğrulandı.")
    return 0


def _run(root: Path) -> None:
    trendyol_api.save_settings(
        root,
        {
            "ai_enabled": True,
            "ai_api_key": "verify-secret-should-not-leak",
            "ai_model": "test-model",
            "ai_cache_enabled": True,
            "ai_confidence_threshold": 0.85,
        },
    )
    trendyol_mapping_api.upsert_product_mapping(
        root,
        {
            "barcode": "TY-AI-FLOW",
            "merchant_sku": "SKU-AI-FLOW",
            "production_type": "label_and_name_cut",
            "model_key": "01",
            "model_path": "templates/designs/01_a_gold.json",
            "model_name": "01 A Gold Rulo Etiket",
            "name_cut_style": "Mochary Personal Use Only",
            "name_cut_width_mm": 300,
        },
    )

    calls = {"count": 0}

    def fake_post_json(url, headers, payload, timeout):
        calls["count"] += 1
        if "verify-secret-should-not-leak" not in headers.get("Authorization", ""):
            raise AssertionError("AI Authorization header missing")
        return {
            "output_text": json.dumps(
                {
                    "label_text": "Selin & Hakan",
                    "name_cut_text": "Selin Hakan",
                    "date_text": "07.06.2026",
                    "note_text": "",
                    "confidence": 0.94,
                    "field_sources": {
                        "label_text": "question_text",
                        "name_cut_text": "question_text",
                        "date_text": "question_text",
                        "note_text": "empty",
                        "quantity": "order_line",
                    },
                    "evidence_spans": {
                        "label_text": "Selin & Hakan",
                        "date_text": "07.06.2026",
                    },
                    "warnings": [],
                    "needs_user_review": False,
                },
                ensure_ascii=False,
            )
        }

    trendyol_ai_extractor._post_json = fake_post_json
    question = trendyol_api._normalize_question_context(
        root,
        {
            "id": "Q-AI-FLOW",
            "orderNumber": "11243461810",
            "barcode": "TY-AI-FLOW",
            "text": "11243461810 Selin & Hakan yazılmasını rica ediyorum 07.06.2026",
        },
    )
    trendyol_api._save_questions(root, [question])
    order = {
        "orderNumber": "11243461810",
        "shipmentPackageId": "PKG-AI-FLOW",
        "customerName": "Hakan Firincioğullari",
        "lines": [
            {
                "id": "LINE-AI-FLOW",
                "productName": "Kız İsteme Çikolatası Söz Çikolatası Nişan Çikolatası İsteme Çiçeği 2762616161",
                "barcode": "TY-AI-FLOW",
                "merchantSku": "SKU-AI-FLOW",
                "quantity": 1,
            }
        ],
    }
    row = trendyol_api.build_suggestions_from_orders(root, [order])[0]

    assert row["label_text"] == "Selin & Hakan", row
    assert row["name_cut_text"] == "Selin & Hakan", row
    assert row["date_text"] == "07.06.2026", row
    assert row["verification_status"] == "alanlar_onay_bekliyor", row
    assert row["status"] == "review", row
    assert row["user_verified"] is False, row
    assert row["needs_user_review"] is True, row
    assert "cloud_ai_extract" in row["source_evidence"], row
    assert "Çiçeği" not in row["label_text"]

    second = trendyol_api.build_suggestions_from_orders(root, [order])[0]
    assert second["label_text"] == "Selin & Hakan"
    assert "cloud_ai_cache" in second["source_evidence"]
    assert calls["count"] <= 2

    serialized = json.dumps(second, ensure_ascii=False)
    assert "verify-secret-should-not-leak" not in serialized
    assert "direct_print" not in serialized.lower()
    assert "rdworks_auto" not in serialized.lower()
    assert "laser_start" not in serialized.lower()


if __name__ == "__main__":
    raise SystemExit(main())
