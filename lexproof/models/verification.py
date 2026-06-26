from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    """Status possíveis de uma verificação de integridade."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"


class VerificationResult(BaseModel):
    """Resultado de uma verificação de integridade ou consistência."""

    id: UUID = Field(default_factory=uuid4, description="Identificador único da verificação")
    check_name: str = Field(..., description="Nome da verificação realizada")
    status: VerificationStatus = Field(..., description="Status final da verificação")
    expected: Optional[str] = Field(
        default=None,
        description="Valor esperado para a verificação",
    )
    actual: Optional[str] = Field(
        default=None,
        description="Valor efetivamente encontrado",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Detalhes adicionais sobre a verificação",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora em que a verificação foi executada (UTC)",
    )
