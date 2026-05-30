from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication

from webui_backend import settings_api
from webui_backend import dxf_library_api
from webui_backend import dxf_library_watcher
from webui_backend import product_definitions_api


class WebBridge(QObject):
    stateChanged = Signal(str)
    logChanged = Signal(str)

    def __init__(self, controller) -> None:
        super().__init__(controller)
        self.controller = controller

    @Slot(result=str)
    def get_status(self) -> str:
        return self.controller.state_json()

    @Slot(result=str)
    def quitApplication(self) -> str:
        app = QApplication.instance()
        if app is None:
            return json.dumps({"status": "ERROR", "message": "Uygulama context'i bulunamadı."})
        app.quit()
        return json.dumps({"status": "OK", "message": "Çıkış sinyali gönderildi."})

    @Slot(result=str)
    def initialState(self) -> str:
        return self.get_status()

    # --- DXF Library (Leyla's hand-prepared reference system) -------------

    @Slot(result=str)
    def dxfLibraryList(self) -> str:
        return json.dumps(
            dxf_library_api.api_list(self.controller.project_root),
            ensure_ascii=False,
        )

    @Slot(str, result=str)
    def dxfLibrarySearch(self, query: str = "") -> str:
        return json.dumps(
            dxf_library_api.api_search(self.controller.project_root, query),
            ensure_ascii=False,
        )

    @Slot(str, result=str)
    def dxfLibraryFind(self, name: str) -> str:
        return json.dumps(
            dxf_library_api.api_find(self.controller.project_root, name),
            ensure_ascii=False,
        )

    @Slot(result=str)
    def dxfLibraryRefresh(self) -> str:
        return json.dumps(
            dxf_library_api.api_refresh(self.controller.project_root),
            ensure_ascii=False,
        )

    @Slot(str, result=str)
    def dxfLibraryResolveForOrder(self, requested_name: str) -> str:
        return json.dumps(
            dxf_library_api.api_resolve_for_order(self.controller.project_root, requested_name),
            ensure_ascii=False,
        )

    @Slot(result=str)
    def dxfLibraryStartWatcher(self) -> str:
        return json.dumps(
            dxf_library_watcher.start_watcher(self.controller.project_root),
            ensure_ascii=False,
        )

    @Slot(result=str)
    def dxfLibraryStopWatcher(self) -> str:
        return json.dumps(
            dxf_library_watcher.stop_watcher(),
            ensure_ascii=False,
        )

    @Slot(result=str)
    def dxfLibraryWatcherStatus(self) -> str:
        return json.dumps(
            {
                "status": "OK",
                "running": dxf_library_watcher.is_running(),
                "available": dxf_library_watcher.watchdog_available(),
            },
            ensure_ascii=False,
        )

    # --- Product Definitions (v2.0 Bölüm 5) -------------------------------

    @Slot(bool, result=str)
    def productDefinitionsList(self, include_archived: bool = False) -> str:
        return json.dumps(
            product_definitions_api.api_list(self.controller.project_root, include_archived=include_archived),
            ensure_ascii=False,
        )

    @Slot(str, result=str)
    def productDefinitionGet(self, sku: str) -> str:
        return json.dumps(
            product_definitions_api.api_get(self.controller.project_root, sku),
            ensure_ascii=False,
        )

    @Slot(str, result=str)
    def productDefinitionsSearch(self, query: str = "") -> str:
        return json.dumps(
            product_definitions_api.api_search(self.controller.project_root, query),
            ensure_ascii=False,
        )

    @Slot(str, result=str)
    def productDefinitionSave(self, payload_json: str) -> str:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError as exc:
            return json.dumps({"status": "ERROR", "message": f"JSON bozuk: {exc}"}, ensure_ascii=False)
        return json.dumps(
            product_definitions_api.api_save(self.controller.project_root, payload),
            ensure_ascii=False,
        )

    @Slot(str, result=str)
    def productDefinitionArchive(self, sku: str) -> str:
        return json.dumps(
            product_definitions_api.api_archive(self.controller.project_root, sku),
            ensure_ascii=False,
        )

    @Slot(str, result=str)
    def productDefinitionRestore(self, sku: str) -> str:
        return json.dumps(
            product_definitions_api.api_restore(self.controller.project_root, sku),
            ensure_ascii=False,
        )

    @Slot(str, bool, result=str)
    def productDefinitionsImportExcel(self, file_path: str, dry_run: bool = False) -> str:
        return json.dumps(
            product_definitions_api.api_import_excel(self.controller.project_root, file_path, dry_run=dry_run),
            ensure_ascii=False,
        )

    @Slot(str, result=str)
    def productDefinitionResolveSizeGroup(self, payload_json: str) -> str:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        return json.dumps(
            product_definitions_api.api_resolve_size_group(self.controller.project_root, payload),
            ensure_ascii=False,
        )

    @Slot(str, result=str)
    def productDefinitionIncrementUsage(self, sku: str) -> str:
        return json.dumps(
            product_definitions_api.api_increment_usage(self.controller.project_root, sku),
            ensure_ascii=False,
        )

    @Slot()
    def select_excel(self) -> None:
        self.controller.choose_excel()

    @Slot()
    def chooseExcel(self) -> None:
        self.select_excel()

    @Slot(str)
    def set_selected_excel(self, path: str) -> None:
        self.controller.set_selected_excel(Path(path))

    @Slot()
    def run_dry_run(self) -> None:
        self.controller.run_dry()

    @Slot()
    def runDry(self) -> None:
        self.run_dry_run()

    @Slot()
    def run_production(self) -> None:
        self.controller.run_production()

    @Slot()
    def runProduction(self) -> None:
        self.run_production()

    @Slot()
    def render_labels(self) -> None:
        self.controller.render_labels()

    @Slot()
    def renderLabels(self) -> None:
        self.render_labels()

    @Slot()
    def bulk_generate_and_add_to_queue(self) -> None:
        self.controller.bulk_generate_and_add_to_queue()

    @Slot(str, result=str)
    def bulk_generate_selected_and_add_to_queue(self, row_numbers_json: str) -> str:
        try:
            row_numbers = json.loads(row_numbers_json or "[]")
        except json.JSONDecodeError:
            row_numbers = []
        return json.dumps(self.controller.bulk_generate_selected_and_add_to_queue(row_numbers), ensure_ascii=False)

    @Slot(str, result=str)
    def bulk_generate_gallery_items_and_add_to_queue(self, items_json: str) -> str:
        try:
            items = json.loads(items_json or "[]")
        except json.JSONDecodeError:
            items = []
        return json.dumps(self.controller.bulk_generate_gallery_items_and_add_to_queue(items), ensure_ascii=False)

    @Slot(str, result=str)
    def prepare_name_cut_files(self, items_json: str) -> str:
        try:
            payload = json.loads(items_json or "[]")
        except json.JSONDecodeError:
            payload = []
        if isinstance(payload, dict):
            items = payload.get("items") or []
            config = payload.get("config") or {}
        else:
            items = payload
            config = {}
        return json.dumps(self.controller.prepare_name_cut_files(items, config), ensure_ascii=False)

    @Slot(str, result=str)
    def preview_name_cut_paths(self, payload_json: str) -> str:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            items = payload.get("items") or []
            config = payload.get("config") or {}
        else:
            items = []
            config = {}
        return json.dumps(self.controller.preview_name_cut_paths(items, config), ensure_ascii=False)

    @Slot(str, result=str)
    def build_name_cut_production_scene(self, payload_json: str) -> str:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            items = payload.get("items") or []
            config = payload.get("config") or {}
        else:
            items = []
            config = {}
        return json.dumps(self.controller.build_name_cut_production_scene(items, config), ensure_ascii=False)

    @Slot(str, result=str)
    def listCorelReferences(self, filters_json: str = "{}") -> str:
        try:
            filters = json.loads(filters_json or "{}")
        except json.JSONDecodeError:
            filters = {}
        return json.dumps(self.controller.list_corel_references(filters), ensure_ascii=False)

    @Slot(str, result=str)
    def getCorelReference(self, reference_id: str) -> str:
        return json.dumps(self.controller.get_corel_reference(reference_id), ensure_ascii=False)

    @Slot(str, str, bool, result=str)
    def updateCorelReferenceLabel(self, reference_id: str, manual_name_label: str, approve_exact: bool = False) -> str:
        return json.dumps(self.controller.update_corel_reference_label(reference_id, manual_name_label, approve_exact), ensure_ascii=False)

    @Slot(str, result=str)
    def approveCorelExactReference(self, reference_id: str) -> str:
        return json.dumps(self.controller.approve_corel_exact_reference(reference_id), ensure_ascii=False)

    @Slot(str, result=str)
    def unapproveCorelReference(self, reference_id: str) -> str:
        return json.dumps(self.controller.unapprove_corel_reference(reference_id), ensure_ascii=False)

    @Slot(str, result=str)
    def markCorelReferenceStyleOnly(self, reference_id: str) -> str:
        return json.dumps(self.controller.mark_corel_reference_style_only(reference_id), ensure_ascii=False)

    @Slot(str, result=str)
    def rejectCorelReferenceCandidate(self, reference_id: str) -> str:
        return json.dumps(self.controller.reject_corel_reference_candidate(reference_id), ensure_ascii=False)

    @Slot(str, result=str)
    def saveOperatorGeneratedCorelReference(self, payload_json: str) -> str:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        return json.dumps(self.controller.save_operator_generated_corel_reference(payload), ensure_ascii=False)

    @Slot(result=str)
    def rebuildCorelReferenceIndex(self) -> str:
        return json.dumps(self.controller.rebuild_corel_reference_index(), ensure_ascii=False)

    @Slot(str, result=str)
    def searchCorelReferences(self, query: str = "") -> str:
        return json.dumps(self.controller.search_corel_references(query), ensure_ascii=False)

    @Slot(str, result=str)
    def splitCorelReference(self, reference_id: str) -> str:
        return json.dumps(self.controller.split_corel_reference(reference_id), ensure_ascii=False)

    @Slot(str, result=str)
    def createCorelReferenceBackup(self, reason: str = "manual") -> str:
        return json.dumps(self.controller.create_corel_reference_backup(reason), ensure_ascii=False)

    @Slot(result=str)
    def listCorelReferenceBackups(self) -> str:
        return json.dumps(self.controller.list_corel_reference_backups(), ensure_ascii=False)

    @Slot(str, result=str)
    def restoreCorelReferenceBackup(self, backup_path: str = "") -> str:
        return json.dumps(self.controller.restore_corel_reference_backup(backup_path), ensure_ascii=False)

    @Slot(result=str)
    def migrateCorelReferenceLibrary(self) -> str:
        return json.dumps(self.controller.migrate_corel_reference_library(), ensure_ascii=False)

    @Slot(result=str)
    def validateCorelReferenceLibrary(self) -> str:
        return json.dumps(self.controller.validate_corel_reference_library(), ensure_ascii=False)

    @Slot(result=str)
    def corelReferenceDataSecurityStatus(self) -> str:
        return json.dumps(self.controller.corel_reference_data_security_status(), ensure_ascii=False)

    @Slot(str, result=str)
    def resolveExactReferenceByName(self, input_name: str) -> str:
        return json.dumps(self.controller.resolve_exact_reference_by_name(input_name), ensure_ascii=False)

    @Slot(str, result=str)
    def resolveNameCutPath(self, input_name: str) -> str:
        return json.dumps(self.controller.resolve_name_cut_path(input_name), ensure_ascii=False)

    @Slot(str, result=str)
    def save_name_cut_queue_items(self, payload_json: str) -> str:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        return json.dumps(self.controller.save_name_cut_queue_items(payload), ensure_ascii=False)

    @Slot(str, result=str)
    def list_name_cut_queue_items(self, filters_json: str = "{}") -> str:
        try:
            filters = json.loads(filters_json or "{}")
        except json.JSONDecodeError:
            filters = {}
        return json.dumps(self.controller.list_name_cut_queue_items(filters), ensure_ascii=False)

    @Slot(str, result=str)
    def get_name_cut_queue_item(self, item_id: str) -> str:
        return json.dumps(self.controller.get_name_cut_queue_item(item_id), ensure_ascii=False)

    @Slot(str, str, result=str)
    def update_name_cut_queue_item_status(self, item_id: str, status: str) -> str:
        return json.dumps(self.controller.update_name_cut_queue_item_status(item_id, status), ensure_ascii=False)

    @Slot(str, result=str)
    def mark_name_cut_queue_item_prepared(self, item_id: str) -> str:
        return json.dumps(self.controller.mark_name_cut_queue_item_prepared(item_id), ensure_ascii=False)

    @Slot(str, result=str)
    def check_name_cut_queue_duplicate(self, duplicate_key: str) -> str:
        return json.dumps(self.controller.check_name_cut_queue_duplicate(duplicate_key), ensure_ascii=False)

    @Slot(result=str)
    def list_name_cut_transfer_history(self) -> str:
        return json.dumps(self.controller.name_cut_transfer_history(), ensure_ascii=False)

    @Slot(result=str)
    def list_name_cut_export_history(self) -> str:
        return json.dumps(self.controller.name_cut_export_history(), ensure_ascii=False)

    @Slot(str, result=str)
    def append_production_audit_event(self, payload_json: str) -> str:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        return json.dumps(self.controller.append_production_audit_event(payload), ensure_ascii=False)

    @Slot(str, result=str)
    def list_production_audit_events(self, filters_json: str = "{}") -> str:
        try:
            filters = json.loads(filters_json or "{}")
        except json.JSONDecodeError:
            filters = {}
        return json.dumps(self.controller.production_audit_events(filters), ensure_ascii=False)

    @Slot(str, result=str)
    def get_production_audit_event(self, event_id: str) -> str:
        return json.dumps(self.controller.get_production_audit_event(event_id), ensure_ascii=False)

    @Slot(result=str)
    def list_production_audit_summary(self) -> str:
        return json.dumps(self.controller.production_audit_summary(), ensure_ascii=False)

    @Slot(result=str)
    def rebuild_production_audit_from_existing_sources(self) -> str:
        return json.dumps(self.controller.rebuild_production_audit_from_existing_sources(), ensure_ascii=False)

    @Slot(str, result=str)
    def export_production_audit_events(self, payload_json: str) -> str:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        return json.dumps(self.controller.export_production_audit_events(payload), ensure_ascii=False)

    @Slot(result=str)
    def list_live_integration_registry(self) -> str:
        return json.dumps(self.controller.live_integration_registry(), ensure_ascii=False)

    @Slot(result=str)
    def live_integration_security_settings(self) -> str:
        return json.dumps(self.controller.live_integration_security_settings(), ensure_ascii=False)

    @Slot(str, result=str)
    def save_live_integration_security_settings(self, payload_json: str = "{}") -> str:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        return json.dumps(self.controller.save_live_integration_security_settings(payload), ensure_ascii=False)

    @Slot(str, str, bool, bool, bool, result=str)
    def guard_live_integration_action(
        self,
        action_key: str,
        payload_json: str = "{}",
        admin_confirmed: bool = False,
        operator_confirmed: bool = False,
        dry_run: bool = True,
    ) -> str:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        return json.dumps(
            self.controller.guard_live_integration_action(
                action_key,
                payload,
                admin_confirmed,
                operator_confirmed,
                dry_run,
            ),
            ensure_ascii=False,
        )

    @Slot(result=str)
    def create_backup(self) -> str:
        return json.dumps(self.controller.create_backup(), ensure_ascii=False)

    @Slot(result=str)
    def list_backups(self) -> str:
        return json.dumps(self.controller.list_backups(), ensure_ascii=False)

    @Slot(str, result=str)
    def validate_backup(self, backup_path: str) -> str:
        return json.dumps(self.controller.validate_backup(backup_path), ensure_ascii=False)

    @Slot(str, bool, result=str)
    def restore_backup(self, backup_path: str, dry_run: bool = True) -> str:
        return json.dumps(self.controller.restore_backup(backup_path, dry_run), ensure_ascii=False)

    @Slot(str, result=str)
    def export_backup_manifest(self, backup_path: str = "") -> str:
        return json.dumps(self.controller.export_backup_manifest(backup_path), ensure_ascii=False)

    @Slot(str, result=str)
    def reveal_file_in_folder(self, path: str) -> str:
        return json.dumps(self.controller.reveal_file_in_folder(path), ensure_ascii=False)

    @Slot(str, result=str)
    def open_file_safe(self, path: str) -> str:
        return json.dumps(self.controller.open_file_safe(path), ensure_ascii=False)

    @Slot(str, result=str)
    def create_customer_order(self, payload: str) -> str:
        data = json.loads(payload or "{}")
        return json.dumps(self.controller.create_customer_order(data), ensure_ascii=False)

    @Slot(str, str, result=str)
    def update_customer_order_status(self, order_id: str, status: str) -> str:
        return json.dumps(self.controller.update_customer_order_status(order_id, status), ensure_ascii=False)

    @Slot(str, result=str)
    def create_customer_order_summary_pdf(self, order_id: str) -> str:
        return json.dumps(self.controller.create_customer_order_summary_pdf(order_id), ensure_ascii=False)

    @Slot(str, result=str)
    def save_trendyol_settings(self, payload: str) -> str:
        data = json.loads(payload or "{}")
        return json.dumps(self.controller.save_trendyol_settings(data), ensure_ascii=False)

    @Slot(result=str)
    def test_trendyol_connection(self) -> str:
        return json.dumps(self.controller.test_trendyol_connection(), ensure_ascii=False)

    @Slot(int, result=str)
    def sync_trendyol_recent_orders(self, days: int) -> str:
        return json.dumps(self.controller.sync_trendyol_recent_orders(days), ensure_ascii=False)

    @Slot(result=str)
    def sync_trendyol_questions(self) -> str:
        return json.dumps(self.controller.sync_trendyol_questions(), ensure_ascii=False)

    @Slot(str, result=str)
    def upsert_trendyol_mapping(self, payload: str) -> str:
        data = json.loads(payload or "{}")
        return json.dumps(self.controller.upsert_trendyol_mapping(data), ensure_ascii=False)

    @Slot(result=str)
    def export_trendyol_mappings(self) -> str:
        return json.dumps(self.controller.export_trendyol_mappings(), ensure_ascii=False)

    @Slot(result=str)
    def import_trendyol_mappings(self) -> str:
        return json.dumps(self.controller.import_trendyol_mappings(), ensure_ascii=False)

    @Slot(result=str)
    def propose_trendyol_mappings_from_catalog(self) -> str:
        return json.dumps(self.controller.propose_trendyol_mappings_from_catalog(), ensure_ascii=False)

    @Slot(str, str, result=str)
    def approve_trendyol_mapping_suggestion(self, suggestion_id: str, payload: str) -> str:
        data = json.loads(payload or "{}")
        return json.dumps(self.controller.approve_trendyol_mapping_suggestion(suggestion_id, data), ensure_ascii=False)

    @Slot(str, result=str)
    def cache_trendyol_product_image(self, image_url: str) -> str:
        return json.dumps(self.controller.cache_trendyol_product_image(image_url), ensure_ascii=False)

    @Slot(str, result=str)
    def import_trendyol_suggestion_to_customer_order(self, suggestion_id: str) -> str:
        return json.dumps(self.controller.import_trendyol_suggestion_to_customer_order(suggestion_id), ensure_ascii=False)

    @Slot(str, result=str)
    def export_trendyol_ready_to_excel(self, suggestion_ids_json: str) -> str:
        try:
            suggestion_ids = json.loads(suggestion_ids_json or "[]")
        except json.JSONDecodeError:
            suggestion_ids = []
        return json.dumps(self.controller.export_trendyol_ready_to_excel(suggestion_ids), ensure_ascii=False)

    @Slot(str, result=str)
    def import_trendyol_to_bulk_production(self, suggestion_ids_json: str) -> str:
        try:
            suggestion_ids = json.loads(suggestion_ids_json or "[]")
        except json.JSONDecodeError:
            suggestion_ids = []
        return json.dumps(self.controller.import_trendyol_to_bulk_production(suggestion_ids), ensure_ascii=False)

    @Slot(str, str, result=str)
    def save_trendyol_operator_correction(self, suggestion_id: str, payload: str) -> str:
        try:
            data = json.loads(payload or "{}")
        except json.JSONDecodeError:
            data = {}
        return json.dumps(self.controller.save_trendyol_operator_correction(suggestion_id, data), ensure_ascii=False)

    @Slot(str, result=str)
    def reanalyze_trendyol_suggestion(self, suggestion_id: str) -> str:
        return json.dumps(self.controller.reanalyze_trendyol_suggestion(suggestion_id), ensure_ascii=False)

    @Slot(result=str)
    def start_bulk_reanalyze(self) -> str:
        return json.dumps(self.controller.start_bulk_reanalyze(), ensure_ascii=False)

    @Slot(result=str)
    def get_bulk_reanalyze_progress(self) -> str:
        return json.dumps(self.controller.get_bulk_reanalyze_progress(), ensure_ascii=False)

    @Slot(str, str, result=str)
    def verify_trendyol_suggestion(self, suggestion_id: str, payload: str) -> str:
        try:
            data = json.loads(payload or "{}")
        except json.JSONDecodeError:
            data = {}
        return json.dumps(self.controller.verify_trendyol_suggestion(suggestion_id, data), ensure_ascii=False)

    @Slot(str, str, result=str)
    def apply_trendyol_question_to_suggestion(self, suggestion_id: str, question_id: str) -> str:
        return json.dumps(self.controller.apply_trendyol_question_to_suggestion(suggestion_id, question_id), ensure_ascii=False)

    @Slot(str, str, result=str)
    def ignore_trendyol_question_for_suggestion(self, suggestion_id: str, question_id: str) -> str:
        return json.dumps(self.controller.ignore_trendyol_question_for_suggestion(suggestion_id, question_id), ensure_ascii=False)

    @Slot(str, result=str)
    def prepare_selected_bulk_excel(self, row_numbers_json: str) -> str:
        try:
            row_numbers = json.loads(row_numbers_json or "[]")
        except json.JSONDecodeError:
            row_numbers = []
        return json.dumps(self.controller.prepare_selected_bulk_excel(row_numbers), ensure_ascii=False)

    @Slot(result=str)
    def render_bulk_preview_samples(self) -> str:
        return json.dumps(self.controller.render_bulk_preview_samples(), ensure_ascii=False)

    @Slot(str, result=str)
    def render_selected_bulk_preview_samples(self, row_numbers_json: str) -> str:
        try:
            row_numbers = json.loads(row_numbers_json or "[]")
        except json.JSONDecodeError:
            row_numbers = []
        return json.dumps(self.controller.render_bulk_preview_samples(row_numbers=row_numbers), ensure_ascii=False)

    @Slot(str, str, int)
    def render_manual_label(self, template_path: str, label_text: str, quantity: int) -> None:
        self.controller.render_manual_label(template_path, label_text, quantity)

    @Slot(str, str, int, result=str)
    def render_manual_label_fields(self, template_path: str, payload: str, quantity: int) -> str:
        return json.dumps(self.controller.render_manual_label_fields(template_path, json.loads(payload or "{}"), quantity), ensure_ascii=False)

    @Slot(str, str, result=str)
    def preview_manual_label_fields(self, template_path: str, payload: str) -> str:
        return json.dumps(self.controller.preview_manual_label_fields(template_path, json.loads(payload or "{}")), ensure_ascii=False)

    @Slot(str, str, int, result=str)
    def preflight_manual_label_fields(self, template_path: str, payload: str, quantity: int) -> str:
        return json.dumps(self.controller.preflight_manual_label_fields(template_path, json.loads(payload or "{}"), quantity), ensure_ascii=False)

    @Slot(str, str, result=str)
    def validate_manual_label_output(self, render_result: str, payload: str) -> str:
        return json.dumps(
            self.controller.validate_manual_label_output(json.loads(render_result or "{}"), json.loads(payload or "{}")),
            ensure_ascii=False,
        )

    @Slot(str, str, int, result=str)
    def render_manual_label_fields_to_queue(self, template_path: str, payload: str, quantity: int) -> str:
        return json.dumps(
            self.controller.render_manual_label_fields_to_queue(template_path, json.loads(payload or "{}"), quantity),
            ensure_ascii=False,
        )

    @Slot()
    def create_calibration_pdf(self) -> None:
        self.controller.create_calibration_pdf()

    @Slot(str, result=str)
    def save_label_defaults_json(self, payload: str) -> str:
        data = json.loads(payload or "{}")
        settings_api.save_label_defaults(self.controller.project_root, data)
        self.controller._emit_state()
        return json.dumps(
            {
                "status": "OK",
                "message": "Varsayılan etiket ve rulo ayarları kaydedildi. Direct print kapalı kaldı.",
                "backups": settings_api.list_settings_backups(self.controller.project_root),
                "label_defaults": settings_api.get_label_defaults(self.controller.project_root),
            },
            ensure_ascii=False,
        )

    @Slot()
    def open_output_folder(self) -> None:
        self.controller.open_output()

    @Slot()
    def openOutput(self) -> None:
        self.open_output_folder()

    @Slot()
    def open_reports_folder(self) -> None:
        self.controller.open_reports()

    @Slot()
    def openReports(self) -> None:
        self.open_reports_folder()

    @Slot()
    def open_print_folder(self) -> None:
        self.controller.open_print()

    @Slot()
    def openPrint(self) -> None:
        self.open_print_folder()

    @Slot()
    def open_print_templates_folder(self) -> None:
        self.controller.open_print_templates()

    @Slot()
    def openPrintTemplates(self) -> None:
        self.open_print_templates_folder()

    @Slot()
    def open_laser_folder(self) -> None:
        self.controller.open_laser()

    @Slot()
    def openLaser(self) -> None:
        self.open_laser_folder()

    @Slot()
    def open_input_folder(self) -> None:
        self.controller.open_input()

    @Slot()
    def openInput(self) -> None:
        self.open_input_folder()

    @Slot()
    def import_template_pack(self) -> None:
        self.controller.import_template_pack()

    @Slot()
    def importTemplatePack(self) -> None:
        self.import_template_pack()

    @Slot()
    def create_label_model_from_source(self) -> None:
        self.controller.create_label_model_from_source()

    @Slot(result=str)
    def choose_new_label_model_design_visual(self) -> str:
        return json.dumps(self.controller.choose_new_label_model_design_visual(), ensure_ascii=False)

    @Slot(str, result=str)
    def create_label_model_from_wizard(self, payload: str) -> str:
        data = json.loads(payload or "{}")
        return json.dumps(self.controller.create_label_model_from_wizard(data), ensure_ascii=False)

    @Slot(str, str, result=str)
    def clone_label_model_variant(self, template_path: str, payload: str) -> str:
        data = json.loads(payload or "{}")
        return json.dumps(self.controller.clone_label_model_variant(template_path, data), ensure_ascii=False)

    @Slot()
    def create_template(self) -> None:
        self.controller.create_template()

    @Slot()
    def createTemplate(self) -> None:
        self.create_template()

    @Slot()
    def create_demo(self) -> None:
        self.controller.create_demo()

    @Slot()
    def createDemo(self) -> None:
        self.create_demo()

    @Slot()
    def convert_legacy_excel(self) -> None:
        self.controller.convert_legacy_excel()

    @Slot()
    def convertLegacyExcel(self) -> None:
        self.convert_legacy_excel()

    @Slot(result=str)
    def load_reports(self) -> str:
        return json.dumps(self.controller.reports_payload(), ensure_ascii=False)

    @Slot(result=str)
    def list_svg_files(self) -> str:
        return json.dumps(self.controller.svg_files(), ensure_ascii=False)

    @Slot(str)
    def open_svg(self, path: str) -> None:
        self.controller.open_svg(path)

    @Slot(str)
    def open_project_file(self, relative_path: str) -> None:
        self.controller.open_project_file(relative_path)

    @Slot(result=str)
    def list_label_templates(self) -> str:
        return json.dumps(self.controller.label_templates(), ensure_ascii=False)

    @Slot(result=str)
    def list_label_model_gallery(self) -> str:
        return json.dumps(self.controller.label_model_gallery(), ensure_ascii=False)

    @Slot(str, result=str)
    def list_label_model_backups(self, template_path: str) -> str:
        return json.dumps(self.controller.label_model_backups(template_path), ensure_ascii=False)

    @Slot(str, str, result=str)
    def compare_label_model_backup(self, template_path: str, backup_relative_path: str) -> str:
        return json.dumps(self.controller.compare_label_model_backup(template_path, backup_relative_path), ensure_ascii=False)

    @Slot(str, str, str, result=str)
    def set_label_model_backup_note(self, template_path: str, backup_relative_path: str, note: str) -> str:
        return json.dumps(self.controller.set_label_model_backup_note(template_path, backup_relative_path, note), ensure_ascii=False)

    @Slot(str, str, str, result=str)
    def compare_label_model_backup_pair(self, template_path: str, first_backup_relative_path: str, second_backup_relative_path: str) -> str:
        return json.dumps(self.controller.compare_label_model_backup_pair(template_path, first_backup_relative_path, second_backup_relative_path), ensure_ascii=False)

    @Slot(str, str, result=str)
    def restore_label_model_backup(self, template_path: str, backup_relative_path: str) -> str:
        return json.dumps(self.controller.restore_label_model_backup(template_path, backup_relative_path), ensure_ascii=False)

    @Slot(str, result=str)
    def choose_label_model_preview(self, template_path: str) -> str:
        return json.dumps(self.controller.choose_label_model_preview(template_path), ensure_ascii=False)

    @Slot(str, result=str)
    def validate_label_model_preview(self, template_path: str) -> str:
        return json.dumps(self.controller.validate_label_model_preview(template_path), ensure_ascii=False)

    @Slot(str, int, str, result=str)
    def save_label_model_field(self, template_path: str, index: int, payload: str) -> str:
        return json.dumps(self.controller.save_label_model_field(template_path, index, json.loads(payload or "{}")), ensure_ascii=False)

    @Slot(str, str, result=str)
    def add_label_model_field(self, template_path: str, field_type: str) -> str:
        return json.dumps(self.controller.add_label_model_field(template_path, field_type), ensure_ascii=False)

    @Slot(str, int, result=str)
    def remove_label_model_field(self, template_path: str, index: int) -> str:
        return json.dumps(self.controller.remove_label_model_field(template_path, index), ensure_ascii=False)

    @Slot(str, result=str)
    def cleanup_duplicate_label_text_fields(self, template_path: str) -> str:
        return json.dumps(self.controller.cleanup_duplicate_label_text_fields(template_path), ensure_ascii=False)

    @Slot(str, result=str)
    def cleanup_duplicate_note_fields(self, template_path: str) -> str:
        return json.dumps(self.controller.cleanup_duplicate_note_fields(template_path), ensure_ascii=False)

    @Slot(str, result=str)
    def normalize_label_model_preview(self, template_path: str) -> str:
        return json.dumps(self.controller.normalize_label_model_preview(template_path), ensure_ascii=False)

    @Slot(result=str)
    def import_label_font(self) -> str:
        return json.dumps(self.controller.import_label_font(), ensure_ascii=False)

    @Slot(str, bool, result=str)
    def run_native_edit_poc(self, template_path: str, edit: bool) -> str:
        return json.dumps(self.controller.run_native_edit_poc(template_path, edit), ensure_ascii=False)

    @Slot(result=str)
    def native_edit_diagnostics(self) -> str:
        return json.dumps(self.controller.native_edit_diagnostics(), ensure_ascii=False)

    @Slot(result=str)
    def open_native_edit_report(self) -> str:
        return json.dumps(self.controller.open_native_edit_report(), ensure_ascii=False)

    @Slot(result=str)
    def list_print_templates(self) -> str:
        return json.dumps(self.controller.print_templates(), ensure_ascii=False)

    @Slot(str, result=str)
    def get_print_template_detail(self, relative_path: str) -> str:
        return json.dumps(self.controller.print_template_detail(relative_path), ensure_ascii=False)

    @Slot(str, str, result=str)
    def save_print_template_metadata(self, relative_path: str, payload: str) -> str:
        data = json.loads(payload or "{}")
        return json.dumps(self.controller.save_print_template_metadata(relative_path, data), ensure_ascii=False)

    @Slot(str, result=str)
    def create_linked_label_design(self, relative_path: str) -> str:
        return json.dumps(self.controller.create_linked_label_design(relative_path), ensure_ascii=False)

    @Slot(result=str)
    def list_label_outputs(self) -> str:
        return json.dumps(self.controller.label_outputs(), ensure_ascii=False)

    @Slot(result=str)
    def list_archived_label_outputs(self) -> str:
        return json.dumps(self.controller.archived_label_outputs(), ensure_ascii=False)

    @Slot(str, result=str)
    def archive_label_outputs(self, relative_paths_json: str) -> str:
        try:
            relative_paths = json.loads(relative_paths_json or "[]")
        except json.JSONDecodeError:
            relative_paths = []
        return json.dumps(self.controller.archive_label_outputs(relative_paths), ensure_ascii=False)

    @Slot(str, result=str)
    def restore_label_outputs(self, relative_paths_json: str) -> str:
        try:
            relative_paths = json.loads(relative_paths_json or "[]")
        except json.JSONDecodeError:
            relative_paths = []
        return json.dumps(self.controller.restore_label_outputs(relative_paths), ensure_ascii=False)

    @Slot(result=str)
    def cancel_running_job(self) -> str:
        return json.dumps(self.controller.cancel_running_job(), ensure_ascii=False)

    @Slot(str, result=str)
    def get_pdf_preview_payload(self, relative_path: str) -> str:
        return json.dumps(self.controller.pdf_preview_payload(relative_path), ensure_ascii=False)

    @Slot(result=str)
    def list_laser_outputs(self) -> str:
        return json.dumps(self.controller.laser_outputs(), ensure_ascii=False)

    @Slot(result=str)
    def list_print_queue(self) -> str:
        return json.dumps(self.controller.print_queue(), ensure_ascii=False)

    @Slot(result=str)
    def add_label_outputs_to_print_queue(self) -> str:
        return json.dumps(self.controller.add_label_outputs_to_print_queue(), ensure_ascii=False)

    @Slot(str, result=str)
    def add_pdf_output_to_print_queue(self, relative_path: str) -> str:
        return json.dumps(self.controller.add_pdf_output_to_print_queue(relative_path), ensure_ascii=False)

    @Slot(str, result=str)
    def remove_from_print_queue(self, item_id: str) -> str:
        return json.dumps(self.controller.remove_from_print_queue(item_id), ensure_ascii=False)

    @Slot(str, result=str)
    def mark_queue_item_printed(self, item_id: str) -> str:
        return json.dumps(self.controller.mark_queue_item_printed(item_id), ensure_ascii=False)

    @Slot(str, result=str)
    def mark_queue_item_pending(self, item_id: str) -> str:
        return json.dumps(self.controller.mark_queue_item_pending(item_id), ensure_ascii=False)

    @Slot(str, result=str)
    def mark_queue_item_delivered(self, item_id: str) -> str:
        return json.dumps(self.controller.mark_queue_item_delivered(item_id), ensure_ascii=False)

    @Slot(result=str)
    def clear_print_queue(self) -> str:
        return json.dumps(self.controller.clear_print_queue(), ensure_ascii=False)

    @Slot(str, result=str)
    def print_queue_item_safe(self, item_id: str) -> str:
        return json.dumps(self.controller.print_queue_item_safe(item_id), ensure_ascii=False)

    @Slot(str, result=str)
    def save_printer_profile(self, profile_json: str) -> str:
        try:
            profile = json.loads(profile_json or "{}")
        except json.JSONDecodeError:
            profile = {}
        return json.dumps(self.controller.save_printer_profile(profile), ensure_ascii=False)

    @Slot(str, result=str)
    def delete_printer_profile(self, profile_id: str) -> str:
        return json.dumps(self.controller.delete_printer_profile(profile_id), ensure_ascii=False)

    @Slot(str, result=str)
    def set_default_printer_profile(self, profile_id: str) -> str:
        return json.dumps(self.controller.set_default_printer_profile(profile_id), ensure_ascii=False)

    @Slot(str, result=str)
    def test_printer_profile(self, profile_id: str) -> str:
        return json.dumps(self.controller.test_printer_profile(profile_id), ensure_ascii=False)

    @Slot(str, str, result=str)
    def prepare_manual_print(self, item_id: str, profile_id: str) -> str:
        return json.dumps(self.controller.prepare_manual_print(item_id, profile_id), ensure_ascii=False)

    @Slot()
    def editTemplate(self) -> None:
        self.controller.edit_template()

    @Slot()
    def showHelp(self) -> None:
        self.controller.show_help()

    @Slot()
    def showSettings(self) -> None:
        self.controller.show_settings()

    @Slot()
    def openErrors(self) -> None:
        self.controller.open_reports()



    # --- Üretim Nabzı KPI Bridge Slot (feat/visual_reporting) ---

    @Slot(str, result=str)
    def metrics_payload(self, date_range_json: str) -> str:
        """KPI metriklerini döndürür. data/production_history.json kaynak."""
        try:
            from webui_backend import report_api
            result = report_api.metrics_payload(
                date_range_json=date_range_json,
                project_root=self.controller.project_root,
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            return json.dumps(
                {"status": "ERROR", "message": f"KPI verisi alınamadı: {exc}"},
                ensure_ascii=False,
            )
