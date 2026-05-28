from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from intelligence import trendyol_ai_extractor
from intelligence.trendyol_order_extractor import extract_production_fields


CASES: list[dict[str, Any]] = [
    {
        "name": "CASE 1 - multi surface Tuğçe Murat",
        "input": "#11242576296 Tuğçe & Murat çiçeğin üstünde siyah kurdele üstüne gold yazı. Çikolatanın üstüne (iki katlı sunumluk olan) Tuğçe & Murat 29.05.2026 gold yazı yazılsın. Çiçekli tasarım olsun. Tepsi içindeki çikolatalarda da “Allahın emri ile kızınızı istemeye geldik” gold yazı ile.",
        "expected": {
            "personNames": ["Tuğçe", "Murat"],
            "labelName": "Tuğçe & Murat",
            "laserName": "Tuğçe & Murat",
            "eventDate": "29.05.2026",
            "customText": "Allah’ın emri ile kızınızı istemeye geldik",
            "productionNoteIncludes": ["siyah kurdele", "gold yazı", "Çikolatanın üstüne", "Çiçekli tasarım", "Tepsi içindeki çikolatalarda"],
        },
        "rejectedLabel": "Kurdele Üstüne Gold & Murat Gold Yazı",
    },
    {
        "name": "CASE 2 - color only no name",
        "input": "Merhaba, 6 tane sipariş verdim. Sipariş numarası 11242658230. Hepsi BEYAZ olsun istiyorum. Teşekkür ederim.",
        "expected": {"personNames": None, "labelName": None, "laserName": None, "eventDate": None, "productionNote": "Hepsi beyaz olacak."},
        "rejectedLabel": "Hepsi Beyaz",
    },
    {
        "name": "CASE 3 - date name custom text",
        "input": "#11242760731 nolu sipariş çikolataların üzerine yazılacak tarih 30.05.2026 nişan hatırası yazılacak isimler Derya ve M.Şerif",
        "expected": {
            "personNames": ["Derya", "M. Şerif"],
            "labelName": "Derya & M. Şerif",
            "laserName": "Derya & M. Şerif",
            "eventDate": "30.05.2026",
            "customText": "Nişan hatırası",
        },
        "rejectedLabel": "Hatırası",
    },
    {
        "name": "CASE 4 - simple lowercase names",
        "input": "elvida ömer olacak isimler",
        "expected": {"personNames": ["Elvida", "Ömer"], "labelName": "Elvida & Ömer", "laserName": "Elvida & Ömer"},
        "rejectedLabel": "Elvida Ömer Olacak İsimler",
    },
    {
        "name": "CASE 5 - infinity and custom text",
        "input": "Görseldekinin aynısı olsun tülü siyah şekilde üzerine elif sonsuzluk işareti Muhammed olacak şekilde yaparsanız sevinirim Allah’ın emri ile kızımızı istemeye geldik olacak çikolatalı tepsi",
        "expected": {
            "personNames": ["Elif", "Muhammed"],
            "labelName": "Elif ♾ Muhammed",
            "laserName": "Elif ♾ Muhammed",
            "customText": "Allah’ın emri ile kızımızı istemeye geldik",
            "productionNoteIncludes": ["Görseldekinin aynısı", "Tülü siyah", "Çikolatalı tepsi"],
        },
    },
    {
        "name": "CASE 6 - custom text only no name",
        "input": "Üzerine Allah’ın emri ile kızımızı istemeye geldik yazılsın.",
        "expected": {"personNames": None, "labelName": None, "laserName": None, "customText": "Allah’ın emri ile kızımızı istemeye geldik"},
        "rejectedLabel": "Allah’ın Emri",
    },
    {
        "name": "CASE 7 - names date nearby",
        "input": "Ayşe Mehmet 12.06.2026 yazılsın, gold olsun",
        "expected": {
            "personNames": ["Ayşe", "Mehmet"],
            "labelName": "Ayşe & Mehmet",
            "laserName": "Ayşe & Mehmet",
            "eventDate": "12.06.2026",
            "productionNote": "Gold yazı kullanılacak.",
        },
    },
    {
        "name": "CASE 8 - Elif Ismail with production words",
        "input": "#11251601296 G\u00fcm\u00fc\u015f renk ince \u00e7er\u00e7eve Elif & \u0130smail orta k\u0131sma kalp koyarsan\u0131z iyi olur \u00e7ikolataya",
        "expected": {
            "personNames": ["Elif", "\u0130smail"],
            "labelName": "Elif & \u0130smail",
            "laserName": "Elif & \u0130smail",
            "eventDate": None,
            "productionNoteIncludes": ["G\u00fcm\u00fc\u015f renk", "\u0130nce \u00e7er\u00e7eve", "kalp"],
        },
        "rejectedLabel": "G\u00fcm\u00fc\u015f",
    },
    {
        "name": "CASE 9 - Melike Kursat nearby date",
        "input": "#11251171218 \u00c7i\u00e7e\u011fin \u00fcst\u00fcnde Melike K\u00fcr\u015fat yaz\u0131lacak \u00e7ikolatalar\u0131n \u00fczerine de Melike K\u00fcr\u015fat 31.05.2026 yaz\u0131lacak",
        "expected": {
            "personNames": ["Melike", "K\u00fcr\u015fat"],
            "labelName": "Melike & K\u00fcr\u015fat",
            "laserName": "Melike & K\u00fcr\u015fat",
            "eventDate": "31.05.2026",
        },
        "rejectedLabel": "De Melike K\u00fcr\u015fat",
    },
    {
        "name": "CASE 10 - Irem Talha explicit ampersand",
        "input": "11251157196 nolu sipari\u015f i\u00e7in \u00e7ift isimleri \u0130rem & Talha tarih : 31.05.2026",
        "expected": {
            "personNames": ["\u0130rem", "Talha"],
            "labelName": "\u0130rem & Talha",
            "laserName": "\u0130rem & Talha",
            "eventDate": "31.05.2026",
        },
        "rejectedLabel": "\u0130\u00e7in \u00c7ift \u0130simleri & Talha",
    },
    {
        "name": "CASE 11 - Ece Kadir slash",
        "input": "#11251008020 merhaba sipari\u015f numaram ki\u015fiselle\u015ftirme ECE / KAD\u0130R 07.06.2026",
        "expected": {
            "personNames": ["Ece", "Kadir"],
            "labelName": "Ece & Kadir",
            "laserName": "Ece & Kadir",
            "eventDate": "07.06.2026",
        },
        "rejectedLabel": "Numaram Ki\u015fiselle\u015ftirme Ece Kadir",
    },
    {
        "name": "CASE 12 - Gulbanu Yasin ampersand",
        "input": "#11250893267 sipari\u015f numaras\u0131 G\u00fclbanu & Yasin \u015feklinde yaz\u0131yor olacak \u015fimdiden te\u015fekk\u00fcrler",
        "expected": {
            "personNames": ["G\u00fclbanu", "Yasin"],
            "labelName": "G\u00fclbanu & Yasin",
            "laserName": "G\u00fclbanu & Yasin",
            "eventDate": None,
        },
        "rejectedLabel": "Numaras\u0131 G\u00fclbanu & Yasin \u015eeklinde Yaz\u0131yor",
    },
    {
        "name": "CASE 13 - Helin Cemal dot separator",
        "input": "11251572511 \u00e7i\u00e7e\u011fe yaz\u0131lan isim Helin.Cemal \u00e7ikolata kutusuna bide \u00e7ikolataya yaz\u0131lan isim tarih helin.Cemal 02.06.2026",
        "expected": {
            "personNames": ["Helin", "Cemal"],
            "labelName": "Helin & Cemal",
            "laserName": "Helin & Cemal",
            "eventDate": "02.06.2026",
        },
        "rejectedLabel": "Helin Cemal \u0130kolata Kutusuna Bide \u0130kolataya",
    },
    {
        "name": "CASE 14 - quoted two names",
        "input": "sipari\u015f numaras\u0131: 11240008370 yaz\u0131lacak isimler \"\u0130rem\" \"Oktay\" yaz\u0131 rengi GOLD olsun.",
        "expected": {
            "personNames": ["\u0130rem", "Oktay"],
            "labelName": "\u0130rem & Oktay",
            "laserName": "\u0130rem & Oktay",
            "eventDate": None,
            "productionNote": "Gold yaz\u0131 kullan\u0131lacak.",
        },
        "rejectedLabel": "Bulunamad\u0131",
    },
    {
        "name": "CASE 15 - field heading after names",
        "input": "#11245257456 sipari\u015f numaral\u0131 \u00fcr\u00fcn\u00fcm\u00fcn \u00fcst\u00fcne yaz\u0131lacaklar \u015f\u00f6yledir; isimler: aleyna ve \u00d6zcan \u0130steme tarihi: 31.05.2026 T\u00fcl se\u00e7imimiz: siyah",
        "expected": {
            "personNames": ["Aleyna", "\u00d6zcan"],
            "labelName": "Aleyna & \u00d6zcan",
            "laserName": "Aleyna & \u00d6zcan",
            "eventDate": "31.05.2026",
            "productionNoteIncludes": ["T\u00fcl se\u00e7imi siyah"],
        },
        "rejectedLabels": [
            "\u00d6zcan \u0130steme",
            "Aleyna Ve \u00d6zcan \u0130steme",
            "\u0130steme Tarihi",
        ],
    },
    {
        "name": "CASE 16 - production instruction only no name",
        "input": "T\u00fcl se\u00e7imi siyah, gold yaz\u0131 olsun. G\u00f6rseldekinin ayn\u0131s\u0131 olsun.",
        "expected": {
            "personNames": None,
            "labelName": None,
            "laserName": None,
            "eventDate": None,
        },
        "rejectedLabels": ["T\u00fcl Se\u00e7imi", "Gold Yaz\u0131", "G\u00f6rseldekinin Ayn\u0131s\u0131"],
    },
]


