from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "trendyol_real_user_smoke"
RESULT_PATH = OUTPUT_DIR / "TRENDYOL_REAL_USER_SMOKE_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 60000):
    loop = QEventLoop()
    result = {"done": False, "value": None}

    def callback(value):
        result["done"] = True
        result["value"] = value
        loop.quit()

    wrapped = f"""
    (() => {{
      try {{
        return JSON.stringify(({script}));
      }} catch (error) {{
        return JSON.stringify({{ "__error": String(error && error.message || error), stack: String(error && error.stack || "") }});
      }}
    }})()
    """
    window.view.page().runJavaScript(wrapped, callback)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if not result["done"]:
        raise RuntimeError(f"JavaScript timed out: {script[:160]}")
    value = result["value"]
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict) and parsed.get("__error"):
            raise RuntimeError(f"{parsed['__error']}\n{parsed.get('stack', '')}")
        return parsed
    return value


def wait_for(window: WebMainWindow, script: str, timeout_ms: int = 60000, interval_ms: int = 500):
    deadline = max(1, timeout_ms // interval_ms)
    last = None
    for _ in range(deadline):
        last = run_js(window, script, timeout_ms=min(timeout_ms, 5000))
        if isinstance(last, dict) and last.get("ok"):
            return last
        wait(interval_ms)
    raise AssertionError(f"Condition timed out: {last}")


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    window.view.grab().save(str(path))
    return str(path)


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def inject_fixture(window: WebMainWindow) -> dict[str, object]:
    return run_js(
        window,
        r"""
        (() => {
          window.__trendyolSmokeCalls = [];
          window.__trendyolSmokeImported = [];
          window.__trendyolSmokeQueue = [];
          const model = {
            path: 'templates/designs/01_a_gold.json',
            model_name: '01 A Gold Rulo Etiket',
            model_no: '01',
            template_no: 'A',
            fields_summary: []
          };
          currentState.labelModels = [model];
          currentLabelModels = [model];
          const mkQuestion = (id, order, barcode, text) => ({
            id,
            status: 'ANSWERED',
            order_number: order,
            barcode,
            question_text: text,
            answer_text: 'Tamamdır efendim, siparişiniz isteğinize göre işleme alınacaktır.',
            created_date: '30.05.2026 15:42'
          });
          const questions = [
            mkQuestion('q-1', '11243826278', 'TY-SMOKE-001', 'Merhaba, sipariş no: 11243826278 Bahar & Yunus ürün görseldeki aynı olacak detaylar gümüş renk olsun istiyorum.'),
            mkQuestion('q-2', '11242760731', 'TY-SMOKE-002', 'İsimler Derya ve M.Şerif tarih 30.05.2026 nişan hatırası yazılsın.'),
            mkQuestion('q-3', '11242658230', 'TY-SMOKE-003', 'Hepsi beyaz olsun, üzerine isim yazılmasın.'),
            mkQuestion('q-4', '11242576296', 'TY-SMOKE-004', 'Tuğçe & Murat 29.05.2026 gold yazı olsun, tepsi içinde Allahın emri yazısı olsun.'),
            mkQuestion('q-5', '11243183515', 'TY-SMOKE-005', 'Elvida Ömer olacak isimler.'),
            mkQuestion('q-6', '11243236233', 'TY-SMOKE-006', 'Görseldeki gibi, tülü siyah olsun, Elif sonsuzluk işareti Muhammed yazılsın.')
          ];
          questions.push({ id: 'q-candidate-smoke', status: 'ANSWERED', answered: true, order_number: '11249990000', customer_name: 'Trendyol M??teri', product_name: 'Gold ?er?eveli Cam Sunumluk Kapakl? Sand?k', barcode: 'TY-SMOKE-CANDIDATE', merchant_sku: '', question_text: 'Sipari? no 11249990000 ?zerindeki isimler nas?l yaz?lacak acaba', answer_text: '' });
          const row = (idx, data) => ({
            id: `ty-smoke-${idx}`,
            order_number: data.order,
            line_id: `line-${idx}`,
            customer_name: data.customer,
            product_name: data.product,
            barcode: data.barcode,
            merchant_sku: data.sku,
            quantity: data.qty || 1,
            image_url: data.image || '',
            product_url: data.url || '',
            status: 'review',
            verification_status: 'alanlar_onay_bekliyor',
            user_verified: false,
            mapping_found: data.mapping !== false,
            production_type: 'label_and_name_cut',
            model_path: data.mapping === false ? '' : model.path,
            model_name: data.mapping === false ? '' : model.model_name,
            label_text: data.label || '',
            name_cut_text: data.laser || data.label || '',
            date_text: data.date || '',
            custom_text: data.custom || '',
            production_note: data.note || '',
            note_text: data.note || '',
            confidence: data.confidence ?? 0.9,
            field_confidence: { personNames: 92, labelName: 90, laserName: 90, eventDate: data.date ? 90 : 0, productionNote: data.note ? 85 : 0, quantity: 95 },
            field_sources: { label_text: data.label ? 'question_text' : 'empty', name_cut_text: data.label ? 'question_text' : 'empty', date_text: data.date ? 'question_text' : 'empty', production_note: data.note ? 'question_text' : 'empty', quantity: 'order_line' },
            evidence_spans: { label_text: data.label || '', name_cut_text: data.label || '', date_text: data.date || '', production_note: data.note || '' },
            source_evidence: ['cloud_ai_extract', 'question_context'],
            question_contexts: data.question ? [data.question] : [],
            warnings: data.warnings || []
          });
          const suggestions = [
            row(1, { order: '11243826278', customer: 'Bahar Doğan', product: '41 Kırmızı Kızisteme Çiçeği ve 80 Adet Söz Çikolatası', barcode: 'TY-SMOKE-001', sku: 'SKU-SMOKE-001', label: 'Bahar & Yunus', note: 'Gümüş renk olsun; görseldeki gibi tasarım.', image: 'https://cdn.example.test/trendyol/bahar-yunus.png', url: 'https://www.trendyol.com/cyzella/41-kirmizi-kizisteme-cicegi-soz-cikolatasi-p-11243826278', question: questions[0] }),
            row(2, { order: '11242760731', customer: 'Necla Demez', product: '41 Karışık Şakayık İsteme Çiçeği Buketi ve İsimli Çikolata', barcode: 'TY-SMOKE-002', sku: 'SKU-SMOKE-002', label: 'Derya & M. Şerif', date: '30.05.2026', custom: 'Nişan hatırası', note: 'Çikolataların üzerine tarih ve nişan hatırası yazılacak.', image: 'https://cdn.example.test/trendyol/derya-serif.png', url: 'https://www.trendyol.com/cyzella/karisik-sakayik-isteme-cicegi-isimli-cikolata-p-11242760731', question: questions[1] }),
            row(3, { order: '11242658230', customer: 'Hammam Aburaidi', product: '3 Adet Kızisteme Söz Nişan Anne Baldız Gülü', barcode: 'TY-SMOKE-003', sku: 'SKU-SMOKE-003', label: '', note: 'Hepsi beyaz olacak.', confidence: 0.62, image: '', url: '', question: questions[2], warnings: ['Müşteri mesajında kişi ismi bulunamadı.'] }),
            row(4, { order: '11242576296', customer: 'Tuğçe Murat', product: 'Çiçekli Tasarım Çikolatalı Tepsi Gold Yazı', barcode: 'TY-SMOKE-004', sku: 'SKU-SMOKE-004', label: 'Tuğçe & Murat', date: '29.05.2026', custom: 'Allah’ın emri ile kızınızı istemeye geldik', note: 'Siyah kurdele, gold yazı, çiçekli tasarım.', image: 'https://cdn.example.test/trendyol/tugce-murat.png', url: 'https://www.trendyol.com/cyzella/cicekli-tasarim-cikolatali-tepsi-gold-yazi-p-11242576296', question: questions[3] }),
            row(5, { order: '11243183515', customer: 'Elvida Ömer', product: '41 Kırmızı Kızisteme Çiçeği ve 150 Adet Çikolata', barcode: 'TY-SMOKE-005', sku: 'SKU-SMOKE-005', label: 'Elvida & Ömer', image: 'https://cdn.example.test/trendyol/elvida-omer.png', url: 'https://www.trendyol.com/cyzella/kirmizi-kizisteme-cicegi-cikolata-p-11243183515', question: questions[4] }),
            row(6, { order: '11243236233', customer: 'Elif Muhammed', product: 'Tüllü Siyah İsteme Çikolatası', barcode: 'TY-SMOKE-006', sku: 'SKU-SMOKE-006', label: 'Elif ♾ Muhammed', custom: 'Allah’ın emri ile kızımızı istemeye geldik', note: 'Görseldeki gibi ve tülü siyah olacak.', mapping: false, image: 'https://cdn.example.test/trendyol/elif-muhammed.png', url: 'https://www.trendyol.com/cyzella/tullu-siyah-isteme-cikolatasi-p-11243236233', question: questions[5], warnings: ['Ürün eşleştirmesi yok.'] }),
            row(7, { order: '11249990000', customer: 'Aday Soru', product: 'Gold Çerçeveli Cam Sunumluk Kapaklı Sandık', barcode: 'TY-SMOKE-CANDIDATE', sku: 'SKU-SMOKE-CANDIDATE', label: '', note: '', confidence: 0.55, image: 'https://cdn.example.test/trendyol/candidate.png', url: 'https://www.trendyol.com/cyzella/gold-cerceveli-cam-sunumluk-kapakli-sandik-p-11249990000', question: null, warnings: ['Soru kanıtı bekleniyor.'] })
          ];
          /* candidate question is appended above before state initialization */
          /*
          currentState.trendyol.questions.push({
            id: 'q-candidate-smoke',
            status: 'ANSWERED',
            answered: true,
            customer_name: 'Trendyol Müşteri',
            product_name: 'Gold Çerçeveli Cam Sunumluk Kapaklı Sandık',
            barcode: 'TY-SMOKE-CANDIDATE',
            merchant_sku: '',
            question_text: 'Üzerindeki isimler nasıl yazılacak acaba',
            answer_text: ''
          });
          */
          const smokeImage = 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><rect width="160" height="160" fill="#eef2ff"/><circle cx="80" cy="70" r="34" fill="#6366f1"/><rect x="34" y="112" width="92" height="14" rx="7" fill="#818cf8"/></svg>');
          bridge = {
            ...(bridge || {}),
            cache_trendyol_product_image(source, callback) {
              window.__trendyolSmokeCalls.push(['cache', source]);
              callback(JSON.stringify({ status: 'OK', preview_url: smokeImage }));
            },
            apply_trendyol_question_to_suggestion(id, questionId, callback) {
              window.__trendyolSmokeCalls.push(['apply', id, questionId]);
              const item = currentState.trendyol.suggestions.find(row => row.id === id);
              if (item) item.source_evidence = [...new Set([...(item.source_evidence || []), 'question_applied'])];
              callback(JSON.stringify({ status: 'OK', message: 'Soru kanıtı bağlandı.' }));
            },
            verify_trendyol_suggestion(id, payloadRaw, callback) {
              window.__trendyolSmokeCalls.push(['verify', id, JSON.parse(payloadRaw || '{}')]);
              const payload = JSON.parse(payloadRaw || '{}');
              const item = currentState.trendyol.suggestions.find(row => row.id === id);
              if (item) {
                Object.assign(item, {
                  label_text: payload.label_text,
                  name_cut_text: payload.name_cut_text,
                  date_text: payload.date_text,
                  note_text: payload.note_text,
                  quantity: Number(payload.quantity || item.quantity || 1),
                  model_path: payload.model_path,
                  model_name: payload.model_name,
                  status: 'ready',
                  verification_status: 'uretime_hazir',
                  user_verified: true,
                  mapping_found: true
                });
              }
              callback(JSON.stringify({ status: 'OK', message: 'Doğrulandı.' }));
            },
            import_trendyol_suggestion_to_customer_order(id, callback) {
              window.__trendyolSmokeCalls.push(['import', id]);
              const item = currentState.trendyol.suggestions.find(row => row.id === id);
              if (item) {
                item.import_status = 'imported';
                item.customer_order_id = `CO-${id}`;
                window.__trendyolSmokeImported.push(id);
              }
              callback(JSON.stringify({ status: 'OK', message: 'Üretime aktarıldı.' }));
            },
            export_trendyol_ready_to_excel(idsRaw, callback) {
              window.__trendyolSmokeCalls.push(['export', idsRaw]);
              callback(JSON.stringify({ status: 'OK', message: 'Excel hazır.' }));
            },
            upsert_trendyol_mapping(payloadRaw, callback) {
              const payload = JSON.parse(payloadRaw || '{}');
              window.__trendyolSmokeCalls.push(['mapping-save', payload]);
              currentState.trendyol.mappings = [...(currentState.trendyol.mappings || []), payload];
              currentState.trendyol.suggestions.forEach(row => {
                if ((payload.barcode && row.barcode === payload.barcode) || (payload.merchant_sku && row.merchant_sku === payload.merchant_sku)) {
                  row.mapping_found = true;
                  row.model_path = payload.model_path || row.model_path;
                  row.production_type = payload.production_type || row.production_type;
                }
              });
              callback(JSON.stringify({ status: 'OK', message: 'Eslestirme kaydedildi.' }));
            }
          };
          refreshState = () => updateTrendyolOrders(currentState.trendyol || {});
          currentState.trendyol = {
            settings: {},
            summary: { total: suggestions.length, ready: 0, review: suggestions.length, unmatched: 1, question_context: 6, imported: 0 },
            suggestions,
            questions,
            mappings: [],
            mappingSuggestions: []
          };
          selectedTrendyolSuggestionId = 'ty-smoke-1';
          expandedTrendyolSuggestionId = '';
          showSection('trendyolOrders');
          updateTrendyolOrders(currentState.trendyol);
          return { ok: true, count: suggestions.length };
        })()
        """,
        timeout_ms=120000,
    )


def click_by_text(window: WebMainWindow, selector: str, text: str, index: int = 0):
    return run_js(
        window,
        f"""
        (() => {{
          const items = [...document.querySelectorAll({json.dumps(selector)})]
            .filter(el => (el.textContent || '').includes({json.dumps(text)}));
          const el = items[{index}];
          if (!el) return {{ ok: false, selector: {json.dumps(selector)}, text: {json.dumps(text)}, count: items.length }};
          el.click();
          return {{ ok: true, text: el.textContent.trim(), count: items.length }};
        }})()
        """,
    )


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    setup = inject_fixture(window)
    assert_true(setup.get("ok"), "Fixture enjekte edilemedi", setup)
    wait(700)

    rendered = wait_for(
        window,
        """
        (() => {
          const text = document.getElementById('trendyolSuggestionsList')?.innerText || '';
          return {
            ok: document.querySelectorAll('#trendyolSuggestionsList .trendyol-suggestion-card').length >= 6,
            cards: document.querySelectorAll('#trendyolSuggestionsList .trendyol-suggestion-card').length,
            thumbs: document.querySelectorAll('#trendyolSuggestionsList .order-product-thumb-wrap').length,
            placeholders: document.querySelectorAll('#trendyolSuggestionsList .order-product-thumb-wrap.missing, #trendyolSuggestionsList .order-product-thumb-placeholder').length,
            titleLinks: document.querySelectorAll('#trendyolSuggestionsList .product-title-link[href^="https://www.trendyol.com/"]').length,
            blockerStrips: document.querySelectorAll('#trendyolSuggestionsList .trendyol-blocker-strip').length,
            hasCandidateSignal: text.includes('Aday soru var') && text.includes('Aday var'),
            rawDebugVisible: /person_names:|label_text:|name_cut_text:|production_note:/i.test(text),
            hasBahar: text.includes('Bahar & Yunus'),
            hasMissing: text.includes('Bulunamadı'),
            hasNoImage: text.includes('Görsel yok')
          };
        })()
        """,
    )
    assert_true(rendered["cards"] >= 6, "6 Trendyol kartı render edilmedi", rendered)
    assert_true(rendered["thumbs"] >= 6, "Ürün görsel/placeholder alanı render edilmedi", rendered)
    assert_true(rendered["titleLinks"] >= 4, "Trendyol ürün linkleri render edilmedi", rendered)
    assert_true(rendered["hasCandidateSignal"], "Kanıt adayı ana kartta görünür değil", rendered)
    assert_true(not rendered["rawDebugVisible"], "Teknik extraction alanları kullanıcı ekranına sızdı", rendered)
    assert_true(rendered["blockerStrips"] >= 1, "Uretim kontrol/blokaj ozet seridi render edilmedi", rendered)
    checks.append({"name": "orders_render_compact_cards_media_links", "status": "PASSED", "state": rendered})
    screenshots["orders_list"] = save_screenshot(window, "trendyol_orders_list.png")

    quick_candidate = click_by_text(window, "#trendyolSuggestionsList button", "En iyi adayı bağla")
    assert_true(quick_candidate.get("ok"), "Aday soru hızlı bağlama butonu bulunamadı", quick_candidate)
    quick_candidate_call = wait_for(
        window,
        "(() => ({ ok: (window.__trendyolSmokeCalls || []).some(call => call[0] === 'apply' && call[1] === 'ty-smoke-7' && call[2] === 'q-candidate-smoke'), calls: window.__trendyolSmokeCalls || [] }))()",
    )
    checks.append({"name": "candidate_question_quick_bind_hook_called", "status": "PASSED", "state": quick_candidate_call})

    modal_click = run_js(
        window,
        """
        (() => {
          const button = document.querySelector('#trendyolSuggestionsList .order-product-thumb-wrap:not(.missing)');
          if (!button) return { ok: false, error: 'thumbnail missing' };
          button.click();
          return { ok: true };
        })()
        """,
    )
    assert_true(modal_click.get("ok"), "Ürün görsel modalı için thumbnail bulunamadı", modal_click)
    lightbox = wait_for(
        window,
        "(() => ({ ok: Boolean(document.querySelector('.image-lightbox-backdrop')), title: document.querySelector('.image-lightbox-head b')?.textContent || '' }))()",
    )
    checks.append({"name": "product_image_lightbox_opens", "status": "PASSED", "state": lightbox})
    run_js(window, "(() => { closeProductImageModal(); return { ok: true }; })()")

    expand = click_by_text(window, "#trendyolSuggestionsList button", "Detayları Göster")
    assert_true(expand.get("ok"), "Detayları Göster butonu çalışmadı", expand)
    wait(500)
    details = wait_for(
        window,
        """
        (() => ({
          ok: Boolean(document.querySelector('#trendyolSuggestionsList .trendyol-suggestion-card.expanded')),
          hasMessage: (document.querySelector('#trendyolSuggestionsList .trendyol-suggestion-card.expanded')?.innerText || '').includes('Müşteri Mesajı'),
          hasAiTable: Boolean(document.querySelector('#trendyolSuggestionsList .trendyol-ai-detail-table')),
          hasVerifyInput: Boolean(document.getElementById('trendyolVerifyLabelText'))
        }))()
        """,
    )
    assert_true(details["hasMessage"] and details["hasAiTable"] and details["hasVerifyInput"], "Detay alanları kart içine açılmadı", details)
    checks.append({"name": "expanded_card_contains_evidence_ai_table_verify_form", "status": "PASSED", "state": details})

    apply = click_by_text(window, "#trendyolSuggestionsList .trendyol-question-evidence.detail button", "Bu metinden alanları kullan")
    assert_true(apply.get("ok"), "Soru kanıtı kullan butonu bulunamadı", apply)
    wait(500)
    applied = wait_for(
        window,
        "(() => ({ ok: (window.__trendyolSmokeCalls || []).some(call => call[0] === 'apply'), calls: window.__trendyolSmokeCalls || [] }))()",
    )
    checks.append({"name": "question_evidence_apply_hook_called", "status": "PASSED", "state": applied})

    match = click_by_text(window, "#trendyolSuggestionsList .trendyol-detail-actions button", "Ürün Eşleştir")
    assert_true(match.get("ok"), "Ürün Eşleştir butonu bulunamadı", match)
    wait(500)
    mapping = wait_for(
        window,
        """
        (() => ({
          ok: document.getElementById('trendyolTabMapping')?.classList.contains('active') && document.getElementById('trendyolMapBarcode')?.value === 'TY-SMOKE-001',
          barcode: document.getElementById('trendyolMapBarcode')?.value || '',
          imageUrl: document.getElementById('trendyolMapImageUrl')?.value || '',
          productName: document.getElementById('trendyolMapProductName')?.value || '',
          priorityRows: document.querySelectorAll('#trendyolMappingPriorityList .trendyol-mapping-priority-row').length,
          priorityText: document.getElementById('trendyolMappingPriorityList')?.innerText || ''
        }))()
        """,
    )
    assert_true(mapping["imageUrl"], "Ürün eşleştirme formuna görsel URL taşınmadı", mapping)
    assert_true(mapping["priorityRows"] >= 1, "Oncelikli eslesmeyen urun paneli render edilmedi", mapping)
    assert_true("Bugünkü hızlı kazanım" in mapping["priorityText"] and "Düşük güvenli AI" in mapping["priorityText"], "Oncelik paneli filtre ve operator raporu gostermedi", mapping)
    checks.append({"name": "product_match_form_prefilled_from_order_card", "status": "PASSED", "state": mapping})

    priority_filter = run_js(
        window,
        """
        (() => {
          setTrendyolMappingPriorityFilter('questions');
          const text = document.getElementById('trendyolMappingPriorityList')?.innerText || '';
          return {
            ok: text.includes('Görseli olanlar') && text.includes('TY-SMOKE-006'),
            text
          };
        })()
        """,
    )
    assert_true(priority_filter["ok"], "Oncelik paneli hizli filtreleri calismadi", priority_filter)
    checks.append({"name": "mapping_priority_filters_render_and_filter", "status": "PASSED", "state": {"text": priority_filter["text"][:500]}})
    run_js(window, "(() => { setTrendyolMappingPriorityFilter('all'); return { ok: true }; })()")

    priority_fill = run_js(
        window,
        """
        (() => {
          const button = document.querySelector('#trendyolMappingPriorityList .trendyol-mapping-priority-row button');
          if (!button) return { ok: false, error: 'priority button missing' };
          button.click();
          return {
            ok: document.getElementById('trendyolMapBarcode')?.value === 'TY-SMOKE-006',
            barcode: document.getElementById('trendyolMapBarcode')?.value || '',
            productName: document.getElementById('trendyolMapProductName')?.value || ''
          };
        })()
        """,
    )
    assert_true(priority_fill["ok"], "Oncelikli urun eslestirme butonu formu doldurmadi", priority_fill)
    checks.append({"name": "mapping_priority_prefills_form", "status": "PASSED", "state": priority_fill})

    mapping_save = run_js(
        window,
        """
        (() => {
          const model = document.getElementById('trendyolMapModelPath');
          if (model) model.value = 'templates/designs/01_a_gold.json';
          saveTrendyolMapping();
          const text = document.getElementById('trendyolMappingPriorityList')?.innerText || '';
          return {
            ok: !(text.includes('TY-SMOKE-006')),
            text,
            calls: window.__trendyolSmokeCalls || []
          };
        })()
        """,
    )
    assert_true(mapping_save["ok"], "Mapping kaydi sonrasi oncelik listesi aninda yenilenmedi", mapping_save)
    assert_true(any(call[0] == "mapping-save" for call in mapping_save["calls"]), "Mapping save hook cagrilmadi", mapping_save)
    checks.append({"name": "mapping_save_recalculates_priority_list", "status": "PASSED", "state": {"calls": mapping_save["calls"]}})

    run_js(window, "(() => { showTrendyolTab('orders', false); expandedTrendyolSuggestionId = 'ty-smoke-1'; updateTrendyolOrders(currentState.trendyol); return { ok: true }; })()")
    wait(500)
    verify = click_by_text(window, "#trendyolSuggestionsList .trendyol-detail-actions button", "Onayla ve Üretime Hazır Yap")
    assert_true(verify.get("ok"), "Doğrulama butonu bulunamadı", verify)
    ready = wait_for(
        window,
        """
        (() => {
          const row = currentState.trendyol.suggestions.find(item => item.id === 'ty-smoke-1');
          return { ok: row?.status === 'ready' && row?.user_verified === true, row, calls: window.__trendyolSmokeCalls || [] };
        })()
        """,
    )
    checks.append({"name": "verify_flow_marks_row_ready", "status": "PASSED", "state": {"calls": ready["calls"]}})

    import_click = click_by_text(window, "#trendyolSuggestionsList button", "Üretime Aktar")
    assert_true(import_click.get("ok"), "Üretime Aktar butonu çalışmadı", import_click)
    imported = wait_for(
        window,
        "(() => ({ ok: (window.__trendyolSmokeImported || []).includes('ty-smoke-1'), calls: window.__trendyolSmokeCalls || [] }))()",
    )
    checks.append({"name": "ready_row_imports_to_customer_order_hook", "status": "PASSED", "state": imported})

    run_js(window, "(() => { openTrendyolSuggestionInStudio('ty-smoke-1'); return { ok: true }; })()")
    studio = wait_for(
        window,
        """
        (() => ({
          ok: document.querySelector('.page.active')?.id === 'label' && document.getElementById('manualText')?.value === 'Bahar & Yunus',
          activePage: document.querySelector('.page.active')?.id || '',
          manualText: document.getElementById('manualText')?.value || '',
          manualNote: document.getElementById('manualNoteText')?.value || '',
          qty: document.getElementById('manualQty')?.value || ''
        }))()
        """,
    )
    assert_true(studio["manualNote"], "Studio'ya üretim notu taşınmadı", studio)
    checks.append({"name": "ready_row_opens_in_studio_with_fields", "status": "PASSED", "state": studio})
    screenshots["studio_from_trendyol"] = save_screenshot(window, "trendyol_studio_fields.png")

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots}


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1500, 950)
    window.show()
    wait(6500)
    try:
        result = run_gate(window)
    except Exception as exc:  # noqa: BLE001
        result = {"status": "FAILED", "message": str(exc)}
    finally:
        window.close()
        app.quit()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
