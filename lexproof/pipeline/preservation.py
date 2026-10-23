"""Pipeline central de preservação de evidências do LexProof.

Este módulo implementa o pipeline completo que executa automaticamente:
1. Catalogação das evidências
2. Leitura de metadados
3. Cálculo de SHA-256
4. Cálculo de BLAKE3
5. OCR das imagens
6. Parser da exportação do WhatsApp
7. Correlação entre OCR e TXT
8. Reconstrução cronológica
9. Classificação técnica da evidência
10. Geração do relatório
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from lexproof.config.paths import Paths
from lexproof.correlation.correlator import EvidenceCorrelator
from lexproof.acquisition.email_intake import EmailEvidence, read_email, write_dkim_archive
from lexproof.acquisition.excerpt import (
    EXCERPT_RECORD_NAME,
    ExcerptResult,
    discard_outside,
    make_excerpt,
    write_excerpt_record,
)
from lexproof.blockchain.rfc3161 import RFC3161Anchor, default_anchors
from lexproof.crypto.hasher import FileHasher
from lexproof.crypto.seal import SealResult, seal_case
from lexproof.models.correlation import CorrelationResult
from lexproof.models.evidence import (
    ChatExportEvidence,
    Evidence,
    EvidenceMetadata,
    EvidenceSource,
    EvidenceType,
    ImageEvidence,
)
from lexproof.models.hash_result import HashResult
from lexproof.models.message import WhatsAppMessage
from lexproof.models.ocr_result import OCRResult
from lexproof.models.quality_grade import GradeCriteria, QualityGrade
from lexproof.models.timeline import TimelineEntry
from lexproof.ocr.processor import OCRProcessor
from lexproof.parsers.whatsapp_parser import WhatsAppParser
from lexproof.reports.methodology import MethodologyGenerator
from lexproof.timeline.timeline_builder import TimelineBuilder
from lexproof.triangulation.contact_profile import ContactLink, link_profiles, read_contact_profile
from lexproof.triangulation.matcher import ScreenshotCheck, ScreenshotMatcher, export_contact_name
from lexproof.triangulation.stitcher import ScreenshotStitcher, StitchResult
from lexproof.triangulation.screenshot_reader import ScreenshotReader, ScreenshotReading
from lexproof.utils.file_utils import detect_evidence_type
from lexproof.verification.checker import VerificationChecker

logger = logging.getLogger(__name__)


class PipelineStepStatus(str, Enum):
    """Status de um passo do pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStep:
    """Representa um passo do pipeline."""

    name: str
    description: str
    status: PipelineStepStatus = PipelineStepStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Resultado completo da execução do pipeline."""

    session_id: str
    start_time: datetime
    end_time: datetime
    total_duration_seconds: float
    steps: list[PipelineStep]
    evidence_count: int
    images_count: int
    exports_count: int
    ocr_results: list[OCRResult]
    hash_results: list[HashResult]
    timeline: list[TimelineEntry]
    correlations: list[CorrelationResult]
    quality_grade: QualityGrade
    messages: list[WhatsAppMessage]
    verification_results: list[Any]
    evidence_files: list[Evidence] = field(default_factory=list)
    report_path: Optional[Path] = None
    seal: Optional[SealResult] = None
    screenshot_checks: list[ScreenshotCheck] = field(default_factory=list)
    emails: list[EmailEvidence] = field(default_factory=list)
    stitch: Optional[StitchResult] = None
    excerpt: Optional[ExcerptResult] = None
    contacts: list[ContactLink] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PreservationPipeline:
    """Pipeline central de preservação de evidências.

    Executa todas as etapas de preservação automaticamente:
    importação, hashing, OCR, parsing, correlação, timeline,
    classificação e geração de relatório.
    """

    STEP_TIMEOUT_SECONDS = 300

    def __init__(self, anchors: Optional[list[RFC3161Anchor]] = None) -> None:
        """Inicializa o pipeline.

        Args:
            anchors: TSAs em ordem de preferencia (padrao: FreeTSA, DigiCert, Sectigo).
        """
        self._anchors = anchors if anchors is not None else default_anchors()
        self._screenshot_reader = ScreenshotReader()
        self._hasher = FileHasher()
        self._ocr_processor = OCRProcessor()
        self._whatsapp_parser = WhatsAppParser()
        self._timeline_builder = TimelineBuilder()
        self._correlator = EvidenceCorrelator()
        self._verification_checker = VerificationChecker()
        self._methodology_generator = MethodologyGenerator()

        self._steps: list[PipelineStep] = []
        self._progress_callback: Optional[Callable[[str, PipelineStepStatus, float], None]] = None
        self._step_timings: dict[str, float] = {}
        self._failed_steps: list[str] = []
        self._skipped_steps: list[str] = []
        self._case_dir: Path | None = None
        self._session_code: str | None = None
        self._emails: list[EmailEvidence] = []
        self._zip_members: dict[Path, list[Path]] = {}
        self._all_messages: list[WhatsAppMessage] | None = None
        self._export_source: Path | None = None

    def set_progress_callback(self, callback: Callable[[str, PipelineStepStatus, float], None]) -> None:
        """Define callback para atualização de progresso.

        Args:
            callback: Função chamada com (nome_do_passo, status, progresso_percentual).
        """
        self._progress_callback = callback

    def _notify_progress(self, step_name: str, status: PipelineStepStatus, progress: float) -> None:
        """Notifica o callback de progresso."""
        if self._progress_callback:
            self._progress_callback(step_name, status, progress)

    def _add_step(self, name: str, description: str) -> PipelineStep:
        """Adiciona um passo ao pipeline."""
        step = PipelineStep(name=name, description=description)
        self._steps.append(step)
        return step

    def _start_step(self, step: PipelineStep) -> None:
        """Inicia a execução de um passo."""
        step.status = PipelineStepStatus.RUNNING
        step.start_time = time.time()
        self._notify_progress(step.name, PipelineStepStatus.RUNNING, 0.0)

    def _complete_step(self, step: PipelineStep, result: Any = None) -> None:
        """Completa a execução de um passo."""
        step.status = PipelineStepStatus.COMPLETED
        step.end_time = time.time()
        step.duration_seconds = step.end_time - (step.start_time or step.end_time)
        step.result = result
        self._notify_progress(step.name, PipelineStepStatus.COMPLETED, 100.0)

    def _fail_step(self, step: PipelineStep, error: str) -> None:
        """Marca um passo como falho."""
        step.status = PipelineStepStatus.FAILED
        step.end_time = time.time()
        step.duration_seconds = step.end_time - (step.start_time or step.end_time)
        step.error = error
        self._failed_steps.append(step.name)
        self._step_timings[step.name] = step.duration_seconds
        logger.error("FALHA em %s: %s (%.1fs)", step.name, error, step.duration_seconds)
        self._notify_progress(step.name, PipelineStepStatus.FAILED, 0.0)

    def _skip_step(self, step: PipelineStep, reason: str) -> None:
        """Marca um passo como pulado."""
        step.status = PipelineStepStatus.SKIPPED
        step.warnings.append(reason)
        self._skipped_steps.append(step.name)
        step.end_time = time.time()
        step.duration_seconds = step.end_time - (step.start_time or step.end_time)
        self._step_timings[step.name] = step.duration_seconds
        logger.warning("IGNORADO %s: %s (%.1fs)", step.name, reason, step.duration_seconds)
        self._notify_progress(step.name, PipelineStepStatus.SKIPPED, 100.0)

    def _check_timeout(self, step: PipelineStep) -> bool:
        """Verifica se o passo excedeu o timeout."""
        if step.start_time is None:
            return False
        elapsed = time.time() - step.start_time
        if elapsed > self.STEP_TIMEOUT_SECONDS:
            self._fail_step(step, f"Timeout apos {self.STEP_TIMEOUT_SECONDS}s")
            return True
        return False

    def execute(
        self,
        evidence_paths: list[Path],
        *,
        client_name: str = "",
        case_number: str = "",
        responsible_technician: str = "",
        output_dir: Path | None = None,
        case_dir: Path | None = None,
        session_code: str | None = None,
        timestamp: bool = True,
        received_via: str = "",
        period: tuple[date, date] | None = None,
        discard_outside_period: bool = False,
    ) -> PipelineResult:
        """Executa o pipeline completo de preservação.

        Args:
            evidence_paths: Lista de caminhos das evidências para preservar
                (preferir cópias permanentes em ``evidence/original/``).
            client_name: Nome do cliente (opcional).
            case_number: Número do processo (opcional).
            responsible_technician: Responsável técnico (opcional).
            output_dir: Diretório de saída para relatórios (opcional).
            case_dir: Diretório do caso (raiz com ``case.lexproof.json``).
                Usado para extrair ZIP em ``evidence/extracted/`` permanente.
            session_code: Código da sessão (fallback para ``Paths``).
            timestamp: Solicita carimbo de tempo do manifesto (requer internet).
            received_via: Como os arquivos chegaram (ex.: enviados pelo cliente).
            period: Periodo de interesse (inicio, fim). O relatorio mostra so as
                mensagens dele; o recorte e verificavel contra o arquivo completo.
            discard_outside_period: Apaga da pasta do caso a conversa completa e as
                midias fora do periodo, guardando apenas os hashes.

        Returns:
            Resultado completo da execução do pipeline.
        """
        start_time = datetime.now(timezone.utc)
        total_start = time.time()
        errors: list[str] = []
        warnings: list[str] = []

        self._case_dir = Path(case_dir) if case_dir is not None else None
        self._session_code = session_code
        self._emails = []
        self._zip_members = {}
        self._all_messages = None
        self._export_source = None
        self._steps = []
        self._failed_steps = []
        self._skipped_steps = []
        self._step_timings = {}
        self._methodology_generator.start()

        logger.info("=" * 60)
        logger.info("INICIO DO PIPELINE - %d arquivo(s)", len(evidence_paths))
        for p in evidence_paths:
            logger.info("  Arquivo: %s", p.name)
        logger.info("=" * 60)

        # Passo 1: Catalogação das evidências
        step_catalog = self._add_step("Catalogação", "Catalogação das evidências importadas")
        self._start_step(step_catalog)
        logger.info("[1/10] Catalogacao iniciada...")
        try:
            evidences = self._catalog_evidence(evidence_paths)
            self._complete_step(step_catalog, evidences)
            self._methodology_generator.add_step(
                "Catalogação",
                f"{len(evidences)} evidência(s) catalogada(s)",
            )
            logger.info("[1/10] Catalogacao OK: %d evidencia(s)", len(evidences))
        except Exception as e:
            self._fail_step(step_catalog, str(e))
            errors.append(f"Erro na catalogação: {e}")
            evidences = []

        # Passo 2: Leitura de metadados
        step_metadata = self._add_step("Metadados", "Extração de metadados das evidências")
        self._start_step(step_metadata)
        logger.info("[2/10] Metadados iniciados...")
        try:
            self._extract_metadata(evidences)
            self._complete_step(step_metadata)
            self._methodology_generator.add_step(
                "Metadados",
                "Metadados extraídos de todas as evidências",
            )
            logger.info("[2/10] Metadados OK")
        except Exception as e:
            self._fail_step(step_metadata, str(e))
            warnings.append(f"Aviso na extração de metadados: {e}")
            logger.warning("[2/10] Metadados com aviso: %s", e)

        # Passo 3: Cálculo de hashes
        step_hashes = self._add_step("Hashes", "Cálculo de SHA-256 e BLAKE3")
        self._start_step(step_hashes)
        logger.info("[3/10] Hashes iniciados...")
        try:
            hash_results = self._compute_hashes(evidences)
            self._complete_step(step_hashes, hash_results)
            self._methodology_generator.add_step(
                "Hashes",
                f"{len(hash_results)} hash(es) calculado(s)",
                details="Algoritmos: SHA-256, BLAKE3",
            )
            logger.info("[3/10] Hashes OK: %d calculado(s)", len(hash_results))
        except Exception as e:
            self._fail_step(step_hashes, str(e))
            errors.append(f"Erro no cálculo de hashes: {e}")
            hash_results = []
            logger.error("[3/10] Hashes FALHOU: %s", e)

        # Recorte do periodo de interesse (antes do selo, que registra o resultado)
        excerpt: Optional[ExcerptResult] = None
        if period is not None:
            step_cut = self._add_step("Recorte do período", "Recorte da conversa ao período de interesse")
            self._start_step(step_cut)
            try:
                excerpt, evidences, hash_results = self._cut_period(
                    evidences, evidence_paths, hash_results, period, discard_outside_period
                )
                self._complete_step(step_cut, excerpt)
            except Exception as e:
                self._fail_step(step_cut, str(e))
                warnings.append(f"Recorte do período não aplicado: {e}")

        # Selo: manifesto dos originais + carimbo de tempo
        seal: Optional[SealResult] = None
        step_seal = self._add_step("Carimbo de tempo", "Manifesto de hashes e carimbo de tempo")
        self._start_step(step_seal)
        if self._case_dir is None:
            self._skip_step(step_seal, "Sem pasta de caso para gravar o manifesto")
        else:
            try:
                originals = [p for p in evidence_paths if Path(p).is_file()]
                if excerpt is not None:
                    originals += [excerpt.excerpt_path, *excerpt.kept_attachments]
                    originals.append(self._case_dir / "preservacao" / EXCERPT_RECORD_NAME)
                dkim_archive = write_dkim_archive(
                    self._emails, self._case_dir / "preservacao" / "dkim-chaves.txt"
                )
                if dkim_archive is not None:
                    originals.append(dkim_archive)
                seal = seal_case(
                    self._case_dir,
                    originals,
                    anchors=self._anchors if timestamp else None,
                    case_label=case_number or client_name,
                )
                if seal.timestamp_error:
                    warnings.append(f"Carimbo de tempo não obtido: {seal.timestamp_error}")
                self._complete_step(step_seal, seal)
                self._methodology_generator.add_step(
                    "Carimbo de tempo",
                    "Manifesto carimbado por " + seal.timestamp.tsa_url
                    if seal.timestamp else "Manifesto gerado sem carimbo de tempo",
                )
            except Exception as e:
                self._fail_step(step_seal, str(e))
                warnings.append(f"Aviso no selo de preservação: {e}")

        # Passo 4: OCR das imagens
        step_ocr = self._add_step("OCR", "Reconhecimento óptico de caracteres")
        self._start_step(step_ocr)
        logger.info("[4/10] OCR iniciado...")
        try:
            ocr_results = self._process_ocr(evidences)
            self._complete_step(step_ocr, ocr_results)
            self._methodology_generator.add_step(
                "OCR",
                f"{len(ocr_results)} imagem(ns) processada(s) com OCR",
            )
            logger.info("[4/10] OCR OK: %d processada(s)", len(ocr_results))
        except Exception as e:
            self._fail_step(step_ocr, str(e))
            warnings.append(f"Aviso no processamento OCR: {e}")
            ocr_results = []
            logger.warning("[4/10] OCR com aviso: %s", e)

        # Passo 5: Parser da exportação do WhatsApp
        step_parser = self._add_step("Parser", "Parsing da exportação do WhatsApp")
        self._start_step(step_parser)
        logger.info("[5/10] Parser WhatsApp iniciado...")
        try:
            messages = self._parse_whatsapp(evidences)
            self._complete_step(step_parser, messages)
            self._methodology_generator.add_step(
                "Parser WhatsApp",
                f"{len(messages)} mensagem(ns) extraída(s)",
            )
            logger.info("[5/10] Parser OK: %d mensagem(s)", len(messages))
        except Exception as e:
            self._fail_step(step_parser, str(e))
            warnings.append(f"Aviso no parser WhatsApp: {e}")
            messages = []
            logger.warning("[5/10] Parser com aviso: %s", e)

        # Conferencia dos prints com a exportacao
        screenshot_checks: list[ScreenshotCheck] = []
        stitch: Optional[StitchResult] = None
        contacts: list[ContactLink] = []
        step_tri = self._add_step("Conferência dos prints", "Confronto dos prints entre si e com a conversa exportada")
        self._start_step(step_tri)
        try:
            direct_prints = list(evidence_paths) + [
                a.path for em in self._emails for a in em.attachments
            ]
            readings, others = self._read_screenshots(evidences, direct_prints)
            if readings:
                stitch = ScreenshotStitcher().stitch(readings)
            screenshot_checks = self._check_screenshots(evidences, readings, messages)
            contacts = self._link_contacts(evidences, others, readings)
            self._complete_step(step_tri, screenshot_checks)
            self._methodology_generator.add_step(
                "Conferência dos prints",
                f"{len(readings)} print(s) conferido(s) entre si; "
                f"{len(screenshot_checks)} com a exportação",
            )
        except Exception as e:
            self._fail_step(step_tri, str(e))
            warnings.append(f"Aviso na conferência dos prints: {e}")

        # Passo 6: Correlação entre OCR e TXT
        step_correlation = self._add_step("Correlação", "Correlação entre prints e exportação")
        self._start_step(step_correlation)
        logger.info("[6/10] Correlacao iniciada...")
        try:
            correlations = self._correlate(evidences)
            self._complete_step(step_correlation, correlations)
            self._methodology_generator.add_step(
                "Correlação",
                f"{len(correlations)} correlação(ões) encontrada(s)",
            )
            logger.info("[6/10] Correlacao OK: %d encontrada(s)", len(correlations))
        except Exception as e:
            self._fail_step(step_correlation, str(e))
            warnings.append(f"Aviso na correlação: {e}")
            correlations = []
            logger.warning("[6/10] Correlacao com aviso: %s", e)

        # Passo 7: Reconstrução cronológica
        step_timeline = self._add_step("Timeline", "Reconstrução da linha do tempo")
        self._start_step(step_timeline)
        logger.info("[7/10] Timeline iniciada...")
        try:
            timeline = self._build_timeline(messages, ocr_results)
            self._complete_step(step_timeline, timeline)
            self._methodology_generator.add_step(
                "Timeline",
                f"{len(timeline)} entrada(s) na linha do tempo",
            )
            logger.info("[7/10] Timeline OK: %d entrada(s)", len(timeline))
        except Exception as e:
            self._fail_step(step_timeline, str(e))
            warnings.append(f"Aviso na timeline: {e}")
            timeline = []
            logger.warning("[7/10] Timeline com aviso: %s", e)

        # Passo 8: Verificação de integridade
        step_verification = self._add_step("Verificação", "Verificação de integridade e consistência")
        self._start_step(step_verification)
        logger.info("[8/10] Verificacao iniciada...")
        try:
            verification_results = self._verify(evidences, ocr_results, messages)
            self._complete_step(step_verification, verification_results)
            self._methodology_generator.add_step(
                "Verificação",
                f"{len(verification_results)} verificação(ões) executada(s)",
            )
            logger.info("[8/10] Verificacao OK: %d executada(s)", len(verification_results))
        except Exception as e:
            self._fail_step(step_verification, str(e))
            warnings.append(f"Aviso na verificação: {e}")
            verification_results = []
            logger.warning("[8/10] Verificacao com aviso: %s", e)

        # Passo 9: Classificação técnica
        step_grade = self._add_step("Classificação", "Classificação técnica da qualidade")
        self._start_step(step_grade)
        logger.info("[9/10] Classificacao iniciada...")
        try:
            quality_grade = self._calculate_quality_grade(
                evidences, ocr_results, timeline, correlations, hash_results
            )
            self._complete_step(step_grade, quality_grade)
            self._methodology_generator.add_step(
                "Classificação",
                f"Grau técnico: {quality_grade.level.value}",
                details=quality_grade.description,
            )
            logger.info("[9/10] Classificacao OK: %s", quality_grade.level.value)
        except Exception as e:
            self._fail_step(step_grade, str(e))
            warnings.append(f"Aviso na classificação: {e}")
            quality_grade = QualityGrade.calculate(GradeCriteria())
            logger.warning("[9/10] Classificacao com aviso: %s", e)

        # Passo 10: Geração do relatório
        step_report = self._add_step("Relatório", "Geração do relatório de preservação")
        self._start_step(step_report)
        logger.info("[10/10] Relatorio iniciado...")
        try:
            report_path = self._generate_report(
                evidences, messages, ocr_results, hash_results,
                timeline, correlations, verification_results,
                quality_grade, output_dir,
                client_name=client_name,
                case_number=case_number,
                responsible_technician=responsible_technician,
                seal=seal,
                screenshot_checks=screenshot_checks,
                received_via=received_via,
                emails=self._emails,
                stitch=stitch,
                excerpt=excerpt,
                contacts=contacts,
            )
            self._complete_step(step_report, report_path)
            self._methodology_generator.add_step(
                "Relatório",
                f"Relatório gerado em {report_path}",
            )
            logger.info("[10/10] Relatorio OK: %s", report_path)
        except Exception as e:
            self._fail_step(step_report, str(e))
            errors.append(f"Erro na geração do relatório: {e}")
            report_path = None
            logger.error("[10/10] Relatorio FALHOU: %s", e)

        # Resultado final
        end_time = datetime.now(timezone.utc)
        total_duration = time.time() - total_start

        # Contar evidências por tipo
        images_count = sum(1 for e in evidences if isinstance(e, ImageEvidence))
        exports_count = sum(1 for e in evidences if isinstance(e, ChatExportEvidence))

        result = PipelineResult(
            session_id=f"LEX-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            start_time=start_time,
            end_time=end_time,
            total_duration_seconds=total_duration,
            steps=self._steps,
            evidence_count=len(evidences),
            images_count=images_count,
            exports_count=exports_count,
            ocr_results=ocr_results,
            hash_results=hash_results,
            timeline=timeline,
            correlations=correlations,
            quality_grade=quality_grade,
            messages=messages,
            verification_results=verification_results,
            evidence_files=evidences,
            report_path=report_path,
            seal=seal,
            screenshot_checks=screenshot_checks,
            emails=list(self._emails),
            stitch=stitch,
            excerpt=excerpt,
            contacts=contacts,
            errors=errors,
            warnings=warnings,
        )

        logger.info("=" * 60)
        logger.info("PIPELINE CONCLUIDO em %.2f segundos", total_duration)
        logger.info("  Evidencias: %d", len(evidences))
        logger.info("  Grau: %s", quality_grade.level.value)
        if self._failed_steps:
            logger.warning("  Etapas com FALHA: %s", ", ".join(self._failed_steps))
        if self._skipped_steps:
            logger.warning("  Etapas IGNORADAS: %s", ", ".join(self._skipped_steps))
        if self._step_timings:
            logger.info("  Tempos por etapa:")
            for step_name, duration in self._step_timings.items():
                logger.info("    %s: %.1fs", step_name, duration)
        logger.info("=" * 60)

        return result

    def _create_evidence_instance(self, path: Path) -> Evidence:
        """Cria a instância apropriada de Evidence com base no tipo detectado."""
        file_size = path.stat().st_size
        ext = path.suffix.lower()
        evidence_type = detect_evidence_type(path)

        if evidence_type == EvidenceType.IMAGE:
            width, height = self._get_image_dimensions(path)
            return ImageEvidence(
                file_path=path,
                file_name=path.name,
                file_size=file_size,
                evidence_type=EvidenceType.IMAGE,
                source=EvidenceSource.MANUAL_UPLOAD,
                sha256="",
                blake3="",
                width=width,
                height=height,
                format=ext.lstrip(".").upper(),
            )
        elif ext == ".txt" and self._is_whatsapp_export(path):
            return ChatExportEvidence(
                file_path=path,
                file_name=path.name,
                file_size=file_size,
                evidence_type=EvidenceType.CHAT_EXPORT,
                source=EvidenceSource.WHATSAPP_EXPORT,
                sha256="",
                blake3="",
                export_format="whatsapp",
                message_count=0,
            )
        else:
            return Evidence(
                file_path=path,
                file_name=path.name,
                file_size=file_size,
                evidence_type=evidence_type,
                source=EvidenceSource.MANUAL_UPLOAD,
                sha256="",
                blake3="",
            )

    def _catalog_evidence(self, paths: list[Path]) -> list[Evidence]:
        """Cataloga as evidências importadas."""
        evidences = []

        for path in paths:
            if not path.exists():
                logger.warning("Arquivo não encontrado: %s", path)
                continue

            # Se for um ZIP, extrair e processar seu conteúdo
            if path.suffix.lower() == ".zip":
                extracted_evidences = self._process_zip_file(path)
                evidences.extend(extracted_evidences)
                continue

            evidences.append(self._create_evidence_instance(path))
            if path.suffix.lower() == ".eml":
                evidences.extend(self._process_email(path))

        return evidences

    def _process_email(self, eml_path: Path) -> list[Evidence]:
        """Confere o DKIM do e-mail e cataloga seus anexos (ZIPs sao abertos)."""
        target = self._resolve_extract_root() / f"email_{eml_path.stem}"
        email = read_email(eml_path, target)
        self._emails.append(email)
        logger.info(
            "E-mail %s: %d anexo(s), DKIM %s",
            eml_path.name, len(email.attachments), "valido" if email.verified else "nao confirmado",
        )
        evidences: list[Evidence] = []
        for att in email.attachments:
            if att.path.suffix.lower() == ".zip":
                evidences.extend(self._process_zip_file(att.path))
            else:
                evidences.append(self._create_evidence_instance(att.path))
        return evidences

    def _process_zip_file(self, zip_path: Path) -> list[Evidence]:
        """Processa um arquivo ZIP, extraindo e catalogando seu conteúdo.

        A extração vai para ``evidence/extracted/`` permanente do caso
        (não usa ``/tmp/lexproof_zip_*``). O ZIP original deve estar —
        ou ser levado para — ``evidence/original/``.

        Args:
            zip_path: Caminho do ZIP (preferir cópia permanente).

        Returns:
            Lista de evidências extraídas do ZIP.
        """
        evidences = []
        extract_root = self._resolve_extract_root()

        try:
            from lexproof.parsers.archive_parser import ArchiveParser
            parser = ArchiveParser(extract_dir=extract_root)
            extracted_files = parser.extract(zip_path)

            logger.info("ZIP extraído: %d arquivos em %s", len(extracted_files), extract_root)

            # Catalogar cada arquivo extraído
            self._zip_members[Path(zip_path).resolve()] = list(extracted_files)
            for file_path in extracted_files:
                if not file_path.exists():
                    continue

                evidences.append(self._create_evidence_instance(file_path))

        except Exception as e:
            logger.error("Erro ao processar ZIP %s: %s", zip_path.name, e)
            # Fallback: ZIP como evidência única, sempre no caminho permanente
            permanent_zip = self._ensure_permanent_zip(zip_path)
            evidence = Evidence(
                file_path=permanent_zip,
                file_name=permanent_zip.name,
                file_size=permanent_zip.stat().st_size,
                evidence_type=EvidenceType.OTHER,
                source=EvidenceSource.MANUAL_UPLOAD,
                sha256="",
                blake3="",
            )
            evidences.append(evidence)

        return evidences

    def _resolve_extract_root(self) -> Path:
        """Resolve o diretório permanente de extração do caso.

        Prioridade: ``case_dir/evidence/extracted`` →
        ``Paths.evidence_extracted_dir(session_code)`` →
        ``Paths.temp_dir()/extracted`` (só sem contexto de caso).
        """
        if self._case_dir is not None:
            root = Path(self._case_dir) / "evidence" / "extracted"
        elif self._session_code:
            root = Paths.evidence_extracted_dir(self._session_code)
        else:
            root = Paths.temp_dir() / "extracted"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _ensure_permanent_zip(self, zip_path: Path) -> Path:
        """Garante cópia do ZIP em ``evidence/original/`` do caso.

        Se ``zip_path`` já está nesse diretório, retorna como está.
        Sem contexto de caso, retorna o próprio caminho (não há onde copiar).
        """
        if self._case_dir is not None:
            original_dir = Path(self._case_dir) / "evidence" / "original"
        elif self._session_code:
            original_dir = Paths.evidence_original_dir(self._session_code)
        else:
            return zip_path

        original_dir.mkdir(parents=True, exist_ok=True)
        try:
            zip_path.resolve().relative_to(original_dir.resolve())
            return zip_path
        except ValueError:
            pass

        dest = original_dir / zip_path.name
        counter = 1
        while dest.exists():
            dest = original_dir / f"{zip_path.stem} ({counter}){zip_path.suffix}"
            counter += 1
        if zip_path.resolve() != dest.resolve():
            shutil.copy2(zip_path, dest)
            logger.info("ZIP fallback copiado para permanente: %s", dest)
        return dest

    def _is_whatsapp_export(self, path: Path) -> bool:
        """Verifica se um arquivo é uma exportação do WhatsApp.

        Usa o formato das linhas (data, hora, remetente), que é estável,
        em vez do aviso de criptografia, cujo texto muda entre versões.
        """
        try:
            return self._whatsapp_parser.validate(path)
        except Exception:
            return False

    def _get_image_dimensions(self, path: Path) -> tuple[int, int]:
        """Obtém as dimensões de uma imagem."""
        try:
            from PIL import Image
            with Image.open(path) as img:
                return img.size
        except Exception:
            return 0, 0

    def _extract_metadata(self, evidences: list[Evidence]) -> None:
        """Extrai metadados de todas as evidências."""
        for evidence in evidences:
            if evidence.evidence_type == EvidenceType.IMAGE:
                metadata = self._extract_image_metadata(evidence.file_path)
                evidence.metadata = metadata

    def _extract_image_metadata(self, path: Path) -> EvidenceMetadata:
        """Extrai metadados de uma imagem."""
        metadata = EvidenceMetadata()

        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            with Image.open(path) as img:
                # Dimensões
                metadata.width, metadata.height = img.size

                # Formato
                metadata.compression = img.format

                # EXIF
                exif_data = img.getexif()
                if exif_data:
                    exif_dict = {}
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, str(tag_id))
                        exif_dict[tag_name] = str(value)
                    metadata.exif = exif_dict

                    # Software
                    if "Software" in exif_dict:
                        metadata.software = exif_dict["Software"]

                    # Dispositivo
                    if "Make" in exif_dict or "Model" in exif_dict:
                        make = exif_dict.get("Make", "")
                        model = exif_dict.get("Model", "")
                        metadata.device = f"{make} {model}".strip()

                    # Data original
                    if "DateTimeOriginal" in exif_dict:
                        try:
                            from datetime import datetime
                            date_str = exif_dict["DateTimeOriginal"]
                            metadata.original_date = datetime.strptime(
                                date_str, "%Y:%m:%d %H:%M:%S"
                            ).replace(tzinfo=timezone.utc)
                        except (ValueError, TypeError):
                            pass

        except Exception as e:
            metadata.missing_metadata_note = (
                "Ausência de metadados compatível com plataformas que "
                "removem informações durante upload ou compartilhamento."
            )
            logger.debug("Metadados não extraídos de %s: %s", path, e)

        return metadata

    def _compute_hashes(self, evidences: list[Evidence]) -> list[HashResult]:
        """Calcula hashes para todas as evidências."""
        hash_results = []
        blake3_unavailable_logged = False

        for evidence in evidences:
            logger.info("Calculando hashes para: %s", evidence.file_name)

            # SHA-256 (sempre disponível)
            try:
                sha256_result = self._hasher.compute_hash(
                    evidence.file_path, "sha256"
                )
                evidence.sha256 = sha256_result.hash_value
                hash_results.append(sha256_result)
                logger.info("  SHA-256: %s", sha256_result.hash_value[:16] + "...")
            except Exception as e:
                logger.error("  Erro SHA-256 para %s: %s", evidence.file_name, e)

            # BLAKE3 (opcional)
            try:
                blake3_result = self._hasher.compute_hash(
                    evidence.file_path, "blake3"
                )
                evidence.blake3 = blake3_result.hash_value
                hash_results.append(blake3_result)
                logger.info("  BLAKE3: %s", blake3_result.hash_value[:16] + "...")
            except ValueError as e:
                if not blake3_unavailable_logged:
                    logger.warning("BLAKE3 indisponivel: %s. Continuando com SHA-256.", e)
                    blake3_unavailable_logged = True
                evidence.blake3 = ""
            except Exception as e:
                logger.warning("  Erro BLAKE3 para %s: %s. Continuando.", evidence.file_name, e)
                evidence.blake3 = ""

        return hash_results

    def _process_ocr(self, evidences: list[Evidence]) -> list[OCRResult]:
        """Processa OCR em todas as imagens (em paralelo, como os prints)."""
        from concurrent.futures import ThreadPoolExecutor

        ocr_results = []
        images = [e for e in evidences if e.evidence_type == EvidenceType.IMAGE]
        if not images:
            return ocr_results
        # Cria o motor antes das threads para elas nao o criarem ao mesmo tempo.
        self._ocr_processor._get_engine("tesseract")
        os.environ.setdefault("OMP_THREAD_LIMIT", "1")

        def run(evidence: Evidence) -> Any:
            try:
                return self._ocr_processor.process_image(evidence.file_path)
            except Exception as exc:
                return exc

        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:
            outcomes = list(pool.map(run, images))

        from lexproof.models.evidence import OCRResult as EvidenceOCRResult

        for evidence, outcome in zip(images, outcomes):
            if isinstance(outcome, Exception):
                logger.warning("OCR falhou para %s: %s", evidence.file_name, outcome)
                # Resultado OCR vazio para não quebrar o pipeline
                evidence.ocr = EvidenceOCRResult(
                    text="", confidence=0.0, language=None, bounding_boxes=None, engine="",
                )
                continue
            ocr_results.append(outcome)
            evidence.ocr = EvidenceOCRResult(
                text=outcome.extracted_text,
                confidence=outcome.confidence,
                language=None,
                bounding_boxes=None,
                engine=outcome.engine_used,
            )

        return ocr_results

    def _parse_whatsapp(self, evidences: list[Evidence]) -> list[WhatsAppMessage]:
        """Faz parsing de exportações do WhatsApp."""
        messages = []

        for evidence in evidences:
            if isinstance(evidence, ChatExportEvidence):
                try:
                    parsed_messages = self._whatsapp_parser.parse(evidence.file_path)
                    messages.extend(parsed_messages)

                    # Atualizar metadados da evidência
                    evidence.message_count = len(parsed_messages)
                    if parsed_messages:
                        evidence.participant_count = len(
                            set(m.sender for m in parsed_messages if m.sender)
                        )
                        evidence.participants = list(
                            set(m.sender for m in parsed_messages if m.sender)
                        )

                except Exception as e:
                    logger.warning("Parser WhatsApp falhou para %s: %s", evidence.file_name, e)

        return messages

    def _read_screenshots(
        self, evidences: list[Evidence], direct_paths: list[Path]
    ) -> tuple[list[ScreenshotReading], list[Path]]:
        """Le os prints enviados diretamente ou por e-mail (nao as midias do ZIP).

        Retorna os prints de conversa e as demais imagens (candidatas a perfil).
        """
        from concurrent.futures import ThreadPoolExecutor

        direct = {Path(p).resolve() for p in direct_paths}
        paths = [
            ev.file_path for ev in evidences
            if isinstance(ev, ImageEvidence) and Path(ev.file_path).resolve() in direct
        ]
        # O Tesseract roda em processo proprio; ler varios prints ao mesmo tempo
        # reduz bastante o tempo com dezenas de prints. Cada Tesseract ja usa
        # todos os nucleos por padrao, e varios juntos se atrapalham (8 prints:
        # 400 s sem o limite, contra ~6 s com ele).
        os.environ.setdefault("OMP_THREAD_LIMIT", "1")
        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:
            all_readings = list(pool.map(self._screenshot_reader.read, paths))
        readings, others = [], []
        for reading in all_readings:
            # Tela de perfil (nome + telefone) tambem tem textos que parecem baloes;
            # sem separador de data e com telefone no topo, e perfil.
            if not reading.date_labels and read_contact_profile(reading.path) is not None:
                others.append(reading.path)
                continue
            if reading.bubbles:
                readings.append(reading)
            else:
                logger.info("%s nao parece print de conversa", reading.path.name)
                others.append(reading.path)
        return readings, others

    def _link_contacts(
        self, evidences: list[Evidence], others: list[Path], readings: list[ScreenshotReading]
    ) -> list[ContactLink]:
        """Le prints de perfil (so entre imagens sem baloes) e confere o nome."""
        profiles = [p for p in (read_contact_profile(path) for path in others) if p is not None]
        if not profiles:
            return []
        export = next((e for e in evidences if isinstance(e, ChatExportEvidence)), None)
        source = self._export_source or (export.file_path if export else None)
        export_contact = export_contact_name(source) if source else None
        return link_profiles(profiles, export_contact, [r.contact for r in readings])

    def _check_screenshots(
        self,
        evidences: list[Evidence],
        readings: list[ScreenshotReading],
        messages: list[WhatsAppMessage],
    ) -> list[ScreenshotCheck]:
        """Confere cada print com a exportacao, quando ela existe."""
        if not messages:
            return []
        export = next((e for e in evidences if isinstance(e, ChatExportEvidence)), None)
        # Com recorte, a conferencia usa a conversa inteira (lida antes do
        # descarte), para que um print fora do periodo nao pareca inventado.
        export_path = self._export_source or (export.file_path if export else None)
        matcher = ScreenshotMatcher(self._all_messages or messages, export_path)
        return [matcher.check(r) for r in readings]

    def _cut_period(
        self,
        evidences: list[Evidence],
        evidence_paths: list[Path],
        hash_results: list[HashResult],
        period: tuple[date, date],
        discard: bool,
    ) -> tuple[ExcerptResult, list[Evidence], list[HashResult]]:
        """Recorta a exportacao ao periodo e, se pedido, descarta o restante."""
        if self._case_dir is None:
            raise RuntimeError("o recorte exige uma pasta de caso")
        export = next((e for e in evidences if isinstance(e, ChatExportEvidence)), None)
        if export is None:
            raise RuntimeError("não há exportação de conversa para recortar")
        txt = Path(export.file_path)
        zip_src = next(
            (z for z, members in self._zip_members.items()
             if txt.resolve() in {Path(m).resolve() for m in members}),
            None,
        )
        self._all_messages = self._whatsapp_parser.parse(txt)
        self._export_source = txt  # o nome do arquivo original traz o nome do contato
        excerpt = make_excerpt(
            txt, self._all_messages, period[0], period[1],
            self._case_dir / "evidence" / "recorte", zip_path=zip_src,
        )
        if discard:
            doomed = [txt, *(self._zip_members.get(zip_src, []) if zip_src else [])]
            direct = {Path(p).resolve() for p in evidence_paths}
            if zip_src is not None and zip_src in direct:
                doomed.append(zip_src)
            discard_outside(excerpt, doomed)
        write_excerpt_record(excerpt, self._case_dir / "preservacao" / EXCERPT_RECORD_NAME)

        # Daqui em diante a conversa e o recorte; arquivos apagados saem do inventario.
        export.file_path = excerpt.excerpt_path
        export.file_name = excerpt.excerpt_path.name
        evidences = [e for e in evidences if Path(e.file_path).exists()]
        hash_results = [h for h in hash_results if Path(h.file_path).exists()]
        hash_results += self._compute_hashes([export])
        return excerpt, evidences, hash_results

    def _correlate(self, evidences: list[Evidence]) -> list[CorrelationResult]:
        """Correlaciona evidências entre si."""
        return self._correlator.correlate(evidences)

    def _build_timeline(
        self,
        messages: list[WhatsAppMessage],
        ocr_results: list[OCRResult],
    ) -> list[TimelineEntry]:
        """Constrói a linha do tempo."""
        return self._timeline_builder.build_timeline(messages, ocr_results=ocr_results)

    def _verify(
        self,
        evidences: list[Evidence],
        ocr_results: list[OCRResult],
        messages: list[WhatsAppMessage],
    ) -> list[Any]:
        """Executa verificações de integridade."""
        case_data = {
            "evidence_files": evidences,
            "ocr_results": ocr_results,
            "messages": messages,
            "txt_messages": messages,
        }
        return self._verification_checker.run_all_verifications(case_data)

    def _calculate_quality_grade(
        self,
        evidences: list[Evidence],
        ocr_results: list[OCRResult],
        timeline: list[TimelineEntry],
        correlations: list[CorrelationResult],
        hash_results: list[HashResult],
    ) -> QualityGrade:
        """Calcula o grau de qualidade técnica."""
        criteria = GradeCriteria(
            has_official_export=any(
                isinstance(e, ChatExportEvidence) for e in evidences
            ),
            has_ocr=len(ocr_results) > 0,
            has_prints=any(e.evidence_type == EvidenceType.IMAGE for e in evidences),
            has_timeline=len(timeline) > 0,
            has_hashes=len(hash_results) > 0,
            has_timestamp=False,  # Não implementado nesta versão
            has_correlation=len(correlations) > 0,
        )
        return QualityGrade.calculate(criteria)

    def _generate_report(
        self,
        evidences: list[Evidence],
        messages: list[WhatsAppMessage],
        ocr_results: list[OCRResult],
        hash_results: list[HashResult],
        timeline: list[TimelineEntry],
        correlations: list[CorrelationResult],
        verification_results: list[Any],
        quality_grade: QualityGrade,
        output_dir: Optional[Path] = None,
        *,
        client_name: str = "",
        case_number: str = "",
        responsible_technician: str = "",
        seal: Optional[SealResult] = None,
        screenshot_checks: Optional[list[ScreenshotCheck]] = None,
        received_via: str = "",
        emails: Optional[list[EmailEvidence]] = None,
        stitch: Optional[StitchResult] = None,
        excerpt: Optional[ExcerptResult] = None,
        contacts: Optional[list[ContactLink]] = None,
    ) -> Path:
        """Gera o relatório de preservação."""
        from lexproof.reports.pdf_report import PDFReportGenerator
        from lexproof.reports.report_data import build_report_data

        if output_dir is None:
            output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)

        report_data = build_report_data(
            evidences=evidences,
            messages=messages,
            ocr_results=ocr_results,
            hash_results=hash_results,
            timeline=timeline,
            correlations=correlations,
            verification_results=verification_results,
            quality_grade=quality_grade,
            client_name=client_name,
            case_number=case_number,
            responsible_technician=responsible_technician,
            seal=seal,
            screenshot_checks=screenshot_checks or [],
            received_via=received_via,
            emails=emails or [],
            stitch=stitch,
            excerpt=excerpt,
            contacts=contacts or [],
        )

        # Gerar relatório PDF
        generator = PDFReportGenerator()
        output_path = output_dir / f"lexproof_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
        generator.generate(report_data, output_path)

        return output_path
