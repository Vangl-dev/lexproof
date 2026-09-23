"""Componente de card moderno para o LexProof.

Cards minimalistas com bordas arredondadas, espaçamento generoso,
e suporte a estados (normal, hover, selecionado).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    """Card moderno estilo flat design.

    Características:
    - border-radius: 12px
    - padding interno generoso
    - estados: normal, hover, selecionado
    - animações suaves
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "",
        subtitle: str = "",
        icon: str = "",
    ) -> None:
        """Inicializa o card.

        Args:
            parent: Widget pai.
            title: Título do card.
            subtitle: Subtítulo do card.
            icon: Nome do ícone SVG.
        """
        super().__init__(parent)
        self.setObjectName("card")
        self._setup_ui(title, subtitle, icon)
        self._setup_style()

    def _setup_ui(self, title: str, subtitle: str, icon: str) -> None:
        """Configura a interface do card."""
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(20, 20, 20, 20)
        self._main_layout.setSpacing(12)

        # Header (ícone + textos)
        if icon or title or subtitle:
            header = QWidget()
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(12)

            # Ícone
            if icon:
                from lexproof.ui.icons import get_icon
                from PySide6.QtGui import QIcon, QPixmap, QImage, QPalette
                from PySide6.QtCore import QByteArray
                from PySide6.QtWidgets import QApplication

                icon_label = QLabel()
                icon_label.setFixedSize(40, 40)
                icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                svg_data = get_icon(icon)

                app = QApplication.instance()
                if app:
                    palette = app.palette()
                    color = palette.color(QPalette.ColorRole.ButtonText)
                    hex_color = f"#{color.red():02x}{color.green():02x}{color.blue():02x}"
                    svg_data = svg_data.replace("currentColor", hex_color)

                data = QByteArray(svg_data.encode("utf-8"))
                img = QImage.fromData(data)
                if not img.isNull():
                    pixmap = QPixmap.fromImage(img).scaled(
                        24, 24,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    icon_label.setPixmap(pixmap)

                header_layout.addWidget(icon_label)

            # Textos
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(2)

            if title:
                self._title_label = QLabel(title)
                self._title_label.setObjectName("cardTitle")
                self._title_label.setStyleSheet(
                    "font-size: 15px; font-weight: 600; color: palette(text);"
                )
                text_layout.addWidget(self._title_label)

            if subtitle:
                self._subtitle_label = QLabel(subtitle)
                self._subtitle_label.setObjectName("cardSubtitle")
                self._subtitle_label.setStyleSheet(
                    "font-size: 12px; color: palette(placeholderText);"
                )
                self._subtitle_label.setWordWrap(True)
                text_layout.addWidget(self._subtitle_label)

            header_layout.addLayout(text_layout, stretch=1)

            self._main_layout.addWidget(header)

        # Conteúdo (área para widgets filhos)
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(8)
        self._main_layout.addWidget(self._content_widget, stretch=1)

    def _setup_style(self) -> None:
        """Configura o estilo do card."""
        self.setStyleSheet("""
            QFrame#card {
                border: 1px solid palette(mid);
                border-radius: 12px;
                background-color: palette(base);
            }
            QFrame#card:hover {
                border: 1px solid palette(dark);
            }
        """)

    def add_widget(self, widget: QWidget) -> None:
        """Adiciona um widget ao conteúdo do card.

        Args:
            widget: Widget para adicionar.
        """
        self._content_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        """Adiciona um layout ao conteúdo do card.

        Args:
            layout: Layout para adicionar.
        """
        self._content_layout.addLayout(layout)

    def set_selected(self, selected: bool) -> None:
        """Define o estado de seleção do card.

        Args:
            selected: True se selecionado.
        """
        if selected:
            self.setObjectName("cardSelected")
            self.setStyleSheet("""
                QFrame#cardSelected {
                    border: 2px solid palette(highlight);
                    border-radius: 12px;
                    background-color: palette(base);
                }
            """)
        else:
            self.setObjectName("card")
            self._setup_style()


class EvidenceCard(Card):
    """Card para exibição de evidências.

    Mostra miniatura, nome, tipo, tamanho, hash e status.
    """

    def __init__(
        self,
        file_name: str = "",
        file_type: str = "",
        file_size: int = 0,
        file_hash: str = "",
        thumbnail_path: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Inicializa o card de evidência.

        Args:
            file_name: Nome do arquivo.
            file_type: Tipo do arquivo.
            file_size: Tamanho em bytes.
            file_hash: Hash SHA-256 (resumido).
            thumbnail_path: Caminho da miniatura.
            parent: Widget pai.
        """
        # Determinar ícone baseado no tipo
        icon_map = {
            "image": "image",
            "chat_export": "file",
            "text": "file",
            "archive": "archive",
            "video": "video",
            "audio": "audio",
            "document": "file",
        }
        icon = icon_map.get(file_type, "file")

        # Formatar tamanho
        size_str = self._format_size(file_size)

        # Resumir hash
        hash_short = file_hash[:16] + "..." if len(file_hash) > 16 else file_hash

        super().__init__(
            parent=parent,
            title=file_name,
            subtitle=f"{file_type.upper()} • {size_str}",
            icon=icon,
        )

        self._file_name = file_name
        self._setup_evidence_ui(file_hash, hash_short)

    def _setup_evidence_ui(self, file_hash: str, hash_short: str) -> None:
        """Configura a interface específica da evidência."""
        # Hash
        hash_widget = QWidget()
        hash_layout = QHBoxLayout(hash_widget)
        hash_layout.setContentsMargins(0, 0, 0, 0)
        hash_layout.setSpacing(8)

        hash_label = QLabel("SHA-256:")
        hash_label.setStyleSheet("font-size: 11px; color: palette(placeholderText);")
        hash_layout.addWidget(hash_label)

        hash_value = QLabel(hash_short)
        hash_value.setStyleSheet("font-size: 11px; color: palette(text); font-family: monospace;")
        hash_layout.addWidget(hash_value)
        hash_layout.addStretch()

        self.add_widget(hash_widget)

        # Status
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)

        status_dot = QLabel("●")
        status_dot.setStyleSheet("color: palette(highlight); font-size: 8px;")
        status_layout.addWidget(status_dot)

        status_text = QLabel("Preservado")
        status_text.setStyleSheet("font-size: 11px; color: palette(placeholderText);")
        status_layout.addWidget(status_text)
        status_layout.addStretch()

        self.add_widget(status_widget)

    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes para legível."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


class PipelineStepCard(QFrame):
    """Card para etapa do pipeline de processamento."""

    def __init__(
        self,
        step_name: str = "",
        status: str = "pending",
        parent: QWidget | None = None,
    ) -> None:
        """Inicializa o card de etapa.

        Args:
            step_name: Nome da etapa.
            status: Status (pending, running, completed, failed).
            parent: Widget pai.
        """
        super().__init__(parent)
        self.setObjectName("pipelineStep")
        self._step_name = step_name
        self._status = status
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface."""
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Status indicator
        self._status_indicator = QLabel()
        self._status_indicator.setFixedSize(24, 24)
        self._status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_status_indicator()
        layout.addWidget(self._status_indicator)

        # Step name
        self._name_label = QLabel(self._step_name)
        self._name_label.setStyleSheet("font-size: 13px; font-weight: 500;")
        layout.addWidget(self._name_label)

        layout.addStretch()

        # Status text
        self._status_text = QLabel(self._get_status_text())
        self._status_text.setStyleSheet("font-size: 12px; color: palette(placeholderText);")
        layout.addWidget(self._status_text)

        self._update_style()

    def _get_status_text(self) -> str:
        """Retorna texto do status."""
        status_map = {
            "pending": "Aguardando",
            "running": "Executando...",
            "completed": "Concluido",
            "failed": "Falhou",
        }
        return status_map.get(self._status, "")

    def _update_status_indicator(self) -> None:
        """Atualiza o indicador visual de status."""
        status_config = {
            "pending": ("○", "palette(placeholderText)"),
            "running": ("◉", "palette(highlight)"),
            "completed": ("●", "palette(highlight)"),
            "failed": ("●", "palette(brightText)"),
        }
        symbol, color = status_config.get(self._status, ("○", "palette(placeholderText)"))
        self._status_indicator.setText(symbol)
        self._status_indicator.setStyleSheet(f"color: {color}; font-size: 16px;")

    def _update_style(self) -> None:
        """Atualiza o estilo baseado no status."""
        if self._status == "completed":
            self.setStyleSheet("""
                QFrame#pipelineStep {
                    background-color: palette(base);
                    border-radius: 8px;
                    border: 1px solid palette(highlight);
                }
            """)
        elif self._status == "failed":
            self.setStyleSheet("""
                QFrame#pipelineStep {
                    background-color: palette(base);
                    border-radius: 8px;
                    border: 1px solid palette(brightText);
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#pipelineStep {
                    background-color: palette(base);
                    border-radius: 8px;
                    border: 1px solid palette(mid);
                }
            """)

    def set_status(self, status: str) -> None:
        """Define o status da etapa.

        Args:
            status: Novo status.
        """
        self._status = status
        self._status_text.setText(self._get_status_text())
        self._update_status_indicator()
        self._update_style()
