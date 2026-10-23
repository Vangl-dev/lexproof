"""Testes do recebimento por e-mail (DKIM) e da conferencia dos prints entre si."""

from __future__ import annotations

import base64
import subprocess
from datetime import date, datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from lexproof.acquisition.email_intake import read_email, write_dkim_archive
from lexproof.triangulation.screenshot_reader import ScreenBubble, ScreenshotReading
from lexproof.triangulation.stitcher import ScreenshotStitcher

dkim = pytest.importorskip("dkim")
TZ = ZoneInfo("America/Sao_Paulo")
SELECTOR_NAME = "sel._domainkey.cliente.com.br."


@pytest.fixture(scope="module")
def keypair() -> tuple[bytes, bytes]:
    priv = subprocess.run(["openssl", "genrsa", "2048"], capture_output=True, check=True).stdout
    pub = subprocess.run(
        ["openssl", "rsa", "-pubout", "-outform", "DER"], input=priv, capture_output=True, check=True
    ).stdout
    return priv, b"v=DKIM1; k=rsa; p=" + base64.b64encode(pub)


def _signed_email(priv: bytes, sender: str = "Maria <maria@cliente.com.br>", domain: bytes = b"cliente.com.br") -> bytes:
    m = EmailMessage()
    m["From"] = sender
    m["To"] = "adv@escritorio.com.br"
    m["Subject"] = "Prints"
    m["Date"] = format_datetime(datetime(2026, 10, 23, 12, 5, tzinfo=timezone.utc))
    m.set_content("Seguem os prints.")
    m.add_attachment(b"\x89PNG print 1", maintype="image", subtype="png", filename="Screenshot_20260701144616.png")
    m.add_attachment(b"\x89PNG print 2", maintype="image", subtype="png", filename="../../etc/passwd.png")
    raw = m.as_bytes(policy=m.policy.clone(linesep="\r\n"))
    sig = dkim.sign(raw, b"sel", domain, priv, include_headers=[b"from", b"to", b"subject", b"date"])
    return sig + raw


def _dns(record: bytes):
    def lookup(name, timeout=5):
        name = name.decode() if isinstance(name, bytes) else name
        return record if name == SELECTOR_NAME else None
    return lookup


class TestEmail:
    def test_valid_signature_and_attachments(self, tmp_path, keypair):
        priv, record = keypair
        eml = tmp_path / "cliente.eml"
        eml.write_bytes(_signed_email(priv))
        ev = read_email(eml, tmp_path / "anexos", dnsfunc=_dns(record))
        assert ev.verified
        assert ev.aligned_signature.domain == "cliente.com.br"
        assert ev.sender_domain == "cliente.com.br"
        assert ev.date == datetime(2026, 10, 23, 12, 5, tzinfo=timezone.utc)
        assert [a.path.read_bytes() for a in ev.attachments] == [b"\x89PNG print 1", b"\x89PNG print 2"]

    def test_attachment_names_cannot_escape_folder(self, tmp_path, keypair):
        priv, record = keypair
        eml = tmp_path / "cliente.eml"
        eml.write_bytes(_signed_email(priv))
        ev = read_email(eml, tmp_path / "anexos", dnsfunc=_dns(record))
        for a in ev.attachments:
            assert a.path.parent == tmp_path / "anexos"

    def test_tampered_attachment_fails(self, tmp_path, keypair):
        priv, record = keypair
        raw = _signed_email(priv).replace(b"Seguem os prints.", b"Seguem os prints!")
        eml = tmp_path / "cliente.eml"
        eml.write_bytes(raw)
        ev = read_email(eml, tmp_path / "anexos", dnsfunc=_dns(record))
        assert not ev.verified
        assert "body hash mismatch" in ev.signatures[0].error

    def test_signature_from_other_domain_is_not_aligned(self, tmp_path, keypair):
        priv, record = keypair
        eml = tmp_path / "cliente.eml"
        eml.write_bytes(_signed_email(priv, sender="Maria <maria@outro.com>"))
        ev = read_email(eml, tmp_path / "anexos", dnsfunc=_dns(record))
        assert ev.signatures[0].valid
        assert not ev.verified

    def test_unsigned_email(self, tmp_path):
        m = EmailMessage()
        m["From"] = "x@y.com"
        m.set_content("oi")
        eml = tmp_path / "semassinatura.eml"
        eml.write_bytes(m.as_bytes())
        ev = read_email(eml, tmp_path / "anexos", dnsfunc=_dns(b""))
        assert ev.signatures == []
        assert not ev.verified

    def test_dns_key_is_archived(self, tmp_path, keypair):
        priv, record = keypair
        eml = tmp_path / "cliente.eml"
        eml.write_bytes(_signed_email(priv))
        ev = read_email(eml, tmp_path / "anexos", dnsfunc=_dns(record))
        archive = write_dkim_archive([ev], tmp_path / "dkim-chaves.txt")
        text = archive.read_text()
        assert SELECTOR_NAME in text
        assert record.decode() in text


