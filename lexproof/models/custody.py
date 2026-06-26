"""Modelos de cadeia de custódia."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CustodyEventType(str, Enum):
    """Tipos de evento na cadeia de custódia."""

    IMPORT = "import"
    HASH = "hash"
    VERIFY = "verify"
    EXPORT = "export"
    MODIFICATION = "modification"
    ANNOTATION = "annotation"


class CustodyEvent(BaseModel):
    """Evento individual na cadeia de custódia."""

    event_type: CustodyEventType = Field(..., description="Tipo do evento")
    description: str = Field(..., description="Descrição do evento")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora do evento (UTC)",
    )
    hash_before: Optional[str] = Field(
        default=None, description="Hash do arquivo antes do evento"
    )
    hash_after: Optional[str] = Field(
        default=None, description="Hash do arquivo após o evento"
    )
    operator: str = Field(default="system", description="Operador que realizou o evento")
    metadata: dict[str, str] = Field(default_factory=dict, description="Dados adicionais")


class CustodyChain(BaseModel):
    """Cadeia de custódia completa de uma evidência."""

    evidence_id: str = Field(..., description="Identificador da evidência")
    events: list[CustodyEvent] = Field(default_factory=list, description="Lista de eventos")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora de criação da cadeia (UTC)",
    )

    def add_event(self, event: CustodyEvent) -> None:
        """Adiciona um evento à cadeia de custódia."""
        self.events.append(event)

    def get_last_hash(self) -> Optional[str]:
        """Retorna o hash mais recente da cadeia."""
        for event in reversed(self.events):
            if event.hash_after is not None:
                return event.hash_after
        return None
