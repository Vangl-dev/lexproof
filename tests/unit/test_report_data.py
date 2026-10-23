"""Testes do builder único de report_data e do consumo pelo PDF."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from lexproof.models.correlation import (
    CorrelationMatch,
    CorrelationResult,
    CorrelationType,
)
from lexproof.models.evidence import Evidence, EvidenceType, ImageEvidence
from lexproof.models.hash_result import HashAlgorithm, HashResult
from lexproof.models.message import WhatsAppMessage
from lexproof.models.ocr_result import OCRResult
from lexproof.models.quality_grade import GradeCriteria, QualityGrade
from lexproof.models.timeline import TimelineEntry, TimelineEntryType
from lexproof.models.verification import VerificationResult, VerificationStatus
from lexproof.reports.pdf_report import PDFReportGenerator
from lexproof.reports.report_data import build_report_data, hash_algorithm_rows


@pytest.fixture
def evidence(tmp_path: Path) -> Evidence:
    p = tmp_path / "conversa.txt"
    p.write_text("conteudo", encoding="utf-8")
    return Evidence(
        file_path=p,
        file_name=p.name,
        file_size=8,
        evidence_type=EvidenceType.TEXT,
        sha256="a" * 64,
        blake3="b" * 64,
    )


@pytest.fixture
def image_evidence(tmp_path: Path) -> ImageEvidence:
    from PIL import Image

    p = tmp_path / "screenshot_conversa.png"
    Image.new("RGB", (40, 40), color="blue").save(p, format="PNG")
    return ImageEvidence(
        file_path=p,
        file_name=p.name,
        file_size=p.stat().st_size,
        width=40,
        height=40,
        format="PNG",
        sha256="c" * 64,
        blake3="d" * 64,
    )


@pytest.fixture
def messages() -> list[WhatsAppMessage]:
    return [
        WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="João",
            content="Bom dia!",
        ),
        WhatsAppMessage(
            line_number=2,
            timestamp=datetime(2024, 3, 15, 10, 1, tzinfo=timezone.utc),
            sender="Maria",
            content="Oi!",
        ),
    ]


@pytest.fixture
def ocr_result(image_evidence: ImageEvidence) -> OCRResult:
    return OCRResult(
        source_image=str(image_evidence.file_path),
        extracted_text="15/03/2024 10:00, João: Bom dia!",
        confidence=0.95,
        engine_used="tesseract",
    )


@pytest.fixture
def hash_results(evidence: Evidence) -> list[HashResult]:
    return [
        HashResult(
            algorithm=HashAlgorithm.SHA256,
            hash_value="a" * 64,
            file_path=evidence.file_path,
        ),
        HashResult(
            algorithm=HashAlgorithm.BLAKE3,
            hash_value="b" * 64,
            file_path=evidence.file_path,
        ),
    ]


@pytest.fixture
def timeline() -> list[TimelineEntry]:
    return [
        TimelineEntry(
            entry_type=TimelineEntryType.MESSAGE,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="João",
            content="Bom dia!",
        ),
        TimelineEntry(
            entry_type=TimelineEntryType.MESSAGE,
            timestamp=datetime(2024, 3, 15, 10, 1, tzinfo=timezone.utc),
            sender="Maria",
            content="Oi!",
        ),
    ]


@pytest.fixture
def correlation(image_evidence: Evidence) -> CorrelationResult:
    return CorrelationResult(
        correlation_type=CorrelationType.PRINT_TO_TXT,
        matches=[
            CorrelationMatch(
                source_evidence_id=image_evidence.id,
                target_evidence_id="export-1",
                target_text="Bom dia!",
                confidence=0.9,
                match_type="exact",
            )
        ],
        overall_confidence=0.9,
    )


@pytest.fixture
def quality() -> QualityGrade:
    return QualityGrade.calculate(GradeCriteria(has_hashes=True, has_prints=True))


def _base_kwargs(**overrides):
    kwargs: dict = {
        "evidences": [],
        "messages": [],
        "ocr_results": [],
        "hash_results": [],
        "timeline": [],
        "correlations": [],
        "verification_results": [],
        "quality_grade": "B",
    }
    kwargs.update(overrides)
    return kwargs


class TestBuildReportData:
    def test_includes_messages(self, messages):
        data = build_report_data(**_base_kwargs(messages=messages))
        assert "messages" in data
        assert len(data["messages"]) == 2
        assert data["messages"][0].content == "Bom dia!"

    def test_includes_timeline_real(self, timeline):
        data = build_report_data(**_base_kwargs(timeline=timeline))
        assert "timeline" in data
        assert len(data["timeline"]) == 2
        assert data["timeline"][0].sender == "João"

    def test_does_not_reconstruct_timeline_from_messages(self, messages, timeline):
        data = build_report_data(
            **_base_kwargs(messages=messages, timeline=timeline)
        )
        assert len(data["timeline"]) == len(timeline)
        assert all(isinstance(t, TimelineEntry) for t in data["timeline"])

    def test_empty_timeline_stays_empty(self, messages):
        data = build_report_data(**_base_kwargs(messages=messages, timeline=[]))
        assert data["timeline"] == []

    def test_metadata_client_case_technician(self):
        data = build_report_data(
            **_base_kwargs(
                client_name="Cliente Silva",
                case_number="PROC-2024-001",
                responsible_technician="Perito Ana",
            )
        )
        meta = data["metadata"]
        assert meta["client_name"] == "Cliente Silva"
        assert meta["case_number"] == "PROC-2024-001"
        assert meta["examiner"] == "Perito Ana"
        assert meta["title"] == "PROC-2024-001"
        assert "Cliente Silva" in meta["description"]

    def test_does_not_invent_examiner_when_missing(self):
        data = build_report_data(**_base_kwargs())
        assert data["metadata"]["examiner"] == "-"
        assert data["metadata"]["client_name"] == ""
        assert data["metadata"]["case_number"] == ""

    def test_quality_grade_object_and_string(self, quality):
        data_obj = build_report_data(**_base_kwargs(quality_grade=quality))
        data_str = build_report_data(**_base_kwargs(quality_grade="A"))
        assert data_obj["metadata"]["quality_grade"] == quality.level.value
        assert data_str["metadata"]["quality_grade"] == "A"

    def test_session_id_as_case_id(self):
        data = build_report_data(**_base_kwargs(session_id="LEX-TEST-1"))
        assert data["metadata"]["case_id"] == "LEX-TEST-1"

    def test_correlations_mapped_from_real_model(
        self, correlation, image_evidence
    ):
        data = build_report_data(
            **_base_kwargs(
                correlations=[correlation],
                evidences=[image_evidence],
            )
        )
        corr = data["correlations"][0]
        assert corr["evidence_name"] == image_evidence.file_name
        assert "Bom dia!" in corr["matched_messages"]
        assert corr["confidence"] == "90%"
        assert corr["result"]

    def test_correlation_without_evidence_match_has_empty_name(self, correlation):
        data = build_report_data(
            **_base_kwargs(correlations=[correlation], evidences=[])
        )
        assert data["correlations"][0]["evidence_name"] == ""

    def test_ocr_results_passed_through(self, ocr_result):
        data = build_report_data(**_base_kwargs(ocr_results=[ocr_result]))
        assert data["ocr_results"][0].source_image.endswith("screenshot_conversa.png")

    def test_hashes_and_global_hash(self, hash_results):
        data = build_report_data(**_base_kwargs(hash_results=hash_results))
        assert data["hashes"][0]["sha256"] == "a" * 64
        assert data["hashes"][0]["blake3"] == "b" * 64
        assert len(data["global_hash"]) == 64

    def test_verifications_mapped(
        self,
    ):
        vr = VerificationResult(
            check_name="Integridade de Arquivos",
            status=VerificationStatus.PASS,
        )
        data = build_report_data(**_base_kwargs(verification_results=[vr]))
        assert data["verifications"][0]["check_name"] == "Integridade de Arquivos"
        assert data["verifications"][0]["status"] == "PASS"


class TestHashAlgorithmRows:
    def test_derives_from_existing_keys_only(self):
        hashes = [
            {"file_name": "a.txt", "sha256": "aa", "blake3": "bb"},
        ]
        rows = hash_algorithm_rows(hashes)
        assert rows == [
            ["a.txt", "sha256", "aa"],
            ["a.txt", "blake3", "bb"],
        ]

    def test_does_not_invent_algorithm_column(self):
        hashes = [{"file_name": "b.txt", "sha256": "cc"}]
        rows = hash_algorithm_rows(hashes)
        assert all(r[1] for r in rows)
        assert not any(r[1] == "" for r in rows)

    def test_hash_value_label(self):
        hashes = [{"file_name": "c.txt", "hash_value": "dd"}]
        rows = hash_algorithm_rows(hashes)
        assert rows[0][1] == "hash"

    def test_legacy_algorithm_key_fallback(self):
        hashes = [
            {"file_name": "d.txt", "algorithm": "sha256", "hash_value": "ee"},
        ]
        rows = hash_algorithm_rows(hashes)
        assert rows == [["d.txt", "sha256", "ee"]]

    def test_empty_file_name_only_skipped(self):
        hashes = [{"file_name": "e.txt"}]
        assert hash_algorithm_rows(hashes) == []


class TestPDFConsumption:
    def test_pdf_generates_with_messages_and_timeline(
        self,
        tmp_path,
        evidence,
        image_evidence,
        messages,
        ocr_result,
        hash_results,
        timeline,
        correlation,
        quality,
    ):
        data = build_report_data(
            evidences=[evidence, image_evidence],
            messages=messages,
            ocr_results=[ocr_result],
            hash_results=hash_results,
            timeline=timeline,
            correlations=[correlation],
            verification_results=[],
            quality_grade=quality,
            session_id="LEX-TEST-PDF",
            client_name="Cliente Teste",
            case_number="PROC-999",
            responsible_technician="Perito Ana",
        )
        out = tmp_path / "relatorio_teste.pdf"
        PDFReportGenerator().generate(data, out)
        assert out.exists()
        assert out.stat().st_size > 0
