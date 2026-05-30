from __future__ import annotations

import re
from typing import Any

from intelligence.text_cleanup import clean_spaces, repair_text, title_turkish_name


TR_CHARS = "A-Za-z\u00c7\u011e\u0130\u00d6\u015e\u00dc\u00e7\u011f\u0131i\u00f6\u015f\u00fc"
DATE_PATTERN = re.compile(r"(?P<day>\d{1,2})[./-](?P<month>\d{1,2})[./-](?P<year>\d{2,4})")
MONTH_NAME_PATTERN = re.compile(
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>ocak|şubat|subat|mart|nisan|mayıs|mayis|haziran|temmuz|ağustos|agustos|"
    r"eylül|eylul|ekim|kasım|kasim|aralık|aralik)"
    r"(?:\s+(?P<year>\d{4}))?",
    re.IGNORECASE,
)
NOTE_PATTERN = re.compile(r"(?:not|mesaj|a\u00e7\u0131klama|aciklama)\s*[:\uff1a-]\s*(?P<note>[^|;\n]+)", re.IGNORECASE)
NAME_PATTERN = re.compile(r"(?:isim(?:ler)?|ad\s*soyad|etiket\s*yaz\u0131s\u0131|etiket_yazisi)\s*(?:k\u0131sm\u0131na|alan\u0131na|olarak)?\s*[:\uff1a-]?\s*(?P<name>[^|;\n]+)", re.IGNORECASE)
PAIR_PATTERN = re.compile(rf"([{TR_CHARS}]{{2,}})\s*(?:&|\+|\u2661|\u2665|\bve\b)\s*([{TR_CHARS}]{{2,}})", re.IGNORECASE)
PERSONALIZATION_VERBS = (
    r"yaz\u0131lmas\u0131n\u0131\s+rica\s+ediyorum|yazilmasini\s+rica\s+ediyorum|"
    r"yaz\u0131lmas\u0131n\u0131|yazilmasini|yaz\u0131lacak|yazilacak|yaz\u0131l\u0131cak|yazilicak|"
    r"yazacak|yaz\u0131ls\u0131n|yazilsin|yazs\u0131n|yazsin|yaz\u0131n|yazin|yazabilir\s+misiniz|yazar\s+m\u0131s\u0131n\u0131z|"
    r"yazar\s+misiniz|olsun|olacak|olucak|kesilsin|haz\u0131rlans\u0131n|hazirlansin"
)
PERSONALIZATION_TARGETS = (
    r"lazer\s*isim|isim\s*kesim|isimler?|etiket(?:e|te)?|"
    r"\u00fczerine|uzerine|\u00fczerinde|uzerinde|\u00e7i\u00e7e\u011fin\s+\u00fczerinde|"
    r"cicegin\s+uzerinde|\u00fcr\u00fcn\u00fcme|urunume|\u00fcr\u00fcne|urune"
)
PERSONALIZATION_AFTER_TARGET_PATTERN = re.compile(
    rf"(?:{PERSONALIZATION_TARGETS})\s+(?P<name>[^|;\n]{{2,120}}?)\s*(?:{PERSONALIZATION_VERBS})",
    re.IGNORECASE,
)
PERSONALIZATION_BEFORE_VERB_PATTERN = re.compile(
    rf"(?P<name>[^|;\n]{{2,120}}?)\s*(?:{PERSONALIZATION_VERBS})",
    re.IGNORECASE,
)
ORDER_REF_PATTERN = re.compile(
    r"(?:#\d{8,}|\b\d{8,}\b\s*(?:sipari\u015f|siparis)?|sipari[\u015fs]\s*(?:no|numaram?|numaras\u0131|numarasi|numaral\u0131|numarali)?\s*\d{8,})",
    re.IGNORECASE,
)
STOP_WORDS = {
    "sipari\u015f", "siparis", "sipari\u015fe", "siparise", "nolu", "no", "numara", "numarali",
    "\u00fcr\u00fcn", "urun", "\u00fcr\u00fcn\u00fcme", "urunume", "etiket", "lazer", "isim", "isimler",
    "kesim", "yaz\u0131ls\u0131n", "yazilsin", "yaz\u0131lacak", "yazilacak", "yaz\u0131lmas\u0131n\u0131",
    "yazilmasini", "yazacak", "yazabilir", "misiniz", "m\u0131s\u0131n\u0131z", "rica", "ediyorum", "ederim", "l\u00fctfen", "lutfen", "merhaba", "selam",
    "\u00e7ikolata", "cikolata", "\u00e7i\u00e7ek", "cicek", "\u00e7i\u00e7e\u011fin", "cicegin",
    "adet", "kutu", "buketi", "g\u00fcl", "gul", "allah", "emri", "yaz\u0131s\u0131", "yazisi",
    "s\u00f6z", "soz", "ni\u015fan", "nisan", "isteme", "g\u00f6rseldeki", "gorseldeki", "ayn\u0131", "ayni",
    "olsun", "olacak", "\u00fcst\u00fcnde", "ustunde", "tarih", "tarihimiz", "tarihli", "nikah", "d\u00fc\u011f\u00fcn", "dugun", "renk", "renkli", "once", "\u00f6nce", "sonra",
    "tedarik", "de\u011fi\u015fim", "degisim", "iade",
    "g\u00f6rseldekinin", "gorseldekinin", "ayn\u0131s\u0131", "aynisi", "siyah", "beyaz",
    "t\u00fcl", "tulu", "t\u00fcl\u00fc", "tul\u00fc", "sekilde", "\u015fekilde", "model",
    "allah\u0131n", "allah\u2019\u0131n", "k\u0131z\u0131m\u0131z\u0131", "kizimizi", "istemeye", "geldik",
    "cikolatal\u0131", "\u00e7ikolatal\u0131", "tepsi", "gibi", "sadece", "yapal\u0131m", "yapalim", "in", "ile",
    # Faz A: selamlama typo varyantlar\u0131
    "merhba", "mrhb", "mrhba", "mrb", "slm", "sln", "meraba",
    # Faz A: renkler
    "gold", "gumus", "silver", "bronz", "altin",
    # Faz A: teslimat/kargo
    "teslimat", "kargo", "teslimatim", "teslimatim",
}
INFINITY_TOKEN = "\u267e"
# Faz A: niyet anahtar\u0131 tespit \u2014 bu olmadan sipari\u015f-ref yolunda isim alma
_INTENT_KEY_DET_RE = re.compile(
    r"(?:isim(?:ler)?\s*(?:yaz\u0131lacak|yazilacak|yaz\u0131ls\u0131n|yazilsin|:)|"
    r"yaz\u0131lacak\s+isim|yazilacak\s+isim|"
    r"isimleri\s+|\u00fczerine|uzerine|\u00fczerinde|uzerinde|\u00fcst\u00fcne|ustune|\u00fcst\u00fcnde|ustunde|"
    r"isim\s*:\s*|etikete|etiketine|lazer\s*isim|yaz\u0131ls\u0131n|yazilsin|yazacak|yaz\u0131lacak)",
    re.IGNORECASE,
)


