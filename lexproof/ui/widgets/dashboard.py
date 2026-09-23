"""Dashboard moderno para o LexProof.

Tela inicial inspirada no Cantai com:
- Ações principais
- Sessões recentes
- Último relatório
"""

from __future__ import annotations

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


class DashboardWidget(QWidget):
    """Dashboard moderno com ações principais e informações recentes."""

    new_session_clicked = Signal()
    import_clicked = Signal()
    generate_report_clicked = Signal()
    session_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Inicializa o dashboard."""
        super().__init__(parent)
        self.setObjectName("dashboard")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface do dashboard."""
        # Scroll area principal
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container principal
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 32, 40, 32)
        container_layout.setSpacing(32)

        # Header
        header = self._create_header()
        container_layout.addWidget(header)

        # Ações principais
        actions_section = self._create_actions_section()
        container_layout.addWidget(actions_section)

        # Grid de cards
        grid_section = self._create_grid_section()
        container_layout.addWidget(grid_section)

        container_layout.addStretch()

        scroll.setWidget(container)

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_header(self) -> QWidget:
        """Cria o cabeçalho do dashboard."""
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Título
        title = QLabel("LexProof")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: palette(text);
            letter-spacing: -0.5px;
        """)
        layout.addWidget(title)

        # Subtítulo
        subtitle = QLabel("Preservacao Tecnica de Evidencias Digitais")
        subtitle.setStyleSheet("""
            font-size: 15px;
            color: palette(placeholderText);
            font-weight: 400;
        """)
        layout.addWidget(subtitle)

        return header

    def _create_actions_section(self) -> QWidget:
        """Cria a seção de ações principais."""
        section = QWidget()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Card: Nova Sessão
        new_session_card = Card(
            title="Nova Sessao",
            subtitle="Criar uma nova sessao de preservacao",
            icon="add",
        )
        new_session_card.setMinimumWidth(280)
        new_session_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        new_session_card.mousePressEvent = lambda _: self.new_session_clicked.emit()
        layout.addWidget(new_session_card)

        # Card: Importar Evidências
        import_card = Card(
            title="Importar Evidencias",
            subtitle="Importar prints, ZIPs ou conversas",
            icon="upload",
        )
        import_card.setMinimumWidth(280)
        import_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        import_card.mousePressEvent = lambda _: self.import_clicked.emit()
        layout.addWidget(import_card)

        # Card: Gerar Relatório
        report_card = Card(
            title="Gerar Relatorio",
            subtitle="Gerar relatorio de preservacao",
            icon="report",
        )
        report_card.setMinimumWidth(280)
        report_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        report_card.mousePressEvent = lambda _: self.generate_report_clicked.emit()
        layout.addWidget(report_card)

        return section

    def _create_grid_section(self) -> QWidget:
        """Cria a seção de grid com informações."""
        section = QWidget()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Card: Sessões Recentes
        recent_card = self._create_recent_sessions_card()
        recent_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(recent_card)

        # Card: Último Relatório
        last_report_card = self._create_last_report_card()
        last_report_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(last_report_card)

        return section

    def _create_recent_sessions_card(self) -> Card:
        """Cria o card de sessões recentes."""
        card = Card(
            title="Sessoes Recentes",
            subtitle="Ultimas sessoes de preservacao",
            icon="log",
        )

        # Placeholder - em producao seria preenchido com dados reais
        self._recent_sessions_label = QLabel("Nenhuma sessao recente")
        self._recent_sessions_label.setStyleSheet("""
            font-size: 13px;
            color: palette(placeholderText);
            padding: 20px 0;
        """)
        self._recent_sessions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.add_widget(self._recent_sessions_label)

        return card

    def _create_last_report_card(self) -> Card:
        """Cria o card do último relatório."""
        card = Card(
            title="Ultimo Relatorio",
            subtitle="Relatorio mais recente gerado",
            icon="report",
        )

        # Placeholder
        self._last_report_label = QLabel("Nenhum relatorio gerado")
        self._last_report_label.setStyleSheet("""
            font-size: 13px;
            color: palette(placeholderText);
            padding: 20px 0;
        """)
        self._last_report_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.add_widget(self._last_report_label)

        return card

    def update_session_data(self, session_data: dict) -> None:
        """Atualiza os dados da sessao no dashboard."""
        if session_data:
            evidence_count = session_data.get("evidence_count", 0)
            session_code = session_data.get("session_code", "")
            self._recent_sessions_label.setText(
                f"Sessao: {session_code}\n"
                f"Evidencias: {evidence_count}"
            )
            self._recent_sessions_label.setStyleSheet("""
                font-size: 13px;
                color: palette(text);
                padding: 20px 0;
            """)

    def update_report_data(self, report_path: str) -> None:
        """Atualiza os dados do relatorio no dashboard."""
        if report_path:
            from pathlib import Path
            report_name = Path(report_path).name
            self._last_report_label.setText(f"Relatorio: {report_name}")
            self._last_report_label.setStyleSheet("""
                font-size: 13px;
                color: palette(text);
                padding: 20px 0;
            """)
