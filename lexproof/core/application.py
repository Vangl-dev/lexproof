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

        self._main_window: Optional[QMainWindow] = None
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

    def _create_simple_window(self) -> None:
        """Cria a janela simplificada (padrao)."""
        from lexproof.ui.simple_window import SimpleMainWindow, apply_light_theme

        apply_light_theme(self._qapp)
        self._main_window = SimpleMainWindow()
        self._main_window.show()

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
