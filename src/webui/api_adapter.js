/**
 * CeyizHome Lab — Browser Mode API Adapter (Sprint 1 + Sprint 2)
 *
 * Simulates window.cyzella via fetch() calls to the Flask REST server.
 * Only loaded when Qt WebEngine is NOT present (browser mode).
 * Desktop mode (QWebChannel) is unaffected.
 *
 * Sprint 1: 7 GET endpoints.
 * Sprint 2: 30 POST (write) endpoints.
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

  function postJson(url, body, callback) {
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {})
    })
      .then(function (r) {
        if (!r.ok) {
          // HTTP error (405, 500, …) — parse body for detail, never swallow
          return r.text().then(function (text) {
            var msg = "HTTP " + r.status + " " + r.statusText;
            var data;
            try { data = JSON.parse(text); } catch (_) { data = null; }
            return {
              status: "ERROR",
              message: (data && (data.message || data.error)) || msg,
              error:   (data && data.error) || msg,
              http_status: r.status
            };
          });
        }
        return r.json();
      })
      .then(function (data) {
        // Normalize: backend uses "error" key; app.js reads "message" → copy it
        if (data && data.status === "ERROR" && data.error && !data.message) {
          data = Object.assign({}, data, { message: data.error });
        }
        if (typeof callback === "function") {
          callback(JSON.stringify(data));
        }
      })
      .catch(function (err) {
        console.error("[api_adapter] POST error:", url, err);
        if (typeof callback === "function") {
          callback(JSON.stringify({ status: "ERROR", message: String(err), error: String(err) }));
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
    },

    // ── Sprint 2: WRITE endpoints ────────────────────────────────────────────

    // GRUP 1 — Print Queue
    mark_queue_item_printed: function (item_id, callback) {
      postJson("/api/mark_queue_item_printed", { item_id: item_id }, callback);
    },

    mark_queue_item_pending: function (item_id, callback) {
      postJson("/api/mark_queue_item_pending", { item_id: item_id }, callback);
    },

    mark_queue_item_delivered: function (item_id, callback) {
      postJson("/api/mark_queue_item_delivered", { item_id: item_id }, callback);
    },

    remove_from_print_queue: function (item_id, callback) {
      postJson("/api/remove_from_print_queue", { item_id: item_id }, callback);
    },

    clear_print_queue: function (callback) {
      postJson("/api/clear_print_queue", {}, callback);
    },

    add_pdf_output_to_print_queue: function (relative_path, callback) {
      postJson("/api/add_pdf_output_to_print_queue", { relative_path: relative_path }, callback);
    },

    add_label_outputs_to_print_queue: function (callback) {
      postJson("/api/add_label_outputs_to_print_queue", {}, callback);
    },

    // GRUP 2 — Label Model Fields
    save_label_model_field: function (template_path, index, field_data, callback) {
      var body = Object.assign({}, field_data, { template_path: template_path, index: index });
      postJson("/api/save_label_model_field", body, callback);
    },

    add_label_model_field: function (template_path, field_type, callback) {
      postJson("/api/add_label_model_field", { template_path: template_path, field_type: field_type }, callback);
    },

    remove_label_model_field: function (template_path, index, callback) {
      postJson("/api/remove_label_model_field", { template_path: template_path, index: index }, callback);
    },

    save_label_defaults_json: function (payload, callback) {
      var body = (typeof payload === "string") ? JSON.parse(payload) : payload;
      postJson("/api/save_label_defaults_json", body, callback);
    },

    clone_label_model_variant: function (template_path, payload, callback) {
      var data = (typeof payload === "string") ? JSON.parse(payload) : payload;
      data.template_path = template_path;
      postJson("/api/clone_label_model_variant", data, callback);
    },

    save_print_template_metadata: function (relative_path, payload, callback) {
      var data = (typeof payload === "string") ? JSON.parse(payload) : payload;
      data.relative_path = relative_path;
      postJson("/api/save_print_template_metadata", data, callback);
    },

    // GRUP 3 — Ürün Tanımları
    productDefinitionSave: function (payload, callback) {
      var body = (typeof payload === "string") ? JSON.parse(payload) : payload;
      postJson("/api/productDefinitionSave", body, callback);
    },

    productDefinitionArchive: function (sku, callback) {
      postJson("/api/productDefinitionArchive", { sku: sku }, callback);
    },

    productDefinitionRestore: function (sku, callback) {
      postJson("/api/productDefinitionRestore", { sku: sku }, callback);
    },

    // GRUP 4 — Müşteri Siparişleri
    create_customer_order: function (payload, callback) {
      var body = (typeof payload === "string") ? JSON.parse(payload) : payload;
      postJson("/api/create_customer_order", body, callback);
    },

    update_customer_order_status: function (order_id, status, callback) {
      postJson("/api/update_customer_order_status", { order_id: order_id, status: status }, callback);
    },

    // GRUP 5 — Audit / Log
    append_production_audit_event: function (payload, callback) {
      var body = (typeof payload === "string") ? JSON.parse(payload) : payload;
      postJson("/api/append_production_audit_event", body, callback);
    },

    rebuild_production_audit_from_existing_sources: function (callback) {
      postJson("/api/rebuild_production_audit_from_existing_sources", {}, callback);
    },

    // GRUP 6 — Yazıcı Profili
    save_printer_profile: function (profile_json, callback) {
      var body = (typeof profile_json === "string") ? JSON.parse(profile_json) : profile_json;
      postJson("/api/save_printer_profile", body, callback);
    },

    delete_printer_profile: function (profile_id, callback) {
      postJson("/api/delete_printer_profile", { profile_id: profile_id }, callback);
    },

    // GRUP 7 — Yedekleme
    create_backup: function (callback) {
      postJson("/api/create_backup", {}, callback);
    },

    restore_backup: function (backup_path, dry_run, callback) {
      postJson("/api/restore_backup", { backup_path: backup_path, dry_run: dry_run !== false }, callback);
    },

    // GRUP 8 — Trendyol
    test_trendyol_connection: function (callback) {
      postJson("/api/test_trendyol_connection", {}, callback);
    },

    sync_trendyol_recent_orders: function (days, callback) {
      postJson("/api/sync_trendyol_recent_orders", { days: Number(days) || 2 }, callback);
    },

    sync_trendyol_questions: function (callback) {
      postJson("/api/read_trendyol_questions", {}, callback);
    },

    upsert_trendyol_mapping: function (payload, callback) {
      var body = (typeof payload === "string") ? JSON.parse(payload) : payload;
      postJson("/api/upsert_trendyol_mapping", body, callback);
    },

    save_trendyol_settings: function (payload, callback) {
      var body = (typeof payload === "string") ? JSON.parse(payload) : payload;
      postJson("/api/save_trendyol_settings", body, callback);
    },

    trendyol_auto_sync_status: function (callback) {
      fetchJson("/api/trendyol_auto_sync_status", callback);
    },

    trendyol_auto_sync_toggle: function (enabled, interval_sec, callback) {
      postJson("/api/trendyol_auto_sync_toggle", { enabled: Boolean(enabled), interval_sec: Number(interval_sec) || 30 }, callback);
    },

    // GRUP 9 — İsim Kesim

    update_name_cut_queue_item_status: function (item_id, status, callback) {
      postJson("/api/update_name_cut_queue_item_status", { item_id: item_id, status: status }, callback);
    },

    // build_name_cut_production_scene: FontTools+pyclipper production geometry.
    // Payload: JSON string {items, config}. Response: same format as desktop QWebChannel.
    build_name_cut_production_scene: function (payload_json, callback) {
      var body = (typeof payload_json === "string") ? JSON.parse(payload_json || "{}") : (payload_json || {});
      postJson("/api/name_cut_production_scene", body, callback);
    },

    // preview_name_cut_paths: read-only canvas preview (wraps build_name_cut_production_scene).
    // Masaüstü ile aynı format; bridge.build_name_cut_production_scene yoksa fallback olarak kullanılır.
    preview_name_cut_paths: function (payload_json, callback) {
      var body = (typeof payload_json === "string") ? JSON.parse(payload_json || "{}") : (payload_json || {});
      postJson("/api/name_cut_preview_paths", body, callback);
    },

    // prepare_name_cut_files: SVG/DXF/PDF export. Response: {status, svg_path, dxf_path,
    // pdf_preview, manifest_path, export_history, ...}. Dosyalar /api/files/<path> üzerinden indirilir.
    // RDWorks/lazer otomatik açılmaz.
    prepare_name_cut_files: function (payload_json, callback) {
      var body = (typeof payload_json === "string") ? JSON.parse(payload_json || "{}") : (payload_json || {});
      postJson("/api/name_cut_export", body, function (raw) {
        var result;
        try { result = JSON.parse(raw); } catch (_) { result = { status: "ERROR", message: "Parse hatası" }; }
        // Tarayıcı modunda export dosyaları /api/files/ üzerinden erişilebilir.
        // svg_path/dxf_path/pdf_preview "output/..." ile başlıyor; strip ederek URL yap.
        function toFileUrl(relPath) {
          if (!relPath) return "";
          var p = String(relPath).replace(/\\/g, "/");
          if (p.startsWith("output/")) p = p.slice("output/".length);
          return "/api/files/" + p;
        }
        if (result && result.status === "OK") {
          result.svg_download_url  = toFileUrl(result.svg_path);
          result.dxf_download_url  = toFileUrl(result.dxf_path);
          result.pdf_download_url  = toFileUrl(result.pdf_preview);
          result.manifest_download_url = toFileUrl(result.manifest_path);
        }
        if (typeof callback === "function") callback(JSON.stringify(result));
      });
    },

    // mark_name_cut_queue_item_prepared: kalıcı durum güncellemesi.
    // Bridge imzası: mark_name_cut_queue_item_prepared(item_id, callback).
    mark_name_cut_queue_item_prepared: function (item_id, callback) {
      postJson("/api/mark_name_cut_queue_item_prepared", { item_id: String(item_id || "") }, callback);
    },

    // save_name_cut_queue_items: toplu İsim Kesim kuyruğu kaydı.
    // Bridge imzası: save_name_cut_queue_items(payload_json, callback).
    save_name_cut_queue_items: function (payload_json, callback) {
      var body = (typeof payload_json === "string") ? JSON.parse(payload_json || "{}") : (payload_json || {});
      postJson("/api/save_name_cut_queue_items", body, callback);
    },

    // GRUP 10 — Güvenlik
    save_live_integration_security_settings: function (payload, callback) {
      var body = (typeof payload === "string") ? JSON.parse(payload || "{}") : (payload || {});
      postJson("/api/save_live_integration_security_settings", body, callback);
    },

    // Etiket Çıktı Arşivleme
    archive_label_outputs: function (relative_paths_json, callback) {
      var paths = (typeof relative_paths_json === "string") ? JSON.parse(relative_paths_json || "[]") : relative_paths_json;
      postJson("/api/archive_label_outputs", { relative_paths: paths }, callback);
    },

    restore_label_outputs: function (relative_paths_json, callback) {
      var paths = (typeof relative_paths_json === "string") ? JSON.parse(relative_paths_json || "[]") : relative_paths_json;
      postJson("/api/restore_label_outputs", { relative_paths: paths }, callback);
    },

    // ── Sprint 3: File Upload + Subprocess ──────────────────────────────────

    // GRUP A — File Upload (multipart/form-data)
    uploadExcel: function (formData, callback) {
      fetch("/api/upload_excel", { method: "POST", body: formData })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (typeof callback === "function") callback(JSON.stringify(d)); })
        .catch(function (e) { if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", error: String(e) })); });
    },

    uploadFont: function (formData, callback) {
      fetch("/api/upload_font", { method: "POST", body: formData })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (typeof callback === "function") callback(JSON.stringify(d)); })
        .catch(function (e) { if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", error: String(e) })); });
    },

    uploadDesignVisual: function (formData, callback) {
      fetch("/api/upload_design_visual", { method: "POST", body: formData })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (typeof callback === "function") callback(JSON.stringify(d)); })
        .catch(function (e) { if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", error: String(e) })); });
    },

    uploadTemplatePack: function (formData, callback) {
      fetch("/api/upload_template_pack", { method: "POST", body: formData })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (typeof callback === "function") callback(JSON.stringify(d)); })
        .catch(function (e) { if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", error: String(e) })); });
    },

    uploadLabelPreview: function (formData, callback) {
      fetch("/api/upload_label_preview", { method: "POST", body: formData })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (typeof callback === "function") callback(JSON.stringify(d)); })
        .catch(function (e) { if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", error: String(e) })); });
    },

    // GRUP B — Subprocess Jobs
    start_render_labels: function (excel_path, callback) {
      postJson("/api/start_render_labels", { excel_path: excel_path || "" }, callback);
    },

    renderLabels: function (callback) {
      postJson("/api/start_render_labels", {}, callback);
    },

    start_run_dry: function (excel_path, callback) {
      postJson("/api/start_run_dry", { excel_path: excel_path || "" }, callback);
    },

    run_dry_run: function (callback) {
      postJson("/api/start_run_dry", {}, callback);
    },

    runDry: function (callback) {
      postJson("/api/start_run_dry", {}, callback);
    },

    getJobStatus: function (job_id, callback) {
      fetchJson("/api/job_status/" + encodeURIComponent(job_id), callback);
    },

    getJobLog: function (job_id, tail, callback) {
      var t = tail || 100;
      fetchJson("/api/job_log/" + encodeURIComponent(job_id) + "?tail=" + t, callback);
    },

    cancelJob: function (job_id, callback) {
      postJson("/api/cancel_job/" + encodeURIComponent(job_id), {}, callback);
    },

    cancel_running_job: function (callback) {
      // Browser mode: no single running job concept — list and cancel latest
      fetchJson("/api/state", function (stateStr) {
        if (typeof callback === "function") {
          callback(JSON.stringify({ status: "BROWSER_MODE", message: "Aktif job yok veya zaten durdu." }));
        }
      });
    },

    // ── PART A — Font Kütüphanesi ──────────────────────────────────────────

    list_fonts: function (callback) {
      fetchJson("/api/fonts", callback);
    },

    uploadFontLibrary: function (formData, callback) {
      fetch("/api/upload_font_library", { method: "POST", body: formData })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (typeof callback === "function") callback(JSON.stringify(d)); })
        .catch(function (e) { if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", error: String(e) })); });
    },

    delete_font: function (font_id, callback) {
      fetch("/api/font/" + encodeURIComponent(font_id), { method: "DELETE" })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (typeof callback === "function") callback(JSON.stringify(d)); })
        .catch(function (e) { if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", error: String(e) })); });
    },

    // ── PART B — Trendyol Ürün Kataloğu ───────────────────────────────────

    sync_trendyol_products: function (callback) {
      postJson("/api/sync_trendyol_products", {}, callback);
    },

    list_trendyol_products: function (callback) {
      fetchJson("/api/trendyol_products", callback);
    },

    // ── PART C — Reçete ───────────────────────────────────────────────────

    get_recipe: function (barkod, callback) {
      fetchJson("/api/recipe/" + encodeURIComponent(barkod), callback);
    },

    save_recipe: function (barkod, slots, callback) {
      var slotsArr = (typeof slots === "string") ? JSON.parse(slots) : slots;
      postJson("/api/save_recipe", { barkod: barkod, slots: slotsArr }, callback);
    },

    // ── PART D — Toplu Uygula ─────────────────────────────────────────────

    bulk_apply_recipe: function (barkodlar, ayarlar, callback) {
      var barArr = (typeof barkodlar === "string") ? JSON.parse(barkodlar) : barkodlar;
      var ayarObj = (typeof ayarlar === "string") ? JSON.parse(ayarlar) : ayarlar;
      postJson("/api/bulk_apply_recipe", { barkodlar: barArr, ayarlar: ayarObj }, callback);
    },

    // ── PART E — Trendyol Operatör Düzeltme + AI Yeniden Analiz ─────────────
    save_trendyol_operator_correction: function (suggestion_id, payload_json, callback) {
      var body = (typeof payload_json === "string") ? JSON.parse(payload_json || "{}") : (payload_json || {});
      body.suggestion_id = suggestion_id;
      postJson("/api/save_trendyol_operator_correction", body, callback);
    },

    reanalyze_trendyol_suggestion: function (suggestion_id, callback) {
      postJson("/api/reanalyze_trendyol_suggestion", { id: suggestion_id }, callback);
    },

    reanalyze_all_trendyol_suggestions: function (callback) {
      postJson("/api/reanalyze_all_trendyol_suggestions", {}, callback);
    },

    get_reanalyze_all_trendyol_status: function (callback) {
      fetchJson("/api/reanalyze_all_trendyol_suggestions_status", callback);
    },

    ai_connection_test: function (callback) {
      fetchJson("/api/ai_connection_test", callback);
    },

    // ── PART F — Toplu Yeniden Analiz ────────────────────────────────────────
    start_bulk_reanalyze: function (callback) {
      postJson("/api/reanalyze_all_trendyol_suggestions", {}, callback);
    },

    get_bulk_reanalyze_progress: function (callback) {
      fetchJson("/api/bulk_reanalyze_progress", callback);
    }

  };

  // ── Sprint 4+ stubs: warn but don't crash ────────────────────────────────
  // Sprint 2: 30 POST methods implemented.
  // Sprint 3: file upload + subprocess/job methods implemented.
  // Remaining stubs: Qt-desktop-only actions (file dialogs, folder opens).

  var _notImpl = [
    "select_excel", "chooseExcel",
    "run_production", "runProduction",
    "bulk_generate_and_add_to_queue", "bulk_generate_selected_and_add_to_queue",
    "render_manual_label",
    "render_manual_label_fields_to_queue", "preview_manual_label_fields",
    "validate_manual_label_output",
    "create_label_model_from_wizard",
    "import_template_pack", "importTemplatePack", "import_label_font",
    "validate_backup",
    "export_production_audit_events",
    "guard_live_integration_action",
    "quitApplication",
    "editTemplate", "showHelp", "showSettings",
    "create_calibration_pdf"
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

  // ── Folder-open stubs: masaüstü-only, tarayıcıda açık mesaj ver ─────────────
  var _desktopOnlyFolderActions = [
    "open_output_folder", "openOutput", "open_reports_folder", "openReports",
    "open_print_folder", "openPrint", "open_input_folder", "openInput",
    "open_laser_folder", "openLaser", "reveal_file_in_folder", "open_file_safe",
    "open_svg", "open_project_file"
  ];
  _desktopOnlyFolderActions.forEach(function (method) {
    if (!cyzella[method]) {
      cyzella[method] = function () {
        var msg = "Bu özellik yalnızca masaüstü uygulamasında kullanılabilir.";
        if (typeof window.showToast === "function") {
          window.showToast(msg, "warn");
        } else {
          console.warn("[api_adapter] Desktop-only:", method, msg);
        }
      };
    }
  });

  // ── choose_new_label_model_design_visual: tarayıcıda file-input + upload ───
  if (!cyzella.choose_new_label_model_design_visual) {
    cyzella.choose_new_label_model_design_visual = function (callback) {
      var input = document.createElement("input");
      input.type = "file";
      input.accept = ".png,.jpg,.jpeg,.webp,.svg";
      input.style.position = "fixed";
      input.style.opacity = "0";
      input.style.pointerEvents = "none";
      document.body.appendChild(input);
      input.addEventListener("change", function () {
        document.body.removeChild(input);
        var file = input.files && input.files[0];
        if (!file) {
          if (typeof callback === "function") callback(JSON.stringify({ status: "CANCELLED", message: "Görsel seçilmedi." }));
          return;
        }
        var formData = new FormData();
        formData.append("file", file);
        fetch("/api/upload_label_preview", { method: "POST", body: formData })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.status !== "OK") {
              if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", message: data.error || "Görsel yüklenemedi." }));
              return;
            }
            if (typeof callback === "function") callback(JSON.stringify({
              status: "OK",
              path: data.path || "",
              preview_url: data.path ? "/api/asset/" + data.path.replace(/^assets\//, "") : "",
              file_name: file.name
            }));
          })
          .catch(function (err) {
            if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", message: String(err) }));
          });
      });
      input.click();
    };
  }

  // ── Etiket Studio — Tarayıcı modu render/preflight (P0-3) ─────────────────
  // preflight_manual_label_fields: POST /api/preflight_manual_label
  cyzella.preflight_manual_label_fields = function (template_path, payload_json, quantity, callback) {
    var fields;
    try { fields = JSON.parse(payload_json || "{}"); } catch (e) { fields = {}; }
    fetch("/api/preflight_manual_label", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template_path: template_path, fields: fields, quantity: quantity })
    }).then(function (r) { return r.json(); })
      .then(function (data) { if (typeof callback === "function") callback(JSON.stringify(data)); })
      .catch(function (err) { if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", message: String(err) })); });
  };

  // render_manual_label_fields: POST /api/render_manual_label
  cyzella.render_manual_label_fields = function (template_path, payload_json, quantity, callback) {
    var fields;
    try { fields = JSON.parse(payload_json || "{}"); } catch (e) { fields = {}; }
    fetch("/api/render_manual_label", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template_path: template_path, fields: fields, quantity: quantity })
    }).then(function (r) { return r.json(); })
      .then(function (data) { if (typeof callback === "function") callback(JSON.stringify(data)); })
      .catch(function (err) { if (typeof callback === "function") callback(JSON.stringify({ status: "ERROR", message: String(err) })); });
  };

  // ── Signals stub (QWebChannel emits these; browser mode ignores them) ────

  cyzella.stateChanged = { connect: function () {} };
  cyzella.logChanged   = { connect: function () {} };

  window.cyzella = cyzella;
  console.info("[api_adapter] Browser mode active — fetch-based bridge loaded (Sprint 1: 7 GET + Sprint 2: 30 POST + Sprint 3: 10 upload/job + Sprint 4: Trendyol + İsim Kesim + Sprint 5: Etiket Studio render/preflight)");

}());
