"""Testes unitários para o Smart Analysis Engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lexproof.analysis.engine import SmartAnalysisEngine
from lexproof.analysis.models import (
    EvidenceAnalysis,
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
from lexproof.models.message import MessageType, WhatsAppMessage


class TestTechnicalScores:
    """Testes para os scores técnicos."""

    def test_calculate_grade_a_plus(self) -> None:
        """Testa cálculo de grau A+."""
        scores = TechnicalScores(
            ocr_score=95.0,
            timeline_score=95.0,
            correlation_score=95.0,
            metadata_score=95.0,
            integrity_score=95.0,
            completeness_score=95.0,
        )
        assert scores.calculate_grade() == "A+"

    def test_calculate_grade_a(self) -> None:
        """Testa cálculo de grau A."""
        scores = TechnicalScores(
            ocr_score=85.0,
            timeline_score=85.0,
            correlation_score=85.0,
            metadata_score=85.0,
            integrity_score=85.0,
            completeness_score=85.0,
        )
        assert scores.calculate_grade() == "A"

    def test_calculate_grade_b(self) -> None:
        """Testa cálculo de grau B."""
        scores = TechnicalScores(
            ocr_score=75.0,
            timeline_score=75.0,
            correlation_score=75.0,
            metadata_score=75.0,
            integrity_score=75.0,
            completeness_score=75.0,
        )
        assert scores.calculate_grade() == "B"

    def test_calculate_grade_c(self) -> None:
        """Testa cálculo de grau C."""
        scores = TechnicalScores(
            ocr_score=65.0,
            timeline_score=65.0,
            correlation_score=65.0,
            metadata_score=65.0,
            integrity_score=65.0,
            completeness_score=65.0,
        )
        assert scores.calculate_grade() == "C"

    def test_calculate_grade_d(self) -> None:
        """Testa cálculo de grau D."""
        scores = TechnicalScores(
            ocr_score=50.0,
            timeline_score=50.0,
            correlation_score=50.0,
            metadata_score=50.0,
            integrity_score=50.0,
            completeness_score=50.0,
        )
        assert scores.calculate_grade() == "D"

    def test_to_dict(self) -> None:
        """Testa conversão para dicionário."""
        scores = TechnicalScores(
            ocr_score=85.0,
            timeline_score=90.0,
            correlation_score=75.0,
            metadata_score=60.0,
            integrity_score=95.0,
            completeness_score=80.0,
            technical_grade="A",
        )
        data = scores.to_dict()
        assert data["ocr_score"] == 85.0
        assert data["technical_grade"] == "A"


class TestEvidenceAnalysis:
    """Testes para o modelo EvidenceAnalysis."""

    def test_add_finding(self) -> None:
        """Testa adição de constatação."""
        analysis = EvidenceAnalysis()
        finding = Finding(
            category=FindingCategory.CHRONOLOGY,
            severity=FindingSeverity.WARNING,
            title="Lacuna detectada",
            description="Intervalo de 45 minutos",
            evidence="Timestamps",
            confidence=0.9,
        )
        analysis.add_finding(finding)
        assert len(analysis.findings) == 1

    def test_get_findings_by_severity(self) -> None:
        """Testa filtragem por severidade."""
        analysis = EvidenceAnalysis()
        analysis.add_finding(Finding(
            category=FindingCategory.CHRONOLOGY,
            severity=FindingSeverity.WARNING,
            title="A",
            description="B",
            evidence="C",
            confidence=0.9,
        ))
        analysis.add_finding(Finding(
            category=FindingCategory.INTEGRITY,
            severity=FindingSeverity.SUCCESS,
            title="D",
            description="E",
            evidence="F",
            confidence=1.0,
        ))

        warnings = analysis.get_findings_by_severity(FindingSeverity.WARNING)
        assert len(warnings) == 1

    def test_generate_executive_summary_text(self) -> None:
        """Testa geração do resumo executivo."""
        analysis = EvidenceAnalysis()
        analysis.summary.images_count = 10
        analysis.summary.exports_count = 1
        analysis.summary.participants_count = 2
        analysis.summary.messages_count = 150
        analysis.summary.period_days = 3
        analysis.summary.integrity_ok = True
        analysis.summary.gaps_detected = 1

        text = analysis.generate_executive_summary_text()
        assert "10" in text
        assert "1" in text
        assert "150" in text

    def test_generate_limitations_text(self) -> None:
        """Testa geração do texto de limitações."""
        analysis = EvidenceAnalysis()
        text = analysis.generate_limitations_text()
        assert "LexProof" in text
        assert "autenticidade" in text


class TestSmartAnalysisEngine:
    """Testes para o motor de análise."""

    def test_analyze_empty_evidences(self) -> None:
        """Testa análise sem evidências."""
        engine = SmartAnalysisEngine()
        result = engine.analyze([])
        assert result.evidence_count == 0
        assert result.scores.technical_grade == "D"

    def test_analyze_with_images(self, tmp_path: Path) -> None:
        """Testa análise com imagens."""
        # Criar imagens de teste
        from PIL import Image

        images = []
        for i in range(3):
            img_path = tmp_path / f"img_{i}.png"
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(img_path)
            images.append(ImageEvidence(
                file_path=img_path,
                file_name=f"img_{i}.png",
                file_size=1000,
                evidence_type=EvidenceType.IMAGE,
                sha256=f"hash_{i}",
                blake3=f"blake_{i}",
                width=100,
                height=100,
                format="PNG",
            ))

        engine = SmartAnalysisEngine()
        result = engine.analyze(images)

        assert result.summary.images_count == 3
        assert result.scores.integrity_score == 100.0

    def test_analyze_with_messages(self) -> None:
        """Testa análise com mensagens."""
        messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
                sender="João",
                content="Olá!",
            ),
            WhatsAppMessage(
                line_number=2,
                timestamp=datetime(2024, 3, 15, 10, 5, tzinfo=timezone.utc),
                sender="Maria",
                content="Oi!",
            ),
        ]

        engine = SmartAnalysisEngine()
        result = engine.analyze([], messages=messages)

        assert result.summary.messages_count == 2
        assert result.summary.participants_count == 2

    def test_detect_gap(self) -> None:
        """Testa detecção de lacuna."""
        messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
                sender="João",
                content="Olá!",
            ),
            WhatsAppMessage(
                line_number=2,
                timestamp=datetime(2024, 3, 15, 11, 0, tzinfo=timezone.utc),  # 1 hora depois
                sender="Maria",
                content="Oi!",
            ),
        ]

        engine = SmartAnalysisEngine()
        result = engine.analyze([], messages=messages)

        assert result.summary.gaps_detected == 1
        gap_findings = result.get_findings_by_category(FindingCategory.CHRONOLOGY)
        assert len(gap_findings) == 1

    def test_detect_duplicates(self) -> None:
        """Testa detecção de duplicatas."""
        evidences = [
            Evidence(
                file_path=Path("file1.txt"),
                file_name="file1.txt",
                file_size=100,
                evidence_type=EvidenceType.TEXT,
                sha256="same_hash",
                blake3="same_blake",
            ),
            Evidence(
                file_path=Path("file2.txt"),
                file_name="file2.txt",
                file_size=100,
                evidence_type=EvidenceType.TEXT,
                sha256="same_hash",
                blake3="same_blake",
            ),
        ]

        engine = SmartAnalysisEngine()
        result = engine.analyze(evidences)

        assert result.summary.duplicates_detected == 1
        dup_findings = result.get_findings_by_category(FindingCategory.DUPLICATE)
        assert len(dup_findings) == 1

    def test_decision_logs_created(self) -> None:
        """Testa que logs de decisão são criados."""
        engine = SmartAnalysisEngine()
        result = engine.analyze([])

        assert len(result.decision_logs) > 0

    def test_recommendations_generated(self) -> None:
        """Testa que recomendações são geradas."""
        engine = SmartAnalysisEngine()
        result = engine.analyze([])

        assert len(result.recommendations) > 0

    def test_limitations_generated(self) -> None:
        """Testa que limitações são geradas."""
        engine = SmartAnalysisEngine()
        result = engine.analyze([])

        assert len(result.limitations) > 0
        assert any("autenticidade jurídica" in l for l in result.limitations)
