from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from intelligence.text_cleanup import repair_text  # noqa: E402
from webui_backend import trendyol_api  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "trendyol_live_audit"
JSON_PATH = OUTPUT_DIR / "TRENDYOL_LIVE_DATA_AUDIT.json"
MD_PATH = OUTPUT_DIR / "TRENDYOL_LIVE_DATA_AUDIT.md"
CSV_PATH = OUTPUT_DIR / "TRENDYOL_LIVE_DATA_AUDIT_ISSUES.csv"
MAPPING_PRIORITY_CSV_PATH = OUTPUT_DIR / "TRENDYOL_MAPPING_PRIORITY.csv"
DEBUG_LOG_PATH = PROJECT_ROOT / "logs" / "trendyol_extraction_debug.jsonl"


PRODUCTION_TYPES_REQUIRING_MODEL = {"label", "label_and_name_cut"}
LOW_CONFIDENCE_THRESHOLD = 0.7
REASON_LABELS = {
    "question_service_unavailable": "Trendyol soru servisi son denemede yanıt vermedi.",
    "no_saved_questions": "Yerel soru/mesaj kanıtı dosyasında kayıt yok.",
    "no_matching_question_by_order_barcode_sku": "Kaydedilmiş sorular var ama sipariş/barkod/SKU ile eşleşen kanıt bulunamadı.",
    "question_exists_but_not_attached": "Bu satıra benzeyen soru var; operatör aday soruyu bağlamalı.",
    "missing_product_image_url": "Ürün görsel URL alanı boş.",
    "missing_product_url": "Trendyol ürün linki yok.",
    "product_url_rejected_fuzzy_catalog_match": "Ürün linki başlıkla güvenli eşleşmediği için reddedildi.",
    "missing_product_mapping": "Barkod/SKU ürün eşleştirmesi yok.",
    "missing_model_path": "Üretim tipi model gerektiriyor ama model yolu yok.",
    "ai_low_confidence": "AI alan güveni düşük.",
    "no_person_name_found": "Müşteri mesajında kişi ismi bulunamadı veya final alanda yok.",
}
REASON_CATEGORIES = {
    "question_service_unavailable": "evidence",
    "no_saved_questions": "evidence",
    "no_matching_question_by_order_barcode_sku": "evidence",
    "question_exists_but_not_attached": "evidence",
    "missing_product_image_url": "media",
    "missing_product_url": "media",
    "product_url_rejected_fuzzy_catalog_match": "media",
    "missing_product_mapping": "mapping",
    "missing_model_path": "mapping",
    "ai_low_confidence": "extraction",
    "no_person_name_found": "extraction",
}
ACTION_METADATA = {
    "bind_candidate_question": {
        "label": "Aday soruyu bagla",
        "description": "Siparis numarasi veya line id ile guvenli aday soru varsa satira bagla.",
    },
    "refresh_or_manual_question_check": {
        "label": "Kaniti yenile veya manuel kontrol et",
        "description": "Sorulari Oku ile read-only yenile; exact siparis kaniti yoksa urun benzerligini kanit sayma.",
    },
    "complete_product_mapping": {
        "label": "Urun eslestir",
        "description": "Barkod/SKU icin dogru model ve uretim tipini bagla.",
    },
    "fix_product_media": {
        "label": "Gorsel/link kontrol et",
        "description": "Katalog gorseli ve Trendyol linki kaynagini duzelt.",
    },
    "manual_ai_review": {
        "label": "AI alanlarini manuel dogrula",
        "description": "Isim yoksa sahte isim uretme; dusuk guvenli alanlari musteri metniyle kontrol et.",
    },
    "operator_review": {
        "label": "Operator kontrolu",
        "description": "Satiri uretime almadan once manuel kontrol et.",
    },
}


def _text(value: Any) -> str:
    return repair_text(value or "").strip()


def _sku(value: Any) -> str:
    text = _text(value)
    return "" if _identity(text) in {"merchantsku", "merchant_sku"} else text


def _identity(value: Any) -> str:
    text = _text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text)


def _search_key(value: Any) -> str:
    text = _text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _safe_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        raw = f"https:{raw}"
    elif raw.startswith("/"):
        raw = f"https://www.trendyol.com{raw}"
    elif not re.match(r"^https?://", raw, flags=re.I):
        if re.match(r"^(?:www\.)?trendyol\.com\b", raw, flags=re.I) or re.match(r"^[^/\s]+\.[^/\s]+", raw):
            raw = f"https://{raw}"
        else:
            return ""
    return raw if re.match(r"^https?://", raw, flags=re.I) else ""


def _contexts(row: dict[str, Any]) -> list[dict[str, Any]]:
    contexts = row.get("question_contexts") if isinstance(row.get("question_contexts"), list) else []
    return [item for item in contexts if isinstance(item, dict)]


def _has_question_evidence(row: dict[str, Any]) -> bool:
    if _text(row.get("question_text")) or _text(row.get("answer_text")):
        return True
    return any(_text(item.get("question_text")) or _text(item.get("answer_text")) for item in _contexts(row))


