from __future__ import annotations

from typing import Final

from PySide6.QtCore import QMimeData, QSize, Qt, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from lexproof.ui.styles.theme import ThemeManager, ThemeMode
from lexproof.ui.widgets.log_panel import LogPanelWidget
from lexproof.ui.widgets.sidebar import SidebarWidget
from lexproof.ui.widgets.status_bar import StatusBarWidget

APP_TITLE: Final[str] = "LexProof - Preservacao de Evidencias Digitais"
APP_VERSION: Final[str] = "0.1.0"
MIN_SIZE: Final[QSize] = QSize(1200, 800)


class MainWindow(QMainWindow):
    """Main application window with sidebar, tabs, log panel, and status bar."""

    file_dropped = Signal(list)
    case_opened = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(MIN_SIZE)
        self.resize(1400, 900)
        self.setAcceptDrops(True)

        self._theme_manager = ThemeManager.instance()
        self._sidebar_visible = True
        self._log_panel_visible = True

        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._apply_theme()

    # ------------------------------------------------------------------ #
    # UI Setup
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        """Construct the main layout: sidebar | central tabs, with log dock below."""
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        # Sidebar
        self._sidebar = SidebarWidget(self)

        # Tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.tabCloseRequested.connect(self._close_tab)

        # Add a welcome tab
        self._add_welcome_tab()

        # Splitter for sidebar + tabs
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._tab_widget)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([240, 960])

        # Log panel dock
        self._log_dock = QDockWidget("Registro de Atividades", self)
        self._log_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self._log_panel = LogPanelWidget()
        self._log_dock.setWidget(self._log_panel)
        self._log_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)

        # Drop zone overlay (added to central widget)
        from lexproof.ui.widgets.drop_zone import DropZoneWidget

        self._drop_zone = DropZoneWidget(central)
        self._drop_zone.files_dropped.connect(self._on_files_dropped)

        # Main layout
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._splitter)

        # Position drop zone over central
        self._drop_zone.setFixedSize(central.size())

    def _add_welcome_tab(self) -> None:
        """Create the initial welcome tab."""
        welcome = QWidget()
        layout = QVBoxLayout(welcome)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        from PySide6.QtWidgets import QLabel, QPushButton

        title = QLabel("Bem-vindo ao LexProof")
        title.setObjectName("headingLabel")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1A1A1A;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(
            "Sistema de Preservacao Tecnica de Evidencias Digitais\n"
            "Arraste arquivos para esta janela ou crie um novo caso para comecar."
        )
        subtitle.setObjectName("subheadingLabel")
        subtitle.setStyleSheet("font-size: 14px; color: #666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        new_case_btn = QPushButton("Novo Caso")
        new_case_btn.setFixedWidth(200)
        new_case_btn.setFixedHeight(40)
        new_case_btn.clicked.connect(self._new_case)

        open_case_btn = QPushButton("Abrir Caso Existente")
        open_case_btn.setFixedWidth(200)
        open_case_btn.setFixedHeight(40)
        open_case_btn.setObjectName("secondaryButton")
        open_case_btn.clicked.connect(self._open_case)

        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(24)
        layout.addWidget(new_case_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(open_case_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self._tab_widget.addTab(welcome, "Inicio")

    def _setup_menu_bar(self) -> None:
        """Build the application menu bar."""
        menubar = self.menuBar()

        # ---- File ----
        file_menu = menubar.addMenu("Arquivo(&A)")

        new_action = QAction("Novo Caso", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._new_case)
        file_menu.addAction(new_action)

        open_action = QAction("Abrir Caso", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._open_case)
        file_menu.addAction(open_action)

        save_action = QAction("Salvar", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_case)
        file_menu.addAction(save_action)

        save_as_action = QAction("Salvar Como...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._save_case_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        import_action = QAction("Importar Arquivos", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self._import_files)
        file_menu.addAction(import_action)

        recent_menu = QMenu("Arquivos Recentes", self)
        file_menu.addMenu(recent_menu)

        file_menu.addSeparator()

        exit_action = QAction("Sair", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ---- Edit ----
        edit_menu = menubar.addMenu("Editar(&E)")

        prefs_action = QAction("Preferencias", self)
        prefs_action.setShortcut(QKeySequence("Ctrl+,"))
        prefs_action.triggered.connect(self._open_preferences)
        edit_menu.addAction(prefs_action)

        # ---- View ----
        view_menu = menubar.addMenu("Exibir(&V)")

        toggle_sidebar_action = QAction("Alternar Barra Lateral", self)
        toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        toggle_sidebar_action.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(toggle_sidebar_action)

        toggle_log_action = QAction("Alternar Painel de Log", self)
        toggle_log_action.setShortcut(QKeySequence("Ctrl+L"))
        toggle_log_action.triggered.connect(self._toggle_log_panel)
        view_menu.addAction(toggle_log_action)

        view_menu.addSeparator()

        theme_menu = QMenu("Tema", self)

        light_theme_action = QAction("Claro", self)
        light_theme_action.triggered.connect(lambda: self._set_theme(ThemeMode.LIGHT))
        theme_menu.addAction(light_theme_action)

        dark_theme_action = QAction("Escuro", self)
        dark_theme_action.triggered.connect(lambda: self._set_theme(ThemeMode.DARK))
        theme_menu.addAction(dark_theme_action)

        system_theme_action = QAction("Sistema", self)
        system_theme_action.triggered.connect(lambda: self._set_theme(ThemeMode.SYSTEM))
        theme_menu.addAction(system_theme_action)

        view_menu.addMenu(theme_menu)

        # ---- Help ----
        help_menu = menubar.addMenu("Ajuda(&H)")

        about_action = QAction("Sobre o LexProof", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_status_bar(self) -> None:
        """Initialize the custom status bar."""
        self._status_bar = StatusBarWidget()
        self.statusBar().addPermanentWidget(self._status_bar, 1)
        self.statusBar().setFixedHeight(32)

    def _apply_theme(self) -> None:
        """Apply the current theme stylesheet."""
        stylesheet = self._theme_manager.get_stylesheet()
        QApplication.instance().setStyleSheet(stylesheet)  # type: ignore[union-attr]

    # ------------------------------------------------------------------ #
    # Resize override to keep drop zone sized correctly
    # ------------------------------------------------------------------ #

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        if hasattr(self, "_drop_zone") and hasattr(self, "_log_dock"):
            central = self.centralWidget()
            if central:
                self._drop_zone.setFixedSize(central.size())

    # ------------------------------------------------------------------ #
    # Drag & Drop
    # ------------------------------------------------------------------ #

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if paths:
            self.file_dropped.emit(paths)
            self._log_panel.log("INFO", f"Arquivos recebidos: {len(paths)} arquivo(s)")

    # ------------------------------------------------------------------ #
    # Tab Management
    # ------------------------------------------------------------------ #

    def add_tab(self, widget: QWidget, title: str) -> int:
        """Add a new tab and return its index."""
        index = self._tab_widget.addTab(widget, title)
        self._tab_widget.setCurrentIndex(index)
        return index

    def _close_tab(self, index: int) -> None:
        if self._tab_widget.count() > 1:
            self._tab_widget.removeTab(index)

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def _new_case(self) -> None:
        """Create a new case tab."""
        case_widget = QWidget()
        layout = QVBoxLayout(case_widget)
        layout.setContentsMargins(24, 24, 24, 24)

        from PySide6.QtWidgets import QLabel

        label = QLabel("Novo Caso - Em construcao")
        label.setStyleSheet("font-size: 16px; color: #666;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self.add_tab(case_widget, "Novo Caso")
        self._log_panel.log("INFO", "Novo caso criado")

    def _open_case(self) -> None:
        """Open an existing case file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Caso",
            "",
            "LexProof Cases (*.lexcase);;Todos os Arquivos (*)",
        )
        if path:
            self._log_panel.log("INFO", f"Caso aberto: {path}")
            self.case_opened.emit(path)

    def _save_case(self) -> None:
        """Save the current case."""
        self._log_panel.log("INFO", "Caso salvo")

    def _save_case_as(self) -> None:
        """Save the current case with a new name."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Caso Como",
            "",
            "LexProof Cases (*.lexcase);;Todos os Arquivos (*)",
        )
        if path:
            self._log_panel.log("INFO", f"Caso salvo como: {path}")

    def _import_files(self) -> None:
        """Import files into the current case."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar Arquivos",
            "",
            "Todos os Arquivos (*)",
        )
        if paths:
            self._log_panel.log("INFO", f"Arquivos importados: {len(paths)} arquivo(s)")

    def _toggle_sidebar(self) -> None:
        """Toggle the sidebar visibility."""
        self._sidebar_visible = not self._sidebar_visible
        self._sidebar.setVisible(self._sidebar_visible)

    def _toggle_log_panel(self) -> None:
        """Toggle the log panel dock visibility."""
        self._log_panel_visible = not self._log_panel_visible
        self._log_dock.setVisible(self._log_panel_visible)

    def _set_theme(self, mode: ThemeMode) -> None:
        """Switch the application theme."""
        self._theme_manager.set_mode(mode)
        self._apply_theme()
        mode_label = {"light": "Claro", "dark": "Escuro", "system": "Sistema"}
        self._log_panel.log(
            "INFO", f"Tema alterado para: {mode_label.get(mode.value, mode.value)}"
        )

    def _open_preferences(self) -> None:
        """Open the preferences dialog."""
        self._log_panel.log("INFO", "Preferencias abertas")

    def _show_about(self) -> None:
        """Display the About dialog."""
        QMessageBox.about(
            self,
            "Sobre o LexProof",
            f"<h2>LexProof v{APP_VERSION}</h2>"
            "<p>Sistema de Preservacao Tecnica de Evidencias Digitais</p>"
            "<p>Ferramenta profissional para preservacao, verificacao "
            "e apresentacao de evidencias digitais em ambientes juridicos.</p>"
            "<p>Licenca: MIT</p>",
        )

    def _on_files_dropped(self, paths: list[str]) -> None:
        """Handle files dropped onto the drop zone overlay."""
        self.file_dropped.emit(paths)
        self._log_panel.log("INFO", f"Arquivos recebidos via drop: {len(paths)} arquivo(s)")

    # ------------------------------------------------------------------ #
    # Public accessors
    # ------------------------------------------------------------------ #

    @property
    def log_panel(self) -> LogPanelWidget:
        return self._log_panel

    @property
    def sidebar(self) -> SidebarWidget:
        return self._sidebar

    @property
    def status_bar(self) -> StatusBarWidget:
        return self._status_bar

    @property
    def tab_widget(self) -> QTabWidget:
        return self._tab_widget
