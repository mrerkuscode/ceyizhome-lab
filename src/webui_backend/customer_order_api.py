from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any


ORDER_FIELDS = [
    "customer_name",
    "phone",
    "event_date",
    "note_text",
    "model_path",
    "model_name",
    "quantity",
    "delivery_date",
    "payment_status",
    "production_status",
    "source",
    "trendyol_order_number",
    "trendyol_package_id",
    "trendyol_line_id",
    "trendyol_barcode",
    "trendyol_merchant_sku",
    "trendyol_question_text",
    "trendyol_source_evidence",
]


def orders_path(project_root: Path) -> Path:
    path = project_root / "data" / "customer_orders.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def list_customer_orders(project_root: Path) -> list[dict[str, Any]]:
    path = orders_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def save_customer_orders(project_root: Path, rows: list[dict[str, Any]]) -> None:
    orders_path(project_root).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def create_customer_order(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    rows = list_customer_orders(project_root)
    order = _normalize_order_payload(payload)
    order["id"] = uuid.uuid4().hex
    order["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order["updated_at"] = order["created_at"]
    rows.insert(0, order)
    save_customer_orders(project_root, rows)
    return {"status": "OK", "message": "Sipariş kaydedildi.", "order": order}


def update_customer_order_status(project_root: Path, order_id: str, status: str) -> dict[str, Any]:
    rows = list_customer_orders(project_root)
    for row in rows:
        if row.get("id") == order_id:
            row["production_status"] = str(status or "Yeni")
            row["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_customer_orders(project_root, rows)
            return {"status": "OK", "message": "Sipariş durumu güncellendi.", "order": row}
    return {"status": "MISSING", "message": "Sipariş bulunamadı."}


def create_order_summary_pdf(project_root: Path, order_id: str) -> dict[str, Any]:
    order = next((row for row in list_customer_orders(project_root) if row.get("id") == order_id), None)
    if not order:
        return {"status": "MISSING", "message": "Sipariş bulunamadı."}
    output_dir = project_root / "output" / date.today().isoformat() / "orders"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(order.get("customer_name") or "siparis")
    pdf_path = output_dir / f"is_emri_{safe_name}_{order_id[:8]}.pdf"
    manifest_path = pdf_path.with_suffix(".json")
    lines = [
        "Cyzella Production Studio - Is Emri",
        f"Siparis ID: {order_id[:8]}",
        f"Musteri: {order.get('customer_name', '')}",
        f"Telefon: {order.get('phone', '')}",
        f"Etkinlik Tarihi: {order.get('event_date', '')}",
        f"Teslim Tarihi: {order.get('delivery_date', '')}",
        f"Model: {order.get('model_name', '')}",
        f"Adet: {order.get('quantity', '')}",
        f"Odeme/Kapora: {order.get('payment_status', '')}",
        f"Uretim Durumu: {order.get('production_status', '')}",
        f"Not: {order.get('note_text', '')}",
        "",
        "Güvenlik: Bu PDF sadece iş emri özetidir. Yazıcı veya lazer otomatik çalışmaz.",
    ]
    _write_simple_pdf(pdf_path, lines)
    manifest_path.write_text(json.dumps({"order": order, "pdf": _relative(project_root, pdf_path)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "OK",
        "message": "İş emri PDF'i oluşturuldu.",
        "relative_path": _relative(project_root, pdf_path),
        "manifest_path": _relative(project_root, manifest_path),
    }


def _normalize_order_payload(payload: dict[str, Any]) -> dict[str, Any]:
    order = {field: str(payload.get(field) or "").strip() for field in ORDER_FIELDS}
    order["quantity"] = str(max(1, _safe_int(order.get("quantity"), 1)))
    order["payment_status"] = order["payment_status"] or "Belirtilmedi"
    order["production_status"] = order["production_status"] or "Yeni"
    return order


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return default


def _safe_filename(value: object) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip())
    return text.strip("_")[:48] or "siparis"


def _relative(project_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _write_simple_pdf(path: Path, lines: list[str]) -> None:
    content = ["BT", "/F1 13 Tf", "50 790 Td"]
    first = True
    for line in lines:
        if not first:
            content.append("0 -22 Td")
        first = False
        content.append(f"({_pdf_escape(_ascii_pdf_text(line))}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode("ascii"))
        data.extend(obj)
        data.extend(b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    data.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    path.write_bytes(bytes(data))


def _ascii_pdf_text(value: str) -> str:
    return (
        str(value)
        .replace("ğ", "g").replace("Ğ", "G")
        .replace("ü", "u").replace("Ü", "U")
        .replace("ş", "s").replace("Ş", "S")
        .replace("ı", "i").replace("İ", "I")
        .replace("ö", "o").replace("Ö", "O")
        .replace("ç", "c").replace("Ç", "C")
    )


def _pdf_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
