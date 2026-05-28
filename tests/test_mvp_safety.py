from __future__ import annotations

import sys
import shutil
import unittest
import uuid
import json
import zipfile
import re
from dataclasses import replace
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from excel_reader import read_orders_excel
from config_loader import load_settings
from file_manager import create_run_folders
from laser_nesting import CONNECTED_STATUS_FONT_MISSING, nest_laser_orders
from legacy_converter import convert_legacy_excel
from label_designer.label_service import render_labels_from_excel
from label_designer.manual_label_service import render_manual_label, render_manual_preview
from label_designer.placeholder_resolver import resolve_placeholders
from label_designer.calibration import export_roll_label_calibration_pdf
from label_designer.renderer import measure_text_fit, mm_to_points
from label_designer.settings_resolver import LabelSettingsError, resolve_label_settings
from label_designer.template_loader import find_template, load_template
from desktop.template_importer import safe_extract_template_pack
from webui_backend.label_api import archive_label_outputs, list_archived_label_outputs, list_label_output_archive_history, list_label_outputs, list_laser_outputs, preview_manual, restore_label_outputs
from webui_backend.pdf_preview_api import get_pdf_preview_payload
from webui_backend.file_api import to_web_file_url
from webui_backend.bulk_label_api import column_mapping, preview_samples, used_label_models, write_selected_rows_excel
from webui_backend.settings_api import save_label_defaults
from webui_backend.text_normalizer import friendly_error
from webui_backend.production_safety import (
    append_production_history,
    list_production_history,
    model_health_for_template,
    preflight_manual_label,
    validate_manual_output,
)
from webui_backend.print_queue_api import (
    add_label_outputs_to_queue,
    add_pdf_output_to_queue,
    add_to_print_queue,
    list_print_queue,
    mark_queue_item_pending,
    mark_queue_item_printed,
    print_queue_item_safe,
    remove_from_print_queue,
)
from webui_backend.template_api import (
    add_label_model_field,
    clone_label_model_variant,
    create_linked_label_design,
    create_label_model_from_wizard,
    create_label_model_from_source,
    get_print_template_detail,
    import_print_template_file,
    list_label_model_gallery,
    list_print_templates,
    cleanup_duplicate_label_text_fields,
    cleanup_duplicate_note_fields,
    normalize_label_model_preview,
    save_print_template_metadata,
    save_label_model_field,
    remove_label_model_field,
    read_image_size,
    restore_label_model_backup,
    set_label_model_preview,
    validate_model_preview,
)
from native_edit.diagnostics import run_diagnostics
from native_edit.job_runner import prepare_input_copy, run_native_edit_poc, sha256_file
from native_edit.manifest import add_error, add_warning, create_manifest, load_manifest, save_manifest
from desktop.label_template_editor import (
    add_variable_field,
    find_label_text_element,
    import_font_file,
    load_template_data,
    remove_variable_field,
    render_sample_template,
    save_template_with_backup,
    update_text_element,
    update_top_line,
    update_variable_field,
)
from models import (
    BOTH,
    LASER_CUT,
    LASER_ENGRAVE,
    PRINT,
    AppConfig,
    AppSettings,
    ExcelSettings,
    LaserSettings,
    LaserTextSettings,
    LabelDefaults,
    Order,
    PrintSettings,
    ReportSettings,
)
from print_service import generate_print_jobs
from template_writer import PRODUCTION_COLUMNS, TURKISH_PRODUCTION_HEADERS, create_demo_orders, create_production_template
from validators import validate_and_build_orders


