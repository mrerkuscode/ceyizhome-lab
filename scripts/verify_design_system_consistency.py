from __future__ import annotations

import json
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = PROJECT_ROOT / "src" / "webui" / "styles.css"
OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "design_system"
RESULT_PATH = OUTPUT_DIR / "VERIFY_DESIGN_SYSTEM_CONSISTENCY_RESULT.json"


REQUIRED_SNIPPETS = {
    "shared_control_height": "--ds-control-height",
    "shared_card_radius": "--ds-radius-card",
    "shared_control_radius": "--ds-radius-control",
    "shared_surface": "--ds-surface",
    "shared_button_rule": ".btn {",
    "primary_button_gradient": ".btn.primary",
    "danger_button_rule": ".btn.danger-soft",
    "input_rule": "input,\nselect,\ntextarea",
    "pill_rule": ".pill,\n.status-pill",
    "empty_state_rule": ".empty-state {",
    "modal_card_rule": ".modal-card {",
    "responsive_page_shell": "@media (max-width: 1180px)",
}


def main() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    checks: list[dict[str, str]] = []
    missing: list[str] = []
    for name, snippet in REQUIRED_SNIPPETS.items():
        ok = snippet in css
        checks.append({"name": name, "status": "PASSED" if ok else "FAILED"})
        if not ok:
            missing.append(name)

    result = {
        "status": "PASSED" if not missing else "FAILED",
        "css_path": str(CSS_PATH),
        "checks": checks,
        "missing": missing,
        "note": "Static guard for shared UI tokens and low-risk component rules.",
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
