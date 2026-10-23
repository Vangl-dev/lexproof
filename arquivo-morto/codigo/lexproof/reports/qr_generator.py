"""Gerador de QR codes para verificação de relatórios."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import qrcode
from PIL import Image

logger = logging.getLogger("lexproof.reports.qr")


class QRCodeGenerator:
    """Gera QR codes para verificação de integridade de relatórios.

    Utiliza a biblioteca qrcode para criar imagens de QR code
    que codificam dados de verificação do caso.
    """

    def __init__(self, box_size: int = 10, border: int = 4) -> None:
        """Inicializa o gerador de QR code.

        Args:
            box_size: Tamanho de cada caixa do QR code em pixels.
            border: Largura da borda ao redor do QR code em caixas.
        """
        self.box_size = box_size
        self.border = border

    def encode_case_hash(self, case_hash: str) -> str:
        """Codifica um hash de caso em uma string para o QR code.

        Gera uma string JSON estruturada contendo o hash e metadados
        de verificação que podem ser lidos a partir do QR code.

        Args:
            case_hash: Hash SHA-256 do caso ou arquivo.

        Returns:
            String JSON codificada para o QR code.
        """
        qr_data = {
            "type": "lexproof_verification",
            "version": "1.0",
            "case_hash": case_hash,
            "algorithm": "sha256",
        }
        encoded = json.dumps(qr_data, separators=(",", ":"), ensure_ascii=True)
        logger.debug("Hash codificado para QR: %s", encoded[:80])
        return encoded

    def generate_verification_qr(self, data: dict) -> Image.Image:
        """Gera uma imagem de QR code a partir dos dados de verificação.

        Args:
            data: Dicionário com dados a serem codificados. Deve conter
                pelo menos a chave "case_hash".

        Returns:
            Imagem Pillow com o QR code gerado.
        """
        qr_data_string = json.dumps(data, separators=(",", ":"), ensure_ascii=True)

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=self.box_size,
            border=self.border,
        )
        qr.add_data(qr_data_string)
        qr.make(fit=True)

        image = qr.make_image(fill_color="black", back_color="white")
        if not isinstance(image, Image.Image):
            image = image.convert("RGB")

        logger.debug("QR code gerado com dados de %d bytes", len(qr_data_string))
        return image

    def save_qr(self, image: Image.Image, path: Path) -> Path:
        """Salva a imagem do QR code em disco.

        Args:
            image: Imagem do QR code a ser salva.
            path: Caminho do arquivo de saída.

        Returns:
            Caminho do arquivo salvo.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(path), format="PNG", optimize=True)
        logger.info("QR code salvo em: %s", path)
        return path
