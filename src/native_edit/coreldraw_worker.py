from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .diagnostics import detect_coreldraw
from .job_runner import prepare_input_copy, sha256_file
from .manifest import add_error, add_warning, create_manifest, save_manifest, text_object


def _engine_missing_result(prepared: dict[str, Any], manifest: dict[str, Any], message: str, warnings: list[str]) -> dict[str, Any]:
    add_warning(manifest, message)
    for warning in warnings:
        add_warning(manifest, warning)
    manifest_path = save_manifest(manifest, prepared["job_dir"] / "manifest_cdr.json")
    return {
        "status": "ENGINE_MISSING",
        "message": message,
        "source_path": str(prepared["source"]),
        "input_copy_path": str(prepared["input_copy"]),
        "source_unchanged": sha256_file(prepared["source"]) == prepared["source_hash_before"],
        "text_shapes_count": 0,
        "manifest_path": str(manifest_path),
        "edited_cdr_path": "",
        "preview_png_path": "",
        "export_pdf_path": "",
        "warnings": manifest["warnings"],
        "errors": manifest["errors"],
    }


def _shape_text(shape: Any) -> str:
    try:
        return str(shape.Text.Story.Text or "")
    except Exception:
        return ""


def _shape_bounds(shape: Any) -> dict[str, float]:
    try:
        return {
            "x": float(shape.LeftX),
            "y": float(shape.TopY),
            "width": float(shape.SizeWidth),
            "height": float(shape.SizeHeight),
        }
    except Exception:
        return {"x": 0, "y": 0, "width": 0, "height": 0}


def _walk_shapes(shapes: Any) -> list[Any]:
    found: list[Any] = []
    try:
        count = int(getattr(shapes, "Count", 0) or 0)
    except Exception:
        count = 0
    for index in range(1, count + 1):
        try:
            shape = shapes.Item(index)
            found.append(shape)
            if hasattr(shape, "Shapes"):
                found.extend(_walk_shapes(shape.Shapes))
        except Exception:
            continue
    return found


