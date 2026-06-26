from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QWidget):
    """A collapsible section with icon, label, and expandable content area."""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        icon: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._expanded = False

        self._header = QPushButton()
        self._header.setCheckable(True)
        self._header.setFlat(True)
        self._header.setFixedHeight(40)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet(
            "QPushButton { text-align: left; padding: 8px 12px; border-radius: 6px; }"
            "QPushButton:hover { background-color: rgba(0, 120, 212, 0.08); }"
        )

        self._icon_label = QLabel(icon)
        self._icon_label.setFixedWidth(24)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        self._arrow_label = QLabel("\u25B6")  # right-pointing triangle
        self._arrow_label.setFixedWidth(20)
        self._arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        header_layout.addWidget(self._icon_label)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        header_layout.addWidget(self._arrow_label)

        self._content_area = QWidget()
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(8, 4, 8, 4)
        self._content_layout.setSpacing(4)
        self._content_area.setMaximumHeight(0)
        self._content_area.setVisible(False)

        self._animation = QPropertyAnimation(self._content_area, b"maximumHeight")
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.setDuration(200)

        self._header.clicked.connect(self._on_toggle)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._header)
        layout.addWidget(self._content_area)

    def add_widget(self, widget: QWidget) -> None:
        """Add a widget to the collapsible content area."""
        self._content_layout.addWidget(widget)

    def add_layout(self, layout_item: QVBoxLayout) -> None:
        """Add a layout to the collapsible content area."""
        self._content_layout.addLayout(layout_item)

    def _on_toggle(self, checked: bool) -> None:
        self._expanded = checked
        self._arrow_label.setText("\u25BC" if checked else "\u25B6")

        if checked:
            self._content_area.setVisible(True)
            self._animation.setStartValue(0)
            self._animation.setEndValue(self._content_area.sizeHint().height())
        else:
            self._animation.setStartValue(self._content_area.height())
            self._animation.setEndValue(0)
            self._animation.finished.connect(self._on_collapse_finished)

        self._animation.start()
        self.toggled.emit(checked)

    def _on_collapse_finished(self) -> None:
        if not self._expanded:
            self._content_area.setVisible(False)
        self._animation.finished.disconnect(self._on_collapse_finished)

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    def set_narrow(self, narrow: bool) -> None:
        """Switch between narrow (icon-only) and wide (icon + text) mode."""
        self._title_label.setVisible(not narrow)
        self._arrow_label.setVisible(not narrow)
        if narrow:
            self._icon_label.setStyleSheet("font-size: 16px;")
        else:
            self._icon_label.setStyleSheet("font-size: 14px;")


class SidebarWidget(QWidget):
    """Collapsible sidebar with sections for case info, files, tools, and settings."""

    mode_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarWidget")
        self._narrow = False
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)

        self._sections: list[CollapsibleSection] = []

        # Toggle button
        self._toggle_btn = QPushButton("\u2630")  # hamburger icon
        self._toggle_btn.setFixedSize(36, 36)
        self._toggle_btn.setToolTip("Alternar modo da barra lateral")
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet(
            "QPushButton { border-radius: 8px; font-size: 18px; }"
        )
        self._toggle_btn.clicked.connect(self._toggle_mode)

        # Sections
        self._case_section = CollapsibleSection("Informacoes do Caso", "\u2696")  # scales
        self._files_section = CollapsibleSection("Arquivos", "\u25C8")  # diamond
        self._tools_section = CollapsibleSection("Ferramentas", "\u2692")  # hammer and pick
        self._settings_section = CollapsibleSection("Configuracoes", "\u2699")  # gear
        self._sections = [
            self._case_section,
            self._files_section,
            self._tools_section,
            self._settings_section,
        ]

        # Placeholder content for each section
        for section in self._sections:
            placeholder = QLabel("Nenhum conteudo disponivel.")
            placeholder.setStyleSheet("color: #888; font-size: 12px; padding: 4px;")
            section.add_widget(placeholder)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(2)
        container_layout.addWidget(self._case_section)
        container_layout.addWidget(self._files_section)
        container_layout.addWidget(self._tools_section)
        container_layout.addWidget(self._settings_section)
        container_layout.addStretch()
        self._scroll.setWidget(container)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(8)
        layout.addWidget(self._toggle_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._scroll)

    def _toggle_mode(self) -> None:
        """Toggle between narrow and wide mode."""
        self._narrow = not self._narrow
        if self._narrow:
            self.setMaximumWidth(60)
            self.setMinimumWidth(60)
            self._toggle_btn.setText("\u2630")
        else:
            self.setMaximumWidth(300)
            self.setMinimumWidth(220)
            self._toggle_btn.setText("\u2630")

        for section in self._sections:
            section.set_narrow(self._narrow)

        self.mode_changed.emit(self._narrow)

    def get_section(self, name: str) -> CollapsibleSection | None:
        """Retrieve a section by name: 'case', 'files', 'tools', 'settings'."""
        mapping = {
            "case": self._case_section,
            "files": self._files_section,
            "tools": self._tools_section,
            "settings": self._settings_section,
        }
        return mapping.get(name)
