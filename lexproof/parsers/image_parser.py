from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image
from PIL.ExifTags import Base as ExifBase
from PIL.ExifTags import TAGS

from lexproof.models.evidence import EvidenceFile, EvidenceType
from lexproof.models.message import WhatsAppMessage
from lexproof.parsers.base import BaseParser, ParseError

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


class ImageParser(BaseParser):
    """Parser para arquivos de imagem (PNG, JPG, JPEG).

    Extrai metadados EXIF, texto via OCR e cria modelos EvidenceFile.
    """

    def __init__(self, enable_ocr: bool = True) -> None:
        """Inicializa o parser de imagem.

        Args:
            enable_ocr: Se True, tenta extrair texto via OCR.
        """
        self._enable_ocr = enable_ocr

    def parse(self, file_path: Path) -> list[WhatsAppMessage]:
        """Extrai dados de uma imagem (não retorna mensagens WhatsApp).

        Para imagens, o método principal de extração é `parse_image()` que
        retorna um EvidenceFile. Este método retorna lista vazia por
        compatibilidade com a interface BaseParser.

        Args:
            file_path: Caminho para o arquivo de imagem.

        Returns:
            Lista vazia (imagens não geram WhatsAppMessage diretamente).

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se o parsing falhar.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if not self.validate(file_path):
            raise ParseError(f"Arquivo inválido como imagem: {file_path.name}")

        return []

    def parse_image(self, file_path: Path) -> EvidenceFile:
        """Extrai metadados e informações de uma imagem.

        Args:
            file_path: Caminho para o arquivo de imagem.

        Returns:
            Modelo EvidenceFile com os metadados extraídos.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se o parsing falhar.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if not self.validate(file_path):
            raise ParseError(f"Formato de imagem não suportado: {file_path.suffix}")

        try:
            img = Image.open(file_path)
            img.load()
        except Exception as e:
            raise ParseError(f"Erro ao abrir imagem {file_path.name}: {e}") from e

        file_size = file_path.stat().st_size
        exif_data = self._extract_exif(img)

        description_parts: list[str] = []
        if exif_data:
            for key, value in exif_data.items():
                description_parts.append(f"{key}: {value}")

        description = "; ".join(description_parts) if description_parts else ""

        evidence = EvidenceFile(
            file_path=file_path,
            file_name=file_path.name,
            file_size=file_size,
            evidence_type=EvidenceType.IMAGE,
            description=description,
        )

        img.close()
        logger.info("Imagem parseada: %s (%d bytes)", file_path.name, file_size)
        return evidence

    def extract_text_ocr(self, file_path: Path) -> str:
        """Extrai texto de uma imagem via OCR.

        Importa懒ly o módulo OCR do LexProof para evitar
        carregamento desnecessário.

        Args:
            file_path: Caminho para a imagem.

        Returns:
            Texto extraído ou string vazia se OCR indisponível.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se o processamento OCR falhar.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if not self._enable_ocr:
            logger.debug("OCR desabilitado, ignorando %s", file_path.name)
            return ""

        try:
            from lexproof.ocr.processor import OCRProcessor

            processor = OCRProcessor()
            result = processor.process_image(file_path)
            logger.info(
                "OCR extraído de %s: %d caracteres",
                file_path.name,
                len(result.extracted_text),
            )
            return result.extracted_text
        except ImportError:
            logger.warning(
                "Módulo OCR não disponível, ignorando extração de %s",
                file_path.name,
            )
            return ""
        except Exception as e:
            logger.error("Erro no OCR de %s: %s", file_path.name, e)
            raise ParseError(f"Erro no OCR: {e}") from e

    def validate(self, file_path: Path) -> bool:
        """Verifica se o arquivo é uma imagem válida.

        Args:
            file_path: Caminho para o arquivo.

        Returns:
            True se o arquivo existe, é legível e tem extensão suportada.
        """
        if not file_path.exists():
            return False

        if file_path.suffix.lower() not in _IMAGE_EXTENSIONS:
            return False

        try:
            img = Image.open(file_path)
            img.load()
            img.close()
            return True
        except Exception:
            return False

    def _extract_exif(self, img: Image.Image) -> dict[str, str]:
        """Extrai metadados EXIF de uma imagem.

        Args:
            img: Imagem PIL aberta.

        Returns:
            Dicionário com pares chave-valor dos metadados EXIF.
        """
        exif_data: dict[str, str] = {}

        try:
            raw_exif = img.getexif()  # type: ignore[union-attr]
        except Exception:
            logger.debug("Nenhum dado EXIF encontrado")
            return exif_data

        if not raw_exif:
            return exif_data

        for tag_id, value in raw_exif.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", errors="replace")
                except Exception:
                    value = f"<bytes len={len(value)}>"
            exif_data[str(tag_name)] = str(value)

        return exif_data
