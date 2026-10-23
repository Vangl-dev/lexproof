"""Sistema de design moderno para o LexProof.

Estilo minimalista, flat, baseado em cards, inspirado em aplicativos
comerciais modernos como Cantai e EraserID.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def get_modern_stylesheet() -> str:
    """Retorna o stylesheet moderno completo.

    Utiliza apenas palette() para cores - nenhum valor fixo.
    Segue padrão flat com cards, bordas arredondadas, espaçamento generoso.
    """
    return """
    /* ============================================================
       LEXPROOF MODERN DESIGN SYSTEM
       Flat • Card-based • Minimalist
       ============================================================ */

    /* === GLOBAL === */
    QWidget {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 13px;
        color: palette(text);
    }

    /* === MAIN WINDOW === */
    QMainWindow {
        background-color: palette(window);
    }

    /* === BUTTONS === */
    QPushButton {
        border: none;
        border-radius: 8px;
        padding: 8px 20px;
        min-height: 32px;
        font-weight: 500;
        background-color: palette(button);
        color: palette(buttonText);
    }

    QPushButton:hover {
        background-color: palette(mid);
    }

    QPushButton:pressed {
        background-color: palette(dark);
        padding-top: 9px;
        padding-bottom: 7px;
    }

    QPushButton:disabled {
        background-color: palette(mid);
        color: palette(placeholderText);
    }

    /* Primary button */
    QPushButton[cssClass="primary"] {
        background-color: palette(highlight);
        color: palette(highlightedText);
    }

    QPushButton[cssClass="primary"]:hover {
        background-color: palette(highlight);
        opacity: 0.9;
    }

    /* === INPUTS === */
    QLineEdit, QTextEdit, QPlainTextEdit {
        border: 1px solid palette(mid);
        border-radius: 8px;
        padding: 8px 12px;
        background-color: palette(base);
        color: palette(text);
        selection-background-color: palette(highlight);
    }

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border: 2px solid palette(highlight);
    }

    QLineEdit::placeholder {
        color: palette(placeholderText);
    }

    /* === COMBOBOX === */
    QComboBox {
        border: 1px solid palette(mid);
        border-radius: 8px;
        padding: 8px 12px;
        background-color: palette(base);
        color: palette(text);
        min-height: 32px;
    }

    QComboBox:hover {
        border: 1px solid palette(dark);
    }

    QComboBox:focus {
        border: 2px solid palette(highlight);
    }

    QComboBox::drop-down {
        border: none;
        width: 32px;
    }

    QComboBox::down-arrow {
        image: none;
        border: none;
    }

    QComboBox QAbstractItemView {
        border: 1px solid palette(mid);
        border-radius: 8px;
        background-color: palette(base);
        selection-background-color: palette(highlight);
        selection-color: palette(highlightedText);
        padding: 4px;
    }

    /* === PROGRESS BAR === */
    QProgressBar {
        border: none;
        border-radius: 4px;
        max-height: 6px;
        background-color: palette(mid);
        text-align: center;
    }

    QProgressBar::chunk {
        border-radius: 4px;
        background-color: palette(highlight);
    }

    /* === TABS === */
    QTabWidget::pane {
        border: none;
        background: transparent;
    }

    QTabBar {
        background: transparent;
    }

    QTabBar::tab {
        border: none;
        border-bottom: 2px solid transparent;
        padding: 10px 20px;
        margin-right: 4px;
        font-weight: 500;
        color: palette(placeholderText);
        background: transparent;
    }

    QTabBar::tab:hover {
        color: palette(text);
    }

    QTabBar::tab:selected {
        color: palette(highlight);
        border-bottom: 2px solid palette(highlight);
    }

    /* === MENUS === */
    QMenu {
        border: 1px solid palette(mid);
        border-radius: 8px;
        padding: 6px;
        background-color: palette(base);
    }

    QMenu::item {
        border-radius: 6px;
        margin: 2px 4px;
        padding: 8px 32px 8px 16px;
        color: palette(text);
    }

    QMenu::item:selected {
        background-color: palette(highlight);
        color: palette(highlightedText);
    }

    QMenu::separator {
        height: 1px;
        background: palette(mid);
        margin: 4px 8px;
    }

    /* === TOOLTIPS === */
    QToolTip {
        border: 1px solid palette(mid);
        border-radius: 6px;
        padding: 6px 10px;
        background-color: palette(base);
        color: palette(text);
    }

    /* === SCROLLBARS === */
    QScrollBar:vertical {
        width: 8px;
        border-radius: 4px;
        background: transparent;
        margin: 0;
    }

    QScrollBar::handle:vertical {
        border-radius: 4px;
        min-height: 30px;
        background: palette(mid);
    }

    QScrollBar::handle:vertical:hover {
        background: palette(dark);
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {
        height: 0px;
        background: none;
        border: none;
    }

    QScrollBar:horizontal {
        height: 8px;
        border-radius: 4px;
        background: transparent;
        margin: 0;
    }

    QScrollBar::handle:horizontal {
        border-radius: 4px;
        min-width: 30px;
        background: palette(mid);
    }

    QScrollBar::handle:horizontal:hover {
        background: palette(dark);
    }

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {
        width: 0px;
        background: none;
        border: none;
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
        background-color: palette(window);
        border-right: 1px solid palette(mid);
    }

    /* === CARDS === */
    QFrame#card {
        border: 1px solid palette(mid);
        border-radius: 12px;
        padding: 20px;
        background-color: palette(base);
    }

    QFrame#card:hover {
        border: 1px solid palette(dark);
    }

    QFrame#cardSelected {
        border: 2px solid palette(highlight);
        border-radius: 12px;
        padding: 20px;
        background-color: palette(base);
    }

    /* === MENU BAR === */
    QMenuBar {
        background-color: palette(window);
        border-bottom: 1px solid palette(mid);
        padding: 4px 8px;
    }

    QMenuBar::item {
        padding: 6px 12px;
        border-radius: 6px;
        color: palette(text);
    }

    QMenuBar::item:selected {
        background-color: palette(highlight);
        color: palette(highlightedText);
    }

    /* === STATUS BAR === */
    QStatusBar {
        background-color: palette(window);
        border-top: 1px solid palette(mid);
        padding: 4px 12px;
        font-size: 12px;
        color: palette(placeholderText);
    }

    /* === SCROLL AREA === */
    QScrollArea {
        border: none;
        background: transparent;
    }

    QScrollArea > QWidget > QWidget {
        background: transparent;
    }

    /* === CHECKBOX === */
    QCheckBox {
        spacing: 10px;
        color: palette(text);
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid palette(mid);
        border-radius: 4px;
        background: palette(base);
    }

    QCheckBox::indicator:checked {
        background: palette(highlight);
        border: 2px solid palette(highlight);
    }

    QCheckBox::indicator:hover {
        border: 2px solid palette(dark);
    }

    /* === RADIO BUTTON === */
    QRadioButton {
        spacing: 10px;
        color: palette(text);
    }

    QRadioButton::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid palette(mid);
        border-radius: 9px;
        background: palette(base);
    }

    QRadioButton::indicator:checked {
        background: palette(highlight);
        border: 2px solid palette(highlight);
    }

    /* === GROUP BOX === */
    QGroupBox {
        font-weight: 600;
        border: 1px solid palette(mid);
        border-radius: 12px;
        margin-top: 16px;
        padding-top: 24px;
        padding-bottom: 16px;
        padding-left: 16px;
        padding-right: 16px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 8px;
        color: palette(text);
    }

    /* === LIST VIEW / TREE VIEW === */
    QListView, QTreeView {
        border: 1px solid palette(mid);
        border-radius: 8px;
        background-color: palette(base);
        padding: 4px;
    }

    QListView::item, QTreeView::item {
        border-radius: 6px;
        padding: 8px 12px;
        margin: 2px 4px;
    }

    QListView::item:selected, QTreeView::item:selected {
        background-color: palette(highlight);
        color: palette(highlightedText);
    }

    QListView::item:hover, QTreeView::item:hover {
        background-color: palette(mid);
    }

    /* === TABLE VIEW === */
    QTableView {
        border: 1px solid palette(mid);
        border-radius: 8px;
        background-color: palette(base);
        gridline-color: palette(mid);
        selection-background-color: palette(highlight);
        selection-color: palette(highlightedText);
    }

    QTableView::item {
        padding: 8px 12px;
    }

    QTableView::item:selected {
        background-color: palette(highlight);
    }

    QHeaderView::section {
        background-color: palette(window);
        border: none;
        border-bottom: 1px solid palette(mid);
        padding: 8px 12px;
        font-weight: 600;
        color: palette(text);
    }

    /* === SPIN BOX === */
    QSpinBox, QDoubleSpinBox {
        border: 1px solid palette(mid);
        border-radius: 8px;
        padding: 6px 10px;
        background-color: palette(base);
        color: palette(text);
    }

    QSpinBox:focus, QDoubleSpinBox:focus {
        border: 2px solid palette(highlight);
    }

    /* === SLIDER === */
    QSlider::groove:horizontal {
        height: 6px;
        border-radius: 3px;
        background: palette(mid);
    }

    QSlider::handle:horizontal {
        width: 18px;
        height: 18px;
        margin: -6px 0;
        border-radius: 9px;
        background: palette(highlight);
    }

    QSlider::handle:horizontal:hover {
        background: palette(dark);
    }

    QSlider::sub-page:horizontal {
        border-radius: 3px;
        background: palette(highlight);
    }

    /* === LABELS === */
    QLabel {
        background: transparent;
    }

    /* Title label */
    QLabel[cssClass="title"] {
        font-size: 24px;
        font-weight: 600;
        color: palette(text);
    }

    /* Subtitle label */
    QLabel[cssClass="subtitle"] {
        font-size: 16px;
        font-weight: 500;
        color: palette(text);
    }

    /* Caption label */
    QLabel[cssClass="caption"] {
        font-size: 12px;
        color: palette(placeholderText);
    }
    """
