"""
CeyizHome Lab — Trendyol Çıkarım Canlı Örnek Raporu
====================================================
Kullanım:
    python scripts/extraction_live_sample.py          # deterministik (LLM yok)
    python scripts/extraction_live_sample.py --ai     # AI anahtarı varsa LLM de çalışır
    python scripts/extraction_live_sample.py --n 50   # kaç mesaj örnekleneceği

Kaynak: data/trendyol_questions_context.json (gerçek senkronize mesajlar)
Çıktı:  metrik tablosu + 10 örnek satır
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

# Windows terminali UTF-8 yapılandır
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# --- proje kök dizini ---
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from intelligence.trendyol_order_extractor import extract_production_fields
from intelligence.trendyol_ai_extractor import (
    extract_with_ai_or_fallback,
    is_ai_configured,
)
from webui_backend.trendyol_api import get_settings

# ---------------------------------------------------------------------------

def _load_messages(n: int) -> list[dict[str, Any]]:
    path = _ROOT / "data" / "trendyol_questions_context.json"
    if not path.exists():
        sys.exit(f"HATA: {path} bulunamadi")
    rows = json.loads(path.read_text(encoding="utf-8"))
    # Sadece question_text olan kayitlar
    rows = [r for r in rows if r.get("question_text") and len(r.get("question_text", "")) > 5]
    return rows[:n]


def _run_deterministic(row: dict[str, Any]) -> dict[str, Any]:
    return extract_production_fields(row, {})


def _run_with_ai(row: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    det = extract_production_fields(row, {})
    return extract_with_ai_or_fallback(_ROOT, row, {}, det, settings)


def _classify(result: dict[str, Any]) -> str:
    label = result.get("label_text", "")
    conf  = float(result.get("confidence", 0))
    needs_review = result.get("needs_user_review", True)
    if not label:
        return "isim_yok"
    if needs_review or conf < 0.85:
        return "kontrole_dustu"
    return "isim_bulundu"


_JUNK_TOKENS = re.compile(
    r"^(?:gold|gumus|silver|beyaz|siyah|mavi|mor|merhba?|mrb|slm|selam|"
    r"teslimat|kargo|siparis|numara|seklinde|gibi|olsun|verdigim|olusturdum)$",
    re.IGNORECASE,
)

def _is_junk(label: str) -> bool:
    if not label:
        return False
    tokens = re.split(r"[\s&]+", label.strip())
    return all(_JUNK_TOKENS.match(t) for t in tokens if t)


def _truncate(text: str, n: int = 60) -> str:
    t = str(text or "").replace("\n", " ")
    return t[:n] + "…" if len(t) > n else t


def main() -> None:
    ap = argparse.ArgumentParser(description="Trendyol çıkarım canlı örnek raporu")
    ap.add_argument("--n",   type=int, default=100, help="Kaç mesaj örnekleneceği (default: 100)")
    ap.add_argument("--ai",  action="store_true",  help="AI yapılandırılmışsa LLM de çalıştır")
    ap.add_argument("--all", action="store_true",  help="Tüm mesajları örnekle")
    args = ap.parse_args()

    rows = _load_messages(999999 if args.all else args.n)
    settings = get_settings(_ROOT, masked=False)
    use_ai = args.ai and is_ai_configured(settings)

    print(f"\n{'='*68}")
    print(f"  Trendyol Çıkarım Canlı Örnek Raporu — Faz A")
    print(f"  Kaynak  : data/trendyol_questions_context.json")
    print(f"  Örneklem: {len(rows)} mesaj")
    print(f"  Mod     : {'LLM + deterministik' if use_ai else 'Sadece deterministik (AI key yok)'}")
    print(f"{'='*68}\n")

    counts: dict[str, int] = {"isim_bulundu": 0, "kontrole_dustu": 0, "isim_yok": 0}
    junk_count = 0
    samples: list[dict] = []

    for row in rows:
        result = _run_with_ai(row, settings) if use_ai else _run_deterministic(row)
        cat = _classify(result)
        counts[cat] += 1
        label = result.get("label_text", "")
        if _is_junk(label):
            junk_count += 1
        samples.append({
            "msg":   _truncate(row.get("question_text", "")),
            "label": label,
            "date":  result.get("date_text", ""),
            "conf":  round(float(result.get("confidence", 0)), 2),
            "cat":   cat,
            "junk":  _is_junk(label),
            "order": row.get("order_number", ""),
        })

    total = len(rows)
    print(f"{'-'*68}")
    print(f"  ÖZET METRİK ({total} mesaj)")
    print(f"{'-'*68}")
    print(f"  ✅ İsim bulundu (≥0.85, review yok) : {counts['isim_bulundu']:4d}  ({counts['isim_bulundu']/total*100:.1f}%)")
    print(f"  ⚠️  Kontrole düştü (düşük güven)     : {counts['kontrole_dustu']:4d}  ({counts['kontrole_dustu']/total*100:.1f}%)")
    print(f"  ⬜ İsim yok / boş                    : {counts['isim_yok']:4d}  ({counts['isim_yok']/total*100:.1f}%)")
    print(f"  🚨 Çöp isim* (blocklist eşleşmesi)  : {junk_count:4d}  ({junk_count/total*100:.1f}%)")
    print(f"{'-'*68}")
    print(f"  * Renk/selamlama/teslimat gibi token'lar isim alanına geçti")
    print()

    # --- 10 örnek satır ---
    print(f"  ÖRNEK ÇIKTILAR (10 satır)")
    print(f"{'-'*68}")
    fmt = "  {cat:16s} | conf:{conf:.2f} | {label:22s} | {msg}"
    shown = 0
    for s in samples:
        if shown >= 10:
            break
        cat_icon = {"isim_bulundu": "✅", "kontrole_dustu": "⚠️ ", "isim_yok": "⬜"}.get(s["cat"], "?")
        junk_mark = " 🚨ÇÖPTOKEN" if s["junk"] else ""
        print(f"  {cat_icon} conf:{s['conf']:.2f} | {s['label'] or '(boş)':22s} | {s['msg']}{junk_mark}")
        shown += 1

    # --- Çöp isim örnekleri ---
    junk_samples = [s for s in samples if s["junk"]][:5]
    if junk_samples:
        print()
        print(f"  ÇÖPTOKEN ÖRNEKLERİ (Faz A sonrası kalan — varsa ciddi sorun)")
        print(f"{'-'*68}")
        for s in junk_samples:
            print(f"  🚨 '{s['label']}' ← {s['msg']}")

    print(f"\n{'='*68}\n")


if __name__ == "__main__":
    main()
