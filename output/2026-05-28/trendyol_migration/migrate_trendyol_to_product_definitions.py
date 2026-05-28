"""Migration: data/trendyol_product_mappings.json (36 onaylı) →
data/product_definitions.json (yeni Ürün Tanım Sistemi schema'sı).

Kural (Leyla, 2026-05-28):
- 332 öneriye DOKUNMA (sadece 36 onaylı aktar)
- Eski sistem SILINMEZ (data/trendyol_product_mappings.json korunur)
- Sahte başarı YASAK: her satırın schema validation sonucu raporlanır
- Default değerler (Leyla sonra düzenler):
    name_config.type = "couple" (label_and_name_cut için)
                     = "single" (sadece name_cut için)
    name_config.count = 1
    name_config.size_group = "auto"
    name_config.compound_format = "joined"
    label_config.default_count = 10 (etiketli ürünler için)
    label_config.adjustable_in_production = True
    label_config.min_count = 1
    label_config.max_count = 50

Kullanım:
    python migrate_trendyol_to_product_definitions.py --dry-run    # önizleme, yazma yok
    python migrate_trendyol_to_product_definitions.py              # gerçek aktarım
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Project import path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # output/2026-05-28/trendyol_migration → root
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from webui_backend import product_definitions_api as pda


SOURCE_RELATIVE = "data/trendyol_product_mappings.json"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def map_one(old: dict) -> dict:
    """Convert one old-mapping row → new product-definition payload."""
    barcode = str(old.get("barcode") or "").strip()
    product_name = str(old.get("product_name") or "").strip()
    production_type = str(old.get("production_type") or "").strip()
    model_key = str(old.get("model_key") or "").strip()
    model_name = str(old.get("model_name") or "").strip()
    merchant_sku = str(old.get("merchant_sku") or "").strip()
    stock_code = str(old.get("stock_code") or "").strip()

    label_enabled = "label" in production_type
    if production_type == "name_cut":
        name_type = "single"  # safe default; Leyla can flip to couple
    elif production_type in {"label_and_name_cut", "label"}:
        name_type = "couple" if "name_cut" in production_type else "none"
    else:
        name_type = "single"
    name_count = 0 if name_type == "none" else 1

    label_model = model_key or model_name or ""
    notes_lines = []
    if model_name and model_key and model_name != model_key:
        notes_lines.append(f"Eski etiket model: {model_name} ({model_key})")
    elif model_name:
        notes_lines.append(f"Eski etiket model: {model_name}")
    if merchant_sku and merchant_sku.lower() not in {"merchantsku", "merchant_sku"}:
        notes_lines.append(f"Trendyol merchant_sku: {merchant_sku}")
    if stock_code and stock_code != merchant_sku and stock_code.lower() not in {"merchantsku", "merchant_sku"}:
        notes_lines.append(f"Stock code: {stock_code}")
    notes_lines.append(
        f"Trendyol mapping'den aktarıldı (production_type={production_type}, "
        f"name_cut_width_mm={old.get('name_cut_width_mm')}, "
        f"created={old.get('created_at')})."
    )
    notes_lines.append("DEFAULT değerler — Leyla düzenleyebilir.")

    return {
        "sku": barcode,
        "trendyol_sku": barcode,
        "product_name": product_name,
        "name_config": {
            "type": name_type,
            "count": name_count,
            "size_group": "auto",
            "compound_format": "joined",
            "test_name": "",
        },
        "label_config": {
            "enabled": label_enabled,
            "model": label_model if label_enabled else "",
            "default_count": 10 if label_enabled else 0,
            "adjustable_in_production": True if label_enabled else False,
            "min_count": 1 if label_enabled else 0,
            "max_count": 50 if label_enabled else 0,
        },
        "extras": {
            "special_requests_allowed": True,
            "production_notes": "\n".join(notes_lines),
        },
        "metadata": {
            "source": "trendyol_mapping_migration_2026-05-28",
        },
    }


def run(*, dry_run: bool, force_overwrite: bool = False) -> dict:
    src = PROJECT_ROOT / SOURCE_RELATIVE
    if not src.exists():
        return {"status": "ERROR", "message": f"Kaynak dosya yok: {SOURCE_RELATIVE}"}

    source = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(source, list):
        return {"status": "ERROR", "message": "Kaynak liste değil."}

    # Filter: only active=true rows (per spec — 36 onaylı)
    rows = [r for r in source if isinstance(r, dict) and r.get("active") is True]

    results = {
        "started_at": _now_iso(),
        "dry_run": dry_run,
        "total_source": len(source),
        "total_active": len(rows),
        "success": [],
        "skipped_existing": [],
        "failed": [],
    }

    for index, old in enumerate(rows, start=1):
        barcode = str(old.get("barcode") or "").strip()
        if not barcode:
            results["failed"].append({
                "index": index,
                "sku": "",
                "product_name": old.get("product_name", ""),
                "errors": ["barcode boş — Trendyol mapping kaydı geçersiz."],
            })
            continue

        # Skip if SKU already exists in product_definitions (and not force_overwrite)
        existing = pda.get_definition(PROJECT_ROOT, barcode)
        if existing and not force_overwrite:
            results["skipped_existing"].append({
                "index": index,
                "sku": barcode,
                "product_name": old.get("product_name", ""),
                "reason": "Bu SKU zaten product_definitions.json'da var.",
            })
            continue

        payload = map_one(old)
        # Validate ahead of save so we can see all errors at once
        normalized = pda.normalize_definition(payload, prior=None)
        errors = pda.validate_definition(PROJECT_ROOT, normalized)
        if errors:
            results["failed"].append({
                "index": index,
                "sku": barcode,
                "product_name": old.get("product_name", ""),
                "errors": errors,
                "normalized_preview": normalized,
            })
            continue

        if dry_run:
            results["success"].append({
                "index": index,
                "sku": barcode,
                "product_name": old.get("product_name", ""),
                "preview": {
                    "name_config": normalized["name_config"],
                    "label_config": normalized["label_config"],
                },
                "would_create": True,
            })
        else:
            save_result = pda.api_save(PROJECT_ROOT, payload)
            if save_result.get("status") == "OK":
                results["success"].append({
                    "index": index,
                    "sku": barcode,
                    "product_name": old.get("product_name", ""),
                    "created": save_result.get("created"),
                })
            else:
                results["failed"].append({
                    "index": index,
                    "sku": barcode,
                    "product_name": old.get("product_name", ""),
                    "errors": save_result.get("errors") or [save_result.get("message", "Bilinmeyen hata.")],
                })

    results["finished_at"] = _now_iso()
    results["counts"] = {
        "success": len(results["success"]),
        "skipped_existing": len(results["skipped_existing"]),
        "failed": len(results["failed"]),
    }
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Yazma, sadece raporla")
    parser.add_argument("--force", action="store_true", help="Var olanları üzerine yaz (TEHLİKELİ)")
    parser.add_argument("--output", help="Sonucu JSON dosyasına yaz")
    args = parser.parse_args()

    result = run(dry_run=args.dry_run, force_overwrite=args.force)
    summary = result.get("counts") or {}
    print(f"[migration] dry_run={result.get('dry_run')} "
          f"total_active={result.get('total_active')} "
          f"success={summary.get('success')} "
          f"skipped_existing={summary.get('skipped_existing')} "
          f"failed={summary.get('failed')}")

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        print(f"[migration] sonuç yazıldı: {args.output}")

    return 0 if not result.get("failed") else 1


if __name__ == "__main__":
    sys.exit(main())
