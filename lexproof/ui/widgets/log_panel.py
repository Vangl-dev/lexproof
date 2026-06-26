from __future__ import annotations

import datetime
from typing import Final

from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

LOG_COLORS: Final[dict[str, str]] = {
    "DEBUG": "#8661C5",
    "INFO": "#0078D4",
    "WARNING": "#FFB900",
    "ERROR": "#D13438",
}

LEVELS: Final[list[str]] = ["DEBUG", "INFO", "WARNING", "ERROR"]


class LogPanelWidget(QWidget):
    """Bottom panel displaying application log output with filtering and export."""

    log_exported = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auto_scroll = True
        self._all_entries: list[tuple[str, str, str]] = []  # (timestamp, level, message)
        self._active_filter: str = "ALL"

        # Log text area
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(self._monospace_font())
        self._text_edit.setStyleSheet(
            "QTextEdit { background-color: #FAFAFA; border: 1px solid #E0E0E0;"
            " border-radius: 6px; padding: 8px; }"
        )
        self._text_edit.verticalScrollBar().valueChanged.connect(
            self._on_scroll_changed
        )

        # Filter combo
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["ALL"] + LEVELS)
        self._filter_combo.setFixedWidth(100)
        self._filter_combo.currentTextChanged.connect(self._on_filter_changed)

        # Buttons
        self._clear_btn = QPushButton("Limpar")
        self._clear_btn.setFixedHeight(28)
        self._clear_btn.setObjectName("secondaryButton")
        self._clear_btn.clicked.connect(self.clear_logs)

        self._export_btn = QPushButton("Exportar")
        self._export_btn.setFixedHeight(28)
        self._export_btn.setObjectName("secondaryButton")
        self._export_btn.clicked.connect(self._export_logs)

        # Title
        title = QLabel("Registro de Atividades")
        title.setStyleSheet("font-weight: 600; font-size: 12px;")

        # Top toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        toolbar.addWidget(title)
        toolbar.addStretch()
        toolbar.addWidget(QLabel("Filtrar:"))
        toolbar.addWidget(self._filter_combo)
        toolbar.addWidget(self._clear_btn)
        toolbar.addWidget(self._export_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.addLayout(toolbar)
        layout.addWidget(self._text_edit)

    def _monospace_font(self) -> "QFont":
        from PySide6.QtGui import QFont

        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        return font

    @Slot(str, str)
    def log(self, level: str, message: str) -> None:
        """Append a log entry with the given level and message."""
        now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = (now, level.upper(), message)
        self._all_entries.append(entry)

        if self._should_display(level.upper()):
            self._append_formatted(now, level.upper(), message)

    def _should_display(self, level: str) -> bool:
        return self._active_filter == "ALL" or self._active_filter == level

    def _append_formatted(self, timestamp: str, level: str, message: str) -> None:
        color = LOG_COLORS.get(level, "#666666")
        html = (
            f'<span style="color:{color}; font-weight:600;">[{level}]</span> '
            f'<span style="color:#999;">{timestamp}</span> '
            f'<span style="color:#1A1A1A;">{_escape_html(message)}</span>'
        )
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html + "<br>")

        if self._auto_scroll:
            self._text_edit.verticalScrollBar().setValue(
                self._text_edit.verticalScrollBar().maximum()
            )

    def _on_scroll_changed(self, value: int) -> None:
        maximum = self._text_edit.verticalScrollBar().maximum()
        self._auto_scroll = value >= maximum - 5

    @Slot(str)
    def _on_filter_changed(self, filter_text: str) -> None:
        self._active_filter = filter_text
        self._refresh_display()

    def _refresh_display(self) -> None:
        self._text_edit.clear()
        for timestamp, level, message in self._all_entries:
            if self._should_display(level):
                self._append_formatted(timestamp, level, message)

    def clear_logs(self) -> None:
        """Clear all log entries."""
        self._all_entries.clear()
        self._text_edit.clear()

    def _export_logs(self) -> None:
        """Export visible logs to a text file."""
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Registros",
            f"lexproof_log_{datetime.date.today().isoformat()}.txt",
            "Arquivos de Texto (*.txt);;Todos os Arquivos (*)",
        )
        if not path:
            return

        from pathlib import Path

        output = Path(path)
        lines: list[str] = []
        for timestamp, level, message in self._all_entries:
            if self._should_display(level):
                lines.append(f"[{level}] {timestamp} {message}")
        output.write_text("\n".join(lines), encoding="utf-8")
        self.log_exported.emit(str(output))

    def get_log_count(self) -> int:
        """Return the total number of log entries."""
        return len(self._all_entries)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
