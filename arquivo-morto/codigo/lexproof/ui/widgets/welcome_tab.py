"""WelcomeTab — modern landing page with cards, drop zone, and recent cases."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from lexproof.ui.icons import get_icon
from lexproof.ui.styles.constants import (
    CARD_MIN_HEIGHT,
    CARD_MIN_WIDTH,
    CARD_PADDING,
    CARD_RADIUS,
    CARD_SHADOW_BLUR,
    CARD_SHADOW_Y,
    SPACING_LG,
    SPACING_MD,
    SPACING_SM,
    SPACING_XL,
    SPACING_XXL,
    WELCOME_DROP_MIN_HEIGHT,
    WELCOME_MAX_WIDTH,
)


def _svg_icon_label(svg: str, size: int = 32) -> QLabel:
    """Create a QLabel displaying an inline SVG."""
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QImage, QPixmap

    lbl = QLabel()
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    data = QByteArray(svg.encode("utf-8"))
    img = QImage.fromData(data)
    if not img.isNull():
        pixmap = QPixmap.fromImage(img).scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        lbl.setPixmap(pixmap)
    return lbl


class _DropZone(QFrame):
    """Central drag-and-drop area with dashed border and highlight state."""

    files_dropped = Signal(list)

    _BORDER_WIDTH: int = 2
    _BORDER_RADIUS: int = 12
    _HIGHLIGHT_BORDER_WIDTH: int = 3

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropArea")
        self.setMinimumHeight(WELCOME_DROP_MIN_HEIGHT)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._highlighted: bool = False

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(SPACING_SM)

        icon_label = _svg_icon_label(get_icon("upload"), 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setObjectName("dropIcon")

        text_label = QLabel("Arraste arquivos aqui para iniciar")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setObjectName("dropText")

        sub_label = QLabel("Suporta: PNG, JPG, TXT do WhatsApp, PDF, ZIP")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_label.setObjectName("dropSubText")

        layout.addStretch()
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

    def paintEvent(self, event: object) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        border_color = (
            self.palette().highlight()
            if self._highlighted
            else self.palette().mid()
        )
        pen_width = self._HIGHLIGHT_BORDER_WIDTH if self._highlighted else self._BORDER_WIDTH
        pen = QPen(border_color, pen_width, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            self.rect().adjusted(1, 1, -1, -1),
            self._BORDER_RADIUS,
            self._BORDER_RADIUS,
        )
        painter.end()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._highlighted = True
            self.update()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._highlighted = False
        self.update()

    def dropEvent(self, event: QDropEvent) -> None:
        self._highlighted = False
        self.update()
        paths: list[str] = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        if paths:
            self.files_dropped.emit(paths)


class _ActionCard(QFrame):
    """Clickable action card with icon, title, and description."""

    clicked = Signal()

    def __init__(
        self,
        icon_name: str,
        title: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(CARD_MIN_WIDTH)
        self.setMinimumHeight(CARD_MIN_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        layout.setSpacing(SPACING_SM)

        icon_label = _svg_icon_label(get_icon(icon_name), 28)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("cardTitle")

        desc_label = QLabel(description)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setObjectName("cardDescription")
        desc_label.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(CARD_SHADOW_BLUR)
        shadow.setOffset(0, CARD_SHADOW_Y)
        shadow.setColor(self.palette().shadow().color())
        self.setGraphicsEffect(shadow)

    def enterEvent(self, event: object) -> None:  # noqa: ANN001
        self.setStyleSheet(
            "#card { background-color: palette(mid); }"
        )

    def leaveEvent(self, event: object) -> None:  # noqa: ANN001
        self.setStyleSheet("")

    def mousePressEvent(self, event: object) -> None:  # noqa: ANN001
        self.clicked.emit()


class _CaseCard(QFrame):
    """Single recent-case card showing name, date, and evidence count."""

    case_selected = Signal(str)

    def __init__(
        self,
        case_name: str,
        case_date: str,
        evidence_count: int,
        case_path: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(CARD_MIN_WIDTH)
        self.setMinimumHeight(CARD_MIN_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._case_path = case_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        layout.setSpacing(SPACING_SM)

        name_label = QLabel(case_name)
        name_label.setObjectName("caseName")
        name_label.setWordWrap(True)

        date_label = QLabel(case_date)
        date_label.setObjectName("caseDate")

        count_label = QLabel(f"{evidence_count} evidencia{'s' if evidence_count != 1 else ''}")
        count_label.setObjectName("caseCount")

        layout.addWidget(name_label)
        layout.addWidget(date_label)
        layout.addStretch()
        layout.addWidget(count_label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(CARD_SHADOW_BLUR)
        shadow.setOffset(0, CARD_SHADOW_Y)
        shadow.setColor(self.palette().shadow().color())
        self.setGraphicsEffect(shadow)

    def enterEvent(self, event: object) -> None:  # noqa: ANN001
        self.setStyleSheet("#card { background-color: palette(mid); }")

    def leaveEvent(self, event: object) -> None:  # noqa: ANN001
        self.setStyleSheet("")

    def mousePressEvent(self, event: object) -> None:  # noqa: ANN001
        self.case_selected.emit(self._case_path)


class WelcomeTab(QWidget):
    """Welcome screen — primary entry point for LexProof.

    Sections (top to bottom):
        1. Header with app title, subtitle, and version.
        2. Three action cards: Novo Caso, Abrir Caso, Usar Assistente.
        3. Prominent drag-and-drop zone.
        4. Recent cases grid (2x2, up to 4 items).
    """

    new_case_clicked = Signal()
    open_case_clicked = Signal()
    wizard_clicked = Signal()
    case_selected = Signal(str)
    files_dropped = Signal(list)

    _VERSION: str = "v0.1.0"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        scroll.setWidget(container)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Center everything with max width
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(SPACING_XXL, SPACING_XXL, SPACING_XXL, SPACING_XXL)
        center_layout.setSpacing(SPACING_XL)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        center_container.setMaximumWidth(WELCOME_MAX_WIDTH)

        center_layout.addWidget(self._create_header())
        center_layout.addWidget(self._create_action_cards())
        center_layout.addWidget(self._create_drop_zone())
        center_layout.addWidget(self._create_recent_cases_section())
        center_layout.addStretch()

        wrapper = QHBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(center_container, alignment=Qt.AlignmentFlag.AlignHCenter)

        main_layout.addLayout(wrapper)

    def _create_header(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Shield icon
        shield_icon = _svg_icon_label(get_icon("shield"), 48)
        shield_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("LexProof")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Sistema de Preservacao Tecnica de Evidencias Digitais")
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel(self._VERSION)
        version.setObjectName("appVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(shield_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(version)
        return widget

    def _create_drop_zone(self) -> _DropZone:
        return _DropZone()

    def _create_action_cards(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_new = _ActionCard(
            icon_name="add",
            title="Novo Caso",
            description="Criar caso de analise do zero",
        )
        card_open = _ActionCard(
            icon_name="open_folder",
            title="Abrir Caso",
            description="Continuar trabalho anterior",
        )
        card_wizard = _ActionCard(
            icon_name="magic_wand",
            title="Usar Assistente",
            description="Guia passo a passo",
        )

        layout.addWidget(card_new)
        layout.addWidget(card_open)
        layout.addWidget(card_wizard)

        self._card_new = card_new
        self._card_open = card_open
        self._card_wizard = card_wizard
        return widget

    def _create_recent_cases_section(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        title = QLabel("Casos Recentes")
        title.setObjectName("recentCasesTitle")
        layout.addWidget(title)

        self._cases_grid = QHBoxLayout()
        self._cases_grid.setSpacing(SPACING_LG)
        self._cases_grid.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._no_cases_label = QLabel("Nenhum caso recente")
        self._no_cases_label.setObjectName("noCasesLabel")
        self._no_cases_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_cases_label.hide()

        self._cases_grid_watcher = QWidget()
        self._cases_grid_watcher.setLayout(self._cases_grid)

        layout.addWidget(self._cases_grid_watcher)
        layout.addWidget(self._no_cases_label)
        layout.addStretch()

        self._set_empty_cases()
        return widget

    def _set_empty_cases(self) -> None:
        self._clear_cases_grid()
        self._no_cases_label.show()
        self._cases_grid_watcher.hide()

    def _clear_cases_grid(self) -> None:
        while self._cases_grid.count():
            item = self._cases_grid.takeAt(0)
            if (child := item.widget()) is not None:
                child.deleteLater()

    def set_recent_cases(
        self, cases: list[tuple[str, str, int, str]]
    ) -> None:
        """Populate the recent-cases grid.

        Each entry is ``(name, date, evidence_count, path)``.
        At most four items are shown in a 2x2 grid.
        """
        self._clear_cases_grid()

        if not cases:
            self._set_empty_cases()
            return

        self._no_cases_label.hide()
        self._cases_grid_watcher.show()

        for case_name, case_date, evidence_count, case_path in cases[:4]:
            card = _CaseCard(case_name, case_date, evidence_count, case_path)
            card.case_selected.connect(self.case_selected.emit)
            self._cases_grid.addWidget(card)

    def _connect_signals(self) -> None:
        self._card_new.clicked.connect(self.new_case_clicked.emit)
        self._card_open.clicked.connect(self.open_case_clicked.emit)
        self._card_wizard.clicked.connect(self.wizard_clicked.emit)

        drop_zone = self.findChild(_DropZone, "dropArea")
        if drop_zone is not None:
            drop_zone.files_dropped.connect(self.files_dropped.emit)
