from __future__ import annotations

import enum
import platform
from typing import Final


class ThemeMode(enum.Enum):
    """Available theme modes."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ThemeColors:
    """Color definitions for light and dark themes."""

    # --- Light theme ---
    LIGHT_BG: Final[str] = "#FFFFFF"
    LIGHT_SURFACE: Final[str] = "#F5F5F5"
    LIGHT_BORDER: Final[str] = "#E0E0E0"
    LIGHT_BORDER_SUBTLE: Final[str] = "#ECECEC"
    LIGHT_TEXT_PRIMARY: Final[str] = "#1A1A1A"
    LIGHT_TEXT_SECONDARY: Final[str] = "#666666"
    LIGHT_TEXT_DISABLED: Final[str] = "#AAAAAA"
    LIGHT_ACCENT: Final[str] = "#0078D4"
    LIGHT_ACCENT_HOVER: Final[str] = "#106EBE"
    LIGHT_ACCENT_PRESSED: Final[str] = "#005A9E"
    LIGHT_ACCENT_LIGHT: Final[str] = "#E8F4FD"
    LIGHT_DANGER: Final[str] = "#D13438"
    LIGHT_WARNING: Final[str] = "#FFB900"
    LIGHT_SUCCESS: Final[str] = "#107C10"
    LIGHT_DEBUG: Final[str] = "#8661C5"
    LIGHT_SHADOW: Final[str] = "rgba(0, 0, 0, 0.08)"
    LIGHT_TAB_BG: Final[str] = "#F0F0F0"
    LIGHT_SIDEBAR_BG: Final[str] = "#F8F8F8"
    LIGHT_INPUT_BG: Final[str] = "#FFFFFF"
    LIGHT_LOG_BG: Final[str] = "#FAFAFA"

    # --- Dark theme ---
    DARK_BG: Final[str] = "#1E1E1E"
    DARK_SURFACE: Final[str] = "#2D2D2D"
    DARK_BORDER: Final[str] = "#404040"
    DARK_BORDER_SUBTLE: Final[str] = "#353535"
    DARK_TEXT_PRIMARY: Final[str] = "#E0E0E0"
    DARK_TEXT_SECONDARY: Final[str] = "#999999"
    DARK_TEXT_DISABLED: Final[str] = "#666666"
    DARK_ACCENT: Final[str] = "#60CDFF"
    DARK_ACCENT_HOVER: Final[str] = "#3DB8FF"
    DARK_ACCENT_PRESSED: Final[str] = "#0098FF"
    DARK_ACCENT_LIGHT: Final[str] = "#1A3A4A"
    DARK_DANGER: Final[str] = "#FF6B6B"
    DARK_WARNING: Final[str] = "#FFD33D"
    DARK_SUCCESS: Final[str] = "#6CCF5A"
    DARK_DEBUG: Final[str] = "#B490E0"
    DARK_SHADOW: Final[str] = "rgba(0, 0, 0, 0.24)"
    DARK_TAB_BG: Final[str] = "#252525"
    DARK_SIDEBAR_BG: Final[str] = "#252525"
    DARK_INPUT_BG: Final[str] = "#333333"
    DARK_LOG_BG: Final[str] = "#282828"


def _system_is_dark() -> bool:
    """Detect whether the OS is using a dark theme."""
    if platform.system() == "Darwin":
        import subprocess

        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return "Dark" in result.stdout
        except Exception:
            return False
    return False


class ThemeManager:
    """Manages application themes and provides styled stylesheets."""

    _instance: ThemeManager | None = None

    def __init__(self) -> None:
        self._current_mode: ThemeMode = ThemeMode.SYSTEM
        self._colors = ThemeColors()

    @classmethod
    def instance(cls) -> ThemeManager:
        """Return the singleton ThemeManager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_mode(self) -> ThemeMode:
        return self._current_mode

    @property
    def is_dark(self) -> bool:
        if self._current_mode == ThemeMode.DARK:
            return True
        if self._current_mode == ThemeMode.LIGHT:
            return False
        return _system_is_dark()

    def set_mode(self, mode: ThemeMode) -> None:
        self._current_mode = mode

    def get_stylesheet(self, theme: str | None = None) -> str:
        """Return the full application stylesheet for the given theme."""
        if theme is not None:
            is_dark = theme.lower() == "dark"
        else:
            is_dark = self.is_dark

        c = self._colors
        if is_dark:
            return self._dark_stylesheet(c)
        return self._light_stylesheet(c)

    def _font_family(self) -> str:
        family = "Segoe UI"
        if platform.system() == "Darwin":
            family = "SF Pro Text"
        elif platform.system() == "Linux":
            family = "Noto Sans"
        return family

    def _light_stylesheet(self, c: ThemeColors) -> str:
        ff = self._font_family()
        return f"""
            /* ===== Global ===== */
            * {{
                font-family: "{ff}", "Segoe UI Variable", "Helvetica Neue", sans-serif;
                font-size: 13px;
                color: {c.LIGHT_TEXT_PRIMARY};
            }}
            QMainWindow, QWidget#centralWidget {{
                background-color: {c.LIGHT_BG};
                border: none;
            }}

            /* ===== MenuBar ===== */
            QMenuBar {{
                background-color: {c.LIGHT_BG};
                border-bottom: 1px solid {c.LIGHT_BORDER};
                padding: 2px 4px;
                spacing: 2px;
            }}
            QMenuBar::item {{
                background: transparent;
                padding: 6px 12px;
                border-radius: 6px;
            }}
            QMenuBar::item:selected {{
                background-color: {c.LIGHT_ACCENT_LIGHT};
                color: {c.LIGHT_ACCENT};
            }}
            QMenu {{
                background-color: {c.LIGHT_BG};
                border: 1px solid {c.LIGHT_BORDER};
                border-radius: 8px;
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 8px 32px 8px 16px;
                border-radius: 4px;
                margin: 2px 4px;
            }}
            QMenu::item:selected {{
                background-color: {c.LIGHT_ACCENT_LIGHT};
                color: {c.LIGHT_ACCENT};
            }}
            QMenu::separator {{
                height: 1px;
                background: {c.LIGHT_BORDER};
                margin: 4px 8px;
            }}

            /* ===== TabWidget / TabBar ===== */
            QTabWidget::pane {{
                border: 1px solid {c.LIGHT_BORDER};
                border-radius: 8px;
                background: {c.LIGHT_BG};
                top: -1px;
            }}
            QTabBar {{
                background: transparent;
            }}
            QTabBar::tab {{
                background: {c.LIGHT_TAB_BG};
                color: {c.LIGHT_TEXT_SECONDARY};
                border: 1px solid {c.LIGHT_BORDER_SUBTLE};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 20px;
                margin-right: 2px;
                min-width: 100px;
            }}
            QTabBar::tab:selected {{
                background: {c.LIGHT_BG};
                color: {c.LIGHT_ACCENT};
                border-color: {c.LIGHT_BORDER};
                font-weight: 600;
            }}
            QTabBar::tab:hover:!selected {{
                background: {c.LIGHT_ACCENT_LIGHT};
                color: {c.LIGHT_TEXT_PRIMARY};
            }}
            QTabBar::close-button {{
                image: none;
                subcontrol-position: right;
                padding: 2px;
                border-radius: 4px;
            }}
            QTabBar::close-button:hover {{
                background: {c.LIGHT_DANGER};
            }}

            /* ===== DockWidget ===== */
            QDockWidget {{
                titlebar-close-icon: none;
                font-weight: 600;
                font-size: 12px;
                color: {c.LIGHT_TEXT_SECONDARY};
            }}
            QDockWidget::title {{
                background: {c.LIGHT_SURFACE};
                padding: 8px 12px;
                border-top: 1px solid {c.LIGHT_BORDER_SUBTLE};
                border-bottom: 1px solid {c.LIGHT_BORDER_SUBTLE};
            }}

            /* ===== StatusBar ===== */
            QStatusBar {{
                background-color: {c.LIGHT_SURFACE};
                border-top: 1px solid {c.LIGHT_BORDER_SUBTLE};
                padding: 2px 8px;
                color: {c.LIGHT_TEXT_SECONDARY};
                font-size: 12px;
            }}
            QStatusBar::item {{
                border: none;
            }}

            /* ===== PushButton ===== */
            QPushButton {{
                background-color: {c.LIGHT_ACCENT};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 500;
                min-height: 16px;
            }}
            QPushButton:hover {{
                background-color: {c.LIGHT_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {c.LIGHT_ACCENT_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {c.LIGHT_BORDER};
                color: {c.LIGHT_TEXT_DISABLED};
            }}
            QPushButton#secondaryButton, QPushButton[flat="true"] {{
                background-color: transparent;
                color: {c.LIGHT_ACCENT};
                border: 1px solid {c.LIGHT_BORDER};
            }}
            QPushButton#secondaryButton:hover, QPushButton[flat="true"]:hover {{
                background-color: {c.LIGHT_ACCENT_LIGHT};
            }}

            /* ===== LineEdit ===== */
            QLineEdit {{
                background-color: {c.LIGHT_INPUT_BG};
                border: 1px solid {c.LIGHT_BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                selection-background-color: {c.LIGHT_ACCENT_LIGHT};
                selection-color: {c.LIGHT_ACCENT};
            }}
            QLineEdit:focus {{
                border: 2px solid {c.LIGHT_ACCENT};
            }}
            QLineEdit:disabled {{
                background-color: {c.LIGHT_SURFACE};
                color: {c.LIGHT_TEXT_DISABLED};
            }}

            /* ===== TextEdit / PlainTextEdit ===== */
            QTextEdit, QPlainTextEdit {{
                background-color: {c.LIGHT_INPUT_BG};
                border: 1px solid {c.LIGHT_BORDER};
                border-radius: 6px;
                padding: 8px;
                selection-background-color: {c.LIGHT_ACCENT_LIGHT};
            }}
            QTextEdit:focus, QPlainTextEdit:focus {{
                border: 2px solid {c.LIGHT_ACCENT};
            }}

            /* ===== TreeView ===== */
            QTreeView {{
                background-color: {c.LIGHT_BG};
                border: 1px solid {c.LIGHT_BORDER};
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}
            QTreeView::item {{
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QTreeView::item:selected {{
                background-color: {c.LIGHT_ACCENT_LIGHT};
                color: {c.LIGHT_ACCENT};
            }}
            QTreeView::item:hover {{
                background-color: {c.LIGHT_SURFACE};
            }}
            QTreeView::branch {{
                background: transparent;
            }}
            QHeaderView::section {{
                background-color: {c.LIGHT_SURFACE};
                border: none;
                border-bottom: 1px solid {c.LIGHT_BORDER};
                border-right: 1px solid {c.LIGHT_BORDER_SUBTLE};
                padding: 6px 12px;
                font-weight: 600;
                color: {c.LIGHT_TEXT_SECONDARY};
            }}

            /* ===== Splitter ===== */
            QSplitter::handle {{
                background: {c.LIGHT_BORDER_SUBTLE};
            }}
            QSplitter::handle:horizontal {{
                width: 3px;
                margin: 4px 0px;
                border-radius: 1px;
            }}
            QSplitter::handle:vertical {{
                height: 3px;
                margin: 0px 4px;
                border-radius: 1px;
            }}
            QSplitter::handle:hover {{
                background: {c.LIGHT_ACCENT};
            }}

            /* ===== ProgressBar ===== */
            QProgressBar {{
                background-color: {c.LIGHT_SURFACE};
                border: none;
                border-radius: 4px;
                text-align: center;
                color: {c.LIGHT_TEXT_SECONDARY};
                font-size: 11px;
                min-height: 8px;
                max-height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {c.LIGHT_ACCENT};
                border-radius: 4px;
            }}

            /* ===== Label ===== */
            QLabel {{
                background: transparent;
                border: none;
                color: {c.LIGHT_TEXT_PRIMARY};
            }}
            QLabel#headingLabel {{
                font-size: 18px;
                font-weight: 700;
            }}
            QLabel#subheadingLabel {{
                font-size: 13px;
                color: {c.LIGHT_TEXT_SECONDARY};
            }}

            /* ===== ComboBox ===== */
            QComboBox {{
                background-color: {c.LIGHT_INPUT_BG};
                border: 1px solid {c.LIGHT_BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border: 1px solid {c.LIGHT_ACCENT};
            }}
            QComboBox:focus {{
                border: 2px solid {c.LIGHT_ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c.LIGHT_BG};
                border: 1px solid {c.LIGHT_BORDER};
                border-radius: 8px;
                padding: 4px;
                selection-background-color: {c.LIGHT_ACCENT_LIGHT};
            }}

            /* ===== CheckBox ===== */
            QCheckBox {{
                spacing: 8px;
                color: {c.LIGHT_TEXT_PRIMARY};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {c.LIGHT_BORDER};
                border-radius: 4px;
                background-color: {c.LIGHT_INPUT_BG};
            }}
            QCheckBox::indicator:hover {{
                border-color: {c.LIGHT_ACCENT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {c.LIGHT_ACCENT};
                border-color: {c.LIGHT_ACCENT};
            }}

            /* ===== ScrollBar ===== */
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 0;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {c.LIGHT_BORDER};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c.LIGHT_TEXT_DISABLED};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {c.LIGHT_BORDER};
                border-radius: 5px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {c.LIGHT_TEXT_DISABLED};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}

            /* ===== ToolTip ===== */
            QToolTip {{
                background-color: {c.LIGHT_TEXT_PRIMARY};
                color: {c.LIGHT_BG};
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}

            /* ===== ToolButton ===== */
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 6px;
            }}
            QToolButton:hover {{
                background-color: {c.LIGHT_SURFACE};
            }}
            QToolButton:pressed {{
                background-color: {c.LIGHT_BORDER};
            }}

            /* ===== Sidebar ===== */
            QWidget#sidebarWidget {{
                background-color: {c.LIGHT_SIDEBAR_BG};
                border-right: 1px solid {c.LIGHT_BORDER_SUBTLE};
            }}

            /* ===== Drop Zone Overlay ===== */
            QWidget#dropZoneOverlay {{
                background-color: rgba(0, 120, 212, 0.08);
                border: 2px dashed {c.LIGHT_ACCENT};
                border-radius: 12px;
            }}
        """

    def _dark_stylesheet(self, c: ThemeColors) -> str:
        ff = self._font_family()
        return f"""
            /* ===== Global ===== */
            * {{
                font-family: "{ff}", "Segoe UI Variable", "Helvetica Neue", sans-serif;
                font-size: 13px;
                color: {c.DARK_TEXT_PRIMARY};
            }}
            QMainWindow, QWidget#centralWidget {{
                background-color: {c.DARK_BG};
                border: none;
            }}

            /* ===== MenuBar ===== */
            QMenuBar {{
                background-color: {c.DARK_BG};
                border-bottom: 1px solid {c.DARK_BORDER};
                padding: 2px 4px;
                spacing: 2px;
            }}
            QMenuBar::item {{
                background: transparent;
                padding: 6px 12px;
                border-radius: 6px;
            }}
            QMenuBar::item:selected {{
                background-color: {c.DARK_ACCENT_LIGHT};
                color: {c.DARK_ACCENT};
            }}
            QMenu {{
                background-color: {c.DARK_SURFACE};
                border: 1px solid {c.DARK_BORDER};
                border-radius: 8px;
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 8px 32px 8px 16px;
                border-radius: 4px;
                margin: 2px 4px;
            }}
            QMenu::item:selected {{
                background-color: {c.DARK_ACCENT_LIGHT};
                color: {c.DARK_ACCENT};
            }}
            QMenu::separator {{
                height: 1px;
                background: {c.DARK_BORDER};
                margin: 4px 8px;
            }}

            /* ===== TabWidget / TabBar ===== */
            QTabWidget::pane {{
                border: 1px solid {c.DARK_BORDER};
                border-radius: 8px;
                background: {c.DARK_BG};
                top: -1px;
            }}
            QTabBar {{
                background: transparent;
            }}
            QTabBar::tab {{
                background: {c.DARK_TAB_BG};
                color: {c.DARK_TEXT_SECONDARY};
                border: 1px solid {c.DARK_BORDER_SUBTLE};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 20px;
                margin-right: 2px;
                min-width: 100px;
            }}
            QTabBar::tab:selected {{
                background: {c.DARK_BG};
                color: {c.DARK_ACCENT};
                border-color: {c.DARK_BORDER};
                font-weight: 600;
            }}
            QTabBar::tab:hover:!selected {{
                background: {c.DARK_ACCENT_LIGHT};
                color: {c.DARK_TEXT_PRIMARY};
            }}
            QTabBar::close-button {{
                image: none;
                subcontrol-position: right;
                padding: 2px;
                border-radius: 4px;
            }}
            QTabBar::close-button:hover {{
                background: {c.DARK_DANGER};
            }}

            /* ===== DockWidget ===== */
            QDockWidget {{
                titlebar-close-icon: none;
                font-weight: 600;
                font-size: 12px;
                color: {c.DARK_TEXT_SECONDARY};
            }}
            QDockWidget::title {{
                background: {c.DARK_SURFACE};
                padding: 8px 12px;
                border-top: 1px solid {c.DARK_BORDER_SUBTLE};
                border-bottom: 1px solid {c.DARK_BORDER_SUBTLE};
            }}

            /* ===== StatusBar ===== */
            QStatusBar {{
                background-color: {c.DARK_SURFACE};
                border-top: 1px solid {c.DARK_BORDER_SUBTLE};
                padding: 2px 8px;
                color: {c.DARK_TEXT_SECONDARY};
                font-size: 12px;
            }}
            QStatusBar::item {{
                border: none;
            }}

            /* ===== PushButton ===== */
            QPushButton {{
                background-color: {c.DARK_ACCENT};
                color: #1E1E1E;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 500;
                min-height: 16px;
            }}
            QPushButton:hover {{
                background-color: {c.DARK_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {c.DARK_ACCENT_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {c.DARK_BORDER};
                color: {c.DARK_TEXT_DISABLED};
            }}
            QPushButton#secondaryButton, QPushButton[flat="true"] {{
                background-color: transparent;
                color: {c.DARK_ACCENT};
                border: 1px solid {c.DARK_BORDER};
            }}
            QPushButton#secondaryButton:hover, QPushButton[flat="true"]:hover {{
                background-color: {c.DARK_ACCENT_LIGHT};
            }}

            /* ===== LineEdit ===== */
            QLineEdit {{
                background-color: {c.DARK_INPUT_BG};
                border: 1px solid {c.DARK_BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                color: {c.DARK_TEXT_PRIMARY};
                selection-background-color: {c.DARK_ACCENT_LIGHT};
                selection-color: {c.DARK_ACCENT};
            }}
            QLineEdit:focus {{
                border: 2px solid {c.DARK_ACCENT};
            }}
            QLineEdit:disabled {{
                background-color: {c.DARK_SURFACE};
                color: {c.DARK_TEXT_DISABLED};
            }}

            /* ===== TextEdit / PlainTextEdit ===== */
            QTextEdit, QPlainTextEdit {{
                background-color: {c.DARK_INPUT_BG};
                border: 1px solid {c.DARK_BORDER};
                border-radius: 6px;
                padding: 8px;
                color: {c.DARK_TEXT_PRIMARY};
                selection-background-color: {c.DARK_ACCENT_LIGHT};
            }}
            QTextEdit:focus, QPlainTextEdit:focus {{
                border: 2px solid {c.DARK_ACCENT};
            }}

            /* ===== TreeView ===== */
            QTreeView {{
                background-color: {c.DARK_BG};
                border: 1px solid {c.DARK_BORDER};
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}
            QTreeView::item {{
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QTreeView::item:selected {{
                background-color: {c.DARK_ACCENT_LIGHT};
                color: {c.DARK_ACCENT};
            }}
            QTreeView::item:hover {{
                background-color: {c.DARK_SURFACE};
            }}
            QTreeView::branch {{
                background: transparent;
            }}
            QHeaderView::section {{
                background-color: {c.DARK_SURFACE};
                border: none;
                border-bottom: 1px solid {c.DARK_BORDER};
                border-right: 1px solid {c.DARK_BORDER_SUBTLE};
                padding: 6px 12px;
                font-weight: 600;
                color: {c.DARK_TEXT_SECONDARY};
            }}

            /* ===== Splitter ===== */
            QSplitter::handle {{
                background: {c.DARK_BORDER_SUBTLE};
            }}
            QSplitter::handle:horizontal {{
                width: 3px;
                margin: 4px 0px;
                border-radius: 1px;
            }}
            QSplitter::handle:vertical {{
                height: 3px;
                margin: 0px 4px;
                border-radius: 1px;
            }}
            QSplitter::handle:hover {{
                background: {c.DARK_ACCENT};
            }}

            /* ===== ProgressBar ===== */
            QProgressBar {{
                background-color: {c.DARK_SURFACE};
                border: none;
                border-radius: 4px;
                text-align: center;
                color: {c.DARK_TEXT_SECONDARY};
                font-size: 11px;
                min-height: 8px;
                max-height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {c.DARK_ACCENT};
                border-radius: 4px;
            }}

            /* ===== Label ===== */
            QLabel {{
                background: transparent;
                border: none;
                color: {c.DARK_TEXT_PRIMARY};
            }}
            QLabel#headingLabel {{
                font-size: 18px;
                font-weight: 700;
            }}
            QLabel#subheadingLabel {{
                font-size: 13px;
                color: {c.DARK_TEXT_SECONDARY};
            }}

            /* ===== ComboBox ===== */
            QComboBox {{
                background-color: {c.DARK_INPUT_BG};
                border: 1px solid {c.DARK_BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 120px;
                color: {c.DARK_TEXT_PRIMARY};
            }}
            QComboBox:hover {{
                border: 1px solid {c.DARK_ACCENT};
            }}
            QComboBox:focus {{
                border: 2px solid {c.DARK_ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c.DARK_SURFACE};
                border: 1px solid {c.DARK_BORDER};
                border-radius: 8px;
                padding: 4px;
                color: {c.DARK_TEXT_PRIMARY};
                selection-background-color: {c.DARK_ACCENT_LIGHT};
            }}

            /* ===== CheckBox ===== */
            QCheckBox {{
                spacing: 8px;
                color: {c.DARK_TEXT_PRIMARY};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {c.DARK_BORDER};
                border-radius: 4px;
                background-color: {c.DARK_INPUT_BG};
            }}
            QCheckBox::indicator:hover {{
                border-color: {c.DARK_ACCENT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {c.DARK_ACCENT};
                border-color: {c.DARK_ACCENT};
            }}

            /* ===== ScrollBar ===== */
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 0;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {c.DARK_BORDER};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c.DARK_TEXT_DISABLED};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {c.DARK_BORDER};
                border-radius: 5px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {c.DARK_TEXT_DISABLED};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}

            /* ===== ToolTip ===== */
            QToolTip {{
                background-color: {c.DARK_SURFACE};
                color: {c.DARK_TEXT_PRIMARY};
                border: 1px solid {c.DARK_BORDER};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}

            /* ===== ToolButton ===== */
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 6px;
                color: {c.DARK_TEXT_PRIMARY};
            }}
            QToolButton:hover {{
                background-color: {c.DARK_SURFACE};
            }}
            QToolButton:pressed {{
                background-color: {c.DARK_BORDER};
            }}

            /* ===== Sidebar ===== */
            QWidget#sidebarWidget {{
                background-color: {c.DARK_SIDEBAR_BG};
                border-right: 1px solid {c.DARK_BORDER_SUBTLE};
            }}

            /* ===== Drop Zone Overlay ===== */
            QWidget#dropZoneOverlay {{
                background-color: rgba(96, 205, 255, 0.08);
                border: 2px dashed {c.DARK_ACCENT};
                border-radius: 12px;
            }}
        """