def _reading(name, bubbles, size=(1080, 2295), contact="Carlos", captured=datetime(2026, 7, 1, 14, 46, tzinfo=TZ)):
    return ScreenshotReading(path=Path(name), contact=contact, captured_at=captured, size=size, bubbles=bubbles)


def _b(text, time, day=None):
    return ScreenBubble(text=text, time=time, top=0, date=day)


D25, D28, D04 = date(2026, 3, 25), date(2026, 3, 28), date(2026, 4, 4)
LONG = "Se vc quiser comprar pão na padaria o cartão tem 14 reais"


class TestStitcher:
    def test_overlapping_prints_are_continuous(self):
        a = _reading("a.jpg", [_b("Acorda o Beto", "10:13", date(2026, 3, 20)), _b(LONG, "08:39", D25)])
        # segundo print comeca com o mesmo balao cortado na borda, sem separador de data
        b = _reading("b.jpg", [_b("padaria o cartão tem 14 reais", "08:39"), _b("Carlos não abre a porta", "09:17", D28)])
        res = ScreenshotStitcher().stitch([b, a])
        assert [r.path.name for r in res.order] == ["a.jpg", "b.jpg"]
        assert res.gaps == [] and res.contradictions == []
        assert len(res.messages) == 3
        merged = next(m for m in res.messages if m.time == "08:39")
        assert merged.text == LONG and merged.date == D25
        assert merged.sources == ["a.jpg", "b.jpg"]
        assert res.all_ok

    def test_gap_between_prints(self):
        a = _reading("a.jpg", [_b("Papai chegou?", "10:34", D04)])
        b = _reading("b.jpg", [_b("Tô saindo da igreja", "12:09", date(2026, 6, 20))])
        res = ScreenshotStitcher().stitch([a, b])
        assert len(res.gaps) == 1
        assert res.gaps[0].last_before.text == "Papai chegou?"
        assert not res.all_ok

    def test_changed_number_in_cut_bubble_is_contradiction(self):
        a = _reading("a.jpg", [_b(LONG, "08:39", D25)])
        b = _reading("b.jpg", [_b("padaria o cartão tem 40 reais", "08:39"), _b("Carlos não abre a porta", "09:17", D28)])
        res = ScreenshotStitcher().stitch([a, b])
        assert len(res.contradictions) == 1
        assert res.contradictions[0].differences == [("14", "40")]
        assert res.gaps == []

    def test_short_repeated_texts_do_not_link_prints(self):
        # "Te amo" em horarios diferentes nao e a mesma mensagem
        a = _reading("a.jpg", [_b("Te amo", "10:00", D25)])
        b = _reading("b.jpg", [_b("Te amo", "11:00", D28)])
        res = ScreenshotStitcher().stitch([a, b])
        assert len(res.messages) == 2
        assert len(res.gaps) == 1

    def test_different_contact_and_size_are_flagged(self):
        a = _reading("a.jpg", [_b("Papai chegou?", "10:34", D04)])
        b = _reading("b.jpg", [_b("Papai chegou?", "10:34", D04)], contact="Pedro")
        c = _reading("c.jpg", [_b("Papai chegou?", "10:34", D04)], size=(720, 1600))
        res = ScreenshotStitcher().stitch([a, b, c])
        messages = " | ".join(i.message for i in res.issues)
        assert "Contato diferente" in messages and "Pedro" in messages
        assert "Tamanho de tela diferente" in messages

    def test_print_taken_before_messages_is_flagged(self):
        a = _reading("a.jpg", [_b("Papai chegou?", "10:34", D04)], captured=datetime(2026, 4, 1, 9, 0, tzinfo=TZ))
        res = ScreenshotStitcher().stitch([a])
        assert any("antes da mensagem" in i.message for i in res.issues)

    def test_status_clock_mismatch_is_flagged(self):
        a = _reading("a.jpg", [_b("Papai chegou?", "10:34", D04)])
        a.status_clock = "09:12"
        res = ScreenshotStitcher().stitch([a])
        assert any("Relógio do celular" in i.message for i in res.issues)
