from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = PROJECT_ROOT / "release"
PACKAGE_NAME = "CyzellaProductionStudio"

COPY_DIRS = [
    "src",
    "scripts",
    "templates",
    "assets",
    "examples",
    "config",
    "docs",
    "tests",
]

COPY_FILES = [
    "README.md",
    "requirements.txt",
    "pytest.ini",
    "RELEASE_NOTES.md",
    "USER_MANUAL.md",
    "TECHNICAL_MANUAL.md",
    "INSTALLATION_CHECKLIST.md",
    "FINAL_RELEASE_CHECKLIST.md",
    "FINAL_HUMAN_QA_SIGNOFF_REPORT.md",
    "FINAL_DELIVERY_PACKAGE_REVIEW_REPORT.md",
    "RDWORKS_BOOLEAN_OFFSET_POC_REPORT.md",
    "run_web_desktop.bat",
    "setup.bat",
    "start_app.bat",
]

OPTIONAL_FILES = [
    "RELEASE_AUTOMATION_IMPLEMENTATION_REPORT.md",
    "RELEASE_AUTOMATION_ROADMAP_REPORT.md",
    "FINAL_REAL_USER_MVP_ACCEPTANCE_REPORT.md",
    "USER_QUICKSTART_IN_APP_HELP_REPORT.md",
    "CLEAN_DEMO_DATA_AND_ARCHIVE_REPORT.md",
    "RDWORKS_FIELD_IMPORT_AND_PACKING_ROADMAP.md",
    "RELEASE_QUALITY_GATE_ALIGNMENT_REPORT.md",
    "RDWORKS_REAL_IMPORT_FIELD_CHECKLIST.md",
    "RDWORKS_REAL_IMPORT_FIELD_CHECKLIST_REPORT.md",
    "CLEAN_DEMO_USER_DELIVERY_GUIDE_REPORT.md",
    "FINAL_USER_HANDOFF_NOTE.md",
    "USER_DELIVERY_FINAL_CHECK_REPORT.md",
    "RDWORKS_MANUAL_CUT_QA_NOTES.md",
    "FINAL_DELIVERY_READY_SUMMARY.md",
    "TARGET_INSTALLATION_REHEARSAL_REPORT.md",
]

EMPTY_RUNTIME_DIRS = [
    "output",
    "backups",
    "logs",
    "data",
]

EXCLUDE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "release",
}

EXCLUDE_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tmp",
    ".log",
}


def _ignore(_dir: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(_dir) / name
        if path.is_dir() and name in EXCLUDE_DIR_NAMES:
            ignored.add(name)
        if path.is_file() and path.suffix.lower() in EXCLUDE_FILE_SUFFIXES:
            ignored.add(name)
    return ignored


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_runtime_bats(package_dir: Path) -> None:
    (package_dir / "start_app.bat").write_text(
        """@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist ".venv\\Scripts\\python.exe" (
    echo Ilk kurulum icin setup.bat calistiriliyor...
    call setup.bat
    if errorlevel 1 exit /b 1
)
echo Cyzella Production Studio aciliyor...
".venv\\Scripts\\python.exe" -m src.desktop.app
if errorlevel 1 (
    echo Uygulama baslatilamadi.
    pause
    exit /b 1
)
""",
        encoding="utf-8",
    )

    (package_dir / "run_release_quality_gate.bat").write_text(
        """@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist ".venv\\Scripts\\python.exe" (
    echo Python sanal ortami yok. Once setup.bat calistirin.
    pause
    exit /b 1
)
node --check src\\webui\\app.js
if errorlevel 1 exit /b 1
".venv\\Scripts\\python.exe" -m pytest -q
if errorlevel 1 exit /b 1
".venv\\Scripts\\python.exe" scripts\\verify_clean_customer_demo_flow.py
if errorlevel 1 exit /b 1
".venv\\Scripts\\python.exe" scripts\\verify_rdworks_name_cut_layout_export.py
if errorlevel 1 exit /b 1
".venv\\Scripts\\python.exe" scripts\\verify_combined_excel_label_and_name_cut_flow.py
if errorlevel 1 exit /b 1
".venv\\Scripts\\python.exe" scripts\\real_production_quality_gate.py
if errorlevel 1 exit /b 1
".venv\\Scripts\\python.exe" scripts\\final_acceptance_gate.py
if errorlevel 1 exit /b 1
".venv\\Scripts\\python.exe" scripts\\final_release_package_gate.py
if errorlevel 1 exit /b 1
echo Release kalite kapisi basarili.
pause
""",
        encoding="utf-8",
    )


def _copy_required_content(package_dir: Path) -> None:
    for rel in COPY_DIRS:
        source = PROJECT_ROOT / rel
        target = package_dir / rel
        if not source.exists():
            raise FileNotFoundError(f"Required release directory missing: {rel}")
        shutil.copytree(source, target, ignore=_ignore)

    for rel in COPY_FILES:
        source = PROJECT_ROOT / rel
        target = package_dir / rel
        if not source.exists():
            raise FileNotFoundError(f"Required release file missing: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    for rel in OPTIONAL_FILES:
        source = PROJECT_ROOT / rel
        target = package_dir / rel
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    for rel in EMPTY_RUNTIME_DIRS:
        runtime_dir = package_dir / rel
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / ".keep").write_text(
            "Runtime directory is intentionally empty in the release package.\n",
            encoding="utf-8",
        )

    _write_runtime_bats(package_dir)


def _build_manifest(package_dir: Path, created_at: str) -> dict[str, object]:
    files: list[dict[str, object]] = []
    for path in sorted(package_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(package_dir).as_posix()
            files.append(
                {
                    "path": rel,
                    "size": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )

    return {
        "package": PACKAGE_NAME,
        "created_at": created_at,
        "source_root": str(PROJECT_ROOT),
        "file_count": len(files),
        "safety": {
            "direct_print_enabled": False,
            "printer_auto_start": False,
            "coreldraw_auto_open": False,
            "illustrator_auto_open": False,
            "rdworks_auto_open": False,
            "laser_auto_start": False,
            "source_ai_cdr_modified": False,
        },
        "manual_decisions": [
            "Yazici otomatik calismaz; PDF kullanici onayi ile acilir.",
            "RDWorks ve lazer otomatik acilmaz; dosya hazirlanir ve kullanici manuel kontrol eder.",
            "Kaynak AI/CDR dosyalari release otomasyonu tarafindan degistirilmez.",
        ],
        "files": files,
    }


def build_release_package() -> Path:
    created_at = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    package_dir = RELEASE_ROOT / f"{PACKAGE_NAME}_{created_at}"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True)

    _copy_required_content(package_dir)
    manifest = _build_manifest(package_dir, created_at)
    (package_dir / "release_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    latest_pointer = RELEASE_ROOT / "latest_release.json"
    latest_pointer.write_text(
        json.dumps(
            {
                "latest_package": package_dir.name,
                "path": str(package_dir),
                "created_at": created_at,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return package_dir


def main() -> None:
    package_dir = build_release_package()
    print(
        json.dumps(
            {
                "status": "PASSED",
                "release_package": str(package_dir),
                "manifest": str(package_dir / "release_manifest.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
