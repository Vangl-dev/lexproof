"""PropertiesPanel — card-based file metadata viewer."""

from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class _SectionHeader(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(
            "font-weight: 600; font-size: 12px; padding-top: 12px; padding-bottom: 6px; "
            "letter-spacing: 0.5px;"
        )


class _KeyValueRow(QWidget):
    value_changed = Signal(str, str)

    def __init__(
        self,
        key: str,
        value: str,
        editable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._edit_key = key

        self._key_label = QLabel(key)
        self._key_label.setStyleSheet("font-weight: 500; font-size: 12px;")
        self._key_label.setFixedWidth(130)

        self._value_edit = QLineEdit(value)
        self._value_edit.setReadOnly(not editable)
        self._value_edit.setStyleSheet(
            "QLineEdit { border: 1px solid palette(mid); border-radius: 4px; "
            "padding: 3px 8px; background: transparent; font-size: 12px; }"
        )
        if editable:
            self._value_edit.editingFinished.connect(self._on_edited)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setColumnStretch(1, 1)
        layout.addWidget(self._key_label, 0, 0)
        layout.addWidget(self._value_edit, 0, 1)

    def set_value(self, value: str) -> None:
        self._value_edit.setText(value)

    def value(self) -> str:
        return self._value_edit.text()

    def _on_edited(self) -> None:
        self.value_changed.emit(self._edit_key, self.value())


class PropertiesPanelWidget(QWidget):
    """Panel displaying properties of the selected evidence file.

    Sections: General Info, Hashes, EXIF Metadata, OCR Results, Timeline Info.
    Scrollable with card-based layout for each section.
    """

    property_changed = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("propertiesPanelWidget")

        self._rows: dict[str, _KeyValueRow] = {}

        container = QWidget()
        self._content_layout = QVBoxLayout(container)
        self._content_layout.setContentsMargins(12, 12, 12, 12)
        self._content_layout.setSpacing(0)

        self._build_general_section()
        self._build_hashes_section()
        self._build_exif_section()
        self._build_ocr_section()
        self._build_timeline_section()

        self._content_layout.addStretch()

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setWidget(container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll_area)

    def _build_general_section(self) -> None:
        self._content_layout.addWidget(_SectionHeader("Informacoes Gerais"))
        self._add_row("name", "Nome")
        self._add_row("path", "Caminho")
        self._add_row("size", "Tamanho")
        self._add_row("type", "Tipo")
        self._add_row("mime", "MIME")

    def _build_hashes_section(self) -> None:
        self._content_layout.addWidget(_SectionHeader("Hashes"))
        self._add_row("sha256", "SHA-256")
        self._add_row("sha3_512", "SHA3-512")
        self._add_row("blake3", "BLAKE3")

    def _build_exif_section(self) -> None:
        self._content_layout.addWidget(_SectionHeader("Metadados EXIF"))
        self._add_row("exif_camera", "Camera")
        self._add_row("exif_date", "Data Original")
        self._add_row("exif_gps", "GPS")
        self._add_row("exif_software", "Software")
        self._add_row("exif_orientation", "Orientacao")
        self._add_row("exif_custom", "Personalizado", editable=True)

    def _build_ocr_section(self) -> None:
        self._content_layout.addWidget(_SectionHeader("Resultados OCR"))
        self._add_row("ocr_engine", "Motor OCR")
        self._add_row("ocr_confidence", "Confianca")
        self._add_row("ocr_language", "Idioma")
        self._add_row("ocr_text", "Texto Extraido")

    def _build_timeline_section(self) -> None:
        self._content_layout.addWidget(_SectionHeader("Informacoes de Timeline"))
        self._add_row("created_at", "Criado em")
        self._add_row("modified_at", "Modificado em")
        self._add_row("imported_at", "Importado em")

    def _add_row(self, key: str, label: str, editable: bool = False) -> None:
        row = _KeyValueRow(label, "", editable=editable)
        row.setProperty("propKey", key)
        if editable:
            row.value_changed.connect(self.property_changed)
        self._rows[key] = row
        self._content_layout.addWidget(row)

    def show_file(self, file_path: str) -> None:
        p = Path(file_path)
        if not p.is_file():
            self.clear()
            return

        stat = p.stat()
        mime_type, _ = mimetypes.guess_type(str(p))

        self._rows["name"].set_value(p.name)
        self._rows["path"].set_value(str(p))
        self._rows["size"].set_value(f"{stat.st_size} bytes")
        self._rows["type"].set_value(p.suffix.upper().lstrip("."))
        self._rows["mime"].set_value(mime_type or "desconhecido")

        self._rows["created_at"].set_value(self._format_timestamp(stat.st_ctime))
        self._rows["modified_at"].set_value(self._format_timestamp(stat.st_mtime))
        self._rows["imported_at"].set_value("N/A")

    def clear(self) -> None:
        for row in self._rows.values():
            row.set_value("")

    def set_hashes(self, hashes: dict[str, str]) -> None:
        for key, value in hashes.items():
            if key in self._rows:
                self._rows[key].set_value(value)

    def set_exif(self, metadata: dict[str, str]) -> None:
        mapping = {
            "camera": "exif_camera",
            "date": "exif_date",
            "gps": "exif_gps",
            "software": "exif_software",
            "orientation": "exif_orientation",
        }
        for src_key, target_key in mapping.items():
            if src_key in metadata and target_key in self._rows:
                self._rows[target_key].set_value(metadata[src_key])
        if "custom" in metadata and "exif_custom" in self._rows:
            self._rows["exif_custom"].set_value(metadata["custom"])

    def set_ocr(self, ocr_data: dict[str, str]) -> None:
        mapping = {
            "engine": "ocr_engine",
            "confidence": "ocr_confidence",
            "language": "ocr_language",
            "text": "ocr_text",
        }
        for src_key, target_key in mapping.items():
            if src_key in ocr_data and target_key in self._rows:
                self._rows[target_key].set_value(ocr_data[src_key])

    def set_timeline(self, timeline_data: dict[str, str]) -> None:
        for key, value in timeline_data.items():
            if key in self._rows:
                self._rows[key].set_value(value)

    @staticmethod
    def _format_timestamp(ts: float) -> str:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


PropertiesPanel = PropertiesPanelWidget
