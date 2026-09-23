"""Modelo de índice técnico de qualidade da evidência."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GradeLevel(str, Enum):
    """Níveis de qualidade técnica."""

    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class GradeCriteria(BaseModel):
    """Critérios para cálculo do índice de qualidade."""

    has_official_export: bool = Field(
        default=False, description="Possui exportação oficial (WhatsApp, etc.)"
    )
    has_ocr: bool = Field(
        default=False, description="Possui OCR processado"
    )
    has_prints: bool = Field(
        default=False, description="Possui prints/screenshots"
    )
    has_timeline: bool = Field(
        default=False, description="Possui timeline cronológica"
    )
    has_hashes: bool = Field(
        default=False, description="Possui hashes de integridade"
    )
    has_timestamp: bool = Field(
        default=False, description="Possui timestamp de ancoramento"
    )
    has_correlation: bool = Field(
        default=False, description="Possui correlação print ↔ TXT"
    )


class QualityGrade(BaseModel):
    """Índice técnico de qualidade do conjunto de evidências.

    Este índice NÃO representa valor jurídico.
    Ele representa apenas a qualidade técnica do conjunto preservado.

    Critérios:
    - A+: Exportação oficial + OCR + prints + timeline + hashes + timestamp
    - A: OCR + prints + timeline + hashes
    - B: Prints + timeline + hashes
    - C: Prints + hashes
    - D: Apenas prints sem processamento
    """

    level: GradeLevel = Field(
        ..., description="Nível de qualidade (A+, A, B, C, D)"
    )

    criteria: GradeCriteria = Field(
        ..., description="Critérios utilizados para cálculo"
    )

    score: float = Field(
        ..., ge=0, le=100, description="Score numérico (0-100)"
    )

    description: str = Field(
        ..., description="Descrição do nível de qualidade"
    )

    recommendations: list[str] = Field(
        default_factory=list,
        description="Recomendações para melhorar a qualidade",
    )

    @classmethod
    def calculate(cls, criteria: GradeCriteria) -> QualityGrade:
        """Calcula o índice de qualidade baseado nos critérios.

        Args:
            criteria: Critérios de avaliação.

        Returns:
            Instância de QualityGrade com o nível calculado.
        """
        # Calcula score baseado nos critérios
        score = 0.0

        if criteria.has_official_export:
            score += 25.0
        if criteria.has_ocr:
            score += 20.0
        if criteria.has_prints:
            score += 15.0
        if criteria.has_timeline:
            score += 15.0
        if criteria.has_hashes:
            score += 15.0
        if criteria.has_timestamp:
            score += 10.0

        # Determina nível
        if score >= 90:
            level = GradeLevel.A_PLUS
            description = (
                "Excelente: Exportação oficial + OCR + prints + "
                "timeline + hashes + timestamp"
            )
        elif score >= 75:
            level = GradeLevel.A
            description = (
                "Ótimo: OCR + prints + timeline + hashes"
            )
        elif score >= 55:
            level = GradeLevel.B
            description = "Bom: Prints + timeline + hashes"
        elif score >= 35:
            level = GradeLevel.C
            description = "Regular: Prints + hashes"
        else:
            level = GradeLevel.D
            description = "Básico: Apenas prints sem processamento"

        # Gera recomendações
        recommendations = cls._generate_recommendations(criteria)

        return cls(
            level=level,
            criteria=criteria,
            score=score,
            description=description,
            recommendations=recommendations,
        )

    @staticmethod
    def _generate_recommendations(criteria: GradeCriteria) -> list[str]:
        """Gera recomendações para melhorar a qualidade.

        Args:
            criteria: Critérios atuais.

        Returns:
            Lista de recomendações.
        """
        recommendations = []

        if not criteria.has_official_export:
            recommendations.append(
                "Adicionar exportação oficial da conversa (WhatsApp, Telegram, etc.)"
            )
        if not criteria.has_ocr:
            recommendations.append(
                "Processar OCR nas imagens para extrair texto"
            )
        if not criteria.has_prints:
            recommendations.append(
                "Adicionar prints/screenshots das conversas"
            )
        if not criteria.has_timeline:
            recommendations.append(
                "Gerar timeline cronológica das evidências"
            )
        if not criteria.has_hashes:
            recommendations.append(
                "Calcular hashes de integridade (SHA-256, BLAKE3)"
            )
        if not criteria.has_timestamp:
            recommendations.append(
                "Ancorar timestamp para comprovar data de preservação"
            )

        return recommendations
