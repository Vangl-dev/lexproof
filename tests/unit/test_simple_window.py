"""Testes da janela simplificada e da identificacao de arquivos."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from lexproof.utils.intake import KIND_EXPORT, KIND_OTHER, KIND_SCREENSHOT, describe_file, intake_warnings

EXPORT = """\
12/10/2021 18:53 - As mensagens e ligações são protegidas com a criptografia de ponta a ponta.
12/10/2021 18:54 - Carlos: Oi
13/10/2021 09:00 - Ana: Tudo bem?
"""


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def files(tmp_path: Path) -> Path:
    folder = tmp_path / "entrada"
    folder.mkdir()
    with zipfile.ZipFile(folder / "Conversa do WhatsApp com Carlos.zip", "w") as zf:
        zf.writestr("Conversa do WhatsApp com Carlos.txt", EXPORT)
        zf.writestr("IMG-20211012-WA0001.jpg", b"x")
    from PIL import Image

    Image.new("RGB", (10, 20), "white").save(folder / "Screenshot_20260701144616.jpg")
    Image.new("RGB", (10, 20), "white").save(folder / "foto.jpg")
    (folder / "notas.txt").write_text("sem formato de conversa", encoding="utf-8")
    return folder


class TestIntake:
    def test_zip_export(self, files):
        info = describe_file(files / "Conversa do WhatsApp com Carlos.zip")
        assert info.kind == KIND_EXPORT
        assert info.detail == "3 mensagens, de 12/10/2021 a 13/10/2021 e 1 anexo(s)"

    def test_screenshot_with_capture_time(self, files):
        info = describe_file(files / "Screenshot_20260701144616.jpg")
        assert info.kind == KIND_SCREENSHOT
        assert info.detail == "tirado em 01/07/2026 às 14:46"
        assert not info.warnings

    def test_image_without_capture_time_warns(self, files):
        info = describe_file(files / "foto.jpg")
        assert info.warnings and "WhatsApp como foto" in info.warnings[0]

    def test_plain_text_is_other(self, files):
        assert describe_file(files / "notas.txt").kind == KIND_OTHER

    def test_prints_without_export_warn(self, files):
        infos = [describe_file(files / "Screenshot_20260701144616.jpg")]
        assert any("Sem a conversa exportada" in w for w in intake_warnings(infos))


class TestSetupPage:
    def test_folder_drop_fills_list_and_case_name(self, qapp, files, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from lexproof.ui.simple_window import SetupPage

        page = SetupPage()
        assert not page.start_button.isEnabled()
        page.add_paths([files])
        assert page.file_list.count() == 4
        assert page.case_name.text() == "Conversa com Carlos"
        assert page.start_button.isEnabled()

    def test_requires_case_name(self, qapp, files, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from lexproof.ui.simple_window import SetupPage

        page = SetupPage()
        page.add_paths([files / "Screenshot_20260701144616.jpg"])
        assert not page.start_button.isEnabled()
        assert "nome do caso" in page.missing.text()
        page.case_name.setText("Caso X")
        assert page.start_button.isEnabled()


def test_worker_creates_case_with_report(qapp, files, monkeypatch, tmp_path):
    """Fluxo completo da interface, sem rede (carimbo desabilitado no conftest)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from lexproof.ui.simple_window import PreservationWorker, recent_cases

    worker = PreservationWorker(
        [files / "Conversa do WhatsApp com Carlos.zip", files / "Screenshot_20260701144616.jpg"],
        "Caso Teste", "Ana", "Enviados pelo cliente por e-mail ou nuvem", True,
    )
    out = {}
    worker.finished_ok.connect(lambda r, d: out.update(result=r, case_dir=d))
    worker.failed.connect(lambda m: out.update(error=m))
    worker.run()

    assert "error" not in out
    case_dir = out["case_dir"]
    assert (case_dir / "preservacao" / "manifesto-sha256.txt").exists()
    assert out["result"].report_path.exists()
    assert out["result"].report_path.parent == case_dir / "relatorio"
    assert len(out["result"].messages) == 3
    cases = recent_cases()
    assert cases[0]["name"] == "Caso Teste"
    assert cases[0]["timestamped"] is False
