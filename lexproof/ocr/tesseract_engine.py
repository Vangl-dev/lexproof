from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from PIL import Image

from lexproof.ocr.base import BaseOCR

logger = logging.getLogger(__name__)


class TesseractOCR(BaseOCR):
    """Engine OCR baseado no Tesseract.

    Utiliza pytesseract para extração de texto de imagens.
    Suporta português e inglês com modos PSM configuráveis.
    """

    DEFAULT_LANGUAGES = "por+eng"

    def __init__(
        self,
        languages: str | None = None,
        psm_mode: int = 3,
        max_image_width: int = 1920,
    ) -> None:
        """Inicializa o engine Tesseract OCR.

        Args:
            languages: String de idiomas do Tesseract (ex: 'por+eng').
            psm_mode: Page Segmentation Mode do Tesseract.
                3 = Página inteira com layout automático (padrão).
                6 = Bloco de texto uniforme.
                11 = Texto sem orientação.
            max_image_width: Largura máxima para redimensionamento.

        Raises:
            ImportError: Se o pytesseract não estiver instalado.
        """
        super().__init__(max_image_width)
        self._languages = languages or self.DEFAULT_LANGUAGES
        self._psm_mode = psm_mode
        self._pytesseract = self._import_pytesseract()

    @staticmethod
    def _import_pytesseract() -> Any:
        """Importa pytesseract com tratamento de erro.

        Returns:
            Módulo pytesseract.

        Raises:
            ImportError: Se pytesseract não estiver instalado.
        """
        try:
            import pytesseract

            return pytesseract
        except ImportError:
            raise ImportError(
                "pytesseract não está instalado. "
                "Instale com: pip install pytesseract"
            )

    @property
    def languages(self) -> str:
        """Retorna os idiomas configurados."""
        return self._languages

    @property
    def psm_mode(self) -> int:
        """Retorna o modo PSM configurado."""
        return self._psm_mode

    def extract_text(self, image_path: Path) -> str:
        """Extrai texto completo de uma imagem usando Tesseract.

        Args:
            image_path: Caminho para a imagem.

        Returns:
            Texto completo extraído.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            RuntimeError: Se ocorrer erro no processamento.
        """
        logger.info("Extraindo texto (Tesseract) de: %s", image_path)
        start = time.monotonic()

        image = self._load_image(image_path)
        processed = self._preprocess_image(image)

        config = f"--psm {self._psm_mode}"

        try:
            text = self._pytesseract.image_to_string(
                processed, lang=self._languages, config=config
            )
        except Exception as e:
            raise RuntimeError(
                f"Erro no Tesseract ao processar {image_path}: {e}"
            ) from e

        elapsed = time.monotonic() - start
        logger.info(
            "Tesseract concluído em %.2fs, %d caracteres extraídos",
            elapsed,
            len(text),
        )
        return text

    def extract_text_with_boxes(
        self, image_path: Path
    ) -> list[tuple[str, tuple[int, int, int, int], float]]:
        """Extrai texto com bounding boxes e scores de confiança.

        Args:
            image_path: Caminho para a imagem.

        Returns:
            Lista de (texto, (x, y, largura, altura), confiança).

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            RuntimeError: Se ocorrer erro no processamento.
        """
        logger.info("Extraindo texto com boxes (Tesseract) de: %s", image_path)

        image = self._load_image(image_path)
        processed = self._preprocess_image(image)

        config = f"--psm {self._psm_mode}"

        try:
            data = self._pytesseract.image_to_data(
                processed,
                lang=self._languages,
                config=config,
                output_type=self._pytesseract.Output.DICT,
            )
        except Exception as e:
            raise RuntimeError(
                f"Erro no Tesseract ao extrair boxes de {image_path}: {e}"
            ) from e

        results: list[tuple[str, tuple[int, int, int, int], float]] = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf = float(data["conf"][i]) / 100.0

            if not text or conf <= 0:
                continue

            x = int(data["left"][i])
            y = int(data["top"][i])
            w = int(data["width"][i])
            h = int(data["height"][i])

            results.append((text, (x, y, w, h), conf))

        logger.info(
            "Tesseract boxes: %d elementos de texto extraídos", len(results)
        )
        return results

    def extract_text_detailed(
        self, image_path: Path
    ) -> dict[str, Any]:
        """Extrai texto com dados detalhados do Tesseract.

        Args:
            image_path: Caminho para a imagem.

        Returns:
            Dicionário com 'text', 'data' (dict do pytesseract),
            e 'average_confidence'.
        """
        image = self._load_image(image_path)
        processed = self._preprocess_image(image)

        config = f"--psm {self._psm_mode}"

        try:
            text = self._pytesseract.image_to_string(
                processed, lang=self._languages, config=config
            )
            data = self._pytesseract.image_to_data(
                processed,
                lang=self._languages,
                config=config,
                output_type=self._pytesseract.Output.DICT,
            )
        except Exception as e:
            raise RuntimeError(
                f"Erro no Tesseract ao processar detalhes de {image_path}: {e}"
            ) from e

        confs = [float(c) for c in data["conf"] if float(c) > 0]
        avg_conf = sum(confs) / len(confs) / 100.0 if confs else 0.0

        return {
            "text": text,
            "data": data,
            "average_confidence": avg_conf,
        }
