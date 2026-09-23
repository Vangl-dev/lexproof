"""Módulo de modelos de dados do LexProof."""

from lexproof.models.case import PreservationSession, SessionMetadata
from lexproof.models.correlation import CorrelationResult, CorrelationType
from lexproof.models.evidence import (
    ChatExportEvidence,
    Evidence,
    EvidenceMetadata,
    EvidenceSource,
    EvidenceType,
    ImageEvidence,
    OCRResult,
    PerceptualHashes,
)
from lexproof.models.hash_result import HashAlgorithm, HashResult
from lexproof.models.message import MessageType, WhatsAppMessage
from lexproof.models.quality_grade import GradeCriteria, GradeLevel, QualityGrade
from lexproof.models.timeline import TimelineEntry, TimelineEntryType

__all__ = [
    # Evidência (novo)
    "Evidence",
    "ImageEvidence",
    "ChatExportEvidence",
    "EvidenceType",
    "EvidenceSource",
    "EvidenceMetadata",
    "OCRResult",
    "PerceptualHashes",
    # Sessão (novo)
    "PreservationSession",
    "SessionMetadata",
    # Correlação (novo)
    "CorrelationResult",
    "CorrelationType",
    # Hash
    "HashAlgorithm",
    "HashResult",
    # Mensagem
    "MessageType",
    "WhatsAppMessage",
    # Grade (novo)
    "GradeCriteria",
    "GradeLevel",
    "QualityGrade",
    # Timeline
    "TimelineEntry",
    "TimelineEntryType",
]

# Compatibilidade com código existente (deprecated)
# Estes aliases serão removidos em versões futuras
EvidenceFile = Evidence
CaseFile = PreservationSession
CaseMetadata = SessionMetadata
