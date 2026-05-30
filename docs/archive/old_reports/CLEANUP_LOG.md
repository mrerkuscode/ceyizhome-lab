# Dead Code Cleanup Log — dead-code-cleanup dalı

Tarih: 2026-05-29  
Dal: `dead-code-cleanup` (base: `button-audit-fix`)  
Başlangıç testleri: 23 başarısız / 234 geçti  
Bitiş testleri: 23 başarısız / 234 geçti ✅

---

## AŞAMA 1 — Kök .md Raporları Arşivlendi

| Öğe | Tür | Aksiyon | Test |
|-----|-----|---------|------|
| 205 rapor .md (root) | Dokümantasyon | `docs/archive/` altına `git mv` | ✅ YEŞİL |
| 16 test-zorunlu .md (README.md, RELEASE_NOTES.md, USER_MANUAL.md, TECHNICAL_MANUAL.md, INSTALLATION_CHECKLIST.md, FINAL_RELEASE_CHECKLIST.md, REAL_USER_TESTING_STANDARD.md, HUMAN_QA_PROTOCOL.md, INTERACTION_TESTING_GUIDE.md, BUTTON_CLICK_TESTING_STANDARD.md, VISUAL_SCREENSHOT_QA_GUIDE.md, OUTPUT_VALIDATION_STANDARD.md, TEST_COMMAND_REAL_USER_QA_PROTOCOL.md, COMMAND_ALIASES.md, START_HERE_FOR_CODEX.md, CODEX_CURRENT_PRIORITY.md, CODEX_LEAD_DEVELOPER_MANUAL.md) | Dokümantasyon | Kök dizinde korundu | ✅ |

**Commit:** `1faf6d9`

---

## AŞAMA 2 — LEGACY Web UI Silindi

| Öğe | Tür | Ölü Kanıtı | Dinamik/Backend | Aksiyon | Test |
|-----|-----|-----------|-----------------|---------|------|
| `src/desktop/web_ui/LEGACY_NOT_USED.md` | Belge | Açık işaret | Yok | Silindi | ✅ |
| `src/desktop/web_ui/app.js` | JS | 0 referans Python/app.js/html | Yok | Silindi | ✅ |
| `src/desktop/web_ui/index.html` | HTML | 0 referans | Yok | Silindi | ✅ |
| `src/desktop/web_ui/style.css` | CSS | 0 referans | Yok | Silindi | ✅ |

**Commit:** `15ec2c2`

---

## AŞAMA 3 — TypeScript/TSX Artıkları Silindi

| Öğe | Tür | Ölü Kanıtı | Dinamik/Backend | Aksiyon | Test |
|-----|-----|-----------|-----------------|---------|------|
| `src/webui/components/text/ScriptFontPreview.tsx` | TSX | Build yok, 0 import | Yok | Silindi | ✅ |
| `src/webui/components/text/ScriptTextRenderer.tsx` | TSX | Build yok, 0 import | Yok | Silindi | ✅ |
| `src/webui/components/text/capitalConnectionFixMap.ts` | TS | Build yok, 0 import | Yok | Silindi | ✅ |
| `src/webui/components/text/punctuationFixMap.ts` | TS | Build yok, 0 import | Yok | Silindi | ✅ |
| `src/webui/lib/fonts/capitalConnectionFixMap.ts` | TS | Build yok, 0 import | Yok | Silindi | ✅ |
| `src/webui/lib/fonts/fontProfiles.ts` | TS | Build yok, 0 import | Yok | Silindi | ✅ |
| `src/webui/lib/fonts/punctuationFixMap.ts` | TS | Build yok, 0 import | Yok | Silindi | ✅ |

Not: app.js başındaki `capitalConnectionFixMap`, `punctuationFixMap`, `fontProfiles` sabit tanımları — TS dosyalarından import değil, satır içi tanımlı.

**Commit:** `0752179`

---

## AŞAMA 4 — Çift Tanımlı Fonksiyonlar

| Fonksiyon | Kopya | Satır | Aksiyon | Test |
|-----------|-------|-------|---------|------|
| `parseBridgeResult` | İlk (eski, daha az kapsamlı) | ~497 | Silindi — son kopya (ln 20304) runtime'da kazanır | ✅ |
| `labelOutputCreatedDate` | İlk (birebir aynı) | ~2532 | Silindi — son kopya (ln 18084) runtime'da kazanır | ✅ |

