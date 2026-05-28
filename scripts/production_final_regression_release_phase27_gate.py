from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-05-23"
OUTPUT_DIR = PROJECT_ROOT / "output" / DAY / "production_final_regression_release_phase27"
RESULT_PATH = OUTPUT_DIR / "production_final_regression_release_phase27_gate_result.json"
PHASE26_SCREENSHOT_DIR = PROJECT_ROOT / "output" / "2026-05-22" / "production_final_ui_sidebar_phase26"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


GATE_SCRIPTS = [
    "scripts/production_final_ui_sidebar_phase26_gate.py",
    "scripts/production_live_integration_dryrun_phase25_gate.py",
    "scripts/production_backup_restore_phase24_gate.py",
    "scripts/production_printer_profile_manual_phase23_gate.py",
    "scripts/production_trendyol_readonly_api_phase22_gate.py",
    "scripts/production_namecut_rdworks_export_phase21_gate.py",
    "scripts/production_label_studio_output_model_phase20_gate.py",
    "scripts/production_real_user_e2e_phase19_gate.py",
    "scripts/production_trendyol_evidence_drawer_phase18_gate.py",
    "scripts/production_trendyol_bulk_import_phase17_gate.py",
    "scripts/production_audit_deeplink_phase16_gate.py",
    "scripts/production_audit_append_export_phase15_gate.py",
    "scripts/production_audit_center_phase14_gate.py",
    "scripts/production_print_queue_hardening_phase13_gate.py",
    "scripts/production_label_studio_integration_phase12_gate.py",
    "scripts/production_namecut_safe_export_phase11_gate.py",
    "scripts/production_namecut_single_piece_quality_phase10_gate.py",
    "scripts/production_namecut_queue_persistence_phase9_gate.py",
    "scripts/production_bulk_laser_queue_phase8_gate.py",
    "scripts/production_bulk_performance_phase7_gate.py",
    "scripts/production_bulk_queue_integration_phase6_gate.py",
]

BUILD_COMMANDS = [
    ["node", "--check", "src/webui/app.js"],
    ["npm", "run", "test"],
    ["npm", "run", "build", "--if-present"],
    ["npm", "run", "lint", "--if-present"],
    ["npm", "run", "typecheck", "--if-present"],
]

DOC_FILES = [
    "docs/OPERATOR_UAT_CHECKLIST.md",
    "docs/OPERATOR_GUIDE.md",
    "docs/TECHNICAL_MAINTENANCE.md",
    "docs/PRODUCTION_SAFETY_RULES.md",
    "docs/RELEASE_NOTES.md",
    "docs/KNOWN_ISSUES.md",
]

SCREENSHOT_MAP = {
    "dashboard-1366.png": "dashboard-1366.png",
    "bulk-production-1366.png": "bulk-production-1366.png",
    "label-studio-1366.png": "label-studio-1366.png",
    "trendyol-orders-1366.png": "trendyol-1366.png",
    "print-queue-1366.png": "print-queue-1366.png",
    "namecut-1366.png": "namecut-1366.png",
    "production-audit-1366.png": "production-audit-1366.png",
    "settings-integrations-1366.png": "settings-integrations-1366.png",
    "data-maintenance-1366.png": "data-maintenance-1366.png",
    "sidebar-collapsed-1366.png": "sidebar-collapsed-1366.png",
    "sidebar-hover-expanded-1366.png": "sidebar-hover-expanded-1366.png",
    "dashboard-1920.png": "dashboard-1920.png",
    "bulk-production-1920.png": "bulk-production-1920.png",
    "label-studio-1920.png": "label-studio-1920.png",
    "trendyol-orders-1920.png": "trendyol-1920.png",
    "print-queue-1920.png": "print-queue-1920.png",
    "namecut-1920.png": "namecut-1920.png",
    "production-audit-1920.png": "production-audit-1920.png",
    "settings-integrations-1920.png": "settings-integrations-1920.png",
    "data-maintenance-1920.png": "data-maintenance-1920.png",
    "sidebar-open-1920.png": "sidebar-open-1920.png",
}


def command_to_text(command: list[str]) -> str:
    return " ".join(command)


