import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from . import print_queue_api


ALLOWED_FORMATS = {"PDF", "PNG", "SVG", "DXF", "PLT"}


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def profiles_path(project_root: Path) -> Path:
    path = project_root / "data" / "printer_profiles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _clean_text(value: object, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _normalize_formats(value: object) -> list[str]:
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        raw_items = [str(item).strip() for item in value]
    else:
        raw_items = []
    formats = []
    for item in raw_items:
        normalized = item.upper().lstrip(".")
        if normalized in ALLOWED_FORMATS and normalized not in formats:
            formats.append(normalized)
    return formats or ["PDF"]


def normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    now = _now_text()
    copies_raw = profile.get("copies_default", 1)
    try:
        copies_default = max(1, int(float(str(copies_raw).replace(",", "."))))
    except ValueError:
        copies_default = 1
    normalized = {
        "printer_profile_id": _clean_text(profile.get("printer_profile_id")) or uuid.uuid4().hex,
        "profile_name": _clean_text(profile.get("profile_name"), "Manuel PDF Kontrol Profili"),
        "printer_name": _clean_text(profile.get("printer_name"), "Manuel PDF kontrolü"),
        "paper_size": _clean_text(profile.get("paper_size"), "A4"),
        "label_size": _clean_text(profile.get("label_size"), "50 x 30 mm"),
        "orientation": _clean_text(profile.get("orientation"), "portrait"),
        "margin": _clean_text(profile.get("margin"), "0 mm"),
        "copies_default": copies_default,
        "output_format_allowed": _normalize_formats(profile.get("output_format_allowed")),
        "is_default": bool(profile.get("is_default")),
        "created_at": _clean_text(profile.get("created_at"), now),
        "updated_at": now,
    }
    return normalized


def list_printer_profiles(project_root: Path) -> list[dict[str, Any]]:
    path = profiles_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    profiles = [normalize_profile(row) for row in data if isinstance(row, dict)]
    default_seen = False
    for profile in profiles:
        if profile.get("is_default") and not default_seen:
            default_seen = True
        elif profile.get("is_default"):
            profile["is_default"] = False
    return profiles


def save_printer_profiles(project_root: Path, profiles: list[dict[str, Any]]) -> None:
    profiles_path(project_root).write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")


def save_printer_profile(project_root: Path, profile: dict[str, Any]) -> dict[str, Any]:
    profiles = list_printer_profiles(project_root)
    normalized = normalize_profile(profile)
    if normalized.get("is_default"):
        for row in profiles:
            row["is_default"] = False
    replaced = False
    for index, row in enumerate(profiles):
        if row.get("printer_profile_id") == normalized["printer_profile_id"]:
            normalized["created_at"] = row.get("created_at") or normalized["created_at"]
            profiles[index] = normalized
            replaced = True
            break
    if not replaced:
        profiles.append(normalized)
    if profiles and not any(row.get("is_default") for row in profiles):
        profiles[0]["is_default"] = True
    save_printer_profiles(project_root, profiles)
    return {"status": "OK", "message": "Yazıcı profili kaydedildi. Cihaz otomatik tetiklenmedi.", "profile": normalized, "profiles": profiles}


def delete_printer_profile(project_root: Path, profile_id: str) -> dict[str, Any]:
    profiles = list_printer_profiles(project_root)
    remaining = [row for row in profiles if row.get("printer_profile_id") != profile_id]
    if len(remaining) == len(profiles):
        return {"status": "MISSING", "message": "Yazıcı profili bulunamadı.", "profiles": profiles}
    if remaining and not any(row.get("is_default") for row in remaining):
        remaining[0]["is_default"] = True
    save_printer_profiles(project_root, remaining)
    return {"status": "OK", "message": "Yazıcı profili silindi. Cihaz otomatik tetiklenmedi.", "profiles": remaining}


def set_default_printer_profile(project_root: Path, profile_id: str) -> dict[str, Any]:
    profiles = list_printer_profiles(project_root)
    found = False
    for row in profiles:
        row["is_default"] = row.get("printer_profile_id") == profile_id
        found = found or row["is_default"]
    if not found:
        return {"status": "MISSING", "message": "Varsayılan yapılacak profil bulunamadı.", "profiles": profiles}
    save_printer_profiles(project_root, profiles)
    return {"status": "OK", "message": "Varsayılan yazıcı profili seçildi. Yazıcı otomatik çalışmaz.", "profiles": profiles}


