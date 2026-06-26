from __future__ import annotations

import logging
import re
import unicodedata
from abc import ABC, abstractmethod
from pathlib import Path

from lexproof.models.message import WhatsAppMessage

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Erro durante o parsing de um arquivo de evidência."""


class BaseParser(ABC):
    """Classe base abstrata para parsers de evidências digitais.

    Fornece interface comum e métodos auxiliares para todos
    os parsers implementados no LexProof.
    """

    @abstractmethod
    def parse(self, file_path: Path) -> list[WhatsAppMessage]:
        """Extrai mensagens ou dados estruturados de um arquivo de evidência.

        Args:
            file_path: Caminho para o arquivo a ser processado.

        Returns:
            Lista de WhatsAppMessage extraídas do arquivo.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se ocorrer erro durante o parsing.
        """

    @abstractmethod
    def validate(self, file_path: Path) -> bool:
        """Verifica se o arquivo é válido para este parser.

        Args:
            file_path: Caminho para o arquivo a ser validado.

        Returns:
            True se o arquivo é válido, False caso contrário.
        """

    @staticmethod
    def clean_text(text: str) -> str:
        """Remove caracteres de controle e normaliza o texto.

        Remove bytes de BOM, normaliza Unicode NFC, e elimina
        caracteres de controle invisíveis preservando quebras de linha.

        Args:
            text: Texto de entrada.

        Returns:
            Texto limpo e normalizado.
        """
        text = text.strip()
        text = unicodedata.normalize("NFC", text)
        text = text.replace("\ufeff", "")
        cleaned_chars: list[str] = []
        for ch in text:
            cat = unicodedata.category(ch)
            if cat == "Cc" and ch not in ("\n", "\r", "\t"):
                continue
            cleaned_chars.append(ch)
        return "".join(cleaned_chars).strip()

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normaliza espaços em branco, preservando quebras de linha.

        Substitui múltiplos espaços por um único espaço e remove
        espaços nas bordas de cada linha.

        Args:
            text: Texto de entrada.

        Returns:
            Texto com espaços normalizados.
        """
        lines = text.split("\n")
        normalized: list[str] = []
        for line in lines:
            line = re.sub(r"[^\S\n]+", " ", line).strip()
            normalized.append(line)
        return "\n".join(normalized)

    def _read_file_with_encoding_detection(self, file_path: Path) -> str:
        """Lê o conteúdo de um arquivo, tentando múltiplas codificações.

        Tenta UTF-8, Latin-1 e CP1252 na ordem de prioridade.

        Args:
            file_path: Caminho para o arquivo.

        Returns:
            Conteúdo do arquivo como string.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se nenhuma codificação for válida.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        encodings = ["utf-8", "latin-1", "cp1252"]
        for encoding in encodings:
            try:
                content = file_path.read_text(encoding=encoding)
                logger.debug(
                    "Arquivo %s lido com codificação %s", file_path.name, encoding
                )
                return content
            except (UnicodeDecodeError, UnicodeError):
                logger.debug("Codificação %s falhou para %s", encoding, file_path.name)
                continue

        raise ParseError(
            f"Não foi possível ler o arquivo {file_path.name} "
            f"com nenhuma das codificações suportadas: {encodings}"
        )
