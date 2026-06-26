"""Modelo de evidência digital."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Tipos de evidência suportados."""

    IMAGE = "image"
    TEXT = "text"
    VIDEO = "video"
    ARCHIVE = "archive"
    MESSAGE = "message"
    DOCUMENT = "document"
    OTHER = "other"


class EvidenceFile(BaseModel):
    """Arquivo de evidência importado para o caso."""

    file_path: Path = Field(..., description="Caminho original do arquivo")
    file_name: str = Field(..., description="Nome do arquivo")
    file_size: int = Field(..., ge=0, description="Tamanho do arquivo em bytes")
    evidence_type: EvidenceType = Field(..., description="Tipo da evidência")
    imported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da importação (UTC)",
    )
    original_hash: Optional[str] = Field(
        default=None, description="Hash SHA-256 do arquivo original"
    )
    description: str = Field(default="", description="Descrição opcional da evidência")
    tags: list[str] = Field(default_factory=list, description="Tags para organização")
