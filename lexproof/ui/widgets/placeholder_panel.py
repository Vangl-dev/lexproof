from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderPanel(QWidget):
    """A generic placeholder panel for tabs not yet fully implemented."""

    def __init__(self, title: str = "Em desenvolvimento", description: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)

        icon_label = QLabel("\u2699")
        icon_label.setStyleSheet("font-size: 48px; color: #0078D4;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #1A1A1A;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc_label = QLabel(description or "Esta funcionalidade será implementada em breve.")
        desc_label.setStyleSheet("font-size: 13px; color: #666;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)
        layout.addStretch()
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
