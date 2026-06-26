"""Gerador de manifest.json com hashes e metadados de integridade."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lexproof.models.report import ReportConfig
from lexproof.reports.base import BaseReportGenerator

logger = logging.getLogger("lexproof.reports.manifest")


class ManifestReportGenerator(BaseReportGenerator):
    """Gera manifest.json seguindo especificação de manifest de integridade.

    O manifest contém hashes de todos os arquivos do caso, metadados
    de cada arquivo e um hash global de integridade que cobre todo o
    conteúdo do manifest.
    """

    def generate(self, case_data: dict[str, Any], config: ReportConfig) -> Path:
        """Gera o manifest.json com hashes e metadados.

        Cria um manifesto estruturado contendo:
        - Informações gerais do caso
        - Lista de arquivos com seus hashes e metadados
        - Hash de integridade global que cobre todo o conteúdo

        Args:
            case_data: Dicionário com os dados do caso.
            config: Configuração do relatório.

        Returns:
            Caminho do arquivo manifest.json gerado.
        """
        report_data = self.prepare_report_data(case_data)
        output_path = config.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        manifest: dict[str, Any] = {
            "manifest_version": "1.0",
            "schema_version": report_data.get("schema_version", "1.0.0"),
            "app_version": report_data.get("app_version", "unknown"),
            "generated_at": report_data.get("report_generated_at", ""),
            "generator": "LexProof Manifest Generator",
            "metadata": report_data.get("metadata", {}),
            "files": self._build_file_entries(report_data),
            "hash_results": self._build_hash_entries(report_data),
            "verification_summary": self._build_verification_summary(report_data),
            "integrity": {},
        }

        manifest["integrity"] = self._compute_global_integrity(manifest)

        output_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        logger.info("Manifest gerado: %s", output_path)
        return output_path

    def _build_file_entries(self, report_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Constrói a lista de entradas de arquivos do manifest.

        Args:
            report_data: Dados preparados do relatório.

        Returns:
            Lista de dicts com metadados de cada arquivo.
        """
        entries = []
        evidence_files = report_data.get("evidence_files", [])
        hash_results = report_data.get("hash_results", [])

        hash_map: dict[str, list[dict[str, Any]]] = {}
        for hr in hash_results:
            fp = str(hr.get("file_path", ""))
            if fp not in hash_map:
                hash_map[fp] = []
            hash_map[fp].append(hr)

        for ev in evidence_files:
            file_path = str(ev.get("file_path", ""))
            file_name = ev.get("file_name", "")
            file_size = ev.get("file_size", 0)
            ev_type = ev.get("evidence_type", "")
            imported_at = ev.get("imported_at")
            original_hash = ev.get("original_hash")

            file_hashes = hash_map.get(file_path, [])
            hashes = {}
            for fh in file_hashes:
                algo = str(fh.get("algorithm", ""))
                hashes[algo] = fh.get("hash_value", "")

            entry: dict[str, Any] = {
                "file_name": file_name,
                "file_path": file_path,
                "file_size": file_size,
                "evidence_type": str(ev_type),
                "imported_at": self._to_iso(imported_at),
                "hashes": hashes,
            }

            if original_hash:
                entry["original_hash"] = original_hash

            entries.append(entry)

        return entries

    def _build_hash_entries(self, report_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Constrói a lista de resultados de hash.

        Args:
            report_data: Dados preparados do relatório.

        Returns:
            Lista de dicts com resultados de hash.
        """
        entries = []
        for hr in report_data.get("hash_results", []):
            entry = {
                "algorithm": str(hr.get("algorithm", "")),
                "hash_value": hr.get("hash_value", ""),
                "file_path": str(hr.get("file_path", "")),
                "computed_at": self._to_iso(hr.get("computed_at")),
                "file_size": hr.get("file_size"),
            }
            entries.append(entry)
        return entries

    def _build_verification_summary(self, report_data: dict[str, Any]) -> dict[str, Any]:
        """Constrói o resumo de verificações.

        Args:
            report_data: Dados preparados do relatório.

        Returns:
            Dicionário com resumo das verificações.
        """
        verifications = report_data.get("verification_results", [])
        pass_count = sum(1 for v in verifications if v.get("status") == "pass")
        fail_count = sum(1 for v in verifications if v.get("status") == "fail")
        warning_count = sum(1 for v in verifications if v.get("status") == "warning")

        return {
            "total_checks": len(verifications),
            "passed": pass_count,
            "failed": fail_count,
            "warnings": warning_count,
            "all_passed": fail_count == 0 and warning_count == 0,
        }

    def _compute_global_integrity(self, manifest: dict[str, Any]) -> dict[str, str]:
        """Calcula o hash de integridade global do manifest.

        Cria uma representação canônica do manifest (sem o campo integrity)
        e calcula hash SHA-256 sobre ela.

        Args:
            manifest: Dicionário completo do manifest.

        Returns:
            Dicionário com o hash global e metadados.
        """
        content_for_hash = {
            k: v for k, v in manifest.items() if k != "integrity"
        }
        canonical = json.dumps(content_for_hash, sort_keys=True, ensure_ascii=False, default=str)
        global_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        return {
            "algorithm": "sha256",
            "hash_value": global_hash,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "covers": "full_manifest_content",
        }

    def _to_iso(self, value: Any) -> str | None:
        """Converte valor para string ISO 8601."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
