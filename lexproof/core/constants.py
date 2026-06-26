"""Constantes globais do LexProof."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from lexproof import __version__

APP_NAME: Final[str] = "LexProof"
APP_VERSION: Final[str] = __version__
APP_AUTHOR: Final[str] = "LexProof Team"

BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent
RESOURCES_DIR: Final[Path] = BASE_DIR / "resources"
STYLES_DIR: Final[Path] = RESOURCES_DIR / "styles"

SUPPORTED_IMAGE_TYPES: Final[frozenset[str]] = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".heic",
})

SUPPORTED_TEXT_TYPES: Final[frozenset[str]] = frozenset({
    ".txt", ".csv", ".json", ".xml", ".html", ".htm", ".log",
})

SUPPORTED_VIDEO_TYPES: Final[frozenset[str]] = frozenset({
    ".mp4", ".avi", ".mov", ".mkv", ".webm",
})

SUPPORTED_ARCHIVE_TYPES: Final[frozenset[str]] = frozenset({
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
})

SUPPORTED_MESSAGE_TYPES: Final[frozenset[str]] = frozenset({
    ".txt", ".csv", ".json", ".zip",
})

MAX_FILE_SIZE_MB: Final[int] = 500
MAX_FILE_SIZE_BYTES: Final[int] = MAX_FILE_SIZE_MB * 1024 * 1024

DEFAULT_ENCODING: Final[str] = "utf-8"

HASH_ALGORITHMS: Final[list[str]] = ["sha256", "sha3_512", "blake3"]

SIDEBAR_WIDTH: Final[int] = 280
STATUS_BAR_HEIGHT: Final[int] = 24
MIN_WINDOW_WIDTH: Final[int] = 1024
MIN_WINDOW_HEIGHT: Final[int] = 768
PREVIEW_MAX_WIDTH: Final[int] = 600

TIMEZONE_DEFAULT: Final[str] = "America/Sao_Paulo"

SESSION_FILE_EXTENSION: Final[str] = ".lexproof.json"
REPORT_OUTPUT_DIR: Final[str] = "reports"

LOG_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
