# İsim Kesim Modülü — Tam İnceleme ve Çekirdek Editör Planı

## Yönetici Özeti

- **Manuel yazı yazma/düzenleme: ~%55** — JS mantığı (taslak, canlı önizleme, kaydet) tam yazılmış ama `nameCutEditModal` ve tüm form alanları `index.html`'de YOK; "Manuel" düğmesi tıklanınca hiçbir şey açılmıyor (canlı doğrulandı).
- **Kalınlaştırma: ~%40** — "Tümüne Uygula" `offset_mm` verisini yazıyor, ama panel kaydırıcısı (slider) bağlı değil ve gerçek path dilation yalnızca Qt backend'inde; web modunda metadata + uyarı kalıyor.
- **Harfleri birleştirme/weld: ~%35** — `nameCutInternalWeld` sadece bayrak işaretliyor (`internal_weld_requested`); gerçek path kaynağı Qt `build_name_cut_production_scene` köprüsünde, bu köprü web modunda yok.
- **En kritik 5 bozukluk:** (a) Manuel/Düzenle modalı DOM'da yok; (b) Yerleşim paneli inputları `updateNameCutLayoutConfig()`'i argümansız çağırıyor → hiçbir değer yazılmıyor; (c) Stil font `<select>` config'i değil sadece `runNameCutBreakCheck()`'i çağırıyor → font değişmiyor; (d) Export onay modalı (`nameCutExportConfirmModal`) ve Yapıştır modalı (`nameCutPasteModal`) DOM'da yok; (e) web modunda tüm name-cut üretim köprüleri (`prepare_name_cut_files`, `build_name_cut_production_scene`, `preview_name_cut_paths`) tanımsız.
- **Önerilen ilk 3 adım:** (1) `nameCutEditModal` + alan id'lerini `index.html`'e ekleyip Manuel'i ayağa kaldırmak; (2) Yerleşim/Stil/Kalınlaştır panel inputlarına doğru field argümanları ve id'ler vermek; (3) Export/Yapıştır modallarının markup'ını eklemek.
- **Güvenlik durumu olumlu:** lazer/RDWorks otomatik başlamıyor, export operatör onayı + blocker kontrolü arkasında (`confirmNameCutSafeExport`, app.js:16971), stublar "sahte başarı" göstermiyor (`showNameCutFeatureNotice`, app.js:16263).

## A) Manuel Yazı Yazma / Düzenleme

"Manuel" düğmesi (index.html:592 ve index.html:623) → `openManualNameCutModal()` (app.js:16662). Fonksiyon eksiksiz: `manual-name-<timestamp>` id'li yeni taslak oluşturuyor, varsayılan ad "Sedef Sefer", width_mm/height_mm/style/composition/offset_mm alanlarını dolduruyor, `nameCutApplyFontMetaToItem` ile font metasını uyguluyor, sonra `renderNameCutEditor()` çağırıp `byId("nameCutEditModal")`'ı görünür yapmaya çalışıyor (app.js:16690-16691).

**Sorun (BOZUK):** `nameCutEditModal` ve alanları (nameCutEditName, nameCutEditPreview, nameCutEditStyle, nameCutEditComposition, nameCutEditWidth, nameCutEditHeight, nameCutEditQty, nameCutEditThickening, nameCutEditOffset, nameCutEditSupport, nameCutEditPlate, nameCutEditStatus) `index.html`'de hiç tanımlı değil. Canlı testte "Manuel" tıklandı → hiçbir modal açılmadı, konsola hata da düşmedi (null-guard sayesinde sessiz başarısızlık).

Mevcut ismi düzenleme: `openNameCutEditor(index)` (app.js:16653) aynı modalı kullandığı için aynı sebeple çalışmıyor. Canvas'ta seçili ismi taşıma/yeniden boyutlama veri katmanında çalışıyor: `nameCutApplyManualGeometry` (app.js:14597, work-area clamp'li), `updateSelectedNameCutGeometry` (app.js:16203), pointer işleyicileri `beginNameCutItemPointer`/`moveNameCutInteraction`/`endNameCutInteraction` (app.js:16096/16134/16190).

