from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class HashAlgorithm(str, Enum):
    """Algoritmos de hash suportados pelo LexProof."""

    SHA256 = "sha256"
    SHA3_512 = "sha3_512"
    BLAKE3 = "blake3"


class HashResult(BaseModel):
    """Resultado de um cálculo de hash sobre um arquivo."""

    algorithm: HashAlgorithm = Field(..., description="Algoritmo utilizado no cálculo")
    hash_value: str = Field(..., description="Valor do hash em representação hexadecimal")
    file_path: Path = Field(..., description="Caminho do arquivo que foi hasheado")
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora em que o hash foi calculado (UTC)",
    )
    file_size: Optional[int] = Field(
        default=None,
        ge=0,
        description="Tamanho do arquivo em bytes no momento do cálculo",
    )
