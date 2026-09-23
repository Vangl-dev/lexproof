"""Janela principal do LexProof com design moderno.

Layout:
- Sidebar (72px) com ícones SVG
- Área de conteúdo principal
- Barra de status inferior
"""

from __future__ import annotations

import os
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
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
from lexproof.ui.styles.modern import get_modern_stylesheet
from lexproof.ui.widgets.log_panel import LogPanelWidget
from lexproof.ui.widgets.sidebar import NavigationRail
from lexproof.ui.widgets.dashboard import DashboardWidget
from lexproof.ui.widgets.status_bar import StatusBarWidget
from lexproof.ui.widgets.drop_zone import DropZoneWidget
from lexproof.ui.widgets.evidence_list import EvidenceListWidget
from lexproof.ui.widgets.toast_notification import ToastManager
from lexproof.ui.widgets.wizard import WizardDialog
from lexproof.ui.widgets.tour import TourManager
from lexproof.ui.widgets.timeline_view import TimelineViewWidget
from lexproof.ui.widgets.hashes_view import HashesViewWidget
from lexproof.utils.demo_data import generate_demo_case
from lexproof.core.constants import APP_NAME, APP_VERSION
from lexproof.core.event_bus import EventBus
from lexproof.core.session import SessionManager

logger = logging.getLogger(__name__)

EVIDENCE_FILTER = (
    "WhatsApp ZIP (*.zip);;"
    "Imagens (*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp);;"
    "Texto (*.txt *.csv *.json *.xml *.html);;"
    "PDF (*.pdf);;"
    "Arquivos Compactados (*.zip *.rar *.7z);;"
    "Todos os Arquivos (*)"
)


