from __future__ import annotations

from enum import Enum
from typing import Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QFont, QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class ToastLevel(Enum):
    """Toast notification severity levels."""

    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


OBJECT_NAME_MAP: dict[ToastLevel, str] = {
    ToastLevel.INFO: "toastInfo",
    ToastLevel.SUCCESS: "toastSuccess",
    ToastLevel.WARNING: "toastWarning",
    ToastLevel.ERROR: "toastError",
}


class ToastNotification(QWidget):
    """A floating notification widget that appears at the bottom-right of the main window.

    Supports different severity levels (INFO, SUCCESS, WARNING, ERROR),
    auto-dismiss after a configurable timeout, smooth fade-in/fade-out animation,
    and a close button.
    """

    closed = Signal()

    # --- Themable class constants ---
    BORDER_RADIUS: int = 8
    TOAST_WIDTH: int = 340
    TOAST_HEIGHT: int = 60
    PADDING: int = 12
    ICON_FONT_SIZE: int = 20
    CLOSE_BUTTON_SIZE: int = 24
    ANIMATION_DURATION: int = 300
    MAX_VISIBLE: int = 3
    DEFAULT_TIMEOUT: int = 3000

    ICON_MAP: dict[ToastLevel, str] = {
        ToastLevel.INFO: "\u2139",
        ToastLevel.SUCCESS: "\u2714",
        ToastLevel.WARNING: "\u26a0",
        ToastLevel.ERROR: "\u2716",
    }

    def __init__(
        self,
        message: str,
        level: ToastLevel = ToastLevel.INFO,
        timeout: int = DEFAULT_TIMEOUT,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialise the toast notification.

        Args:
            message: Text to display in the toast.
            level: Severity level determining colour and icon.
            timeout: Milliseconds before auto-dismiss. 0 disables auto-dismiss.
            parent: Parent widget used for positioning.
        """
        super().__init__(parent)
        self._message = message
        self._level = level
        self._timeout = timeout

        self.setObjectName(OBJECT_NAME_MAP.get(level, "toastInfo"))
        self._setup_ui()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_in = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in.setDuration(self.ANIMATION_DURATION)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out.setDuration(self.ANIMATION_DURATION)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self._on_fade_out_finished)

        self._timer: Optional[QTimer] = None
        if self._timeout > 0:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(self._timeout)
            self._timer.timeout.connect(self.dismiss)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the internal widget layout."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(self.TOAST_WIDTH)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            self.PADDING, self.PADDING, self.PADDING, self.PADDING
        )
        layout.setSpacing(8)

        icon_char = self.ICON_MAP.get(self._level, "")
        self._icon_label = QLabel(icon_char)
        self._icon_label.setFixedWidth(self.ICON_FONT_SIZE + 4)
        font = QFont()
        font.setPointSize(self.ICON_FONT_SIZE)
        self._icon_label.setFont(font)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_label)

        self._text_label = QLabel(self._message)
        self._text_label.setWordWrap(True)
        layout.addWidget(self._text_label, 1)

        self._close_btn = QPushButton("\u2715")
        self._close_btn.setFixedSize(self.CLOSE_BUTTON_SIZE, self.CLOSE_BUTTON_SIZE)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; font-size: 14px; border-radius: 4px; }"
        )
        self._close_btn.clicked.connect(self.dismiss)
        layout.addWidget(self._close_btn, 0, Qt.AlignmentFlag.AlignTop)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        """Draw a rounded-rectangle background using the palette window color."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(
            0, 0, self.width(), self.height(), self.BORDER_RADIUS, self.BORDER_RADIUS
        )
        bg = self.palette().color(QPalette.ColorRole.Window)
        painter.fillPath(path, bg)
        painter.end()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_toast(self) -> None:
        """Show the toast with fade-in animation."""
        self.show()
        self._fade_in.start()
        if self._timer is not None:
            self._timer.start()

    def dismiss(self) -> None:
        """Dismiss the toast with fade-out animation."""
        self._timer.stop()
        self._fade_out.start()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_fade_out_finished(self) -> None:
        """Clean up after fade-out completes."""
        self.hide()
        self.closed.emit()
        self.deleteLater()

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Trigger a repaint on resize so the rounded rect stays correct."""
        super().resizeEvent(event)
        self.update()


class ToastManager:
    """Singleton manager that positions and displays multiple toasts.

    Toasts are stacked vertically at the bottom-right of the parent widget.
    At most ``ToastNotification.MAX_VISIBLE`` toasts are shown at once;
    excess toasts are queued and shown as earlier ones are dismissed.
    """

    _instance: Optional[ToastManager] = None

    def __init__(self) -> None:
        self._queue: list[ToastNotification] = []
        self._visible: list[ToastNotification] = []
        self._parent: Optional[QWidget] = None

    @classmethod
    def instance(cls) -> ToastManager:
        """Return the singleton ``ToastManager`` instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_parent(self, parent: QWidget) -> None:
        """Set the parent widget used for positioning toasts.

        Args:
            parent: The main application window or container.
        """
        self._parent = parent

    def show_toast(
        self,
        message: str,
        level: str = "INFO",
        timeout: int = ToastNotification.DEFAULT_TIMEOUT,
    ) -> None:
        """Show a toast notification.

        Args:
            message: Text to display.
            level: One of ``"INFO"``, ``"SUCCESS"``, ``"WARNING"``, ``"ERROR"``.
            timeout: Milliseconds before auto-dismiss. 0 disables auto-dismiss.
        """
        toast_level = ToastLevel(level.upper())
        toast = ToastNotification(
            message=message,
            level=toast_level,
            timeout=timeout,
            parent=self._parent,
        )
        toast.closed.connect(lambda t=toast: self._on_toast_closed(t))
        self._queue.append(toast)
        self._show_next()

    def _show_next(self) -> None:
        """Display the next queued toast if below the visible limit."""
        while len(self._visible) < ToastNotification.MAX_VISIBLE and self._queue:
            toast = self._queue.pop(0)
            self._visible.append(toast)
            self._reposition_all()
            toast.show_toast()

    def _reposition_all(self) -> None:
        """Reposition all visible toasts in a vertical stack."""
        parent_rect = self._parent.rect() if self._parent else QApplication.primaryScreen().availableGeometry()
        x_offset = parent_rect.width() - ToastNotification.TOAST_WIDTH - 20
        y_offset = parent_rect.height() - 20

        for toast in reversed(self._visible):
            toast.setFixedHeight(ToastNotification.TOAST_HEIGHT)
            y_offset -= toast.height() + 10
            toast.move(x_offset, y_offset)

    def _on_toast_closed(self, toast: ToastNotification) -> None:
        """Handle a toast being dismissed."""
        if toast in self._visible:
            self._visible.remove(toast)
        self._reposition_all()
        self._show_next()
