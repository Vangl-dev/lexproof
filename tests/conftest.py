"""Fixtures compartilhadas para testes do LexProof."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from lexproof.models.case import PreservationSession, SessionMetadata
from lexproof.models.custody import CustodyChain, CustodyEvent, CustodyEventType
from lexproof.models.evidence import Evidence, EvidenceType
from lexproof.models.hash_result import HashAlgorithm, HashResult
from lexproof.models.message import MessageType, WhatsAppMessage
from lexproof.models.ocr_result import OCRResult
from lexproof.models.report import ReportConfig, ReportType
from lexproof.models.timeline import TimelineEntry, TimelineEntryType
from lexproof.models.verification import VerificationResult, VerificationStatus


@pytest.fixture(autouse=True)
def _no_network_timestamp(monkeypatch, request):
    """Testes nao chamam a TSA real; use o marcador ``network`` para isso."""
    if request.node.get_closest_marker("network"):
        return
    from lexproof.blockchain.rfc3161 import RFC3161Anchor

    def _offline(self, path):
        raise RuntimeError("TSA desabilitada nos testes")

    monkeypatch.setattr(RFC3161Anchor, "stamp_file", _offline)
    monkeypatch.setattr("lexproof.crypto.seal.time.sleep", lambda _s: None)


SAMPLE_TXT_BR = """\
15/03/2024 10:30, João: Bom dia!
15/03/2024 10:31, Maria: Olá João, tudo bem?
15/03/2024 10:32, João: Tudo ótimo!
15/03/2024 10:35, Maria: Viu a foto que mandei?
15/03/2024 10:36, João: <Mídia ocultada>
15/03/2024 10:40, Sistema: Você foi adicionado ao grupo
"""

SAMPLE_TXT_INT = """\
3/15/2024, 10:30 AM, John: Good morning!
3/15/2024, 10:31 AM, Jane: Hi John, how are you?
3/15/2024, 10:32 AM, John: All great!
3/15/2024, 10:35 AM, Jane: Did you see the image I sent?
3/15/2024, 10:36 AM, John: <Image omitted>
3/15/2024, 10:40 AM, System: You were added to the group
"""

SAMPLE_TXT_MULTILINE = """\
15/03/2024 11:00, João: Mensagem longa
que continua na próxima linha
e mais uma linha
15/03/2024 11:01, Maria: Resposta curta
"""

SAMPLE_TXT_DELETED = """\
15/03/2024 12:00, João: Mensagem normal
15/03/2024 12:01, Maria: <Esta mensagem foi apagada>
15/03/2024 12:02, João: Outra mensagem
"""

SAMPLE_TXT_MEDIA = """\
15/03/2024 13:00, João: <Mídia ocultada>
15/03/2024 13:01, Maria: <Imagem ocultada>
15/03/2024 13:02, João: <Áudio>
15/03/2024 13:03, Maria: <Vídeo>
"""

SAMPLE_TXT_LINKS = """\
15/03/2024 14:00, João: Confira https://example.com/abc
15/03/2024 14:01, Maria: E também http://test.com/path?q=1
15/03/2024 14:02, João: Mensagem normal
"""

SAMPLE_TXT_SYSTEM = """\
15/03/2024 09:00, Sistema: Mensagens e chamadas são criptografadas de ponta a ponta. Ninguém fora desta conversa pode ler ou escutá-las.
15/03/2024 09:01, João: Primeira mensagem
"""


@pytest.fixture
def sample_txt_content(tmp_path: Path) -> Path:
    """Fixture que cria um arquivo TXT de WhatsApp no formato brasileiro."""
    file_path = tmp_path / "conversa.txt"
    file_path.write_text(SAMPLE_TXT_BR, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_txt_international(tmp_path: Path) -> Path:
    """Fixture que cria um arquivo TXT de WhatsApp no formato internacional."""
    file_path = tmp_path / "conversation.txt"
    file_path.write_text(SAMPLE_TXT_INT, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_txt_multiline(tmp_path: Path) -> Path:
    """Fixture que cria um arquivo TXT com mensagens multi-linha."""
    file_path = tmp_path / "multiline.txt"
    file_path.write_text(SAMPLE_TXT_MULTILINE, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_txt_deleted(tmp_path: Path) -> Path:
    """Fixture que cria um arquivo TXT com mensagens deletadas."""
    file_path = tmp_path / "deleted.txt"
    file_path.write_text(SAMPLE_TXT_DELETED, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_txt_media(tmp_path: Path) -> Path:
    """Fixture que cria um arquivo TXT com referências de mídia."""
    file_path = tmp_path / "media.txt"
    file_path.write_text(SAMPLE_TXT_MEDIA, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_txt_links(tmp_path: Path) -> Path:
    """Fixture que cria um arquivo TXT com links."""
    file_path = tmp_path / "links.txt"
    file_path.write_text(SAMPLE_TXT_LINKS, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_txt_system(tmp_path: Path) -> Path:
    """Fixture que cria um arquivo TXT com mensagens de sistema."""
    file_path = tmp_path / "system.txt"
    file_path.write_text(SAMPLE_TXT_SYSTEM, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """Fixture que cria um arquivo PNG temporário para testes."""
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="blue")
    file_path = tmp_path / "test_image.png"
    img.save(file_path, format="PNG")
    return file_path


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Fixture que cria um arquivo PDF temporário para testes."""
    file_path = tmp_path / "test_document.pdf"
    file_path.write_bytes(b"%PDF-1.4 test content")
    return file_path


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Fixture que fornece um diretório temporário limpo."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    return work_dir


