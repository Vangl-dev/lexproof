from __future__ import annotations

import math
import logging
from typing import Union

from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

Number = Union[int, float]


def grayscale(image: Image.Image) -> Image.Image:
    """Converte imagem para escala de cinza.

    Args:
        image: Imagem de entrada.

    Returns:
        Imagem em escala de cinza.
    """
    return image.convert("L")


def enhance_contrast(image: Image.Image, factor: float = 1.5) -> Image.Image:
    """Aumenta o contraste da imagem.

    Args:
        image: Imagem de entrada.
        factor: Fator de contraste (1.0 = sem alteração, >1.0 = mais contraste).

    Returns:
        Imagem com contraste ajustado.
    """
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(factor)


def binarize(image: Image.Image, threshold: int = 128) -> Image.Image:
    """Binariza a imagem usando um limiar.

    Args:
        image: Imagem de entrada (geralmente em escala de cinza).
        threshold: Limiar para binarização (0-255).

    Returns:
        Imagem binarizada (preto e branco).
    """
    gray = grayscale(image) if image.mode != "L" else image
    return gray.point(lambda x: 255 if x > threshold else 0, "1")


def resize(image: Image.Image, max_width: int = 1920) -> Image.Image:
    """Redimensiona a imagem mantendo a proporção.

    Args:
        image: Imagem de entrada.
        max_width: Largura máxima da imagem de saída.

    Returns:
        Imagem redimensionada.
    """
    if image.width <= max_width:
        return image

    ratio = max_width / image.width
    new_height = int(image.height * ratio)
    return image.resize((max_width, new_height), Image.Resampling.LANCZOS)


def denoise(image: Image.Image) -> Image.Image:
    """Remove ruído da imagem usando filtro mediano.

    Args:
        image: Imagem de entrada.

    Returns:
        Imagem com ruído reduzido.
    """
    return image.filter(ImageFilter.MedianFilter(size=3))


def deskew(image: Image.Image) -> Image.Image:
    """Corrige a inclinação da imagem usando análise de projeção horizontal.

    Calcula o ângulo de inclinação analisando a variação de pixels pretos
    ao longo de linhas horizontais e rotaciona a imagem para corrigir.

    Args:
        image: Imagem de entrada.

    Returns:
        Imagem com inclinação corrigida.
    """
    gray = grayscale(image)
    binary = binarize(gray)

    import numpy as np

    img_array = np.array(binary, dtype=np.float64)

    if img_array.ndim > 2:
        img_array = img_array.mean(axis=2)

    binary_array = (img_array < 128).astype(np.float64)

    if binary_array.sum() == 0:
        logger.debug("Imagem binarizada vazia, ignorando deskew")
        return image

    best_angle = 0.0
    best_score = -1.0
    step = 0.1

    for angle_int in range(-300, 301, int(step * 1000)):
        angle = angle_int / 1000.0
        rotated = binary_array
        h, w = rotated.shape
        cy, cx = h // 2, w // 2
        cos_a = math.cos(math.radians(angle))
        sin_a = math.sin(math.radians(angle))

        y_coords, x_coords = np.nonzero(rotated)
        if len(y_coords) == 0:
            continue

        x_centered = x_coords - cx
        y_centered = y_coords - cy

        new_x = (x_centered * cos_a - y_centered * sin_a + cx).astype(int)
        new_y = (x_centered * sin_a + y_centered * cos_a + cy).astype(int)

        valid = (new_x >= 0) & (new_x < w) & (new_y >= 0) & (new_y < h)
        new_y, new_x = new_y[valid], new_x[valid]

        if len(new_y) == 0:
            continue

        score = 0.0
        for row in range(h):
            count = np.sum(new_y == row)
            if count > 0:
                score += count * count

        if score > best_score:
            best_score = score
            best_angle = angle

    if abs(best_angle) < 0.5:
        logger.debug("Inclinação insignificante (%.2f°), ignorando deskew", best_angle)
        return image

    logger.info("Corrigindo inclinação de %.2f°", best_angle)
    return image.rotate(best_angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=(255, 255, 255))
