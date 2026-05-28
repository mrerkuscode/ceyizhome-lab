from __future__ import annotations

import json
import os
import subprocess
import sys
import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TODAY = datetime.now().strftime("%Y-%m-%d")
LOG_DIR = ROOT / "output" / TODAY / "test_command_real_user_qa"
REPORT_PATH = ROOT / "TEST_COMMAND_REAL_USER_QA_REPORT.md"

REQUIRED_DOCS = [
    "START_HERE_FOR_CODEX.md",
    "PROJECT_MASTER_CONTEXT.md",
    "CODEX_LEAD_DEVELOPER_MANUAL.md",
    "REAL_USER_TESTING_STANDARD.md",
    "HUMAN_QA_PROTOCOL.md",
    "INTERACTION_TESTING_GUIDE.md",
    "BUTTON_CLICK_TESTING_STANDARD.md",
    "OUTPUT_VALIDATION_STANDARD.md",
    "VISUAL_SCREENSHOT_QA_GUIDE.md",
    "QA_ACCEPTANCE_CHECKLIST.md",
    "CODEX_CURRENT_PRIORITY.md",
    "TEST_COMMAND_REAL_USER_QA_PROTOCOL.md",
]


@dataclass
class CommandResult:
    name: str
    command: list[str]
    returncode: int
    log_path: Path
    stdout_tail: str
    duration_seconds: float = 0.0
    timed_out: bool = False
    timeout_seconds: int = 0
    json_status: str | None = None

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and self.json_status not in {"FAILED", "ERROR"}


def run_command(name: str, command: list[str], timeout_seconds: int) -> CommandResult:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
        output = completed.stdout or ""
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        output += f"\nTIMEOUT after {timeout_seconds}s"
        returncode = 124
    finished = datetime.now()
    log_path = LOG_DIR / f"{name}.txt"
    log_path.write_text(
        "\n".join(
            [
                f"Command: {' '.join(command)}",
                f"Started: {started.isoformat(timespec='seconds')}",
                f"Finished: {finished.isoformat(timespec='seconds')}",
                f"Duration seconds: {round((finished - started).total_seconds(), 2)}",
                f"Timeout seconds: {timeout_seconds}",
                f"Timed out: {timed_out}",
                f"Return code: {returncode}",
                "",
                output,
            ]
        ),
        encoding="utf-8",
    )
    return CommandResult(
        name=name,
        command=command,
        returncode=returncode,
        log_path=log_path,
        stdout_tail=tail(output),
        duration_seconds=round((finished - started).total_seconds(), 2),
        timed_out=timed_out,
        timeout_seconds=timeout_seconds,
        json_status=parse_json_status(output),
    )


def tail(text: str, limit: int = 2200) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return "..." + text[-limit:]


def parse_json_status(output: str) -> str | None:
    stripped = output.strip()
    if not stripped.startswith("{"):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    status = payload.get("status")
    return str(status) if status is not None else None


def validate_docs() -> tuple[list[str], list[str]]:
    missing: list[str] = []
    read_ok: list[str] = []
    for name in REQUIRED_DOCS:
        path = ROOT / name
        if not path.exists():
            missing.append(name)
            continue
        path.read_text(encoding="utf-8")
        read_ok.append(name)
    return read_ok, missing


