from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TimelineEntryType(str, Enum):
    """Tipos de entrada na linha do tempo forense."""

    MESSAGE = "message"
    MEDIA = "media"
    SYSTEM_EVENT = "system_event"
    DELETION = "deletion"
    EDIT = "edit"
    TIMESTAMP_GAP = "timestamp_gap"
    ANOMALY = "anomaly"
    NOTE = "note"


class TimelineEntry(BaseModel):
    """Entrada individual na linha do tempo consolidada de uma investigação."""

    id: UUID = Field(default_factory=uuid4, description="Identificador único da entrada")
    entry_type: TimelineEntryType = Field(..., description="Classificação do tipo de entrada")
    timestamp: datetime = Field(..., description="Data/hora do evento registrado")
    sender: Optional[str] = Field(default=None, description="Remetente associado ao evento")
    content: str = Field(default="", description="Conteúdo textual do evento")
    source_file: Optional[str] = Field(
        default=None,
        description="Arquivo de origem de onde a entrada foi extraída",
    )
    line_in_source: Optional[int] = Field(
        default=None,
        ge=1,
        description="Número da linha no arquivo de origem",
    )
    position_in_image: Optional[str] = Field(
        default=None,
        description="Posição detectada na imagem (ex.: 'top-left', 'center')",
    )
    notes: str = Field(default="", description="Observações adicionais sobre a entrada")
    inconsistencies: list[str] = Field(
        default_factory=list,
        description="Lista de inconsistências detectadas nesta entrada",
    )
