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
        """Create a proper dark palette."""
        palette = QPalette()

        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)

        disabled = QColor(127, 127, 127)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled)

        return palette

    def _light_palette(self) -> QPalette:
        """Create a proper light palette."""
        palette = QPalette()

        palette.setColor(QPalette.ColorRole.Window, QColor(250, 250, 250))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Text, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Button, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 102, 204))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 102, 204))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)

        disabled = QColor(160, 160, 160)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled)

        return palette

    def _minimal_stylesheet(self) -> str:
        """Return minimal QSS with NO color values — only layout properties."""
        return """
            /* ROUNDED CORNERS */
            QPushButton { border-radius: 6px; padding: 6px 16px; }
            QLineEdit { border-radius: 6px; padding: 6px 10px; }
            QTextEdit, QPlainTextEdit { border-radius: 6px; padding: 6px; }
            QTreeView, QListView { border-radius: 6px; padding: 4px; }
            QComboBox { border-radius: 6px; padding: 6px 10px; }
            QProgressBar { border-radius: 4px; max-height: 6px; }
            QProgressBar::chunk { border-radius: 4px; }
            QTabBar::tab { border-top-left-radius: 8px; border-top-right-radius: 8px; padding: 8px 16px; margin-right: 2px; }
            QMenu { border-radius: 8px; padding: 4px; }
            QMenu::item { border-radius: 4px; margin: 2px 4px; padding: 6px 24px 6px 12px; }
            QToolTip { border-radius: 6px; padding: 4px 8px; }

            /* SPACING */
            QMenuBar { padding: 2px; }
            QMenuBar::item { padding: 4px 10px; border-radius: 4px; }
            QStatusBar { padding: 2px 8px; }
            QDockWidget::title { padding: 6px 10px; }

            /* SCROLLBARS */
            QScrollBar:vertical { width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { border-radius: 4px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar:horizontal { height: 8px; border-radius: 4px; }
            QScrollBar::handle:horizontal { border-radius: 4px; min-width: 30px; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

            /* SPLITTER */
            QSplitter::handle:horizontal { width: 2px; }
            QSplitter::handle:vertical { height: 2px; }

            /* NAVIGATION RAIL */
            QWidget#navigationRail { border-radius: 12px; padding: 8px 4px; }

            /* CARDS */
            QFrame#card { border-radius: 10px; padding: 16px; }
        """
