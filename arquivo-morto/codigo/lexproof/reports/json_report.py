"""Gerador de relatórios em formato JSON."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lexproof.models.report import ReportConfig
from lexproof.reports.base import BaseReportGenerator

logger = logging.getLogger("lexproof.reports.json")


class JSONReportGenerator(BaseReportGenerator):
    """Gera relatórios estruturados em formato JSON.

    Produz um arquivo JSON com todos os dados do caso em formato
    máquina-legível, incluindo timestamps em ISO 8601 e versão do schema.
    """

    def generate(self, case_data: dict[str, Any], config: ReportConfig) -> Path:
        """Gera o relatório JSON.

        Serializa todos os dados do caso em formato JSON estruturado,
        com timestamps em ISO 8601 e metadados do schema.

        Args:
            case_data: Dicionário com os dados do caso.
            config: Configuração do relatório.

        Returns:
            Caminho do arquivo JSON gerado.
        """
        report_data = self.prepare_report_data(case_data)
        output_path = config.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        json_report = {
            "schema_version": report_data.get("schema_version", "1.0.0"),
            "app_version": report_data.get("app_version", "unknown"),
            "report_generated_at": report_data.get("report_generated_at", ""),
            "report_type": "json",
            "config": {
                "include_timeline": config.include_timeline,
                "include_ocr": config.include_ocr,
                "include_hashes": config.include_hashes,
                "include_custody": config.include_custody,
                "include_verification": config.include_verification,
                "include_qr_code": config.include_qr_code,
            },
            "metadata": report_data.get("metadata", {}),
            "summary": report_data.get("summary", {}),
            "evidence_files": self._serialize_evidence(report_data.get("evidence_files", [])),
            "hash_results": self._serialize_hashes(report_data.get("hash_results", [])),
            "timeline": self._serialize_timeline(report_data.get("timeline", [])),
            "ocr_results": self._serialize_ocr(report_data.get("ocr_results", [])),
            "verification_results": self._serialize_verification(
                report_data.get("verification_results", [])
            ),
            "custody_chains": self._serialize_custody(
                report_data.get("custody_chains", [])
            ),
            "inconsistencies": report_data.get("inconsistencies", []),
        }

        if config.custom_notes:
            json_report["custom_notes"] = config.custom_notes

        output_path.write_text(
            json.dumps(json_report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        logger.info("Relatório JSON gerado: %s", output_path)
        return output_path

    def _serialize_evidence(self, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Serializa evidências garantindo formato JSON-safe."""
        result = []
        for ev in evidence:
            serialized = {
                "file_name": ev.get("file_name", ""),
                "file_path": str(ev.get("file_path", "")),
                "file_size": ev.get("file_size", 0),
                "evidence_type": str(ev.get("evidence_type", "")),
                "imported_at": self._to_iso(ev.get("imported_at")),
                "original_hash": ev.get("original_hash"),
                "description": ev.get("description", ""),
                "tags": ev.get("tags", []),
            }
            result.append(serialized)
        return result

    def _serialize_hashes(self, hashes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Serializa resultados de hash garantindo formato JSON-safe."""
        result = []
        for hr in hashes:
            serialized = {
                "algorithm": str(hr.get("algorithm", "")),
                "hash_value": hr.get("hash_value", ""),
                "file_path": str(hr.get("file_path", "")),
                "computed_at": self._to_iso(hr.get("computed_at")),
                "file_size": hr.get("file_size"),
            }
            result.append(serialized)
        return result

    def _serialize_timeline(self, timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Serializa entradas da timeline garantindo formato JSON-safe."""
        result = []
        for entry in timeline:
            serialized = {
                "id": str(entry.get("id", "")),
                "entry_type": str(entry.get("entry_type", "")),
                "timestamp": self._to_iso(entry.get("timestamp")),
                "sender": entry.get("sender"),
                "content": entry.get("content", ""),
                "source_file": entry.get("source_file"),
                "line_in_source": entry.get("line_in_source"),
                "position_in_image": entry.get("position_in_image"),
                "notes": entry.get("notes", ""),
                "inconsistencies": entry.get("inconsistencies", []),
            }
            result.append(serialized)
        return result

    def _serialize_ocr(self, ocr_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Serializa resultados de OCR garantindo formato JSON-safe."""
        result = []
        for ocr in ocr_results:
            serialized = {
                "id": str(ocr.get("id", "")),
                "source_image": ocr.get("source_image", ""),
                "extracted_text": ocr.get("extracted_text", ""),
                "confidence": ocr.get("confidence", 0.0),
                "detected_timestamps": ocr.get("detected_timestamps", []),
                "detected_senders": ocr.get("detected_senders", []),
                "detected_messages": ocr.get("detected_messages", []),
                "engine_used": ocr.get("engine_used", ""),
                "processing_time": ocr.get("processing_time", 0.0),
            }
            result.append(serialized)
        return result

    def _serialize_verification(
        self, verifications: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Serializa resultados de verificação garantindo formato JSON-safe."""
        result = []
        for vr in verifications:
            serialized = {
                "id": str(vr.get("id", "")),
                "check_name": vr.get("check_name", ""),
                "status": str(vr.get("status", "")),
                "expected": vr.get("expected"),
                "actual": vr.get("actual"),
                "details": vr.get("details", {}),
                "timestamp": self._to_iso(vr.get("timestamp")),
            }
            result.append(serialized)
        return result

    def _serialize_custody(self, chains: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Serializa cadeias de custódia garantindo formato JSON-safe."""
        result = []
        for chain in chains:
            events = []
            for ev in chain.get("events", []):
                events.append({
                    "event_type": str(ev.get("event_type", "")),
                    "description": ev.get("description", ""),
                    "timestamp": self._to_iso(ev.get("timestamp")),
                    "hash_before": ev.get("hash_before"),
                    "hash_after": ev.get("hash_after"),
                    "operator": ev.get("operator", "system"),
                    "metadata": ev.get("metadata", {}),
                })
            serialized = {
                "evidence_id": chain.get("evidence_id", ""),
                "events": events,
                "created_at": self._to_iso(chain.get("created_at")),
            }
            result.append(serialized)
        return result

    def _to_iso(self, value: Any) -> str | None:
        """Converte um valor para string ISO 8601.

        Args:
            value: Valor a ser convertido (datetime, string, ou None).

        Returns:
            String ISO 8601 ou None se o valor for None.
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
