from __future__ import annotations

import re
from pathlib import Path


def strip_paths(text: str) -> str:
    return re.sub(r"[A-Za-z]:\\[^\n\r,;]+", lambda match: Path(match.group(0)).name, text).replace("\\", "/")


def friendly_error(row: dict[str, str]) -> dict[str, str]:
    message = " ".join(str(value) for value in row.values() if value).strip()
    lower = message.lower()
    order_no = row.get("order_no") or row.get("Sipariş") or ""
    row_no = row.get("row_number") or row.get("row") or row.get("Satır") or ""
    if "connected script font missing" in lower or "connected_script.ttf" in lower:
        title = "Lazer kesim fontu eksik."
        desc = "assets/fonts/connected_script.ttf dosyasını ekleyin. Font yokken LASER_CUT güvenlik için bloke edilir."
    elif "label_text" in lower:
        title = "Etiket yazısı eksik."
        desc = "Excel’de label_text kolonunu doldurun."
    elif "laser_text" in lower:
        title = "Lazer yazısı eksik."
        desc = "Excel’de laser_text kolonunu doldurun."
    elif "template" in lower:
        title = "Etiket şablonu bulunamadı."
        desc = "Model, şablon ve varyant bilgisini veya templates/designs klasörünü kontrol edin."
    elif "quantity" in lower:
        title = "Adet değeri geçersiz."
        desc = "Excel’de quantity alanına pozitif sayı girin."
    elif "process_type" in lower:
        title = "İşlem tipi geçersiz."
        desc = "process_type alanını PRINT, LASER_ENGRAVE, LASER_CUT, BOTH veya NONE yapın."
    else:
        title = strip_paths(message)[:90] or "Kontrol hatası."
        desc = "Detayları Raporlar > Günlük veya errors_report.csv içinde inceleyin."
    if order_no:
        title = f"Sipariş {order_no}: {title}"
    return {"title": title, "desc": desc, "row": f"Satır: {row_no}" if row_no else ""}
