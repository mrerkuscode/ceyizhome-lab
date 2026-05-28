from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TODAY = datetime.now().strftime("%Y-%m-%d")
OUTPUT_DIR = PROJECT_ROOT / "output" / TODAY / "project_code_audit"
JSON_REPORT = OUTPUT_DIR / "PROJECT_CODE_AUDIT.json"
MD_REPORT = OUTPUT_DIR / "PROJECT_CODE_AUDIT.md"

ACTIVE_UI = [
    PROJECT_ROOT / "src" / "webui" / "index.html",
    PROJECT_ROOT / "src" / "webui" / "app.js",
    PROJECT_ROOT / "src" / "webui" / "styles.css",
]
BACKEND_MODULES = [
    PROJECT_ROOT / "src" / "webui_backend" / "bridge.py",
    PROJECT_ROOT / "src" / "webui_backend" / "trendyol_api.py",
    PROJECT_ROOT / "src" / "webui_backend" / "bulk_label_api.py",
    PROJECT_ROOT / "src" / "webui_backend" / "combined_production_api.py",
    PROJECT_ROOT / "src" / "label_designer" / "renderer.py",
    PROJECT_ROOT / "src" / "laser_nesting.py",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def line_matches(path: Path, pattern: str) -> list[dict[str, Any]]:
    regex = re.compile(pattern, re.I)
    matches: list[dict[str, Any]] = []
    for index, line in enumerate(read(path).splitlines(), start=1):
        if regex.search(line):
            matches.append(
                {
                    "file": str(path.relative_to(PROJECT_ROOT)),
                    "line": index,
                    "text": line.strip()[:220],
                }
            )
    return matches


def count_js_functions(source: str) -> int:
    return len(re.findall(r"\bfunction\s+[A-Za-z0-9_]+\s*\(", source))


def extract_bridge_slots(source: str) -> list[str]:
    names = re.findall(r"\n\s+def\s+([a-zA-Z0-9_]+)\s*\(", source)
    return [name for name in names if not name.startswith("_")]


def package_scripts() -> dict[str, str]:
    try:
        return json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8")).get("scripts", {})
    except Exception:
        return {}


def audit() -> dict[str, Any]:
    html = read(ACTIVE_UI[0])
    js = read(ACTIVE_UI[1])
    css = read(ACTIVE_UI[2])
    bridge = read(PROJECT_ROOT / "src" / "webui_backend" / "bridge.py")
    css_patterns = {
        "w_screen_like": r"\b100vw\b|\bw-screen\b",
        "overflow_hidden": r"overflow\s*:\s*hidden|overflow-x\s*:\s*hidden",
        "large_min_width": r"min-width\s*:\s*(?:[8-9]\d{2}|[1-9]\d{3,})px",
        "max_width_constraints": r"max-width\s*:",
        "media_queries": r"@media\s*\(",
    }
    css_findings = {name: line_matches(ACTIVE_UI[2], pattern) for name, pattern in css_patterns.items()}
    js_markers = {
        "trendyol_render_limit": "TRENDYOL_ORDER_RENDER_LIMIT" in js,
        "bulk_gallery": "function renderBulkGallery" in js,
        "name_cut_rdworks": "function renderNameCutStudioSummary" in js and "nameCutLayoutConfig" in js,
        "debounced_inputs": "function debounceRender" in js and "scheduleTrendyolOrdersUpdate" in js,
        "layout_learning": "LAYOUT_LEARNING_STORAGE_KEY" in js,
    }
    backend_features = {
        "trendyol_sync": "def sync_recent_orders" in read(PROJECT_ROOT / "src" / "webui_backend" / "trendyol_api.py"),
        "trendyol_questions": "def sync_questions" in read(PROJECT_ROOT / "src" / "webui_backend" / "trendyol_api.py"),
        "bulk_gallery_backend": "def bulk_gallery_items" in read(PROJECT_ROOT / "src" / "webui_backend" / "bulk_label_api.py"),
        "name_cut_export": "def export_name_cut_batch" in read(PROJECT_ROOT / "src" / "webui_backend" / "combined_production_api.py"),
        "layout_learning_engine": (PROJECT_ROOT / "src" / "intelligence" / "layout_learning_engine.py").exists(),
    }
    scripts = package_scripts()
    module_sizes = {
        str(path.relative_to(PROJECT_ROOT)): path.stat().st_size
        for path in [*ACTIVE_UI, *BACKEND_MODULES]
        if path.exists()
    }
    risk_counter = Counter()
    for name, matches in css_findings.items():
        if name != "media_queries":
            risk_counter[name] = len(matches)
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "architecture": {
            "active_ui": [str(path.relative_to(PROJECT_ROOT)) for path in ACTIVE_UI],
            "legacy_ui_marker": (PROJECT_ROOT / "src" / "desktop" / "web_ui" / "LEGACY_NOT_USED.md").exists(),
            "webview_entrypoint": "src/desktop/web_main_window.py loads src/webui/index.html",
            "frontend_stack": "Vanilla JS/CSS inside PySide6 WebEngine WebView",
            "backend_stack": "Python service modules exposed to JS through Qt WebChannel bridge",
        },
        "package_scripts": scripts,
        "missing_standard_scripts": [name for name in ["build", "lint", "typecheck"] if name not in scripts],
        "module_sizes_bytes": module_sizes,
        "frontend": {
            "html_bytes": len(html),
            "js_bytes": len(js),
            "css_bytes": len(css),
            "js_function_count": count_js_functions(js),
            "media_query_count": len(css_findings["media_queries"]),
            "markers": js_markers,
        },
        "backend": {
            "bridge_slot_count": len(extract_bridge_slots(bridge)),
            "bridge_slots_sample": extract_bridge_slots(bridge)[:80],
            "features": backend_features,
        },
        "layout_risks": {
            "counts": dict(risk_counter),
            "examples": {key: value[:12] for key, value in css_findings.items() if key != "media_queries"},
        },
        "performance_risks": [
            {
                "area": "src/webui/app.js",
                "risk": "Large monolithic UI file; expensive list render paths must stay capped/debounced.",
                "mitigation": "Trendyol order list is capped; Trendyol and bulk gallery text search now use debounced input render.",
            },
            {
                "area": "Bulk gallery",
                "risk": "Verification currently expects 100 gallery cards; full virtualization needs test contract update first.",
                "mitigation": "Keep existing card behavior for compatibility; use filters/search and future virtual-grid migration.",
            },
            {
                "area": "Long backend jobs",
                "risk": "Trendyol sync, Excel render and laser export can be long-running.",
                "mitigation": "Existing health gates separate quick/long profiles; future queue/job progress should move heavy work off direct UI callbacks.",
            },
        ],
    }


