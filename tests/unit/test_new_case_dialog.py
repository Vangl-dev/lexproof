"""Testes do diálogo de novo caso e da identificação mínima do processo (Etapa 3.2)."""

from __future__ import annotations

import locale
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from lexproof.config.paths import Paths
from lexproof.core.session import SessionManager
from lexproof.ui.dialogs.new_case_dialog import NewCaseDialog


@pytest.fixture(scope="session")
def qapp():
    """QApplication sem poluir LC_TIME (Qt muda p/ pt_BR e quebra strptime %p)."""
    app = QApplication.instance()
    if app is None:
        prev_lc_time = locale.setlocale(locale.LC_TIME)
        app = QApplication([])
        try:
            locale.setlocale(locale.LC_TIME, prev_lc_time)
        except locale.Error:
            locale.setlocale(locale.LC_TIME, "C")
    return app


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


class TestNewCaseDialogFields:
    def test_get_data_returns_four_fields(self, qapp):
        dialog = NewCaseDialog()
        dialog.set_data(
            {
                "client_name": "ACME",
                "case_number": "PROC-1",
                "responsible_technician": "Perito Ana",
                "description": "Caso WhatsApp",
            }
        )
        data = dialog.get_data()
        assert data == {
            "client_name": "ACME",
            "case_number": "PROC-1",
            "responsible_technician": "Perito Ana",
            "description": "Caso WhatsApp",
        }

    def test_empty_fields_return_empty_strings(self, qapp):
        dialog = NewCaseDialog()
        data = dialog.get_data()
        assert data["client_name"] == ""
        assert data["case_number"] == ""
        assert data["responsible_technician"] == ""
        assert data["description"] == ""

    def test_values_are_stripped(self, qapp):
        dialog = NewCaseDialog()
        dialog.set_data(
            {
                "client_name": "  ACME  ",
                "case_number": "\tPROC-9\n",
                "responsible_technician": " Ana ",
                "description": "  desc  ",
            }
        )
        data = dialog.get_data()
        assert data["client_name"] == "ACME"
        assert data["case_number"] == "PROC-9"
        assert data["responsible_technician"] == "Ana"
        assert data["description"] == "desc"

    def test_cancel_button_rejects(self, qapp):
        dialog = NewCaseDialog()
        dialog.reject()
        assert dialog.result() == QDialog.DialogCode.Rejected

    def test_accept_returns_accepted(self, qapp):
        dialog = NewCaseDialog()
        dialog.accept()
        assert dialog.result() == QDialog.DialogCode.Accepted


class TestNewCaseFlowWithoutMainWindow:
    """Flor de criação: diálogo → start_session (sem instanciar MainWindow)."""

    def test_confirm_creates_session_with_four_fields(self, isolated_home: Path, qapp):
        dialog = NewCaseDialog()
        dialog.set_data(
            {
                "client_name": "ACME",
                "case_number": "PROC-42",
                "responsible_technician": "Perito Ana",
                "description": "Ação civil",
            }
        )
        dialog.accept()
        assert dialog.result() == QDialog.DialogCode.Accepted
        data = dialog.get_data()

        mgr = SessionManager()
        session = mgr.start_session(
            case_number=data["case_number"],
            description=data["description"],
            client_name=data["client_name"],
            responsible_technician=data["responsible_technician"],
        )
        assert session.metadata.client_name == "ACME"
        assert session.metadata.case_number == "PROC-42"
        assert session.metadata.responsible_technician == "Perito Ana"
        assert session.metadata.description == "Ação civil"
        assert mgr.session_path is not None
        assert mgr.session_path.is_file()
        assert mgr.session_path.parent == Paths.case_dir(session.session_code)

    def test_cancel_does_not_create_session(self, isolated_home: Path, qapp):
        mgr = SessionManager()
        path_before = mgr.session_path
        active_before = mgr.is_active

        dialog = NewCaseDialog()
        dialog.set_data({"client_name": "Não Salvar"})
        dialog.reject()
        assert dialog.result() == QDialog.DialogCode.Rejected
        # Cancelamento do diálogo não dispara start_session
        assert mgr.session_path == path_before
        assert mgr.is_active == active_before

    def test_four_fields_survive_save_load(self, isolated_home: Path):
        mgr = SessionManager()
        mgr.start_session(
            case_number="LOAD-1",
            description="desc load",
            client_name="Cliente Load",
            responsible_technician="Tecnico Load",
        )
        path = mgr.session_path

        fresh = SessionManager()
        loaded = fresh.load_session(path)
        assert loaded.metadata.case_number == "LOAD-1"
        assert loaded.metadata.description == "desc load"
        assert loaded.metadata.client_name == "Cliente Load"
        assert loaded.metadata.responsible_technician == "Tecnico Load"
        assert fresh.session_path == path

    def test_ui_session_gets_permanent_save_path(self, isolated_home: Path, qapp):
        dialog = NewCaseDialog()
        dialog.set_data(
            {
                "client_name": "C",
                "case_number": "P",
                "responsible_technician": "T",
                "description": "D",
            }
        )
        data = dialog.get_data()
        mgr = SessionManager()
        # mesma chamada feita por MainWindow._new_case após accept
        mgr.start_session(
            case_number=data["case_number"],
            description=data["description"],
            client_name=data["client_name"],
            responsible_technician=data["responsible_technician"],
        )
        assert mgr.session_path is not None
        assert str(mgr.session_path).endswith(".lexproof.json")
        assert Paths.cases_dir() in mgr.session_path.parents

    def test_empty_fields_stored_coherently(self, isolated_home: Path, qapp):
        dialog = NewCaseDialog()
        data = dialog.get_data()
        assert data == {
            "client_name": "",
            "case_number": "",
            "responsible_technician": "",
            "description": "",
        }

        mgr = SessionManager()
        session = mgr.start_session(
            case_number=data["case_number"],
            description=data["description"],
            client_name=data["client_name"],
            responsible_technician=data["responsible_technician"],
        )
        # coerente com implementação atual: strings vazias (não None)
        assert session.metadata.client_name == ""
        assert session.metadata.case_number == ""
        assert session.metadata.responsible_technician == ""
        assert session.metadata.description == ""
        assert mgr.session_path is not None and mgr.session_path.is_file()
