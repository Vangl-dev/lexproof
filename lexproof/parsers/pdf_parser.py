from __future__ import annotations

import logging
from pathlib import Path

from lexproof.models.evidence import EvidenceFile, EvidenceType
from lexproof.models.message import WhatsAppMessage
from lexproof.parsers.base import BaseParser, ParseError

logger = logging.getLogger(__name__)

_PDF_EXTENSION = ".pdf"


class PDFParser(BaseParser):
    """Parser para arquivos PDF.

    Extrai conteúdo de texto, metadados e cria modelos EvidenceFile.
    """

    def __init__(self) -> None:
        """Inicializa o parser PDF."""
        self._pdf_reader = None

    def parse(self, file_path: Path) -> list[WhatsAppMessage]:
        """Extrai dados de um PDF (não retorna mensagens WhatsApp).

        Para PDFs, o método principal de extração é `parse_pdf()` que
        retorna um EvidenceFile. Este método retorna lista vazia por
        compatibilidade com a interface BaseParser.

        Args:
            file_path: Caminho para o arquivo PDF.

        Returns:
            Lista vazia (PDFs não geram WhatsAppMessage diretamente).

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se o parsing falhar.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if not self.validate(file_path):
            raise ParseError(f"Arquivo inválido como PDF: {file_path.name}")

        return []

    def parse_pdf(self, file_path: Path) -> EvidenceFile:
        """Extrai metadados e informações de um PDF.

        Args:
            file_path: Caminho para o arquivo PDF.

        Returns:
            Modelo EvidenceFile com os metadados extraídos.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se o parsing falhar.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if not self.validate(file_path):
            raise ParseError(f"Formato PDF não suportado: {file_path.name}")

        file_size = file_path.stat().st_size
        metadata = self._extract_metadata(file_path)

        description_parts: list[str] = []
        if metadata.get("title"):
            description_parts.append(f"Título: {metadata['title']}")
        if metadata.get("author"):
            description_parts.append(f"Autor: {metadata['author']}")
        if metadata.get("page_count"):
            description_parts.append(f"Páginas: {metadata['page_count']}")

        description = "; ".join(description_parts) if description_parts else ""

        evidence = EvidenceFile(
            file_path=file_path,
            file_name=file_path.name,
            file_size=file_size,
            evidence_type=EvidenceType.DOCUMENT,
            description=description,
        )

        logger.info("PDF parseado: %s (%d bytes)", file_path.name, file_size)
        return evidence

    def extract_text(self, file_path: Path) -> str:
        """Extrai o conteúdo de texto completo de um PDF.

        Args:
            file_path: Caminho para o arquivo PDF.

        Returns:
            Texto extraído de todas as páginas.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se a extração falhar.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        try:
            import PyPDF2

            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)  # type: ignore[attr-defined]
                text_parts: list[str] = []
                for page in reader.pages:
                    page_text = page.extract_text()  # type: ignore[union-attr]
                    if page_text:
                        text_parts.append(page_text)
                full_text = "\n\n".join(text_parts)
                logger.info(
                    "Texto extraído de %s: %d caracteres",
                    file_path.name,
                    len(full_text),
                )
                return full_text
        except ImportError:
            logger.warning(
                "PyPDF2 não disponível, tentando extração básica de %s",
                file_path.name,
            )
            return self._fallback_extract_text(file_path)
        except Exception as e:
            logger.error("Erro ao extrair texto de %s: %s", file_path.name, e)
            raise ParseError(f"Erro na extração de texto: {e}") from e

    def _fallback_extract_text(self, file_path: Path) -> str:
        """Extrai texto usando apenas stdlib (método básico).

        Args:
            file_path: Caminho para o PDF.

        Returns:
            Texto parcial extraído, se possível.
        """
        try:
            raw = file_path.read_bytes()
            text_parts: list[str] = []
            start = 0
            while True:
                stream_start = raw.find(b"stream\r\n", start)
                if stream_start == -1:
                    stream_start = raw.find(b"stream\n", start)
                if stream_start == -1:
                    break
                stream_end = raw.find(b"endstream", stream_start)
                if stream_end == -1:
                    break
                stream_data = raw[stream_start:stream_end]
                for segment in stream_data.split(b"\n"):
                    try:
                        decoded = segment.decode("utf-8", errors="ignore")
                        if any(c.isalpha() for c in decoded):
                            text_parts.append(decoded.strip())
                    except Exception:
                        pass
                start = stream_end + 1
            return "\n".join(text_parts)
        except Exception:
            return ""

    def _extract_metadata(self, file_path: Path) -> dict[str, str | int]:
        """Extrai metadados do PDF.

        Args:
            file_path: Caminho para o arquivo PDF.

        Returns:
            Dicionário com metadados extraídos.
        """
        metadata: dict[str, str | int] = {}

        try:
            import PyPDF2

            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)  # type: ignore[attr-defined]
                if reader.metadata:  # type: ignore[union-attr]
                    info = reader.metadata  # type: ignore[union-attr]
                    if info.get("/Title"):
                        metadata["title"] = str(info["/Title"])
                    if info.get("/Author"):
                        metadata["author"] = str(info["/Author"])
                    if info.get("/Subject"):
                        metadata["subject"] = str(info["/Subject"])
                    if info.get("/Creator"):
                        metadata["creator"] = str(info["/Creator"])
                    if info.get("/Producer"):
                        metadata["producer"] = str(info["/Producer"])
                metadata["page_count"] = len(reader.pages)  # type: ignore[arg-type]
        except ImportError:
            logger.debug("PyPDF2 indisponível para metadados, usando fallback")
            metadata.update(self._fallback_extract_metadata(file_path))
        except Exception as e:
            logger.warning("Erro ao extrair metadados de %s: %s", file_path.name, e)

        return metadata

    def _fallback_extract_metadata(self, file_path: Path) -> dict[str, str | int]:
        """Extrai metadados básicos usando stdlib.

        Args:
            file_path: Caminho para o PDF.

        Returns:
            Dicionário com metadados básicos.
        """
        metadata: dict[str, str | int] = {}
        try:
            raw = file_path.read_bytes()
            page_count = raw.count(b"/Type /Page") - raw.count(b"/Type /Pages")
            if page_count > 0:
                metadata["page_count"] = page_count
        except Exception:
            pass
        return metadata

    def validate(self, file_path: Path) -> bool:
        """Verifica se o arquivo é um PDF válido.

        Args:
            file_path: Caminho para o arquivo.

        Returns:
            True se o arquivo existe, tem extensão .pdf e começa com %PDF.
        """
        if not file_path.exists():
            return False

        if file_path.suffix.lower() != _PDF_EXTENSION:
            return False

        try:
            with open(file_path, "rb") as f:
                header = f.read(5)
            return header == b"%PDF-"
        except Exception:
            return False
