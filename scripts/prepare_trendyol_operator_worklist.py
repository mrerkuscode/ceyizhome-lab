from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_trendyol_live_data_quality import run_audit  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "trendyol_operator_worklist"
JSON_PATH = OUTPUT_DIR / "TRENDYOL_OPERATOR_WORKLIST.json"
MD_PATH = OUTPUT_DIR / "TRENDYOL_OPERATOR_WORKLIST.md"
CSV_PATH = OUTPUT_DIR / "TRENDYOL_OPERATOR_WORKLIST.csv"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sku(value: Any) -> str:
    text = _text(value)
    return "" if text.lower().replace("_", "") == "merchantsku" else text


def _top_mapping_tasks(payload: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for index, item in enumerate(payload.get("mapping_priorities") or [], start=1):
        if len(tasks) >= limit:
            break
        tasks.append(
            {
                "rank": index,
                "type": "product_mapping",
                "priority": "high",
                "row_count": int(item.get("row_count") or 0),
                "barcode": _text(item.get("barcode")),
                "merchant_sku": _sku(item.get("merchant_sku")),
                "product_name": _text(item.get("product_name")),
                "question_linked_count": int(item.get("question_linked_count") or 0),
                "low_confidence_count": int(item.get("low_confidence_count") or 0),
                "no_person_name_count": int(item.get("no_person_name_count") or 0),
                "sample_order_numbers": item.get("sample_order_numbers") or [],
                "image_url": _text(item.get("image_url")),
                "product_url": _text(item.get("product_url")),
                "auto_apply_safe": False,
                "blocked_reason": "Model ve üretim tipi operatör tarafından doğrulanmadan canlı eşleştirme yazılmadı.",
                "next_action": "Ürün Eşleştirme tabında bu barkod/SKU için doğru model ve üretim tipini seç.",
            }
        )
    return tasks


def _question_binding_tasks(payload: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for issue in payload.get("issues") or []:
        candidates = issue.get("question_candidates") or []
        if not candidates:
            continue
        top = candidates[0]
        tasks.append(
            {
                "type": "question_binding",
                "priority": "high" if int(top.get("score") or 0) >= 100 else "medium",
                "order_number": _text(issue.get("order_number")),
                "line_id": _text(issue.get("line_id")),
                "customer_name": _text(issue.get("customer_name")),
                "barcode": _text(issue.get("barcode")),
                "merchant_sku": _sku(issue.get("merchant_sku")),
                "product_name": _text(issue.get("product_name")),
                "candidate_question_id": _text(top.get("id")),
                "candidate_score": int(top.get("score") or 0),
                "candidate_question_text": _text(top.get("question_text")),
                "next_action": "Sipariş kartındaki 'En iyi adayı bağla' butonuyla kanıtı satıra bağla.",
            }
        )
        if len(tasks) >= limit:
            break
    return tasks


def _evidence_missing_tasks(payload: dict[str, Any], limit: int = 60) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    wanted = {"no_matching_question_by_order_barcode_sku", "no_saved_questions", "question_service_unavailable"}
    for issue in payload.get("issues") or []:
        reasons = set(issue.get("reasons") or [])
        if not reasons.intersection(wanted):
            continue
        tasks.append(
            {
                "type": "evidence_missing",
                "priority": issue.get("priority") or ("high" if "no_person_name_found" in reasons else "medium"),
                "category": issue.get("category") or "evidence",
                "order_number": _text(issue.get("order_number")),
                "line_id": _text(issue.get("line_id")),
                "customer_name": _text(issue.get("customer_name")),
                "barcode": _text(issue.get("barcode")),
                "merchant_sku": _sku(issue.get("merchant_sku")),
                "product_name": _text(issue.get("product_name")),
                "reasons": sorted(reasons),
                "blocks_production": bool(issue.get("blocks_production")),
                "next_action": "Soruları Oku ile kanıtları yenile; exact sipariş kanıtı yoksa ürün benzerliğini bağlama ve satırı manuel kontrol et.",
            }
        )
        if len(tasks) >= limit:
            break
    return tasks


def _ai_review_tasks(payload: dict[str, Any], limit: int = 40) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    wanted = {"ai_low_confidence", "no_person_name_found"}
    for issue in payload.get("issues") or []:
        reasons = set(issue.get("reasons") or [])
        if not reasons.intersection(wanted):
            continue
        tasks.append(
            {
                "type": "ai_review",
                "priority": issue.get("priority") or "medium",
                "category": issue.get("category") or "extraction",
                "order_number": _text(issue.get("order_number")),
                "line_id": _text(issue.get("line_id")),
                "customer_name": _text(issue.get("customer_name")),
                "barcode": _text(issue.get("barcode")),
                "merchant_sku": _sku(issue.get("merchant_sku")),
                "product_name": _text(issue.get("product_name")),
                "confidence": issue.get("confidence") or 0,
                "label_text": _text(issue.get("label_text")),
                "name_cut_text": _text(issue.get("name_cut_text")),
                "reasons": sorted(reasons.intersection(wanted)),
                "blocks_production": bool(issue.get("blocks_production")),
                "next_action": "Müşteri mesajını kontrol et; kişi ismi yoksa isim/lazer alanlarını boş bırak.",
            }
        )
        if len(tasks) >= limit:
            break
    return tasks


def _media_tasks(payload: dict[str, Any], limit: int = 30) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    wanted = {"missing_product_image_url", "missing_product_url", "product_url_rejected_fuzzy_catalog_match"}
    for issue in payload.get("issues") or []:
        reasons = set(issue.get("reasons") or [])
        if not reasons.intersection(wanted):
            continue
        tasks.append(
            {
                "type": "media_review",
                "priority": issue.get("priority") or "medium",
                "category": "media",
                "order_number": _text(issue.get("order_number")),
                "line_id": _text(issue.get("line_id")),
                "customer_name": _text(issue.get("customer_name")),
                "barcode": _text(issue.get("barcode")),
                "merchant_sku": _sku(issue.get("merchant_sku")),
                "product_name": _text(issue.get("product_name")),
                "reasons": sorted(reasons.intersection(wanted)),
                "next_action": "Ürün eşleştirme/katalog kaynağında görsel ve Trendyol linkini doğrula; fuzzy link reddedildiyse doğru linki elle gir.",
            }
        )
        if len(tasks) >= limit:
            break
    return tasks


def build_worklist(payload: dict[str, Any]) -> dict[str, Any]:
    mapping_tasks = _top_mapping_tasks(payload)
    question_tasks = _question_binding_tasks(payload)
    evidence_tasks = _evidence_missing_tasks(payload)
    ai_tasks = _ai_review_tasks(payload)
    media_tasks = _media_tasks(payload)
    total_mapping_impact = sum(int(item.get("row_count") or 0) for item in mapping_tasks)
    return {
        "status": "PASSED",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_audit_created_at": payload.get("created_at"),
        "summary": {
            "top_mapping_task_count": len(mapping_tasks),
            "top_mapping_row_impact": total_mapping_impact,
            "question_binding_task_count": len(question_tasks),
            "evidence_missing_task_count": len(evidence_tasks),
            "ai_review_task_count": len(ai_tasks),
            "media_review_task_count": len(media_tasks),
            "production_blocking_task_count": sum(1 for group in [question_tasks, evidence_tasks, ai_tasks] for item in group if item.get("blocks_production")),
            "safe_auto_mapping_applied": False,
            "safe_auto_mapping_note": "Canlı model doğruluğu bilinmediği için ürün eşleştirmeleri otomatik yazılmadı.",
        },
        "mapping_tasks": mapping_tasks,
        "question_binding_tasks": question_tasks,
        "evidence_missing_tasks": evidence_tasks,
        "ai_review_tasks": ai_tasks,
        "media_review_tasks": media_tasks,
        "release_checklist": [
            "İlk 5 mapping görevi operatör tarafından doğru modelle eşleştirildi.",
            "Aday soru görevleri UI'da bağlandı.",
            "AI düşük güven ve isim yok satırları manuel kontrol edildi.",
            "npm run test:trendyol geçti.",
            "npm run test geçti.",
            "Gerekirse npm run test:long geçti.",
        ],
    }


def _write_csv(worklist: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    for item in worklist["mapping_tasks"]:
        rows.append(
            {
                "type": item["type"],
                "priority": item["priority"],
                "impact": item["row_count"],
                "order_number": ", ".join(item.get("sample_order_numbers") or []),
                "line_id": "",
                "barcode": item["barcode"],
                "merchant_sku": item["merchant_sku"],
                "product_name": item["product_name"],
                "candidate_question_id": "",
                "next_action": item["next_action"],
                "blocked_reason": item["blocked_reason"],
            }
        )
    for item in worklist["question_binding_tasks"]:
        rows.append(
            {
                "type": item["type"],
                "priority": item["priority"],
                "impact": 1,
                "order_number": item["order_number"],
                "line_id": item["line_id"],
                "barcode": item["barcode"],
                "merchant_sku": item["merchant_sku"],
                "product_name": item["product_name"],
                "candidate_question_id": item["candidate_question_id"],
                "next_action": item["next_action"],
                "blocked_reason": "",
            }
        )
    for item in worklist["evidence_missing_tasks"]:
        rows.append(
            {
                "type": item["type"],
                "priority": item["priority"],
                "impact": 1,
                "order_number": item["order_number"],
                "line_id": item["line_id"],
                "barcode": item["barcode"],
                "merchant_sku": item["merchant_sku"],
                "product_name": item["product_name"],
                "candidate_question_id": "",
                "next_action": item["next_action"],
                "blocked_reason": ", ".join(item.get("reasons") or []),
            }
        )
    for item in worklist["ai_review_tasks"]:
        rows.append(
            {
                "type": item["type"],
                "priority": item["priority"],
                "impact": 1,
                "order_number": item["order_number"],
                "line_id": item["line_id"],
                "barcode": item["barcode"],
                "merchant_sku": item["merchant_sku"],
                "product_name": item["product_name"],
                "candidate_question_id": "",
                "next_action": item["next_action"],
                "blocked_reason": ", ".join(item.get("reasons") or []),
            }
        )
    for item in worklist["media_review_tasks"]:
        rows.append(
            {
                "type": item["type"],
                "priority": item["priority"],
                "impact": 1,
                "order_number": item["order_number"],
                "line_id": item["line_id"],
                "barcode": item["barcode"],
                "merchant_sku": item["merchant_sku"],
                "product_name": item["product_name"],
                "candidate_question_id": "",
                "next_action": item["next_action"],
                "blocked_reason": ", ".join(item.get("reasons") or []),
            }
        )
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "type",
                "priority",
                "impact",
                "order_number",
                "line_id",
                "barcode",
                "merchant_sku",
                "product_name",
                "candidate_question_id",
                "next_action",
                "blocked_reason",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(worklist: dict[str, Any]) -> None:
    summary = worklist["summary"]
    lines = [
        "# Trendyol Operator Worklist",
        "",
        f"Created: `{worklist['created_at']}`",
        "",
        "## Summary",
        "",
        f"- İlk mapping görevi: `{summary['top_mapping_task_count']}`",
        f"- İlk mapping toplam etkisi: `{summary['top_mapping_row_impact']}` satır",
        f"- Aday soru bağlama görevi: `{summary['question_binding_task_count']}`",
        f"- AI manuel kontrol görevi: `{summary['ai_review_task_count']}`",
        f"- Otomatik mapping yazıldı mı: `{summary['safe_auto_mapping_applied']}`",
        f"- Not: {summary['safe_auto_mapping_note']}",
        "",
        "## İlk 5 Ürün Eşleştirme",
        "",
    ]
    for item in worklist["mapping_tasks"]:
        lines.extend(
            [
                f"### {item['rank']}. {item['barcode'] or '-'} / {item['merchant_sku'] or '-'}",
                "",
                f"- Etki: `{item['row_count']}` satır",
                f"- Ürün: {item['product_name']}",
                f"- Örnek siparişler: `{', '.join(item.get('sample_order_numbers') or [])}`",
                f"- Link: {item['product_url'] or 'Yok'}",
                f"- Görsel: {item['image_url'] or 'Yok'}",
                f"- Aksiyon: {item['next_action']}",
                f"- Güvenlik: {item['blocked_reason']}",
                "",
            ]
        )
    lines.extend(["## Aday Soru Bağlama", ""])
    if worklist["question_binding_tasks"]:
        for item in worklist["question_binding_tasks"][:20]:
            lines.append(
                f"- `{item['order_number']}` / `{item['line_id']}`: aday `{item['candidate_question_id']}` "
                f"skor `{item['candidate_score']}` - {item['next_action']}"
            )
    else:
        lines.append("- Aday soru bağlama görevi yok.")
    lines.extend(["", "## AI Manuel Kontrol", ""])
    if worklist["ai_review_tasks"]:
        for item in worklist["ai_review_tasks"][:25]:
            lines.append(
                f"- `{item['order_number']}` / `{item['line_id']}`: güven `{item['confidence']}` "
                f"neden `{', '.join(item.get('reasons') or [])}` - {item['next_action']}"
            )
    else:
        lines.append("- AI manuel kontrol görevi yok.")
    lines.extend(["", "## Evidence Missing", ""])
    if worklist["evidence_missing_tasks"]:
        for item in worklist["evidence_missing_tasks"][:30]:
            lines.append(
                f"- `{item['order_number']}` / `{item['line_id']}`: `{item['priority']}` "
                f"neden `{', '.join(item.get('reasons') or [])}` - {item['next_action']}"
            )
    else:
        lines.append("- Kanıt eksik görevi yok.")
    lines.extend(["", "## Media / Link Review", ""])
    if worklist["media_review_tasks"]:
        for item in worklist["media_review_tasks"][:20]:
            lines.append(
                f"- `{item['order_number']}` / `{item['line_id']}`: `{', '.join(item.get('reasons') or [])}` - {item['next_action']}"
            )
    else:
        lines.append("- Görsel/link görevi yok.")
    lines.extend(["", "## Release Checklist", ""])
    lines.extend(f"- [ ] {item}" for item in worklist["release_checklist"])
    lines.extend(["", "## Files", "", f"- JSON: `{JSON_PATH}`", f"- CSV: `{CSV_PATH}`"])
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Run the read-only Trendyol refresh before preparing the worklist.")
    args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = run_audit(refresh=args.refresh)
    worklist = build_worklist(payload)
    JSON_PATH.write_text(json.dumps(worklist, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(worklist)
    _write_markdown(worklist)
    print(
        json.dumps(
            {
                "status": worklist["status"],
                "summary": worklist["summary"],
                "json_report": str(JSON_PATH),
                "markdown_report": str(MD_PATH),
                "csv_report": str(CSV_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
