"""Widget de relatório para o LexProof.

Mostra o status do relatório e permite gerar novos relatórios.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from lexproof.ui.widgets.card import Card


class ReportPanelWidget(QWidget):
    """Widget de relatório."""

    generate_report_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reportPanel")
        self._report_path = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 32, 40, 32)
        container_layout.setSpacing(24)

        header = self._create_header()
        container_layout.addWidget(header)

        self._status_card = self._create_status_card()
        container_layout.addWidget(self._status_card)

        self._generate_card = self._create_generate_card()
        container_layout.addWidget(self._generate_card)

        self._open_card = self._create_open_card()
        container_layout.addWidget(self._open_card)

        container_layout.addStretch()

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_header(self) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Relatorio de Preservacao")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: palette(text);
        """)
        layout.addWidget(title)

        subtitle = QLabel("Gere e visualize relatorios de preservacao de evidencias")
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: palette(placeholderText);
        """)
        layout.addWidget(subtitle)

        return header

    def _create_status_card(self) -> Card:
        card = Card(
            title="Status do Relatorio",
            subtitle="Informacoes sobre o relatorio atual",
            icon="report",
        )

        self._status_label = QLabel("Nenhum relatorio gerado")
        self._status_label.setStyleSheet("""
            font-size: 13px;
            color: palette(placeholderText);
            padding: 20px 0;
        """)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        card.add_widget(self._status_label)

        return card

    def _create_generate_card(self) -> Card:
        card = Card(
            title="Gerar Relatorio",
            subtitle="Clique para gerar o relatorio de preservacao",
            icon="report",
        )
        card.mousePressEvent = lambda _: self.generate_report_clicked.emit()
        return card

    def _create_open_card(self) -> Card:
        card = Card(
            title="Abrir Relatorio",
            subtitle="Abrir o ultimo relatorio gerado",
            icon="report",
        )
        card.mousePressEvent = lambda _: self._open_report()
        return card

    def _open_report(self) -> None:
        if not self._report_path:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "Relatorio", "Nenhum relatorio disponivel.\nGere um relatorio primeiro."
            )
            return

        if not Path(self._report_path).exists():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Relatorio", f"Arquivo nao encontrado:\n{self._report_path}"
            )
            return

        import subprocess
        import sys
        try:
            result = None
            if sys.platform == "linux":
                result = subprocess.run(
                    ["xdg-open", self._report_path],
                    timeout=10,
                    capture_output=True,
                )
            elif sys.platform == "darwin":
                result = subprocess.run(
                    ["open", self._report_path],
                    timeout=10,
                    capture_output=True,
                )
            elif sys.platform == "win32":
                os.startfile(self._report_path)

            if result is not None and result.returncode != 0:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Relatorio",
                    f"Nao foi possivel abrir o relatorio automaticamente.\n"
                    f"Arquivo: {self._report_path}",
                )
        except FileNotFoundError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Relatorio",
                f"Nao foi possivel abrir o relatorio.\n"
                f"Arquivo: {self._report_path}",
            )
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Relatorio",
                f"Erro ao abrir relatorio: {exc}\n"
                f"Arquivo: {self._report_path}",
            )

    def update_status(self, status: str, report_path: str = "") -> None:
        self._status_label.setText(status)
        self._status_label.setStyleSheet("""
            font-size: 13px;
            color: palette(text);
            padding: 20px 0;
        """)
        if report_path:
            self._report_path = report_path
