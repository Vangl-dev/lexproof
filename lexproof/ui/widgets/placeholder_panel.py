from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class PlaceholderPanel(QWidget):
    """A generic placeholder panel for tabs not yet fully implemented."""

    def __init__(self, title: str = "Em desenvolvimento", description: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)

        card = QFrame()
        card.setObjectName("card")

        icon_label = QLabel("\u2699")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName("headingLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc_label = QLabel(description or "Esta funcionalidade será implementada em breve.")
        desc_label.setObjectName("subheadingLabel")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(12)
        card_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(desc_label, alignment=Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
