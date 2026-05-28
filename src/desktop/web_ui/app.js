let bridge = null;

function esc(value) {
  return String(value || "").replace(/[&<>"']/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[c]));
}

function applyState(raw) {
  const state = typeof raw === "string" ? JSON.parse(raw) : raw;
  document.getElementById("excelName").textContent = state.selectedExcelName || "Excel seçilmedi";
  document.getElementById("fontTitle").textContent = state.fontOk ? "LAZER FONTU HAZIR" : "LAZER FONTU EKSİK";
  document.getElementById("fontText").textContent = state.fontOk ? "Font mevcut" : "Font yüklenmedi";
  document.getElementById("fontCard").className = "status-card " + (state.fontOk ? "success" : "danger");
  document.getElementById("lastOutput").textContent = "Çıktı: " + (state.outputDir || "output/");

  const s = state.summary || {};
  setText("validCount", s.valid || 0);
  setText("errorCount", s.errors || 0);
  setText("reviewCount", s.review || 0);
  setText("labelCount", s.label || 0);
  setText("printCount", s.print || 0);
  setText("laserCount", s.laser || 0);

  updateReadiness(state.readiness || "NO_CHECK");
  updateErrors(state.errors || []);
  updateActivities(state.activities || []);
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function updateReadiness(readiness) {
  const banner = document.getElementById("banner");
  const title = document.getElementById("bannerTitle");
  const text = document.getElementById("bannerText");
  const blocked = readiness === "BLOKE";
  const review = readiness === "KONTROL_GEREKLI";
  const ready = readiness === "HAZIR";

  banner.className = "banner " + (blocked ? "blocked" : review ? "review" : ready ? "ready" : "idle");
  title.textContent = blocked ? "ÜRETİM BLOKE" : review ? "KONTROL GEREKLİ" : ready ? "ÜRETİME HAZIR" : "KONTROL BEKLENİYOR";
  text.textContent = blocked
    ? "Kritik hatalar düzeltilmeden üretim dosyası oluşturulamaz."
    : review
      ? "Kontrol gerektiren satırlar var. Üretime geçmeden önce inceleyin."
      : ready
        ? "Kontrol tamamlandı. Dosya hazırlama adımlarına geçebilirsiniz."
        : "Excel dosyanızı seçip dry-run kontrolünü başlatın.";

  setStep("step2", blocked ? "blocked" : ready ? "done" : review ? "blocked" : "");
  setStep("step3", blocked ? "blocked" : "");
  setStep("step4", blocked ? "blocked" : "");
  document.getElementById("sideControl").textContent = blocked ? "Bloke" : ready ? "Tamamlandı" : review ? "Kontrol Gerekli" : "Beklemede";
  document.getElementById("sideLabel").textContent = blocked ? "Bloke" : "Beklemede";
  document.getElementById("sideLaser").textContent = blocked ? "Bloke" : "Beklemede";
}

function setStep(id, state) {
  const el = document.getElementById(id);
  el.classList.remove("done", "blocked");
  if (state) el.classList.add(state);
}

function updateErrors(errors) {
  const list = document.getElementById("errorList");
  if (!errors.length) {
    list.innerHTML = `<div class="error-item"><b>Kritik hata yok.</b><p>Dry-run sonrası kritik hata bulunmazsa burada temiz görünür.</p></div>`;
    return;
  }
  list.innerHTML = errors.map(item => `
    <div class="error-item">
      ${item.row ? `<span class="row-pill">${esc(item.row)}</span>` : ""}
      <b>${esc(item.title)}</b>
      <p>${esc(item.desc)}</p>
    </div>
  `).join("");
}

function updateActivities(rows) {
  const body = document.getElementById("activityRows");
  if (!rows.length) {
    body.innerHTML = `<tr><td>-</td><td>Henüz işlem yok</td><td>-</td><td>Excel seçip kontrol başlatın</td></tr>`;
    return;
  }
  body.innerHTML = rows.map(row => `
    <tr>
      <td>${esc(row.time)}</td>
      <td>${esc(row.action)}</td>
      <td>${esc(row.status)}</td>
      <td>${esc(row.detail)}</td>
    </tr>
  `).join("");
}

new QWebChannel(qt.webChannelTransport, channel => {
  bridge = channel.objects.cyzella;
  window.bridge = bridge;
  bridge.stateChanged.connect(applyState);
  bridge.logChanged.connect(() => {});
  bridge.initialState(applyState);
});

document.getElementById("themeCheck").addEventListener("change", event => {
  document.body.classList.toggle("dark", event.target.checked);
});
document.getElementById("dayBtn").addEventListener("click", () => {
  document.body.classList.remove("dark");
  document.getElementById("themeCheck").checked = false;
});
document.getElementById("nightBtn").addEventListener("click", () => {
  document.body.classList.add("dark");
  document.getElementById("themeCheck").checked = true;
});
