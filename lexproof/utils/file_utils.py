"""Funções utilitárias para manipulação de arquivos."""

import hashlib
import mimetypes
import os
import re
import unicodedata
from pathlib import Path


from lexproof.crypto.hasher import FileHasher


def get_file_hash(path: Path, algorithm: str = "sha256") -> str:
    """Calcula o hash de um arquivo usando o algoritmo especificado.

    Delegado centralizadamente para FileHasher.

    Args:
        path: Caminho do arquivo.
        algorithm: Algoritmo de hash (sha256, sha3_512, md5, etc.).

    Returns:
        Hash hexadecimal do arquivo.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se o algoritmo não for suportado.
    """
    return FileHasher.hash_file_str(path, algorithm)


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


from lexproof.models.evidence import EvidenceType

EXTENSION_EVIDENCE_TYPE_MAP: dict[str, EvidenceType] = {
    # Imagens
    ".png": EvidenceType.IMAGE,
    ".jpg": EvidenceType.IMAGE,
    ".jpeg": EvidenceType.IMAGE,
    ".gif": EvidenceType.IMAGE,
    ".bmp": EvidenceType.IMAGE,
    ".tiff": EvidenceType.IMAGE,
    ".tif": EvidenceType.IMAGE,
    ".webp": EvidenceType.IMAGE,
    ".heic": EvidenceType.IMAGE,
    ".svg": EvidenceType.IMAGE,
    ".ico": EvidenceType.IMAGE,
    # Texto
    ".txt": EvidenceType.TEXT,
    ".csv": EvidenceType.TEXT,
    ".json": EvidenceType.TEXT,
    ".xml": EvidenceType.TEXT,
    ".html": EvidenceType.TEXT,
    ".htm": EvidenceType.TEXT,
    ".log": EvidenceType.TEXT,
    ".css": EvidenceType.TEXT,
    ".js": EvidenceType.TEXT,
    ".py": EvidenceType.TEXT,
    ".md": EvidenceType.TEXT,
    # Vídeo
    ".mp4": EvidenceType.VIDEO,
    ".avi": EvidenceType.VIDEO,
    ".mov": EvidenceType.VIDEO,
    ".mkv": EvidenceType.VIDEO,
    ".wmv": EvidenceType.VIDEO,
    ".flv": EvidenceType.VIDEO,
    ".webm": EvidenceType.VIDEO,
    ".m4v": EvidenceType.VIDEO,
    # Áudio
    ".mp3": EvidenceType.AUDIO,
    ".wav": EvidenceType.AUDIO,
    ".flac": EvidenceType.AUDIO,
    ".aac": EvidenceType.AUDIO,
    ".ogg": EvidenceType.AUDIO,
    ".wma": EvidenceType.AUDIO,
    ".m4a": EvidenceType.AUDIO,
    # Archives / Compactados
    ".zip": EvidenceType.ARCHIVE,
    ".rar": EvidenceType.ARCHIVE,
    ".7z": EvidenceType.ARCHIVE,
    ".tar": EvidenceType.ARCHIVE,
    ".gz": EvidenceType.ARCHIVE,
    ".bz2": EvidenceType.ARCHIVE,
    ".xz": EvidenceType.ARCHIVE,
    # Documentos
    ".pdf": EvidenceType.DOCUMENT,
    ".doc": EvidenceType.DOCUMENT,
    ".docx": EvidenceType.DOCUMENT,
    ".xls": EvidenceType.DOCUMENT,
    ".xlsx": EvidenceType.DOCUMENT,
    ".ppt": EvidenceType.DOCUMENT,
    ".pptx": EvidenceType.DOCUMENT,
    ".odt": EvidenceType.DOCUMENT,
    ".ods": EvidenceType.DOCUMENT,
    ".odp": EvidenceType.DOCUMENT,
    ".rtf": EvidenceType.DOCUMENT,
}


def detect_evidence_type(path: Path | str) -> EvidenceType:
    """Detecta o EvidenceType de um arquivo com base na extensão.

    Args:
        path: Caminho do arquivo ou string do caminho.

    Returns:
        EvidenceType correspondente ou EvidenceType.OTHER se desconhecido.
    """
    ext = Path(path).suffix.lower()
    return EXTENSION_EVIDENCE_TYPE_MAP.get(ext, EvidenceType.OTHER)


def is_supported_type(path: Path, file_type: str) -> bool:
    """Verifica se um arquivo pertence a uma categoria de tipo suportada.

    Args:
        path: Caminho do arquivo.
        file_type: Categoria do tipo ('image', 'document', 'video',
                   'audio', 'archive', 'text').

    Returns:
        True se o arquivo pertence à categoria especificada.
    """
    cat = file_type.lower()
    detected = detect_evidence_type(path)
    if detected.value == cat:
        return True
    if cat == "document" and detected == EvidenceType.TEXT and path.suffix.lower() == ".txt":
        return True
    return False


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