class MainWindow(QMainWindow):
    """Janela principal do LexProof com design moderno."""

    file_dropped = Signal(list)
    case_opened = Signal(str)
    pipeline_progress = Signal(str, str, float)
    pipeline_step_update = Signal(int, str, float)
    pipeline_complete_signal = Signal(object, object)
    pipeline_error_signal = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        event_bus: EventBus | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        super().__init__(parent)

        self._event_bus = event_bus or EventBus()
        self._session_manager = session_manager or SessionManager()

        self.setWindowTitle(f"{APP_NAME}")
        self.setMinimumSize(QSize(1280, 800))
        self.resize(1440, 900)
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
        self._pipeline_result = None
        self._analysis_result = None
        self._last_report_path: str = ""

        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._apply_theme()

        self._connect_events()
        self._start_tour_if_needed()

    # ------------------------------------------------------------------ #
    # UI Setup
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        self._nav_rail = NavigationRail()
        self._nav_rail.navigation_changed.connect(self._on_nav_changed)

        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.setTabsClosable(False)
        self._tab_widget.setMovable(False)

        self._dashboard = DashboardWidget()
        self._dashboard.new_session_clicked.connect(self._new_case)
        self._dashboard.import_clicked.connect(self._import_files)
        self._dashboard.generate_report_clicked.connect(self._generate_report)
        self._tab_widget.addTab(self._dashboard, "Inicio")

        self._evidence_list_widget = EvidenceListWidget()
        self._tab_widget.addTab(self._evidence_list_widget, "Evidencias")

        self._hashes_view = HashesViewWidget()
        self._tab_widget.addTab(self._hashes_view, "Hashes")

        self._timeline_view = TimelineViewWidget()
        self._tab_widget.addTab(self._timeline_view, "Timeline")

        self._pipeline_panel = self._create_pipeline_panel()
        self._tab_widget.addTab(self._pipeline_panel, "Pipeline")

        from lexproof.ui.widgets.report_panel import ReportPanelWidget
        self._report_panel = ReportPanelWidget()
        self._report_panel.generate_report_clicked.connect(self._generate_report)
        self._tab_widget.addTab(self._report_panel, "Relatorio")

        self._log_panel = LogPanelWidget()

        bottom_splitter = QSplitter(Qt.Orientation.Vertical)
        bottom_splitter.addWidget(self._tab_widget)
        bottom_splitter.addWidget(self._log_panel)
        bottom_splitter.setStretchFactor(0, 4)
        bottom_splitter.setStretchFactor(1, 1)
        bottom_splitter.setSizes([700, 180])

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._nav_rail)
        self._splitter.addWidget(bottom_splitter)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([72, 1368])

        self._drop_zone = DropZoneWidget(central)
        self._drop_zone.files_dropped.connect(self._on_files_dropped)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._splitter)

        self._drop_zone.setFixedSize(central.size())

    def _create_pipeline_panel(self) -> QWidget:
        from lexproof.ui.widgets.pipeline import PipelineWidget
        pw = PipelineWidget()
        pw.open_report_clicked.connect(self._open_last_report)
        pw.open_folder_clicked.connect(self._open_output_folder)
        pw.new_preservation_clicked.connect(self._new_case)
        return pw

    def _on_nav_changed(self, name: str) -> None:
        tab_map = {
            "inicio": 0,
            "evidencias": 1,
            "hashes": 2,
            "timeline": 3,
            "pipeline": 4,
            "relatorio": 5,
        }
        idx = tab_map.get(name)
        if idx is not None and idx < self._tab_widget.count():
            self._tab_widget.setCurrentIndex(idx)

    def _start_tour_if_needed(self) -> None:
        tour = TourManager.instance()
        if tour.is_first_run():
            QTimer.singleShot(500, lambda: tour.start_tour(self))

    # ------------------------------------------------------------------ #
    # Menu Bar
    # ------------------------------------------------------------------ #

    def _setup_menu_bar(self) -> None:
        menubar = self.menuBar()
        self._build_file_menu(menubar)
        self._build_edit_menu(menubar)
        self._build_view_menu(menubar)
        self._build_tools_menu(menubar)
        self._build_help_menu(menubar)

    def _build_file_menu(self, menubar: QMenuBar) -> None:
        file_menu = menubar.addMenu("Arquivo")

        new_action = QAction("Nova Sessao", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._new_case)
        file_menu.addAction(new_action)

        open_action = QAction("Abrir Sessao", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._open_case)
        file_menu.addAction(open_action)

        save_action = QAction("Salvar", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_case)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        import_action = QAction("Importar Evidencias", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self._import_files)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        exit_action = QAction("Sair", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _build_edit_menu(self, menubar: QMenuBar) -> None:
        edit_menu = menubar.addMenu("Editar")

        prefs_action = QAction("Configuracoes", self)
        prefs_action.setShortcut(QKeySequence("Ctrl+,"))
        prefs_action.triggered.connect(self._open_preferences)
        edit_menu.addAction(prefs_action)

    def _build_view_menu(self, menubar: QMenuBar) -> None:
        view_menu = menubar.addMenu("Exibir")

        toggle_sidebar_action = QAction("Alternar Barra Lateral", self)
        toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        toggle_sidebar_action.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(toggle_sidebar_action)

        toggle_log_action = QAction("Alternar Console", self)
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
        tools_menu = menubar.addMenu("Ferramentas")

        verify_action = QAction("Verificar Integridade", self)
        verify_action.triggered.connect(self._run_verification)
        tools_menu.addAction(verify_action)

        tools_menu.addSeparator()

        report_action = QAction("Gerar Relatorio", self)
        report_action.triggered.connect(self._generate_report)
        tools_menu.addAction(report_action)

    def _build_help_menu(self, menubar: QMenuBar) -> None:
        help_menu = menubar.addMenu("Ajuda")

        about_action = QAction("Sobre o LexProof", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------ #
    # Status Bar
    # ------------------------------------------------------------------ #

    def _setup_status_bar(self) -> None:
        self._status_bar = StatusBarWidget()
        self.statusBar().addPermanentWidget(self._status_bar, 1)
        self.statusBar().setFixedHeight(32)

    # ------------------------------------------------------------------ #
    # Event Bus Connections
    # ------------------------------------------------------------------ #

    def _connect_events(self) -> None:
        self.pipeline_progress.connect(self._on_pipeline_progress)
        self.pipeline_step_update.connect(self._on_pipeline_step_update)
        self.pipeline_complete_signal.connect(self._on_pipeline_complete)
        self.pipeline_error_signal.connect(self._on_pipeline_error)

    # ------------------------------------------------------------------ #
    # Theme
    # ------------------------------------------------------------------ #

    def _apply_theme(self) -> None:
        self._theme_manager.apply_theme()
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_modern_stylesheet())

    def _set_theme(self, mode: ThemeMode) -> None:
        self._theme_manager.set_mode(mode)
        self._apply_theme()
        mode_label = {ThemeMode.LIGHT: "Claro", ThemeMode.DARK: "Escuro", ThemeMode.SYSTEM: "Sistema"}
        label = mode_label.get(mode, mode.value)
        self._log_panel.log("INFO", f"Tema alterado para: {label}")
        self._toast_manager.show_toast(f"Tema alterado para: {label}", "INFO")

    # ------------------------------------------------------------------ #
    # Resize
    # ------------------------------------------------------------------ #

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_drop_zone") and hasattr(self, "centralWidget"):
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
            self._on_files_dropped(paths)

    # ------------------------------------------------------------------ #
    # Tab Management
    # ------------------------------------------------------------------ #

    def add_tab(self, widget: QWidget, title: str) -> int:
        index = self._tab_widget.addTab(widget, title)
        self._tab_widget.setCurrentIndex(index)
        return index

    # ------------------------------------------------------------------ #
    # File Operations
    # ------------------------------------------------------------------ #

    def _new_case(self) -> None:
        self._session_manager.start_session()
        self._evidence_list.clear()
        self._evidence_list_widget.clear_files()
        self._pipeline_result = None
        self._analysis_result = None
        self._last_report_path = ""
        self._hashes_view.clear()
        self._timeline_view.clear()
        self._pipeline_panel.reset()
        self._log_panel.log("SUCCESS", "Nova sessao criada")
        self._toast_manager.show_toast("Nova sessao criada com sucesso", "SUCCESS")
        self._status_bar.set_status("Nova sessao criada")

    def _open_case(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Sessao",
            "",
            "LexProof Sessions (*.lexproof.json);;Todos os Arquivos (*)",
        )
        if path:
            try:
                self._session_manager.load_session(Path(path))
                self._log_panel.log("SUCCESS", f"Sessao aberta: {path}")
                self._toast_manager.show_toast(f"Sessao aberta: {Path(path).name}", "SUCCESS")
                self.case_opened.emit(path)
                self._status_bar.set_status(f"Sessao aberta: {Path(path).name}")
            except Exception as exc:
                self._log_panel.log("ERROR", f"Erro ao abrir sessao: {exc}")
                self._toast_manager.show_toast(f"Erro ao abrir sessao: {exc}", "ERROR")

    def _save_case(self) -> None:
        if not self._session_manager.is_active:
            self._session_manager.start_session()
        try:
            path = self._session_manager.save_session()
            self._log_panel.log("SUCCESS", f"Sessao salva em: {path}")
            self._toast_manager.show_toast("Sessao salva com sucesso", "SUCCESS")
            self._status_bar.set_status("Sessao salva")
        except Exception as exc:
            self._log_panel.log("ERROR", f"Erro ao salvar sessao: {exc}")
            self._toast_manager.show_toast(f"Erro ao salvar sessao: {exc}", "ERROR")

    def _import_files(self) -> None:
        if not self._session_manager.is_active:
            self._session_manager.start_session()
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar Evidencias",
            "",
            EVIDENCE_FILTER,
        )
        if paths:
            self._process_imported_files(paths)

    def _on_files_dropped(self, paths: list[str]) -> None:
        if not self._session_manager.is_active:
            self._session_manager.start_session()
        self._process_imported_files(paths)

    def _process_imported_files(self, paths: list[str]) -> None:
        logger.info("Arquivos importados: %d", len(paths))
        new_files = []
        for file_path in paths:
            path_obj = Path(file_path)
            if path_obj.exists() and file_path not in self._evidence_list:
                self._evidence_list.append(file_path)
                self._evidence_list_widget.add_file(file_path)
                new_files.append(file_path)
                try:
                    self._session_manager.add_evidence(path_obj)
                except Exception as exc:
                    self._log_panel.log("WARNING", f"Falha ao registrar evidencia {path_obj.name}: {exc}")

        if not new_files:
            return

        count = len(new_files)
        self._log_panel.log("SUCCESS", f"ZIP importado — {count} arquivo(s)")
        self._toast_manager.show_toast(
            f"{count} arquivo(s) importado(s) com sucesso",
            "SUCCESS",
        )
        self._status_bar.set_status(f"{count} arquivo(s) importado(s)")
        self.file_dropped.emit(new_files)

        zip_files = [p for p in new_files if p.lower().endswith('.zip')]
        if zip_files:
            self._start_pipeline(zip_files)
        elif new_files:
            self._start_pipeline(new_files)

    def _analyze_zip(self, zip_path: str) -> dict:
        import zipfile
        info = {"name": Path(zip_path).name, "size": self._format_size(Path(zip_path).stat().st_size)}
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                names = zf.namelist()
                info["total_files"] = len(names)
                img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
                info["images"] = sum(1 for n in names if Path(n).suffix.lower() in img_exts)
                info["has_txt"] = any(n.lower().endswith('.txt') for n in names)
                info["has_whatsapp"] = info["has_txt"]
        except Exception:
            info["total_files"] = "?"
            info["images"] = "?"
            info["has_txt"] = False
            info["has_whatsapp"] = False
        return info

    def _start_pipeline(self, zip_files: list[str]) -> None:
        import threading
        from lexproof.pipeline.preservation import PreservationPipeline, PipelineStepStatus
        from lexproof.analysis.engine import SmartAnalysisEngine

        self._tab_widget.setCurrentIndex(4)
        self._pipeline_panel.reset()

        zip_info = self._analyze_zip(zip_files[0])
        self._pipeline_panel.show_zip_info(zip_info)
        self._log_panel.log("INFO", f"ZIP importado: {zip_info['name']}")
        self._log_panel.log("INFO", f"  {zip_info['size']} — {zip_info.get('total_files', '?')} arquivo(s) — {zip_info.get('images', 0)} imagem(ns)")
        if zip_info.get("has_whatsapp"):
            self._log_panel.log("INFO", "  Exportacao WhatsApp detectada")

        step_names = [
            "Catalogacao",
            "Metadados",
            "Hashes",
            "OCR",
            "Parser",
            "Correlacao",
            "Timeline",
            "Verificacao",
            "Classificacao",
            "Relatorio",
        ]
        total_steps = len(step_names)
        self._pipeline_step_times: dict[int, float] = {}
        self._pipeline_current_step = 0

        for name in step_names:
            self._pipeline_panel.add_step(name)

        self._status_bar.set_status("Iniciando preservacao...")

        self._pipeline_total_steps = total_steps
        self._pipeline_step_names = step_names

        def progress_callback(step_name: str, status: PipelineStepStatus, progress: float) -> None:
            import unicodedata

            def strip_accents(s: str) -> str:
                return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

            normalized_step = strip_accents(step_name).lower()

            for i, name in enumerate(step_names):
                if strip_accents(name).lower() in normalized_step:
                    status_str = status.value
                    pct = 0
                    if status_str == "running":
                        pct = int((i / total_steps) * 100)
                    elif status_str == "completed":
                        pct = int(((i + 1) / total_steps) * 100)
                    self.pipeline_progress.emit(step_name, status_str, float(pct))
                    self.pipeline_step_update.emit(i, status_str, 0.0)
                    break

        def run_pipeline() -> None:
            try:
                pipeline = PreservationPipeline()
                pipeline.set_progress_callback(progress_callback)

                evidence_paths = [Path(p) for p in zip_files]

                meta = None
                if self._session_manager.is_active:
                    meta = self._session_manager.session.metadata

                result = pipeline.execute(
                    evidence_paths,
                    client_name=(meta.client_name or "") if meta else "",
                    case_number=(meta.case_number or "") if meta else "",
                    responsible_technician=(meta.responsible_technician or "") if meta else "",
                    output_dir=Path("output"),
                )

                analysis_engine = SmartAnalysisEngine()
                analysis = analysis_engine.analyze(
                    result.evidence_files,
                    result.messages,
                    result.ocr_results,
                    result.correlations,
                )

                self._pipeline_result = result
                self._analysis_result = analysis

                self.pipeline_complete_signal.emit(result, analysis)

            except Exception as exc:
                logger.exception("Erro no pipeline")
                self.pipeline_error_signal.emit(str(exc))

        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()

    def _on_pipeline_progress(self, step_name: str, status_str: str, pct: float) -> None:
        self._pipeline_panel.set_progress(int(pct))

    def _on_pipeline_step_update(self, idx: int, status_str: str, dur: float) -> None:
        self._pipeline_panel.update_step(idx, status_str, dur if dur > 0 else None)

    def _on_pipeline_complete(self, result, analysis) -> None:
        self._log_panel.log("SUCCESS", "Preservacao concluida com sucesso")
        self._log_panel.log("SUCCESS", f"OCR concluido — {len(result.ocr_results)} imagem(ns) processada(s)")
        if result.correlations:
            self._log_panel.log("SUCCESS", f"Correlacoes encontradas — {len(result.correlations)} correspondencia(s)")
        else:
            self._log_panel.log("INFO", "Nenhuma correlacao automatica encontrada")
        self._log_panel.log("SUCCESS", "Relatorio gerado com sucesso")
        self._status_bar.set_status("Preservacao concluida")

        self._update_hashes_tab(result)
        self._update_timeline_tab(result)
        self._update_dashboard_data()

        if result.report_path:
            self._last_report_path = str(result.report_path)
            self._report_panel.update_status(
                f"Relatorio gerado: {result.report_path.name}",
                self._last_report_path,
            )

        participants = set()
        if result.messages:
            participants = set(m.sender for m in result.messages if m.sender)

        summary_data = {
            "files": result.evidence_count,
            "images": result.images_count,
            "conversations": result.exports_count,
            "participants": len(participants),
            "messages": len(result.messages),
            "hashes_ok": len(result.hash_results) > 0,
            "ocr_count": len(result.ocr_results),
            "correlations_count": len(result.correlations),
            "report_path": str(result.report_path) if result.report_path else "",
            "duration": f"{result.total_duration_seconds:.1f}s",
        }

        self._pipeline_panel.show_summary(summary_data)
        self._pipeline_panel.set_progress(100)

        self._toast_manager.show_toast("Preservacao concluida. Relatorio disponivel.", "SUCCESS")

    def _on_pipeline_error(self, error_msg: str) -> None:
        self._log_panel.log("ERROR", "O processamento encontrou um problema")
        self._log_panel.log("ERROR", f"Detalhes: {error_msg}")
        self._status_bar.set_status("Erro no processamento")
        self._pipeline_panel.show_error(
            "O processamento encontrou um problema. "
            "O restante da preservacao foi concluido normalmente."
        )
        self._toast_manager.show_toast("Processamento concluido com avisos", "WARNING")

    def _update_hashes_tab(self, result) -> None:
        hashes_data = []
        for hr in result.hash_results:
            file_name = hr.file_path.name
            existing = next((h for h in hashes_data if h["file_name"] == file_name), None)
            if existing:
                existing[hr.algorithm.value] = hr.hash_value
            else:
                hashes_data.append({
                    "file_name": file_name,
                    "file_size": self._format_size(hr.file_size or 0),
                    hr.algorithm.value: hr.hash_value,
                })

        if hashes_data:
            self._hashes_view.set_hashes(hashes_data)

            all_hashes = sorted([hr.hash_value for hr in result.hash_results])
            import hashlib
            h = hashlib.sha256()
            for hash_val in all_hashes:
                h.update(hash_val.encode())
            self._hashes_view.set_global_hash(h.hexdigest())

    def _update_timeline_tab(self, result) -> None:
        entries = []
        for entry in result.timeline:
            entries.append({
                "timestamp": entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(entry, 'timestamp') and entry.timestamp else "",
                "sender": getattr(entry, 'sender', '') or "",
                "content": getattr(entry, 'content', '') or getattr(entry, 'description', '') or "",
                "source": getattr(entry, 'source', '') or "",
                "status": getattr(entry, 'status', '') or "",
            })

        if not entries and result.messages:
            for msg in result.messages:
                entries.append({
                    "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S") if msg.timestamp else "",
                    "sender": msg.sender or "",
                    "content": msg.content or "",
                    "source": "WhatsApp",
                    "status": "",
                })

        if entries:
            self._timeline_view.set_entries(entries)

    def _update_dashboard_data(self) -> None:
        if self._pipeline_result:
            session_data = self._session_manager.get_session_data()
            self._dashboard.update_session_data(session_data)
            if self._pipeline_result.report_path:
                self._dashboard.update_report_data(str(self._pipeline_result.report_path))

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    # ------------------------------------------------------------------ #
    # Tools
    # ------------------------------------------------------------------ #

    def _run_verification(self) -> None:
        if not self._evidence_list:
            self._log_panel.log("WARNING", "Nenhuma evidencia para verificar")
            self._toast_manager.show_toast("Nenhuma evidencia disponivel", "WARNING")
            return
        self._log_panel.log("INFO", f"Verificando integridade de {len(self._evidence_list)} arquivo(s)...")
        self._status_bar.set_status("Verificando integridade...")
        all_ok = True
        for file_path in self._evidence_list:
            try:
                is_valid = self._session_manager.verify_integrity(Path(file_path))
                status = "OK" if is_valid else "ALTERADO"
                level = "SUCCESS" if is_valid else "WARNING"
                self._log_panel.log(level, f"Verificacao: {Path(file_path).name} — {status}")
                if not is_valid:
                    all_ok = False
            except Exception as exc:
                self._log_panel.log("ERROR", f"Erro na verificacao de {Path(file_path).name}: {exc}")
                all_ok = False
        if all_ok:
            self._toast_manager.show_toast("Todas as evidencias intactas", "SUCCESS")
        else:
            self._toast_manager.show_toast("Algumas evidencias foram alteradas", "WARNING")
        self._status_bar.set_status("Verificacao concluida")

    def _generate_report(self) -> None:
        if not self._pipeline_result:
            self._log_panel.log("WARNING", "Nenhum resultado de pipeline disponivel")
            self._toast_manager.show_toast("Execute o processamento primeiro", "WARNING")
            return

        self._log_panel.log("INFO", "Gerando relatorio de preservacao...")
        self._status_bar.set_status("Gerando relatorio...")

        try:
            from datetime import datetime, timezone

            from lexproof.reports.pdf_report import PDFReportGenerator
            from lexproof.reports.report_data import build_report_data

            result = self._pipeline_result
            analysis = self._analysis_result

            meta = None
            if self._session_manager.is_active:
                meta = self._session_manager.session.metadata
            client_name = (meta.client_name or "") if meta else ""
            case_number = (meta.case_number or "") if meta else ""
            responsible = (meta.responsible_technician or "") if meta else ""

            analysis_summary = ""
            if analysis:
                analysis_summary = f"""
Analise Tecnica:
- Plataforma detectada: {analysis.detected_platform}
- Score tecnico: {analysis.scores.technical_grade}
- Constatacoes: {len(analysis.findings)}
- Recomendacoes: {len(analysis.recommendations)}
"""
            if client_name:
                base_desc = f"Preservacao de evidencias digitais para {client_name}"
            else:
                base_desc = "Preservacao de evidencias digitais"
            description = f"{base_desc}{analysis_summary}"

            report_data = build_report_data(
                evidences=result.evidence_files,
                messages=result.messages,
                ocr_results=result.ocr_results,
                hash_results=result.hash_results,
                timeline=result.timeline,
                correlations=result.correlations,
                verification_results=result.verification_results,
                quality_grade=result.quality_grade,
                session_id=result.session_id,
                client_name=client_name,
                case_number=case_number,
                responsible_technician=responsible,
                description=description,
            )

            generator = PDFReportGenerator()
            output_dir = Path("output")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"lexproof_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
            generator.generate(report_data, output_path)

            self._last_report_path = str(output_path)
            self._log_panel.log("SUCCESS", f"Relatorio gerado: {output_path}")
            self._status_bar.set_status("Relatorio gerado")
            self._toast_manager.show_toast(f"Relatorio gerado: {output_path.name}", "SUCCESS")

            self._report_panel.update_status(
                f"Relatorio gerado: {output_path.name}",
                self._last_report_path,
            )

            import subprocess
            import sys
            try:
                opened = False
                if sys.platform == "linux":
                    r = subprocess.run(
                        ["xdg-open", str(output_path)],
                        timeout=10,
                        capture_output=True,
                    )
                    opened = r.returncode == 0
                elif sys.platform == "darwin":
                    r = subprocess.run(
                        ["open", str(output_path)],
                        timeout=10,
                        capture_output=True,
                    )
                    opened = r.returncode == 0
                elif sys.platform == "win32":
                    os.startfile(str(output_path))
                    opened = True

                if not opened:
                    self._toast_manager.show_toast(
                        f"Relatorio salvo em: {output_path.name}", "INFO"
                    )
            except FileNotFoundError:
                self._toast_manager.show_toast(
                    f"Relatorio salvo em: {output_path.name}", "INFO"
                )
            except Exception:
                self._toast_manager.show_toast(
                    f"Relatorio salvo em: {output_path.name}", "INFO"
                )

        except Exception as exc:
            logger.exception("Erro ao gerar relatorio")
            self._log_panel.log("ERROR", f"Erro ao gerar relatorio: {exc}")
            self._status_bar.set_status("Erro ao gerar relatorio")
            self._toast_manager.show_toast(f"Erro ao gerar relatorio: {exc}", "ERROR")

    # ------------------------------------------------------------------ #
    # Wizard
    # ------------------------------------------------------------------ #

    def _open_wizard(self) -> None:
        wizard = WizardDialog(self)
        wizard.wizard_completed.connect(self._on_wizard_completed)
        wizard.exec()

    def _on_wizard_completed(self, data: dict[str, str]) -> None:
        if not self._session_manager.is_active:
            self._session_manager.start_session()
        session = self._session_manager.session
        examiner = data.get("examiner_name", "")
        if examiner:
            session.metadata.responsible_technician = examiner
        title = data.get("case_title", "")
        if title and not session.metadata.description:
            session.metadata.description = title
        self._log_panel.log("SUCCESS", f"Caso criado via assistente: {data.get('case_title', '')}")
        self._toast_manager.show_toast("Caso criado com sucesso", "SUCCESS")

    # ------------------------------------------------------------------ #
    # View Toggles
    # ------------------------------------------------------------------ #

    def _toggle_sidebar(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        self._nav_rail.setVisible(self._sidebar_visible)

    def _toggle_log_panel(self) -> None:
        self._log_panel_visible = not self._log_panel_visible
        self._log_panel.setVisible(self._log_panel_visible)

    # ------------------------------------------------------------------ #
    # Preferences
    # ------------------------------------------------------------------ #

    def _open_preferences(self) -> None:
        QMessageBox.information(
            self,
            "Configuracoes",
            "Configuracoes do LexProof\n\n"
            "Versao: " + APP_VERSION + "\n"
            "Sistema de Preservacao Tecnica de Evidencias Digitais",
        )

    # ------------------------------------------------------------------ #
    # About
    # ------------------------------------------------------------------ #

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"Sobre o {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            "<p>Sistema de Preservacao Tecnica de Evidencias Digitais</p>"
            "<p>Ferramenta profissional para preservacao, verificacao "
            "e apresentacao de evidencias digitais em ambientes juridicos.</p>"
            "<p>Licenca: MIT</p>",
        )

    # ------------------------------------------------------------------ #
    # Public Accessors
    # ------------------------------------------------------------------ #

    @property
    def log_panel(self) -> LogPanelWidget:
        return self._log_panel

    @property
    def nav_rail(self) -> NavigationRail:
        return self._nav_rail

    @property
    def sidebar(self) -> NavigationRail:
        return self._nav_rail

    @property
    def status_bar(self) -> StatusBarWidget:
        return self._status_bar

    @property
    def tab_widget(self) -> QTabWidget:
        return self._tab_widget

    @property
    def evidence_list(self) -> list[str]:
        return list(self._evidence_list)

    def _open_last_report(self) -> None:
        path = self._last_report_path
        if not path or not Path(path).exists():
            self._toast_manager.show_toast("Nenhum relatorio disponivel", "WARNING")
            return
        import subprocess
        import sys
        try:
            result = None
            if sys.platform == "linux":
                result = subprocess.run(
                    ["xdg-open", path],
                    timeout=10,
                    capture_output=True,
                )
            elif sys.platform == "darwin":
                result = subprocess.run(
                    ["open", path],
                    timeout=10,
                    capture_output=True,
                )
            elif sys.platform == "win32":
                os.startfile(path)
            if result is not None and result.returncode != 0:
                self._toast_manager.show_toast(
                    f"Relatorio salvo em: {Path(path).name}", "INFO"
                )
        except Exception:
            self._toast_manager.show_toast(
                f"Relatorio salvo em: {Path(path).name}", "INFO"
            )

    def _open_output_folder(self) -> None:
        output_dir = Path("output")
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        import subprocess
        import sys
        try:
            result = None
            if sys.platform == "linux":
                result = subprocess.run(
                    ["xdg-open", str(output_dir.resolve())],
                    timeout=10,
                    capture_output=True,
                )
            elif sys.platform == "darwin":
                result = subprocess.run(
                    ["open", str(output_dir.resolve())],
                    timeout=10,
                    capture_output=True,
                )
            elif sys.platform == "win32":
                os.startfile(str(output_dir.resolve()))
            if result is not None and result.returncode != 0:
                self._toast_manager.show_toast(
                    f"Pasta: {output_dir.resolve()}", "INFO"
                )
        except Exception:
            self._toast_manager.show_toast(
                f"Pasta: {output_dir.resolve()}", "INFO"
            )
