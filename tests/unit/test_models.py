"""Testes unitários para os modelos de dados do LexProof."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from lexproof.models.case import CaseFile, CaseMetadata
from lexproof.models.custody import CustodyChain, CustodyEvent, CustodyEventType
from lexproof.models.evidence import EvidenceFile, EvidenceType
from lexproof.models.hash_result import HashAlgorithm, HashResult
from lexproof.models.message import MessageType, WhatsAppMessage
from lexproof.models.ocr_result import OCRResult
from lexproof.models.report import ReportConfig, ReportType
from lexproof.models.timeline import TimelineEntry, TimelineEntryType
from lexproof.models.verification import VerificationResult, VerificationStatus


class TestEvidenceType:
    def test_evidence_type_enum_values(self):
        assert EvidenceType.IMAGE == "image"
        assert EvidenceType.TEXT == "text"
        assert EvidenceType.VIDEO == "video"
        assert EvidenceType.ARCHIVE == "archive"
        assert EvidenceType.MESSAGE == "message"
        assert EvidenceType.DOCUMENT == "document"
        assert EvidenceType.OTHER == "other"

    def test_evidence_type_is_string_enum(self):
        assert isinstance(EvidenceType.IMAGE, str)
        assert EvidenceType.IMAGE == "image"


class TestEvidenceFileCreation:
    def test_evidence_file_creation(self):
        evidence = EvidenceFile(
            file_path=Path("/tmp/test.txt"),
            file_name="test.txt",
            file_size=1024,
            evidence_type=EvidenceType.TEXT,
        )
        assert evidence.file_path == Path("/tmp/test.txt")
        assert evidence.file_name == "test.txt"
        assert evidence.file_size == 1024
        assert evidence.evidence_type == EvidenceType.TEXT
        assert evidence.imported_at is not None
        assert evidence.original_hash is None
        assert evidence.description == ""
        assert evidence.tags == []

    def test_evidence_file_with_all_fields(self):
        evidence = EvidenceFile(
            file_path=Path("/tmp/evidence.png"),
            file_name="evidence.png",
            file_size=5120,
            evidence_type=EvidenceType.IMAGE,
            imported_at=datetime(2024, 3, 15, tzinfo=timezone.utc),
            original_hash="abc123hash",
            description="Screenshot de conversa",
            tags=["screenshot", "conversa"],
        )
        assert evidence.original_hash == "abc123hash"
        assert evidence.description == "Screenshot de conversa"
        assert "screenshot" in evidence.tags

    def test_evidence_file_invalid_size(self):
        with pytest.raises(ValidationError):
            EvidenceFile(
                file_path=Path("/tmp/test.txt"),
                file_name="test.txt",
                file_size=-1,
                evidence_type=EvidenceType.TEXT,
            )

    def test_evidence_file_missing_required_fields(self):
        with pytest.raises(ValidationError):
            EvidenceFile(file_path=Path("/tmp/test.txt"))


class TestMessageType:
    def test_message_type_enum_values(self):
        assert MessageType.TEXT == "text"
        assert MessageType.MEDIA == "media"
        assert MessageType.DELETED == "deleted"
        assert MessageType.EDITED == "edited"
        assert MessageType.SYSTEM == "system"
        assert MessageType.STICKER == "sticker"
        assert MessageType.AUDIO == "audio"
        assert MessageType.VIDEO == "video"
        assert MessageType.LINK == "link"
        assert MessageType.MULTI == "multi"


class TestWhatsAppMessageCreation:
    def test_whatsapp_message_creation(self):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc),
            sender="João",
            content="Olá!",
        )
        assert msg.line_number == 1
        assert msg.sender == "João"
        assert msg.content == "Olá!"
        assert msg.message_type == MessageType.TEXT
        assert msg.is_deleted is False
        assert msg.is_edited is False
        assert msg.media_reference is None
        assert msg.ocr_extracted is False
        assert msg.id is not None

    def test_whatsapp_message_with_all_fields(self):
        msg = WhatsAppMessage(
            line_number=10,
            timestamp=datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc),
            sender="Maria",
            content="<Mídia ocultada>",
            message_type=MessageType.MEDIA,
            is_deleted=False,
            is_edited=False,
            media_reference="image",
            raw_text="15/03/2024 10:30, Maria: <Mídia ocultada>",
            ocr_extracted=True,
        )
        assert msg.message_type == MessageType.MEDIA
        assert msg.media_reference == "image"
        assert msg.ocr_extracted is True
        assert msg.raw_text.startswith("15/03/2024")

    def test_whatsapp_message_invalid_line_number(self):
        with pytest.raises(ValidationError):
            WhatsAppMessage(
                line_number=0,
                timestamp=datetime.now(timezone.utc),
                sender="Teste",
                content="Teste",
            )

    def test_whatsapp_message_deleted(self):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc),
            sender="João",
            content="<Esta mensagem foi apagada>",
            message_type=MessageType.DELETED,
            is_deleted=True,
        )
        assert msg.is_deleted is True
        assert msg.message_type == MessageType.DELETED

    def test_whatsapp_message_edited(self):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc),
            sender="João",
            content="<Esta mensagem foi editada>",
            message_type=MessageType.EDITED,
            is_edited=True,
        )
        assert msg.is_edited is True


class TestTimelineEntry:
    def test_timeline_entry_creation(self):
        entry = TimelineEntry(
            entry_type=TimelineEntryType.MESSAGE,
            timestamp=datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc),
            sender="João",
            content="Bom dia!",
        )
        assert entry.entry_type == TimelineEntryType.MESSAGE
        assert entry.sender == "João"
        assert entry.content == "Bom dia!"
        assert entry.id is not None
        assert entry.inconsistencies == []

    def test_timeline_entry_with_inconsistencies(self):
        entry = TimelineEntry(
            entry_type=TimelineEntryType.TIMESTAMP_GAP,
            timestamp=datetime(2024, 3, 15, 12, 0, tzinfo=timezone.utc),
            content="Lacuna detectada",
            inconsistencies=["Lacuna temporal de 2.0h detectada"],
        )
        assert len(entry.inconsistencies) == 1

    def test_timeline_entry_type_enum(self):
        assert TimelineEntryType.MESSAGE == "message"
        assert TimelineEntryType.MEDIA == "media"
        assert TimelineEntryType.SYSTEM_EVENT == "system_event"
        assert TimelineEntryType.DELETION == "deletion"
        assert TimelineEntryType.TIMESTAMP_GAP == "timestamp_gap"
        assert TimelineEntryType.ANOMALY == "anomaly"

    def test_timeline_entry_invalid_line_number(self):
        with pytest.raises(ValidationError):
            TimelineEntry(
                entry_type=TimelineEntryType.MESSAGE,
                timestamp=datetime.now(timezone.utc),
                line_in_source=0,
            )


class TestHashResult:
    def test_hash_result_creation(self):
        result = HashResult(
            algorithm=HashAlgorithm.SHA256,
            hash_value="abc123def456",
            file_path=Path("/tmp/test.txt"),
        )
        assert result.algorithm == HashAlgorithm.SHA256
        assert result.hash_value == "abc123def456"
        assert result.computed_at is not None
        assert result.file_size is None

    def test_hash_result_with_file_size(self):
        result = HashResult(
            algorithm=HashAlgorithm.SHA3_512,
            hash_value="abc123def456",
            file_path=Path("/tmp/test.txt"),
            file_size=1024,
        )
        assert result.file_size == 1024

    def test_hash_algorithm_enum(self):
        assert HashAlgorithm.SHA256 == "sha256"
        assert HashAlgorithm.SHA3_512 == "sha3_512"
        assert HashAlgorithm.BLAKE3 == "blake3"


class TestCustodyEvent:
    def test_custody_event_creation(self):
        event = CustodyEvent(
            event_type=CustodyEventType.IMPORT,
            description="Arquivo importado",
        )
        assert event.event_type == CustodyEventType.IMPORT
        assert event.description == "Arquivo importado"
        assert event.timestamp is not None
        assert event.hash_before is None
        assert event.hash_after is None
        assert event.operator == "system"
        assert event.metadata == {}

    def test_custody_event_with_metadata(self):
        event = CustodyEvent(
            event_type=CustodyEventType.HASH,
            description="Hash calculado",
            hash_before="old_hash",
            hash_after="new_hash",
            operator="investigador",
            metadata={"algoritmo": "sha256"},
        )
        assert event.hash_before == "old_hash"
        assert event.hash_after == "new_hash"
        assert event.operator == "investigador"
        assert event.metadata["algoritmo"] == "sha256"

    def test_custody_event_type_enum(self):
        assert CustodyEventType.IMPORT == "import"
        assert CustodyEventType.HASH == "hash"
        assert CustodyEventType.VERIFY == "verify"
        assert CustodyEventType.EXPORT == "export"
        assert CustodyEventType.MODIFICATION == "modification"
        assert CustodyEventType.ANNOTATION == "annotation"


class TestCustodyChain:
    def test_custody_chain_creation(self):
        chain = CustodyChain(evidence_id="ev-001")
        assert chain.evidence_id == "ev-001"
        assert chain.events == []
        assert chain.created_at is not None

    def test_custody_chain_add_event(self):
        chain = CustodyChain(evidence_id="ev-001")
        event = CustodyEvent(
            event_type=CustodyEventType.IMPORT,
            description="Importado",
            hash_after="abc123",
        )
        chain.add_event(event)
        assert len(chain.events) == 1
        assert chain.events[0].event_type == CustodyEventType.IMPORT

    def test_custody_chain_get_last_hash(self):
        chain = CustodyChain(evidence_id="ev-001")
        chain.add_event(
            CustodyEvent(
                event_type=CustodyEventType.IMPORT,
                description="Importado",
                hash_after="first_hash",
            )
        )
        chain.add_event(
            CustodyEvent(
                event_type=CustodyEventType.HASH,
                description="Re-hash",
                hash_after="second_hash",
            )
        )
        assert chain.get_last_hash() == "second_hash"

    def test_custody_chain_get_last_hash_empty(self):
        chain = CustodyChain(evidence_id="ev-001")
        assert chain.get_last_hash() is None

    def test_custody_chain_get_last_hash_no_after(self):
        chain = CustodyChain(evidence_id="ev-001")
        chain.add_event(
            CustodyEvent(
                event_type=CustodyEventType.IMPORT,
                description="Importado",
            )
        )
        assert chain.get_last_hash() is None


class TestOCRResult:
    def test_ocr_result_creation(self):
        result = OCRResult(source_image="test.png")
        assert result.source_image == "test.png"
        assert result.extracted_text == ""
        assert result.confidence == 0.0
        assert result.detected_timestamps == []
        assert result.detected_senders == []
        assert result.detected_messages == []
        assert result.engine_used == ""
        assert result.processing_time == 0.0

    def test_ocr_result_with_data(self):
        result = OCRResult(
            source_image="screenshot.png",
            extracted_text="Texto extraído",
            confidence=0.85,
            detected_timestamps=["15/03/2024 10:30"],
            detected_senders=["João"],
            detected_messages=["Olá!"],
            engine_used="tesseract",
            processing_time=2.5,
        )
        assert result.confidence == 0.85
        assert len(result.detected_timestamps) == 1
        assert result.engine_used == "tesseract"

    def test_ocr_result_invalid_confidence(self):
        with pytest.raises(ValidationError):
            OCRResult(source_image="test.png", confidence=1.5)

    def test_ocr_result_negative_confidence(self):
        with pytest.raises(ValidationError):
            OCRResult(source_image="test.png", confidence=-0.1)


class TestVerificationResult:
    def test_verification_result_creation(self):
        result = VerificationResult(
            check_name="Teste",
            status=VerificationStatus.PASS,
        )
        assert result.check_name == "Teste"
        assert result.status == VerificationStatus.PASS
        assert result.expected is None
        assert result.actual is None
        assert result.details == {}
        assert result.timestamp is not None

    def test_verification_result_with_details(self):
        result = VerificationResult(
            check_name="Verificação de Hash",
            status=VerificationStatus.FAIL,
            expected="abc123",
            actual="def456",
            details={"differences": ["hash divergente"]},
        )
        assert result.status == VerificationStatus.FAIL
        assert result.expected == "abc123"
        assert result.actual == "def456"
        assert "differences" in result.details

    def test_verification_status_enum(self):
        assert VerificationStatus.PASS == "pass"
        assert VerificationStatus.FAIL == "fail"
        assert VerificationStatus.WARNING == "warning"
        assert VerificationStatus.INCONCLUSIVE == "inconclusive"
        assert VerificationStatus.NOT_APPLICABLE == "not_applicable"


class TestReportConfig:
    def test_report_config_creation(self):
        config = ReportConfig(
            report_type=ReportType.PDF,
            output_path=Path("/tmp/report.pdf"),
        )
        assert config.report_type == ReportType.PDF
        assert config.output_path == Path("/tmp/report.pdf")
        assert config.include_timeline is True
        assert config.include_ocr is True
        assert config.include_hashes is True
        assert config.include_custody is True
        assert config.include_verification is True
        assert config.include_qr_code is False
        assert config.custom_notes == ""

    def test_report_config_all_options(self):
        config = ReportConfig(
            report_type=ReportType.HTML,
            output_path=Path("/tmp/report.html"),
            include_timeline=False,
            include_ocr=False,
            include_hashes=False,
            include_custody=False,
            include_verification=False,
            include_qr_code=True,
            custom_notes="Notas personalizadas",
        )
        assert config.include_timeline is False
        assert config.include_qr_code is True
        assert config.custom_notes == "Notas personalizadas"

    def test_report_type_enum(self):
        assert ReportType.PDF == "pdf"
        assert ReportType.HTML == "html"
        assert ReportType.JSON == "json"
        assert ReportType.MANIFEST == "manifest"
        assert ReportType.ZIP == "zip"


class TestCaseMetadata:
    def test_case_metadata_creation(self):
        metadata = CaseMetadata()
        assert metadata.case_id is not None
        assert len(metadata.case_id) == 32
        assert metadata.case_number == ""
        assert metadata.title == "Sem título"
        assert metadata.description == ""
        assert metadata.tags == []

    def test_case_metadata_with_values(self):
        metadata = CaseMetadata(
            case_number="2024-001",
            title="Caso Teste",
            description="Descrição",
            client_name="João",
            lawyer_name="Maria",
            court="TJSP",
            tags=["civil", "urgente"],
        )
        assert metadata.case_number == "2024-001"
        assert metadata.title == "Caso Teste"
        assert "civil" in metadata.tags


class TestCaseFile:
    def test_case_file_creation(self):
        case = CaseFile()
        assert case.metadata is not None
        assert case.evidence_files == []
        assert case.hash_results == []
        assert case.custody_chains == []

    def test_case_file_add_evidence(self, sample_evidence_files):
        case = CaseFile()
        case.add_evidence(sample_evidence_files[0])
        assert len(case.evidence_files) == 1
        assert case.evidence_files[0].file_name == "evidence.txt"

    def test_case_file_get_evidence_by_name(self, sample_evidence_files):
        case = CaseFile()
        case.add_evidence(sample_evidence_files[0])
        found = case.get_evidence_by_name("evidence.txt")
        assert found is not None
        assert found.file_name == "evidence.txt"

    def test_case_file_get_evidence_by_name_not_found(self, sample_evidence_files):
        case = CaseFile()
        case.add_evidence(sample_evidence_files[0])
        found = case.get_evidence_by_name("nonexistent.txt")
        assert found is None

    def test_case_file_add_custody_chain(self):
        case = CaseFile()
        chain = CustodyChain(evidence_id="ev-001")
        case.add_custody_chain(chain)
        assert len(case.custody_chains) == 1

    def test_case_file_get_custody_chain(self):
        case = CaseFile()
        chain = CustodyChain(evidence_id="ev-001")
        case.add_custody_chain(chain)
        found = case.get_custody_chain("ev-001")
        assert found is not None
        assert found.evidence_id == "ev-001"

    def test_case_file_get_custody_chain_not_found(self):
        case = CaseFile()
        found = case.get_custody_chain("nonexistent")
        assert found is None
