from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from intelligence.text_cleanup import repair_text, title_turkish_name
from intelligence.trendyol_ai_extractor import DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_MODEL as DEFAULT_AI_MODEL
from intelligence.trendyol_ai_extractor import extract_with_ai_or_fallback, extract_with_cloud_ai, is_ai_configured, record_learning_example
from intelligence.trendyol_order_extractor import extract_production_fields
from webui_backend import customer_order_api, file_api, trendyol_mapping_api


LIVE_BASE_URL = "https://apigw.trendyol.com/integration"
LIVE_BASE_URL_V2 = "https://apigw.trendyol.com"
STAGE_BASE_URL = "https://stageapigw.trendyol.com/integration"
STAGE_BASE_URL_V2 = "https://stageapigw.trendyol.com"
AI_AUTONOMOUS_MODEL_THRESHOLD = 0.72
AI_AUTONOMOUS_FIELD_THRESHOLD = 0.65
AI_DEFAULT_TIMEOUT_SECONDS = 20
VERIFICATION_READY = "uretime_hazir"
VERIFICATION_TRANSFERRED = "aktarildi"
VERIFICATION_WAITING_EVIDENCE = "kanit_bekliyor"
VERIFICATION_USER_REVIEW = "kullanici_kontrol_gerekli"
VERIFICATION_WAITING_APPROVAL = "alanlar_onay_bekliyor"
QUESTION_EVIDENCE_STATUSES = ["WAITING_FOR_ANSWER", "ANSWERED", "REJECTED", "REPORTED"]
QUESTION_LOOKBACK_DAYS = 14
QUESTION_MAX_PAGES = 10
QUESTION_PAGE_SIZE = 50
QUESTION_REQUEST_TIMEOUT_SECONDS = 8
ORDER_NUMBER_PATTERNS = [
    re.compile(r"#(\d{8,})"),
    re.compile(r"sipari[şs]\s*(?:no|numaram?|numarası|numarasi|numaralı|numarali)?[:\s#-]*(\d{8,})", re.IGNORECASE),
    re.compile(r"\b(\d{10,})\b"),
]

# Rate-limit / retry constants
_RETRY_ON_CODES = {429, 502, 503}
_REQUEST_INTER_DELAY = 0.05   # seconds between sequential list API requests
_ITEMS_INTER_DELAY = 0.10     # seconds between per-package items requests


def settings_path(project_root: Path) -> Path:
    path = project_root / "data" / "trendyol_settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def suggestions_path(project_root: Path) -> Path:
    path = project_root / "data" / "trendyol_production_suggestions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def mapping_suggestions_path(project_root: Path) -> Path:
    path = project_root / "data" / "trendyol_mapping_suggestions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def questions_path(project_root: Path) -> Path:
    path = project_root / "data" / "trendyol_questions_context.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def readonly_orders_cache_path(project_root: Path) -> Path:
    path = project_root / "data" / "trendyol_readonly_orders_cache.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_cached_orders_by_package_id(project_root: Path) -> dict[str, dict[str, Any]]:
    """Return existing cached orders indexed by shipmentPackageId."""
    path = readonly_orders_cache_path(project_root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        orders = data.get("orders") or [] if isinstance(data, dict) else []
        return {
            str(o.get("shipmentPackageId") or ""): o
            for o in orders
            if isinstance(o, dict) and o.get("shipmentPackageId")
        }
    except (json.JSONDecodeError, OSError):
        return {}


def image_cache_dir(project_root: Path) -> Path:
    path = project_root / "data" / "trendyol_image_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_settings(project_root: Path, *, masked: bool = True) -> dict[str, Any]:
    path = settings_path(project_root)
    if not path.exists():
        data: dict[str, Any] = {}
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    normalized = {
        "supplier_id": str(data.get("supplier_id") or "").strip(),
        "api_key": str(data.get("api_key") or "").strip(),
        "api_secret": str(data.get("api_secret") or "").strip(),
        "stage": bool(data.get("stage", False)),
        "environment": "stage" if bool(data.get("stage", False)) else "live",
        "read_only_mode": _safe_bool(data.get("read_only_mode"), True),
        "last_sync_at": str(data.get("last_sync_at") or ""),
        "last_questions_sync_at": str(data.get("last_questions_sync_at") or ""),
        "last_questions_sync_status": str(data.get("last_questions_sync_status") or ""),
        "last_questions_sync_message": str(data.get("last_questions_sync_message") or ""),
        "last_orders_sync_status": str(data.get("last_orders_sync_status") or ""),
        "last_orders_sync_message": str(data.get("last_orders_sync_message") or ""),
        "last_orders_count": int(data.get("last_orders_count") or 0),
        "last_messages_count": int(data.get("last_messages_count") or 0),
        "ai_autonomous_production_enabled": _safe_bool(data.get("ai_autonomous_production_enabled"), True),
        "ai_autonomous_model_threshold": float(data.get("ai_autonomous_model_threshold") or AI_AUTONOMOUS_MODEL_THRESHOLD),
        "ai_autonomous_field_threshold": float(data.get("ai_autonomous_field_threshold") or AI_AUTONOMOUS_FIELD_THRESHOLD),
        "ai_enabled": _safe_bool(data.get("ai_enabled"), False),
        "ai_provider": str(data.get("ai_provider") or "openai_compatible").strip(),
        "ai_api_key": str(data.get("ai_api_key") or "").strip(),
        "ai_model": str(data.get("ai_model") or DEFAULT_AI_MODEL).strip(),
        "ai_confidence_threshold": float(data.get("ai_confidence_threshold") or DEFAULT_CONFIDENCE_THRESHOLD),
        "ai_timeout_seconds": float(data.get("ai_timeout_seconds") or AI_DEFAULT_TIMEOUT_SECONDS),
        "ai_cache_enabled": _safe_bool(data.get("ai_cache_enabled"), True),
        "last_orders_sync_at": str(data.get("last_orders_sync_at") or data.get("last_sync_at") or ""),
        "auto_sync_enabled": _safe_bool(data.get("auto_sync_enabled"), False),
        "auto_sync_interval_sec": max(10, int(data.get("auto_sync_interval_sec") or 30)),
    }
    if masked:
        normalized["api_key"] = _mask(normalized["api_key"])
        normalized["api_secret"] = _mask(normalized["api_secret"])
        normalized["ai_configured"] = bool(normalized["ai_enabled"] and normalized["ai_api_key"])
        normalized["ai_api_key"] = _mask(normalized["ai_api_key"])
        normalized["configured"] = is_configured(project_root)
        if not normalized["configured"]:
            normalized["connection_status"] = "Eksik credential"
        elif normalized.get("last_orders_sync_status") == "OK" or normalized.get("last_questions_sync_status") == "OK":
            normalized["connection_status"] = "Read-only senkron hazır"
        elif normalized.get("last_orders_sync_status") or normalized.get("last_questions_sync_status"):
            normalized["connection_status"] = normalized.get("last_orders_sync_message") or normalized.get("last_questions_sync_message") or "Kontrol gerekli"
        else:
            normalized["connection_status"] = "Ayar kaydedildi, sync bekliyor"
    return normalized


def save_settings(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    current = get_settings(project_root, masked=False)
    api_key_payload = str(payload.get("api_key") or "").strip()
    api_secret_payload = str(payload.get("api_secret") or "").strip()
    ai_key_payload = str(payload.get("ai_api_key") or "").strip()
    if "environment" in payload:
        stage = str(payload.get("environment") or "").lower() == "stage"
    elif "stage" in payload:
        stage = _safe_bool(payload.get("stage"), False)
    else:
        stage = bool(current.get("stage", False))
    merged = {
        **current,
        "supplier_id": str(payload.get("supplier_id") or current.get("supplier_id") or "").strip(),
        "api_key": current.get("api_key") if _is_masked_secret(api_key_payload) else (api_key_payload or current.get("api_key") or ""),
        "api_secret": current.get("api_secret") if _is_masked_secret(api_secret_payload) else (api_secret_payload or current.get("api_secret") or ""),
        "stage": stage,
        "read_only_mode": True,
        "last_sync_at": current.get("last_sync_at") or "",
        "last_questions_sync_at": current.get("last_questions_sync_at") or "",
        "last_questions_sync_status": current.get("last_questions_sync_status") or "",
        "last_questions_sync_message": current.get("last_questions_sync_message") or "",
        "last_orders_sync_status": current.get("last_orders_sync_status") or "",
        "last_orders_sync_message": current.get("last_orders_sync_message") or "",
        "last_orders_count": int(current.get("last_orders_count") or 0),
        "last_messages_count": int(current.get("last_messages_count") or 0),
        "ai_autonomous_production_enabled": _safe_bool(payload.get("ai_autonomous_production_enabled"), _safe_bool(current.get("ai_autonomous_production_enabled"), True)),
        "ai_autonomous_model_threshold": float(payload.get("ai_autonomous_model_threshold") or current.get("ai_autonomous_model_threshold") or AI_AUTONOMOUS_MODEL_THRESHOLD),
        "ai_autonomous_field_threshold": float(payload.get("ai_autonomous_field_threshold") or current.get("ai_autonomous_field_threshold") or AI_AUTONOMOUS_FIELD_THRESHOLD),
        "ai_enabled": _safe_bool(payload.get("ai_enabled"), _safe_bool(current.get("ai_enabled"), False)),
        "ai_provider": str(payload.get("ai_provider") or current.get("ai_provider") or "openai_compatible").strip(),
        "ai_api_key": current.get("ai_api_key") if _is_masked_secret(ai_key_payload) else (ai_key_payload or current.get("ai_api_key") or ""),
        "ai_model": str(payload.get("ai_model") or current.get("ai_model") or DEFAULT_AI_MODEL).strip(),
        "ai_confidence_threshold": float(payload.get("ai_confidence_threshold") or current.get("ai_confidence_threshold") or DEFAULT_CONFIDENCE_THRESHOLD),
        "ai_timeout_seconds": float(payload.get("ai_timeout_seconds") or current.get("ai_timeout_seconds") or AI_DEFAULT_TIMEOUT_SECONDS),
        "ai_cache_enabled": _safe_bool(payload.get("ai_cache_enabled"), _safe_bool(current.get("ai_cache_enabled"), True)),
        "last_orders_sync_at": current.get("last_orders_sync_at") or current.get("last_sync_at") or "",
        "auto_sync_enabled": _safe_bool(payload.get("auto_sync_enabled"), _safe_bool(current.get("auto_sync_enabled"), False)),
        "auto_sync_interval_sec": max(10, int(payload.get("auto_sync_interval_sec") or current.get("auto_sync_interval_sec") or 30)),
    }
    merged["environment"] = "stage" if merged["stage"] else "live"
    settings_path(project_root).write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "OK", "message": "Trendyol API ayarları yerel olarak kaydedildi.", "settings": get_settings(project_root)}


def is_configured(project_root: Path) -> bool:
    settings = get_settings(project_root, masked=False)
    return bool(settings.get("supplier_id") and settings.get("api_key") and settings.get("api_secret"))


def test_connection(project_root: Path) -> dict[str, Any]:
    if not is_configured(project_root):
        return {"status": "CONFIG_MISSING", "ok": False, "message": "Trendyol API ayarları eksik. Secret değerler gösterilmez."}
    settings = get_settings(project_root, masked=False)
    problem = _credential_configuration_problem(settings)
    if problem:
        return {"status": "CONFIG_INVALID", "ok": False, "message": problem}
    try:
        products, packages = _test_connection_probe(project_root)
    except Exception as exc:  # noqa: BLE001
        message = _trendyol_connection_message(str(exc), stage=bool(settings.get("stage")))
        if settings.get("stage"):
            try:
                live_products, live_packages = _test_connection_probe(project_root, force_stage=False)
            except Exception:
                return {"status": "ERROR", "ok": False, "message": message}
            return {
                "status": "ENV_MISMATCH",
                "ok": False,
                "message": (
                    "Stage/test ortamı açık görünüyor; aynı bilgiler canlı Trendyol endpointinde yanıt verdi. "
                    "Canlı API bilgileri kullanıyorsanız Stage/test kutusunu kapatıp ayarları kaydedin, sonra tekrar test edin."
                ),
                "products": live_products.get("totalElements", 0),
                "packages": live_packages.get("totalItemCount", 0),
            }
        return {"status": "ERROR", "ok": False, "message": message}
    return {
        "status": "OK",
        "ok": True,
        "message": "Trendyol bağlantısı başarılı.",
        "products": products.get("totalElements", 0),
        "packages": packages.get("totalItemCount", 0),
    }

def sync_recent_orders(
    project_root: Path,
    days: int = 2,
    label_models: list[dict[str, Any]] | None = None,
    *,
    incremental: bool = True,
) -> dict[str, Any]:
    if not is_configured(project_root):
        _save_orders_sync_status(project_root, "CONFIG_MISSING", "Trendyol API ayarları eksik.", 0, 0)
        return {"status": "CONFIG_MISSING", "message": "Trendyol API ayarları eksik. Read-only sync başlatılmadı.", "suggestions": list_suggestions(project_root), "settings": get_settings(project_root)}
    settings = get_settings(project_root, masked=False)
    problem = _credential_configuration_problem(settings)
    if problem:
        _save_orders_sync_status(project_root, "CONFIG_INVALID", problem, 0, 0)
        return {"status": "CONFIG_INVALID", "message": problem, "suggestions": list_suggestions(project_root), "settings": get_settings(project_root)}
    end = datetime.now()
    # Determine API window start — incremental uses last_orders_sync_at
    last_sync_str = settings.get("last_orders_sync_at") or settings.get("last_sync_at") or ""
    if incremental and last_sync_str:
        try:
            last_dt = datetime.strptime(last_sync_str[:19], "%Y-%m-%d %H:%M:%S")
            # 1-hour buffer to catch orders modified just before last sync
            api_start = max(last_dt - timedelta(hours=1), end - timedelta(days=14))
        except ValueError:
            api_start = end - timedelta(days=max(1, min(days, 14)))
    else:
        api_start = end - timedelta(days=max(1, min(days, 14)))
    # Load existing cache for merge + skip optimisation
    cached_by_id = _load_cached_orders_by_package_id(project_root) if incremental else {}
    skip_ids: set[str] = set(cached_by_id.keys())
    try:
        # Only pass skip_package_ids when there are known packages to skip —
        # avoids breaking callers that patched fetch_orders without **kwargs
        _fetch_kw: dict[str, Any] = {}
        if incremental and skip_ids:
            _fetch_kw["skip_package_ids"] = skip_ids
        new_orders = fetch_orders(project_root, api_start, end, **_fetch_kw)
        # Merge: existing cached orders + new orders (new overwrites by package_id)
        if incremental and cached_by_id:
            merged_map = dict(cached_by_id)
            for order in new_orders:
                pid = str(order.get("shipmentPackageId") or "")
                if pid:
                    merged_map[pid] = order
            raw_orders = list(merged_map.values())
        else:
            raw_orders = new_orders
        raw_orders = enrich_orders_with_product_catalog(project_root, raw_orders)
        question_rows = _refresh_questions_safely(project_root)
    except Exception as exc:  # noqa: BLE001
        detail = _safe_trendyol_service_message(str(exc), stage=bool(settings.get("stage")))
        _save_orders_sync_status(project_root, "UNAVAILABLE", detail, 0, len(list_questions(project_root)))
        return {
            "status": "UNAVAILABLE",
            "message": f"Trendyol read-only sync tamamlanamadı; canlı sipariş statüsü, kargo veya fatura tetiklenmedi. Detay: {detail}",
            "suggestions": list_suggestions(project_root),
            "questions": list_questions(project_root),
            "settings": get_settings(project_root),
        }
    _save_readonly_orders_cache(project_root, raw_orders, start=api_start, end=end, questions=question_rows)
    suggestions = build_suggestions_from_orders(
        project_root,
        raw_orders,
        label_models=label_models,
        questions=question_rows,
        run_ai=False,
        reuse_existing=True,
    )
    _save_suggestions(project_root, suggestions)
    new_count = len(new_orders)
    total_count = len(raw_orders)
    _save_orders_sync_status(
        project_root, "OK",
        f"{total_count} sipariş paketi ({new_count} yeni) ve {len(question_rows)} soru/mesaj kanıtı read-only çekildi.",
        total_count, len(question_rows),
    )
    return {
        "status": "OK",
        "message": (
            f"{len(suggestions)} Trendyol üretim önerisi hazırlandı "
            f"({new_count} yeni sipariş). Read-only mod: Trendyol statüsü, kargo ve fatura tetiklenmedi."
        ),
        "suggestions": suggestions,
        "questions": question_rows,
        "settings": get_settings(project_root),
        "sync_summary": {
            "orders": total_count,
            "new_orders": new_count,
            "messages": len(question_rows),
            "read_only_mode": True,
            "marketplace_status_changed": False,
            "cargo_invoice_triggered": False,
        },
    }


def _refresh_questions_safely(project_root: Path) -> list[dict[str, Any]]:
    """Best-effort question context refresh for production suggestions.

    Questions are read-only evidence. Failures never block order sync.
    """
    rows = list_questions(project_root)
    if not is_configured(project_root):
        return rows
    fetched: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        fetched.extend(fetch_latest_questions(project_root))
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))
    if fetched:
        product_index = _cached_product_reference_index(project_root)
        rows = _dedupe_questions([_normalize_question_context(project_root, question, product_index=product_index) for question in fetched] + rows)
        _save_questions(project_root, rows)
        _refresh_saved_suggestions_with_questions(project_root, rows, run_extraction=False)
        _save_question_sync_status(project_root, "OK", f"{len(rows)} Trendyol soru/mesaj kanıtı yenilendi.")
    elif errors:
        settings = get_settings(project_root, masked=False)
        message = _safe_trendyol_service_message(errors[0], stage=bool(settings.get("stage")))
        _save_question_sync_status(project_root, "UNAVAILABLE", message)
    return rows


