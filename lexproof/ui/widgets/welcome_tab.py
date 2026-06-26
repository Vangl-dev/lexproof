from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class WelcomeTab(QWidget):
    """Welcome/start screen with action cards for common tasks."""

    new_case_clicked = Signal()
    open_case_clicked = Signal()
    import_files_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(24)

        main_layout.addStretch()

        title_label = QLabel("LexProof")
        title_label.setObjectName("appTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Preservacao de Evidencias Digitais")
        subtitle_label.setObjectName("appSubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_new = self._create_card(
            icon="☐",
            title="Novo Caso",
            description="Criar um novo caso de analise",
            signal=self.new_case_clicked,
        )
        card_open = self._create_card(
            icon="📂",
            title="Abrir Caso",
            description="Abrir um caso existente",
            signal=self.open_case_clicked,
        )
        card_import = self._create_card(
            icon="⬇",
            title="Importar Arquivos",
            description="Adicionar evidencias",
            signal=self.import_files_clicked,
        )

        cards_layout.addWidget(card_new)
        cards_layout.addWidget(card_open)
        cards_layout.addWidget(card_import)

        hint_label = QLabel("Arraste arquivos aqui ou selecione uma opcao acima")
        hint_label.setObjectName("subheadingLabel")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(cards_layout)
        main_layout.addWidget(hint_label, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addStretch()

    def _create_card(
        self,
        icon: str,
        title: str,
        description: str,
        signal: Signal,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(200)
        card.setFixedHeight(120)
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName("headingLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc_label = QLabel(description)
        desc_label.setObjectName("subheadingLabel")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)
        card_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(desc_label, alignment=Qt.AlignmentFlag.AlignCenter)

        card.mousePressEvent = lambda _: signal.emit()

        return card
