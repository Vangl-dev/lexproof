from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from lexproof.acquisition.zip_handler import SecureZipHandler
from lexproof.parsers.base import ParseError

logger = logging.getLogger(__name__)

_ARCHIVE_EXTENSIONS = {".zip"}


class ArchiveParser:
    """Parser para arquivos compactados (ZIP).

    Fornece métodos para extrair, listar e validar integridade
    de arquivos ZIP utilizando o SecureZipHandler para garantir
    proteção forense (antisslip, antibomb e antisymlink).
    """

    def __init__(self, extract_dir: Path | None = None) -> None:
        """Inicializa o parser de arquivo compactado.

        Args:
            extract_dir: Diretório de destino para extração.
                Se None, usa um diretório temporário.
        """
        self._extract_dir = extract_dir
        self._secure_handler = SecureZipHandler()

    def extract(self, file_path: Path) -> list[Path]:
        """Extrai o conteúdo de um arquivo ZIP para um diretório.

        Args:
            file_path: Caminho para o arquivo ZIP.

        Returns:
            Lista de caminhos dos arquivos extraídos.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se a extração falhar.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        dest = self._get_extract_dir(file_path)

        try:
            extracted = self._secure_handler.extract(file_path, dest)
            logger.info(
                "Extraídos %d arquivos de %s para %s",
                len(extracted),
                file_path.name,
                dest,
            )
            return extracted
        except ValueError as e:
            raise ParseError(f"Arquivo ZIP inválido ou inseguro: {file_path.name} ({e})") from e
        except Exception as e:
            raise ParseError(f"Erro ao extrair {file_path.name}: {e}") from e

    def list_contents(self, file_path: Path) -> list[dict[str, object]]:
        """Lista o conteúdo de um arquivo ZIP sem extrair.

        Args:
            file_path: Caminho para o arquivo ZIP.

        Returns:
            Lista de dicionários com informações de cada arquivo:
                - name: nome do arquivo
                - size: tamanho descompactado em bytes
                - compressed_size: tamanho compactado
                - is_dir: se é diretório

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se a leitura falhar.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        try:
            zip_infos = self._secure_handler.get_contents(file_path)
            contents: list[dict[str, object]] = [
                {
                    "name": info.name,
                    "size": info.size,
                    "compressed_size": info.compressed_size,
                    "is_dir": info.is_dir,
                }
                for info in zip_infos
            ]
            logger.info(
                "Listados %d itens em %s", len(contents), file_path.name
            )
            return contents
        except Exception as e:
            raise ParseError(f"Erro ao listar {file_path.name}: {e}") from e

    def validate(self, file_path: Path) -> bool:
        """Verifica se o arquivo é um ZIP válido e seguro.

        Args:
            file_path: Caminho para o arquivo.

        Returns:
            True se o arquivo existe, tem extensão .zip e é um ZIP válido e seguro.
        """
        return self._secure_handler.validate(file_path)

    def _get_extract_dir(self, file_path: Path) -> Path:
        """Determina o diretório de extração.

        Args:
            file_path: Caminho do arquivo ZIP original.

        Returns:
            Caminho do diretório de extração.
        """
        if self._extract_dir is not None:
            dest = self._extract_dir / file_path.stem
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        dest = Path(tempfile.mkdtemp(prefix=f"lexproof_{file_path.stem}_"))
        logger.debug("Diretório temporário: %s", dest)
        return dest
