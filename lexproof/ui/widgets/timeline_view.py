from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class _EntryCard(QWidget):
    """Single timeline entry card."""

    def __init__(self, entry: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry = entry
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self) -> None:
        palette = self.palette()

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 8)
        outer.setSpacing(0)

        timeline_col = QVBoxLayout()
        timeline_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        timeline_col.setContentsMargins(0, 0, 0, 0)
        timeline_col.setSpacing(0)

        dot = QWidget()
        dot.setFixedSize(12, 12)
        dot.setStyleSheet(
            "background-color: %s; border-radius: 6px;" % palette.color(
                self.palette().ColorRole.Highlight
            ).name()
        )
        timeline_col.addWidget(dot, alignment=Qt.AlignmentFlag.AlignHCenter)

        line = QWidget()
        line.setFixedWidth(2)
        line.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        line.setStyleSheet("background-color: %s;" % palette.color(
            self.palette().ColorRole.Mid
        ).name())
        timeline_col.addWidget(line)

        outer.addLayout(timeline_col)

        card = QWidget()
        card.setStyleSheet(
            "background-color: %s; border-radius: 6px; padding: 8px;"
            % palette.color(self.palette().ColorRole.Base).name()
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        ts_label = QLabel(self._entry.get("timestamp", ""))
        ts_label.setStyleSheet(
            "font-size: 11px; color: %s;" % palette.color(
                self.palette().ColorRole.PlaceholderText
            ).name()
        )
        header.addWidget(ts_label)
        header.addStretch()

        status = self._entry.get("status", "")
        if status:
            status_label = QLabel(status)
            color_role = (
                self.palette().ColorRole.Highlight
                if status.lower() == "ok"
                else self.palette().ColorRole.Link
            )
            status_label.setStyleSheet(
                "font-size: 11px; font-weight: 600; color: %s;"
                % palette.color(color_role).name()
            )
            header.addWidget(status_label)

        card_layout.addLayout(header)

        sender = self._entry.get("sender", "")
        if sender:
            sender_label = QLabel(sender)
            sender_label.setStyleSheet("font-weight: 600; font-size: 13px;")
            card_layout.addWidget(sender_label)

        content = self._entry.get("content", "")
        if content:
            content_label = QLabel(content)
            content_label.setWordWrap(True)
            card_layout.addWidget(content_label)

        source = self._entry.get("source", "")
        if source:
            source_label = QLabel(source)
            source_label.setStyleSheet(
                "font-size: 11px; color: %s;" % palette.color(
                    self.palette().ColorRole.PlaceholderText
                ).name()
            )
            card_layout.addWidget(source_label)

        outer.addWidget(card, stretch=1)

    def mousePressEvent(self, event: object) -> None:  # noqa: ANN401
        """Emit entry data when card is clicked."""
        if hasattr(self, "parent") and isinstance(self.parent(), QWidget):
            parent = self.parent()
            while parent is not None:
                if isinstance(parent, TimelineViewWidget):
                    parent.entry_clicked.emit(self._entry)
                    break
                parent = parent.parent()  # type: ignore[assignment]


class TimelineViewWidget(QWidget):
    """Widget showing timeline entries as vertical cards connected by a line."""

    entry_clicked = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._all_entries: list[dict[str, str]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Timeline")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        self._sender_filter = QComboBox()
        self._sender_filter.setPlaceholderText("Filtrar por remetente")
        self._sender_filter.currentIndexChanged.connect(self._apply_filters)
        self._sender_filter.setFixedWidth(180)
        toolbar.addWidget(self._sender_filter)

        layout.addLayout(toolbar)

        date_row = QHBoxLayout()
        date_row.setContentsMargins(0, 0, 0, 0)

        self._date_start = QDate.currentDate()
        self._date_end = QDate.currentDate()

        self._date_start_input = QLineEdit()
        self._date_start_input.setPlaceholderText("Data início (AAAA-MM-DD)")
        self._date_start_input.setFixedWidth(150)
        self._date_start_input.editingFinished.connect(self._apply_filters)
        date_row.addWidget(self._date_start_input)

        self._date_end_input = QLineEdit()
        self._date_end_input.setPlaceholderText("Data fim (AAAA-MM-DD)")
        self._date_end_input.setFixedWidth(150)
        self._date_end_input.editingFinished.connect(self._apply_filters)
        date_row.addWidget(self._date_end_input)

        date_row.addStretch()
        layout.addLayout(date_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(8, 8, 8, 8)
        self._cards_layout.setSpacing(0)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_container)
        layout.addWidget(scroll)

        self._empty_label = QLabel(
            "Nenhuma entrada na timeline.\nAdicione entradas para visualizar o histórico."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: %s; font-style: italic;"
            % self.palette().color(
                self.palette().ColorRole.PlaceholderText
            ).name()
        )
        self._cards_layout.insertWidget(self._cards_layout.count() - 1, self._empty_label)

    def set_entries(self, entries: list[dict[str, str]]) -> None:
        """Set the timeline entries."""
        self._all_entries = list(entries)
        self._rebuild_sender_filter()
        self._apply_filters()

    def clear(self) -> None:
        """Remove all entries from the timeline."""
        self._all_entries.clear()
        self._clear_cards()
        self._sender_filter.clear()

    def filter_by_sender(self, sender: str) -> None:
        """Filter entries by sender name."""
        idx = self._sender_filter.findText(sender)
        if idx >= 0:
            self._sender_filter.setCurrentIndex(idx)

    def filter_by_date(self, start: datetime, end: datetime) -> None:
        """Filter entries by date range."""
        self._date_start_input.setText(start.strftime("%Y-%m-%d"))
        self._date_end_input.setText(end.strftime("%Y-%m-%d"))
        self._apply_filters()

    def _rebuild_sender_filter(self) -> None:
        self._sender_filter.blockSignals(True)
        self._sender_filter.clear()
        self._sender_filter.addItem("")
        senders = sorted({e.get("sender", "") for e in self._all_entries if e.get("sender")})
        for s in senders:
            self._sender_filter.addItem(s)
        self._sender_filter.blockSignals(False)

    def _apply_filters(self) -> None:
        filtered = list(self._all_entries)

        sender = self._sender_filter.currentText()
        if sender:
            filtered = [e for e in filtered if e.get("sender") == sender]

        start_text = self._date_start_input.text().strip()
        end_text = self._date_end_input.text().strip()
        if start_text:
            try:
                start = datetime.strptime(start_text, "%Y-%m-%d")
                filtered = [
                    e for e in filtered
                    if self._parse_ts(e.get("timestamp", "")) >= start
                ]
            except ValueError:
                pass
        if end_text:
            try:
                end = datetime.strptime(end_text, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                filtered = [
                    e for e in filtered
                    if self._parse_ts(e.get("timestamp", "")) <= end
                ]
            except ValueError:
                pass

        self._rebuild_cards(filtered)

    def _rebuild_cards(self, entries: list[dict[str, str]]) -> None:
        self._clear_cards()
        for entry in entries:
            card = _EntryCard(entry, self)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

        if not entries:
            self._empty_label.show()
        else:
            self._empty_label.hide()

    def _clear_cards(self) -> None:
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._empty_label.show()

    @staticmethod
    def _parse_ts(ts: str) -> datetime:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
        return datetime.min
