from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class EvidenceListWidget(QWidget):
    """Widget displaying imported evidence files with add/remove actions."""

    file_selected = Signal(str)
    file_removed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._files: list[str] = []

        title = QLabel("Evidências")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")

        self._list_widget = QListWidget()
        self._list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self._list_widget.currentRowChanged.connect(self._on_row_changed)

        add_btn = QPushButton("+ Adicionar")
        add_btn.setFixedHeight(28)
        add_btn.setObjectName("secondaryButton")
        add_btn.clicked.connect(self._on_add_clicked)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.addWidget(title)
        toolbar.addStretch()
        toolbar.addWidget(add_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(toolbar)
        layout.addWidget(self._list_widget)

    def add_file(self, path: str) -> None:
        """Add a file to the evidence list."""
        if path not in self._files:
            self._files.append(path)
            item = QListWidgetItem(Path(path).name)
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self._list_widget.addItem(item)

    def add_files(self, paths: list[str]) -> None:
        """Add multiple files to the evidence list."""
        for path in paths:
            self.add_file(path)

    def remove_selected(self) -> None:
        """Remove the currently selected file."""
        row = self._list_widget.currentRow()
        if row >= 0:
            item = self._list_widget.takeItem(row)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in self._files:
                self._files.remove(path)
            self.file_removed.emit(path)

    def clear_files(self) -> None:
        """Remove all files from the list."""
        self._files.clear()
        self._list_widget.clear()

    def get_files(self) -> list[str]:
        """Return all file paths in the list."""
        return list(self._files)

    def file_count(self) -> int:
        """Return the number of files."""
        return len(self._files)

    def _on_row_changed(self, row: int) -> None:
        if row >= 0:
            item = self._list_widget.item(row)
            path = item.data(Qt.ItemDataRole.UserRole)
            self.file_selected.emit(path)

    def _on_add_clicked(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Adicionar Evidências",
            "",
            "Todos os Arquivos (*)",
        )
        if paths:
            self.add_files(paths)

    def _show_context_menu(self, pos: Any) -> None:
        item = self._list_widget.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        remove_action = menu.addAction("Remover")
        remove_action.triggered.connect(self.remove_selected)
        menu.exec(self._list_widget.mapToGlobal(pos))
