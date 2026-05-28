/* ============================================================================
   CeyizHome Lab — REDESIGN ETKİLEŞİMLERİ
   Bu dosyayı app.js'in EN SONUNA ekle (veya index.html'de app.js'ten SONRA
   <script src="redesign-interactions.js"></script> ile yükle).
   Hepsi app.js'in MEVCUT fonksiyonlarını çağırır; yeni iş mantığı yok.
   Amaç: önizlemede çalışan ama app.js'e taşınmayan 3 davranışı gerçek uygulamada açmak:
     1) Sol menü aç/kapa
     2) Çalışma alanında (Etiket Studio + İsim Kesim) fare TEKERLEĞİ ile zoom
     3) Studio'ya girince / pencere boyutu değişince çalışma alanını EKRANA SIĞDIR (büyüt)
   ============================================================================ */
(function () {
  "use strict";

  /* ---- 1) SOL MENÜ AÇ / KAPA -------------------------------------------- */
  // Sidebar'daki .sidebar-toggle butonuna basınca .app'e .nav-collapsed ekler/çıkarır.
  // (CSS: .app.nav-collapsed grid kolonunu 66px'e indirip etiketleri gizler.)
  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest(".sidebar-toggle");
    if (!btn) return;
    e.preventDefault();
    var app = document.getElementById("appShell") || document.querySelector(".app");
    if (app) app.classList.toggle("nav-collapsed");
  });

  /* ---- 2) FARE TEKERLEĞİ İLE ZOOM --------------------------------------- */
  // Çalışma alanının üzerinde tekerlek: yukarı = yakınlaş, aşağı = uzaklaş.
  // Mevcut zoom fonksiyonlarını çağırır (varsa). Sayfa kaymasını engeller.
  function bindWheelZoom(stageSelector, zoomIn, zoomOut) {
    var stage = document.querySelector(stageSelector);
    if (!stage) return;
    stage.addEventListener(
      "wheel",
      function (e) {
        e.preventDefault();
        (e.deltaY < 0 ? zoomIn : zoomOut)();
      },
      { passive: false }
    );
  }
  // Etiket Studio çalışma alanı (.canvas-stage) → app.js: setManualZoom('in'/'out')
  bindWheelZoom(
    "#label .canvas-stage",
    function () { if (typeof setManualZoom === "function") setManualZoom("in"); },
    function () { if (typeof setManualZoom === "function") setManualZoom("out"); }
  );
  // İsim Kesim çalışma alanı (.nc-stage) → app.js: nameCutZoom(±)
  bindWheelZoom(
    "#nameCutStudio .nc-stage",
    function () { if (typeof nameCutZoom === "function") nameCutZoom(10); },
    function () { if (typeof nameCutZoom === "function") nameCutZoom(-10); }
  );

  /* ---- 3) ÇALIŞMA ALANINI EKRANA SIĞDIR (BÜYÜT) ------------------------- */
  // Studio'ya her girişte ve pencere yeniden boyutlanınca, app.js'in mevcut
  // "ekrana sığdır" fonksiyonunu çağırır ki tabla alanı tüm boşluğu doldursun.
  function fitActiveStudio() {
    var L = document.getElementById("label");
    var N = document.getElementById("nameCutStudio");
    if (L && L.classList.contains("active")) {
      if (typeof setManualZoom === "function") setManualZoom("fit");
    }
    if (N && N.classList.contains("active")) {
      if (typeof nameCutFitToScreen === "function") nameCutFitToScreen();
    }
  }
  // Sidebar'dan Etiket Studio / İsim Kesim'e geçince (DOM yerleşince) sığdır.
  document.addEventListener("click", function (e) {
    var nav = e.target.closest && e.target.closest(
      '.nav-btn[data-page="label"], .nav-btn[data-page="nameCutStudio"]'
    );
    if (nav) setTimeout(fitActiveStudio, 80);
  });
  // Pencere boyutu değişince yeniden sığdır.
  var rT;
  window.addEventListener("resize", function () {
    clearTimeout(rT);
    rT = setTimeout(fitActiveStudio, 150);
  });
  // İlk yükleme.
  setTimeout(fitActiveStudio, 350);

  /* --------------------------------------------------------------------------
     NOT (önemli): Eğer "fit" çağrısından sonra tabla HÂLÂ küçük kalıyorsa,
     app.js'teki setManualZoom('fit') / nameCutFitToScreen() fonksiyonları sabit bir
     boyuta sığdırıyor demektir. O fonksiyonların içinde, hedef boyutu çalışma
     alanının GERÇEK ölçüsünden hesaplaması gerekir. Referans mantık:

       var stage = document.querySelector('#label .canvas-stage'); // veya .nc-stage
       var pad = 18;
       var availW = stage.clientWidth  - pad * 2;
       var availH = stage.clientHeight - pad * 2;
       // en-boy oranını koruyarak availW/availH içine ~%94 sığdır:
       var w = availW, h = w / aspect;          // aspect = tablaGenişlik / tablaYükseklik
       if (h > availH) { h = availH; w = h * aspect; }
       w *= 0.94; h *= 0.94;
       // -> tabla/preview elemanını (manualPreview / nameCutStudioLayoutPreview) bu w,h ile ölçekle.

     Böylece tabla, yan paneller daraldıkça/pencere büyüdükçe alanı doldurur.
  -------------------------------------------------------------------------- */
})();
