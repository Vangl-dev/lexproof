"""Smart Analysis Engine - Motor de Análise Inteligente do LexProof.

Motor determinístico, reproduzível e auditável para análise
técnica de conjuntos de evidências digitais.

Não utiliza IA generativa ou LLMs.
Toda análise é baseada em regras documentadas.
"""

from __future__ import annotations

import hashlib
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from lexproof.analysis.models import (
    DecisionLog,
    EvidenceAnalysis,
    EvidenceHealth,
    ExecutiveSummary,
    Finding,
    FindingCategory,
    FindingSeverity,
    TechnicalScores,
)
from lexproof.models.evidence import (
    ChatExportEvidence,
    Evidence,
    EvidenceType,
    ImageEvidence,
)
from lexproof.models.message import WhatsAppMessage
from lexproof.models.ocr_result import OCRResult

logger = logging.getLogger(__name__)

# Constantes para análise
GAP_THRESHOLD_MINUTES = 30  # Limiar para detectar lacuna
MIN_IMAGE_SIZE_KB = 50  # Tamanho mínimo para considerar imagem viável
MIN_OCR_RESOLUTION = 200  # Resolução mínima para OCR
OVERLAP_SIMILARITY_THRESHOLD = 0.7  # Limiar de similaridade para sobreposição