class MvpSafetyTests(unittest.TestCase):
    def test_excel_reading_preserves_turkish_names(self) -> None:
        with temp_workspace() as tmp_path:
            excel_path = tmp_path / "demo_siparisler.xlsx"
            create_demo_orders(excel_path)

            dataframe = read_orders_excel(excel_path)

            self.assertEqual(list(dataframe.columns), PRODUCTION_COLUMNS)
            self.assertIn("Ayşe", set(dataframe["buyer_name"]))
            self.assertIn("Gülşah", set(dataframe["buyer_name"]))
            self.assertIn("Mücahit", set(dataframe["buyer_name"]))
            self.assertIn("İrem", set(dataframe["buyer_name"]))
            self.assertIn("Çağla", set(dataframe["buyer_name"]))
            self.assertIn("Ömer", set(dataframe["buyer_name"]))
            self.assertIn("Şükran", set(dataframe["buyer_name"]))
            self.assertTrue({PRINT, LASER_ENGRAVE, LASER_CUT, BOTH, "NONE"}.issubset(set(dataframe["process_type"])))

    def test_required_column_validation_reports_missing_column(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            dataframe = pd.DataFrame([valid_row()]).drop(columns=["buyer_name"])

            orders, issues = validate_and_build_orders(dataframe, settings)

            self.assertEqual(orders, [])
            self.assertTrue(any(issue.field == "buyer_name" and "Missing required column" in issue.message for issue in issues))

    def test_invalid_process_type_is_rejected(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)

            orders, issues = validate_and_build_orders(pd.DataFrame([valid_row(process_type="UNKNOWN")]), settings)

            self.assertEqual(orders, [])
            self.assertTrue(any(issue.field == "process_type" and "Invalid process_type" in issue.message for issue in issues))

    def test_missing_buyer_name_is_rejected(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)

            orders, issues = validate_and_build_orders(pd.DataFrame([valid_row(buyer_name="")]), settings)

            self.assertEqual(orders, [])
            self.assertTrue(any(issue.field == "buyer_name" and issue.message == "Missing buyer_name" for issue in issues))

    def test_missing_label_text_for_print_is_rejected(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            row = valid_row(process_type=PRINT, personalization_type="LABEL", label_text="")

            orders, issues = validate_and_build_orders(pd.DataFrame([row]), settings)

            self.assertEqual(orders, [])
            self.assertTrue(any(issue.field == "label_text" and "PRINT" in issue.message for issue in issues))

    def test_missing_laser_text_for_laser_cut_is_rejected(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            row = valid_row(
                process_type=LASER_CUT,
                personalization_type="NAME",
                label_variant="NONE",
                label_text="",
                laser_text="",
                material_type="Acrylic",
                material_thickness_mm="3",
            )

            orders, issues = validate_and_build_orders(pd.DataFrame([row]), settings)

            self.assertEqual(orders, [])
            self.assertTrue(any(issue.field == "laser_text" and "LASER_CUT" in issue.message for issue in issues))

    def test_output_folder_generation(self) -> None:
        with temp_workspace() as tmp_path:
            paths = create_run_folders(tmp_path / "output", pd.Timestamp("2026-04-27").date())

            self.assertTrue(paths.run_dir.exists())
            self.assertTrue(paths.reports_dir.exists())
            self.assertTrue(paths.logs_dir.exists())
            self.assertTrue((paths.run_dir / "print").exists())
            self.assertTrue((paths.run_dir / "laser").exists())
            folder_names = {path.name for path in paths.run_dir.iterdir() if path.is_dir()}
            self.assertEqual(folder_names, {"print", "laser", "reports", "logs"})

    def test_production_template_is_empty_with_correct_headers(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = create_production_template(tmp_path / "input" / "cyzella_production_template.xlsx")

            raw_dataframe = pd.read_excel(template_path, dtype=object, engine="openpyxl")
            dataframe = read_orders_excel(template_path)

            self.assertEqual(list(raw_dataframe.columns), [TURKISH_PRODUCTION_HEADERS[column] for column in PRODUCTION_COLUMNS])
            self.assertEqual(list(dataframe.columns), PRODUCTION_COLUMNS)
            self.assertEqual(len(dataframe), 0)

    def test_demo_excel_uses_turkish_headers_but_reads_as_internal_schema(self) -> None:
        with temp_workspace() as tmp_path:
            excel_path = tmp_path / "input" / "demo_siparisler.xlsx"
            create_demo_orders(excel_path)

            raw_dataframe = pd.read_excel(excel_path, dtype=object, engine="openpyxl")
            normalized = read_orders_excel(excel_path)

            self.assertEqual(list(raw_dataframe.columns), [TURKISH_PRODUCTION_HEADERS[column] for column in PRODUCTION_COLUMNS])
            self.assertEqual(list(normalized.columns), PRODUCTION_COLUMNS)
            self.assertGreater(len(normalized), 0)

    def test_turkish_excel_headers_are_normalized_to_internal_schema(self) -> None:
        dataframe = pd.DataFrame(
            [
                {
                    "Sipariş No": "TR-001",
                    "Alıcı Adı": "Ayşe",
                    "Ürün Adı": "Gold Etiket",
                    "Model No": "01",
                    "Şablon No": "A",
                    "İşlem Tipi": "PRINT",
                    "Kişiselleştirme Türü": "LABEL",
                    "Etiket Varyantı": "GOLD",
                    "Etiket Yazısı": "Ayşe & Mehmet",
                    "Lazer Yazısı": "",
                    "Adet": 1,
                    "Malzeme Türü": "",
                    "Malzeme Kalınlığı mm": "",
                    "Ekstra Çikolata Adedi": 0,
                    "Ekstra Madlen Adedi": 0,
                    "Üretim Notu": "",
                    "Kontrol Gerekli": "",
                    "Durum": "NEW",
                }
            ]
        )
        with temp_workspace() as tmp_path:
            excel_path = tmp_path / "input" / "turkce.xlsx"
            excel_path.parent.mkdir(parents=True, exist_ok=True)
            dataframe.to_excel(excel_path, index=False)

            normalized = read_orders_excel(excel_path)

            self.assertEqual(list(normalized.columns), PRODUCTION_COLUMNS)
            self.assertEqual(normalized.loc[0, "label_text"], "Ayşe & Mehmet")

    def test_print_template_matching_generates_print_data(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            (settings.print_templates_dir / "01_a_gold.cdr").write_text("template", encoding="utf-8")

            written_files, issues = generate_print_jobs([make_order()], tmp_path / "output" / "2026-04-27", settings)

            self.assertEqual(issues, [])
            self.assertTrue(any(path.name == "print_data.csv" for path in written_files))

    def test_multiple_print_template_conflict_is_reported(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            (settings.print_templates_dir / "01_a_gold.cdr").write_text("template 1", encoding="utf-8")
            (settings.print_templates_dir / "model_01_template_a_gold.pdf").write_text("template 2", encoding="utf-8")

            _written_files, issues = generate_print_jobs([make_order()], tmp_path / "output" / "2026-04-27", settings)

            self.assertTrue(any("multiple print templates" in issue.message for issue in issues))

    def test_missing_print_template_is_reported(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)

            _written_files, issues = generate_print_jobs([make_order()], tmp_path / "output" / "2026-04-27", settings)

            self.assertTrue(any("Missing print template" in issue.message for issue in issues))

    def test_laser_row_based_nesting_places_items_inside_plate(self) -> None:
        with temp_workspace() as tmp_path:
            settings = replace(
                make_settings(tmp_path),
                laser=LaserSettings(
                    auto_start_laser=False,
                    output_format="svg",
                    plate_width_mm=95,
                    plate_height_mm=80,
                    margin_mm=5,
                    gap_x_mm=3,
                    gap_y_mm=3,
                    include_order_number_guide=True,
                ),
                laser_text=LaserTextSettings(
                    laser_font_path=tmp_path / "assets" / "fonts" / "missing.ttf",
                    default_font_size_mm=20,
                    min_font_size_mm=12,
                    max_font_size_mm=24,
                    force_connected_letters=False,
                    convert_text_to_paths=False,
                    warn_if_disconnected_shapes=True,
                    add_bridges_for_dots_and_accents=False,
                ),
            )
            orders = [
                make_order(order_no="L-1", process_type=LASER_ENGRAVE, label_text="", laser_text="Ayşe"),
                make_order(order_no="L-2", process_type=LASER_ENGRAVE, label_text="", laser_text="Ömer"),
                make_order(order_no="L-3", process_type=LASER_ENGRAVE, label_text="", laser_text="Çağla"),
            ]

            result = nest_laser_orders(orders, tmp_path / "laser" / "model_01", 1, settings)

            self.assertEqual(result.issues, [])
            self.assertTrue(result.plates)
            for plate in result.plates:
                for item in plate.items:
                    self.assertGreaterEqual(item.x_mm, settings.laser.margin_mm)
                    self.assertGreaterEqual(item.y_mm, settings.laser.margin_mm)
                    self.assertLessEqual(item.x_mm + item.width_mm, settings.laser.plate_width_mm - settings.laser.margin_mm)
                    self.assertLessEqual(item.y_mm + item.height_mm, settings.laser.plate_height_mm - settings.laser.margin_mm)

    def test_long_laser_name_is_rejected_when_it_cannot_fit(self) -> None:
        with temp_workspace() as tmp_path:
            settings = replace(
                make_settings(tmp_path),
                laser=LaserSettings(
                    auto_start_laser=False,
                    output_format="svg",
                    plate_width_mm=70,
                    plate_height_mm=45,
                    margin_mm=5,
                    gap_x_mm=3,
                    gap_y_mm=3,
                    include_order_number_guide=True,
                ),
            )
            order = make_order(
                process_type=LASER_ENGRAVE,
                label_text="",
                laser_text="Ayşe Gülşah Mücahit İrem Çağla Ömer Şükran Çok Çok Uzun İsim",
            )

            result = nest_laser_orders([order], tmp_path / "laser" / "model_01", 1, settings)

            self.assertFalse(result.plates)
            self.assertTrue(any("too large" in issue.message for issue in result.issues))

    def test_missing_font_blocks_laser_cut_output(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            order = make_order(
                process_type=LASER_CUT,
                personalization_type="NAME",
                label_variant="NONE",
                label_text="",
                laser_text="Mücahit",
                material_type="Acrylic",
                material_thickness_mm="3",
            )

            result = nest_laser_orders([order], tmp_path / "laser" / "model_01", 1, settings)

            self.assertFalse(result.plates)
            self.assertTrue(any(issue.message.startswith("Connected script font missing") for issue in result.issues))
            self.assertTrue(any(row["connected_status"] == CONNECTED_STATUS_FONT_MISSING for row in result.report_rows))

    def test_laser_cut_blocks_when_connected_safety_is_disabled(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            settings.laser_text.laser_font_path.write_text("fake font placeholder", encoding="utf-8")
            unsafe_settings = replace(
                settings,
                laser_text=replace(settings.laser_text, force_connected_letters=False, convert_text_to_paths=False),
            )
            order = make_order(
                process_type=LASER_CUT,
                personalization_type="NAME",
                label_variant="NONE",
                label_text="",
                laser_text="Ada",
                material_type="Acrylic",
                material_thickness_mm="3",
            )

            result = nest_laser_orders([order], tmp_path / "laser" / "model_01", 1, unsafe_settings)

            self.assertFalse(result.plates)
            self.assertTrue(any("force_connected_letters=true" in issue.message for issue in result.issues))

    def test_legacy_converter_outputs_clean_schema_and_warnings(self) -> None:
        with temp_workspace() as tmp_path:
            legacy_path = tmp_path / "input" / "siparisler.xlsx"
            legacy_path.parent.mkdir(parents=True, exist_ok=True)
            dataframe = pd.DataFrame(
                [
                    {
                        "sipariş numarası": "",
                        "alıcı ismi": "",
                        "gold": "",
                        "gümüş": "",
                        "ürün": "Çikolata Kutusu",
                        "not": "",
                    },
                    {
                        "sipariş numarası": "1001",
                        "alıcı ismi": "Ayşe",
                        "gold": "Ayşe",
                        "gümüş": "",
                        "ürün": "",
                        "not": "",
                    },
                    {
                        "sipariş numarası": "1002",
                        "alıcı ismi": "Gülşah",
                        "gold": "isim yok",
                        "gümüş": "",
                        "ürün": "2 adet ekstra çikolata",
                        "not": "paket notu",
                    },
                    {
                        "sipariş numarası": "1003",
                        "alıcı ismi": "Mücahit",
                        "gold": "acil kontrol et",
                        "gümüş": "",
                        "ürün": "Madlen 5",
                        "not": "",
                    },
                ]
            )
            dataframe.to_excel(legacy_path, index=False)

            result = convert_legacy_excel(legacy_path, tmp_path / "output" / "converted")
            clean = pd.read_excel(result.clean_excel_path, dtype=object, engine="openpyxl")
            warnings = pd.read_csv(result.warnings_csv_path)

            self.assertEqual(list(clean.columns), PRODUCTION_COLUMNS)
            self.assertEqual(result.converted_rows, 3)
            self.assertTrue((clean["needs_review"].fillna("") == "true").any())
            self.assertIn("Ayşe", set(clean["label_text"].fillna("")))
            self.assertTrue((clean["extra_chocolate_qty"].fillna(0).astype(int) >= 1).any())
            self.assertFalse(warnings.empty)

    def test_label_template_loading(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template(tmp_path)

            template = load_template(template_path)

            self.assertEqual(template.model_no, "01")
            self.assertEqual(template.template_no, "A")
            self.assertEqual(template.label_variant, "GOLD")
            self.assertEqual(template.canvas_width_mm, 70)
            self.assertTrue(template.elements)

    def test_label_placeholder_replacement_preserves_turkish_text(self) -> None:
        order = make_order(label_text="Ayşe & Mehmet", buyer_name="Gülşah")

        text = resolve_placeholders("{{LABEL_TEXT}} / {{BUYER_NAME}} / {{ORDER_NO}} / {{DATE}}", order, pd.Timestamp("2026-04-27").date())

        self.assertIn("Ayşe & Mehmet", text)
        self.assertIn("Gülşah", text)
        self.assertIn(order.order_no, text)
        self.assertIn("2026-04-27", text)

    def test_label_placeholder_replacement_supports_model_field_columns(self) -> None:
        order = make_order(label_text="Ayşe & Mehmet")
        source = dict(order.source)
        source.update({"date_text": "12.05.2026", "note_text": "Söz Hatırası", "custom_text_1": "Altın"})
        order = replace(order, source=source)

        text = resolve_placeholders("{{LABEL_TEXT}} / {{DATE_TEXT}} / {{NOTE_TEXT}} / {{CUSTOM_TEXT_1}}", order, pd.Timestamp("2026-04-27").date())

        self.assertIn("Ayşe & Mehmet", text)
        self.assertIn("12.05.2026", text)
        self.assertIn("Söz Hatırası", text)
        self.assertIn("Altın", text)

    def test_label_designer_reports_missing_template(self) -> None:
        with temp_workspace() as tmp_path:
            settings = replace(make_settings(tmp_path), print=replace(make_settings(tmp_path).print, mode="label_designer"))
            excel_path = tmp_path / "input" / "siparisler.xlsx"
            pd.DataFrame([valid_row(label_text="Ayşe")]).to_excel(excel_path, index=False)

            result = render_labels_from_excel(settings, excel_path, pd.Timestamp("2026-04-27").date())

            self.assertTrue(any(row["status"] == "ERROR" and "template" in row["warning"].lower() for row in result.rows))
            self.assertTrue(result.report_path.exists())

    def test_label_designer_generates_pdf_and_png(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            settings = replace(settings, print=replace(settings.print, mode="label_designer"))
            write_label_template(tmp_path)
            excel_path = tmp_path / "input" / "siparisler.xlsx"
            pd.DataFrame([valid_row(label_text="Ayşe & Mehmet")]).to_excel(excel_path, index=False)

            result = render_labels_from_excel(settings, excel_path, pd.Timestamp("2026-04-27").date())

            ok_rows = [row for row in result.rows if row["status"] == "OK"]
            self.assertEqual(len(ok_rows), 1)
            self.assertTrue(Path(ok_rows[0]["output_pdf"]).exists())
            self.assertTrue(Path(ok_rows[0]["output_png"]).exists())

    def test_label_model_fields_map_excel_columns_to_render_output(self) -> None:
        with temp_workspace() as tmp_path:
            settings = replace(make_settings(tmp_path), print=replace(make_settings(tmp_path).print, mode="label_designer"))
            write_label_template_with_fields(tmp_path)
            excel_path = tmp_path / "input" / "siparisler.xlsx"
            pd.DataFrame(
                [
                    valid_row(
                        label_text="Ayşe & Mehmet",
                        date_text="12.05.2026",
                        note_text="Söz Hatırası",
                        custom_text_1="Gold",
                    )
                ]
            ).to_excel(excel_path, index=False)

            result = render_labels_from_excel(settings, excel_path, pd.Timestamp("2026-04-27").date())

            ok_rows = [row for row in result.rows if row["status"] == "OK"]
            self.assertEqual(len(ok_rows), 1)
            self.assertTrue(Path(ok_rows[0]["output_pdf"]).exists())

    def test_label_model_missing_field_column_is_reported(self) -> None:
        with temp_workspace() as tmp_path:
            settings = replace(make_settings(tmp_path), print=replace(make_settings(tmp_path).print, mode="label_designer"))
            write_label_template_with_fields(tmp_path, extra_column="missing_column")
            excel_path = tmp_path / "input" / "siparisler.xlsx"
            pd.DataFrame([valid_row(label_text="Ayşe")]).to_excel(excel_path, index=False)

            result = render_labels_from_excel(settings, excel_path, pd.Timestamp("2026-04-27").date())

            self.assertTrue(any(row["status"] == "ERROR" and "missing_column" in row["warning"] for row in result.rows))
            self.assertTrue((tmp_path / "output" / "2026-04-27" / "print" / "model_01" / "rendered" / "label_render_report.csv").exists())

    def test_roll_label_template_uses_own_size(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            template = load_template(write_label_template(tmp_path, width=48, height=28, include_roll_size=True))

            resolved = resolve_label_settings(template, settings)

            self.assertEqual(resolved.media_type, "ROLL")
            self.assertEqual(resolved.label_width_mm, 48)
            self.assertEqual(resolved.label_height_mm, 28)
            self.assertEqual(resolved.used_settings_source, "TEMPLATE")

    def test_roll_label_template_falls_back_to_default_size(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            template = load_template(write_label_template(tmp_path, include_roll_size=False))

            resolved = resolve_label_settings(template, settings)

            self.assertEqual(resolved.label_width_mm, settings.label_defaults.label_width_mm)
            self.assertEqual(resolved.label_height_mm, settings.label_defaults.label_height_mm)
            self.assertEqual(resolved.used_settings_source, "DEFAULT_CONFIG")

    def test_missing_roll_label_dimensions_without_defaults_blocks_rendering(self) -> None:
        with temp_workspace() as tmp_path:
            settings = replace(make_settings(tmp_path), label_defaults=None)
            template = load_template(write_label_template(tmp_path, include_roll_size=False))

            with self.assertRaises(LabelSettingsError):
                resolve_label_settings(template, settings)

    def test_roll_batch_pdf_is_generated_with_copies_and_report_columns(self) -> None:
        with temp_workspace() as tmp_path:
            settings = replace(make_settings(tmp_path), print=replace(make_settings(tmp_path).print, mode="label_designer"))
            write_label_template(tmp_path, include_roll_size=False)
            excel_path = tmp_path / "input" / "siparisler.xlsx"
            pd.DataFrame([valid_row(label_text="Ayşe & Mehmet", quantity=2)]).to_excel(excel_path, index=False)

            result = render_labels_from_excel(settings, excel_path, pd.Timestamp("2026-04-27").date())

            batch_rows = [row for row in result.rows if row["status"] == "OK_BATCH"]
            self.assertTrue(batch_rows)
            self.assertTrue(Path(batch_rows[0]["roll_batch_pdf"]).exists())
            self.assertEqual(batch_rows[0]["media_type"], "ROLL")
            self.assertEqual(batch_rows[0]["used_settings_source"], "DEFAULT_CONFIG")
            self.assertEqual(batch_rows[0]["copies"], "2")
            self.assertIn("text_fit_status", batch_rows[0])
            self.assertIn("final_font_size", batch_rows[0])
            self.assertIn("render_warning", batch_rows[0])

    def test_calibration_pdf_generation(self) -> None:
        with temp_workspace() as tmp_path:
            settings = make_settings(tmp_path)
            output = tmp_path / "output" / "2026-04-27" / "print" / "calibration" / "roll_label_calibration.pdf"

            export_roll_label_calibration_pdf(output, settings.label_defaults)

            self.assertTrue(output.exists())

    def test_mm_to_points_conversion(self) -> None:
        self.assertAlmostEqual(mm_to_points(25.4), 72.0, places=4)
        self.assertAlmostEqual(mm_to_points(10), 28.3464, places=3)

    def test_50x30_roll_pdf_page_size_and_text_fit(self) -> None:
        with temp_workspace() as tmp_path:
            settings = replace(
                make_settings(tmp_path),
                print=replace(make_settings(tmp_path).print, mode="label_designer"),
                label_defaults=LabelDefaults(label_width_mm=50, label_height_mm=30, printer_dpi=300),
            )
            write_label_template(tmp_path, width=50, height=30)
            excel_path = tmp_path / "input" / "siparisler.xlsx"
            pd.DataFrame([valid_row(order_no="11111111111", label_text="Ayşe & Mehmet", quantity=1)]).to_excel(excel_path, index=False)

            result = render_labels_from_excel(settings, excel_path, pd.Timestamp("2026-04-27").date())

            pdf_path = tmp_path / "output" / "2026-04-27" / "print" / "model_01" / "rendered" / "order_11111111111.pdf"
            self.assertTrue(pdf_path.exists())
            media_box = _pdf_media_box(pdf_path)
            self.assertAlmostEqual(media_box[2], mm_to_points(50), delta=1.0)
            self.assertAlmostEqual(media_box[3], mm_to_points(30), delta=1.0)
            ok_rows = [row for row in result.rows if row["order_no"] == "11111111111" and row["status"] == "OK"]
            self.assertTrue(ok_rows)
            self.assertIn(ok_rows[0]["text_fit_status"], {"OK", "SHRUNK_TO_FIT"})

    def test_roll_batch_pdf_has_one_page_per_copy(self) -> None:
        with temp_workspace() as tmp_path:
            settings = replace(
                make_settings(tmp_path),
                print=replace(make_settings(tmp_path).print, mode="label_designer"),
                label_defaults=LabelDefaults(label_width_mm=50, label_height_mm=30, printer_dpi=300),
            )
            write_label_template(tmp_path, width=50, height=30)
            excel_path = tmp_path / "input" / "siparisler.xlsx"
            rows = [
                valid_row(order_no="A-1", label_text="Ayşe", quantity=2),
                valid_row(order_no="A-2", label_text="Mehmet", quantity=1),
            ]
            pd.DataFrame(rows).to_excel(excel_path, index=False)

            render_labels_from_excel(settings, excel_path, pd.Timestamp("2026-04-27").date())

            batch_path = tmp_path / "output" / "2026-04-27" / "print" / "model_01" / "rendered" / "roll_batch_01_A_GOLD.pdf"
            self.assertTrue(batch_path.exists())
            self.assertEqual(_pdf_page_count(batch_path), 3)

    def test_calibration_pdf_50x30_page_size(self) -> None:
        with temp_workspace() as tmp_path:
            output = tmp_path / "calibration.pdf"
            export_roll_label_calibration_pdf(
                output,
                LabelDefaults(label_width_mm=50, label_height_mm=30, printer_dpi=300),
            )

            media_box = _pdf_media_box(output)
            self.assertAlmostEqual(media_box[2], mm_to_points(50), delta=1.0)
            self.assertAlmostEqual(media_box[3], mm_to_points(30), delta=1.0)

    def test_turkish_label_text_fit_smoke(self) -> None:
        raw = {
            "placeholder": "{{LABEL_TEXT}}",
            "x_mm": 5,
            "y_mm": 9,
            "width_mm": 40,
            "height_mm": 11,
            "font_family": "Segoe UI",
            "font_size": 13,
        }

        status, final_size, warning = measure_text_fit(raw, "Ayşe & Mehmet")

        self.assertIn(status, {"OK", "SHRUNK"})
        self.assertGreaterEqual(final_size, 3.5)
        self.assertIsInstance(warning, str)

    def test_label_defaults_load_from_config(self) -> None:
        with temp_workspace() as tmp_path:
            config_path = tmp_path / "config" / "settings.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                """
app:
  output_date_format: "%Y-%m-%d"
  language: "tr"
excel:
  mode: "clean_production_excel"
  input_file: "input/siparisler.xlsx"
templates:
  print_folder: "templates/print"
  laser_folder: "templates/laser"
print:
  mode: "data_only"
  generate_print_data_csv: true
  auto_print_enabled: false
  allow_direct_print: false
  require_print_confirmation: true
  default_printer: ""
  use_default_label_settings: true
label_defaults:
  media_type: "ROLL"
  label_width_mm: 55
  label_height_mm: 32
  roll_gap_mm: 3
  printer_dpi: 300
  default_copies: 1
  horizontal_offset_mm: 0
  vertical_offset_mm: 0
  scale_percent: 100
  background_enabled: true
  show_cut_boundary: false
  safe_margin_mm: 1.5
  show_order_number_on_label: false
laser:
  auto_start_laser: false
  output_format: "svg"
  plate_width_mm: 600
  plate_height_mm: 400
  margin_mm: 5
  gap_x_mm: 3
  gap_y_mm: 3
  include_order_number_guide: true
laser_text:
  laser_font_path: "assets/fonts/connected_script.ttf"
  default_font_size_mm: 28
  min_font_size_mm: 18
  max_font_size_mm: 36
  force_connected_letters: true
  convert_text_to_paths: true
  warn_if_disconnected_shapes: true
  add_bridges_for_dots_and_accents: false
reports:
  generate_errors_report: true
  generate_summary_report: true
  generate_layout_report: true
  generate_template_matching_report: true
""",
                encoding="utf-8",
            )

            settings = load_settings(config_path)

            self.assertEqual(settings.label_defaults.media_type, "ROLL")
            self.assertEqual(settings.label_defaults.label_width_mm, 55)
            self.assertEqual(settings.label_defaults.label_height_mm, 32)
            self.assertFalse(settings.label_defaults.show_order_number_on_label)
            self.assertTrue(settings.print.use_default_label_settings)

    def test_order_number_hidden_by_default_on_label_output(self) -> None:
        with temp_workspace() as tmp_path:
            settings = replace(make_settings(tmp_path), print=replace(make_settings(tmp_path).print, mode="label_designer"))
            write_label_template(tmp_path, width=50, height=30, include_order_size=True)
            excel_path = tmp_path / "input" / "siparisler.xlsx"
            pd.DataFrame([valid_row(order_no="11111111111", label_text="Ayşe & Mehmet")]).to_excel(excel_path, index=False)

            result = render_labels_from_excel(settings, excel_path, pd.Timestamp("2026-04-27").date())

            ok_rows = [row for row in result.rows if row["status"] == "OK"]
            self.assertTrue(ok_rows)
            self.assertEqual(ok_rows[0]["show_order_number_on_label"], "False")
            self.assertIn("11111111111", ok_rows[0]["order_no"])

    def test_template_pack_import_copies_only_allowed_files(self) -> None:
        with temp_workspace() as tmp_path:
            zip_path = tmp_path / "pack.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("templates/designs/09_a_gold.json", "{}")
                archive.writestr("templates/print/01_a_gold.cdr", b"fakecdr")
                archive.writestr("assets/label_backgrounds/bg.png", b"fakepng")
                archive.writestr("input/imported.xlsx", b"fakexlsx")
                archive.writestr("preview_contact_sheet.png", b"preview")
                archive.writestr("bad.exe", b"bad")

            result = safe_extract_template_pack(zip_path, tmp_path, run_date=pd.Timestamp("2026-04-27").date())

            self.assertTrue((tmp_path / "templates" / "designs" / "09_a_gold.json").exists())
            self.assertTrue((tmp_path / "templates" / "print" / "01_a_gold.cdr").exists())
            self.assertTrue((tmp_path / "assets" / "label_backgrounds" / "bg.png").exists())
            self.assertTrue((tmp_path / "input" / "imported.xlsx").exists())
            self.assertTrue((tmp_path / "output" / "2026-04-27" / "imports" / "pack" / "preview_contact_sheet.png").exists())
            self.assertTrue(result.report_path.exists())
            self.assertEqual(result.imported_templates, 1)
            self.assertEqual(result.imported_print_templates, 1)
            self.assertEqual(result.imported_backgrounds, 1)
            self.assertEqual(result.imported_excels, 1)
            self.assertTrue(any(row["status"] == "SKIPPED_INVALID_TYPE" and row["source_path"] == "bad.exe" for row in result.rows))

    def test_single_cdr_print_template_import_is_supported(self) -> None:
        with temp_workspace() as tmp_path:
            cdr_path = tmp_path / "incoming" / "01_a_gold.cdr"
            cdr_path.parent.mkdir(parents=True, exist_ok=True)
            cdr_path.write_bytes(b"fake cdr")

            result = import_print_template_file(tmp_path, cdr_path)

            self.assertEqual(result["status"], "IMPORTED")
            self.assertTrue((tmp_path / "templates" / "print" / "01_a_gold.cdr").exists())

    def test_print_templates_are_listed_and_metadata_is_saved(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = tmp_path / "templates" / "print" / "02 gold cyzella.ai"
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_bytes(b"fake ai")

            rows = list_print_templates(tmp_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["file_name"], "02 gold cyzella.ai")
            self.assertEqual(rows[0]["model_no"], "02")
            self.assertEqual(rows[0]["label_variant"], "GOLD")

            result = save_print_template_metadata(
                tmp_path,
                rows[0]["relative_path"],
                {"model_no": "02", "template_no": "A", "label_variant": "GOLD", "notes": "ana gold", "active": True},
            )
            detail = get_print_template_detail(tmp_path, rows[0]["relative_path"])

            self.assertEqual(result["status"], "OK")
            self.assertEqual(detail["template_no"], "A")
            self.assertEqual(detail["notes"], "ana gold")
            self.assertTrue((tmp_path / "templates" / "print" / ".template_metadata.json").exists())

    def test_linked_label_design_is_created_without_overwriting_print_template(self) -> None:
        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            template_path = tmp_path / "templates" / "print" / "02 gold cyzella.ai"
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_bytes(b"fake ai")
            relative = "templates/print/02 gold cyzella.ai"
            save_print_template_metadata(
                tmp_path,
                relative,
                {"model_no": "02", "template_no": "A", "label_variant": "GOLD", "active": True},
            )

            result = create_linked_label_design(tmp_path, relative)

            self.assertEqual(result["status"], "CREATED")
            self.assertTrue((tmp_path / "templates" / "designs" / "02_a_gold.json").exists())
            self.assertEqual(template_path.read_bytes(), b"fake ai")

    def test_cdr_ai_model_source_creates_label_model_json_without_changing_source(self) -> None:
        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            source = tmp_path / "incoming" / "yedek_bordolu.cdr"
            preview = tmp_path / "incoming" / "yedek_bordolu_preview.png"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"fake cdr source")
            preview.write_bytes(b"fake preview")

            result = create_label_model_from_source(
                tmp_path,
                source,
                {
                    "model_name": "Bordolu Etiket",
                    "model_no": "02",
                    "template_no": "A",
                    "label_variant": "GOLD",
                    "label_width_mm": 50,
                    "label_height_mm": 30,
                    "active": True,
                },
                preview_image=preview,
            )
            data = json.loads((tmp_path / "templates" / "designs" / "02_a_gold.json").read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "CREATED")
            self.assertEqual(source.read_bytes(), b"fake cdr source")
            self.assertTrue((tmp_path / "templates" / "print" / "yedek_bordolu.cdr").exists())
            self.assertTrue((tmp_path / "assets" / "label_backgrounds" / "yedek_bordolu_preview.png").exists())
            self.assertEqual(data["source_file"], "templates/print/yedek_bordolu.cdr")
            self.assertEqual(data["preview_image"], "assets/label_backgrounds/yedek_bordolu_preview.png")
            self.assertEqual(data["fields"][0]["excel_column"], "label_text")

    def test_ai_model_source_auto_links_same_name_preview(self) -> None:
        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            source = tmp_path / "incoming" / "03_pink.ai"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"fake ai source")
            auto_preview = tmp_path / "assets" / "label_backgrounds" / "03_pink_preview.png"
            auto_preview.parent.mkdir(parents=True, exist_ok=True)
            auto_preview.write_bytes(b"fake preview")

            result = create_label_model_from_source(
                tmp_path,
                source,
                {
                    "model_name": "Pembe Etiket",
                    "model_no": "03",
                    "template_no": "B",
                    "label_variant": "PINK",
                },
            )
            data = json.loads((tmp_path / "templates" / "designs" / "03_b_pink.json").read_text(encoding="utf-8"))

            self.assertEqual(result["preview_image"], "assets/label_backgrounds/03_pink_preview.png")
            self.assertEqual(data["source_file"], "templates/print/03_pink.ai")

    def test_manual_label_renders_with_model_created_from_ai_source(self) -> None:
        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            source = tmp_path / "incoming" / "04_white.ai"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"fake ai source")
            create_label_model_from_source(
                tmp_path,
                source,
                {
                    "model_name": "Beyaz Etiket",
                    "model_no": "04",
                    "template_no": "C",
                    "label_variant": "WHITE",
                },
            )

            result = render_manual_label(
                tmp_path,
                tmp_path / "templates" / "designs" / "04_c_white.json",
                "Ayşe & Mehmet",
                2,
            )

            self.assertTrue(result.pdf_path.exists())
            self.assertTrue(result.png_path.exists())
            self.assertEqual(_pdf_page_count(result.batch_pdf_path), 2)

    def test_label_model_gallery_payload_prefers_visual_model_information(self) -> None:
        with temp_workspace() as tmp_path:
            preview = tmp_path / "assets" / "label_backgrounds" / "02_gold_preview.png"
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview.write_bytes(b"fake png")
            write_label_template_with_fields(tmp_path, preview_image="assets/label_backgrounds/02_gold_preview.png")

            rows = list_label_model_gallery(tmp_path)

            self.assertEqual(rows[0]["model_no"], "01")
            self.assertIn("Model", rows[0]["subtitle"])
            self.assertEqual(rows[0]["preview_status"], "VAR")
            self.assertNotEqual(rows[0]["title"], "01_a_gold.json")

    def test_label_model_gallery_reports_missing_preview(self) -> None:
        with temp_workspace() as tmp_path:
            write_label_template_with_fields(tmp_path, source_file="templates/print/02_gold_cyzella.ai")

            rows = list_label_model_gallery(tmp_path)

            self.assertEqual(rows[0]["preview_status"], "YOK")
            self.assertIn("önizleme", rows[0]["preview_warning"].lower())
            self.assertIn("doğrudan önizlenemiyor", rows[0]["source_preview_note"])
            self.assertEqual(rows[0]["source_file_type"], "AI")
            self.assertGreaterEqual(len(rows[0]["fields_summary"]), 3)
            self.assertEqual(rows[0]["fields_summary"][0]["excel_column"], "label_text")
            self.assertIn("width_mm", rows[0]["fields_summary"][0])
            self.assertIn("font_path", rows[0]["fields_summary"][0])

    def test_label_model_preview_image_selection_updates_json(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template_with_fields(tmp_path)
            source = tmp_path / "incoming" / "preview.png"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"fake png")

            result = set_label_model_preview(tmp_path, template_path, source)
            data = json.loads(template_path.read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "OK")
            self.assertTrue(data["preview_image"].startswith("assets/label_backgrounds/"))
            self.assertTrue((tmp_path / data["preview_image"]).exists())

    def test_label_outputs_and_laser_outputs_are_listed_for_in_app_views(self) -> None:
        with temp_workspace() as tmp_path:
            label_dir = tmp_path / "output" / "2026-04-27" / "print" / "model_01" / "rendered"
            laser_dir = tmp_path / "output" / "2026-04-27" / "laser" / "model_01"
            label_dir.mkdir(parents=True, exist_ok=True)
            laser_dir.mkdir(parents=True, exist_ok=True)
            (label_dir / "order_111.pdf").write_bytes(b"%PDF")
            (label_dir / "order_111.png").write_bytes(b"png")
            (label_dir / "roll_batch_01_A_GOLD.pdf").write_bytes(b"%PDF")
            (laser_dir / "plate_001.svg").write_text("<svg></svg>", encoding="utf-8")

            label_rows = list_label_outputs(tmp_path)
            laser_rows = list_laser_outputs(tmp_path)

            self.assertTrue(any(row["file_name"] == "order_111.png" and row["preview_uri"] for row in label_rows))
            png_row = next(row for row in label_rows if row["file_name"] == "order_111.png")
            self.assertTrue(png_row["preview_url"].startswith("file:///"))
            self.assertEqual(png_row["preview_url"], png_row["preview_uri"])
            self.assertTrue(png_row["file_path"].endswith("order_111.png"))
            self.assertEqual(png_row["display_name"], "Etiket çıktısı 111")
            self.assertTrue(any(row["file_name"] == "roll_batch_01_A_GOLD.pdf" for row in label_rows))
            self.assertTrue(any(row["file_name"] == "plate_001.svg" and row["preview_uri"] for row in laser_rows))

    def test_web_file_url_converts_project_png_paths_for_qwebengine(self) -> None:
        with temp_workspace() as tmp_path:
            png_path = tmp_path / "output" / "2026-04-27" / "print" / "model 01" / "rendered" / "order 111.png"
            png_path.parent.mkdir(parents=True, exist_ok=True)
            png_path.write_bytes(b"png")

            absolute_url = to_web_file_url(png_path, tmp_path)
            relative_url = to_web_file_url(png_path.relative_to(tmp_path), tmp_path)
            backslash_url = to_web_file_url(str(png_path), tmp_path)
            missing_url = to_web_file_url(tmp_path / "output" / "missing.png", tmp_path)

            self.assertTrue(absolute_url.startswith("file:///"))
            self.assertIn("order%20111.png", absolute_url)
            self.assertEqual(relative_url, absolute_url)
            self.assertEqual(backslash_url, absolute_url)
            self.assertEqual(missing_url, "")

    def test_pdf_preview_payload_is_safe_and_falls_back_without_render_pages(self) -> None:
        with temp_workspace() as tmp_path:
            pdf_path = tmp_path / "output" / "2026-04-27" / "print" / "manual" / "manual_batch_test.pdf"
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(
                b"%PDF-1.4\n"
                b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
                b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
                b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 142 85] >> endobj\n"
                b"trailer << /Root 1 0 R >>\n%%EOF"
            )
            outside = tmp_path.parent / "outside.pdf"
            outside.write_bytes(b"%PDF")

            payload = get_pdf_preview_payload(tmp_path, pdf_path.relative_to(tmp_path))
            outside_payload = get_pdf_preview_payload(tmp_path, outside)

            self.assertEqual(payload["status"], "OK")
            self.assertTrue(str(payload["file_url"]).startswith("file:///"))
            self.assertEqual(payload["file_type"], "Manuel PDF")
            self.assertGreaterEqual(int(payload["page_count"]), 1)
            self.assertIn("preview_pages", payload)
            self.assertEqual(outside_payload["status"], "ERROR")

    def test_pdf_preview_ui_buttons_are_present_and_safe(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
        js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
        bridge_source = (project_root / "src" / "webui_backend" / "bridge.py").read_text(encoding="utf-8")

        self.assertIn("PDF Önizleme", html)
        self.assertIn("pdfPreviewModal", html)
        self.assertIn("PDF’i Gör", html)
        self.assertIn("openPdfPreview", js)
        self.assertIn("get_pdf_preview_payload", bridge_source)
        self.assertIn("Yazıcı otomatik çalışmaz", html)
        self.assertIn("Yazdırmaya Hazır", html)
        self.assertIn("safePrintStatus", html)
        self.assertIn("safePrintDetails", html)
        self.assertIn("requestManualPrint", js)
        self.assertIn("requestPdfPrint", js)
        self.assertIn("confirmSafePrintOpen", js)
        self.assertIn("Yazdır", html)

    def test_single_pdf_output_can_be_added_to_print_queue_safely(self) -> None:
        with temp_workspace() as tmp_path:
            pdf_path = tmp_path / "output" / "2026-04-27" / "print" / "manual" / "manual_batch_test.pdf"
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(b"%PDF")
            report_path = tmp_path / "output" / "2026-04-27" / "print" / "manual" / "label_render_report.pdf"
            report_path.write_bytes(b"%PDF")

            added = add_pdf_output_to_queue(tmp_path, pdf_path.relative_to(tmp_path).as_posix())
            duplicate = add_pdf_output_to_queue(tmp_path, pdf_path.relative_to(tmp_path).as_posix())
            report = add_pdf_output_to_queue(tmp_path, report_path.relative_to(tmp_path).as_posix())
            rows = list_print_queue(tmp_path)

            self.assertEqual(added["status"], "ADDED")
            self.assertEqual(duplicate["status"], "EXISTS")
            self.assertEqual(report["status"], "ERROR")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["job_type"], "Manuel")

    def test_print_queue_persists_label_jobs_only(self) -> None:
        with temp_workspace() as tmp_path:
            outputs = [
                {"file_name": "roll_batch_01_A_GOLD.pdf", "relative_path": "output/2026-04-27/print/model_01/rendered/roll_batch_01_A_GOLD.pdf", "type": "RULO TOPLU PDF"},
                {"file_name": "order_111.png", "relative_path": "output/2026-04-27/print/model_01/rendered/order_111.png", "type": "PNG"},
                {"file_name": "plate_001.svg", "relative_path": "output/2026-04-27/laser/model_01/plate_001.svg", "type": "SVG PLAKA"},
            ]

            result = add_label_outputs_to_queue(tmp_path, outputs)
            rows = list_print_queue(tmp_path)

            self.assertEqual(result["added"], "1")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["job_type"], "Toplu")
            self.assertTrue(rows[0]["relative_path"].endswith(".pdf"))

    def test_bulk_label_usage_counts_selected_excel_models(self) -> None:
        with temp_workspace() as tmp_path:
            excel_path = tmp_path / "input" / "orders.xlsx"
            excel_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(
                [
                    {"order_no": "1", "model_no": "02", "template_no": "A", "label_variant": "GOLD", "process_type": PRINT, "quantity": 2, "label_text": "Ayşe"},
                    {"order_no": "2", "model_no": "02", "template_no": "A", "label_variant": "GOLD", "process_type": BOTH, "quantity": 3, "label_text": "Mehmet", "date_text": "12.05.2026", "note_text": "Söz"},
                    {"order_no": "3", "model_no": "03", "template_no": "B", "label_variant": "PINK", "process_type": LASER_ENGRAVE, "quantity": 1},
                    {"order_no": "4", "model_no": "09", "template_no": "X", "label_variant": "WHITE", "process_type": PRINT, "quantity": 1, "label_text": "Eksik"},
                ]
            ).to_excel(excel_path, index=False)
            models = [
                {
                    "model_no": "02",
                    "template_no": "A",
                    "label_variant": "GOLD",
                    "model_name": "Bordolu Gold Etiket",
                    "preview_image": "file:///preview.png",
                    "size_text": "50 x 30 mm",
                    "active": "true",
                }
            ]

            rows = used_label_models(tmp_path, excel_path, models)
            samples = preview_samples(tmp_path, excel_path, models)

            gold = next(row for row in rows if row["model_no"] == "02")
            missing = next(row for row in rows if row["model_no"] == "09")
            self.assertEqual(gold["order_count"], "2")
            self.assertEqual(gold["quantity_total"], "5")
            self.assertFalse(gold["missing_model"])
            self.assertTrue(missing["missing_model"])
            self.assertIn("Model bulunamadı", missing["warning"])
            self.assertEqual(samples[0]["label_text"], "Ayşe")
            self.assertEqual(samples[1]["date_text"], "12.05.2026")

    def test_selected_bulk_rows_excel_contains_only_chosen_rows(self) -> None:
        with temp_workspace() as tmp_path:
            excel_path = tmp_path / "input" / "orders.xlsx"
            excel_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(
                [
                    {"order_no": "1", "model_no": "02", "template_no": "A", "label_variant": "GOLD", "process_type": PRINT, "quantity": 2, "label_text": "Ayşe"},
                    {"order_no": "2", "model_no": "02", "template_no": "A", "label_variant": "GOLD", "process_type": BOTH, "quantity": 3, "label_text": "Mehmet"},
                    {"order_no": "3", "model_no": "02", "template_no": "A", "label_variant": "GOLD", "process_type": PRINT, "quantity": 1, "label_text": "Zeynep"},
                ]
            ).to_excel(excel_path, index=False)

            result = write_selected_rows_excel(tmp_path, excel_path, ["3"])

            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["row_count"], 1)
            selected = read_orders_excel(Path(str(result["path"])))
            self.assertEqual(list(selected["label_text"]), ["Mehmet"])
            self.assertTrue(str(result["relative_path"]).startswith("output/"))

    def test_manual_print_queue_and_safe_print_fallback(self) -> None:
        with temp_workspace() as tmp_path:
            pdf_path = tmp_path / "output" / "2026-04-27" / "print" / "manual" / "manual_batch_ayse_mehmet.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-1.4\n")
            add_to_print_queue(
                tmp_path,
                {
                    "job_name": "Manuel Etiket - Ayşe & Mehmet",
                    "job_type": "Manuel",
                    "quantity": "10",
                    "file_type": "MANUEL RULO TOPLU PDF",
                    "relative_path": "output/2026-04-27/print/manual/manual_batch_ayse_mehmet.pdf",
                },
            )
            row = list_print_queue(tmp_path)[0]

            fallback = print_queue_item_safe(tmp_path, row["id"], direct_print_enabled=False)
            marked = mark_queue_item_printed(tmp_path, row["id"])
            pending = mark_queue_item_pending(tmp_path, row["id"])

            self.assertEqual(fallback["status"], "MANUAL_PRINT_REQUIRED")
            self.assertIn("Doğrudan yazdırma", fallback["message"])
            self.assertEqual(marked["status"], "OK")
            self.assertEqual(pending["status"], "OK")
            self.assertEqual(list_print_queue(tmp_path)[0]["status"], "Beklemede")
            removed = remove_from_print_queue(tmp_path, row["id"])
            self.assertEqual(removed["status"], "OK")
            self.assertEqual(list_print_queue(tmp_path), [])

    def test_template_pack_import_rejects_path_traversal(self) -> None:
        with temp_workspace() as tmp_path:
            zip_path = tmp_path / "unsafe.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("../outside.json", "{}")

            result = safe_extract_template_pack(zip_path, tmp_path, run_date=pd.Timestamp("2026-04-27").date())

            self.assertTrue(any(row["status"] == "ERROR_INVALID_PATH" for row in result.rows))
            self.assertFalse((tmp_path.parent / "outside.json").exists())

    def test_label_template_editor_updates_text_position(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template(tmp_path, width=50, height=30)
            data = load_template_data(template_path)

            update_text_element(
                data,
                x_mm=6,
                y_mm=8,
                width_mm=38,
                height_mm=12,
                font_family="Segoe UI",
                font_size=12,
                color="#111111",
                bold=True,
                italic=False,
                align="center",
                vertical_align="middle",
            )
            save_template_with_backup(tmp_path, data, overwrite=True)
            updated = load_template_data(template_path)
            text = find_label_text_element(updated)

            self.assertEqual(text["x_mm"], 6)
            self.assertEqual(text["y_mm"], 8)
            self.assertEqual(text["width_mm"], 38)
            self.assertEqual(text["height_mm"], 12)

    def test_label_template_editor_updates_font_size(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template(tmp_path, width=50, height=30)
            data = load_template_data(template_path)

            update_text_element(
                data,
                x_mm=5,
                y_mm=9,
                width_mm=40,
                height_mm=11,
                font_family="Segoe UI",
                font_size=10.5,
                color="#2B2118",
                bold=False,
                italic=True,
                align="right",
                vertical_align="bottom",
            )
            save_template_with_backup(tmp_path, data, overwrite=True)
            text = find_label_text_element(load_template_data(template_path))

            self.assertEqual(text["font_size"], 10.5)
            self.assertFalse(text["bold"])
            self.assertTrue(text["italic"])
            self.assertEqual(text["align"], "right")
            self.assertEqual(text["vertical_align"], "bottom")

    def test_label_template_editor_toggles_decorative_line(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template(tmp_path, width=50, height=30)
            data = load_template_data(template_path)

            update_top_line(data, visible=False, x_mm=4, y_mm=6, width_mm=42, thickness_mm=0.3, color="#B9973E")
            save_template_with_backup(tmp_path, data, overwrite=True)
            updated = load_template_data(template_path)
            line = next(element for element in updated["elements"] if element.get("id") == "top_rule")

            self.assertFalse(line["visible"])
            self.assertEqual(line["x1_mm"], 4)
            self.assertEqual(line["x2_mm"], 46)

    def test_label_template_editor_saves_backup_before_overwrite(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template(tmp_path, width=50, height=30)
            data = load_template_data(template_path)
            data["template_name"] = "Updated Template"

            result = save_template_with_backup(tmp_path, data, overwrite=True)

            self.assertEqual(result.target_path, template_path)
            self.assertIsNotNone(result.backup_path)
            self.assertTrue(result.backup_path.exists())
            self.assertTrue((tmp_path / "templates" / "designs" / "backups").exists())

    def test_label_template_backup_restore_saves_current_version_first(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template(tmp_path, width=50, height=30)
            original = load_template_data(template_path)
            original["template_name"] = "Original Backup"
            template_path.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8")
            changed = dict(original)
            changed["template_name"] = "Changed Live Model"
            save_template_with_backup(tmp_path, changed, overwrite=True)
            backup_path = next((template_path.parent / "backups").glob("01_a_gold_*.json"))

            result = restore_label_model_backup(tmp_path, template_path, backup_path.relative_to(tmp_path).as_posix())
            restored = load_template_data(template_path)

            self.assertEqual(result["status"], "OK")
            self.assertEqual(restored["template_name"], "Original Backup")
            self.assertTrue(result["backup_current"])
            self.assertTrue((tmp_path / str(result["backup_current"])).exists())

    def test_label_template_editor_adds_and_removes_variable_fields(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template(tmp_path, width=50, height=30)
            data = load_template_data(template_path)
            data["fields"] = []

            add_variable_field(data, "name")
            add_variable_field(data, "date")
            add_variable_field(data, "note")
            custom = add_variable_field(data, "custom")
            removed = remove_variable_field(data, 1)

            self.assertEqual(data["fields"][0]["excel_column"], "label_text")
            self.assertEqual(custom["excel_column"], "custom_text_1")
            self.assertEqual(removed["excel_column"], "date_text")
            self.assertEqual(len(data["fields"]), 3)

    def test_label_template_field_validation_blocks_out_of_bounds(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template(tmp_path, width=50, height=30)
            data = load_template_data(template_path)
            data["fields"] = []
            add_variable_field(data, "name")
            update_variable_field(data, 0, x_mm=45, y_mm=10, width_mm=10, height_mm=6)

            with self.assertRaises(Exception):
                save_template_with_backup(tmp_path, data, overwrite=True)

    def test_field_font_path_is_saved_and_font_file_is_imported(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template(tmp_path, width=50, height=30)
            data = load_template_data(template_path)
            data["fields"] = []
            add_variable_field(data, "name")
            font_source = tmp_path / "incoming" / "custom_font.ttf"
            font_source.parent.mkdir(parents=True, exist_ok=True)
            font_source.write_bytes(b"fake font")

            relative_font = import_font_file(tmp_path, font_source)
            update_variable_field(data, 0, font_family="Custom Font", font_path=relative_font)
            save_template_with_backup(tmp_path, data, overwrite=True)
            updated = load_template_data(template_path)

            self.assertEqual(updated["fields"][0]["font_path"], relative_font)
            self.assertTrue((tmp_path / relative_font).exists())

    def test_web_label_model_field_save_updates_position_and_warns_for_missing_font(self) -> None:
        with temp_workspace() as tmp_path:
            template_path = write_label_template_with_fields(tmp_path)

            result = save_label_model_field(
                tmp_path,
                template_path,
                0,
                {
                    "x_mm": 6,
                    "y_mm": 7,
                    "width_mm": 30,
                    "height_mm": 6,
                    "font_family": "Missing Custom",
                    "font_path": "assets/fonts/missing.ttf",
                    "font_size": 12,
                    "color": "#111111",
                    "align": "center",
                    "vertical_align": "middle",
                },
            )
            data = load_template_data(template_path)

            self.assertEqual(result["status"], "OK")
            self.assertIn("fallback", result["font_warning"])
            self.assertEqual(data["fields"][0]["x_mm"], 6)
            self.assertEqual(data["fields"][0]["font_path"], "assets/fonts/missing.ttf")

    def test_label_template_editor_renders_preview_after_edit(self) -> None:
        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            template_path = write_label_template(tmp_path, width=50, height=30)
            data = load_template_data(template_path)
            update_text_element(
                data,
                x_mm=5,
                y_mm=9,
                width_mm=40,
                height_mm=11,
                font_family="Segoe UI",
                font_size=12,
                color="#2B2118",
                bold=True,
                italic=False,
                align="center",
                vertical_align="middle",
            )
            save_template_with_backup(tmp_path, data, overwrite=True)

            pdf_path, png_path = render_sample_template(tmp_path, template_path, "Ayşe & Mehmet", tmp_path / "preview")

            self.assertTrue(pdf_path.exists())
            self.assertTrue(png_path.exists())

    def test_manual_preview_uses_real_renderer_png_and_web_url(self) -> None:
        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            template_path = write_label_template_with_fields(tmp_path)

            result = render_manual_preview(
                tmp_path,
                template_path,
                "Ayşe & Mehmet",
                pd.Timestamp("2026-04-27").date(),
                field_values={"date_text": "12.05.2026", "note_text": "Söz Hatırası", "custom_text_1": "Gold"},
            )
            payload = preview_manual(
                tmp_path,
                template_path,
                {"label_text": "Ayşe & Mehmet", "date_text": "12.05.2026", "note_text": "Söz Hatırası"},
            )

            self.assertTrue(result.png_path.exists())
            self.assertEqual(payload["status"], "OK")
            self.assertTrue(payload["preview_url"].startswith("file:///"))

    def test_manual_label_service_generates_pdf_png_and_batch(self) -> None:
        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            template_path = write_label_template(tmp_path, width=50, height=30)

            result = render_manual_label(tmp_path, template_path, "Ayşe & Mehmet", 2, pd.Timestamp("2026-04-27").date())

            self.assertTrue(result.pdf_path.exists())
            self.assertTrue(result.png_path.exists())
            self.assertTrue(result.batch_pdf_path.exists())
            self.assertEqual(_pdf_page_count(result.batch_pdf_path), 2)

    def test_manual_label_service_accepts_model_field_values(self) -> None:
        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            template_path = write_label_template_with_fields(tmp_path)

            result = render_manual_label(
                tmp_path,
                template_path,
                "Ayşe & Mehmet",
                3,
                pd.Timestamp("2026-04-27").date(),
                field_values={"date_text": "12.05.2026", "note_text": "Söz Hatırası"},
            )

            self.assertTrue(result.pdf_path.exists())
            self.assertEqual(_pdf_page_count(result.batch_pdf_path), 3)

    def test_studio_final_render_uses_canvas_background_and_latest_text_fields(self) -> None:
        from PySide6.QtGui import QColor, QImage

        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            bg_path = tmp_path / "assets" / "label_backgrounds" / "flower_test.png"
            bg_path.parent.mkdir(parents=True, exist_ok=True)
            image = QImage(600, 360, QImage.Format_RGB32)
            image.fill(QColor("#D71920"))
            self.assertTrue(image.save(str(bg_path), "PNG"))
            template_path = write_label_template_with_fields(tmp_path, preview_image="assets/label_backgrounds/flower_test.png")
            data = load_template_data(template_path)
            data["background_image"] = "assets/label_backgrounds/missing_old_background.png"
            data["background_enabled"] = True
            data["preview_usage"] = "production_background"
            data["elements"].insert(
                0,
                {
                    "type": "rectangle",
                    "id": "legacy_background",
                    "visible": True,
                    "x_mm": 0,
                    "y_mm": 0,
                    "width_mm": 50,
                    "height_mm": 30,
                    "fill_color": "#FFF8E6",
                    "stroke_color": "#B9973E",
                    "stroke_width": 0.35,
                },
            )
            save_template_with_backup(tmp_path, data, overwrite=True)
            fields = data["fields"]

            result = render_manual_label(
                tmp_path,
                template_path,
                "Mücahit Leyla",
                1,
                pd.Timestamp("2026-05-07").date(),
                field_values={
                    "_studio_render_state": "true",
                    "_background_image": bg_path.resolve().as_uri(),
                    "_fields": fields,
                    "label_text": "Mücahit Leyla",
                    "date_text": "18.06.2026",
                    "note_text": "Nişan hatırası",
                    "custom_text_1": "",
                },
            )

            output = QImage(str(result.png_path))
            self.assertFalse(output.isNull())
            sample = QColor(output.pixel(20, 20))
            self.assertGreater(sample.red(), 190)
            self.assertLess(sample.green(), 80)
            dark_pixels = 0
            for x in range(0, output.width(), 8):
                for y in range(0, output.height(), 8):
                    color = QColor(output.pixel(x, y))
                    if color.red() < 80 and color.green() < 80 and color.blue() < 80:
                        dark_pixels += 1
            self.assertGreater(dark_pixels, 0)

            pdf_payload = get_pdf_preview_payload(tmp_path, result.batch_pdf_path.relative_to(tmp_path).as_posix())
            self.assertEqual(pdf_payload["status"], "OK")
            self.assertTrue(pdf_payload["preview_pages"])
            pdf_page = QImage(str(tmp_path / pdf_payload["preview_pages"][0]["preview_png_path"]))
            self.assertFalse(pdf_page.isNull())

            def dark_pixels_for_rect(image: QImage, x0: int, y0: int, x1: int, y1: int) -> int:
                count = 0
                for x in range(x0, x1, max(1, (x1 - x0) // 30)):
                    for y in range(y0, y1, max(1, (y1 - y0) // 15)):
                        color = QColor(image.pixel(x, y))
                        if color.red() < 120 and color.green() < 120 and color.blue() < 120:
                            count += 1
                return count

            for field in fields:
                if field["excel_column"] not in {"label_text", "date_text", "note_text"}:
                    continue
                x0 = max(0, int(float(field["x_mm"]) / 50 * output.width()))
                y0 = max(0, int(float(field["y_mm"]) / 30 * output.height()))
                x1 = min(output.width(), int((float(field["x_mm"]) + float(field["width_mm"])) / 50 * output.width()))
                y1 = min(output.height(), int((float(field["y_mm"]) + float(field["height_mm"])) / 30 * output.height()))
                png_dark = dark_pixels_for_rect(output, x0, y0, x1, y1)
                self.assertGreater(png_dark, 0)

            pdf_dark_pixels = 0
            for x in range(0, pdf_page.width(), 8):
                for y in range(0, pdf_page.height(), 8):
                    color = QColor(pdf_page.pixel(x, y))
                    if color.red() < 80 and color.green() < 80 and color.blue() < 80:
                        pdf_dark_pixels += 1
            self.assertGreater(pdf_dark_pixels, 0)
            ratio = pdf_dark_pixels / dark_pixels
            self.assertLess(ratio, 3.0)
            self.assertGreater(ratio, 0.25)

    def test_production_preflight_output_validation_and_history_are_real_gates(self) -> None:
        from PySide6.QtGui import QColor, QImage

        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            bg_path = tmp_path / "assets" / "label_backgrounds" / "preflight_flower.png"
            bg_path.parent.mkdir(parents=True, exist_ok=True)
            bg = QImage(600, 360, QImage.Format_RGB32)
            bg.fill(QColor("#D71920"))
            self.assertTrue(bg.save(str(bg_path), "PNG"))
            template_path = write_label_template_with_fields(tmp_path, preview_image="assets/label_backgrounds/preflight_flower.png")
            data = load_template_data(template_path)
            data["background_image"] = "assets/label_backgrounds/preflight_flower.png"
            data["background_enabled"] = True
            save_template_with_backup(tmp_path, data, overwrite=True)

            payload = {
                "_studio_render_state": "true",
                "_background_image": "assets/label_backgrounds/preflight_flower.png",
                "_fields": data["fields"],
                "label_text": "Ayşe & Mehmet",
                "date_text": "18.06.2026",
                "note_text": "Nişan hatırası",
                "_label_width_mm": 50,
                "_label_height_mm": 30,
            }
            preflight = preflight_manual_label(tmp_path, template_path, payload, 2)
            self.assertNotEqual(preflight["status"], "ERROR")
            self.assertTrue(preflight["can_render"])

            result = render_manual_label(
                tmp_path,
                template_path,
                "Ayşe & Mehmet",
                2,
                pd.Timestamp("2026-05-07").date(),
                field_values=payload,
            )
            validation = validate_manual_output(tmp_path, result.__dict__ | {"_render_started_at": "2000-01-01T00:00:00"}, payload)
            self.assertEqual(validation["status"], "OK", validation)

            placeholder = tmp_path / "output" / "2026-05-07" / "print" / "manual" / "placeholder.png"
            placeholder.parent.mkdir(parents=True, exist_ok=True)
            cream = QImage(600, 360, QImage.Format_RGB32)
            cream.fill(QColor("#FFF8E6"))
            self.assertTrue(cream.save(str(placeholder), "PNG"))
            invalid = validate_manual_output(tmp_path, {"png_path": str(placeholder), "pdf_path": str(result.pdf_path)}, payload)
            self.assertEqual(invalid["status"], "ERROR")

            entry = append_production_history(
                tmp_path,
                template_path,
                payload,
                2,
                result.__dict__,
                preflight,
                validation,
                queue_result={"status": "QUEUED"},
            )
            rows = list_production_history(tmp_path)
            self.assertEqual(rows[0]["id"], entry["record"]["id"])
            self.assertEqual(rows[0]["label_text"], "Ayşe & Mehmet")
            self.assertTrue(rows[0]["pdf_path"].endswith(".pdf"))

            health = model_health_for_template(tmp_path, template_path)
            self.assertEqual(health["status"], "Hazır")

        with temp_workspace() as tmp_path:
            write_minimal_config(tmp_path)
            bad_template = write_label_template_with_fields(tmp_path, preview_image="")
            bad = preflight_manual_label(tmp_path, bad_template, {"label_text": "Ayşe"}, 1)
            self.assertEqual(bad["status"], "ERROR")
            self.assertFalse(bad["can_render"])
            self.assertTrue(any("görsel" in error.lower() for error in bad["errors"]))

    def test_webui_uses_existing_local_assets(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")

        self.assertIn('href="./styles.css"', html)
        self.assertIn('src="./app.js"', html)
        self.assertTrue((project_root / "src" / "webui" / "styles.css").exists())
        self.assertTrue((project_root / "src" / "webui" / "app.js").exists())
        self.assertNotIn("style.css", html.replace("./styles.css", ""))
        self.assertIn("CDR / AI Model", html)

    def test_webui_distinguishes_print_templates_from_label_outputs(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Baskı Şablonları Klasörünü Aç", html)
        self.assertIn("Baskı Şablonlarını Gör", html)
        self.assertIn("ETİKET MODEL KÜTÜPHANESİ", html)
        self.assertIn("Etiket Model Galerisini Aç", html)
        self.assertIn("Etiket Çıktıları Klasörünü Aç", html)
        self.assertIn("Etiket Çıktılarını Gör", html)
        self.assertIn("Şablon dosyaları üretimden önce kullanılan kaynak dosyalardır.", html)
        self.assertIn("Etiket çıktıları ise üretimden sonra oluşturulan PDF/PNG dosyalarıdır.", html)
        self.assertIn("AI/CDR dosyası kaynak tasarımdır", html)
        self.assertIn("Program içinde doğru tasarımı görmek", html)
        self.assertIn("manualModelGallery", html)
        self.assertIn("Önizleme Görseli Seç", html)
        self.assertIn("Teknik: Klasörde Göster", html)
        self.assertIn("Toplu Etiket (Excel)", html)
        self.assertIn("Yazdırma Sırası", html)
        self.assertIn("Hepsini Oluştur ve Sıraya Ekle", html)
        self.assertIn("Son Çalışma", html)
        self.assertIn("Kullanılacak Etiket Modelleri", html)
        self.assertIn("Üretilecek Rulo Batch PDF", html)
        self.assertIn("Harici Programda Aç", html)
        self.assertNotIn(">Etiket Klasörünü Aç<", html)

    def test_safe_p2_polish_controls_are_present_without_touching_output_chain(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
        app = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
        css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")
        bulk_api = (project_root / "src" / "webui_backend" / "bulk_label_api.py").read_text(encoding="utf-8")
        template_api = (project_root / "src" / "webui_backend" / "template_api.py").read_text(encoding="utf-8")
        desktop = (project_root / "src" / "desktop" / "web_main_window.py").read_text(encoding="utf-8")

        self.assertIn("labelOutputModelFilter", html)
        self.assertIn("labelOutputDateFilter", html)
        self.assertIn("labelOutputTabs", html)
        self.assertIn("data-output-tab=\"batch\"", html)
        self.assertIn("data-output-tab=\"technical\"", html)
        self.assertIn("renderBulkRealMiniPreviews", html)
        self.assertIn("renderSelectedBulkMiniPreviews", html)
        self.assertIn("selectedBulkRunCard", html)
        self.assertIn("Seçili Satırları Render Et", html)
        self.assertIn("modelBackupHistory", html)
        self.assertIn("settingsBackupInfo", html)
        self.assertIn("Yedekleme ve Geri Alma", html)
        self.assertIn("Tüm modeller", html)
        self.assertIn("Son 7 gün", html)
        self.assertIn("align-tool", html)
        self.assertIn("Seçili yazıyı etiket merkezine alır", html)

        self.assertIn("bulk-row-mini-preview", app)
        self.assertIn("historyForOutputPath", app)
        self.assertIn("output-production-meta", app)
        self.assertIn("Model: ${esc(modelLabel)}", app)
        self.assertIn("Adet: ${esc(quantity)}", app)
        self.assertIn("outputModelLabel", app)
        self.assertIn("matchesDateFilter", app)
        self.assertIn("function selectLabelOutputTab", app)
        self.assertIn("function updateLabelOutputTabs", app)
        self.assertIn("function outputPreviewForPath", app)
        self.assertIn("function openOutputHistoryInStudio", app)
        self.assertIn("function reproduceOutputFromHistory", app)
        self.assertIn("Studio’da Aç", app)
        self.assertIn("Tekrar Üret", app)
        self.assertIn("Klasörde Göster", app)
        self.assertIn("function renderBulkRealMiniPreviews", app)
        self.assertIn("function renderSelectedBulkMiniPreviews", app)
        self.assertIn("function generateSelectedBulkRowsAndQueue", app)
        self.assertIn("function selectedBulkPreviewRowNumbers", app)
        self.assertIn("function updateSelectedBulkRunCard", app)
        self.assertIn("function setSelectedBulkRunState", app)
        self.assertIn("function syncSelectedBulkRunFromState", app)
        self.assertIn("selectedBulkRunState", app)
        self.assertTrue((project_root / "scripts" / "bulk_label_real_user_gate.py").exists())
        self.assertTrue((project_root / "scripts" / "production_history_real_user_gate.py").exists())
        self.assertTrue((project_root / "scripts" / "label_outputs_gallery_gate.py").exists())
        self.assertIn("Üretim kuyruğa alındı", app)
        self.assertIn("Üretim tamamlandı", app)
        self.assertIn("bulkSelectedRun", app)
        self.assertIn("function loadSelectedModelBackupHistory", app)
        self.assertIn("function saveSelectedModelBackupNote", app)
        self.assertIn("function selectBackupForPairCompare", app)
        self.assertIn("function compareTwoSelectedBackups", app)
        self.assertIn("function compareSelectedModelBackup", app)
        self.assertIn("function backupCompareDetailHtml", app)
        self.assertIn("function backupDiffValue", app)
        self.assertIn("function restoreSelectedModelBackup", app)
        self.assertIn("function hydrateQueuePdfThumbnails", app)
        self.assertIn("function bulkIssueCategory", app)
        self.assertIn("bulk-issue-breakdown", app)
        self.assertIn("queue-safe-note", app)
        self.assertIn("queue-thumb", app)
        self.assertIn("data-pdf-thumb-path", app)
        self.assertIn("Teknik arşiv", app)
        self.assertIn("render_status", app)
        self.assertIn("bulk-preview-row-select", app)
        self.assertIn("Mevcutle Karşılaştır", app)
        self.assertIn("Yazıcı otomatik çalışmaz. PDF’i kontrol ettikten sonra manuel yazdırın.", app)
        self.assertIn("function repairBackupLine", app)
        self.assertIn("Backup alındı:", app)
        self.assertIn("settingsBackupInfo", app)
        self.assertIn("AI/CDR overwrite edilmez", app)

        self.assertIn(".bulk-row-mini-preview", css)
        self.assertIn(".bulk-issue-breakdown", css)
        self.assertIn(".output-tabs", css)
        self.assertIn(".output-tab.active", css)
        self.assertIn(".output-tab.subtle", css)
        self.assertIn(".technical-output-item", css)
        self.assertIn(".output-production-meta", css)
        self.assertIn(".queue-meta", css)
        self.assertIn(".queue-thumb", css)
        self.assertIn(".queue-safe-note", css)
        self.assertIn("Print queue compact card polish", css)
        self.assertIn("#printQueue .queue-thumb", css)
        self.assertIn("object-fit: contain !important;", css)
        self.assertIn("height: 78px !important;", css)
        self.assertIn("#printQueue .queue-card", css)
        self.assertIn("align-items: center !important;", css)
        self.assertIn("Cross-page UI density polish", css)
        self.assertIn("#labelModels .model-preview", css)
        self.assertIn("height: clamp(145px, 14vw, 178px);", css)
        self.assertIn("#label .manual-studio", css)
        self.assertIn("clamp(330px, 25vw, 390px)", css)
        self.assertIn("#bulkLabel .bulk-row-mini-preview", css)
        self.assertIn("#labelOutputs .output-thumb", css)
        self.assertIn("#labelOutputs .output-filter-bar", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr) minmax(360px, 420px);", css)
        self.assertIn("#labelOutputs .output-stack", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", css)
        self.assertIn("grid-template-columns: minmax(220px, 1fr) minmax(220px, 1fr);", css)
        self.assertIn("#labelOutputs .output-filter-bar .btn", css)
        self.assertIn("#settings .settings-layout .card", css)
        self.assertIn(".model-backup-panel", css)
        self.assertIn(".backup-compare-result", css)
        self.assertIn(".backup-diff-detail", css)
        self.assertIn(".backup-diff-row", css)
        self.assertIn(".backup-version-note-input", css)
        self.assertIn(".bulk-row-select", css)
        self.assertIn(".selected-bulk-run-card", css)
        self.assertIn(".selected-bulk-run-card.pending", css)
        self.assertIn(".history-match-meta", css)
        self.assertIn(".btn.danger-soft", css)
        self.assertIn(".settings-backup-step", css)
        self.assertIn(".align-tool", css)

        self.assertIn('"row_number"', bulk_api)
        self.assertIn("row_numbers", bulk_api)
        self.assertIn("def write_selected_rows_excel", bulk_api)
        self.assertIn("def render_preview_samples", bulk_api)
        self.assertIn("preview_manual", bulk_api)
        self.assertIn("Model pasif görünüyor. Üretimden önce kontrol edin.", bulk_api)
        self.assertIn("self.bulk_selected_run", desktop)
        self.assertIn('"bulkSelectedRun"', desktop)
        self.assertIn('"status": "COMPLETED"', desktop)
        self.assertNotIn("Model pasif grnyor", bulk_api)
        self.assertNotIn("retimden nce", bulk_api)
        self.assertIn("def compare_label_model_backup", template_api)
        self.assertIn("def restore_label_model_backup", template_api)
        self.assertIn('"setting_diffs"', template_api)
        self.assertIn('"field_diffs"', template_api)
        self.assertIn("Geçersiz backup yolu.", template_api)
        self.assertIn("Mevcut model ile backup arasında önemli fark görünmüyor.", template_api)

    def test_webui_visible_buttons_have_bridge_methods(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        bridge_source = (project_root / "src" / "webui_backend" / "bridge.py").read_text(encoding="utf-8")

        for method_name in (
            "chooseExcel",
            "runDry",
            "runProduction",
            "renderLabels",
            "openOutput",
            "openReports",
            "openPrint",
            "openPrintTemplates",
            "openLaser",
            "create_template",
            "create_demo",
            "convert_legacy_excel",
            "import_template_pack",
            "create_label_model_from_source",
            "list_print_templates",
            "get_print_template_detail",
            "save_print_template_metadata",
            "create_linked_label_design",
            "list_label_outputs",
            "get_pdf_preview_payload",
            "list_laser_outputs",
            "list_label_model_gallery",
            "list_label_model_backups",
            "compare_label_model_backup",
            "set_label_model_backup_note",
            "compare_label_model_backup_pair",
            "restore_label_model_backup",
            "choose_label_model_preview",
            "render_manual_label_fields",
            "open_project_file",
            "bulk_generate_and_add_to_queue",
            "bulk_generate_selected_and_add_to_queue",
            "prepare_selected_bulk_excel",
            "render_bulk_preview_samples",
            "render_selected_bulk_preview_samples",
            "render_manual_label_fields_to_queue",
            "list_print_queue",
            "add_label_outputs_to_print_queue",
            "add_pdf_output_to_print_queue",
            "remove_from_print_queue",
            "mark_queue_item_printed",
            "clear_print_queue",
            "print_queue_item_safe",
        ):
            self.assertIn(f"def {method_name}", bridge_source)


class temp_workspace:
    def __enter__(self) -> Path:
        self.path = Path(__file__).resolve().parents[1] / ".test_tmp" / uuid.uuid4().hex
        self.path.mkdir(parents=True, exist_ok=True)
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def make_settings(tmp_path: Path) -> AppSettings:
    project_root = tmp_path
    input_dir = project_root / "input"
    output_dir = project_root / "output"
    print_templates_dir = project_root / "templates" / "print"
    laser_templates_dir = project_root / "templates" / "laser"
    font_path = project_root / "assets" / "fonts" / "connected_script.ttf"

    for path in (input_dir, output_dir, print_templates_dir, laser_templates_dir, font_path.parent):
        path.mkdir(parents=True, exist_ok=True)

    return AppSettings(
        project_root=project_root,
        app=AppConfig(output_date_format="%Y-%m-%d", language="tr"),
        excel=ExcelSettings(mode="clean_production_excel", input_file=input_dir / "siparisler.xlsx"),
        print=PrintSettings(generate_print_data_csv=True, auto_print_enabled=False),
        label_defaults=LabelDefaults(),
        reports=ReportSettings(
            generate_errors_report=True,
            generate_summary_report=True,
            generate_layout_report=True,
            generate_template_matching_report=True,
        ),
        input_excel=input_dir / "siparisler.xlsx",
        output_dir=output_dir,
        print_templates_dir=print_templates_dir,
        laser_templates_dir=laser_templates_dir,
        required_columns=list(PRODUCTION_COLUMNS),
        optional_columns=[],
        valid_process_types={PRINT, LASER_ENGRAVE, LASER_CUT, BOTH, "NONE"},
        valid_personalization_types={"LABEL", "NAME", "LABEL_AND_NAME", "NO_PERSONALIZATION"},
        valid_label_variants={"GOLD", "SILVER", "WHITE", "RED", "CUSTOM", "NONE"},
        valid_statuses={"NEW", "READY", "NEEDS_REVIEW", "COMPLETED", "CANCELLED"},
        print_processes={PRINT, BOTH},
        laser_processes={LASER_ENGRAVE, LASER_CUT, BOTH},
        laser=LaserSettings(
            auto_start_laser=False,
            output_format="svg",
            plate_width_mm=600,
            plate_height_mm=400,
            margin_mm=5,
            gap_x_mm=3,
            gap_y_mm=3,
            include_order_number_guide=True,
        ),
        laser_text=LaserTextSettings(
            laser_font_path=font_path,
            default_font_size_mm=28,
            min_font_size_mm=18,
            max_font_size_mm=36,
            force_connected_letters=True,
            convert_text_to_paths=True,
            warn_if_disconnected_shapes=True,
            add_bridges_for_dots_and_accents=False,
        ),
    )


def valid_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "order_no": "T-001",
        "buyer_name": "Ayşe",
        "product_name": "Gold Çikolata Etiketi",
        "model_no": "01",
        "template_no": "A",
        "process_type": PRINT,
        "personalization_type": "LABEL",
        "label_variant": "GOLD",
        "label_text": "Ayşe",
        "laser_text": "",
        "quantity": 2,
        "material_type": "",
        "material_thickness_mm": "",
        "extra_chocolate_qty": 0,
        "extra_madlen_qty": 0,
        "production_note": "",
        "needs_review": "",
        "status": "NEW",
    }
    row.update(overrides)
    return row


def make_order(**overrides: object) -> Order:
    data = valid_row(**overrides)
    return Order(
        row_number=int(overrides.get("row_number", 2)),
        order_no=str(data["order_no"]),
        buyer_name=str(data["buyer_name"]),
        product_name=str(data["product_name"]),
        model_no=str(data["model_no"]),
        template_no=str(data["template_no"]),
        process_type=str(data["process_type"]),
        personalization_type=str(data["personalization_type"]),
        label_variant=str(data["label_variant"]),
        label_text=str(data["label_text"]),
        laser_text=str(data["laser_text"]),
        quantity=int(data["quantity"]),
        material_type=str(data["material_type"]),
        material_thickness_mm=str(data["material_thickness_mm"]),
        extra_chocolate_qty=int(data["extra_chocolate_qty"]),
        extra_madlen_qty=int(data["extra_madlen_qty"]),
        production_note=str(data["production_note"]),
        needs_review=str(data["needs_review"]),
        status=str(data["status"]),
        source=data,
    )


def write_label_template(
    tmp_path: Path,
    width: float = 70,
    height: float = 35,
    include_roll_size: bool = True,
    include_order_size: bool = False,
) -> Path:
    templates_dir = tmp_path / "templates" / "designs"
    templates_dir.mkdir(parents=True, exist_ok=True)
    template_path = templates_dir / "01_a_gold.json"
    payload = {
        "template_id": "01_a_gold",
        "model_no": "01",
        "template_no": "A",
        "label_variant": "GOLD",
        "media_type": "ROLL",
        "canvas_width_mm": width,
        "canvas_height_mm": height,
        "background_image": "",
        "elements": [
            {
                "type": "rectangle",
                "id": "border",
                "x_mm": 1,
                "y_mm": 1,
                "width_mm": max(width - 2, 1),
                "height_mm": max(height - 2, 1),
                "stroke_color": "#B9973E",
                "stroke_width": 0.4,
                "fill_color": "#FFFFFF",
            },
            {
                "type": "text",
                "id": "label_text",
                "placeholder": "{{LABEL_TEXT}}",
                "x_mm": 5,
                "y_mm": 10,
                "width_mm": max(width - 10, 1),
                "height_mm": 10,
                "font_family": "Segoe UI",
                "font_size": 16,
                "color": "#1F2933",
                "bold": True,
                "italic": False,
                "align": "center",
                "vertical_align": "center",
                "rotation": 0,
            },
        ],
    }
    if include_order_size:
        payload["elements"].append(
            {
                "type": "text",
                "id": "order_no",
                "placeholder": "Sipariş: {{ORDER_NO}}",
                "x_mm": 5,
                "y_mm": max(height - 8, 1),
                "width_mm": max(width - 10, 1),
                "height_mm": 5,
                "font_family": "Segoe UI",
                "font_size": 7,
                "color": "#6B5A2A",
                "bold": False,
                "italic": False,
                "align": "center",
                "vertical_align": "center",
                "rotation": 0,
            }
        )
    if include_roll_size:
        payload.update(
            {
                "label_width_mm": width,
                "label_height_mm": height,
                "roll_gap_mm": 3,
                "printer_dpi": 300,
                "copies_per_order": 1,
            }
        )
    template_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return template_path


def write_label_template_with_fields(
    tmp_path: Path,
    preview_image: str = "",
    extra_column: str = "",
    source_file: str = "templates/print/01_a_gold.ai",
) -> Path:
    templates_dir = tmp_path / "templates" / "designs"
    templates_dir.mkdir(parents=True, exist_ok=True)
    template_path = templates_dir / "01_a_gold.json"
    fields = [
        {
            "field_name": "İsim",
            "placeholder": "{{LABEL_TEXT}}",
            "excel_column": "label_text",
            "x_mm": 5,
            "y_mm": 8,
            "width_mm": 40,
            "height_mm": 8,
            "font_family": "Segoe UI",
            "font_size": 12,
            "color": "#111111",
            "align": "center",
            "vertical_align": "middle",
            "bold": False,
            "italic": False,
        },
        {
            "field_name": "Tarih",
            "placeholder": "{{DATE_TEXT}}",
            "excel_column": "date_text",
            "x_mm": 5,
            "y_mm": 17,
            "width_mm": 40,
            "height_mm": 5,
            "font_family": "Segoe UI",
            "font_size": 7,
            "color": "#111111",
            "align": "center",
            "vertical_align": "middle",
            "bold": False,
            "italic": False,
        },
        {
            "field_name": "Not",
            "placeholder": "{{NOTE_TEXT}}",
            "excel_column": "note_text",
            "x_mm": 5,
            "y_mm": 23,
            "width_mm": 40,
            "height_mm": 4,
            "font_family": "Segoe UI",
            "font_size": 6,
            "color": "#111111",
            "align": "center",
            "vertical_align": "middle",
            "bold": False,
            "italic": False,
        },
    ]
    if extra_column:
        fields.append(
            {
                "field_name": "Eksik",
                "placeholder": "{{MISSING_COLUMN}}",
                "excel_column": extra_column,
                "x_mm": 1,
                "y_mm": 1,
                "width_mm": 10,
                "height_mm": 5,
                "font_family": "Segoe UI",
                "font_size": 6,
                "color": "#111111",
                "align": "center",
                "vertical_align": "middle",
                "bold": False,
                "italic": False,
            }
        )
    payload = {
        "model_no": "01",
        "template_no": "A",
        "label_variant": "GOLD",
        "model_name": "Bordolu Gold Etiket",
        "source_file": source_file,
        "preview_image": preview_image,
        "media_type": "ROLL",
        "label_width_mm": 50,
        "label_height_mm": 30,
        "active": True,
        "fields": fields,
        "elements": [],
    }
    template_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return template_path


def write_minimal_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config" / "settings.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
app:
  output_date_format: "%Y-%m-%d"
  language: "tr"
excel:
  mode: "clean_production_excel"
  input_file: "input/siparisler.xlsx"
templates:
  print_folder: "templates/print"
  laser_folder: "templates/laser"
print:
  mode: "label_designer"
  generate_print_data_csv: true
  auto_print_enabled: false
  allow_direct_print: false
  require_print_confirmation: true
  default_printer: ""
  use_default_label_settings: true
label_defaults:
  media_type: "ROLL"
  label_width_mm: 50
  label_height_mm: 30
  roll_gap_mm: 3
  printer_dpi: 300
  default_copies: 1
  horizontal_offset_mm: 0
  vertical_offset_mm: 0
  scale_percent: 100
  background_enabled: true
  show_cut_boundary: false
  safe_margin_mm: 1.5
  show_order_number_on_label: false
laser:
  auto_start_laser: false
  output_format: "svg"
  plate_width_mm: 600
  plate_height_mm: 400
  margin_mm: 5
  gap_x_mm: 3
  gap_y_mm: 3
  include_order_number_guide: true
laser_text:
  laser_font_path: "assets/fonts/connected_script.ttf"
  default_font_size_mm: 28
  min_font_size_mm: 18
  max_font_size_mm: 36
  force_connected_letters: true
  convert_text_to_paths: true
  warn_if_disconnected_shapes: true
  add_bridges_for_dots_and_accents: false
reports:
  generate_errors_report: true
  generate_summary_report: true
  generate_layout_report: true
  generate_template_matching_report: true
""",
        encoding="utf-8",
    )
    return config_path


def _pdf_media_box(path: Path) -> tuple[float, float, float, float]:
    content = path.read_bytes().decode("latin-1", errors="ignore")
    match = re.search(r"/MediaBox\s*\[\s*([0-9.\-]+)\s+([0-9.\-]+)\s+([0-9.\-]+)\s+([0-9.\-]+)\s*\]", content)
    if not match:
        raise AssertionError(f"PDF MediaBox bulunamadı: {path}")
    return tuple(float(item) for item in match.groups())  # type: ignore[return-value]


def _pdf_page_count(path: Path) -> int:
    content = path.read_bytes().decode("latin-1", errors="ignore")
    return len(re.findall(r"/Type\s*/Page\b", content))


def test_set_label_model_preview_updates_background_and_warning_payload(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path, source_file="templates/print/02 gold cyzella.ai")
    image_path = tmp_path / "real_preview.png"
    try:
        from PIL import Image

        Image.new("RGB", (500, 300), "white").save(image_path)
    except Exception:
        image_path.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff"
            b"\x00\x05\xfe\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    result = set_label_model_preview(tmp_path, template_path, image_path)
    data = json.loads(template_path.read_text(encoding="utf-8"))

    assert result["status"] == "OK"
    assert data["preview_image"].startswith("assets/label_backgrounds/")
    assert data["background_image"] == data["preview_image"]
    assert data["background_enabled"] is True
    assert (tmp_path / data["preview_image"]).exists()
    assert list((template_path.parent / "backups").glob("01_a_gold_*.json"))


def test_new_label_model_wizard_creates_user_friendly_model_with_basic_fields(tmp_path: Path):
    write_minimal_config(tmp_path)
    source = tmp_path / "incoming" / "new_model.png"
    source.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        Image.new("RGB", (600, 360), "white").save(source)
    except Exception:
        source.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff"
            b"\x00\x05\xfe\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    result = create_label_model_from_wizard(
        tmp_path,
        {
            "model_name": "Yeni Gold Model",
            "label_variant": "GOLD",
            "active": True,
            "label_width_mm": 50,
            "label_height_mm": 30,
        },
        source,
    )
    data = json.loads((tmp_path / result["path"]).read_text(encoding="utf-8"))

    assert result["status"] == "CREATED"
    assert data["model_name"] == "Yeni Gold Model"
    assert data["preview_image"].startswith("assets/label_backgrounds/")
    assert data["background_image"] == data["preview_image"]
    assert data["background_enabled"] is True
    assert [field["excel_column"] for field in data["fields"]] == ["label_text", "date_text", "note_text"]
    assert data["fields"][0]["field_name"] == "İsim"
    assert data["fields"][1]["field_name"] == "Tarih"
    assert data["fields"][2]["field_name"] == "Not"


def test_gallery_marks_missing_preview_as_design_position_not_approved(tmp_path: Path):
    write_minimal_config(tmp_path)
    write_label_template_with_fields(tmp_path, preview_image="", source_file="templates/print/02 gold cyzella.ai")

    gallery = list_label_model_gallery(tmp_path)
    model = gallery[0]

    assert model["preview_status"] == "YOK"
    assert model["design_position_status"] == "ONAYLANMADI"
    assert "Gerçek tasarım önizlemesi yok" in model["preview_warning"]
    assert "Tasarım konumu onaylanmadı" in model["design_position_warning"]


def test_gallery_does_not_mark_broken_preview_path_as_ready(tmp_path: Path):
    write_minimal_config(tmp_path)
    write_label_template_with_fields(
        tmp_path,
        preview_image="assets/label_backgrounds/missing_preview.png",
        source_file="templates/print/02 gold cyzella.ai",
    )

    model = list_label_model_gallery(tmp_path)[0]

    assert model["preview_status"] == "YOK"
    assert model["preview_image"] == ""
    assert model["preview_exists"] is False
    assert model["preview_missing_file"] is True


def test_user_friendly_add_remove_label_fields(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path)
    data = json.loads(template_path.read_text(encoding="utf-8"))
    data["fields"] = []
    template_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    added = add_label_model_field(tmp_path, template_path, "name")
    data = json.loads(template_path.read_text(encoding="utf-8"))

    assert added["status"] == "OK"
    assert data["fields"][0]["excel_column"] == "label_text"
    assert data["fields"][0]["placeholder"] == "{{LABEL_TEXT}}"
    assert list((template_path.parent / "backups").glob("01_a_gold_*.json"))

    removed = remove_label_model_field(tmp_path, template_path, 0)
    data = json.loads(template_path.read_text(encoding="utf-8"))
    assert removed["status"] == "OK"
    assert data["fields"] == []


def test_save_label_model_field_clamps_to_template_validation(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path)
    result = save_label_model_field(
        tmp_path,
        template_path,
        0,
        {
            "x_mm": 5,
            "y_mm": 5,
            "width_mm": 30,
            "height_mm": 8,
            "font_family": "Segoe UI",
            "font_size": 12,
            "color": "#111111",
            "align": "center",
            "vertical_align": "middle",
        },
    )
    data = json.loads(template_path.read_text(encoding="utf-8"))
    assert result["status"] == "OK"
    assert data["fields"][0]["x_mm"] == 5
    assert data["fields"][0]["width_mm"] == 30


def test_preview_binding_rejects_cdr_and_ai_as_preview_files(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path, source_file="templates/print/02 gold cyzella.ai")
    for suffix in (".cdr", ".ai"):
        source = tmp_path / f"wrong_preview{suffix}"
        source.write_bytes(b"source design")
        try:
            set_label_model_preview(tmp_path, template_path, source)
        except ValueError as exc:
            assert "kaynak tasar" in str(exc)
        else:
            raise AssertionError(f"{suffix} dosyasi onizleme olarak kabul edilmemeli")


def test_validate_model_preview_payload_and_ratio_status(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path, source_file="templates/print/02 gold cyzella.ai")
    image_path = tmp_path / "real_preview.png"
    try:
        from PIL import Image

        Image.new("RGB", (500, 300), "white").save(image_path)
    except Exception:
        image_path.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff"
            b"\x00\x05\xfe\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    bind_result = set_label_model_preview(tmp_path, template_path, image_path)
    result = validate_model_preview(tmp_path, template_path)

    assert bind_result["status"] == "OK"
    assert result["has_preview_image"] is True
    assert result["preview_exists"] is True
    assert str(result["preview_url"]).startswith("file:///")
    assert result["background_enabled"] is True
    assert result["background_image"] == result["preview_path"]
    assert result["ratio_status"] in {"OK", "WARNING"}


def test_set_label_model_preview_accepts_svg_as_preview_guide(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path, source_file="templates/print/02 gold cyzella.ai")
    svg_path = tmp_path / "preview.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="500" height="300"><rect width="500" height="300" fill="white"/></svg>',
        encoding="utf-8",
    )

    result = set_label_model_preview(tmp_path, template_path, svg_path)
    payload = validate_model_preview(tmp_path, template_path)

    assert result["status"] == "OK"
    assert result["background_enabled"] == "true"
    assert payload["has_preview_image"] is True
    assert str(payload["preview_path"]).endswith(".svg")
    assert str(payload["preview_url"]).startswith("file:///")


def test_native_edit_manifest_save_load(tmp_path: Path):
    manifest = create_manifest(tmp_path / "source.ai", "ai", "illustrator", "ai_test")
    add_warning(manifest, "Uyarı")
    add_error(manifest, "Hata")
    path = save_manifest(manifest, tmp_path / "manifest.json")

    loaded = load_manifest(path)

    assert loaded["source_format"] == "ai"
    assert loaded["editor_engine"] == "illustrator"
    assert loaded["warnings"] == ["Uyarı"]
    assert loaded["errors"] == ["Hata"]


def test_native_edit_prepare_input_copy_keeps_source_hash(tmp_path: Path):
    source = tmp_path / "templates" / "print" / "sample.ai"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"ai source")
    before = sha256_file(source)

    prepared = prepare_input_copy(tmp_path, source, "ai")

    assert prepared["input_copy"].exists()
    assert sha256_file(source) == before
    assert prepared["source_hash_before"] == before


def test_native_edit_unsupported_format_is_safe(tmp_path: Path):
    source = tmp_path / "templates" / "print" / "sample.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")

    result = run_native_edit_poc(tmp_path, source, allow_engine=False)

    assert result["status"] == "FAILED"
    assert result["source_unchanged"] is True
    assert "uygun değil" in result["message"]


def test_native_edit_worker_unavailable_does_not_touch_original(tmp_path: Path):
    source = tmp_path / "templates" / "print" / "sample.ai"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"ai source")
    before = sha256_file(source)

    result = run_native_edit_poc(tmp_path, source, edit=True, allow_engine=False)

    assert result["status"] == "ENGINE_MISSING"
    assert result["source_unchanged"] is True
    assert sha256_file(source) == before
    assert Path(result["manifest_path"]).exists()


def test_native_edit_diagnostics_structured_payload(tmp_path: Path):
    result = run_diagnostics(tmp_path, allow_launch=False)

    assert {"illustrator", "coreldraw", "preview_tools"}.issubset(result)
    assert "status" in result["illustrator"]
    assert "status" in result["coreldraw"]
    assert "tools" in result["preview_tools"]


def test_settings_save_creates_backup(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text("label_defaults:\n  label_width_mm: 50\n", encoding="utf-8")

    save_label_defaults(tmp_path, {"label_height_mm": 30})

    assert settings_path.exists()
    assert list((config_dir / "backups").glob("settings_*.yaml"))


def test_preview_image_header_size_and_file_url_payload(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path, source_file="templates/print/01_a_gold.ai")
    image_path = tmp_path / "01_a_gold_preview.png"
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + (500).to_bytes(4, "big")
        + (300).to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )

    set_label_model_preview(tmp_path, template_path, image_path)
    payload = validate_model_preview(tmp_path, template_path)

    assert read_image_size(tmp_path / payload["preview_path"]) == (500, 300, "OK")
    assert payload["preview_exists"] is True
    assert payload["image_width_px"] == 500
    assert payload["image_height_px"] == 300
    assert payload["image_status"] == "OK"
    assert str(payload["preview_url"]).startswith("file:///")
    assert "okunamadı" not in "\n".join(payload["warnings"])


def test_gallery_reports_duplicate_label_text_fields(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path)
    data = json.loads(template_path.read_text(encoding="utf-8"))
    data["fields"].append({**data["fields"][0], "x_mm": 10, "y_mm": 12, "width_mm": 30, "height_mm": 6})
    template_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    model = list_label_model_gallery(tmp_path)[0]

    assert model["duplicate_field_warnings"]
    assert "birden fazla" in model["duplicate_field_warnings"][0]


def test_duplicate_label_text_cleanup_keeps_small_in_bounds_field(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path)
    data = json.loads(template_path.read_text(encoding="utf-8"))
    data["fields"].append(
        {
            **data["fields"][0],
            "x_mm": 10,
            "y_mm": 12,
            "width_mm": 30,
            "height_mm": 6,
            "font_size": 14,
        }
    )
    template_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    result = cleanup_duplicate_label_text_fields(tmp_path, template_path)
    updated = json.loads(template_path.read_text(encoding="utf-8"))
    label_fields = [field for field in updated["fields"] if field["excel_column"] == "label_text"]

    assert result["status"] == "OK"
    assert result["backup_path"]
    assert len(result["deleted_fields"]) == 1
    assert len(label_fields) == 1
    assert label_fields[0]["width_mm"] == 30
    assert label_fields[0]["height_mm"] == 6


def test_duplicate_note_cleanup_keeps_single_note_field(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path)
    data = json.loads(template_path.read_text(encoding="utf-8"))
    note_field = {
        "field_name": "Not",
        "placeholder": "{{NOTE_TEXT}}",
        "excel_column": "note_text",
        "x_mm": 12,
        "y_mm": 22,
        "width_mm": 26,
        "height_mm": 4,
        "font_family": "Segoe UI",
        "font_size": 8,
        "color": "#111111",
        "align": "center",
        "vertical_align": "middle",
        "bold": False,
        "italic": False,
    }
    initial_note_count = len([field for field in data["fields"] if field["excel_column"] == "note_text"])
    data["fields"].append(note_field)
    data["fields"].append({**note_field, "field_name": "Not 2", "y_mm": 5, "height_mm": 18})
    template_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    result = cleanup_duplicate_note_fields(tmp_path, template_path)
    updated = json.loads(template_path.read_text(encoding="utf-8"))
    note_fields = [field for field in updated["fields"] if field["excel_column"] == "note_text"]

    assert result["status"] == "OK"
    assert result["backup_path"]
    assert len(result["deleted_fields"]) == initial_note_count + 1
    assert len(note_fields) == 1
    assert note_fields[0]["y_mm"] == 22
    assert note_fields[0]["height_mm"] == 4


def test_normalize_label_model_preview_creates_matching_ratio_png(tmp_path: Path):
    write_minimal_config(tmp_path)
    template_path = write_label_template_with_fields(tmp_path, source_file="templates/print/01_a_gold.ai")
    source = tmp_path / "wide_preview.png"

    from PySide6.QtGui import QColor, QImage

    image = QImage(800, 800, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ffeecc"))
    assert image.save(str(source), "PNG")
    set_label_model_preview(tmp_path, template_path, source)

    result = normalize_label_model_preview(tmp_path, template_path)
    updated = json.loads(template_path.read_text(encoding="utf-8"))
    payload = validate_model_preview(tmp_path, template_path)

    assert result["status"] == "OK"
    assert result["backup_path"]
    assert updated["preview_image"] == "assets/label_backgrounds/normalized/01_a_gold_preview_50x30.png"
    assert updated["background_image"] == updated["preview_image"]
    assert updated["background_enabled"] is True
    assert payload["ratio_status"] == "OK"
    assert payload["image_width_px"] == 591
    assert payload["image_height_px"] == 354


def test_default_variable_field_sizes_are_production_sized(tmp_path: Path):
    template_path = write_label_template(tmp_path, width=50, height=30)
    data = load_template_data(template_path)
    data["fields"] = []

    name = add_variable_field(data, "name")
    date_field = add_variable_field(data, "date")
    note = add_variable_field(data, "note")

    assert name["x_mm"] == 10.0
    assert name["y_mm"] == 10.0
    assert name["width_mm"] == 30.0
    assert name["height_mm"] == 6.0
    assert date_field["width_mm"] == 16.0
    assert note["y_mm"] == 22.0
    assert name["width_mm"] < 50
    assert name["height_mm"] < 30


def test_webui_field_editor_supports_free_drag_resize_and_keyboard_adjustment() -> None:
    project_root = Path(__file__).resolve().parents[1]
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")
    manual_service = (project_root / "src" / "label_designer" / "manual_label_service.py").read_text(encoding="utf-8")

    for token in [
        "function imageRectForDimensions",
        "function mmToFieldRectPx",
        "function fieldRectPxToMm",
        "dragOffsetX",
        "requestAnimationFrame",
        "fieldSnapEnabled",
        "const minFieldWidthMm = 2",
        "event.altKey ? 0.05",
        "event.ctrlKey || event.metaKey",
        "startFontSize",
        "payload.font_size",
        "updateFieldBoxFont(index)",
        "function scrollSelectedFieldIntoCanvasView",
        "scrollSelectedFieldIntoCanvasView();",
        'onpointerdown="startFieldDrag(event, ${index})"',
        'onmousedown="startFieldDrag(event, ${index})"',
        'onpointerdown="startFieldResize(event, ${index}, \'${handle}\')"',
        'onmousedown="startFieldResize(event, ${index}, \'${handle}\')"',
        "function delegatedFieldInteractionStart",
        'document.addEventListener("mousedown", delegatedFieldInteractionStart)',
        'window.addEventListener("mousemove", continueFieldInteraction)',
        'byId("fieldSnapEnabled")?.checked ?? false',
    ]:
        assert token in js

    for handle in ["nw", "n", "ne", "e", "se", "s", "sw", "w"]:
        assert f"'{handle}'" in js or f'"{handle}"' in js
        handle = f"handle-{handle}"
        assert f".resize-handle.{handle}" in css

    assert "fieldBoxRectPx" in js
    assert "resizeRectPx" in js
    assert "clampRectToImage" in js
    assert "background: rgba(37,99,235,.045)" in css
    assert ".field-box .resize-handle { display: block;" in css
    assert ".field-box.text-layer { background: transparent; color: #111827; text-align: center; overflow: visible; }" in css
    assert ".field-box.text-layer > span" in css and "pointer-events: none;" in css
    assert ".field-box.selected { z-index: 30;" in css
    assert ".field-overlay-wrap > img" in css and "pointer-events: none;" in css
    assert ".field-box.selected .resize-handle { opacity: .9; pointer-events: auto; }" in css
    assert ".field-box:hover .resize-handle" not in css
    interaction_gate = (project_root / "scripts" / "studio_canvas_interaction_gate.py").read_text(encoding="utf-8")
    for token in [
        "fit_drag",
        "corner_resize",
        "side_resize_width",
        "side_resize_height",
        'f"zoom_{zoom}_drag"',
        'f"zoom_{zoom}_corner_resize"',
        'f"{column}_drag"',
        "window.PointerEvent || MouseEvent",
        "keyboard_movement",
        "payload_geometry",
        "assert_changed",
        "KeyboardEvent('keydown'",
    ]:
        assert token in interaction_gate

    undo_redo_gate = (project_root / "scripts" / "verify_corel_undo_redo.py").read_text(encoding="utf-8")
    for token in [
        "text_change_undo_redo",
        "drag_undo_redo",
        "corner_resize_undo_redo",
        "font_color_undo_redo",
        "layer_visibility_lock_undo_redo",
        "auto_layout_undo_redo",
        "copy_duplicate_delete_undo_redo_payload",
        "payload_after_undo_redo_is_current",
    ]:
        assert token in undo_redo_gate


def test_webui_manual_label_live_text_binding_is_frontend_only() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")
    manual_service = (project_root / "src" / "label_designer" / "manual_label_service.py").read_text(encoding="utf-8")

    for token in [
        "let currentFieldValues",
        "let manualFieldValuesByModel",
        "function setupManualLiveBindings",
        "function updateManualFieldValue",
        "function updateCanvasTextLayers",
        "function syncManualValuesFromInputs",
        "function ensureBasicManualFields",
        "function missingBasicManualFields",
        "function cleanupDuplicateNoteFields",
        "function isBasicManualColumn",
        "function isCustomManualColumn",
        "function isManualRenderableColumn",
        "function duplicateSelectedField",
        "function pasteCopiedField",
        "seenManualColumns",
        "manualCustom2",
        "manualCustom3",
        "input.addEventListener(\"input\", () => updateManualFieldValue",
    ]:
        assert token in js

    for field_id in ["manualText", "manualDateText", "manualNoteText", "manualCustom1", "manualCustom2", "manualCustom3"]:
        assert f'id="{field_id}"' in html

    assert "Yazıyı Düzenle" not in html.split('<section id="label" class="page">', 1)[1].split('<section id="labelOutputs"', 1)[0]
    assert "manualModelDropdown" in html
    assert "manualModelSelectButton" in html
    assert "Etiket Boyutu" in html
    assert "manualUseDefaultSize" in html
    assert "manualWidthMm" in html and "manualHeightMm" in html
    assert "Gerçek Render Kontrolü" in html
    assert "function toggleManualModelDropdown" in js
    assert "function setManualZoom" in js
    assert "let manualSizeOverridesByModel" in js
    assert "function effectiveManualSize" in js
    assert "_label_width_mm" in js and "_label_height_mm" in js
    assert "manualSizeOverridesByModel[key]" in js
    assert "def _apply_label_size_override" in manual_service
    assert "STUDIO_OVERRIDE" in manual_service
    assert "#label .corel-studio" in css
    assert "grid-template-columns: 76px minmax(0, 1fr) minmax(340px, 390px);" in css
    assert ".manual-studio .model-picker { display: none; }" in css
    assert "#label .corel-canvas-panel .studio-canvas" in css and "min-height: 460px;" in css
    assert "#label .corel-inspector" in css and "max-height: calc(100vh - 335px);" in css
    assert "@media (max-width: 1120px)" in css
    assert "document.body.classList.add(\"studio-interacting\")" in js
    assert "document.body.classList.remove(\"studio-interacting\")" in js
    assert "if (index === selectedFieldIndex && !activeDrag)" in js
    assert ".studio-interacting .card" in css and "transition: none !important;" in css
    assert ".manual-model-dropdown-list" in css
    assert ".label-size-panel" in css

    normal_panel = html.split('<details class="advanced-manual-fields">')[0]
    assert "Özel Metin 1" not in normal_panel
    assert "Özel Metin 2" not in normal_panel
    assert "Özel Metin 3" not in normal_panel
    assert "date_text" in js and "note_text" in js
    assert "preview_manual_label_fields(template, JSON.stringify(manualPayload())" in js
    assert "render_manual_label_fields(template, JSON.stringify(manualPayload())" in js
    assert "render_manual_label_fields_to_queue(template, JSON.stringify(manualPayload())" in js
    assert "handleQueueAddedResult" in js
    assert "queueAddedModal" in html
    assert "Yazdırma sırasına eklendi" in html
    assert "Yazdırma Sırasına Git" in html
    assert "Devam Et" in html
    assert "QMessageBox.information(self, \"Manuel etiket\", message + f\"\\n{queue_result.get('message', '')}\")" not in (project_root / "src" / "desktop" / "web_main_window.py").read_text(encoding="utf-8")
    assert "@Slot(str, str, int, result=str)" in (project_root / "src" / "webui_backend" / "bridge.py").read_text(encoding="utf-8")
    assert "payload._studio_render_state = \"true\"" in js
    assert "payload._background_image" in js
    assert "payload._fields = studioVisibleFieldsForPayload(model)" in js
    assert "function studioVisibleFieldsForPayload" in js
    assert "label_text: byId(\"manualText\")?.value" in js
    assert "date_text: byId(\"manualDateText\")?.value" in js
    assert "note_text: byId(\"manualNoteText\")?.value" in js
    assert "input.live-linked" in css
    assert "if (!isManualRenderableColumn(column)) return \"\";" in js
    assert "if (useManualText && !String(text || \"\").trim()) return \"\";" in js


def test_label_studio_has_preflight_undo_alignment_and_history_ui() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")
    bridge_source = (project_root / "src" / "webui_backend" / "bridge.py").read_text(encoding="utf-8")
    controller_source = (project_root / "src" / "desktop" / "web_main_window.py").read_text(encoding="utf-8")
    safety_source = (project_root / "src" / "webui_backend" / "production_safety.py").read_text(encoding="utf-8")

    for token in [
        "manualUndoButton",
        "manualRedoButton",
        "manualPreflightStatus",
        "manualTextFitStatus",
        "Çıktı Kontrolü",
        "Hızlı Hizalama",
        "Fontu Otomatik Küçült",
        "Alanı Genişlet",
        "Satıra Böl",
        "productionHistoryList",
        "productionHistoryAnalytics",
        "bulkRowPreviewSummary",
        "bulkRowPreviewList",
        "rollLayoutPreview",
        "labelOutputTabs",
    ]:
        assert token in html

    for token in [
        "function runManualPreflight",
        "function undoManualEdit",
        "function redoManualEdit",
        "let manualFieldClipboard",
        "function copySelectedField",
        "function duplicateSelectedField",
        "function pasteCopiedField",
        "function alignSelectedField",
        "function shrinkSelectedFieldTextToFit",
        "function expandSelectedFieldToFit",
        "function splitSelectedFieldTextLine",
        "function bestTwoLineSplitForField",
        "function bestMultiLineSplitForField",
        "function splitSelectedFieldTextMultiLine",
        "function textFitResultForField",
        "function manualTextFitIssues",
        "function autoFitTextIssue",
        "function autoFitAllTextIssues",
        "function textFitPreflightHtml",
        "function updateSelectedTextFitStatus",
        "function currentSelectedTextFit",
        "function modelBackupVersionSummaryHtml",
        "function saveSelectedModelBackupNote",
        "function compareTwoSelectedBackups",
        "function updateProductionHistory",
        "function updateProductionHistoryAnalytics",
        "function productionHistoryTopValue",
        "function toggleManualGuide",
        "function setLabelOutputDateFilter",
        "function updateBulkRowPreview",
        "function bulkRowIssueHint",
        "function bulkIssueCategory",
        "function rollLayoutVisualHtml",
        "function updateRollLayoutPreview",
        "function selectLabelOutputTab",
        "function updateLabelOutputTabs",
        "canvas-guides",
        "safe-area-guide",
        "validate_manual_label_output",
        "preflight_manual_label_fields",
    ]:
        assert token in js or token in bridge_source or token in controller_source

    assert "preflight_manual_label_fields" in bridge_source
    assert "validate_manual_label_output" in bridge_source
    assert "append_production_history" in controller_source
    assert "validate_manual_output" in controller_source
    assert "tasarım/background görünmüyor" in safety_source
    assert "etiket yazıları görünmüyor" in safety_source
    assert "Bu model için tasarım görseli bağlı değil" in safety_source
    assert "preflight-panel" in css
    assert "preflight-text-fit-list" in css
    assert "preflight-text-fit-head" in css
    assert "preflight-fit-item" in css
    assert "backup-version-summary" in css
    assert "backup-version-pill" in css
    assert "backup-version-note-input" in css
    assert "alignment-panel" in css
    assert "text-fit-panel" in css
    assert ".canvas-guides" in css
    assert ".guide-line.guide-v" in css
    assert ".safe-area-guide" in css
    assert "bulk-row-summary" in css
    assert "bulk-row-card" in css
    assert "Hazır satır" in js
    assert "Hatalı satırlar düzeltilmeden toplu üretime geçmeyin." in js
    assert "Üretime hazır" in js
    assert "Excel satırını düzeltip tekrar Kontrol Et çalıştırın." in js
    assert "bulk-row-fix" in css
    assert "bulk-issue-breakdown" in css
    assert "roll-visual-card" in css
    assert "roll-preview-strip" in css
    assert "roll-row-breakdown" in css
    assert "roll-breakdown-row" in css
    assert "roll-waste-note" in css
    assert "Rulo yerleşim simülasyonu" in js
    assert "Toplam satır:" in js
    assert "Son satır:" in js
    assert "Satır kırılımı" in js
    assert "Yaklaşık şerit:" in js
    assert "Toplam uzunluk:" in js
    assert "Boş genişlik:" in js
    assert "Ortalama fire:" in js
    assert "Kullanılan alan:" in js
    assert "Yaklaşık alan firesi:" in js
    assert "Yaklaşık maliyet:" in js
    assert "Etiket başı:" in js
    assert "bulkRollCostPerMeter" in html
    assert "bulkRollCostCurrency" in html
    assert "roll-cost-controls" in css
    assert "Fire özeti" in js
    assert "Çok Satıra Böl" in js
    assert "multi_split" in js
    assert "Satır Aralığı" in js
    assert "fieldLineHeight" in js
    assert "line_height" in js
    assert "manualGuideState" in js
    assert "Merkez çizgisi" in js
    assert "Güvenli alan" in js
    assert "canvas-guide-toggle-bar" in css
    assert "history-analytics-grid" in css
    assert "history-filter-bar" in css
    assert "output-tab.active" in css
    assert "output-group-summary" in css
    assert "labelOutputGroupSummary" in html
    assert "Çıktı grupları" in js
    assert "labelOutputArchiveAdvisor" in html
    assert "Güvenli arşiv önerisi" in js
    assert "Son 7 Günü Göster" in js
    assert "archive-advisor-card" in css
    assert "productionHistorySearch" in html
    assert "productionHistoryModelFilter" in html
    assert "function filteredProductionHistory" in js
    assert "function refreshProductionHistoryFilters" in js
    assert "function clearProductionHistoryFilters" in js
    assert "queue-safe-note" in css
    assert "kutuya sığmıyor olabilir." in js
    assert "seçili alana sığıyor." in js
    assert "overflowPenalty" in js
    assert "editor-live::before" in css and "editor-live::after" in css
    assert "canvas-guide-hud" in js
    assert "Yazılar güvenli alanda kalmalı" in js
    assert ".canvas-guide-hud" in css


def test_label_models_page_is_user_friendly_catalog_view() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")

    label_models_section = html.split('<section id="labelModels" class="page">', 1)[1].split('<section id="bulkLabel"', 1)[0]

    assert "Etiket Hazırla" in label_models_section
    assert "Studio’da Düzenle" in label_models_section
    assert "Gelişmiş Teknik Detaylar" in label_models_section
    assert "Teknik Mod" in label_models_section
    assert "Sadece hazır modeller" in label_models_section
    assert "Hazır modeller önce" in label_models_section
    assert "Tüm hazırlık durumları" in label_models_section
    assert "labelModelHealthSummary" in label_models_section
    assert "modelRepairResult" in label_models_section
    assert "selectedModelFields" not in label_models_section
    assert "fieldEditorPanel" not in label_models_section
    assert "label_text" not in label_models_section
    assert "note_text" not in label_models_section
    assert "font_path" not in label_models_section
    assert "openNativeModelEditor()\">Yeni Model Ekle" not in label_models_section
    assert "bridge.create_label_model_from_source()\">Tasarım Görseli Yükle" not in label_models_section

    assert "function modelReadiness" in js
    assert "function modelHealthDetails" in js
    assert "function renderLabelModelHealthSummary" in js
    assert "function runSelectedModelHealthCheck" in js
    assert "function showModelRepairResult" in js
    assert "function clearModelRepairResult" in js
    assert "function repairSelectedMissingTextFields" in js
    assert "function repairSelectedFieldsInsideBounds" in js
    assert "teknik editör açmadan model ayarını güvenli şekilde düzeltir" in js
    assert "kaynak AI/CDR dosyalarına dokunulmaz" in js
    assert ".repair-safe-copy" in css
    assert "function jsArg" in js
    assert "Önizleme henüz hazır değil." in js
    assert "Küçük bir alan çakışması bulundu. Sistem otomatik düzeltebilir." in js
    assert "function cleanupDuplicateBasicFields" in js
    assert "cleanup_duplicate_note_fields" in js
    assert "model-card-actions" in js
    assert "model-mini-actions" in js
    assert "function labelModelPreviewHtml" in js
    assert "function handleLabelModelPreviewError" in js
    assert "preview_missing_file" in js
    assert "model-health-pill" in js
    assert "model-health-corner" in js
    assert "selected-ribbon" in js
    assert "function refreshLabelModels" in js
    assert "function uploadDesignVisualForSelectedModel" in js
    assert "function openNewLabelModelWizard" in js
    assert "function chooseNewLabelModelDesignVisual" in js
    assert "function saveNewLabelModelWizard" in js
    assert "choose_new_label_model_design_visual" in js
    assert "create_label_model_from_wizard" in js
    assert "function openAdvancedTemplateEditor" in js
    assert "Gelişmiş Şablon Düzenleyici yalnızca Teknik Mod açıkken kullanılabilir." in js
    assert "function syncSelectedLabelModelToManualState" in js
    assert "syncSelectedLabelModelToManualState();" in js
    assert 'byId("manualTemplate").value = selectedLabelModel.path;' in js
    assert "function previewSelectedModelOnly" in js
    assert 'alert("Önce galeriden bir model seçin.")' not in js
    assert 'alert("Bu modelde otomatik düzeltilecek alan çakışması görünmüyor.")' not in js
    assert 'alert(result.message || "Görsel etikete uyduruldu.")' not in js
    assert 'showLabelModelStatus("Önce bir model seçin.", "warn")' in js
    assert 'showLabelModelStatus("Bu modelde otomatik düzeltilecek alan çakışması görünmüyor.", "ok")' in js
    assert "Duplicate alan temizliği tamamlandı." in js
    assert "Eksik yazı alanları oluşturuldu." in js
    assert "Alanlar etiket içine alındı." in js
    assert "Kaynak AI/CDR dosyası değiştirilmedi." in js
    assert "modelPreviewModal" in html
    assert "newLabelModelModal" in html
    assert "wizard-progress" in html
    assert "wizard-field-preview" in html
    assert "openPendingWizardModelInStudio" in js
    assert "new-model-result-actions" in css
    assert "Model adı" in html
    assert "Tasarım Görseli Yükle" in html
    assert "Kaydet" in html
    assert "Tasarım Dosyası Seç ve Model Oluştur" not in html

    assert "grid-template-columns: repeat(auto-fill, minmax(310px, 1fr))" in css
    assert "#labelModels .model-gallery" in css
    assert "grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));" in css
    assert "#labelModels .detail-panel > .button-grid" in css
    assert "Global UI stability guard" in css
    assert ".topbar {\n  position: static !important;" in css
    assert ".model-health-summary {\n  position: static !important;" in css
    assert "#labelModels .detail-panel {\n  position: static !important;" in css
    assert "#labelModels .detail-panel > .button-grid {\n  position: static !important;" in css
    assert ".nav-btn:hover,\n.workflow-card:hover" in css
    assert ".sidebar {\n  backdrop-filter: none !important;" in css
    assert ".nav-btn {\n  transform: none !important;" in css
    assert "contain: paint;" in css
    assert "backdrop-filter: none !important;" in css
    assert "transform: none !important;" in css
    assert ".model-health-summary" in css
    assert ".kpi-icon" in css
    assert ".model-health-corner" in css
    assert ".model-health-pill" in css
    assert ".selected-model-heading" in css
    assert ".model-issue-card" in css
    assert ".model-mini-actions" in css
    assert ".model-health-panel" in css
    assert ".repair-action-grid" in css
    assert ".repair-result-panel" in css
    assert ".technical-details" in css
    assert "body:not(.label-technical-mode) #selectedModelTechnicalWrap" in css
    assert ".detail-summary-card" in css

    click_gate = (project_root / "scripts" / "label_models_real_click_gate.py").read_text(encoding="utf-8")
    premium_gate = (project_root / "scripts" / "verify_label_models_premium_flow.py").read_text(encoding="utf-8")
    for token in [
        "card_prepare_opens_studio_with_selected_model",
        "card_edit_opens_studio_with_clicked_model",
        "preview_modal_opens",
        "new_model_opens_safe_modal",
        "upload_design_visual_opens_safe_binding",
        "model_health_check_visible",
        "technical_mode_isolated",
        "newModelWizardStepCount",
        "newModelWizardFieldPreview",
        "Kart seçimi Studio model state değerini senkronlamadı",
        "Eksik görsel filtresi Studio model state değerini senkron tutmadı",
        "editTemplateCalls",
        "sourceModelCalls",
    ]:
        assert token in click_gate
    for token in [
        "premium_layout_tokens",
        "kpi_filters_apply_real_filters",
        "preview_resolver_never_leaves_blank_box",
        "model_check_result_visible",
    ]:
        assert token in premium_gate


def test_home_page_is_production_start_center() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")

    home_section = html.split('<section id="home" class="page active">', 1)[1].split('<section id="labelModels"', 1)[0]
    topbar = html.split('<header class="topbar">', 1)[1].split("</header>", 1)[0]

    assert "Hoş geldiniz, CeyizHome Lab" in home_section
    assert "Etiket, Trendyol, toplu üretim ve lazer isim kesim operasyon merkezi." in home_section
    assert "Güvenli Mod:" in home_section
    assert "Direct Print:" in home_section
    assert "Son kalite kontrol:" in home_section
    assert "Yazıcı:" in home_section

    assert "Tekli etiket hazırlayın." in home_section
    assert "Excel’den toplu etiket oluşturun." in home_section
    assert "Hazır tasarımları yönetin, yeni model ekleyin." in home_section
    assert 'onclick="openHomeStudio()"' in home_section
    assert 'onclick="showSection(\'bulkLabel\')"' in home_section
    assert 'onclick="showSection(\'labelModels\')"' in home_section

    for text in [
        "Hızlı İşlemler",
        "Son PDF’i Aç",
        "Son PNG’yi Önizle",
        "Yazdırma Sırasını Gör",
        "Yeni Model Ekle",
        "Görsel Bağla",
        "Ayarları Aç",
        "Bugünkü Üretim Özeti",
        "Model Durumu",
        "Yazdırma Güvenliği",
        "Son İşler",
        "Henüz üretim geçmişi yok.",
    ]:
        assert text in home_section

    for element_id in [
        "homeTodayPdfCount",
        "homeTodayPngCount",
        "homeQueueCount",
        "homeLastOutput",
        "homeReadyModelCount",
        "homeMissingPreviewCount",
        "homeFieldIssueCount",
        "homePassiveModelCount",
        "homeRecentJobsList",
    ]:
        assert f'id="{element_id}"' in home_section

    for technical_word in ["JSON", "X/Y", "field id", "template path", "backend", "debug", "native editor", "render payload"]:
        assert technical_word not in home_section

    assert 'title="Tema değiştir"' in topbar
    assert 'title="Yardım">?</button>' in topbar
    assert 'title="CeyizHome Lab"' in topbar
    assert "title=\"Raporlar\"></button>" not in topbar

    for function_name in [
        "function updateHomeDashboard",
        "function openHomeLastPdf",
        "function openHomeLastPng",
        "function openHomeNewModel",
        "function openHomePreviewUpload",
        "function openHomeModelHealth",
        "function openHomeModelStatus",
    ]:
        assert function_name in js

    assert "openHomeNewModel" in js and "openNewLabelModelWizard();" in js
    assert "openHomePreviewUpload" in js and "Görsel bağlamak için önce modeli seçin" in js
    assert "home-metric-btn" in home_section
    assert "recent-job-head" in js and "recent-job-meta" in js
    assert "workflow-art" in home_section and "<svg viewBox" in home_section
    assert "create_label_model_from_source" not in js
    assert "openNativeModelEditor()\">Yeni Model Ekle" not in html
    assert ".home-dashboard" in css
    assert ".quick-actions" in css


def test_home_page_uses_real_state_without_mock_outputs() -> None:
    project_root = Path(__file__).resolve().parents[1]
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    source = js.split("function updateHomeDashboard", 1)[1].split("function modelCard", 1)[0]
    assert "state.labelOutputs" in source
    assert "state.productionHistory" in source
    assert "state.printQueue" in source
    assert "state.labelModels" in source
    assert "modelReadiness(model).label" in source
    assert "modelReadiness(model).key" not in source
    assert "Bugün henüz çıktı oluşturulmadı." in source
    assert "Henüz üretim geçmişi yok." in source
    assert "mock" not in source.lower()
    assert "sample" not in source.lower()
    assert "bridge.editTemplate" not in source
    assert "create_label_model_from_source" not in source
    for unsafe in ["CorelDRAW", "Illustrator", "RDWorks", "LASER_CUT", "direct_print"]:
        assert unsafe not in source


def test_premium_ui_polish_uses_icon_navigation_and_shared_visual_rules() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")

    sidebar = html.split('<aside class="sidebar"', 1)[1].split("</aside>", 1)[0]
    for letter_icon in [
        '<span class="nav-icon">M</span>',
        '<span class="nav-icon">S</span>',
        '<span class="nav-icon">X</span>',
        '<span class="nav-icon">Q</span>',
        '<span class="nav-icon">O</span>',
        '<span class="nav-icon">A</span>',
        '<span class="nav-icon">R</span>',
        '<span class="nav-icon">N</span>',
        '<span class="nav-icon">L</span>',
        '<span class="nav-icon">F</span>',
    ]:
        assert letter_icon not in sidebar

    for label in [
        "TRENDYOL ENTEGRASYONU",
        "Kontrol Kuyruğu",
        "Ürün Eşleştirme",
        "Kanıt Eşleştirme",
        "Aktarım Geçmişi",
        "AYARLAR",
        "Trendyol API",
    ]:
        assert label in sidebar
    assert "sidebar-toggle" in sidebar
    assert "data-trendyol-sidebar-tab" in sidebar
    assert '<details class="nav-section technical-nav" hidden>' in sidebar

    for token in [
        "Premium production UI polish",
        "--panel-glass",
        "--shadow-hover",
        "--focus-ring",
        'input[type="checkbox"]',
        "accent-color: var(--blue)",
        ".filterbar {",
        "grid-template-columns: minmax(240px, 1.2fr) repeat(3, minmax(170px, .85fr))",
        "grid-template-columns: 18px minmax(0, 1fr)",
        ".technical-mode-toggle { min-height: 34px; opacity: .72;",
        ".model-card.selected::after",
        ".missing-preview-placeholder::before",
        ".field-box .resize-handle { width: 16px; height: 16px;",
        ".manual-output-actions { border-color: rgba(22,163,74,.24); background: linear-gradient(180deg, #f0fdf4, #ffffff); }",
    ]:
        assert token in css


def test_real_user_testing_standards_are_persistent_project_rules() -> None:
    project_root = Path(__file__).resolve().parents[1]
    required_docs = {
        "REAL_USER_TESTING_STANDARD.md": [
            "Gerçek Kullanıcı Test Standardı",
            "Gerçek kullanıcı aksiyonu çalışıyor mu?",
            "Kullanıcı Gözlemi Üstündür",
            "Handle görünüyor ama drag/resize çalışmıyor.",
        ],
        "HUMAN_QA_PROTOCOL.md": [
            "İnsan Gibi QA Protokolü",
            "Etiket Hazırla tıklanır.",
            "Drag gerçek `x/y` değiştirir.",
            "Queue doğru dosyayı alır.",
        ],
        "INTERACTION_TESTING_GUIDE.md": [
            "pointerdown",
            "pointermove",
            "Corner Resize Testi",
            "%150",
            "%200",
        ],
        "BUTTON_CLICK_TESTING_STANDARD.md": [
            "Buton testi sadece butonun DOM’da görünmesi değildir.",
            "selectedModel",
            "Sessiz buton başarısızdır.",
            "Teknik editör yanlış açılıyor mu?",
        ],
        "VISUAL_SCREENSHOT_QA_GUIDE.md": [
            "Visual Screenshot QA Guide",
            "Screenshot kötü görünüyorsa",
            "PDF/PNG preview canvas ile aynı mı?",
        ],
        "OUTPUT_VALIDATION_STANDARD.md": [
            "Output Validation Standard",
            "Sadece krem/bej zemin + çizgi.",
            "Queue son doğrulanmış batch PDF’i almalı.",
            "real_production_quality_gate.py",
        ],
        "TEST_COMMAND_REAL_USER_QA_PROTOCOL.md": [
            "Test Komutu Gerçek Kullanıcı QA Protokolü",
            "Kullanıcı yalnızca `test` yazdığında",
            "run_test_command_real_user_qa.py",
            "P0/P1 hata bulursa",
        ],
        "COMMAND_ALIASES.md": [
            "Komut Kısayolları",
            "## test",
            "Projeyi gerçek kullanıcı gibi test et",
            "TEST_COMMAND_REAL_USER_QA_REPORT.md",
            "test komutu tamamlandı, P0/P1 hata yok.",
        ],
    }

    for filename, tokens in required_docs.items():
        text = (project_root / filename).read_text(encoding="utf-8")
        for token in tokens:
            assert token in text

    start_here = (project_root / "START_HERE_FOR_CODEX.md").read_text(encoding="utf-8")
    priority = (project_root / "CODEX_CURRENT_PRIORITY.md").read_text(encoding="utf-8")
    for filename in required_docs:
        assert filename in start_here
    assert "Gerçek kullanıcı akışı test edilir." in start_here
    assert "P0/P1 kalırsa görev bitmiş sayılmaz." in start_here
    assert "Kalıcı Gerçek Kullanıcı Test Kilidi" in priority
    assert "scripts/run_test_command_real_user_qa.py" in priority
    assert "scripts/studio_canvas_interaction_gate.py" in priority
    assert "scripts/label_models_real_click_gate.py" in priority

    manual = (project_root / "CODEX_LEAD_DEVELOPER_MANUAL.md").read_text(encoding="utf-8")
    assert "Kısa Komutlar" in manual
    assert "COMMAND_ALIASES.md" in manual
    assert "tam gerçek kullanıcı kalite kontrol döngüsü" in manual

    runner = (project_root / "scripts" / "run_test_command_real_user_qa.py").read_text(encoding="utf-8")
    for token in [
        "TEST_COMMAND_REAL_USER_QA_REPORT.md",
        "label_models_real_click_gate.py",
        "studio_canvas_interaction_gate.py",
        "real_production_quality_gate.py",
        "final_acceptance_gate.py",
        "capture_webui_screenshots.py",
        "capture_quality_gate_screenshots.py",
        "P0/P1 hata yok.",
    ]:
        assert token in runner


def test_label_outputs_keep_customer_outputs_and_technical_reports_separate() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")

    section = html.split('<section id="labelOutputs" class="page">', 1)[1].split('<section id="printQueue"', 1)[0]
    assert "labelOutputStatus" in section
    assert "labelOutputSummary" in section
    assert "productionHistoryAnalytics" in section
    assert "labelOutputSearch" in section
    assert "labelOutputTypeFilter" in section
    assert "labelOutputStatusFilter" in section
    assert "labelOutputQueueFilter" in section
    assert "Tüm müşteri çıktıları" in section
    assert "Rulo Batch" in section
    assert "Üretim Geçmişi" in section
    assert "Seçili Çıktı Önizleme" in section
    assert "selectedOutputActions" in section
    assert "Filtreleri Temizle" in section
    assert "Teknik raporları göster" in section
    assert "Bu bölüm üretim dosyası değildir" in section

    source = js.split("function updateLabelOutputs", 1)[1].split("function updateProductionHistory", 1)[0]
    assert "Teknik raporlar varsayılan müşteri galerisine karışmaz." in source
    assert "Bu filtrelere uygun çıktı bulunamadı." in source
    assert "Sıraya PDF Eklenir" in source
    assert "PNG önizleme dosyasıdır. Yazdırma sırasına PDF eklenir." in source
    assert "function refreshLabelOutputFilters" in js
    assert "function clearLabelOutputFilters" in js
    assert "function outputPairForPath" in js
    assert "function updateSelectedOutputPanel" in js
    assert "function outputKind" in js
    assert "function outputValidationState" in js
    assert "PDF eşleşti" in source
    assert "PNG eşleşti" in source
    assert "PDF’i Aç" in js
    assert "PNG Önizle" in js
    assert "addPdfToQueue" in source
    assert "requestPdfPrint" in source
    assert "function showLabelOutputStatus" in js
    assert "function updateProductionHistoryAnalytics" in js
    assert "Top model:" in js
    assert "Toplam adet" in js
    assert "Yazdırma sırasına sadece doğrulanmış PDF dosyaları eklenir." in js
    assert ".output-summary" in css
    assert ".output-preview-panel" in css
    assert ".selected-output-actions" in css
    assert ".output-type-badge" in css
    assert ".history-analytics" in css
    assert ".output-pair-meta" in css
    assert ".output-preview-actions" in css
    assert ".output-filter-bar" in css
    assert ".technical-output-card summary" in css
    assert "verify_outputs_gallery_flow.py" in str((project_root / "scripts" / "verify_outputs_gallery_flow.py"))


def test_print_queue_uses_manual_pdf_check_language() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")

    section = html.split('<section id="printQueue" class="page">', 1)[1].split('<section id="reports"', 1)[0]
    assert "Otomatik yazdırma yoktur." in section
    assert "Yazıcı otomatik çalışmaz" in html
    assert "queueSearch" in section
    assert "queueStatusFilter" in section
    assert "queueTypeFilter" in section
    assert "queueDetailPanel" in section or "queue-detail-panel" in section
    assert "queueClearModal" in html
    assert "Yazdırmaya Hazır" in html
    assert "safePrintDetails" in html
    assert "safePrintStatus" in html
    assert "confirmClearPrintQueue" in js
    assert "refreshPrintQueueFilters" in js
    assert "toggleAllPrintQueueSelection" in js
    assert "markQueuePending" in js
    assert "PDF’i Aç" in js
    assert "Yazdır</button>" in js
    assert "PNG Önizle" in js
    assert "Sıradan Kaldır" in js
    assert "requestPdfPrint" in js
    assert "confirmSafePrintOpen" in js
    assert "PDF varsayılan görüntüleyicide açılıyor. Yazdırmayı kullanıcı onaylar." in js
    assert "Bu iş yazdırma sırasında bulunamadı. Listeyi yenileyin." in js
    assert "PDF’i Kontrol Et" not in js
    safe_print_source = js.split("function safePrint", 1)[1].split("function closeSafePrintModal", 1)[0]
    assert "alert(result.message)" not in safe_print_source
    assert ".safe-print-status" in css
    assert ".safe-print-details" in css
    assert ".print-safety-banner" in css
    assert ".queue-detail-panel" in css
    assert ".queue-job-card" in css
    assert ".queue-filter-bar" in css
    assert (project_root / "scripts" / "verify_print_queue_flow.py").exists()


def test_safe_print_action_validates_latest_pdf_without_silent_print() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    controller = (project_root / "src" / "desktop" / "web_main_window.py").read_text(encoding="utf-8")
    print_gate = (project_root / "scripts" / "print_action_real_user_gate.py").read_text(encoding="utf-8")
    full_e2e = (project_root / "scripts" / "full_real_user_e2e_smoke.py").read_text(encoding="utf-8")
    test_runner = (project_root / "scripts" / "run_test_command_real_user_qa.py").read_text(encoding="utf-8")

    assert "PDF/PNG Oluştur" in html
    assert "manualOutputActions" in html
    assert "requestManualPrint()" in js
    assert "function prepareManualOutputThenPrint" in js
    assert "prepareManualOutputThenPrint(\"missing\")" in js
    assert "prepareManualOutputThenPrint(\"stale\")" in js
    assert "silentPreflight: true" in js
    assert "skipStateRefresh: true" in js
    assert "skipOutputActions: true" in js
    assert "inline: false" in js
    assert "manualOutputSignature" in js
    assert "_manual_signature" in js
    assert "Çıktı güncel değil. Lütfen yeniden PDF/PNG oluşturun." in js
    assert "isOutputValidationPassed(lastManualOutput)" in js
    assert "Önce PDF/PNG oluşturun." in js
    assert "Çıktı güvenli değil. Lütfen kontrol edin." in js
    assert "showSafePrintConfirm" in js
    assert "bridge.open_project_file(pendingPrintCandidate.relativePath)" in js
    assert "window.print(" not in js
    assert "print()" not in js
    assert "direct_print_enabled=False" in controller
    assert "direct_print_enabled=True" not in controller
    assert "requestManualPrint();" in print_gate
    assert "stale_manual_print_auto_refreshed" in print_gate
    assert "print_click_layout_stable" in print_gate
    assert "__printLayoutBefore" in print_gate
    assert "safePrint(row.id);" in print_gate
    assert "Stale output was not refreshed before print" in print_gate
    assert "print_action_real_user_gate.py" in full_e2e
    assert "print_action_real_user_gate.py" in test_runner
    assert "production_history_real_user_gate.py" in full_e2e
    assert "production_history_real_user_gate.py" in test_runner
    assert "label_outputs_gallery_gate.py" in full_e2e
    assert "label_outputs_gallery_gate.py" in test_runner


def test_reports_page_uses_user_friendly_cards_instead_of_raw_text_only() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")

    section = html.split('<section id="reports" class="page">', 1)[1].split('<section id="settings"', 1)[0]
    assert "reportSummaryCards" in section
    assert '<div id="reportBox" class="report-box">' in section
    assert '<pre id="reportBox"' not in section
    assert "function renderReportSummaryCards" in js
    assert "function reportMetric" in js
    assert "function formatRowsAsCards" in js
    assert "Üretim Özeti" in js
    assert "Kritik hata yok." in js
    assert "Güvenlik: CorelDRAW, yazıcı, RDWorks ve lazer otomatik çalışmaz." in js
    assert "report-row-card bad" in js
    assert "report-log" in js
    assert ".report-summary-cards" in css
    assert ".report-row-card" in css
    assert ".report-safe-note" in css


def test_settings_page_exposes_safe_production_defaults_without_technical_toggles() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")

    section = html.split('<section id="settings" class="page">', 1)[1].split('<section id="nativeTools"', 1)[0]
    assert "settingsSafetyStrip" in section
    assert "labelDefaultsCards" in section
    assert "settingsSecurityList" in section
    assert "settingsRollSummary" in section
    assert "Yazıcı otomatik çalışmaz" in section
    assert "Etiket Studio’da Kullan" in section
    assert "Ayar Penceresini Aç" in section

    assert "function settingsMetric" in js
    assert "Direct Print: Kapalı" in js
    assert "Yazdırma güvenliği" in js
    assert "Yazdır butonu PDF’i kullanıcı onayına sunar; sessiz otomatik yazdırma kapalıdır." in js
    assert "Kaynak AI/CDR" in js
    assert "Etiket Studio’da yapılan ölçü değişikliği sadece o iş için geçicidir" in js
    assert ".settings-layout" in css
    assert ".settings-kpi-grid" in css
    assert ".settings-check-list" in css
    assert ".settings-roll-note" in css


def test_label_models_page_hides_mojibake_from_user_visible_ui() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    desktop = (project_root / "src" / "desktop" / "web_main_window.py").read_text(encoding="utf-8")
    queue_api = (project_root / "src" / "webui_backend" / "print_queue_api.py").read_text(encoding="utf-8")
    normalizer = (project_root / "src" / "webui_backend" / "text_normalizer.py").read_text(encoding="utf-8")

    mojibake_needles = [
        bytes(values).decode("cp1252")
        for values in (
            [0x64, 0xC3],
            [0x61, 0xC3],
            [0x64, 0x65, 0xC4],
            [0x67, 0xC3, 0xB6, 0x72, 0x73, 0x65, 0x6C],
            [0xC5, 0x9F, 0x61, 0x62, 0x6C, 0x6F, 0x6E],
            [0xC3, 0xBC, 0x72, 0x65, 0x74, 0x69, 0x6D],
            [0x59, 0x61, 0x7A, 0x64, 0xC4],
            [0x69, 0xC5, 0x9F],
        )
    ]
    for source in (html, js, desktop, queue_api, normalizer):
        for needle in mojibake_needles:
            assert needle not in source


def test_print_queue_normalizes_legacy_mojibake_display_fields(tmp_path: Path) -> None:
    queue_dir = tmp_path / "data"
    queue_dir.mkdir()

    def legacy_mojibake(text: str) -> str:
        return text.encode("utf-8").decode("cp1252")

    (queue_dir / "print_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "legacy",
                    "job_name": legacy_mojibake("Manuel Etiket Gerçek Önizleme Eksik QA"),
                    "job_type": legacy_mojibake("Müşteri"),
                    "quantity": "1",
                    "file_type": "Rulo Batch PDF",
                    "relative_path": "output/2026-05-07/manual_batch.pdf",
                    "status": legacy_mojibake("Yazdırıldı"),
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    row = list_print_queue(tmp_path)[0]

    assert row["job_name"] == "Manuel Etiket Gerçek Önizleme Eksik QA"
    assert row["job_type"] == "Müşteri"
    assert row["status"] == "Yazdırıldı"


def test_friendly_errors_use_clean_turkish_text() -> None:
    label_error = friendly_error({"order_no": "1001", "row": "7", "error": "label_text missing"})
    template_error = friendly_error({"row": "8", "error": "template not found"})

    assert label_error["title"] == "Sipariş 1001: Etiket yazısı eksik."
    assert label_error["desc"] == "Excel’de label_text kolonunu doldurun."
    assert label_error["row"] == "Satır: 7"
    assert template_error["title"] == "Etiket şablonu bulunamadı."
    assert "templates/designs klasörünü" in template_error["desc"]


def test_final_reports_are_utf8_and_do_not_contain_question_mark_mojibake() -> None:
    project_root = Path(__file__).resolve().parents[1]
    report_dir = project_root / "output" / "2026-05-07"
    report_names = [
        "FINAL_PROJECT_AUDIT_REPORT.md",
        "FINAL_BUTTON_ACTION_MATRIX.md",
        "FINAL_FIX_IMPLEMENTATION_REPORT.md",
        "FINAL_TEST_RESULTS_REPORT.md",
        "FINAL_SCREENSHOT_QA_REPORT.md",
        "FINAL_KNOWN_LIMITATIONS_AND_ROADMAP.md",
        "FINAL_HUMAN_ACCEPTANCE_CHECKLIST.md",
    ]
    broken_tokens = [
        "T?rk",
        "?niz",
        "Yazd?r",
        "??kt",
        "G?rsel",
        "?retim",
        "?al??",
        "ba?ar",
        "d??meden",
        "kullan?c?",
    ]
    expected_turkish = ["Türkçe", "Önizleme", "Yazdırma", "Çıktı", "Görsel", "Üretim", "Çalıştırıldı", "Başarı", "kullanıcı"]
    for name in report_names:
        path = report_dir / name
        assert path.exists(), f"Final rapor eksik: {name}"
        text = path.read_text(encoding="utf-8")
        for token in broken_tokens:
            assert token not in text
        assert "?" not in text
        assert any(token in text for token in expected_turkish), f"Türkçe kanıt metni yok: {name}"


def test_label_model_clone_variant_is_safe_and_exposed_to_ui(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    bridge = (project_root / "src" / "webui_backend" / "bridge.py").read_text(encoding="utf-8")
    desktop = (project_root / "src" / "desktop" / "web_main_window.py").read_text(encoding="utf-8")

    assert "cloneLabelModelModal" in html
    assert "openCloneLabelModelWizard" in js
    assert "chooseCloneLabelModelDesignVisual" in js
    assert "saveCloneLabelModelWizard" in js
    assert "clone_label_model_variant" in bridge
    assert "clone_label_model_variant" in desktop
    clone_block = js.split("function saveCloneLabelModelWizard", 1)[1].split("function openAdvancedTemplateEditor", 1)[0]
    assert "create_label_model_from_source" not in clone_block
    assert "editTemplate" not in clone_block

    design_dir = tmp_path / "templates" / "designs"
    design_dir.mkdir(parents=True)
    source = design_dir / "01_a_gold.json"
    source_payload = {
        "template_id": "01_a_gold",
        "template_name": "01 A Gold",
        "model_name": "01 A Gold",
        "model_no": "01",
        "template_no": "A",
        "label_variant": "GOLD",
        "label_width_mm": 50,
        "label_height_mm": 30,
        "preview_image": "assets/label_backgrounds/01_a_gold_preview.png",
        "background_image": "assets/label_backgrounds/01_a_gold_preview.png",
        "source_file": "templates/print/01_a_gold.cdr",
        "fields": [
            {"field_name": "İsim", "excel_column": "label_text", "x_mm": 10, "y_mm": 8, "width_mm": 30, "height_mm": 8},
            {"field_name": "Tarih", "excel_column": "date_text", "x_mm": 16, "y_mm": 17, "width_mm": 18, "height_mm": 4},
            {"field_name": "Not", "excel_column": "note_text", "x_mm": 10, "y_mm": 23, "width_mm": 30, "height_mm": 5},
        ],
        "elements": [],
        "active": True,
    }
    source.write_text(json.dumps(source_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    result = clone_label_model_variant(
        tmp_path,
        source,
        {
            "model_name": "01 A Gold Varyant",
            "model_no": "02",
            "template_no": "A",
            "label_variant": "SILVER",
            "active": True,
            "use_source_size": True,
        },
    )

    assert result["status"] == "CREATED"
    target = tmp_path / result["path"]
    assert target.exists()
    cloned = json.loads(target.read_text(encoding="utf-8"))
    assert cloned["model_name"] == "01 A Gold Varyant"
    assert cloned["model_no"] == "02"
    assert cloned["label_variant"] == "SILVER"
    assert cloned["preview_image"] == source_payload["preview_image"]
    assert cloned["source_file"] == source_payload["source_file"]
    assert cloned["fields"] == source_payload["fields"]
    assert json.loads(source.read_text(encoding="utf-8")) == source_payload

    visual = tmp_path / "variant.png"
    visual.write_bytes(b"safe variant visual")
    visual_result = clone_label_model_variant(
        tmp_path,
        source,
        {
            "model_name": "01 A Gold Farklı Görsel",
            "model_no": "03",
            "template_no": "A",
            "label_variant": "BLUE",
            "active": True,
            "use_source_size": True,
            "design_visual_path": str(visual),
        },
    )
    visual_target = tmp_path / visual_result["path"]
    visual_cloned = json.loads(visual_target.read_text(encoding="utf-8"))
    assert visual_cloned["preview_image"].endswith("03_a_blue_preview.png")
    assert (tmp_path / visual_cloned["preview_image"]).exists()
    assert visual_cloned["background_image"] == visual_cloned["preview_image"]


def test_safe_archive_and_bulk_column_mapping_features(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    html = (repo_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (repo_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    bridge = (repo_root / "src" / "webui_backend" / "bridge.py").read_text(encoding="utf-8")
    desktop = (repo_root / "src" / "desktop" / "web_main_window.py").read_text(encoding="utf-8")
    css = (repo_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")
    settings_api_source = (repo_root / "src" / "webui_backend" / "settings_api.py").read_text(encoding="utf-8")
    screenshot_script = (repo_root / "scripts" / "capture_webui_screenshots.py").read_text(encoding="utf-8")
    full_e2e_script = (repo_root / "scripts" / "full_real_user_e2e_smoke.py").read_text(encoding="utf-8")

    assert "bulkColumnMappingPanel" in html
    assert "Release Dashboard" in html
    assert "manualUndoHistoryView" in html
    assert "archiveLabelOutput" in js
    assert "restoreLabelOutput" in js
    assert "updateBulkColumnMapping" in js
    assert "renderManualUndoHistory" in js
    assert "labelOutputArchiveList" in html
    assert "labelOutputArchiveHistory" in desktop
    assert "labelOutputArchiveHistory" in js
    assert "productionHistoryFromDate" in html
    assert "productionHistoryToDate" in html
    assert "productionHistoryDateKey" in js
    assert "archiveSelectedLabelOutputs" in js
    assert "toggleOutputArchiveSelection" in js
    assert "bulkCancelJobButton" in html
    assert "cancel_running_job" in bridge
    assert "def cancel_running_job" in desktop
    assert "cancelRunningBulkJob" in js
    assert "studioShortcutHelp" in html
    assert "toggleStudioShortcutHelp" in js
    assert "undo-timeline" in js
    assert "label_models_real_click_gate.py" in full_e2e_script
    assert "production_history_real_user_gate.py" in full_e2e_script
    assert "label_outputs_gallery_gate.py" in full_e2e_script
    assert "settings_security_gate.py" in full_e2e_script
    assert "help_onboarding_gate.py" in full_e2e_script
    assert "studio_canvas_interaction_gate.py" in full_e2e_script
    assert "archive_label_outputs" in bridge
    assert "restore_label_outputs" in bridge
    assert "archivedLabelOutputs" in desktop
    assert "qualityGateEvidence" in desktop
    assert "REAL_PRODUCTION_QUALITY_GATE_RESULT.json" in desktop
    assert "Kalite kapısı" in js
    assert "queue_relative_path" in js
    assert "bulk_column_mapping" in desktop
    assert "labelArchiveFilterState" in js
    assert "setArchiveModelFilter" in js
    assert "clearArchiveFilters" in js
    assert "release-evidence-grid" in js
    assert "latestValidationForModel" in js
    assert "Aynı Bilgilerle Studio’da Aç" in js
    assert "text-fit-decision" in js
    assert "settingsBackups" in desktop
    assert "def list_settings_backups" in settings_api_source
    assert "save_label_defaults_json" in bridge
    assert "settings-center-layout" in html
    assert "settingsWidthMm" in html
    assert "settingsRollWidthMm" in html
    assert "settingsOutputFolders" in html
    assert "settings_security_gate" in (repo_root / "scripts" / "run_test_command_real_user_qa.py").read_text(encoding="utf-8")
    assert "helpCenterModal" in html
    assert "openHelpCenter" in js
    assert "helpTourSteps" in js
    assert "Görsel eksik" in html
    assert "Ctrl + Z" in html
    assert "help_onboarding_gate" in (repo_root / "scripts" / "run_test_command_real_user_qa.py").read_text(encoding="utf-8")
    assert "release_dashboard.png" in screenshot_script
    assert ".archive-filter-bar" in css
    assert ".column-wizard" in css
    assert ".release-evidence-grid" in css
    assert ".settings-backup-log" in css
    assert ".settings-center-layout" in css
    assert ".settings-form-grid" in css
    assert ".help-center-modal" in css
    assert ".shortcut-grid" in css
    assert ".model-health-validation" in css
    assert ".text-fit-decision" in css
    assert "object-fit: contain !important;" in css
    assert ".archive-history-card" in css
    assert ".history-day-bar" in css
    assert ".undo-timeline" in css
    assert ".studio-shortcut-help" in css

    project_root = tmp_path
    today = project_root / "output" / "2026-05-11" / "print" / "manual"
    today.mkdir(parents=True)
    pdf = today / "safe_output.pdf"
    png = today / "safe_output.png"
    pdf.write_bytes(b"%PDF safe")
    png.write_bytes(b"PNG safe")
    result = archive_label_outputs(project_root, ["output/2026-05-11/print/manual/safe_output.pdf"])
    assert result["status"] == "OK"
    assert not pdf.exists()
    moved_to = project_root / result["moved"][0]["to"]
    assert moved_to.exists()
    assert "archive" in moved_to.parts
    assert png.exists()
    archived = list_archived_label_outputs(project_root)
    assert archived
    history = list_label_output_archive_history(project_root)
    assert history and history[0]["action"] == "archived"
    restore_result = restore_label_outputs(project_root, [result["moved"][0]["to"]])
    assert restore_result["status"] == "OK"
    restored_to = project_root / restore_result["restored"][0]["to"]
    assert restored_to.exists()
    assert "archive" not in restored_to.relative_to(project_root / "output").parts
    history = list_label_output_archive_history(project_root)
    assert history and history[0]["action"] == "restored"

    excel_path = project_root / "orders.xlsx"
    pd.DataFrame(
        [
            {
                "Sipariş No": "1",
                "Model No": "01",
                "Şablon No": "A",
                "Varyant": "GOLD",
                "İsim": "Ayşe",
                "Tarih": "12.05.2026",
                "Adet": 1,
            }
        ]
    ).to_excel(excel_path, index=False)
    mapping = column_mapping(project_root, excel_path)
    assert mapping["status"] == "OK"
    mapped = {row["mapped"] for row in mapping["columns"]}
    assert {"order_no", "model_no", "template_no", "label_variant", "label_text", "date_text", "quantity"}.issubset(mapped)
    assert mapping["missing_required"] == []


def test_label_studio_corel_like_editor_shell_is_exposed() -> None:
    project_root = Path(__file__).resolve().parents[1]
    html = (project_root / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")
    studio = html.split('<section id="label" class="page">', 1)[1].split('<section id="labelOutputs"', 1)[0]

    for token in [
        "corel-property-bar",
        "studio-combo",
        "dock-only-combo",
        "corel-left-toolbar",
        "corel-canvas-panel",
        "corel-inspector",
        "manualLayerPanel",
        "manualColorPanel",
        "manualFontPresetPanel",
        "corel-bottom-panel",
        "corel-statusbar",
        "Yazdırma Sırasına Ekle",
    ]:
        assert token in studio

    for token in [
        "function renderManualLayers",
        "function renderManualColorPanel",
        "const MANUAL_COLOR_GROUPS",
        "CeyizHome Gold",
        "function manualColorContrastResult",
        "function suggestReadableTextColor",
        "Bu renk baskıda zor okunabilir",
        "const LABEL_FONT_PRESETS",
        "function renderManualFontPresetPanel",
        "function setupStudioCombos",
        "function syncStudioCombos",
        "function toggleStudioCombo",
        "function applyManualFontFamily",
        "combo.classList.contains(\"dock-only-combo\")",
        "function recommendedFontPresetForModel",
        "function applyFontPreset",
        "letter_spacing",
        "font_preset_id",
        "function applyColorSwatch",
        "function autoArrangeManualFields",
        "function auto_layout_label",
        "function auto_fit_text_field",
        "function clamp_field_inside_label",
        "function center_field_horizontally",
        "function distribute_fields_vertically",
        "function detect_text_overflow",
        "function reduce_font_to_fit",
        "function expand_field_to_fit",
        "function normalize_label_fields",
        "function apply_safe_area",
        "function fitAllManualText",
        "function moveAllFieldsIntoSafeArea",
        "function prepareManualForProduction",
        "function openManualPdfPreview",
        "function addLastManualPdfToQueue",
        "if (field.visible === false",
        "Bu katman kilitli",
    ]:
        assert token in js

    for token in [
        "#label .corel-studio",
        ".corel-property-bar",
        ".corel-left-toolbar",
        "#label .corel-canvas-panel .preview-label.editor-live",
        ".corel-layer-row.selected",
        ".font-preset-panel",
        ".font-preset-chip",
        ".font-family-chip-grid",
        ".font-family-chip",
        ".color-swatch",
        ".corel-bottom-panel",
        "#label .resize-handle",
    ]:
        assert token in css

    assert (project_root / "docs" / "design" / "corel_like_label_studio_reference.png").exists()


def test_mouse_hover_flicker_guards_are_persistent() -> None:
    project_root = Path(__file__).resolve().parents[1]
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")

    assert "function setupSidebarLayout" in js
    assert "function toggleSidebarCollapse" in js
    assert "function closeMobileSidebar" in js
    assert "pointerenter" not in js
    assert "pointerleave" not in js
    assert "sidebar.classList.add(\"sidebar-expanded\")" not in js
    assert "sidebar.classList.remove(\"sidebar-expanded\")" not in js
    assert ".sidebar:hover .nav-btn" not in css
    assert ".sidebar:hover .nav-label" not in css
    assert ".field-box:hover .resize-handle" not in css
    assert ".field-box:not(.selected) .resize-handle" in css
    assert ".studio-interacting .sidebar" in css
    assert "Final mouse-stability override" in css
    assert ".btn:hover:not(:disabled)" in css
    assert "transform: none !important" in css
    assert "animation: none !important" in css


def test_label_studio_viewport_is_locked_against_page_scroll() -> None:
    project_root = Path(__file__).resolve().parents[1]
    js = (project_root / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    css = (project_root / "src" / "webui" / "styles.css").read_text(encoding="utf-8")

    assert 'applyLabelStudioViewportLock(id === "label")' in js
    assert 'document.body.classList.toggle("label-studio-active", enabled)' in js
    assert 'function applyLabelStudioViewportLock' in js
    assert 'main?.classList.toggle("label-studio-main-active", enabled)' in js
    assert 'main.style.overflow = "hidden"' in js
    assert 'topbar.style.display = "none"' in js
    assert "function setupLabelStudioScrollContainment" in js
    assert "function clampLabelStudioPageScroll" in js
    assert "new WheelEvent('wheel'" in (project_root / "scripts" / "verify_corel_editor_interactions.py").read_text(encoding="utf-8")
    assert "Etiket Studio viewport lock" in css
    assert "body:has(#label.page.active)" not in css
    assert ".main.label-studio-main-active" in css
    assert "body.label-studio-active .main" in css
    assert "overflow: hidden !important;" in css
    assert "body.label-studio-active #label.page.active" in css
    assert "height: calc(100vh - 20px) !important" in css
    assert "body.label-studio-active #label .corel-production-topbar" in css
    assert "body.label-studio-active #label .corel-canvas-panel .studio-canvas" in css
    assert "overscroll-behavior: contain !important" in css
    assert "body.label-studio-active .sidebar" in css
    assert "document.documentElement.classList.contains('label-studio-active')" in (project_root / "scripts" / "verify_corel_editor_interactions.py").read_text(encoding="utf-8")
    assert "document.documentElement.scrollHeight <= document.documentElement.clientHeight + 2" in (project_root / "scripts" / "verify_corel_editor_interactions.py").read_text(encoding="utf-8")
    assert "#label .corel-dock-panel.active" in css
    assert "flex-direction: column" in css
    assert "#label #corelDockLayers #manualLayerPanel" in css
    assert "#label #corelDockLayers .label-size-panel" in css


def test_final_release_package_docs_and_gate_exist() -> None:
    project_root = Path(__file__).resolve().parents[1]

    for rel_path in [
        "RELEASE_NOTES.md",
        "USER_MANUAL.md",
        "TECHNICAL_MANUAL.md",
        "INSTALLATION_CHECKLIST.md",
        "FINAL_RELEASE_CHECKLIST.md",
        "examples/sample_bulk_labels.csv",
        "scripts/final_release_package_gate.py",
    ]:
        assert (project_root / rel_path).exists(), rel_path

    release_text = (project_root / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    user_manual = (project_root / "USER_MANUAL.md").read_text(encoding="utf-8")
    checklist = (project_root / "FINAL_RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    gate = (project_root / "scripts" / "final_release_package_gate.py").read_text(encoding="utf-8")

    assert "Direct print kapalıdır" in release_text
    assert "Yazıcı otomatik çalışmaz" in user_manual
    assert "PDF/PNG canvas ile aynı çıkar" in checklist
    assert "REQUIRED_DOCS" in gate
    assert "sample_bulk_labels.csv" in gate


if __name__ == "__main__":
    unittest.main()
