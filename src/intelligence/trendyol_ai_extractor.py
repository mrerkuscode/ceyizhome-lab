from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

from intelligence.text_cleanup import clean_spaces, repair_text, title_turkish_name


DEFAULT_MODEL = "gpt-5-nano"
DEFAULT_CONFIDENCE_THRESHOLD = 0.85
DEFAULT_TIMEOUT_SECONDS = 20
AI_CACHE_SCHEMA_VERSION = 3
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
SAFE_MESSAGE_SOURCES = {"customerMessage", "question_text", "answer_text", "sellerAnswer", "empty", "order_line"}
TR_NAME_CHARS = "A-Za-zÇĞİÖŞÜçğıiöşü"
INSTRUCTION_NAME_WORDS = {
    "kurdele", "ustune", "üstüne", "ustunde", "üstünde", "gold", "yazi", "yazı",
    "cikolata", "çikolata", "cicek", "çiçek", "tasarim", "tasarım", "olsun",
    "yazilsin", "yazılsın", "tepsi", "sunumluk", "katli", "katlı", "hatirasi", "hatırası",
}

# --- Faz A: genişletilmiş bloklama sabitleri ---
# Selamlama yazım varyantları (typo dahil)
_GREETING_KEYS: frozenset[str] = frozenset({
    "merhaba", "meraba", "merhba", "mrhb", "mrhba", "mrb", "slm", "sln",
    "selam", "iyi", "gunaydin", "günaydın", "selamlar", "kolay", "hayirli",
    "hayırlı", "iyi gunler", "iyi günler",
})
# Tek başına isim olamayacak token'lar (normalize edilmiş, diacritic'siz)
_BLOCKED_NAME_KEYS: frozenset[str] = frozenset({
    # Renkler
    "gold", "gumus", "silver", "beyaz", "siyah", "kirmizi",
    "pembe", "mavi", "mor", "yesil", "sari", "bronz", "bakir", "altin",
    # Teslimat/sipariş
    "teslimat", "teslimatim", "teslimatimiz",
    "kargo", "kargom", "kargonuz",
    "siparis", "siparisim", "siparisimiz",
    "numara", "numarasi", "numarayi",
    "verdigim", "olusturdum",
    # Sıfat/zarf/hal eki — asla isim değil
    "seklinde", "gibi", "boyle", "aynisi", "ayni",
    "sadece", "hepsi", "butun", "tum",
    # Fiil gövdeleri
    "olsun", "olacak", "olucak", "yazsin", "yazilsin", "yazilacak",
    "yazacak", "yazabilir", "misiniz", "rica", "ediyorum",
    # Bağlaçlar ve genel kelimeler
    "ve", "ile", "bu", "bir", "de", "da", "this",
    "ozel", "kisiye", "kisisellestirme",
})
# Niyet anahtarı regex (Faz A: bu varsa LLM'e güven artıyor)
_INTENT_KEY_RE = re.compile(
    r"(?:isim(?:ler)?\s*(?:yazılacak|yazilacak|yazılsın|yazilsin|:)|"
    r"(?:yazılacak|yazilacak|yazılsın|yazilsin)\s+isim|"
    r"üzerine|uzerine|üstüne|ustune|etikete|etiketine|"
    r"isim\s*:\s*|isimleri\s+|yazılmasını|yazilmasini)",
    re.IGNORECASE,
)


def ai_cache_path(project_root: Path) -> Path:
    path = project_root / "data" / "trendyol_ai_extraction_cache.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def learning_examples_path(project_root: Path) -> Path:
    path = project_root / "data" / "trendyol_extraction_learning_examples.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def is_ai_configured(settings: dict[str, Any] | None) -> bool:
    settings = settings or {}
    return _safe_bool(settings.get("ai_enabled"), False) and bool(str(settings.get("ai_api_key") or "").strip())


