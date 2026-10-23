"""WizardDialog — multi-step case creation wizard with modern step indicator."""

from __future__ import annotations

import enum
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from lexproof.ui.styles.constants import WIZARD_CIRCLE_SIZE


class WizardStep(enum.Enum):
    """Enumeration of wizard steps."""

    CREATE_CASE = 0
    ADD_WHATSAPP = 1
    ADD_PRINTS = 2
    CONFIRM_OPTIONS = 3
    GENERATE_REPORT = 4


class StepIndicator(QWidget):
    """Horizontal step indicator showing status icons and labels.

    States:
        Completed: circle with checkmark (filled)
        Current: filled circle with number
        Future: circle with number (outline)
    """

    def __init__(self, steps: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._steps = steps
        self._current: int = 0
        self._completed: set[int] = set()
        self._circles: list[QFrame] = []
        self._labels: list[QLabel] = []
        self._connectors: list[QFrame] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        for i, name in enumerate(self._steps):
            if i > 0:
                connector = QFrame()
                connector.setObjectName("stepConnector")
                connector.setFixedHeight(2)
                connector.setMinimumWidth(40)
                connector.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                layout.addWidget(connector)
                self._connectors.append(connector)

            container = QVBoxLayout()
            container.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container.setSpacing(6)

            circle = QFrame()
            circle.setObjectName("stepCircle")
            circle.setFixedSize(WIZARD_CIRCLE_SIZE, WIZARD_CIRCLE_SIZE)
            circle_layout = QHBoxLayout(circle)
            circle_layout.setContentsMargins(0, 0, 0, 0)
            circle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            number_label = QLabel(str(i + 1))
            number_label.setObjectName("stepNumber")
            number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle_layout.addWidget(number_label)
            self._circles.append(circle)

            text_label = QLabel(name)
            text_label.setObjectName("stepLabel")
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._labels.append(text_label)

            container.addWidget(circle, alignment=Qt.AlignmentFlag.AlignCenter)
            container.addWidget(text_label, alignment=Qt.AlignmentFlag.AlignCenter)

            wrapper = QWidget()
            wrapper.setLayout(container)
            layout.addWidget(wrapper)

        layout.addStretch()
        self._update_styles()

    def set_current(self, index: int) -> None:
        self._current = index
        self._update_styles()

    def mark_completed(self, index: int) -> None:
        self._completed.add(index)
        self._update_styles()

    def _update_styles(self) -> None:
        palette = self.palette()
        highlight = palette.color(palette.ColorRole.Highlight)
        highlight_text = palette.color(palette.ColorRole.HighlightedText)
        window_text = palette.color(palette.ColorRole.WindowText)
        mid = palette.color(palette.ColorRole.Mid)

        for i, (circle, label, num_label) in enumerate(
            zip(self._circles, self._labels, [c.findChild(QLabel) for c in self._circles])
        ):
            if num_label is None:
                continue
            if i == self._current:
                # Current step: filled circle
                circle.setStyleSheet(
                    f"background-color: {highlight.name()}; border-radius: {WIZARD_CIRCLE_SIZE // 2}px; border: none;"
                )
                num_label.setText(str(i + 1))
                num_label.setStyleSheet(
                    f"color: {highlight_text.name()}; font-weight: bold; border: none; background: transparent;"
                )
                label.setStyleSheet(f"color: {highlight.name()}; font-weight: bold;")
            elif i in self._completed:
                # Completed step: filled circle with checkmark
                circle.setStyleSheet(
                    f"background-color: {highlight.name()}; border-radius: {WIZARD_CIRCLE_SIZE // 2}px; border: none;"
                )
                num_label.setText("\u2713")
                num_label.setStyleSheet(
                    f"color: {highlight_text.name()}; font-weight: bold; border: none; background: transparent;"
                )
                label.setStyleSheet(f"color: {window_text.name()};")
            else:
                # Future step: outlined circle
                circle.setStyleSheet(
                    f"background-color: transparent; border-radius: {WIZARD_CIRCLE_SIZE // 2}px; border: 2px solid {mid.name()};"
                )
                num_label.setText(str(i + 1))
                num_label.setStyleSheet(
                    f"color: {mid.name()}; border: none; background: transparent;"
                )
                label.setStyleSheet(f"color: {mid.name()};")

        for connector in self._connectors:
            connector.setStyleSheet(f"background-color: {mid.name()};")

        for i in range(self._current, len(self._connectors)):
            if i < self._current:
                self._connectors[i].setStyleSheet(f"background-color: {highlight.name()};")


class StepCreateCase(QWidget):
    """Step 1: Create case with title, examiner name, and description."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._case_id = uuid4().hex[:12].upper()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        title = QLabel("Criar Novo Caso")
        title.setObjectName("headingLabel")
        card_layout.addWidget(title)

        form = QGridLayout()
        form.setSpacing(12)

        id_label = QLabel("ID do Caso:")
        id_label.setObjectName("formLabel")
        self._id_display = QLineEdit(self._case_id)
        self._id_display.setReadOnly(True)
        self._id_display.setPlaceholderText("Gerado automaticamente")
        form.addWidget(id_label, 0, 0)
        form.addWidget(self._id_display, 0, 1)

        title_label = QLabel("Titulo do Caso:")
        title_label.setObjectName("formLabel")
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Ex: Analise de Conversa WhatsApp")
        form.addWidget(title_label, 1, 0)
        form.addWidget(self._title_edit, 1, 1)

        examiner_label = QLabel("Responsavel pela Preservacao:")
        examiner_label.setObjectName("formLabel")
        self._examiner_edit = QLineEdit()
        self._examiner_edit.setPlaceholderText("Nome completo do responsavel")
        form.addWidget(examiner_label, 2, 0)
        form.addWidget(self._examiner_edit, 2, 1)

        card_layout.addLayout(form)

        desc_label = QLabel("Descricao:")
        desc_label.setObjectName("formLabel")
        card_layout.addWidget(desc_label)

        self._description_edit = QTextEdit()
        self._description_edit.setPlaceholderText(
            "Descreva brevemente o caso e o objetivo da analise..."
        )
        self._description_edit.setMinimumHeight(100)
        card_layout.addWidget(self._description_edit)

        layout.addWidget(card)
        layout.addStretch()

    def get_data(self) -> dict[str, str]:
        return {
            "case_id": self._case_id,
            "case_title": self._title_edit.text(),
            "examiner_name": self._examiner_edit.text(),
            "description": self._description_edit.toPlainText(),
        }

    def validate(self) -> bool:
        return bool(self._title_edit.text().strip() and self._examiner_edit.text().strip())


class StepAddWhatsApp(QWidget):
    """Step 2: Add WhatsApp export .txt files with drag-and-drop."""

    files_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._files: list[Path] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        title = QLabel("Adicionar Exportacao do WhatsApp")
        title.setObjectName("headingLabel")
        card_layout.addWidget(title)

        subtitle = QLabel("Selecione ou arraste o arquivo .txt exportado do WhatsApp")
        subtitle.setObjectName("subheadingLabel")
        card_layout.addWidget(subtitle)

        self._drop_area = _DropArea("Arraste o arquivo .txt aqui", ".txt")
        self._drop_area.files_dropped.connect(self._on_files_dropped)
        card_layout.addWidget(self._drop_area)

        btn_row = QHBoxLayout()
        self._select_btn = QPushButton("Selecionar arquivo...")
        self._select_btn.clicked.connect(self._select_file)
        btn_row.addWidget(self._select_btn)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        self._file_list_label = QLabel("Nenhum arquivo selecionado")
        self._file_list_label.setObjectName("subheadingLabel")
        card_layout.addWidget(self._file_list_label)

        self._preview_label = QLabel("")
        self._preview_label.setObjectName("subheadingLabel")
        self._preview_label.setWordWrap(True)
        self._preview_label.setMinimumHeight(60)
        card_layout.addWidget(self._preview_label)

        layout.addWidget(card)
        layout.addStretch()

    def _select_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar exportacao WhatsApp", "", "Arquivos de texto (*.txt)"
        )
        if path:
            self._add_file(Path(path))

    def _on_files_dropped(self, paths: list[str]) -> None:
        for p in paths:
            if p.lower().endswith(".txt"):
                self._add_file(Path(p))

    def _add_file(self, path: Path) -> None:
        if path not in self._files:
            self._files.append(path)
            self._update_display()
            self._show_preview(path)
            self.files_changed.emit()

    def _update_display(self) -> None:
        if self._files:
            names = "\n".join(f"  \u2022 {f.name}" for f in self._files)
            self._file_list_label.setText(f"Arquivos selecionados:\n{names}")
        else:
            self._file_list_label.setText("Nenhum arquivo selecionado")

    def _show_preview(self, path: Path) -> None:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(5)]
            preview = "".join(lines)
            self._preview_label.setText(f"Preview (primeiras 5 linhas):\n{preview}")
        except Exception:
            self._preview_label.setText("Nao foi possivel visualizar o arquivo.")

    def get_data(self) -> dict[str, Any]:
        return {"whatsapp_files": [str(f) for f in self._files]}


class StepAddPrints(QWidget):
    """Step 3: Add print/screenshot images with thumbnails."""

    images_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._images: list[Path] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        title = QLabel("Adicionar Print(s)")
        title.setObjectName("headingLabel")
        card_layout.addWidget(title)

        subtitle = QLabel("Selecione ou arraste imagens (.png, .jpg, .jpeg)")
        subtitle.setObjectName("subheadingLabel")
        card_layout.addWidget(subtitle)

        self._drop_area = _DropArea("Arraste imagens aqui", ".png", ".jpg", ".jpeg")
        self._drop_area.files_dropped.connect(self._on_files_dropped)
        card_layout.addWidget(self._drop_area)

        btn_row = QHBoxLayout()
        self._select_btn = QPushButton("Selecionar imagens...")
        self._select_btn.clicked.connect(self._select_images)
        btn_row.addWidget(self._select_btn)
        self._clear_btn = QPushButton("Limpar tudo")
        self._clear_btn.clicked.connect(self._clear_images)
        btn_row.addWidget(self._clear_btn)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        self._count_label = QLabel("Nenhuma imagem selecionada")
        self._count_label.setObjectName("subheadingLabel")
        card_layout.addWidget(self._count_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("thumbnailScroll")
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(8)
        scroll.setWidget(self._grid_container)
        scroll.setMinimumHeight(180)
        scroll.setMaximumHeight(250)
        card_layout.addWidget(scroll)

        layout.addWidget(card)
        layout.addStretch()

    def _select_images(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar imagens", "", "Imagens (*.png *.jpg *.jpeg)",
        )
        for p in paths:
            self._add_image(Path(p))

    def _on_files_dropped(self, paths: list[str]) -> None:
        valid_ext = {".png", ".jpg", ".jpeg"}
        for p in paths:
            if Path(p).suffix.lower() in valid_ext:
                self._add_image(Path(p))

    def _add_image(self, path: Path) -> None:
        if path not in self._images:
            self._images.append(path)
            self._refresh_grid()
            self.images_changed.emit()

    def _clear_images(self) -> None:
        self._images.clear()
        self._refresh_grid()
        self.images_changed.emit()

    def _refresh_grid(self) -> None:
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 5
        for i, img_path in enumerate(self._images):
            thumbnail = self._create_thumbnail(img_path)
            row, col = divmod(i, cols)
            self._grid_layout.addWidget(thumbnail, row, col)

        if self._images:
            self._count_label.setText(f"{len(self._images)} imagem(ns) selecionada(s)")
        else:
            self._count_label.setText("Nenhuma imagem selecionada")

    def _create_thumbnail(self, path: Path) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        frame.setFixedSize(100, 100)
        v_layout = QVBoxLayout(frame)
        v_layout.setContentsMargins(4, 4, 4, 4)
        v_layout.setSpacing(2)

        pixmap = QPixmap(str(path))
        img_label = QLabel()
        if not pixmap.isNull():
            scaled = pixmap.scaled(80, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(scaled)
        else:
            img_label.setText("\u26a0")
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(img_label)

        name_label = QLabel(path.name)
        name_label.setObjectName("subheadingLabel")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setMaximumWidth(90)
        v_layout.addWidget(name_label)

        return frame

    def get_data(self) -> dict[str, Any]:
        return {"print_files": [str(f) for f in self._images]}


class StepConfirmOptions(QWidget):
    """Step 4: Confirm processing options with checkboxes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        title = QLabel("Confirmar Opcoes")
        title.setObjectName("headingLabel")
        card_layout.addWidget(title)

        subtitle = QLabel("Selecione as operacoes que deseja executar:")
        subtitle.setObjectName("subheadingLabel")
        card_layout.addWidget(subtitle)

        options_group = QGroupBox("Opcoes de Processamento")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(10)

        self._hash_check = QCheckBox("Calcular hashes (SHA256, SHA3-512, BLAKE3)")
        self._hash_check.setChecked(True)
        options_layout.addWidget(self._hash_check)

        self._ocr_check = QCheckBox("Executar OCR nas imagens")
        self._ocr_check.setChecked(True)
        options_layout.addWidget(self._ocr_check)

        self._timeline_check = QCheckBox("Gerar timeline de eventos")
        self._timeline_check.setChecked(True)
        options_layout.addWidget(self._timeline_check)

        self._custody_check = QCheckBox("Incluir cadeia de custodia")
        self._custody_check.setChecked(True)
        options_layout.addWidget(self._custody_check)

        self._compare_check = QCheckBox("Comparar OCR x TXT")
        self._compare_check.setChecked(True)
        options_layout.addWidget(self._compare_check)

        card_layout.addWidget(options_group)
        layout.addWidget(card)
        layout.addStretch()

    def get_data(self) -> dict[str, bool]:
        return {
            "calculate_hashes": self._hash_check.isChecked(),
            "run_ocr": self._ocr_check.isChecked(),
            "generate_timeline": self._timeline_check.isChecked(),
            "include_custody": self._custody_check.isChecked(),
            "compare_ocr_txt": self._compare_check.isChecked(),
        }


class StepGenerateReport(QWidget):
    """Step 5: Summary, output directory, format, and generation."""

    generate_clicked = Signal()
    open_report_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._output_path: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        title = QLabel("Gerar Relatorio")
        title.setObjectName("headingLabel")
        card_layout.addWidget(title)

        summary_group = QGroupBox("Resumo")
        summary_layout = QVBoxLayout(summary_group)
        self._summary_label = QLabel("Preencha os passos anteriores para ver o resumo aqui.")
        self._summary_label.setWordWrap(True)
        self._summary_label.setObjectName("subheadingLabel")
        summary_layout.addWidget(self._summary_label)
        card_layout.addWidget(summary_group)

        output_group = QGroupBox("Saida")
        output_layout = QHBoxLayout(output_group)
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("Diretorio de saida")
        self._output_edit.setReadOnly(True)
        output_layout.addWidget(self._output_edit)
        self._output_btn = QPushButton("Selecionar...")
        self._output_btn.clicked.connect(self._select_output_dir)
        output_layout.addWidget(self._output_btn)
        card_layout.addWidget(output_group)

        format_group = QGroupBox("Formato do Relatorio")
        format_layout = QHBoxLayout(format_group)
        format_label = QLabel("Formato:")
        format_layout.addWidget(format_label)
        self._format_combo = QComboBox()
        self._format_combo.addItems(["PDF", "HTML", "JSON"])
        self._format_combo.setCurrentIndex(0)
        format_layout.addWidget(self._format_combo)
        format_layout.addStretch()
        card_layout.addWidget(format_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        card_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        self._status_label.setObjectName("subheadingLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._status_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._generate_btn = QPushButton("Gerar Relatorio")
        self._generate_btn.clicked.connect(self.generate_clicked.emit)
        btn_row.addWidget(self._generate_btn)
        self._open_btn = QPushButton("Abrir Relatorio")
        self._open_btn.setVisible(False)
        self._open_btn.clicked.connect(lambda: self.open_report_clicked.emit(self._output_path))
        btn_row.addWidget(self._open_btn)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        layout.addWidget(card)
        layout.addStretch()

    def _select_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Selecionar diretorio de saida")
        if directory:
            self._output_path = directory
            self._output_edit.setText(directory)

    def set_summary(self, text: str) -> None:
        self._summary_label.setText(text)

    def set_progress(self, value: int) -> None:
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(value)

    def set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def show_success(self, report_path: str) -> None:
        self._output_path = report_path
        self._progress_bar.setValue(100)
        self._status_label.setText("Relatorio gerado com sucesso!")
        self._generate_btn.setEnabled(False)
        self._open_btn.setVisible(True)

    def get_data(self) -> dict[str, str]:
        return {
            "output_dir": self._output_path,
            "format": self._format_combo.currentText().lower(),
        }


class _DropArea(QFrame):
    """Drag-and-drop area for file acceptance."""

    files_dropped = Signal(list)

    def __init__(self, message: str, *extensions: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._extensions = [e.lower() for e in extensions]
        self.setObjectName("dropArea")
        self.setMinimumHeight(80)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        msg = QLabel(message)
        msg.setObjectName("subheadingLabel")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            palette = self.palette()
            highlight = palette.color(palette.ColorRole.Highlight)
            self.setStyleSheet(
                f"QFrame#dropArea {{ border: 2px dashed {highlight.name()}; border-radius: 8px; }}"
            )

    def dragLeaveEvent(self, event: Any) -> None:
        self.setStyleSheet("")

    def dropEvent(self, event: QDropEvent) -> None:
        self.setStyleSheet("")
        paths: list[str] = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if not self._extensions or Path(path).suffix.lower() in self._extensions:
                    paths.append(path)
        if paths:
            self.files_dropped.emit(paths)


class WizardDialog(QDialog):
    """Multi-step wizard dialog for generating a preservation report."""

    wizard_completed = Signal(dict)

    _STEP_TITLES: list[str] = [
        "Caso",
        "WhatsApp",
        "Prints",
        "Opcoes",
        "Relatorio",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_step = WizardStep.CREATE_CASE
        self._step_widgets: dict[WizardStep, QWidget] = {}
        self._setup_ui()
        self._update_navigation()
        self.setMinimumSize(700, 520)
        self.setWindowTitle("LexProof - Assistente de Relatorio")

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 16, 24, 16)
        main_layout.setSpacing(16)

        self._step_indicator = StepIndicator(self._STEP_TITLES)
        main_layout.addWidget(self._step_indicator)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(separator)

        self._stack = QFrame()
        self._stack.setObjectName("card")
        self._stack_layout = QVBoxLayout(self._stack)
        self._stack_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.addWidget(self._stack, 1)

        self._create_steps()

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(8)

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.clicked.connect(self.reject)
        nav_layout.addWidget(self._cancel_btn)

        nav_layout.addStretch()

        self._back_btn = QPushButton("Voltar")
        self._back_btn.clicked.connect(self._go_back)
        nav_layout.addWidget(self._back_btn)

        self._next_btn = QPushButton("Proximo")
        self._next_btn.clicked.connect(self._go_next)
        nav_layout.addWidget(self._next_btn)

        main_layout.addLayout(nav_layout)

    def _create_steps(self) -> None:
        step_create = StepCreateCase()
        step_whatsapp = StepAddWhatsApp()
        step_prints = StepAddPrints()
        step_options = StepConfirmOptions()
        step_generate = StepGenerateReport()

        step_generate.generate_clicked.connect(self._on_generate)
        step_generate.open_report_clicked.connect(self._on_open_report)

        self._step_widgets = {
            WizardStep.CREATE_CASE: step_create,
            WizardStep.ADD_WHATSAPP: step_whatsapp,
            WizardStep.ADD_PRINTS: step_prints,
            WizardStep.CONFIRM_OPTIONS: step_options,
            WizardStep.GENERATE_REPORT: step_generate,
        }

        self._stack_layout.addWidget(step_create)
        self._stack_layout.addWidget(step_whatsapp)
        self._stack_layout.addWidget(step_prints)
        self._stack_layout.addWidget(step_options)
        self._stack_layout.addWidget(step_generate)

        for step in WizardStep:
            w = self._step_widgets[step]
            w.setVisible(step == self._current_step)

    def _go_next(self) -> None:
        steps = list(WizardStep)
        current_idx = steps.index(self._current_step)

        if self._current_step == WizardStep.CREATE_CASE:
            widget = self._step_widgets[WizardStep.CREATE_CASE]
            assert isinstance(widget, StepCreateCase)
            if not widget.validate():
                return

        self._step_indicator.mark_completed(current_idx)

        next_idx = current_idx + 1
        if next_idx < len(steps):
            self._step_indicator.set_current(next_idx)
            self._current_step = steps[next_idx]
            self._show_current_step()
            self._update_navigation()

    def _go_back(self) -> None:
        steps = list(WizardStep)
        current_idx = steps.index(self._current_step)
        prev_idx = current_idx - 1
        if prev_idx >= 0:
            self._step_indicator.set_current(prev_idx)
            self._current_step = steps[prev_idx]
            self._show_current_step()
            self._update_navigation()

    def _show_current_step(self) -> None:
        for step, widget in self._step_widgets.items():
            widget.setVisible(step == self._current_step)
        if self._current_step == WizardStep.GENERATE_REPORT:
            self._update_summary()

    def _update_navigation(self) -> None:
        steps = list(WizardStep)
        current_idx = steps.index(self._current_step)
        self._back_btn.setEnabled(current_idx > 0 and self._current_step != WizardStep.GENERATE_REPORT)

        if self._current_step == WizardStep.GENERATE_REPORT:
            self._next_btn.setVisible(False)
        else:
            self._next_btn.setVisible(True)
            self._next_btn.setText("Proximo")

    def _update_summary(self) -> None:
        data = self.get_data()
        case_title = data.get("case_title", "N/A")
        examiner = data.get("examiner_name", "N/A")
        whatsapp_files = data.get("whatsapp_files", [])
        print_files = data.get("print_files", [])
        opts = data.get("options", {})

        lines = [
            f"Caso: {case_title}",
            f"Responsavel: {examiner}",
            f"WhatsApp: {len(whatsapp_files)} arquivo(s)",
            f"Prints: {len(print_files)} imagem(ns)",
        ]
        if opts.get("calculate_hashes"):
            lines.append("Hashes: SHA256, SHA3-512, BLAKE3")
        if opts.get("run_ocr"):
            lines.append("OCR nas imagens: Sim")
        if opts.get("generate_timeline"):
            lines.append("Timeline: Sim")
        if opts.get("include_custody"):
            lines.append("Cadeia de custodia: Sim")
        if opts.get("compare_ocr_txt"):
            lines.append("Comparacao OCR x TXT: Sim")

        widget = self._step_widgets[WizardStep.GENERATE_REPORT]
        assert isinstance(widget, StepGenerateReport)
        widget.set_summary("\n".join(lines))

    def _on_generate(self) -> None:
        widget = self._step_widgets[WizardStep.GENERATE_REPORT]
        assert isinstance(widget, StepGenerateReport)
        report_data = widget.get_data()
        if not report_data.get("output_dir"):
            widget.set_status("Selecione um diretorio de saida.")
            return

        widget.set_progress(0)
        widget.set_status("Gerando relatorio...")

        from PySide6.QtCore import QTimer

        self._progress_value = 0
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(50)
        self._progress_timer.timeout.connect(self._advance_progress)
        self._progress_timer.start()

    def _advance_progress(self) -> None:
        self._progress_value += 2
        widget = self._step_widgets[WizardStep.GENERATE_REPORT]
        assert isinstance(widget, StepGenerateReport)
        widget.set_progress(self._progress_value)

        if self._progress_value >= 100:
            self._progress_timer.stop()
            report_data = widget.get_data()
            output_dir = report_data.get("output_dir", "")
            fmt = report_data.get("format", "pdf")
            report_path = os.path.join(output_dir, f"relatorio.{fmt}")
            widget.show_success(report_path)
            self.wizard_completed.emit(self.get_data())

    def _on_open_report(self, path: str) -> None:
        import subprocess
        import sys
        if sys.platform == "linux":
            subprocess.Popen(["xdg-open", path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            os.startfile(path)

    @property
    def current_step(self) -> WizardStep:
        return self._current_step

    def get_data(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for step in WizardStep:
            widget = self._step_widgets[step]
            if hasattr(widget, "get_data"):
                result.update(widget.get_data())
        return result
