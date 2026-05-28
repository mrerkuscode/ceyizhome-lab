"""Full regression suite for product_definitions_api (6 scenarios + audit + cleanup)."""
import sys
import json
from pathlib import Path

sys.path.insert(0, 'src')

from webui_backend import product_definitions_api as pda

ROOT = Path('.')

print('=== PRODUCT DEFINITIONS — FULL REGRESSION ===')
print()

# --- Scenario 1: Manual create ---
print('SCENARIO 1: Manual create')
r1 = pda.api_save(ROOT, {
    'sku': 'MAN-001',
    'product_name': '10 kisilik soz cikolatasi',
    'name_config': {'type': 'couple', 'count': 1, 'size_group': 'auto', 'compound_format': 'joined', 'test_name': 'Ayse Mehmet'},
    'label_config': {'enabled': True, 'model': 'soz_3', 'default_count': 10, 'adjustable_in_production': True, 'min_count': 5, 'max_count': 20},
    'extras': {'production_notes': 'Test entry', 'special_requests_allowed': True},
    'metadata': {'source': 'test_manual'}
})
msg = r1['message'].encode('ascii', 'replace').decode()
print(f'  -> {r1["status"]}: {msg}')
assert r1['status'] == 'OK'

# --- Scenario 2: Excel bulk import ---
print()
print('SCENARIO 2: Excel bulk import')
xlsx = 'output/2026-05-28/product_definitions_system/proofs/test_products.xlsx'
r2_dry = pda.api_import_excel(ROOT, xlsx, dry_run=True)
print(f'  DRY-RUN: added={r2_dry["added"]}, updated={r2_dry["updated"]}, errors={len(r2_dry["errors"])}')
for err in r2_dry['errors'][:5]:
    msg = err['error'].encode('ascii', 'replace').decode()
    print(f'    row={err["row"]}, sku={err["sku"]!r}: {msg[:80]}')

print('  Actual import:')
r2 = pda.api_import_excel(ROOT, xlsx, dry_run=False)
print(f'  -> added={r2["added"]}, updated={r2["updated"]}, errors={len(r2["errors"])}')
assert r2['added'] >= 5, f'expected at least 5 added, got {r2["added"]}'

# --- Scenario 3: Edit existing ---
print()
print('SCENARIO 3: Edit existing (TRY-001 update)')
r3 = pda.api_save(ROOT, {
    'sku': 'TRY-001',
    'product_name': 'PREMIUM 10 kisilik set',
    'name_config': {'type': 'couple', 'count': 1, 'size_group': 'auto', 'compound_format': 'joined', 'test_name': ''},
    'label_config': {'enabled': True, 'model': 'soz_3', 'default_count': 12, 'adjustable_in_production': True, 'min_count': 8, 'max_count': 24},
    'extras': {'production_notes': 'Updated', 'special_requests_allowed': True},
    'metadata': {}
})
print(f'  -> {r3["status"]} (created={r3.get("created")})')
assert r3['status'] == 'OK' and r3['created'] is False

# --- Scenario 4: Archive (soft delete) ---
print()
print('SCENARIO 4: Archive soft delete')
r4 = pda.api_archive(ROOT, 'TRY-002')
print(f'  -> {r4["status"]}')
r4_check = pda.api_get(ROOT, 'TRY-002')
print(f'  After archive: status={r4_check["status"]}, def.metadata.status={r4_check["definition"]["metadata"]["status"]}')
assert r4_check['definition']['metadata']['status'] == 'archived'

# --- Scenario 5: Search ---
print()
print('SCENARIO 5: Search')
r5 = pda.api_search(ROOT, 'kisilik')
print(f'  search "kisilik": {r5["count"]} hits')
r5b = pda.api_search(ROOT, 'TRY-00')
print(f'  search "TRY-00": {r5b["count"]} hits')
r5c = pda.api_search(ROOT, 'PREMIUM')
print(f'  search "PREMIUM": {r5c["count"]} hits')
assert r5c['count'] >= 1

# --- Scenario 6: DXF integration ---
print()
print('SCENARIO 6: DXF library integration')

def resolve(test_name):
    return pda.api_resolve_size_group(ROOT, {
        'sku': 'T', 'product_name': 'X',
        'name_config': {'type': 'single', 'count': 1, 'size_group': 'auto', 'compound_format': 'joined', 'test_name': test_name},
        'label_config': {'enabled': False},
        'metadata': {}
    })

