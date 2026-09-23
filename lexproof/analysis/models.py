"""Modelos para o Smart Analysis Engine.

Define as estruturas de dados para análise técnica de evidências.
Toda análise é determinística, reproduzível e auditável.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class FindingSeverity(str, Enum):
    """Severidade de uma constatação."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class FindingCategory(str, Enum):
    """Categoria da constatação."""

    PLATFORM = "platform"
    CHRONOLOGY = "chronology"
    OVERLAP = "overlap"
    ORDER = "order"
    CONTINUITY = "continuity"
    DUPLICATE = "duplicate"
    QUALITY = "quality"
    METADATA = "metadata"
    INTEGRITY = "integrity"
    COMPLETENESS = "completeness"


@dataclass
class DecisionLog:
    """Log de decisão do motor de análise.

    Registra cada passo lógico para total transparência.
    """

    rule: str
    data_analyzed: str
    justification: str
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now())

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "rule": self.rule,
            "data_analyzed": self.data_analyzed,
            "justification": self.justification,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Finding:
    """Uma constatação da análise.

    Cada finding deve ser explicável e baseado em evidências.
    """

    category: FindingCategory
    severity: FindingSeverity
    title: str
    description: str
    evidence: str
    confidence: float
    recommendation: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "details": self.details,
        }


@dataclass
class TechnicalScores:
    """Índices técnicos da análise.

    Cada score é calculado por fórmula documentada.
    Nenhum valor é arbitrário.
    """

    ocr_score: float = 0.0
    timeline_score: float = 0.0
    correlation_score: float = 0.0
    metadata_score: float = 0.0
    integrity_score: float = 0.0
    completeness_score: float = 0.0
    technical_grade: str = "D"

    def calculate_grade(self) -> str:
        """Calcula o grau técnico baseado nos scores.

        Fórmula:
        - A+: score >= 90
        - A: score >= 80
        - B: score >= 70
        - C: score >= 60
        - D: score < 60

        O score final é a média ponderada:
        - Integridade: 25%
        - Completude: 25%
        - Timeline: 20%
        - OCR: 15%
        - Correlação: 10%
        - Metadados: 5%
        """
        weights = {
            "integrity": 0.25,
            "completeness": 0.25,
            "timeline": 0.20,
            "ocr": 0.15,
            "correlation": 0.10,
            "metadata": 0.05,
        }

        weighted_sum = (
            self.integrity_score * weights["integrity"]
            + self.completeness_score * weights["completeness"]
            + self.timeline_score * weights["timeline"]
            + self.ocr_score * weights["ocr"]
            + self.correlation_score * weights["correlation"]
            + self.metadata_score * weights["metadata"]
        )

        if weighted_sum >= 90:
            self.technical_grade = "A+"
        elif weighted_sum >= 80:
            self.technical_grade = "A"
        elif weighted_sum >= 70:
            self.technical_grade = "B"
        elif weighted_sum >= 60:
            self.technical_grade = "C"
        else:
            self.technical_grade = "D"

        return self.technical_grade

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "ocr_score": round(self.ocr_score, 1),
            "timeline_score": round(self.timeline_score, 1),
            "correlation_score": round(self.correlation_score, 1),
            "metadata_score": round(self.metadata_score, 1),
            "integrity_score": round(self.integrity_score, 1),
            "completeness_score": round(self.completeness_score, 1),
            "technical_grade": self.technical_grade,
        }


@dataclass
class ExecutiveSummary:
    """Resumo executivo da análise."""

    images_count: int = 0
    exports_count: int = 0
    participants_count: int = 0
    messages_count: int = 0
    period_days: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    integrity_ok: bool = True
    gaps_detected: int = 0
    duplicates_detected: int = 0
    overlaps_detected: int = 0
    recommendations_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "images_count": self.images_count,
            "exports_count": self.exports_count,
            "participants_count": self.participants_count,
            "messages_count": self.messages_count,
            "period_days": self.period_days,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "integrity_ok": self.integrity_ok,
            "gaps_detected": self.gaps_detected,
            "duplicates_detected": self.duplicates_detected,
            "overlaps_detected": self.overlaps_detected,
            "recommendations_count": self.recommendations_count,
        }


@dataclass
class EvidenceHealth:
    """Saúde do conjunto de evidências (health check)."""

    overall_score: float = 0.0
    integrity_status: str = "pending"
    timeline_status: str = "pending"
    ocr_status: str = "pending"
    correlation_status: str = "pending"
    metadata_status: str = "pending"
    gaps_count: int = 0
    duplicates_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "overall_score": round(self.overall_score, 1),
            "integrity_status": self.integrity_status,
            "timeline_status": self.timeline_status,
            "ocr_status": self.ocr_status,
            "correlation_status": self.correlation_status,
            "metadata_status": self.metadata_status,
            "gaps_count": self.gaps_count,
            "duplicates_count": self.duplicates_count,
        }


