"""Funções utilitárias para manipulação de arquivos."""

import hashlib
import mimetypes
import os
import re
import unicodedata
from pathlib import Path


def get_file_hash(path: Path, algorithm: str = "sha256") -> str:
    """Calcula o hash de um arquivo usando o algoritmo especificado.

    Args:
        path: Caminho do arquivo.
        algorithm: Algoritmo de hash (sha256, sha3_512, md5, etc.).

    Returns:
        Hash hexadecimal do arquivo.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se o algoritmo não for suportado pelo hashlib.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    hasher = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_file_info(path: Path) -> dict:
    """Retorna informações detalhadas sobre um arquivo.

    Args:
        path: Caminho do arquivo.

    Returns:
        Dicionário com metadados: nome, extensão, tamanho, tipo MIME,
        data de modificação, data de criação e se é arquivo/diretório.
    """
    stat = path.stat()
    mime_type, _ = mimetypes.guess_type(str(path))
    return {
        "name": path.name,
        "extension": path.suffix.lower(),
        "size": stat.st_size,
        "mime_type": mime_type or "application/octet-stream",
        "modified": stat.st_mtime,
        "created": stat.st_ctime,
        "is_file": path.is_file(),
        "is_directory": path.is_dir(),
        "is_symlink": path.is_symlink(),
        "absolute_path": str(path.resolve()),
    }


def safe_filename(name: str) -> str:
    """Converte um nome para um nome de arquivo seguro.

    Remove caracteres especiais, normaliza unicode e substitui espaços
    por underscores.

    Args:
        name: Nome original.

    Returns:
        Nome seguro para uso como arquivo.
    """
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s\-.]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    name = re.sub(r"_+", "_", name)
    return name[:200] if name else "unnamed"


def ensure_directory(path: Path) -> Path:
    """Garante que um diretório exista, criando-o se necessário.

    Args:
        path: Caminho do diretório.

    Returns:
        O caminho do diretório criado ou existente.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_mime_type(path: Path) -> str:
    """Detecta o tipo MIME de um arquivo.

    Args:
        path: Caminho do arquivo.

    Returns:
        String do tipo MIME detectado.
    """
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type or "application/octet-stream"


def is_supported_type(path: Path, file_type: str) -> bool:
    """Verifica se um arquivo pertence a uma categoria de tipo suportada.

    Args:
        path: Caminho do arquivo.
        file_type: Categoria do tipo ('image', 'document', 'video',
                   'audio', 'archive', 'text').

    Returns:
        True se o arquivo pertence à categoria especificada.
    """
    TYPE_MAP: dict[str, list[str]] = {
        "image": [
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
            ".tif", ".webp", ".svg", ".ico",
        ],
        "document": [
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt",
            ".pptx", ".odt", ".ods", ".odp", ".rtf", ".txt",
        ],
        "video": [
            ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
            ".webm", ".m4v",
        ],
        "audio": [
            ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma",
            ".m4a",
        ],
        "archive": [
            ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
            ".xz",
        ],
        "text": [
            ".txt", ".csv", ".json", ".xml", ".html", ".htm",
            ".css", ".js", ".py", ".md", ".log",
        ],
    }
    supported = TYPE_MAP.get(file_type.lower(), [])
    return path.suffix.lower() in supported


def calculate_directory_size(path: Path) -> int:
    """Calcula o tamanho total de um diretório recursivamente.

    Args:
        path: Caminho do diretório.

    Returns:
        Tamanho total em bytes.

    Raises:
        NotADirectoryError: Se o caminho não for um diretório.
    """
    if not path.is_dir():
        raise NotADirectoryError(f"Não é um diretório: {path}")
    total = 0
    for entry in os.scandir(path):
        if entry.is_file(follow_symlinks=False):
            total += entry.stat(follow_symlinks=False).st_size
        elif entry.is_dir(follow_symlinks=False):
            total += calculate_directory_size(Path(entry.path))
    return total