**Commit:** `0149302`

---

## AŞAMA 5 — Çağrılmayan Fonksiyonlar (25 adet)

Her fonksiyon için doğrulama: app.js+index.html çağrı yok, Python backend yok, eval/window[] dinamik çağrı yok.

| Fonksiyon | Kategori | Aksiyon | Test |
|-----------|----------|---------|------|
| `auto_layout_label` | Layout artık | Silindi | ✅ |
| `center_field_horizontally` | Layout artık | Silindi | ✅ |
| `distribute_fields_vertically` | Layout artık | Silindi | ✅ |
| `estimateJoinedNameWidth` | Layout artık | Silindi | ✅ |
| `cleanupDuplicateNameFields` | Layout artık | Silindi | ✅ |
| `callBridge` | Bridge artık | Silindi | ✅ |
| `openNativeModelEditor` | Native artık | Silindi | ✅ |
| `formatRows` | Tablo artık | Silindi | ✅ |
| `missingPreviewHtml` | Önizleme artık | Silindi | ✅ |
| `queueSourceLabelForPath` | Kuyruk artık | Silindi | ✅ |
| `requestNameCutPathPreview` | İsim Kesim artık | Silindi | ✅ |
| `nameCutPathPreviewForItem` | İsim Kesim artık | Silindi | ✅ |
| `nameCutPreviewText` | İsim Kesim artık | Silindi | ✅ |
| `renderNameCutPreviewWord` | İsim Kesim artık | Silindi | ✅ |
| `fixNameCutDraftToTargetSize` | İsim Kesim artık | Silindi | ✅ |
| `addLastManualPdfToQueue` | PDF artık | Silindi | ✅ |
| `openManualPdfPreview` | Önizleme artık | Silindi | ✅ |
| `previewManualPng` | Önizleme artık | Silindi | ✅ |
| `dxfLibraryLookupForName` | DXF artık | Silindi | ✅ |
| `exportTrendyolReadyToExcel` | Trendyol artık | Silindi | ✅ |
| `setBulkGallerySearch` | Galeri artık | Silindi | ✅ |
| `showBulkGalleryProblemDetail` | Galeri artık | Silindi | ✅ |
| `renderTrendyolSelectedQuestionCandidates` | Trendyol artık | Silindi | ✅ |
| `startNewLabelModelWizardSourceSelect` | Wizard artık | Silindi | ✅ |
| `testSelectedModelPreview` | Model artık | Silindi | ✅ |

**Commit:** `d69aa90`

**Teknik Not:** `requestNameCutPathPreview(layout = {})` default parametresindeki `{}` ilk basit script'in brace sayacını yanıltıyordu. Parametre listesini atlayan gelişmiş parser ile çözüldü.

---

## KORUNAN ÖĞELER (TUT)

| Öğe | Neden Korundu |
|-----|--------------|
| `src/desktop/*.py` | Qt desktop app'in aktif modülleri |
| `src/webui/` tüm aktif JS | Çalışan uygulama |
| `scripts/` klasörü | Testlerde referans var (package.json, test suite) |
| `assets/`, `data/`, `models/` | Üretim verisi |
| `src/webui_backend/` tüm Python | Aktif backend API'lar |
| legacy generative name-cut kodu | Proje invariantı: geri dönüş için korunacak (use_legacy_name_cut_algorithms flag) |

---

## ÖZET

| Metrik | Değer |
|--------|-------|
| Arşivlenen .md | 205 dosya |
| Silinen LEGACY klasör | 4 dosya (758 satır) |
| Silinen TS/TSX | 7 dosya (340 satır) |
| Silinen çift fonksiyon | 2 kopya (15 satır) |
| Silinen çağrılmayan fonksiyon | 25 adet (~222 satır) |
| **Toplam silinen satır (app.js)** | **~237 satır** |
| Testler: başlangıç | 23 başarısız / 234 geçti |
| Testler: bitiş | 23 başarısız / 234 geçti ✅ |
| Görsel/işlev değişikliği | YOK |
