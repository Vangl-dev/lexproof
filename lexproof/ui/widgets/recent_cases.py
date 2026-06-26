from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class _CaseCard(QFrame):
    """Clickable card representing a single recent case."""

    clicked = Signal(str)

    _CARD_STYLE: ClassVar[str] = (
        "#card { border: 1px solid palette(mid); border-radius: 6px; "
        "background: palette(base); }"
        "#card:hover { background: palette(highlight); }"
    )

    def __init__(
        self,
        title: str,
        date: str,
        file_path: str,
        evidence_count: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._path = file_path
        self.setObjectName("card")
        self.setStyleSheet(self._CARD_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(120)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        title_label.setWordWrap(True)

        date_label = QLabel(date)
        date_label.setStyleSheet("font-size: 11px;")

        path_label = QLabel(file_path)
        path_label.setStyleSheet("font-size: 10px;")
        path_label.setWordWrap(True)

        evidence_label = QLabel(f"{evidence_count} evidência(s)")
        evidence_label.setStyleSheet("font-size: 11px;")

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(2)
        info_layout.addWidget(title_label)
        info_layout.addWidget(date_label)
        info_layout.addWidget(path_label)
        info_layout.addStretch()
        info_layout.addWidget(evidence_label)

        self.setLayout(info_layout)

    def mousePressEvent(self, event: object) -> None:  # noqa: ANN401
        self.clicked.emit(self._path)
        super().mousePressEvent(event)  # type: ignore[misc]


class RecentCasesWidget(QWidget):
    """Widget displaying up to 6 recent cases as clickable cards in a 3×2 grid."""

    case_selected = Signal(str)

    _MAX_CARDS: ClassVar[int] = 6
    _COLUMNS: ClassVar[int] = 3

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: list[_CaseCard] = []

        title = QLabel("Casos Recentes")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")

        self._empty_label = QLabel(
            "Nenhum caso recente. Crie um novo caso para começar."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("font-size: 12px;")

        self._grid_layout = QGridLayout()
        self._grid_layout.setSpacing(8)

        self._grid_container = QWidget()
        self._grid_container.setLayout(self._grid_layout)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll_area.setWidget(self._grid_container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(title)
        layout.addWidget(self._empty_label)
        layout.addWidget(self._scroll_area)

        self._update_visibility()

    def add_recent(
        self,
        title: str,
        path: str,
        evidence_count: int,
        date: str,
    ) -> None:
        """Add a case to the recent list. Oldest entry is removed when full."""
        if len(self._cards) >= self._MAX_CARDS:
            oldest = self._cards.pop(0)
            oldest.deleteLater()

        card = _CaseCard(title=title, date=date, file_path=path, evidence_count=evidence_count)
        card.clicked.connect(self._on_card_clicked)
        self._cards.append(card)

        row = (len(self._cards) - 1) // self._COLUMNS
        col = (len(self._cards) - 1) % self._COLUMNS
        self._grid_layout.addWidget(card, row, col)
        self._update_visibility()

    def load_from_settings(self) -> None:
        """Load recent cases from the application settings."""
        from lexproof.config.settings import Settings

        settings = Settings.get_instance()
        for file_path in settings.recent_files:
            path = Path(file_path)
            if path.exists():
                self.add_recent(
                    title=path.stem,
                    path=str(path),
                    evidence_count=0,
                    date="",
                )

    def clear(self) -> None:
        """Remove all recent case cards."""
        for card in self._cards:
            self._grid_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._update_visibility()

    def _update_visibility(self) -> None:
        has_cards = len(self._cards) > 0
        self._empty_label.setVisible(not has_cards)
        self._scroll_area.setVisible(has_cards)

    @Slot(str)
    def _on_card_clicked(self, path: str) -> None:
        self.case_selected.emit(path)