def _image_url(row: dict[str, Any]) -> tuple[str, str]:
    for key in [
        "preview_url",
        "cached_image_url",
        "productImageUrl",
        "productImage",
        "imageUrl",
        "thumbnailUrl",
        "image_url",
        "primary_image_url",
        "trendyolImageUrl",
    ]:
        url = _safe_url(row.get(key))
        if url:
            return url, str(row.get("image_url_source") or key)
    image_urls = row.get("image_urls") if isinstance(row.get("image_urls"), list) else []
    for item in image_urls:
        url = _safe_url(item)
        if url:
            return url, "image_urls"
    for context in _contexts(row):
        for key in ["image_url", "primary_image_url", "imageUrl"]:
            url = _safe_url(context.get(key))
            if url:
                return url, f"question_context.{key}"
    return "", ""


def _title_relevant_to_url(row: dict[str, Any], url: str) -> bool:
    if not url:
        return False
    if "trendyol.com" not in url.lower():
        return True
    path = _search_key(url)
    title = _search_key(row.get("product_name"))
    if not path or not title:
        return True
    tokens = [token for token in title.split() if len(token) >= 4 and not token.isdigit()]
    if not tokens:
        return True
    compact_path = path.replace(" ", "")
    hits = sum(1 for token in tokens if token in path or token in compact_path)
    return hits >= min(3, len(tokens))


def _product_url(row: dict[str, Any]) -> tuple[str, str, str]:
    for key in ["product_url", "productUrl", "productLink", "trendyolUrl", "productPageUrl", "url"]:
        url = _safe_url(row.get(key))
        if url:
            source = str(row.get("product_url_source") or key)
            if source == "catalog_name" or not _title_relevant_to_url(row, url):
                return url, source, "rejected"
            return url, source, "accepted"
    for context in _contexts(row):
        for key in ["product_url", "productUrl"]:
            url = _safe_url(context.get(key))
            if url:
                return url, f"question_context.{key}", "accepted" if _title_relevant_to_url(row, url) else "rejected"
    return "", "", "missing"


def _question_match_probe(row: dict[str, Any], question_index: dict[str, list[dict[str, Any]]]) -> str:
    source = dict(row)
    source["question_text"] = ""
    source["answer_text"] = ""
    source["question_contexts"] = []
    attached = trendyol_api._attach_question_context(source, question_index)  # noqa: SLF001
    return "would_attach" if _has_question_evidence(attached) else "no_match"


def _question_candidate_score(row: dict[str, Any], question: dict[str, Any]) -> int:
    score = 0
    order_number = _identity(row.get("order_number"))
    question_order = _identity(question.get("order_number") or question.get("orderNumber"))
    if order_number and question_order and order_number == question_order:
        score += 100
    question_text_raw = _text(question.get("question_text") or question.get("answer_text"))
    if order_number and order_number in _identity(question_text_raw):
        score += 90
    line_id = _identity(row.get("line_id"))
    question_line_id = _identity(question.get("line_id") or question.get("lineId"))
    if line_id and question_line_id and line_id == question_line_id:
        score += 90
    barcode = _identity(row.get("barcode"))
    question_barcode = _identity(question.get("barcode"))
    if barcode and question_barcode and barcode == question_barcode:
        score += 55
    sku = _identity(_sku(row.get("merchant_sku") or row.get("stock_code")))
    question_sku = _identity(_sku(question.get("merchant_sku") or question.get("stock_code")))
    if sku and question_sku and sku == question_sku:
        score += 35
    product_tokens = {token for token in _search_key(row.get("product_name")).split() if len(token) > 3}
    question_product_tokens = [token for token in _search_key(question.get("product_name")).split() if len(token) > 3]
    if product_tokens and sum(1 for token in question_product_tokens if token in product_tokens) >= 3:
        score += 18
    question_text = _search_key(question.get("question_text"))
    suggested_name = _search_key(row.get("label_text") or row.get("name_cut_text"))
    if question_text and suggested_name and suggested_name in question_text:
        score += 20
    return score


def _question_candidate_is_safe(row: dict[str, Any], question: dict[str, Any]) -> bool:
    order_number = _identity(row.get("order_number"))
    question_order = _identity(question.get("order_number") or question.get("orderNumber"))
    if order_number and question_order and order_number == question_order:
        return True
    question_text_raw = _text(question.get("question_text") or question.get("answer_text"))
    if order_number and order_number in _identity(question_text_raw):
        return True
    line_id = _identity(row.get("line_id"))
    question_line_id = _identity(question.get("line_id") or question.get("lineId"))
    return bool(line_id and question_line_id and line_id == question_line_id)


