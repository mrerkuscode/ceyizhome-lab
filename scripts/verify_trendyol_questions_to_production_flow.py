from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend import trendyol_api, trendyol_mapping_api  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cyzella_trendyol_questions_") as tmp:
        root = Path(tmp)
        trendyol_mapping_api.upsert_product_mapping(
            root,
            {
                "product_name": "Kişiye Özel Nişan Etiketi",
                "barcode": "TY-SORU-01",
                "merchant_sku": "SKU-SORU-01",
                "stock_code": "SKU-SORU-01",
                "production_type": "label_and_name_cut",
                "model_key": "01",
                "model_path": "templates/designs/01_a_gold.json",
                "model_name": "01 A Gold Rulo Etiket",
                "name_cut_style": "Mochary Personal Use Only",
                "name_cut_width_mm": 300,
                "image_url": "https://cdn.example.test/product.png",
                "active": True,
            },
        )
        question = trendyol_api._normalize_question_context(
            root,
            {
                "id": "Q-SORU-01",
                "status": "WaitingForAnswer",
                "barcode": "TY-SORU-01",
                "productName": "Kişiye Özel Nişan Etiketi",
                "customerName": "Trendyol Müşteri",
                "text": "3248924141 sipariş numaralı ürünüme ayse ali yazılsın",
            },
        )
        trendyol_api._save_questions(root, [question])
        order = {
            "orderNumber": "3248924141",
            "shipmentPackageId": "PKG-SORU-01",
            "customerFirstName": "Ayse",
            "customerLastName": "Ali",
            "lines": [
                {
                    "id": "LINE-SORU-01",
                    "productName": "Kişiye Özel Nişan Etiketi",
                    "barcode": "TY-SORU-01",
                    "merchantSku": "SKU-SORU-01",
                    "quantity": 1,
                }
            ],
        }
        suggestions = trendyol_api.build_suggestions_from_orders(root, [order])
        _assert(len(suggestions) == 1, "Tek sipariş satırı tek üretim önerisi oluşturmalı.")
        row = suggestions[0]
        _assert(row["label_text"] == "Ayşe & Ali", f"Etiket ismi soru metninden gelmeli: {row['label_text']}")
        _assert(row["name_cut_text"] == "Ayşe & Ali", f"Lazer ismi soru metninden gelmeli: {row['name_cut_text']}")
        _assert(row["production_type"] == "label_and_name_cut", "Ürün eşleştirmesi etiket+lazer üretim tipini belirlemeli.")
        _assert(row["verification_status"] == "alanlar_onay_bekliyor", "Soru bağlı satır kullanıcı onayı beklemeli.")
        _assert(row["question_contexts"][0]["question_text"].startswith("3248924141"), "Soru kanıtı siparişe bağlı görünmeli.")
        _assert(row["field_sources"]["label_text"] == "question_text", "Etiket alan kaynağı soru metni olmalı.")
        trendyol_api.save_suggestions(root, suggestions)
        verified = trendyol_api.verify_suggestion(
            root,
            row["id"],
            {
                "label_required": True,
                "name_cut_required": True,
                "label_text": row["label_text"],
                "name_cut_text": row["name_cut_text"],
                "date_text": row.get("date_text") or "",
                "note_text": row.get("note_text") or "",
                "model_path": row["model_path"],
            },
        )
        _assert(verified["status"] == "OK", "Kullanıcı onayı sonrası satır üretime hazır olmalı.")
        ready = verified["suggestion"]
        _assert(ready["verification_status"] == "uretime_hazir", "Doğrulanan satır üretime hazır durumuna geçmeli.")
        _assert(not (root / "rdworks_opened.flag").exists(), "RDWorks otomatik açılmamalı.")
        _assert(not (root / "laser_started.flag").exists(), "Lazer otomatik başlamamalı.")
        _assert(not (root / "direct_print.flag").exists(), "Direct print tetiklenmemeli.")

    print(
        json.dumps(
            {
                "status": "PASSED",
                "checked": [
                    "qna question evidence",
                    "order number link",
                    "AI name extraction from question text",
                    "product mapping decides label+laser",
                    "user verification required",
                    "no RDWorks/laser/direct print automation",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
