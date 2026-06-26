from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CaseInfoPanel(QWidget):
    """Panel for viewing and editing case information."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        group = QGroupBox("Dados do Caso")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._case_number = QLineEdit()
        self._case_number.setPlaceholderText("Número do processo")
        form.addRow("Número:", self._case_number)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Título do caso")
        form.addRow("Título:", self._title_edit)

        self._client = QLineEdit()
        self._client.setPlaceholderText("Nome do cliente")
        form.addRow("Cliente:", self._client)

        self._lawyer = QLineEdit()
        self._lawyer.setPlaceholderText("Advogado responsável")
        form.addRow("Advogado:", self._lawyer)

        self._court = QLineEdit()
        self._court.setPlaceholderText("Foro / Vara")
        form.addRow("Foro:", self._court)

        self._description = QTextEdit()
        self._description.setPlaceholderText("Descrição do caso")
        self._description.setMaximumHeight(120)
        form.addRow("Descrição:", self._description)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(group)
        layout.addStretch()

    def get_data(self) -> dict[str, str]:
        """Return case info as a dictionary."""
        return {
            "case_number": self._case_number.text(),
            "title": self._title_edit.text(),
            "client": self._client.text(),
            "lawyer": self._lawyer.text(),
            "court": self._court.text(),
            "description": self._description.toPlainText(),
        }

    def set_data(self, data: dict[str, str]) -> None:
        """Populate fields from a dictionary."""
        self._case_number.setText(data.get("case_number", ""))
        self._title_edit.setText(data.get("title", ""))
        self._client.setText(data.get("client", ""))
        self._lawyer.setText(data.get("lawyer", ""))
        self._court.setText(data.get("court", ""))
        self._description.setPlainText(data.get("description", ""))

    def clear(self) -> None:
        """Clear all fields."""
        self._case_number.clear()
        self._title_edit.clear()
        self._client.clear()
        self._lawyer.clear()
        self._court.clear()
        self._description.clear()