def extract_production_fields(source: dict[str, Any], mapping: dict[str, Any] | None = None) -> dict[str, Any]:
    mapping = mapping or {}
    text = _source_text(source)
    customer = title_turkish_name(source.get("customer_name") or source.get("customerName") or "")
    product_name = repair_text(source.get("product_name") or source.get("productName") or source.get("name") or "")
    evidence: list[str] = []
    warnings: list[str] = []

    question_text = repair_text(source.get("question_text") or "")
    answer_text = repair_text(source.get("answer_text") or "")
    question_or_answer = " | ".join(part for part in [question_text, answer_text] if part)
    label_source = ""
    evidence_spans: dict[str, str] = {}

    label_text, label_span = _extract_name_with_span(question_text) if question_text else ("", "")
    if label_text:
        label_source = "question_text"
        evidence_spans["label_text"] = label_span
    if not label_text and answer_text:
        label_text, label_span = _extract_name_with_span(answer_text)
        label_source = "answer_text" if label_text else label_source
        if label_text:
            evidence_spans["label_text"] = label_span
    if label_text:
        evidence.append("rule_parser_extract")
    else:
        warnings.append("\u0130sim/etiket yaz\u0131s\u0131 net bulunamad\u0131.")

    date_text, date_span = _extract_date_with_span(question_or_answer) if question_or_answer else ("", "")
    date_source = "question_text" if date_text and question_text else ("answer_text" if date_text and answer_text else "")
    if not date_text:
        date_text = repair_text(mapping.get("default_date_text") or "")
        date_source = "mapping_default_date" if date_text else date_source
    if date_text:
        evidence.append("date_extract")
        if date_span:
            evidence_spans["date_text"] = date_span
    elif question_or_answer:
        warnings.append("Tarih m\u00fc\u015fteri mesaj\u0131nda bulunamad\u0131.")

    note_text, note_span = _extract_note_with_span(question_or_answer) if question_or_answer else ("", "")
    note_source = "question_text" if note_text and question_text else ("answer_text" if note_text and answer_text else "")
    if not note_text:
        note_text = repair_text(mapping.get("default_note_text") or "")
        note_source = "mapping_default_note" if note_text else note_source
    if note_text:
        evidence.append("note_extract")
        if note_span:
            evidence_spans["note_text"] = note_span

    if question_text:
        evidence.append("question_context")
    if answer_text:
        evidence.append("answer_context")

    quantity_text, quantity_span = _extract_quantity_with_span(question_or_answer) if question_or_answer else (0, "")
    quantity = quantity_text or _safe_int(source.get("quantity"), 1)
    quantity_source = "question_text" if quantity_text and question_text else "order_line"
    if quantity_span:
        evidence_spans["quantity"] = quantity_span
    name_cut_text = _clean_name_for_cut(label_text)
    name_cut_source = label_source if name_cut_text else ""
    if name_cut_text and evidence_spans.get("label_text"):
        evidence_spans["name_cut_text"] = evidence_spans["label_text"]
    confidence = 0.5
    if mapping:
        confidence += 0.02
        evidence.append("barcode_match")
    if label_text:
        confidence += 0.3
    if date_text:
        confidence += 0.03
    if note_text:
        confidence += 0.06
    if question_or_answer:
        confidence += 0.02
    confidence = min(0.98, round(confidence, 2))
    if confidence < 0.7:
        warnings.append("AI alan ay\u0131klama g\u00fcveni d\u00fc\u015f\u00fck; kullan\u0131c\u0131 kontrol\u00fc gerekli.")

    return {
        "label_text": label_text,
        "date_text": date_text,
        "note_text": note_text,
        "quantity": quantity,
        "name_cut_text": name_cut_text,
        "name_cut_width_mm": mapping.get("name_cut_width_mm") or 300,
        "name_cut_style": mapping.get("name_cut_style") or "Mochary Personal Use Only",
        "confidence": confidence,
        "warnings": warnings,
        "source_evidence": list(dict.fromkeys(evidence)),
        "field_sources": {
            "label_text": label_source or "unknown",
            "date_text": date_source or "unknown",
            "note_text": note_source or "unknown",
            "name_cut_text": name_cut_source or "unknown",
            "quantity": quantity_source,
        },
        "evidence_spans": evidence_spans,
    }


