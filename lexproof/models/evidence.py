"""Modelo de evidência digital para preservação jurídica."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Tipos de evidência suportados."""

    IMAGE = "image"
    CHAT_EXPORT = "chat_export"
    TEXT = "text"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    OTHER = "other"

    # Compatibilidade com código existente (deprecated)
    MESSAGE = "chat_export"  # Alias para CHAT_EXPORT


class EvidenceSource(str, Enum):
    """Origem da evidência."""

    MANUAL_UPLOAD = "manual_upload"
    WHATSAPP_EXPORT = "whatsapp_export"
    TELEGRAM_EXPORT = "telegram_export"
    SCREENSHOT = "screenshot"
    OTHER = "other"


class EvidenceMetadata(BaseModel):
    """Metadados extraídos da evidência."""

    # EXIF
    exif: Optional[dict[str, str]] = Field(default=None, description="Dados EXIF")

    # XMP
    xmp: Optional[dict[str, str]] = Field(default=None, description="Dados XMP")

    # ICC Profile
    icc_profile: Optional[str] = Field(default=None, description="Perfil de cor ICC")

    # Software
    software: Optional[str] = Field(default=None, description="Software utilized")

    # Dispositivo
    device: Optional[str] = Field(default=None, description="Dispositivo de captura")

    # Data Original
    original_date: Optional[datetime] = Field(
        default=None, description="Data original da mídia"
    )

    # Resolução
    width: Optional[int] = Field(default=None, description="Largura em pixels")
    height: Optional[int] = Field(default=None, description="Altura em pixels")

    # Compressão
    compression: Optional[str] = Field(default=None, description="Tipo de compressão")

    # Color Space
    color_space: Optional[str] = Field(default=None, description="Espaço de cor")

    # Nota sobre ausência
    missing_metadata_note: Optional[str] = Field(
        default=None,
        description="Nota quando metadados estão ausentes",
    )


class OCRResult(BaseModel):
    """Resultado da extração de texto por OCR."""

    text: str = Field(..., description="Texto extraído")
    confidence: float = Field(..., ge=0, le=1, description="Nível de confiança (0-1)")
    language: Optional[str] = Field(default=None, description="Idioma detectado")
    bounding_boxes: Optional[list[dict[str, int]]] = Field(
        default=None, description="Caixas delimitadoras do texto"
    )
    engine: str = Field(..., description="Mecanismo OCR utilizado")
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora do processamento",
    )


class PerceptualHashes(BaseModel):
    """Hashes perceptuais para comparação visual (v0.4)."""

    phash: Optional[str] = Field(default=None, description="Perceptual hash")
    dhash: Optional[str] = Field(default=None, description="Difference hash")
    ahash: Optional[str] = Field(default=None, description="Average hash")


class Evidence(BaseModel):
    """Classe base para todas as evidências digitais preservadas.

    Cada evidência possui:
    - Identificador único (LP-000001)
    - Hash SHA-256
    - Hash BLAKE3
    - Metadados
    - OCR (obrigatório para imagens)
    - Miniatura
    - Origem
    - Data de preservação
    - Observações
    """

    # Identificador único
    id: str = Field(
        default_factory=lambda: f"LP-{uuid4().hex[:6].upper()}",
        description="Identificador único da evidência (LP-XXXXXX)",
    )

    # Arquivo
    file_path: Path = Field(..., description="Caminho do arquivo")
    file_name: str = Field(..., description="Nome do arquivo")
    file_size: int = Field(..., ge=0, description="Tamanho em bytes")

    # Tipo
    evidence_type: EvidenceType = Field(..., description="Tipo da evidência")
    source: EvidenceSource = Field(
        default=EvidenceSource.MANUAL_UPLOAD, description="Origem da evidência"
    )

    # Hashes criptográficos
    sha256: str = Field(..., description="Hash SHA-256 do arquivo")
    blake3: str = Field(..., description="Hash BLAKE3 do arquivo")

    # Metadados
    metadata: EvidenceMetadata = Field(
        default_factory=EvidenceMetadata, description="Metadados extraídos"
    )

    # OCR
    ocr: Optional[OCRResult] = Field(default=None, description="Resultado do OCR")

    # Miniatura
    thumbnail: Optional[Path] = Field(default=None, description="Caminho da miniatura")

    # Rastreabilidade
    preservation_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da preservação (UTC)",
    )
    imported_by: Optional[str] = Field(
        default=None, description="Usuário responsável pela importação"
    )

    # Descrição e tags
    description: str = Field(default="", description="Descrição opcional")
    tags: list[str] = Field(default_factory=list, description="Tags para organização")

    # Observações
    notes: Optional[str] = Field(
        default=None, description="Observações sobre a evidência"
    )

    # Compatibilidade com código existente (deprecated)
    @property
    def imported_at(self) -> datetime:
        """Alias para preservation_date (compatibilidade)."""
        return self.preservation_date

    @property
    def original_hash(self) -> Optional[str]:
        """Alias para sha256 (compatibilidade)."""
        return self.sha256


class ImageEvidence(Evidence):
    """Evidência do tipo imagem (prints de conversas)."""

    evidence_type: EvidenceType = Field(
        default=EvidenceType.IMAGE, description="Tipo da evidência"
    )

    # Dimensões
    width: int = Field(..., description="Largura em pixels")
    height: int = Field(..., description="Altura em pixels")

    # Formato
    format: str = Field(..., description="Formato da imagem (PNG, JPG, etc.)")

    # Hashes perceptuais (v0.4)
    perceptual_hashes: Optional[PerceptualHashes] = Field(
        default=None, description="Hashes perceptuais para comparação visual"
    )


class ChatExportEvidence(Evidence):
    """Evidência do tipo exportação de conversa (WhatsApp TXT, etc.)."""

    evidence_type: EvidenceType = Field(
        default=EvidenceType.CHAT_EXPORT, description="Tipo da evidência"
    )

    # Formato da exportação
    export_format: str = Field(
        ..., description="Formato da exportação (whatsapp, telegram, etc.)"
    )

    # Estatísticas
    message_count: int = Field(..., ge=0, description="Número de mensagens")
    participant_count: int = Field(
        default=0, ge=0, description="Número de participantes"
    )

    # Período
    date_range_start: Optional[datetime] = Field(
        default=None, description="Data da primeira mensagem"
    )
    date_range_end: Optional[datetime] = Field(
        default=None, description="Data da última mensagem"
    )

    # Participantes
    participants: list[str] = Field(
        default_factory=list, description="Nomes dos participantes"
    )


# Alias para compatibilidade
EvidenceFile = Evidence
