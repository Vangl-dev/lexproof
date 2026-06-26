from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image

from lexproof.ocr.preprocessing import enhance_contrast, grayscale, resize

logger = logging.getLogger(__name__)


class BaseOCR(ABC):
    """Classe base abstrata para engines OCR.

    Fornece interface comum e pré-processamento de imagem para todos
    os engines OCR implementados no LexProof.
    """

    def __init__(self, max_image_width: int = 1920) -> None:
        """Inicializa o engine OCR base.

        Args:
            max_image_width: Largura máxima para redimensionamento de imagens.
        """
        self._max_image_width = max_image_width

    @abstractmethod
    def extract_text(self, image_path: Path) -> str:
        """Extrai texto completo de uma imagem.

        Args:
            image_path: Caminho para a imagem a ser processada.

        Returns:
            Texto extraído pela engine OCR.

        Raises:
            FileNotFoundError: Se o arquivo de imagem não existir.
            RuntimeError: Se ocorrer erro durante o processamento OCR.
        """

    @abstractmethod
    def extract_text_with_boxes(
        self, image_path: Path
    ) -> list[tuple[str, tuple[int, int, int, int], float]]:
        """Extrai texto com bounding boxes e confiança.

        Args:
            image_path: Caminho para a imagem a ser processada.

        Returns:
            Lista de tuplas contendo:
                - texto extraído
                - bounding box (x, y, largura, altura)
                - score de confiança (0.0 a 1.0)

        Raises:
            FileNotFoundError: Se o arquivo de imagem não existir.
            RuntimeError: Se ocorrer erro durante o processamento OCR.
        """

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Aplica pré-processamento comum na imagem antes do OCR.

        Realiza conversão para escala de cinza, redimensionamento
        e melhoria de contraste para melhorar a acurácia do OCR.

        Args:
            image: Imagem de entrada.

        Returns:
            Imagem pré-processada.
        """
        logger.debug(
            "Pré-processando imagem: %dx%d -> max_width=%d",
            image.width,
            image.height,
            self._max_image_width,
        )

        processed = grayscale(image)
        processed = resize(processed, self._max_image_width)
        processed = enhance_contrast(processed, factor=1.3)

        logger.debug("Imagem pré-processada: %dx%d", processed.width, processed.height)
        return processed

    def _load_image(self, image_path: Path) -> Image.Image:
        """Carrega e valida a imagem do disco.

        Args:
            image_path: Caminho para a imagem.

        Returns:
            Imagem carregada.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            RuntimeError: Se não for possível abrir a imagem.
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

        try:
            image = Image.open(image_path)
            image.load()
            return image
        except Exception as e:
            raise RuntimeError(f"Erro ao abrir imagem {image_path}: {e}") from e
