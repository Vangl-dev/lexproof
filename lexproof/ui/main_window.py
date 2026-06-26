from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
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
from lexproof.ui.widgets.drop_zone import DropZoneWidget
from lexproof.ui.widgets.evidence_list import EvidenceListWidget
from lexproof.ui.widgets.properties_panel import PropertiesPanel
from lexproof.ui.widgets.placeholder_panel import PlaceholderPanel
from lexproof.ui.widgets.case_info_panel import CaseInfoPanel
from lexproof.ui.widgets.toast_notification import ToastManager
from lexproof.core.constants import APP_NAME, APP_VERSION
from lexproof.core.event_bus import EventBus
from lexproof.core.session import SessionManager

EVIDENCE_FILTER = (
    "Imagens (*.png *.jpg *.jpeg *.gif *.bmp *.tiff);;"
    "Texto (*.txt *.csv *.json *.xml *.html);;"
    "PDF (*.pdf);;"
    "Arquivos Compactados (*.zip *.rar *.7z);;"
    "Todos os Arquivos (*)"
)


class MainWindow(QMainWindow):
    """Janela principal do LexProof com sidebar, abas, log e barra de status."""

    file_dropped = Signal(list)
    case_opened = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        event_bus: EventBus | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        super().__init__(parent)

        self._event_bus = event_bus or EventBus()
        self._session_manager = session_manager or SessionManager()

        self.setWindowTitle(f"{APP_NAME} - Preservação de Evidências Digitais")
        self.setMinimumSize(QSize(1200, 800))
        self.resize(1400, 900)
        self.setAcceptDrops(True)

        icon_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icons" / "app_icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._theme_manager = ThemeManager.instance()
        self._toast_manager = ToastManager.instance()
        self._toast_manager.set_parent(self)

        self._sidebar_visible = True
        self._log_panel_visible = True
        self._evidence_list: list[str] = []

        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._apply_theme()

        self._connect_events()

    # ------------------------------------------------------------------ #
    # UI Setup
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        """Constrói o layout principal: sidebar | central com abas e painéis."""
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        self._sidebar = SidebarWidget(self)

        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.tabCloseRequested.connect(self._close_tab)

        self._add_welcome_tab()
        self._add_placeholder_tabs()

        self._properties_panel = PropertiesPanel()
        self._properties_dock = QDockWidget("Propriedades", self)
        self._properties_dock.setWidget(self._properties_panel)
        self._properties_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self._properties_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        central_splitter = QSplitter(Qt.Orientation.Vertical)
        central_splitter.addWidget(self._tab_widget)
        central_splitter.addWidget(self._properties_dock)
        central_splitter.setStretchFactor(0, 3)
        central_splitter.setStretchFactor(1, 1)
        central_splitter.setSizes([600, 200])

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(central_splitter)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([240, 960])

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

        self._drop_zone = DropZoneWidget(central)
        self._drop_zone.files_dropped.connect(self._on_files_dropped)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._splitter)

        self._drop_zone.setFixedSize(central.size())

    def _add_welcome_tab(self) -> None:
        """Cria a aba de boas-vindas com botões de ação e zona de drop."""
        welcome = QWidget()
        layout = QVBoxLayout(welcome)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("Bem-vindo ao LexProof")
        title.setObjectName("headingLabel")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1A1A1A;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(
            "Sistema de Preservação Técnica de Evidências Digitais\n"
            "Arraste arquivos para esta janela ou crie um novo caso para começar."
        )
        subtitle.setObjectName("subheadingLabel")
        subtitle.setStyleSheet("font-size: 14px; color: #666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        new_case_btn = QPushButton("Novo Caso")
        new_case_btn.setFixedWidth(200)
        new_case_btn.setFixedHeight(40)
        new_case_btn.clicked.connect(self._new_case)

        open_case_btn = QPushButton("Abrir Caso")
        open_case_btn.setFixedWidth(200)
        open_case_btn.setFixedHeight(40)
        open_case_btn.setObjectName("secondaryButton")
        open_case_btn.clicked.connect(self._open_case)

        import_btn = QPushButton("Adicionar Arquivos")
        import_btn.setFixedWidth(200)
        import_btn.setFixedHeight(40)
        import_btn.setObjectName("secondaryButton")
        import_btn.clicked.connect(self._import_files)

        drop_hint = QLabel("ou arraste arquivos aqui")
        drop_hint.setStyleSheet("font-size: 12px; color: #999;")
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(24)
        layout.addWidget(new_case_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(open_case_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(import_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(12)
        layout.addWidget(drop_hint, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self._tab_widget.addTab(welcome, "Início")

    def _add_placeholder_tabs(self) -> None:
        """Adiciona abas placeholder para funcionalidades em desenvolvimento."""
        tabs = [
            ("Hashes", "\u26D3", "Cálculo e verificação de hashes de integridade"),
            ("OCR", "\U0001F50D", "Reconhecimento óptico de caracteres"),
            ("Timeline", "\u23F1", "Linha do tempo de evidências"),
            ("Relatório", "\U0001F4C4", "Geração de relatórios de preservação"),
        ]
        for label, icon, description in tabs:
            panel = PlaceholderPanel(f"{icon} {label}", description)
            self._tab_widget.addTab(panel, label)

    # ------------------------------------------------------------------ #
    # Menu Bar
    # ------------------------------------------------------------------ #

    def _setup_menu_bar(self) -> None:
        """Constrói a barra de menus da aplicação."""
        menubar = self.menuBar()

        self._build_file_menu(menubar)
        self._build_edit_menu(menubar)
        self._build_view_menu(menubar)
        self._build_tools_menu(menubar)
        self._build_help_menu(menubar)

    def _build_file_menu(self, menubar: QMenuBar) -> None:
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

        self._recent_menu = QMenu("Arquivos Recentes", self)
        self._recent_menu.setEnabled(False)
        file_menu.addMenu(self._recent_menu)

        file_menu.addSeparator()

        exit_action = QAction("Sair", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _build_edit_menu(self, menubar: QMenuBar) -> None:
        edit_menu = menubar.addMenu("Editar(&E)")

        prefs_action = QAction("Preferências", self)
        prefs_action.setShortcut(QKeySequence("Ctrl+,"))
        prefs_action.triggered.connect(self._open_preferences)
        edit_menu.addAction(prefs_action)

    def _build_view_menu(self, menubar: QMenuBar) -> None:
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

    def _build_tools_menu(self, menubar: QMenuBar) -> None:
        tools_menu = menubar.addMenu("Ferramentas(&T)")

        hash_action = QAction("Executar Hashes", self)
        hash_action.triggered.connect(self._run_hashes)
        tools_menu.addAction(hash_action)

        ocr_action = QAction("Executar OCR", self)
        ocr_action.triggered.connect(self._run_ocr)
        tools_menu.addAction(ocr_action)

        verify_action = QAction("Verificar Integridade", self)
        verify_action.triggered.connect(self._run_verification)
        tools_menu.addAction(verify_action)

        tools_menu.addSeparator()

        report_action = QAction("Gerar Relatório", self)
        report_action.triggered.connect(self._generate_report)
        tools_menu.addAction(report_action)

    def _build_help_menu(self, menubar: QMenuBar) -> None:
        help_menu = menubar.addMenu("Ajuda(&H)")

        about_action = QAction("Sobre o LexProof", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------ #
    # Status Bar
    # ------------------------------------------------------------------ #

    def _setup_status_bar(self) -> None:
        """Inicializa a barra de status customizada."""
        self._status_bar = StatusBarWidget()
        self.statusBar().addPermanentWidget(self._status_bar, 1)
        self.statusBar().setFixedHeight(32)

    # ------------------------------------------------------------------ #
    # Event Bus Connections
    # ------------------------------------------------------------------ #

    def _connect_events(self) -> None:
        """Conecta sinais do event bus aos slots relevantes."""
        pass

    # ------------------------------------------------------------------ #
    # Theme
    # ------------------------------------------------------------------ #

    def _apply_theme(self) -> None:
        """Aplica o stylesheet do tema atual."""
        stylesheet = self._theme_manager.get_stylesheet()
        QApplication.instance().setStyleSheet(stylesheet)  # type: ignore[union-attr]

    def _set_theme(self, mode: ThemeMode) -> None:
        """Alterna o tema da aplicação."""
        self._theme_manager.set_mode(mode)
        self._apply_theme()
        mode_label = {ThemeMode.LIGHT: "Claro", ThemeMode.DARK: "Escuro", ThemeMode.SYSTEM: "Sistema"}
        label = mode_label.get(mode, mode.value)
        self._log_panel.log("INFO", f"Tema alterado para: {label}")
        self._toast_manager.show_toast(f"Tema alterado para: {label}", "INFO")

    # ------------------------------------------------------------------ #
    # Resize
    # ------------------------------------------------------------------ #

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_drop_zone") and hasattr(self, "centralWidget"):
            central = self.centralWidget()
            if central:
                self._drop_zone.setFixedSize(central.size())

    # ------------------------------------------------------------------ #
    # Drag & Drop
    # ------------------------------------------------------------------ #

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if paths:
            self._on_files_dropped(paths)

    # ------------------------------------------------------------------ #
    # Tab Management
    # ------------------------------------------------------------------ #

    def add_tab(self, widget: QWidget, title: str) -> int:
        """Adiciona uma nova aba e retorna seu índice."""
        index = self._tab_widget.addTab(widget, title)
        self._tab_widget.setCurrentIndex(index)
        return index

    def _close_tab(self, index: int) -> None:
        if self._tab_widget.count() > 1:
            self._tab_widget.removeTab(index)

    # ------------------------------------------------------------------ #
    # File Operations
    # ------------------------------------------------------------------ #

    def _new_case(self) -> None:
        """Cria um novo caso com aba de informações."""
        self._session_manager.start_session()
        case_widget = CaseInfoPanel()
        self.add_tab(case_widget, "Novo Caso")
        self._log_panel.log("INFO", "Novo caso criado")
        self._toast_manager.show_toast("Novo caso criado com sucesso", "SUCCESS")
        self._status_bar.set_status("Novo caso criado")

    def _open_case(self) -> None:
        """Abre um arquivo de caso existente."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Caso",
            "",
            "LexProof Cases (*.lexcase);;Todos os Arquivos (*)",
        )
        if path:
            try:
                self._session_manager.load_session(Path(path))
                self._log_panel.log("INFO", f"Caso aberto: {path}")
                self._toast_manager.show_toast(f"Caso aberto: {Path(path).name}", "SUCCESS")
                self.case_opened.emit(path)
                self._status_bar.set_status(f"Caso aberto: {Path(path).name}")
            except Exception as exc:
                self._log_panel.log("ERROR", f"Erro ao abrir caso: {exc}")
                self._toast_manager.show_toast(f"Erro ao abrir caso: {exc}", "ERROR")

    def _save_case(self) -> None:
        """Salva o caso atual."""
        try:
            path = self._session_manager.save_session()
            self._log_panel.log("INFO", f"Caso salvo em: {path}")
            self._toast_manager.show_toast("Caso salvo com sucesso", "SUCCESS")
            self._status_bar.set_status("Caso salvo")
        except Exception as exc:
            self._log_panel.log("ERROR", f"Erro ao salvar caso: {exc}")
            self._toast_manager.show_toast(f"Erro ao salvar caso: {exc}", "ERROR")

    def _save_case_as(self) -> None:
        """Salva o caso com um novo nome de arquivo."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Caso Como",
            "",
            "LexProof Cases (*.lexcase);;Todos os Arquivos (*)",
        )
        if path:
            try:
                save_path = Path(path)
                if not save_path.suffix:
                    save_path = save_path.with_suffix(".lexcase")
                self._session_manager.save_session(save_path)
                self._log_panel.log("INFO", f"Caso salvo como: {save_path}")
                self._toast_manager.show_toast(f"Caso salvo: {save_path.name}", "SUCCESS")
                self._status_bar.set_status(f"Caso salvo: {save_path.name}")
            except Exception as exc:
                self._log_panel.log("ERROR", f"Erro ao salvar caso: {exc}")
                self._toast_manager.show_toast(f"Erro ao salvar caso: {exc}", "ERROR")

    def _import_files(self) -> None:
        """Importa arquivos de evidência para o caso atual."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar Arquivos",
            "",
            EVIDENCE_FILTER,
        )
        if paths:
            self._process_imported_files(paths)

    def _on_files_dropped(self, paths: list[str]) -> None:
        """Processa arquivos arrastados e soltados na janela."""
        self._process_imported_files(paths)

    def _process_imported_files(self, paths: list[str]) -> None:
        """Adiciona arquivos à lista de evidências e registra no log."""
        for file_path in paths:
            path_obj = Path(file_path)
            if path_obj.exists() and file_path not in self._evidence_list:
                self._evidence_list.append(file_path)
                try:
                    self._session_manager.add_evidence(path_obj)
                except Exception as exc:
                    self._log_panel.log("WARNING", f"Falha ao registrar evidência {path_obj.name}: {exc}")

        count = len(paths)
        self._log_panel.log("INFO", f"Arquivos importados: {count} arquivo(s)")
        self._toast_manager.show_toast(
            f"{count} arquivo(s) importado(s) com sucesso",
            "SUCCESS",
        )
        self._status_bar.set_status(f"{count} arquivo(s) importado(s)")
        self.file_dropped.emit(paths)

    # ------------------------------------------------------------------ #
    # Tools
    # ------------------------------------------------------------------ #

    def _run_hashes(self) -> None:
        """Executa o cálculo de hashes para todas as evidências."""
        if not self._evidence_list:
            self._log_panel.log("WARNING", "Nenhuma evidência para calcular hashes")
            self._toast_manager.show_toast("Nenhuma evidência disponível", "WARNING")
            return
        self._log_panel.log("INFO", f"Calculando hashes para {len(self._evidence_list)} arquivo(s)...")
        self._status_bar.set_status("Calculando hashes...")
        self._status_bar.set_progress(0)
        for i, file_path in enumerate(self._evidence_list):
            try:
                result = self._session_manager.compute_file_hash(Path(file_path))
                self._log_panel.log("INFO", f"Hash calculado: {Path(file_path).name} ({result.algorithm})")
            except Exception as exc:
                self._log_panel.log("ERROR", f"Erro ao calcular hash de {Path(file_path).name}: {exc}")
            self._status_bar.set_progress(int((i + 1) / len(self._evidence_list) * 100))
        self._status_bar.set_status("Hashes calculados")
        self._toast_manager.show_toast("Cálculo de hashes concluído", "SUCCESS")

    def _run_ocr(self) -> None:
        """Executa reconhecimento óptico de caracteres nas evidências."""
        self._log_panel.log("INFO", "OCR não implementado ainda")
        self._toast_manager.show_toast("OCR será implementado em breve", "INFO")

    def _run_verification(self) -> None:
        """Verifica a integridade de todas as evidências registradas."""
        if not self._evidence_list:
            self._log_panel.log("WARNING", "Nenhuma evidência para verificar")
            self._toast_manager.show_toast("Nenhuma evidência disponível", "WARNING")
            return
        self._log_panel.log("INFO", f"Verificando integridade de {len(self._evidence_list)} arquivo(s)...")
        self._status_bar.set_status("Verificando integridade...")
        all_ok = True
        for file_path in self._evidence_list:
            try:
                is_valid = self._session_manager.verify_integrity(Path(file_path))
                status = "OK" if is_valid else "ALTERADO"
                level = "INFO" if is_valid else "WARNING"
                self._log_panel.log(level, f"Verificação: {Path(file_path).name} — {status}")
                if not is_valid:
                    all_ok = False
            except Exception as exc:
                self._log_panel.log("ERROR", f"Erro na verificação de {Path(file_path).name}: {exc}")
                all_ok = False
        if all_ok:
            self._toast_manager.show_toast("Todas as evidências íntegras", "SUCCESS")
        else:
            self._toast_manager.show_toast("Algumas evidências foram alteradas", "WARNING")
        self._status_bar.set_status("Verificação concluída")

    def _generate_report(self) -> None:
        """Gera um relatório do caso atual."""
        self._log_panel.log("INFO", "Geração de relatório não implementada ainda")
        self._toast_manager.show_toast("Relatório será implementado em breve", "INFO")

    # ------------------------------------------------------------------ #
    # View Toggles
    # ------------------------------------------------------------------ #

    def _toggle_sidebar(self) -> None:
        """Alterna a visibilidade da barra lateral."""
        self._sidebar_visible = not self._sidebar_visible
        self._sidebar.setVisible(self._sidebar_visible)

    def _toggle_log_panel(self) -> None:
        """Alterna a visibilidade do painel de log."""
        self._log_panel_visible = not self._log_panel_visible
        self._log_dock.setVisible(self._log_panel_visible)

    # ------------------------------------------------------------------ #
    # Preferences
    # ------------------------------------------------------------------ #

    def _open_preferences(self) -> None:
        """Abre o diálogo de preferências."""
        self._log_panel.log("INFO", "Preferências abertas")

    # ------------------------------------------------------------------ #
    # About
    # ------------------------------------------------------------------ #

    def _show_about(self) -> None:
        """Exibe o diálogo Sobre."""
        QMessageBox.about(
            self,
            f"Sobre o {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            "<p>Sistema de Preservação Técnica de Evidências Digitais</p>"
            "<p>Ferramenta profissional para preservação, verificação "
            "e apresentação de evidências digitais em ambientes jurídicos.</p>"
            "<p>Licença: MIT</p>",
        )

    # ------------------------------------------------------------------ #
    # Public Accessors
    # ------------------------------------------------------------------ #

    @property
    def log_panel(self) -> LogPanelWidget:
        """Retorna o painel de log."""
        return self._log_panel

    @property
    def sidebar(self) -> SidebarWidget:
        """Retorna a barra lateral."""
        return self._sidebar

    @property
    def status_bar(self) -> StatusBarWidget:
        """Retorna a barra de status."""
        return self._status_bar

    @property
    def tab_widget(self) -> QTabWidget:
        """Retorna o widget de abas."""
        return self._tab_widget

    @property
    def evidence_list(self) -> list[str]:
        """Retorna a lista de evidências importadas."""
        return list(self._evidence_list)

    @property
    def properties_panel(self) -> PropertiesPanel:
        """Retorna o painel de propriedades."""
        return self._properties_panel
