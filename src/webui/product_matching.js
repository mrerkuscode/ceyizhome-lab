/**
 * Ürün Eşleştirme + Font Kütüphanesi — Part E JS
 * product_matching.js — browser + desktop (bridge) uyumlu
 */

(function () {
  "use strict";

  // ── State ────────────────────────────────────────────────────────────────

  var _pmProducts = [];          // tüm ürünler (katalog + reçete durumu)
  var _pmFilter = "eslesmedi";   // aktif filtre
  var _pmSelected = {};          // barkod → true (seçili ürünler)
  var _pmFonts = { label_fonts: [], laser_fonts: [] };
  var _pmCurrentBarkod = null;   // açık reçete editörünün barkodu
  var _pmCurrentSlots = [];      // düzenlenen slotlar

  // ── Init (sayfa açıldığında) ─────────────────────────────────────────────

  window.initProductMatching = function () {
    loadFontManifest(function () {
      loadProductList();
    });
  };

  // ── Font Kütüphanesi ─────────────────────────────────────────────────────

  function loadFontManifest(cb) {
    bridge.list_fonts(function (raw) {
      var data = _parse(raw);
      _pmFonts = data && data.label_fonts ? data : { label_fonts: [], laser_fonts: [] };
      renderFontLibraryUI();
      if (typeof cb === "function") cb();
    });
  }

  function renderFontLibraryUI() {
    renderFontList("labelFontList", _pmFonts.label_fonts || [], "label");
    renderFontList("lazerFontList", _pmFonts.laser_fonts || [], "laser");
  }

  function renderFontList(containerId, fonts, type) {
    var el = document.getElementById(containerId);
    if (!el) return;
    if (!fonts.length) {
      el.innerHTML = '<div class="settings-check"><span class="muted">Henüz font yüklenmedi.</span></div>';
      return;
    }
    el.innerHTML = fonts.map(function (f) {
      var laserTag = (type === "laser" && f.laser_safe) ? '<span class="pm-tag-laser">lazer-güvenli</span>' : "";
      var warnTag = (type === "laser" && !f.laser_safe) ? '<span style="color:var(--warn);font-size:10px;margin-left:4px;">⚠ güvenli değil</span>' : "";
      return '<div class="settings-check" style="justify-content:space-between;">'
        + '<span><b>' + _esc(f.name) + '</b>' + laserTag + warnTag + '<br><span class="muted" style="font-size:10.5px;">' + _esc(f.file || "") + ' · ' + _esc(f.uploaded_at || "") + '</span></span>'
        + '<button class="btn ghost small" onclick="deleteFontLibraryEntry(\'' + _esc(f.id) + '\')" title="Sil" style="margin-left:8px;">✕</button>'
        + '</div>';
    }).join("");
  }

  window.uploadFontLibraryFile = function (type) {
    var inputId = type === "laser" ? "lazerFontFileInput" : "labelFontFileInput";
    var fileInput = document.getElementById(inputId);
    if (!fileInput || !fileInput.files.length) return;
    var file = fileInput.files[0];
    var laserSafe = false;
    if (type === "laser") {
      var cb = document.getElementById("lazerFontSafeCheck");
      laserSafe = cb ? cb.checked : false;
    }
    var fd = new FormData();
    fd.append("file", file);
    fd.append("tip", type === "laser" ? "laser" : "label");
    fd.append("laser_safe", laserSafe ? "true" : "false");
    _setFontLibStatus("Yükleniyor…", "warn");
    bridge.uploadFontLibrary(fd, function (raw) {
      var r = _parse(raw);
      if (r && r.status === "OK") {
        _setFontLibStatus("Font yüklendi: " + (r.font && r.font.name || ""), "ok");
        fileInput.value = "";
        loadFontManifest(function () { refreshBulkFontSelects(); });
      } else {
        _setFontLibStatus("Hata: " + ((r && r.error) || "Bilinmeyen hata"), "error");
      }
    });
  };

  window.deleteFontLibraryEntry = function (fontId) {
    if (!confirm("Bu fontu kütüphaneden silmek istediğinizden emin misiniz?")) return;
    bridge.delete_font(fontId, function (raw) {
      var r = _parse(raw);
      if (r && r.status === "OK") {
        _setFontLibStatus("Font silindi.", "ok");
        loadFontManifest(function () { refreshBulkFontSelects(); });
      } else {
        _setFontLibStatus("Silinemedi: " + ((r && r.error) || "Hata"), "error");
      }
    });
  };

  function _setFontLibStatus(msg, kind) {
    var el = document.getElementById("fontLibraryStatus");
    if (!el) return;
    el.hidden = false;
    el.className = "status-line " + (kind === "ok" ? "ok" : kind === "warn" ? "warn" : "err");
    el.textContent = msg;
  }

  // ── Ürün Listesi ─────────────────────────────────────────────────────────

  function loadProductList() {
    bridge.list_trendyol_products(function (raw) {
      var data = _parse(raw);
      _pmProducts = Array.isArray(data) ? data : [];
      _pmSelected = {};
      updatePmCounts();
      renderProductMatchingList();
    });
  }

  window.syncTrendyolProducts = function () {
    var st = document.getElementById("productMatchingStatus");
    if (st) { st.hidden = false; st.className = "status-line warn"; st.textContent = "Trendyol'dan ürünler çekiliyor… (read-only)"; }
    bridge.sync_trendyol_products(function (raw) {
      var r = _parse(raw);
      if (r && r.status === "OK") {
        if (st) { st.className = "status-line ok"; st.textContent = r.message || (r.count + " ürün çekildi."); }
        loadProductList();
      } else {
        if (st) { st.className = "status-line err"; st.textContent = "Hata: " + ((r && (r.error || r.message)) || "Bağlantı başarısız"); }
      }
    });
  };

  window.filterProductMatching = function (filter) {
    _pmFilter = filter;
    document.querySelectorAll(".chip").forEach(function (c) { c.classList.remove("on"); });
    var map = { "eslesmedi": "pmChipUnmatched", "eslesti": "pmChipMatched", "all": "pmChipAll" };
    var el = document.getElementById(map[filter]);
    if (el) el.classList.add("on");
    renderProductMatchingList();
  };

  window.renderProductMatchingList = function () {
    var search = (document.getElementById("pmSearch") || {}).value || "";
    search = search.toLowerCase().trim();
    var rows = _pmProducts.filter(function (p) {
      if (_pmFilter === "eslesmedi" && p.eslesme_durumu !== "eslesmedi") return false;
      if (_pmFilter === "eslesti" && p.eslesme_durumu !== "eslesti") return false;
      if (search) {
        var hay = ((p.title || "") + " " + (p.barkod || "") + " " + (p.model_code || "")).toLowerCase();
        if (!hay.includes(search)) return false;
      }
      return true;
    });

    var container = document.getElementById("pmProductRows");
    if (!container) return;
    if (!rows.length) {
      container.innerHTML = '<div class="lrow" style="grid-template-columns:1fr;"><span class="muted" style="padding:8px 0;">'
        + (_pmProducts.length ? "Filtre sonucu boş." : "Katalog boş. Trendyol\'dan çek butonunu kullanın.") + '</span></div>';
      return;
    }
    container.innerHTML = rows.map(function (p) {
      var checked = _pmSelected[p.barkod] ? "checked" : "";
      var imgHtml = p.image_url
        ? '<img class="pm-thumb" src="' + _esc(p.image_url) + '" alt="" onerror="this.style.display=\'none\'" />'
        : '<div class="pm-thumb-placeholder">📦</div>';
      var sale = p.sale_status ? ('<span class="badge ' + (p.sale_status === "true" || p.sale_status === "Satışta" ? "b-green" : "b-amber") + '">' + _esc(String(p.sale_status)) + '</span>') : '<span class="muted">—</span>';
      var eslesme = p.eslesme_durumu === "eslesti"
        ? '<span class="badge b-green">Eşleşti ✓</span>'
        : '<span class="badge b-amber">Eşleşmedi</span>';
      var action = p.eslesme_durumu === "eslesti"
        ? '<button class="btn ghost small" onclick="openPmRecipeEditor(\'' + _esc(p.barkod) + '\')">Reçeteyi düzenle</button>'
        : '<button class="btn primary small" onclick="openPmRecipeEditor(\'' + _esc(p.barkod) + '\')">Reçete oluştur</button>';
      return '<div class="lrow">'
        + '<span><input type="checkbox" ' + checked + ' data-barkod="' + _esc(p.barkod) + '" onchange="toggleProductSelection(\'' + _esc(p.barkod) + '\',this.checked)" style="width:16px;height:16px;cursor:pointer;" /></span>'
        + '<div class="pm-prod">' + imgHtml + '<div style="min-width:0"><div class="pm-pname">' + _esc(p.title || p.barkod) + '</div><div class="pm-pmeta">Model ' + _esc(p.model_code || "—") + ' · Barkod ' + _esc(p.barkod) + '</div></div></div>'
        + '<span>' + sale + '</span>'
        + '<span>' + eslesme + '</span>'
        + '<span class="right">' + action + '</span>'
        + '</div>';
    }).join("");
  };

  function updatePmCounts() {
    var unmatched = _pmProducts.filter(function (p) { return p.eslesme_durumu === "eslesmedi"; }).length;
    var matched = _pmProducts.filter(function (p) { return p.eslesme_durumu === "eslesti"; }).length;
    var all = _pmProducts.length;
    _setText("pmCountUnmatched", unmatched);
    _setText("pmCountMatched", matched);
    _setText("pmCountAll", all);
  }

  // ── Seçim + Toplu İşlem ──────────────────────────────────────────────────

  window.toggleProductSelection = function (barkod, checked) {
    if (checked) _pmSelected[barkod] = true;
    else delete _pmSelected[barkod];
    updateBulkBar();
  };

  window.toggleSelectAllProducts = function (checked) {
    var visibleBarkodlar = [];
    document.querySelectorAll("#pmProductRows input[type=checkbox][data-barkod]").forEach(function (cb) {
      visibleBarkodlar.push(cb.dataset.barkod);
      cb.checked = checked;
    });
    if (checked) visibleBarkodlar.forEach(function (b) { _pmSelected[b] = true; });
    else _pmSelected = {};
    updateBulkBar();
  };

  window.clearProductMatchingSelection = function () {
    _pmSelected = {};
    document.querySelectorAll("#pmProductRows input[type=checkbox]").forEach(function (cb) { cb.checked = false; });
    var selAll = document.getElementById("pmSelectAll");
    if (selAll) selAll.checked = false;
    updateBulkBar();
  };

  function updateBulkBar() {
    var count = Object.keys(_pmSelected).length;
    var bar = document.getElementById("pmBulkBar");
    if (bar) bar.hidden = count === 0;
    _setText("pmBulkCount", count);
    _setText("pmBulkCountBtn", count);
    refreshBulkFontSelects();
  }

  function refreshBulkFontSelects() {
    _populateFontSelect("pmBulkEtiketFont", _pmFonts.label_fonts || [], false);
    _populateFontSelect("pmBulkLazerFont", _pmFonts.laser_fonts ? _pmFonts.laser_fonts.filter(function (f) { return f.laser_safe; }) : [], false);
  }

  window.applyBulkRecipe = function () {
    var barkodlar = Object.keys(_pmSelected);
    if (!barkodlar.length) return;
    var cikti = (document.getElementById("pmBulkCikti") || {}).value || "";
    var etiketFontId = (document.getElementById("pmBulkEtiketFont") || {}).value || "";
    var lazerFontId = (document.getElementById("pmBulkLazerFont") || {}).value || "";
    var adet = parseInt((document.getElementById("pmBulkAdet") || {}).value || "0", 10) || null;
    var ayarlar = {};
    if (cikti) ayarlar.cikti = cikti;
    if (etiketFontId) ayarlar.etiket_font_id = etiketFontId;
    if (lazerFontId) ayarlar.lazer_font_id = lazerFontId;
    if (adet && adet > 0) ayarlar.adet = adet;

    var st = document.getElementById("productMatchingStatus");
    if (st) { st.hidden = false; st.className = "status-line warn"; st.textContent = "Toplu uygulama yapılıyor…"; }

    bridge.bulk_apply_recipe(barkodlar, ayarlar, function (raw) {
      var r = _parse(raw);
      if (r && r.status === "OK") {
        if (st) { st.className = "status-line ok"; st.textContent = r.message || "Toplu uygulama tamamlandı."; }
        clearProductMatchingSelection();
        loadProductList();
      } else {
        if (st) { st.className = "status-line err"; st.textContent = "Hata: " + ((r && r.error) || "Bilinmeyen hata"); }
      }
    });
  };

  // ── Reçete Editörü ───────────────────────────────────────────────────────

  window.openPmRecipeEditor = function (barkod) {
    _pmCurrentBarkod = barkod;
    var panel = document.getElementById("pmRecipePanel");
    if (panel) panel.hidden = false;

    // Ürün bilgisini bul
    var prod = _pmProducts.find(function (p) { return p.barkod === barkod; }) || { barkod: barkod };
    _setHtml("pmRecipeTitle", _esc(prod.title || barkod));
    _setHtml("pmRecipeMeta", "Barkod " + _esc(barkod) + (prod.model_code ? " · Model " + _esc(prod.model_code) : ""));
    var img = document.getElementById("pmRecipeImg");
    if (img) { img.src = prod.image_url || ""; img.style.display = prod.image_url ? "block" : "none"; }

    // Reçeteyi yükle
    bridge.get_recipe(barkod, function (raw) {
      var r = _parse(raw);
      _pmCurrentSlots = (r && Array.isArray(r.slots) && r.slots.length) ? JSON.parse(JSON.stringify(r.slots)) : [];
      if (!_pmCurrentSlots.length) {
        _pmCurrentSlots = [_newSlot(1)];
      }
      var badge = document.getElementById("pmRecipeStatusBadge");
      if (badge) {
        if (r && r.has_recipe) {
          badge.className = "badge b-green";
          badge.textContent = "Reçete var ✓";
        } else {
          badge.className = "badge b-amber";
          badge.textContent = "Reçete eksik";
        }
      }
      renderSlots();
      renderPreview();
    });
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  window.closePmRecipePanel = function () {
    var panel = document.getElementById("pmRecipePanel");
    if (panel) panel.hidden = true;
    _pmCurrentBarkod = null;
    _pmCurrentSlots = [];
  };

  function _newSlot(idx) {
    return { id: "slot_" + idx, konum: "", cikti: "etiket", besleyen: "isim", font_id: "", adet: 1, sabit_metin: "", plaka_adedi: null };
  }

  window.addPmSlot = function () {
    _pmCurrentSlots.push(_newSlot(_pmCurrentSlots.length + 1));
    renderSlots();
    renderPreview();
  };

  window.removePmSlot = function (idx) {
    _pmCurrentSlots.splice(idx, 1);
    renderSlots();
    renderPreview();
  };

  window.updatePmSlot = function (idx, field, value) {
    if (!_pmCurrentSlots[idx]) return;
    _pmCurrentSlots[idx][field] = value;
    if (field === "cikti" || field === "font_id") renderPreview();
    if (field === "cikti") renderSlots();
    // besleyen değişince sabit_metin input'u göster/gizle
    if (field === "besleyen") renderSlots();
  };

  function renderSlots() {
    var container = document.getElementById("pmSlotList");
    if (!container) return;
    var besleyenOptions = [
      { v: "isim", l: "İsim(ler)" },
      { v: "tarih", l: "Tarih" },
      { v: "not", l: "Not" },
      { v: "sabit", l: "Sabit metin" },
      { v: "sabit+isim", l: "Sabit + İsim(ler)" },
    ];
    container.innerHTML = _pmCurrentSlots.map(function (slot, i) {
      var isLazer = slot.cikti === "lazer";
      var availableFonts = isLazer
        ? (_pmFonts.laser_fonts || []).filter(function (f) { return f.laser_safe; })
        : (_pmFonts.label_fonts || []);
      var fontOpts = '<option value="">— font seç —</option>' + availableFonts.map(function (f) {
        return '<option value="' + _esc(f.id) + '" ' + (slot.font_id === f.id ? "selected" : "") + '>' + _esc(f.name) + (isLazer && f.laser_safe ? " ✓" : "") + '</option>';
      }).join("");

      var besleOpts = besleyenOptions.map(function (o) {
        return '<option value="' + o.v + '" ' + (slot.besleyen === o.v ? "selected" : "") + '>' + o.l + '</option>';
      }).join("");

      var konumVal = _esc(slot.konum || "");
      var sabitField = (slot.besleyen === "sabit" || slot.besleyen === "sabit+isim")
        ? '<div class="pm-fixed-txt"><input style="border:none;background:transparent;width:100%;font-size:12.5px;" placeholder="Sabit metin girin…" value="' + _esc(slot.sabit_metin || "") + '" oninput="updatePmSlot(' + i + ',\'sabit_metin\',this.value)" /></div>'
        : "";

      var adetLabel = isLazer ? "Plaka adedi" : "Etiket adedi";
      var adetHint = isLazer ? "" : '<div class="pm-slot-hint">beyaz rulo</div>';
      var adetVal = isLazer ? (slot.plaka_adedi || 1) : (slot.adet || 1);
      var fontLabel = isLazer ? 'Lazer fontu <span class="pm-tag-laser">lazer-güvenli</span>' : "Etiket fontu";

      return '<div class="pm-slot" id="pmSlot_' + i + '">'
        + '<div class="pm-slot-top">'
        + '<input class="pm-slot-name" placeholder="Slot adı (örn: Kurdele baskısı)" value="' + konumVal + '" oninput="updatePmSlot(' + i + ',\'konum\',this.value)" style="border:none;background:transparent;font-weight:600;font-size:13.5px;flex:1;min-width:0;" />'
        + '<div class="pm-seg">'
        + '<span class="' + (!isLazer ? "on" : "") + '" onclick="updatePmSlot(' + i + ',\'cikti\',\'etiket\')">Etiket</span>'
        + '<span class="' + (isLazer ? "on" : "") + '" onclick="updatePmSlot(' + i + ',\'cikti\',\'lazer\')">Lazer</span>'
        + '</div>'
        + '<button class="btn ghost small" onclick="removePmSlot(' + i + ')" style="margin-left:8px;" title="Sil">✕</button>'
        + '</div>'
        + '<div class="pm-slot-grid">'
        + '<div class="pm-slot-fld"><label>Besleyen alan</label><select onchange="updatePmSlot(' + i + ',\'besleyen\',this.value)">' + besleOpts + '</select></div>'
        + '<div class="pm-slot-fld"><label>' + fontLabel + '</label><select onchange="updatePmSlot(' + i + ',\'font_id\',this.value)">' + fontOpts + '</select><div class="pm-slot-hint">kütüphaneden</div></div>'
        + '<div class="pm-slot-fld"><label>' + adetLabel + '</label><input type="number" min="1" value="' + adetVal + '" oninput="updatePmSlot(' + i + ',' + (isLazer ? '\'plaka_adedi\'' : '\'adet\'') + ',parseInt(this.value)||1)" />' + adetHint + '</div>'
        + '</div>'
        + sabitField
        + '</div>';
    }).join("");
  }

  // @font-face injeksiyonu — yüklenen fontu tarayıcıya tanıt
  function _injectFontFace(fontEntry) {
    if (!fontEntry || !fontEntry.id || !fontEntry.name) return;
    var styleId = "pmFontFace_" + fontEntry.id;
    if (document.getElementById(styleId)) return; // zaten enjekte edildi
    var url = "/api/font_file/" + encodeURIComponent(fontEntry.id);
    var fmt = (fontEntry.file || "").endsWith(".otf") ? "opentype" : "truetype";
    var style = document.createElement("style");
    style.id = styleId;
    style.textContent = "@font-face { font-family: " + JSON.stringify(fontEntry.name) + "; src: url(" + JSON.stringify(url) + ") format(" + JSON.stringify(fmt) + "); }";
    document.head.appendChild(style);
    // Yükleme hatası: FontFace API ile kontrol et (opsiyonel, modern tarayıcı)
    if (typeof FontFace !== "undefined") {
      var ff = new FontFace(fontEntry.name, "url(" + url + ")");
      ff.load().catch(function () {
        var warn = document.getElementById("pmFontLoadWarn");
        if (!warn) return;
        warn.hidden = false;
        warn.textContent = "⚠ \"" + fontEntry.name + "\" önizlemede yüklenemedi — dosya eksik veya bozuk olabilir.";
      });
    }
  }

  function renderPreview() {
    var area = document.getElementById("pmPreviewArea");
    if (!area) return;

    // Kullanılan fontları @font-face ile inject et
    var allFonts = (_pmFonts.label_fonts || []).concat(_pmFonts.laser_fonts || []);
    var warnEl = document.getElementById("pmFontLoadWarn");
    if (warnEl) warnEl.hidden = true;
    _pmCurrentSlots.forEach(function (slot) {
      if (!slot.font_id) return;
      var entry = allFonts.find(function (f) { return f.id === slot.font_id; });
      if (entry) _injectFontFace(entry);
    });

    area.innerHTML = _pmCurrentSlots.map(function (slot) {
      var isLazer = slot.cikti === "lazer";
      var fontName = "";
      var fontList = isLazer ? (_pmFonts.laser_fonts || []) : (_pmFonts.label_fonts || []);
      var fontEntry = fontList.find(function (f) { return f.id === slot.font_id; });
      if (fontEntry) fontName = fontEntry.name;
      var sampleText = slot.sabit_metin || "Pınar & Çağatay";
      var capText = (isLazer ? "Lazer" : "Etiket") + " · " + (slot.konum || "Slot") + (fontName ? " · " + fontName : "");
      if (isLazer) {
        return '<div class="pm-preview-card"><div class="pm-preview-cap">' + _esc(capText) + '</div>'
          + '<div class="pm-preview-laser" style="' + (fontName ? 'font-family:' + JSON.stringify(fontName) + ',serif;' : '') + '">' + _esc(sampleText) + '</div></div>';
      } else {
        return '<div class="pm-preview-card"><div class="pm-preview-cap">' + _esc(capText) + '</div>'
          + '<div class="pm-preview-label" style="' + (fontName ? 'font-family:' + JSON.stringify(fontName) + ',sans-serif;' : '') + '">' + _esc(sampleText) + '</div></div>';
      }
    }).join("");

    // Footer notu
    var lazerSlots = _pmCurrentSlots.filter(function (s) { return s.cikti === "lazer"; });
    var note = document.getElementById("pmRecipeFooterNote");
    if (note) {
      if (lazerSlots.length) {
        var allSafe = lazerSlots.every(function (s) {
          if (!s.font_id) return true;
          return _pmFonts.laser_fonts && _pmFonts.laser_fonts.some(function (f) { return f.id === s.font_id && f.laser_safe; });
        });
        note.textContent = allSafe
          ? "✓ Lazer-güvenli fontlar · " + _pmCurrentSlots.length + " slot"
          : "⚠ Lazer slotunda güvenli olmayan font var — kaydetmeden önce düzeltin";
        note.style.color = allSafe ? "var(--ok)" : "var(--warn)";
      } else {
        note.textContent = _pmCurrentSlots.length + " slot tanımlandı.";
        note.style.color = "var(--ok)";
      }
    }
  }

  window.savePmRecipe = function () {
    if (!_pmCurrentBarkod) return;
    if (!_pmCurrentSlots.length) {
      alert("En az 1 slot gerekli.");
      return;
    }
    var st = document.getElementById("productMatchingStatus");
    bridge.save_recipe(_pmCurrentBarkod, _pmCurrentSlots, function (raw) {
      var r = _parse(raw);
      if (r && r.status === "OK") {
        if (st) { st.hidden = false; st.className = "status-line ok"; st.textContent = r.message || "Reçete kaydedildi."; }
        var badge = document.getElementById("pmRecipeStatusBadge");
        if (badge) { badge.className = "badge b-green"; badge.textContent = "Reçete var ✓"; }
        loadProductList(); // listeyi yenile
      } else {
        if (st) { st.hidden = false; st.className = "status-line err"; st.textContent = "Hata: " + ((r && r.error) || "Kayıt başarısız"); }
        alert("Kayıt hatası: " + ((r && r.error) || "Bilinmeyen hata"));
      }
    });
  };

  // ── Font select yardımcıları ─────────────────────────────────────────────

  function _populateFontSelect(selectId, fonts, addBlank) {
    var el = document.getElementById(selectId);
    if (!el) return;
    var cur = el.value;
    el.innerHTML = '<option value="">— kütüphaneden —</option>'
      + (fonts || []).map(function (f) { return '<option value="' + _esc(f.id) + '">' + _esc(f.name) + '</option>'; }).join("");
    if (cur) el.value = cur;
  }

  // ── Util ─────────────────────────────────────────────────────────────────

  function _parse(raw) {
    if (typeof raw === "object") return raw;
    try { return JSON.parse(raw); } catch (_) { return null; }
  }

  function _esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function _setText(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function _setHtml(id, html) {
    var el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  // ── Sayfa gösterildiğinde tetikle ────────────────────────────────────────
  // app.js'teki showSection() çağrıldığında initProductMatching() çağrılır.
  // Bunun için global bir hook yazıyoruz.

  var _origShowSection = window.showSection;
  window.showSection = function (page) {
    if (typeof _origShowSection === "function") _origShowSection(page);
    if (page === "productMatching") {
      window.initProductMatching();
    }
    if (page === "settings") {
      // Font kütüphanesini settings açıldığında da yenile
      loadFontManifest(function () {});
    }
  };

})();
