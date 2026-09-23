"""Testes de integração para o pipeline completo de análise do LexProof."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lexproof.crypto.hasher import FileHasher
from lexproof.crypto.manifest import ManifestGenerator
from lexproof.models.case import PreservationSession, SessionMetadata
from lexproof.models.custody import CustodyChain, CustodyEvent, CustodyEventType
from lexproof.models.evidence import Evidence, EvidenceType
from lexproof.models.hash_result import HashAlgorithm
from lexproof.models.message import MessageType, WhatsAppMessage
from lexproof.models.ocr_result import OCRResult
from lexproof.models.verification import VerificationStatus
from lexproof.parsers.whatsapp_parser import WhatsAppParser
from lexproof.timeline.timeline_builder import TimelineBuilder
from lexproof.verification.checker import VerificationChecker


SAMPLE_WHATSAPP = """\
15/03/2024 10:00, João: Bom dia, pessoal!
15/03/2024 10:01, Maria: Oi João, tudo bem?
15/03/2024 10:02, João: Tudo ótimo! Preciso de uma ajuda.
15/03/2024 10:03, Maria: Claro, o que precisa?
15/03/2024 10:05, João: Preciso do documento que você me mandou.
15/03/2024 10:06, Maria: <Mídia ocultada>
15/03/2024 10:10, João: Recebi, obrigado!
15/03/2024 10:15, Maria: De nada! Qualquer coisa é só chamar.
"""


@pytest.fixture
def full_test_dir(tmp_path: Path) -> Path:
    """Fixture que prepara um diretório completo para testes de integração."""
    work_dir = tmp_path / "lexproof_integration"
    work_dir.mkdir()
    return work_dir


@pytest.fixture
def whatsapp_file(full_test_dir: Path) -> Path:
    """Fixture que cria um arquivo de conversa WhatsApp."""
    file_path = full_test_dir / "conversa_exportada.txt"
    file_path.write_text(SAMPLE_WHATSAPP, encoding="utf-8")
    return file_path


@pytest.fixture
def evidence_file(full_test_dir: Path) -> Path:
    """Fixture que cria um arquivo de evidência."""
    file_path = full_test_dir / "documento_evidencia.txt"
    file_path.write_text("Conteúdo do documento de evidência.", encoding="utf-8")
    return file_path


class TestFullAnalysisPipeline:
    """Teste de integração: pipeline completo de análise."""

    def test_full_analysis_pipeline(
        self, full_test_dir, whatsapp_file, evidence_file
    ):
        # Passo 1: Parse da conversa WhatsApp
        parser = WhatsAppParser()
        messages = parser.parse(whatsapp_file)
        assert len(messages) >= 8
        assert messages[0].sender == "João"
        assert messages[0].message_type == MessageType.TEXT

        # Passo 2: Hashing dos arquivos de evidência
        hasher = FileHasher()
        whatsapp_hashes = hasher.compute_all_hashes(whatsapp_file)
        evidence_hashes = hasher.compute_all_hashes(evidence_file)

        assert len(whatsapp_hashes) == 3
        assert len(evidence_hashes) == 3

        for h in whatsapp_hashes + evidence_hashes:
            assert len(h.hash_value) > 0

        # Passo 3: Construção da linha do tempo
        builder = TimelineBuilder()
        timeline = builder.build_timeline(messages)
        assert len(timeline) >= 8

        timestamps = [e.timestamp for e in timeline]
        assert timestamps == sorted(timestamps)

        # Passo 4: Verificações
        checker = VerificationChecker()
        case_data = {"messages": messages}
        results = checker.run_all_verifications(case_data)
        assert len(results) >= 4

        for r in results:
            assert r.status in ("pass", "warning", "not_applicable", "inconclusive")

        # Passo 5: Geração do manifesto
        manifest_gen = ManifestGenerator()
        all_hashes = whatsapp_hashes + evidence_hashes
        manifest_data = manifest_gen.generate(
            all_hashes, {"case_number": "INTEG-001", "pipeline_test": True}
        )
        assert manifest_data["file_count"] == 6

        manifest_path = full_test_dir / "manifest.json"
        created_path = manifest_gen.create_manifest_file(manifest_data, manifest_path)
        assert created_path.exists()

        # Passo 6: Validação do manifesto
        assert ManifestGenerator.validate_manifest(created_path) is True

        # Passo 7: Criação do caso
        case = PreservationSession(
            metadata=SessionMetadata(
                case_number="INTEG-001",
                description="Pipeline completo de análise",
                client_name="Cliente Teste",
                responsible_technician="Advogado Teste",
            )
        )

        wp_evidence = Evidence(
            file_path=whatsapp_file,
            file_name=whatsapp_file.name,
            file_size=whatsapp_file.stat().st_size,
            evidence_type=EvidenceType.MESSAGE,
            description="Conversa WhatsApp exportada",
            sha256=whatsapp_hashes[0].hash_value,
            blake3=whatsapp_hashes[0].hash_value,
        )
        doc_evidence = Evidence(
            file_path=evidence_file,
            file_name=evidence_file.name,
            file_size=evidence_file.stat().st_size,
            evidence_type=EvidenceType.TEXT,
            description="Documento de evidência",
            sha256=evidence_hashes[0].hash_value,
            blake3=evidence_hashes[0].hash_value,
        )

        case.add_evidence(wp_evidence)
        case.add_evidence(doc_evidence)

        chain = CustodyChain(evidence_id="wp-001")
        chain.add_event(
            CustodyEvent(
                event_type=CustodyEventType.IMPORT,
                description="Arquivo importado para análise",
                hash_after=whatsapp_hashes[0].hash_value,
            )
        )
        chain.add_event(
            CustodyEvent(
                event_type=CustodyEventType.HASH,
                description="Hash calculado com múltiplos algoritmos",
                hash_before=whatsapp_hashes[0].hash_value,
                hash_after=whatsapp_hashes[0].hash_value,
            )
        )

        # Passo 8: Verificação de integridade
        assert case.evidence_files[0].sha256 == whatsapp_hashes[0].hash_value

        case_json = case.model_dump(mode="json")
        assert case_json["metadata"]["case_number"] == "INTEG-001"
        assert len(case_json["evidence_files"]) == 2

        # Passo 9: Salvar e recarregar caso
        case_path = full_test_dir / "case.json"
        case_path.write_text(
            json.dumps(case_json, indent=2, default=str), encoding="utf-8"
        )
        loaded_data = json.loads(case_path.read_text(encoding="utf-8"))
        loaded_case = PreservationSession.model_validate(loaded_data)
        assert loaded_case.metadata.case_number == "INTEG-001"
        assert len(loaded_case.evidence_files) == 2

    def test_pipeline_with_ocr_comparison(self, full_test_dir, whatsapp_file):
        parser = WhatsAppParser()
        messages = parser.parse(whatsapp_file)

        ocr_results = [
            OCRResult(
                source_image="screenshot_conversa.png",
                extracted_text="15/03/2024 10:00, João: Bom dia!",
                confidence=0.92,
                detected_timestamps=["15/03/2024 10:00"],
                detected_senders=["João"],
                detected_messages=["Bom dia!"],
                engine_used="tesseract",
                processing_time=2.3,
            )
        ]

        checker = VerificationChecker()
        result = checker.verify_ocr_vs_txt(ocr_results, messages)
        assert result.check_name == "OCR vs TXT"
        assert result.status in (
            VerificationStatus.PASS,
            VerificationStatus.WARNING,
            VerificationStatus.FAIL,
        )

    def test_pipeline_verification_detects_tampering(self, full_test_dir):
        file1 = full_test_dir / "original.txt"
        file1.write_text("conteúdo original", encoding="utf-8")

        hasher = FileHasher()
        original_hash = hasher.compute_hash(file1, HashAlgorithm.SHA256)

        file1.write_text("conteúdo modificado!", encoding="utf-8")

        new_hash = hasher.compute_hash(file1, HashAlgorithm.SHA256)
        assert original_hash.hash_value != new_hash.hash_value

    def test_pipeline_timeline_with_ocr(self, full_test_dir):
        messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
                sender="João",
                content="Bom dia!",
            ),
            WhatsAppMessage(
                line_number=2,
                timestamp=datetime(2024, 3, 15, 10, 5, tzinfo=timezone.utc),
                sender="Maria",
                content="Oi!",
            ),
        ]

        ocr_results = [
            OCRResult(
                source_image="screenshot.png",
                extracted_text="15/03/2024 10:00, João: Bom dia!",
                confidence=0.9,
                detected_timestamps=["15/03/2024 10:00"],
                detected_senders=["João"],
                detected_messages=["Bom dia!"],
                engine_used="tesseract",
            )
        ]

        builder = TimelineBuilder()
        timeline = builder.build_timeline(messages, ocr_results=ocr_results)
        assert len(timeline) > 2

    def test_pipeline_serialization_roundtrip(self, full_test_dir):
        case = PreservationSession(
            metadata=SessionMetadata(
                case_number="ROUND-001",
                description="Roundtrip Test",
            )
        )

        evidence = Evidence(
            file_path=full_test_dir / "test.txt",
            file_name="test.txt",
            file_size=42,
            evidence_type=EvidenceType.TEXT,
            sha256="abc123",
            blake3="def456",
        )
        case.add_evidence(evidence)

        chain = CustodyChain(evidence_id="ev-001")
        chain.add_event(
            CustodyEvent(
                event_type=CustodyEventType.IMPORT,
                description="Imported",
                hash_after="abc123",
            )
        )
        case_json = case.model_dump(mode="json")
        json_str = json.dumps(case_json, default=str)
        loaded = PreservationSession.model_validate(json.loads(json_str))

        assert loaded.metadata.case_number == "ROUND-001"
        assert len(loaded.evidence_files) == 1
        assert loaded.evidence_files[0].file_name == "test.txt"