def write_report(results: list[CommandResult], docs_ok: list[str], docs_missing: list[str]) -> None:
    failures = [result for result in results if not result.passed]
    p0p1_status = "P0/P1 hata yok." if not failures and not docs_missing else "P0/P1 inceleme gerekli."
    status = "PASSED" if not failures and not docs_missing else "FAILED"

    screenshot_paths = [
        ROOT / "output" / TODAY / "ui_screenshots",
        ROOT / "output" / TODAY / "quality_gate",
        ROOT / "output" / TODAY / "label_models_click_gate",
        ROOT / "output" / TODAY / "studio_interaction",
        ROOT / "output" / TODAY / "print_action_gate",
    ]

    lines = [
        "# TEST_COMMAND_REAL_USER_QA_REPORT",
        "",
        f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Durum: {status}",
        "",
        "## Okunan Standart Dosyalar",
        "",
        *[f"- `{name}`" for name in docs_ok],
    ]
    if docs_missing:
        lines.extend(["", "Eksik dosyalar:", "", *[f"- `{name}`" for name in docs_missing]])

    lines.extend(
        [
            "",
            "## Test Edilen Sayfalar ve Akışlar",
            "",
            "- Ana Sayfa",
            "- Etiket Modelleri",
            "- Etiket Studio",
            "- Toplu Etiket",
            "- Yazdırma Sırası",
            "- Etiket Çıktıları",
            "- Ayarlar",
            "",
            "## Test Edilen Kritik Davranışlar",
            "",
            "- Etiket Modelleri gerçek click: Yenile, Yeni Model Ekle, Görsel Bağla, Önizle, Etiket Hazırla, Studio’da Düzenle, filtreler, Teknik Mod.",
            "- Etiket Studio gerçek pointer/keyboard interaction: drag, corner resize, side resize, zoom %100/%150/%200, Arrow/Shift+Arrow/Alt+Arrow.",
            "- Output validation: PDF/PNG background, İsim/Tarih/Not, stale dosya kontrolü, queue path doğruluğu.",
            "- Yazdırma güvenliği: Studio ve queue içindeki Yazdır butonları safe modal açar; silent/direct print tetiklenmez.",
            "- Screenshot QA: UI screenshotları ve quality gate screenshotları üretildi.",
            "",
            "## Komut Sonuçları",
            "",
        ]
    )

    for result in results:
        lines.extend(
            [
                f"### {result.name}",
                "",
                f"- Komut: `{' '.join(result.command)}`",
                f"- Return code: `{result.returncode}`",
                f"- Süre: `{result.duration_seconds}s`",
                f"- Timeout: `{result.timeout_seconds}s`",
                f"- Zaman aşımı: `{'evet' if result.timed_out else 'hayır'}`",
                f"- JSON status: `{result.json_status or 'n/a'}`",
                f"- Sonuç: `{'PASSED' if result.passed else 'FAILED'}`",
                f"- Log: `{result.log_path}`",
                "",
                "```text",
                result.stdout_tail or "(çıktı yok)",
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## Screenshot Yolları",
            "",
            *[f"- `{path}`" for path in screenshot_paths],
            "",
            "## P0/P1 Durumu",
            "",
            p0p1_status,
            "",
            "## Kalan Riskler",
            "",
            "- Runner otomatik kalite kapılarını çalıştırır; kullanıcı manuel olarak farklı bir davranış görürse kullanıcı gözlemi esas alınır.",
            "- P0/P1 fail olursa Codex düzeltme yapıp runner'ı tekrar çalıştırmalıdır.",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=420, help="Each gate command timeout in seconds.")
    args = parser.parse_args()
    docs_ok, docs_missing = validate_docs()
    python = sys.executable
    commands = [
        ("node_check_app", ["node", "--check", "src\\webui\\app.js"]),
        ("pytest", [python, "-m", "pytest"]),
        ("label_models_real_click_gate", [python, "scripts\\label_models_real_click_gate.py"]),
        ("studio_canvas_interaction_gate", [python, "scripts\\studio_canvas_interaction_gate.py"]),
        ("print_action_real_user_gate", [python, "scripts\\print_action_real_user_gate.py"]),
        ("production_history_real_user_gate", [python, "scripts\\production_history_real_user_gate.py"]),
        ("label_outputs_gallery_gate", [python, "scripts\\label_outputs_gallery_gate.py"]),
        ("settings_security_gate", [python, "scripts\\settings_security_gate.py"]),
        ("help_onboarding_gate", [python, "scripts\\help_onboarding_gate.py"]),
        ("real_production_quality_gate", [python, "scripts\\real_production_quality_gate.py"]),
        ("final_acceptance_gate", [python, "scripts\\final_acceptance_gate.py"]),
        ("capture_webui_screenshots", [python, "scripts\\capture_webui_screenshots.py"]),
        ("capture_quality_gate_screenshots", [python, "scripts\\capture_quality_gate_screenshots.py"]),
    ]
    results: list[CommandResult] = []
    for name, command in commands:
        print(json.dumps({"status": "RUNNING", "gate": name, "timeout_seconds": args.timeout}, ensure_ascii=False))
        result = run_command(name, command, args.timeout)
        results.append(result)
        write_report(results, docs_ok, docs_missing)
        print(json.dumps({"status": "PASSED" if result.passed else "FAILED", "gate": name, "returncode": result.returncode, "timed_out": result.timed_out, "log": str(result.log_path)}, ensure_ascii=False))
    write_report(results, docs_ok, docs_missing)
    failed = [result.name for result in results if not result.passed]
    if docs_missing:
        print(json.dumps({"status": "FAILED", "missing_docs": docs_missing, "failed_commands": failed, "report": str(REPORT_PATH)}, ensure_ascii=False, indent=2))
        return 1
    if failed:
        print(json.dumps({"status": "FAILED", "failed_commands": failed, "report": str(REPORT_PATH)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "PASSED", "report": str(REPORT_PATH), "log_dir": str(LOG_DIR)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
