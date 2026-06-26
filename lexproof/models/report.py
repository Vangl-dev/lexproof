from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Tipos de relatório que o LexProof pode gerar."""

    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    MANIFEST = "manifest"
    ZIP = "zip"


class ReportConfig(BaseModel):
    """Configuração de um relatório a ser gerado pelo sistema."""

    report_type: ReportType = Field(..., description="Formato do relatório")
    output_path: Path = Field(..., description="Caminho de saída do relatório gerado")
    include_timeline: bool = Field(
        default=True,
        description="Se a linha do tempo deve ser incluída no relatório",
    )
    include_ocr: bool = Field(
        default=True,
        description="Se os resultados de OCR devem ser incluídos",
    )
    include_hashes: bool = Field(
        default=True,
        description="Se os hashes de integridade devem ser incluídos",
    )
    include_custody: bool = Field(
        default=True,
        description="Se a cadeia de custódia deve ser incluída",
    )
    include_verification: bool = Field(
        default=True,
        description="Se os resultados de verificação devem ser incluídos",
    )
    include_qr_code: bool = Field(
        default=False,
        description="Se um QR code de verificação deve ser gerado no relatório",
    )
    custom_notes: str = Field(
        default="",
        description="Notas personalizadas a serem incluídas no relatório",
    )
