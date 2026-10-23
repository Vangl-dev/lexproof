from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPropertyAnimation,
    QRect,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Position(Enum):
    """Tooltip position relative to the target widget."""

    BOTTOM = "bottom"
    TOP = "top"
    LEFT = "left"
    RIGHT = "right"


@dataclass
class TourStep:
    """A single step in the guided tour."""

    title: str
    description: str
    target_widget: QWidget | None = None
    position: Position = Position.BOTTOM


class TourOverlay(QWidget):
    """Semi-transparent overlay that highlights a specific UI element with a tooltip card."""

    next_clicked = Signal()
    skip_clicked = Signal()

    PADDING = 12
    CARD_RADIUS = 12
    HOLE_MARGIN = 8

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._target_rect = QRect()
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(250)

        self._step_label = QLabel(self)
        self._title_label = QLabel(self)
        self._desc_label = QLabel(self)
        self._desc_label.setWordWrap(True)
        self._next_btn = QPushButton(self)
        self._skip_btn = QPushButton(self)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        self._step_label.setAlignment(Qt.AlignCenter)
        self._step_label.setStyleSheet("font-weight: bold;")
        self._title_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        self._desc_label.setStyleSheet("font-size: 13px;")
        self._next_btn.setText("Próximo")
        self._skip_btn.setText("Pular Tour")
        self._skip_btn.setStyleSheet("border: none; text-decoration: underline;")
        self._skip_btn.setCursor(Qt.PointingHandCursor)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self._skip_btn)
        btn_layout.addWidget(self._next_btn)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(6)
        card_layout.addWidget(self._step_label)
        card_layout.addWidget(self._title_label)
        card_layout.addSpacing(4)
        card_layout.addWidget(self._desc_label)
        card_layout.addSpacing(8)
        card_layout.addLayout(btn_layout)

        self._card = QWidget(self)
        self._card.setLayout(card_layout)
        self._card.setObjectName("tourCard")

    def _connect_signals(self) -> None:
        self._next_btn.clicked.connect(self.next_clicked.emit)
        self._skip_btn.clicked.connect(self.skip_clicked.emit)

    def configure(
        self,
        step_number: int,
        total_steps: int,
        title: str,
        description: str,
        target_widget: QWidget | None,
        position: Position,
        is_last: bool,
    ) -> None:
        self._step_label.setText(f"{step_number} de {total_steps}")
        self._title_label.setText(title)
        self._desc_label.setText(description)
        self._next_btn.setText("Concluir" if is_last else "Próximo")

        self._target_rect = QRect()
        if target_widget is not None:
            self._target_rect = target_widget.rect()
            map_pos = target_widget.mapToParent(self.parent().pos())
            self._target_rect.moveTopLeft(
                target_widget.mapTo(self.parent(), target_widget.rect().topLeft())
            )

        self._position_card(position)
        self.update()

    def _position_card(self, position: Position) -> None:
        card = self._card
        card.adjustSize()
        card_w = card.sizeHint().width()
        card_h = card.sizeHint().height()
        pw = self.parent().width()
        ph = self.parent().height()

        gap = self.PADDING + self.HOLE_MARGIN

        if self._target_rect.isNull():
            x = (pw - card_w) // 2
            y = (ph - card_h) // 2
        else:
            cx = self._target_rect.center().x()
            cy = self._target_rect.center().y()

            if position == Position.BOTTOM:
                x = cx - card_w // 2
                y = self._target_rect.bottom() + gap
            elif position == Position.TOP:
                x = cx - card_w // 2
                y = self._target_rect.top() - card_h - gap
            elif position == Position.LEFT:
                x = self._target_rect.left() - card_w - gap
                y = cy - card_h // 2
            else:  # RIGHT
                x = self._target_rect.right() + gap
                y = cy - card_h // 2

        x = max(0, min(x, pw - card_w))
        y = max(0, min(y, ph - card_h))

        card.setGeometry(x, y, card_w, card_h)

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 140))

        if not self._target_rect.isNull():
            hole = self._target_rect.adjusted(
                -self.HOLE_MARGIN,
                -self.HOLE_MARGIN,
                self.HOLE_MARGIN,
                self.HOLE_MARGIN,
            )
            path = QPainterPath()
            path.addRect(self.rect())
            hole_path = QPainterPath()
            hole_path.addRoundedRect(hole, 6, 6)
            path = path.united(hole_path)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillPath(path, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        card_rect = self._card.geometry()
        shadow_rect = card_rect.adjusted(2, 2, 2, 2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawRoundedRect(shadow_rect, self.CARD_RADIUS, self.CARD_RADIUS)

        card_bg = self.palette().window()
        painter.setBrush(card_bg)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(card_rect, self.CARD_RADIUS, self.CARD_RADIUS)

        painter.end()

    def fade_in(self) -> None:
        self._fade_anim.stop()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self.show()
        self._fade_anim.start()

    def fade_out(self) -> None:
        self._fade_anim.stop()
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()


class TourManager:
    """Singleton manager for the guided tour."""

    _instance: TourManager | None = None

    def __new__(cls) -> TourManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._completed_path = Path.home() / ".lexproof" / "tour_completed"
        self._overlay: TourOverlay | None = None
        self._steps: list[TourStep] = []
        self._current_index = 0
        self._parent: QWidget | None = None

    @classmethod
    def instance(cls) -> TourManager:
        return cls()

    def is_first_run(self) -> bool:
        return not self._completed_path.exists()

    def mark_tour_completed(self) -> None:
        self._completed_path.parent.mkdir(parents=True, exist_ok=True)
        self._completed_path.touch()

    def start_tour(
        self, parent: QWidget, steps: list[TourStep] | None = None
    ) -> None:
        self._parent = parent
        self._steps = steps if steps is not None else self._default_steps()
        self._current_index = 0

        if self._overlay is None:
            self._overlay = TourOverlay(parent)
            self._overlay.next_clicked.connect(self._on_next)
            self._overlay.skip_clicked.connect(self._on_skip)

        self._show_step()

    def _default_steps(self) -> list[TourStep]:
        return [
            TourStep(
                title="Bem-vindo ao LexProof!",
                description=(
                    "O LexProof é uma plataforma para gerenciamento e análise "
                    "de documentos jurídicos. Vamos fazer um tour rápido pelas "
                    "principais funcionalidades."
                ),
                position=Position.BOTTOM,
            ),
            TourStep(
                title="Navigation Rail",
                description=(
                    "Use a barra de navegação à esquerda para alternar entre "
                    "as seções do aplicativo: Casos, Documentos, Relatórios e "
                    "Configurações."
                ),
                position=Position.RIGHT,
            ),
            TourStep(
                title="Arrastar Arquivos",
                description=(
                    "Arraste e solte arquivos PDF, DOCX ou TXT diretamente "
                    "na área de trabalho para importá-los automaticamente."
                ),
                position=Position.BOTTOM,
            ),
            TourStep(
                title="Criar Caso",
                description=(
                    "Clique neste botão para criar um novo caso jurídico. Você "
                    "poderá adicionar documentos, definir categorias e atribuir "
                    "responsáveis."
                ),
                position=Position.RIGHT,
            ),
            TourStep(
                title="Gerar Relatório",
                description=(
                    "Use o assistente de relatórios para gerar análises "
                    "detalhadas dos seus casos. Escolha o modelo, selecione "
                    "os documentos e exporte em PDF."
                ),
                position=Position.LEFT,
            ),
        ]

    def _show_step(self) -> None:
        if self._overlay is None or self._parent is None:
            return
        if self._current_index >= len(self._steps):
            self._cleanup()
            return

        step = self._steps[self._current_index]
        self._overlay.configure(
            step_number=self._current_index + 1,
            total_steps=len(self._steps),
            title=step.title,
            description=step.description,
            target_widget=step.target_widget,
            position=step.position,
            is_last=self._current_index == len(self._steps) - 1,
        )
        self._overlay.fade_in()

    @Slot()
    def _on_next(self) -> None:
        if self._overlay is not None:
            self._overlay.fade_out()
        self._current_index += 1
        if self._current_index >= len(self._steps):
            self.mark_tour_completed()
            self._cleanup()
        else:
            self._show_step()

    @Slot()
    def _on_skip(self) -> None:
        self.mark_tour_completed()
        if self._overlay is not None:
            self._overlay.fade_out()
        self._cleanup()

    def _cleanup(self) -> None:
        if self._overlay is not None:
            self._overlay.hide()
        self._current_index = 0
