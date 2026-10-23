"""DropZoneWidget — overlay for drag and drop with fade animation."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from lexproof.ui.icons import get_icon


class DropZoneWidget(QWidget):
    """Overlay widget for drag and drop file acceptance with fade animation."""

    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZoneOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._animation_opacity = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._animation_opacity.setDuration(200)
        self._animation_opacity.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self.hide()

        # Icon
        from PySide6.QtCore import QByteArray
        from PySide6.QtGui import QImage, QPixmap

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        svg = get_icon("upload")
        data = QByteArray(svg.encode("utf-8"))
        img = QImage.fromData(data)
        if not img.isNull():
            pixmap = QPixmap.fromImage(img).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        icon_label.setStyleSheet("background: transparent; border: none;")

        # Message
        msg_label = QLabel("Solte os arquivos aqui")
        msg_label.setStyleSheet("font-size: 16px; font-weight: 600; background: transparent; border: none;")
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub_label = QLabel("Aceita multiplos arquivos para processamento")
        sub_label.setStyleSheet("font-size: 12px; background: transparent; border: none;")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(4)
        layout.addWidget(sub_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.show()
            self._fade_in()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._fade_out()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        paths: list[str] = []
        for url in urls:
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        self._fade_out()
        if paths:
            self.files_dropped.emit(paths)

    def _fade_in(self) -> None:
        self._animation_opacity.stop()
        self._animation_opacity.setStartValue(self._opacity_effect.opacity())
        self._animation_opacity.setEndValue(1.0)
        self._animation_opacity.start()

    def _fade_out(self) -> None:
        self._animation_opacity.stop()
        self._animation_opacity.setStartValue(self._opacity_effect.opacity())
        self._animation_opacity.setEndValue(0.0)
        self._animation_opacity.start()
        self._animation_opacity.finished.connect(self._hide_on_fade_out)

    def _hide_on_fade_out(self) -> None:
        if self._opacity_effect.opacity() < 0.01:
            self.hide()
        try:
            self._animation_opacity.finished.disconnect(self._hide_on_fade_out)
        except RuntimeError:
            pass
