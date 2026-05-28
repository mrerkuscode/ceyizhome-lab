from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .diagnostics import detect_illustrator
from .job_runner import prepare_input_copy, sha256_file
from .manifest import add_error, add_warning, create_manifest, save_manifest, text_object


def _bounds_from_geometric(raw: Any) -> dict[str, float]:
    try:
        left, top, right, bottom = [float(value) for value in list(raw)]
        return {"x": left, "y": top, "width": abs(right - left), "height": abs(top - bottom)}
    except Exception:
        return {"x": 0, "y": 0, "width": 0, "height": 0}


def _engine_missing_result(prepared: dict[str, Any], manifest: dict[str, Any], message: str, warnings: list[str]) -> dict[str, Any]:
    add_warning(manifest, message)
    for warning in warnings:
        add_warning(manifest, warning)
    manifest_path = save_manifest(manifest, prepared["job_dir"] / "manifest_ai.json")
    source_hash_after = sha256_file(prepared["source"])
    return {
        "status": "ENGINE_MISSING",
        "message": message,
        "source_path": str(prepared["source"]),
        "input_copy_path": str(prepared["input_copy"]),
        "source_unchanged": source_hash_after == prepared["source_hash_before"],
        "text_frames_count": 0,
        "manifest_path": str(manifest_path),
        "edited_ai_path": "",
        "preview_png_path": "",
        "export_pdf_path": "",
        "warnings": manifest["warnings"],
        "errors": manifest["errors"],
    }


def run_ai_poc(project_root: str | Path, source_ai_path: str | Path, *, edit: bool = True, allow_engine: bool = True) -> dict[str, Any]:
    prepared = prepare_input_copy(project_root, source_ai_path, "ai")
    manifest = create_manifest(prepared["source"], "ai", "illustrator", prepared["job_id"])

    if not allow_engine:
        return _engine_missing_result(
            prepared,
            manifest,
            "Illustrator otomasyonu test modunda bilinçli olarak çalıştırılmadı.",
            ["Birim testleri dış uygulama açmadan güvenli şekilde geçer."],
        )

    diagnostic = detect_illustrator(allow_launch=False)
    if diagnostic["status"] == "ENGINE_MISSING":
        return _engine_missing_result(prepared, manifest, "Illustrator bulunamadı.", diagnostic.get("details", []))

    doc = None
    app = None
    try:
        import win32com.client  # type: ignore[import-not-found]

        app = win32com.client.DispatchEx("Illustrator.Application")
        try:
            app.Visible = False
        except Exception:
            pass
        doc = app.Open(str(prepared["input_copy"]))
        text_frames = getattr(doc, "TextFrames", None)
        count = int(getattr(text_frames, "Count", 0) or 0)
        for index in range(1, count + 1):
            frame = text_frames.Item(index)
            current_text = str(getattr(frame, "Contents", "") or "")
            manifest["objects"].append(
                text_object(
                    f"text_{index - 1}",
                    f"textFrames[{index - 1}]",
                    current_text,
                    name=str(getattr(frame, "Name", "") or f"Text {index}"),
                    bounds=_bounds_from_geometric(getattr(frame, "GeometricBounds", None)),
                    extra={
                        "typename": str(getattr(frame, "typename", "") or "TextFrame"),
                        "kind": str(getattr(frame, "Kind", "") or ""),
                        "visible": not bool(getattr(frame, "Hidden", False)),
                        "locked": bool(getattr(frame, "Locked", False)),
                    },
                )
            )

        if not manifest["objects"]:
            add_warning(manifest, "Bu AI dosyasında düzenlenebilir text frame bulunamadı. Yazılar outline/path olabilir.")
            manifest_path = save_manifest(manifest, prepared["job_dir"] / "manifest_ai.json")
            return {
                "status": "NO_EDITABLE_TEXT_FOUND",
                "message": "AI dosyasında düzenlenebilir yazı bulunamadı.",
                "source_path": str(prepared["source"]),
                "input_copy_path": str(prepared["input_copy"]),
                "source_unchanged": sha256_file(prepared["source"]) == prepared["source_hash_before"],
                "text_frames_count": 0,
                "manifest_path": str(manifest_path),
                "edited_ai_path": "",
                "preview_png_path": "",
                "export_pdf_path": "",
                "warnings": manifest["warnings"],
                "errors": manifest["errors"],
            }

        if edit:
            first = text_frames.Item(1)
            try:
                first.Contents = "Ayşe & Mehmet"
            except Exception as exc:  # noqa: BLE001
                add_error(manifest, f"İlk text frame değiştirilemedi: {exc}")
        edited_ai = prepared["job_dir"] / "edited.ai"
        shutil.copy2(prepared["input_copy"], edited_ai)
        try:
            doc.SaveAs(str(edited_ai))
        except Exception as exc:  # noqa: BLE001
            add_warning(manifest, f"edited.ai kaydı Illustrator tarafından yapılamadı: {exc}")

        pdf_path = prepared["job_dir"] / "export.pdf"
        png_path = prepared["job_dir"] / "preview.png"
        try:
            doc.SaveAs(str(pdf_path))
        except Exception as exc:  # noqa: BLE001
            add_warning(manifest, f"PDF export alınamadı: {exc}")
        try:
            options = win32com.client.Dispatch("Illustrator.ExportOptionsPNG24")
            doc.Export(str(png_path), 5, options)
        except Exception as exc:  # noqa: BLE001
            add_warning(manifest, f"PNG preview export alınamadı: {exc}")

        manifest_path = save_manifest(manifest, prepared["job_dir"] / "manifest_ai.json")
        source_unchanged = sha256_file(prepared["source"]) == prepared["source_hash_before"]
        status = "PASSED" if edited_ai.exists() and (pdf_path.exists() or png_path.exists()) and not manifest["errors"] else "PARTIAL"
        return {
            "status": status,
            "message": "Test düzenleme kopya dosyada tamamlandı." if status == "PASSED" else "Test kısmen tamamlandı.",
            "source_path": str(prepared["source"]),
            "input_copy_path": str(prepared["input_copy"]),
            "source_unchanged": source_unchanged,
            "text_frames_count": len(manifest["objects"]),
            "manifest_path": str(manifest_path),
            "edited_ai_path": str(edited_ai) if edited_ai.exists() else "",
            "preview_png_path": str(png_path) if png_path.exists() else "",
            "export_pdf_path": str(pdf_path) if pdf_path.exists() else "",
            "warnings": manifest["warnings"],
            "errors": manifest["errors"],
        }
    except Exception as exc:  # noqa: BLE001
        add_error(manifest, f"Illustrator açıldı ancak dosya işlenemedi: {exc}")
        manifest_path = save_manifest(manifest, prepared["job_dir"] / "manifest_ai.json")
        return {
            "status": "FAILED",
            "message": "Illustrator açıldı ancak dosya işlenemedi.",
            "source_path": str(prepared["source"]),
            "input_copy_path": str(prepared["input_copy"]),
            "source_unchanged": sha256_file(prepared["source"]) == prepared["source_hash_before"],
            "text_frames_count": len(manifest["objects"]),
            "manifest_path": str(manifest_path),
            "edited_ai_path": "",
            "preview_png_path": "",
            "export_pdf_path": "",
            "warnings": manifest["warnings"],
            "errors": manifest["errors"],
        }
    finally:
        if doc is not None:
            try:
                doc.Close(2)
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