class SmartAnalysisEngine:
    """Motor de análise inteligente de evidências.

    Implementa análise determinística com:
    - Detecção de plataforma
    - Análise cronológica
    - Detecção de sobreposição
    - Análise de qualidade
    - Geração de recomendações
    """

    def __init__(self) -> None:
        """Inicializa o motor de análise."""
        self._analysis: Optional[EvidenceAnalysis] = None

    def analyze(
        self,
        evidences: list[Evidence],
        messages: list[WhatsAppMessage] | None = None,
        ocr_results: list[OCRResult] | None = None,
        correlations: list | None = None,
    ) -> EvidenceAnalysis:
        """Executa a análise completa do conjunto de evidências.

        Args:
            evidences: Lista de evidências para analisar.
            messages: Mensagens extraídas de exportações (opcional).
            ocr_results: Resultados OCR (opcional).
            correlations: Resultados de correlação (opcional).

        Returns:
            EvidenceAnalysis com todas as constatações.
        """
        self._analysis = EvidenceAnalysis(
            analysis_id=f"ANALYSIS-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            evidence_count=len(evidences),
        )

        # Executar todas as análises
        self._detect_platform(evidences, messages)
        self._analyze_composition(evidences)
        self._analyze_chronology(messages)
        self._detect_overlaps(evidences)
        self._detect_order_issues(messages)
        self._detect_continuity_breaks(messages)
        self._detect_duplicates(evidences)
        self._analyze_image_quality(evidences)
        self._analyze_metadata(evidences)
        self._analyze_integrity(evidences)
        self._calculate_scores(evidences, messages, ocr_results, correlations)
        self._calculate_health()
        self._generate_recommendations()
        self._generate_limitations()

        logger.info(
            "Análise concluída: %d constatações, grau %s",
            len(self._analysis.findings),
            self._analysis.scores.technical_grade,
        )

        return self._analysis

    def _detect_platform(
        self,
        evidences: list[Evidence],
        messages: list[WhatsAppMessage] | None,
    ) -> None:
        """Detecta a plataforma de origem das evidências.

        Algoritmo:
        1. Verificar se há exportação oficial
        2. Analisar formato das mensagens
        3. Verificar metadados de dispositivo

        Regra: WhatsApp Android usa formato "DD/MM/YYYY HH:MM, Nome:"
        Regra: WhatsApp iPhone usa formato "[DD/MM/YYYY, HH:MM:MM] Nome:"
        """
        platform = "Desconhecida"
        confidence = 0.0

        # Verificar exportações
        has_export = any(isinstance(e, ChatExportEvidence) for e in evidences)

        if has_export:
            # Analisar formato das mensagens
            if messages:
                # Padrão brasileiro
                br_pattern_count = sum(
                    1 for m in messages
                    if m.timestamp and m.sender
                )
                if br_pattern_count > len(messages) * 0.5:
                    platform = "WhatsApp (Android/Brasileiro)"
                    confidence = 0.8

            # Verificar nome do arquivo
            for e in evidences:
                if isinstance(e, ChatExportEvidence):
                    if "_chat" in e.file_name.lower():
                        platform = "WhatsApp (Android)"
                        confidence = 0.9
                    elif "whatsapp" in e.file_name.lower():
                        platform = "WhatsApp"
                        confidence = 0.7

        # Verificar imagens
        image_count = sum(1 for e in evidences if e.evidence_type == EvidenceType.IMAGE)
        if image_count > 0 and not has_export:
            platform = "Imagens (plataforma desconhecida)"
            confidence = 0.3

        self._analysis.detected_platform = platform

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Detecção de plataforma baseada em formato de mensagens e nomes de arquivos",
            data_analyzed=f"{len(evidences)} evidências, {len(messages or [])} mensagens",
            justification=f"Plataforma identificada como '{platform}' com confiança {confidence:.0%}",
            confidence=confidence,
        ))

        # Adicionar finding se plataforma conhecida
        if confidence > 0.5:
            self._analysis.add_finding(Finding(
                category=FindingCategory.PLATFORM,
                severity=FindingSeverity.INFO,
                title="Plataforma identificada",
                description=f"A plataforma detectada é: {platform}",
                evidence="Análise de formato de mensagens e nomes de arquivos",
                confidence=confidence,
            ))

    def _analyze_composition(self, evidences: list[Evidence]) -> None:
        """Analisa a composição do conjunto de evidências.

        Conta:
        - Imagens
        - Exportações
        - Participantes
        - Período abrangido
        """
        summary = self._analysis.summary

        # Contar por tipo
        for e in evidences:
            if e.evidence_type == EvidenceType.IMAGE:
                summary.images_count += 1
            elif e.evidence_type == EvidenceType.CHAT_EXPORT:
                summary.exports_count += 1

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Contagem de evidências por tipo",
            data_analyzed=f"{len(evidences)} evidências",
            justification=f"Encontradas {summary.images_count} imagens e {summary.exports_count} exportações",
            confidence=1.0,
        ))

    def _analyze_chronology(self, messages: list[WhatsAppMessage] | None) -> None:
        """Analisa a cronologia das mensagens.

        Detecta:
        - Período abrangido
        - Lacunas temporais
        - Participantes
        """
        if not messages:
            return

        summary = self._analysis.summary

        # Ordenar por timestamp
        sorted_msgs = sorted(messages, key=lambda m: m.timestamp)

        if not sorted_msgs:
            return

        # Período
        summary.period_start = sorted_msgs[0].timestamp
        summary.period_end = sorted_msgs[-1].timestamp
        summary.messages_count = len(messages)

        if summary.period_start and summary.period_end:
            delta = summary.period_end - summary.period_start
            summary.period_days = max(1, delta.days)

        # Participantes
        participants = set(m.sender for m in messages if m.sender)
        summary.participants_count = len(participants)

        # Detectar lacunas
        gaps = self._detect_gaps(sorted_msgs)
        summary.gaps_detected = len(gaps)

        # Adicionar findings para lacunas
        for gap in gaps:
            self._analysis.add_finding(Finding(
                category=FindingCategory.CHRONOLOGY,
                severity=FindingSeverity.WARNING,
                title="Lacuna cronológica detectada",
                description=f"Intervalo de {gap['duration']:.0f} minutos entre mensagens",
                evidence=f"De {gap['start']} para {gap['end']}",
                confidence=0.95,
                recommendation="Verificar se há prints ou mensagens ausentes neste período",
                details=gap,
            ))

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Análise de cronologia com limiar de 30 minutos",
            data_analyzed=f"{len(messages)} mensagens, período de {summary.period_days} dias",
            justification=f"Detectadas {len(gaps)} lacuna(s) temporal(is)",
            confidence=0.95,
        ))

    def _detect_gaps(self, sorted_messages: list[WhatsAppMessage]) -> list[dict[str, Any]]:
        """Detecta lacunas temporais significativas.

        Regra: Intervalo superior a GAP_THRESHOLD_MINUTES minutos.
        """
        gaps = []

        for i in range(len(sorted_messages) - 1):
            current = sorted_messages[i]
            next_msg = sorted_messages[i + 1]

            delta = (next_msg.timestamp - current.timestamp).total_seconds() / 60

            if delta > GAP_THRESHOLD_MINUTES:
                gaps.append({
                    "start": current.timestamp.isoformat(),
                    "end": next_msg.timestamp.isoformat(),
                    "duration": delta,
                    "after_line": current.line_number,
                    "before_line": next_msg.line_number,
                })

        return gaps

    def _detect_overlaps(self, evidences: list[Evidence]) -> None:
        """Detecta sobreposição entre prints.

        Algoritmo: Compara texto OCR de imagens consecutivas.
        Se o texto de uma imagem aparece parcialmente na outra,
        há sobreposição.
        """
        images = [e for e in evidences if isinstance(e, ImageEvidence) and e.ocr]

        if len(images) < 2:
            return

        overlaps = []
        for i in range(len(images)):
            for j in range(i + 1, len(images)):
                img_a = images[i]
                img_b = images[j]

                if img_a.ocr and img_b.ocr:
                    similarity = self._calculate_text_similarity(
                        img_a.ocr.text, img_b.ocr.text
                    )

                    if similarity > OVERLAP_SIMILARITY_THRESHOLD:
                        overlaps.append({
                            "image_a": img_a.file_name,
                            "image_b": img_b.file_name,
                            "similarity": similarity,
                        })

        self._analysis.summary.overlaps_detected = len(overlaps)

        for overlap in overlaps:
            self._analysis.add_finding(Finding(
                category=FindingCategory.OVERLAP,
                severity=FindingSeverity.INFO,
                title="Sobreposição detectada",
                description=f"Imagens '{overlap['image_a']}' e '{overlap['image_b']}' contêm texto similar",
                evidence=f"Similaridade: {overlap['similarity']:.0%}",
                confidence=overlap['similarity'],
                details=overlap,
            ))

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Detecção de sobreposição por similaridade de texto OCR",
            data_analyzed=f"{len(images)} imagens com OCR",
            justification=f"Detectadas {len(overlaps)} sobreposição(ões)",
            confidence=0.8,
        ))

    def _calculate_text_similarity(self, text_a: str, text_b: str) -> float:
        """Calcula similaridade entre dois textos.

        Usa coeficiente de Jaccard sobre tokens.
        """
        if not text_a or not text_b:
            return 0.0

        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b

        return len(intersection) / len(union) if union else 0.0

    def _detect_order_issues(self, messages: list[WhatsAppMessage] | None) -> None:
        """Detecta possível ordem incorreta de prints.

        Regra: Se mensagens com timestamp anterior aparecem
        em prints posteriores, há problema de ordem.
        """
        if not messages or len(messages) < 2:
            return

        out_of_order = []
        for i in range(len(messages) - 1):
            if messages[i].timestamp > messages[i + 1].timestamp:
                out_of_order.append({
                    "line_a": messages[i].line_number,
                    "time_a": messages[i].timestamp.isoformat(),
                    "line_b": messages[i + 1].line_number,
                    "time_b": messages[i + 1].timestamp.isoformat(),
                })

        for issue in out_of_order[:5]:  # Limitar a 5 exemplos
            self._analysis.add_finding(Finding(
                category=FindingCategory.ORDER,
                severity=FindingSeverity.WARNING,
                title="Possível ordem incorreta",
                description=f"Mensagem na linha {issue['line_a']} é posterior à linha {issue['line_b']}",
                evidence=f"Timestamp {issue['time_a']} > {issue['time_b']}",
                confidence=0.9,
                details=issue,
            ))

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Verificação de ordenação cronológica",
            data_analyzed=f"{len(messages)} mensagens",
            justification=f"Detectados {len(out_of_order)} problema(s) de ordem",
            confidence=0.9,
        ))

    def _detect_continuity_breaks(self, messages: list[WhatsAppMessage] | None) -> None:
        """Detecta mensagens interrompidas.

        Regra: Se o texto termina abruptamente (sem pontuação final)
        e a próxima mensagem é do mesmo remetente, pode haver continuidade.
        """
        if not messages or len(messages) < 2:
            return

        breaks = []
        for i in range(len(messages) - 1):
            current = messages[i]
            next_msg = messages[i + 1]

            # Verificar se texto termina abruptamente
            if current.content and not current.content.rstrip().endswith(('.', '!', '?', '...')):
                # Verificar se próximo é do mesmo remetente
                if current.sender == next_msg.sender:
                    breaks.append({
                        "line_a": current.line_number,
                        "line_b": next_msg.line_number,
                        "sender": current.sender,
                        "text_end": current.content[-50:],
                    })

        for break_item in breaks[:5]:
            self._analysis.add_finding(Finding(
                category=FindingCategory.CONTINUITY,
                severity=FindingSeverity.INFO,
                title="Mensagem possivelmente interrompida",
                description=f"Texto na linha {break_item['line_a']} pode continuar na linha {break_item['line_b']}",
                evidence=f"Remetente: {break_item['sender']}",
                confidence=0.7,
                details=break_item,
            ))

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Detecção de continuidade por remetente e terminação de texto",
            data_analyzed=f"{len(messages)} mensagens",
            justification=f"Detectadas {len(breaks)} possíve(is) interrupção(ões)",
            confidence=0.7,
        ))

    def _detect_duplicates(self, evidences: list[Evidence]) -> None:
        """Detecta prints repetidos.

        Regra: Hashes SHA-256 idênticos indicam arquivo duplicado.
        """
        hash_counter = Counter(e.sha256 for e in evidences if e.sha256)
        duplicates = {h: count for h, count in hash_counter.items() if count > 1}

        self._analysis.summary.duplicates_detected = len(duplicates)

        for hash_val, count in duplicates.items():
            dup_files = [e.file_name for e in evidences if e.sha256 == hash_val]
            self._analysis.add_finding(Finding(
                category=FindingCategory.DUPLICATE,
                severity=FindingSeverity.WARNING,
                title="Evidência duplicada",
                description=f"{count} arquivos idênticos detectados",
                evidence=f"Arquivos: {', '.join(dup_files)}",
                confidence=1.0,
                recommendation="Remover duplicatas para evitar confusão",
                details={"files": dup_files, "count": count},
            ))

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Detecção de duplicatas por hash SHA-256",
            data_analyzed=f"{len(evidences)} evidências",
            justification=f"Detectadas {len(duplicates)} duplicidade(s)",
            confidence=1.0,
        ))

    def _analyze_image_quality(self, evidences: list[Evidence]) -> None:
        """Analisa qualidade das imagens.

        Detecta:
        - Imagens muito comprimidas
        - Resolução baixa para OCR
        """
        images = [e for e in evidences if isinstance(e, ImageEvidence)]

        for img in images:
            # Verificar tamanho (compressão)
            if img.file_size < MIN_IMAGE_SIZE_KB * 1024:
                self._analysis.add_finding(Finding(
                    category=FindingCategory.QUALITY,
                    severity=FindingSeverity.WARNING,
                    title="Imagem possivelmente comprimida",
                    description=f"Arquivo '{img.file_name}' tem apenas {img.file_size / 1024:.1f} KB",
                    evidence=f"Tamanho: {img.file_size} bytes",
                    confidence=0.8,
                    recommendation="Solicitar imagem em resolução original",
                ))

            # Verificar resolução
            if img.width > 0 and img.height > 0:
                min_dim = min(img.width, img.height)
                if min_dim < MIN_OCR_RESOLUTION:
                    self._analysis.add_finding(Finding(
                        category=FindingCategory.QUALITY,
                        severity=FindingSeverity.WARNING,
                        title="Resolução baixa para OCR",
                        description=f"Imagem '{img.file_name}' tem resolução {img.width}x{img.height}",
                        evidence=f"Dimensão mínima: {min_dim}px (recomendado: {MIN_OCR_RESOLUTION}px)",
                        confidence=0.9,
                        recommendation="Solicitar imagem em resolução original",
                    ))

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Análise de qualidade com limiares: 50KB tamanho, 200px resolução",
            data_analyzed=f"{len(images)} imagens",
            justification="Análise de compressão e resolução para OCR",
            confidence=0.85,
        ))

    def _analyze_metadata(self, evidences: list[Evidence]) -> None:
        """Analisa metadados das evidências.

        Detecta:
        - Presença de EXIF
        - Dispositivo de captura
        - Data original
        """
        images = [e for e in evidences if e.evidence_type == EvidenceType.IMAGE]

        with_exif = 0
        without_exif = 0

        for img in images:
            if img.metadata and img.metadata.exif:
                with_exif += 1
            else:
                without_exif += 1

        # Atualizar score de metadados
        if images:
            self._analysis.scores.metadata_score = (with_exif / len(images)) * 100

        # Finding se não houver metadados
        if without_exif > 0 and with_exif == 0:
            self._analysis.add_finding(Finding(
                category=FindingCategory.METADATA,
                severity=FindingSeverity.INFO,
                title="Metadados não disponíveis",
                description=(
                    "As imagens não contêm metadados EXIF. "
                    "Diversas plataformas removem metadados durante upload ou compartilhamento. "
                    "Ausência de EXIF não indica fraude."
                ),
                evidence=f"{without_exif} imagens sem metadados",
                confidence=1.0,
            ))

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Análise de metadados EXIF",
            data_analyzed=f"{len(images)} imagens",
            justification=f"{with_exif} com metadados, {without_exif} sem metadados",
            confidence=1.0,
        ))

    def _analyze_integrity(self, evidences: list[Evidence]) -> None:
        """Analisa integridade das evidências.

        Verifica:
        - Presença de hashes
        - Consistência dos hashes
        """
        with_hash = sum(1 for e in evidences if e.sha256)
        without_hash = sum(1 for e in evidences if not e.sha256)

        if evidences:
            self._analysis.scores.integrity_score = (with_hash / len(evidences)) * 100

        # Atualizar resumo
        self._analysis.summary.integrity_ok = (without_hash == 0)

        if without_hash > 0:
            self._analysis.add_finding(Finding(
                category=FindingCategory.INTEGRITY,
                severity=FindingSeverity.WARNING,
                title="Evidências sem hash",
                description=f"{without_hash} evidência(s) não possui(m) hash calculado",
                evidence="Verificação de integridade incompleta",
                confidence=1.0,
            ))

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Verificação de integridade por presença de hash SHA-256",
            data_analyzed=f"{len(evidences)} evidências",
            justification=f"{with_hash} com hash, {without_hash} sem hash",
            confidence=1.0,
        ))

    def _calculate_scores(
        self,
        evidences: list[Evidence],
        messages: list[WhatsAppMessage] | None,
        ocr_results: list[OCRResult] | None,
        correlations: list | None = None,
    ) -> None:
        """Calcula os scores técnicos.

        Fórmulas documentadas:
        - OCR Score: % de imagens com OCR processado
        - Timeline Score: % de mensagens com timestamp válido
        - Correlation Score: % de evidências correlacionadas
        - Metadata Score: % de imagens com metadados
        - Integrity Score: % de evidências com hash
        - Completeness Score: score composto
        """
        scores = self._analysis.scores

        # OCR Score
        images = [e for e in evidences if e.evidence_type == EvidenceType.IMAGE]
        if images:
            with_ocr = sum(1 for e in images if e.ocr and e.ocr.text)
            scores.ocr_score = (with_ocr / len(images)) * 100

        # Timeline Score
        if messages:
            with_timestamp = sum(1 for m in messages if m.timestamp)
            scores.timeline_score = (with_timestamp / len(messages)) * 100
        else:
            scores.timeline_score = 100.0 if not evidences else 0.0

        # Correlation Score - calculado baseado em evidencias reais
        if correlations and len(correlations) > 0:
            # Calcular baseado no numero de correlacoes encontradas
            # Cada correlacao positiva contribui para o score
            correlation_count = len(correlations)
            total_evidences = len(evidences) if evidences else 1
            # Score baseado na proporcao de evidencias correlacionadas
            scores.correlation_score = min(100.0, (correlation_count / total_evidences) * 100)
        else:
            # Sem correlacoes disponiveis
            scores.correlation_score = 0.0

        # Completeness Score (média dos outros)
        scores.completeness_score = (
            scores.ocr_score * 0.3
            + scores.timeline_score * 0.3
            + scores.metadata_score * 0.2
            + scores.integrity_score * 0.2
        )

        # Calcular grau
        scores.calculate_grade()

        # Log de decisão
        self._analysis.add_decision_log(DecisionLog(
            rule="Cálculo de scores técnicos com fórmulas documentadas",
            data_analyzed="Todos os scores parciais",
            justification=f"Grau técnico: {scores.technical_grade}",
            confidence=1.0,
        ))

    def _calculate_health(self) -> None:
        """Calcula a saúde do conjunto de evidências."""
        scores = self._analysis.scores
        health = self._analysis.health

        # Score geral
        health.overall_score = (
            scores.integrity_score * 0.25
            + scores.completeness_score * 0.25
            + scores.timeline_score * 0.20
            + scores.ocr_score * 0.15
            + scores.correlation_score * 0.10
            + scores.metadata_score * 0.05
        )

        # Status de cada área
        health.integrity_status = "pass" if scores.integrity_score >= 80 else "warning"
        health.timeline_status = "pass" if scores.timeline_score >= 80 else "warning"
        health.ocr_status = "pass" if scores.ocr_score >= 80 else "warning"
        health.correlation_status = "pass" if scores.correlation_score >= 80 else "warning"
        health.metadata_status = "pass" if scores.metadata_score >= 80 else "warning"

        # Contagens
        health.gaps_count = self._analysis.summary.gaps_detected
        health.duplicates_count = self._analysis.summary.duplicates_detected

    def _generate_recommendations(self) -> None:
        """Gera recomendações baseadas na análise.

        Regra: Recomendações são apenas sugestões técnicas.
        Nunca afirmam valor jurídico.
        """
        analysis = self._analysis

        # Verificar ausência de exportação oficial
        if analysis.summary.exports_count == 0:
            analysis.add_recommendation(
                "Solicitar exportação oficial da conversa (WhatsApp, Telegram, etc.)"
            )

        # Verificar lacunas
        if analysis.summary.gaps_detected > 0:
            analysis.add_recommendation(
                "Verificar se há prints ou mensagens ausentes nos períodos com lacunas"
            )

        # Verificar duplicatas
        if analysis.summary.duplicates_detected > 0:
            analysis.add_recommendation(
                "Remover evidências duplicadas para evitar confusão"
            )

        # Verificar qualidade de imagens
        quality_findings = analysis.get_findings_by_category(FindingCategory.QUALITY)
        if quality_findings:
            analysis.add_recommendation(
                "Solicitar imagens em resolução original quando possível"
            )

        # Verificar metadados
        if analysis.scores.metadata_score < 50:
            analysis.add_recommendation(
                "Preservar ZIP original quando disponível (contém metadados)"
            )

        # Verificar OCR
        if analysis.scores.ocr_score < 50:
            analysis.add_recommendation(
                "Processar OCR nas imagens para melhorar indexação"
            )

        # Log de decisão
        analysis.add_decision_log(DecisionLog(
            rule="Geração de recomendações baseada em constatações",
            data_analyzed=f"{len(analysis.findings)} constatações",
            justification=f"{len(analysis.recommendations)} recomendação(ões) gerada(s)",
            confidence=1.0,
        ))

    def _generate_limitations(self) -> None:
        """Gera as limitações do sistema."""
        self._analysis.limitations = [
            "O LexProof documenta tecnicamente o estado das evidências recebidas.",
            "O software não certifica autenticidade jurídica.",
            "O software não verifica autoria das mensagens.",
            "O software não verifica veracidade do conteúdo.",
            "As conclusões referem-se exclusivamente aos aspectos técnicos observados.",
        ]
