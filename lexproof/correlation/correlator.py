"""Correlacionador de evidências do LexProof.

Mecanismo que relaciona automaticamente:
Print → OCR → Exportação TXT → Timeline

O relatório informa:
Print LP-000023 corresponde às linhas 541–548 do arquivo exportado
grau de confiança: 94%
"""

from __future__ import annotations

from typing import Optional

from lexproof.models.correlation import (
    CorrelationMatch,
    CorrelationResult,
    CorrelationType,
)
from lexproof.models.evidence import (
    ChatExportEvidence,
    Evidence,
    ImageEvidence,
)


class EvidenceCorrelator:
    """Correlacionador de evidências.

    Relaciona automaticamente prints de conversas com exportações de texto,
    identificando quais partes do texto exportado correspondem a cada imagem.
    """

    def __init__(self) -> None:
        """Inicializa o correlacionador."""
        self._correlation_results: list[CorrelationResult] = []

    def correlate(
        self,
        evidences: list[Evidence],
    ) -> list[CorrelationResult]:
        """Executa a correlação entre todas as evidências.

        Args:
            evidences: Lista de evidências para correlacionar.

        Returns:
            Lista de resultados de correlação.
        """
        self._correlation_results = []

        # Separa por tipo
        images = [e for e in evidences if isinstance(e, ImageEvidence)]
        exports = [e for e in evidences if isinstance(e, ChatExportEvidence)]

        # Correlaciona prints com exportações
        if images and exports:
            results = self._correlate_prints_to_exports(images, exports)
            self._correlation_results.extend(results)

        # Correlação temporal (todos os tipos)
        temporal_results = self._correlate_temporal(evidences)
        self._correlation_results.extend(temporal_results)

        return self._correlation_results

    def _correlate_prints_to_exports(
        self,
        images: list[ImageEvidence],
        exports: list[ChatExportEvidence],
    ) -> list[CorrelationResult]:
        """Correlaciona prints de imagens com exportações de texto.

        Args:
            images: Lista de evidências de imagem.
            exports: Lista de evidências de exportação.

        Returns:
            Lista de resultados de correlação.
        """
        results = []

        for image in images:
            for export in exports:
                result = self._match_image_to_export(image, export)
                if result and result.matches:
                    results.append(result)

        return results

    def _match_image_to_export(
        self,
        image: ImageEvidence,
        export: ChatExportEvidence,
    ) -> CorrelationResult | None:
        """Tenta correlacionar uma imagem com uma exportação.

        Args:
            image: Evidência de imagem.
            export: Evidência de exportação.

        Returns:
            Resultado da correlação ou None se não houver correspondência.
        """
        # Verifica se a imagem tem OCR
        if not image.ocr or not image.ocr.text:
            return None

        # Verifica se a exportação tem conteúdo
        if not export.file_path.exists():
            return None

        # Lê o conteúdo da exportação
        try:
            export_content = export.file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        # Busca o texto OCR no conteúdo da exportação
        ocr_text = image.ocr.text.strip()
        if not ocr_text:
            return None

        # Dividir o texto OCR em linhas para busca
        ocr_lines = ocr_text.split("\n")
        export_lines = export_content.split("\n")

        matches = []
        for ocr_line in ocr_lines:
            ocr_line = ocr_line.strip()
            if len(ocr_line) < 10:  # Ignora linhas muito curtas
                continue

            # Busca a linha OCR no conteúdo da exportação
            for i, export_line in enumerate(export_lines):
                if ocr_line in export_line:
                    match = CorrelationMatch(
                        source_evidence_id=image.id,
                        target_evidence_id=export.id,
                        source_line_start=i + 1,
                        source_line_end=i + 1,
                        target_text=ocr_line,
                        confidence=0.9,  # Confiança alta para match exato
                        match_type="exact",
                    )
                    matches.append(match)
                    break

        if not matches:
            # Tenta correspondência fuzzy (simplificada)
            matches = self._fuzzy_match(ocr_lines, export_lines, image.id, export.id)

        if not matches:
            return None

        result = CorrelationResult(
            correlation_type=CorrelationType.PRINT_TO_TXT,
            matches=matches,
        )

        return result

    def _fuzzy_match(
        self,
        ocr_lines: list[str],
        export_lines: list[str],
        image_id: str,
        export_id: str,
    ) -> list[CorrelationMatch]:
        """Realiza correspondência fuzzy entre linhas.

        Args:
            ocr_lines: Linhas do texto OCR.
            export_lines: Linhas da exportação.
            image_id: ID da evidência de imagem.
            export_id: ID da evidência de exportação.

        Returns:
            Lista de correspondências encontradas.
        """
        matches = []

        for ocr_line in ocr_lines:
            ocr_line = ocr_line.strip()
            if len(ocr_line) < 10:
                continue

            # Calcula similaridade com cada linha da exportação
            best_match = None
            best_score = 0.0

            for i, export_line in enumerate(export_lines):
                score = self._calculate_similarity(ocr_line, export_line)
                if score > best_score and score > 0.7:  # Limiar mínimo
                    best_score = score
                    best_match = (i, export_line)

            if best_match:
                match = CorrelationMatch(
                    source_evidence_id=image_id,
                    target_evidence_id=export_id,
                    source_line_start=best_match[0] + 1,
                    source_line_end=best_match[0] + 1,
                    target_text=best_match[1],
                    confidence=best_score,
                    match_type="fuzzy",
                )
                matches.append(match)

        return matches

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcula a similaridade entre dois textos.

        Args:
            text1: Primeiro texto.
            text2: Segundo texto.

        Returns:
            Score de similaridade (0-1).
        """
        # Implementação simplificada usando tokens comuns
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union) if union else 0.0

    def _correlate_temporal(
        self,
        evidences: list[Evidence],
    ) -> list[CorrelationResult]:
        """Correlaciona evidências por data/hora.

        Args:
            evidences: Lista de evidências.

        Returns:
            Lista de resultados de correlação temporal.
        """
        results: list[CorrelationResult] = []

        # Ordena por data de preservação
        sorted_evidences = sorted(
            evidences, key=lambda e: e.preservation_date
        )

        if len(sorted_evidences) < 2:
            return results

        # Cria correlações temporais entre evidências consecutivas
        for i in range(len(sorted_evidences) - 1):
            current = sorted_evidences[i]
            next_ev = sorted_evidences[i + 1]

            # Calcula diferença temporal
            time_diff = (next_ev.preservation_date - current.preservation_date).total_seconds()

            # Se preservadas em sequência rápida (< 5 minutos), são provavelmente relacionadas
            if time_diff < 300:  # 5 minutos
                match = CorrelationMatch(
                    source_evidence_id=current.id,
                    target_evidence_id=next_ev.id,
                    confidence=0.8,
                    match_type="temporal",
                )

                result = CorrelationResult(
                    correlation_type=CorrelationType.TEMPORAL,
                    matches=[match],
                )
                results.append(result)

        return results

    def get_correlation_summary(self) -> str:
        """Retorna um resumo de todas as correlações para o relatório.

        Returns:
            Resumo formatado das correlações.
        """
        if not self._correlation_results:
            return "Nenhuma correlação encontrada"

        summary_parts = []
        for result in self._correlation_results:
            summary_parts.append(result.get_summary())

        return "\n".join(summary_parts)
