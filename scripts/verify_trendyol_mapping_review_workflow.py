from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend import trendyol_api, trendyol_mapping_api


MOJIBAKE_MARKERS = ("Ã", "Ä", "Å", "Â", "�")


def assert_condition(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def _sample_order(barcode: str, sku: str, line_id: str, product_name: str, customer_name: str = "ayse omer") -> dict[str, object]:
    return {
        "orderNumber": f"TY-{line_id}",
        "shipmentPackageId": f"PKG-{line_id}",
        "customerName": customer_name,
        "lines": [
            {
                "id": line_id,
                "productName": product_name,
                "barcode": barcode,
                "merchantSku": sku,
                "quantity": 2,
            }
        ],
    }


def _save_question(root: Path, barcode: str = "TY-READY-01", text: str = "isim: Ayşe & Ömer tarih: 15.05.2026 not: Nişan Hatırası") -> None:
    trendyol_api._save_questions(
        root,
        [
            trendyol_api._normalize_question_context(
                root,
                {
                    "id": f"Q-{barcode}",
                    "status": "WaitingForAnswer",
                    "barcode": barcode,
                    "text": text,
                },
            )
        ],
    )


def _verify_for_export(root: Path, row: dict[str, object]) -> dict[str, object]:
    return trendyol_api.verify_suggestion(
        root,
        str(row.get("id") or ""),
        {
            "label_required": True,
            "name_cut_required": False,
            "label_text": row.get("label_text") or "",
            "date_text": row.get("date_text") or "",
            "note_text": row.get("note_text") or "",
            "model_path": row.get("model_path") or "",
        },
    )


def _contains_mojibake(value: object) -> bool:
    text = str(value or "")
    return any(marker in text for marker in MOJIBAKE_MARKERS)


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cyzella_trendyol_mapping_review_") as temp:
        root = Path(temp)
        trendyol_mapping_api.upsert_product_mapping(
            root,
            {
                "barcode": "TY-READY-01",
                "merchant_sku": "SKU-READY-01",
                "production_type": "label",
                "model_key": "01",
                "model_path": "templates/designs/01_a_gold.json",
                "model_name": "01 A Gold Rulo Etiket",
                "active": True,
            },
        )
        _save_question(root, "TY-READY-01")
        orders = [
            _sample_order(
                "TY-READY-01",
                "SKU-READY-01",
                "READY-1",
                "Kişiye Özel Nişan Etiketi isim: Ayşe & Ömer not: Nişan Hatırası 15.05.2026",
            ),
            _sample_order(
                "TY-UNKNOWN-01",
                "SKU-UNKNOWN-01",
                "REVIEW-1",
                "KiÅŸiye Ã–zel Nisan Etiketi not: Nisan Hatirasi",
                "ebubekir gÃ¶rdegir",
            ),
        ]
        suggestions = trendyol_api.build_suggestions_from_orders(root, orders)
        trendyol_api.save_suggestions(root, suggestions)
        listed = trendyol_api.list_suggestions(root)

        pending_rows = [row for row in listed if row.get("verification_status") == "alanlar_onay_bekliyor"]
        review_rows = [row for row in listed if row.get("verification_status") != "alanlar_onay_bekliyor"]
        assert_condition(len(pending_rows) == 1, "Tam olarak 1 soru kanitli onay bekleyen Trendyol satiri bekleniyordu.", failures)
        assert_condition(len(review_rows) == 1, "Tam olarak 1 kontrol gerekli Trendyol satiri bekleniyordu.", failures)
        assert_condition(not any(_contains_mojibake(row.get("customer_name")) or _contains_mojibake(row.get("product_name")) for row in listed), "Kullaniciya giden Trendyol metinlerinde bozuk karakter kaldi.", failures)
        assert_condition(any("düşük güven" in " ".join(row.get("warnings") or []).lower() for row in review_rows), "Dusuk guvenli satir kullanici kontrol uyarisi tasimiyor.", failures)

        verified = _verify_for_export(root, pending_rows[0] if pending_rows else {})
        assert_condition(verified.get("status") == "OK", "Soru kanitli satir kullanici onayiyla hazir yapilamadi.", failures)
        exported = trendyol_api.export_ready_suggestions_to_excel(root)
        assert_condition(exported["status"] == "OK", "Sadece hazir satirlar uretim Excel'ine aktarilamadi.", failures)
        export_path = root / exported["relative_path"]
        manifest_path = root / exported["manifest_path"]
        assert_condition(export_path.exists(), "Uretim Excel dosyasi olusmadi.", failures)
        assert_condition(manifest_path.exists(), "Uretim manifest dosyasi olusmadi.", failures)

        frame = pd.read_excel(export_path)
        assert_condition(len(frame) == 1, "Kontrol gerekli/dusuk guvenli satir uretim Excel'ine sizdi.", failures)
        assert_condition(str(frame.iloc[0].get("barcode")) == "TY-READY-01", "Uretim Excel'i yanlis Trendyol satirini aldi.", failures)
        assert_condition(str(frame.iloc[0].get("etiket_cikar")).lower() == "evet", "Hazir etiket satiri etiket_cikar=evet tasimiyor.", failures)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        safety = manifest.get("safety") or {}
        assert_condition(safety.get("direct_print") is False, "Trendyol uretim export manifestinde direct print kapali degil.", failures)
        assert_condition(safety.get("rdworks_auto_open") is False, "Trendyol uretim export manifestinde RDWorks otomatik acma kapali degil.", failures)
        assert_condition(safety.get("laser_auto_start") is False, "Trendyol uretim export manifestinde lazer otomatik baslatma kapali degil.", failures)

        ai_orders = [
            _sample_order(
                "TY-AI-UNKNOWN",
                "SKU-01",
                "AI-1",
                "Kişiye Özel Nişan Etiketi isim: Ayşe & Ömer not: Nişan Hatırası 15.05.2026",
            )
        ]
        ai_models = [
            {
                "model_no": "01",
                "template_no": "A",
                "model_name": "01 A Gold Rulo Etiket",
                "path": "templates/designs/01_a_gold.json",
            }
        ]
        ai_suggestions = trendyol_api.build_suggestions_from_orders(root, ai_orders, label_models=ai_models)
        assert_condition(ai_suggestions[0].get("status") == "review", "AI otonom modu soru kaniti olmadan hazir satir uretmemeli.", failures)
        assert_condition(ai_suggestions[0].get("verification_status") == "kanit_bekliyor", "AI otonom satir soru kaniti beklemeli.", failures)
        assert_condition(ai_suggestions[0].get("ai_autonomous") is True, "AI otonom satir isaretlenmedi.", failures)
        assert_condition(ai_suggestions[0].get("mapping_source") == "ai_autonomous", "AI otonom satirin kaynak bilgisi dogru degil.", failures)
        assert_condition(trendyol_mapping_api.list_product_mappings(root)[0].get("barcode") == "TY-READY-01", "AI otonom mod urun eslestirme tablosuna sessiz kayit acti.", failures)
        trendyol_api.save_suggestions(root, ai_suggestions)
        ai_exported = trendyol_api.export_ready_suggestions_to_excel(root)
        assert_condition(ai_exported.get("status") == "ERROR", "AI otonom satir kullanici onayi olmadan uretim Excel'ine aktarilmamali.", failures)

    report_dir = PROJECT_ROOT / "output" / datetime.now().strftime("%Y-%m-%d") / "trendyol_mapping_review_workflow"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "VERIFY_TRENDYOL_MAPPING_REVIEW_WORKFLOW_RESULT.json"
    report = {
        "status": "FAILED" if failures else "PASSED",
        "failures": failures,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "checks": [
            "ready_vs_review_split",
            "mojibake_repair",
            "low_confidence_warning",
            "ready_only_excel_export",
            "manifest_safety_flags",
            "ai_autonomous_ready_candidate",
            "ai_autonomous_manifest_safety",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    print(f"PASSED: Trendyol mapping review workflow verified. Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
