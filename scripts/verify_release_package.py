from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = PROJECT_ROOT / "release"

REQUIRED_FILES = [
    "README.md",
    "requirements.txt",
    "RELEASE_NOTES.md",
    "USER_MANUAL.md",
    "TECHNICAL_MANUAL.md",
    "INSTALLATION_CHECKLIST.md",
    "FINAL_RELEASE_CHECKLIST.md",
    "start_app.bat",
    "run_release_quality_gate.bat",
    "release_manifest.json",
]

REQUIRED_DIRS = [
    "src/webui",
    "src/webui_backend",
    "scripts",
    "templates/designs",
    "assets/label_backgrounds",
    "examples",
    "tests",
    "output",
    "backups",
    "logs",
]

REQUIRED_GATE_COMMANDS = [
    "scripts\\verify_clean_customer_demo_flow.py",
    "scripts\\verify_rdworks_name_cut_layout_export.py",
    "scripts\\verify_combined_excel_label_and_name_cut_flow.py",
    "scripts\\real_production_quality_gate.py",
    "scripts\\final_acceptance_gate.py",
    "scripts\\final_release_package_gate.py",
]

OPTIONAL_REPORTS_TO_COPY_WHEN_PRESENT = [
    "CLEAN_DEMO_DATA_AND_ARCHIVE_REPORT.md",
    "RDWORKS_FIELD_IMPORT_AND_PACKING_ROADMAP.md",
    "RELEASE_QUALITY_GATE_ALIGNMENT_REPORT.md",
    "RDWORKS_REAL_IMPORT_FIELD_CHECKLIST.md",
    "RDWORKS_REAL_IMPORT_FIELD_CHECKLIST_REPORT.md",
    "CLEAN_DEMO_USER_DELIVERY_GUIDE_REPORT.md",
    "FINAL_USER_HANDOFF_NOTE.md",
    "USER_DELIVERY_FINAL_CHECK_REPORT.md",
    "TARGET_INSTALLATION_REHEARSAL_REPORT.md",
]

FORBIDDEN_DIRS = [
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "release",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _latest_release_dir() -> Path:
    pointer = RELEASE_ROOT / "latest_release.json"
    if pointer.exists():
        data = json.loads(pointer.read_text(encoding="utf-8"))
        path = Path(data["path"])
        if path.exists():
            return path

    candidates = sorted(
        [path for path in RELEASE_ROOT.glob("CyzellaProductionStudio_*") if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise AssertionError("Release package bulunamadi.")
    return candidates[0]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_release_package(package_dir: Path) -> dict[str, object]:
    _assert(package_dir.exists(), f"Release klasoru yok: {package_dir}")
    checks: list[dict[str, str]] = []

    for rel in REQUIRED_FILES:
        path = package_dir / rel
        _assert(path.is_file(), f"Eksik release dosyasi: {rel}")
        checks.append({"name": rel, "status": "PASSED"})

    for rel in REQUIRED_DIRS:
        path = package_dir / rel
        _assert(path.is_dir(), f"Eksik release klasoru: {rel}")
        checks.append({"name": rel, "status": "PASSED"})

    release_gate = (package_dir / "run_release_quality_gate.bat").read_text(encoding="utf-8")
    for command in REQUIRED_GATE_COMMANDS:
        _assert(command in release_gate, f"Release kalite kapisi komutu eksik: {command}")
        checks.append({"name": f"quality_gate:{command}", "status": "PASSED"})

    for report in OPTIONAL_REPORTS_TO_COPY_WHEN_PRESENT:
        source_report = PROJECT_ROOT / report
        if source_report.exists():
            _assert((package_dir / report).is_file(), f"Release paketinde rapor eksik: {report}")
            checks.append({"name": report, "status": "PASSED"})

    for forbidden in FORBIDDEN_DIRS:
        matches = [path for path in package_dir.rglob(forbidden) if path.exists()]
        _assert(not matches, f"Release paketinde yasakli klasor var: {forbidden}")

    manifest_path = package_dir / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    safety = manifest.get("safety", {})
    for key in [
        "direct_print_enabled",
        "printer_auto_start",
        "coreldraw_auto_open",
        "illustrator_auto_open",
        "rdworks_auto_open",
        "laser_auto_start",
        "source_ai_cdr_modified",
    ]:
        _assert(safety.get(key) is False, f"Release guvenlik bayragi hatali: {key}")

    manifest_files = manifest.get("files", [])
    _assert(isinstance(manifest_files, list) and manifest_files, "Manifest file listesi bos.")
    sample = next((item for item in manifest_files if item["path"] == "requirements.txt"), None)
    _assert(sample is not None, "Manifest requirements.txt icermiyor.")
    _assert(
        sample["sha256"] == _sha256(package_dir / "requirements.txt"),
        "Manifest checksum dogrulamasi basarisiz.",
    )

    return {
        "status": "PASSED",
        "release_package": str(package_dir),
        "checks": checks,
        "manifest_file_count": len(manifest_files),
        "safety": safety,
    }


def main() -> None:
    package_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else _latest_release_dir()
    result = verify_release_package(package_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
