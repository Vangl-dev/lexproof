from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Tipos de mensagem encontrados em conversas do WhatsApp."""

    TEXT = "text"
    MEDIA = "media"
    DELETED = "deleted"
    EDITED = "edited"
    SYSTEM = "system"
    STICKER = "sticker"
    AUDIO = "audio"
    VIDEO = "video"
    LINK = "link"
    MULTI = "multi"


class WhatsAppMessage(BaseModel):
    """Representa uma mensagem individual extraída de uma conversa do WhatsApp."""

    id: UUID = Field(default_factory=uuid4, description="Identificador único da mensagem")
    line_number: int = Field(..., ge=1, description="Número da linha no arquivo de origem")
    timestamp: datetime = Field(..., description="Data/hora da mensagem conforme registrada")
    sender: str = Field(..., description="Nome ou número do remetente")
    content: str = Field(default="", description="Texto da mensagem após parsing")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Tipo da mensagem")
    is_deleted: bool = Field(default=False, description="Se a mensagem foi deletada pelo remetente")
    is_edited: bool = Field(default=False, description="Se a mensagem foi editada")
    media_reference: Optional[str] = Field(
        default=None,
        description="Caminho ou referência ao arquivo de mídia associado",
    )
    raw_text: str = Field(default="", description="Texto bruto da linha original antes do parsing")
    ocr_extracted: bool = Field(
        default=False,
        description="Se o conteúdo foi extraído via OCR a partir de imagem",
    )
