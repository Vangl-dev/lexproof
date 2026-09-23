"""Modelo de correlação entre evidências."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CorrelationType(str, Enum):
    """Tipos de correlação entre evidências."""

    PRINT_TO_TXT = "print_to_txt"  # Print corresponde a linhas do TXT
    OCR_TO_TXT = "ocr_to_txt"  # Texto OCR corresponde ao TXT
    TEMPORAL = "temporal"  # Correlação temporal
    PARTICIPANT = "participant"  # Correlação por participante


class CorrelationMatch(BaseModel):
    """Detalhes de uma correspondência encontrada."""

    source_evidence_id: str = Field(
        ..., description="ID da evidência de origem"
    )
    target_evidence_id: str = Field(
        ..., description="ID da evidência alvo"
    )
    source_line_start: Optional[int] = Field(
        default=None, description="Linha inicial no arquivo de origem"
    )
    source_line_end: Optional[int] = Field(
        default=None, description="Linha final no arquivo de origem"
    )
    target_text: Optional[str] = Field(
        default=None, description="Texto correspondente no alvo"
    )
    confidence: float = Field(
        ..., ge=0, le=1, description="Grau de confiança (0-1)"
    )
    match_type: str = Field(
        ..., description="Tipo de correspondência (exact, fuzzy, semantic)"
    )


class CorrelationResult(BaseModel):
    """Resultado da correlação entre evidências."""

    id: str = Field(
        default_factory=lambda: f"COR-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        description="ID único da correlação",
    )

    correlation_type: CorrelationType = Field(
        ..., description="Tipo de correlação"
    )

    matches: list[CorrelationMatch] = Field(
        default_factory=list, description="Lista de correspondências encontradas"
    )

    overall_confidence: float = Field(
        default=0.0, ge=0, le=1, description="Confiança geral da correlação"
    )

    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora do processamento",
    )

    notes: Optional[str] = Field(
        default=None, description="Observações sobre a correlação"
    )

    def add_match(self, match: CorrelationMatch) -> None:
        """Adiciona uma correspondência e recalcula a confiança geral."""
        self.matches.append(match)
        if self.matches:
            self.overall_confidence = sum(
                m.confidence for m in self.matches
            ) / len(self.matches)

    def get_summary(self) -> str:
        """Retorna um resumo da correlação para o relatório."""
        if not self.matches:
            return "Nenhuma correspondência encontrada"

        count = len(self.matches)
        avg_confidence = self.overall_confidence * 100

        return (
            f"{count} correspondência(s) encontrada(s) "
            f"com confiança média de {avg_confidence:.1f}%"
        )
