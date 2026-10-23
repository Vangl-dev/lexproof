"""Theme manager for LexProof.

All colors are derived from QPalette — no hardcoded hex values in QSS.
QSS covers layout properties: rounded corners, spacing, margins, animations.
"""

from __future__ import annotations

import enum

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class ThemeMode(enum.Enum):
    """Available theme modes."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ThemeManager:
    """Manages application themes via QPalette and Fusion style.

    All colors are derived from QPalette — no hardcoded hex values in QSS.
    QSS is limited to layout properties: rounded corners, spacing, margins,
    scrollbar dimensions.
    """

    _instance: ThemeManager | None = None

    def __init__(self) -> None:
        self._current_mode: ThemeMode = ThemeMode.SYSTEM

    @classmethod
    def instance(cls) -> ThemeManager:
        """Return the singleton ThemeManager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_mode(self) -> ThemeMode:
        return self._current_mode

    def set_mode(self, mode: ThemeMode) -> None:
        """Set the active theme mode."""
        self._current_mode = mode

    def is_dark(self) -> bool:
        """Detect if current theme is dark using QPalette."""
        app = QApplication.instance()
        if app is None:
            return False
        palette = app.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        brightness = (
            window_color.red() * 299 + window_color.green() * 587 + window_color.blue() * 114
        ) / 1000
        return brightness < 128

    def apply_theme(self) -> None:
        """Apply Fusion style + system palette + minimal QSS."""
        app = QApplication.instance()
        if app is None:
            return

        app.setStyle("Fusion")

        if self._current_mode == ThemeMode.DARK:
            palette = self._dark_palette()
        elif self._current_mode == ThemeMode.LIGHT:
            palette = self._light_palette()
        else:
            palette = app.style().standardPalette()

        app.setPalette(palette)
        app.setStyleSheet(self._minimal_stylesheet())

    def get_stylesheet(self, theme: str | None = None) -> str:
        """Return the minimal stylesheet.

        If *theme* is provided, the corresponding mode is applied first.
        Otherwise the current mode is used.
        """
        if theme is not None:
            self._current_mode = (
                ThemeMode.DARK if theme.lower() == "dark" else ThemeMode.LIGHT
            )
        self.apply_theme()
        return self._minimal_stylesheet()

    def _dark_palette(self) -> QPalette:
        """Create a refined dark palette."""
        palette = QPalette()

        # Base
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 31, 34))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(219, 222, 225))
        palette.setColor(QPalette.ColorRole.Base, QColor(37, 39, 42))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(44, 46, 51))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(44, 46, 51))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(219, 222, 225))
        palette.setColor(QPalette.ColorRole.Text, QColor(219, 222, 225))
        palette.setColor(QPalette.ColorRole.Button, QColor(44, 46, 51))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(219, 222, 225))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 85, 85))

        # Accent
        palette.setColor(QPalette.ColorRole.Link, QColor(88, 166, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(88, 166, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

        # Mid tones
        palette.setColor(QPalette.ColorRole.Dark, QColor(28, 29, 33))
        palette.setColor(QPalette.ColorRole.Mid, QColor(63, 65, 72))
        palette.setColor(QPalette.ColorRole.Light, QColor(70, 72, 79))
        palette.setColor(QPalette.ColorRole.Midlight, QColor(55, 57, 63))

        # Placeholder / shadow
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(126, 130, 137))
        palette.setColor(QPalette.ColorRole.Shadow, QColor(0, 0, 0, 80))

        # Disabled
        disabled = QColor(90, 93, 98)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled)

        return palette

    def _light_palette(self) -> QPalette:
        """Create a refined light palette."""
        palette = QPalette()

        # Base
        palette.setColor(QPalette.ColorRole.Window, QColor(247, 248, 250))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(36, 41, 46))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(243, 244, 246))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(36, 41, 46))
        palette.setColor(QPalette.ColorRole.Text, QColor(36, 41, 46))
        palette.setColor(QPalette.ColorRole.Button, QColor(243, 244, 246))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(36, 41, 46))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(220, 38, 38))

        # Accent
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 102, 204))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 102, 204))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

        # Mid tones
        palette.setColor(QPalette.ColorRole.Dark, QColor(209, 213, 219))
        palette.setColor(QPalette.ColorRole.Mid, QColor(209, 213, 219))
        palette.setColor(QPalette.ColorRole.Light, QColor(229, 231, 235))
        palette.setColor(QPalette.ColorRole.Midlight, QColor(220, 222, 226))

        # Placeholder / shadow
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(156, 163, 175))
        palette.setColor(QPalette.ColorRole.Shadow, QColor(0, 0, 0, 30))

        # Disabled
        disabled = QColor(156, 163, 175)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled)

        return palette

    def _minimal_stylesheet(self) -> str:
        """Return minimal QSS with NO color values — only layout properties."""
        return """
            /* === GLOBAL === */
            QWidget {
                font-size: 13px;
            }

            /* === BUTTONS === */
            QPushButton {
                border-radius: 6px;
                padding: 6px 16px;
                min-height: 24px;
                font-weight: 500;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QPushButton:pressed {
                padding-top: 7px;
                padding-bottom: 5px;
            }
            QPushButton:disabled {
                opacity: 0.5;
            }

            /* === INPUTS === */
            QLineEdit, QTextEdit, QPlainTextEdit {
                border-radius: 6px;
                padding: 6px 10px;
                border: 1px solid palette(mid);
                selection-background-color: palette(highlight);
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
                border: 1px solid palette(highlight);
            }

            /* === COMBOBOX === */
            QComboBox {
                border-radius: 6px;
                padding: 6px 10px;
                border: 1px solid palette(mid);
            }
            QComboBox:focus {
                border: 1px solid palette(highlight);
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }

            /* === PROGRESS === */
            QProgressBar {
                border-radius: 4px;
                max-height: 6px;
                background-color: palette(mid);
                border: none;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background-color: palette(highlight);
            }

            /* === TABS === */
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                font-weight: 600;
            }

            /* === MENUS === */
            QMenu {
                border-radius: 8px;
                padding: 4px;
                border: 1px solid palette(mid);
            }
            QMenu::item {
                border-radius: 4px;
                margin: 2px 4px;
                padding: 6px 24px 6px 12px;
            }
            QMenu::item:selected {
                background-color: palette(highlight);
                color: palette(highlightedText);
            }

            /* === TOOLTIPS === */
            QToolTip {
                border-radius: 6px;
                padding: 4px 8px;
                border: 1px solid palette(mid);
            }

            /* === SCROLLBARS === */
            QScrollBar:vertical {
                width: 8px;
                border-radius: 4px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                border-radius: 4px;
                min-height: 30px;
                background: palette(mid);
            }
            QScrollBar::handle:vertical:hover {
                background: palette(dark);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                height: 8px;
                border-radius: 4px;
                background: transparent;
            }
            QScrollBar::handle:horizontal {
                border-radius: 4px;
                min-width: 30px;
                background: palette(mid);
            }
            QScrollBar::handle:horizontal:hover {
                background: palette(dark);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }

            /* === SPLITTER === */
            QSplitter::handle:horizontal {
                width: 1px;
                background: palette(mid);
            }
            QSplitter::handle:vertical {
                height: 1px;
                background: palette(mid);
            }
            QSplitter::handle:hover {
                background: palette(highlight);
            }

            /* === NAVIGATION RAIL === */
            QWidget#navigationRail {
                border-radius: 0px;
            }

            /* === CARDS === */
            QFrame#card {
                border-radius: 10px;
                padding: 16px;
                border: 1px solid palette(mid);
            }

            /* === MENU BAR === */
            QMenuBar {
                padding: 2px;
                border-bottom: 1px solid palette(mid);
            }
            QMenuBar::item {
                padding: 4px 10px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: palette(highlight);
                color: palette(highlightedText);
            }

            /* === STATUS BAR === */
            QStatusBar {
                padding: 2px 8px;
                border-top: 1px solid palette(mid);
            }

            /* === SCROLL AREA === */
            QScrollArea {
                border: none;
                background: transparent;
            }

            /* === CHECKBOX === */
            QCheckBox {
                spacing: 8px;
            }

            /* === GROUP BOX === */
            QGroupBox {
                font-weight: 600;
                border: 1px solid palette(mid);
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
        """
