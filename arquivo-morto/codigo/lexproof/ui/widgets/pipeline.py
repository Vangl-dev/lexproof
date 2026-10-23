"""Widget de pipeline visual para o LexProof.

Mostra o progresso do processamento de evidências com:
- Informações do ZIP detectado
- Lista de etapas com status visual (○ 🟡 🟢 🔴)
- Porcentagem de progresso
- Tempo por etapa
- Descrições humanas
- Tela de resumo ao finalizar
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


STEP_DESCRIPTIONS = {
    "catalogacao": "Organizando seus arquivos",
    "metadados": "Lendo informacoes dos arquivos",
    "hashes": "Calculando hashes de integridade",
    "ocr": "Lendo texto das imagens",
    "parser": "Lendo a conversa do WhatsApp",
    "correlacao": "Combinando prints com a conversa",
    "timeline": "Reconstruindo a ordem das mensagens",
    "verificacao": "Conferindo integridade",
    "relatorio": "Montando relatorio",
}

STEP_ICONS = {
    "pending": "\u25cb",
    "running": "\u25cf",
    "completed": "\u2713",
    "failed": "\u2717",
}


class ZipInfoWidget(QWidget):
    """Widget que mostra informacoes do ZIP detectado."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("zipInfo")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        self.setStyleSheet("""
            QFrame#zipInfo {
                background-color: palette(base);
                border: 1px solid palette(highlight);
                border-radius: 12px;
            }
        """)

        header = QLabel("\u2705 ZIP detectado")
        header.setStyleSheet("font-size: 16px; font-weight: 600; color: palette(text);")
        layout.addWidget(header)

        self._details = QLabel()
        self._details.setStyleSheet("font-size: 13px; color: palette(text); line-height: 1.6;")
        self._details.setWordWrap(True)
        layout.addWidget(self._details)

    def set_info(self, info: dict) -> None:
        lines = []
        if info.get("name"):
            lines.append(f"<b>Nome:</b> {info['name']}")
        if info.get("size"):
            lines.append(f"<b>Tamanho:</b> {info['size']}")
        if info.get("total_files"):
            lines.append(f"<b>Arquivos:</b> {info['total_files']}")
        if info.get("images"):
            lines.append(f"<b>Imagens:</b> {info['images']}")
        if info.get("has_whatsapp"):
            lines.append("<b>Exportacao WhatsApp:</b> Sim")
        if info.get("has_txt"):
            lines.append("<b>TXT encontrado:</b> Sim")
        self._details.setText("<br>".join(lines))
        self.show()


class SummaryWidget(QWidget):
    """Tela de resumo ao finalizar o processamento."""

    open_report_clicked = Signal()
    open_folder_clicked = Signal()
    new_preservation_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryWidget")
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(24)

        title = QLabel("\U0001f389 Preservacao concluida")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: palette(text);")
        layout.addWidget(title)

        self._stats_label = QLabel()
        self._stats_label.setStyleSheet("font-size: 14px; color: palette(text); line-height: 1.8;")
        self._stats_label.setWordWrap(True)
        layout.addWidget(self._stats_label)

        layout.addSpacing(16)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._report_btn = QLabel("Abrir relatorio")
        self._report_btn.setStyleSheet("""
            font-size: 14px; font-weight: 600; color: palette(highlight);
            padding: 12px 24px; border: 2px solid palette(highlight);
            border-radius: 8px; cursor: pointer;
        """)
        self._report_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._report_btn.mousePressEvent = lambda _: self.open_report_clicked.emit()
        btn_layout.addWidget(self._report_btn)

        self._folder_btn = QLabel("Abrir pasta")
        self._folder_btn.setStyleSheet("""
            font-size: 14px; font-weight: 600; color: palette(text);
            padding: 12px 24px; border: 2px solid palette(mid);
            border-radius: 8px; cursor: pointer;
        """)
        self._folder_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.mousePressEvent = lambda _: self.open_folder_clicked.emit()
        btn_layout.addWidget(self._folder_btn)

        self._new_btn = QLabel("Nova preservacao")
        self._new_btn.setStyleSheet("""
            font-size: 14px; font-weight: 600; color: palette(text);
            padding: 12px 24px; border: 2px solid palette(mid);
            border-radius: 8px; cursor: pointer;
        """)
        self._new_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_btn.mousePressEvent = lambda _: self.new_preservation_clicked.emit()
        btn_layout.addWidget(self._new_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def set_summary(self, data: dict) -> None:
        lines = []
        lines.append("\u2714 <b>Preservacao concluida</b>")
        lines.append("")
        lines.append("<b>Arquivos:</b>")
        lines.append(f"  \u2022 Total: {data.get('files', 0)}")
        if data.get("images"):
            lines.append(f"  \u2022 Imagens: {data['images']}")
        if data.get("conversations"):
            lines.append(f"  \u2022 Exportacoes: {data['conversations']}")
        if data.get("participants"):
            lines.append(f"  \u2022 Participantes: {data['participants']}")
        if data.get("messages"):
            lines.append(f"  \u2022 Mensagens: {data['messages']}")
        lines.append("")
        if data.get("ocr_count"):
            lines.append(f"\u2714 <b>OCR:</b> {data['ocr_count']} processada(s)")
        if data.get("correlations_count"):
            lines.append(f"\u2714 <b>Correlacoes:</b> {data['correlations_count']} encontrada(s)")
        if data.get("report_path"):
            lines.append("\u2714 <b>Relatorio:</b> Gerado")
        if data.get("duration"):
            lines.append(f"\u2714 <b>Tempo:</b> {data['duration']}")
        self._stats_label.setText("<br>".join(lines))
        self.show()


class PipelineWidget(QWidget):
    """Widget de pipeline visual completo."""

    open_report_clicked = Signal()
    open_folder_clicked = Signal()
    new_preservation_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pipelineWidget")
        self._step_widgets: list[_StepRow] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(40, 32, 40, 32)
        self._container_layout.setSpacing(16)

        self._header = self._create_header()
        self._container_layout.addWidget(self._header)

        self._zip_info = ZipInfoWidget()
        self._zip_info.hide()
        self._container_layout.addWidget(self._zip_info)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: palette(mid);
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background-color: palette(highlight);
            }
        """)
        self._container_layout.addWidget(self._progress_bar)

        self._percent_label = QLabel("0%")
        self._percent_label.setStyleSheet("font-size: 13px; color: palette(placeholderText);")
        self._container_layout.addWidget(self._percent_label)

        self._steps_container = QWidget()
        self._steps_layout = QVBoxLayout(self._steps_container)
        self._steps_layout.setContentsMargins(0, 0, 0, 0)
        self._steps_layout.setSpacing(4)
        self._container_layout.addWidget(self._steps_container)

        self._container_layout.addStretch()

        self._summary = SummaryWidget()
        self._summary.open_report_clicked.connect(self.open_report_clicked.emit)
        self._summary.open_folder_clicked.connect(self.open_folder_clicked.emit)
        self._summary.new_preservation_clicked.connect(self.new_preservation_clicked.emit)
        self._summary.hide()
        self._container_layout.addWidget(self._summary)

        scroll.setWidget(self._container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_header(self) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._title = QLabel("Preservacao de Evidencias")
        self._title.setStyleSheet("font-size: 20px; font-weight: 600; color: palette(text);")
        layout.addWidget(self._title)

        self._subtitle = QLabel("Acompanhe o processamento")
        self._subtitle.setStyleSheet("font-size: 13px; color: palette(placeholderText);")
        layout.addWidget(self._subtitle)

        return header

    def show_zip_info(self, info: dict) -> None:
        self._zip_info.set_info(info)

    def reset(self) -> None:
        for row in self._step_widgets:
            self._steps_layout.removeWidget(row)
            row.deleteLater()
        self._step_widgets.clear()
        self._progress_bar.setValue(0)
        self._percent_label.setText("0%")
        self._zip_info.hide()
        self._summary.hide()
        self._title.setText("Preservacao de Evidencias")
        self._subtitle.setText("Acompanhe o processamento")
        self.show()

    def add_step(self, name: str, description: str = "") -> None:
        desc = STEP_DESCRIPTIONS.get(name.lower(), description or name)
        row = _StepRow(name, desc)
        self._step_widgets.append(row)
        self._steps_layout.addWidget(row)

    def update_step(self, index: int, status: str, duration: float = 0.0) -> None:
        if 0 <= index < len(self._step_widgets):
            self._step_widgets[index].set_status(status, duration)

    def set_progress(self, percent: int) -> None:
        self._progress_bar.setValue(percent)
        self._percent_label.setText(f"{percent}%")

    def show_summary(self, data: dict) -> None:
        self._summary.set_summary(data)
        self._title.setText("Preservacao concluida")
        self._subtitle.setText("Todos os arquivos foram preservados com sucesso")

    def show_error(self, message: str) -> None:
        self._title.setText("Preservacao concluida com avisos")
        self._subtitle.setText(message)


class _StepRow(QWidget):
    """Linha de uma etapa do pipeline."""

    def __init__(self, name: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self._description = description
        self._status = "pending"
        self._duration = 0.0
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)
        self.setStyleSheet("""
            QWidget {
                border-radius: 6px;
                padding: 4px 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        self._icon_label = QLabel(STEP_ICONS["pending"])
        self._icon_label.setFixedSize(24, 24)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self._icon_label)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        self._name_label = QLabel(self._name)
        self._name_label.setStyleSheet("font-size: 13px; font-weight: 600; color: palette(text);")
        self._name_label.setMinimumWidth(120)
        text_layout.addWidget(self._name_label)

        self._desc_label = QLabel(self._description)
        self._desc_label.setStyleSheet("font-size: 11px; color: palette(placeholderText);")
        self._desc_label.setMinimumWidth(120)
        text_layout.addWidget(self._desc_label)

        layout.addLayout(text_layout, stretch=1)

        self._time_label = QLabel("")
        self._time_label.setStyleSheet("font-size: 12px; color: palette(placeholderText); font-family: monospace;")
        self._time_label.setFixedWidth(60)
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._time_label.setMinimumWidth(60)
        layout.addWidget(self._time_label)

        self._status_label = QLabel("Aguardando")
        self._status_label.setStyleSheet("font-size: 12px; color: palette(placeholderText);")
        self._status_label.setFixedWidth(100)
        self._status_label.setMinimumWidth(100)
        layout.addWidget(self._status_label)

    def set_status(self, status: str, duration: float = 0.0) -> None:
        self._status = status
        self._duration = duration

        icon = STEP_ICONS.get(status, "\u25cb")
        self._icon_label.setText(icon)

        status_texts = {
            "pending": "Aguardando",
            "running": "Executando...",
            "completed": "Concluido",
            "failed": "Falhou",
        }
        self._status_label.setText(status_texts.get(status, ""))

        if duration is not None and duration > 0:
            if duration < 1:
                self._time_label.setText(f"{duration:.1f}s")
            else:
                self._time_label.setText(f"{duration:.1f}s")

        if status == "completed":
            self._icon_label.setStyleSheet("font-size: 16px; color: palette(highlight); font-weight: bold;")
            self._status_label.setStyleSheet("font-size: 12px; color: palette(highlight); font-weight: 600;")
            self.setStyleSheet("""
                QWidget {
                    border-radius: 6px;
                    padding: 4px 12px;
                    background-color: palette(base);
                    border: 1px solid palette(highlight);
                }
            """)
        elif status == "failed":
            self._icon_label.setStyleSheet("font-size: 16px; color: palette(brightText); font-weight: bold;")
            self._status_label.setStyleSheet("font-size: 12px; color: palette(brightText); font-weight: 600;")
            self.setStyleSheet("""
                QWidget {
                    border-radius: 6px;
                    padding: 4px 12px;
                    background-color: palette(base);
                    border: 1px solid palette(brightText);
                }
            """)
        elif status == "running":
            self._icon_label.setStyleSheet("font-size: 16px; color: palette(highlight); font-weight: bold;")
            self._status_label.setStyleSheet("font-size: 12px; color: palette(highlight); font-weight: 500;")
            self.setStyleSheet("""
                QWidget {
                    border-radius: 6px;
                    padding: 4px 12px;
                    background-color: palette(base);
                    border: 1px solid palette(highlight);
                }
            """)
        else:
            self._icon_label.setStyleSheet("font-size: 16px; color: palette(placeholderText);")
            self._status_label.setStyleSheet("font-size: 12px; color: palette(placeholderText);")
            self.setStyleSheet("""
                QWidget {
                    border-radius: 6px;
                    padding: 4px 12px;
                    background-color: palette(base);
                    border: 1px solid palette(mid);
                }
            """)