def run_case(case: dict[str, Any]) -> tuple[bool, dict[str, Any], list[str]]:
    source = {"question_text": case["input"], "quantity": 1, "product_name": "Kişiye Özel Ürün"}
    deterministic = extract_production_fields(source, {"production_type": "label_and_name_cut"})
    actual = trendyol_ai_extractor.extract_with_ai_or_fallback(
        PROJECT_ROOT,
        source,
        {"production_type": "label_and_name_cut"},
        deterministic,
        {"ai_enabled": False},
    )
    normalized = {
        "personNames": actual.get("person_names") or None,
        "labelName": actual.get("label_text") or None,
        "laserName": actual.get("name_cut_text") or None,
        "eventDate": actual.get("date_text") or None,
        "customText": actual.get("custom_text") or None,
        "productionNote": actual.get("production_note") or actual.get("note_text") or None,
        "quantity": actual.get("quantity") or None,
        "confidence": round(float(actual.get("confidence") or 0) * 100),
        "warnings": actual.get("warnings") or [],
    }
    diffs: list[str] = []
    expected = case["expected"]
    for key in ["personNames", "labelName", "laserName", "eventDate", "customText", "productionNote"]:
        if key in expected and normalized.get(key) != expected[key]:
            diffs.append(f"{key}: expected {expected[key]!r}, actual {normalized.get(key)!r}")
    for snippet in expected.get("productionNoteIncludes", []):
        if snippet.lower() not in str(normalized.get("productionNote") or "").lower():
            diffs.append(f"productionNote missing snippet {snippet!r}")
    rejected = case.get("rejectedLabel")
    if rejected and normalized.get("labelName") == rejected:
        diffs.append(f"labelName rejected value appeared: {rejected!r}")
    for rejected_item in case.get("rejectedLabels", []):
        if normalized.get("labelName") == rejected_item:
            diffs.append(f"labelName rejected value appeared: {rejected_item!r}")
    if normalized.get("labelName") and any(word in normalized["labelName"].lower() for word in ["kurdele", "gold yazı", "üstüne", "çikolata", "çiçek", "tasarım", "olacak isimler", "hepsi beyaz", "ikolata", "kutu", "kutusuna"]):
        diffs.append("labelName contains production/instruction words")
    return not diffs, normalized, diffs


def main() -> int:
    failed = 0
    for case in CASES:
        ok, actual, diffs = run_case(case)
        print("=" * 80)
        print(case["name"])
        print("INPUT")
        print(case["input"])
        print("EXPECTED")
        print(json.dumps(case["expected"], ensure_ascii=False, indent=2))
        print("ACTUAL")
        print(json.dumps(actual, ensure_ascii=False, indent=2))
        print("PASS" if ok else "FAIL")
        print("DIFF")
        print("\n".join(diffs) if diffs else "-")
        if not ok:
            failed += 1
    print("=" * 80)
    print(f"SUMMARY: {len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
