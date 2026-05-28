from __future__ import annotations

import re
from typing import Any


MOJIBAKE_MARKERS = ("\u00c3", "\u00c4", "\u00c5", "\u00c2", "\u00d0", "\ufffd")

TURKISH_NAME_FIXES = {
    "ayse": "Ay\u015fe",
    "omer": "\u00d6mer",
    "cagatay": "\u00c7a\u011fatay",
    "cagla": "\u00c7a\u011fla",
    "cagri": "\u00c7a\u011fr\u0131",
    "tugce": "Tu\u011f\u00e7e",
    "gulsah": "G\u00fcl\u015fah",
    "sule": "\u015eule",
    "ozge": "\u00d6zge",
    "ozgur": "\u00d6zg\u00fcr",
    "ipek": "\u0130pek",
    "irem": "\u0130rem",
    "ilker": "\u0130lker",
    "ibrahim": "\u0130brahim",
    "ismail": "\u0130smail",
    "oguz": "O\u011fuz",
    "yagmur": "Ya\u011fmur",
    "bugra": "Bu\u011fra",
    "mucahit": "M\u00fccahit",
    "mujahit": "M\u00fccahit",
    "nisan": "Ni\u015fan",
    "soz": "S\u00f6z",
}


def repair_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if any(marker in text for marker in MOJIBAKE_MARKERS):
        for encoding in ("cp1252", "latin1", "cp1254"):
            try:
                candidate = text.encode(encoding).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if _score_text(candidate) > _score_text(text):
                text = candidate
                break
    return clean_spaces(text)


def clean_spaces(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def title_turkish_name(value: Any) -> str:
    words = re.split(r"\s+", repair_text(value).strip())
    return " ".join(_title_word(word) for word in words if word)


def _title_word(word: str) -> str:
    normalized = _ascii_key(word)
    if normalized in TURKISH_NAME_FIXES:
        return TURKISH_NAME_FIXES[normalized]
    lowered = word.lower().replace("\u0307", "")
    if not lowered:
        return ""
    first = "\u0130" if lowered[0] == "i" else lowered[0].upper()
    return first + lowered[1:]


def _ascii_key(value: str) -> str:
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
    return repair_text(value).lower().translate(table)


def _score_text(value: str) -> int:
    score = 0
    score -= sum(value.count(marker) * 8 for marker in MOJIBAKE_MARKERS)
    score += sum(value.count(ch) * 2 for ch in "\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc")
    score += sum(value.lower().count(word) for word in ("ki\u015fiye", "\u00f6zel", "ni\u015fan", "s\u00f6z", "m\u00fc\u015fteri", "\u00e7ikolata"))
    return score
