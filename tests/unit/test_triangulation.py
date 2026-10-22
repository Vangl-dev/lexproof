"""Testes da leitura de exportacoes atuais, do selo e da conferencia dos prints."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from lexproof.blockchain.rfc3161 import RFC3161Anchor, _parse_openssl_time, default_anchors
from lexproof.crypto.seal import MANIFEST_NAME, seal_case
from lexproof.models.message import MessageType
from lexproof.parsers.whatsapp_parser import WhatsAppParser
from lexproof.pipeline.preservation import PreservationPipeline
from lexproof.reports.pdf_report import _safe
from lexproof.triangulation.matcher import (
    CheckStatus,
    ScreenshotMatcher,
    export_contact_name,
    text_differences,
)
from lexproof.triangulation.screenshot_reader import (
    ScreenBubble,
    ScreenshotReading,
    capture_time_from_file,
    is_date_label,
    resolve_date_label,
)

TZ = ZoneInfo("America/Sao_Paulo")

# Formato da exportacao atual do WhatsApp (Android, pt-BR)
CURRENT_EXPORT = """\
12/10/2021 18:53 - As mensagens e ligações são protegidas com a criptografia de ponta a ponta. Somente as pessoas que fazem parte da conversa podem ler, ouvir e compartilhar esse conteúdo. *Saiba mais*
14/03/2026 12:30 - Carlos: tá demorando?
14/03/2026 13:15 - Ana: <Mídia oculta>
16/03/2026 10:44 - Carlos: tá demorando?
20/03/2026 10:13 - Ana: Acorda o Beto pra gente ir no médico
25/03/2026 08:39 - Ana: Se vc quiser comprar pão na padaria o cartão tem 14 reais
25/03/2026 08:40 - Ana: Não esquece o troco
28/03/2026 09:17 - Ana: Carlos não abre a porta pra ninguém tá <Mensagem editada>
04/04/2026 10:58 - Ana:
06/06/2026 18:48 - Ana: Mensagem apagada
07/06/2026 10:00 - Seu código de segurança com Carlos mudou. Toque para saber mais.
"""


@pytest.fixture
def export_file(tmp_path: Path) -> Path:
    path = tmp_path / "Conversa do WhatsApp com Carlos.txt"
    path.write_text(CURRENT_EXPORT, encoding="utf-8")
    return path


@pytest.fixture
def messages(export_file: Path):
    return WhatsAppParser().parse(export_file)


def _reading(bubbles, contact="Carlos", captured=datetime(2026, 7, 1, 14, 46, tzinfo=TZ)):
    return ScreenshotReading(
        path=Path("Screenshot_20260701144616.jpg"),
        contact=contact,
        captured_at=captured,
        bubbles=bubbles,
    )


def _b(text, time, day=None, kind="text"):
    return ScreenBubble(text=text, time=time, top=0, kind=kind, date=day)


class TestCurrentExportFormat:
    def test_detected_as_whatsapp_export(self, export_file):
        assert PreservationPipeline()._is_whatsapp_export(export_file)

    def test_times_are_local_not_utc(self, messages):
        ts = messages[1].timestamp
        assert ts.utcoffset() == timedelta(hours=-3)
        assert (ts.hour, ts.minute) == (12, 30)

    def test_hidden_media(self, messages):
        assert messages[2].message_type == MessageType.MEDIA

    def test_deleted_without_brackets(self, messages):
        deleted = [m for m in messages if m.is_deleted]
        assert len(deleted) == 1
        assert deleted[0].content == "Mensagem apagada"

    def test_edited_marker(self, messages):
        edited = [m for m in messages if m.is_edited]
        assert len(edited) == 1
        assert edited[0].content.startswith("Carlos não abre")

    def test_system_lines(self, messages):
        system = [m for m in messages if m.message_type == MessageType.SYSTEM]
        assert len(system) == 2

    def test_contact_from_file_name(self, export_file):
        assert export_contact_name(export_file) == "Carlos"


class TestDateLabels:
    captured = date(2026, 7, 1)  # quarta-feira

    def test_full_date(self):
        assert resolve_date_label("16 de março de 2026", None) == date(2026, 3, 16)

    def test_date_without_year_uses_capture_year(self):
        assert resolve_date_label("20 de junho", self.captured) == date(2026, 6, 20)

    def test_date_without_year_in_future_is_last_year(self):
        assert resolve_date_label("20 de dezembro", self.captured) == date(2025, 12, 20)

    def test_relative_labels(self):
        assert resolve_date_label("Hoje", self.captured) == self.captured
        assert resolve_date_label("Ontem", self.captured) == date(2026, 6, 30)

    def test_weekday_is_most_recent_past_day(self):
        assert resolve_date_label("Segunda-feira", self.captured) == date(2026, 6, 29)
        assert resolve_date_label("Quarta-feira", self.captured) == date(2026, 6, 24)
        assert resolve_date_label("Sábado", self.captured) == date(2026, 6, 27)

    def test_relative_label_without_capture_date(self):
        assert resolve_date_label("Ontem", None) is None

    def test_is_date_label(self):
        assert is_date_label("4 de abril de 2026")
        assert is_date_label("Segunda-feira")
        assert not is_date_label("Papai chegou?")

    def test_capture_time_from_file_name(self, tmp_path):
        path = tmp_path / "Screenshot_20260701144616.jpg"
        path.write_bytes(b"")
        captured, source = capture_time_from_file(path, TZ)
        assert captured == datetime(2026, 7, 1, 14, 46, 16, tzinfo=TZ)
        assert source == "nome do arquivo"


class TestMatcher:
    def test_all_bubbles_confirmed(self, messages, export_file):
        reading = _reading([
            _b("tá demorando?", "10:44", date(2026, 3, 16)),
            _b("Acorda o Beto pra gente ir no médico", "10:13", date(2026, 3, 20)),
        ])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert [c.status for c in check.checks] == [CheckStatus.CONFERE, CheckStatus.CONFERE]
        assert check.contact_matches is True
        assert check.captured_after_messages is True
        assert check.hidden_messages == []
        assert check.all_ok

    def test_call_matches_empty_export_line(self, messages, export_file):
        reading = _reading([_b("Ligação de voz", None, date(2026, 4, 4), kind="call")])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.CONFERE_SEM_HORARIO
        assert check.checks[0].message.timestamp.hour == 10

    def test_changed_number_is_flagged(self, messages, export_file):
        reading = _reading([
            _b("Se vc quiser comprar pão na padaria o cartão tem 40 reais", "08:39", date(2026, 3, 25)),
        ])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.TEXTO_DIVERGENTE
        assert any('"40"' in n and '"14"' in n for n in check.checks[0].notes)
        assert not check.all_ok

    def test_changed_time_is_flagged(self, messages, export_file):
        reading = _reading([_b("Acorda o Beto pra gente ir no médico", "11:13", date(2026, 3, 20))])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.HORARIO_DIVERGENTE

    def test_wrong_date_is_flagged(self, messages, export_file):
        reading = _reading([_b("Acorda o Beto pra gente ir no médico", "10:13", date(2026, 3, 21))])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.DATA_DIVERGENTE

    def test_invented_message_not_found(self, messages, export_file):
        reading = _reading([_b("Vou te pagar amanhã sem falta", "10:00", date(2026, 3, 20))])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.NAO_ENCONTRADA

    def test_message_hidden_from_print(self, messages, export_file):
        # "Nao esquece o troco" (08:40) foi omitida entre duas mensagens exibidas
        reading = _reading([
            _b("Se vc quiser comprar pão na padaria o cartão tem 14 reais", "08:39", date(2026, 3, 25)),
            _b("Carlos não abre a porta pra ninguém tá", "09:17", date(2026, 3, 28)),
        ])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert [m.content for m in check.hidden_messages] == ["Não esquece o troco"]
        assert not check.all_ok

    def test_edited_message_is_noted(self, messages, export_file):
        reading = _reading([_b("Carlos não abre a porta pra ninguém tá", "09:17", date(2026, 3, 28))])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.CONFERE
        assert any("editada" in n for n in check.checks[0].notes)

    def test_repeated_text_disambiguated_by_time(self, messages, export_file):
        reading = _reading([_b("tá demorando?", "12:30")])  # sem separador de data
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.CONFERE
        assert check.checks[0].message.timestamp.day == 14

    def test_other_contact_is_flagged(self, messages, export_file):
        reading = _reading([_b("tá demorando?", "10:44", date(2026, 3, 16))], contact="Pedro")
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.contact_matches is False
        assert not check.all_ok

    def test_print_older_than_messages_is_flagged(self, messages, export_file):
        reading = _reading(
            [_b("tá demorando?", "10:44", date(2026, 3, 16))],
            captured=datetime(2026, 3, 1, 9, 0, tzinfo=TZ),
        )
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.captured_after_messages is False

    def test_order_swapped_is_flagged(self, messages, export_file):
        reading = _reading([
            _b("Acorda o Beto pra gente ir no médico", "10:13", date(2026, 3, 20)),
            _b("tá demorando?", "10:44", date(2026, 3, 16)),
        ])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.order_ok is False

    def test_text_differences_ignore_accents_and_punctuation(self):
        assert text_differences("Tô saindo da igreja!", "To saindo da igreja") == []
        assert text_differences("tem 40 reais", "tem 14 reais") == [("40", "14")]


class TestSeal:
    def _originals(self, case_dir: Path) -> list[Path]:
        orig = case_dir / "evidence" / "original"
        orig.mkdir(parents=True)
        files = []
        for name, data in [("a.zip", b"zip"), ("print.jpg", b"jpg")]:
            (orig / name).write_bytes(data)
            files.append(orig / name)
        return files

    def test_manifest_in_sha256sum_format(self, tmp_path):
        files = self._originals(tmp_path)
        result = seal_case(tmp_path, files)
        lines = result.manifest_path.read_text().splitlines()
        assert lines[0].endswith("  evidence/original/a.zip")
        assert len(lines[0].split("  ")[0]) == 64
        assert not result.timestamped
        text = (result.seal_dir / "COMO_VERIFICAR.txt").read_text()
        assert f"sha256sum -c preservacao/{MANIFEST_NAME}" in text
        assert "Nao foi obtido" in text

    def test_tsa_failure_is_recorded_not_raised(self, tmp_path):
        files = self._originals(tmp_path)
        result = seal_case(tmp_path, files, anchors=default_anchors(), retry_delay=0)
        assert result.timestamp is None
        assert result.timestamp_error.count("TSA desabilitada") == 3
        assert "digicert" in result.timestamp_error

    def test_openssl_time_independent_of_locale(self):
        dt = _parse_openssl_time("Oct 22 18:42:16.123 2026 GMT")
        assert (dt.year, dt.month, dt.day, dt.hour) == (2026, 10, 22, 18)


@pytest.mark.network
@pytest.mark.skipif(
    not os.environ.get("LEXPROOF_NETWORK_TESTS"),
    reason="defina LEXPROOF_NETWORK_TESTS=1 para chamar a FreeTSA",
)
def test_real_timestamp_detects_tampering(tmp_path):
    anchor = RFC3161Anchor()
    if not anchor.is_available():
        pytest.skip("openssl ausente")
    files = TestSeal()._originals(tmp_path)
    result = seal_case(tmp_path, files, anchors=anchor)
    assert result.timestamped
    assert "freetsa_cacert.pem" in result.verify_command
    assert anchor.verify_file(result.manifest_path, result.timestamp.tsr_path)
    result.manifest_path.write_text(result.manifest_path.read_text() + "x")
    assert not anchor.verify_file(result.manifest_path, result.timestamp.tsr_path)


def test_safe_text_for_pdf():
    assert _safe("⚜️ 𝓜𝓪𝓻𝓲𝓪 𝓢  ⚜️") == "[emoji] Maria S [emoji]"
    assert _safe("Mamãe vai chegar") == "Mamãe vai chegar"