@dataclass
class EvidenceAnalysis:
    """Resultado completo da análise de evidências.

    Contém todas as constatações, scores, recomendações
    e logs de decisão para total transparência.
    """

    # Metadados
    analysis_id: str = ""
    analysis_date: datetime = field(default_factory=lambda: datetime.now())
    evidence_count: int = 0

    # Constatações
    findings: list[Finding] = field(default_factory=list)

    # Scores técnicos
    scores: TechnicalScores = field(default_factory=TechnicalScores)

    # Resumo executivo
    summary: ExecutiveSummary = field(default_factory=ExecutiveSummary)

    # Saúde do conjunto
    health: EvidenceHealth = field(default_factory=EvidenceHealth)

    # Recomendações
    recommendations: list[str] = field(default_factory=list)

    # Limitações
    limitations: list[str] = field(default_factory=list)

    # Logs de decisão
    decision_logs: list[DecisionLog] = field(default_factory=list)

    # Plataforma detectada
    detected_platform: str = "Desconhecida"

    def add_finding(self, finding: Finding) -> None:
        """Adiciona uma constatação."""
        self.findings.append(finding)

    def add_decision_log(self, log: DecisionLog) -> None:
        """Adiciona um log de decisão."""
        self.decision_logs.append(log)

    def add_recommendation(self, recommendation: str) -> None:
        """Adiciona uma recomendação."""
        if recommendation not in self.recommendations:
            self.recommendations.append(recommendation)

    def get_findings_by_severity(self, severity: FindingSeverity) -> list[Finding]:
        """Retorna constatações por severidade."""
        return [f for f in self.findings if f.severity == severity]

    def get_findings_by_category(self, category: FindingCategory) -> list[Finding]:
        """Retorna constatações por categoria."""
        return [f for f in self.findings if f.category == category]

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "analysis_id": self.analysis_id,
            "analysis_date": self.analysis_date.isoformat(),
            "evidence_count": self.evidence_count,
            "detected_platform": self.detected_platform,
            "findings": [f.to_dict() for f in self.findings],
            "scores": self.scores.to_dict(),
            "summary": self.summary.to_dict(),
            "health": self.health.to_dict(),
            "recommendations": self.recommendations,
            "limitations": self.limitations,
            "decision_logs": [dl.to_dict() for dl in self.decision_logs],
        }

    def generate_executive_summary_text(self) -> str:
        """Gera o texto do resumo executivo."""
        parts = []

        # Evidências preservadas
        parts.append("Foram preservadas:")
        if self.summary.images_count > 0:
            parts.append(f"  {self.summary.images_count} imagem(s)")
        if self.summary.exports_count > 0:
            parts.append(f"  {self.summary.exports_count} exportacao(oes) oficial(is)")
        if self.summary.participants_count > 0:
            parts.append(f"  {self.summary.participants_count} participante(s)")
        if self.summary.messages_count > 0:
            parts.append(f"  {self.summary.messages_count} mensagem(ns)")

        # Período
        if self.summary.period_days > 0:
            parts.append(f"\nPeriodo: {self.summary.period_days} dia(s)")

        # Integridade
        if self.summary.integrity_ok:
            parts.append("\nNao foram detectadas alteracoes na integridade dos arquivos recebidos.")
        else:
            parts.append("\nATENCAO: Foram detectadas alteracoes na integridade de alguns arquivos.")

        # Lacunas
        if self.summary.gaps_detected > 0:
            parts.append(
                f"\nFoi identificada(s) {self.summary.gaps_detected} lacuna(s) cronologica(s)."
            )

        # Duplicidades
        if self.summary.duplicates_detected > 0:
            parts.append(
                f"\nForam detectadas {self.summary.duplicates_detected} duplicidade(s)."
            )

        # Limitações
        parts.append(
            "\n\nA documentacao tecnica completa encontra-se nas paginas seguintes."
        )

        return "\n".join(parts)

    def generate_limitations_text(self) -> str:
        """Gera o texto de limitações."""
        return (
            "O LexProof documenta tecnicamente o estado das evidencias recebidas "
            "e os procedimentos executados durante sua preservacao.\n\n"
            "O software nao certifica autenticidade juridica, autoria das mensagens "
            "ou veracidade do conteudo.\n\n"
            "As conclusoes apresentadas referem-se exclusivamente aos aspectos "
            "tecnicos observados."
        )
