from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


RISKY_ACTIONS: dict[str, dict[str, Any]] = {
    "trendyol_status_update": {
        "label": "Trendyol statü güncelleme",
        "category": "Trendyol",
        "default_disabled": True,
        "dry_run_only": True,
        "requires_admin": True,
        "requires_operator_confirmation": True,
        "audit_required": True,
        "rollback_possible": False,
        "would_do": "Trendyol sipariş statüsü canlı marketplace üzerinde değiştirilecekti.",
    },
    "trendyol_shipping_label": {
        "label": "Trendyol kargo etiketi",
        "category": "Trendyol",
        "default_disabled": True,
        "dry_run_only": True,
        "requires_admin": True,
        "requires_operator_confirmation": True,
        "audit_required": True,
        "rollback_possible": False,
        "would_do": "Trendyol kargo etiketi canlı sistemden alınacaktı.",
    },
    "trendyol_invoice": {
        "label": "Trendyol fatura",
        "category": "Trendyol",
        "default_disabled": True,
        "dry_run_only": True,
        "requires_admin": True,
        "requires_operator_confirmation": True,
        "audit_required": True,
        "rollback_possible": False,
        "would_do": "Trendyol fatura/finans işlemi canlı sistemde tetiklenecekti.",
    },
    "direct_print": {
        "label": "Direct print",
        "category": "Yazıcı",
        "default_disabled": True,
        "dry_run_only": True,
        "requires_admin": True,
        "requires_operator_confirmation": True,
        "audit_required": True,
        "rollback_possible": False,
        "would_do": "Seçili yazıcıya doğrudan baskı işi gönderilecekti.",
    },
    "laser_send": {
        "label": "Lazer otomatik gönderim",
        "category": "Lazer",
        "default_disabled": True,
        "dry_run_only": True,
        "requires_admin": True,
        "requires_operator_confirmation": True,
        "audit_required": True,
        "rollback_possible": False,
        "would_do": "Hazırlanan kesim dosyası lazer cihazına gönderilecekti.",
    },
    "rdworks_open_or_send": {
        "label": "RDWorks aç/gönder",
        "category": "RDWorks",
        "default_disabled": True,
        "dry_run_only": True,
        "requires_admin": True,
        "requires_operator_confirmation": True,
        "audit_required": True,
        "rollback_possible": False,
        "would_do": "RDWorks otomatik açılacak veya kesim dosyası RDWorks'e gönderilecekti.",
    },
}


DEFAULT_SETTINGS: dict[str, Any] = {
    "live_trendyol_actions_enabled": False,
    "direct_print_enabled": False,
    "laser_rdworks_auto_send_enabled": False,
    "dry_run_only": True,
    "admin_approval_required": True,
    "operator_confirmation_required": True,
    "updated_at": "",
}


def _settings_path(project_root: Path) -> Path:
    path = project_root / "data" / "live_integration_security.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def list_risky_actions() -> dict[str, dict[str, Any]]:
    return {key: dict(value, action_key=key) for key, value in RISKY_ACTIONS.items()}


def load_security_settings(project_root: Path) -> dict[str, Any]:
    path = _settings_path(project_root)
    if not path.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DEFAULT_SETTINGS.copy() | {"status": "ERROR", "message": "Entegrasyon güvenliği ayarı okunamadı."}
    if not isinstance(data, dict):
        return DEFAULT_SETTINGS.copy()
    settings = DEFAULT_SETTINGS.copy()
    settings.update({k: data.get(k) for k in DEFAULT_SETTINGS if k in data})
    # Phase 25 is infrastructure only: risky live channels stay locked.
    settings["live_trendyol_actions_enabled"] = False
    settings["direct_print_enabled"] = False
    settings["laser_rdworks_auto_send_enabled"] = False
    settings["dry_run_only"] = True
    settings["admin_approval_required"] = True
    settings["operator_confirmation_required"] = True
    return settings


def save_security_settings(project_root: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = load_security_settings(project_root)
    payload = payload or {}
    settings.update({k: payload.get(k) for k in DEFAULT_SETTINGS if k in payload})
    settings["live_trendyol_actions_enabled"] = False
    settings["direct_print_enabled"] = False
    settings["laser_rdworks_auto_send_enabled"] = False
    settings["dry_run_only"] = True
    settings["admin_approval_required"] = True
    settings["operator_confirmation_required"] = True
    settings["updated_at"] = _now_text()
    _settings_path(project_root).write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "OK",
        "message": "Entegrasyon güvenliği ayarı kaydedildi. Canlı aksiyonlar kapalı, dry-run modu açık kaldı.",
        "settings": settings,
    }


def evaluate_action(
    project_root: Path,
    action_key: str,
    payload: dict[str, Any] | None = None,
    *,
    admin_confirmed: bool = False,
    operator_confirmed: bool = False,
    dry_run: bool = True,
) -> dict[str, Any]:
    registry = list_risky_actions()
    action = registry.get(action_key)
    payload = payload or {}
    settings = load_security_settings(project_root)
    base = {
        "action_key": action_key,
        "payload": payload,
        "settings": settings,
        "live_trendyol_changed": False,
        "shipping_label_created": False,
        "invoice_created": False,
        "auto_print_started": False,
        "laser_started": False,
        "rdworks_started": False,
        "live_action_performed": False,
        "audit_required": True,
        "created_at": _now_text(),
    }
    if not action:
        return {
            **base,
            "status": "NOT_CONFIGURED",
            "severity": "warning",
            "event_type": "integration_not_configured",
            "message": "Bu riskli entegrasyon aksiyonu kayıtlı değil; canlı işlem yapılmadı.",
        }
    base.update(action)
    if action.get("requires_operator_confirmation") and not operator_confirmed:
        return {
            **base,
            "status": "PERMISSION_REQUIRED",
            "severity": "warning",
            "event_type": "integration_permission_required",
            "message": "Operatör onayı gerekli. Canlı işlem yapılmadı.",
        }
    if action.get("requires_admin") and not admin_confirmed:
        return {
            **base,
            "status": "PERMISSION_REQUIRED",
            "severity": "warning",
            "event_type": "integration_permission_required",
            "message": "Yönetici onayı gerekli. Canlı işlem yapılmadı.",
        }
    if not dry_run:
        return {
            **base,
            "status": "BLOCKED",
            "severity": "blocked",
            "event_type": "integration_action_blocked",
            "message": "Canlı entegrasyon bu fazda kapalı. Dry-run dışı çağrı engellendi.",
        }
    return {
        **base,
        "status": "DRY_RUN",
        "severity": "info",
        "event_type": "integration_dry_run_completed",
        "message": "Dry-run tamamlandı. Canlı Trendyol, yazıcı, lazer veya RDWorks işlemi yapılmadı.",
    }
