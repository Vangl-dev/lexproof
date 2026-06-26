"""Testes unitários para o parser de WhatsApp."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from lexproof.models.message import MessageType, WhatsAppMessage
from lexproof.parsers.base import ParseError
from lexproof.parsers.whatsapp_parser import WhatsAppParser


@pytest.fixture
def parser() -> WhatsAppParser:
    return WhatsAppParser()


class TestParseBrazilianFormat:
    def test_parse_brazilian_format(self, parser, sample_txt_content):
        messages = parser.parse(sample_txt_content)
        assert len(messages) == 6
        assert messages[0].sender == "João"
        assert messages[0].content == "Bom dia!"
        assert messages[0].timestamp.year == 2024
        assert messages[0].timestamp.month == 3
        assert messages[0].timestamp.day == 15

    def test_parse_brazilian_format_senders(self, parser, sample_txt_content):
        messages = parser.parse(sample_txt_content)
        senders = [m.sender for m in messages]
        assert "João" in senders
        assert "Maria" in senders
        assert "Sistema" in senders

    def test_parse_brazilian_timestamp_format(self, parser, sample_txt_content):
        messages = parser.parse(sample_txt_content)
        assert messages[0].timestamp.hour == 10
        assert messages[0].timestamp.minute == 30


class TestParseInternationalFormat:
    def test_parse_international_format(self, parser, sample_txt_international):
        messages = parser.parse(sample_txt_international)
        assert len(messages) == 6
        assert messages[0].sender == "John"
        assert messages[0].content == "Good morning!"
        assert messages[0].timestamp.year == 2024
        assert messages[0].timestamp.month == 3
        assert messages[0].timestamp.day == 15

    def test_parse_international_senders(self, parser, sample_txt_international):
        messages = parser.parse(sample_txt_international)
        senders = [m.sender for m in messages]
        assert "John" in senders
        assert "Jane" in senders
        assert "System" in senders


class TestParseMultiLineMessages:
    def test_parse_multi_line_messages(self, parser, sample_txt_multiline):
        messages = parser.parse(sample_txt_multiline)
        assert len(messages) == 2
        multiline_msg = messages[0]
        assert "continua na próxima linha" in multiline_msg.content
        assert "e mais uma linha" in multiline_msg.content

    def test_multi_line_preserves_first_sender(self, parser, sample_txt_multiline):
        messages = parser.parse(sample_txt_multiline)
        assert messages[0].sender == "João"
        assert messages[1].sender == "Maria"


class TestParseDeletedMessages:
    def test_parse_deleted_messages(self, parser, sample_txt_deleted):
        messages = parser.parse(sample_txt_deleted)
        assert len(messages) == 3

    def test_deleted_message_flag(self, parser, sample_txt_deleted):
        messages = parser.parse(sample_txt_deleted)
        deleted = [m for m in messages if m.is_deleted]
        assert len(deleted) == 1
        assert deleted[0].message_type == MessageType.DELETED

    def test_normal_messages_not_deleted(self, parser, sample_txt_deleted):
        messages = parser.parse(sample_txt_deleted)
        normal = [m for m in messages if not m.is_deleted]
        assert len(normal) == 2


class TestParseMediaOmitted:
    def test_parse_media_omitted(self, parser, sample_txt_media):
        messages = parser.parse(sample_txt_media)
        assert len(messages) == 4

    def test_media_type_classification(self, parser, sample_txt_media):
        messages = parser.parse(sample_txt_media)
        media_msgs = [m for m in messages if m.message_type == MessageType.MEDIA]
        assert len(media_msgs) >= 2

    def test_audio_detected(self, parser, sample_txt_media):
        messages = parser.parse(sample_txt_media)
        audio_msgs = [m for m in messages if m.message_type == MessageType.AUDIO]
        assert len(audio_msgs) >= 1

    def test_video_detected(self, parser, sample_txt_media):
        messages = parser.parse(sample_txt_media)
        video_msgs = [m for m in messages if m.message_type == MessageType.VIDEO]
        assert len(video_msgs) >= 1


class TestParseEmptyFile:
    def test_parse_empty_file(self, parser, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        messages = parser.parse(empty_file)
        assert messages == []

    def test_parse_whitespace_only_file(self, parser, tmp_path):
        ws_file = tmp_path / "whitespace.txt"
        ws_file.write_text("   \n\n   \n", encoding="utf-8")
        messages = parser.parse(ws_file)
        assert messages == []


class TestParseMalformedLines:
    def test_parse_malformed_lines(self, parser, tmp_path):
        content = """\
