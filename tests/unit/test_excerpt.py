"""Testes do recorte da conversa ao periodo de interesse."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import zipfile
from datetime import date
from pathlib import Path

import pytest

from lexproof.acquisition.excerpt import discard_outside, make_excerpt, write_excerpt_record
from lexproof.parsers.whatsapp_parser import WhatsAppParser
from lexproof.pipeline.preservation import PreservationPipeline
from lexproof.triangulation.stitcher import ScreenshotStitcher, StitchResult, Gap, StitchedMessage

EXPORT = """\
10/01/2026 09:00 - As mensagens e ligações são protegidas com a criptografia de ponta a ponta.
10/01/2026 09:01 - Ana: Bom dia
15/02/2026 10:00 - Ana: Primeira do período
continuação em outra linha
15/02/2026 10:05 - João: ‎foto.jpg (arquivo anexado)
20/03/2026 11:00 - João: Última do período

25/04/2026 12:00 - Ana: Fora do período
"""


@pytest.fixture
def export(tmp_path: Path) -> Path:
    folder = tmp_path / "extraido"
    folder.mkdir()
    txt = folder / "Conversa do WhatsApp com João.txt"
    txt.write_text(EXPORT, encoding="utf-8")
    (folder / "foto.jpg").write_bytes(b"jpg")
    (folder / "antiga.jpg").write_bytes(b"old")
    return txt


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestMakeExcerpt:
    def test_contiguous_block_with_continuation(self, export, tmp_path):
        msgs = WhatsAppParser().parse(export)
        r = make_excerpt(export, msgs, date(2026, 2, 1), date(2026, 3, 31), tmp_path / "recorte")
        assert (r.first_line, r.last_line) == (3, 6)
        assert r.kept_messages == 3 and r.total_messages == 6
        text = r.excerpt_path.read_text(encoding="utf-8")
        assert text.startswith("15/02/2026 10:00 - Ana: Primeira do período\ncontinuação")
        assert "Fora do período" not in text and "Bom dia" not in text
        assert [a.name for a in r.kept_attachments] == ["foto.jpg"]

    @pytest.mark.skipif(shutil.which("sed") is None, reason="sed ausente")
    def test_matches_sed_command(self, export, tmp_path):
        msgs = WhatsAppParser().parse(export)
        r = make_excerpt(export, msgs, date(2026, 2, 1), date(2026, 3, 31), tmp_path / "recorte")
        out = subprocess.run(
            ["sed", "-n", f"{r.first_line},{r.last_line}p", str(export)], capture_output=True, check=True
        ).stdout
        assert hashlib.sha256(out).hexdigest() == r.excerpt_sha256

    @pytest.mark.skipif(shutil.which("sed") is None, reason="sed ausente")
    def test_matches_sed_when_file_has_no_final_newline(self, export, tmp_path):
        export.write_bytes(export.read_bytes().rstrip(b"\n"))
        msgs = WhatsAppParser().parse(export)
        r = make_excerpt(export, msgs, date(2026, 4, 1), date(2026, 4, 30), tmp_path / "recorte")
        out = subprocess.run(
            ["sed", "-n", f"{r.first_line},{r.last_line}p", str(export)], capture_output=True, check=True
        ).stdout
        assert hashlib.sha256(out).hexdigest() == r.excerpt_sha256

    def test_empty_period_is_an_error(self, export, tmp_path):
        msgs = WhatsAppParser().parse(export)
        with pytest.raises(ValueError):
            make_excerpt(export, msgs, date(2025, 1, 1), date(2025, 12, 31), tmp_path / "recorte")

    def test_discard_keeps_attachments_of_period(self, export, tmp_path):
        msgs = WhatsAppParser().parse(export)
        r = make_excerpt(export, msgs, date(2026, 2, 1), date(2026, 3, 31), tmp_path / "recorte")
        folder = export.parent
        discard_outside(r, [export, folder / "foto.jpg", folder / "antiga.jpg"])
        assert not export.exists() and not (folder / "antiga.jpg").exists()
        assert (folder / "foto.jpg").exists()
        assert sorted(r.removed_files) == ["Conversa do WhatsApp com João.txt", "antiga.jpg"]
        record = write_excerpt_record(r, tmp_path / "recorte.txt").read_text()
        assert "DESCARTADO" in record and r.source_txt_sha256 in record


def _case_with_zip(tmp_path: Path) -> tuple[Path, list[Path]]:
    case = tmp_path / "caso"
    orig = case / "evidence" / "original"
    orig.mkdir(parents=True)
    zpath = orig / "Conversa do WhatsApp com João.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("Conversa do WhatsApp com João.txt", EXPORT)
        zf.writestr("foto.jpg", b"jpg")
    return case, [zpath]


class TestPipelinePeriod:
    def test_keep_full_copy_sealed(self, tmp_path):
        case, files = _case_with_zip(tmp_path)
        r = PreservationPipeline().execute(
            files, case_dir=case, output_dir=case / "relatorio", timestamp=False,
            period=(date(2026, 2, 1), date(2026, 3, 31)),
        )
        assert r.excerpt is not None and not r.excerpt.discarded
        assert len(r.messages) == 3
        assert files[0].exists()
        manifest = (case / "preservacao" / "manifesto-sha256.txt").read_text()
        assert "evidence/original/Conversa do WhatsApp com João.zip" in manifest
        assert "recorte" in manifest and "preservacao/recorte.txt" in manifest

    def test_discard_removes_full_copy_but_keeps_hash(self, tmp_path):
        case, files = _case_with_zip(tmp_path)
        zip_hash = _sha(files[0])
        r = PreservationPipeline().execute(
            files, case_dir=case, output_dir=case / "relatorio", timestamp=False,
            period=(date(2026, 2, 1), date(2026, 3, 31)), discard_outside_period=True,
        )
        assert r.excerpt.discarded
        assert not files[0].exists()
        remaining = {p.name for p in (case / "evidence").rglob("*") if p.is_file()}
        assert "Conversa do WhatsApp com João.txt" not in remaining
        assert "foto.jpg" in remaining  # anexo citado no periodo
        manifest = (case / "preservacao" / "manifesto-sha256.txt").read_text()
        assert ".zip" not in manifest  # sha256sum -c nao pode apontar arquivo apagado
        assert zip_hash in (case / "preservacao" / "recorte.txt").read_text()
        if shutil.which("pdftotext"):
            text = subprocess.run(
                ["pdftotext", str(r.report_path), "-"], capture_output=True, text=True, check=True
            ).stdout
            assert "Primeira do período" in text  # controle: o PDF e legivel
            assert "Fora do período" not in text and "Bom dia" not in text


def test_gaps_are_neutral_when_export_confirms_prints():
    m = StitchedMessage("a", date(2026, 1, 1), "10:00", "text", ["x.jpg"])
    st = StitchResult(order=[object()], messages=[m], gaps=[Gap("x.jpg", "y.jpg", m, m)])
    assert st.needs_attention(with_export=False)
    assert not st.needs_attention(with_export=True)
    assert ScreenshotStitcher  # importado para o teste de integracao do modulo