@pytest.fixture
def sample_messages() -> list[WhatsAppMessage]:
    """Fixture que retorna uma lista de mensagens WhatsApp de exemplo."""
    return [
        WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc),
            sender="João",
            content="Bom dia!",
            message_type=MessageType.TEXT,
        ),
        WhatsAppMessage(
            line_number=2,
            timestamp=datetime(2024, 3, 15, 10, 31, tzinfo=timezone.utc),
            sender="Maria",
            content="Olá João, tudo bem?",
            message_type=MessageType.TEXT,
        ),
        WhatsAppMessage(
            line_number=3,
            timestamp=datetime(2024, 3, 15, 10, 32, tzinfo=timezone.utc),
            sender="João",
            content="Tudo ótimo!",
            message_type=MessageType.TEXT,
        ),
        WhatsAppMessage(
            line_number=4,
            timestamp=datetime(2024, 3, 15, 10, 35, tzinfo=timezone.utc),
            sender="Maria",
            content="Viu a foto que mandei?",
            message_type=MessageType.TEXT,
        ),
        WhatsAppMessage(
            line_number=5,
            timestamp=datetime(2024, 3, 15, 10, 36, tzinfo=timezone.utc),
            sender="João",
            content="<Mídia ocultada>",
            message_type=MessageType.MEDIA,
            media_reference="media",
        ),
        WhatsAppMessage(
            line_number=6,
            timestamp=datetime(2024, 3, 15, 10, 40, tzinfo=timezone.utc),
            sender="Sistema",
            content="Você foi adicionado ao grupo",
            message_type=MessageType.SYSTEM,
        ),
    ]


@pytest.fixture
def sample_evidence_files(tmp_path: Path) -> list[Evidence]:
    """Fixture que retorna uma lista de arquivos de evidência de exemplo."""
    test_file = tmp_path / "evidence.txt"
    test_file.write_text("evidence content", encoding="utf-8")

    return [
        Evidence(
            file_path=test_file,
            file_name="evidence.txt",
            file_size=16,
            evidence_type=EvidenceType.TEXT,
            sha256="abc123",
            blake3="def456",
            description="Teste de evidência",
            tags=["teste"],
        ),
    ]


@pytest.fixture
def sample_ocr_results() -> list[OCRResult]:
    """Fixture que retorna uma lista de resultados OCR de exemplo."""
    return [
        OCRResult(
            source_image="test_screenshot.png",
            extracted_text="15/03/2024 10:30, João: Bom dia!\n15/03/2024 10:31, Maria: Olá!",
            confidence=0.95,
            detected_timestamps=["15/03/2024 10:30", "15/03/2024 10:31"],
            detected_senders=["João", "Maria"],
            detected_messages=["Bom dia!", "Olá!"],
            engine_used="tesseract",
            processing_time=1.5,
        ),
    ]


@pytest.fixture
def mock_settings(tmp_path: Path):
    """Fixture que retorna um objeto Settings para testes."""
    from lexproof.config.settings import Settings

    return Settings(
        log_directory=tmp_path / "logs",
        output_directory=tmp_path / "output",
        temp_directory=tmp_path / "temp",
    )


@pytest.fixture
def sample_case_metadata() -> SessionMetadata:
    """Fixture que retorna metadados de caso de exemplo."""
    return SessionMetadata(
        case_number="PROC-2024-001",
        description="Descrição do caso de teste",
        client_name="Cliente Teste",
        responsible_technician="Advogado Teste",
    )
