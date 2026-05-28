from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config_loader import load_settings
from models import Order, PRINT
from label_designer.pdf_exporter import export_label_pdf
from label_designer.preview_exporter import export_label_png
from label_designer.settings_resolver import resolve_label_settings
from label_designer.template_loader import load_template


TEXT_ALIGNS = ["left", "center", "right"]
VERTICAL_ALIGNS = ["top", "middle", "bottom"]
VERTICAL_TO_RENDER = {"middle": "center"}
RENDER_TO_VERTICAL = {"center": "middle"}
SUPPORTED_FIELD_COLUMNS = {
    "label_text",
    "date_text",
    "note_text",
    "custom_text_1",
    "custom_text_2",
    "custom_text_3",
}
FIELD_PRESETS = {
    "name": ("İsim", "{{LABEL_TEXT}}", "label_text"),
    "date": ("Tarih", "{{DATE_TEXT}}", "date_text"),
    "note": ("Not", "{{NOTE_TEXT}}", "note_text"),
    "custom": ("Özel Metin 1", "{{CUSTOM_TEXT_1}}", "custom_text_1"),
}


@dataclass(frozen=True)
class TemplateSaveResult:
    target_path: Path
    backup_path: Path | None


class TemplateEditorError(ValueError):
    pass


def list_design_templates(project_root: Path) -> list[Path]:
    designs_dir = project_root / "templates" / "designs"
    if not designs_dir.exists():
        return []
    return sorted(path for path in designs_dir.glob("*.json") if path.parent.name != "backups")


def load_template_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TemplateEditorError("Şablon JSON object olmalıdır.")
    data.setdefault("elements", [])
    if not isinstance(data["elements"], list):
        raise TemplateEditorError("Şablon elements alanı liste olmalıdır.")
    return data


def template_target_path(project_root: Path, data: dict[str, Any]) -> Path:
    model_no = _required_text(data, "model_no")
    template_no = _required_text(data, "template_no")
    label_variant = _required_text(data, "label_variant")
    filename = f"{model_no}_{template_no}_{label_variant}".lower().replace(" ", "_") + ".json"
    return project_root / "templates" / "designs" / filename


def save_template_with_backup(project_root: Path, data: dict[str, Any], overwrite: bool = False) -> TemplateSaveResult:
    validate_template_data(project_root, data)
    target = template_target_path(project_root, data)
    target.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = None
    if target.exists():
        if not overwrite:
            raise TemplateEditorError(f"Şablon zaten var: {target.name}")
        backup_dir = target.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = backup_dir / f"{target.stem}_{stamp}.json"
        shutil.copy2(target, backup_path)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return TemplateSaveResult(target_path=target, backup_path=backup_path)


def validate_template_data(project_root: Path, data: dict[str, Any]) -> None:
    width_key = "label_width_mm" if data.get("label_width_mm") not in {None, ""} else "canvas_width_mm"
    height_key = "label_height_mm" if data.get("label_height_mm") not in {None, ""} else "canvas_height_mm"
    width = _positive_float(data, width_key, None)
    height = _positive_float(data, height_key, None)
    if width <= 0 or height <= 0:
        raise TemplateEditorError("Etiket genişliği ve yüksekliği 0'dan büyük olmalıdır.")

    background_image = str(data.get("background_image", "") or "").strip()
    if background_image:
        background_path = _safe_project_relative_path(project_root, background_image)
        try:
            background_path.relative_to(project_root / "assets")
        except ValueError as exc:
            raise TemplateEditorError("Arka plan görseli assets klasörü içinde olmalıdır.") from exc

    for field in data.get("fields", []):
        if not isinstance(field, dict):
            raise TemplateEditorError("Değişken yazı alanları object olmalıdır.")
        _validate_field(field, width, height)

    for element in data.get("elements", []):
        if not isinstance(element, dict):
            raise TemplateEditorError("Şablon elementleri object olmalıdır.")
        element_type = str(element.get("type", ""))
        if element_type == "text":
            _validate_text_element(element, width, height)
        elif element_type == "line":
            _validate_line_element(element, width, height)
        elif element_type == "rectangle":
            _validate_rectangle_element(element, width, height)


