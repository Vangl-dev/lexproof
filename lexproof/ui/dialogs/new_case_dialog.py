"""Diálogo mínimo para identificação de um novo caso."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)


class NewCaseDialog(QDialog):
    """Coleta os dados mínimos de um caso: cliente, processo, responsável e descrição.

    Sem etapas, sem processamento, sem geração de relatório.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo Caso")
        self.setModal(True)
        self.setMinimumWidth(420)

        self._client = QLineEdit(self)
        self._client.setPlaceholderText("Nome do cliente")
        self._case_number = QLineEdit(self)
        self._case_number.setPlaceholderText("Ex.: PROC-2024-001")
        self._technician = QLineEdit(self)
        self._technician.setPlaceholderText("Responsável técnico")
        self._description = QPlainTextEdit(self)
        self._description.setPlaceholderText("Descrição do caso")
        self._description.setMaximumHeight(120)

        form = QFormLayout()
        form.addRow("Cliente:", self._client)
        form.addRow("Número do processo:", self._case_number)
        form.addRow("Responsável técnico:", self._technician)
        form.addRow("Descrição:", self._description)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Criar caso")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_data(self) -> dict[str, str]:
        """Retorna os quatro campos preenchidos (strings aparadas)."""
        return {
            "client_name": self._client.text().strip(),
            "case_number": self._case_number.text().strip(),
            "responsible_technician": self._technician.text().strip(),
            "description": self._description.toPlainText().strip(),
        }

    def set_data(self, data: dict[str, str]) -> None:
        """Preenche os campos (usado em testes e reabertura futura)."""
        self._client.setText(data.get("client_name", ""))
        self._case_number.setText(data.get("case_number", ""))
        self._technician.setText(data.get("responsible_technician", ""))
        self._description.setPlainText(data.get("description", ""))
