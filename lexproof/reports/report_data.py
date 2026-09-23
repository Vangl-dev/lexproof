"""Construtor único de report_data para o relatório PDF.

Fonte única de montagem do dicionário consumido por PDFReportGenerator.
Tanto o pipeline quanto a UI devem usar este módulo — não manter
montagens independentes de report_data em outros locais.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from lexproof.models.quality_grade import QualityGrade

if TYPE_CHECKING:
    from lexproof.models.correlation import CorrelationResult
    from lexproof.models.evidence import Evidence
    from lexproof.models.hash_result import HashResult
    from lexproof.models.message import WhatsAppMessage
    from lexproof.models.ocr_result import OCRResult
    from lexproof.models.timeline import TimelineEntry

# Chaves de algoritmo reconhecidas nos dicts de hash
_HASH_ALGO_KEYS = ("sha256", "sha3_512", "blake3")


def _map_evidence_files(evidences: list[Evidence]) -> list[dict[str, Any]]:
    evidence_files: list[dict[str, Any]] = []
    for ev in evidences:
        evidence_files.append(
            {
                "name": ev.file_name,
                "path": str(ev.file_path),
                "type": ev.evidence_type.value,
                "size": ev.file_size,
                "imported_at": ev.preservation_date.isoformat(),
                "thumbnail_path": str(ev.thumbnail) if ev.thumbnail else None,
            }
        )
    return evidence_files


def _map_hashes(hash_results: list[HashResult]) -> list[dict[str, str]]:
    hashes_by_file: dict[str, dict[str, str]] = {}
    for hr in hash_results:
        file_name = hr.file_path.name
        if file_name not in hashes_by_file:
            hashes_by_file[file_name] = {"file_name": file_name}
        hashes_by_file[file_name][hr.algorithm.value] = hr.hash_value
    return list(hashes_by_file.values())


def _compute_global_hash(hash_results: list[HashResult]) -> str:
    if not hash_results:
        return ""
    all_hashes = sorted(hr.hash_value for hr in hash_results)
    h = hashlib.sha256()
    for hash_val in all_hashes:
        h.update(hash_val.encode())
    return h.hexdigest()


def _map_verifications(verification_results: list[Any]) -> list[dict[str, Any]]:
    verifications: list[dict[str, Any]] = []
    for vr in verification_results:
        verifications.append(
            {
                "check_name": vr.check_name,
                "status": vr.status.value.upper(),
                "details": vr.details if hasattr(vr, "details") else {},
            }
        )
    return verifications


def _map_custody_stub(
    evidences: list[Evidence], responsible_technician: str
) -> list[dict[str, str]]:
    # Stub temporário — cadeia de custódia real fica para etapa posterior
    custody_chain: list[dict[str, str]] = []
    user = responsible_technician or "Sistema"
    for ev in evidences:
        custody_chain.append(
            {
                "timestamp": ev.preservation_date.isoformat(),
                "user": user,
                "action": "Importação",
                "details": f"Arquivo {ev.file_name} importado para preservação",
            }
        )
    return custody_chain


def _map_correlations(
    correlations: list[CorrelationResult],
    evidences: list[Evidence],
) -> list[dict[str, str]]:
    """Mapeia CorrelationResult real para o schema consumido pelo PDF.

    Campos do modelo: correlation_type, matches, overall_confidence.
    Schema do PDF: evidence_name, matched_messages, confidence, result.
    """
    id_to_name = {ev.id: ev.file_name for ev in evidences}
    mapped: list[dict[str, str]] = []

    for c in correlations:
        evidence_name = ""
        matched_parts: list[str] = []
        for m in c.matches:
            if not evidence_name:
                evidence_name = id_to_name.get(m.source_evidence_id, "")
            if m.target_text:
                matched_parts.append(m.target_text)

        matched_messages = "; ".join(matched_parts) if matched_parts else ""
        confidence = f"{c.overall_confidence:.0%}"
        result = c.get_summary() if c.matches else "Sem correspondência"

        mapped.append(
            {
                "evidence_name": evidence_name,
                "matched_messages": matched_messages,
                "confidence": confidence,
                "result": result,
            }
        )
    return mapped


def build_report_data(
    *,
    evidences: list[Evidence],
    messages: list[WhatsAppMessage],
    ocr_results: list[OCRResult],
    hash_results: list[HashResult],
    timeline: list[TimelineEntry],
    correlations: list[CorrelationResult],
    verification_results: list[Any],
    quality_grade: QualityGrade | str,
    session_id: str | None = None,
    client_name: str = "",
    case_number: str = "",
    responsible_technician: str = "",
    description: str | None = None,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Monta o report_data completo consumido pelo PDFReportGenerator.

    Args:
        evidences: Evidências catalogadas.
        messages: Mensagens reais do parser WhatsApp.
        ocr_results: Resultados OCR (models.ocr_result.OCRResult).
        hash_results: Resultados de hash.
        timeline: Timeline real do PipelineResult (não reconstruída).
        correlations: CorrelationResult do correlacionador.
        verification_results: Resultados de verificação.
        quality_grade: QualityGrade ou string do grau.
        session_id: Identificador da sessão/caso (opcional).
        client_name: Nome real do cliente, quando disponível.
        case_number: Número real do processo, quando disponível.
        responsible_technician: Responsável técnico real, quando disponível.
        description: Sobrescreve a descrição padrão (ex.: resumo da análise).
        created_at: Data/hora de criação do relatório.

    Returns:
        Dicionário no contrato consumido por PDFReportGenerator.
    """
    now = created_at or datetime.now(timezone.utc)

    if isinstance(quality_grade, QualityGrade):
        quality_level = quality_grade.level.value
    else:
        quality_level = str(quality_grade)

    case_id = session_id or f"LEX-{now.strftime('%Y%m%d%H%M%S')}"
    examiner = responsible_technician or "LexProof"
    title = f"Caso {case_number}" if case_number else "Caso de Preservação"

    if description is None:
        if client_name:
            description = f"Preservação de evidências digitais para {client_name}"
        else:
            description = "Preservação de evidências digitais"

    report_data: dict[str, Any] = {
        "metadata": {
            "case_id": case_id,
            "title": title,
            "description": description,
            "examiner": examiner,
            "organization": "LexProof Digital Forensics",
            "created_at": now.isoformat(),
            "client_name": client_name,
            "case_number": case_number,
            "quality_grade": quality_level,
        },
        "evidence_files": _map_evidence_files(evidences),
        "hashes": _map_hashes(hash_results),
        "global_hash": _compute_global_hash(hash_results),
        "custody_chain": _map_custody_stub(evidences, responsible_technician),
        "verifications": _map_verifications(verification_results),
        "inconsistencies": [],
        "correlations": _map_correlations(correlations, evidences),
        "ocr_results": list(ocr_results),
        "messages": list(messages),
        "timeline": list(timeline),
    }
    return report_data


def hash_algorithm_rows(hashes: list[dict[str, Any]]) -> list[list[str]]:
    """Expande dicts de hash em linhas [arquivo, algoritmo, valor] para o Apêndice A.

    Deriva o algoritmo apenas das chaves efetivamente presentes — não inventa dados.
    """
    rows: list[list[str]] = []
    for h in hashes:
        file_name = str(h.get("file_name", ""))
        algo_keys_present = [k for k in ("sha256", "sha3_512", "blake3") if h.get(k)]
        if algo_keys_present:
            for key in algo_keys_present:
                rows.append([file_name, key, str(h[key])])
            if h.get("hash_value"):
                rows.append([file_name, "hash", str(h["hash_value"])])
            continue
        if h.get("algorithm") and h.get("hash_value"):
            rows.append([file_name, str(h["algorithm"]), str(h["hash_value"])])
            continue
        if h.get("hash_value"):
            rows.append([file_name, "hash", str(h["hash_value"])])
    return rows
