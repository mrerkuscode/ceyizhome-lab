from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from desktop.file_actions import latest_run_dir
from .label_template_editor import LabelTemplateEditorDialog
from .main_window import SettingsDialog
from .worker import CommandWorker
from native_edit.diagnostics import run_diagnostics
from native_edit.job_runner import run_native_edit_poc_for_template
from webui_backend.bridge import WebBridge
from webui_backend import backup_api, bulk_label_api, combined_production_api, customer_order_api, file_api, label_api, live_integration_guard_api, name_cut_queue_api, pdf_preview_api, print_queue_api, printer_profile_api, production_audit_api, production_safety, report_api, settings_api, template_api, trendyol_api, trendyol_mapping_api
from template_writer import create_production_template


class LabelModelSourceDialog(QDialog):
    def __init__(self, project_root: Path, source_path: Path, inferred: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.project_root = project_root
        self.source_path = source_path
        self._preview_path: Path | None = None
        self.setWindowTitle("CDR / AI Etiket Modeli")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.model_name = QLineEdit(inferred.get("model_name") or source_path.stem.replace("_", " ").title())
        self.model_no = QLineEdit(inferred.get("model_no", ""))
        self.template_no = QLineEdit(inferred.get("template_no") or "A")
        self.label_variant = QLineEdit(inferred.get("label_variant") or "GOLD")
        self.width = QDoubleSpinBox()
        self.width.setRange(1, 500)
        self.width.setValue(50)
        self.height = QDoubleSpinBox()
        self.height.setRange(1, 500)
        self.height.setValue(30)
        self.preview_text = QLineEdit("")
        self.preview_text.setReadOnly(True)
        preview_button = QPushButton("Önizleme Görseli Seç")
        preview_button.clicked.connect(self._choose_preview)
        self.active = QCheckBox("Aktif")
        self.active.setChecked(True)
        form.addRow("Model Adı", self.model_name)
        form.addRow("Model No", self.model_no)
        form.addRow("Şablon No", self.template_no)
        form.addRow("Varyant", self.label_variant)
        form.addRow("Etiket Genişliği (mm)", self.width)
        form.addRow("Etiket Yüksekliği (mm)", self.height)
        form.addRow("Önizleme", self.preview_text)
        form.addRow("", preview_button)
        form.addRow("", self.active)
        layout.addLayout(form)

        note = QLineEdit(
            "CDR/AI kaynak dosyası değiştirilmez. PNG/JPG/WebP önizleme görseli programda görüntüleme için kullanılır."
        )
        note.setReadOnly(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _choose_preview(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Önizleme Görseli Seç",
            str(self.project_root / "assets" / "label_backgrounds"),
            "Önizleme Görselleri (*.png *.jpg *.jpeg *.webp)",
        )
        if not path:
            return
        self._preview_path = Path(path)
        self.preview_text.setText(self._preview_path.name)

    def preview_path(self) -> Path | None:
        return self._preview_path

    def payload(self) -> dict[str, object]:
        return {
            "model_name": self.model_name.text().strip(),
            "model_no": self.model_no.text().strip(),
            "template_no": self.template_no.text().strip(),
            "label_variant": self.label_variant.text().strip(),
            "label_width_mm": self.width.value(),
            "label_height_mm": self.height.value(),
            "active": self.active.isChecked(),
        }


class WebMainWindow(QMainWindow):
    def __init__(self, project_root: Path, python_exe: Path) -> None:
        super().__init__()
        self.project_root = project_root
        self.python_exe = python_exe
        self.selected_excel = self.project_root / "input" / "siparisler.xlsx"
        self.report_set: ReportSet | None = None
        self.readiness = "NO_CHECK"
        self.log_text = ""
        self.activities: list[dict[str, str]] = []
        self.add_labels_to_queue_after_command = False
        self.current_command = ""
        self.command_cancel_requested = False
        self.bulk_selected_run: dict[str, object] = {
            "status": "IDLE",
            "message": "Seçili satır üretimi bekleniyor.",
            "row_numbers": [],
            "row_count": 0,
        }
        self.pending_new_label_model_visual: Path | None = None

        self.worker = CommandWorker(project_root, python_exe, self)
        self.worker.output_received.connect(self._append_log)
        self.worker.started.connect(self._command_started)
        self.worker.finished.connect(self._command_finished)

        self.bridge = WebBridge(self)
        self.channel = QWebChannel(self)
        self.channel.registerObject("cyzella", self.bridge)

        self.view = QWebEngineView()
        self.view.page().setWebChannel(self.channel)
        self.setCentralWidget(self.view)

        self.setWindowTitle("CeyizHome Lab")
        self.resize(1500, 900)
        self.setMinimumSize(1180, 720)
        self._load_reports()

        webui_dir = (self.project_root / "src" / "webui").resolve()
        html_path = (webui_dir / "index.html").resolve()
        self.view.page().profile().clearHttpCache()
        url = QUrl.fromLocalFile(str(html_path))
        url.setQuery(f"v={int(time.time())}")
        self.view.setUrl(url)

    def state_json(self) -> str:
        return json.dumps(self._state(), ensure_ascii=False)

    def choose_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Excel Dosyası Seç",
            str(self.project_root / "input"),
            "Excel Dosyaları (*.xlsx)",
        )
        if not path:
            return
        self.selected_excel = Path(path)
        self._record_production_audit_event({
            "id": f"audit-bulk-import-{self.selected_excel.name}-{int(self.selected_excel.stat().st_mtime) if self.selected_excel.exists() else ''}",
            "event_type": "bulk_import_created",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "status": "selected",
            "message": "Excel dosyası Toplu Üretim akışı için seçildi.",
            "file_path": str(self.selected_excel),
            "metadata": {"file_name": self.selected_excel.name},
        })
        self._add_activity("Excel seçildi", "Başarılı", self.selected_excel.name)
        self._emit_state()

    def run_dry(self) -> None:
        if not self._ensure_excel():
            return
        self._run_command("Dry-run kontrolü", ["src/main.py", "--excel", str(self.selected_excel), "--dry-run"])

    def run_production(self) -> None:
        if self.readiness == "BLOKE":
            QMessageBox.warning(self, "Üretim bloke", "Kritik hatalar varken üretim dosyası oluşturulamaz.")
            return
        if not self._ensure_excel():
            return
        answer = QMessageBox.question(
            self,
            "Üretim dosyaları oluşturulsun mu",
            "Bu işlem sadece dosya ve rapor üretir. CorelDRAW, yazıcı, RDWorks ve lazer otomatik çalışmaz. Devam edilsin mi",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._run_command("Üretim dosyaları", ["src/main.py", "--excel", str(self.selected_excel)])

    def render_labels(self, add_to_queue: bool = False) -> None:
        if not self._ensure_excel():
            return
        if self._print_mode() != "label_designer":
            message = "Etiket tasarım modu kapalı. Ayarlardan print.mode değerini label_designer yapın."
            QMessageBox.information(self, "Etiket tasarım modu kapalı", message)
            self._append_log(message + "\n")
            self._add_activity("Etiket PDF oluştur", "Bilgi", "Etiket tasarım modu kapalı")
            self._emit_state()
            return
        self.add_labels_to_queue_after_command = add_to_queue
        self._run_command("Etiket PDF oluştur", ["src/main.py", "--excel", str(self.selected_excel), "--render-labels"])

    def bulk_generate_and_add_to_queue(self) -> None:
        self.render_labels(add_to_queue=True)

    def bulk_generate_selected_and_add_to_queue(self, row_numbers: list[str]) -> dict[str, object]:
        result = bulk_label_api.write_selected_rows_excel(self.project_root, self.selected_excel, row_numbers)
        if result.get("status") != "OK":
            return result
        temp_excel = Path(str(result.get("path") or ""))
        if self.worker.is_running():
            return {"status": "ERROR", "message": "Bir işlem zaten çalışıyor. Lütfen bitmesini bekleyin."}
        if self._print_mode() != "label_designer":
            return {
                "status": "ERROR",
                "message": "Etiket tasarım modu kapalı. Ayarlardan print.mode değerini label_designer yapın.",
            }
        self.add_labels_to_queue_after_command = True
        self.bulk_selected_run = {
            "status": "STARTED",
            "message": f"{result.get('row_count', 0)} seçili satır için PDF/PNG üretimi başlatıldı.",
            "selected_excel": result.get("relative_path", ""),
            "row_numbers": result.get("row_numbers", []),
            "row_count": result.get("row_count", 0),
            "queue_result": {},
        }
        self._append_log(f"\nSeçili toplu etiket üretimi başlatıldı: {result.get('relative_path', temp_excel.name)}\n")
        self._run_command("Seçili toplu etiket PDF oluştur", ["src/main.py", "--excel", str(temp_excel), "--render-labels"])
        self._emit_state()
        return {
            "status": "STARTED",
            "message": f"{result.get('row_count', 0)} seçili satır için PDF/PNG üretimi ve queue ekleme başlatıldı.",
            "selected_excel": result.get("relative_path", ""),
            "row_numbers": result.get("row_numbers", []),
        }

    def bulk_generate_gallery_items_and_add_to_queue(self, items: list[dict[str, object]]) -> dict[str, object]:
        result = bulk_label_api.write_gallery_items_excel(self.project_root, self.selected_excel, items)
        if result.get("status") != "OK":
            return result
        temp_excel = Path(str(result.get("path") or ""))
        if self.worker.is_running():
            return {"status": "ERROR", "message": "Bir işlem zaten çalışıyor. Lütfen bitmesini bekleyin."}
        if self._print_mode() != "label_designer":
            return {
                "status": "ERROR",
                "message": "Etiket tasarım modu kapalı. Ayarlardan print.mode değerini label_designer yapın.",
            }
        self.add_labels_to_queue_after_command = True
        row_numbers = [str(item.get("row_number") or "") for item in items if not item.get("is_deleted")]
        self.bulk_selected_run = {
            "status": "STARTED",
            "message": f"{result.get('row_count', 0)} galeri satırı için PDF/PNG üretimi başlatıldı.",
            "selected_excel": result.get("relative_path", ""),
            "row_numbers": row_numbers,
            "row_count": result.get("row_count", 0),
            "manifest_path": result.get("manifest_path", ""),
            "batch_id": result.get("batch_id", ""),
            "queue_result": {},
        }
        self._append_log(f"\nToplu Etiket Galerisi üretimi başlatıldı: {result.get('relative_path', temp_excel.name)}\n")
        self._run_command("Seçili toplu etiket PDF oluştur", ["src/main.py", "--excel", str(temp_excel), "--render-labels"])
        self._emit_state()
        return {
            "status": "STARTED",
            "message": f"{result.get('row_count', 0)} galeri satırı için üretim ve queue ekleme başlatıldı.",
            "selected_excel": result.get("relative_path", ""),
            "manifest_path": result.get("manifest_path", ""),
            "row_numbers": row_numbers,
        }

    def open_output(self) -> None:
        self._open_result(file_api.open_output_folder(self.project_root), "Çıktı klasörü")

    def open_reports(self) -> None:
        self._open_result(file_api.open_reports_folder(self.project_root), "Raporlar klasörü")

    def open_print(self) -> None:
        self._open_result(file_api.open_print_folder(self.project_root), "Etiket çıktıları klasörü")

    def open_print_templates(self) -> None:
        self._open_result(file_api.open_print_templates_folder(self.project_root), "Baskı şablonları klasörü")

    def open_laser(self) -> None:
        self._open_result(file_api.open_laser_folder(self.project_root), "Lazer klasörü")

    def open_input(self) -> None:
        self._open_result(file_api.open_input_folder(self.project_root), "Input klasörü")

    def open_templates(self) -> None:
        self._open_folder(self.project_root / "templates" / "designs", "Etiket şablonları")

    def import_template_pack(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Şablon veya Paket Yükle",
            str(self.project_root),
            "Şablon Paketi / Baskı Şablonu (*.zip *.cdr *.ai *.pdf *.svg);;ZIP Paketleri (*.zip);;CorelDRAW Şablonu (*.cdr);;Tüm Dosyalar (*)",
        )
        if not path:
            return
        selected_path = Path(path)
        if selected_path.suffix.lower() != ".zip":
            self._import_print_template_file(selected_path)
            return
        try:
            result = template_api.import_template_pack(self.project_root, selected_path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Şablon paketi yüklenemedi", str(exc))
            self._append_log(f"Şablon paketi yüklenemedi: {exc}\n")
            return
        message = (
            f"Şablon paketi yüklendi. JSON: {result.imported_templates}, "
            f"CDR/AI/PDF/SVG baskı şablonu: {result.imported_print_templates}, "
            f"görsel: {result.imported_backgrounds}, Excel: {result.imported_excels}."
        )
        QMessageBox.information(self, "Şablon paketi", message)
        self._append_log(message + "\n")
        self._add_activity("Şablon paketi yüklendi", "Başarılı", Path(path).name)
        self._emit_state()

    def _import_print_template_file(self, source_path: Path) -> None:
        target_path = self.project_root / "templates" / "print" / source_path.name
        overwrite = False
        if target_path.exists():
            answer = QMessageBox.question(
                self,
                "Baskı şablonu zaten var",
                (
                    f"{target_path.name} zaten templates/print klasöründe var.\n\n"
                    "Üzerine yazılsın mı"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            overwrite = answer == QMessageBox.Yes
        try:
            result = template_api.import_print_template_file(self.project_root, source_path, overwrite=overwrite)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Baskı şablonu yüklenemedi", str(exc))
            self._append_log(f"Baskı şablonu yüklenemedi: {exc}\n")
            return
        if result["status"] == "SKIPPED_EXISTS":
            QMessageBox.information(self, "Baskı şablonu atlandı", "Dosya zaten var olduğu için atlandı.")
            self._append_log(f"Baskı şablonu atlandı: {result['target_path']}\n")
            return
        imported_path = Path(result["target_path"])
        message = (
            "Baskı şablonu yüklendi.\n\n"
            "Dosya şu klasöre kaydedildi: templates\\print\\\n"
            f"Dosya adı: {imported_path.name}\n\n"
            "Şablon dosyaları üretimden önce kullanılan kaynak dosyalardır.\n"
            "Etiket çıktıları ise üretimden sonra oluşturulan PDF/PNG dosyalarıdır.\n\n"
            "Not: CDR/AI dosyaları dahili Label Designer tarafından PDF'e çevrilmez. "
            "Bu dosyalar Corel hazırlık/eşleştirme akışı için templates/print içinde saklanır."
        )
        answer = QMessageBox.question(
            self,
            "Baskı şablonu yüklendi",
            message + "\n\nBaskı Şablonları Klasörünü Açmak ister misiniz",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        self._append_log(message + f"\nTam hedef: {result['target_path']}\n")
        self._add_activity("Baskı şablonu yüklendi", "Başarılı", source_path.name)
        if answer == QMessageBox.Yes:
            self.open_print_templates()
        self._emit_state()

    def create_label_model_from_source(self) -> None:
        source_text, _ = QFileDialog.getOpenFileName(
            self,
            "CDR / AI Model Yükle",
            str(self.project_root / "templates" / "print"),
            "Etiket Model Kaynakları (*.cdr *.ai *.pdf *.svg *.png *.jpg *.jpeg *.webp)",
        )
        if not source_text:
            return
        source_path = Path(source_text)
        inferred = template_api.infer_label_model_fields(source_path)
        dialog = LabelModelSourceDialog(self.project_root, source_path, inferred, self)
        if dialog.exec() != QDialog.Accepted:
            return
        payload = dialog.payload()
        preview_path = dialog.preview_path()
        target = self.project_root / "templates" / "designs" / (
            f"{payload['model_no']}_{payload['template_no']}_{payload['label_variant']}".lower().replace(" ", "_") + ".json"
        )
        overwrite = False
        if target.exists():
            answer = QMessageBox.question(
                self,
                "Model zaten var",
                f"{target.name} zaten var.\n\nÜzerine yazmadan önce backup alınacak. Devam edilsin mi",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
            overwrite = True
        try:
            result = template_api.create_label_model_from_source(
                self.project_root,
                source_path,
                payload,
                preview_image=preview_path,
                overwrite=overwrite,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Etiket modeli oluşturulamadı", str(exc))
            self._append_log(f"Etiket modeli oluşturulamadı: {exc}\n")
            return
        QMessageBox.information(
            self,
            "Etiket modeli hazır",
            (
                f"{result.get('message', 'Etiket modeli oluşturuldu.')}\n\n"
                f"Model JSON: {result.get('path', '')}\n"
                f"Kaynak dosya: {result.get('source_file', '')}\n"
                f"Programda Görünen Önizleme: {result.get('preview_image') or 'Önizleme yok - görsel seçebilirsiniz.'}\n\n"
                "CDR/AI kaynak dosyası değiştirilmez. Program içinde yazı alanları ve üretim ayarları düzenlenir."
            ),
        )
        self._append_log(f"Etiket modeli oluşturuldu: {result.get('path', '')}\n")
        self._add_activity("Etiket modeli eklendi", "Başarılı", source_path.name)
        self._emit_state()

    def choose_new_label_model_design_visual(self) -> dict[str, str]:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Tasarım Görseli Seç",
            str(self.project_root / "assets" / "label_backgrounds"),
            "Tasarım Görselleri (*.png *.jpg *.jpeg *.webp *.svg *.pdf)",
        )
        if not path:
            return {"status": "CANCELLED", "message": "Görsel seçilmedi."}
        selected_path = Path(path)
        if selected_path.suffix.lower() in {".cdr", ".ai"}:
            return {
                "status": "ERROR",
                "message": "Bu dosya kaynak tasarımdır, önizleme görseli değildir. Lütfen PNG/JPG/WebP/SVG/PDF seçin.",
            }
        if selected_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".pdf"}:
            return {"status": "ERROR", "message": "Tasarım görseli için PNG, JPG, JPEG, WebP, SVG veya PDF seçin."}
        self.pending_new_label_model_visual = selected_path
        try:
            preview_url = file_api.to_web_file_url(selected_path, self.project_root)
        except Exception:
            preview_url = ""
        return {
            "status": "OK",
            "message": "Tasarım görseli seçildi.",
            "path": str(selected_path),
            "file_name": selected_path.name,
            "preview_url": preview_url,
        }

    def create_label_model_from_wizard(self, data: dict[str, object]) -> dict[str, str]:
        visual_path = Path(str(data.get("design_visual_path") or ""))
        if not visual_path.exists() and self.pending_new_label_model_visual:
            visual_path = self.pending_new_label_model_visual
        try:
            result = template_api.create_label_model_from_wizard(self.project_root, data, visual_path)
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Etiket modeli kaydedilemedi: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}
        self.pending_new_label_model_visual = None
        self._append_log(result.get("message", "Etiket modeli kaydedildi.") + "\n")
        self._add_activity("Etiket modeli eklendi", "Başarılı", result.get("path", ""))
        self._emit_state()
        return result

    def clone_label_model_variant(self, template_path: str, data: dict[str, object]) -> dict[str, str]:
        try:
            result = template_api.clone_label_model_variant(self.project_root, Path(template_path), data)
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Model varyantı oluşturulamadı: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}
        self._append_log(result.get("message", "Model varyantı oluşturuldu.") + "\n")
        self._add_activity("Model varyantı oluşturuldu", "Başarılı", result.get("path", ""))
        self._emit_state()
        return result

    def create_template(self) -> None:
        template_path = self.project_root / "input" / "cyzella_production_template.xlsx"
        if template_path.exists():
            answer = QMessageBox.question(
                self,
                "Boş Excel şablonu yenilensin mi",
                (
                    "input/cyzella_production_template.xlsx dosyası zaten var.\n\n"
                    "Üzerine boş ve doğru kolon başlıklı temiz şablon yazılsın mı"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                self._append_log("Boş Excel şablonu oluşturma iptal edildi.\n")
                return
        try:
            created_path = create_production_template(template_path)
            self._append_log(f"Boş Excel şablonu oluşturuldu: {created_path}\n")
            self._add_activity("Boş Excel şablonu", "Başarılı", created_path.name)
            QMessageBox.information(
                self,
                "Boş Excel şablonu hazır",
                (
                    "Boş üretim Excel şablonu oluşturuldu.\n\n"
                    f"Dosya: {created_path}\n\n"
                    "Dosya şimdi açılacak. Eğer Excel açılmazsa Input klasöründen dosyayı açabilirsiniz."
                ),
            )
            self._open_file(created_path, "Boş Excel şablonu")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Boş Excel şablonu oluşturulamadı", str(exc))
            self._append_log(f"Boş Excel şablonu oluşturulamadı: {exc}\n")
        self._emit_state()

    def create_demo(self) -> None:
        self._run_command("Demo Excel", ["src/main.py", "--create-demo"])

    def convert_legacy_excel(self) -> None:
        if not self._ensure_excel():
            return
        self._run_command(
            "Eski Excel dönüştürme",
            ["src/main.py", "--excel", str(self.selected_excel), "--convert-legacy-excel"],
        )

    def render_manual_label(self, template_path: str, label_text: str, quantity: int) -> None:
        self.render_manual_label_fields(template_path, {"label_text": label_text}, quantity)

    def render_manual_label_fields(self, template_path: str, field_values: dict[str, str], quantity: int) -> dict[str, str]:
        preflight = self.preflight_manual_label_fields(template_path, field_values, quantity)
        if preflight.get("status") == "ERROR":
            self._record_production_audit_event({
                "event_type": "manual_review_required",
                "source": str(field_values.get("_queue_source") or "label_studio"),
                "source_label": str(field_values.get("_queue_source_label") or "Etiket Studio"),
                "source_item_id": str(field_values.get("_source_item_id") or ""),
                "status": "preflight_error",
                "severity": "blocked",
                "message": "\n".join(preflight.get("errors", [])) or "Etiket Studio preflight üretime engel verdi.",
                "metadata": {"preflight": preflight, "field_values": field_values},
            })
            return {"status": "ERROR", "message": "\n".join(preflight.get("errors", [])), "preflight": preflight}
        started_at = time.time()
        field_values = dict(field_values)
        field_values["_render_started_at"] = str(started_at)
        try:
            label_text = str(field_values.get("label_text") or "")
            result = label_api.render_manual(self.project_root, Path(template_path), label_text, quantity, field_values)
        except Exception as exc:  # noqa: BLE001
            self._record_production_audit_event({
                "event_type": "label_output_failed",
                "source": str(field_values.get("_queue_source") or "label_studio"),
                "source_label": str(field_values.get("_queue_source_label") or "Etiket Studio"),
                "origin_source": str(field_values.get("_origin_source") or ""),
                "origin_source_label": str(field_values.get("_origin_source_label") or ""),
                "source_item_id": str(field_values.get("_source_item_id") or ""),
                "studio_session_id": str(field_values.get("_studio_session_id") or ""),
                "status": "render_failed",
                "severity": "error",
                "message": str(exc),
                "metadata": {"field_values": field_values},
            })
            QMessageBox.warning(self, "Manuel etiket oluşturulamadı", str(exc))
            self._append_log(f"Manuel etiket oluşturulamadı: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}
        render_payload = {
            "status": "OK",
            "message": "PDF/PNG oluşturuldu.",
            "pdf_path": self._relative_or_name(result.pdf_path),
            "png_path": self._relative_or_name(result.png_path),
            "batch_pdf_path": self._relative_or_name(result.batch_pdf_path),
        }
        validation = self.validate_manual_label_output(render_payload, field_values)
        if validation.get("status") != "OK":
            self._record_production_audit_event({
                "event_type": "label_output_mismatch",
                "source": str(field_values.get("_queue_source") or "label_studio"),
                "source_label": str(field_values.get("_queue_source_label") or "Etiket Studio"),
                "origin_source": str(field_values.get("_origin_source") or ""),
                "origin_source_label": str(field_values.get("_origin_source_label") or ""),
                "source_item_id": str(field_values.get("_source_item_id") or ""),
                "studio_session_id": str(field_values.get("_studio_session_id") or ""),
                "status": "output_validation_failed",
                "severity": "error",
                "message": validation.get("message", "Çıktı canvas ile eşleşmedi."),
                "output_path": render_payload.get("batch_pdf_path") or render_payload.get("pdf_path") or "",
                "metadata": {"preflight": preflight, "output_validation": validation, "render_result": render_payload},
            })
            return {
                **render_payload,
                "status": "ERROR",
                "message": validation.get("message", "Çıktı canvas ile eşleşmedi."),
                "preflight": preflight,
                "output_validation": validation,
            }
        history = production_safety.append_production_history(
            self.project_root,
            Path(template_path),
            field_values,
            quantity,
            render_payload,
            preflight,
            validation,
        )
        self._record_production_audit_event(production_audit_api.create_audit_event_from_label_output({
            **field_values,
            **render_payload,
            "source": str(field_values.get("_queue_source") or "label_studio"),
            "source_label": str(field_values.get("_queue_source_label") or "Etiket Studio"),
            "origin_source": str(field_values.get("_origin_source") or ""),
            "origin_source_label": str(field_values.get("_origin_source_label") or ""),
            "source_item_id": str(field_values.get("_source_item_id") or ""),
            "studio_session_id": str(field_values.get("_studio_session_id") or ""),
            "label_text": str(field_values.get("label_text") or ""),
            "status": validation.get("status") or "OK",
        }, "label_output_created", "Etiket Studio PDF/PNG çıktısı oluşturuldu."))
        message = f"Manuel etiket hazır: {result.batch_pdf_path}"
        QMessageBox.information(self, "Manuel etiket", message)
        self._append_log(message + "\n")
        self._add_activity("Manuel etiket", "Başarılı", result.batch_pdf_path.name)
        self._emit_state()
        return {
            **render_payload,
            "preflight": preflight,
            "output_validation": validation,
            "production_history": history,
        }

    def preview_manual_label_fields(self, template_path: str, field_values: dict[str, str]) -> dict[str, str]:
        try:
            return label_api.preview_manual(self.project_root, Path(template_path), field_values)
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Manuel önizleme oluşturulamadı: {exc}\n")
            return {"status": "ERROR", "message": str(exc), "preview_url": ""}

    def render_manual_label_fields_to_queue(self, template_path: str, field_values: dict[str, str], quantity: int) -> dict[str, object]:
        preflight = self.preflight_manual_label_fields(template_path, field_values, quantity)
        if preflight.get("status") == "ERROR":
            self._record_production_audit_event({
                "event_type": "manual_review_required",
                "source": str(field_values.get("_queue_source") or "manual_label"),
                "source_label": str(field_values.get("_queue_source_label") or "Manuel Etiket"),
                "source_item_id": str(field_values.get("_source_item_id") or ""),
                "status": "preflight_error",
                "severity": "blocked",
                "message": "Çıktı kontrolünde sorun bulundu.",
                "metadata": {"preflight": preflight, "field_values": field_values},
            })
            return {
                "status": "ERROR",
                "message": "Çıktı kontrolünde sorun bulundu.",
                "errors": preflight.get("errors", []),
                "preflight": preflight,
            }
        started_at = time.time()
        field_values = dict(field_values)
        field_values["_render_started_at"] = str(started_at)
        queue_source = str(field_values.get("_queue_source") or "").strip().lower().replace("-", "_").replace(" ", "_")
        if queue_source not in {"label_studio", "etiket_studio", "manual_label", "trendyol", "bulk_production"}:
            queue_source = "manual_label"
        queue_source_label = str(
            field_values.get("_queue_source_label")
            or {
                "label_studio": "Etiket Studio",
                "etiket_studio": "Etiket Studio",
                "manual_label": "Manuel Etiket",
                "trendyol": "Trendyol",
                "bulk_production": "Toplu Üretim",
            }.get(queue_source, "Manuel Etiket")
        )
        queue_job_prefix = queue_source_label if queue_source_label else "Manuel Etiket"
        try:
            label_text = str(field_values.get("label_text") or "")
            result = label_api.render_manual(self.project_root, Path(template_path), label_text, quantity, field_values)
            render_payload = {
                "status": "OK",
                "message": "PDF/PNG oluşturuldu.",
                "pdf_path": self._relative_or_name(result.pdf_path),
                "png_path": self._relative_or_name(result.png_path),
                "batch_pdf_path": self._relative_or_name(result.batch_pdf_path),
            }
            validation = self.validate_manual_label_output(render_payload, field_values)
            if validation.get("status") != "OK":
                self._record_production_audit_event({
                    "event_type": "label_output_mismatch",
                    "source": queue_source,
                    "source_label": queue_source_label,
                    "origin_source": str(field_values.get("_origin_source") or ""),
                    "origin_source_label": str(field_values.get("_origin_source_label") or ""),
                    "source_item_id": str(field_values.get("_source_item_id") or ""),
                    "studio_session_id": str(field_values.get("_studio_session_id") or ""),
                    "status": "output_validation_failed",
                    "severity": "error",
                    "message": validation.get("message", "Çıktı canvas ile eşleşmedi."),
                    "output_path": render_payload.get("batch_pdf_path") or render_payload.get("pdf_path") or "",
                    "metadata": {"output_validation": validation, "render_result": render_payload},
                })
                return {
                    "render_result": render_payload,
                    "status": "ERROR",
                    "message": validation.get("message", "Çıktı canvas ile eşleşmedi."),
                    "output_validation": validation,
                }
            queue_result = print_queue_api.add_to_print_queue(
                self.project_root,
                {
                    "job_name": f"{queue_job_prefix} - {label_text or result.batch_pdf_path.stem}",
                    "job_type": "Manuel",
                    "source": queue_source,
                    "source_label": queue_source_label,
                    "origin_source": str(field_values.get("_origin_source") or ""),
                    "origin_source_label": str(field_values.get("_origin_source_label") or ""),
                    "source_item_id": str(field_values.get("_source_item_id") or ""),
                    "studio_session_id": str(field_values.get("_studio_session_id") or ""),
                    "bulk_row_id": str(field_values.get("_bulk_row_id") or ""),
                    "order_no": str(field_values.get("_order_no") or ""),
                    "customer_name": str(field_values.get("_customer_name") or ""),
                    "label_text": label_text,
                    "date_text": str(field_values.get("date_text") or ""),
                    "note_text": str(field_values.get("note_text") or ""),
                    "quantity": str(quantity),
                    "file_type": "MANUEL RULO TOPLU PDF",
                    "relative_path": self._relative_or_name(result.batch_pdf_path),
                },
            )
            production_safety.append_production_history(
                self.project_root,
                Path(template_path),
                field_values,
                quantity,
                render_payload,
                preflight,
                validation,
                queue_result,
            )
            self._record_production_audit_event(production_audit_api.create_audit_event_from_label_output({
                **field_values,
                **render_payload,
                "source": queue_source,
                "source_label": queue_source_label,
                "origin_source": str(field_values.get("_origin_source") or ""),
                "origin_source_label": str(field_values.get("_origin_source_label") or ""),
                "source_item_id": str(field_values.get("_source_item_id") or ""),
                "studio_session_id": str(field_values.get("_studio_session_id") or ""),
                "label_text": label_text,
                "status": validation.get("status") or "OK",
            }, "label_output_created", "Etiket Studio PDF/PNG çıktısı oluşturuldu."))
            self._record_production_audit_event({
                "event_type": "print_queue_created",
                "source": queue_source,
                "source_label": queue_source_label,
                "origin_source": str(field_values.get("_origin_source") or ""),
                "origin_source_label": str(field_values.get("_origin_source_label") or ""),
                "source_item_id": str(field_values.get("_source_item_id") or ""),
                "queue_item_id": queue_result.get("id", ""),
                "batch_id": queue_result.get("batch_id", ""),
                "title": label_text,
                "status": queue_result.get("status", ""),
                "message": queue_result.get("message", "Etiket Studio çıktısı Yazdırma Sırası'na aktarıldı."),
                "output_path": render_payload["batch_pdf_path"],
                "metadata": queue_result,
            })
        except Exception as exc:  # noqa: BLE001
            self._record_production_audit_event({
                "event_type": "label_output_failed",
                "source": queue_source,
                "source_label": queue_source_label,
                "origin_source": str(field_values.get("_origin_source") or ""),
                "origin_source_label": str(field_values.get("_origin_source_label") or ""),
                "source_item_id": str(field_values.get("_source_item_id") or ""),
                "studio_session_id": str(field_values.get("_studio_session_id") or ""),
                "status": "render_or_queue_failed",
                "severity": "error",
                "message": str(exc),
                "metadata": {"field_values": field_values},
            })
            self._append_log(f"Manuel etiket oluşturulamadı: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}
        message = f"Manuel etiket hazır ve yazdırma sırasına eklendi: {result.batch_pdf_path}"
        self._append_log(message + "\n")
        self._add_activity("Manuel etiket sıraya eklendi", "Başarılı", result.batch_pdf_path.name)
        self._emit_state()
        return {
            "status": "OK",
            "message": "Yazdırma sırasına eklendi.",
            "pdf_path": render_payload["pdf_path"],
            "png_path": render_payload["png_path"],
            "batch_pdf_path": render_payload["batch_pdf_path"],
            "queue_result": queue_result,
            "preflight": preflight,
            "output_validation": validation,
        }

    def preflight_manual_label_fields(self, template_path: str, field_values: dict[str, object], quantity: int) -> dict[str, object]:
        try:
            return production_safety.preflight_manual_label(self.project_root, Path(template_path), field_values, quantity)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "can_render": False, "message": str(exc), "errors": [str(exc)], "warnings": []}

    def validate_manual_label_output(self, render_result: dict[str, object], field_values: dict[str, object]) -> dict[str, object]:
        try:
            return production_safety.validate_manual_output(self.project_root, render_result, field_values)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": str(exc), "errors": [str(exc)]}

    def production_history(self) -> list[dict[str, object]]:
        return production_safety.list_production_history(self.project_root)

    def production_audit_events(self, filters: dict[str, object] | None = None) -> list[dict[str, object]]:
        return production_audit_api.list_production_audit_events(self.project_root, filters)

    def production_audit_summary(self) -> dict[str, object]:
        return production_audit_api.list_production_audit_summary(self.project_root)

    def append_production_audit_event(self, event: dict[str, object]) -> dict[str, object]:
        result = production_audit_api.append_production_audit_event(self.project_root, event)
        self._append_log(result.get("message", "Üretim geçmişi audit kaydı güncellendi.") + "\n")
        self._emit_state()
        return result

    def _record_production_audit_event(self, event: dict[str, object]) -> dict[str, object]:
        try:
            return production_audit_api.append_production_audit_event(self.project_root, event)
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Audit kaydı yazılamadı: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}

    def get_production_audit_event(self, event_id: str) -> dict[str, object]:
        return production_audit_api.get_production_audit_event(self.project_root, event_id)

    def rebuild_production_audit_from_existing_sources(self) -> dict[str, object]:
        result = production_audit_api.rebuild_production_audit_from_existing_sources(self.project_root)
        self._append_log(result.get("message", "Üretim geçmişi yeniden tarandı.") + "\n")
        self._add_activity("Üretim Geçmişi", str(result.get("status", "OK")), result.get("message", "Audit kayıtları güncellendi."))
        self._emit_state()
        return result

    def export_production_audit_events(self, payload: dict[str, object] | None = None) -> dict[str, object]:
        payload = payload or {}
        filters = payload.get("filters") if isinstance(payload.get("filters"), dict) else {}
        export_format = str(payload.get("format") or "json")
        result = production_audit_api.export_production_audit_events(self.project_root, filters, export_format)
        self._append_log(result.get("message", "Üretim geçmişi dışa aktarımı tamamlandı.") + "\n")
        self._add_activity("Üretim Geçmişi export", str(result.get("status", "OK")), result.get("path", ""))
        self._emit_state()
        return result

    def live_integration_registry(self) -> dict[str, object]:
        return live_integration_guard_api.list_risky_actions()

    def live_integration_security_settings(self) -> dict[str, object]:
        return live_integration_guard_api.load_security_settings(self.project_root)

    def save_live_integration_security_settings(self, payload: dict[str, object] | None = None) -> dict[str, object]:
        result = live_integration_guard_api.save_security_settings(self.project_root, payload or {})
        self._record_production_audit_event({
            "event_type": "integration_action_blocked",
            "source": "integration_guard",
            "source_label": "Entegrasyon Guvenligi",
            "status": result.get("status", ""),
            "severity": "info",
            "message": result.get("message", ""),
            "metadata": {"settings": result.get("settings", {})},
        })
        self._emit_state()
        return result

    def guard_live_integration_action(
        self,
        action_key: str,
        payload: dict[str, object] | None = None,
        admin_confirmed: bool = False,
        operator_confirmed: bool = False,
        dry_run: bool = True,
    ) -> dict[str, object]:
        payload = payload or {}
        if dry_run:
            self._record_production_audit_event({
                "event_type": "integration_dry_run_started",
                "audit_key": f"integration:{action_key}:started:{payload.get('source_item_id') or payload.get('record_id') or payload.get('order_no') or 'manual'}",
                "source": "integration_guard",
                "source_label": "Entegrasyon Guvenligi",
                "source_item_id": str(payload.get("source_item_id") or payload.get("record_id") or ""),
                "order_no": str(payload.get("order_no") or ""),
                "title": str(payload.get("title") or action_key),
                "status": "DRY_RUN_STARTED",
                "severity": "info",
                "message": f"{action_key} dry-run kontrolu baslatildi. Canli islem yapilmadi.",
                "metadata": {"action_key": action_key, "payload": payload},
            })
        result = live_integration_guard_api.evaluate_action(
            self.project_root,
            action_key,
            payload,
            admin_confirmed=admin_confirmed,
            operator_confirmed=operator_confirmed,
            dry_run=dry_run,
        )
        self._record_production_audit_event({
            "event_type": str(result.get("event_type") or "integration_action_blocked"),
            "audit_key": f"integration:{action_key}:{result.get('event_type') or result.get('status') or 'guard'}:{payload.get('source_item_id') or payload.get('record_id') or payload.get('order_no') or 'manual'}",
            "source": "integration_guard",
            "source_label": "Entegrasyon Guvenligi",
            "source_item_id": str(payload.get("source_item_id") or payload.get("record_id") or ""),
            "order_no": str(payload.get("order_no") or ""),
            "title": str(result.get("label") or action_key),
            "status": str(result.get("status") or ""),
            "severity": str(result.get("severity") or "warning"),
            "message": str(result.get("message") or ""),
            "metadata": result,
        })
        self._append_log(str(result.get("message") or "Entegrasyon guard kontrol edildi.") + "\n")
        self._emit_state()
        return result

    def _audit_backup_event(self, event_type: str, result: dict[str, object], severity: str = "info") -> None:
        self._record_production_audit_event({
            "event_type": event_type,
            "source": "backup",
            "source_label": "Veri Bakımı",
            "status": result.get("status", ""),
            "severity": severity,
            "message": result.get("message", ""),
            "file_path": result.get("manifest_path", "") or result.get("backup_path", ""),
            "metadata": result,
        })

    def create_backup(self) -> dict[str, object]:
        try:
            result = backup_api.create_backup(self.project_root, reason="manual")
        except Exception as exc:  # noqa: BLE001
            result = {"status": "ERROR", "message": str(exc)}
            self._audit_backup_event("backup_failed", result, "error")
            self._emit_state()
            return result
        self._audit_backup_event("backup_created", result, "success")
        self._append_log(result.get("message", "Yedek oluşturuldu.") + "\n")
        self._add_activity("Veri Bakımı", "Yedek", result.get("backup_path", ""))
        self._emit_state()
        return result

    def list_backups(self) -> list[dict[str, object]]:
        return backup_api.list_backups(self.project_root)

    def validate_backup(self, path: str) -> dict[str, object]:
        result = backup_api.validate_backup(self.project_root, path)
        self._audit_backup_event("backup_validated", result, "success" if result.get("status") == "OK" else "error")
        self._emit_state()
        return result

    def restore_backup(self, path: str, dry_run: bool = True) -> dict[str, object]:
        result = backup_api.restore_backup(self.project_root, path, dry_run=dry_run)
        if dry_run:
            self._audit_backup_event("restore_previewed", result, "info" if result.get("status") == "DRY_RUN" else "error")
        elif result.get("status") == "OK":
            self._audit_backup_event("restore_completed", result, "success")
        else:
            self._audit_backup_event("restore_failed", result, "error")
        self._append_log(result.get("message", "Geri yükleme kontrol edildi.") + "\n")
        self._emit_state()
        return result

    def export_backup_manifest(self, path: str = "") -> dict[str, object]:
        return backup_api.export_backup_manifest(self.project_root, path)

    def create_calibration_pdf(self) -> None:
        try:
            result = label_api.create_calibration(self.project_root)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Kalibrasyon PDF oluşturulamadı", str(exc))
            self._append_log(f"Kalibrasyon PDF oluşturulamadı: {exc}\n")
            return
        message = f"Kalibrasyon PDF hazır: {result.pdf_path}"
        QMessageBox.information(self, "Kalibrasyon PDF", message)
        self._append_log(message + "\n")
        self._add_activity("Kalibrasyon PDF", "Başarılı", result.pdf_path.name)
        self._emit_state()

    def set_selected_excel(self, path: Path) -> None:
        self.selected_excel = path
        self._emit_state()

    def edit_template(self) -> None:
        QMessageBox.information(
            self,
            "Model düzenleme penceresi",
            "Model düzenleme penceresi açılıyor.\n\nBu güvenli düzenleme penceresi JSON şablonu backup alarak kaydeder. CDR/AI kaynak dosyaları değiştirilmez.",
        )
        dialog = LabelTemplateEditorDialog(self.project_root, self)
        dialog.saved.connect(self._emit_state)
        dialog.exec()

    def show_help(self) -> None:
        QMessageBox.information(
            self,
            "Nasıl Kullanırım",
            (
                "1. Excel dosyanızı seçin.\n"
                "2. Kontrolü çalıştırın (Dry-run).\n"
                "3. Hataları düzeltin.\n"
                "4. Tekrar kontrol edin.\n"
                "5. Etiket ve lazer dosyalarını oluşturup raporları inceleyin.\n\n"
                "Güvenlik: CorelDRAW, yazıcı, RDWorks ve lazer otomatik çalışmaz."
            ),
        )

    def show_settings(self) -> None:
        dialog = SettingsDialog(self.project_root, self)
        dialog.saved.connect(self._emit_state)
        dialog.exec()

    def _run_command(self, name: str, args: list[str]) -> None:
        if self.worker.is_running():
            QMessageBox.information(self, "İşlem devam ediyor", "Bir işlem zaten çalışıyor. Lütfen bitmesini bekleyin.")
            return
        self.current_command = name
        self.command_cancel_requested = False
        self._append_log(f"\n{name} başlatıldı...\n")
        self.worker.run(args)

    def _command_started(self) -> None:
        self._add_activity(getattr(self, "current_command", "Komut"), "Çalışıyor", "Komut başlatıldı")
        self._emit_state()

    def _command_finished(self, exit_code: int) -> None:
        name = getattr(self, "current_command", "Komut")
        was_cancelled = bool(getattr(self, "command_cancel_requested", False))
        status = "İptal edildi" if was_cancelled else "Başarılı" if exit_code == 0 else "Hata"
        self._add_activity(name, status, f"Çıkış kodu: {exit_code}")
        self._load_reports()
        queue_result: dict[str, object] | None = None
        if exit_code == 0 and self.add_labels_to_queue_after_command and not was_cancelled:
            queue_result = print_queue_api.add_label_outputs_to_queue(self.project_root, self.label_outputs())
            self._record_production_audit_event({
                "event_type": "bulk_sent_to_print_queue",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "batch_id": self.bulk_selected_run.get("batch_id", ""),
                "status": queue_result.get("status", ""),
                "message": queue_result.get("message", "Toplu Üretim çıktıları Yazdırma Sırası'na aktarıldı."),
                "metadata": queue_result,
            })
            self._append_log(queue_result.get("message", "Etiket çıktıları yazdırma sırasına eklendi.") + "\n")
            self._add_activity("Yazdırma sırası", "Başarılı", queue_result.get("message", "Etiket çıktıları eklendi"))
        if name == "Seçili toplu etiket PDF oluştur":
            if exit_code == 0:
                self._update_bulk_gallery_manifest_after_run(queue_result or {})
                self.bulk_selected_run = {
                    **self.bulk_selected_run,
                    "status": "COMPLETED",
                    "message": (queue_result or {}).get("message", "Seçili satır üretimi tamamlandı ve yazdırma sırası güncellendi."),
                    "exit_code": exit_code,
                    "queue_result": queue_result or {},
                    "queue_count": len(self.print_queue()),
                }
            elif was_cancelled:
                self.bulk_selected_run = {
                    **self.bulk_selected_run,
                    "status": "CANCELLED",
                    "message": "Seçili satır üretimi kullanıcı isteğiyle iptal edildi.",
                    "exit_code": exit_code,
                    "queue_result": {},
                }
            else:
                self.bulk_selected_run = {
                    **self.bulk_selected_run,
                    "status": "ERROR",
                    "message": "Seçili satır üretimi tamamlanamadı. Çalışma günlüğünü kontrol edin.",
                    "exit_code": exit_code,
                    "queue_result": {},
                }
        self.add_labels_to_queue_after_command = False
        self.command_cancel_requested = False
        self._append_log(f"{name} tamamlandı. Durum: {status}\n")
        self._emit_state()

    def _update_bulk_gallery_manifest_after_run(self, queue_result: dict[str, object]) -> None:
        manifest_relative = str(self.bulk_selected_run.get("manifest_path") or "")
        if not manifest_relative:
            return
        manifest_path = (self.project_root / manifest_relative).resolve()
        try:
            if not manifest_path.exists() or self.project_root.resolve() not in manifest_path.parents:
                return
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            latest_outputs = self.label_outputs()
            latest_pdf = next((row for row in latest_outputs if str(row.get("relative_path") or "").lower().endswith(".pdf")), None)
            latest_pngs = [str(row.get("relative_path") or "") for row in latest_outputs if str(row.get("relative_path") or "").lower().endswith(".png")][:50]
            if latest_pdf:
                manifest["generated_pdf"] = latest_pdf.get("relative_path") or latest_pdf.get("file_path") or ""
            manifest["generated_pngs"] = latest_pngs
            manifest["queue_path"] = str(queue_result.get("queue_path") or queue_result.get("path") or "")
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Toplu galeri manifest güncellenemedi: {exc}\n")

    def _append_log(self, text: str) -> None:
        self.log_text += text
        if len(self.log_text) > 20000:
            self.log_text = self.log_text[-20000:]
        self.bridge.logChanged.emit(self.log_text)

    def _load_reports(self) -> None:
        self.report_set = report_api.load_reports(self.project_root)
        self.readiness = report_api.readiness(self.report_set)

    def _state(self) -> dict[str, object]:
        self._load_reports()
        summary = report_api.summary(self.report_set)
        errors = report_api.first_errors(self.report_set)
        font_ok = (self.project_root / "assets" / "fonts" / "connected_script.ttf").exists()
        run_dir = latest_run_dir(self.project_root)
        return {
            "selectedExcelName": self.selected_excel.name if self.selected_excel.exists() else "Excel seçilmedi",
            "selectedExcelPath": self._relative_or_name(self.selected_excel),
            "readiness": self.readiness,
            "fontOk": font_ok,
            "fontText": "Lazer Fontu Hazır" if font_ok else "Lazer Fontu Eksik",
            "summary": summary,
            "errors": errors,
            "activities": list(reversed(self.activities[-5:])),
            "outputDir": self._relative_or_name(run_dir),
            "log": self.log_text,
            "templates": self.label_templates(),
            "labelModels": self.label_model_gallery(),
            "printTemplates": self.print_templates(),
            "labelOutputs": self.label_outputs(),
            "archivedLabelOutputs": self.archived_label_outputs(),
            "labelOutputArchiveHistory": self.label_output_archive_history(),
            "laserOutputs": self.laser_outputs(),
            "printQueue": self.print_queue(),
            "customerOrders": self.customer_orders(),
            "trendyol": self.trendyol_state(),
            "bulkLabelUsage": self.bulk_label_usage(),
            "bulkPreviewSamples": self.bulk_preview_samples(),
            "bulkColumnMapping": self.bulk_column_mapping(),
            "bulkGalleryItems": self.bulk_gallery_items(),
            "combinedProduction": self.combined_production_state(),
            "nameCutQueue": self.name_cut_queue(),
            "nameCutTransferHistory": self.name_cut_transfer_history(),
            "nameCutExportHistory": self.name_cut_export_history(),
            "bulkSelectedRun": self.bulk_selected_run,
            "commandRunning": self.worker.is_running(),
            "currentCommand": self.current_command,
            "reports": self.reports_payload(),
            "qualityGateEvidence": self.quality_gate_evidence(),
            "productionHistory": self.production_history(),
            "productionAudit": self.production_audit_events(),
            "productionAuditSummary": self.production_audit_summary(),
            "printerProfiles": self.printer_profiles(),
            "systemBackups": self.list_backups(),
            "settingsBackups": settings_api.list_settings_backups(self.project_root),
            "liveIntegrationRegistry": self.live_integration_registry(),
            "liveIntegrationSecurity": self.live_integration_security_settings(),
            "labelDefaults": settings_api.get_label_defaults(self.project_root),
            "printMode": settings_api.get_print_mode(self.project_root),
        }

    def _emit_state(self) -> None:
        self.bridge.stateChanged.emit(self.state_json())

    def reports_payload(self) -> dict[str, object]:
        return report_api.report_payload(self.report_set)

    def quality_gate_evidence(self) -> dict[str, object]:
        candidates = sorted((self.project_root / "output").glob("20??-??-??/quality_gate"), reverse=True)
        if not candidates:
            return {"status": "MISSING", "message": "Kalite kapısı kanıtı bulunamadı."}
        quality_dir = candidates[0]
        result_path = quality_dir / "REAL_PRODUCTION_QUALITY_GATE_RESULT.json"
        acceptance_path = quality_dir / "FINAL_MULTI_MODEL_ACCEPTANCE_RESULT.json"
        evidence: dict[str, object] = {
            "status": "MISSING",
            "message": "Kalite kapısı sonucu okunamadı.",
            "quality_gate_dir": self._relative_or_name(quality_dir),
        }
        try:
            if result_path.exists():
                quality = json.loads(result_path.read_text(encoding="utf-8"))
                evidence.update(
                    {
                        "status": str(quality.get("status") or "UNKNOWN"),
                        "model": str(quality.get("model") or ""),
                        "final_png_path": str(quality.get("final_png_path") or ""),
                        "final_pdf_path": str(quality.get("final_pdf_path") or ""),
                        "queue_relative_path": str(quality.get("queue_relative_path") or ""),
                    }
                )
            if acceptance_path.exists():
                acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
                evidence["acceptance_status"] = str(acceptance.get("status") or "UNKNOWN")
                evidence["acceptance_scenarios"] = len(acceptance.get("scenarios") or [])
        except Exception as exc:  # noqa: BLE001
            evidence["status"] = "ERROR"
            evidence["message"] = str(exc)
        return evidence

    def svg_files(self) -> list[str]:
        return [str(path) for path in (self.report_set.svg_files if self.report_set else [])]

    def open_svg(self, path: str) -> None:
        self._open_result(file_api.open_svg(Path(path)), "SVG")

    def open_project_file(self, relative_path: str) -> None:
        path = (self.project_root / relative_path).resolve()
        try:
            path.relative_to(self.project_root.resolve())
        except ValueError:
            QMessageBox.warning(self, "Dosya açılamadı", "Proje dışındaki dosya açılamaz.")
            return
        self._open_file(path, "Harici dosya")

    def _resolve_audit_safe_path(self, raw_path: str) -> tuple[Path | None, str]:
        value = str(raw_path or "").strip().replace("file:///", "").replace("file://", "")
        if not value:
            return None, "Dosya yolu boş."
        path = Path(value)
        if not path.is_absolute():
            path = self.project_root / value
        try:
            resolved = path.resolve()
            root = self.project_root.resolve()
            relative = resolved.relative_to(root)
        except Exception:
            return None, "Proje dışındaki dosya audit ekranından açılamaz."
        allowed_roots = {"output", "data"}
        first = relative.parts[0].lower() if relative.parts else ""
        if first not in allowed_roots:
            return None, "Audit dosya aksiyonları sadece output/ veya data/ altındaki dosyalar için açıktır."
        return resolved, ""

    def reveal_file_in_folder(self, raw_path: str) -> dict[str, object]:
        path, error = self._resolve_audit_safe_path(raw_path)
        if error:
            return {"status": "ERROR", "message": error}
        if not path or not path.exists():
            return {"status": "ERROR", "message": f"Dosya yolu var ancak dosya bulunamadı: {raw_path}"}
        target = path if path.is_dir() else path.parent
        if sys.platform.startswith("win"):
            try:
                os.startfile(target)  # noqa: S606 - user requested revealing a safe project folder.
            except OSError as exc:
                return {"status": "ERROR", "message": f"Klasör açılamadı: {exc}"}
            message = f"Klasör gösterildi: {target}"
            self._append_log(message + "\n")
            self._add_activity("Audit klasörde göster", "Başarılı", message)
            self._emit_state()
            return {"status": "OK", "message": message, "path": str(path), "folder": str(target)}
        return {"status": "ERROR", "message": "Klasörde gösterme sadece Windows oturumunda desteklenir."}

    def open_file_safe(self, raw_path: str) -> dict[str, object]:
        path, error = self._resolve_audit_safe_path(raw_path)
        if error:
            return {"status": "ERROR", "message": error}
        if not path or not path.exists() or path.is_dir():
            return {"status": "ERROR", "message": f"Dosya yolu var ancak dosya bulunamadı: {raw_path}"}
        allowed_suffixes = {".csv", ".json", ".txt", ".md", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".svg"}
        if path.suffix.lower() not in allowed_suffixes:
            return {"status": "ERROR", "message": "Bu dosya türü audit ekranından otomatik açılmaz. Klasörde göstererek manuel kontrol edin."}
        if sys.platform.startswith("win"):
            try:
                os.startfile(path)  # noqa: S606 - user requested opening a safe generated audit/output file.
            except OSError as exc:
                return {"status": "ERROR", "message": f"Dosya açılamadı: {exc}"}
            message = f"Dosya açıldı: {path}"
            self._append_log(message + "\n")
            self._add_activity("Audit dosya aç", "Başarılı", message)
            self._emit_state()
            return {"status": "OK", "message": message, "path": str(path)}
        return {"status": "ERROR", "message": "Dosya açma sadece Windows oturumunda desteklenir."}

    def label_templates(self) -> list[dict[str, str]]:
        return template_api.list_label_templates(self.project_root)

    def label_model_gallery(self) -> list[dict[str, str]]:
        return template_api.list_label_model_gallery(self.project_root)

    def choose_label_model_preview(self, template_path: str) -> dict[str, str]:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "\u00d6nizleme G\u00f6rseli Se\u00e7",
            str(self.project_root / "assets" / "label_backgrounds"),
            "\u00d6nizleme Dosyalar\u0131 (*.png *.jpg *.jpeg *.webp *.pdf *.svg)",
        )
        if not path:
            return {"status": "CANCELLED", "message": "\u00d6nizleme g\u00f6rseli se\u00e7ilmedi."}
        try:
            result = template_api.set_label_model_preview(self.project_root, Path(template_path), Path(path))
            preview_result = label_api.preview_manual(
                self.project_root,
                Path(template_path),
                {
                    "label_text": "Ay\u015fe & Mehmet",
                    "date_text": "12.05.2026",
                    "note_text": "S\u00f6z Hat\u0131ras\u0131",
                },
            )
            if preview_result.get("status") == "OK":
                result["test_preview_url"] = preview_result.get("preview_url", "")
                result["test_preview_path"] = preview_result.get("preview_path", "")
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": str(exc)}
        self._append_log(result.get("message", "\u00d6nizleme g\u00f6rseli kaydedildi.") + "\n")
        self._add_activity("Model \u00f6nizleme g\u00f6rseli", "Ba\u015far\u0131l\u0131", Path(template_path).name)
        self._emit_state()
        return result

    def validate_label_model_preview(self, template_path: str) -> dict[str, object]:
        try:
            return template_api.validate_model_preview(self.project_root, Path(template_path))
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": str(exc), "warnings": [str(exc)]}

    def save_label_model_field(self, template_path: str, index: int, data: dict[str, object]) -> dict[str, str]:
        try:
            result = template_api.save_label_model_field(self.project_root, Path(template_path), index, data)
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Yazı alanı kaydedilemedi: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}
        self._append_log(result.get("message", "Yazı alanı kaydedildi.") + "\n")
        self._add_activity("Yazı alanı kaydedildi", "Başarılı", Path(template_path).name)
        self._emit_state()
        return result

    def add_label_model_field(self, template_path: str, field_type: str) -> dict[str, object]:
        try:
            result = template_api.add_label_model_field(self.project_root, Path(template_path), field_type)
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Yaz\u0131 alan\u0131 eklenemedi: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}
        self._append_log(result.get("message", "Yaz\u0131 alan\u0131 eklendi.") + "\n")
        self._add_activity("Yaz\u0131 alan\u0131 eklendi", "Ba\u015far\u0131l\u0131", Path(template_path).name)
        self._emit_state()
        return result

    def remove_label_model_field(self, template_path: str, index: int) -> dict[str, str]:
        try:
            result = template_api.remove_label_model_field(self.project_root, Path(template_path), index)
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Yaz\u0131 alan\u0131 silinemedi: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}
        self._append_log(result.get("message", "Yaz\u0131 alan\u0131 silindi.") + "\n")
        self._add_activity("Yaz\u0131 alan\u0131 silindi", "Ba\u015far\u0131l\u0131", Path(template_path).name)
        self._emit_state()
        return result

    def cleanup_duplicate_label_text_fields(self, template_path: str) -> dict[str, object]:
        try:
            result = template_api.cleanup_duplicate_label_text_fields(self.project_root, Path(template_path))
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Tekrar isim alanlar\u0131 temizlenemedi: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}
        self._append_log(result.get("message", "Tekrar isim alanlar\u0131 kontrol edildi.") + "\n")
        self._add_activity("Tekrar isim alan\u0131 temizli\u011fi", str(result.get("status", "OK")), Path(template_path).name)
        self._emit_state()
        return result

    def cleanup_duplicate_note_fields(self, template_path: str) -> dict[str, object]:
        try:
            result = template_api.cleanup_duplicate_note_fields(self.project_root, Path(template_path))
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Tekrar not alanlar\u0131 temizlenemedi: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}
        self._append_log(result.get("message", "Tekrar not alanlar\u0131 kontrol edildi.") + "\n")
        self._add_activity("Tekrar not alan\u0131 temizli\u011fi", str(result.get("status", "OK")), Path(template_path).name)
        self._emit_state()
        return result

    def normalize_label_model_preview(self, template_path: str) -> dict[str, object]:
        try:
            result = template_api.normalize_label_model_preview(self.project_root, Path(template_path))
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"G\u00f6rsel etikete uydurulamad\u0131: {exc}\n")
            return {"status": "ERROR", "message": str(exc)}
        self._append_log(result.get("message", "G\u00f6rsel etikete uyduruldu.") + "\n")
        self._add_activity("G\u00f6rsel etikete uyduruldu", str(result.get("status", "OK")), Path(template_path).name)
        self._emit_state()
        return result

    def import_label_font(self) -> dict[str, str]:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Font Y\u00fckle",
            str(self.project_root / "assets" / "fonts"),
            "Font Dosyalar\u0131 (*.ttf *.otf)",
        )
        if not path:
            return {"status": "CANCELLED", "message": "Font se\u00e7ilmedi."}
        try:
            result = template_api.import_label_font(self.project_root, Path(path))
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": str(exc)}
        self._append_log(result.get("message", "Font y\u00fcklendi.") + "\n")
        self._emit_state()
        return result

    def run_native_edit_poc(self, template_path: str, edit: bool) -> dict[str, object]:
        try:
            result = run_native_edit_poc_for_template(self.project_root, Path(template_path), edit=edit, allow_engine=True)
        except Exception as exc:  # noqa: BLE001
            result = {"status": "FAILED", "message": str(exc), "errors": [str(exc)]}
        self._append_log(f"Native AI/CDR PoC: {result.get('status', 'UNKNOWN')} - {result.get('message', '')}\n")
        self._add_activity("Native AI/CDR PoC", str(result.get("status", "UNKNOWN")), Path(template_path).name)
        self._emit_state()
        return result

    def native_edit_diagnostics(self) -> dict[str, object]:
        return run_diagnostics(self.project_root, allow_launch=False)

    def open_native_edit_report(self) -> dict[str, str]:
        reports = sorted((self.project_root / "output").glob("*/NATIVE*_REPORT.md"))
        if not reports:
            return {"status": "MISSING", "message": "Native edit raporu bulunamad\u0131."}
        self._open_file(reports[-1], "Native edit raporu")
        return {"status": "OK", "message": "Son native edit raporu a\u00e7\u0131ld\u0131.", "path": str(reports[-1])}

    def print_templates(self) -> list[dict[str, str]]:
        return template_api.list_print_templates(self.project_root)

    def print_template_detail(self, relative_path: str) -> dict[str, str]:
        return template_api.get_print_template_detail(self.project_root, relative_path)

    def save_print_template_metadata(self, relative_path: str, data: dict[str, object]) -> dict[str, str]:
        result = template_api.save_print_template_metadata(self.project_root, relative_path, data)
        self._append_log(result.get("message", "Baskı şablonu bilgileri kaydedildi.") + "\n")
        self._add_activity("Baskı şablonu bilgisi", "Başarılı", relative_path)
        self._emit_state()
        return result

    def create_linked_label_design(self, relative_path: str) -> dict[str, str]:
        result = template_api.create_linked_label_design(self.project_root, relative_path)
        self._append_log(result.get("message", "Bağlı etiket tasarımı işlemi tamamlandı.") + "\n")
        self._add_activity("Bağlı etiket tasarımı", "Başarılı" if result.get("status") in {"CREATED", "EXISTS"} else "Bilgi", relative_path)
        self._emit_state()
        return result

    def label_outputs(self) -> list[dict[str, str]]:
        return label_api.list_label_outputs(self.project_root)

    def archived_label_outputs(self) -> list[dict[str, str]]:
        return label_api.list_archived_label_outputs(self.project_root)

    def label_output_archive_history(self) -> list[dict[str, object]]:
        return label_api.list_label_output_archive_history(self.project_root)

    def archive_label_outputs(self, relative_paths: list[str]) -> dict[str, object]:
        result = label_api.archive_label_outputs(self.project_root, relative_paths)
        self._append_log(result.get("message", "Çıktı arşivleme işlemi tamamlandı.") + "\n")
        self._emit_state()
        return result

    def restore_label_outputs(self, relative_paths: list[str]) -> dict[str, object]:
        result = label_api.restore_label_outputs(self.project_root, relative_paths)
        self._append_log(result.get("message", "Arşivden geri alma işlemi tamamlandı.") + "\n")
        self._emit_state()
        return result

    def cancel_running_job(self) -> dict[str, object]:
        if not self.worker.is_running():
            return {"status": "IDLE", "message": "Devam eden işlem yok."}
        self.command_cancel_requested = True
        cancelled = self.worker.cancel()
        if cancelled:
            name = self.current_command or "İşlem"
            self.bulk_selected_run = {
                **self.bulk_selected_run,
                "status": "CANCELLED",
                "message": f"{name} güvenli şekilde iptal edildi.",
            }
            self._add_activity(name, "İptal edildi", "Kullanıcı isteğiyle durduruldu")
            self._emit_state()
            return {"status": "OK", "message": f"{name} iptal edildi."}
        self.command_cancel_requested = False
        return {"status": "ERROR", "message": "İşlem iptal edilemedi."}

    def pdf_preview_payload(self, relative_path: str) -> dict[str, object]:
        return pdf_preview_api.get_pdf_preview_payload(self.project_root, relative_path)

    def laser_outputs(self) -> list[dict[str, str]]:
        return label_api.list_laser_outputs(self.project_root)

    def print_queue(self) -> list[dict[str, str]]:
        return print_queue_api.list_print_queue(self.project_root)

    def printer_profiles(self) -> list[dict[str, object]]:
        return printer_profile_api.list_printer_profiles(self.project_root)

    def save_printer_profile(self, profile: dict[str, object]) -> dict[str, object]:
        result = printer_profile_api.save_printer_profile(self.project_root, profile)
        self._append_log(result.get("message", "Yazıcı profili kaydedildi.") + "\n")
        self._emit_state()
        return result

    def delete_printer_profile(self, profile_id: str) -> dict[str, object]:
        result = printer_profile_api.delete_printer_profile(self.project_root, profile_id)
        self._append_log(result.get("message", "Yazıcı profili silindi.") + "\n")
        self._emit_state()
        return result

    def set_default_printer_profile(self, profile_id: str) -> dict[str, object]:
        result = printer_profile_api.set_default_printer_profile(self.project_root, profile_id)
        self._append_log(result.get("message", "Varsayılan yazıcı profili güncellendi.") + "\n")
        self._emit_state()
        return result

    def test_printer_profile(self, profile_id: str) -> dict[str, object]:
        result = printer_profile_api.test_printer_profile(self.project_root, profile_id)
        self._append_log(result.get("message", "Yazıcı profil testi pasif.") + "\n")
        return result

    def name_cut_queue(self) -> list[dict[str, object]]:
        return name_cut_queue_api.list_name_cut_queue_items(self.project_root)

    def name_cut_transfer_history(self) -> list[dict[str, object]]:
        return name_cut_queue_api.list_name_cut_transfer_history(self.project_root)

    def name_cut_export_history(self) -> list[dict[str, object]]:
        return name_cut_queue_api.list_name_cut_export_history(self.project_root)

    def save_name_cut_queue_items(self, payload: dict[str, object] | list[dict[str, object]]) -> dict[str, object]:
        result = name_cut_queue_api.save_name_cut_queue_items(self.project_root, payload)
        transfer = result.get("transfer") if isinstance(result.get("transfer"), dict) else {}
        if transfer:
            self._record_production_audit_event(production_audit_api.create_audit_event_from_bulk_batch(
                transfer,
                "bulk_sent_to_namecut_queue",
                result.get("message", "Toplu Üretim İsim Kesim hazırlık kuyruğuna aktarıldı."),
            ))
        for item in result.get("items", []) if isinstance(result.get("items"), list) else []:
            self._record_production_audit_event(production_audit_api.create_audit_event_from_namecut_item(
                item,
                "namecut_queue_created",
                "İsim Kesim hazırlık queue kaydı oluşturuldu. Lazer/RDWorks başlatılmadı.",
            ))
        duplicate_count = int(result.get("duplicate") or 0)
        if duplicate_count:
            self._record_production_audit_event({
                "event_type": "duplicate_detected",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "transfer_batch_id": result.get("transfer_batch_id", ""),
                "status": "duplicate",
                "severity": "warning",
                "message": f"{duplicate_count} İsim Kesim hazırlık kaydı duplicate olarak engellendi.",
                "metadata": result,
            })
        blocked_count = int(result.get("blocked") or 0)
        if blocked_count:
            self._record_production_audit_event({
                "event_type": "blocked_detected",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "transfer_batch_id": result.get("transfer_batch_id", ""),
                "status": "blocked",
                "severity": "blocked",
                "message": f"{blocked_count} İsim Kesim hazırlık kaydı üretime engel nedeniyle aktarılmadı.",
                "metadata": result,
            })
        self._append_log(result.get("message", "İsim Kesim hazırlık kuyruğu güncellendi.") + "\n")
        self._add_activity("İsim Kesim hazırlık kuyruğu", str(result.get("status", "OK")), result.get("message", ""))
        self._emit_state()
        return result

    def list_name_cut_queue_items(self, filters: dict[str, object] | None = None) -> list[dict[str, object]]:
        return name_cut_queue_api.list_name_cut_queue_items(self.project_root, filters)

    def get_name_cut_queue_item(self, item_id: str) -> dict[str, object]:
        return name_cut_queue_api.get_name_cut_queue_item(self.project_root, item_id)

    def update_name_cut_queue_item_status(self, item_id: str, status: str) -> dict[str, object]:
        result = name_cut_queue_api.update_name_cut_queue_item_status(self.project_root, item_id, status)
        item = result.get("item") if isinstance(result.get("item"), dict) else {"id": item_id, "status": status}
        self._record_production_audit_event(production_audit_api.create_audit_event_from_namecut_item(
            item,
            "namecut_status_updated",
            result.get("message", "İsim Kesim hazırlık durumu güncellendi."),
        ))
        self._append_log(result.get("message", "İsim Kesim hazırlık durumu güncellendi.") + "\n")
        self._emit_state()
        return result

    def mark_name_cut_queue_item_prepared(self, item_id: str) -> dict[str, object]:
        return self.update_name_cut_queue_item_status(item_id, "prepared")

    def list_name_cut_export_history(self) -> list[dict[str, object]]:
        return self.name_cut_export_history()

    def check_name_cut_queue_duplicate(self, duplicate_key: str) -> dict[str, object]:
        return name_cut_queue_api.check_name_cut_queue_duplicate(self.project_root, duplicate_key)

    def customer_orders(self) -> list[dict[str, object]]:
        return customer_order_api.list_customer_orders(self.project_root)

    def create_customer_order(self, data: dict[str, object]) -> dict[str, object]:
        result = customer_order_api.create_customer_order(self.project_root, data)
        self._append_log(result.get("message", "Sipariş kaydedildi.") + "\n")
        self._add_activity("Sipariş", str(result.get("status", "OK")), str(result.get("order", {}).get("customer_name", "")))
        self._emit_state()
        return result

    def update_customer_order_status(self, order_id: str, status: str) -> dict[str, object]:
        result = customer_order_api.update_customer_order_status(self.project_root, order_id, status)
        self._append_log(result.get("message", "Sipariş durumu güncellendi.") + "\n")
        self._emit_state()
        return result

    def create_customer_order_summary_pdf(self, order_id: str) -> dict[str, object]:
        result = customer_order_api.create_order_summary_pdf(self.project_root, order_id)
        self._append_log(result.get("message", "İş emri PDF'i oluşturuldu.") + "\n")
        self._emit_state()
        return result

    def trendyol_state(self) -> dict[str, object]:
        return {
            "settings": trendyol_api.get_settings(self.project_root),
            "summary": trendyol_api.summary(self.project_root),
            "mappings": trendyol_mapping_api.list_product_mappings(self.project_root),
            "mappingSuggestions": trendyol_api.list_mapping_suggestions(self.project_root),
            "suggestions": trendyol_api.list_suggestions(self.project_root),
            "questions": trendyol_api.list_questions(self.project_root),
        }

    def save_trendyol_settings(self, data: dict[str, object]) -> dict[str, object]:
        result = trendyol_api.save_settings(self.project_root, data)
        self._record_production_audit_event({
            "event_type": "trendyol_readonly_mode_confirmed",
            "source": "trendyol",
            "source_label": "Trendyol",
            "status": result.get("status", ""),
            "severity": "success" if result.get("status") == "OK" else "warning",
            "message": "Trendyol API ayarları read-only modda kaydedildi. Secret değerler audit/log içine yazılmadı.",
            "metadata": {
                "environment": (result.get("settings") or {}).get("environment"),
                "read_only_mode": True,
                "secret_masked": True,
                "marketplace_status_changed": False,
                "cargo_invoice_triggered": False,
            },
        })
        self._append_log(result.get("message", "Trendyol ayarları kaydedildi.") + "\n")
        self._emit_state()
        return result

    def test_trendyol_connection(self) -> dict[str, object]:
        result = trendyol_api.test_connection(self.project_root)
        self._append_log(result.get("message", "Trendyol bağlantı testi tamamlandı.") + "\n")
        self._emit_state()
        return result

    def sync_trendyol_recent_orders(self, days: int = 2) -> dict[str, object]:
        batch_id = f"trendyol-sync-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self._record_production_audit_event({
            "event_type": "trendyol_sync_started",
            "source": "trendyol",
            "source_label": "Trendyol",
            "batch_id": batch_id,
            "status": "started",
            "severity": "info",
            "message": "Trendyol read-only sipariş/soru sync başlatıldı. Canlı statü, kargo ve fatura tetiklenmez.",
            "metadata": {"days": days, "read_only_mode": True},
        })
        result = trendyol_api.sync_recent_orders(self.project_root, days=days, label_models=self.label_model_gallery())
        summary = result.get("sync_summary") if isinstance(result.get("sync_summary"), dict) else {}
        self._record_production_audit_event({
            "event_type": "trendyol_sync_completed" if result.get("status") == "OK" else "trendyol_sync_failed",
            "source": "trendyol",
            "source_label": "Trendyol",
            "batch_id": batch_id,
            "status": result.get("status", ""),
            "severity": "success" if result.get("status") == "OK" else "warning",
            "message": result.get("message", "Trendyol read-only sync tamamlandı."),
            "metadata": {
                "orders": summary.get("orders", 0),
                "messages": summary.get("messages", 0),
                "suggestions": len(result.get("suggestions") or []),
                "read_only_mode": True,
                "marketplace_status_changed": False,
                "cargo_invoice_triggered": False,
                "secret_masked": True,
            },
        })
        self._append_log(result.get("message", "Trendyol sipariş senkronu tamamlandı.") + "\n")
        self._emit_state()
        return result

    def sync_trendyol_questions(self) -> dict[str, object]:
        batch_id = f"trendyol-question-sync-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self._record_production_audit_event({
            "event_type": "trendyol_sync_started",
            "source": "trendyol",
            "source_label": "Trendyol",
            "batch_id": batch_id,
            "status": "started",
            "severity": "info",
            "message": "Trendyol read-only soru/mesaj sync başlatıldı. Otomatik cevap verilmez.",
            "metadata": {"read_only_mode": True, "sync_type": "questions"},
        })
        result = trendyol_api.sync_questions(self.project_root)
        summary = result.get("sync_summary") if isinstance(result.get("sync_summary"), dict) else {}
        self._record_production_audit_event({
            "event_type": "trendyol_sync_completed" if result.get("status") == "OK" else "trendyol_sync_failed",
            "source": "trendyol",
            "source_label": "Trendyol",
            "batch_id": batch_id,
            "status": result.get("status", ""),
            "severity": "success" if result.get("status") == "OK" else "warning",
            "message": result.get("message", "Trendyol soru/mesaj read-only sync tamamlandı."),
            "metadata": {
                "messages": summary.get("messages", len(result.get("questions") or [])),
                "suggestions": len(result.get("suggestions") or []),
                "read_only_mode": True,
                "marketplace_status_changed": False,
                "cargo_invoice_triggered": False,
                "secret_masked": True,
            },
        })
        self._append_log(result.get("message", "Trendyol soru/mesaj senkronu tamamlandı.") + "\n")
        self._emit_state()
        return result

    def upsert_trendyol_mapping(self, data: dict[str, object]) -> dict[str, object]:
        result = trendyol_mapping_api.upsert_product_mapping(self.project_root, data)
        self._append_log(result.get("message", "Trendyol ürün eşleştirmesi kaydedildi.") + "\n")
        self._emit_state()
        return result

    def export_trendyol_mappings(self) -> dict[str, object]:
        result = trendyol_mapping_api.export_product_mappings_to_excel(self.project_root)
        self._append_log(result.get("message", "Trendyol ürün eşleştirmeleri dışa aktarıldı.") + "\n")
        self._emit_state()
        return result

    def import_trendyol_mappings(self) -> dict[str, object]:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Trendyol Ürün Eşleştirme Dosyası Seç",
            str(self.project_root / "input"),
            "Eşleştirme Dosyaları (*.xlsx *.csv *.json)",
        )
        if not path:
            return {"status": "CANCELLED", "message": "Trendyol eşleştirme içe aktarma iptal edildi."}
        result = trendyol_mapping_api.import_product_mappings_from_file(self.project_root, path)
        self._append_log(result.get("message", "Trendyol ürün eşleştirmeleri içe aktarıldı.") + "\n")
        self._emit_state()
        return result

    def propose_trendyol_mappings_from_catalog(self) -> dict[str, object]:
        result = trendyol_api.propose_mapping_from_catalog(self.project_root, self.label_model_gallery())
        self._append_log(result.get("message", "Trendyol katalog eşleştirme önerileri hazırlandı.") + "\n")
        self._emit_state()
        return result

    def approve_trendyol_mapping_suggestion(self, suggestion_id: str, data: dict[str, object]) -> dict[str, object]:
        result = trendyol_api.approve_mapping_suggestion(self.project_root, suggestion_id, data)
        self._append_log(result.get("message", "Trendyol katalog önerisi eşleştirmeye dönüştürüldü.") + "\n")
        self._emit_state()
        return result

    def cache_trendyol_product_image(self, image_url: str) -> dict[str, object]:
        result = trendyol_api.cache_product_image(self.project_root, image_url)
        self._append_log(result.get("message", "Trendyol ürün görseli önbellek kontrolü tamamlandı.") + "\n")
        return result

    def import_trendyol_suggestion_to_customer_order(self, suggestion_id: str) -> dict[str, object]:
        result = trendyol_api.import_suggestion_to_customer_order(self.project_root, suggestion_id)
        self._append_log(result.get("message", "Trendyol siparişi üretim akışına aktarıldı.") + "\n")
        self._emit_state()
        return result

    def export_trendyol_ready_to_excel(self, suggestion_ids: list[str] | None = None) -> dict[str, object]:
        result = trendyol_api.export_ready_suggestions_to_excel(self.project_root, suggestion_ids)
        path = Path(str(result.get("path") or ""))
        if result.get("status") == "OK" and path.exists():
            self.selected_excel = path
        self._append_log(result.get("message", "Trendyol üretim Excel'i hazırlandı.") + "\n")
        self._emit_state()
        return result

    def import_trendyol_to_bulk_production(self, suggestion_ids: list[str] | None = None) -> dict[str, object]:
        result = trendyol_api.import_suggestions_to_bulk_production(self.project_root, suggestion_ids, self.label_model_gallery())
        for event in result.get("audit_events", []) if isinstance(result.get("audit_events"), list) else []:
            if isinstance(event, dict):
                self._record_production_audit_event(event)
        self._append_log(result.get("message", "Trendyol satırları Toplu Üretim hazırlığına aktarıldı.") + "\n")
        self._emit_state()
        return result

    def save_trendyol_operator_correction(self, suggestion_id: str, payload: dict[str, object]) -> dict[str, object]:
        result = trendyol_api.save_trendyol_operator_correction(self.project_root, suggestion_id, payload, self.label_model_gallery())
        for event in result.get("audit_events", []) if isinstance(result.get("audit_events"), list) else []:
            if isinstance(event, dict):
                self._record_production_audit_event(event)
        self._append_log(result.get("message", "Trendyol operatör düzeltmesi kaydedildi.") + "\n")
        self._emit_state()
        return result

    def reanalyze_trendyol_suggestion(self, suggestion_id: str) -> dict[str, object]:
        result = trendyol_api.reanalyze_trendyol_suggestion(self.project_root, suggestion_id)
        self._append_log(result.get("message", "Trendyol AI yeniden analiz tamamlandı.") + "\n")
        self._emit_state()
        return result

    def verify_trendyol_suggestion(self, suggestion_id: str, data: dict[str, object]) -> dict[str, object]:
        result = trendyol_api.verify_suggestion(self.project_root, suggestion_id, data)
        self._append_log(result.get("message", "Trendyol satırı doğrulandı.") + "\n")
        self._emit_state()
        return result

    def apply_trendyol_question_to_suggestion(self, suggestion_id: str, question_id: str) -> dict[str, object]:
        result = trendyol_api.apply_question_to_suggestion(self.project_root, suggestion_id, question_id)
        self._append_log(result.get("message", "Trendyol soru kanıtı satıra bağlandı.") + "\n")
        self._emit_state()
        return result

    def ignore_trendyol_question_for_suggestion(self, suggestion_id: str, question_id: str) -> dict[str, object]:
        result = trendyol_api.ignore_question_for_suggestion(self.project_root, suggestion_id, question_id)
        self._append_log(result.get("message", "Trendyol soru kanıtı yok sayıldı.") + "\n")
        self._emit_state()
        return result

    def bulk_label_usage(self) -> list[dict[str, object]]:
        return bulk_label_api.used_label_models(self.project_root, self.selected_excel, self.label_model_gallery())

    def bulk_preview_samples(self) -> list[dict[str, str]]:
        return bulk_label_api.preview_samples(self.project_root, self.selected_excel, self.label_model_gallery())

    def bulk_column_mapping(self) -> dict[str, object]:
        result = bulk_label_api.column_mapping(self.project_root, self.selected_excel)
        status = str(result.get("status") or "")
        if status:
            self._record_production_audit_event({
                "id": f"audit-bulk-column-mapping-{self.selected_excel.name}-{int(self.selected_excel.stat().st_mtime) if self.selected_excel.exists() else 'missing'}",
                "event_type": "bulk_validation_completed",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "status": status,
                "severity": "warning" if status.upper() == "WARNING" else "success",
                "message": "Excel kolon eşleştirme kontrolü tamamlandı.",
                "file_path": str(self.selected_excel),
                "metadata": result,
            })
        return result

    def bulk_gallery_items(self) -> list[dict[str, object]]:
        rows = bulk_label_api.bulk_gallery_items(self.project_root, self.selected_excel, self.label_model_gallery())
        if rows:
            blocked = sum(1 for row in rows if str(row.get("status") or "").upper() == "ERROR")
            review = sum(1 for row in rows if str(row.get("status") or "").upper() == "WARNING")
            self._record_production_audit_event({
                "id": f"audit-bulk-gallery-validation-{self.selected_excel.name}-{int(self.selected_excel.stat().st_mtime) if self.selected_excel.exists() else 'missing'}-{len(rows)}",
                "event_type": "bulk_validation_completed",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "status": "completed",
                "severity": "blocked" if blocked else "warning" if review else "success",
                "message": f"Toplu Önizleme Galerisi validasyonu tamamlandı: {len(rows)} kayıt.",
                "file_path": str(self.selected_excel),
                "metadata": {"total": len(rows), "blocked": blocked, "review": review},
            })
        return rows

    def combined_production_state(self) -> dict[str, object]:
        try:
            return combined_production_api.combined_production_state(
                self.project_root,
                self.selected_excel,
                self.label_model_gallery(),
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "ERROR",
                "message": f"Birleşik üretim kontrolü yapılamadı: {exc}",
                "summary": {},
                "orders": [],
                "label_items": [],
                "name_cut_items": [],
                "layout": {},
                "presets": [],
            }

    def prepare_name_cut_files(self, items: list[dict[str, object]], config: dict[str, object] | None = None) -> dict[str, object]:
        config = config or {}
        def _safe_qty(row: dict[str, object]) -> int:
            try:
                return max(1, int(float(str(row.get("quantity") or "1").replace(",", "."))))
            except (TypeError, ValueError):
                return 1
        try:
            result = combined_production_api.export_name_cut_batch(self.project_root, self.selected_excel, items, config)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": str(exc)}
        export_batch_id = result.get("export_batch_id") or result.get("batch_id") or config.get("export_batch_id", "")
        if str(result.get("status") or "").upper() != "OK":
            self._record_production_audit_event({
                "event_type": "namecut_export_preflight_failed",
                "source": "name_cut",
                "source_label": "İsim Kesim",
                "export_batch_id": export_batch_id,
                "status": "blocked",
                "severity": "blocked",
                "message": result.get("message", "İsim Kesim export kalite kontrolünden geçemedi."),
                "metadata": {
                    "export_preflight": result.get("export_preflight", {}),
                    "skipped_formats": result.get("skipped_formats", []),
                },
            })
        if str(result.get("status") or "").upper() == "OK":
            self._record_production_audit_event({
                "event_type": "namecut_export_preflight_passed",
                "source": "name_cut",
                "source_label": "İsim Kesim",
                "export_batch_id": result.get("export_batch_id") or result.get("batch_id"),
                "status": "passed",
                "severity": "success",
                "message": "İsim Kesim export preflight geçti. RDWorks/lazer başlatılmadı.",
                "metadata": {
                    "export_preflight": result.get("export_preflight", {}),
                    "rdworks_compatibility_qa": result.get("rdworks_compatibility_qa", {}),
                },
            })
            queue_ids = [str(item.get("id") or item.get("item_id") or "") for item in items if str(item.get("id") or item.get("item_id") or "").strip()]
            status_result = name_cut_queue_api.mark_name_cut_queue_items_exported(self.project_root, queue_ids)
            summary = result.get("layout", {}).get("summary", {}) if isinstance(result.get("layout"), dict) else {}
            export_files = {
                "svg": result.get("svg_path", ""),
                "dxf": result.get("dxf_path", ""),
                "pdf": result.get("pdf_preview", ""),
                "png": result.get("png_preview", ""),
                "manifest": result.get("manifest_path", ""),
                "plt": "",
            }
            history_result = name_cut_queue_api.record_name_cut_export_history(self.project_root, {
                "export_batch_id": result.get("export_batch_id") or result.get("batch_id"),
                "created_at": result.get("created_at"),
                "operator": config.get("operator", ""),
                "formats": config.get("formats") or ["svg", "dxf", "pdf"],
                "item_count": len(items),
                "quantity_total": summary.get("total_copies") or sum(_safe_qty(item) for item in items),
                "plate_count": summary.get("pages") or 0,
                "cut_direction": config.get("cut_direction", ""),
                "mirror_horizontal": config.get("mirror_cut", False),
                "mirror_vertical": config.get("mirror_vertical", False),
                "quality_summary": config.get("quality_summary") or {},
                "exported_files": export_files,
                "manifest_path": result.get("manifest_path", ""),
                "status": result.get("status"),
                "message": result.get("message"),
            })
            result["queue_status_update"] = status_result
            result["export_history"] = history_result.get("history", [])
            result["export_history_entry"] = history_result.get("entry", {})
            self._record_production_audit_event({
                "event_type": "namecut_export_manifest_created",
                "source": "name_cut",
                "source_label": "İsim Kesim",
                "export_batch_id": result.get("export_batch_id") or result.get("batch_id"),
                "status": "OK",
                "severity": "success",
                "message": "İsim Kesim manifest dosyası oluşturuldu. RDWorks/lazer başlatılmadı.",
                "file_path": result.get("manifest_path", ""),
                "metadata": {
                    "manifest_path": result.get("manifest_path", ""),
                    "rdworks_compatibility_qa": result.get("rdworks_compatibility_qa", {}),
                },
            })
            for skipped_format in result.get("skipped_formats", []) or []:
                self._record_production_audit_event({
                    "event_type": "namecut_export_format_skipped",
                    "source": "name_cut",
                    "source_label": "İsim Kesim",
                    "export_batch_id": result.get("export_batch_id") or result.get("batch_id"),
                    "status": "skipped",
                    "severity": "warning",
                    "message": f"{str(skipped_format).upper()} export bu fazda gerçek backend desteğine bağlı değil; sahte çıktı üretilmedi.",
                    "metadata": {"format": skipped_format},
                })
            self._record_production_audit_event({
                "event_type": "namecut_export_created",
                "source": "name_cut",
                "source_label": "İsim Kesim",
                "export_batch_id": result.get("export_batch_id") or result.get("batch_id"),
                "status": result.get("status"),
                "message": result.get("message", "İsim Kesim export paketi oluşturuldu. Lazer/RDWorks başlatılmadı."),
                "file_path": result.get("manifest_path", ""),
                "output_path": result.get("svg_path", "") or result.get("dxf_path", ""),
                "metadata": {
                    "export_files": export_files,
                    "queue_status_update": status_result,
                    "history_entry": history_result.get("entry", {}),
                    "quality_summary": config.get("quality_summary") or {},
                },
            })
        self._append_log(result.get("message", "İsim kesim dosyaları hazırlandı.") + "\n")
        self._add_activity("İsim kesim dosyası", str(result.get("status", "OK")), result.get("svg_path", ""))
        self._emit_state()
        return result

    def preview_name_cut_paths(self, items: list[dict[str, object]], config: dict[str, object] | None = None) -> dict[str, object]:
        try:
            return combined_production_api.preview_name_cut_paths(items, config or {})
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "ERROR",
                "message": f"İsim Kesim path önizlemesi oluşturulamadı: {exc}",
                "paths": [],
                "safety": {
                    "rdworks_auto_start": False,
                    "laser_auto_start": False,
                    "printer_auto_start": False,
                    "read_only_preview": True,
                },
            }

    def build_name_cut_production_scene(self, items: list[dict[str, object]], config: dict[str, object] | None = None) -> dict[str, object]:
        try:
            return combined_production_api.build_name_cut_production_scene(items, config or {})
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "ERROR",
                "message": f"İsim Kesim production scene oluşturulamadı: {exc}",
                "sourceItems": [],
                "objects": [],
                "placements": [],
                "paths": [],
                "safety": {
                    "rdworks_auto_start": False,
                    "laser_auto_start": False,
                    "printer_auto_start": False,
                    "read_only_preview": True,
                },
            }

    def list_corel_references(self, filters: dict[str, object] | None = None) -> dict[str, object]:
        try:
            return combined_production_api.list_corel_references(filters or {})
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referansları listelenemedi: {exc}", "references": []}

    def get_corel_reference(self, reference_id: str) -> dict[str, object]:
        try:
            return combined_production_api.get_corel_reference(reference_id)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referansı okunamadı: {exc}"}

    def update_corel_reference_label(self, reference_id: str, manual_name_label: str, approve_exact: bool = False) -> dict[str, object]:
        try:
            return combined_production_api.update_corel_reference_label(reference_id, manual_name_label, approve_exact)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referans etiketi kaydedilemedi: {exc}"}

    def approve_corel_exact_reference(self, reference_id: str) -> dict[str, object]:
        try:
            return combined_production_api.approve_corel_exact_reference(reference_id)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel exact referansı onaylanamadı: {exc}"}

    def unapprove_corel_reference(self, reference_id: str) -> dict[str, object]:
        try:
            return combined_production_api.unapprove_corel_reference(reference_id)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referans onayı kaldırılamadı: {exc}"}

    def mark_corel_reference_style_only(self, reference_id: str) -> dict[str, object]:
        try:
            return combined_production_api.mark_corel_reference_style_only(reference_id)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referansı stil kaydına alınamadı: {exc}"}

    def reject_corel_reference_candidate(self, reference_id: str) -> dict[str, object]:
        try:
            return combined_production_api.reject_corel_reference_candidate(reference_id)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referansı yanlış aday olarak işaretlenemedi: {exc}"}

    def save_operator_generated_corel_reference(self, payload: dict[str, object] | None = None) -> dict[str, object]:
        try:
            return combined_production_api.save_operator_generated_corel_reference(payload or {})
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Operator onaylı generated referans kaydedilemedi: {exc}"}

    def rebuild_corel_reference_index(self) -> dict[str, object]:
        try:
            return combined_production_api.rebuild_corel_reference_index()
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referans indeksi yenilenemedi: {exc}"}

    def search_corel_references(self, query: str = "") -> dict[str, object]:
        try:
            return combined_production_api.search_corel_references(query)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referans araması yapılamadı: {exc}", "references": []}

    def split_corel_reference(self, reference_id: str) -> dict[str, object]:
        try:
            return combined_production_api.split_corel_reference(reference_id)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referansı split edilemedi: {exc}"}

    def create_corel_reference_backup(self, reason: str = "manual") -> dict[str, object]:
        try:
            return combined_production_api.create_corel_reference_backup(reason)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referans backup oluşturulamadı: {exc}"}

    def list_corel_reference_backups(self) -> dict[str, object]:
        try:
            return combined_production_api.list_corel_reference_backups()
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referans backup listesi okunamadı: {exc}", "backups": []}

    def restore_corel_reference_backup(self, backup_path: str = "") -> dict[str, object]:
        try:
            return combined_production_api.restore_corel_reference_backup(backup_path)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referans backup geri yüklenemedi: {exc}"}

    def migrate_corel_reference_library(self) -> dict[str, object]:
        try:
            return combined_production_api.migrate_corel_reference_library()
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referans migration çalışmadı: {exc}"}

    def validate_corel_reference_library(self) -> dict[str, object]:
        try:
            return combined_production_api.validate_corel_reference_library()
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel referans validation çalışmadı: {exc}"}

    def corel_reference_data_security_status(self) -> dict[str, object]:
        try:
            return combined_production_api.corel_reference_data_security_status()
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel veri güvenliği durumu okunamadı: {exc}"}

    def resolve_exact_reference_by_name(self, input_name: str) -> dict[str, object]:
        try:
            return combined_production_api.resolve_exact_reference_by_name(input_name)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"Corel exact referans çözümlenemedi: {exc}"}

    def resolve_name_cut_path(self, input_name: str) -> dict[str, object]:
        try:
            return combined_production_api.resolve_name_cut_path(input_name)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"İsim Kesim path kaynağı çözümlenemedi: {exc}"}

    def render_bulk_preview_samples(self, row_numbers: list[str] | None = None) -> dict[str, object]:
        try:
            rows = bulk_label_api.render_preview_samples(
                self.project_root,
                self.selected_excel,
                self.label_model_gallery(),
                row_numbers=row_numbers,
            )
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": str(exc), "samples": []}
        return {
            "status": "OK",
            "message": "Gerçek satır mini önizlemeleri oluşturuldu.",
            "samples": rows,
        }

    def prepare_selected_bulk_excel(self, row_numbers: list[str]) -> dict[str, object]:
        return bulk_label_api.write_selected_rows_excel(self.project_root, self.selected_excel, row_numbers)

    def label_model_backups(self, template_path: str) -> list[dict[str, str]]:
        try:
            return template_api.list_label_model_backups(self.project_root, Path(template_path))
        except Exception:
            return []

    def compare_label_model_backup(self, template_path: str, backup_relative_path: str) -> dict[str, object]:
        try:
            return template_api.compare_label_model_backup(self.project_root, Path(template_path), backup_relative_path)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": str(exc)}

    def set_label_model_backup_note(self, template_path: str, backup_relative_path: str, note: str) -> dict[str, object]:
        try:
            return template_api.set_label_model_backup_note(self.project_root, Path(template_path), backup_relative_path, note)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": str(exc)}

    def compare_label_model_backup_pair(self, template_path: str, first_backup_relative_path: str, second_backup_relative_path: str) -> dict[str, object]:
        try:
            return template_api.compare_label_model_backup_pair(self.project_root, Path(template_path), first_backup_relative_path, second_backup_relative_path)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": str(exc)}

    def restore_label_model_backup(self, template_path: str, backup_relative_path: str) -> dict[str, object]:
        try:
            result = template_api.restore_label_model_backup(self.project_root, Path(template_path), backup_relative_path)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": str(exc)}
        self._append_log(result.get("message", "Model backup dosyasından geri yüklendi.") + "\n")
        self._emit_state()
        return result

    def add_label_outputs_to_print_queue(self) -> dict[str, str]:
        result = print_queue_api.add_label_outputs_to_queue(self.project_root, self.label_outputs())
        self._record_production_audit_event({
            "event_type": "print_queue_created",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "status": result.get("status", ""),
            "message": result.get("message", "Etiket çıktıları Yazdırma Sırası'na eklendi."),
            "output_path": result.get("queue_path", ""),
            "metadata": result,
        })
        self._append_log(result.get("message", "Etiket çıktıları yazdırma sırasına eklendi.") + "\n")
        self._add_activity("Yazdırma sırası", "Başarılı", result.get("message", "Etiket çıktıları eklendi"))
        self._emit_state()
        return result

    def add_pdf_output_to_print_queue(self, relative_path: str) -> dict[str, str]:
        result = print_queue_api.add_pdf_output_to_queue(self.project_root, relative_path)
        self._record_production_audit_event({
            "event_type": "print_queue_created" if result.get("status") in {"ADDED", "OK"} else "manual_review_required",
            "source": result.get("source", "label_studio"),
            "source_label": result.get("source_label", "Etiket Studio"),
            "queue_item_id": result.get("id", ""),
            "status": result.get("status", ""),
            "severity": "success" if result.get("status") in {"ADDED", "OK"} else "warning",
            "message": result.get("message", "PDF Yazdırma Sırası'na eklendi."),
            "output_path": relative_path,
            "metadata": result,
        })
        self._append_log(result.get("message", "PDF yazdırma sırasına eklendi.") + "\n")
        self._emit_state()
        return result

    def remove_from_print_queue(self, item_id: str) -> dict[str, str]:
        result = print_queue_api.remove_from_print_queue(self.project_root, item_id)
        self._record_production_audit_event({
            "event_type": "print_queue_status_updated",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": item_id,
            "status": "cancelled",
            "message": result.get("message", "Yazdırma Sırası kaydı iptal edildi."),
            "metadata": result,
        })
        self._append_log(result.get("message", "Yazdırma sırasından silindi.") + "\n")
        self._emit_state()
        return result

    def mark_queue_item_printed(self, item_id: str) -> dict[str, str]:
        result = print_queue_api.mark_queue_item_printed(self.project_root, item_id)
        self._record_production_audit_event({
            "event_type": "printed_marked",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": item_id,
            "status": "printed",
            "message": result.get("message", "İş yazdırıldı olarak işaretlendi."),
            "metadata": result,
        })
        self._append_log(result.get("message", "İş yazdırıldı olarak işaretlendi.") + "\n")
        self._emit_state()
        return result

    def mark_queue_item_pending(self, item_id: str) -> dict[str, str]:
        result = print_queue_api.mark_queue_item_pending(self.project_root, item_id)
        self._record_production_audit_event({
            "event_type": "print_queue_status_updated",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": item_id,
            "status": "requeued",
            "message": result.get("message", "İş yeniden kuyruğa alındı."),
            "metadata": result,
        })
        self._append_log(result.get("message", "İş yeniden beklemeye alındı.") + "\n")
        self._emit_state()
        return result

    def mark_queue_item_delivered(self, item_id: str) -> dict[str, str]:
        result = print_queue_api.mark_queue_item_delivered(self.project_root, item_id)
        self._record_production_audit_event({
            "event_type": "print_queue_status_updated",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": item_id,
            "status": "delivered",
            "message": result.get("message", "İş teslim edildi olarak işaretlendi."),
            "metadata": result,
        })
        self._append_log(result.get("message", "İş teslim edildi olarak işaretlendi.") + "\n")
        self._emit_state()
        return result

    def clear_print_queue(self) -> dict[str, str]:
        result = print_queue_api.clear_print_queue(self.project_root)
        self._append_log(result.get("message", "Yazdırma sırası temizlendi.") + "\n")
        self._emit_state()
        return result

    def print_queue_item_safe(self, item_id: str) -> dict[str, str]:
        result = print_queue_api.print_queue_item_safe(self.project_root, item_id, direct_print_enabled=False)
        self._record_production_audit_event({
            "event_type": "print_confirm_opened" if result.get("status") in {"MANUAL_PRINT_REQUIRED", "CONFIRMATION_REQUIRED"} else "manual_review_required",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": item_id,
            "status": result.get("status", ""),
            "severity": "info" if result.get("status") in {"MANUAL_PRINT_REQUIRED", "CONFIRMATION_REQUIRED"} else "warning",
            "message": result.get("message", "Güvenli yazdırma kontrolü açıldı."),
            "output_path": result.get("relative_path", ""),
            "metadata": {**result, "direct_print_enabled": False},
        })
        self._append_log(result.get("message", "Güvenli yazdırma yönlendirmesi hazır.") + "\n")
        return result

    def prepare_manual_print(self, item_id: str, profile_id: str) -> dict[str, object]:
        result = printer_profile_api.prepare_manual_print(self.project_root, item_id, profile_id)
        self._record_production_audit_event({
            "event_type": "manual_print_prepared" if result.get("status") == "OK" else "print_failed",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": item_id,
            "status": result.get("status", ""),
            "severity": "success" if result.get("status") == "OK" else "warning",
            "message": result.get("message", "Manuel print hazırlığı kontrol edildi."),
            "output_path": result.get("relative_path", ""),
            "metadata": {
                "printer_profile_id": profile_id,
                "auto_print_started": False,
                "laser_started": False,
                "rdworks_started": False,
                "result_status": result.get("status", ""),
            },
        })
        self._append_log(result.get("message", "Manuel print hazırlığı kontrol edildi.") + "\n")
        self._emit_state()
        return result

    def _ensure_excel(self) -> bool:
        if not self.selected_excel.exists():
            QMessageBox.warning(self, "Excel dosyası seçilmedi", "Excel dosyası seçilmedi veya bulunamadı.")
            return False
        return True

    def _print_mode(self) -> str:
        try:
            data = yaml.safe_load((self.project_root / "config" / "settings.yaml").read_text(encoding="utf-8")) or {}
            return str(data.get("print", {}).get("mode", "data_only")).strip()
        except Exception:
            return "data_only"

    def _open_folder(self, path: Path, label: str) -> None:
        from desktop.file_actions import open_folder

        self._open_result(open_folder(path), label)

    def _open_file(self, path: Path, label: str) -> None:
        if not path.exists():
            self._open_result((False, f"Dosya bulunamadı: {path}"), label)
            return
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606 - user explicitly requested opening the generated Excel file.
            self._open_result((True, f"Dosya açıldı: {path}"), label)
            return
        self._open_result((False, "Dosya açma sadece Windows için hazırlandı."), label)

    def _open_result(self, result: tuple[bool, str], label: str) -> None:
        ok, message = result
        self._append_log(message + "\n")
        self._add_activity(label, "Başarılı" if ok else "Bilgi", message)
        if not ok:
            QMessageBox.information(self, label, message)
        self._emit_state()

    def _add_activity(self, action: str, status: str, detail: str) -> None:
        self.activities.append(
            {"time": datetime.now().strftime("%H:%M:%S"), "action": action, "status": status, "detail": detail}
        )
        self.activities = self.activities[-10:]

    def _relative_or_name(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.project_root.resolve())).replace("\\", "/")
        except Exception:
            return path.name if path.name else str(path)

    def _non_empty(self, rows: list[dict[str, str]]) -> list[dict[str, str]]:
        return [row for row in rows if any((value or "").strip() for value in row.values())]
