from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TODAY = datetime.now().strftime("%Y-%m-%d")
REPORT_DIR = PROJECT_ROOT / "output" / TODAY / "project_health"
JSON_REPORT = REPORT_DIR / "PROJECT_HEALTH_AUDIT.json"
MD_REPORT = REPORT_DIR / "PROJECT_HEALTH_AUDIT.md"
ACTIVE_UI = [
    PROJECT_ROOT / "src" / "webui" / "index.html",
    PROJECT_ROOT / "src" / "webui" / "app.js",
    PROJECT_ROOT / "src" / "webui" / "styles.css",
]
LEGACY_UI = PROJECT_ROOT / "src" / "desktop" / "web_ui"


@dataclass
class CommandSpec:
    name: str
    command: list[str]
    timeout: int = 180


def profiles(python: str) -> dict[str, list[CommandSpec]]:
    trendyol_core = [
        CommandSpec("trendyol_order_to_production", [python, "scripts\\verify_trendyol_order_to_production_flow.py"], 120),
        CommandSpec("trendyol_mapping_review", [python, "scripts\\verify_trendyol_mapping_review_workflow.py"], 120),
        CommandSpec("trendyol_ai_question_extraction", [python, "scripts\\verify_trendyol_ai_question_extraction_flow.py"], 120),
        CommandSpec("trendyol_product_media_smoke", [python, "scripts\\verify_trendyol_product_media_smoke.py"], 60),
    ]
    trendyol = [
        *trendyol_core,
        CommandSpec("trendyol_real_user_smoke", [python, "scripts\\verify_trendyol_real_user_smoke.py"], 120),
    ]
    trendyol_live_audit = [
        CommandSpec("trendyol_live_data_audit", [python, "scripts\\audit_trendyol_live_data_quality.py"], 120),
    ]
    trendyol_operator_worklist = [
        CommandSpec("trendyol_operator_worklist", [python, "scripts\\prepare_trendyol_operator_worklist.py"], 120),
    ]
    release = [
        CommandSpec("rdworks_name_cut_layout_export", [python, "scripts\\verify_rdworks_name_cut_layout_export.py"], 180),
        CommandSpec("real_production_quality_gate", [python, "scripts\\real_production_quality_gate.py"], 180),
        CommandSpec("final_acceptance_gate", [python, "scripts\\final_acceptance_gate.py"], 180),
        CommandSpec("final_release_package_gate", [python, "scripts\\final_release_package_gate.py"], 180),
    ]
    quick = [
        CommandSpec("active_webui_syntax", ["node", "--check", "src\\webui\\app.js"], 60),
        CommandSpec("legacy_webui_syntax", ["node", "--check", "src\\desktop\\web_ui\\app.js"], 60),
        CommandSpec("pytest", [python, "-m", "pytest", "-q"], 180),
        CommandSpec("extraction_eval", [python, "scripts\\run_extraction_eval.py"], 120),
        *trendyol_core,
    ]
    return {
        "quick": quick,
        "trendyol": trendyol,
        "trendyol-live-audit": trendyol_live_audit,
        "trendyol-operator-worklist": trendyol_operator_worklist,
        "release": release,
        "all": [*quick, *release],
    }


def run_command(spec: CommandSpec) -> dict[str, Any]:
    started = datetime.now()
    try:
        completed = subprocess.run(
            spec.command,
            cwd=PROJECT_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=spec.timeout,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )
        timed_out = False
        output = completed.stdout or ""
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        output += f"\nTIMEOUT after {spec.timeout}s"
        returncode = 124
    finished = datetime.now()
    return {
        "name": spec.name,
        "command": spec.command,
        "returncode": returncode,
        "timed_out": timed_out,
        "timeout_seconds": spec.timeout,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "duration_seconds": round((finished - started).total_seconds(), 2),
        "status": "PASSED" if returncode == 0 else "FAILED",
        "tail": tail(output),
    }


def tail(text: str, limit: int = 2500) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else "..." + text[-limit:]


