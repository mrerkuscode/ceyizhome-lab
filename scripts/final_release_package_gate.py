from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCS = [
    "RELEASE_NOTES.md",
    "USER_MANUAL.md",
    "TECHNICAL_MANUAL.md",
    "INSTALLATION_CHECKLIST.md",
    "FINAL_RELEASE_CHECKLIST.md",
    "USER_HELP_AND_ONBOARDING_REPORT.md",
]

REQUIRED_PATHS = [
    "src/webui/index.html",
    "src/webui/app.js",
    "src/webui/styles.css",
    "scripts/build_release_package.py",
    "scripts/verify_release_package.py",
    "templates/designs",
    "assets/label_backgrounds",
    "output",
    "backups",
    "logs",
    "examples/sample_bulk_labels.csv",
    "examples/toplu_etiket_ornek.xlsx",
    "examples/etiket_ve_isim_kesim_ornek.xlsx",
    "start_app.bat",
    "run_release_quality_gate.bat",
]

SAFETY_TOKENS = [
    "Direct print kapalı",
    "Yazıcı otomatik çalışmaz",
    "CorelDRAW",
    "Illustrator",
    "RDWorks",
    "Kaynak AI/CDR",
]

MOJIBAKE_TOKENS = [
    "T?rk",
    "?niz",
    "Yazd?r",
    "??kt",
    "G?rsel",
    "?retim",
    "ba?ar",
    "d??meden",
    "kullan?c?",
    "Ã",
    "Å",
    "Ä",
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    checks: list[dict[str, str]] = []

    for doc in REQUIRED_DOCS:
        path = PROJECT_ROOT / doc
        assert_true(path.exists(), f"Eksik release dokümanı: {doc}")
        text = path.read_text(encoding="utf-8")
        assert_true(len(text.strip()) > 200, f"Release dokümanı çok kısa: {doc}")
        for token in MOJIBAKE_TOKENS:
            assert_true(token not in text, f"Şüpheli mojibake izi: {doc} -> {token}")
        checks.append({"name": doc, "status": "PASSED"})

    release_text = "\n".join((PROJECT_ROOT / doc).read_text(encoding="utf-8") for doc in REQUIRED_DOCS)
    for token in SAFETY_TOKENS:
        assert_true(token in release_text, f"Release güvenlik metni eksik: {token}")

    for rel in REQUIRED_PATHS:
        path = PROJECT_ROOT / rel
        assert_true(path.exists(), f"Eksik release path: {rel}")
        checks.append({"name": rel, "status": "PASSED"})

    sample = (PROJECT_ROOT / "examples" / "sample_bulk_labels.csv").read_text(encoding="utf-8")
    for token in ["model_name", "label_text", "date_text", "note_text", "quantity", "Ayşe"]:
        assert_true(token in sample, f"Örnek Excel/CSV alanı eksik: {token}")

    result = {
        "status": "PASSED",
        "checks": checks,
        "manual_decisions": [
            "Sessiz/direct print üretime alınmadı.",
            "CorelDRAW/Illustrator/RDWorks native edit üretim akışına bağlanmadı.",
            "Kaynak AI/CDR dosyaları değiştirilmedi.",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
