from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

APP_VERSION: str = "0.1.0"


class StatusBarWidget(QWidget):
    """Status bar widget with current operation, progress bar, and version label."""

    item_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(32)

        # Status label
        self._status_label = QLabel("Pronto")
        self._status_label.setStyleSheet("font-size: 12px; padding-left: 4px;")
        self._status_label.setCursor(Qt.CursorShape.PointingHandCursor)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedWidth(160)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.hide()

        # Progress label
        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet("font-size: 11px;")
        self._progress_label.hide()

        # Version label
        self._version_label = QLabel(f"v{APP_VERSION}")
        self._version_label.setStyleSheet("font-size: 11px; padding-right: 4px;")
        self._version_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._version_label.mousePressEvent = lambda e: self.item_clicked.emit(
            "version"
        )

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(12)
        layout.addWidget(self._status_label)
        layout.addWidget(self._progress_bar)
        layout.addWidget(self._progress_label)
        layout.addStretch()
        layout.addWidget(self._version_label)

    def set_status(self, text: str) -> None:
        """Update the status text."""
        self._status_label.setText(text)

    def set_progress(self, value: int) -> None:
        """Update the progress bar value (0-100). Show bar if not visible."""
        self._progress_bar.show()
        self._progress_label.show()
        self._progress_bar.setValue(value)
        self._progress_label.setText(f"{value}%")

    def hide_progress(self) -> None:
        """Hide the progress bar."""
        self._progress_bar.hide()
        self._progress_label.hide()

    def set_version(self, version: str) -> None:
        """Update the version label."""
        self._version_label.setText(f"v{version}")

    def reset(self) -> None:
        """Reset status to default ready state."""
        self.set_status("Pronto")
        self.hide_progress()