def dependency_status(python: str) -> dict[str, Any]:
    code = "import json\nmods=['pyclipper','pandas','openpyxl','PySide6','fontTools']\nresult={}\nfor m in mods:\n    try:\n        mod=__import__(m); result[m]={'status':'OK','version':getattr(mod,'__version__','')}\n    except Exception as e:\n        result[m]={'status':'MISSING','error':str(e)}\nprint(json.dumps(result, ensure_ascii=False))"
    completed = subprocess.run([python, "-c", code], cwd=PROJECT_ROOT, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        return json.loads(completed.stdout.strip())
    except json.JSONDecodeError:
        return {"status": "ERROR", "output": completed.stdout}


def ui_status() -> dict[str, Any]:
    return {
        "active_entrypoint": [str(path.relative_to(PROJECT_ROOT)) for path in ACTIVE_UI],
        "active_files_exist": all(path.exists() for path in ACTIVE_UI),
        "legacy_folder": str(LEGACY_UI.relative_to(PROJECT_ROOT)),
        "legacy_exists": LEGACY_UI.exists(),
        "legacy_marker_exists": (LEGACY_UI / "LEGACY_NOT_USED.md").exists(),
        "note": "Current desktop WebView loads src/webui from src/desktop/web_main_window.py.",
    }


def trendyol_debug_status() -> dict[str, Any]:
    path = PROJECT_ROOT / "logs" / "trendyol_extraction_debug.jsonl"
    if not path.exists():
        return {"exists": False, "path": str(path.relative_to(PROJECT_ROOT))}
    stat = path.stat()
    last_line = ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        last_line = lines[-1] if lines else ""
    except Exception as exc:
        last_line = f"read_error: {exc}"
    return {
        "exists": True,
        "path": str(path.relative_to(PROJECT_ROOT)),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "last_line_tail": tail(last_line, 800),
    }


def write_reports(payload: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Project Health Audit",
        "",
        f"Created: {payload['created_at']}",
        f"Profile: `{payload['profile']}`",
        f"Status: `{payload['status']}`",
        "",
        "## Commands",
        "",
    ]
    lines.append(f"Total command time: `{payload.get('total_duration_seconds', 0)}s`")
    lines.append("")
    for result in payload["commands"]:
        lines.append(f"- `{result['name']}`: `{result['status']}` ({result['duration_seconds']}s)")
    slowest = payload.get("slowest_commands") or []
    if slowest:
        lines.extend(["", "## Slowest Gates", ""])
        lines.extend(f"- `{item['name']}`: `{item['duration_seconds']}s`" for item in slowest)
    lines.extend(
        [
            "",
            "## Environment",
            "",
            f"- Python: `{payload['python']}`",
            f"- Active UI exists: `{payload['ui']['active_files_exist']}`",
            f"- Legacy marker exists: `{payload['ui']['legacy_marker_exists']}`",
            f"- Trendyol debug log exists: `{payload['trendyol_debug']['exists']}`",
            "",
            "JSON report:",
            "",
            f"`{JSON_REPORT}`",
        ]
    )
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["quick", "trendyol", "trendyol-live-audit", "trendyol-operator-worklist", "release", "all"], default="quick")
    args = parser.parse_args()
    python = sys.executable
    selected = profiles(python)[args.profile]
    command_results = [run_command(spec) for spec in selected]
    failed = [result["name"] for result in command_results if result["status"] != "PASSED"]
    total_duration = round(sum(float(result.get("duration_seconds") or 0) for result in command_results), 2)
    slowest = sorted(command_results, key=lambda item: float(item.get("duration_seconds") or 0), reverse=True)[:5]
    payload = {
        "status": "PASSED" if not failed else "FAILED",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "profile": args.profile,
        "python": python,
        "commands": command_results,
        "failed_commands": failed,
        "total_duration_seconds": total_duration,
        "slowest_commands": [{"name": item["name"], "duration_seconds": item["duration_seconds"], "status": item["status"]} for item in slowest],
        "dependencies": dependency_status(python),
        "ui": ui_status(),
        "trendyol_debug": trendyol_debug_status(),
    }
    write_reports(payload)
    print(json.dumps({"status": payload["status"], "profile": args.profile, "failed_commands": failed, "json_report": str(JSON_REPORT), "markdown_report": str(MD_REPORT)}, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
