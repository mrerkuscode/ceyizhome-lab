"""Üretim Reçetesi API — Part C + D

Barkod bazlı reçete saklar ve bulk apply uygular.
Reçeteler: data/recipes.json  (barkod → reçete)
Ürün kataloğu: data/trendyol_products.json  (barkod → ürün)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def recipes_path(project_root: Path) -> Path:
    p = project_root / "data" / "recipes.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def products_path(project_root: Path) -> Path:
    p = project_root / "data" / "trendyol_products.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_recipes(project_root: Path) -> dict[str, Any]:
    p = recipes_path(project_root)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _save_recipes(project_root: Path, data: dict[str, Any]) -> None:
    recipes_path(project_root).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_products(project_root: Path) -> dict[str, Any]:
    p = products_path(project_root)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _empty_recipe(barkod: str) -> dict[str, Any]:
    return {"barkod": barkod, "slots": [], "updated_at": ""}


# ── Part C: get / save recipe ──────────────────────────────────────────────────

def get_recipe(project_root: Path, barkod: str) -> dict[str, Any]:
    """Return recipe for barkod, or an empty template."""
    barkod = str(barkod).strip()
    recipes = _load_recipes(project_root)
    recipe = recipes.get(barkod)
    if recipe and isinstance(recipe, dict):
        recipe["barkod"] = barkod
        recipe["has_recipe"] = bool(recipe.get("slots"))
        return recipe
    return {**_empty_recipe(barkod), "has_recipe": False}


def save_recipe(project_root: Path, barkod: str, slots: list[dict[str, Any]]) -> dict[str, Any]:
    """Save or update the production recipe for a barcode."""
    barkod = str(barkod).strip()
    if not barkod:
        return {"status": "ERROR", "error": "Barkod boş olamaz"}
    if not isinstance(slots, list):
        return {"status": "ERROR", "error": "slots liste olmalı"}
    if len(slots) == 0:
        return {"status": "ERROR", "error": "Reçete için en az 1 slot gerekli"}

    # Validate slots
    for i, slot in enumerate(slots):
        if not isinstance(slot, dict):
            return {"status": "ERROR", "error": f"Slot {i} geçersiz format"}
        cikti = slot.get("cikti", "")
        if cikti not in {"etiket", "lazer"}:
            return {"status": "ERROR", "error": f"Slot {i}: cikti 'etiket' veya 'lazer' olmalı"}
        adet = slot.get("adet")
        if adet is not None:
            try:
                adet_int = int(adet)
                if adet_int < 1:
                    return {"status": "ERROR", "error": f"Slot {i}: adet pozitif tamsayı olmalı"}
                slot["adet"] = adet_int
            except (ValueError, TypeError):
                return {"status": "ERROR", "error": f"Slot {i}: adet geçersiz"}
        # Laser font safety check: if cikti=lazer, font_id must be a laser-safe font
        if cikti == "lazer" and slot.get("font_id"):
            laser_check = _check_laser_font_safe(project_root, slot["font_id"])
            if not laser_check:
                font_name = slot.get("font_id", "")
                return {
                    "status": "ERROR",
                    "error": f"Slot '{slot.get('konum', i)}': Lazer slotunda lazer-güvenli olmayan font kullanılamaz. "
                             f"Lazer kesimde kopabilir. Font ID: {font_name}",
                }

    recipes = _load_recipes(project_root)
    recipes[barkod] = {
        "slots": slots,
        "updated_at": _now(),
    }
    _save_recipes(project_root, recipes)
    return {
        "status": "OK",
        "message": f"Reçete kaydedildi — barkod {barkod} için kalıcı.",
        "barkod": barkod,
        "recipe": {**recipes[barkod], "barkod": barkod, "has_recipe": True},
    }


def _check_laser_font_safe(project_root: Path, font_id: str) -> bool:
    """Return True if font_id is in laser_fonts and laser_safe=True."""
    from webui_backend.font_library_api import list_fonts
    manifest = list_fonts(project_root)
    for f in manifest.get("laser_fonts", []):
        if f.get("id") == font_id:
            return bool(f.get("laser_safe", False))
    # If the font_id is not in laser_fonts at all → not safe
    return False


# ── Part D: bulk apply ────────────────────────────────────────────────────────

def bulk_apply_recipe(
    project_root: Path,
    barkodlar: list[str],
    ayarlar: dict[str, Any],
) -> dict[str, Any]:
    """Merge ayarlar into each barcode's recipe.

    Existing slots are updated with provided settings (cikti, font_ids, adet).
    If a barcode has no recipe, a single default slot is created.
    """
    if not isinstance(barkodlar, list) or not barkodlar:
        return {"status": "ERROR", "error": "barkodlar listesi boş olamaz"}
    if not isinstance(ayarlar, dict):
        return {"status": "ERROR", "error": "ayarlar dict olmalı"}

    recipes = _load_recipes(project_root)
    updated: list[str] = []
    now = _now()

    for barkod in barkodlar:
        barkod = str(barkod).strip()
        if not barkod:
            continue

        existing = recipes.get(barkod, {})
        slots: list[dict[str, Any]] = list(existing.get("slots", []))

        if not slots:
            # Create a default slot so settings can be applied
            slots = [{"id": "slot_1", "konum": "Varsayılan", "cikti": "etiket", "besleyen": "isim", "adet": 1}]

        # Merge settings into slots
        for slot in slots:
            cikti_override = ayarlar.get("cikti")
            if cikti_override and cikti_override in {"etiket", "lazer", "etiket+lazer"}:
                if cikti_override == "etiket+lazer":
                    # Do not change individual slot cikti when "both" is selected
                    pass
                else:
                    slot["cikti"] = cikti_override

            if slot.get("cikti") == "etiket" and ayarlar.get("etiket_font_id"):
                slot["font_id"] = ayarlar["etiket_font_id"]
            if slot.get("cikti") == "lazer" and ayarlar.get("lazer_font_id"):
                slot["font_id"] = ayarlar["lazer_font_id"]
            if ayarlar.get("adet") is not None:
                try:
                    slot["adet"] = max(1, int(ayarlar["adet"]))
                except (ValueError, TypeError):
                    pass

        recipes[barkod] = {"slots": slots, "updated_at": now}
        updated.append(barkod)

    _save_recipes(project_root, recipes)
    return {
        "status": "OK",
        "message": f"{len(updated)} barkodun reçetesi güncellendi.",
        "updated": updated,
        "count": len(updated),
    }


# ── Product list with recipe status ──────────────────────────────────────────

def list_products_with_recipe_status(project_root: Path) -> list[dict[str, Any]]:
    """Return product catalog rows with recipe has_recipe field."""
    products = _load_products(project_root)
    recipes = _load_recipes(project_root)
    rows: list[dict[str, Any]] = []
    for barkod, prod in products.items():
        has_recipe = barkod in recipes and bool(recipes[barkod].get("slots"))
        rows.append({
            **prod,
            "barkod": barkod,
            "has_recipe": has_recipe,
            "eslesme_durumu": "eslesti" if has_recipe else "eslesmedi",
        })
    return rows


def recipe_status_for_barcode(project_root: Path, barkod: str) -> str:
    """Return 'eslesti' or 'eslesmedi' for a single barcode."""
    recipes = _load_recipes(project_root)
    has_recipe = barkod in recipes and bool(recipes[barkod].get("slots"))
    return "eslesti" if has_recipe else "eslesmedi"
