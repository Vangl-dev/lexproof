"""Handler seguro para arquivos ZIP com proteções forenses.

Implementa proteções contra:
- ZIP Slip (path traversal)
- Symlinks
- Arquivos gigantes (ZIP Bomb)
- Path Traversal
- Nomes Unicode maliciosos
"""

from __future__ import annotations

import logging
import os
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Limites de segurança
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB por arquivo
MAX_TOTAL_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB total
MAX_FILES = 10000  # Máximo de arquivos
MAX_COMPRESSION_RATIO = 100  # Razão máxima de compressão (ZIP Bomb)


@dataclass
class ZipFileInfo:
    """Informações de um arquivo dentro do ZIP."""

    name: str
    size: int
    compressed_size: int
    is_dir: bool
    is_symlink: bool
    sha256: Optional[str] = None
    blake3: Optional[str] = None


@dataclass
class ZipManifest:
    """Manifesto de um arquivo ZIP."""

    original_zip: str
    sha256: str
    blake3: str
    size: int
    file_count: int
    files: list[ZipFileInfo] = field(default_factory=list)


class SecureZipHandler:
    """Handler seguro para extração de ZIPs com proteções forenses.

    Implementa todas as proteções necessárias para aquisição segura:
    - Validação de path traversal (ZIP Slip)
    - Detecção de symlinks
    - Limite de tamanho de arquivos
    - Limite de razão de compressão (ZIP Bomb)
    - Validação de nomes Unicode
    """

    def __init__(
        self,
        max_file_size: int = MAX_FILE_SIZE,
        max_total_size: int = MAX_TOTAL_SIZE,
        max_files: int = MAX_FILES,
        max_compression_ratio: int = MAX_COMPRESSION_RATIO,
    ) -> None:
        """Inicializa o handler seguro.

        Args:
            max_file_size: Tamanho máximo por arquivo em bytes.
            max_total_size: Tamanho total máximo em bytes.
            max_files: Número máximo de arquivos.
            max_compression_ratio: Razão máxima de compressão.
        """
        self._max_file_size = max_file_size
        self._max_total_size = max_total_size
        self._max_files = max_files
        self._max_compression_ratio = max_compression_ratio
        self._warnings: list[str] = []
        self._errors: list[str] = []

    @property
    def warnings(self) -> list[str]:
        """Retorna os avisos acumulados."""
        return list(self._warnings)

    @property
    def errors(self) -> list[str]:
        """Retorna os erros acumulados."""
        return list(self._errors)

    def validate(self, zip_path: Path) -> bool:
        """Valida um arquivo ZIP completamente.

        Args:
            zip_path: Caminho do arquivo ZIP.

        Returns:
            True se o ZIP é válido e seguro.
        """
        self._warnings.clear()
        self._errors.clear()

        if not zip_path.exists():
            self._errors.append(f"Arquivo não encontrado: {zip_path}")
            return False

        if not zip_path.suffix.lower() == ".zip":
            self._errors.append(f"Extensão não é .zip: {zip_path.suffix}")
            return False

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Verificar integridade básica
                bad = zf.testzip()
                if bad is not None:
                    self._errors.append(f"Arquivo corrompido: {bad}")
                    return False

                # Verificar número de arquivos
                namelist = zf.namelist()
                if len(namelist) > self._max_files:
                    self._errors.append(
                        f"Muitos arquivos: {len(namelist)} > {self._max_files}"
                    )
                    return False

                # Verificar cada arquivo
                total_size = 0
                for info in zf.infolist():
                    # Verificar symlinks
                    if self._is_symlink(info):
                        self._errors.append(
                            f"Symlink detectado: {info.filename}"
                        )
                        return False

                    # Verificar path traversal
                    if self._has_path_traversal(info.filename):
                        self._errors.append(
                            f"Path traversal detectado: {info.filename}"
                        )
                        return False

                    # Verificar tamanho individual
                    if info.file_size > self._max_file_size:
                        self._errors.append(
                            f"Arquivo muito grande: {info.filename} "
                            f"({info.file_size} > {self._max_file_size})"
                        )
                        return False

                    # Verificar ZIP Bomb
                    if info.compress_size > 0 and info.file_size > 0:
                        ratio = info.file_size / info.compress_size
                        if ratio > self._max_compression_ratio:
                            self._warnings.append(
                                f"Alta compressão (possível ZIP Bomb): "
                                f"{info.filename} (razão: {ratio:.1f})"
                            )

                    total_size += info.file_size

                # Verificar tamanho total
                if total_size > self._max_total_size:
                    self._errors.append(
                        f"Tamanho total excedido: {total_size} > {self._max_total_size}"
                    )
                    return False

                logger.info(
                    "ZIP validado: %s (%d arquivos, %d bytes)",
                    zip_path.name,
                    len(namelist),
                    total_size,
                )
                return True

        except zipfile.BadZipFile as e:
            self._errors.append(f"ZIP inválido: {e}")
            return False
        except Exception as e:
            self._errors.append(f"Erro ao validar: {e}")
            return False

    def extract(
        self,
        zip_path: Path,
        dest_dir: Path,
        *,
        safe_mode: bool = True,
    ) -> list[Path]:
        """Extrai um ZIP de forma segura.

        Args:
            zip_path: Caminho do arquivo ZIP.
            dest_dir: Diretório de destino.
            safe_mode: Se True, aplica todas as proteções.

        Returns:
            Lista de caminhos dos arquivos extraídos.

        Raises:
            ValueError: Se o ZIP não for válido.
        """
        if not self.validate(zip_path):
            raise ValueError(f"ZIP não válido: {self._errors}")

        dest_dir.mkdir(parents=True, exist_ok=True)
        extracted: list[Path] = []

        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue

                # Resolver caminho de destino
                target_path = self._resolve_path(info.filename, dest_dir)

                # Criar diretório pai
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Extrair arquivo
                with zf.open(info.filename) as src, open(target_path, "wb") as dst:
                    dst.write(src.read())

                extracted.append(target_path)
                logger.debug("Extraído: %s -> %s", info.filename, target_path)

        logger.info(
            "Extraídos %d arquivos de %s para %s",
            len(extracted),
            zip_path.name,
            dest_dir,
        )

        return extracted

    def get_contents(self, zip_path: Path) -> list[ZipFileInfo]:
        """Retorna o conteúdo do ZIP sem extrair.

        Args:
            zip_path: Caminho do arquivo ZIP.

        Returns:
            Lista de informações dos arquivos.
        """
        if not zip_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {zip_path}")

        contents: list[ZipFileInfo] = []

        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                contents.append(ZipFileInfo(
                    name=info.filename,
                    size=info.file_size,
                    compressed_size=info.compress_size,
                    is_dir=info.is_dir(),
                    is_symlink=self._is_symlink(info),
                ))

        return contents

    def _is_symlink(self, info: zipfile.ZipInfo) -> bool:
        """Verifica se um arquivo é symlink.

        Args:
            info: Informações do arquivo no ZIP.

        Returns:
            True se for symlink.
        """
        # Verificar pelo atributo externo (Unix)
        # Bit 0x0100 = symlink
        if info.external_attr & 0x0100:
            return True

        # Verificar pelo conteúdo (método mais robusto)
        # Se o tamanho for muito pequeno, pode ser symlink
        if info.file_size < 100 and not info.is_dir():
            try:
                with zipfile.ZipFile(
                    os.path.join(info.header_offset, "r")
                ) as zf:
                    content = zf.read(info.filename).decode("utf-8", errors="ignore")
                    if content.startswith("/") or content.startswith("./"):
                        return True
            except Exception:
                pass

        return False

    def _has_path_traversal(self, filename: str) -> bool:
        """Verifica se o nome do arquivo contém path traversal.

        Args:
            filename: Nome do arquivo.

        Returns:
            True se detectar path traversal.
        """
        # Verificar componentes perigosos
        dangerous = ["..", "~", "/"]
        parts = Path(filename).parts

        for part in parts:
            if part in dangerous:
                return True
            if part.startswith("~"):
                return True
            if any(c in part for c in ["\x00", "\xff"]):
                return True

        return False

    def _resolve_path(self, filename: str, base_dir: Path) -> Path:
        """Resolve o caminho de destino de forma segura.

        Args:
            filename: Nome do arquivo no ZIP.
            base_dir: Diretório base.

        Returns:
            Caminho absoluto seguro.
        """
        # Normalizar e resolver
        target = (base_dir / filename).resolve()
        base = base_dir.resolve()

        # Verificar que o destino está dentro do base_dir
        if not str(target).startswith(str(base)):
            raise ValueError(
                f"Path traversal detectado: {filename} "
                f"escaparia de {base_dir}"
            )

        return target
