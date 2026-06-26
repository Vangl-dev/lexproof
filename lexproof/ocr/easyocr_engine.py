from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from PIL import Image

from lexproof.ocr.base import BaseOCR

logger = logging.getLogger(__name__)


class EasyOCREngine(BaseOCR):
    """Engine OCR baseado no EasyOCR.

    Utiliza easyocr para extração de texto com suporte a português e inglês.
    O reader é inicializado sob demanda (lazy initialization) para evitar
    custo de memória quando não utilizado.
    """

    DEFAULT_LANGUAGES = ["pt", "en"]

    def __init__(
        self,
        languages: list[str] | None = None,
        gpu: bool = True,
        max_image_width: int = 1920,
    ) -> None:
        """Inicializa o engine EasyOCR.

        Args:
            languages: Lista de códigos de idioma (ex: ['pt', 'en']).
            gpu: Se True, usa GPU para processamento (requer CUDA).
            max_image_width: Largura máxima para redimensionamento.

        Raises:
            ImportError: Se o easyocr não estiver instalado.
        """
        super().__init__(max_image_width)
        self._languages = languages or self.DEFAULT_LANGUAGES
        self._gpu = gpu
        self._reader: Any = None
        self._easyocr = self._import_easyocr()

    @staticmethod
    def _import_easyocr() -> Any:
        """Importa easyocr com tratamento de erro.

        Returns:
            Módulo easyocr.

        Raises:
            ImportError: Se easyocr não estiver instalado.
        """
        try:
            import easyocr

            return easyocr
        except ImportError:
            raise ImportError(
                "easyocr não está instalado. "
                "Instale com: pip install easyocr"
            )

    def _get_reader(self) -> Any:
        """Inicializa o reader EasyOCR sob demanda.

        Returns:
            Instância do EasyOCR Reader.
        """
        if self._reader is None:
            logger.info(
                "Inicializando EasyOCR reader com idiomas: %s (gpu=%s)",
                self._languages,
                self._gpu,
            )
            self._reader = self._easyocr.Reader(
                self._languages, gpu=self._gpu
            )
        return self._reader

    @property
    def languages(self) -> list[str]:
        """Retorna os idiomas configurados."""
        return self._languages

    def extract_text(self, image_path: Path) -> str:
        """Extrai texto completo de uma imagem usando EasyOCR.

        Args:
            image_path: Caminho para a imagem.

        Returns:
            Texto completo extraído.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            RuntimeError: Se ocorrer erro no processamento.
        """
        logger.info("Extraindo texto (EasyOCR) de: %s", image_path)
        start = time.monotonic()

        image = self._load_image(image_path)
        processed = self._preprocess_image(image)

        import numpy as np

        img_array = np.array(processed)

        try:
            reader = self._get_reader()
            raw_results = reader.readtext(img_array)
        except Exception as e:
            raise RuntimeError(
                f"Erro no EasyOCR ao processar {image_path}: {e}"
            ) from e

        text_parts = [r[1] for r in raw_results]
        text = " ".join(text_parts)

        elapsed = time.monotonic() - start
        logger.info(
            "EasyOCR concluído em %.2fs, %d caracteres extraídos",
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
        logger.info("Extraindo texto com boxes (EasyOCR) de: %s", image_path)

        image = self._load_image(image_path)
        processed = self._preprocess_image(image)

        import numpy as np

        img_array = np.array(processed)

        try:
            reader = self._get_reader()
            raw_results = reader.readtext(img_array)
        except Exception as e:
            raise RuntimeError(
                f"Erro no EasyOCR ao extrair boxes de {image_path}: {e}"
            ) from e

        results: list[tuple[str, tuple[int, int, int, int], float]] = []

        for bbox_points, text, confidence in raw_results:
            if not text.strip():
                continue

            x_coords = [int(p[0]) for p in bbox_points]
            y_coords = [int(p[1]) for p in bbox_points]

            x_min = min(x_coords)
            y_min = min(y_coords)
            width = max(x_coords) - x_min
            height = max(y_coords) - y_min

            results.append((text, (x_min, y_min, width, height), float(confidence)))

        logger.info(
            "EasyOCR boxes: %d elementos de texto extraídos", len(results)
        )
        return results

    def extract_text_detailed(
        self, image_path: Path
    ) -> dict[str, Any]:
        """Extrai texto com dados detalhados do EasyOCR.

        Args:
            image_path: Caminho para a imagem.

        Returns:
            Dicionário com 'text', 'raw_results', e 'average_confidence'.
        """
        image = self._load_image(image_path)
        processed = self._preprocess_image(image)

        import numpy as np

        img_array = np.array(processed)

        try:
            reader = self._get_reader()
            raw_results = reader.readtext(img_array)
        except Exception as e:
            raise RuntimeError(
                f"Erro no EasyOCR ao extrair detalhes de {image_path}: {e}"
            ) from e

        text_parts = [r[1] for r in raw_results]
        text = " ".join(text_parts)

        confs = [r[2] for r in raw_results if r[2] > 0]
        avg_conf = sum(confs) / len(confs) if confs else 0.0

        return {
            "text": text,
            "raw_results": raw_results,
            "average_confidence": avg_conf,
        }