r6a = resolve('Ada')           # 3 letters -> 70x40
r6b = resolve('Mucahit')       # 7 letters -> 80x40
r6c = resolve('Muhammed Ali')  # 11 letters -> 100x40
r6d = resolve('Umit')          # In DXF library
r6e = resolve('X-Unknown')

print(f'  3-letter Ada:  {r6a["resolution"]["effective"]} (exp 70x40)')
print(f'  7-letter Mucahit: {r6b["resolution"]["effective"]} (exp 80x40)')
print(f'  11-letter Muhammed Ali: {r6c["resolution"]["effective"]} (exp 100x40)')
print(f'  DXF lookup Umit: found={r6d["resolution"]["dxf_status"]["found"]} (exp True)')
print(f'  DXF lookup X-Unknown: found={r6e["resolution"]["dxf_status"]["found"]} (exp False)')

assert r6a['resolution']['effective'] == '70x40'
assert r6b['resolution']['effective'] == '80x40'
assert r6c['resolution']['effective'] == '100x40'
assert r6d['resolution']['dxf_status']['found'] is True
assert r6e['resolution']['dxf_status']['found'] is False

# --- Sahte success check (validation must reject) ---
print()
print('SAHTE BASARI KONTROLU:')
r_bad = pda.api_save(ROOT, {
    'sku': 'BAD-TEST',
    'product_name': '',  # empty
    'name_config': {'type': 'couple', 'count': 0, 'size_group': 'auto', 'compound_format': 'joined'},  # invalid
    'label_config': {'enabled': True, 'model': '', 'default_count': 10},  # enabled with no model
    'metadata': {}
})
print(f'  Invalid save -> {r_bad["status"]} (expected VALIDATION_ERROR)')
print(f'  Errors: {len(r_bad.get("errors", []))}')
for e in r_bad.get('errors', [])[:5]:
    print(f'    - {e.encode("ascii", "replace").decode()[:80]}')
assert r_bad['status'] == 'VALIDATION_ERROR'

# --- Audit log ---
print()
print('AUDIT LOG:')
audit_path = Path('data/product_definitions_audit_log.jsonl')
assert audit_path.exists(), 'audit log missing'
lines = audit_path.read_text(encoding='utf-8').strip().split('\n')
print(f'  Audit entries: {len(lines)}')
last = json.loads(lines[-1])
print(f'  Last: action={last["action"]}, sku={last["sku"]}')

# --- Regression: external invariants ---
print()
print('REGRESSION:')
ref_lib = json.loads(Path('assets/references/corel_name_reference_library.json').read_text(encoding='utf-8'))
ref_count = len(ref_lib.get('references') or []) if isinstance(ref_lib, dict) else len(ref_lib)
print(f'  corel ref library: {ref_count} entries (exp 167)')
assert ref_count == 167

from webui_backend.dxf_library_api import scan_library
dxf_result = scan_library(Path('.'))
print(f'  DXF library scan: {dxf_result["scanned"]} entries (exp >= 2)')
assert dxf_result['scanned'] >= 2

from webui_backend.trendyol_api import _is_verified_ready
sug = json.loads(Path('data/trendyol_production_suggestions.json').read_text(encoding='utf-8'))
approved = [r for r in sug if _is_verified_ready(r)]
print(f'  Trendyol approved rows: {len(approved)} (exp >= 1)')
assert len(approved) >= 1

# --- Summary ---
print()
s = pda.summary(ROOT)
print(f'SUMMARY: total={s["total"]}, active={s["active"]}, archived={s["archived"]}, by_type={s["by_name_type"]}, with_label={s["with_label"]}')

# --- Cleanup ---
print()
print('CLEANUP:')
db_path = Path('data/product_definitions.json')
db = json.loads(db_path.read_text(encoding='utf-8'))
removed = 0
for sku in list(db.get('definitions', {}).keys()):
    if sku.startswith('TRY-00') or sku.startswith('MAN-') or sku.startswith('BAD-'):
        db['definitions'].pop(sku, None)
        removed += 1
db['total_count'] = 0
db_path.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'  Removed {removed} test entries')

print()
print('=== ALL 6 SCENARIOS PASS ===')
