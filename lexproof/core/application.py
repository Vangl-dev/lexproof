"""Aplicação principal do LexProof."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from lexproof.core.constants import (
    APP_AUTHOR,
    APP_NAME,
    APP_VERSION,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
)
from lexproof.core.event_bus import EventBus
from lexproof.core.session import SessionManager

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)


class LexProofApplication:
    """Classe principal que inicializa e executa o LexProof.

    Responsável por configurar o QApplication do PySide6,
    carregar estilos, e gerenciar o ciclo de vida da aplicação.
    """

    def __init__(self, argv: list[str]) -> None:
        """Inicializa a aplicação LexProof.

        Args:
            argv: Argumentos da linha de comando (sys.argv).
        """
        self._setup_logging()

        logger.info("Iniciando %s v%s", APP_NAME, APP_VERSION)

        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
        os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

        self._qapp: QApplication = QApplication(argv)
        self._qapp.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self._qapp.setApplicationName(APP_NAME)
        self._qapp.setApplicationVersion(APP_VERSION)
        self._qapp.setOrganizationName(APP_AUTHOR)

        self._event_bus: EventBus = EventBus()
        self._session_manager: SessionManager = SessionManager()

        # Interface antiga (abas e menus) so com --classico.
        self._classic_ui = "--classico" in argv

        self._main_window: Optional[QMainWindow] = None
        if self._classic_ui:
            self._load_stylesheet()
            self._create_main_window()
        else:
            self._create_simple_window()

    @property
    def event_bus(self) -> EventBus:
        """Retorna a instância do barramento de eventos."""
        return self._event_bus

    @property
    def session_manager(self) -> SessionManager:
        """Retorna o gerenciador de sessões."""
        return self._session_manager

    @property
    def qapp(self) -> QApplication:
        """Retorna a instância do QApplication."""
        return self._qapp

    def run(self) -> int:
        """Executa o loop principal da aplicação.

        Returns:
            Código de retorno do aplicativo (0 = sucesso).
        """
        logger.info("Loop principal iniciado")
        exit_code: int = self._qapp.exec()

        self._session_manager.close_session()
        logger.info("Aplicação encerrada com código %d", exit_code)
        return exit_code

    def _create_main_window(self) -> None:
        """Cria e exibe a janela principal."""
        try:
            from lexproof.ui.main_window import MainWindow

            self._main_window = MainWindow(
                event_bus=self._event_bus,
                session_manager=self._session_manager,
            )
            self._main_window.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
            self._main_window.show()
            logger.debug("Janela principal criada e exibida")
        except ImportError:
            logger.warning(
                "Módulo UI não disponível. A aplicação será executada sem interface gráfica."
            )

    def _create_simple_window(self) -> None:
        """Cria a janela simplificada (padrao)."""
        from lexproof.ui.simple_window import SimpleMainWindow, apply_light_theme

        apply_light_theme(self._qapp)
        self._main_window = SimpleMainWindow()
        self._main_window.show()

    def _load_stylesheet(self) -> None:
        """Carrega o stylesheet da aplicação."""
        try:
            from lexproof.ui.styles.theme import ThemeManager

            theme_manager = ThemeManager.instance()
            stylesheet = theme_manager.get_stylesheet()
            self._qapp.setStyleSheet(stylesheet)
            logger.debug("Stylesheet carregado via ThemeManager")
            return
        except Exception:
            logger.debug("ThemeManager indisponível, usando fallback baseado em arquivo")

        from lexproof.core.constants import STYLES_DIR

        theme = self._resolve_theme()
        stylesheet_path = STYLES_DIR / f"{theme}.qss"

        if stylesheet_path.exists():
            stylesheet = stylesheet_path.read_text(encoding="utf-8")
            self._qapp.setStyleSheet(stylesheet)
            logger.debug("Stylesheet carregado: %s", stylesheet_path)
        else:
            try:
                from lexproof.config.settings import Settings

                settings = Settings.get_instance()
                settings_theme = settings.theme
                fallback_path = STYLES_DIR / f"{settings_theme}.qss"
                if fallback_path.exists():
                    stylesheet = fallback_path.read_text(encoding="utf-8")
                    self._qapp.setStyleSheet(stylesheet)
                    logger.debug("Stylesheet fallback carregado: %s", fallback_path)
                else:
                    logger.debug("Nenhum stylesheet encontrado em %s", STYLES_DIR)
            except Exception:
                logger.debug("Nenhum stylesheet disponível")

    def _resolve_theme(self) -> str:
        """Resolve o tema ativo a partir das configurações.

        Returns:
            Nome do tema ('light', 'dark' ou 'system').
        """
        try:
            from lexproof.config.settings import Settings

            settings = Settings.get_instance()
            theme = settings.theme
            if theme == "system":
                return self._detect_system_theme()
            return theme
        except Exception:
            return "light"

    def _detect_system_theme(self) -> str:
        """Detecta o tema do sistema operacional.

        Returns:
            'dark' ou 'light' baseado na paleta do sistema.
        """
        from PySide6.QtGui import QPalette

        palette = self._qapp.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        brightness = (window_color.red() * 299 + window_color.green() * 587 + window_color.blue() * 114) / 1000
        return "dark" if brightness < 128 else "light"

    @staticmethod
    def _setup_logging() -> None:
        """Configura o sistema de logging da aplicação."""
        try:
            from lexproof.config.settings import Settings

            settings = Settings.get_instance()
            log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
            log_dir = settings.log_directory
        except Exception:
            log_level = logging.INFO
            log_dir = Path.home() / ".lexproof" / "logs"

        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "lexproof.log"

        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        root_logger.addHandler(console_handler)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        root_logger.addHandler(file_handler)

        logger.info("Logging configurado: nível=%s, arquivo=%s", logging.getLevelName(log_level), log_file)
