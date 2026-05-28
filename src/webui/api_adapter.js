/**
 * CeyizHome Lab — Browser Mode API Adapter (Sprint 1)
 *
 * Simulates window.cyzella via fetch() calls to the Flask REST server.
 * Only loaded when Qt WebEngine is NOT present (browser mode).
 * Desktop mode (QWebChannel) is unaffected.
 *
 * Sprint 1: 7 GET endpoints implemented.
 * Sprint 2+: POST / mutation endpoints will be added here.
 */

(function () {
  "use strict";

  function fetchJson(url, callback) {
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (typeof callback === "function") {
          callback(JSON.stringify(data));
        }
      })
      .catch(function (err) {
        console.error("[api_adapter] fetch error:", url, err);
        if (typeof callback === "function") {
          callback(JSON.stringify({ status: "ERROR", error: String(err) }));
        }
      });
  }

  // ── Sprint 1: READ-ONLY endpoints ────────────────────────────────────────

  var cyzella = {

    get_status: function (callback) {
      fetchJson("/api/state", callback);
    },

    initialState: function (callback) {
      fetchJson("/api/state", callback);
    },

    metrics_payload: function (date_range_json, callback) {
      var url = "/api/metrics?range=" + encodeURIComponent(date_range_json || "{}");
      fetchJson(url, callback);
    },

    list_label_outputs: function (callback) {
      fetchJson("/api/label_outputs", callback);
    },

    list_print_queue: function (callback) {
      fetchJson("/api/print_queue", callback);
    },

    list_label_model_gallery: function (callback) {
      fetchJson("/api/label_model_gallery", callback);
    },

    load_reports: function (callback) {
      fetchJson("/api/reports", callback);
    }

  };

  // ── Sprint 2+ stubs: warn but don't crash ────────────────────────────────

  var _notImpl = [
    "select_excel", "chooseExcel", "run_dry_run", "runDry",
    "run_production", "runProduction", "render_labels", "renderLabels",
    "bulk_generate_and_add_to_queue", "bulk_generate_selected_and_add_to_queue",
    "render_manual_label", "render_manual_label_fields",
    "render_manual_label_fields_to_queue", "preview_manual_label_fields",
    "preflight_manual_label_fields", "validate_manual_label_output",
    "save_label_model_field", "add_label_model_field", "remove_label_model_field",
    "create_label_model_from_wizard", "clone_label_model_variant",
    "choose_new_label_model_design_visual", "choose_label_model_preview",
    "import_template_pack", "importTemplatePack", "import_label_font",
    "mark_queue_item_printed", "mark_queue_item_pending", "mark_queue_item_delivered",
    "remove_from_print_queue", "clear_print_queue",
    "create_backup", "restore_backup", "validate_backup",
    "save_trendyol_settings", "test_trendyol_connection", "sync_trendyol_recent_orders",
    "upsert_trendyol_mapping", "save_printer_profile", "delete_printer_profile",
    "productDefinitionSave", "productDefinitionArchive", "productDefinitionRestore",
    "append_production_audit_event", "rebuild_production_audit_from_existing_sources",
    "export_production_audit_events", "save_live_integration_security_settings",
    "guard_live_integration_action", "create_customer_order",
    "open_output_folder", "openOutput", "open_reports_folder", "openReports",
    "open_print_folder", "openPrint", "open_input_folder", "openInput",
    "open_laser_folder", "openLaser", "reveal_file_in_folder", "open_file_safe",
    "open_svg", "open_project_file", "quitApplication",
    "editTemplate", "showHelp", "showSettings",
    "save_label_defaults_json", "create_calibration_pdf", "cancel_running_job"
  ];

  _notImpl.forEach(function (method) {
    if (!cyzella[method]) {
      cyzella[method] = function () {
        console.warn("[api_adapter] Sprint 2+ method not yet implemented in browser mode:", method);
        var args = Array.prototype.slice.call(arguments);
        var callback = args[args.length - 1];
        if (typeof callback === "function") {
          callback(JSON.stringify({ status: "NOT_IMPLEMENTED", method: method, sprint: 2 }));
        }
      };
    }
  });

  // ── Signals stub (QWebChannel emits these; browser mode ignores them) ────

  cyzella.stateChanged = { connect: function () {} };
  cyzella.logChanged   = { connect: function () {} };

  window.cyzella = cyzella;
  console.info("[api_adapter] Browser mode active — fetch-based bridge loaded (Sprint 1: 7 endpoints)");

}());