**Önizleme:** `renderNameCutEditor` (app.js:16701) ve `refreshNameCutEditorFeedback` (app.js:16778) her alan değişiminde `computeNameCutLayout(... forceRecompute:true)` (app.js:13866) çağırıp `renderNameCutComputedPreview` ile FontTools-benzeri tahmin önizlemesi üretiyor. Kaydet: `saveNameCutDraft` (app.js:16792) yeni ismi `nameCutItems.unshift`, düzenlemeyi index ile değiştiriyor — mantık tam.

**Eksik tamamlama yolu (kod değil, plan):** Yeni isim nesnesi zaten `openManualNameCutModal`'da doğru şemada kuruluyor; layout'a girişi `saveNameCutDraft` + `applyNameCutLayoutResultToItem` (app.js:14064) hallediyor. Tek gereken modal markup'ı.

## B) Kalınlaştırma

İşlem şeridi "Tümüne Uygula" (index.html:709) ve panel butonu → `applyNameCutOffsetToAll()` (app.js:16508). Bu fonksiyon `nameCutLayoutConfig.offset_mm`'i 0–1.5 mm clamp'leyip tüm öğelere `offset_mm` + `thickening_mode:"Özel offset"` yazıyor ve "üretim öncesi kontrol değeri" uyarısı ekliyor (app.js:16515) — yani veri katmanında gerçek, ancak path büyütme değil.

Backend parametreleri config'te mevcut: `offset_mm: 0.3` (app.js:304), `offset_type: "Dışa kalınlaştır"` (app.js:306), `min_stroke_mm: 0.28` (app.js:308). Moda göre offset: `nameCutOffsetForMode` (app.js:15674; yok=0, hafif=0.4, kalın=1.2, özel=0.8). Bu değerler `nameCutPathPreviewPayload` (app.js:14394) ile backend'e gidiyor.

**Sorun (BOZUK/KISMİ):** Kalınlaştır panelindeki kaydırıcı `<input type="range" ... value="0.3">` (index.html:707) id'siz ve oninput handler'sız — hareket ettirmek hiçbir şey yapmıyor; sadece "Tümüne Uygula" çalışıyor. Gerçek geometrik dilation yalnızca Qt `build_name_cut_production_scene`/`preview_name_cut_paths` üzerinden; web modunda bu köprüler tanımsız, bu yüzden `requestNameCutProductionScene` (app.js:14487) erken return ediyor (app.js:14489) ve önizleme JS tahminine düşüyor.

## C) Harfleri Birleştirme / Kaynak (Weld)

Config bayrakları: `weld_inside_name: true` (app.js:291), `capital_connection_fix: true` (app.js:293), `punctuation_fix: true` (app.js:294), `turkish_mark_bridge: true` (app.js:309), `dot_bridge_enabled: true` (app.js:310). Bunlar `updateNameCutLayoutConfig` içinde boolean olarak değiştirilebiliyor (app.js:16538) ama bunları değiştiren bir UI kontrolü görünür panellerde yok.

"İç Kaynak" (index.html:609) → `nameCutInternalWeld()` (app.js:16453): seçiliye veya tümüne `internal_weld_requested=true` + `inter_name_connection_forbidden=true` bayrağı koyuyor. Gerçek bitişik-harf birleştirme path'i frontend'de YAPILMIYOR — backend'e (Qt) deferral. Farklı isimler asla birbirine bağlanmıyor (güvenli, doğru tasarım). "Köprü" (index.html:610) → `nameCutBridgeDots()` (app.js:16465) sadece Türkçe diakritik içeren isimlerde `diacritic_bridge_requested` bayrağı koyuyor.

## D) Sayfanın Tam Denetimi (özet)

