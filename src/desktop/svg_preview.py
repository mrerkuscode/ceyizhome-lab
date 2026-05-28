from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

try:
    from PySide6.QtSvgWidgets import QSvgWidget
except ImportError:  # pragma: no cover - depends on local PySide6 build.
    QSvgWidget = None


class SvgPreview(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.svg_path: Path | None = None
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.message = QLabel("SVG seçilmedi.")
        self.message.setAlignment(Qt.AlignCenter)
        self.open_button = QPushButton("SVG Dosyasını Aç")
        self.open_button.setVisible(False)
        self.svg_widget = QSvgWidget() if QSvgWidget is not None else None
        if self.svg_widget is not None:
            self.svg_widget.setMinimumHeight(260)
            self.layout.addWidget(self.svg_widget)
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.open_button)

    def load_svg(self, path: Path) -> None:
        self.svg_path = path
        self.message.setText(str(path))
        self.open_button.setVisible(True)
        if self.svg_widget is not None and path.exists():
            self.svg_widget.load(str(path))
        elif QSvgWidget is None:
            self.message.setText("SVG önizleme bu ortamda kullanılamıyor. Dosyayı açabilirsiniz.")