def update_text_element(data: dict[str, Any], **values: Any) -> None:
    text = find_label_text_element(data, create=True)
    text.update(
        {
            "type": "text",
            "id": "label_text",
            "placeholder": "{{LABEL_TEXT}}",
            "x_mm": values["x_mm"],
            "y_mm": values["y_mm"],
            "width_mm": values["width_mm"],
            "height_mm": values["height_mm"],
            "font_family": values["font_family"],
            "font_size": values["font_size"],
            "color": values["color"],
            "bold": values["bold"],
            "italic": values["italic"],
            "align": values["align"],
            "vertical_align": VERTICAL_TO_RENDER.get(values["vertical_align"], values["vertical_align"]),
            "rotation": 0,
        }
    )


def add_variable_field(data: dict[str, Any], field_type: str, label_width: float | None = None, label_height: float | None = None) -> dict[str, Any]:
    field_name, placeholder, excel_column = FIELD_PRESETS[field_type]
    width = float(label_width or data.get("label_width_mm") or data.get("canvas_width_mm") or 50)
    height = float(label_height or data.get("label_height_mm") or data.get("canvas_height_mm") or 30)
    existing_same = sum(1 for field in data.get("fields", []) if str(field.get("excel_column", "")) == excel_column)
    existing_custom = sum(1 for field in data.get("fields", []) if str(field.get("excel_column", "")).startswith("custom_text_"))
    defaults = {
        "name": {"x_mm": 10.0, "y_mm": 10.0, "width_mm": 30.0, "height_mm": 6.0, "font_size": 14},
        "date": {"x_mm": 17.0, "y_mm": 17.0, "width_mm": 16.0, "height_mm": 4.0, "font_size": 8},
        "note": {"x_mm": 12.0, "y_mm": 22.0, "width_mm": 26.0, "height_mm": 4.0, "font_size": 8},
        "custom": {"x_mm": 12.0, "y_mm": 22.0, "width_mm": 26.0, "height_mm": 4.0, "font_size": 8},
    }
    if field_type == "custom":
        index = min(existing_custom + 1, 3)
        field_name = f"Özel Metin {index}"
        placeholder = "{{CUSTOM_TEXT_" + str(index) + "}}"
        excel_column = f"custom_text_{index}"
    elif existing_same:
        field_name = f"{field_name} {existing_same + 1}"
    preset = defaults[field_type]
    field_width = min(float(preset["width_mm"]), width)
    field_height = min(float(preset["height_mm"]), height)
    x_mm = min(float(preset["x_mm"]), max(width - field_width, 0))
    y_mm = min(float(preset["y_mm"]), max(height - field_height, 0))
    field = {
        "field_name": field_name,
        "placeholder": placeholder,
        "excel_column": excel_column,
        "x_mm": round(x_mm, 2),
        "y_mm": round(y_mm, 2),
        "width_mm": round(field_width, 2),
        "height_mm": round(field_height, 2),
        "font_family": "Segoe UI",
        "font_path": "",
        "font_size": preset["font_size"],
        "color": "#111111",
        "bold": False,
        "italic": False,
        "align": "center",
        "vertical_align": "middle",
    }
    data.setdefault("fields", []).append(field)
    return field


def remove_variable_field(data: dict[str, Any], index: int) -> dict[str, Any]:
    fields = data.setdefault("fields", [])
    if index < 0 or index >= len(fields):
        raise TemplateEditorError("Silinecek alan bulunamadı.")
    return fields.pop(index)


def update_variable_field(data: dict[str, Any], index: int, **values: Any) -> None:
    fields = data.setdefault("fields", [])
    if index < 0 or index >= len(fields):
        raise TemplateEditorError("Düzenlenecek alan bulunamadı.")
    fields[index].update(values)


