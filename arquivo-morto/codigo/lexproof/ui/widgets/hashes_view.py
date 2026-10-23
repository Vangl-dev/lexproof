"""HashesViewWidget — hash results displayed as cards."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class _HashBar(QWidget):
    """Row of small colored squares representing a hash visually."""

    def __init__(self, hash_value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hash = hash_value
        self.setFixedHeight(16)
        self._colors = [
            self.palette().ColorRole.Highlight,
            self.palette().ColorRole.Link,
            self.palette().ColorRole.Mid,
            self.palette().ColorRole.Button,
        ]
        self.setMinimumWidth(max(1, len(hash_value) * 4))

    def paintEvent(self, event: object) -> None:  # noqa: ANN401
        from PySide6.QtGui import QPainter
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        square_w = 4
        gap = 1
        x = 0
        for i, ch in enumerate(self._hash):
            if x > self.width():
                break
            color = palette.color(self._colors[i % len(self._colors)])
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(x, 0, square_w, self.height() - 1)
            x += square_w + gap
        painter.end()


class _FileCard(QWidget):
    """Card showing hash results for a single file."""

    def __init__(self, data: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data = data
        self._setup_ui()

    def _setup_ui(self) -> None:
        palette = self.palette()
        self.setStyleSheet(
            "background-color: %s; border-radius: 8px; padding: 8px; border: 1px solid palette(mid);"
            % palette.color(palette.ColorRole.Base).name()
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        name = self._data.get("file_name", "")
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        header.addWidget(name_label)
        header.addStretch()

        size = self._data.get("file_size", "")
        if size:
            size_label = QLabel(size)
            size_label.setStyleSheet(
                "font-size: 11px; color: %s;"
                % palette.color(palette.ColorRole.PlaceholderText).name()
            )
            header.addWidget(size_label)

        layout.addLayout(header)

        for key, label_text in (
            ("sha256", "SHA256"),
            ("sha3_512", "SHA3-512"),
            ("blake3", "BLAKE3"),
        ):
            value = self._data.get(key, "")
            if not value:
                continue

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)

            lbl = QLabel(label_text)
            lbl.setFixedWidth(80)
            lbl.setStyleSheet(
                "font-size: 11px; font-weight: 600; color: %s;"
                % palette.color(palette.ColorRole.PlaceholderText).name()
            )
            row.addWidget(lbl)

            hash_box = QLabel(value)
            hash_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            hash_box.setStyleSheet(
                "font-family: monospace; font-size: 11px; padding: 2px 4px; "
                "background-color: %s; border-radius: 3px;"
                % palette.color(palette.ColorRole.Window).name()
            )
            row.addWidget(hash_box, stretch=1)

            copy_btn = QLabel("Copiar")
            copy_btn.setStyleSheet(
                "font-size: 11px; color: %s; cursor: pointer;"
                % palette.color(palette.ColorRole.Link).name()
            )
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.mousePressEvent = lambda _e, v=value: self._copy(v)
            row.addWidget(copy_btn)

            layout.addLayout(row)

            bar = _HashBar(value)
            bar.setFixedHeight(16)
            layout.addWidget(bar)

    def _copy(self, text: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, HashesViewWidget):
                parent.hash_copied.emit(text)
                break
            parent = parent.parent()  # type: ignore[assignment]


class HashesViewWidget(QWidget):
    """Widget showing hash calculation results as cards."""

    hash_copied = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._global_hash: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Hashes")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        self._container = QWidget()
        self._cards_layout = QVBoxLayout(self._container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        scroll.setWidget(self._container)
        layout.addWidget(scroll)

        self._empty_label = QLabel(
            "Nenhum hash calculado. Execute o calculo de hashes primeiro."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: %s; font-style: italic;"
            % self.palette().color(self.palette().ColorRole.PlaceholderText).name()
        )
        self._cards_layout.insertWidget(self._cards_layout.count() - 1, self._empty_label)

        self._global_frame = QFrame()
        self._global_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._global_layout = QVBoxLayout(self._global_frame)
        self._global_layout.setContentsMargins(12, 8, 12, 8)

        global_title = QLabel("Hash Global")
        global_title.setStyleSheet("font-weight: 600; font-size: 12px;")
        self._global_layout.addWidget(global_title)

        self._global_value = QLabel("---")
        self._global_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._global_value.setStyleSheet("font-family: monospace; font-size: 11px;")
        self._global_layout.addWidget(self._global_value)

        global_copy = QLabel("Copiar")
        global_copy.setStyleSheet(
            "font-size: 11px; color: %s; cursor: pointer;"
            % self.palette().color(self.palette().ColorRole.Link).name()
        )
        global_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        global_copy.mousePressEvent = lambda _e: self._copy_global()
        self._global_layout.addWidget(global_copy, alignment=Qt.AlignmentFlag.AlignLeft)

        self._global_frame.setVisible(False)
        layout.addWidget(self._global_frame)

    def set_hashes(self, hashes: list[dict[str, str]]) -> None:
        self._clear_cards()
        for data in hashes:
            card = _FileCard(data, self)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        if not hashes:
            self._empty_label.show()
        else:
            self._empty_label.hide()

    def clear(self) -> None:
        self._clear_cards()
        self._global_hash = ""
        self._global_value.setText("---")
        self._global_frame.setVisible(False)

    def set_global_hash(self, value: str) -> None:
        self._global_hash = value
        self._global_value.setText(value or "---")
        self._global_frame.setVisible(bool(value))

    def _clear_cards(self) -> None:
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._empty_label.show()

    def _copy_global(self) -> None:
        if self._global_hash:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(self._global_hash)
            self.hash_copied.emit(self._global_hash)