Çalışan kontroller: Menü, Yeni, Kaydet, Farklı, Toplu, zoom/sığdır/1:1, ayna, otomatik diz, kopma kontrol, AI öneri, kuyruğa, Trendyol salt-okunur, yukarı/aşağı/sil, listeyi temizle, sekme geçişleri, referans/kontrol panelleri, alt durum çubuğu.

Stub (dürüst "desteklenmiyor" toast'ı): Ayarlar, Rehber, Aç, Geri, İleri.

**Bozuk:** Manuel (`openManualNameCutModal` → modal DOM'da yok), Yapıştır (`nameCutPasteModal` yok), Lazer Dosyalarını Hazırla (`prepareNameCutFiles` → onay modalı yok), Manuel Ekle çekmecesi (aynı modal).

**Ölü/bağsız inputlar:** Yerleşim Tabla W/H/boşluk/kenar (`updateNameCutLayoutConfig()` argümansız → field=undefined), Stil font `<select>` (sadece `runNameCutBreakCheck()`), Harf yüksekliği (id yok), "Bağlı yazı" checkbox (id yok), Kalınlaştır offset slider (id/oninput yok), Katman kesim hızı/güç (id yok, kozmetik).

## E) Bozukluk / Runtime Denetimi

**Tanımsız handler'lar (canlı typeof ile doğrulandı):** `openCurrentPdfForPrint` (index.html:760) ve İsim Kesim dışı: `openOutput` (239), `openPrintTemplates` (240), `exportPNG` (369), `exportPDF` (372), `chooseExcel` (873), `runDry` (913), `openSelectedOutput`/`previewSelectedOutput`/`addSelectedOutputToQueue` (1176-1178), `showSettings` (1570). Tıklanınca ReferenceError üretir.

**DOM'da olmayan ama JS'in beklediği elemanlar:** `nameCutEditModal` + tüm `nameCutEdit*` alanları, `nameCutExportConfirmModal`/`nameCutExportConfirmBody`, `nameCutPasteModal` → ilgili akışlar sessizce başarısız.

**İki mod farkı (Qt 'cyzella' ↔ '/api' routes):** `api_adapter.js` yalnızca `update_name_cut_queue_item_status` sağlıyor (api_adapter.js:211). Web modunda `prepare_name_cut_files`, `build_name_cut_production_scene`, `preview_name_cut_paths` YOK. Sonuç: web modunda gerçek path önizleme, weld/kalınlaştırma geometrisi ve export yalnızca Qt masaüstü modunda işliyor. (Backend Python kaynakları tarayıcıya açık değil — Qt tarafındaki varlık dosya:satır ile doğrulanamadı, tahmin edilmedi.)

**Konsol:** Tek log — "Browser mode active — fetch-based bridge loaded" (api_adapter.js:360). Manuel tıklamasında hata yok (null-guard).

## F) Geliştirilmesi Gerekenler (öncelik sırasıyla)

1. **Manuel editör modalını ekle (yüksek değer):** çekirdek özellik UI'sı yok; `nameCutEditModal` markup'ı + alanlar; risk düşük (JS hazır).
2. **Panel input bağlama düzeltmeleri (yüksek):** Yerleşim/Stil/Kalınlaştır kontrolleri etkisiz/yanlış argüman; her input'a doğru field argümanı + id; risk düşük-orta.
3. **Geri/İleri (undo/redo) (orta):** stub; Etiket Studio undo motorunu uyarla (bkz. G); risk orta.
4. **Geri bildirim/seçili durum netliği (orta):** seçili öğe vurgusu ve dokunma alanları küçük; klavye odak halkası zayıf.
5. **Performans (düşük-orta):** `renderNameCutBottomDetails`, gallery her refresh'te yeniden basıyor; büyük listede sanallaştırma önerilir.
6. **Tutarlı Türkçe/etiket (düşük):** "Ayna Y/Ayna D" kısaltmaları belirsiz; tooltip netleştirilmeli.
7. **Güvenlik kapısı netliği (düşük):** export onay modalı eksik olduğundan operatör onay akışı görünmüyor; modal eklenince netleşir.

## G) Ortak Altyapı + Yeniden Kullanım

Etiket Studio'da hazır ve İsim Kesim çekirdek editörüne uyarlanabilir parçalar: `setCorelTool` (app.js:9512), `corelApplyTypography` (app.js:9908 — font family/size/color), `toggleCorelTextStyle('bold'...)` (app.js:9920), `applyFieldGeometry` (app.js:7197), `selectedManualField` (app.js:9508) ve özellikle tam undo/redo motoru: `pushManualUndo` (app.js:9142), `undoManualEdit` (app.js:9150), `redoManualEdit` (app.js:9156), `manualUndoStack`/`manualRedoStack`. Sonuç: ortak bir "editör çekirdeği" (metin alanı + tipografi + bold + undo/redo + geometri clamp) çıkarmak mantıklı; İsim Kesim ve Etiket Studio iki tüketici olur.

## H) Uygulama Planı (sahip onayına)

| İş | Mevcut % | Eksik | Dokunulacak dosyalar | Risk | Kabul kriteri |
|---|---|---|---|---|---|
| B1.1 Manuel modalı | 55 | nameCutEditModal + alanlar | index.html | Düşük | Manuel→modal açılır, isim eklenir/önizlenir/kaydedilir |
| B1.2 Kalınlaştırma bağlama | 40 | slider id+handler | index.html (707) | Düşük | Slider offset_mm'i günceller, önizlemeye yansır |
| B1.3 Weld UI bağlama | 35 | weld toggle'ları | index.html, app.js | Düşük | Toggle config'i değiştirir; geometri Qt pipeline'da kalır |
| B2.1 Yerleşim inputları | bozuk | field arg + id | index.html (692-696) | Düşük-Orta | W/H/boşluk/kenar config'i gerçekten değiştirir |
| B2.2 Stil font select | bozuk | font_family arg | index.html (700) | Düşük | Font değişimi önizlemeye yansır |
| B2.3 Export/Yapıştır modalları | bozuk | nameCutExportConfirmModal, nameCutPasteModal | index.html | Orta | Onay modalı açılır; blocker+offset onayı görünür |
| B2.4 Tanımsız handler'lar | bozuk | eksik fonksiyonlar/temizlik | index.html, app.js | Orta | Tanımsız onclick kalmaz |
| B3.1 Undo/Redo | stub | editör çekirdeği uyarlaması | app.js | Orta | Geri/İleri gerçek çalışır |
| B3.2 UX/perf iyileştirmeleri | — | F maddeleri | app.js, styles.css | Düşük | F'deki kriterler |

**Sıra:** B1 (3 çekirdek) → B2 (bozuk/stub onarımı) → B3 (iyileştirmeler). Geometri mümkün olduğunca mevcut Qt backend pipeline'ında bırakılır.

## Güvenlik (her adımda korunacak)

- Lazer/yazıcı asla otomatik başlamaz (Lazer otomatik başlamaz rozeti + `confirmNameCutSafeExport`'ta `bridge.prepare_name_cut_files` guard, app.js:16972).
- Üretim onay/doğrulama kapısı korunur (blocker + `nameCutExportOffsetApproval`, app.js:16978).
- FontTools Türkçe-karakter doğruluğu (`formatNameCutName` app.js:15683'te İlknur/Şeyma/Çağla/Oğuz/ŞÜKRÜ/"Ayşe & Mehmet" düzeltmeleri) bozulmaz.
- Kesim mm doğruluğu (`nameCutApplyManualGeometry` clamp'leri) korunur.
- Testler ≥250/0 korunacak şekilde planlanır.
- Trendyol salt-okunur (`openTrendyolSidebarTab('orders')` yalnızca çekme).