def run_cdr_poc(project_root: str | Path, source_cdr_path: str | Path, *, edit: bool = True, allow_engine: bool = True) -> dict[str, Any]:
    prepared = prepare_input_copy(project_root, source_cdr_path, "cdr")
    manifest = create_manifest(prepared["source"], "cdr", "coreldraw", prepared["job_id"])

    if not allow_engine:
        return _engine_missing_result(
            prepared,
            manifest,
            "CorelDRAW otomasyonu test modunda bilinçli olarak çalıştırılmadı.",
            ["Birim testleri dış uygulama açmadan güvenli şekilde geçer."],
        )

    diagnostic = detect_coreldraw(allow_launch=False)
    if diagnostic["status"] == "ENGINE_MISSING":
        return _engine_missing_result(prepared, manifest, "CorelDRAW bulunamadı.", diagnostic.get("details", []))

    doc = None
    app = None
    try:
        import win32com.client  # type: ignore[import-not-found]

        app = win32com.client.DispatchEx("CorelDRAW.Application")
        try:
            app.Visible = False
        except Exception:
            pass
        doc = app.OpenDocument(str(prepared["input_copy"]))
        text_shapes: list[Any] = []
        try:
            pages = doc.Pages
            page_count = int(getattr(pages, "Count", 0) or 0)
            for page_index in range(1, page_count + 1):
                page = pages.Item(page_index)
                for shape in _walk_shapes(page.Shapes):
                    current_text = _shape_text(shape)
                    if current_text:
                        text_shapes.append(shape)
                        manifest["objects"].append(
                            text_object(
                                f"text_{len(text_shapes) - 1}",
                                f"pages[{page_index - 1}].shapes",
                                current_text,
                                name=str(getattr(shape, "Name", "") or f"Text {len(text_shapes)}"),
                                bounds=_shape_bounds(shape),
                                extra={
                                    "page": page_index,
                                    "text_type": str(getattr(shape, "Type", "") or ""),
                                    "visible": bool(getattr(shape, "Visible", True)),
                                    "locked": bool(getattr(shape, "Locked", False)),
                                },
                            )
                        )
        except Exception as exc:  # noqa: BLE001
            add_warning(manifest, f"Text shape tarama kısmen başarısız: {exc}")

        if not text_shapes:
            add_warning(manifest, "Bu CDR dosyasında düzenlenebilir text shape bulunamadı. Yazılar curve/path olabilir.")
            manifest_path = save_manifest(manifest, prepared["job_dir"] / "manifest_cdr.json")
            return {
                "status": "NO_EDITABLE_TEXT_FOUND",
                "message": "CDR dosyasında düzenlenebilir yazı bulunamadı.",
                "source_path": str(prepared["source"]),
                "input_copy_path": str(prepared["input_copy"]),
                "source_unchanged": sha256_file(prepared["source"]) == prepared["source_hash_before"],
                "text_shapes_count": 0,
                "manifest_path": str(manifest_path),
                "edited_cdr_path": "",
                "preview_png_path": "",
                "export_pdf_path": "",
                "warnings": manifest["warnings"],
                "errors": manifest["errors"],
            }

        if edit:
            try:
                text_shapes[0].Text.Story.Text = "Ayşe & Mehmet"
            except Exception as exc:  # noqa: BLE001
                add_error(manifest, f"İlk text shape değiştirilemedi: {exc}")

        edited_cdr = prepared["job_dir"] / "edited.cdr"
        shutil.copy2(prepared["input_copy"], edited_cdr)
        try:
            doc.SaveAs(str(edited_cdr))
        except Exception as exc:  # noqa: BLE001
            add_warning(manifest, f"edited.cdr kaydı CorelDRAW tarafından yapılamadı: {exc}")

        pdf_path = prepared["job_dir"] / "export.pdf"
        png_path = prepared["job_dir"] / "preview.png"
        try:
            doc.PublishToPDF(str(pdf_path))
        except Exception as exc:  # noqa: BLE001
            add_warning(manifest, f"PDF export alınamadı: {exc}")
        try:
            doc.Export(str(png_path), 774, 1)
        except Exception as exc:  # noqa: BLE001
            add_warning(manifest, f"PNG preview export alınamadı: {exc}")

        manifest_path = save_manifest(manifest, prepared["job_dir"] / "manifest_cdr.json")
        status = "PASSED" if edited_cdr.exists() and (pdf_path.exists() or png_path.exists()) and not manifest["errors"] else "PARTIAL"
        return {
            "status": status,
            "message": "Test düzenleme kopya dosyada tamamlandı." if status == "PASSED" else "Test kısmen tamamlandı.",
            "source_path": str(prepared["source"]),
            "input_copy_path": str(prepared["input_copy"]),
            "source_unchanged": sha256_file(prepared["source"]) == prepared["source_hash_before"],
            "text_shapes_count": len(manifest["objects"]),
            "manifest_path": str(manifest_path),
            "edited_cdr_path": str(edited_cdr) if edited_cdr.exists() else "",
            "preview_png_path": str(png_path) if png_path.exists() else "",
            "export_pdf_path": str(pdf_path) if pdf_path.exists() else "",
            "warnings": manifest["warnings"],
            "errors": manifest["errors"],
        }
    except Exception as exc:  # noqa: BLE001
        add_error(manifest, f"CorelDRAW açıldı ancak dosya işlenemedi: {exc}")
        manifest_path = save_manifest(manifest, prepared["job_dir"] / "manifest_cdr.json")
        return {
            "status": "FAILED",
            "message": "CorelDRAW açıldı ancak dosya işlenemedi.",
            "source_path": str(prepared["source"]),
            "input_copy_path": str(prepared["input_copy"]),
            "source_unchanged": sha256_file(prepared["source"]) == prepared["source_hash_before"],
            "text_shapes_count": len(manifest["objects"]),
            "manifest_path": str(manifest_path),
            "edited_cdr_path": "",
            "preview_png_path": "",
            "export_pdf_path": "",
            "warnings": manifest["warnings"],
            "errors": manifest["errors"],
        }
    finally:
        if doc is not None:
            try:
                doc.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