def _manual_question_candidates(row: dict[str, Any], questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    ignored = {str(item or "") for item in (row.get("ignored_question_ids") if isinstance(row.get("ignored_question_ids"), list) else [])}
    linked = {str(item.get("id") or "") for item in _contexts(row)}
    for question in questions:
        question_id = str(question.get("id") or "")
        if question_id and (question_id in ignored or question_id in linked):
            continue
        score = _question_candidate_score(row, question)
        if score < 80 or not _question_candidate_is_safe(row, question):
            continue
        candidates.append({
            "id": question_id,
            "score": score,
            "barcode": _text(question.get("barcode")),
            "merchant_sku": _text(question.get("merchant_sku") or question.get("stock_code")),
            "product_name": _text(question.get("product_name")),
            "question_text": _text(question.get("question_text"))[:220],
        })
    return sorted(candidates, key=lambda item: item["score"], reverse=True)[:5]


def _unsafe_question_candidates(row: dict[str, Any], questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    ignored = {str(item or "") for item in (row.get("ignored_question_ids") if isinstance(row.get("ignored_question_ids"), list) else [])}
    linked = {str(item.get("id") or "") for item in _contexts(row)}
    for question in questions:
        question_id = str(question.get("id") or "")
        if question_id and (question_id in ignored or question_id in linked):
            continue
        score = _question_candidate_score(row, question)
        if score < 25 or _question_candidate_is_safe(row, question):
            continue
        candidates.append({
            "id": question_id,
            "score": score,
            "barcode": _text(question.get("barcode")),
            "merchant_sku": _text(question.get("merchant_sku") or question.get("stock_code")),
            "product_name": _text(question.get("product_name")),
            "question_text": _text(question.get("question_text"))[:220],
            "rejected_reason": "Sipariş numarası veya line id ile doğrulanmadı; ürün benzerliği tek başına kanıt değildir.",
        })
    return sorted(candidates, key=lambda item: item["score"], reverse=True)[:5]


def _has_person_name(row: dict[str, Any]) -> bool:
    person_names = row.get("person_names") if isinstance(row.get("person_names"), list) else []
    return bool([item for item in person_names if _text(item)] or _text(row.get("label_text")) or _text(row.get("name_cut_text")))


def _row_reasons(row: dict[str, Any], questions: list[dict[str, Any]], question_index: dict[str, list[dict[str, Any]]], settings: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    evidence = _has_question_evidence(row)
    candidates: list[dict[str, Any]] = []
    unsafe_candidates: list[dict[str, Any]] = []
    if not evidence:
        if str(settings.get("last_questions_sync_status") or "").upper() == "UNAVAILABLE":
            reasons.append("question_service_unavailable")
        if not questions:
            reasons.append("no_saved_questions")
        else:
            probe = _question_match_probe(row, question_index)
            candidates = _manual_question_candidates(row, questions)
            unsafe_candidates = _unsafe_question_candidates(row, questions)
            reasons.append("question_exists_but_not_attached" if probe == "would_attach" or candidates else "no_matching_question_by_order_barcode_sku")

    image_url, image_source = _image_url(row)
    if not image_url:
        reasons.append("missing_product_image_url")

    product_url, product_url_source, product_url_status = _product_url(row)
    if product_url_status == "missing":
        reasons.append("missing_product_url")
    elif product_url_status == "rejected":
        reasons.append("product_url_rejected_fuzzy_catalog_match")

    if not row.get("mapping_found"):
        reasons.append("missing_product_mapping")
    if str(row.get("production_type") or "") in PRODUCTION_TYPES_REQUIRING_MODEL and not _text(row.get("model_path")):
        reasons.append("missing_model_path")
    if float(row.get("confidence") or 0) < LOW_CONFIDENCE_THRESHOLD:
        reasons.append("ai_low_confidence")
    if not _has_person_name(row):
        reasons.append("no_person_name_found")

    details = {
        "image_url": image_url,
        "image_url_source": image_source,
        "product_url": product_url if product_url_status == "accepted" else "",
        "rejected_product_url": product_url if product_url_status == "rejected" else "",
        "product_url_source": product_url_source,
        "product_url_status": product_url_status,
        "has_question_evidence": evidence,
        "question_candidate_count": len(candidates),
        "question_candidates": candidates,
        "unsafe_question_candidate_count": len(unsafe_candidates),
        "unsafe_question_candidates": unsafe_candidates,
    }
    return list(dict.fromkeys(reasons)), details


def _summarize(rows: list[dict[str, Any]], issues: list[dict[str, Any]]) -> dict[str, Any]:
    reason_counts = Counter(reason for issue in issues for reason in issue["reasons"])
    priority_counts = Counter(issue.get("priority", "low") for issue in issues)
    category_counts = Counter(issue.get("category", "mixed") for issue in issues)
    return {
        "total_rows": len(rows),
        "question_linked": sum(1 for row in rows if _has_question_evidence(row)),
        "evidence_waiting": sum(1 for row in rows if row.get("verification_status") == trendyol_api.VERIFICATION_WAITING_EVIDENCE),
        "verification_pending": sum(1 for row in rows if row.get("verification_status") == trendyol_api.VERIFICATION_WAITING_APPROVAL),
        "ready": sum(1 for row in rows if row.get("status") == "ready" and row.get("verification_status") == trendyol_api.VERIFICATION_READY and bool(row.get("user_verified"))),
        "with_image_url": sum(1 for row in rows if _image_url(row)[0]),
        "missing_image_url": sum(1 for row in rows if not _image_url(row)[0]),
        "with_product_url": sum(1 for row in rows if _product_url(row)[2] == "accepted"),
        "missing_product_url": sum(1 for row in rows if _product_url(row)[2] == "missing"),
        "rejected_product_url": sum(1 for row in rows if _product_url(row)[2] == "rejected"),
        "mapped": sum(1 for row in rows if row.get("mapping_found")),
        "unmapped": sum(1 for row in rows if not row.get("mapping_found")),
        "low_confidence": sum(1 for row in rows if float(row.get("confidence") or 0) < LOW_CONFIDENCE_THRESHOLD),
        "no_person_name": sum(1 for row in rows if not _has_person_name(row)),
        "issue_rows": len(issues),
        "blocks_production": sum(1 for issue in issues if issue.get("blocks_production")),
        "priority_counts": dict(priority_counts.most_common()),
        "category_counts": dict(category_counts.most_common()),
        "reason_counts": dict(reason_counts.most_common()),
    }


def _evidence_gap_summary(rows: list[dict[str, Any]], questions: list[dict[str, Any]], issues: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [row for row in rows if not _has_question_evidence(row)]
    question_order_numbers = {_identity(row.get("order_number")) for row in questions if _identity(row.get("order_number"))}
    question_text_order_numbers = {
        _identity(trendyol_api._detect_question_order_number(row.get("question_text") or row.get("answer_text") or ""))  # noqa: SLF001
        for row in questions
        if trendyol_api._detect_question_order_number(row.get("question_text") or row.get("answer_text") or "")  # noqa: SLF001
    }
    exact_order_hits = [row for row in missing if _identity(row.get("order_number")) in question_order_numbers or _identity(row.get("order_number")) in question_text_order_numbers]
    unsafe_rows = [issue for issue in issues if issue.get("unsafe_question_candidate_count")]
    return {
        "missing_evidence_rows": len(missing),
        "saved_questions": len(questions),
        "questions_with_order_number": len(question_order_numbers.union(question_text_order_numbers)),
        "missing_rows_with_exact_order_question": len(exact_order_hits),
        "product_level_candidate_rows_rejected": len(unsafe_rows),
        "product_level_candidate_note": "Bu adaylar yalnızca ürün/barkod benzerliğine dayanır; sipariş numarası veya line id yoksa otomatik kanıt sayılmaz.",
        "sample_missing_orders": [
            {
                "order_number": row.get("order_number") or "",
                "line_id": row.get("line_id") or "",
                "barcode": row.get("barcode") or "",
                "product_name": _text(row.get("product_name"))[:140],
            }
            for row in missing[:15]
        ],
        "sample_rejected_product_level_candidates": [
            {
                "order_number": issue.get("order_number") or "",
                "line_id": issue.get("line_id") or "",
                "candidate": (issue.get("unsafe_question_candidates") or [{}])[0],
            }
            for issue in unsafe_rows[:10]
        ],
    }


def _recommended_action(reasons: list[str]) -> str:
    reason_set = set(reasons)
    if "question_exists_but_not_attached" in reason_set:
        return "UI'da Aday soru var satırından en iyi soruyu bağla."
    if "no_matching_question_by_order_barcode_sku" in reason_set or "no_saved_questions" in reason_set:
        return "Soruları Oku ile kanıtları yenile; gerekirse soru kanıtları tabında manuel bağla."
    if "missing_product_mapping" in reason_set or "missing_model_path" in reason_set:
        return "Ürün Eşleştirme tabında barkod/SKU model eşleşmesini tamamla."
    if "missing_product_image_url" in reason_set or "missing_product_url" in reason_set or "product_url_rejected_fuzzy_catalog_match" in reason_set:
        return "Ürün kataloğu/görsel önbelleğini kontrol et; link ve görsel alanlarını güncelle."
    if "ai_low_confidence" in reason_set or "no_person_name_found" in reason_set:
        return "Müşteri mesajını kontrol et; isim yoksa alanları boş bırakıp üretim notunu doğrula."
    return "Satırı operatör kontrolünden geçir."
def _recommended_action_code(reasons: list[str]) -> str:
    reason_set = set(reasons)
    if "question_exists_but_not_attached" in reason_set:
        return "bind_candidate_question"
    if "no_matching_question_by_order_barcode_sku" in reason_set or "no_saved_questions" in reason_set or "question_service_unavailable" in reason_set:
        return "refresh_or_manual_question_check"
    if "missing_product_mapping" in reason_set or "missing_model_path" in reason_set:
        return "complete_product_mapping"
    if "missing_product_image_url" in reason_set or "missing_product_url" in reason_set or "product_url_rejected_fuzzy_catalog_match" in reason_set:
        return "fix_product_media"
    if "ai_low_confidence" in reason_set or "no_person_name_found" in reason_set:
        return "manual_ai_review"
    return "operator_review"


def _issue_category(reasons: list[str]) -> str:
    categories = {REASON_CATEGORIES.get(reason, "other") for reason in reasons}
    if len(categories) == 1:
        return next(iter(categories))
    if "evidence" in categories and "extraction" in categories:
        return "evidence_and_extraction"
    if "mapping" in categories:
        return "mapping"
    if "media" in categories:
        return "media"
    return "mixed"


def _issue_priority(reasons: list[str], details: dict[str, Any] | None = None) -> str:
    reason_set = set(reasons)
    details = details or {}
    if "missing_product_mapping" in reason_set or "missing_model_path" in reason_set:
        return "critical"
    if "question_exists_but_not_attached" in reason_set:
        return "high"
    if "no_person_name_found" in reason_set and ("no_matching_question_by_order_barcode_sku" in reason_set or "no_saved_questions" in reason_set):
        return "high"
    if "ai_low_confidence" in reason_set or "no_person_name_found" in reason_set:
        return "medium"
    if details.get("product_url_status") == "rejected":
        return "medium"
    return "low"


def _blocks_production(reasons: list[str]) -> bool:
    blockers = {
        "question_service_unavailable",
        "no_saved_questions",
        "no_matching_question_by_order_barcode_sku",
        "question_exists_but_not_attached",
        "missing_product_mapping",
        "missing_model_path",
        "ai_low_confidence",
        "no_person_name_found",
    }
    return bool(blockers.intersection(reasons))


def _operator_actions(summary: dict[str, Any], issues: list[dict[str, Any]], priorities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    candidate_rows = sum(1 for issue in issues if issue.get("question_candidate_count"))
    if candidate_rows:
        actions.append({
            "title": "Aday soruları bağla",
            "impact": candidate_rows,
            "detail": f"{candidate_rows} satırda kanıt adayı var; UI'daki Aday soru var aksiyonuyla bağlanabilir.",
        })
    if priorities:
        top5 = sum(int(item.get("row_count") or 0) for item in priorities[:5])
        actions.append({
            "title": "İlk 5 ürün eşleştirmesini tamamla",
            "impact": top5,
            "detail": f"İlk 5 eşleşmeyen ürün tamamlanırsa yaklaşık {top5} satır açılır.",
        })
    if summary.get("missing_image_url") or summary.get("missing_product_url") or summary.get("rejected_product_url"):
        media_count = int(summary.get("missing_image_url") or 0) + int(summary.get("missing_product_url") or 0) + int(summary.get("rejected_product_url") or 0)
        actions.append({
            "title": "Görsel/link kaynaklarını düzelt",
            "impact": media_count,
            "detail": "Görsel/link eksikleri üretim kararını yavaşlatıyor; katalog kaynakları kontrol edilmeli.",
        })
    if summary.get("low_confidence") or summary.get("no_person_name"):
        actions.append({
            "title": "AI düşük güven satırlarını gözden geçir",
            "impact": int(summary.get("low_confidence") or 0) + int(summary.get("no_person_name") or 0),
            "detail": "İsim yoksa alan boş kalmalı; düşük güvenli öneriler kullanıcı onayı olmadan aktarılmamalı.",
        })
    return actions


def _mapping_priority_key(row: dict[str, Any]) -> tuple[str, str, str]:
    barcode = _text(row.get("barcode"))
    sku = _sku(row.get("merchant_sku") or row.get("stock_code"))
    product = _text(row.get("product_name"))
    return barcode, sku, product


def _mapping_priorities(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("mapping_found"):
            continue
        key = _mapping_priority_key(row)
        if not any(key):
            continue
        item = grouped.setdefault(key, {
            "barcode": key[0],
            "merchant_sku": key[1],
            "product_name": key[2],
            "row_count": 0,
            "question_linked_count": 0,
            "low_confidence_count": 0,
            "no_person_name_count": 0,
            "sample_order_numbers": [],
            "image_url": "",
            "product_url": "",
            "suggested_action": "Ürün Eşleştirme tabında model ve üretim tipini bağla.",
        })
        item["row_count"] += 1
        if _has_question_evidence(row):
            item["question_linked_count"] += 1
        if float(row.get("confidence") or 0) < LOW_CONFIDENCE_THRESHOLD:
            item["low_confidence_count"] += 1
        if not _has_person_name(row):
            item["no_person_name_count"] += 1
        order_number = _text(row.get("order_number"))
        if order_number and order_number not in item["sample_order_numbers"] and len(item["sample_order_numbers"]) < 5:
            item["sample_order_numbers"].append(order_number)
        if not item["image_url"]:
            item["image_url"] = _image_url(row)[0]
        if not item["product_url"]:
            product_url, _, product_url_status = _product_url(row)
            if product_url_status == "accepted":
                item["product_url"] = product_url
    return sorted(grouped.values(), key=lambda item: (-int(item["row_count"]), item["product_name"]))


def _extraction_debug_summary() -> dict[str, Any]:
    if not DEBUG_LOG_PATH.exists():
        return {"exists": False, "path": str(DEBUG_LOG_PATH.relative_to(PROJECT_ROOT))}
    total = 0
    errors = 0
    fallback_used = 0
    ai_missing = 0
    ai_final_mismatch = 0
    parser_would_have_overridden = 0
    samples: list[dict[str, Any]] = []
    for line in DEBUG_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        error = _text(item.get("error"))
        if error:
            errors += 1
        ai_raw = _text(item.get("ai_raw_json_response"))
        if not ai_raw:
            ai_missing += 1
        final_result = item.get("final_ui_result") if isinstance(item.get("final_ui_result"), dict) else {}
        final_sources = final_result.get("source_evidence") if isinstance(final_result.get("source_evidence"), list) else []
        if any("fallback" in str(source) for source in final_sources) or error:
            fallback_used += 1
        validated = item.get("schema_validation_result") if isinstance(item.get("schema_validation_result"), dict) else {}
        deterministic = item.get("deterministic_parser_result") if isinstance(item.get("deterministic_parser_result"), dict) else {}
        ai_label = _text(validated.get("labelName") or validated.get("label_text"))
        final_label = _text(final_result.get("label_text") or final_result.get("labelName"))
        deterministic_label = _text(deterministic.get("label_text"))
        if ai_label and final_label and ai_label != final_label:
            ai_final_mismatch += 1
        if ai_label and deterministic_label and final_label == deterministic_label and final_label != ai_label:
            parser_would_have_overridden += 1
        if (error or not ai_raw or (ai_label and final_label and ai_label != final_label)) and len(samples) < 8:
            samples.append({
                "created_at": item.get("created_at") or "",
                "order_number": item.get("order_number") or "",
                "error": error,
                "ai_label": ai_label,
                "deterministic_label": deterministic_label,
                "final_label": final_label,
            })
    return {
        "exists": True,
        "path": str(DEBUG_LOG_PATH.relative_to(PROJECT_ROOT)),
        "total_records": total,
        "error_records": errors,
        "ai_raw_missing": ai_missing,
        "fallback_used": fallback_used,
        "ai_final_mismatch": ai_final_mismatch,
        "parser_would_have_overridden": parser_would_have_overridden,
        "samples": samples,
    }


def _write_csv(issues: list[dict[str, Any]]) -> None:
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "order_number",
                "line_id",
                "customer_name",
                "barcode",
                "merchant_sku",
                "product_name",
                "verification_status",
                "priority",
                "category",
                "blocks_production",
                "reasons",
                "image_url_source",
                "product_url_source",
                "rejected_product_url",
                "question_candidate_count",
                "top_question_candidate",
                "unsafe_question_candidate_count",
                "top_unsafe_question_candidate",
                "recommended_action",
                "recommended_action_code",
                "recommended_action_label",
            ],
        )
        writer.writeheader()
        for issue in issues:
            writer.writerow({
                "order_number": issue["order_number"],
                "line_id": issue["line_id"],
                "customer_name": issue["customer_name"],
                "barcode": issue["barcode"],
                "merchant_sku": issue["merchant_sku"],
                "product_name": issue["product_name"],
                "verification_status": issue["verification_status"],
                "priority": issue.get("priority", ""),
                "category": issue.get("category", ""),
                "blocks_production": issue.get("blocks_production", False),
                "reasons": ", ".join(issue["reasons"]),
                "image_url_source": issue["image_url_source"],
                "product_url_source": issue["product_url_source"],
                "rejected_product_url": issue["rejected_product_url"],
                "question_candidate_count": issue.get("question_candidate_count", 0),
                "top_question_candidate": (issue.get("question_candidates") or [{}])[0].get("id", "") if issue.get("question_candidates") else "",
                "unsafe_question_candidate_count": issue.get("unsafe_question_candidate_count", 0),
                "top_unsafe_question_candidate": (issue.get("unsafe_question_candidates") or [{}])[0].get("id", "") if issue.get("unsafe_question_candidates") else "",
                "recommended_action": issue.get("recommended_action", ""),
                "recommended_action_code": issue.get("recommended_action_code", ""),
                "recommended_action_label": issue.get("recommended_action_label", ""),
            })


def _write_mapping_priority_csv(priorities: list[dict[str, Any]]) -> None:
    with MAPPING_PRIORITY_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "row_count",
                "barcode",
                "merchant_sku",
                "product_name",
                "question_linked_count",
                "low_confidence_count",
                "no_person_name_count",
                "sample_order_numbers",
                "image_url",
                "product_url",
                "suggested_action",
            ],
        )
        writer.writeheader()
        for item in priorities:
            writer.writerow({
                **item,
                "sample_order_numbers": ", ".join(item.get("sample_order_numbers") or []),
            })


def _write_markdown(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Trendyol Live Data Audit",
        "",
        f"Created: `{payload['created_at']}`",
        f"Refresh mode: `{payload['refresh_mode']}`",
        "",
        "## Summary",
        "",
        f"- Total rows: `{summary['total_rows']}`",
        f"- Question linked: `{summary['question_linked']}`",
        f"- Evidence waiting: `{summary['evidence_waiting']}`",
        f"- Verification pending: `{summary['verification_pending']}`",
        f"- Ready: `{summary['ready']}`",
        f"- Image URL: `{summary['with_image_url']}` present / `{summary['missing_image_url']}` missing",
        f"- Product URL: `{summary['with_product_url']}` present / `{summary['missing_product_url']}` missing / `{summary['rejected_product_url']}` rejected",
        f"- Mapped: `{summary['mapped']}` / Unmapped: `{summary['unmapped']}`",
        f"- Low confidence: `{summary['low_confidence']}`",
        f"- No person name: `{summary['no_person_name']}`",
        f"- Blocks production: `{summary.get('blocks_production', 0)}`",
        "",
        "## Priority Counts",
        "",
    ]
    if summary.get("priority_counts"):
        lines.extend(f"- `{priority}`: `{count}`" for priority, count in summary["priority_counts"].items())
    else:
        lines.append("- No priority counts.")
    lines.extend([
        "",
        "## Category Counts",
        "",
    ])
    if summary.get("category_counts"):
        lines.extend(f"- `{category}`: `{count}`" for category, count in summary["category_counts"].items())
    else:
        lines.append("- No category counts.")
    lines.extend([
        "",
        "## Reason Counts",
        "",
    ])
    if summary["reason_counts"]:
        lines.extend(f"- `{reason}`: `{count}` - {REASON_LABELS.get(reason, reason)}" for reason, count in summary["reason_counts"].items())
    else:
        lines.append("- No issue reasons detected.")
    lines.extend(["", "## Operator Actions", ""])
    actions = payload.get("operator_actions") or []
    if actions:
        lines.extend(f"- **{item['title']}** (`{item['impact']}`): {item['detail']}" for item in actions)
    else:
        lines.append("- Açık operatör aksiyonu yok.")
    lines.extend(["", "## First Issue Rows", ""])
    for issue in payload["issues"][:25]:
        candidate_note = ""
        if issue.get("question_candidate_count"):
            top = (issue.get("question_candidates") or [{}])[0]
            candidate_note = f" · aday soru: `{top.get('id', '')}` skor `{top.get('score', '')}`"
        lines.append(
            f"- `{issue['order_number']}` / `{issue['line_id']}` / `{issue['barcode']}`: "
            f"{', '.join(f'`{reason}`' for reason in issue['reasons'])}{candidate_note}"
            f" · {issue.get('recommended_action', '')}"
        )
    evidence_gap = payload.get("evidence_gap_summary") or {}
    lines.extend(["", "## Evidence Gap", ""])
    lines.extend([
        f"- Missing evidence rows: `{evidence_gap.get('missing_evidence_rows', 0)}`",
        f"- Saved questions: `{evidence_gap.get('saved_questions', 0)}`",
        f"- Questions with exact order number: `{evidence_gap.get('questions_with_order_number', 0)}`",
        f"- Missing rows with exact order question: `{evidence_gap.get('missing_rows_with_exact_order_question', 0)}`",
        f"- Product-level candidates rejected: `{evidence_gap.get('product_level_candidate_rows_rejected', 0)}`",
        f"- Note: {evidence_gap.get('product_level_candidate_note', '')}",
    ])
    rejected = evidence_gap.get("sample_rejected_product_level_candidates") or []
    if rejected:
        lines.extend(["", "Rejected product-level candidate samples:"])
        for item in rejected[:8]:
            candidate = item.get("candidate") or {}
            lines.append(
                f"- `{item.get('order_number', '')}` / `{item.get('line_id', '')}`: "
                f"candidate `{candidate.get('id', '')}` score `{candidate.get('score', '')}` - {candidate.get('rejected_reason', '')}"
            )
    debug = payload.get("extraction_debug_summary") or {}
    lines.extend(["", "## Extraction Debug", ""])
    if debug.get("exists"):
        lines.extend([
            f"- Total records: `{debug.get('total_records', 0)}`",
            f"- Error records: `{debug.get('error_records', 0)}`",
            f"- AI raw missing: `{debug.get('ai_raw_missing', 0)}`",
            f"- Fallback used: `{debug.get('fallback_used', 0)}`",
            f"- AI/final mismatch: `{debug.get('ai_final_mismatch', 0)}`",
            f"- Parser override risk: `{debug.get('parser_would_have_overridden', 0)}`",
        ])
        samples = debug.get("samples") or []
        if samples:
            lines.append("")
            lines.append("Samples:")
            for item in samples:
                lines.append(f"- `{item.get('order_number', '')}`: AI `{item.get('ai_label', '')}` / parser `{item.get('deterministic_label', '')}` / final `{item.get('final_label', '')}` / error `{item.get('error', '')}`")
    else:
        lines.append("- Extraction debug log yok.")
    lines.extend(["", "## Mapping Priorities", ""])
    priorities = payload.get("mapping_priorities") or []
    if priorities:
        lines.append("Önce çok tekrar eden barkod/SKU kayıtlarını eşleştirin; her satır bir kez bağlanınca ilgili siparişlerin tamamı açılır.")
        lines.append("")
        for item in priorities[:20]:
            lines.append(
                f"- `{item['row_count']}` satır · `{item['barcode'] or '-'}` / `{item['merchant_sku'] or '-'}` · "
                f"{item['product_name'][:140]}"
            )
    else:
        lines.append("- Eşleşmemiş ürün önceliği yok.")
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- JSON: `{JSON_PATH}`",
            f"- CSV: `{CSV_PATH}`",
            f"- Mapping priority CSV: `{MAPPING_PRIORITY_CSV_PATH}`",
        ]
    )
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_audit(*, refresh: bool = False) -> dict[str, Any]:
    refresh_result: dict[str, Any] | None = None
    if refresh:
        refresh_result = trendyol_api.sync_recent_orders(PROJECT_ROOT, days=7)
    rows = trendyol_api.list_suggestions(PROJECT_ROOT)
    questions = trendyol_api.list_questions(PROJECT_ROOT)
    settings = trendyol_api.get_settings(PROJECT_ROOT, masked=True)
    question_index = trendyol_api._question_context_index(questions)  # noqa: SLF001
    issues: list[dict[str, Any]] = []
    for row in rows:
        reasons, details = _row_reasons(row, questions, question_index, settings)
        if not reasons:
            continue
        action_code = _recommended_action_code(reasons)
        action_meta = ACTION_METADATA.get(action_code, ACTION_METADATA["operator_review"])
        issues.append({
            "id": row.get("id") or "",
            "order_number": row.get("order_number") or "",
            "line_id": row.get("line_id") or "",
            "customer_name": _text(row.get("customer_name")),
            "product_name": _text(row.get("product_name")),
            "barcode": row.get("barcode") or "",
            "merchant_sku": _sku(row.get("merchant_sku") or row.get("stock_code")),
            "verification_status": row.get("verification_status") or "",
            "status": row.get("status") or "",
            "confidence": row.get("confidence") or 0,
            "mapping_found": bool(row.get("mapping_found")),
            "model_path": row.get("model_path") or "",
            "label_text": _text(row.get("label_text")),
            "name_cut_text": _text(row.get("name_cut_text")),
            "reasons": reasons,
            "reason_labels": [REASON_LABELS.get(reason, reason) for reason in reasons],
            "priority": _issue_priority(reasons, details),
            "category": _issue_category(reasons),
            "blocks_production": _blocks_production(reasons),
            "recommended_action_code": action_code,
            "recommended_action_label": action_meta["label"],
            "recommended_action_description": action_meta["description"],
            "recommended_action": _recommended_action(reasons),
            **details,
        })
    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    issues.sort(key=lambda item: (priority_rank.get(str(item.get("priority") or "low"), 4), str(item.get("order_number") or ""), str(item.get("line_id") or "")))
    priorities = _mapping_priorities(rows)
    summary = _summarize(rows, issues)
    payload = {
        "status": "PASSED",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "refresh_mode": refresh,
        "refresh_result": {
            "status": refresh_result.get("status"),
            "message": refresh_result.get("message"),
        } if isinstance(refresh_result, dict) else None,
        "settings": {
            "configured": bool(settings.get("configured")),
            "environment": settings.get("environment"),
            "last_sync_at": settings.get("last_sync_at"),
            "last_questions_sync_at": settings.get("last_questions_sync_at"),
            "last_questions_sync_status": settings.get("last_questions_sync_status"),
            "last_questions_sync_message": settings.get("last_questions_sync_message"),
            "ai_enabled": bool(settings.get("ai_enabled")),
            "ai_configured": bool(settings.get("ai_configured")),
        },
        "source_files": {
            "suggestions": str(trendyol_api.suggestions_path(PROJECT_ROOT).relative_to(PROJECT_ROOT)),
            "questions": str(trendyol_api.questions_path(PROJECT_ROOT).relative_to(PROJECT_ROOT)),
            "settings": str(trendyol_api.settings_path(PROJECT_ROOT).relative_to(PROJECT_ROOT)),
        },
        "summary": summary,
        "evidence_gap_summary": _evidence_gap_summary(rows, questions, issues),
        "operator_actions": _operator_actions(summary, issues, priorities),
        "extraction_debug_summary": _extraction_debug_summary(),
        "mapping_priorities": priorities,
        "issues": issues,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Refresh read-only Trendyol order/question data before auditing.")
    args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = run_audit(refresh=args.refresh)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(payload["issues"])
    _write_mapping_priority_csv(payload["mapping_priorities"])
    _write_markdown(payload)
    print(json.dumps({
        "status": payload["status"],
        "summary": payload["summary"],
        "json_report": str(JSON_PATH),
        "markdown_report": str(MD_PATH),
        "csv_report": str(CSV_PATH),
        "mapping_priority_csv": str(MAPPING_PRIORITY_CSV_PATH),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
