"""Classe abstrata base para geração de relatórios."""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lexproof.models.case import CaseMetadata
from lexproof.models.custody import CustodyChain
from lexproof.models.evidence import EvidenceFile
from lexproof.models.hash_result import HashResult
from lexproof.models.ocr_result import OCRResult
from lexproof.models.report import ReportConfig
from lexproof.models.timeline import TimelineEntry
from lexproof.models.verification import VerificationResult

logger = logging.getLogger("lexproof.reports")


class BaseReportGenerator(ABC):
    """Classe abstrata base para todos os geradores de relatório.

    Fornece preparação comum de dados e interface abstrata
    que cada formato de relatório deve implementar.
    """

    def prepare_report_data(self, case_data: dict[str, Any]) -> dict[str, Any]:
        """Prepara os dados do caso para inclusão em qualquer formato de relatório.

        Extrae e organiza todas as seções do caso a partir do dicionário
        case_data, que deve conter as chaves esperadas pelo sistema.

        Args:
            case_data: Dicionário com os dados do caso. Chaves esperadas:
                - "metadata" (CaseMetadata): Metadados do caso
                - "evidence_files" (list[EvidenceFile]): Evidências
                - "hash_results" (list[HashResult]): Resultados de hash
                - "timeline" (list[TimelineEntry]): Entradas da linha do tempo
                - "ocr_results" (list[OCRResult]): Resultados de OCR
                - "verification_results" (list[VerificationResult]): Verificações
                - "custody_chains" (list[CustodyChain]): Cadeias de custódia
                - "inconsistencies" (list[str]): Inconsistências detectadas

        Returns:
            Dicionário organizado com todas as seções do relatório.
        """
        metadata = case_data.get("metadata")
        if isinstance(metadata, CaseMetadata):
            meta_dict = metadata.model_dump(mode="json")
        elif isinstance(metadata, dict):
            meta_dict = metadata
        else:
            meta_dict = {}

        evidence_files = case_data.get("evidence_files", [])
        evidence_section = []
        for ev in evidence_files:
            if isinstance(ev, EvidenceFile):
                evidence_section.append(ev.model_dump(mode="json"))
            elif isinstance(ev, dict):
                evidence_section.append(ev)

        hash_results = case_data.get("hash_results", [])
        hashes_section = []
        for hr in hash_results:
            if isinstance(hr, HashResult):
                hashes_section.append(hr.model_dump(mode="json"))
            elif isinstance(hr, dict):
                hashes_section.append(hr)

        timeline = case_data.get("timeline", [])
        timeline_section = []
        for entry in timeline:
            if isinstance(entry, TimelineEntry):
                timeline_section.append(entry.model_dump(mode="json"))
            elif isinstance(entry, dict):
                timeline_section.append(entry)

        ocr_results = case_data.get("ocr_results", [])
        ocr_section = []
        for ocr in ocr_results:
            if isinstance(ocr, OCRResult):
                ocr_section.append(ocr.model_dump(mode="json"))
            elif isinstance(ocr, dict):
                ocr_section.append(ocr)

        verification_results = case_data.get("verification_results", [])
        verification_section = []
        for vr in verification_results:
            if isinstance(vr, VerificationResult):
                verification_section.append(vr.model_dump(mode="json"))
            elif isinstance(vr, dict):
                verification_section.append(vr)

        custody_chains = case_data.get("custody_chains", [])
        custody_section = []
        for chain in custody_chains:
            if isinstance(chain, CustodyChain):
                custody_section.append(chain.model_dump(mode="json"))
            elif isinstance(chain, dict):
                custody_section.append(chain)

        inconsistencies = case_data.get("inconsistencies", [])

        report_data = {
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0.0",
            "app_version": self._get_app_version(),
            "metadata": meta_dict,
            "evidence_files": evidence_section,
            "hash_results": hashes_section,
            "timeline": timeline_section,
            "ocr_results": ocr_section,
            "verification_results": verification_section,
            "custody_chains": custody_section,
            "inconsistencies": inconsistencies,
            "summary": self._build_summary(
                evidence_section, hashes_section, timeline_section,
                verification_section, inconsistencies,
            ),
        }

        logger.debug(
            "Dados do relatório preparados: %d evidências, %d hashes, %d entradas na timeline",
            len(evidence_section),
            len(hashes_section),
            len(timeline_section),
        )
        return report_data

    @abstractmethod
    def generate(self, case_data: dict[str, Any], config: ReportConfig) -> Path:
        """Gera o relatório no formato específico.

        Args:
            case_data: Dicionário com os dados completos do caso.
            config: Configuração do relatório a ser gerado.

        Returns:
            Caminho do arquivo de relatório gerado.
        """
        ...

    def _get_app_version(self) -> str:
        """Retorna a versão atual do LexProof."""
        try:
            from lexproof import __version__
            return __version__
        except ImportError:
            return "unknown"

    def _build_summary(
        self,
        evidence_files: list[dict[str, Any]],
        hash_results: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        verification_results: list[dict[str, Any]],
        inconsistencies: list[str],
    ) -> dict[str, Any]:
        """Constrói um resumo estatístico do caso.

        Args:
            evidence_files: Lista de evidências em formato dict.
            hash_results: Lista de hashes em formato dict.
            timeline: Lista de entradas da timeline em formato dict.
            verification_results: Lista de verificações em formato dict.
            inconsistencies: Lista de inconsistências detectadas.

        Returns:
            Dicionário com estatísticas resumidas do caso.
        """
        pass_count = sum(
            1 for v in verification_results if v.get("status") == "pass"
        )
        fail_count = sum(
            1 for v in verification_results if v.get("status") == "fail"
        )
        warning_count = sum(
            1 for v in verification_results if v.get("status") == "warning"
        )

        return {
            "total_evidence_files": len(evidence_files),
            "total_hash_results": len(hash_results),
            "total_timeline_entries": len(timeline),
            "total_verification_checks": len(verification_results),
            "verification_pass": pass_count,
            "verification_fail": fail_count,
            "verification_warnings": warning_count,
            "total_inconsistencies": len(inconsistencies),
        }
