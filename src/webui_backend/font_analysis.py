from __future__ import annotations

from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont


UPPERCASE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWERCASE_CHARS = "abcdefghijklmnopqrstuvwxyz"
TURKISH_CHARS = "ÇĞİÖŞÜçğıöşü"
DIGIT_CHARS = "0123456789"
PUNCTUATION_CHARS = ".,:;!?-_/&+@₺'\"()"
CONNECTED_CAPITAL_VARIANTS = ["A_con", "F_con", "H_con", "X_con", "S_con", "L_con", "M_con"]


def _feature_tags(font: TTFont, table_name: str) -> list[str]:
    table = font.get(table_name)
    if not table or not getattr(table, "table", None) or not getattr(table.table, "FeatureList", None):
        return []
    return sorted({record.FeatureTag for record in table.table.FeatureList.FeatureRecord})


def _coverage(chars: str, cmap: dict[int, str]) -> dict[str, Any]:
    present = [char for char in chars if ord(char) in cmap]
    missing = [char for char in chars if ord(char) not in cmap]
    return {
        "total": len(chars),
        "present": present,
        "missing": missing,
        "coverage_percent": round((len(present) / max(1, len(chars))) * 100, 1),
    }


def analyze_font(font_path: str | Path) -> dict[str, Any]:
    path = Path(font_path)
    if not path.exists():
        return {"status": "ERROR", "message": f"Font bulunamadı: {path}", "font_path": str(path)}

    font = TTFont(str(path))
    cmap = font.getBestCmap() or {}
    glyph_order = set(font.getGlyphOrder())
    name_table = font["name"] if "name" in font else None
    names = []
    if name_table:
        for record in name_table.names:
            if record.nameID in {1, 2, 4, 6}:
                try:
                    names.append(record.toUnicode())
                except Exception:
                    continue

    connected_variants = {variant: variant in glyph_order for variant in CONNECTED_CAPITAL_VARIANTS}
    alternatives = sorted(
        glyph
        for glyph in glyph_order
        if any(token in glyph.lower() for token in [".", "_", "con", "salt", "liga", "init", "fina", "alt"])
    )[:160]

    return {
        "status": "OK",
        "font_path": str(path),
        "names": sorted(set(names)),
        "glyph_count": len(glyph_order),
        "coverage": {
            "uppercase": _coverage(UPPERCASE_CHARS, cmap),
            "lowercase": _coverage(LOWERCASE_CHARS, cmap),
            "turkish": _coverage(TURKISH_CHARS, cmap),
            "digits": _coverage(DIGIT_CHARS, cmap),
            "punctuation": _coverage(PUNCTUATION_CHARS, cmap),
            "try_symbol": _coverage("₺", cmap),
        },
        "features": {
            "GSUB": _feature_tags(font, "GSUB"),
            "GPOS": _feature_tags(font, "GPOS"),
        },
        "connected_capital_variants": connected_variants,
        "natural_connected_capitals": [key.replace("_con", "") for key, present in connected_variants.items() if present],
        "manual_bridge_capitals": [key.replace("_con", "") for key, present in connected_variants.items() if not present],
        "alternative_glyphs": alternatives,
        "try_fallback_required": ord("₺") not in cmap,
    }