def write_reports(payload: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Project Code Audit",
        "",
        f"Created: {payload['created_at']}",
        "",
        "## Architecture",
        "",
        f"- Active UI: `{', '.join(payload['architecture']['active_ui'])}`",
        f"- WebView entrypoint: `{payload['architecture']['webview_entrypoint']}`",
        f"- Frontend: {payload['architecture']['frontend_stack']}",
        f"- Backend: {payload['architecture']['backend_stack']}",
        f"- Legacy UI marker exists: `{payload['architecture']['legacy_ui_marker']}`",
        "",
        "## Scripts",
        "",
        f"- Available npm scripts: `{', '.join(sorted(payload['package_scripts'].keys()))}`",
        f"- Missing standard scripts: `{', '.join(payload['missing_standard_scripts']) or 'none'}`",
        "",
        "## Frontend",
        "",
        f"- JS functions: `{payload['frontend']['js_function_count']}`",
        f"- CSS media queries: `{payload['frontend']['media_query_count']}`",
        f"- Debounced production searches: `{payload['frontend']['markers']['debounced_inputs']}`",
        f"- Trendyol render cap present: `{payload['frontend']['markers']['trendyol_render_limit']}`",
        f"- Layout learning marker present: `{payload['frontend']['markers']['layout_learning']}`",
        "",
        "## Backend",
        "",
        f"- Bridge slot count: `{payload['backend']['bridge_slot_count']}`",
        f"- Trendyol sync present: `{payload['backend']['features']['trendyol_sync']}`",
        f"- Bulk gallery backend present: `{payload['backend']['features']['bulk_gallery_backend']}`",
        f"- Name cut export present: `{payload['backend']['features']['name_cut_export']}`",
        "",
        "## Layout Risk Counts",
        "",
    ]
    for key, value in payload["layout_risks"]["counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Performance Notes", ""])
    for item in payload["performance_risks"]:
        lines.append(f"- **{item['area']}**: {item['risk']} Mitigation: {item['mitigation']}")
    lines.extend(["", "JSON report:", "", f"`{JSON_REPORT}`"])
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    payload = audit()
    write_reports(payload)
    print(
        json.dumps(
            {
                "status": "OK",
                "json_report": str(JSON_REPORT),
                "markdown_report": str(MD_REPORT),
                "missing_standard_scripts": payload["missing_standard_scripts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