def default_printer_profile(project_root: Path) -> dict[str, Any] | None:
    profiles = list_printer_profiles(project_root)
    return next((row for row in profiles if row.get("is_default")), None)


def test_printer_profile(project_root: Path, profile_id: str) -> dict[str, Any]:
    profile = next((row for row in list_printer_profiles(project_root) if row.get("printer_profile_id") == profile_id), None)
    if not profile:
        return {"status": "MISSING", "message": "Test edilecek yazıcı profili bulunamadı."}
    return {
        "status": "UNSUPPORTED",
        "message": "Cihaz bağlantı testi bu fazda pasif. Yazıcı otomatik tetiklenmedi.",
        "profile": profile,
        "auto_print_started": False,
    }


def _format_for_queue_item(item: dict[str, Any]) -> str:
    path = str(item.get("relative_path") or item.get("output_path") or "")
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix:
        return suffix.upper()
    return str(item.get("output_format") or "PDF").upper()


def prepare_manual_print(project_root: Path, item_id: str, profile_id: str) -> dict[str, Any]:
    if not profile_id:
        return {"status": "PROFILE_REQUIRED", "message": "Manuel print hazırlığı için yazıcı profili seçin.", "auto_print_started": False}
    profiles = list_printer_profiles(project_root)
    profile = next((row for row in profiles if row.get("printer_profile_id") == profile_id), None)
    if not profile:
        return {"status": "PROFILE_REQUIRED", "message": "Seçili yazıcı profili bulunamadı.", "auto_print_started": False}
    rows = print_queue_api.list_print_queue(project_root)
    for row in rows:
        if row.get("id") != item_id:
            continue
        relative_path = str(row.get("relative_path") or row.get("output_path") or "")
        output_path = print_queue_api._resolve_project_path(project_root, relative_path)  # noqa: SLF001
        flags = row.get("safety_flags") if isinstance(row.get("safety_flags"), list) else []
        if row.get("status_key") != "ready_to_print":
            return {"status": "NOT_READY", "message": "Kayıt ready_to_print durumunda değil; manuel print hazırlığı tamamlanmadı.", "item": row, "profile": profile, "auto_print_started": False}
        if flags:
            return {"status": "BLOCKED", "message": "Güvenlik bayrakları temizlenmeden print hazırlığı yapılamaz.", "safety_flags": flags, "item": row, "profile": profile, "auto_print_started": False}
        if not relative_path or not output_path.exists():
            return {"status": "OUTPUT_MISSING", "message": "Çıktı dosyası bulunamadı. Yazdırmaya hazır değil.", "item": row, "profile": profile, "auto_print_started": False}
        output_format = _format_for_queue_item(row)
        if output_format not in set(profile.get("output_format_allowed") or []):
            return {"status": "FORMAT_BLOCKED", "message": f"{output_format} bu yazıcı profilinde izinli değil.", "item": row, "profile": profile, "auto_print_started": False}
        try:
            quantity = int(float(str(row.get("quantity") or "1").replace(",", ".")))
        except ValueError:
            quantity = 0
        if quantity <= 0:
            return {"status": "INVALID_QUANTITY", "message": "Adet geçersiz. Manuel print hazırlığı yapılmadı.", "item": row, "profile": profile, "auto_print_started": False}
        row["printer_profile_id"] = profile["printer_profile_id"]
        row["printer_profile_name"] = profile["profile_name"]
        row["manual_print_prepared_at"] = _now_text()
        row["updated_at"] = row["manual_print_prepared_at"]
        print_queue_api.append_queue_history(row, "manual_print_prepared", "ready_to_print", "Manuel print hazırlığı tamamlandı; yazıcı otomatik başlamadı.")
        print_queue_api.save_print_queue(project_root, rows)
        return {
            "status": "OK",
            "message": "Manuel print hazırlığı tamamlandı. Dosya kontrol için açılabilir; yazıcı otomatik başlamadı.",
            "item": row,
            "profile": profile,
            "relative_path": relative_path,
            "auto_print_started": False,
            "laser_started": False,
            "rdworks_started": False,
        }
    return {"status": "MISSING", "message": "Yazdırma sırasında bu iş bulunamadı.", "auto_print_started": False}
