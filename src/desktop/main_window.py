from __future__ import annotations

import csv
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml
from openpyxl import load_workbook
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from webui_backend.settings_api import save_config

from .file_actions import latest_run_dir, open_folder
from .label_template_editor import LabelTemplateEditorDialog
from .report_loader import ReportSet, load_latest_reports
from .svg_preview import SvgPreview
from .template_importer import TemplateImportError, safe_extract_template_pack
from .worker import CommandWorker


STEP_NAMES = ["Excel", "Kontrol", "Etiket", "Lazer", "Raporlar"]
PRODUCTION_COLUMNS = [
    "order_no",
    "buyer_name",
    "product_name",
    "model_no",
    "template_no",
    "process_type",
    "personalization_type",
    "label_variant",
    "label_text",
    "laser_text",
    "quantity",
    "material_type",
    "material_thickness_mm",
    "extra_chocolate_qty",
    "extra_madlen_qty",
    "production_note",
    "needs_review",
    "status",
]


class MainWindow(QMainWindow):
    def __init__(self, project_root: Path, python_exe: Path) -> None:
        super().__init__()
        self.project_root = project_root
        self.python_exe = python_exe
        self.selected_excel = self.project_root / "input" / "siparisler.xlsx"
        self.report_set: ReportSet | None = None
        self.current_readiness = "NO_CHECK"
        self.last_import_preview: Path | None = None
        self.dark_mode = False
        self.activity_rows: list[tuple[str, str, str, str]] = []
        self.summary_labels: dict[str, QLabel] = {}
        self.step_buttons: list[QPushButton] = []
        self.side_step_buttons: list[QPushButton] = []
        self.last_command_name = ""

        self.worker = CommandWorker(project_root, python_exe, self)
        self.worker.output_received.connect(self._append_log)
        self.worker.started.connect(self._command_started)
        self.worker.finished.connect(self._command_finished)

        self.setWindowTitle("CeyizHome Lab")
        self.resize(1500, 900)
        self.setMinimumSize(1280, 760)
        self._build_ui()
        self._refresh_static_status()
        self._refresh_excel_status()
        self._load_reports()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppShell")
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_sidebar())
        shell.addWidget(self._build_main_area(), 1)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 16)
        layout.setSpacing(10)

        brand = QHBoxLayout()
        logo = QLabel("C")
        logo.setObjectName("LogoMark")
        brand_text = QVBoxLayout()
        title = QLabel("CEYIZHOME LAB")
        title.setObjectName("SidebarBrand")
        subtitle = QLabel("Production & Label Studio")
        subtitle.setObjectName("SidebarSubtitle")
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        brand.addWidget(logo)
        brand.addLayout(brand_text)
        layout.addLayout(brand)

        layout.addWidget(self._side_section_title("ANA MENÜ"))
        overview = self._sidebar_button("Genel Bakış", "Tüm süreç özeti", active=True)
        overview.clicked.connect(lambda: self._scroll_top())
        layout.addWidget(overview)

        layout.addWidget(self._side_section_title("SÜREÇ ADIMLARI"))
        for index, name in enumerate(STEP_NAMES):
            button = self._sidebar_button(name, "Beklemede", number=str(index + 1))
            button.clicked.connect(lambda _checked=False, step=index: self._activate_step(step))
            self.side_step_buttons.append(button)
            layout.addWidget(button)

        layout.addWidget(self._side_section_title("ARAÇLAR"))
        folder_buttons = [
            ("Etiket Şablonları", lambda: self._open_folder(self.project_root / "templates" / "designs")),
            ("Etiket Şablonu Düzenle", self._show_template_editor),
            ("Şablon Paketi Yükle", self._import_template_pack),
            ("Çıktı Klasörünü Aç", lambda: self._open_folder(latest_run_dir(self.project_root))),
            ("Raporlar Klasörünü Aç", lambda: self._open_folder(latest_run_dir(self.project_root) / "reports")),
            ("Lazer Klasörünü Aç", lambda: self._open_folder(latest_run_dir(self.project_root) / "laser")),
            ("Ayarlar", self._show_settings_dialog),
        ]
        for text, callback in folder_buttons:
            button = self._sidebar_button(text, "", compact=True)
            button.clicked.connect(callback)
            layout.addWidget(button)

        layout.addStretch()
        safety = QFrame()
        safety.setObjectName("SidebarSafetyCard")
        safety_layout = QVBoxLayout(safety)
        safety_layout.setContentsMargins(16, 14, 16, 14)
        safety_title = QLabel("GÜVENLİ MOD AKTİF")
        safety_title.setObjectName("SidebarSafetyTitle")
        safety_text = QLabel("CorelDRAW, yazıcı, RDWorks ve lazer otomatik çalışmaz.")
        safety_text.setObjectName("SidebarSafetyText")
        safety_text.setWordWrap(True)
        safety_layout.addWidget(safety_title)
        safety_layout.addWidget(safety_text)
        layout.addWidget(safety)
        return sidebar

    def _build_main_area(self) -> QWidget:
        area = QScrollArea()
        area.setObjectName("MainScroll")
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_scroll = area

        content = QWidget()
        content.setObjectName("MainContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 16, 14, 20)
        layout.setSpacing(14)
        layout.addWidget(self._build_topbar())
        layout.addWidget(self._build_page_header())

        left = QVBoxLayout()
        left.setSpacing(16)
        left.addWidget(self._build_steps())
        left.addWidget(self._build_status_banner())
        left.addLayout(self._build_main_grid())
        left.addWidget(self._build_quick_actions())
        left.addWidget(self._build_right_panel())
        left.addLayout(self._build_bottom_grid())
        left.addWidget(self._build_reports())
        left.addWidget(self._build_footer())
        layout.addLayout(left)
        area.setWidget(content)
        return area

    def _build_topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setObjectName("Topbar")
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        excel = QFrame()
        excel.setObjectName("ExcelCard")
        excel_layout = QHBoxLayout(excel)
        excel_layout.setContentsMargins(12, 9, 12, 9)
        excel_layout.setSpacing(10)
        icon = QLabel("X")
        icon.setObjectName("ExcelIcon")
        info = QVBoxLayout()
        info.setSpacing(2)
        label = QLabel("Seçili Excel Dosyası")
        label.setObjectName("SmallMuted")
        self.excel_name_top = QLabel("-")
        self.excel_name_top.setObjectName("ExcelName")
        self.excel_name_top.setMinimumWidth(110)
        info.addWidget(label)
        info.addWidget(self.excel_name_top)
        change = QPushButton("Değiştir")
        change.setObjectName("LightButton")
        change.clicked.connect(self._choose_excel)
        excel_layout.addWidget(icon)
        excel_layout.addLayout(info, 1)
        excel_layout.addWidget(change)
        layout.addWidget(excel, 1)

        self.safe_badge = self._pill("GÜVENLİ MOD AKTİF\nSistem korumalı çalışıyor", "success")
        self.font_badge = self._pill("LAZER FONTU KONTROL EDİLİYOR\n-", "warning")
        layout.addWidget(self.safe_badge)
        layout.addWidget(self.font_badge)

        theme = QFrame()
        theme.setObjectName("ThemeToggle")
        theme_layout = QHBoxLayout(theme)
        theme_layout.setContentsMargins(4, 4, 4, 4)
        theme_layout.setSpacing(4)
        self.day_button = QPushButton("Gündüz")
        self.day_button.setObjectName("ThemeActive")
        self.night_button = QPushButton("Gece")
        self.night_button.setObjectName("ThemeOption")
        self.day_button.clicked.connect(lambda: self._set_theme(False))
        self.night_button.clicked.connect(lambda: self._set_theme(True))
        theme_layout.addWidget(self.day_button)
        theme_layout.addWidget(self.night_button)
        layout.addWidget(theme)

        help_button = QPushButton("Nasıl Kullanırım")
        help_button.setObjectName("HeaderButton")
        help_button.clicked.connect(self._show_help_dialog)
        settings_button = QPushButton("Ayarlar")
        settings_button.setObjectName("HeaderButton")
        settings_button.clicked.connect(self._show_settings_dialog)
        layout.addWidget(help_button)
        layout.addWidget(settings_button)
        return topbar

    def _build_page_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("PageHeader")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Genel Bakış")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Üretim dosyalarını güvenli şekilde kontrol edin ve hazırlayın.")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return header

    def _build_steps(self) -> QWidget:
        container = QFrame()
        container.setObjectName("StepsWrap")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        for index, name in enumerate(STEP_NAMES):
            button = QPushButton(f"{index + 1}\n{name}\nBekliyor")
            button.setObjectName("StepCard")
            button.setCursor(Qt.PointingHandCursor)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda _checked=False, step=index: self._activate_step(step))
            self.step_buttons.append(button)
            layout.addWidget(button)
        return container

    def _build_status_banner(self) -> QWidget:
        banner = QFrame()
        banner.setObjectName("StatusBanner")
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        icon = QLabel("!")
        icon.setObjectName("BannerIcon")
        self.banner_title = QLabel("HENÜZ KONTROL YAPILMADI")
        self.banner_title.setObjectName("BannerTitle")
        self.banner_text = QLabel("Excel dosyasını seçin ve dry-run kontrolünü başlatın.")
        self.banner_text.setObjectName("BannerText")
        self.banner_text.setWordWrap(True)
        text_box = QVBoxLayout()
        text_box.addWidget(self.banner_title)
        text_box.addWidget(self.banner_text)
        self.banner_button = QPushButton("Kontrolü Başlat")
        self.banner_button.setObjectName("BannerButton")
        self.banner_button.clicked.connect(self._run_dry)
        layout.addWidget(icon)
        layout.addLayout(text_box, 1)
        layout.addWidget(self.banner_button)
        self.banner = banner
        return banner

    def _build_main_grid(self) -> QVBoxLayout:
        grid = QVBoxLayout()
        grid.setSpacing(14)

        summary = self._card("ÖZET BİLGİLER")
        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(12)
        summary_grid.setVerticalSpacing(12)
        kpis = [
            ("valid_rows", "GEÇERLİ SİPARİŞ", "0", "success"),
            ("invalid_rows", "KRİTİK HATA", "0", "error"),
            ("review", "KONTROL GEREKLİ", "0", "warning"),
            ("label_jobs", "ETİKET İŞLERİ", "0", "neutral"),
            ("print_jobs_count", "BASKI İŞLERİ", "0", "blue"),
            ("laser_jobs", "LAZER İŞLERİ", "0", "neutral"),
        ]
        for index, (key, title, value, status) in enumerate(kpis):
            card, value_label = self._kpi(title, value, status)
            self.summary_labels[key] = value_label
            summary_grid.addWidget(card, index // 3, index % 3)
        summary.layout().addLayout(summary_grid)
        grid.addWidget(summary)

        errors = self._card("İLK KRİTİK HATALAR")
        self.errors_list = QVBoxLayout()
        self.errors_list.setSpacing(0)
        errors.layout().addLayout(self.errors_list)
        grid.addWidget(errors)
        return grid

    def _build_quick_actions(self) -> QWidget:
        card = self._card("YAPILACAK İŞLEMLER")
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        actions = [
            ("Excel Dosyası Seç", self._choose_excel, False),
            ("Kontrolü Tekrar Çalıştır", self._run_dry, True),
            ("Etiket PDF Oluştur", self._render_labels, False),
            ("Etiket Şablonu Düzenle", self._show_template_editor, False),
            ("Çıktı Klasörünü Aç", lambda: self._open_folder(latest_run_dir(self.project_root)), False),
            ("Rulo Etiket PDF Oluştur", self._render_labels, False),
            ("Şablon Paketi Yükle", self._import_template_pack, False),
            ("Raporlar Klasörünü Aç", lambda: self._open_folder(latest_run_dir(self.project_root) / "reports"), False),
            ("Lazer Klasörünü Aç", lambda: self._open_folder(latest_run_dir(self.project_root) / "laser"), False),
        ]
        for index, (text, callback, primary) in enumerate(actions):
            button = QPushButton(text)
            button.setObjectName("QuickButtonGold" if primary else "QuickButton")
            button.clicked.connect(callback)
            grid.addWidget(button, index // 2, index % 2)
        card.layout().addLayout(grid)
        return card

    def _build_bottom_grid(self) -> QVBoxLayout:
        grid = QVBoxLayout()
        grid.setSpacing(14)

        activity = self._card("SON İŞLEMLER")
        self.activity_table = self._table()
        activity.layout().addWidget(self.activity_table)
        grid.addWidget(activity)

        next_card = self._card("SONRAKİ ADIM")
        self.next_title = QLabel("Excel kontrolü bekleniyor")
        self.next_title.setObjectName("NextTitle")
        self.next_text = QLabel("Excel dosyasını seçip dry-run kontrolünü başlatın.")
        self.next_text.setObjectName("MutedText")
        self.next_text.setWordWrap(True)
        self.confirm_checkbox = QCheckBox("Dry-run raporlarını kontrol ettim. Sadece dosya ve rapor üretileceğini anlıyorum.")
        self.confirm_checkbox.setObjectName("ConfirmCheck")
        self.production_button = QPushButton("Üretim Dosyalarını Oluştur")
        self.production_button.setObjectName("PrimaryButton")
        self.production_button.clicked.connect(self._run_production)
        next_card.layout().addWidget(self.next_title)
        next_card.layout().addWidget(self.next_text)
        next_card.layout().addWidget(self.confirm_checkbox)
        next_card.layout().addWidget(self.production_button)
        grid.addWidget(next_card)
        return grid

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("RightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        help_card = self._card("NASIL KULLANIRIM")
        steps = [
            ("Excel dosyanızı seçin.", "Verilerinizi yükleyin ve doğrulayın."),
            ("Kontrolü başlatın.", "Klasörler, kurallar ve veriler kontrol edilir."),
            ("Hataları düzeltin.", "Kritik hataları Excel veya şablonlardan düzeltin."),
            ("Çıktıları oluşturun.", "PDF/PNG ve SVG çıktıları hazırlanır."),
            ("Raporları inceleyin.", "Tüm sonuçları kontrol edip onaylayın."),
        ]
        for index, (title, text) in enumerate(steps, start=1):
            help_card.layout().addWidget(self._help_step(index, title, text))
        guide = QPushButton("Detaylı Kullanım Kılavuzu")
        guide.setObjectName("LightButton")
        guide.clicked.connect(self._show_help_dialog)
        help_card.layout().addWidget(guide)
        layout.addWidget(help_card)

        quick = self._card("HIZLI ERİŞİM")
        for text, callback in [
            ("Çıktı Klasörünü Aç", lambda: self._open_folder(latest_run_dir(self.project_root))),
            ("Raporlar Klasörünü Aç", lambda: self._open_folder(latest_run_dir(self.project_root) / "reports")),
            ("Lazer Klasörünü Aç", lambda: self._open_folder(latest_run_dir(self.project_root) / "laser")),
            ("Günlük Kayıtları", lambda: self.tabs.setCurrentIndex(6)),
        ]:
            button = QPushButton(text)
            button.setObjectName("SideButton")
            button.clicked.connect(callback)
            quick.layout().addWidget(button)
        layout.addWidget(quick)
        layout.addStretch()
        return panel

    def _build_reports(self) -> QWidget:
        card = self._card("RAPORLAR")
        self.tabs = QTabWidget()
        self.tabs.setObjectName("ReportsTabs")
        self.tabs.setMinimumHeight(420)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.tabBar().setExpanding(False)

        self.summary_text = QTextEdit()
        self.summary_text.setObjectName("ReportText")
        self.summary_text.setReadOnly(True)
        self.summary_table = self._table()
        self.tabs.addTab(self._tab(self.summary_text, self.summary_table), "Özet")

        self.errors_table = self._table()
        self.tabs.addTab(self.errors_table, "Hatalar")
        self.review_table = self._table()
        self.tabs.addTab(self.review_table, "Kontrol Gerekli")
        self.template_table = self._table()
        self.tabs.addTab(self.template_table, "Baskı İşleri")
        self.render_report_table = self._table()
        self.tabs.addTab(self.render_report_table, "Etiket Çıktıları")

        laser_tab = QWidget()
        laser_layout = QVBoxLayout(laser_tab)
        self.laser_report_table = self._table()
        self.svg_list = QListWidget()
        self.svg_list.setObjectName("SvgList")
        self.svg_list.currentTextChanged.connect(self._select_svg)
        self.svg_preview = SvgPreview()
        self.svg_preview.open_button.clicked.connect(self._open_selected_svg)
        laser_layout.addWidget(self.laser_report_table)
        laser_layout.addWidget(self.svg_list)
        laser_layout.addWidget(self.svg_preview)
        self.tabs.addTab(laser_tab, "Lazer")

        self.log_box = QPlainTextEdit()
        self.log_box.setObjectName("LogPanel")
        self.log_box.setReadOnly(True)
        self.tabs.addTab(self.log_box, "Günlük")
        card.layout().addWidget(self.tabs)
        return card

    def _build_footer(self) -> QWidget:
        footer = QLabel("CeyizHome Lab v1.0.0  |  Tüm hakları saklıdır.")
        footer.setObjectName("Footer")
        footer.setAlignment(Qt.AlignCenter)
        return footer

    def _card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        label = QLabel(title)
        label.setObjectName("CardTitle")
        layout.addWidget(label)
        return card

    def _kpi(self, title: str, value: str, status: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName(f"Kpi_{status}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)
        label = QLabel(title)
        label.setObjectName("KpiLabel")
        label.setWordWrap(True)
        value_label = QLabel(value)
        value_label.setObjectName("KpiValue")
        layout.addWidget(label)
        layout.addWidget(value_label)
        return frame, value_label

    def _table(self) -> QTableWidget:
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setWordWrap(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.setMinimumHeight(150)
        return table

    def _tab(self, *widgets: QWidget) -> QWidget:
        page = QWidget()
        page.setObjectName("TabPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        for widget in widgets:
            layout.addWidget(widget)
        return page

    def _help_step(self, number: int, title: str, text: str) -> QWidget:
        row = QFrame()
        row.setObjectName("HelpStep")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 8, 0, 8)
        badge = QLabel(str(number))
        badge.setObjectName("HelpNumber")
        body = QVBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("HelpTitle")
        desc = QLabel(text)
        desc.setObjectName("HelpText")
        desc.setWordWrap(True)
        body.addWidget(heading)
        body.addWidget(desc)
        layout.addWidget(badge)
        layout.addLayout(body, 1)
        return row

    def _pill(self, text: str, status: str) -> QLabel:
        pill = QLabel(text)
        pill.setObjectName(f"Pill_{status}")
        pill.setWordWrap(True)
        pill.setAlignment(Qt.AlignCenter)
        return pill

    def _side_section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SideSectionTitle")
        return label

    def _sidebar_button(self, title: str, subtitle: str, active: bool = False, number: str = "", compact: bool = False) -> QPushButton:
        text = title if compact else f"{number + '  ' if number else ''}{title}\n{subtitle}"
        button = QPushButton(text)
        button.setObjectName("SideNavActive" if active else "SideNav")
        button.setCursor(Qt.PointingHandCursor)
        return button

    def _activate_step(self, index: int) -> None:
        if index == 0:
            self._scroll_top()
        elif index == 1:
            self._scroll_to_widget(self.banner)
        elif index == 2:
            self.tabs.setCurrentIndex(4)
            self._scroll_to_widget(self.tabs)
        elif index == 3:
            self.tabs.setCurrentIndex(5)
            self._scroll_to_widget(self.tabs)
        else:
            self.tabs.setCurrentIndex(0)
            self._scroll_to_widget(self.tabs)

    def _scroll_top(self) -> None:
        self.main_scroll.verticalScrollBar().setValue(0)

    def _scroll_to_widget(self, widget: QWidget) -> None:
        self.main_scroll.ensureWidgetVisible(widget, 20, 20)

    def _choose_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Excel Dosyası Seç",
            str(self.project_root / "input"),
            "Excel Dosyaları (*.xlsx)",
        )
        if not path:
            return
        self.selected_excel = Path(path)
        self._add_activity("Excel Seçildi", "Başarılı", self.selected_excel.name)
        self._refresh_excel_status()

    def _run_dry(self) -> None:
        if not self._ensure_excel_selected():
            return
        self.last_command_name = "Dry-run Kontrolü"
        self._run_command(["src/main.py", "--excel", str(self.selected_excel), "--dry-run"])

    def _run_production(self) -> None:
        if self.current_readiness == "BLOKE":
            QMessageBox.warning(self, "Üretim bloke", "Kritik hatalar var. Önce Excel veya şablon hatalarını düzeltin.")
            return
        if not self.confirm_checkbox.isChecked():
            QMessageBox.warning(self, "Onay gerekli", "Önce onay kutusunu işaretleyin.")
            return
        if self.current_readiness == "KONTROL_GEREKLI":
            answer = QMessageBox.warning(
                self,
                "Kontrol gerekli",
                "Kontrol gerektiren satırlar var. Yine de yalnızca dosya ve rapor üretmek istiyor musunuz",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        if not self._ensure_excel_selected():
            return
        self.last_command_name = "Üretim Dosyaları"
        self._run_command(["src/main.py", "--excel", str(self.selected_excel)])

    def _render_labels(self) -> None:
        mode = self._print_mode()
        if mode != "label_designer":
            QMessageBox.information(
                self,
                "Etiket tasarım modu kapalı",
                "Etiket tasarım modu kapalı. Ayarlardan print.mode değerini label_designer yapın.",
            )
            self._append_log("Etiket tasarım modu kapalı. Ayarlardan print.mode değerini label_designer yapın.\n")
            return
        if self.current_readiness == "BLOKE":
            QMessageBox.warning(self, "Üretim bloke", "Kritik hatalar varken etiket çıktısı oluşturulamaz.")
            return
        if not self._ensure_excel_selected():
            return
        self.last_command_name = "Etiket PDF/PNG"
        self._run_command(["src/main.py", "--excel", str(self.selected_excel), "--render-labels"])

    def _create_template(self) -> None:
        self.last_command_name = "Temiz Excel Şablonu"
        self._run_command(["src/main.py", "--create-template"])

    def _create_demo(self) -> None:
        self.last_command_name = "Demo Excel"
        self._run_command(["src/main.py", "--create-demo"])

    def _convert_legacy_excel(self) -> None:
        if not self._ensure_excel_selected():
            return
        self.last_command_name = "Eski Excel Dönüştürme"
        self._run_command(["src/main.py", "--excel", str(self.selected_excel), "--convert-legacy-excel"])

    def _import_template_pack(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Şablon Paketi Yükle",
            str(self.project_root),
            "ZIP Paketleri (*.zip)",
        )
        if not path:
            return
        try:
            conflict_state = {"all": ""}
            result = safe_extract_template_pack(
                Path(path),
                self.project_root,
                conflict_handler=lambda _source, target: self._confirm_overwrite(target, conflict_state),
            )
        except TemplateImportError as exc:
            QMessageBox.warning(self, "Şablon paketi yüklenemedi", f"Şablon paketi yüklenemedi.\n\n{exc}")
            self._append_log(f"Şablon paketi yüklenemedi: {exc}\n")
            return
        self.last_import_preview = result.preview_path
        summary = (
            f"Şablon paketi başarıyla işlendi.\n\n"
            f"JSON şablon: {result.imported_templates}\n"
            f"Arka plan görseli: {result.imported_backgrounds}\n"
            f"Excel dosyası: {result.imported_excels}\n"
            f"Atlanan dosya: {result.skipped_files}\n"
            f"Hatalı dosya: {result.error_files}\n\n"
            f"Rapor: {result.report_path}"
        )
        QMessageBox.information(self, "Şablon paketi", summary)
        self._append_log(summary + "\n")
        self._add_activity("Şablon Paketi", "Başarılı", Path(path).name)
        self._refresh_static_status()
        self._load_reports()

    def _run_command(self, args: list[str]) -> None:
        if not self.python_exe.exists():
            QMessageBox.warning(
                self,
                "Python sanal ortamı bulunamadı",
                "Python sanal ortamı bulunamadı. Lütfen masaüstü kısayolunu yeniden açın veya start_cyzella.bat çalıştırın.",
            )
            return
        self.worker.run(args)

    def _command_started(self) -> None:
        self._append_log(f"\n--- {self.last_command_name or 'Komut'} başladı ---\n")

    def _command_finished(self, exit_code: int) -> None:
        status = "Başarılı" if exit_code == 0 else "Hata"
        self._append_log(f"--- {self.last_command_name or 'Komut'} bitti. Çıkış kodu: {exit_code} ---\n")
        self._add_activity(self.last_command_name or "Komut", status, f"Çıkış kodu: {exit_code}")
        self._refresh_excel_status()
        self._load_reports()
        if exit_code == 0:
            QMessageBox.information(self, "İşlem tamamlandı", f"{self.last_command_name or 'Komut'} tamamlandı.")
        else:
            QMessageBox.warning(self, "İşlem tamamlanamadı", "Komut çalışırken hata oluştu. Detaylar Günlük sekmesinde.")

    def _append_log(self, text: str) -> None:
        if not hasattr(self, "log_box"):
            return
        self.log_box.moveCursor(QTextCursor.End)
        self.log_box.insertPlainText(text)
        self.log_box.moveCursor(QTextCursor.End)

    def _refresh_static_status(self) -> None:
        font_path = self.project_root / "assets" / "fonts" / "connected_script.ttf"
        if font_path.exists():
            self.font_badge.setText("LAZER FONTU HAZIR\nİlk üretimden önce SVG kontrol edilmeli")
            self.font_badge.setObjectName("Pill_success")
        else:
            self.font_badge.setText("LAZER FONTU EKSİK\nFont yüklenmedi")
            self.font_badge.setObjectName("Pill_error")
        _repolish(self.font_badge)

    def _refresh_excel_status(self) -> None:
        name = self.selected_excel.name if self.selected_excel.exists() else "Excel seçilmedi"
        self.excel_name_top.setText(name)
        self.excel_name_top.setToolTip(str(self.selected_excel))
        if self.selected_excel.exists():
            self._add_activity("Excel Yüklendi", "Başarılı", name)

    def _load_reports(self) -> None:
        try:
            self.report_set = load_latest_reports(self.project_root)
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Raporlar okunamadı: {exc}\n")
            self.report_set = None
            return

        self.current_readiness = self._readiness_from_reports()
        self._update_status_banner()
        self._update_steps()
        self._update_summary_cards()
        self._update_error_preview()
        self._update_next_step()
        self._load_report_tabs()
        self._load_svg_list()
        self._load_activity_table()

    def _readiness_from_reports(self) -> str:
        if self.report_set is None:
            return "NO_CHECK"
        if not self.report_set.summary_rows and not self.report_set.error_rows and not self.report_set.review_rows:
            return "NO_CHECK"
        if self._non_empty_rows(self.report_set.error_rows):
            return "BLOKE"
        if self._non_empty_rows(self.report_set.review_rows):
            return "KONTROL_GEREKLI"
        return "HAZIR"

    def _update_status_banner(self) -> None:
        styles = {
            "NO_CHECK": ("HENÜZ KONTROL YAPILMADI", "Excel dosyasını seçin ve dry-run kontrolünü başlatın.", "Kontrolü Başlat", "neutral"),
            "BLOKE": ("ÜRETİM BLOKE", "Kritik hatalar düzeltilmeden üretim dosyası oluşturulamaz.", "Hatalar Sayfasına Git", "error"),
            "KONTROL_GEREKLI": ("KONTROL GEREKLİ", "Kontrol gerektiren satırlar var. Üretime geçmeden önce inceleyin.", "Kontrol Gerekli", "warning"),
            "HAZIR": ("ÜRETİME HAZIR", "Kontrol tamamlandı. Üretim dosyaları oluşturulabilir.", "Üretim Dosyalarını Oluştur", "success"),
        }
        title, text, button, status = styles[self.current_readiness]
        self.banner_title.setText(title)
        self.banner_text.setText(text)
        self.banner_button.setText(button)
        self.banner.setObjectName(f"StatusBanner_{status}")
        self.banner_button.clicked.disconnect()
        if self.current_readiness == "BLOKE":
            self.banner_button.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        elif self.current_readiness == "HAZIR":
            self.banner_button.clicked.connect(self._run_production)
        elif self.current_readiness == "KONTROL_GEREKLI":
            self.banner_button.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        else:
            self.banner_button.clicked.connect(self._run_dry)
        _repolish(self.banner)

    def _update_steps(self) -> None:
        states = ["Bekliyor"] * 5
        if self.selected_excel.exists():
            states[0] = "Veri Tamamlandı"
        if self.current_readiness == "NO_CHECK":
            states[1] = "Beklemede"
        elif self.current_readiness == "BLOKE":
            states[1] = "Bloke"
            states[2] = "Bloke"
            states[3] = "Bloke"
            states[4] = "Aktif"
        elif self.current_readiness == "KONTROL_GEREKLI":
            states[1] = "Kontrol Gerekli"
            states[2] = "Kontrol Gerekli"
            states[3] = "Kontrol Gerekli"
            states[4] = "Aktif"
        else:
            states[1] = "Tamamlandı"
            states[2] = "Hazır"
            states[3] = "Hazır"
            states[4] = "Aktif"

        for index, button in enumerate(self.step_buttons):
            button.setText(f"{index + 1}\n{STEP_NAMES[index]}\n{states[index]}")
            button.setProperty("state", self._state_property(states[index], index))
            _repolish(button)
        for index, button in enumerate(self.side_step_buttons):
            button.setText(f"{index + 1}  {STEP_NAMES[index]}\n{states[index]}")

    def _state_property(self, state: str, index: int) -> str:
        if index == 0 and self.selected_excel.exists():
            return "done"
        if state == "Bloke":
            return "blocked"
        if state == "Kontrol Gerekli":
            return "warning"
        if state in {"Tamamlandı", "Hazır", "Veri Tamamlandı"}:
            return "done"
        if index == 1 and self.current_readiness in {"NO_CHECK", "BLOKE", "KONTROL_GEREKLI"}:
            return "active"
        return "normal"

    def _update_summary_cards(self) -> None:
        values = self._summary_values()
        for key, label in self.summary_labels.items():
            label.setText(str(values.get(key, "0")))

    def _summary_values(self) -> dict[str, str]:
        if self.report_set is None or not self.report_set.summary_rows:
            return {}
        row = self.report_set.summary_rows[0]
        print_jobs = _as_int(row.get("print_jobs_count")) + _as_int(row.get("both_jobs_count"))
        laser_jobs = _as_int(row.get("laser_engrave_jobs_count")) + _as_int(row.get("laser_cut_jobs_count")) + _as_int(row.get("both_jobs_count"))
        review = len(self._non_empty_rows(self.report_set.review_rows))
        label_jobs = print_jobs
        return {
            "total_rows": row.get("total_rows", "0"),
            "valid_rows": row.get("valid_rows", "0"),
            "invalid_rows": row.get("invalid_rows", "0"),
            "print_jobs_count": str(print_jobs),
            "laser_jobs": str(laser_jobs),
            "review": str(review),
            "label_jobs": str(label_jobs),
        }

    def _update_error_preview(self) -> None:
        _clear_layout(self.errors_list)
        rows = self._non_empty_rows(self.report_set.error_rows if self.report_set else [])
        if not rows:
            self.errors_list.addWidget(self._issue_row("Kritik hata yok.", "Dry-run sonrası kritik hatalar burada görünür.", ""))
            return
        for row in rows[:5]:
            title, desc = self._friendly_issue(row)
            tag = f"Satır: {row.get('row_number', '-')}"
            self.errors_list.addWidget(self._issue_row(title, desc, tag))

    def _issue_row(self, title: str, desc: str, tag: str) -> QWidget:
        row = QFrame()
        row.setObjectName("IssueRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 8, 0, 8)
        dot = QLabel("")
        dot.setObjectName("IssueDot")
        text = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("IssueTitle")
        title_label.setWordWrap(True)
        desc_label = QLabel(desc)
        desc_label.setObjectName("IssueDesc")
        desc_label.setWordWrap(True)
        text.addWidget(title_label)
        text.addWidget(desc_label)
        tag_label = QLabel(tag)
        tag_label.setObjectName("RowTag")
        tag_label.setAlignment(Qt.AlignCenter)
        tag_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(dot)
        layout.addLayout(text, 1)
        if tag:
            layout.addWidget(tag_label)
        return row

    def _issue_title(self, row: dict[str, str]) -> str:
        order = row.get("order_no", "")
        field = row.get("field", "")
        message = row.get("message") or row.get("reason") or row.get("warning") or "Kontrol gerekli."
        prefix = f"Sipariş {order}: " if order else ""
        return f"{prefix}{field} - {message}" if field else f"{prefix}{message}"

    def _friendly_issue(self, row: dict[str, str]) -> tuple[str, str]:
        order = row.get("order_no", "").strip()
        field = row.get("field", "").strip()
        raw_message = row.get("message") or row.get("reason") or row.get("warning") or "Kontrol gerekli."
        message = self._strip_paths(raw_message)
        lower = raw_message.lower()
        prefix = f"Sipariş {order}: " if order else ""

        if "connected script font missing" in lower or "connected_script.ttf" in lower:
            return (
                prefix + "Lazer kesim fontu eksik.",
                "assets/fonts/connected_script.ttf dosyasını ekleyin. Font yokken LASER_CUT güvenlik için bloke edilir.",
            )
        if "missing label_text" in lower or (field == "label_text" and "missing" in lower):
            return (
                prefix + "Etiket yazısı eksik.",
                "Excel’de label_text kolonunu doldurun.",
            )
        if "missing print template" in lower or "label design template" in lower or field == "print_template":
            return (
                prefix + "Etiket şablonu bulunamadı.",
                "model_no, template_no ve label_variant değerlerini kontrol edin.",
            )
        if "invalid process_type" in lower:
            return (
                prefix + "İşlem tipi geçersiz.",
                "process_type alanını PRINT, LASER_ENGRAVE, LASER_CUT, BOTH veya NONE yapın.",
            )
        if "quantity" in lower and ("invalid" in lower or "positive" in lower):
            return (
                prefix + "Adet değeri geçersiz.",
                "quantity alanına 0’dan büyük bir sayı girin.",
            )
        if "laser_text" in field or "laser_text" in lower:
            return (
                prefix + "Lazer yazısı eksik veya hatalı.",
                "Excel’de laser_text kolonunu kontrol edin.",
            )
        if "customer_name" in lower or "buyer_name" in lower:
            return (
                prefix + "Alıcı adı eksik.",
                "Excel’de buyer_name kolonunu doldurun.",
            )
        return (prefix + self._turkish_field_label(field, message), "Excel veya şablon alanlarını kontrol edin.")

    def _strip_paths(self, text: str) -> str:
        text = re.sub(r"[A-Za-z]:\\[^\n\r,;]+", lambda match: Path(match.group(0)).name, text)
        return text.replace("\\", "/")

    def _turkish_field_label(self, field: str, message: str) -> str:
        labels = {
            "laser_text": "Lazer yazısı",
            "label_text": "Etiket yazısı",
            "buyer_name": "Alıcı adı",
            "quantity": "Adet",
            "process_type": "İşlem tipi",
            "print_template": "Etiket şablonu",
        }
        if field in labels:
            return f"{labels[field]} kontrol gerekli."
        return self._strip_paths(message)

    def _update_next_step(self) -> None:
        if self.current_readiness == "BLOKE":
            self.next_title.setText("Hataları düzeltin")
            self.next_text.setText("Hatalar sekmesindeki kritik hataları düzeltin. Excel dosyanızı güncelledikten sonra kontrolü tekrar çalıştırın.")
            self.production_button.setEnabled(False)
        elif self.current_readiness == "KONTROL_GEREKLI":
            self.next_title.setText("Kontrol gerektiren satırları inceleyin")
            self.next_text.setText("Üretime geçmeden önce kontrol gerektiren satırları inceleyin. Gerekirse Excel’i düzeltip dry-run çalıştırın.")
            self.production_button.setEnabled(True)
        elif self.current_readiness == "HAZIR":
            self.next_title.setText("Üretim dosyalarını oluşturabilirsiniz")
            self.next_text.setText("Raporlar temiz görünüyor. Onay kutusunu işaretleyip dosya ve rapor çıktısı oluşturabilirsiniz.")
            self.production_button.setEnabled(True)
        else:
            self.next_title.setText("Kontrolü başlatın")
            self.next_text.setText("Excel dosyasını seçin ve dry-run kontrolünü başlatın.")
            self.production_button.setEnabled(False)

    def _load_report_tabs(self) -> None:
        if self.report_set is None:
            return
        self.summary_text.setPlainText(self.report_set.human_summary or "Henüz kullanıcı dostu özet raporu oluşturulmadı.")
        self._fill_table(self.summary_table, self.report_set.summary_rows, "Henüz özet raporu oluşturulmadı.")
        self._fill_table(self.errors_table, self.report_set.error_rows, "Kritik hata yok.")
        self._fill_table(self.review_table, self.report_set.review_rows, "Kontrol gerektiren satır yok.")
        self._fill_table(self.template_table, self.report_set.template_rows, "Baskı/şablon eşleşme raporu bulunamadı.")
        self._fill_table(self.render_report_table, self._label_render_rows(), "Henüz etiket çıktısı yok.")
        self._fill_table(self.laser_report_table, self.report_set.material_rows, "Henüz lazer raporu oluşturulmadı.")

    def _fill_table(self, table: QTableWidget, rows: list[dict[str, str]], empty_message: str) -> None:
        table.clear()
        rows = self._non_empty_rows(rows)
        if not rows:
            table.setColumnCount(1)
            table.setRowCount(1)
            table.setHorizontalHeaderLabels(["Durum"])
            table.setItem(0, 0, QTableWidgetItem(empty_message))
            table.setRowHeight(0, 42)
            return
        headers = list(rows[0].keys())
        table.setColumnCount(len(headers))
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(rows):
            table.setRowHeight(row_index, 36)
            for column_index, header in enumerate(headers):
                table.setItem(row_index, column_index, QTableWidgetItem(str(row.get(header, ""))))
        table.resizeColumnsToContents()

    def _load_svg_list(self) -> None:
        self.svg_list.clear()
        if self.report_set is None or not self.report_set.svg_files:
            self.svg_list.addItem("Henüz lazer plakası yok.")
            self.svg_preview.svg_path = None
            self.svg_preview.message.setText("Henüz lazer plakası yok.")
            self.svg_preview.open_button.setVisible(False)
            return
        for path in self.report_set.svg_files:
            self.svg_list.addItem(str(path))

    def _select_svg(self, text: str) -> None:
        path = Path(text)
        if path.exists() and path.suffix.lower() == ".svg":
            self.svg_preview.load_svg(path)
        else:
            self.svg_preview.svg_path = None
            self.svg_preview.message.setText("SVG dosyası seçilmedi.")
            self.svg_preview.open_button.setVisible(False)

    def _open_selected_svg(self) -> None:
        if self.svg_preview.svg_path is None:
            QMessageBox.information(self, "SVG dosyası seçilmedi", "Önce listeden bir SVG plaka dosyası seçin.")
            return
        if not self.svg_preview.svg_path.exists():
            QMessageBox.warning(self, "SVG dosyası bulunamadı", f"SVG dosyası bulunamadı:\n{self.svg_preview.svg_path}")
            return
        if sys.platform.startswith("win"):
            os.startfile(self.svg_preview.svg_path)  # noqa: S606 - user-requested file opening.
        else:
            QMessageBox.information(self, "SVG açma", "SVG dosyasını açma sadece Windows için hazırlandı.")

    def _open_folder(self, path: Path) -> None:
        ok, message = open_folder(path)
        if not ok:
            QMessageBox.information(self, "Klasör", message)
        self._append_log(message + "\n")

    def _show_help_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Nasıl Kullanırım")
        dialog.setMinimumWidth(520)
        layout = QVBoxLayout(dialog)
        title = QLabel("CeyizHome Lab Kullanımı")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)
        steps = [
            "1. Excel dosyanızı seçin.",
            "2. Dry-run kontrolünü başlatın.",
            "3. Hatalar varsa Excel veya şablon dosyalarını düzeltin.",
            "4. Raporlar temizse üretim dosyalarını oluşturun.",
            "5. PDF/PNG/SVG dosyalarını manuel kontrol edip kendi programınızda kullanın.",
        ]
        text = QLabel("\n".join(steps) + "\n\nGüvenlik: CorelDRAW, yazıcı, RDWorks ve lazer otomatik çalışmaz.")
        text.setObjectName("DialogText")
        text.setWordWrap(True)
        layout.addWidget(text)
        close = QPushButton("Tamam")
        close.setObjectName("PrimaryButton")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close, 0, Qt.AlignRight)
        dialog.exec()

    def _show_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.project_root, self)
        dialog.saved.connect(self._settings_saved)
        dialog.exec()

    def _show_template_editor(self) -> None:
        dialog = LabelTemplateEditorDialog(self.project_root, self)
        dialog.saved.connect(self._template_editor_saved)
        dialog.exec()

    def _template_editor_saved(self) -> None:
        self._append_log("Etiket şablonu kaydedildi veya önizleme oluşturuldu.\n")
        self._refresh_static_status()
        self._load_reports()

    def _settings_saved(self) -> None:
        self._append_log("Rulo etiket ayarları kaydedildi.\n")
        self._refresh_static_status()

    def _set_theme(self, dark: bool) -> None:
        self.dark_mode = dark
        app = QApplication.instance()
        style_path = Path(__file__).with_name("style.qss")
        if style_path.exists() and app is not None:
            base = style_path.read_text(encoding="utf-8")
            app.setStyleSheet(base + ("\n" + DARK_QSS if dark else ""))
        self.day_button.setObjectName("ThemeOption" if dark else "ThemeActive")
        self.night_button.setObjectName("ThemeActive" if dark else "ThemeOption")
        _repolish(self.day_button)
        _repolish(self.night_button)

    def _ensure_excel_selected(self) -> bool:
        if not self.selected_excel.exists():
            QMessageBox.warning(self, "Excel dosyası seçilmedi", "Excel dosyası seçilmedi veya bulunamadı.")
            return False
        return True

    def _print_mode(self) -> str:
        try:
            data = yaml.safe_load((self.project_root / "config" / "settings.yaml").read_text(encoding="utf-8")) or {}
            return str(data.get("print", {}).get("mode", "data_only")).strip()
        except Exception:
            return "data_only"

    def _confirm_overwrite(self, target_path: Path, conflict_state: dict[str, str]) -> str:
        if conflict_state.get("all") in {"overwrite", "skip"}:
            return conflict_state["all"]
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Question)
        message.setWindowTitle("Dosya zaten var")
        message.setText(f"Bu dosya zaten var. Üzerine yazılsın mı\n\n{target_path.name}")
        message.setInformativeText("Güvenli varsayılan seçenek atlamaktır.")
        message.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.YesToAll | QMessageBox.NoToAll)
        message.setDefaultButton(QMessageBox.No)
        choice = message.exec()
        if choice == QMessageBox.YesToAll:
            conflict_state["all"] = "overwrite"
            return "overwrite"
        if choice == QMessageBox.NoToAll:
            conflict_state["all"] = "skip"
            return "skip"
        return "overwrite" if choice == QMessageBox.Yes else "skip"

    def _label_render_rows(self) -> list[dict[str, str]]:
        print_dir = self._print_dir()
        rows: list[dict[str, str]] = []
        for path in [print_dir / "label_render_report.csv", *sorted(print_dir.glob("model_*/rendered/label_render_report.csv"))]:
            rows.extend(_read_csv(path))
        return rows

    def _print_dir(self) -> Path:
        run_dir = latest_run_dir(self.project_root)
        lower = run_dir / "print"
        upper = run_dir / "PRINT"
        return lower if lower.exists() else upper

    def _add_activity(self, action: str, status: str, detail: str) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        item = (now, action, status, detail)
        if self.activity_rows and self.activity_rows[-1] == item:
            return
        self.activity_rows.append(item)
        self.activity_rows = self.activity_rows[-10:]
        if hasattr(self, "activity_table"):
            self._load_activity_table()

    def _load_activity_table(self) -> None:
        rows = [
            {"Zaman": time, "İşlem": action, "Durum": status, "Detay": detail}
            for time, action, status, detail in reversed(self.activity_rows)
        ]
        self._fill_table(self.activity_table, rows, "Henüz işlem kaydı yok.")

    def _non_empty_rows(self, rows: list[dict[str, str]]) -> list[dict[str, str]]:
        return [row for row in rows if any((value or "").strip() for value in row.values())]


class SettingsDialog(QDialog):
    saved = Signal()

    def __init__(self, project_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_root = project_root
        self.fields: dict[str, QLineEdit] = {}
        self.checks: dict[str, QCheckBox] = {}
        self.setWindowTitle("Ayarlar")
        self.setMinimumWidth(620)
        self._build()
        self._load()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Rulo Etiket Varsayılanları")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        labels = [
            ("label_width_mm", "Etiket genişliği (mm)"),
            ("label_height_mm", "Etiket yüksekliği (mm)"),
            ("roll_gap_mm", "Etiket aralığı / gap (mm)"),
            ("printer_dpi", "Yazıcı DPI"),
            ("default_copies", "Varsayılan adet"),
            ("horizontal_offset_mm", "Yatay kaydırma (mm)"),
            ("vertical_offset_mm", "Dikey kaydırma (mm)"),
            ("scale_percent", "Ölçek (%)"),
            ("safe_margin_mm", "Güvenli iç boşluk (mm)"),
        ]
        for row, (key, text) in enumerate(labels):
            label = QLabel(text)
            editor = QLineEdit()
            self.fields[key] = editor
            grid.addWidget(label, row, 0)
            grid.addWidget(editor, row, 1)
        layout.addLayout(grid)
        for key, text in [
            ("background_enabled", "Arka plan kullan"),
            ("show_cut_boundary", "Kesim sınırını göster"),
            ("show_order_number_on_label", "Etikette sipariş numarası göster"),
        ]:
            check = QCheckBox(text)
            self.checks[key] = check
            layout.addWidget(check)
        buttons = QHBoxLayout()
        save = QPushButton("Ayarları Kaydet")
        save.setObjectName("PrimaryButton")
        reset = QPushButton("Varsayılana Sıfırla")
        reset.setObjectName("LightButton")
        save.clicked.connect(self._save)
        reset.clicked.connect(self._reset)
        buttons.addStretch()
        buttons.addWidget(reset)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _load(self) -> None:
        defaults = self._config().get("label_defaults", {}) or {}
        fallback = self._fallback()
        for key, editor in self.fields.items():
            editor.setText(str(defaults.get(key, fallback[key])))
        for key, check in self.checks.items():
            check.setChecked(bool(defaults.get(key, fallback[key])))

    def _reset(self) -> None:
        fallback = self._fallback()
        for key, editor in self.fields.items():
            editor.setText(str(fallback[key]))
        for key, check in self.checks.items():
            check.setChecked(bool(fallback[key]))

    def _save(self) -> None:
        try:
            values = self._values()
        except ValueError as exc:
            QMessageBox.warning(self, "Ayar hatası", str(exc))
            return
        data = self._config()
        print_data = data.setdefault("print", {})
        print_data.setdefault("mode", "data_only")
        print_data["allow_direct_print"] = False
        print_data["require_print_confirmation"] = True
        print_data["use_default_label_settings"] = True
        print_data.setdefault("default_printer", "")
        data["label_defaults"] = {"media_type": "ROLL", **values}
        save_config(self.project_root, data)
        QMessageBox.information(self, "Ayarlar kaydedildi", "Rulo etiket varsayılanları kaydedildi.")
        self.saved.emit()
        self.accept()

    def _values(self) -> dict[str, object]:
        width = self._float("label_width_mm", positive=True)
        height = self._float("label_height_mm", positive=True)
        dpi = int(self._float("printer_dpi", positive=True))
        if dpi not in {203, 300, 600}:
            QMessageBox.warning(self, "DPI uyarısı", "Yazıcı DPI standart değerlerden farklı. Test baskısı yapın.")
        scale = self._float("scale_percent", positive=True)
        if scale != 100:
            QMessageBox.warning(self, "Ölçek uyarısı", "Etiket baskısında ölçek genelde %100 olmalıdır. Lütfen test baskısı yapın.")
        return {
            "label_width_mm": width,
            "label_height_mm": height,
            "roll_gap_mm": self._float("roll_gap_mm", non_negative=True),
            "printer_dpi": dpi,
            "default_copies": int(self._float("default_copies", positive=True)),
            "horizontal_offset_mm": self._float("horizontal_offset_mm"),
            "vertical_offset_mm": self._float("vertical_offset_mm"),
            "scale_percent": scale,
            "safe_margin_mm": self._float("safe_margin_mm", non_negative=True),
            "background_enabled": self.checks["background_enabled"].isChecked(),
            "show_cut_boundary": self.checks["show_cut_boundary"].isChecked(),
            "show_order_number_on_label": self.checks["show_order_number_on_label"].isChecked(),
        }

    def _float(self, key: str, positive: bool = False, non_negative: bool = False) -> float:
        text = self.fields[key].text().strip().replace(",", ".")
        try:
            value = float(text)
        except ValueError as exc:
            raise ValueError(f"{key} sayı olmalıdır.") from exc
        if positive and value <= 0:
            raise ValueError(f"{key} 0'dan büyük olmalıdır.")
        if non_negative and value < 0:
            raise ValueError(f"{key} negatif olamaz.")
        return value

    def _config(self) -> dict:
        path = self.project_root / "config" / "settings.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _fallback(self) -> dict[str, object]:
        return {
            "label_width_mm": 50,
            "label_height_mm": 30,
            "roll_gap_mm": 3,
            "printer_dpi": 300,
            "default_copies": 1,
            "horizontal_offset_mm": 0,
            "vertical_offset_mm": 0,
            "scale_percent": 100,
            "safe_margin_mm": 1.5,
            "background_enabled": True,
            "show_cut_boundary": False,
            "show_order_number_on_label": False,
        }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _as_int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


DARK_QSS = """
QWidget#AppShell, QScrollArea#MainScroll, QWidget#MainContent { background: #111318; }
QFrame#Sidebar, QFrame#Topbar, QFrame#Card, QFrame#ExcelCard { background: #1a1d24; border-color: #2a2f3a; }
QLabel, QPushButton, QTableWidget, QTextEdit { color: #f9fafb; }
QLabel#PageSubtitle, QLabel#SmallMuted, QLabel#MutedText, QLabel#IssueDesc { color: #a1a7b3; }
QPushButton#LightButton, QPushButton#HeaderButton, QPushButton#QuickButton, QPushButton#SideButton {
    background: #20242c; color: #f9fafb; border-color: #2a2f3a;
}
QTableWidget, QTextEdit#ReportText { background: #1a1d24; color: #f9fafb; border-color: #2a2f3a; }
"""