Linha sem formato válido
Outra linha sem timestamp
15/03/2024 10:00, João: Mensagem válida
"""
        file_path = tmp_path / "malformed.txt"
        file_path.write_text(content, encoding="utf-8")
        messages = parser.parse(file_path)
        assert len(messages) == 1
        assert messages[0].sender == "João"

    def test_parse_mixed_valid_invalid(self, parser, tmp_path):
        content = """\
Lixo
15/03/2024 10:00, João: Primeira
Lixo intermediário
15/03/2024 10:01, Maria: Segunda
Lixo no final
"""
        file_path = tmp_path / "mixed.txt"
        file_path.write_text(content, encoding="utf-8")
        messages = parser.parse(file_path)
        assert len(messages) == 2

    def test_parse_line_without_colon(self, parser, tmp_path):
        content = "15/03/2024 10:00, João Sem dois pontos"
        file_path = tmp_path / "nocolon.txt"
        file_path.write_text(content, encoding="utf-8")
        messages = parser.parse(file_path)
        assert len(messages) == 1
        assert messages[0].sender == "Desconhecido"


class TestDetectEncoding:
    def test_detect_utf8_encoding(self, parser, tmp_path):
        content = "15/03/2024 10:00, João: Mensagem com acentos: áéíóú"
        file_path = tmp_path / "utf8.txt"
        file_path.write_text(content, encoding="utf-8")
        messages = parser.parse(file_path)
        assert len(messages) == 1
        assert "áéíóú" in messages[0].content

    def test_detect_latin1_encoding(self, parser, tmp_path):
        content = "15/03/2024 10:00, João: Mensagem"
        file_path = tmp_path / "latin1.txt"
        file_path.write_bytes(content.encode("latin-1"))
        messages = parser.parse(file_path)
        assert len(messages) == 1


class TestParseLinks:
    def test_parse_links(self, parser, sample_txt_links):
        messages = parser.parse(sample_txt_links)
        assert len(messages) == 3

    def test_link_message_type(self, parser, sample_txt_links):
        messages = parser.parse(sample_txt_links)
        link_msgs = [m for m in messages if m.message_type == MessageType.LINK]
        assert len(link_msgs) >= 1

    def test_normal_message_not_link(self, parser, sample_txt_links):
        messages = parser.parse(sample_txt_links)
        text_msgs = [
            m
            for m in messages
            if m.message_type == MessageType.TEXT and not m.is_deleted
        ]
        assert len(text_msgs) >= 1


class TestParseSystemMessages:
    def test_parse_system_messages(self, parser, sample_txt_system):
        messages = parser.parse(sample_txt_system)
        assert len(messages) >= 1

    def test_system_message_type(self, parser, sample_txt_system):
        messages = parser.parse(sample_txt_system)
        system_msgs = [m for m in messages if m.message_type == MessageType.SYSTEM]
        assert len(system_msgs) >= 1


class TestValidate:
    def test_validate_valid_file(self, parser, sample_txt_content):
        assert parser.validate(sample_txt_content) is True

    def test_validate_international_file(self, parser, sample_txt_international):
        assert parser.validate(sample_txt_international) is True

    def test_validate_nonexistent_file(self, parser, tmp_path):
        assert parser.validate(tmp_path / "nonexistent.txt") is False

    def test_validate_invalid_content(self, parser, tmp_path):
        file_path = tmp_path / "invalid.txt"
        file_path.write_text("Lixo\nMais lixo\n", encoding="utf-8")
        assert parser.validate(file_path) is False


class TestParseFileNotFound:
    def test_parse_nonexistent_file(self, parser, tmp_path):
        with pytest.raises((FileNotFoundError, ParseError)):
            parser.parse(tmp_path / "nonexistent.txt")
