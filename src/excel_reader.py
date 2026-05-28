from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


TURKISH_COLUMN_ALIASES = {
    "siparis_no": "order_no",
    "siparis_numarasi": "order_no",
    "alici_adi": "buyer_name",
    "alici_ismi": "buyer_name",
    "musteri_adi": "buyer_name",
    "urun_adi": "product_name",
    "urun": "product_name",
    "model_no": "model_no",
    "model_numarasi": "model_no",
    "sablon_no": "template_no",
    "sablon_numarasi": "template_no",
    "islem_tipi": "process_type",
    "uretim_tipi": "process_type",
    "kisisellestirme_turu": "personalization_type",
    "etiket_varyanti": "label_variant",
    "etiket_rengi": "label_variant",
    "etiket_yazisi": "label_text",
    "etiket_metni": "label_text",
    "tarih_yazisi": "date_text",
    "tarih_metni": "date_text",
    "not_yazisi": "note_text",
    "not_metni": "note_text",
    "ozel_metin_1": "custom_text_1",
    "ozel_yazi_1": "custom_text_1",
    "ozel_metin_2": "custom_text_2",
    "ozel_yazi_2": "custom_text_2",
    "ozel_metin_3": "custom_text_3",
    "ozel_yazi_3": "custom_text_3",
    "lazer_yazisi": "laser_text",
    "lazer_metni": "laser_text",
    "adet": "quantity",
    "miktar": "quantity",
    "malzeme_turu": "material_type",
    "malzeme": "material_type",
    "malzeme_kalinligi_mm": "material_thickness_mm",
    "malzeme_kalinligi": "material_thickness_mm",
    "ekstra_cikolata_adedi": "extra_chocolate_qty",
    "ekstra_cikolata": "extra_chocolate_qty",
    "ekstra_madlen_adedi": "extra_madlen_qty",
    "ekstra_madlen": "extra_madlen_qty",
    "uretim_notu": "production_note",
    "not": "production_note",
    "kontrol_gerekli": "needs_review",
    "inceleme_gerekli": "needs_review",
    "durum": "status",
}


def read_orders_excel(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    dataframe = pd.read_excel(path, dtype=object, engine="openpyxl")
    dataframe.columns = [_canonical_column_name(column) for column in dataframe.columns]
    return dataframe


def _canonical_column_name(value: object) -> str:
    normalized = _normalize_column_name(value)
    return TURKISH_COLUMN_ALIASES.get(normalized, normalized)


def _normalize_column_name(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.strip().lower()
    text = _replace_turkish_characters(text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def _replace_turkish_characters(value: str) -> str:
    replacements = str.maketrans(
        {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
        }
    )
    return value.replace("İ", "i").replace("i̇", "i").translate(replacements)
