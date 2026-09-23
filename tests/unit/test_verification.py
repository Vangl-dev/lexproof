"""Testes unitários para o módulo de verificação."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lexproof.models.evidence import Evidence, EvidenceType
from lexproof.models.message import MessageType, WhatsAppMessage
from lexproof.models.ocr_result import OCRResult
from lexproof.models.verification import VerificationResult, VerificationStatus
from lexproof.verification.checker import VerificationChecker


@pytest.fixture
def checker() -> VerificationChecker:
    return VerificationChecker()


@pytest.fixture
def valid_messages() -> list[WhatsAppMessage]:
    return [
        WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="João",
            content="Mensagem 1",
        ),
        WhatsAppMessage(
            line_number=2,
            timestamp=datetime(2024, 3, 15, 10, 5, tzinfo=timezone.utc),
            sender="Maria",
            content="Mensagem 2",
        ),
        WhatsAppMessage(
            line_number=3,
            timestamp=datetime(2024, 3, 15, 10, 10, tzinfo=timezone.utc),
            sender="João",
            content="Mensagem 3",
        ),
    ]


class TestVerifyOcrVsTxt:
    def test_verify_ocr_vs_txt_pass(self, checker):
        ocr_results = [
            OCRResult(
                source_image="test.png",
                detected_messages=["Mensagem 1", "Mensagem 2"],
            )
        ]
        txt_messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime.now(timezone.utc),
                sender="A",
                content="Mensagem 1",
            ),
            WhatsAppMessage(
                line_number=2,
                timestamp=datetime.now(timezone.utc),
                sender="B",
                content="Mensagem 2",
            ),
        ]
        result = checker.verify_ocr_vs_txt(ocr_results, txt_messages)
        assert result.status in (VerificationStatus.PASS, VerificationStatus.WARNING)

    def test_verify_ocr_vs_txt_no_ocr(self, checker):
        result = checker.verify_ocr_vs_txt([], [])
        assert result.status == VerificationStatus.NOT_APPLICABLE

    def test_verify_ocr_vs_txt_no_txt_messages(self, checker):
        ocr_results = [
            OCRResult(source_image="test.png", detected_messages=["Msg1"])
        ]
        result = checker.verify_ocr_vs_txt(ocr_results, [])
        assert result.status == VerificationStatus.WARNING

    def test_verify_ocr_vs_txt_no_ocr_messages(self, checker):
        ocr_results = [OCRResult(source_image="test.png", detected_messages=[])]
        txt_messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime.now(timezone.utc),
                sender="A",
                content="Msg1",
            )
        ]
        result = checker.verify_ocr_vs_txt(ocr_results, txt_messages)
        assert result.status == VerificationStatus.WARNING

    def test_verify_ocr_vs_txt_both_empty(self, checker):
        ocr_results = [
            OCRResult(source_image="test.png", detected_messages=[], extracted_text="")
        ]
        result = checker.verify_ocr_vs_txt(ocr_results, [])
        assert result.status == VerificationStatus.INCONCLUSIVE

    def test_verify_ocr_vs_txt_fail(self, checker):
        ocr_results = [
            OCRResult(
                source_image="test.png",
                detected_messages=["Completamente diferente"],
            )
        ]
        txt_messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime.now(timezone.utc),
                sender="A",
                content="Totalmente outro texto diferente",
            ),
        ]
        result = checker.verify_ocr_vs_txt(ocr_results, txt_messages)
        assert result.status in (VerificationStatus.FAIL, VerificationStatus.WARNING)


class TestVerifyTimestamps:
    def test_verify_timestamps_valid(self, checker, valid_messages):
        result = checker.verify_timestamps(valid_messages)
        assert result.status == VerificationStatus.PASS
        assert result.details["total_messages"] == 3

    def test_verify_timestamps_empty(self, checker):
        result = checker.verify_timestamps([])
        assert result.status == VerificationStatus.NOT_APPLICABLE

    def test_verify_timestamps_duplicates(self, checker):
        ts = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        messages = [
            WhatsAppMessage(line_number=1, timestamp=ts, sender="A", content="1"),
            WhatsAppMessage(line_number=2, timestamp=ts, sender="B", content="2"),
        ]
        result = checker.verify_timestamps(messages)
        assert result.status in (
            VerificationStatus.WARNING,
            VerificationStatus.FAIL,
        )

    def test_verify_timestamps_out_of_order(self, checker):
        messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime(2024, 3, 15, 10, 10, tzinfo=timezone.utc),
                sender="A",
                content="Depois",
            ),
            WhatsAppMessage(
                line_number=2,
                timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
                sender="B",
                content="Antes",
            ),
        ]
        result = checker.verify_timestamps(messages)
        assert result.status in (
            VerificationStatus.WARNING,
            VerificationStatus.FAIL,
        )
        assert len(result.details["issues"]) >= 1

    def test_verify_timestamps_suspicious_year(self, checker):
        messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime(1999, 3, 15, 10, 0, tzinfo=timezone.utc),
                sender="A",
                content="Mensagem antiga",
            ),
            WhatsAppMessage(
                line_number=2,
                timestamp=datetime(2024, 3, 15, 10, 5, tzinfo=timezone.utc),
                sender="B",
                content="Mensagem normal",
            ),
        ]
        result = checker.verify_timestamps(messages)
        assert result.status in (
            VerificationStatus.WARNING,
            VerificationStatus.FAIL,
        )


class TestVerifySenders:
    def test_verify_senders_valid(self, checker, valid_messages):
        result = checker.verify_senders(valid_messages)
        assert result.status == VerificationStatus.PASS
        assert result.details["unique_senders"] == 2

    def test_verify_senders_empty(self, checker):
        result = checker.verify_senders([])
        assert result.status == VerificationStatus.NOT_APPLICABLE

    def test_verify_senders_empty_sender(self, checker):
        messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime.now(timezone.utc),
                sender="",
                content="Sem remetente",
            ),
            WhatsAppMessage(
                line_number=2,
                timestamp=datetime.now(timezone.utc),
                sender="João",
                content="Com remetente",
            ),
        ]
        result = checker.verify_senders(messages)
        assert result.details["empty_sender_count"] >= 1

    def test_verify_senders_long_name(self, checker):
        long_name = "A" * 150
        messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime.now(timezone.utc),
                sender=long_name,
                content="Mensagem",
            ),
        ]
        result = checker.verify_senders(messages)
        assert len(result.details["issues"]) >= 1


class TestVerifyMessageOrder:
    def test_verify_message_order_valid(self, checker, valid_messages):
        result = checker.verify_message_order(valid_messages)
        assert result.status == VerificationStatus.PASS
        assert result.details["order_ratio"] == 1.0

    def test_verify_message_order_single_message(self, checker):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime.now(timezone.utc),
            sender="A",
            content="Única",
        )
        result = checker.verify_message_order([msg])
        assert result.status == VerificationStatus.NOT_APPLICABLE

    def test_verify_message_order_out_of_order(self, checker):
        messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime(2024, 3, 15, 10, 10, tzinfo=timezone.utc),
                sender="A",
                content="Depois",
            ),
            WhatsAppMessage(
                line_number=2,
                timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
                sender="B",
                content="Antes",
            ),
        ]
        result = checker.verify_message_order(messages)
        assert result.details["out_of_order_count"] == 1
        assert result.details["order_ratio"] == 0.0

    def test_verify_message_order_mostly_ordered(self, checker):
        base = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        messages = [
            WhatsAppMessage(line_number=1, timestamp=base, sender="A", content="1"),
            WhatsAppMessage(
                line_number=2,
                timestamp=base + timedelta(minutes=1),
                sender="B",
                content="2",
            ),
            WhatsAppMessage(
                line_number=3,
                timestamp=base + timedelta(minutes=2),
                sender="A",
                content="3",
            ),
            WhatsAppMessage(
                line_number=4,
                timestamp=base + timedelta(seconds=30),
                sender="B",
                content="4",
            ),
            WhatsAppMessage(
                line_number=5,
                timestamp=base + timedelta(minutes=3),
                sender="A",
                content="5",
            ),
        ]
        result = checker.verify_message_order(messages)
        assert result.details["order_ratio"] >= 0.7


class TestVerifyMessageCount:
    def test_verify_message_count_valid(self, checker, valid_messages):
        result = checker.verify_message_count(valid_messages)
        assert result.status == VerificationStatus.PASS
        assert result.details["total"] == 3

    def test_verify_message_count_empty(self, checker):
        result = checker.verify_message_count([])
        assert result.status == VerificationStatus.NOT_APPLICABLE

    def test_verify_message_count_with_deletions(self, checker):
        messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime.now(timezone.utc),
                sender="A",
                content="Normal",
                is_deleted=False,
            ),
            WhatsAppMessage(
                line_number=2,
                timestamp=datetime.now(timezone.utc),
                sender="B",
                content="Deletada",
                is_deleted=True,
            ),
        ]
        result = checker.verify_message_count(messages)
        assert result.details["deleted_count"] == 1

    def test_verify_message_count_high_deletion_ratio(self, checker):
        messages = [
            WhatsAppMessage(
                line_number=i,
                timestamp=datetime.now(timezone.utc),
                sender="A",
                content=f"Msg {i}",
                is_deleted=True,
            )
            for i in range(1, 11)
        ]
        messages.append(
            WhatsAppMessage(
                line_number=11,
                timestamp=datetime.now(timezone.utc),
                sender="B",
                content="Normal",
                is_deleted=False,
            )
        )
        result = checker.verify_message_count(messages)
        assert result.status == VerificationStatus.WARNING

    def test_verify_message_count_duplicate_line_numbers(self, checker):
        messages = [
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime.now(timezone.utc),
                sender="A",
                content="1",
            ),
            WhatsAppMessage(
                line_number=1,
                timestamp=datetime.now(timezone.utc),
                sender="B",
                content="2",
            ),
        ]
        result = checker.verify_message_count(messages)
        assert len(result.details["issues"]) >= 1


class TestRunAllVerifications:
    def test_run_all_verifications(self, checker, valid_messages):
        case_data = {"messages": valid_messages}
        results = checker.run_all_verifications(case_data)
        assert len(results) >= 4

    def test_run_all_verifications_with_ocr(self, checker, valid_messages):
        ocr_results = [
            OCRResult(
                source_image="test.png",
                detected_messages=["Mensagem 1", "Mensagem 2"],
            )
        ]
        case_data = {
            "ocr_results": ocr_results,
            "txt_messages": valid_messages,
            "messages": valid_messages,
        }
        results = checker.run_all_verifications(case_data)
        assert len(results) >= 5

    def test_run_all_verifications_empty(self, checker):
        results = checker.run_all_verifications({})
        assert results == []

    def test_run_all_verifications_with_evidence(self, checker, tmp_path):
        test_file = tmp_path / "evidence.txt"
        test_file.write_text("test content", encoding="utf-8")
        evidence = Evidence(
            file_path=test_file,
            file_name="evidence.txt",
            file_size=12,
            evidence_type=EvidenceType.TEXT,
            sha256="abc123",
            blake3="def456",
        )
        case_data = {"evidence_files": [evidence]}
        results = checker.run_all_verifications(case_data)
        assert len(results) >= 1
        assert any(r.check_name == "Integridade de Arquivos" for r in results)
