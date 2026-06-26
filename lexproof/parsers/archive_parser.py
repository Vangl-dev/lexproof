from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path

from lexproof.parsers.base import ParseError

logger = logging.getLogger(__name__)

_ARCHIVE_EXTENSIONS = {".zip"}


class ArchiveParser:
    """Parser para arquivos compactados (ZIP).

    Fornece métodos para extrair, listar e validar integridade
    de arquivos ZIP.
    """

    def __init__(self, extract_dir: Path | None = None) -> None:
        """Inicializa o parser de arquivo compactado.

        Args:
            extract_dir: Diretório de destino para extração.
                Se None, usa um diretório temporário.
        """
        self._extract_dir = extract_dir

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

        if not self.validate(file_path):
            raise ParseError(f"Arquivo ZIP inválido: {file_path.name}")

        dest = self._get_extract_dir(file_path)

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                zf.extractall(dest)
                extracted = [
                    dest / name
                    for name in zf.namelist()
                    if not name.endswith("/")
                ]
                logger.info(
                    "Extraídos %d arquivos de %s para %s",
                    len(extracted),
                    file_path.name,
                    dest,
                )
                return extracted
        except zipfile.BadZipFile as e:
            raise ParseError(f"ZIP corrompido: {e}") from e
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

        if not self.validate(file_path):
            raise ParseError(f"Arquivo ZIP inválido: {file_path.name}")

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                contents: list[dict[str, object]] = []
                for info in zf.infolist():
                    contents.append({
                        "name": info.filename,
                        "size": info.file_size,
                        "compressed_size": info.compress_size,
                        "is_dir": info.is_dir(),
                    })
                logger.info(
                    "Listados %d itens em %s", len(contents), file_path.name
                )
                return contents
        except zipfile.BadZipFile as e:
            raise ParseError(f"ZIP corrompido: {e}") from e
        except Exception as e:
            raise ParseError(f"Erro ao listar {file_path.name}: {e}") from e

    def validate(self, file_path: Path) -> bool:
        """Verifica se o arquivo é um ZIP válido e íntegro.

        Args:
            file_path: Caminho para o arquivo.

        Returns:
            True se o arquivo existe, tem extensão .zip e é um ZIP válido.
        """
        if not file_path.exists():
            return False

        if file_path.suffix.lower() not in _ARCHIVE_EXTENSIONS:
            return False

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                bad = zf.testzip()
                return bad is None
        except zipfile.BadZipFile:
            return False
        except Exception:
            return False

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