def _save_readonly_orders_cache(
    project_root: Path,
    orders: list[dict[str, Any]],
    *,
    start: datetime,
    end: datetime,
    questions: list[dict[str, Any]] | None = None,
) -> None:
    cache = {
        "created_at": _now(),
        "source": "trendyol",
        "source_label": "Trendyol",
        "mode": "read_only",
        "read_only_mode": True,
        "marketplace_status_changed": False,
        "cargo_invoice_triggered": False,
        "date_range": {
            "start": start.isoformat(timespec="seconds"),
            "end": end.isoformat(timespec="seconds"),
        },
        "order_count": len(orders or []),
        "message_count": len(questions or []),
        "orders": orders or [],
    }
    readonly_orders_cache_path(project_root).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_orders_sync_status(project_root: Path, status: str, message: str, order_count: int, message_count: int) -> None:
    settings = get_settings(project_root, masked=False)
    _ts = _now()
    settings["last_sync_at"] = _ts
    settings["last_orders_sync_at"] = _ts
    settings["last_orders_sync_status"] = status
    settings["last_orders_sync_message"] = _safe_trendyol_service_message(message, stage=bool(settings.get("stage"))) if status not in {"OK", "CONFIG_MISSING"} else message
    settings["last_orders_count"] = int(order_count or 0)
    settings["last_messages_count"] = int(message_count or 0)
    settings["read_only_mode"] = True
    settings_path(project_root).write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_products(project_root: Path, *, max_pages: int = 10, page_size: int = 200) -> list[dict[str, Any]]:
    supplier = _supplier_id(project_root)
    products: list[dict[str, Any]] = []
    page = 0
    while page < max_pages:
        data = _fetch_json(project_root, f"/product/sellers/{supplier}/products?page={page}&size={page_size}", v2=False)
        content = data.get("content") or []
        if not isinstance(content, list):
            break
        products.extend(row for row in content if isinstance(row, dict))
        if len(content) < page_size:
            break
        page += 1
    return products


def trendyol_products_path(project_root: Path) -> Path:
    p = project_root / "data" / "trendyol_products.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def sync_products(project_root: Path, *, max_pages: int = 50, page_size: int = 200) -> dict[str, Any]:
    """Fetch ALL Trendyol products (paginated) and write to data/trendyol_products.json.

    READ-ONLY: never triggers orders, status, cargo or billing.
    Returns {status, count, synced_at} on success.
    """
    if not is_configured(project_root):
        return {
            "status": "CONFIG_MISSING",
            "error": "Trendyol API ayarları eksik. Credential girilmeden ürün kataloğu çekilemez.",
            "count": 0,
        }
    settings = get_settings(project_root, masked=False)
    problem = _credential_configuration_problem(settings)
    if problem:
        return {"status": "CONFIG_INVALID", "error": problem, "count": 0}

    try:
        all_products = fetch_products(project_root, max_pages=max_pages, page_size=page_size)
    except Exception as exc:  # noqa: BLE001
        detail = _safe_trendyol_service_message(str(exc), stage=bool(settings.get("stage")))
        return {"status": "ERROR", "error": detail, "count": 0}

    catalog: dict[str, Any] = {}
    for prod in all_products:
        if not isinstance(prod, dict):
            continue
        barkod = str(prod.get("barcode") or prod.get("sellerBarcode") or "").strip()
        if not barkod:
            continue
        catalog[barkod] = {
            "barkod": barkod,
            # productCode = Trendyol'un gösterdiği model kodu (ör: "ADE-001")
            # stockCode   = satıcının SKU kodu (yedek)
            "model_code": str(
                prod.get("productCode") or prod.get("stockCode") or prod.get("sellerBarcode") or ""
            ),
            "title": str(prod.get("title") or prod.get("name") or ""),
            "image_url": str(
                prod.get("images", [{}])[0].get("url") if isinstance(prod.get("images"), list) and prod.get("images") else ""
            ),
            "sale_status": str(prod.get("onSale") or prod.get("saleStatus") or ""),
            "synced_at": _now(),
        }

    synced_at = _now()
    trendyol_products_path(project_root).write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "status": "OK",
        "count": len(catalog),
        "synced_at": synced_at,
        "message": f"{len(catalog)} Trendyol ürünü kataloga yazıldı. Read-only: durum/kargo/fatura tetiklenmedi.",
    }


def enrich_orders_with_product_catalog(project_root: Path, orders: list[dict[str, Any]], *, max_pages: int = 10) -> list[dict[str, Any]]:
    """Attach product catalog details such as image URL to order lines.

    Trendyol order/package endpoints do not always include product images. The
    catalog endpoint usually does, so order sync enriches lines by barcode,
    merchantSku or stockCode before production suggestions are created.
    """

    index = _cached_product_reference_index(project_root)
    try:
        products = fetch_products(project_root, max_pages=max_pages)
        index = {**index, **_product_catalog_index(products)}
    except Exception:
        pass
    if not index:
        return orders
    enriched_orders: list[dict[str, Any]] = []
    for order in orders:
        if not isinstance(order, dict):
            enriched_orders.append(order)
            continue
        copy_order = dict(order)
        lines = copy_order.get("lines") or copy_order.get("items") or []
        if isinstance(lines, list):
            copy_order["lines"] = [_enrich_line_with_catalog(line, index) if isinstance(line, dict) else line for line in lines]
        enriched_orders.append(copy_order)
    return enriched_orders


def sync_questions(project_root: Path, status: str = "") -> dict[str, Any]:
    if not is_configured(project_root):
        _save_question_sync_status(project_root, "CONFIG_MISSING", "Trendyol API ayarları eksik.")
        return {
            "status": "CONFIG_MISSING",
            "message": "Trendyol API ayarları eksik. Sorular sadece ayarlar girildikten sonra read-only çekilir.",
            "questions": list_questions(project_root),
            "settings": get_settings(project_root),
        }
    raw_questions: list[dict[str, Any]] = []
    try:
        raw_questions.extend(fetch_latest_questions(project_root, status=status))
    except Exception as exc:  # noqa: BLE001
        settings = get_settings(project_root, masked=False)
        detail = _safe_trendyol_service_message(str(exc), stage=bool(settings.get("stage")))
        _save_question_sync_status(project_root, "UNAVAILABLE", detail)
        return {
            "status": "UNAVAILABLE",
            "message": (
                "Trendyol soru/mesaj servisi şu an yanıt vermiyor; mevcut kayıtlar korundu. "
                "Sipariş çekme ve üretim önerileri bundan etkilenmez. "
                f"Detay: {detail}"
            ),
            "questions": list_questions(project_root),
            "settings": get_settings(project_root),
        }
    product_index = _cached_product_reference_index(project_root)
    rows = _dedupe_questions([_normalize_question_context(project_root, question, product_index=product_index) for question in raw_questions])
    _save_questions(project_root, rows)
    updated_suggestions = _refresh_saved_suggestions_with_questions(project_root, rows, run_extraction=False)
    latest_question_time = rows[0].get("last_modified_at") or rows[0].get("created_date") or rows[0].get("created_at") if rows else ""
    latest_suffix = f" En güncel soru: {latest_question_time}." if latest_question_time else ""
    _save_question_sync_status(project_root, "OK", f"{len(rows)} Trendyol soru/mesaj kaydı read-only çekildi.{latest_suffix}")
    return {
        "status": "OK",
        "message": f"{len(rows)} Trendyol soru/mesaj kaydı read-only çekildi. {updated_suggestions} mevcut sipariş önerisi soru kanıtıyla güncellendi; otomatik cevap veya üretim yapılmadı.{latest_suffix}",
        "questions": rows,
        "suggestions": list_suggestions(project_root),
        "settings": get_settings(project_root),
        "sync_summary": {
            "messages": len(rows),
            "read_only_mode": True,
            "marketplace_status_changed": False,
            "cargo_invoice_triggered": False,
        },
    }


def propose_mapping_from_catalog(project_root: Path, label_models: list[dict[str, Any]], *, max_pages: int = 10) -> dict[str, Any]:
    if not is_configured(project_root):
        return {
            "status": "CONFIG_MISSING",
            "message": "Trendyol API ayarları eksik. Katalogdan eşleştirme önerisi üretilemedi.",
            "suggestions": list_mapping_suggestions(project_root),
        }
    products = fetch_products(project_root, max_pages=max_pages)
    existing = trendyol_mapping_api.list_product_mappings(project_root)
    existing_keys = {
        _identity_key(row.get("barcode"))
        or _identity_key(row.get("merchant_sku"))
        or _identity_key(row.get("stock_code"))
        for row in existing
    }
    existing_keys.discard("")
    suggestions: list[dict[str, Any]] = []
    for product in products:
        normalized = _normalize_product(product)
        identity = _identity_key(normalized.get("barcode")) or _identity_key(normalized.get("merchant_sku")) or _identity_key(normalized.get("stock_code"))
        if identity and identity in existing_keys:
            continue
        model, score, reasons = _guess_label_model(normalized, label_models)
        production_type = "label" if model and score >= 0.72 else "review"
        if production_type == "review" and _looks_like_label_product(normalized):
            production_type = "label"
            reasons.append("Ürün adı kişiye özel etiket/baskı/çikolata üretimi gibi görünüyor; model kullanıcı tarafından seçilmeli.")
        if _looks_like_name_cut(normalized):
            production_type = "label_and_name_cut" if production_type == "label" else "name_cut"
        suggestion_status = "suggested" if model and score >= 0.72 and production_type != "review" else "needs_review"
        suggestions.append(
            {
                **normalized,
                "production_type": production_type,
                "model_key": str(model.get("model_no") or "") if model else "",
                "model_path": str(model.get("path") or "") if model else "",
                "model_name": str(model.get("model_name") or model.get("title") or "") if model else "",
                "confidence": round(score, 2),
                "reasons": reasons,
                "status": suggestion_status,
                "active": True,
                "created_at": _now(),
            }
        )
    _save_mapping_suggestions(project_root, suggestions)
    return {
        "status": "OK",
        "message": f"{len(suggestions)} Trendyol katalog eşleştirme önerisi hazırlandı. Otomatik kaydedilmedi.",
        "product_count": len(products),
        "suggestions": suggestions,
    }


