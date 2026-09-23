"""Modelo de sessão de preservação de evidências."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from lexproof.models.custody import CustodyChain
from lexproof.models.evidence import Evidence
from lexproof.models.hash_result import HashResult
from lexproof.models.timeline import TimelineEntry


class SessionMetadata(BaseModel):
    """Metadados opcionais da sessão de preservação."""

    client_name: Optional[str] = Field(
        default=None, description="Nome do cliente"
    )
    case_number: Optional[str] = Field(
        default=None, description="Número do processo"
    )
    responsible_technician: Optional[str] = Field(
        default=None, description="Responsável técnico pela preservação"
    )
    description: Optional[str] = Field(
        default=None, description="Descrição da sessão"
    )

    # Compatibilidade com código existente (deprecated)
    @property
    def case_id(self) -> str:
        """Alias para session_code (compatibilidade)."""
        return self.case_number or ""

    @property
    def title(self) -> str:
        """Alias para description (compatibilidade)."""
        return self.description or "Sem título"


class PreservationSession(BaseModel):
    """Sessão de preservação de evidências digitais.

    Uma sessão representa um conjunto de evidências preservadas
    para um caso jurídico específico.
    """

    # Identificador único
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Identificador único da sessão",
    )

    # Código amigável
    session_code: str = Field(
        default_factory=lambda: f"LEX-{uuid4().hex[:8].upper()}",
        description="Código amigável da sessão",
    )

    # Metadados opcionais
    metadata: SessionMetadata = Field(
        default_factory=SessionMetadata,
        description="Metadados opcionais da sessão",
    )

    # Evidências
    evidence_files: list[Evidence] = Field(
        default_factory=list, description="Lista de evidências preservadas"
    )

    # Timeline
    timeline: list[TimelineEntry] = Field(
        default_factory=list, description="Timeline cronológica das evidências"
    )

    # Integridade
    hash_results: list[HashResult] = Field(
        default_factory=list, description="Resultados de hash calculados"
    )

    # Índice técnico de qualidade
    quality_grade: Optional[str] = Field(
        default=None,
        description="Índice técnico de qualidade (A+, A, B, C, D)",
    )

    # Datas
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora de criação da sessão (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da última atualização (UTC)",
    )

    def add_evidence(self, evidence: Evidence) -> None:
        """Adiciona uma evidência à sessão."""
        self.evidence_files.append(evidence)
        self.updated_at = datetime.now(timezone.utc)

    def get_evidence_by_id(self, evidence_id: str) -> Optional[Evidence]:
        """Busca uma evidência pelo ID."""
        for ev in self.evidence_files:
            if ev.id == evidence_id:
                return ev
        return None

    def get_evidence_by_name(self, name: str) -> Optional[Evidence]:
        """Busca uma evidência pelo nome do arquivo (compatibilidade)."""
        for ev in self.evidence_files:
            if ev.file_name == name:
                return ev
        return None

    def get_evidence_count(self) -> int:
        """Retorna o número de evidências."""
        return len(self.evidence_files)

    def add_custody_chain(self, chain: CustodyChain) -> None:
        """Adiciona uma cadeia de custódia (compatibilidade)."""
        # Método mantido para compatibilidade, mas não faz nada
        # A cadeia de custódia agora é gerenciada separadamente
        pass

    def get_custody_chain(self, evidence_id: str) -> Optional[CustodyChain]:
        """Retorna uma cadeia de custódia (compatibilidade)."""
        # Método mantido para compatibilidade
        # Retorna None pois a cadeia de custódia agora é gerenciada separadamente
        return None

    def calculate_quality_grade(self) -> str:
        """Calcula o índice técnico de qualidade baseado nas evidências.

        Critérios:
        - A+: Exportação oficial + OCR + prints + timeline + hashes + timestamp
        - A: OCR + prints + timeline + hashes
        - B: Prints + timeline + hashes
        - C: Prints + hashes
        - D: Apenas prints sem processamento
        """
        if not self.evidence_files:
            return "D"

        has_export = any(
            hasattr(ev, "export_format") for ev in self.evidence_files
        )
        has_ocr = any(ev.ocr is not None for ev in self.evidence_files)
        has_timeline = len(self.timeline) > 0
        has_hashes = len(self.hash_results) > 0

        if has_export and has_ocr and has_timeline and has_hashes:
            return "A+"
        elif has_ocr and has_timeline and has_hashes:
            return "A"
        elif has_timeline and has_hashes:
            return "B"
        elif has_hashes:
            return "C"
        else:
            return "D"


# Alias para compatibilidade
CaseFile = PreservationSession
CaseMetadata = SessionMetadata
