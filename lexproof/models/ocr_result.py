from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OCRResult(BaseModel):
    """Resultado da extração de texto via OCR de uma imagem de evidência."""

    id: UUID = Field(default_factory=uuid4, description="Identificador único do resultado OCR")
    source_image: str = Field(..., description="Caminho da imagem processada")
    extracted_text: str = Field(default="", description="Texto extraído pela引擎 OCR")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Nível de confiança geral da extração (0.0 a 1.0)",
    )
    detected_timestamps: list[str] = Field(
        default_factory=list,
        description="Timestamps detectados no texto da imagem",
    )
    detected_senders: list[str] = Field(
        default_factory=list,
        description="Nomes ou números de remetentes detectados no texto",
    )
    detected_messages: list[str] = Field(
        default_factory=list,
        description="Mensagens individuais segmentadas a partir do texto extraído",
    )
    engine_used: str = Field(
        default="",
        description="Engine OCR utilizado (ex.: 'tesseract', 'easyocr')",
    )
    processing_time: float = Field(
        default=0.0,
        ge=0.0,
        description="Tempo de processamento em segundos",
    )