def fetch_orders(
    project_root: Path,
    start: datetime,
    end: datetime,
    *,
    skip_package_ids: set[str] | None = None,
    poll_statuses: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Read orders with V2+V1 strategy.

    skip_package_ids: if provided, packages already in cache are skipped
    (no _fetch_package_items_v2 call). In this incremental mode an empty
    list is a valid result (no new packages) so V1 fallback is suppressed.
    poll_statuses: limit to specific Trendyol package statuses (for polling).
    """
    incremental = skip_package_ids is not None
    try:
        orders = _fetch_orders_from_v2_packages(
            project_root, start, end,
            skip_package_ids=skip_package_ids,
            poll_statuses=poll_statuses,
        )
        # In incremental mode empty list means "nothing new" — don't fall back
        if orders or incremental:
            return orders
    except Exception:
        pass  # Always fall through to V1 (V2 may be unavailable for this supplier)
    v1_orders = _fetch_orders_v1(project_root, start, end)
    # In incremental mode, exclude already-cached packages from V1 results
    if incremental and skip_package_ids:
        return [o for o in v1_orders if str(o.get("shipmentPackageId") or "") not in skip_package_ids]
    return v1_orders


def _fetch_orders_v1(project_root: Path, start: datetime, end: datetime) -> list[dict[str, Any]]:
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    supplier = _supplier_id(project_root)
    orders: list[dict[str, Any]] = []
    page = 0
    while page < 20:
        path = f"/order/sellers/{supplier}/orders?startDate={start_ms}&endDate={end_ms}&page={page}&size=200&orderByDirection=DESC"
        data = _fetch_json(project_root, path, v2=False)
        content = data.get("content") or []
        if not isinstance(content, list):
            break
        orders.extend(row for row in content if isinstance(row, dict))
        if len(content) < 200:
            break
        page += 1
    return orders


def _fetch_orders_from_v2_packages(
    project_root: Path,
    start: datetime,
    end: datetime,
    *,
    skip_package_ids: set[str] | None = None,
    poll_statuses: list[str] | None = None,
) -> list[dict[str, Any]]:
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    supplier = _supplier_id(project_root)
    statuses = poll_statuses or ["Created", "Picking", "Invoiced", "Shipped", "Delivered"]
    skip = skip_package_ids or set()
    packages: list[dict[str, Any]] = []
    seen_packages: set[str] = set()
    for status in statuses:
        page = 1
        while page < 20:
            qs = urllib.parse.urlencode(
                {
                    "status": status,
                    "creationStartDate": start_ms,
                    "creationEndDate": end_ms,
                    "page": page,
                    "size": 200,
                }
            )
            data = _fetch_json_with_retry(project_root, f"/integration/ecgw/v2/{supplier}/packages?{qs}", v2=True)
            time.sleep(_REQUEST_INTER_DELAY)
            items = data.get("items") or []
            if not isinstance(items, list) or not items:
                break
            for package in items:
                if not isinstance(package, dict):
                    continue
                package_key = str(package.get("packageId") or "")
                if package_key and package_key in seen_packages:
                    continue
                if package_key:
                    seen_packages.add(package_key)
                packages.append(package)
            if len(items) < 200:
                break
            page += 1

    if not packages:
        return []

    # Only fetch items for packages NOT already in the cache (skip optimisation)
    new_packages = [p for p in packages if str(p.get("packageId") or "") not in skip]
    if not new_packages:
        return []

    v1_index = _build_v1_enrichment_index(_fetch_orders_v1(project_root, start, end))
    orders: list[dict[str, Any]] = []
    for package in new_packages:
        package_id = str(package.get("packageId") or "")
        time.sleep(_ITEMS_INTER_DELAY)
        package_items = _fetch_package_items_v2(project_root, package_id)
        if not package_items:
            continue
        enriched = v1_index.get(package_id) or v1_index.get(str(package.get("trackingNumber") or "")) or {}
        orders.append(_order_from_v2_package(package, package_items, enriched))
    return orders


def _fetch_package_items_v2(project_root: Path, package_id: str) -> list[dict[str, Any]]:
    if not package_id:
        return []
    supplier = _supplier_id(project_root)
    qs = urllib.parse.urlencode({"packageId": package_id, "page": 1, "size": 200})
    data = _fetch_json(project_root, f"/integration/ecgw/v2/{supplier}/packages/items?{qs}", v2=True)
    items = data.get("items") or []
    return [row for row in items if isinstance(row, dict)] if isinstance(items, list) else []


def _build_v1_enrichment_index(orders: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for order in orders:
        package_id = str(order.get("shipmentPackageId") or "")
        order_number = str(order.get("orderNumber") or "")
        if package_id:
            index[package_id] = order
        if order_number:
            index[order_number] = order
    return index


def _order_from_v2_package(package: dict[str, Any], items: list[dict[str, Any]], v1_order: dict[str, Any]) -> dict[str, Any]:
    package_id = str(package.get("packageId") or "")
    order_number = str(v1_order.get("orderNumber") or package.get("trackingNumber") or package_id)
    customer_first = str(v1_order.get("customerFirstName") or package.get("customerFirstName") or "").strip()
    customer_last = str(v1_order.get("customerLastName") or package.get("customerLastName") or "").strip()
    shipment_address = v1_order.get("shipmentAddress") if isinstance(v1_order.get("shipmentAddress"), dict) else {}
    lines: list[dict[str, Any]] = []
    for item in items:
        lines.append(
            {
                "id": str(item.get("itemId") or ""),
                "lineId": str(item.get("itemId") or ""),
                "productName": str(item.get("name") or ""),
                "barcode": str(item.get("barcode") or item.get("sellerBarcode") or ""),
                "merchantSku": str(item.get("sellerBarcode") or item.get("barcode") or ""),
                "stockCode": str(item.get("sellerBarcode") or ""),
                "quantity": _safe_int(item.get("completedQuantity") or item.get("newQuantity") or item.get("pendingQuantity"), 1),
                "price": item.get("unitBuyingPrice") or 0,
                "creationDate": item.get("creationDate") or package.get("creationDate"),
            }
        )
    cargos = package.get("cargos") if isinstance(package.get("cargos"), list) else []
    first_cargo = cargos[0] if cargos and isinstance(cargos[0], dict) else {}
    cargo_codes = first_cargo.get("codes") if isinstance(first_cargo.get("codes"), list) else []
    return {
        "id": order_number,
        "orderNumber": order_number,
        "shipmentPackageId": package_id,
        "trackingNumber": package.get("trackingNumber") or "",
        "status": _map_package_status_v2(str(package.get("status") or "")),
        "grossAmount": package.get("totalBuyingPrice") or 0,
        "totalPrice": package.get("totalBuyingPrice") or 0,
        "orderDate": package.get("creationDate") or v1_order.get("orderDate") or int(time.time() * 1000),
        "customerFirstName": customer_first,
        "customerLastName": customer_last,
        "customerName": " ".join(part for part in [customer_first, customer_last] if part).strip(),
        "shipmentAddress": shipment_address,
        "cargoTrackingNumber": cargo_codes[0] if cargo_codes else "",
        "cargoProviderName": first_cargo.get("provider") or "",
        "lines": lines,
        "source_api": "v2_packages_with_v1_enrichment" if v1_order else "v2_packages",
    }


def _map_package_status_v2(status: str) -> str:
    return {"new": "Created", "pending": "Picking", "completed": "Delivered", "cancelled": "Cancelled"}.get(status, status or "Created")


def build_suggestions_from_orders(
    project_root: Path,
    orders: list[dict[str, Any]],
    label_models: list[dict[str, Any]] | None = None,
    questions: list[dict[str, Any]] | None = None,
    *,
    run_ai: bool = True,
    reuse_existing: bool = False,
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    seen: set[str] = set()
    question_index = _question_context_index(questions if questions is not None else list_questions(project_root))
    existing_index = _existing_suggestion_index(list_suggestions(project_root)) if reuse_existing else {}
    settings = get_settings(project_root, masked=False) if run_ai else {}
    for order in orders:
        order_number = str(order.get("orderNumber") or order.get("order_number") or order.get("id") or "")
        package_id = str(order.get("shipmentPackageId") or order.get("package_id") or order.get("packageId") or "")
        customer_name = _customer_name(order)
        lines = order.get("lines") or order.get("items") or []
        if not isinstance(lines, list):
            continue
        for line in lines:
            if not isinstance(line, dict):
                continue
            normalized = _normalize_line(order_number, package_id, customer_name, line)
            normalized["source_api"] = normalized.get("source_api") or str(order.get("source_api") or "")
            unique_key = f"{normalized['order_number']}:{normalized['package_id']}:{normalized['line_id']}"
            if unique_key in seen:
                continue
            seen.add(unique_key)
            normalized = _attach_question_context(normalized, question_index)
            mapping = trendyol_mapping_api.find_mapping_for_line(project_root, normalized)
            deterministic = extract_production_fields(normalized, mapping)
            existing = existing_index.get(unique_key)
            if existing and not run_ai:
                suggestions.append(_refresh_existing_suggestion_from_line(existing, normalized, mapping, deterministic))
                continue
            extracted = (
                extract_with_ai_or_fallback(project_root, normalized, mapping, deterministic, settings)
                if run_ai
                else deterministic
            )
            if run_ai and not mapping:
                mapping = _ai_autonomous_mapping(project_root, normalized, extracted, label_models or [])
                if mapping:
                    deterministic = extract_production_fields(normalized, mapping)
                    extracted = extract_with_ai_or_fallback(project_root, normalized, mapping, deterministic, settings)
            suggestion = _suggestion_from_line(normalized, mapping, extracted)
            suggestions.append(suggestion)
    return suggestions


def fetch_questions(
    project_root: Path,
    status: str = "",
    page: int = 0,
    size: int = QUESTION_PAGE_SIZE,
    max_pages: int = QUESTION_MAX_PAGES,
    request_timeout: int = QUESTION_REQUEST_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    """Fetch Trendyol customer questions read-only.

    This mirrors the old project's questions integration, but Cyzella uses it
    only as optional context for production text extraction. It never answers a
    question automatically.
    """
    supplier = _supplier_id(project_root)
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (QUESTION_LOOKBACK_DAYS * 24 * 60 * 60 * 1000)
    rows: list[dict[str, Any]] = []
    current_page = max(0, int(page))
    pages_read = 0
    while pages_read < max(1, int(max_pages)):
        qs = urllib.parse.urlencode(
            {
                "page": current_page,
                "size": size,
                "startDate": start_ms,
                "endDate": end_ms,
                "orderByField": "LastModifiedDate",
                "orderByDirection": "DESC",
                **({"status": status} if status else {}),
            }
        )
        data = _fetch_json(project_root, f"/qna/sellers/{supplier}/questions/filter?{qs}", v2=False, timeout=request_timeout)
        pages_read += 1
        content = data.get("content") or []
        if not isinstance(content, list) or not content:
            break
        rows.extend(row for row in content if isinstance(row, dict))
        if len(content) < size:
            break
        current_page += 1
    return rows


def fetch_latest_questions(project_root: Path, status: str = "") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if status:
        rows.extend(fetch_questions(project_root, status=status))
    else:
        first_error: Exception | None = None
        try:
            rows.extend(fetch_questions(project_root, status=""))
        except Exception as exc:  # noqa: BLE001
            first_error = exc
        for item_status in QUESTION_EVIDENCE_STATUSES:
            try:
                rows.extend(fetch_questions(project_root, status=item_status))
            except Exception as exc:  # noqa: BLE001
                first_error = first_error or exc
        if not rows and first_error:
            raise first_error
    return _sort_questions_newest_first(_dedupe_questions(rows))


def list_questions(project_root: Path) -> list[dict[str, Any]]:
    path = questions_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    rows = [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []
    return _sort_questions_newest_first(rows)


def _question_context_index(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    loose_candidates: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in _question_context_keys(row, include_loose=False):
            index.setdefault(key, []).append(row)
        if not _identity_key(row.get("order_number")) and not _question_has_specific_customer(row):
            for key in _question_loose_identity_keys(row):
                loose_candidates.setdefault(key, []).append(row)
    for key, matches in loose_candidates.items():
        if len(matches) == 1:
            index.setdefault(key, []).extend(matches)
    return index


def _question_context_keys(row: dict[str, Any], *, include_loose: bool = True) -> list[str]:
    """Return strict keys that are safe for automatic question attachment.

    Product-name similarity is intentionally excluded here. Trendyol questions
    are often product-level, so matching by product text can attach many
    unrelated customer questions to every order for the same product. Loose
    product matching is reserved for UI candidates where the user can manually
    link the right question.
    """
    keys: list[str] = []
    for field in ["order_number", "package_id", "line_id"]:
        key = _identity_key(row.get(field))
        if key and key not in keys:
            keys.append(key)
    detected_order = _detect_question_order_number(row.get("question_text") or row.get("answer_text") or "")
    key = _identity_key(detected_order)
    if key and key not in keys:
        keys.append(key)
    customer_key = _identity_key(row.get("customer_name"))
    if customer_key:
        for field in ["barcode", "merchant_sku", "stock_code"]:
            identity = _identity_key(row.get(field))
            if identity:
                composite = f"{field}:{identity}:customer:{customer_key}"
                if composite not in keys:
                    keys.append(composite)
    if include_loose:
        for key in _question_loose_identity_keys(row):
            if key not in keys:
                keys.append(key)
    return keys


def _question_loose_identity_keys(row: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for field in ["barcode", "merchant_sku", "stock_code"]:
        identity = _identity_key(row.get(field))
        if identity:
            keys.append(f"unique:{field}:{identity}")
    return keys


def _question_has_specific_customer(row: dict[str, Any]) -> bool:
    customer = _identity_key(row.get("customer_name"))
    return bool(customer and customer not in {"trendyol müşteri", "trendyol musteri"})


def _attach_question_context(line: dict[str, Any], question_index: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if not question_index:
        return line
    matches: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for key in _question_context_keys(line):
        for row in question_index.get(key, []):
            row_id = str(row.get("id") or json.dumps(row, ensure_ascii=False, sort_keys=True))
            if row_id in seen_ids:
                continue
            seen_ids.add(row_id)
            matches.append(row)
    if not matches:
        return line
    enriched = dict(line)
    question_texts = [repair_text(row.get("question_text") or "") for row in matches if repair_text(row.get("question_text") or "")]
    answer_texts = [repair_text(row.get("answer_text") or "") for row in matches if repair_text(row.get("answer_text") or "")]
    if question_texts:
        existing = repair_text(enriched.get("question_text") or "")
        enriched["question_text"] = " | ".join(part for part in [existing, *question_texts] if part)
    if answer_texts:
        existing_answer = repair_text(enriched.get("answer_text") or "")
        enriched["answer_text"] = " | ".join(part for part in [existing_answer, *answer_texts] if part)
    enriched["question_contexts"] = [
        {
            "id": row.get("id") or "",
            "status": row.get("status") or "",
            "answered": bool(row.get("answered")),
            "question_text": repair_text(row.get("question_text") or ""),
            "answer_text": repair_text(row.get("answer_text") or ""),
            "label_text": row.get("label_text") or "",
            "date_text": row.get("date_text") or "",
            "note_text": row.get("note_text") or "",
            "name_cut_text": row.get("name_cut_text") or "",
            "product_name": row.get("product_name") or "",
            "barcode": row.get("barcode") or "",
            "merchant_sku": row.get("merchant_sku") or "",
            "image_url": row.get("image_url") or row.get("primary_image_url") or "",
            "confidence": row.get("confidence") or 0,
        }
        for row in matches[:4]
    ]
    return enriched


def _refresh_saved_suggestions_with_questions(project_root: Path, questions: list[dict[str, Any]], *, run_extraction: bool = False) -> int:
    rows = list_suggestions(project_root)
    if not rows or not questions:
        return 0
    question_index = _question_context_index(questions)
    updated = 0
    for row in rows:
        if row.get("verification_status") == VERIFICATION_TRANSFERRED or row.get("import_status"):
            continue
        previous_question_text = row.get("question_text") or ""
        previous_answer_text = row.get("answer_text") or ""
        previous_contexts = row.get("question_contexts") if isinstance(row.get("question_contexts"), list) else []
        previous_context_ids = {str(item.get("id") or "") for item in previous_contexts if isinstance(item, dict) and item.get("id")}
        match_source = dict(row)
        match_source["question_text"] = ""
        match_source["answer_text"] = ""
        match_source["question_contexts"] = []
        attached = _attach_question_context(match_source, question_index)
        if not _has_question_evidence(attached):
            if previous_question_text or previous_answer_text or previous_contexts:
                row["question_text"] = ""
                row["answer_text"] = ""
                row["question_contexts"] = []
                row["selected_question_id"] = ""
                row["verification_status"] = VERIFICATION_WAITING_EVIDENCE
                row["status"] = "review"
                row["user_verified"] = False
                row["updated_at"] = _now()
                updated += 1
            continue
        attached_contexts = attached.get("question_contexts") if isinstance(attached.get("question_contexts"), list) else []
        attached_context_ids = {str(item.get("id") or "") for item in attached_contexts if isinstance(item, dict) and item.get("id")}
        needs_refresh = _needs_extraction_refresh(row)
        if previous_context_ids and attached_context_ids == previous_context_ids and previous_question_text and not needs_refresh:
            continue
        row["question_text"] = ""
        row["answer_text"] = ""
        row["question_contexts"] = []
        row["selected_question_id"] = ""
        previous_context_count = len(previous_contexts)
        row.update(attached)
        if run_extraction or needs_refresh:
            deterministic = extract_production_fields(row, _mapping_from_suggestion(row))
            extracted = extract_with_ai_or_fallback(project_root, row, _mapping_from_suggestion(row), deterministic, get_settings(project_root, masked=False))
            _apply_extracted_fields(row, extracted)
        if not row.get("selected_question_id"):
            row["selected_question_id"] = _first_question_id(row)
        if row.get("verification_status") not in {VERIFICATION_READY, VERIFICATION_TRANSFERRED}:
            row["verification_status"] = VERIFICATION_WAITING_APPROVAL
            row["status"] = "review"
            row["user_verified"] = False
        row["updated_at"] = _now()
        current_context_count = len(row.get("question_contexts") if isinstance(row.get("question_contexts"), list) else [])
        if current_context_count != previous_context_count or row.get("question_text"):
            updated += 1
    if updated:
        _save_suggestions(project_root, rows)
    return updated


def list_mapping_suggestions(project_root: Path) -> list[dict[str, Any]]:
    path = mapping_suggestions_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [_repair_trendyol_row(row) for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def cache_product_image(project_root: Path, image_url: str) -> dict[str, Any]:
    """Download a Trendyol product image into the project cache for stable WebView display."""
    url = str(image_url or "").strip()
    if not url:
        return {"status": "MISSING", "message": "Ürün görseli URL'i boş.", "image_url": "", "preview_url": ""}
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"status": "ERROR", "message": "Ürün görseli URL'i geçerli bir HTTP/HTTPS adresi değil.", "image_url": url, "preview_url": ""}

    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    cache_path = image_cache_dir(project_root) / f"{digest}{suffix}"
    meta_path = cache_path.with_suffix(cache_path.suffix + ".json")
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return {
            "status": "OK",
            "message": "Ürün görseli önbellekten gösteriliyor.",
            "image_url": url,
            "cached_path": str(cache_path),
            "preview_url": file_api.to_web_file_url(cache_path, project_root),
        }

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 CyzellaProductionStudio/1.0",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://www.trendyol.com/",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = str(response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            data = response.read()
    except Exception as exc:
        return {
            "status": "ERROR",
            "message": f"Ürün görseli indirilemedi: {str(exc)[:160]}",
            "image_url": url,
            "preview_url": "",
        }
    if not data or len(data) < 64:
        return {"status": "ERROR", "message": "Ürün görseli boş veya geçersiz döndü.", "image_url": url, "preview_url": ""}
    guessed = mimetypes.guess_extension(content_type or "")
    if guessed in {".jpg", ".jpeg", ".png", ".webp"} and guessed != suffix:
        cache_path = image_cache_dir(project_root) / f"{digest}{guessed}"
        meta_path = cache_path.with_suffix(cache_path.suffix + ".json")
    cache_path.write_bytes(data)
    meta_path.write_text(
        json.dumps(
            {"source_url": url, "content_type": content_type, "bytes": len(data), "cached_at": datetime.now().isoformat()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "status": "OK",
        "message": "Ürün görseli indirildi ve yerel önbellekten gösteriliyor.",
        "image_url": url,
        "cached_path": str(cache_path),
        "preview_url": file_api.to_web_file_url(cache_path, project_root),
    }


def approve_mapping_suggestion(project_root: Path, suggestion_id: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = list_mapping_suggestions(project_root)
    suggestion = next((row for row in rows if str(row.get("id") or "") == str(suggestion_id)), None)
    if not suggestion:
        return {"status": "MISSING", "message": "Trendyol katalog eşleştirme önerisi bulunamadı."}
    payload = {**suggestion, **(overrides or {})}
    production_type = str(payload.get("production_type") or "")
    if production_type == "review":
        return {
            "status": "NEEDS_REVIEW",
            "message": "Kontrol gerekli katalog önerileri doğrudan onaylanmaz; üretim tipi/model seçip manuel kaydedin.",
            "suggestions": rows,
        }
    if production_type in {"label", "label_and_name_cut"} and not str(payload.get("model_path") or "").strip():
        return {
            "status": "NEEDS_MODEL",
            "message": "Etiket üretimi için önce etiket modeli seçilmelidir; model olmadan ürün eşleştirmesi onaylanmadı.",
            "suggestions": rows,
        }
    result = trendyol_mapping_api.upsert_product_mapping(project_root, payload)
    if result.get("status") == "OK":
        for row in rows:
            if str(row.get("id") or "") == str(suggestion_id):
                row["approved_at"] = _now()
                row["status"] = "approved"
        _save_mapping_suggestions(project_root, rows)
    return {**result, "suggestions": rows}


def list_suggestions(project_root: Path) -> list[dict[str, Any]]:
    path = suggestions_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    product_index = _cached_product_reference_index(project_root)
    return [_repair_trendyol_row(_enrich_line_with_catalog(row, product_index)) for row in data if isinstance(row, dict)]


def _suggestion_line_key(row: dict[str, Any]) -> str:
    return f"{row.get('order_number') or ''}:{row.get('package_id') or ''}:{row.get('line_id') or ''}"


def _existing_suggestion_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _suggestion_line_key(row)
        if key != "::":
            index[key] = row
    return index


def _refresh_existing_suggestion_from_line(
    existing: dict[str, Any],
    line: dict[str, Any],
    mapping: dict[str, Any] | None,
    deterministic: dict[str, Any],
) -> dict[str, Any]:
    """Keep expensive AI/user decisions while refreshing live order metadata.

    The "Son 7 Günü Çek" action is an order sync, not an extraction review
    action. Reusing the previous suggestion prevents hundreds of AI calls and
    keeps the UI responsive; explicit question selection still refreshes AI
    fields for the selected row.
    """

    row = dict(existing)
    row.update(
        {
            "order_number": line.get("order_number") or row.get("order_number") or "",
            "package_id": line.get("package_id") or row.get("package_id") or "",
            "line_id": line.get("line_id") or row.get("line_id") or "",
            "customer_name": title_turkish_name(line.get("customer_name") or row.get("customer_name") or ""),
            "product_name": repair_text(line.get("product_name") or row.get("product_name") or ""),
            "barcode": line.get("barcode") or row.get("barcode") or "",
            "merchant_sku": line.get("merchant_sku") or row.get("merchant_sku") or "",
            "stock_code": line.get("stock_code") or row.get("stock_code") or "",
            "source_api": line.get("source_api") or row.get("source_api") or "",
            "image_url": line.get("image_url") or row.get("image_url") or "",
            "product_url": line.get("product_url") or row.get("product_url") or "",
            "image_url_source": line.get("image_url_source") or row.get("image_url_source") or "",
            "product_url_source": line.get("product_url_source") or row.get("product_url_source") or "",
            "quantity": line.get("quantity") or row.get("quantity") or deterministic.get("quantity") or 1,
            "updated_at": _now(),
        }
    )
    for key in ["question_text", "answer_text", "question_contexts", "selected_question_id"]:
        if line.get(key):
            row[key] = line.get(key)
    if mapping:
        row["production_type"] = mapping.get("production_type") or row.get("production_type") or "review"
        row["model_key"] = mapping.get("model_key") or row.get("model_key") or ""
        row["model_path"] = mapping.get("model_path") or row.get("model_path") or ""
        row["model_name"] = mapping.get("model_name") or row.get("model_name") or ""
        row["mapping_found"] = True
        if row.get("mapping_source") in {"", "none", None}:
            row["mapping_source"] = "barcode_sku"
    elif not row.get("mapping_found"):
        row["mapping_found"] = False
    return row


def save_suggestions(project_root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    _save_suggestions(project_root, rows)
    return {"status": "OK", "message": f"{len(rows)} Trendyol önerisi kaydedildi.", "suggestions": rows}


def apply_question_to_suggestion(project_root: Path, suggestion_id: str, question_id: str) -> dict[str, Any]:
    rows = list_suggestions(project_root)
    suggestion = next((row for row in rows if str(row.get("id") or "") == str(suggestion_id)), None)
    if not suggestion:
        return {"status": "MISSING", "message": "Trendyol üretim önerisi bulunamadı."}
    contexts = _all_question_contexts_for_suggestion(project_root, suggestion)
    context = next((row for row in contexts if str(row.get("id") or "") == str(question_id)), None)
    if not context:
        return {"status": "MISSING", "message": "Bu siparişe bağlanacak soru/mesaj kaydı bulunamadı.", "suggestion": suggestion}

    suggestion["selected_question_id"] = str(context.get("id") or "")
    suggestion["question_contexts"] = _merge_question_contexts(suggestion.get("question_contexts"), [context])
    merged_contexts = [item for item in (suggestion.get("question_contexts") or []) if isinstance(item, dict)]
    suggestion["question_text"] = " | ".join(repair_text(item.get("question_text") or "") for item in merged_contexts if repair_text(item.get("question_text") or ""))
    suggestion["answer_text"] = " | ".join(repair_text(item.get("answer_text") or "") for item in merged_contexts if repair_text(item.get("answer_text") or ""))
    deterministic = extract_production_fields(suggestion, _mapping_from_suggestion(suggestion))
    extracted = extract_with_ai_or_fallback(project_root, suggestion, _mapping_from_suggestion(suggestion), deterministic, get_settings(project_root, masked=False))
    _apply_extracted_fields(suggestion, extracted)
    suggestion["verification_status"] = VERIFICATION_WAITING_APPROVAL
    suggestion["status"] = "review"
    suggestion["user_verified"] = False
    suggestion["updated_at"] = _now()
    _save_suggestions(project_root, rows)
    return {"status": "OK", "message": "Soru/mesaj kanıtı seçili siparişe bağlandı. Alanları kontrol edip onaylayın.", "suggestion": suggestion, "suggestions": rows}


def ignore_question_for_suggestion(project_root: Path, suggestion_id: str, question_id: str) -> dict[str, Any]:
    rows = list_suggestions(project_root)
    suggestion = next((row for row in rows if str(row.get("id") or "") == str(suggestion_id)), None)
    if not suggestion:
        return {"status": "MISSING", "message": "Trendyol üretim önerisi bulunamadı."}
    ignored = [str(item) for item in suggestion.get("ignored_question_ids") or [] if str(item)]
    if str(question_id) not in ignored:
        ignored.append(str(question_id))
    suggestion["ignored_question_ids"] = ignored
    if str(suggestion.get("selected_question_id") or "") == str(question_id):
        suggestion["selected_question_id"] = ""
    suggestion["updated_at"] = _now()
    _save_suggestions(project_root, rows)
    return {"status": "OK", "message": "Soru bu sipariş için yok sayıldı.", "suggestion": suggestion, "suggestions": rows}


def verify_suggestion(project_root: Path, suggestion_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = list_suggestions(project_root)
    suggestion = next((row for row in rows if str(row.get("id") or "") == str(suggestion_id)), None)
    if not suggestion:
        return {"status": "MISSING", "message": "Trendyol üretim önerisi bulunamadı."}
    payload = payload or {}
    for key in [
        "label_text",
        "date_text",
        "note_text",
        "name_cut_text",
        "name_cut_style",
        "name_cut_width_mm",
        "production_type",
        "model_key",
        "model_path",
        "model_name",
    ]:
        if key in payload:
            suggestion[key] = repair_text(payload.get(key)) if key.endswith("_text") or key in {"model_name", "name_cut_style"} else payload.get(key)
    if "quantity" in payload:
        suggestion["quantity"] = _safe_int(payload.get("quantity"), 1)
    label_required = _safe_bool(payload.get("label_required"), suggestion.get("production_type") in {"label", "label_and_name_cut"})
    name_cut_required = _safe_bool(payload.get("name_cut_required"), suggestion.get("production_type") in {"name_cut", "label_and_name_cut"})
    if label_required and name_cut_required:
        suggestion["production_type"] = "label_and_name_cut"
    elif label_required:
        suggestion["production_type"] = "label"
    elif name_cut_required:
        suggestion["production_type"] = "name_cut"
    else:
        suggestion["production_type"] = "none"

    warnings = _dedupe_warnings(suggestion.get("warnings") or [])
    if not _has_question_evidence(suggestion):
        warnings.append("Müşteri soru/mesaj kanıtı yok; bu satır üretime alınmadan önce manuel kontrol gerektirir.")
    if suggestion.get("production_type") in {"label", "label_and_name_cut"} and not suggestion.get("model_path"):
        warnings.append("Etiket üretimi için model seçilmedi.")
    ready = (
        _has_question_evidence(suggestion)
        and suggestion.get("production_type") not in {"review", "none", ""}
        and (suggestion.get("production_type") in {"name_cut"} or bool(suggestion.get("model_path")))
        and bool(suggestion.get("label_text") or suggestion.get("name_cut_text"))
    )
    suggestion["warnings"] = _dedupe_warnings(warnings)
    suggestion["user_verified"] = bool(ready)
    suggestion["verified_at"] = _now() if ready else ""
    suggestion["verified_by"] = "local_user" if ready else ""
    suggestion["verification_status"] = VERIFICATION_READY if ready else VERIFICATION_USER_REVIEW
    suggestion["status"] = "ready" if ready else "review"
    suggestion["updated_at"] = _now()
    if ready:
        try:
            learning = record_learning_example(project_root, suggestion, suggestion, "user_verified")
            if learning.get("saved") and isinstance(learning.get("example"), dict):
                suggestion["learning_example_id"] = learning["example"].get("id") or ""
        except Exception as exc:  # noqa: BLE001
            suggestion["warnings"] = _dedupe_warnings([*suggestion.get("warnings", []), f"Yerel öğrenme örneği kaydedilemedi: {exc}"])
    _save_suggestions(project_root, rows)
    message = "Satır kullanıcı onayıyla üretime hazır yapıldı." if ready else "Satır hâlâ kontrol istiyor; soru kanıtı, model veya üretim alanları eksik."
    return {"status": "OK" if ready else "NEEDS_REVIEW", "message": message, "suggestion": suggestion, "suggestions": rows}


def import_suggestion_to_customer_order(project_root: Path, suggestion_id: str) -> dict[str, Any]:
    rows = list_suggestions(project_root)
    suggestion = next((row for row in rows if row.get("id") == suggestion_id), None)
    if not suggestion:
        return {"status": "MISSING", "message": "Trendyol üretim önerisi bulunamadı."}
    existing = _find_existing_customer_order(project_root, suggestion)
    if existing:
        return {"status": "DUPLICATE", "message": "Bu Trendyol satırı zaten siparişlere aktarılmış.", "order": existing}
    if not _is_verified_ready(suggestion):
        return {"status": "NEEDS_REVIEW", "message": "Bu Trendyol satırı soru/mesaj kanıtı ve kullanıcı onayı olmadan üretime aktarılamaz.", "suggestion": suggestion}
    if suggestion.get("production_type") not in {"label", "label_and_name_cut"}:
        return {"status": "SKIPPED", "message": "Bu satır etiket siparişi değil; müşteri siparişine aktarılmadı.", "suggestion": suggestion}
    order = customer_order_api.create_customer_order(
        project_root,
        {
            "customer_name": suggestion.get("label_text") or suggestion.get("customer_name") or "",
            "event_date": suggestion.get("date_text") or "",
            "note_text": suggestion.get("note_text") or "",
            "trendyol_question_text": _question_evidence_text(suggestion),
            "trendyol_source_evidence": ", ".join(suggestion.get("source_evidence") or []),
            "model_path": suggestion.get("model_path") or "",
            "model_name": suggestion.get("model_name") or "",
            "quantity": suggestion.get("quantity") or 1,
            "payment_status": "Trendyol",
            "production_status": "Yeni",
            "source": "trendyol",
            "trendyol_order_number": suggestion.get("order_number") or "",
            "trendyol_package_id": suggestion.get("package_id") or "",
            "trendyol_line_id": suggestion.get("line_id") or "",
            "trendyol_barcode": suggestion.get("barcode") or "",
            "trendyol_merchant_sku": suggestion.get("merchant_sku") or "",
        },
    )
    suggestion["import_status"] = "customer_order"
    suggestion["verification_status"] = VERIFICATION_TRANSFERRED
    suggestion["imported_order_id"] = order.get("order", {}).get("id", "")
    suggestion["updated_at"] = _now()
    _save_suggestions(project_root, rows)
    return {"status": "OK", "message": "Trendyol satırı müşteri siparişine aktarıldı.", "order": order.get("order"), "suggestion": suggestion}


def summary(project_root: Path) -> dict[str, int]:
    suggestions = list_suggestions(project_root)
    return {
        "total": len(suggestions),
        "ready": sum(1 for row in suggestions if _is_verified_ready(row)),
        "review": sum(1 for row in suggestions if row.get("status") == "review"),
        "unmatched": sum(1 for row in suggestions if not row.get("mapping_found")),
        "question_linked": sum(1 for row in suggestions if _has_question_evidence(row)),
        "evidence_waiting": sum(1 for row in suggestions if row.get("verification_status") == VERIFICATION_WAITING_EVIDENCE),
        "verification_pending": sum(1 for row in suggestions if row.get("verification_status") == VERIFICATION_WAITING_APPROVAL),
        "today_quantity": sum(int(row.get("quantity") or 0) for row in suggestions),
        "total_quantity": sum(int(row.get("quantity") or 0) for row in suggestions),
        "both": sum(1 for row in suggestions if row.get("production_type") == "label_and_name_cut"),
        "imported": sum(1 for row in suggestions if row.get("import_status")),
    }


def export_ready_suggestions_to_excel(project_root: Path, suggestion_ids: list[str] | None = None) -> dict[str, Any]:
    rows = list_suggestions(project_root)
    selected_ids = {str(item) for item in (suggestion_ids or []) if str(item).strip()}
    candidates = [
        row for row in rows
        if _is_verified_ready(row)
        and (not selected_ids or str(row.get("id") or "") in selected_ids)
        and row.get("production_type") in {"label", "name_cut", "label_and_name_cut"}
    ]
    if not candidates:
        return {"status": "ERROR", "message": "Toplu üretime aktarılacak hazır Trendyol satırı bulunamadı.", "path": ""}
    export_rows = [_production_excel_row(row) for row in candidates]
    target_dir = project_root / "output" / datetime.now().strftime("%Y-%m-%d") / "trendyol"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"trendyol_uretim_{datetime.now().strftime('%H%M%S_%f')}.xlsx"
    pd.DataFrame(export_rows).to_excel(target_path, index=False)
    manifest_path = target_path.with_suffix(".json")
    suggestion_ids_out = [row.get("id") for row in candidates]
    manifest = {
        "source": "trendyol",
        "created_at": _now(),
        "row_count": len(export_rows),
        "excel_path": _relative(project_root, target_path),
        "suggestion_ids": suggestion_ids_out,
        "orders": candidates,
        "safety": {
            "direct_print": False,
            "rdworks_auto_open": False,
            "laser_auto_start": False,
            "user_approval_required": True,
            "ai_autonomous_rows": sum(1 for row in candidates if row.get("ai_autonomous")),
            "physical_action_requires_user": True,
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    suggestion_id_set = {str(item) for item in suggestion_ids_out}
    for row in rows:
        if str(row.get("id") or "") in suggestion_id_set:
            row["import_status"] = row.get("import_status") or "production_excel"
            row["production_excel_path"] = _relative(project_root, target_path)
            row["updated_at"] = _now()
    _save_suggestions(project_root, rows)
    return {
        "status": "OK",
        "message": f"{len(export_rows)} Trendyol satırı Toplu Etiket / İsim Kesim Excel akışına aktarıldı.",
        "path": str(target_path),
        "relative_path": _relative(project_root, target_path),
        "manifest_path": _relative(project_root, manifest_path),
        "row_count": len(export_rows),
    }


def import_suggestions_to_bulk_production(project_root: Path, suggestion_ids: list[str] | None, label_models: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Create safe Toplu Uretim gallery rows from Trendyol suggestions.

    This is a local production-preparation import only. It never changes live
    Trendyol order status and never starts printer, laser, or RDWorks actions.
    """

    rows = list_suggestions(project_root)
    selected_ids = {str(item) for item in (suggestion_ids or []) if str(item).strip()}
    candidates = [row for row in rows if (not selected_ids or str(row.get("id") or "") in selected_ids)]
    if not candidates:
        return {
            "status": "ERROR",
            "message": "Toplu Üretim'e aktarılacak Trendyol satırı bulunamadı.",
            "items": [],
            "summary": {},
            "suggestions": rows,
            "audit_events": [],
        }

    model_index = _label_model_index(label_models or [])
    imported_items: list[dict[str, Any]] = []
    audit_events: list[dict[str, Any]] = []
    summary = {
        "selected": len(candidates),
        "imported": 0,
        "ready": 0,
        "needs_review": 0,
        "blocked": 0,
        "duplicate": 0,
        "with_proof": 0,
        "missing_personalization": 0,
        "live_trendyol_changed": False,
        "cargo_invoice_triggered": False,
    }
    batch_id = f"TYB-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    for row in candidates:
        row_id = str(row.get("id") or "")
        duplicate_key = _trendyol_bulk_duplicate_key(row)
        already_imported = str(row.get("bulk_import_duplicate_key") or "") == duplicate_key or str(row.get("import_status") or "") == "bulk_production"
        if already_imported:
            summary["duplicate"] += 1
            audit_events.append(_trendyol_import_audit_event(row, "duplicate_detected", "warning", "Bu Trendyol sipariş satırı daha önce Toplu Üretim'e aktarılmış.", batch_id, duplicate_key))
            continue

        item = _trendyol_bulk_gallery_item(row, model_index, batch_id, duplicate_key)
        imported_items.append(item)
        row["import_status"] = "bulk_production"
        row["bulk_import_batch_id"] = batch_id
        row["bulk_import_duplicate_key"] = duplicate_key
        row["bulk_imported_at"] = _now()
        row["bulk_import_status"] = item.get("trendyol_import_status")
        row["updated_at"] = _now()

        status = str(item.get("trendyol_import_status") or "")
        summary["imported"] += 1
        if status == "proof_confirmed":
            summary["ready"] += 1
        elif status == "blocked":
            summary["blocked"] += 1
        else:
            summary["needs_review"] += 1
        if item.get("proof_text"):
            summary["with_proof"] += 1
        if not item.get("label_text"):
            summary["missing_personalization"] += 1

        audit_events.append(_trendyol_import_audit_event(row, "trendyol_sent_to_bulk_production", "success" if status == "proof_confirmed" else "warning", "Trendyol satırı Toplu Üretim hazırlığına aktarıldı.", batch_id, duplicate_key, item))
        if item.get("proof_text"):
            audit_events.append(_trendyol_import_audit_event(row, "trendyol_personalization_extracted", "success" if status == "proof_confirmed" else "warning", "Kişiselleştirme alanları müşteri mesajı/kanıt üzerinden önerildi.", batch_id, duplicate_key, item))
        if not item.get("label_text"):
            audit_events.append(_trendyol_import_audit_event(row, "trendyol_missing_personalization", "warning", "Kişiselleştirme kanıtı eksik veya belirsiz; alan uydurulmadı.", batch_id, duplicate_key, item))
        if status == "blocked":
            audit_events.append(_trendyol_import_audit_event(row, "blocked_detected", "blocked", "Model, adet veya üretime engel alan nedeniyle kayıt bloklandı.", batch_id, duplicate_key, item))
        elif status == "needs_review":
            audit_events.append(_trendyol_import_audit_event(row, "manual_review_required", "warning", "Trendyol kaydı operatör kontrolü gerektiriyor.", batch_id, duplicate_key, item))

    _save_suggestions(project_root, rows)
    audit_events.insert(0, {
        "event_type": "trendyol_import_started",
        "event_label": "Trendyol Toplu Üretim aktarımı başladı",
        "source": "trendyol",
        "source_label": "Trendyol",
        "batch_id": batch_id,
        "status": "local_import_only",
        "severity": "info",
        "message": f"{len(candidates)} Trendyol satırı yerel Toplu Üretim hazırlığı için kontrol edildi.",
        "created_at": _now(),
        "metadata": {
            "selected": len(candidates),
            "live_trendyol_changed": False,
            "cargo_invoice_triggered": False,
        },
    })
    message = (
        f"{summary['imported']} Trendyol satırı Toplu Üretim hazırlığına aktarıldı. "
        f"{summary['needs_review']} kontrol gerekli, {summary['blocked']} engelli, {summary['duplicate']} duplicate. "
        "Trendyol canlı sipariş durumu, kargo, fatura, yazıcı, lazer veya RDWorks tetiklenmedi."
    )
    status = "OK" if summary["imported"] else ("DUPLICATE" if summary["duplicate"] else "ERROR")
    return {
        "status": status,
        "message": message,
        "items": imported_items,
        "summary": summary,
        "suggestions": rows,
        "audit_events": audit_events,
        "batch_id": batch_id,
    }


def save_trendyol_operator_correction(project_root: Path, suggestion_id: str, payload: dict[str, Any] | None, label_models: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Persist an operator correction for a Trendyol production suggestion.

    The correction is local production preparation only. It does not update
    Trendyol, print, laser, cargo, invoice, or marketplace state.
    """

    rows = list_suggestions(project_root)
    suggestion = next((row for row in rows if str(row.get("id") or "") == str(suggestion_id)), None)
    if not suggestion:
        return {"status": "ERROR", "message": "Düzeltilecek Trendyol kaydı bulunamadı.", "suggestions": rows}

    data = payload or {}
    old_values = {
        "label_text": suggestion.get("label_text") or "",
        "date_text": suggestion.get("date_text") or "",
        "note_text": suggestion.get("note_text") or "",
        "name_cut_text": suggestion.get("name_cut_text") or "",
        "model_path": suggestion.get("model_path") or "",
        "model_name": suggestion.get("model_name") or "",
        "quantity": suggestion.get("quantity") or "",
        "product_match_note": suggestion.get("product_match_note") or "",
    }
    field_map = {
        "label_text": "label_text",
        "name": "label_text",
        "date_text": "date_text",
        "date": "date_text",
        "note_text": "note_text",
        "note": "note_text",
        "name_cut_text": "name_cut_text",
        "laser_name": "name_cut_text",
        "model_path": "model_path",
        "label_model": "model_path",
        "quantity": "quantity",
        "product_match_note": "product_match_note",
    }
    changed_fields: list[dict[str, Any]] = []
    sources = suggestion.get("field_sources") if isinstance(suggestion.get("field_sources"), dict) else {}
    for incoming, target in field_map.items():
        if incoming not in data:
            continue
        raw_value = data.get(incoming)
        value = repair_text(raw_value) if target != "quantity" else raw_value
        if target == "quantity":
            value = _safe_int(value, 0)
        if str(suggestion.get(target) or "") == str(value or ""):
            continue
        changed_fields.append({"field": target, "old": suggestion.get(target) or "", "new": value})
        suggestion[target] = value
        if target in {"label_text", "date_text", "note_text", "name_cut_text"}:
            sources[target] = "operator_manual"

    model_index = _label_model_index(label_models or [])
    model = _trendyol_model_for_row(suggestion, model_index)
    if model:
        suggestion["model_name"] = str(model.get("title") or model.get("model_name") or suggestion.get("model_name") or "")
        suggestion["model_key"] = str(model.get("model_no") or model.get("template_id") or suggestion.get("model_key") or "")
    elif suggestion.get("model_path"):
        # Keep a manually entered model path visible, but the generated item will
        # remain blocked unless it matches a known production model.
        suggestion["model_name"] = suggestion.get("model_name") or Path(str(suggestion.get("model_path"))).stem

    suggestion["field_sources"] = sources
    suggestion["operator_corrected"] = bool(changed_fields) or bool(suggestion.get("operator_corrected"))
    suggestion["operator_correction_note"] = repair_text(data.get("operator_note") or data.get("product_match_note") or suggestion.get("operator_correction_note") or "")
    suggestion["operator_corrected_at"] = _now() if changed_fields else suggestion.get("operator_corrected_at", "")
    suggestion["verification_status"] = VERIFICATION_USER_REVIEW
    suggestion["status"] = "review"
    suggestion["updated_at"] = _now()

    duplicate_key = suggestion.get("bulk_import_duplicate_key") or _trendyol_bulk_duplicate_key(suggestion)
    batch_id = str(data.get("batch_id") or suggestion.get("bulk_import_batch_id") or f"TYC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}")
    item = _trendyol_bulk_gallery_item(suggestion, model_index, batch_id, duplicate_key)
    item["operator_corrected"] = bool(suggestion.get("operator_corrected"))
    item["operator_correction_note"] = suggestion.get("operator_correction_note") or ""
    if item["operator_corrected"]:
        item["proof_source"] = item.get("proof_source") or "operator_manual"

    suggestion["bulk_import_status"] = item.get("trendyol_import_status")
    suggestion["bulk_import_batch_id"] = batch_id
    suggestion["bulk_import_duplicate_key"] = duplicate_key
    _save_suggestions(project_root, rows)

    audit_events = [
        _trendyol_correction_audit_event(suggestion, "trendyol_operator_correction_started", "info", "Operatör Trendyol düzeltme panelini kullandı.", changed_fields, batch_id),
    ]
    if changed_fields:
        audit_events.append(_trendyol_correction_audit_event(suggestion, "trendyol_operator_correction_saved", "success", "Operatör düzeltmesi kaydedildi.", changed_fields, batch_id))
    if item.get("trendyol_import_status") == "proof_confirmed":
        audit_events.append(_trendyol_correction_audit_event(suggestion, "trendyol_personalization_confirmed", "success", "Kişiselleştirme alanları üretim için tamamlandı.", changed_fields, batch_id))
    else:
        audit_events.append(_trendyol_correction_audit_event(suggestion, "trendyol_personalization_still_missing", "warning", "Kişiselleştirme veya kanıt kontrolü hâlâ gerekli.", changed_fields, batch_id))
    if item.get("model_status") == "FOUND":
        audit_events.append(_trendyol_correction_audit_event(suggestion, "trendyol_model_matched", "success", "Trendyol ürün satırı etiket modeliyle eşleşti.", changed_fields, batch_id))
    else:
        audit_events.append(_trendyol_correction_audit_event(suggestion, "trendyol_model_missing", "blocked", "Etiket modeli eşleşmedi; üretime alınamaz.", changed_fields, batch_id))
    if item.get("trendyol_import_status") == "needs_review":
        audit_events.append(_trendyol_correction_audit_event(suggestion, "manual_review_required", "warning", "Trendyol kaydı operatör kontrolü gerektiriyor.", changed_fields, batch_id))

    return {
        "status": "OK" if item.get("trendyol_import_status") != "blocked" else "BLOCKED",
        "message": "Operatör düzeltmesi kaydedildi. Trendyol canlı işlem, yazıcı, lazer veya RDWorks tetiklenmedi.",
        "item": item,
        "suggestion": suggestion,
        "suggestions": rows,
        "audit_events": audit_events,
        "changed_fields": changed_fields,
    }


def reanalyze_trendyol_suggestion(project_root: Path, suggestion_id: str) -> dict[str, Any]:
    """Re-run AI extraction on a single suggestion, bypassing the response cache.

    Returns full diagnostics: ai_enabled, model_used, llm_called, llm_error,
    reasoning, evidence_span.  LLM errors are surfaced — no silent fallback.
    Read-only to Trendyol: only the local suggestion record is updated.
    """
    rows = list_suggestions(project_root)
    suggestion = next((row for row in rows if str(row.get("id") or "") == str(suggestion_id)), None)
    if not suggestion:
        return {"status": "ERROR", "message": "Trendyol önerisi bulunamadı.", "suggestions": rows}

    if not _has_question_evidence(suggestion):
        return {
            "status": "SKIP",
            "message": "Bu siparişe bağlı müşteri mesajı yok; AI analizi çalıştırılamadı.",
            "suggestion": suggestion,
            "suggestions": rows,
            "ai_enabled": False,
            "llm_called": False,
        }

    settings_raw = get_settings(project_root, masked=False)
    settings_no_cache = {**settings_raw, "ai_cache_enabled": False}
    ai_enabled = is_ai_configured(settings_raw)
    model_used = str(settings_raw.get("ai_model") or DEFAULT_AI_MODEL)
    deterministic = extract_production_fields(suggestion, _mapping_from_suggestion(suggestion))
    mapping = _mapping_from_suggestion(suggestion)

    llm_called = False
    llm_error: str | None = None
    extracted: dict[str, Any] | None = None

    if ai_enabled:
        llm_called = True
        try:
            extracted = extract_with_cloud_ai(project_root, suggestion, mapping, deterministic, settings_no_cache)
        except Exception as exc:  # noqa: BLE001
            llm_error = str(exc)
            extracted = None

    if extracted is None:
        # Deterministic fallback — use ai_enabled=False override so it takes the safe path
        extracted = extract_with_ai_or_fallback(
            project_root, suggestion, mapping, deterministic,
            {**settings_no_cache, "ai_enabled": False},
        )

    reasoning = str(extracted.pop("_diag_reasoning", "") or "")
    evidence_span = str(extracted.pop("_diag_evidence_span", "") or "")

    _apply_extracted_fields(suggestion, extracted)

    field_sources = dict(suggestion.get("field_sources") or {})
    for field in ("label_text", "date_text", "name_cut_text", "note_text"):
        if field_sources.get(field) == "operator_manual":
            field_sources.pop(field, None)
    suggestion["field_sources"] = field_sources
    suggestion["operator_corrected"] = False
    suggestion["verification_status"] = VERIFICATION_WAITING_APPROVAL
    suggestion["status"] = "review"
    suggestion["user_verified"] = False
    suggestion["updated_at"] = _now()
    _save_suggestions(project_root, rows)

    label = suggestion.get("label_text") or "(bulunamadı)"
    status = "OK" if not llm_error else "AI_ERROR"
    msg = f"AI yeniden analiz tamamlandı. İsim: {label}"
    if llm_error:
        msg = f"LLM hatası (deterministik fallback kullanıldı). İsim: {label}. Hata: {llm_error}"

    return {
        "status": status,
        "message": msg,
        "suggestion": suggestion,
        "suggestions": rows,
        "ai_enabled": ai_enabled,
        "model_used": model_used,
        "llm_called": llm_called,
        "llm_error": llm_error,
        "reasoning": reasoning,
        "evidence_span": evidence_span,
    }


def _label_model_index(label_models: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for model in label_models:
        for key in [
            model.get("path"),
            model.get("model_no"),
            model.get("template_id"),
            model.get("model_name"),
            model.get("title"),
        ]:
            value = repair_text(key or "").strip()
            if value:
                index[value.lower()] = model
    return index


def _trendyol_bulk_duplicate_key(row: dict[str, Any]) -> str:
    order_no = row.get("order_number") or row.get("trendyol_order_id") or ""
    line_id = row.get("line_id") or ""
    barcode = row.get("barcode") or ""
    sku = row.get("merchant_sku") or row.get("stock_code") or ""
    customer = row.get("customer_name") or ""
    quantity = row.get("quantity") or 1
    raw = "|".join(str(part or "").strip().lower() for part in [order_no, line_id, barcode or sku, quantity, customer])
    return f"trendyol:{hashlib.sha1(raw.encode('utf-8')).hexdigest()}"


def _safe_trendyol_field(row: dict[str, Any], field: str) -> tuple[str, str]:
    value = repair_text(row.get(field) or "").strip()
    if not value:
        return "", "missing"
    sources = row.get("field_sources") if isinstance(row.get("field_sources"), dict) else {}
    source = str(sources.get(field) or "").strip()
    if source in {"product_name", "customer_name"}:
        return "", source
    if _has_question_evidence(row) or source in {"question_text", "answer_text", "manual", "operator", "operator_manual", "template", "mapped_template"}:
        return value, source or "question_evidence"
    return "", source or "no_proof"


def _trendyol_model_for_row(row: dict[str, Any], model_index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for key in [row.get("model_path"), row.get("model_key"), row.get("model_name")]:
        value = repair_text(key or "").strip()
        if value and value.lower() in model_index:
            return model_index[value.lower()]
    return None


def _trendyol_bulk_gallery_item(row: dict[str, Any], model_index: dict[str, dict[str, Any]], batch_id: str, duplicate_key: str) -> dict[str, Any]:
    model = _trendyol_model_for_row(row, model_index)
    label_text, label_source = _safe_trendyol_field(row, "label_text")
    date_text, date_source = _safe_trendyol_field(row, "date_text")
    note_text, note_source = _safe_trendyol_field(row, "note_text")
    laser_text, laser_source = _safe_trendyol_field(row, "name_cut_text")
    proof_text = _question_evidence_text(row) or _answer_evidence_text(row)
    try:
        quantity = max(0, int(row.get("quantity") or 0))
    except (TypeError, ValueError):
        quantity = 0
    errors: list[str] = []
    warnings: list[str] = []
    safety_flags: list[str] = []
    if not model:
        errors.append("Etiket modeli eşleşmedi; Toplu Üretim'de model seçilmeden üretime alınamaz.")
        safety_flags.append("model_missing")
    if quantity < 1:
        errors.append("Adet en az 1 olmalı.")
        safety_flags.append("quantity_invalid")
    if not proof_text:
        if any(src == "operator_manual" for src in [label_source, date_source, note_source, laser_source]):
            safety_flags.append("operator_manual_without_proof")
        else:
            warnings.append("Müşteri mesajı/kanıt yok; kişiselleştirme alanı uydurulmadı.")
            safety_flags.append("proof_missing")
    if not label_text:
        warnings.append("İsim alanı kanıttan net çıkarılamadı; operatör kontrolü gerekli.")
        safety_flags.append("personalization_missing")
    if float(row.get("confidence") or 0) < 0.7:
        warnings.append("Sistem önerisi düşük güvenli; kanıtı kontrol edin.")
        safety_flags.append("low_confidence")
    if label_source in {"product_name", "customer_name"} or laser_source in {"product_name", "customer_name"}:
        warnings.append("Ürün başlığı veya müşteri adından kişiselleştirme yapılmadı; kanıt bekleniyor.")
        safety_flags.append("unsafe_source_ignored")
    status = "ERROR" if errors else "WARNING" if warnings else "READY"
    import_status = "blocked" if errors else "needs_review" if warnings else "proof_confirmed"
    row_id = str(row.get("id") or uuid.uuid4().hex)
    item_id = f"trendyol-{row_id}"
    return {
        "id": item_id,
        "item_id": item_id,
        "row_number": str(row.get("line_id") or row.get("order_number") or row_id[:8]),
        "source": "trendyol",
        "source_label": "Trendyol",
        "source_type": "trendyol",
        "trendyol_order_id": row.get("order_number") or "",
        "source_item_id": row_id,
        "trendyol_suggestion_id": row_id,
        "order_no": row.get("order_number") or "",
        "package_no": row.get("package_id") or "",
        "customer_name": row.get("customer_name") or "",
        "product_name": row.get("product_name") or "",
        "barcode": row.get("barcode") or "",
        "sku": row.get("merchant_sku") or row.get("stock_code") or "",
        "quantity": str(quantity or 1),
        "model_key": row.get("model_key") or "",
        "model_name": str(model.get("title") or model.get("model_name") or row.get("model_name") or "") if model else str(row.get("model_name") or ""),
        "model_status": "FOUND" if model else "MISSING",
        "model_path": str(model.get("path") or row.get("model_path") or "") if model else str(row.get("model_path") or ""),
        "label_model": str(model.get("title") or model.get("model_name") or row.get("model_name") or "") if model else str(row.get("model_name") or ""),
        "label_text": label_text,
        "date_text": date_text,
        "note_text": note_text,
        "laser_name": laser_text,
        "name_cut_text": laser_text,
        "personalized_fields": {
            "name": label_text,
            "date": date_text,
            "note": note_text,
            "laser_name": laser_text,
        },
        "proof_source": "customer_message" if proof_text else "",
        "proof_text": proof_text,
        "proof_message_id": row.get("selected_question_id") or "",
        "confidence": float(row.get("confidence") or 0),
        "trendyol_import_status": import_status,
        "status": status,
        "safety_flags": safety_flags,
        "errors": errors,
        "warnings": warnings,
        "layout_quality_score": 92 if status == "READY" else 64 if status == "WARNING" else 32,
        "is_deleted": False,
        "is_edited": False,
        "created_at": row.get("created_at") or _now(),
        "imported_at": _now(),
        "duplicate_key": duplicate_key,
        "batch_id": batch_id,
        "field_sources": {
            "label_text": label_source,
            "date_text": date_source,
            "note_text": note_source,
            "name_cut_text": laser_source,
        },
        "evidence_status": "proof_confirmed" if proof_text and import_status == "proof_confirmed" else "needs_review" if proof_text else "missing_required_field",
        "product_match_status": "matched" if model else "missing",
    }


def _trendyol_import_audit_event(row: dict[str, Any], event_type: str, severity: str, message: str, batch_id: str, duplicate_key: str, item: dict[str, Any] | None = None) -> dict[str, Any]:
    status = (item or {}).get("trendyol_import_status") or row.get("bulk_import_status") or ""
    return {
        "id": f"audit-{event_type}-{duplicate_key}-{status or 'event'}",
        "event_type": event_type,
        "event_label": {
            "trendyol_sent_to_bulk_production": "Trendyol Toplu Üretim'e aktarıldı",
            "trendyol_personalization_extracted": "Trendyol kişiselleştirme kanıttan önerildi",
            "trendyol_missing_personalization": "Trendyol kişiselleştirme eksik",
            "duplicate_detected": "Duplicate Trendyol aktarımı",
            "blocked_detected": "Trendyol üretime engel kayıt",
            "manual_review_required": "Trendyol kontrol gerekli",
        }.get(event_type, event_type),
        "source": "trendyol",
        "source_label": "Trendyol",
        "origin_source": "trendyol",
        "origin_source_label": "Trendyol",
        "source_item_id": row.get("id") or "",
        "batch_id": batch_id,
        "customer_name": row.get("customer_name") or "",
        "order_no": row.get("order_number") or "",
        "title": row.get("product_name") or row.get("label_text") or "Trendyol üretim kaydı",
        "status": status or row.get("verification_status") or "",
        "severity": severity,
        "message": message,
        "created_at": _now(),
        "metadata": {
            "duplicate_key": duplicate_key,
            "barcode": row.get("barcode") or "",
            "sku": row.get("merchant_sku") or row.get("stock_code") or "",
            "proof_text": (item or {}).get("proof_text") or _question_evidence_text(row),
            "live_trendyol_changed": False,
            "cargo_invoice_triggered": False,
            "safety_flags": (item or {}).get("safety_flags") or [],
        },
    }


def _trendyol_correction_audit_event(row: dict[str, Any], event_type: str, severity: str, message: str, changed_fields: list[dict[str, Any]], batch_id: str) -> dict[str, Any]:
    return {
        "audit_key": f"{event_type}:trendyol:{row.get('id') or ''}:{batch_id}:{hashlib.sha1(json.dumps(changed_fields, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()}",
        "event_type": event_type,
        "event_label": {
            "trendyol_operator_correction_started": "Trendyol operatör düzeltmesi başladı",
            "trendyol_operator_correction_saved": "Trendyol operatör düzeltmesi kaydedildi",
            "trendyol_personalization_confirmed": "Trendyol kişiselleştirme onaylandı",
            "trendyol_personalization_still_missing": "Trendyol kişiselleştirme hâlâ eksik",
            "trendyol_model_matched": "Trendyol model eşleşti",
            "trendyol_model_missing": "Trendyol model eksik",
            "manual_review_required": "Trendyol kontrol gerekli",
        }.get(event_type, event_type),
        "source": "trendyol",
        "source_label": "Trendyol",
        "origin_source": "trendyol",
        "origin_source_label": "Trendyol",
        "source_item_id": row.get("id") or "",
        "batch_id": batch_id,
        "customer_name": row.get("customer_name") or "",
        "order_no": row.get("order_number") or "",
        "title": row.get("product_name") or row.get("label_text") or "Trendyol üretim kaydı",
        "status": row.get("bulk_import_status") or row.get("verification_status") or "",
        "severity": severity,
        "message": message,
        "created_at": _now(),
        "metadata": {
            "changed_fields": changed_fields,
            "field_sources": row.get("field_sources") or {},
            "proof_source": "operator_manual" if row.get("operator_corrected") else row.get("proof_source") or "",
            "operator": "local_operator",
            "live_trendyol_changed": False,
            "cargo_invoice_triggered": False,
        },
    }


def _production_excel_row(row: dict[str, Any]) -> dict[str, Any]:
    production_type = str(row.get("production_type") or "review")
    label_required = production_type in {"label", "label_and_name_cut"}
    name_cut_required = production_type in {"name_cut", "label_and_name_cut"}
    label_model_no = row.get("model_key") or _model_key_from_path(row.get("model_path")) or row.get("barcode") or ""
    name_text = row.get("name_cut_text") or row.get("label_text") or row.get("customer_name") or ""
    return {
        "musteri_adi": row.get("label_text") or row.get("customer_name") or "",
        "tarih": row.get("date_text") or "",
        "not": row.get("note_text") or "",
        "adet": row.get("quantity") or 1,
        "etiket_cikar": "evet" if label_required else "hayır",
        "etiket_no": label_model_no,
        "model_no": label_model_no,
        "label_text": row.get("label_text") or "",
        "date_text": row.get("date_text") or "",
        "note_text": row.get("note_text") or "",
        "isim_kes": "evet" if name_cut_required else "hayır",
        "isim_kesim_text": name_text,
        "isim_kesim_adet": row.get("quantity") or 1,
        "isim_genislik_mm": row.get("name_cut_width_mm") or 300,
        "isim_stil": row.get("name_cut_style") or "Mochary Personal Use Only",
        "kalinlastirma": "orta",
        "offset_mm": 0.8,
        "alt_destek": "hayır",
        "taban_plaka": "hayır",
        "trendyol_order_number": row.get("order_number") or "",
        "trendyol_package_id": row.get("package_id") or "",
        "trendyol_line_id": row.get("line_id") or "",
        "barcode": row.get("barcode") or "",
        "merchant_sku": row.get("merchant_sku") or "",
        "trendyol_soru": _question_evidence_text(row),
        "trendyol_cevap": _answer_evidence_text(row),
        "ai_kanit": ", ".join(row.get("source_evidence") or []),
        "ai_guven": row.get("confidence") or 0,
        "trendyol_dogrulama_durumu": row.get("verification_status") or "",
        "trendyol_kullanici_onayi": "evet" if row.get("user_verified") else "hayır",
        "trendyol_secili_soru_id": row.get("selected_question_id") or "",
        "ai_kaynak_label_text": (row.get("field_sources") or {}).get("label_text", ""),
        "ai_kaynak_date_text": (row.get("field_sources") or {}).get("date_text", ""),
        "ai_kaynak_note_text": (row.get("field_sources") or {}).get("note_text", ""),
        "ai_kaynak_name_cut_text": (row.get("field_sources") or {}).get("name_cut_text", ""),
    }


def _question_evidence_text(row: dict[str, Any]) -> str:
    contexts = row.get("question_contexts") if isinstance(row.get("question_contexts"), list) else []
    texts = [repair_text(item.get("question_text") or "") for item in contexts if isinstance(item, dict) and repair_text(item.get("question_text") or "")]
    if not texts and repair_text(row.get("question_text") or ""):
        texts = [repair_text(row.get("question_text") or "")]
    return " | ".join(texts[:3])


def _answer_evidence_text(row: dict[str, Any]) -> str:
    contexts = row.get("question_contexts") if isinstance(row.get("question_contexts"), list) else []
    texts = [repair_text(item.get("answer_text") or "") for item in contexts if isinstance(item, dict) and repair_text(item.get("answer_text") or "")]
    if not texts and repair_text(row.get("answer_text") or ""):
        texts = [repair_text(row.get("answer_text") or "")]
    return " | ".join(texts[:3])


def _model_key_from_path(value: Any) -> str:
    name = Path(str(value or "")).stem.lower()
    match = re.match(r"(\d+)", name)
    return match.group(1) if match else ""


def _suggestion_from_line(line: dict[str, Any], mapping: dict[str, Any] | None, extracted: dict[str, Any]) -> dict[str, Any]:
    production_type = (mapping or {}).get("production_type") or "review"
    mapping_found = bool(mapping)
    ai_autonomous = bool((mapping or {}).get("_ai_autonomous"))
    has_question = bool(repair_text(line.get("question_text") or "") or line.get("question_contexts"))
    verification_status = _initial_verification_status(mapping_found, production_type, extracted, has_question)
    status = "ready" if verification_status == VERIFICATION_READY else "review"
    warnings = list(extracted.get("warnings") or [])
    if extracted.get("confidence", 0) < 0.7:
        warnings.append("AI önerisi düşük güvenli; kullanıcı onayı olmadan üretime alınmaz.")
    if not mapping_found:
        warnings.append("Bu barcode/SKU için ürün eşleştirmesi yok.")
    if production_type in {"review", "none"}:
        warnings.append("Ürün eşleştirmesi üretim için aktif değil veya kontrol istiyor.")
    if ai_autonomous:
        warnings.append("AI otonom üretim modu: model ve alanlar yüksek güvenle hazırlandı; fiziksel yazdırma/lazer yine kullanıcı onayı gerektirir.")
    if not has_question:
        warnings.append("Müşteri soru/mesaj kanıtı yok; isim/tarih/not kesinleşmeden üretime alınmaz.")
    if any((extracted.get("field_sources") or {}).get(key) in {"product_name", "customer_name"} for key in ["label_text", "name_cut_text"]):
        warnings.append("AI önerisi ürün adı veya müşteri bilgisinden gelmiş olabilir; müşteri sorusu ile doğrulayın.")
    warnings = _drop_stale_source_warnings(warnings, extracted.get("field_sources") or {})
    user_verified = verification_status == VERIFICATION_READY
    return {
        "id": uuid.uuid5(uuid.NAMESPACE_URL, f"{line.get('order_number')}:{line.get('package_id')}:{line.get('line_id')}").hex,
        "source": "trendyol",
        "order_number": line.get("order_number") or "",
        "package_id": line.get("package_id") or "",
        "line_id": line.get("line_id") or "",
        "customer_name": title_turkish_name(line.get("customer_name") or ""),
        "product_name": repair_text(line.get("product_name") or ""),
        "barcode": line.get("barcode") or "",
        "merchant_sku": line.get("merchant_sku") or "",
        "stock_code": line.get("stock_code") or "",
        "source_api": line.get("source_api") or "",
        "question_text": repair_text(line.get("question_text") or ""),
        "answer_text": repair_text(line.get("answer_text") or ""),
        "question_contexts": line.get("question_contexts") or [],
        "image_url": line.get("image_url") or "",
        "product_url": line.get("product_url") or "",
        "image_url_source": line.get("image_url_source") or "",
        "product_url_source": line.get("product_url_source") or "",
        "quantity": extracted.get("quantity") or line.get("quantity") or 1,
        "production_type": production_type,
        "model_key": (mapping or {}).get("model_key") or "",
        "model_path": (mapping or {}).get("model_path") or "",
        "model_name": (mapping or {}).get("model_name") or "",
        "label_text": extracted.get("label_text") or "",
        "date_text": extracted.get("date_text") or "",
        "note_text": extracted.get("note_text") or "",
        "person_names": extracted.get("person_names") or [],
        "custom_text": extracted.get("custom_text") or "",
        "production_note": extracted.get("production_note") or "",
        "name_cut_text": extracted.get("name_cut_text") or "",
        "name_cut_width_mm": extracted.get("name_cut_width_mm") or 300,
        "name_cut_style": extracted.get("name_cut_style") or "Mochary Personal Use Only",
        "confidence": extracted.get("confidence") or 0,
        "ai_model_confidence": (mapping or {}).get("_ai_model_confidence") or 0,
        "ai_autonomous": ai_autonomous,
        "mapping_source": "ai_autonomous" if ai_autonomous else ("barcode_sku" if mapping_found else "none"),
        "status": status,
        "verification_status": verification_status,
        "question_required": True,
        "user_verified": user_verified,
        "verified_at": _now() if user_verified else "",
        "verified_by": "cloud_ai" if user_verified else "",
        "selected_question_id": _first_question_id(line),
        "ignored_question_ids": [],
        "mapping_found": mapping_found,
        "warnings": warnings,
        "source_evidence": extracted.get("source_evidence") or [],
        "field_sources": extracted.get("field_sources") or {},
        "field_confidence": extracted.get("field_confidence") or {},
        "evidence_spans": extracted.get("evidence_spans") or {},
        "needs_user_review": bool(extracted.get("needs_user_review")),
        "import_status": "",
        "created_at": _now(),
        "updated_at": _now(),
    }


def _initial_verification_status(mapping_found: bool, production_type: str, extracted: dict[str, Any], has_question: bool) -> str:
    # Operator approval is mandatory (CLAUDE.md). New rows imported from
    # Trendyol must NEVER auto-advance to VERIFICATION_READY based on AI
    # confidence alone — that was the İrem/Ümit incident root cause
    # (high cloud-AI confidence silently set user_verified=True and sent
    # rows to production without operator review). The READY state is
    # reached ONLY via the explicit operator approval path in
    # set_suggestion_user_verified() (writes verified_by="local_user").
    if not has_question:
        return VERIFICATION_WAITING_EVIDENCE
    if not mapping_found or production_type in {"review", "none", ""}:
        return VERIFICATION_USER_REVIEW
    if float(extracted.get("confidence") or 0) < 0.7:
        return VERIFICATION_USER_REVIEW
    return VERIFICATION_WAITING_APPROVAL


def _is_verified_ready(row: dict[str, Any]) -> bool:
    return (
        row.get("status") == "ready"
        and row.get("verification_status") == VERIFICATION_READY
        and bool(row.get("user_verified"))
    )


def _has_question_evidence(row: dict[str, Any]) -> bool:
    if repair_text(row.get("question_text") or "") or repair_text(row.get("answer_text") or ""):
        return True
    contexts = row.get("question_contexts") if isinstance(row.get("question_contexts"), list) else []
    return any(isinstance(item, dict) and (repair_text(item.get("question_text") or "") or repair_text(item.get("answer_text") or "")) for item in contexts)


def _first_question_id(row: dict[str, Any]) -> str:
    contexts = row.get("question_contexts") if isinstance(row.get("question_contexts"), list) else []
    for item in contexts:
        if isinstance(item, dict) and item.get("id"):
            return str(item.get("id"))
    return ""


def _dedupe_warnings(rows: list[Any]) -> list[str]:
    out: list[str] = []
    for item in rows:
        text = repair_text(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _warning_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", repair_text(value or "").lower())
    return re.sub(r"[^a-z0-9]+", "", text.encode("ascii", "ignore").decode("ascii"))


def _is_product_or_customer_source_warning(value: Any) -> bool:
    key = _warning_key(value)
    return "urunadiveyamusteri" in key or "urunadveyamusteri" in key or "urunveyamusteri" in key or "productorcustomer" in key


def _drop_stale_source_warnings(warnings: list[Any], field_sources: Any) -> list[Any]:
    sources = field_sources if isinstance(field_sources, dict) else {}
    safe_sources = {"question_text", "answer_text"}
    has_unsafe_name_source = any(sources.get(key) in {"product_name", "customer_name"} for key in ["label_text", "name_cut_text"])
    if has_unsafe_name_source:
        return warnings
    return [warning for warning in warnings if not _is_product_or_customer_source_warning(warning)]


def _mapping_from_suggestion(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "production_type": row.get("production_type") or "review",
        "model_key": row.get("model_key") or "",
        "model_path": row.get("model_path") or "",
        "model_name": row.get("model_name") or "",
        "name_cut_style": row.get("name_cut_style") or "",
        "name_cut_width_mm": row.get("name_cut_width_mm") or 300,
    }


def _apply_extracted_fields(row: dict[str, Any], extracted: dict[str, Any]) -> None:
    for key in ["label_text", "date_text", "note_text", "custom_text", "production_note", "name_cut_text"]:
        if key in extracted:
            row[key] = extracted.get(key) or ""
    for key in ["name_cut_style", "name_cut_width_mm", "quantity", "confidence"]:
        if extracted.get(key) not in {None, ""}:
            row[key] = extracted.get(key)
    if extracted.get("person_names") is not None:
        row["person_names"] = extracted.get("person_names") or []
    row["source_evidence"] = list(dict.fromkeys([*(row.get("source_evidence") or []), *(extracted.get("source_evidence") or [])]))
    row["field_sources"] = extracted.get("field_sources") or row.get("field_sources") or {}
    row["field_confidence"] = extracted.get("field_confidence") or row.get("field_confidence") or {}
    if extracted.get("classification") is not None:
        row["classification"] = extracted.get("classification")
    row["evidence_spans"] = extracted.get("evidence_spans") or row.get("evidence_spans") or {}
    row["needs_user_review"] = bool(extracted.get("needs_user_review"))
    existing_warnings = [warning for warning in (row.get("warnings") or []) if not _is_extraction_refresh_warning(warning)]
    warnings = [*existing_warnings, *(extracted.get("warnings") or [])]
    row["warnings"] = _dedupe_warnings(_drop_stale_source_warnings(warnings, row.get("field_sources")))


def _needs_extraction_refresh(row: dict[str, Any]) -> bool:
    if row.get("verification_status") == VERIFICATION_TRANSFERRED or row.get("import_status"):
        return False
    has_message = bool(repair_text(row.get("question_text") or "")) or _has_question_evidence(row)
    if not has_message:
        return False
    warnings = " | ".join(repair_text(item) for item in (row.get("warnings") or []))
    if "Müşteri mesajı yok" in warnings or "musteri mesaji yok" in _ascii_key(warnings):
        return True
    if not row.get("source_evidence"):
        return True
    if (row.get("question_text") or "") and not row.get("label_text") and not row.get("name_cut_text") and not row.get("date_text") and not row.get("note_text"):
        return True
    if row.get("label_text") and _label_has_known_bad_instruction(row.get("label_text")):
        return True
    return False


def _ascii_key(value: Any) -> str:
    text = repair_text(value).casefold()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _label_has_known_bad_instruction(value: Any) -> bool:
    key = _ascii_key(value)
    markers = [
        "gumus", "hepsi beyaz", "hatirasi", "isteme tarihi", "kurdele",
        "gold yazi", "cikolata", "cicek", "tasarim", "numaram",
        "kisisellestirme", "isimleri", "yazilacaklar",
    ]
    return any(marker in key for marker in markers)


def _is_extraction_refresh_warning(value: Any) -> bool:
    text = repair_text(value).lower()
    return any(
        marker in text
        for marker in [
            "ai alan ayıklama",
            "ai önerisi düşük",
            "bulut ai alan ayıklama",
            "müşteri mesajında kişi ismi",
            "mesaj renk/tasarım",
            "tarih müşteri mesajında",
            "final validator",
        ]
    )


def _merge_question_contexts(existing: Any, incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [row for row in (existing if isinstance(existing, list) else []) if isinstance(row, dict)]
    seen = {str(row.get("id") or json.dumps(row, ensure_ascii=False, sort_keys=True)) for row in rows}
    for row in incoming:
        key = str(row.get("id") or json.dumps(row, ensure_ascii=False, sort_keys=True))
        if key not in seen:
            rows.append(row)
            seen.add(key)
    return rows[:8]


def _all_question_contexts_for_suggestion(project_root: Path, suggestion: dict[str, Any]) -> list[dict[str, Any]]:
    contexts = [row for row in (suggestion.get("question_contexts") if isinstance(suggestion.get("question_contexts"), list) else []) if isinstance(row, dict)]
    index = _question_context_index(list_questions(project_root))
    enriched = _attach_question_context(suggestion, index)
    extra = [row for row in (enriched.get("question_contexts") if isinstance(enriched.get("question_contexts"), list) else []) if isinstance(row, dict)]
    return _merge_question_contexts(contexts, extra)


def _normalize_line(order_number: str, package_id: str, customer_name: str, line: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_number": order_number,
        "package_id": package_id,
        "line_id": str(line.get("id") or line.get("lineId") or line.get("itemId") or ""),
        "customer_name": title_turkish_name(customer_name),
        "product_name": repair_text(line.get("productName") or line.get("name") or ""),
        "barcode": str(line.get("barcode") or line.get("sellerBarcode") or ""),
        "merchant_sku": str(line.get("merchantSku") or line.get("stockCode") or ""),
        "stock_code": str(line.get("stockCode") or ""),
        "quantity": _safe_int(line.get("quantity") or line.get("newQuantity") or line.get("completedQuantity"), 1),
        "product_color": repair_text(line.get("productColor") or ""),
        "product_size": repair_text(line.get("productSize") or ""),
        "question_text": repair_text(line.get("questionText") or line.get("question_text") or ""),
        "answer_text": repair_text(line.get("answerText") or line.get("answer_text") or ""),
        "source_api": str(line.get("source_api") or ""),
        "image_url": _line_image_url(line),
        "product_url": str(line.get("productUrl") or line.get("product_url") or ""),
        "image_url_source": "order_line" if _line_image_url(line) else "",
        "product_url_source": "order_line" if str(line.get("productUrl") or line.get("product_url") or "").strip() else "",
    }


def _customer_name(order: dict[str, Any]) -> str:
    repaired_full = repair_text(order.get("customerName") or "").strip()
    if repaired_full:
        return title_turkish_name(repaired_full)
    repaired_first = repair_text(order.get("customerFirstName") or "").strip()
    repaired_last = repair_text(order.get("customerLastName") or "").strip()
    repaired_joined = " ".join(part for part in [repaired_first, repaired_last] if part).strip()
    return title_turkish_name(repaired_joined) or "Trendyol Müşteri"
    full = str(order.get("customerName") or "").strip()
    if full:
        return full
    first = str(order.get("customerFirstName") or "").strip()
    last = str(order.get("customerLastName") or "").strip()
    return " ".join(part for part in [first, last] if part).strip() or "Trendyol Müşteri"


def _line_image_url(line: dict[str, Any]) -> str:
    images = line.get("images") if isinstance(line.get("images"), list) else []
    if images and isinstance(images[0], dict):
        return str(images[0].get("url") or images[0].get("imageUrl") or "")
    if images and isinstance(images[0], str):
        return str(images[0])
    for key in ["imageUrl", "image_url", "productImageUrl", "product_image_url", "image"]:
        if line.get(key):
            return str(line.get(key) or "")
    return ""


def _test_connection_probe(project_root: Path, *, force_stage: bool | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    products = _fetch_json(project_root, f"/product/sellers/{_supplier_id(project_root)}/products?page=0&size=1", v2=False, force_stage=force_stage)
    now = int(time.time() * 1000)
    packages = _fetch_json(
        project_root,
        f"/integration/ecgw/v2/{_supplier_id(project_root)}/packages?creationStartDate={now - 86400000}&creationEndDate={now}&page=1&size=1",
        v2=True,
        force_stage=force_stage,
    )
    return products, packages


def _fetch_json_with_retry(
    project_root: Path,
    path: str,
    *,
    v2: bool,
    timeout: int = 20,
    max_retries: int = 4,
) -> dict[str, Any]:
    """_fetch_json with exponential backoff on 429/502/503 and connection errors."""
    delay = 2.0
    last_exc: Exception = RuntimeError("No attempts")
    for attempt in range(max_retries + 1):
        try:
            return _fetch_json(project_root, path, v2=v2, timeout=timeout)
        except RuntimeError as exc:
            last_exc = exc
            code_match = re.search(r"HTTP (\d+)", str(exc))
            code = int(code_match.group(1)) if code_match else 0
            if code not in _RETRY_ON_CODES:
                raise
        except OSError as exc:
            last_exc = exc
        if attempt < max_retries:
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
    raise last_exc


def _fetch_json(project_root: Path, path: str, *, v2: bool, force_stage: bool | None = None, timeout: int = 20) -> dict[str, Any]:
    settings = get_settings(project_root, masked=False)
    problem = _credential_configuration_problem(settings)
    if problem:
        raise RuntimeError(problem)
    stage = bool(settings.get("stage")) if force_stage is None else bool(force_stage)
    base = (STAGE_BASE_URL_V2 if stage else LIVE_BASE_URL_V2) if v2 else (STAGE_BASE_URL if stage else LIVE_BASE_URL)
    url = f"{base}{path}"
    token = base64.b64encode(f"{settings['api_key']}:{settings['api_secret']}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {token}",
            "User-Agent": f"{settings['supplier_id']} - SelfIntegration",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(_format_trendyol_http_error(exc.code, body, stage=stage)) from exc


def _format_trendyol_http_error(code: int, body: str, *, stage: bool) -> str:
    raw = (body or "").strip()
    is_html = bool(re.search(r"<!doctype|<html|cloudflare|access denied", raw, flags=re.IGNORECASE))
    if is_html:
        detail = "Trendyol gateway HTML hata sayfası döndürdü; gizli bilgiler gösterilmedi."
    else:
        detail = re.sub(r"\s+", " ", raw)[:220] or "Trendyol yanıt gövdesi boş."
    if code in {401, 403}:
        if stage:
            hint = "Stage/test ortamı canlı API bilgilerini kabul etmeyebilir; canlı bilgiler için Stage/test kapalı olmalı."
        else:
            hint = "Supplier ID, Trendyol API key/secret, mağaza yetkisi veya Trendyol entegrasyon iznini kontrol edin."
        return f"HTTP {code}: {detail} {hint}"
    return f"HTTP {code}: {detail}"


def _credential_configuration_problem(settings: dict[str, Any]) -> str:
    api_key = str(settings.get("api_key") or "").strip()
    api_secret = str(settings.get("api_secret") or "").strip()
    ai_key = str(settings.get("ai_api_key") or "").strip()
    if _looks_like_openai_key(api_key):
        return (
            "Trendyol API Key alanında OpenAI anahtarı görünüyor. "
            "API Ayarları sekmesinde Trendyol satıcı panelindeki Trendyol API Key değerini girin; OpenAI anahtarı sadece AI API Key alanında kalmalı."
        )
    if ai_key and api_key and api_key == ai_key:
        return (
            "Trendyol API Key ile AI API Key aynı kaydedilmiş. "
            "Trendyol API Key alanına Trendyol satıcı panelindeki anahtarı, AI API Key alanına OpenAI anahtarını girin."
        )
    if _looks_like_openai_key(api_secret):
        return (
            "Trendyol API Secret alanında OpenAI anahtarı görünüyor. "
            "API Secret alanına Trendyol satıcı panelindeki secret değeri girilmeli."
        )
    return ""


def _looks_like_openai_key(value: str) -> bool:
    text = str(value or "").strip()
    return text.startswith(("sk-", "sk_proj", "sk-proj"))


def _trendyol_connection_message(error: str, *, stage: bool) -> str:
    clean = re.sub(r"<!doctype.*", "HTML hata sayfası gizlendi.", error, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    if stage and "403" in clean:
        return (
            "Trendyol bağlantısı kurulamadı: HTTP 403. Stage/test ortamı açık görünüyor. "
            "Canlı Trendyol API bilgileri için Stage/test kutusunu kapatın; test hesabı kullanıyorsanız Trendyol stage yetkisini kontrol edin."
        )
    return f"Trendyol bağlantısı kurulamadı: {clean}"


def _safe_trendyol_service_message(error: str, *, stage: bool = False) -> str:
    clean = _trendyol_connection_message(error, stage=stage)
    clean = clean.replace("Trendyol bağlantısı kurulamadı: ", "")
    clean = re.sub(r'"?(api[_ -]?key|api[_ -]?secret|apikey|apisecret|authorization|basic)"?\s*:\s*"[^"]*"', '"secret":"gizlendi"', clean, flags=re.IGNORECASE)
    clean = re.sub(r"(api[_ -]?key|api[_ -]?secret|apikey|apisecret|authorization|basic)\s*[:=]\s*[^,\s]+", r"\1 gizlendi", clean, flags=re.IGNORECASE)
    clean = re.sub(r"apiSecret|apiKey|api_secret|api_key", "secret", clean, flags=re.IGNORECASE)
    clean = re.sub(r"should-not-leak", "gizlendi", clean, flags=re.IGNORECASE)
    return clean[:260]


def _repair_trendyol_row(row: dict[str, Any]) -> dict[str, Any]:
    repaired = dict(row)
    for key in [
        "customer_name",
        "product_name",
        "label_text",
        "date_text",
        "note_text",
        "name_cut_text",
        "model_name",
        "brand",
        "category",
        "question_text",
        "answer_text",
    ]:
        if key in repaired:
            repaired[key] = repair_text(repaired.get(key))
    if "warnings" in repaired and isinstance(repaired["warnings"], list):
        repaired["warnings"] = [repair_text(item) for item in repaired["warnings"]]
    if "source_evidence" in repaired and isinstance(repaired["source_evidence"], list):
        repaired["source_evidence"] = [repair_text(item) for item in repaired["source_evidence"]]
    if "question_contexts" in repaired and isinstance(repaired["question_contexts"], list):
        repaired["question_contexts"] = [_repair_trendyol_row(item) if isinstance(item, dict) else item for item in repaired["question_contexts"]]
    repaired.setdefault("verification_status", VERIFICATION_READY if repaired.get("status") == "ready" and repaired.get("user_verified") else VERIFICATION_WAITING_EVIDENCE)
    repaired.setdefault("question_required", True)
    repaired.setdefault("user_verified", False)
    repaired.setdefault("selected_question_id", _first_question_id(repaired))
    repaired.setdefault("ignored_question_ids", [])
    repaired.setdefault("field_sources", {})
    repaired.setdefault("evidence_spans", {})
    repaired.setdefault("needs_user_review", False)
    return repaired


def _normalize_product(product: dict[str, Any]) -> dict[str, Any]:
    images = product.get("images") if isinstance(product.get("images"), list) else []
    image_urls = [
        str(item.get("url") or item.get("imageUrl") or "")
        for item in images
        if isinstance(item, dict) and str(item.get("url") or item.get("imageUrl") or "").strip()
    ]
    if not image_urls:
        for key in ["imageUrl", "image_url", "productImageUrl", "primary_image_url"]:
            if product.get(key):
                image_urls.append(str(product.get(key) or ""))
    title = repair_text(product.get("title") or product.get("name") or "").strip()
    barcode = str(product.get("barcode") or "").strip()
    stock_code = str(product.get("stockCode") or product.get("stock_code") or "").strip()
    merchant_sku = str(product.get("merchantSku") or product.get("merchant_sku") or stock_code).strip()
    content_descriptions = product.get("contentDescriptions") if isinstance(product.get("contentDescriptions"), list) else []
    description = repair_text(product.get("description") or "")
    if not description and content_descriptions:
        description = " ".join(
            repair_text(item.get("description") or "")
            for item in sorted((item for item in content_descriptions if isinstance(item, dict)), key=lambda row: row.get("order") or 0)
        ).strip()
    normalized = {
        "id": uuid.uuid5(uuid.NAMESPACE_URL, f"trendyol-product:{barcode or merchant_sku or title}").hex,
        "product_name": title,
        "barcode": barcode,
        "merchant_sku": merchant_sku,
        "stock_code": stock_code,
        "product_main_id": str(product.get("productMainId") or product.get("product_main_id") or ""),
        "image_url": image_urls[0] if image_urls else "",
        "primary_image_url": image_urls[0] if image_urls else "",
        "image_urls": image_urls,
        "product_url": str(product.get("productUrl") or ""),
        "brand": repair_text(product.get("brand") or product.get("brandName") or ""),
        "category": repair_text(product.get("categoryName") or ""),
        "description": description,
        "content_descriptions": content_descriptions,
    }
    return normalized


def _product_catalog_index(products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for product in products:
        if not isinstance(product, dict):
            continue
        normalized = _normalize_product(product)
        for key in [
            normalized.get("barcode"),
            normalized.get("merchant_sku"),
            normalized.get("stock_code"),
        ]:
            identity = _identity_key(key)
            if identity and identity not in index:
                index[identity] = normalized
        for key in _product_name_reference_keys(normalized.get("product_name")):
            if key and key not in index:
                index[key] = normalized
    return index


def _cached_product_reference_index(project_root: Path) -> dict[str, dict[str, Any]]:
    references: list[dict[str, Any]] = []
    references.extend(list_mapping_suggestions(project_root))
    references.extend(trendyol_mapping_api.list_product_mappings(project_root))
    index: dict[str, dict[str, Any]] = {}
    for row in references:
        normalized = {
            "product_name": repair_text(row.get("product_name") or ""),
            "barcode": str(row.get("barcode") or ""),
            "merchant_sku": str(row.get("merchant_sku") or ""),
            "stock_code": str(row.get("stock_code") or ""),
            "image_url": str(row.get("image_url") or row.get("primary_image_url") or ""),
            "primary_image_url": str(row.get("primary_image_url") or row.get("image_url") or ""),
            "image_urls": row.get("image_urls") if isinstance(row.get("image_urls"), list) else [],
            "product_url": str(row.get("product_url") or ""),
            "brand": repair_text(row.get("brand") or ""),
            "category": repair_text(row.get("category") or ""),
            "description": repair_text(row.get("description") or ""),
        }
        if not normalized["image_url"] and not normalized["product_url"]:
            continue
        for identity in [
            _identity_key(normalized.get("barcode")),
            _identity_key(normalized.get("merchant_sku")),
            _identity_key(normalized.get("stock_code")),
            *_product_name_reference_keys(normalized.get("product_name")),
        ]:
            if identity and identity not in index:
                index[identity] = normalized
    return index


def _enrich_line_with_catalog(line: dict[str, Any], product_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    enriched = dict(line)
    exact_identities = [
        line.get("barcode"),
        line.get("sellerBarcode"),
        line.get("merchantSku"),
        line.get("stockCode"),
        line.get("merchant_sku"),
        line.get("stock_code"),
    ]
    exact_product = next((product_index.get(_identity_key(item)) for item in exact_identities if _identity_key(item)), None)
    fuzzy_identities = _product_name_reference_keys(line.get("product_name") or line.get("productName") or line.get("name"))
    fuzzy_product = next((product_index.get(_identity_key(item)) for item in fuzzy_identities if _identity_key(item)), None)
    product = exact_product or fuzzy_product
    if not product:
        return enriched
    match_source = "catalog_exact" if exact_product else "catalog_name"
    if not _line_image_url(enriched) and product.get("image_url"):
        enriched["image_url"] = product.get("image_url")
        enriched["image_url_source"] = match_source
    if not enriched.get("productUrl") and product.get("product_url") and exact_product:
        enriched["productUrl"] = product.get("product_url")
        enriched["product_url_source"] = match_source
    if not enriched.get("product_url") and product.get("product_url") and exact_product:
        enriched["product_url"] = product.get("product_url")
        enriched["product_url_source"] = match_source
    if not enriched.get("brand") and product.get("brand"):
        enriched["brand"] = product.get("brand")
    if not enriched.get("categoryName") and product.get("category"):
        enriched["categoryName"] = product.get("category")
    if not enriched.get("productName") and product.get("product_name"):
        enriched["productName"] = product.get("product_name")
    return enriched


def _product_name_reference_keys(value: Any) -> list[str]:
    text = repair_text(value or "")
    keys: list[str] = []
    for token in re.findall(r"[A-Za-z]{2,}[A-Za-z0-9]{4,}|\d{6,}", text):
        key = _identity_key(token)
        if key and key not in keys:
            keys.append(key)
    compact = _search_key(text)
    if compact and compact not in keys:
        keys.append(compact)
    return keys


def _normalize_question_context(
    project_root: Path,
    question: dict[str, Any],
    *,
    use_cloud_ai: bool = False,
    product_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    answer = question.get("answer") if isinstance(question.get("answer"), dict) else {}
    product = question.get("product") if isinstance(question.get("product"), dict) else {}
    customer = question.get("customer") if isinstance(question.get("customer"), dict) else {}
    question_text = question.get("text") or question.get("questionText") or question.get("question") or question.get("content") or ""
    answer_text = answer.get("text") or question.get("answerText") or question.get("answer") or ""
    detected_order_number = _detect_question_order_number(question_text) or _detect_question_order_number(answer_text)
    source = {
        "order_number": question.get("orderNumber") or question.get("order_number") or detected_order_number or "",
        "package_id": question.get("packageId") or question.get("shipmentPackageId") or question.get("package_id") or "",
        "line_id": question.get("lineId") or question.get("line_id") or question.get("orderLineId") or "",
        "product_name": question.get("productName") or question.get("product_name") or question.get("name") or product.get("title") or product.get("name") or product.get("productName") or "",
        "barcode": question.get("barcode") or question.get("productBarcode") or product.get("barcode") or product.get("productBarcode") or "",
        "merchant_sku": question.get("merchantSku") or question.get("stockCode") or product.get("merchantSku") or product.get("stockCode") or "",
        "stock_code": question.get("stockCode") or product.get("stockCode") or "",
        "customer_name": question.get("customerName") or question.get("userName") or customer.get("fullName") or customer.get("name") or "Trendyol Müşteri",
        "question_text": question_text,
        "answer_text": answer_text,
        "image_url": question.get("imageUrl") or question.get("image_url") or product.get("imageUrl") or product.get("image_url") or "",
        "product_url": question.get("productUrl") or product.get("productUrl") or "",
        "quantity": 1,
    }
    created_date = _remote_time_text(
        question.get("creationDate")
        or question.get("createdDate")
        or question.get("created_at")
        or question.get("questionDate")
    )
    last_modified_at = _remote_time_text(
        question.get("lastModifiedDate")
        or question.get("lastModifiedAt")
        or question.get("last_update_date")
        or question.get("lastUpdateDate")
        or answer.get("creationDate")
        or created_date
    )
    source = _enrich_question_source_with_catalog(project_root, source, product_index=product_index)
    mapping = trendyol_mapping_api.find_mapping_for_line(project_root, source)
    if use_cloud_ai:
        deterministic = extract_production_fields(source, mapping)
        extracted = extract_with_ai_or_fallback(project_root, source, mapping, deterministic, get_settings(project_root, masked=False))
    else:
        extracted = {
            "label_text": "",
            "date_text": "",
            "note_text": "",
            "name_cut_text": "",
            "confidence": 0,
            "warnings": [],
            "source_evidence": [],
            "field_sources": {},
            "evidence_spans": {},
            "needs_user_review": True,
        }
    return {
        "id": str(question.get("id") or question.get("questionId") or uuid.uuid5(uuid.NAMESPACE_URL, json.dumps(source, ensure_ascii=False, sort_keys=True)).hex),
        "status": str(question.get("status") or ""),
        "answered": bool(question.get("answered") or question.get("answer")),
        "order_number": source["order_number"],
        "package_id": source["package_id"],
        "line_id": source["line_id"],
        "product_name": source["product_name"],
        "barcode": source["barcode"],
        "merchant_sku": source["merchant_sku"],
        "stock_code": source["stock_code"],
        "customer_name": source["customer_name"],
        "question_text": source["question_text"],
        "answer_text": source["answer_text"],
        "image_url": source.get("image_url") or "",
        "primary_image_url": source.get("primary_image_url") or source.get("image_url") or "",
        "image_urls": source.get("image_urls") or [],
        "description": source.get("description") or "",
        "product_url": source.get("product_url") or "",
        "brand": source.get("brand") or "",
        "category": source.get("category") or "",
        "label_text": extracted.get("label_text") or "",
        "date_text": extracted.get("date_text") or "",
        "note_text": extracted.get("note_text") or "",
        "name_cut_text": extracted.get("name_cut_text") or "",
        "confidence": extracted.get("confidence") or 0,
        "warnings": extracted.get("warnings") or [],
        "source_evidence": extracted.get("source_evidence") or [],
        "field_sources": extracted.get("field_sources") or {},
        "evidence_spans": extracted.get("evidence_spans") or {},
        "needs_user_review": bool(extracted.get("needs_user_review")),
        "created_date": created_date,
        "last_modified_at": last_modified_at,
        "synced_at": _now(),
        "created_at": created_date or _now(),
    }


def _detect_question_order_number(text: Any) -> str:
    repaired = repair_text(text)
    if not repaired:
        return ""
    for pattern in ORDER_NUMBER_PATTERNS:
        match = pattern.search(repaired)
        if match:
            return str(match.group(1) or "").strip()
    return ""


def _enrich_question_source_with_catalog(
    project_root: Path,
    source: dict[str, Any],
    *,
    product_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    index = product_index if product_index is not None else _cached_product_reference_index(project_root)
    if not index:
        return source
    identities = [
        source.get("barcode"),
        source.get("merchant_sku"),
        source.get("stock_code"),
        *_product_name_reference_keys(source.get("product_name")),
        *_product_name_reference_keys(source.get("question_text")),
    ]
    product = next((index.get(_identity_key(item)) for item in identities if _identity_key(item)), None)
    if not product:
        return source
    enriched = dict(source)
    if not enriched.get("product_name") and product.get("product_name"):
        enriched["product_name"] = product.get("product_name")
    for key in ["image_url", "primary_image_url", "image_urls", "product_url", "brand", "category", "description"]:
        if not enriched.get(key) and product.get(key):
            enriched[key] = product.get(key)
    if not enriched.get("barcode") and product.get("barcode"):
        enriched["barcode"] = product.get("barcode")
    if not enriched.get("merchant_sku") and product.get("merchant_sku"):
        enriched["merchant_sku"] = product.get("merchant_sku")
    if not enriched.get("stock_code") and product.get("stock_code"):
        enriched["stock_code"] = product.get("stock_code")
    return enriched


def _ai_autonomous_mapping(project_root: Path, line: dict[str, Any], extracted: dict[str, Any], label_models: list[dict[str, Any]]) -> dict[str, Any] | None:
    settings = get_settings(project_root, masked=False)
    if not _safe_bool(settings.get("ai_autonomous_production_enabled"), True):
        return None
    if not label_models:
        return None
    model, score, reasons = _guess_label_model(line, label_models)
    if not model or score < float(settings.get("ai_autonomous_model_threshold") or AI_AUTONOMOUS_MODEL_THRESHOLD):
        return None
    field_confidence = float(extracted.get("confidence") or 0)
    has_question_evidence = bool(repair_text(line.get("question_text") or "") or repair_text(line.get("answer_text") or ""))
    if has_question_evidence and field_confidence < float(settings.get("ai_autonomous_field_threshold") or AI_AUTONOMOUS_FIELD_THRESHOLD):
        return None
    production_type = "label_and_name_cut" if _looks_like_name_cut(line) else "label"
    return {
        "production_type": production_type,
        "model_key": str(model.get("model_no") or _model_key_from_path(model.get("path")) or ""),
        "model_path": str(model.get("path") or ""),
        "model_name": repair_text(model.get("model_name") or model.get("title") or model.get("name") or ""),
        "name_cut_style": "Mochary Personal Use Only",
        "name_cut_width_mm": 300,
        "_ai_autonomous": True,
        "_ai_model_confidence": round(score, 2),
        "_ai_reasons": reasons,
    }


def _guess_label_model(product: dict[str, Any], label_models: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float, list[str]]:
    product_text = " ".join(str(product.get(key) or "") for key in ["product_name", "category", "brand"])
    product_haystack = _search_key(product_text)
    identifier_text = " ".join(str(product.get(key) or "") for key in ["merchant_sku", "stock_code"])
    identifier_haystack = _search_key(identifier_text)
    barcode_haystack = _search_key(product.get("barcode"))
    best: dict[str, Any] | None = None
    best_score = 0.0
    best_reasons: list[str] = []
    for model in label_models:
        if not _catalog_model_is_safe(model):
            continue
        score = 0.0
        reasons: list[str] = []
        model_no = str(model.get("model_no") or "").strip()
        template_no = str(model.get("template_no") or "").strip()
        if model_no and _contains_model_code(product_text, model_no):
            score += 0.5
            reasons.append("model_no_product_text")
        elif model_no and _contains_model_code(identifier_text, model_no):
            score += 0.75
            reasons.append("model_no_sku")
        elif model_no and barcode_haystack == _search_key(model_no):
            score += 0.28
            reasons.append("model_no_exact_barcode")

        if template_no and model_no and _contains_model_code(product_text, model_no) and _contains_model_code(product_text, template_no):
            score += 0.18
            reasons.append("template_no_paired_text")

        for key in ["label_variant", "model_name", "title", "name"]:
            value = _search_key(model.get(key))
            if not value:
                continue
            if value and value in product_haystack:
                score += 0.3 if key in {"model_name", "title", "name"} else 0.22
                reasons.append(f"{key}_text")
        model_path_key = _search_key(Path(str(model.get("path") or "")).stem)
        if model_path_key and model_path_key in product_haystack:
            score += 0.28
            reasons.append("template_file_match")
        if score > best_score:
            best = model
            best_score = score
            best_reasons = reasons
    return best, min(best_score, 0.98), best_reasons


def _catalog_model_is_safe(model: dict[str, Any]) -> bool:
    text = _search_key(" ".join(str(model.get(key) or "") for key in ["model_name", "template_name", "title", "name", "path"]))
    if any(token in text for token in ["qa", "test", "deneme", "kabul"]):
        return False
    return bool(model.get("path") or model.get("model_name") or model.get("title"))


def _contains_model_code(text: Any, code: str) -> bool:
    raw_code = str(code or "").strip()
    if not raw_code:
        return False
    pattern = rf"(?<![A-Za-z0-9]){re.escape(raw_code)}(?![A-Za-z0-9])"
    if re.search(pattern, str(text or ""), flags=re.IGNORECASE):
        return True
    normalized_text = _search_key(text)
    normalized_code = _search_key(raw_code)
    return bool(normalized_code and normalized_text == normalized_code)


def _looks_like_name_cut(product: dict[str, Any]) -> bool:
    text = _search_key(" ".join(str(product.get(key) or "") for key in ["product_name", "barcode", "merchant_sku", "stock_code", "category"]))
    return any(token in text for token in ["isimkesim", "isimkes", "lazerisim", "namecut", "pleksiisim", "isimlik"])


def _looks_like_label_product(product: dict[str, Any]) -> bool:
    text = _search_key(" ".join(str(product.get(key) or "") for key in ["product_name", "barcode", "merchant_sku", "stock_code", "category"]))
    label_tokens = [
        "etiket",
        "isimlibaski",
        "isimbaskili",
        "soznisan",
        "soz",
        "nisan",
        "kizisteme",
        "cikolata",
        "bebekcikolatasi",
        "mevlut",
    ]
    return any(token in text for token in label_tokens)


def _search_key(value: Any) -> str:
    text = str(value or "").lower()
    table = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return re.sub(r"[^a-z0-9]+", "", text.translate(table))


def _identity_key(value: Any) -> str:
    return str(value or "").strip().lower()


def _save_suggestions(project_root: Path, rows: list[dict[str, Any]]) -> None:
    suggestions_path(project_root).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_mapping_suggestions(project_root: Path, rows: list[dict[str, Any]]) -> None:
    mapping_suggestions_path(project_root).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_questions(project_root: Path, rows: list[dict[str, Any]]) -> None:
    questions_path(project_root).write_text(json.dumps(_sort_questions_newest_first(rows), ensure_ascii=False, indent=2), encoding="utf-8")


def _dedupe_questions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        key = str(row.get("id") or row.get("question_id") or "")
        if not key:
            key = "|".join(
                str(row.get(field) or "")
                for field in ("order_number", "line_id", "barcode", "question_text")
            ) or f"row-{index}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _remote_time_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)) or str(value).strip().isdigit():
        try:
            number = int(float(value))
            if number > 10_000_000_000:
                number = number // 1000
            return datetime.fromtimestamp(number).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, OverflowError, ValueError):
            return str(value)
    text = str(value).strip()
    return text.replace("T", " ").replace("Z", "")[:19]


def _question_sort_key(row: dict[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("last_modified_at") or row.get("created_date") or row.get("created_at") or ""),
        str(row.get("id") or ""),
    )


def _sort_questions_newest_first(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=_question_sort_key, reverse=True)


def delta_sync_for_poll(project_root: Path) -> dict[str, Any]:
    """Lightweight incremental sync for the auto-poll scheduler.

    - Fetches only Created/Picking packages since last sync (typically 0-5 requests).
    - Skips _fetch_package_items_v2 for already-cached packages.
    - Merges new orders into the existing cache.
    - Runs AI extraction only on NEW suggestions if AI is enabled.
    Returns {status, new_orders, new_questions, total_orders, message}.
    """
    if not is_configured(project_root):
        return {"status": "CONFIG_MISSING", "new_orders": 0, "new_questions": 0, "message": "API ayarları eksik."}
    settings_raw = get_settings(project_root, masked=False)
    end = datetime.now()
    last_sync_str = settings_raw.get("last_orders_sync_at") or settings_raw.get("last_sync_at") or ""
    if last_sync_str:
        try:
            last_dt = datetime.strptime(last_sync_str[:19], "%Y-%m-%d %H:%M:%S")
            # 5-minute buffer; cap at 7 days for first-ever poll after manual sync
            api_start = max(last_dt - timedelta(minutes=5), end - timedelta(days=7))
        except ValueError:
            api_start = end - timedelta(days=7)
    else:
        api_start = end - timedelta(days=7)
    cached_by_id = _load_cached_orders_by_package_id(project_root)
    try:
        new_orders = fetch_orders(
            project_root, api_start, end,
            skip_package_ids=set(cached_by_id.keys()),
            poll_statuses=["Created", "Picking"],
        )
    except Exception as exc:  # noqa: BLE001
        detail = _safe_trendyol_service_message(str(exc), stage=bool(settings_raw.get("stage")))
        return {"status": "UNAVAILABLE", "new_orders": 0, "new_questions": 0, "message": detail}
    new_question_rows: list[dict[str, Any]] = []
    try:
        new_question_rows = _refresh_questions_delta(project_root)
    except Exception:  # noqa: BLE001
        pass
    if not new_orders and not new_question_rows:
        _save_orders_sync_status(
            project_root, "OK", "Delta poll: yeni sipariş yok.",
            len(cached_by_id), len(list_questions(project_root)),
        )
        return {"status": "OK_NO_NEW", "new_orders": 0, "new_questions": 0, "total_orders": len(cached_by_id), "message": "Yeni sipariş yok."}
    # Merge new orders into cache
    merged_map = dict(cached_by_id)
    for order in new_orders:
        pid = str(order.get("shipmentPackageId") or "")
        if pid:
            merged_map[pid] = order
    all_orders = enrich_orders_with_product_catalog(project_root, list(merged_map.values()))
    all_questions = list_questions(project_root)
    _save_readonly_orders_cache(project_root, all_orders, start=api_start, end=end, questions=all_questions)
    # Build suggestions for NEW orders only
    run_ai = bool(settings_raw.get("ai_enabled"))
    new_suggestions = build_suggestions_from_orders(
        project_root, new_orders,
        questions=all_questions,
        run_ai=run_ai,
        reuse_existing=False,
    )
    # Merge new suggestions into existing (dedupe by order:package:line key)
    existing_sug = list_suggestions(project_root)
    existing_keys = {
        f"{s.get('order_number', '')}:{s.get('package_id', '')}:{s.get('line_id', '')}"
        for s in existing_sug if isinstance(s, dict)
    }
    truly_new = [
        s for s in new_suggestions
        if f"{s.get('order_number', '')}:{s.get('package_id', '')}:{s.get('line_id', '')}" not in existing_keys
    ]
    if truly_new:
        _save_suggestions(project_root, existing_sug + truly_new)
    total = len(merged_map)
    msg = f"Delta poll: {len(new_orders)} yeni sipariş, {len(new_question_rows)} yeni soru çekildi."
    _save_orders_sync_status(project_root, "OK", msg, total, len(all_questions))
    return {
        "status": "OK",
        "new_orders": len(new_orders),
        "new_questions": len(new_question_rows),
        "new_suggestions": len(truly_new),
        "total_orders": total,
        "message": msg,
    }


def _refresh_questions_delta(project_root: Path) -> list[dict[str, Any]]:
    """Fetch only questions modified since last questions sync (single page, fast)."""
    if not is_configured(project_root):
        return []
    settings_raw = get_settings(project_root, masked=False)
    last_q_str = settings_raw.get("last_questions_sync_at") or ""
    if not last_q_str:
        return []
    try:
        last_dt = datetime.strptime(last_q_str[:19], "%Y-%m-%d %H:%M:%S")
        since_dt = last_dt - timedelta(minutes=5)
    except ValueError:
        return []
    supplier = _supplier_id(project_root)
    since_ms = int(since_dt.timestamp() * 1000)
    end_ms = int(datetime.now().timestamp() * 1000)
    try:
        qs = urllib.parse.urlencode({
            "page": 0, "size": QUESTION_PAGE_SIZE,
            "startDate": since_ms, "endDate": end_ms,
            "orderByField": "LastModifiedDate", "orderByDirection": "DESC",
        })
        data = _fetch_json_with_retry(
            project_root, f"/qna/sellers/{supplier}/questions/filter?{qs}",
            v2=False, timeout=QUESTION_REQUEST_TIMEOUT_SECONDS,
        )
        new_rows = [r for r in (data.get("content") or []) if isinstance(r, dict)]
    except Exception:  # noqa: BLE001
        return []
    if not new_rows:
        return []
    product_index = _cached_product_reference_index(project_root)
    normalized = [_normalize_question_context(project_root, q, product_index=product_index) for q in new_rows]
    merged = _dedupe_questions(normalized + list_questions(project_root))
    _save_questions(project_root, merged)
    _save_question_sync_status(project_root, "OK", f"{len(new_rows)} yeni soru/mesaj delta çekildi.")
    return new_rows


def _save_question_sync_status(project_root: Path, status: str, message: str) -> None:
    settings = get_settings(project_root, masked=False)
    settings["last_questions_sync_at"] = _now()
    settings["last_questions_sync_status"] = status
    settings["last_questions_sync_message"] = message[:500]
    settings_path(project_root).write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_existing_customer_order(project_root: Path, suggestion: dict[str, Any]) -> dict[str, Any] | None:
    order_no = str(suggestion.get("order_number") or "")
    line_id = str(suggestion.get("line_id") or "")
    for row in customer_order_api.list_customer_orders(project_root):
        if order_no and str(row.get("trendyol_order_number") or "") == order_no and str(row.get("trendyol_line_id") or "") == line_id:
            return row
    return None


def _supplier_id(project_root: Path) -> str:
    return str(get_settings(project_root, masked=False).get("supplier_id") or "")


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"


def _is_masked_secret(value: str) -> bool:
    text = str(value or "").strip()
    return bool(text) and ("*" in text or "•" in text or "●" in text)


def _relative(project_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _safe_int(value: Any, default: int) -> int:
    try:
        return max(1, int(float(str(value).replace(",", "."))))
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "evet", "e", "stage"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

