from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from .web_main_window import WebMainWindow


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    python_exe = venv_python if venv_python.exists() else Path(sys.executable)
    app = QApplication(sys.argv)

    style_path = Path(__file__).with_name("style.qss")
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))

    window = WebMainWindow(project_root=project_root, python_exe=python_exe)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
