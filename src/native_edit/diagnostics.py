from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from typing import Any


def _pywin32_available() -> tuple[bool, str]:
    try:
        available = importlib.util.find_spec("win32com.client") is not None
    except ModuleNotFoundError:
        available = False
    if not available:
        return False, "pywin32 bulunamadı; COM otomasyonu kullanılamıyor."
    return True, "pywin32 bulundu; COM otomasyonu için Python tarafı hazır."


def _progid_registered(progid: str) -> tuple[bool, str]:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid):
            return True, f"{progid} registry kaydı bulundu."
    except FileNotFoundError:
        return False, f"{progid} registry kaydı bulunamadı."
    except Exception as exc:  # noqa: BLE001
        return False, f"{progid} registry kontrolü başarısız: {exc}"


def detect_illustrator(*, allow_launch: bool = False) -> dict[str, Any]:
    pywin32_ok, pywin32_message = _pywin32_available()
    result: dict[str, Any] = {
        "engine": "illustrator",
        "found": False,
        "automation_available": False,
        "launch_tested": False,
        "status": "ENGINE_MISSING",
        "message": "Illustrator bulunamadı veya güvenli şekilde doğrulanamadı.",
        "details": [pywin32_message],
    }
    if not pywin32_ok:
        return result
    registered, registry_message = _progid_registered("Illustrator.Application")
    result["details"].append(registry_message)
    result["found"] = registered
    if not allow_launch:
        status = "AVAILABLE_NOT_LAUNCHED" if registered else "ENGINE_MISSING"
        message = (
            "Illustrator registry kaydı bulundu; uygulama açma testi güvenli modda otomatik yapılmadı."
            if registered
            else "Illustrator kurulu değil veya COM registry kaydı yok."
        )
        result.update(
            {
                "status": status,
                "message": message,
                "details": result["details"] + ["UI'daki PoC butonu çalıştırılırsa test kopya dosya üzerinde denenir."],
            }
        )
        return result
    try:
        import win32com.client  # type: ignore[import-not-found]

        app = win32com.client.DispatchEx("Illustrator.Application")
        result.update(
            {
                "found": True,
                "automation_available": True,
                "launch_tested": True,
                "status": "PASSED",
                "message": "Illustrator COM otomasyonu oluşturulabildi.",
            }
        )
        try:
            app.Quit()
        except Exception:
            pass
    except Exception as exc:  # noqa: BLE001
        result.update(
            {
                "launch_tested": True,
                "status": "ENGINE_MISSING",
                "message": "Illustrator açılamadı veya COM otomasyonu oluşturulamadı.",
                "details": result["details"] + [str(exc)],
            }
        )
    return result


def detect_coreldraw(*, allow_launch: bool = False) -> dict[str, Any]:
    pywin32_ok, pywin32_message = _pywin32_available()
    result: dict[str, Any] = {
        "engine": "coreldraw",
        "found": False,
        "automation_available": False,
        "launch_tested": False,
        "status": "ENGINE_MISSING",
        "message": "CorelDRAW bulunamadı veya güvenli şekilde doğrulanamadı.",
        "details": [pywin32_message],
    }
    if not pywin32_ok:
        return result
    registered, registry_message = _progid_registered("CorelDRAW.Application")
    result["details"].append(registry_message)
    result["found"] = registered
    if not allow_launch:
        status = "AVAILABLE_NOT_LAUNCHED" if registered else "ENGINE_MISSING"
        message = (
            "CorelDRAW registry kaydı bulundu; uygulama açma testi güvenli modda otomatik yapılmadı."
            if registered
            else "CorelDRAW kurulu değil veya COM registry kaydı yok."
        )
        result.update(
            {
                "status": status,
                "message": message,
                "details": result["details"] + ["UI'daki PoC butonu çalıştırılırsa test kopya dosya üzerinde denenir."],
            }
        )
        return result
    try:
        import win32com.client  # type: ignore[import-not-found]

        app = win32com.client.DispatchEx("CorelDRAW.Application")
        result.update(
            {
                "found": True,
                "automation_available": True,
                "launch_tested": True,
                "status": "PASSED",
                "message": "CorelDRAW COM otomasyonu oluşturulabildi.",
            }
        )
        try:
            app.Quit()
        except Exception:
            pass
    except Exception as exc:  # noqa: BLE001
        result.update(
            {
                "launch_tested": True,
                "status": "ENGINE_MISSING",
                "message": "CorelDRAW açılamadı veya COM otomasyonu oluşturulamadı.",
                "details": result["details"] + [str(exc)],
            }
        )
    return result


def detect_preview_tools() -> dict[str, Any]:
    tools = {
        "pymupdf": importlib.util.find_spec("fitz") is not None,
        "ghostscript": bool(shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")),
        "inkscape": bool(shutil.which("inkscape")),
        "libreoffice": bool(shutil.which("soffice") or shutil.which("libreoffice")),
        "poppler_pdftocairo": bool(shutil.which("pdftocairo")),
    }
    return {
        "status": "PASSED" if any(tools.values()) else "PARTIAL",
        "tools": tools,
        "message": "Önizleme dönüştürme araçları kontrol edildi.",
    }


def run_diagnostics(project_root: str | Path, *, allow_launch: bool = False) -> dict[str, Any]:
    return {
        "project_root": str(Path(project_root)),
        "illustrator": detect_illustrator(allow_launch=allow_launch),
        "coreldraw": detect_coreldraw(allow_launch=allow_launch),
        "preview_tools": detect_preview_tools(),
    }