def run_command(command: list[str], timeout: int) -> dict[str, object]:
    started = time.time()
    command_text = command_to_text(command)
    try:
        completed = subprocess.run(
            command_text,
            cwd=PROJECT_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            shell=True,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return {
            "command": command_to_text(command),
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "returncode": completed.returncode,
            "duration_seconds": round(time.time() - started, 2),
            "stdout_tail": stdout[-6000:],
            "stderr_tail": stderr[-6000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command_text,
            "status": "TIMEOUT",
            "returncode": None,
            "duration_seconds": round(time.time() - started, 2),
            "stdout_tail": (exc.stdout or "")[-6000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-6000:] if isinstance(exc.stderr, str) else "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "command": command_text,
            "status": "ERROR",
            "returncode": None,
            "duration_seconds": round(time.time() - started, 2),
            "stdout_tail": "",
            "stderr_tail": str(exc),
        }


def run_gate(script: str) -> dict[str, object]:
    path = PROJECT_ROOT / script
    if not path.exists():
        return {
            "script": script,
            "status": "MISSING",
            "returncode": None,
            "duration_seconds": 0,
            "stdout_tail": "",
            "stderr_tail": "",
        }
    result = run_command([sys.executable, script], timeout=420)
    result["script"] = script
    return result


def collect_screenshots() -> dict[str, object]:
    screenshot_dir = OUTPUT_DIR / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    missing: list[str] = []
    for source_name, target_name in SCREENSHOT_MAP.items():
        source = PHASE26_SCREENSHOT_DIR / source_name
        target = screenshot_dir / target_name
        if source.exists():
            shutil.copy2(source, target)
            copied[target_name] = str(target)
        else:
            missing.append(str(source))
    return {"count": len(copied), "copied": copied, "missing": missing}


def inspect_docs() -> dict[str, object]:
    rows = []
    for doc in DOC_FILES:
        path = PROJECT_ROOT / doc
        rows.append(
            {
                "path": doc,
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
            }
        )
    return {
        "required_count": len(DOC_FILES),
        "existing_count": sum(1 for row in rows if row["exists"]),
        "rows": rows,
    }


def inspect_known_issues() -> list[str]:
    path = PROJECT_ROOT / "docs" / "KNOWN_ISSUES.md"
    if not path.exists():
        return ["docs/KNOWN_ISSUES.md bulunamadı."]
    text = path.read_text(encoding="utf-8")
    issues = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            issues.append(stripped[2:])
    return issues


def safety_summary(gate_results: list[dict[str, object]]) -> dict[str, object]:
    blob = "\n".join(
        f"{row.get('stdout_tail', '')}\n{row.get('stderr_tail', '')}" for row in gate_results
    ).lower()
    forbidden_success_markers = [
        "auto_print_started\": true",
        "laser_started\": true",
        "rdworks_started\": true",
        "trendyol_live_status_changed\": true",
        "live_action_performed\": true",
        "shipping_label_created\": true",
        "invoice_created\": true",
    ]
    hits = [marker for marker in forbidden_success_markers if marker in blob]
    return {
        "passed": not hits,
        "forbidden_markers": hits,
        "printer_auto_started": False,
        "laser_auto_started": False,
        "rdworks_auto_started": False,
        "trendyol_live_action": False,
        "dry_run_manual_guard_required": True,
    }


def release_score(gate_results: list[dict[str, object]], build_results: list[dict[str, object]], docs: dict[str, object], screenshots: dict[str, object], safety: dict[str, object]) -> dict[str, object]:
    total_gates = len(gate_results)
    passed_gates = sum(1 for row in gate_results if row["status"] == "PASS")
    existing_docs = int(docs["existing_count"])
    screenshot_count = int(screenshots["count"])
    build_passed = all(row["status"] == "PASS" for row in build_results)
    score = 0
    if total_gates:
        score += round((passed_gates / total_gates) * 50)
    score += 20 if build_passed else 0
    score += round((existing_docs / len(DOC_FILES)) * 15)
    score += 10 if screenshot_count >= 20 else round((screenshot_count / 20) * 10)
    score += 5 if safety.get("passed") else 0
    status = "READY_CANDIDATE" if score >= 90 and build_passed and passed_gates == total_gates and safety.get("passed") else "NEEDS_REVIEW"
    return {
        "score": min(score, 100),
        "status": status,
        "passed_gates": passed_gates,
        "total_gates": total_gates,
        "build_passed": build_passed,
        "docs_existing": existing_docs,
        "screenshots": screenshot_count,
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().isoformat(timespec="seconds")
    gate_results = [run_gate(script) for script in GATE_SCRIPTS]
    build_results = [run_command(command, timeout=300) for command in BUILD_COMMANDS]
    screenshots = collect_screenshots()
    docs = inspect_docs()
    known_issues = inspect_known_issues()
    safety = safety_summary(gate_results + build_results)
    score = release_score(gate_results, build_results, docs, screenshots, safety)
    missing = [row for row in gate_results if row["status"] == "MISSING"]
    failed = [row for row in gate_results + build_results if row["status"] not in {"PASS"}]
    result = {
        "phase": 27,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "started_at": started_at,
        "status": "PASS" if not missing and not failed and safety["passed"] else "FAIL",
        "gate_summary": {
            "total": len(gate_results),
            "passed": sum(1 for row in gate_results if row["status"] == "PASS"),
            "failed": sum(1 for row in gate_results if row["status"] == "FAIL"),
            "timeout": sum(1 for row in gate_results if row["status"] == "TIMEOUT"),
            "missing": sum(1 for row in gate_results if row["status"] == "MISSING"),
        },
        "build_summary": {
            "total": len(build_results),
            "passed": sum(1 for row in build_results if row["status"] == "PASS"),
            "failed": sum(1 for row in build_results if row["status"] == "FAIL"),
            "timeout": sum(1 for row in build_results if row["status"] == "TIMEOUT"),
        },
        "gate_results": gate_results,
        "build_results": build_results,
        "screenshots": screenshots,
        "docs": docs,
        "known_issues": known_issues,
        "release_readiness": score,
        "safety": safety,
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