def extract_with_ai_or_fallback(
    project_root: Path,
    source: dict[str, Any],
    mapping: dict[str, Any] | None,
    deterministic: dict[str, Any],
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = {**(source or {}), "_project_root": str(project_root)}
    settings = settings or _load_settings(project_root)
    if not is_ai_configured(settings):
        return _fallback_result({**(deterministic or {}), "_source": source}, mapping, "rule_fallback_ai_disabled")
    last_exc: Exception | None = None
    for _attempt in range(2):
        try:
            return extract_with_cloud_ai(project_root, source, mapping, deterministic, settings)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    if last_exc is not None:
        fallback = _fallback_result({**(deterministic or {}), "_source": source}, mapping, "rule_fallback_ai_error")
        fallback["warnings"] = list(dict.fromkeys([*fallback.get("warnings", []), f"Bulut AI alan ayıklama kullanılamadı; net isim kalıbı ve güvenli alanlar kullanıldı ({_safe_error(last_exc)})."]))
        _write_debug_log(project_root, source, "", "", {}, fallback, deterministic, error=_safe_error(last_exc))
        return fallback
    return _fallback_result({**(deterministic or {}), "_source": source}, mapping, "rule_fallback_ai_error")


def extract_with_cloud_ai(
    project_root: Path,
    source: dict[str, Any],
    mapping: dict[str, Any] | None,
    deterministic: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    if not repair_text(source.get("question_text") or ""):
        empty = _empty_extraction(source, mapping)
        empty["warnings"].append("Müşteri mesajı yok; AI ürün adından isim uydurmadı.")
        return empty

    model = str(settings.get("ai_model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    cache_enabled = _safe_bool(settings.get("ai_cache_enabled"), True)
    cache_key = _cache_key(model, source)
    if cache_enabled:
        cached = _read_cache(project_root).get(cache_key)
        if cached:
            cached_row = _sanitize_ai_result(cached, source, mapping)
            cached_row["source_evidence"] = list(dict.fromkeys([*cached_row.get("source_evidence", []), "cloud_ai_cache"]))
            return cached_row

    prompt = _build_prompt(source)
    raw = _call_openai_compatible(settings, model, prompt)
    parsed = parse_ai_response(raw)
    sanitized = _sanitize_ai_result(parsed, source, mapping)
    sanitized["source_evidence"] = list(dict.fromkeys([*sanitized.get("source_evidence", []), "cloud_ai_extract"]))
    _write_debug_log(project_root, source, prompt, raw, parsed, sanitized, deterministic)
    if cache_enabled:
        cache = _read_cache(project_root)
        cache[cache_key] = {**sanitized, "cached_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        _write_cache(project_root, cache)
    return sanitized


def parse_ai_response(payload_text: str) -> dict[str, Any]:
    try:
        data = json.loads(repair_text(payload_text).strip())
    except json.JSONDecodeError as exc:
        raise ValueError("AI yanıtı strict JSON değil.") from exc
    if not isinstance(data, dict):
        raise ValueError("AI JSON yanıtı obje değil.")
    return data


def _call_openai_compatible(settings: dict[str, Any], model: str, prompt: str) -> str:
    api_key = str(settings.get("ai_api_key") or "").strip()
    timeout = _safe_float(settings.get("ai_timeout_seconds"), DEFAULT_TIMEOUT_SECONDS)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    responses_payload = {"model": model, "instructions": _system_prompt(), "input": prompt}
    if model.lower().startswith("gpt-5"):
        chat_first_payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            response = _post_json(OPENAI_CHAT_URL, headers, chat_first_payload, timeout)
            output = _extract_response_text(response)
            if output:
                return output
        except Exception:
            pass
    try:
        response = _post_json(OPENAI_RESPONSES_URL, headers, responses_payload, timeout)
        output = _extract_response_text(response)
        if output:
            return output
    except Exception:
        pass

    chat_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    if model.lower().startswith("gpt-5"):
        try:
            response = _post_json(OPENAI_CHAT_URL, headers, chat_payload, timeout)
            output = _extract_response_text(response)
            if output:
                return output
        except Exception:
            pass

    response = _post_json(OPENAI_CHAT_URL, headers, chat_payload, timeout)
    output = _extract_response_text(response)
    if not output:
        raise ValueError("AI yanıtında metin yok.")
    return output


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _extract_response_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return str(response.get("output_text") or "")
    for item in response.get("output") or []:
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("text"):
                return str(content.get("text") or "")
    choices = response.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        return str(message.get("content") or "")
    return ""


def _system_prompt() -> str:
    # Faz A: niyet-anahtari odakli, anti-halusinasyon, evidence_span zorunlu
    return (
        "Sen Türkçe müşteri mesajlarından, müşterinin ürüne YAZILMASINI istediği "
        "isim(ler)i, tarihi ve talimatları çıkaran uzmansın. "
        "temperature=0 seviyesinde çalış; kesinlikle emin olmadığın hiçbir değeri üretme.\n\n"

        "== YENİ ALANLAR (Faz A) ==\n"
        "- name_found: true yalnızca müşteri ürüne yazılacak ismi AÇIKÇA belirttiyse.\n"
        "- names: [string] — çıkarılan isimler dizisi; yoksa [].\n"
        "- evidence_span: müşterin mesajında HARFİ HARFİNE geçen, ismi gerekçelendiren parça. "
        "  Kanıt parçası mesajda birebir yoksa o ismi VERME.\n\n"

        "== NİYET ANAHTARLARI (bunlar varsa isim al) ==\n"
        "  'X isim yazılacak', 'isim: X', 'isimleri X ve Y', 'X yazılsın', "
        "'üzerine X', 'X ismi yazılacak', 'X~Y yazarmısınız', 'yazılacak isim X'\n\n"

        "== KESİNLİKLE İSİM OLMAYANLAR ==\n"
        "1. Selamlamalar (tüm yazım varyantları): merhaba, meraba, merhba, mrhb, mrb, slm, "
        "   selam, iyi günler, günaydın\n"
        "2. Sipariş/teslimat numaraları ve '#{rakam}' kalıpları\n"
        "3. Renkler: gold, gümüş, silver, beyaz, siyah, kırmızı, mavi, mor, yeşil, sarı, bronz, altın\n"
        "4. Ölçü ve adet kalıpları: '4/4', 'x adet', '6 tane'\n"
        "5. Satıcı cevabından gelen metinler ('Satıcı cevabı: ...')\n"
        "6. Ürün başlığından gelen metinler\n"
        "7. Fiiller: yazılacak, yazılsın, olacak, olsun, istemek, gelmek\n"
        "8. İyelik ekleri: siparişin, numarası, ürününüz\n"
        "9. Kalıp cümleler: 'nişan hatırası', 'hatırası', 'kızımızı istemeye'\n\n"

        "== ÇOKLU İSİM AYRAÇLARI ==\n"
        "  'X ve Y', 'X / Y', 'X,Y', 'X~Y', 'X & Y', 'X + Y' → her biri ayrı names[]\n\n"

        "== DİĞER KURALLAR ==\n"
        "- containsPersonName false ise personNames, names, labelName, laserName null/[].\n"
        "- Tarih yoksa uydurma. İsim yoksa uydurma.\n"
        "- Product title veya seller answer'dan isim ÇIKARMA.\n"
        "- eventDate'i DD.MM.YYYY veya 'D Ay YYYY' formatında normalize et.\n"
        "- evidence_span her zaman müşteri mesajındaki orijinal metinden al.\n"
        "- Sadece JSON döndür, başka metin yok.\n"
    )


def _build_prompt(source: dict[str, Any]) -> str:
    customer_messages = _customer_messages(source)
    learning_examples = _similar_learning_examples(_project_root_from_source(source), source, limit=5)
    context = {
        "customerMessages": customer_messages,
        "selectedCustomerMessage": customer_messages[0] if customer_messages else repair_text(source.get("question_text") or ""),
        "customerMessage": repair_text(source.get("question_text") or ""),
        "sellerAnswer": repair_text(source.get("answer_text") or "") or None,
        "productTitle": repair_text(source.get("product_name") or "") or None,
        "productSku": str(source.get("merchant_sku") or source.get("stock_code") or "") or None,
        "productBarcode": str(source.get("barcode") or "") or None,
        "orderQuantity": _safe_int(source.get("quantity"), 1),
        "existingMatchedProduct": None,
        "similarApprovedExamples": learning_examples,
    }
    return (
        "Aşağıdaki müşteri mesajından kişiselleştirme alanlarını çıkar.\n\n"
        "Aynı siparişe ait tüm müşteri mesajları:\n"
        + json.dumps(context["customerMessages"], ensure_ascii=False, indent=2)
        + "\n\n"
        f"Seçili müşteri mesajı:\n“““\n{context['selectedCustomerMessage']}\n“““\n\n"
        f"Satıcı cevabı:\n“““\n{context['sellerAnswer'] or ''}\n“““\n\n"
        f"Ürün başlığı:\n“““\n{context['productTitle'] or ''}\n“““\n\n"
        f"Sipariş adedi:\n{context['orderQuantity']}\n\n"
        "Benzer kullanıcı onaylı doğru örnekler:\n"
        + json.dumps(context["similarApprovedExamples"], ensure_ascii=False, indent=2)
        + "\n\n"
        "Lütfen sadece JSON döndür.\n\n"
        "Örnek:\n"
        + json.dumps(
            {
                "customerMessage": "#11242760731 nolu sipariş çikolataların üzerine yazılacak tarih 30.05.2026 nişan hatırası yazılacak isimler Derya ve M.Şerif lütfen ürünü doğru eksiksiz bir şekilde teslimatını yapın teslim etmeden önce ürünün fotoğrafını mesaj yoluyla bana atar mısınız",
                "result": {
                    "personNames": ["Derya", "M. Şerif"],
                    "labelName": "Derya & M. Şerif",
                    "laserName": "Derya & M. Şerif",
                    "eventDate": "30.05.2026",
                    "customText": "Nişan hatırası",
                    "productionNote": "Cikolatalarin uzerine tarih ve Nisan hatirasi yazilacak. Teslim etmeden once urun fotografı mesaj yoluyla gonderilmeli.",
                    "quantity": 1,
                    "confidence": 93,
                    "fieldConfidence": {"personNames": 96, "labelName": 95, "laserName": 95, "eventDate": 94, "customText": 90, "productionNote": 90, "quantity": 90},
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
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n\n"
        "İsim olmayan talimat örneği:\n"
        + json.dumps(
            {
                "customerMessage": "Merhaba, 6 tane sipariş verdim. Sipariş numarası 11242658230. Hepsi BEYAZ olsun istiyorum. Teşekkür ederim.",
                "result": {
                    "containsPersonName": False,
                    "containsDate": False,
                    "containsCustomText": False,
                    "containsProductionInstruction": True,
                    "personNames": None,
                    "labelName": None,
                    "laserName": None,
                    "eventDate": None,
                    "customText": None,
                    "productionNote": "Hepsi beyaz olacak.",
                    "quantity": None,
                    "confidence": 70,
                    "fieldConfidence": {"personNames": 0, "labelName": 0, "laserName": 0, "eventDate": 0, "customText": 0, "productionNote": 90, "quantity": 50},
                    "sources": {"productionNote": "Hepsi BEYAZ olsun istiyorum."},
                    "warnings": [
                        "Müşteri mesajında kişi ismi bulunamadı.",
                        "Mesaj renk/tasarım talimatı içeriyor; isim alanına aktarılmamalı.",
                    ],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n\n"
        "Beklenen JSON şeması:\n"
        + json.dumps(
            {
                "name_found": "boolean — müşteri ürüne yazılacak ismi açıkça belirtti mi?",
                "names": ["string — çıkarılan isimler; yoksa []"],
                "evidence_span": "string — ismi destekleyen, mesajda HARFİ HARFİNE geçen parça; yoksa ''",
                "containsPersonName": "boolean",
                "containsDate": "boolean",
                "containsCustomText": "boolean",
                "containsProductionInstruction": "boolean",
                "messageUnderstanding": {
                    "containsPersonNames": "boolean",
                    "containsDate": "boolean",
                    "containsCustomText": "boolean",
                    "containsProductionInstruction": "boolean",
                    "detectedSurfaces": [
                        {"surface": "çiçek|çikolata|tepsi|kurdele|etiket|lazer|unknown", "textToWrite": "string|null", "colorOrStyle": "string|null", "note": "string|null"}
                    ],
                },
                "personNames": ["string"],
                "labelName": "string|null",
                "laserName": "string|null",
                "eventDate": "string|null — DD.MM.YYYY veya D Ay YYYY",
                "customText": "string|null",
                "productionNote": "string|null",
                "quantity": "number|null",
                "confidence": "0..100",
                "reasoning": "string — kısa gerekçe (audit/debug için)",
                "fieldConfidence": {"personNames": 0, "labelName": 0, "laserName": 0, "eventDate": 0, "customText": 0, "productionNote": 0, "quantity": 0},
                "sources": {
                    "personNames": "string|null",
                    "labelName": "string|null",
                    "laserName": "string|null",
                    "eventDate": "string|null",
                    "customText": "string|null",
                    "productionNote": "string|null",
                    "quantity": "string|null",
                },
                "warnings": ["string"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n\n"
        "Faz A örnekleri (§4c):\n"
        + json.dumps([
            {
                "msg": "Merhba #11276359839 sipariş numaralı ya Yakup Burcu isim yazılacak 10.06.2026 yazılacak lütfen",
                "out": {"name_found": True, "names": ["Yakup Burcu"], "evidence_span": "Yakup Burcu isim yazılacak",
                        "labelName": "Yakup Burcu", "eventDate": "10.06.2026", "confidence": 95},
            },
            {
                "msg": "...yazılacak isim Gizem / Emirhan boyut =4/4",
                "out": {"name_found": True, "names": ["Gizem", "Emirhan"], "evidence_span": "yazılacak isim Gizem / Emirhan",
                        "labelName": "Gizem & Emirhan", "confidence": 93},
            },
            {
                "msg": "Sipariş no:11273868045 / Teslimat no:10539753922. HASAN~BÜŞRA 07.06.2026 yazarmısınız",
                "out": {"name_found": True, "names": ["HASAN", "BÜŞRA"], "evidence_span": "HASAN~BÜŞRA",
                        "labelName": "Hasan & Büşra", "eventDate": "07.06.2026", "confidence": 90},
            },
            {
                "msg": "...nişan için isimleri Melda ve Tarık gümüş rengi, tarih 13 Haziran 2026",
                "out": {"name_found": True, "names": ["Melda", "Tarık"], "evidence_span": "isimleri Melda ve Tarık",
                        "labelName": "Melda & Tarık", "eventDate": "13 Haziran 2026", "productionNote": "gümüş rengi", "confidence": 92},
            },
            {
                "msg": "...isimleri Gülnur,Mehmet tarihte 06.06.2026 olcak",
                "out": {"name_found": True, "names": ["Gülnur", "Mehmet"], "evidence_span": "isimleri Gülnur,Mehmet",
                        "labelName": "Gülnur & Mehmet", "eventDate": "06.06.2026", "confidence": 92},
            },
            {
                "msg": "Merhaba sipariş numaram bu, ne zaman kargolanır?",
                "out": {"name_found": False, "names": [], "evidence_span": "", "confidence": 97},
            },
            {
                "msg": "...gold renk olsun",
                "out": {"name_found": False, "names": [], "evidence_span": "", "confidence": 90},
            },
        ], ensure_ascii=False, indent=2)
    )


def _project_root_from_source(source: dict[str, Any]) -> Path | None:
    value = source.get("_project_root")
    if not value:
        return None
    try:
        return Path(str(value))
    except (TypeError, ValueError):
        return None


def load_learning_examples(project_root: Path | None) -> list[dict[str, Any]]:
    if not project_root:
        return []
    path = learning_examples_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        examples = data.get("examples")
    else:
        examples = data
    return [item for item in examples if isinstance(item, dict)] if isinstance(examples, list) else []


def _write_learning_examples(project_root: Path, examples: list[dict[str, Any]]) -> None:
    path = learning_examples_path(project_root)
    payload = {
        "schema_version": 1,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "examples": examples[-500:],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def record_learning_example(
    project_root: Path,
    source: dict[str, Any],
    result: dict[str, Any],
    reason: str = "user_verified",
) -> dict[str, Any]:
    message = _full_customer_message(source)
    if not message:
        return {"saved": False, "reason": "empty_message"}
    names = _learning_person_names(result)
    label = _normalize_ai_text(
        result.get("label_text")
        or result.get("labelName")
        or (_join_person_names(names, source, result) if names else "")
    )
    laser = _normalize_ai_text(result.get("name_cut_text") or result.get("laserName") or label)
    date = _normalize_date(result.get("date_text") or result.get("eventDate") or result.get("date"))
    custom_text = _normalize_note(result.get("custom_text") or result.get("customText"))
    production_note = _normalize_note(result.get("production_note") or result.get("productionNote") or result.get("note_text") or result.get("note"))
    if not names and not label and not date and not custom_text and not production_note:
        return {"saved": False, "reason": "no_verified_fields"}
    example_id = hashlib.sha256(
        json.dumps(
            {
                "message_key": _compact_text(message)[:240],
                "names": names,
                "label": label,
                "date": date,
                "custom_text": custom_text,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    example = {
        "id": example_id,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reason": reason,
        "customerMessage": message,
        "productTitle": repair_text(source.get("product_name") or ""),
        "result": {
            "personNames": names or None,
            "labelName": label or None,
            "laserName": laser or None,
            "eventDate": date or None,
            "customText": custom_text or None,
            "productionNote": production_note or None,
        },
        "negativeLabels": _learning_negative_labels(source, result),
    }
    examples = load_learning_examples(project_root)
    examples = [item for item in examples if item.get("id") != example_id]
    examples.append(example)
    _write_learning_examples(project_root, examples)
    return {"saved": True, "example": example}


def _learning_person_names(result: dict[str, Any]) -> list[str]:
    names = result.get("person_names") or result.get("personNames")
    normalized = _normalize_person_names(names) if isinstance(names, list) else []
    if normalized:
        return normalized
    label = _normalize_ai_text(result.get("label_text") or result.get("labelName"))
    if label and not _name_has_instruction_noise(label):
        if "\u267e" in label:
            parts = [part.strip() for part in label.split("\u267e") if part.strip()]
        elif "&" in label:
            parts = [part.strip() for part in label.split("&") if part.strip()]
        else:
            parts = []
        normalized = [_normalize_single_person_name(part) for part in parts if _valid_person_phrase(part)]
    return normalized[:4]


def _learning_negative_labels(source: dict[str, Any], result: dict[str, Any]) -> list[str]:
    names = set(_learning_person_names(result))
    negatives: set[str] = set()
    for candidate in [
        source.get("label_text"),
        source.get("name_cut_text"),
        result.get("label_text"),
        result.get("name_cut_text"),
    ]:
        text = _normalize_ai_text(candidate)
        if text and text not in names and _name_has_instruction_noise(text):
            negatives.add(text)
    return sorted(negatives)


def _similar_learning_examples(project_root: Path | None, source: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    message = _full_customer_message(source)
    if not message:
        return []
    scored: list[tuple[float, dict[str, Any]]] = []
    for item in load_learning_examples(project_root):
        other = repair_text(item.get("customerMessage") or "")
        score = _text_similarity(message, other)
        if score >= 0.16:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    result: list[dict[str, Any]] = []
    for score, item in scored[:limit]:
        result.append(
            {
                "similarity": round(score, 3),
                "customerMessage": item.get("customerMessage") or "",
                "result": item.get("result") or {},
                "negativeLabels": item.get("negativeLabels") or [],
            }
        )
    return result


def _infer_person_names_from_learning(source: dict[str, Any]) -> list[str]:
    examples = _similar_learning_examples(_project_root_from_source(source), source, limit=3)
    if not examples:
        return []
    message_tokens = _learning_tokens(_full_customer_message(source))
    for item in examples:
        if float(item.get("similarity") or 0) < 0.34:
            continue
        names = _normalize_person_names((item.get("result") or {}).get("personNames"))
        if not names:
            continue
        name_tokens = {_person_key(name) for name in names if _person_key(name)}
        if name_tokens and name_tokens.issubset(message_tokens):
            return names
    return []


def _learning_signature_from_source(source: dict[str, Any]) -> str:
    examples = _similar_learning_examples(_project_root_from_source(source), source, limit=5)
    raw = json.dumps(
        [
            {
                "message": item.get("customerMessage") or "",
                "result": item.get("result") or {},
                "negativeLabels": item.get("negativeLabels") or [],
            }
            for item in examples
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _text_similarity(first: str, second: str) -> float:
    left = _learning_tokens(first)
    right = _learning_tokens(second)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _learning_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for token in re.findall(rf"[{TR_NAME_CHARS}0-9]{{2,}}", repair_text(value), flags=re.IGNORECASE):
        key = _person_key(token)
        if key:
            tokens.add(key)
    return tokens


def _sanitize_ai_result(raw: dict[str, Any], source: dict[str, Any], mapping: dict[str, Any] | None) -> dict[str, Any]:
    # --- Faz A: yeni alanlar ---
    name_found_flag = _optional_bool(raw.get("name_found"))   # LLM'in niyet tespiti
    raw_names       = raw.get("names") or []                  # yeni names[] dizisi
    evidence_span   = str(raw.get("evidence_span") or "").strip()
    raw_reasoning   = str(raw.get("reasoning") or "").strip()

    # Faz A: name_found=False ise LLM'in personNames/labelName'ini de temizle
    if name_found_flag is False:
        raw = {**raw, "personNames": None, "labelName": None, "laserName": None}

    # Faz A: names[] dizisi varsa personNames'i güncelle (yeni şema öncelikli)
    if raw_names and isinstance(raw_names, list):
        cleaned_names = [_normalize_ai_text(n) for n in raw_names if _normalize_ai_text(n)]
        if cleaned_names and not any(_is_blocked_name(n) for n in cleaned_names):
            raw = {**raw, "personNames": cleaned_names}

    contains_person_name = _optional_bool(raw.get("containsPersonName"))
    contains_production_instruction = _optional_bool(raw.get("containsProductionInstruction"))
    person_names = _normalize_person_names(raw.get("personNames"))
    label = _normalize_ai_text(_first(raw, "labelName", "label_text"))
    if person_names:
        label = " & ".join(person_names)
    laser = _normalize_ai_text(_first(raw, "laserName", "name_cut_text")) or label
    if person_names and (not laser or laser == label):
        laser = label
    date = _normalize_date(_first(raw, "eventDate", "date", "date_text"))
    custom_text = _normalize_note(_first(raw, "customText", "custom_text"))
    production_note = _normalize_production_instruction_note(_normalize_note(_first(raw, "productionNote", "production_note", "note", "note_text")))
    production_note = _remove_duplicate_name_note(production_note, person_names)
    note = _compose_note(custom_text, production_note)
    source_quantity = _safe_int(source.get("quantity"), 0)
    quantity = source_quantity or _safe_int(_first(raw, "quantity"), 0) or 1
    confidence = _confidence_fraction(_first(raw, "confidence"), default=0.0)
    field_confidence = _field_confidence(raw.get("fieldConfidence") if isinstance(raw.get("fieldConfidence"), dict) else raw.get("field_confidence"))
    if source_quantity:
        field_confidence["quantity"] = max(field_confidence.get("quantity", 0), 90)
    sources = raw.get("sources") if isinstance(raw.get("sources"), dict) else raw.get("field_sources") if isinstance(raw.get("field_sources"), dict) else {}
    evidence_spans = _evidence_spans(sources, raw.get("evidence_spans"))
    warnings = [repair_text(item) for item in raw.get("warnings", []) if repair_text(item)]

    if contains_person_name is False:
        person_names = []
        label = ""
        laser = ""
        field_confidence["personNames"] = 0
        field_confidence["labelName"] = 0
        field_confidence["laserName"] = 0
        if not any("kişi ismi bulunamadı" in warning.lower() or "isim bulunamadı" in warning.lower() for warning in warnings):
            warnings.append("Müşteri mesajında kişi ismi bulunamadı.")
        if contains_production_instruction is True and (note or production_note or custom_text):
            if not any("isim alanına aktarılmamalı" in warning.lower() for warning in warnings):
                warnings.append("Mesaj renk/tasarım talimatı içeriyor; isim alanına aktarılmamalı.")
        confidence = min(confidence or 0.7, 0.78)

    # --- Faz A: evidence_span anti-halüsinasyon doğrulaması ---
    customer_msg = _full_customer_message(source)
    span_valid = _validate_evidence_span(evidence_span, customer_msg) if evidence_span and label else True
    if label and evidence_span and not span_valid:
        label = ""
        laser = ""
        person_names = []
        confidence = min(confidence or 0.5, 0.60)
        warnings.append(
            "Faz-A anti-halüsinasyon: evidence_span müşteri mesajında bulunamadı; "
            "isim alanı güvenlik nedeniyle boşaltıldı."
        )

    # --- Faz A: tek token blocklist doğrulaması ---
    if label and _is_blocked_name(label):
        label = ""
        laser = ""
        person_names = []
        confidence = min(confidence or 0.5, 0.60)
        warnings.append("Faz-A blocklist: çıkarılan isim token'ı reddedildi (renk/selamlama/genel kelime).")

    unsafe_name_source = False
    if _unsafe_source(sources.get("labelName") or sources.get("label_text")):
        label = ""
        unsafe_name_source = True
    if _unsafe_source(sources.get("laserName") or sources.get("name_cut_text")):
        laser = ""
        unsafe_name_source = True
    if unsafe_name_source:
        warnings.append("AI ürün/müşteri bağlamından isim önermeye çalıştı; üretim alanı boş bırakıldı.")
    if label and _looks_like_product_context(label, source):
        label = ""
        laser = ""
        warnings.append("AI ürün başlığından isim çıkarmaya çalıştı; isim alanı boş bırakıldı.")
    final_before_validation = {
        "label_text": label,
        "name_cut_text": laser,
        "date_text": date,
        "person_names": person_names,
        "custom_text": custom_text,
        "production_note": production_note,
        "quantity": quantity,
        "confidence": round(confidence, 2),
    }
    guard = _semantic_final_guard(
        source=source,
        raw=raw,
        person_names=person_names,
        label=label,
        laser=laser,
        date=date,
        custom_text=custom_text,
        production_note=production_note,
        confidence=confidence,
    )
    person_names = guard["person_names"]
    label = guard["label"]
    laser = guard["laser"]
    custom_text = guard["custom_text"]
    production_note = guard["production_note"]
    note = _compose_note(custom_text, production_note)
    confidence = guard["confidence"]
    validation_warnings = guard["warnings"]
    warnings.extend(validation_warnings)
    if validation_warnings:
        field_confidence["labelName"] = 0 if not label else max(field_confidence.get("labelName", 0), 90)
        field_confidence["laserName"] = 0 if not laser else max(field_confidence.get("laserName", 0), 90)
        field_confidence["personNames"] = 0 if not person_names else max(field_confidence.get("personNames", 0), 90)

    # --- Faz A: post-guard blocklist (guard mesajdan yeniden çıkarmış olabilir) ---
    if person_names:
        valid_names = [n for n in person_names if n and not _is_blocked_name(n)]
        if len(valid_names) != len(person_names):
            person_names = valid_names
            label = " & ".join(person_names) if person_names else ""
            laser = label
            if not label:
                confidence = min(confidence or 0.5, 0.60)
                if not any("blocklist" in w.lower() for w in warnings):
                    warnings.append("Faz-A post-guard blocklist: geçersiz isim token temizlendi.")
    if label and _is_blocked_name(label):
        label = ""
        laser = ""
        person_names = []
        confidence = min(confidence or 0.5, 0.60)
        if not any("blocklist" in w.lower() for w in warnings):
            warnings.append("Faz-A post-guard blocklist: birleşik isim token reddedildi.")

    if not label:
        laser = ""
        person_names = []
        field_confidence["personNames"] = 0
        field_confidence["labelName"] = 0
        field_confidence["laserName"] = 0
    if not date and not any("Tarih müşteri mesajında bulunamadı." == item for item in warnings):
        warnings.append("Tarih müşteri mesajında bulunamadı.")
    if not label and not any("isim" in warning.lower() for warning in warnings):
        warnings.append("Müşteri mesajında isim bulunamadı.")
    if not confidence:
        confidence = _derive_confidence(label, date, note, field_confidence)

    return {
        "label_text": label,
        "date_text": date,
        "note_text": note,
        "person_names": person_names,
        "custom_text": custom_text,
        "production_note": production_note,
        "quantity": quantity,
        "name_cut_text": laser,
        "name_cut_width_mm": (mapping or {}).get("name_cut_width_mm") or 300,
        "name_cut_style": (mapping or {}).get("name_cut_style") or "Mochary Personal Use Only",
        "confidence": round(confidence, 2),
        "field_confidence": field_confidence,
        "classification": {
            "containsPersonName": contains_person_name,
            "containsDate": _optional_bool(raw.get("containsDate")),
            "containsCustomText": _optional_bool(raw.get("containsCustomText")),
            "containsProductionInstruction": contains_production_instruction,
        },
        "message_understanding": _message_understanding(raw),
        "_debug_final_before_validation": final_before_validation,
        "_debug_validation_warnings": validation_warnings,
        "warnings": list(dict.fromkeys(warnings)),
        "source_evidence": ["cloud_ai_extract"],
        "field_sources": {
            "label_text": _source_label(sources.get("labelName") or sources.get("personNames") or sources.get("label_text"), bool(label)),
            "date_text": _source_label(sources.get("eventDate") or sources.get("date") or sources.get("date_text"), bool(date)),
            "note_text": _source_label(sources.get("productionNote") or sources.get("customText") or sources.get("note") or sources.get("note_text"), bool(note)),
            "name_cut_text": _source_label(sources.get("laserName") or sources.get("name_cut_text"), bool(laser)),
            "quantity": "order_line" if source_quantity else _source_label(sources.get("quantity"), True),
        },
        "evidence_spans": evidence_spans,
        "needs_user_review": not bool(label) or confidence < DEFAULT_CONFIDENCE_THRESHOLD or bool(validation_warnings),
        "_diag_reasoning": raw_reasoning,
        "_diag_evidence_span": evidence_span,
    }


def _fallback_result(deterministic: dict[str, Any], mapping: dict[str, Any] | None, evidence: str) -> dict[str, Any]:
    result = dict(deterministic or {})
    result.setdefault("label_text", "")
    result.setdefault("name_cut_text", "")
    result.setdefault("date_text", "")
    result.setdefault("note_text", "")
    result.setdefault("person_names", [])
    result.setdefault("custom_text", "")
    result.setdefault("production_note", "")
    result.setdefault("quantity", 1)
    result.setdefault("name_cut_width_mm", (mapping or {}).get("name_cut_width_mm") or 300)
    result.setdefault("name_cut_style", (mapping or {}).get("name_cut_style") or "Mochary Personal Use Only")
    result.setdefault("confidence", 0.0)
    result.setdefault("warnings", [])
    result.setdefault("field_sources", {})
    result.setdefault("evidence_spans", {})
    result["source_evidence"] = [
        item for item in (result.get("source_evidence") or [])
        if item not in {"ai_text_extract", "rule_parser_extract"}
    ]
    result["person_names"] = []
    result["label_text"] = ""
    result["name_cut_text"] = ""
    result["field_sources"] = {**result.get("field_sources", {}), "label_text": "empty", "name_cut_text": "empty"}
    result["evidence_spans"] = {
        key: value
        for key, value in (result.get("evidence_spans") or {}).items()
        if key not in {"label_text", "name_cut_text", "person_names"}
    }
    if evidence == "rule_fallback_ai_error":
        result["source_evidence"] = [
            item for item in (result.get("source_evidence") or [])
            if item not in {"ai_text_extract", "rule_parser_extract"}
        ]
        result["warnings"] = list(dict.fromkeys([
            *result.get("warnings", []),
            "Bulut AI yanıt vermediği için isim/lazer alanı otomatik doldurulmadı; müşteri mesajından manuel doğrulayın.",
        ]))
        result["person_names"] = []
        result["label_text"] = ""
        result["name_cut_text"] = ""
        result["field_sources"] = {**result.get("field_sources", {}), "label_text": "empty", "name_cut_text": "empty"}
        result["evidence_spans"] = {key: value for key, value in (result.get("evidence_spans") or {}).items() if key not in {"label_text", "name_cut_text"}}
        result["confidence"] = min(_confidence_fraction(result.get("confidence"), default=0.0), 0.62)
    guard = _semantic_final_guard(
        source=deterministic.get("_source", {}) if isinstance(deterministic.get("_source"), dict) else {},
        raw={},
        person_names=result.get("person_names") if isinstance(result.get("person_names"), list) else [],
        label=repair_text(result.get("label_text") or ""),
        laser=repair_text(result.get("name_cut_text") or ""),
        date=repair_text(result.get("date_text") or ""),
        custom_text=repair_text(result.get("custom_text") or ""),
        production_note=repair_text(result.get("production_note") or result.get("note_text") or ""),
        confidence=_confidence_fraction(result.get("confidence"), default=0.0),
    )
    if guard["warnings"] or guard["person_names"] or guard["custom_text"] or guard["production_note"]:
        result["_debug_final_before_validation"] = {
            "label_text": result.get("label_text") or "",
            "name_cut_text": result.get("name_cut_text") or "",
            "date_text": result.get("date_text") or "",
            "note_text": result.get("note_text") or "",
            "confidence": result.get("confidence") or 0,
        }
        result["_debug_validation_warnings"] = guard["warnings"]
        result["person_names"] = guard["person_names"]
        result["label_text"] = guard["label"]
        result["name_cut_text"] = guard["laser"]
        result["custom_text"] = guard["custom_text"]
        result["production_note"] = guard["production_note"]
        result["note_text"] = _compose_note(guard["custom_text"], guard["production_note"]) or result.get("note_text") or ""
        result["confidence"] = round(guard["confidence"], 2)
        result["warnings"] = list(dict.fromkeys([*result.get("warnings", []), *guard["warnings"]]))
    if result.get("person_names"):
        result["source_evidence"] = list(dict.fromkeys([*result.get("source_evidence", []), "explicit_name_pattern"]))
        result["field_sources"] = {**result.get("field_sources", {}), "label_text": "question_text", "name_cut_text": "question_text"}
        result["evidence_spans"] = {
            **(result.get("evidence_spans") or {}),
            "person_names": result.get("label_text") or "",
            "label_text": result.get("label_text") or "",
            "name_cut_text": result.get("name_cut_text") or "",
        }
    result["field_confidence"] = _fallback_field_confidence(result)
    result["source_evidence"] = list(dict.fromkeys([*result.get("source_evidence", []), evidence]))
    if not result.get("person_names"):
        result["confidence"] = min(_confidence_fraction(result.get("confidence"), default=0.0), 0.62)
    result["needs_user_review"] = True if evidence.startswith("rule_fallback") else (not bool(result.get("label_text")) or float(result.get("confidence") or 0) < DEFAULT_CONFIDENCE_THRESHOLD or bool(result.get("_debug_validation_warnings")))
    if result.get("person_names"):
        clean_evidence = [
            item for item in (result.get("source_evidence") or [])
            if item not in {"ai_text_extract", "rule_parser_extract"}
        ]
        result["source_evidence"] = list(dict.fromkeys([*clean_evidence, "explicit_name_pattern"]))
    return result


def _empty_extraction(source: dict[str, Any], mapping: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "label_text": "",
        "date_text": "",
        "note_text": "",
        "person_names": [],
        "custom_text": "",
        "production_note": "",
        "quantity": _safe_int(source.get("quantity"), 1),
        "name_cut_text": "",
        "name_cut_width_mm": (mapping or {}).get("name_cut_width_mm") or 300,
        "name_cut_style": (mapping or {}).get("name_cut_style") or "Mochary Personal Use Only",
        "confidence": 0.0,
        "field_confidence": {"labelName": 0, "laserName": 0, "date": 0, "note": 0, "quantity": 90},
        "warnings": [],
        "source_evidence": [],
        "field_sources": {"label_text": "empty", "date_text": "empty", "note_text": "empty", "name_cut_text": "empty", "quantity": "order_line"},
        "evidence_spans": {},
        "needs_user_review": True,
    }


def _first(raw: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw:
            return raw.get(key)
    return None


def _customer_messages(source: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    contexts = source.get("question_contexts") if isinstance(source.get("question_contexts"), list) else []
    for item in contexts:
        if isinstance(item, dict):
            text = repair_text(item.get("question_text") or "")
            if text:
                messages.append(text)
    direct = repair_text(source.get("question_text") or "")
    if direct:
        messages.insert(0, direct)
    return list(dict.fromkeys(messages))


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = repair_text(value).strip().lower()
    if text in {"true", "1", "yes", "evet"}:
        return True
    if text in {"false", "0", "no", "hayır", "hayir"}:
        return False
    return None


def _normalize_ai_text(value: Any) -> str:
    if value is None:
        return ""
    text = repair_text(value).replace("\ufe0f", "")
    text = text.replace("\u2661", "&").replace("\u2665", "&").replace("\u221e", "\u267e")
    text = re.sub(r"\b(?:sonsuzluk\s+i\u015fareti|sonsuzluk\s+isareti|sonsuzluk|infinity)\b", "\u267e", text, flags=re.IGNORECASE)
    return clean_spaces(text)


def _normalize_person_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        text = _normalize_ai_text(item)
        if text:
            text = _normalize_initial_spacing(text)
            names.append(text)
    return names[:4]


def _semantic_final_guard(
    *,
    source: dict[str, Any],
    raw: dict[str, Any],
    person_names: list[str],
    label: str,
    laser: str,
    date: str,
    custom_text: str,
    production_note: str,
    confidence: float,
) -> dict[str, Any]:
    warnings: list[str] = []
    message = _full_customer_message(source)
    learned_names = _infer_person_names_from_learning(source)
    inferred_names = learned_names or _infer_person_names_from_message(message)
    if not person_names and inferred_names:
        reconstructed = _join_person_names(inferred_names, source, raw)
        person_names = inferred_names
        if learned_names:
            warnings.append("Yerel ogrenme hafizasindaki benzer dogrulanmis ornekten kisi isimleri uygulandi.")
        if _name_has_instruction_noise(label) or not label or label != reconstructed:
            warnings.append("Final validator kişi isimlerini müşteri mesajındaki açık isimlerden yeniden kurdu.")
    if person_names:
        joined = _join_person_names(person_names, source, raw)
        if label != joined or laser != joined:
            warnings.append("Final validator label/lazer alanını sadece kişi isimlerinden yeniden kurdu.")
        label = joined
        laser = joined
        confidence = max(confidence, 0.9 if len(person_names) >= 2 else 0.84)
    elif label and _name_has_instruction_noise(label):
        warnings.append("Final validator isim alanında üretim talimatı gördü; isim alanı boş bırakıldı.")
        label = ""
        laser = ""
        confidence = min(confidence or 0.68, 0.68)

    if not custom_text:
        custom_text = _infer_custom_text_from_message(message)
    raw_has_production_note = bool(_normalize_ai_text(_first(raw, "productionNote", "production_note", "note", "note_text")))
    if not production_note:
        production_note = _infer_production_note_from_message(message, person_names, date, custom_text)
    else:
        inferred_note = "" if raw_has_production_note else _infer_production_note_from_message(message, person_names, date, custom_text)
        if inferred_note:
            existing_key = _compact_text(production_note)
            additions = [
                part.strip()
                for part in re.split(r"(?<=[.!?])\s+", inferred_note)
                if part.strip() and _compact_text(part.strip()) not in existing_key
            ]
            if additions:
                production_note = clean_spaces(f"{production_note} {' '.join(additions)}")
        if custom_text:
            production_note = _normalize_custom_phrase_in_text(production_note)
    return {
        "person_names": person_names,
        "label": label,
        "laser": laser,
        "custom_text": custom_text,
        "production_note": production_note,
        "confidence": confidence,
        "warnings": warnings,
    }


def _full_customer_message(source: dict[str, Any]) -> str:
    return clean_spaces(" | ".join(_customer_messages(source) or [repair_text(source.get("question_text") or "")]))


# --- Faz A: yardımcı doğrulama fonksiyonları ---

def _normalize_for_span_check(text: str) -> str:
    """Büyük/küçük harf, Türkçe karakter normalize + fazla boşluk sil."""
    tr_table = str.maketrans("ğĞıİöÖüÜşŞçÇ", "ggiioouusscc")
    return re.sub(r"\s+", " ", repair_text(text).lower().translate(tr_table)).strip()


def _validate_evidence_span(evidence_span: str, customer_message: str) -> bool:
    """evidence_span müşteri mesajında birebir (normalize edilmiş) geçiyor mu?"""
    if not evidence_span or not customer_message:
        return False
    norm_span = _normalize_for_span_check(evidence_span)
    norm_msg  = _normalize_for_span_check(customer_message)
    return bool(norm_span) and norm_span in norm_msg


def _is_blocked_name(label: str) -> bool:
    """Tek token renk/selamlama/genel kelime mi? (blocklist kontrolü)"""
    if not label:
        return False
    tr_table = str.maketrans("ğĞıİöÖüÜşŞçÇ", "ggiioouusscc")
    tokens = re.split(r"[\s&]+", label.strip())
    if len(tokens) == 1:
        key = re.sub(r"[^a-z0-9]", "", tokens[0].lower().translate(tr_table))
        return key in _BLOCKED_NAME_KEYS or key in _GREETING_KEYS
    # Tüm token'lar blocklist'te ise reddet
    if all(
        re.sub(r"[^a-z0-9]", "", t.lower().translate(tr_table)) in _BLOCKED_NAME_KEYS | _GREETING_KEYS
        for t in tokens if t.strip()
    ):
        return True
    return False


def _message_understanding(raw: dict[str, Any]) -> dict[str, Any]:
    value = raw.get("messageUnderstanding") or raw.get("message_understanding") or {}
    if not isinstance(value, dict):
        value = {}
    return {
        "containsPersonNames": _optional_bool(value.get("containsPersonNames")) if "containsPersonNames" in value else _optional_bool(raw.get("containsPersonName")),
        "containsDate": _optional_bool(value.get("containsDate")) if "containsDate" in value else _optional_bool(raw.get("containsDate")),
        "containsCustomText": _optional_bool(value.get("containsCustomText")) if "containsCustomText" in value else _optional_bool(raw.get("containsCustomText")),
        "containsProductionInstruction": _optional_bool(value.get("containsProductionInstruction")) if "containsProductionInstruction" in value else _optional_bool(raw.get("containsProductionInstruction")),
        "detectedSurfaces": value.get("detectedSurfaces") if isinstance(value.get("detectedSurfaces"), list) else [],
    }


def _join_person_names(person_names: list[str], source: dict[str, Any], raw: dict[str, Any]) -> str:
    names = [_normalize_single_person_name(name) for name in person_names if _normalize_single_person_name(name)]
    if len(names) == 2 and _has_infinity_intent(source, raw):
        return f"{names[0]} ♾ {names[1]}"
    return " & ".join(names)


def _normalize_single_person_name(value: str) -> str:
    text = _normalize_initial_spacing(title_turkish_name(clean_spaces(value)))
    text = re.sub(
        rf"\b([A-Za-zÇĞİÖŞÜ])\.\s*([{TR_NAME_CHARS}]+)",
        lambda match: f"{match.group(1).upper()}. {title_turkish_name(match.group(2))}",
        text,
    )
    return text


def _has_infinity_intent(source: dict[str, Any], raw: dict[str, Any]) -> bool:
    haystack = " ".join(
        [
            _full_customer_message(source),
            repair_text(raw.get("labelName") or ""),
            repair_text(raw.get("laserName") or ""),
        ]
    ).lower()
    return bool(re.search(r"(♾|∞|sonsuzluk|infinity)", haystack, flags=re.IGNORECASE))


def _name_has_instruction_noise(value: str) -> bool:
    if not value:
        return False
    key = repair_text(value).lower()
    compact = _compact_text(key)
    return any(_compact_text(word) in compact for word in INSTRUCTION_NAME_WORDS)


def _infer_person_names_from_message(message: str) -> list[str]:
    text = _normalize_ai_text(message)
    sep = r"(?:\s*(?:&|\+)\s*|\s+\bve\b\s+)"
    patterns = [
        rf"\b(?P<a>[{TR_NAME_CHARS}]{{2,}}){sep}(?P<b>(?:[A-Za-zÇĞİÖŞÜ]\.\s*)?[{TR_NAME_CHARS}]{{2,}})\b",
        rf"\bisimler?\s+(?P<a>[{TR_NAME_CHARS}]{{2,}})(?:{sep}|\s+)(?P<b>(?:[A-Za-zÇĞİÖŞÜ]\.\s*)?[{TR_NAME_CHARS}]{{2,}})\b",
        rf"\b(?P<a>[{TR_NAME_CHARS}]{{2,}})\s+(?:♾|sonsuzluk\s+i(?:ş|s)areti|sonsuzluk|infinity)\s+(?P<b>[{TR_NAME_CHARS}]{{2,}})\b",
        rf"\b(?P<a>[{TR_NAME_CHARS}]{{2,}})\s+(?P<b>[{TR_NAME_CHARS}]{{2,}})\s+(?:olacak|olsun)\s+isimler?\b",
        rf"\b(?P<a>[{TR_NAME_CHARS}]{{2,}})\s+(?P<b>[{TR_NAME_CHARS}]{{2,}})\s+\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}\s+yaz",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            first = _normalize_single_person_name(match.group("a"))
            second = _normalize_single_person_name(match.group("b"))
            if first and second and not _name_has_instruction_noise(first) and not _name_has_instruction_noise(second):
                return [first, second]
    single = re.search(rf"\b(?:üzerine|ustune|üstüne)\s+(?P<a>[{TR_NAME_CHARS}]{{2,}})\s+(?:yazılsın|yazilsin|yazsın|yazsin|olsun)\b", text, flags=re.IGNORECASE)
    if single:
        name = _normalize_single_person_name(single.group("a"))
        if name and not _name_has_instruction_noise(name):
            return [name]
    return []


def _valid_person_name_token(value: str) -> bool:
    if not value or _name_has_instruction_noise(value):
        return False
    compact = _compact_text(value)
    if compact in {"hepsi", "beyaz", "siyah", "kirmizi", "lacivert", "gold", "istemeye", "geldik", "emri", "allah", "kizimizi", "ile", "de", "ve", "tarih", "tarihte", "fotograftaki", "resimdeki", "gibi", "iade", "altina", "afiyet", "uzerine", "cicegin", "siparisimiz", "siparisim", "biz", "kolay", "gelsin", "cuma", "gunune", "yetisir", "pazartesi", "gunu"}:
        return False
    blocked = {
        "gumus", "gümüş", "renk", "ince", "cerceve", "çerçeve",
        "siparis", "sipariş", "numara", "numaram", "numarasi", "numarası",
        "nolu", "icin", "için", "cift", "çift", "isimleri", "isimler",
        "kisisellestirme", "kişiselleştirme", "sekilde", "şeklinde", "yaziyor", "yazıyor",
        "kalp", "orta", "kisma", "kısma",
    }
    return compact not in {_compact_text(item) for item in blocked}


def _infer_person_names_from_message(message: str) -> list[str]:
    text = _normalize_ai_text(message)
    name_word = r"[A-Za-zÇĞİÖŞÜçğıiöşü]{2,}"
    initial_name = rf"(?:[A-Za-zÇĞİÖŞÜ]\.\s*)?{name_word}"
    sep = r"(?:\s*(?:&|\+|/)\s*|\s+\bve\b\s+)"
    patterns = [
        rf"\b(?P<a>{name_word})\s+(?:♾|∞|sonsuzluk\s+i(?:ş|s)areti|sonsuzluk|infinity)\s+(?P<b>{name_word})\b",
        rf"\b(?P<a>{name_word}){sep}(?P<b>{initial_name})\b",
        rf"\b(?:isimler?|isimleri|kişiselleştirme|kisisellestirme|çift\s+isimleri|cift\s+isimleri)\s+(?P<a>{name_word})(?:{sep}|\s+)(?P<b>{initial_name})\b",
        rf"\b(?P<a>{name_word})\s+(?P<b>{initial_name})\s+\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}\b",
        rf"\b(?P<a>{name_word})\s+(?P<b>{initial_name})\s+(?:yazılacak|yazilacak|yazılsın|yazilsin|olacak|olsun)\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            first = _normalize_single_person_name(match.group("a"))
            second = _normalize_single_person_name(match.group("b"))
            if _valid_person_name_token(first) and _valid_person_name_token(second):
                return [first, second]
    contextual = [
        rf"(?:üstünde|ustunde|üzerinde|uzerinde|üzerine|uzerine|orta\s+kısma|orta\s+kisma)\s+(?P<a>{name_word})\s+(?P<b>{initial_name})(?=\s+(?:yaz|ol|tarih|\d{{1,2}}[./-]|\b))",
        rf"(?:isim\s+olarak|isimleri|çift\s+isimleri|cift\s+isimleri|kişiselleştirme|kisisellestirme)\s+(?P<a>{name_word})\s+(?P<b>{initial_name})(?=\s*(?:$|[.,;]|\d{{1,2}}[./-]|\s+yaz|\s+ol|\s+tarih))",
    ]
    for pattern in contextual:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            first = _normalize_single_person_name(match.group("a"))
            second = _normalize_single_person_name(match.group("b"))
            if _valid_person_name_token(first) and _valid_person_name_token(second):
                return [first, second]
    single = re.search(rf"\b(?:üzerine|ustune|üstüne)\s+(?P<a>{name_word})\s+(?:yazılsın|yazilsin|yazsın|yazsin|olsun)\b", text, flags=re.IGNORECASE)
    if single:
        name = _normalize_single_person_name(single.group("a"))
        if _valid_person_name_token(name):
            return [name]
    return []


def _valid_person_phrase(value: str) -> bool:
    text = clean_spaces(value)
    if not text or _name_has_instruction_noise(text):
        return False
    tokens = [token for token in re.split(r"\s+", text) if token]
    if not tokens or len(tokens) > 3:
        return False
    return all(_valid_person_name_token(token.replace(".", "")) for token in tokens if token != ".")


def _infer_person_names_from_message(message: str) -> list[str]:
    text = _normalize_ai_text(message)
    name_word = rf"[{TR_NAME_CHARS}]{{2,}}"
    initial_name = rf"(?:[A-Za-zÃ‡ÄÄ°Ã–ÅÃœ]\.\s*)?{name_word}"
    person = rf"{initial_name}(?:\s+{name_word})?"
    stop = r"(?=\s*(?:$|[.,;:!?)]|\d|tarih|yaz|ol|olsun|olacak|ÅŸeklinde|sekilde|Ã§ikolata|cikolata|Ã§iÃ§ek|cicek|kutusuna|Ã¼zer|uzer|Ã¼st|ust|gÃ¶rsel|gorsel|tasarÄ±m|tasarim))"
    patterns = [
        rf"\b(?P<a>{name_word})\s+(?:â™¾|âˆ|sonsuzluk\s+i(?:ÅŸ|s)areti|sonsuzluk|infinity)\s+(?P<b>{name_word})\b",
        rf"\b(?P<a>{person})\s*(?:&|\+|/|-|_|\.)\s*(?P<b>{person}){stop}",
        rf"\b(?P<a>{person})\s+\bve\b\s+(?P<b>{person}){stop}",
        rf"\b(?:yazÄ±lan\s+isim|yazilan\s+isim|isimler?|isimleri|kiÅŸiselleÅŸtirme|kisisellestirme|Ã§ift\s+isimleri|cift\s+isimleri)\s+(?P<a>{person})\s*(?:&|\+|/|-|_|\.)\s*(?P<b>{person}){stop}",
        rf"\b(?:yazÄ±lan\s+isim|yazilan\s+isim|isimler?|isimleri|kiÅŸiselleÅŸtirme|kisisellestirme|Ã§ift\s+isimleri|cift\s+isimleri)\s+(?P<a>{name_word})\s+(?P<b>{initial_name}){stop}",
        rf"\b(?P<a>{name_word})\s+(?P<b>{initial_name})\s+\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}\b",
        rf"\b(?P<a>{name_word})\s+(?P<b>{initial_name})\s+(?:yazÄ±lacak|yazilacak|yazÄ±lsÄ±n|yazilsin|yazacak|olacak|olsun)\b",
        rf"(?:Ã¼stÃ¼nde|ustunde|Ã¼zerinde|uzerinde|Ã¼zerine|uzerine|orta\s+kÄ±sma|orta\s+kisma)\s+(?P<a>{name_word})\s+(?P<b>{initial_name}){stop}",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            first = _normalize_single_person_name(match.group("a"))
            second = _normalize_single_person_name(match.group("b"))
            if _valid_person_phrase(first) and _valid_person_phrase(second):
                return [first, second]
    single = re.search(rf"\b(?:Ã¼zerine|ustune|Ã¼stÃ¼ne)\s+(?P<a>{name_word})\s+(?:yazÄ±lsÄ±n|yazilsin|yazsÄ±n|yazsin|olsun)\b", text, flags=re.IGNORECASE)
    if single:
        name = _normalize_single_person_name(single.group("a"))
        if _valid_person_phrase(name):
            return [name]
    return []


def _person_key(value: str) -> str:
    import unicodedata

    text = repair_text(value).casefold().replace("ı", "i").replace("İ", "i")
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if ch.isalnum() and not unicodedata.combining(ch))


def _valid_person_name_token(value: str) -> bool:
    text = clean_spaces(repair_text(value)).strip(" .,:;!?()[]{}“'""''")
    if not text or _name_has_instruction_noise(text):
        return False
    if re.search(r"\d", text):
        return False
    if re.fullmatch(r"[A-Za-zÇĞİÖŞÜ]\.?", text):
        return True
    if not re.fullmatch(rf"[{TR_NAME_CHARS}][{TR_NAME_CHARS}'.-]*", text):
        return False
    key = _person_key(text)
    blocked = {
        "allah", "altina", "anne", "aynisi", "basagi", "beyaz", "bide", "biz", "bugday",
        "cicek", "cicegin", "cikolata", "cikolatanin", "cift", "cerceve", "de", "emri", "extra", "fotograftaki",
        "geldik", "gibi", "gorsel", "gorseldeki", "gorseldekinin", "gold", "gumus",
        "hatirasi", "hepsi", "iade", "icin", "ince", "isim", "ismi", "isimleri", "isimler",
        "isteme", "istemeye", "istiyorum", "kalp", "katli", "kisisellestirme", "kisma", "kolay",
        "kutu", "kutuda", "kutusuna", "lazer", "model", "nolu", "numara", "numaram",
        "numarasi", "olsun", "olacak", "orta", "renk", "resimdeki", "sekilde",
        "sekli", "siyah", "siparis", "siparisim", "siparisimiz", "sunumluk", "tarih", "tarihte",
        "tasarim", "tepsi", "urun", "ust", "ustune", "ustunde", "uzerine", "ve",
        "yazi", "yazilacak", "yazilsin", "yaziyor",
    }
    return key not in blocked and len(key) >= 2


def _valid_person_phrase(value: str) -> bool:
    text = clean_spaces(repair_text(value)).strip(" .,:;!?()[]{}“'""''")
    if not text or _name_has_instruction_noise(text):
        return False
    tokens = [token for token in re.split(r"\s+", text) if token]
    if not tokens or len(tokens) > 3:
        return False
    return all(_valid_person_name_token(token) for token in tokens)


def _person_match_pair(match: re.Match[str]) -> list[str]:
    first = _normalize_single_person_name(match.group("a"))
    second = _normalize_single_person_name(match.group("b"))
    if _valid_person_phrase(first) and _valid_person_phrase(second):
        return [first, second]
    return []


def _infer_person_names_from_message(message: str) -> list[str]:
    text = _normalize_ai_text(message)
    name_word = rf"[{TR_NAME_CHARS}]{{2,}}"
    initial_name = rf"(?:[A-Za-zÇĞİÖŞÜ]\.\s*)?{name_word}"
    stop = (
        r"(?=\s*(?:$|[.,;:!?)]|\d|tarih|yaz|ol|olsun|olacak|şeklinde|sekilde|"
        r"çikolata|cikolata|çikolataya|cikolataya|çiçek|cicek|kutusuna|kutu|ürün|urun|"
        r"üzer|uzer|üst|ust|orta|kısma|kisma|kalp|görsel|gorsel|"
        r"tasarım|tasarim|gold|renk|rengi|isim|ismi|isteme|nisan|nişan|"
        r"tül|tul|seçim|secim|seçimi|secimi|yazı|yazi|not|model))"
    )
    trigger = (
        r"(?:yazılan\s+isim|yazilan\s+isim|yazılacak\s+isim|yazilacak\s+isim|"
        r"isimler?|isimleri|kişiselleştirme|kisisellestirme|çift\s+isimleri|"
        r"cift\s+isimleri)"
    )
    separator = r"(?:&|\+|/|-|_|\.)"
    quote = r"[“'""'']"
    patterns = [
        rf"\b(?P<a>{name_word})\s*(?:♾|∞|sonsuzluk(?:\s+i(?:ş|s)areti)?|infinity)\s*(?P<b>{name_word})\b",
        rf"\b{trigger}\s*:?\s+(?:tarih\s+)?{quote}\s*(?P<a>{initial_name})\s*{quote}\s+{quote}\s*(?P<b>{initial_name})\s*{quote}{stop}",
        rf"\b(?P<a>{initial_name})\s*{separator}\s*(?P<b>{initial_name}){stop}",
        rf"\b(?P<a>{initial_name})\s+ve\s+(?P<b>{initial_name}){stop}",
        rf"\b{trigger}\s*:?\s+(?:tarih\s+)?(?P<a>{initial_name})\s*{separator}\s*(?P<b>{initial_name}){stop}",
        rf"\b{trigger}\s*:?\s+(?P<a>{name_word})\s+ve\s+(?P<b>{initial_name}){stop}",
        rf"\b{trigger}\s*:?\s+(?P<a>{name_word})\s+(?P<b>{initial_name}){stop}",
        rf"\b(?P<a>{name_word})\s+(?P<b>{initial_name})\s+(?:tarih\s*:?\s*)?\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}\b",
        rf"\b(?P<a>{name_word})\s+(?P<b>{initial_name})\s+(?:yazılacak|yazilacak|yazılsın|yazilsin|yazacak|olacak|olsun)\b",
        rf"(?:üstünde|ustunde|üzerinde|uzerinde|üzerine|uzerine|orta\s+kısma|orta\s+kisma)\s+(?P<a>{name_word})\s+(?P<b>{initial_name}){stop}",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            pair = _person_match_pair(match)
            if pair:
                return pair
    single = re.search(
        rf"\b(?:üzerine|uzerine|üstüne|ustune)\s+(?P<a>{name_word})\s+(?:yazılsın|yazilsin|yazsın|yazsin)\b",
        text,
        flags=re.IGNORECASE,
    )
    if single:
        name = _normalize_single_person_name(single.group("a"))
        if _valid_person_phrase(name):
            return [name]
    return []


def _infer_custom_text_from_message(message: str) -> str:
    key = repair_text(message).lower()
    if "allah" in key and "emri" in key and "istemeye geldik" in key:
        if "kızınızı" in key or "kizinizi" in key:
            return "Allah'ın emri ile kızınızı istemeye geldik"
        return "Allah'ın emri ile kızımızı istemeye geldik"
    if re.search(r"\bnişan\s+hatırası\b|\bnisan\s+hatirasi\b", key, flags=re.IGNORECASE):
        return "Nişan hatırası"
    return ""


def _normalize_custom_phrase_in_text(value: str) -> str:
    text = repair_text(value)
    text = re.sub(r"Allah[ıi]n emri ile kızınızı istemeye geldik", "Allah'ın emri ile kızınızı istemeye geldik", text, flags=re.IGNORECASE)
    text = re.sub(r"Allah[ıi]n emri ile kızımızı istemeye geldik", "Allah'ın emri ile kızımızı istemeye geldik", text, flags=re.IGNORECASE)
    return clean_spaces(text)


def _infer_production_note_from_message(message: str, person_names: list[str], date: str, custom_text: str) -> str:
    key = repair_text(message).lower()
    parts: list[str] = []
    joined = " & ".join(person_names) if person_names else ""
    if "gümüş renk" in key or "gumus renk" in key:
        parts.append("Gümüş renk kullanılacak.")
    if "ince çerçeve" in key or "ince cerceve" in key:
        parts.append("İnce çerçeve kullanılacak.")
    if "kalp" in key:
        parts.append("Orta kısma kalp konulacak.")
    if "görseldekinin aynısı" in key or "gorseldekinin aynisi" in key:
        parts.append("Görseldekinin aynısı isteniyor.")
    color_match = re.search(r"\bhepsi\s+(beyaz|siyah)\s+olsun\b", key, flags=re.IGNORECASE)
    if color_match:
        parts.append(f"Hepsi {color_match.group(1).lower()} olacak.")
    if "tülü siyah" in key or "tulu siyah" in key:
        parts.append("Tülü siyah olacak.")
    tulle_selection = re.search(
        r"\bt[üu]l\s+seçim(?:i|imiz)?\s*:?\s*(?P<color>beyaz|siyah|gold|gümüş|gumus|kırmızı|kirmizi|lacivert|pembe)\b",
        key,
        flags=re.IGNORECASE,
    )
    if tulle_selection:
        parts.append(f"Tül seçimi {repair_text(tulle_selection.group('color')).lower()} olacak.")
    if "siyah kurdele" in key:
        parts.append("Çiçek üzerinde siyah kurdele kullanılacak ve yazı gold olacak." if "gold" in key else "Çiçek üzerinde siyah kurdele kullanılacak.")
    if "çikolata" in key or "cikolata" in key:
        if joined and date:
            parts.append(f"Çikolatanın üstüne {joined} ve {date} gold yazı ile yazılacak." if "gold" in key else f"Çikolatanın üstüne {joined} ve {date} yazılacak.")
        elif "çikolatalı tepsi" in key or "cikolatali tepsi" in key:
            parts.append("Çikolatalı tepsi için uygulanacak.")
    if "çiçekli tasarım" in key or "cicekli tasarim" in key:
        parts.append("Çiçekli tasarım isteniyor.")
    if ("tepsi" in key or "çikolatalarda" in key or "cikolatalarda" in key) and custom_text:
        style = " gold yazı ile" if "gold" in key else ""
        parts.append(f"Tepsi içindeki çikolatalarda {custom_text}{style} yazılacak.")
    if "gold olsun" in key or "gold yaz" in key:
        if not parts:
            parts.append("Gold yazı kullanılacak.")
    return clean_spaces(" ".join(parts))


def _normalize_note(value: Any) -> str:
    text = _normalize_ai_text(value)
    if not text:
        return ""
    return text[:1].upper() + text[1:]


def _normalize_production_instruction_note(value: str) -> str:
    text = clean_spaces(value)
    if not text:
        return ""
    match = re.search(r"\bhepsi\s+(?P<color>beyaz|siyah)\s+olsun\b", text, flags=re.IGNORECASE)
    if match:
        color = repair_text(match.group("color")).lower()
        return f"Hepsi {color} olacak."
    return text


def _normalize_date(value: Any) -> str:
    text = _normalize_ai_text(value)
    if not text:
        return ""
    match = re.search(r"(?P<day>\d{1,2})[./-](?P<month>\d{1,2})[./-](?P<year>\d{2,4})", text)
    if not match:
        return text
    year = int(match.group("year"))
    if year < 100:
        year += 2000
    return f"{int(match.group('day')):02d}.{int(match.group('month')):02d}.{year:04d}"


def _compose_note(custom_text: str, production_note: str) -> str:
    if not custom_text:
        return production_note
    custom = custom_text[:1].upper() + custom_text[1:]
    if production_note and custom.lower() not in production_note.lower():
        if "yaz" in production_note.lower():
            return production_note
        return f"Çikolataların üzerine {custom} yazılacak. {production_note}"
    if production_note:
        return production_note
    return f"{custom} yazılacak."


def _remove_duplicate_name_note(value: str, person_names: list[str]) -> str:
    if not value or not person_names:
        return value
    name_keys = [_compact_text(name) for name in person_names if name]
    sentences = re.split(r"(?<=[.!?])\s+", value)
    kept: list[str] = []
    for sentence in sentences:
        key = _compact_text(sentence)
        if "isim" in key and all(name_key in key for name_key in name_keys):
            continue
        kept.append(sentence)
    return clean_spaces(" ".join(kept))


def _normalize_initial_spacing(value: str) -> str:
    return re.sub(r"\b([A-Za-zÇĞİÖŞÜ])\.\s*([A-Za-zÇĞİÖŞÜçğıöşü])", r"\1. \2", clean_spaces(value))


def _compact_text(value: str) -> str:
    return re.sub(r"[^a-z0-9çğıöşü]+", "", repair_text(value).lower().replace("\u0307", ""))


def _confidence_fraction(value: Any, *, default: float) -> float:
    number = _safe_float(value, default)
    if number > 1:
        number /= 100
    return min(0.99, max(0.0, number))


def _field_confidence(value: Any) -> dict[str, int]:
    raw = value if isinstance(value, dict) else {}
    return {
        "labelName": _confidence_percent(raw.get("labelName") or raw.get("label_text")),
        "laserName": _confidence_percent(raw.get("laserName") or raw.get("name_cut_text")),
        "personNames": _confidence_percent(raw.get("personNames")),
        "date": _confidence_percent(raw.get("eventDate") or raw.get("date") or raw.get("date_text")),
        "eventDate": _confidence_percent(raw.get("eventDate") or raw.get("date") or raw.get("date_text")),
        "customText": _confidence_percent(raw.get("customText")),
        "productionNote": _confidence_percent(raw.get("productionNote") or raw.get("note") or raw.get("note_text")),
        "note": _confidence_percent(raw.get("productionNote") or raw.get("note") or raw.get("note_text")),
        "quantity": _confidence_percent(raw.get("quantity"), default=90),
    }


def _confidence_percent(value: Any, default: int = 0) -> int:
    number = _safe_float(value, default)
    if number <= 1 and number > 0:
        number *= 100
    return max(0, min(100, int(round(number))))


def _fallback_field_confidence(result: dict[str, Any]) -> dict[str, int]:
    return {
        "labelName": 75 if result.get("label_text") else 0,
        "laserName": 75 if result.get("name_cut_text") else 0,
        "personNames": 80 if result.get("person_names") else 0,
        "date": 80 if result.get("date_text") else 0,
        "eventDate": 80 if result.get("date_text") else 0,
        "customText": 75 if result.get("custom_text") else 0,
        "productionNote": 75 if result.get("production_note") else 0,
        "note": 70 if result.get("note_text") else 0,
        "quantity": 90,
    }


def _evidence_spans(sources: dict[str, Any], spans: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(spans, dict):
        out.update({str(key): repair_text(value) for key, value in spans.items() if repair_text(value)})
    mapping = {
        "personNames": "person_names",
        "labelName": "label_text",
        "laserName": "name_cut_text",
        "eventDate": "date_text",
        "date": "date_text",
        "customText": "custom_text",
        "productionNote": "production_note",
        "note": "note_text",
        "quantity": "quantity",
    }
    for source_key, target_key in mapping.items():
        value = repair_text(sources.get(source_key) or "")
        if value and value not in {"sipariş satırından", "order_line", "question_text", "answer_text", "empty"}:
            out[target_key] = value
    return out


def _source_label(value: Any, has_value: bool) -> str:
    if not has_value:
        return "empty"
    text = repair_text(value).lower()
    if "sipariş" in text or "order" in text:
        return "order_line"
    if text in {"question_text", "customerMessage", "customermessage"}:
        return "question_text"
    if text in {"answer_text", "sellerAnswer", "selleranswer"}:
        return "answer_text"
    if text in {"product_name", "producttitle", "product_title", "customer_name"}:
        return text
    return "question_text"


def _unsafe_source(value: Any) -> bool:
    text = repair_text(value).lower()
    return text in {"product_name", "producttitle", "product_title", "customer_name"}


def _looks_like_product_context(label: str, source: dict[str, Any]) -> bool:
    product = repair_text(source.get("product_name") or "").lower()
    if not product or not label:
        return False
    compact_label = re.sub(r"[^a-z0-9çğıöşü]+", "", label.lower())
    compact_product = re.sub(r"[^a-z0-9çğıöşü]+", "", product)
    return bool(compact_label and compact_label in compact_product)


def _derive_confidence(label: str, date: str, note: str, field_confidence: dict[str, int]) -> float:
    score = max(field_confidence.get("labelName", 0), field_confidence.get("laserName", 0))
    if not score and note:
        score = field_confidence.get("note", 70)
    if date:
        score = min(100, score + 3)
    return min(0.99, max(0.0, score / 100))


def _read_cache(project_root: Path) -> dict[str, Any]:
    path = ai_cache_path(project_root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_cache(project_root: Path, data: dict[str, Any]) -> None:
    ai_cache_path(project_root).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _cache_key(model: str, source: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "schema_version": AI_CACHE_SCHEMA_VERSION,
            "model": model,
            "question_text": repair_text(source.get("question_text") or ""),
            "answer_text": repair_text(source.get("answer_text") or ""),
            "product_name": repair_text(source.get("product_name") or ""),
            "barcode": source.get("barcode") or "",
            "merchant_sku": source.get("merchant_sku") or source.get("stock_code") or "",
            "learning_signature": _learning_signature_from_source(source),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _write_debug_log(
    project_root: Path,
    source: dict[str, Any],
    ai_input: str,
    ai_raw_json: str,
    parsed: dict[str, Any],
    final_result: dict[str, Any],
    deterministic: dict[str, Any],
    *,
    error: str = "",
) -> None:
    try:
        path = project_root / "logs" / "trendyol_extraction_debug.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "order_number": source.get("order_number") or source.get("orderNumber") or "",
            "orderId": source.get("order_number") or source.get("orderNumber") or source.get("id") or "",
            "raw_customer_message": repair_text(source.get("question_text") or ""),
            "rawCustomerMessages": _customer_messages(source),
            "messageUsedForAI": repair_text(source.get("question_text") or ""),
            "seller_answer": repair_text(source.get("answer_text") or ""),
            "ai_input": ai_input,
            "aiPrompt": ai_input,
            "ai_raw_json_response": ai_raw_json,
            "aiRawResponse": ai_raw_json,
            "schema_validation_result": parsed,
            "parsedAIResult": parsed,
            "deterministic_parser_result": deterministic,
            "deterministicResult": deterministic,
            "finalResultBeforeValidation": final_result.get("_debug_final_before_validation") or final_result,
            "validationWarnings": final_result.get("_debug_validation_warnings") or [],
            "final_ui_result": final_result,
            "finalResultSentToUI": {key: value for key, value in final_result.items() if not str(key).startswith("_debug_")},
            "error": error,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _load_settings(project_root: Path) -> dict[str, Any]:
    path = project_root / "data" / "trendyol_settings.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _safe_error(exc: Exception) -> str:
    text = repair_text(str(exc))
    text = re.sub(r"(api[_ -]?key|api[_ -]?secret|authorization|bearer)\s*[:=]\s*[^,\s]+", r"\1 gizlendi", text, flags=re.IGNORECASE)
    text = re.sub(r"(authorization|bearer)\s+[A-Za-z0-9._-]+", r"\1 gizlendi", text, flags=re.IGNORECASE)
    text = re.sub(r"should-not-leak|verify-secret-should-not-leak", "gizlendi", text, flags=re.IGNORECASE)
    return text[:120] or "AI servis hatası"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(float(str(value).replace(",", "."))))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "evet", "e", "on"}
