"""NavigationRail — narrow vertical strip with icon + text buttons."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class NavigationRail(QWidget):
    """Narrow vertical navigation rail similar to VS Code's activity bar.

    Width: 64px collapsed (icons only), 200px expanded (icons + text).
    """

    navigation_changed = Signal(str)

    _NAV_ITEMS: list[tuple[str, str, str]] = [
        ("inicio", "\u2302", "Inicio"),
        ("evidencias", "\u2630", "Evidencias"),
        ("hashes", "#", "Hashes"),
        ("ocr", "\u2315", "OCR"),
        ("timeline", "\u23F1", "Timeline"),
        ("relatorio", "\u2399", "Relatorio"),
    ]

    _COLLAPSED_WIDTH = 64
    _EXPANDED_WIDTH = 200

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navigationRail")
        self._expanded = False
        self._active = "inicio"
        self._items: dict[str, QPushButton] = {}
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setFixedWidth(self._COLLAPSED_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 8)
        root.setSpacing(4)

        # Toggle button (top)
        self._toggle_btn = self._create_toggle_button()
        root.addWidget(self._toggle_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        root.addSpacing(8)

        # Separator line
        sep_top = self._create_separator()
        root.addWidget(sep_top)

        # Navigation items
        self._nav_container = QWidget()
        self._nav_layout = QVBoxLayout(self._nav_container)
        self._nav_layout.setContentsMargins(0, 4, 0, 4)
        self._nav_layout.setSpacing(2)

        for name, icon, label in self._NAV_ITEMS:
            btn = self._create_nav_button(name, icon, label)
            self._items[name] = btn
            self._nav_layout.addWidget(btn)

        self._nav_layout.addStretch()
        root.addWidget(self._nav_container, stretch=1)

        # Separator before settings
        sep_bottom = self._create_separator()
        root.addWidget(sep_bottom)

        # Settings button (bottom)
        self._items["settings"] = self._create_nav_button(
            "settings", "\u2699", "Configuracoes"
        )
        root.addWidget(self._items["settings"])

        # Set initial active state
        self._update_active_style()

        # Width animation
        self._width_anim = QPropertyAnimation(self, b"maximumWidth")
        self._width_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._width_anim.setDuration(200)

        self._min_width_anim = QPropertyAnimation(self, b"minimumWidth")
        self._min_width_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._min_width_anim.setDuration(200)

    # ------------------------------------------------------------------
    # Widget helpers
    # ------------------------------------------------------------------

    def _create_toggle_button(self) -> QPushButton:
        btn = QPushButton("\u2630")
        btn.setFixedSize(40, 40)
        btn.setToolTip("Expandir / colapsar barra de navegacao")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { border: none; font-size: 18px; border-radius: 8px; }"
            "QPushButton:hover { background-color: palette(highlight); }"
        )
        btn.clicked.connect(self._toggle_expand)
        return btn

    def _create_nav_button(self, name: str, icon_text: str, label: str) -> QPushButton:
        btn = QPushButton(icon_text)
        btn.setObjectName(f"navBtn_{name}")
        btn.setToolTip(label)
        btn.setCheckable(True)
        btn.setFixedHeight(44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { border: none; font-size: 18px; border-radius: 8px; text-align: center; }"
        )

        # Label hidden in collapsed mode, stored for expand
        inner = QWidget()
        inner_layout = QHBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(8)

        icon_lbl = QLabel(icon_text)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFixedWidth(24)
        text_lbl = QLabel(label)
        text_lbl.setObjectName(f"navLabel_{name}")
        text_lbl.setVisible(self._expanded)

        inner_layout.addWidget(icon_lbl)
        inner_layout.addWidget(text_lbl)
        inner_layout.addStretch()

        btn_layout = QHBoxLayout(btn)
        btn_layout.setContentsMargins(0, 0, 8, 0)
        btn_layout.addWidget(inner)

        btn.clicked.connect(lambda _checked=False, n=name: self._on_item_clicked(n))
        return btn

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: palette(mid); border: none;")
        return sep

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_active(self, name: str) -> None:
        """Highlight the given navigation section."""
        if name not in self._items:
            return
        self._active = name
        self._update_active_style()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_item_clicked(self, name: str) -> None:
        self.set_active(name)
        self.navigation_changed.emit(name)

    def _update_active_style(self) -> None:
        for key, btn in self._items.items():
            is_active = key == self._active
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet(
                    "QPushButton { border: none; font-size: 18px; border-radius: 8px; "
                    "text-align: center; background-color: palette(highlight); "
                    "color: palette(highlightedText); }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { border: none; font-size: 18px; border-radius: 8px; "
                    "text-align: center; }"
                    "QPushButton:hover { background-color: palette(mid); }"
                )

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        target = self._EXPANDED_WIDTH if self._expanded else self._COLLAPSED_WIDTH

        self._width_anim.setStartValue(self.width())
        self._width_anim.setEndValue(target)
        self._min_width_anim.setStartValue(self.width())
        self._min_width_anim.setEndValue(target)

        self._width_anim.start()
        self._min_width_anim.start()

        # Toggle label visibility
        for key, btn in self._items.items():
            lbl = btn.findChild(QLabel, f"navLabel_{key}")
            if lbl is not None:
                lbl.setVisible(self._expanded)

        self._toggle_btn.setText("\u2630")
        self._update_active_style()


# Backward-compatible alias
SidebarWidget = NavigationRail
