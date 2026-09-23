"""NavigationRail — narrow vertical strip with SVG icon + text buttons."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from lexproof.ui.icons import get_icon
from lexproof.ui.styles.constants import (
    SIDEBAR_COLLAPSED_WIDTH,
    SIDEBAR_EXPANDED_WIDTH,
    SIDEBAR_ICON_SIZE,
    SIDEBAR_ITEM_HEIGHT,
    SIDEBAR_ITEM_RADIUS,
)


def _svg_label(svg: str, size: int = SIDEBAR_ICON_SIZE) -> QLabel:
    """Create a QLabel displaying an inline SVG via QPixmap."""
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QImage, QPixmap, QPalette
    from PySide6.QtWidgets import QApplication

    lbl = QLabel()
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    app = QApplication.instance()
    if app:
        palette = app.palette()
        color = palette.color(QPalette.ColorRole.ButtonText)
        hex_color = f"#{color.red():02x}{color.green():02x}{color.blue():02x}"
        svg = svg.replace("currentColor", hex_color)

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


class NavigationRail(QWidget):
    """Narrow vertical navigation rail similar to VS Code's activity bar.

    Width: 64px collapsed (icons only), 220px expanded (icons + text).
    """

    navigation_changed = Signal(str)

    _NAV_ITEMS: list[tuple[str, str, str]] = [
        ("inicio", "home", "Inicio"),
        ("evidencias", "file", "Evidencias"),
        ("hashes", "hash", "Hashes"),
        ("ocr", "ocr", "OCR"),
        ("timeline", "timeline", "Timeline"),
        ("relatorio", "report", "Relatorio"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navigationRail")
        self._expanded = False
        self._active = "inicio"
        self._items: dict[str, QPushButton] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedWidth(SIDEBAR_COLLAPSED_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 6, 0, 6)
        root.setSpacing(2)

        # Toggle button (top)
        self._toggle_btn = self._create_toggle_button()
        root.addWidget(self._toggle_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        root.addSpacing(4)

        # Separator
        root.addWidget(self._create_separator())

        # Navigation items
        self._nav_container = QWidget()
        self._nav_layout = QVBoxLayout(self._nav_container)
        self._nav_layout.setContentsMargins(4, 4, 4, 4)
        self._nav_layout.setSpacing(2)

        for name, icon_name, label in self._NAV_ITEMS:
            btn = self._create_nav_button(name, icon_name, label)
            self._items[name] = btn
            self._nav_layout.addWidget(btn)

        self._nav_layout.addStretch()
        root.addWidget(self._nav_container, stretch=1)

        # Separator before settings
        root.addWidget(self._create_separator())

        # Settings button (bottom)
        self._items["settings"] = self._create_nav_button("settings", "settings", "Configuracoes")
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

    def _create_toggle_button(self) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(40, 40)
        btn.setToolTip("Expandir / colapsar barra de navegacao")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        svg = get_icon("menu")
        from PySide6.QtGui import QIcon as QI, QPixmap, QImage, QPalette
        from PySide6.QtCore import QByteArray
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app:
            palette = app.palette()
            color = palette.color(QPalette.ColorRole.ButtonText)
            hex_color = f"#{color.red():02x}{color.green():02x}{color.blue():02x}"
            svg = svg.replace("currentColor", hex_color)

        data = QByteArray(svg.encode("utf-8"))
        img = QImage.fromData(data)
        if not img.isNull():
            pixmap = QPixmap.fromImage(img).scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            btn.setIcon(QI(pixmap))

        btn.setStyleSheet(
            "QPushButton { border: none; border-radius: 8px; padding: 8px; }"
            "QPushButton:hover { background-color: palette(mid); }"
        )
        btn.clicked.connect(self._toggle_expand)
        return btn

    def _create_nav_button(self, name: str, icon_name: str, label: str) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName(f"navBtn_{name}")
        btn.setToolTip(label)
        btn.setCheckable(True)
        btn.setFixedHeight(SIDEBAR_ITEM_HEIGHT)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Build icon via SVG with palette-aware color
        from PySide6.QtGui import QIcon as QI, QPixmap, QImage, QPalette
        from PySide6.QtCore import QByteArray
        from PySide6.QtWidgets import QApplication

        svg = get_icon(icon_name)
        app = QApplication.instance()
        if app:
            palette = app.palette()
            color = palette.color(QPalette.ColorRole.ButtonText)
            hex_color = f"#{color.red():02x}{color.green():02x}{color.blue():02x}"
            svg = svg.replace("currentColor", hex_color)

        data = QByteArray(svg.encode("utf-8"))
        img = QImage.fromData(data)
        if not img.isNull():
            pixmap = QPixmap.fromImage(img).scaled(
                SIDEBAR_ICON_SIZE, SIDEBAR_ICON_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            btn.setIcon(QI(pixmap))
            btn.setIconSize(pixmap.size())

        # Inner layout with icon + label
        inner = QWidget()
        inner_layout = QHBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(10)

        icon_lbl = _svg_label(get_icon(icon_name), SIDEBAR_ICON_SIZE)
        text_lbl = QLabel(label)
        text_lbl.setObjectName(f"navLabel_{name}")
        text_lbl.setVisible(self._expanded)

        inner_layout.addWidget(icon_lbl)
        inner_layout.addWidget(text_lbl)
        inner_layout.addStretch()

        btn_layout = QHBoxLayout(btn)
        btn_layout.setContentsMargins(8, 0, 8, 0)
        btn_layout.addWidget(inner)

        btn.setStyleSheet(
            "QPushButton { border: none; border-radius: %dpx; text-align: left; padding: 4px 8px; }"
            "QPushButton:hover { background-color: palette(mid); }" % SIDEBAR_ITEM_RADIUS
        )

        btn.clicked.connect(lambda _checked=False, n=name: self._on_item_clicked(n))
        return btn

    def _create_separator(self) -> QWidget:
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: palette(mid); border: none; margin: 4px 8px;")
        return sep

    def set_active(self, name: str) -> None:
        if name not in self._items:
            return
        self._active = name
        self._update_active_style()

    def _on_item_clicked(self, name: str) -> None:
        self.set_active(name)
        self.navigation_changed.emit(name)

    def _update_active_style(self) -> None:
        for key, btn in self._items.items():
            is_active = key == self._active
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet(
                    "QPushButton { border: none; border-radius: %dpx; text-align: left; padding: 4px 8px; "
                    "background-color: palette(highlight); color: palette(highlightedText); }"
                    % SIDEBAR_ITEM_RADIUS
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { border: none; border-radius: %dpx; text-align: left; padding: 4px 8px; }"
                    "QPushButton:hover { background-color: palette(mid); }" % SIDEBAR_ITEM_RADIUS
                )

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        target = SIDEBAR_EXPANDED_WIDTH if self._expanded else SIDEBAR_COLLAPSED_WIDTH

        self._width_anim.setStartValue(self.width())
        self._width_anim.setEndValue(target)
        self._min_width_anim.setStartValue(self.width())
        self._min_width_anim.setEndValue(target)

        self._width_anim.start()
        self._min_width_anim.start()

        for key, btn in self._items.items():
            lbl = btn.findChild(QLabel, f"navLabel_{key}")
            if lbl is not None:
                lbl.setVisible(self._expanded)

        self._update_active_style()


# Backward-compatible alias
SidebarWidget = NavigationRail