def import_font_file(project_root: Path, source_font: Path, overwrite: bool = False) -> str:
    if source_font.suffix.lower() not in {".ttf", ".otf"}:
        raise TemplateEditorError("Font dosyası TTF veya OTF olmalıdır.")
    if not source_font.exists():
        raise FileNotFoundError(f"Font dosyası bulunamadı: {source_font}")
    target_dir = project_root / "assets" / "fonts"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source_font.name
    if target.exists() and not overwrite:
        return str(target.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    if source_font.resolve() != target.resolve():
        shutil.copy2(source_font, target)
    return str(target.resolve().relative_to(project_root.resolve())).replace("\\", "/")


def update_top_line(data: dict[str, Any], **values: Any) -> None:
    line = _find_element(data, "top_rule", "line", create=True)
    line.update(
        {
            "type": "line",
            "id": "top_rule",
            "visible": values["visible"],
            "x1_mm": values["x_mm"],
            "y1_mm": values["y_mm"],
            "x2_mm": values["x_mm"] + values["width_mm"],
            "y2_mm": values["y_mm"],
            "color": values["color"],
            "stroke_width": values["thickness_mm"],
        }
    )


def update_border(data: dict[str, Any], **values: Any) -> None:
    width = float(data.get("label_width_mm") or data.get("canvas_width_mm") or 50)
    height = float(data.get("label_height_mm") or data.get("canvas_height_mm") or 30)
    border = _find_element(data, "border", "rectangle", create=True)
    border.update(
        {
            "type": "rectangle",
            "id": "border",
            "visible": values["visible"],
            "x_mm": 0,
            "y_mm": 0,
            "width_mm": width,
            "height_mm": height,
            "fill_color": "transparent",
            "stroke_color": values["color"],
            "stroke_width": values["thickness_mm"],
        }
    )


def find_label_text_element(data: dict[str, Any], create: bool = False) -> dict[str, Any]:
    for element in data.get("elements", []):
        if not isinstance(element, dict):
            continue
        if element.get("type") == "text" and element.get("id") == "label_text":
            return element
    for element in data.get("elements", []):
        if isinstance(element, dict) and element.get("type") == "text" and "{{ORDER_NO}}" not in str(element.get("placeholder", "")):
            return element
    if not create:
        raise TemplateEditorError("Düzenlenecek label_text alanı bulunamadı.")
    element = {
        "type": "text",
        "id": "label_text",
        "placeholder": "{{LABEL_TEXT}}",
        "x_mm": 10,
        "y_mm": 10,
        "width_mm": 30,
        "height_mm": 6,
        "font_family": "Segoe UI",
        "font_size": 14,
        "color": "#111111",
        "bold": False,
        "italic": False,
        "align": "center",
        "vertical_align": "center",
        "rotation": 0,
    }
    data.setdefault("elements", []).append(element)
    return element


def render_sample_template(
    project_root: Path,
    template_path: Path,
    test_text: str,
    output_dir: Path,
    field_values: dict[str, str] | None = None,
) -> tuple[Path, Path]:
    settings = load_settings(project_root / "config" / "settings.yaml")
    template = load_template(template_path)
    label_settings = resolve_label_settings(template, settings)
    source = {
        "label_text": test_text,
        "date_text": "12.05.2026",
        "note_text": "Söz Hatırası",
        "custom_text_1": "Gold",
        "custom_text_2": "No:7",
        "custom_text_3": "Teşekkürler",
    }
    source.update(field_values or {})
    order = Order(
        row_number=0,
        order_no="SAMPLE",
        buyer_name="Önizleme",
        product_name="Etiket Önizleme",
        model_no=template.model_no,
        template_no=template.template_no,
        process_type=PRINT,
        personalization_type="LABEL",
        label_variant=template.label_variant,
        label_text=test_text,
        laser_text="",
        quantity=1,
        material_type="",
        material_thickness_mm="",
        extra_chocolate_qty=0,
        extra_madlen_qty=0,
        production_note="",
        needs_review="",
        status="NEW",
        source=source,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"sample_{template.template_id}.pdf"
    png_path = output_dir / f"sample_{template.template_id}.png"
    export_label_pdf(pdf_path, template, order, date.today(), template.source_file.parent, label_settings)
    export_label_png(png_path, template, order, date.today(), template.source_file.parent, label_settings)
    return pdf_path, png_path


def render_sample_template_data(
    project_root: Path,
    data: dict[str, Any],
    test_text: str,
    output_dir: Path,
    field_values: dict[str, str] | None = None,
) -> tuple[Path, Path]:
    preview_path = project_root / "templates" / "designs" / "__editor_preview__.json"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        return render_sample_template(project_root, preview_path, test_text, output_dir, field_values=field_values)
    finally:
        preview_path.unlink(missing_ok=True)


class LabelTemplateEditorDialog(QDialog):
    saved = Signal()

    def __init__(self, project_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_root = project_root
        self.current_path: Path | None = None
        self.data: dict[str, Any] | None = None
        self.current_field_index = 0
        self.setWindowTitle("Etiket Şablonu Düzenle")
        self.setMinimumWidth(820)
        self._build()
        self._load_template_list()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Etiket Şablonu Düzenleme")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        top = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self._template_changed)
        top.addWidget(QLabel("Şablon"))
        top.addWidget(self.template_combo, 1)
        reload_btn = QPushButton("Yenile")
        reload_btn.setObjectName("LightButton")
        reload_btn.clicked.connect(self._load_template_list)
        top.addWidget(reload_btn)
        layout.addLayout(top)

        layout.addLayout(self._field_manager())

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        grid.addLayout(self._background_form(), 0, 0)
        grid.addLayout(self._text_form(), 0, 1)
        grid.addLayout(self._decor_form(), 1, 0, 1, 2)
        layout.addLayout(grid)

        preview_row = QHBoxLayout()
        self.test_text = QLineEdit("Ayşe & Mehmet")
        preview_row.addWidget(QLabel("Test yazısı"))
        preview_row.addWidget(self.test_text, 1)
        preview = QPushButton("Önizleme Oluştur")
        preview.setObjectName("LightButton")
        preview.clicked.connect(self._generate_sample)
        preview_row.addWidget(preview)
        layout.addLayout(preview_row)

        buttons = QHBoxLayout()
        buttons.addStretch()
        sample = QPushButton("Sample PDF/PNG Oluştur")
        sample.setObjectName("LightButton")
        sample.clicked.connect(self._generate_sample)
        save = QPushButton("Şablonu Kaydet")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save)
        buttons.addWidget(sample)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _field_manager(self) -> QVBoxLayout:
        box = QVBoxLayout()
        row = QHBoxLayout()
        self.field_combo = QComboBox()
        self.field_combo.currentIndexChanged.connect(self._field_changed)
        row.addWidget(QLabel("Değişken Yazı Alanları"))
        row.addWidget(self.field_combo, 1)
        delete_btn = QPushButton("Seçili Alanı Sil")
        delete_btn.setObjectName("LightButton")
        delete_btn.clicked.connect(self._delete_selected_field)
        row.addWidget(delete_btn)
        box.addLayout(row)
        add_row = QHBoxLayout()
        for label, kind in (
            ("İsim Alanı Ekle", "name"),
            ("Tarih Alanı Ekle", "date"),
            ("Not Alanı Ekle", "note"),
            ("Özel Metin Alanı Ekle", "custom"),
        ):
            button = QPushButton(label)
            button.setObjectName("LightButton")
            button.clicked.connect(lambda _checked=False, field_kind=kind: self._add_field(field_kind))
            add_row.addWidget(button)
        box.addLayout(add_row)
        return box

    def _background_form(self) -> QFormLayout:
        form = QFormLayout()
        self.background_enabled = QCheckBox("Arka planı kullan")
        self.background_path = QLineEdit()
        select = QPushButton("Görsel Seç")
        select.setObjectName("LightButton")
        select.clicked.connect(self._select_background)
        remove = QPushButton("Kaldır")
        remove.setObjectName("LightButton")
        remove.clicked.connect(lambda: self.background_path.setText(""))
        row = QHBoxLayout()
        row.addWidget(self.background_path, 1)
        row.addWidget(select)
        row.addWidget(remove)
        form.addRow("Arka plan", row)
        form.addRow("", self.background_enabled)
        return form

    def _text_form(self) -> QFormLayout:
        form = QFormLayout()
        self.text_x = self._double(0, 500, 5)
        self.text_y = self._double(0, 500, 9)
        self.text_w = self._double(0.1, 500, 40)
        self.text_h = self._double(0.1, 500, 11)
        self.font_family = QLineEdit("Segoe UI")
        self.font_path = QLineEdit("")
        self.font_size = self._double(1, 200, 13)
        font_btn = QPushButton("Font Yükle")
        font_btn.setObjectName("LightButton")
        font_btn.clicked.connect(self._load_font)
        font_row = QHBoxLayout()
        font_row.addWidget(self.font_family)
        font_row.addWidget(font_btn)
        self.text_color = QLineEdit("#2B2118")
        color_btn = QPushButton("Renk")
        color_btn.setObjectName("LightButton")
        color_btn.clicked.connect(lambda: self._pick_color(self.text_color))
        color_row = QHBoxLayout()
        color_row.addWidget(self.text_color)
        color_row.addWidget(color_btn)
        self.bold = QCheckBox("Bold")
        self.italic = QCheckBox("Italic")
        checks = QHBoxLayout()
        checks.addWidget(self.bold)
        checks.addWidget(self.italic)
        self.align = QComboBox()
        self.align.addItems(TEXT_ALIGNS)
        self.vertical_align = QComboBox()
        self.vertical_align.addItems(VERTICAL_ALIGNS)
        for label, widget in [
            ("X (mm)", self.text_x),
            ("Y (mm)", self.text_y),
            ("Genişlik (mm)", self.text_w),
            ("Yükseklik (mm)", self.text_h),
            ("Font", font_row),
            ("Font dosyası", self.font_path),
            ("Font boyutu", self.font_size),
            ("Yazı rengi", color_row),
            ("Stil", checks),
            ("Hizalama", self.align),
            ("Dikey hizalama", self.vertical_align),
        ]:
            form.addRow(label, widget)
        return form

    def _decor_form(self) -> QFormLayout:
        form = QFormLayout()
        self.line_visible = QCheckBox("Üst altın çizgiyi göster")
        self.line_x = self._double(0, 500, 6)
        self.line_y = self._double(0, 500, 7)
        self.line_w = self._double(0.1, 500, 38)
        self.line_t = self._double(0.05, 20, 0.25)
        self.line_color = QLineEdit("#B9973E")
        line_grid = QGridLayout()
        for index, (label, widget) in enumerate(
            [
                ("X", self.line_x),
                ("Y", self.line_y),
                ("Genişlik", self.line_w),
                ("Kalınlık", self.line_t),
                ("Renk", self.line_color),
            ]
        ):
            line_grid.addWidget(QLabel(label), 0, index)
            line_grid.addWidget(widget, 1, index)
        self.border_visible = QCheckBox("Kenarlığı göster")
        self.border_color = QLineEdit("#B9973E")
        self.border_t = self._double(0.05, 20, 0.35)
        border_row = QHBoxLayout()
        border_row.addWidget(QLabel("Renk"))
        border_row.addWidget(self.border_color)
        border_row.addWidget(QLabel("Kalınlık"))
        border_row.addWidget(self.border_t)
        form.addRow("", self.line_visible)
        form.addRow("Üst çizgi", line_grid)
        form.addRow("", self.border_visible)
        form.addRow("Kenarlık", border_row)
        return form

    def _load_template_list(self) -> None:
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        for path in list_design_templates(self.project_root):
            self.template_combo.addItem(path.name, str(path))
        self.template_combo.blockSignals(False)
        if self.template_combo.count():
            self.template_combo.setCurrentIndex(0)
            self._template_changed(0)

    def _template_changed(self, index: int) -> None:
        path_text = self.template_combo.itemData(index)
        if not path_text:
            return
        try:
            self.current_path = Path(path_text)
            self.data = load_template_data(self.current_path)
            self._populate()
        except Exception as exc:  # noqa: BLE001 - user-facing editor error.
            QMessageBox.warning(self, "Şablon okunamadı", str(exc))

    def _populate(self) -> None:
        if self.data is None:
            return
        self.background_enabled.setChecked(bool(self.data.get("background_enabled", True)))
        self.background_path.setText(str(self.data.get("background_image", "") or ""))
        self._ensure_fields()
        self._populate_field_combo()
        self._populate_selected_field()
        line = _find_element(self.data, "top_rule", "line", create=True)
        self.line_visible.setChecked(line.get("visible") is not False)
        self.line_x.setValue(float(line.get("x1_mm", 6)))
        self.line_y.setValue(float(line.get("y1_mm", 7)))
        self.line_w.setValue(max(0.1, float(line.get("x2_mm", 44)) - float(line.get("x1_mm", 6))))
        self.line_t.setValue(float(line.get("stroke_width", 0.25)))
        self.line_color.setText(str(line.get("color", "#B9973E")))
        border = _find_element(self.data, "border", "rectangle", create=True)
        self.border_visible.setChecked(border.get("visible") is not False)
        self.border_color.setText(str(border.get("stroke_color", "#B9973E")))
        self.border_t.setValue(float(border.get("stroke_width", 0.35)))

    def _ensure_fields(self) -> None:
        if self.data is None:
            return
        fields = self.data.setdefault("fields", [])
        if fields:
            return
        try:
            text = find_label_text_element(self.data, create=True)
            fields.append(
                {
                    "field_name": "İsim",
                    "placeholder": text.get("placeholder", "{{LABEL_TEXT}}"),
                    "excel_column": text.get("excel_column", "label_text") or "label_text",
                    "x_mm": text.get("x_mm", 5),
                    "y_mm": text.get("y_mm", 9),
                    "width_mm": text.get("width_mm", 40),
                    "height_mm": text.get("height_mm", 11),
                    "font_family": text.get("font_family", "Segoe UI"),
                    "font_path": text.get("font_path", ""),
                    "font_size": text.get("font_size", 13),
                    "color": text.get("color", "#2B2118"),
                    "bold": text.get("bold", False),
                    "italic": text.get("italic", False),
                    "align": text.get("align", "center"),
                    "vertical_align": RENDER_TO_VERTICAL.get(str(text.get("vertical_align", "middle")), str(text.get("vertical_align", "middle"))),
                }
            )
        except Exception:
            add_variable_field(self.data, "name")

    def _populate_field_combo(self) -> None:
        if self.data is None:
            return
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        for index, field in enumerate(self.data.get("fields", [])):
            label = f"{index + 1}. {field.get('field_name') or field.get('excel_column') or 'Yazı alanı'}"
            self.field_combo.addItem(label, index)
        self.field_combo.blockSignals(False)
        if self.field_combo.count():
            self.current_field_index = min(self.current_field_index, self.field_combo.count() - 1)
            self.field_combo.setCurrentIndex(self.current_field_index)

    def _populate_selected_field(self) -> None:
        if self.data is None or not self.data.get("fields"):
            return
        field = self.data["fields"][self.current_field_index]
        self.text_x.setValue(float(field.get("x_mm", 5)))
        self.text_y.setValue(float(field.get("y_mm", 9)))
        self.text_w.setValue(float(field.get("width_mm", 40)))
        self.text_h.setValue(float(field.get("height_mm", 11)))
        self.font_family.setText(str(field.get("font_family", "Segoe UI")))
        self.font_path.setText(str(field.get("font_path", "")))
        self.font_size.setValue(float(field.get("font_size", 13)))
        self.text_color.setText(str(field.get("color", "#2B2118")))
        self.bold.setChecked(bool(field.get("bold", False)))
        self.italic.setChecked(bool(field.get("italic", False)))
        self.align.setCurrentText(str(field.get("align", "center")))
        self.vertical_align.setCurrentText(str(field.get("vertical_align", "middle")))

    def _field_changed(self, index: int) -> None:
        if index < 0:
            return
        self.current_field_index = index
        self._populate_selected_field()

    def _add_field(self, kind: str) -> None:
        if self.data is None:
            return
        add_variable_field(self.data, kind)
        self.current_field_index = len(self.data["fields"]) - 1
        self._populate_field_combo()
        self._populate_selected_field()

    def _delete_selected_field(self) -> None:
        if self.data is None or not self.data.get("fields"):
            return
        if len(self.data["fields"]) == 1:
            QMessageBox.information(self, "Alan silinemez", "En az bir değişken yazı alanı kalmalıdır.")
            return
        remove_variable_field(self.data, self.current_field_index)
        self.current_field_index = max(0, self.current_field_index - 1)
        self._populate_field_combo()
        self._populate_selected_field()

    def _apply_form(self) -> dict[str, Any]:
        if self.data is None:
            raise TemplateEditorError("Önce bir şablon seçin.")
        data = json.loads(json.dumps(self.data, ensure_ascii=False))
        data["background_enabled"] = self.background_enabled.isChecked()
        data["background_image"] = self.background_path.text().strip()
        self._ensure_fields()
        data.setdefault("fields", json.loads(json.dumps(self.data.get("fields", []), ensure_ascii=False)))
        original_field = data["fields"][self.current_field_index]
        update_variable_field(
            data,
            self.current_field_index,
            field_name=str(original_field.get("field_name", "İsim")),
            placeholder=str(original_field.get("placeholder", "{{LABEL_TEXT}}")),
            excel_column=str(original_field.get("excel_column", "label_text")),
            x_mm=self.text_x.value(),
            y_mm=self.text_y.value(),
            width_mm=self.text_w.value(),
            height_mm=self.text_h.value(),
            font_family=self.font_family.text().strip() or "Segoe UI",
            font_path=self.font_path.text().strip(),
            font_size=self.font_size.value(),
            color=self.text_color.text().strip() or "#111111",
            bold=self.bold.isChecked(),
            italic=self.italic.isChecked(),
            align=self.align.currentText(),
            vertical_align=self.vertical_align.currentText(),
        )
        data["elements"] = [
            element
            for element in data.get("elements", [])
            if not (isinstance(element, dict) and element.get("type") == "text")
        ]
        update_top_line(
            data,
            visible=self.line_visible.isChecked(),
            x_mm=self.line_x.value(),
            y_mm=self.line_y.value(),
            width_mm=self.line_w.value(),
            thickness_mm=self.line_t.value(),
            color=self.line_color.text().strip() or "#B9973E",
        )
        update_border(
            data,
            visible=self.border_visible.isChecked(),
            color=self.border_color.text().strip() or "#B9973E",
            thickness_mm=self.border_t.value(),
        )
        validate_template_data(self.project_root, data)
        return data

    def _save(self) -> None:
        try:
            data = self._apply_form()
            target = template_target_path(self.project_root, data)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Şablon hatası", str(exc))
            return
        if target.exists():
            answer = QMessageBox.question(
                self,
                "Şablon üzerine yazılsın mı",
                f"{target.name} zaten var.\n\nÜzerine yazmadan önce backups klasörüne kopya alınacak. Devam edilsin mi",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        try:
            result = save_template_with_backup(self.project_root, data, overwrite=True)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Şablon kaydedilemedi", str(exc))
            return
        self.data = data
        self.current_path = result.target_path
        backup_msg = f"\nBackup: {result.backup_path}" if result.backup_path else ""
        QMessageBox.information(self, "Şablon kaydedildi", f"Şablon kaydedildi:\n{result.target_path}{backup_msg}")
        self.saved.emit()
        self._load_template_list()

    def _generate_sample(self) -> None:
        try:
            data = self._apply_form()
            output_dir = self.project_root / "output" / date.today().strftime("%Y-%m-%d") / "preview" / "model_editor"
            pdf_path, png_path = render_sample_template_data(self.project_root, data, self.test_text.text().strip() or "Ayşe & Mehmet", output_dir)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Önizleme oluşturulamadı", str(exc))
            return
        QMessageBox.information(self, "Önizleme hazır", f"PDF:\n{pdf_path}\n\nPNG:\n{png_path}")
        self.saved.emit()

    def _select_background(self) -> None:
        path_text, _ = QFileDialog.getOpenFileName(
            self,
            "Arka plan görseli seç",
            str(self.project_root / "assets" / "label_backgrounds"),
            "Görseller (*.png *.jpg *.jpeg *.webp)",
        )
        if not path_text:
            return
        source = Path(path_text)
        assets_dir = self.project_root / "assets" / "label_backgrounds"
        assets_dir.mkdir(parents=True, exist_ok=True)
        try:
            if source.resolve().is_relative_to((self.project_root / "assets").resolve()):
                target = source
            else:
                target = assets_dir / source.name
                if target.exists():
                    answer = QMessageBox.question(
                        self,
                        "Görsel zaten var",
                        f"{target.name} zaten var. Üzerine yazılsın mı",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No,
                    )
                    if answer != QMessageBox.Yes:
                        return
                shutil.copy2(source, target)
            self.background_path.setText(str(target.resolve().relative_to(self.project_root.resolve())).replace("\\", "/"))
            self.background_enabled.setChecked(True)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Arka plan seçilemedi", str(exc))

    def _pick_color(self, target: QLineEdit) -> None:
        color = QColorDialog.getColor(QColor(target.text() or "#111111"), self, "Renk seç")
        if color.isValid():
            target.setText(color.name())

    def _load_font(self) -> None:
        path_text, _ = QFileDialog.getOpenFileName(
            self,
            "Font dosyası seç",
            str(self.project_root / "assets" / "fonts"),
            "Font dosyaları (*.ttf *.otf)",
        )
        if not path_text:
            return
        source = Path(path_text)
        target = self.project_root / "assets" / "fonts" / source.name
        overwrite = False
        if target.exists() and source.resolve() != target.resolve():
            answer = QMessageBox.question(
                self,
                "Font zaten var",
                f"{target.name} zaten var. Üzerine yazılsın mı",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            overwrite = answer == QMessageBox.Yes
        try:
            relative_path = import_font_file(self.project_root, source, overwrite=overwrite)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Font yüklenemedi", str(exc))
            return
        self.font_path.setText(relative_path)
        if not self.font_family.text().strip() or self.font_family.text().strip() == "Segoe UI":
            self.font_family.setText(source.stem.replace("_", " ").replace("-", " ").title())
        QMessageBox.information(self, "Font yüklendi", f"Font assets/fonts içine kaydedildi:\n{relative_path}")

    def _double(self, minimum: float, maximum: float, value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(2)
        spin.setSingleStep(0.5)
        spin.setValue(value)
        return spin


def _find_element(data: dict[str, Any], element_id: str, element_type: str, create: bool = False) -> dict[str, Any]:
    for element in data.get("elements", []):
        if isinstance(element, dict) and element.get("id") == element_id and element.get("type") == element_type:
            return element
    if not create:
        raise TemplateEditorError(f"{element_id} elementi bulunamadı.")
    element = {"type": element_type, "id": element_id}
    data.setdefault("elements", []).append(element)
    return element


def _validate_text_element(element: dict[str, Any], label_width: float, label_height: float) -> None:
    x = _positive_float(element, "x_mm", 0, allow_zero=True)
    y = _positive_float(element, "y_mm", 0, allow_zero=True)
    width = _positive_float(element, "width_mm", None)
    height = _positive_float(element, "height_mm", None)
    font_size = _positive_float(element, "font_size", None)
    if x + width > label_width or y + height > label_height:
        raise TemplateEditorError("Yazı kutusu etiket sınırlarının içinde kalmalıdır.")
    if font_size <= 0:
        raise TemplateEditorError("Font boyutu 0'dan büyük olmalıdır.")


def _validate_field(field: dict[str, Any], label_width: float, label_height: float) -> None:
    column = str(field.get("excel_column", "") or "").strip()
    if column not in SUPPORTED_FIELD_COLUMNS:
        raise TemplateEditorError("Excel kolonu desteklenmiyor. label_text, date_text, note_text veya custom_text_1/2/3 kullanın.")
    if not str(field.get("placeholder", "") or "").strip():
        raise TemplateEditorError("Placeholder boş olamaz.")
    x = _positive_float(field, "x_mm", 0, allow_zero=True)
    y = _positive_float(field, "y_mm", 0, allow_zero=True)
    width = _positive_float(field, "width_mm", None)
    height = _positive_float(field, "height_mm", None)
    font_size = _positive_float(field, "font_size", None)
    if x + width > label_width or y + height > label_height:
        raise TemplateEditorError("Değişken yazı alanı etiket sınırlarının içinde kalmalıdır.")
    if font_size <= 0:
        raise TemplateEditorError("Font boyutu 0'dan büyük olmalıdır.")


def _validate_line_element(element: dict[str, Any], label_width: float, label_height: float) -> None:
    x1 = _positive_float(element, "x1_mm", 0, allow_zero=True)
    y1 = _positive_float(element, "y1_mm", 0, allow_zero=True)
    x2 = _positive_float(element, "x2_mm", 0, allow_zero=True)
    y2 = _positive_float(element, "y2_mm", 0, allow_zero=True)
    thickness = _positive_float(element, "stroke_width", None)
    if max(x1, x2) > label_width or max(y1, y2) > label_height:
        raise TemplateEditorError("Dekoratif çizgi etiket sınırlarının içinde kalmalıdır.")
    if thickness <= 0:
        raise TemplateEditorError("Çizgi kalınlığı 0'dan büyük olmalıdır.")


def _validate_rectangle_element(element: dict[str, Any], label_width: float, label_height: float) -> None:
    x = _positive_float(element, "x_mm", 0, allow_zero=True)
    y = _positive_float(element, "y_mm", 0, allow_zero=True)
    width = _positive_float(element, "width_mm", None)
    height = _positive_float(element, "height_mm", None)
    thickness = _positive_float(element, "stroke_width", 0.1)
    if x + width > label_width or y + height > label_height:
        raise TemplateEditorError("Kenarlık etiket sınırlarının içinde kalmalıdır.")
    if thickness <= 0:
        raise TemplateEditorError("Kenarlık kalınlığı 0'dan büyük olmalıdır.")


def _positive_float(data: dict[str, Any], key: str, default: float | None, allow_zero: bool = False) -> float:
    value = data.get(key, default)
    if value is None or value == "":
        raise TemplateEditorError(f"{key} sayısal olmalıdır.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TemplateEditorError(f"{key} sayısal olmalıdır.") from exc
    if allow_zero:
        if number < 0:
            raise TemplateEditorError(f"{key} negatif olamaz.")
    elif number <= 0:
        raise TemplateEditorError(f"{key} 0'dan büyük olmalıdır.")
    return number


def _safe_project_relative_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (project_root / path).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise TemplateEditorError("Dosya yolu proje klasörünün içinde olmalıdır.") from exc
    return resolved


def _required_text(data: dict[str, Any], key: str) -> str:
    value = str(data.get(key, "") or "").strip()
    if not value:
        raise TemplateEditorError(f"{key} alanı zorunludur.")
    return value
