from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "quality_gate"
OUTPUT_PATH = OUTPUT_DIR / "FULL_REAL_USER_E2E_SMOKE_RESULT.json"


CHECKS = [
    ["scripts/label_models_real_click_gate.py"],
    ["scripts/studio_canvas_interaction_gate.py"],
    ["scripts/print_action_real_user_gate.py"],
    ["scripts/production_history_real_user_gate.py"],
    ["scripts/label_outputs_gallery_gate.py"],
    ["scripts/settings_security_gate.py"],
    ["scripts/help_onboarding_gate.py"],
    ["scripts/real_production_quality_gate.py"],
    ["scripts/final_acceptance_gate.py"],
]


def run_check(args: list[str]) -> dict[str, object]:
    started = datetime.now().isoformat(timespec="seconds")
    command = [sys.executable, *args]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    return {
        "command": " ".join(command),
        "started_at": started,
        "exit_code": completed.returncode,
        "output": completed.stdout[-12000:],
        "status": "PASSED" if completed.returncode == 0 else "FAILED",
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [run_check(args) for args in CHECKS]
    status = "PASSED" if all(item["exit_code"] == 0 for item in results) else "FAILED"
    payload = {
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "checks": results,
        "note": "Project-native real user smoke: button route/state, Studio pointer geometry, output validation and final acceptance gates.",
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": status, "result_path": str(OUTPUT_PATH)}, ensure_ascii=False))
    return 0 if status == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
