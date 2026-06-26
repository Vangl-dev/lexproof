"""Modelo de caso e metadados."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from lexproof.models.custody import CustodyChain
from lexproof.models.evidence import EvidenceFile
from lexproof.models.hash_result import HashResult


class CaseMetadata(BaseModel):
    """Metadados de um caso jurídico."""

    case_id: str = Field(default_factory=lambda: uuid4().hex, description="ID único do caso")
    case_number: str = Field(default="", description="Número do processo")
    title: str = Field(default="Sem título", description="Título do caso")
    description: str = Field(default="", description="Descrição do caso")
    client_name: str = Field(default="", description="Nome do cliente")
    lawyer_name: str = Field(default="", description="Nome do advogado responsável")
    court: str = Field(default="", description="Forum/Tribunal")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora de criação do caso (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da última atualização (UTC)",
    )
    tags: list[str] = Field(default_factory=list, description="Tags do caso")


class CaseFile(BaseModel):
    """Representação completa de um caso com todas as evidências."""

    metadata: CaseMetadata = Field(default_factory=CaseMetadata, description="Metadados do caso")
    evidence_files: list[EvidenceFile] = Field(
        default_factory=list, description="Lista de evidências importadas"
    )
    hash_results: list[HashResult] = Field(
        default_factory=list, description="Resultados de hash calculados"
    )
    custody_chains: list[CustodyChain] = Field(
        default_factory=list, description="Cadeias de custódia"
    )

    def add_evidence(self, evidence: EvidenceFile) -> None:
        """Adiciona uma evidência ao caso."""
        self.evidence_files.append(evidence)
        self.metadata.updated_at = datetime.now(timezone.utc)

    def get_evidence_by_name(self, name: str) -> Optional[EvidenceFile]:
        """Busca uma evidência pelo nome do arquivo."""
        for ev in self.evidence_files:
            if ev.file_name == name:
                return ev
        return None

    def get_custody_chain(self, evidence_id: str) -> Optional[CustodyChain]:
        """Retorna a cadeia de custódia de uma evidência."""
        for chain in self.custody_chains:
            if chain.evidence_id == evidence_id:
                return chain
        return None

    def add_custody_chain(self, chain: CustodyChain) -> None:
        """Adiciona uma cadeia de custódia ao caso."""
        self.custody_chains.append(chain)