def _source_text(source: dict[str, Any]) -> str:
    parts = [
        source.get("question_text"),
        source.get("answer_text"),
        source.get("personalization"),
        source.get("customer_note"),
        source.get("product_name"),
        source.get("productName"),
        source.get("name"),
        source.get("product_color"),
        source.get("productColor"),
        source.get("product_size"),
        source.get("productSize"),
    ]
    return " | ".join(repair_text(part) for part in parts if repair_text(part))


def _extract_name(text: str) -> str:
    value, _span = _extract_name_with_span(text)
    return value


def _extract_name_with_span(text: str) -> tuple[str, str]:
    repaired = _normalize_symbols(repair_text(text))
    ordered_pair = _extract_ordered_pair(repaired)
    if ordered_pair:
        return ordered_pair, ordered_pair
    for extractor in (
        _extract_explicit_name_field,
        _extract_personalization_name,
        _extract_name_after_order_ref,
        _pair_like_text,
    ):
        value = extractor(repaired)
        if value:
            return value, _best_name_span(repaired, value)
    return "", ""


def _extract_ordered_pair(text: str) -> str:
    match = re.search(
        rf"(?:\u00f6nce|once)\s+(?P<first>[{TR_CHARS}]{{2,}}(?:\s+[{TR_CHARS}]{{2,}})?)\s+(?:sonra)\s+(?P<second>[{TR_CHARS}]{{2,}}(?:\s+[{TR_CHARS}]{{2,}})?)",
        repair_text(text),
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    first = _normalize_side(match.group("first"))
    second = _normalize_side(match.group("second"))
    return f"{first} & {second}" if first and second else ""


def _extract_explicit_name_field(text: str) -> str:
    match = NAME_PATTERN.search(text)
    if not match:
        return ""
    candidate = _strip_personalization_noise(match.group("name"))
    return _normalize_label_name(candidate) if _looks_like_name(candidate) else ""


def _extract_personalization_name(text: str) -> str:
    for pattern in (PERSONALIZATION_AFTER_TARGET_PATTERN, PERSONALIZATION_BEFORE_VERB_PATTERN):
        match = pattern.search(text)
        if not match:
            continue
        candidate = _strip_personalization_noise(match.group("name"))
        if _looks_like_name(candidate):
            return _normalize_label_name(candidate, force_pair=_force_pair_from_span(match.group(0)))
    return ""


def _strip_personalization_noise(value: str) -> str:
    text = _normalize_symbols(repair_text(value)).replace("+", "&")
    text = DATE_PATTERN.sub(" ", text)
    text = MONTH_NAME_PATTERN.sub(" ", text)
    text = ORDER_REF_PATTERN.sub(" ", text)
    text = re.sub(rf"\b(?:{PERSONALIZATION_TARGETS})\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{5,}\b", " ", text)
    text = re.sub(rf"[^0-9{TR_CHARS}&{INFINITY_TOKEN}\-\s]", " ", text)
    text = re.sub(r"\s+-\s+", " & ", text)
    text = _drop_stopword_runs(clean_spaces(text))
    return _trim_name_candidate(text)


def _drop_stopword_runs(value: str) -> str:
    tokens = [token for token in re.split(r"(\s+|&)", value) if token and not token.isspace()]
    kept: list[str] = []
    for token in tokens:
        if token == "&":
            kept.append(token)
            continue
        if token == INFINITY_TOKEN:
            kept.append(token)
            continue
        if _word_key(token) in STOP_WORDS:
            if kept:
                break
            continue
        kept.append(token)
    return clean_spaces(" ".join(kept).replace(" & ", "&")).replace("&", " & ")


def _extract_name_after_order_ref(text: str) -> str:
    """Faz A: sipariş no. varsa YONLYintent-key ile birlikte isim al.
    Eski davranış ('ilk token'ı al') kaldırıldı — false-positive üretiyordu."""
    if not ORDER_REF_PATTERN.search(text):
        return ""
    # Niyet anahtarı yoksa bu yolda isim ÇIKARMA
    if not _INTENT_KEY_DET_RE.search(text):
        return ""
    candidate = _strip_personalization_noise(text)
    if not _looks_like_name(candidate):
        return ""
    return _normalize_label_name(candidate)


def _trim_name_candidate(value: str) -> str:
    text = clean_spaces(value)
    if not text:
        return ""
    if "&" in text:
        sides = [_normalize_side(side) for side in text.split("&", maxsplit=1)]
        if all(sides):
            return f"{sides[0]} & {sides[1]}"
    if INFINITY_TOKEN in text:
        sides = [_normalize_side(side) for side in text.split(INFINITY_TOKEN, maxsplit=1)]
        if all(sides):
            return f"{sides[0]} {INFINITY_TOKEN} {sides[1]}"
    pair = PAIR_PATTERN.search(text)
    if pair:
        left = _nearest_name_side(text[:pair.start(1)] + pair.group(1), from_right=True)
        right = _nearest_name_side(pair.group(2) + text[pair.end(2):], from_right=False)
        return f"{left} & {right}" if left and right else f"{pair.group(1)} & {pair.group(2)}"
    words = [part for part in re.split(r"\s+|&", text) if part.strip()]
    if len(words) > 6:
        words = words[:6]
    text = " ".join(words)
    return text


def _normalize_side(value: str) -> str:
    words = [
        word for word in re.split(r"\s+", repair_text(value))
        if word and word != INFINITY_TOKEN and _word_key(word) not in STOP_WORDS and not word.isdigit()
    ]
    return title_turkish_name(" ".join(words[:3]))


def _nearest_name_side(value: str, *, from_right: bool) -> str:
    words = [
        word for word in re.split(r"\s+", repair_text(value))
        if word and word != INFINITY_TOKEN and _word_key(word) not in STOP_WORDS and not word.isdigit()
    ]
    if from_right:
        words = words[-3:]
    else:
        words = words[:3]
    return title_turkish_name(" ".join(words))


def _looks_like_name(value: str) -> bool:
    words = [word for word in re.split(r"\s+|&|\+", repair_text(value)) if word.strip()]
    if not words or len(words) > 6:
        return False
    useful = [word for word in words if word == INFINITY_TOKEN or (len(word) >= 2 and _word_key(word) not in STOP_WORDS and not word.isdigit())]
    return bool([word for word in useful if word != INFINITY_TOKEN]) and len(useful) == len(words)


def _extract_date(text: str) -> str:
    value, _span = _extract_date_with_span(text)
    return value


def _extract_date_with_span(text: str) -> tuple[str, str]:
    repaired = repair_text(text)
    name_match = MONTH_NAME_PATTERN.search(repaired)
    if name_match:
        day = int(name_match.group("day"))
        month = _title_month_name(name_match.group("month"))
        year = name_match.group("year")
        value = f"{day} {month} {year}" if year else f"{day} {month}"
        return value, name_match.group(0)
    match = DATE_PATTERN.search(repair_text(text))
    if not match:
        return "", ""
    day = int(match.group("day"))
    month = int(match.group("month"))
    year = int(match.group("year"))
    if year < 100:
        year += 2000
    return f"{day:02d}.{month:02d}.{year:04d}", match.group(0)


def _extract_note(text: str) -> str:
    value, _span = _extract_note_with_span(text)
    return value


def _extract_note_with_span(text: str) -> tuple[str, str]:
    repaired = repair_text(text)
    match = NOTE_PATTERN.search(repair_text(text))
    if match:
        note = DATE_PATTERN.sub("", match.group("note"))
        note = MONTH_NAME_PATTERN.sub("", note)
        return clean_spaces(note), match.group("note")
    notes: list[str] = []
    spans: list[str] = []
    if re.search(r"g\u00f6rseldeki(?:nin)?\s+(?:gibi|ayn\u0131s\u0131|aynisi|ayn\u0131|ayni)", repaired, re.IGNORECASE):
        notes.append("G\u00f6rseldekinin ayn\u0131s\u0131 isteniyor.")
        spans.append("g\u00f6rseldekinin ayn\u0131s\u0131")
    tulle = re.search(r"t\u00fcl[\u00fcü]?\s+(?P<color>siyah|beyaz|k\u0131rm\u0131z\u0131|kirmizi|pembe|mavi|mor|gold|g\u00fcm\u00fc\u015f|gumus)", repaired, re.IGNORECASE)
    if tulle:
        color = title_turkish_name(tulle.group("color"))
        notes.append(f"T\u00fcl\u00fc {color.lower()} olacak.")
        spans.append(tulle.group(0))
    allah = re.search(
        r"allah[\u2019'\u0301]?\u0131?n?\s+emri\s+ile\s+k\u0131z\u0131m\u0131z\u0131\s+istemeye\s+geldik",
        repaired,
        re.IGNORECASE,
    )
    if allah:
        notes.append("\u201cAllah\u2019\u0131n emri ile k\u0131z\u0131m\u0131z\u0131 istemeye geldik\u201d yaz\u0131s\u0131 kullan\u0131lacak.")
        spans.append(allah.group(0))
    if re.search(r"\u00e7ikolatal\u0131\s+tepsi|cikolatal\u0131\s+tepsi", repaired, re.IGNORECASE):
        notes.append("\u00c7ikolatal\u0131 tepsi i\u00e7in uygulanacak.")
        spans.append("\u00e7ikolatal\u0131 tepsi")
    return " ".join(notes), " / ".join(spans)


def _pair_like_text(text: str) -> str:
    pair = PAIR_PATTERN.search(_normalize_symbols(text).replace(INFINITY_TOKEN, "&"))
    if not pair:
        return ""
    return f"{title_turkish_name(pair.group(1))} & {title_turkish_name(pair.group(2))}"


def _clean_name_for_cut(value: str) -> str:
    text = _normalize_symbols(value).replace("+", "&")
    if "&" in text:
        return " & ".join(title_turkish_name(part) for part in text.split("&") if part.strip())
    return clean_spaces(" ".join(INFINITY_TOKEN if part == INFINITY_TOKEN else title_turkish_name(part) for part in re.split(r"\s+|\+", text) if part.strip()))


def _normalize_label_name(value: str, *, force_pair: bool = False) -> str:
    text = clean_spaces(_normalize_symbols(value)).replace("+", "&")
    if INFINITY_TOKEN in text:
        return clean_spaces(" ".join(INFINITY_TOKEN if part == INFINITY_TOKEN else title_turkish_name(part) for part in text.split() if part.strip()))
    if "&" in text:
        return " & ".join(title_turkish_name(part) for part in text.split("&") if part.strip())
    parts = [part for part in text.split() if part.strip()]
    if force_pair and len(parts) == 2:
        return " & ".join(title_turkish_name(part) for part in parts)
    return title_turkish_name(text)


def _extract_quantity_with_span(text: str) -> tuple[int, str]:
    repaired = repair_text(text)
    match = re.search(r"\b(?P<count>\d{1,4})\s*(?:adet|tane|etiket)\b", repaired, re.IGNORECASE)
    if not match:
        return 0, ""
    after = repaired[match.end(): match.end() + 32]
    if re.search(r"\bsipari[\u015fs]\s+verd", after, re.IGNORECASE):
        return 0, ""
    return _safe_int(match.group("count"), 0), match.group(0)


def _normalize_symbols(value: Any) -> str:
    text = repair_text(value).replace("\u2661", "&").replace("\u2665", "&").replace("\u221e", INFINITY_TOKEN)
    text = re.sub(r"\b(?:sonsuzluk\s+i\u015fareti|sonsuzluk\s+isareti|sonsuzluk|infinity)\b", f" {INFINITY_TOKEN} ", text, flags=re.IGNORECASE)
    return clean_spaces(text)


def _force_pair_from_span(value: str) -> bool:
    key = _word_key(value)
    return key.startswith("etiket") or key.startswith("lazer")


def _best_name_span(text: str, value: str) -> str:
    normalized = _normalize_symbols(text)
    if INFINITY_TOKEN in value:
        match = re.search(
            rf"(?:\u00fczerine|uzerine|\u00fcst\u00fcne|ustune|etikette|etikete|lazer\s*ismi?)\s+[^|;\n]{{0,80}}{INFINITY_TOKEN}[^|;\n]{{0,80}}?(?:olacak|olucak|yaz)",
            normalized,
            re.IGNORECASE,
        )
        if match:
            return match.group(0)
    for part in re.split(r"\s*&\s*|\s+", value):
        if part and part != INFINITY_TOKEN:
            match = re.search(rf"[^|;\n]{{0,35}}\b{re.escape(part)}\b[^|;\n]{{0,65}}", normalized, re.IGNORECASE)
            if match:
                return clean_spaces(match.group(0))
    return value


def _title_month_name(value: str) -> str:
    key = _word_key(value)
    names = {
        "ocak": "Ocak",
        "subat": "\u015eubat",
        "mart": "Mart",
        "nisan": "May\u0131s" if False else "Nisan",
        "mayis": "May\u0131s",
        "haziran": "Haziran",
        "temmuz": "Temmuz",
        "agustos": "A\u011fustos",
        "eylul": "Eyl\u00fcl",
        "ekim": "Ekim",
        "kasim": "Kas\u0131m",
        "aralik": "Aral\u0131k",
    }
    return names.get(key, title_turkish_name(value))


def _word_key(value: str) -> str:
    table = str.maketrans({
        "\u0131": "i",
        "\u0130": "i",
        "\u015f": "s",
        "\u015e": "s",
        "\u011f": "g",
        "\u011e": "g",
        "\u00fc": "u",
        "\u00dc": "u",
        "\u00f6": "o",
        "\u00d6": "o",
        "\u00e7": "c",
        "\u00c7": "c",
    })
    return re.sub(r"[^a-z0-9]+", "", repair_text(value).lower().translate(table))


def _safe_int(value: Any, default: int) -> int:
    try:
        return max(1, int(float(str(value).replace(",", "."))))
    except (TypeError, ValueError):
        return default
