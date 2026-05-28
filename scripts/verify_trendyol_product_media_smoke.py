from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    node_code = r"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync('src/webui/app.js', 'utf8');
const fakeImg = { src: 'https://cdn.example.test/img.png', style: { display: 'none' } };
const fakePlaceholder = { style: { display: 'grid' } };
const fakeButton = {
  dataset: { trendyolThumbSource: 'https://cdn.example.test/img.png', trendyolRowId: 'row-1' },
  attrs: {},
  classList: { removed: [], added: [], add(v){ this.added.push(v); }, remove(v){ this.removed.push(v); } },
  querySelector(sel) { return sel.includes('img.order-product-thumb') ? fakeImg : fakePlaceholder; },
  setAttribute(k, v) { this.attrs[k] = v; },
};
let lastSelector = '';
const fakeDocument = {
  addEventListener() {},
  body: { classList: { add(){}, remove(){} }, insertAdjacentHTML() {}, appendChild() {} },
  getElementById() { return null; },
  querySelector() { return null; },
  querySelectorAll(sel) { lastSelector = sel; return sel.includes('#trendyolSuggestionsList') ? [fakeButton] : []; },
  createElement() { return { className:'', innerHTML:'', setAttribute(){}, querySelector(){return null}, querySelectorAll(){return []}, classList:{add(){},remove(){}} }; },
};
const context = {
  console,
  document: fakeDocument,
  window: { addEventListener(){}, removeEventListener(){}, open(){}, localStorage: { getItem(){return null}, setItem(){} } },
  localStorage: { getItem(){return null}, setItem(){} },
  navigator: {},
  setTimeout,
  clearTimeout,
  URL,
};
context.globalThis = context;
vm.createContext(context);
vm.runInContext(code, context);
context.rowOk = { product_name: 'Test Urun Yeni Model', productUrl: '/test-urun-yeni-model-p-123', barcode: 'ABC', merchant_sku: 'SKU' };
context.rowWrongSource = { product_name: 'Test Urun Yeni Model', product_url: 'https://www.trendyol.com/test-urun-yeni-model-p-123', product_url_source: 'catalog_name' };
context.rowWrongPath = { product_name: 'Test Urun Yeni Model', productUrl: 'https://www.trendyol.com/baska-urun-p-999' };
context.rowTurkishSplitSlug = { product_name: '41’li Kırmızı Kızİsteme Çiçeği ve 80 Adet Söz Çikolatası', productUrl: 'https://www.trendyol.com/cyz-home/41-li-kirmizi-kizi-steme-c-ic-eg-i-ve-80-adet-so-z-c-ikolatasi-p-1059321613' };
context.rowImage = { id: 'img1', product_name: 'Image Product', image_url: 'https://cdn.example.test/img.png' };
const checks = [];
function check(name, value) { checks.push({ name, value: Boolean(value) }); if (!value) throw new Error(name); }
check('relative Trendyol URL normalized', vm.runInContext("safeExternalUrl('/magaza/urun-p-123')", context) === 'https://www.trendyol.com/magaza/urun-p-123');
check('matching product title link kept', vm.runInContext('getTrendyolProductUrl(rowOk)', context) === 'https://www.trendyol.com/test-urun-yeni-model-p-123');
check('fuzzy catalog URL rejected', vm.runInContext('getTrendyolProductUrl(rowWrongSource)', context) === '');
check('nonmatching product URL rejected', vm.runInContext('getTrendyolProductUrl(rowWrongPath)', context) === '');
check('Turkish split slug product URL kept', vm.runInContext('getTrendyolProductUrl(rowTurkishSplitSlug)', context) === 'https://www.trendyol.com/cyz-home/41-li-kirmizi-kizi-steme-c-ic-eg-i-ve-80-adet-so-z-c-ikolatasi-p-1059321613');
const thumb = vm.runInContext('trendyolProductThumb(rowImage)', context);
check('thumbnail renders img', thumb.includes('order-product-thumb'));
check('thumbnail not initials avatar', !thumb.includes('trendyol-avatar'));
context.cacheCalls = [];
vm.runInContext(`bridge = { cache_trendyol_product_image(source, cb) { cacheCalls.push(source); cb(JSON.stringify({ status: 'OK', preview_url: 'file:///cached-thumb.png' })); } }`, context);
vm.runInContext('hydrateTrendyolProductThumbs()', context);
check('hydrate uses suggestions list selector', lastSelector.includes('#trendyolSuggestionsList'));
check('hydrate calls image cache bridge', context.cacheCalls[0] === 'https://cdn.example.test/img.png');
check('hydrate replaces thumbnail with cached preview', fakeImg.src === 'file:///cached-thumb.png');
check('hydrate restores modal click', String(fakeButton.attrs.onclick || '').includes('openProductImageModal'));
console.log(JSON.stringify({ status: 'PASSED', checks }, null, 2));
"""
    completed = subprocess.run(
        ["node", "-e", textwrap.dedent(node_code)],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    print(completed.stdout.strip())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
