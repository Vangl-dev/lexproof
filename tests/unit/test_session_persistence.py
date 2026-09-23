"""Testes da infraestrutura de paths e persistência confiável de sessão (Etapa 3.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lexproof.config.paths import Paths
from lexproof.core.constants import SESSION_FILE_EXTENSION
from lexproof.core.session import SessionManager


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redireciona Path.home() para tmp_path (não toca ~/.lexproof real)."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


class TestPathsCases:
    def test_config_dir_under_home(self, isolated_home: Path):
        assert Paths.config_dir() == isolated_home / ".lexproof"
        assert Paths.config_dir().is_dir()

    def test_cases_dir_created(self, isolated_home: Path):
        cases = Paths.cases_dir()
        assert cases == isolated_home / ".lexproof" / "cases"
        assert cases.is_dir()

    def test_case_dir_created_and_sanitized(self, isolated_home: Path):
        case_dir = Paths.case_dir("LEX-Ab12Cd34")
        assert case_dir == Paths.cases_dir() / "LEX-Ab12Cd34"
        assert case_dir.is_dir()

        weird = Paths.case_dir("a/b\\c")
        assert weird == Paths.cases_dir() / "a_b_c"
        assert weird.is_dir()

    def test_case_dir_rejects_empty(self, isolated_home: Path):
        with pytest.raises(ValueError):
            Paths.case_dir("  ")

    def test_session_file_path_layout(self, isolated_home: Path):
        p = Paths.session_file_path("LEX-Test01")
        assert p == (
            isolated_home / ".lexproof" / "cases" / "LEX-Test01" / f"case{SESSION_FILE_EXTENSION}"
        )
        assert p.name.endswith(".lexproof.json")
        assert p.parent.is_dir()

    def test_single_root_no_parallel_tree(self, isolated_home: Path):
        Paths.cases_dir()
        Paths.session_file_path("LEX-X")
        assert not (isolated_home / "lexproof").exists()
        assert (isolated_home / ".lexproof" / "cases").is_dir()


class TestSessionSavePath:
    def test_start_session_sets_default_permanent_path(self, isolated_home: Path):
        mgr = SessionManager()
        session = mgr.start_session(description="Caso 3.1")
        assert mgr.session_path is not None
        assert mgr.session_path.name == f"case{SESSION_FILE_EXTENSION}"
        assert mgr.session_path.parent == Paths.case_dir(session.session_code)
        assert mgr.session_path.is_file()

    def test_start_session_with_explicit_save_path(self, tmp_path: Path):
        explicit = tmp_path / "meu_caso" / "sessao"
        mgr = SessionManager()
        mgr.start_session(save_path=explicit)
        expected = explicit.with_suffix(SESSION_FILE_EXTENSION)
        assert mgr.session_path == expected
        assert expected.is_file()

    def test_initial_save_creates_file(self, isolated_home: Path):
        mgr = SessionManager()
        mgr.start_session(description="inicial")
        path = mgr.session_path
        assert path is not None and path.exists()
        assert path.read_text(encoding="utf-8")

    def test_subsequent_save_same_path_no_duplicate_extension(self, isolated_home: Path):
        mgr = SessionManager()
        mgr.start_session(description="v1")
        path1 = mgr.session_path
        saved = mgr.save_session()
        assert saved == path1
        assert saved.name.count("lexproof") == 1
        assert saved.name == f"case{SESSION_FILE_EXTENSION}"

        mgr.session.metadata.description = "v2"
        saved2 = mgr.save_session()
        assert saved2 == path1
        assert saved2.name.endswith(SESSION_FILE_EXTENSION)
        assert not saved2.name.endswith(".lexproof.lexproof.json")
        assert path1.is_file()

    def test_suffix_not_duplicated_when_called_many_times(self, isolated_home: Path):
        mgr = SessionManager()
        mgr.start_session()
        for _ in range(5):
            mgr.save_session()
        assert mgr.session_path.name == f"case{SESSION_FILE_EXTENSION}"
        assert mgr.session_path.parent.is_dir()


class TestSessionLoadRoundTrip:
    def test_load_keeps_same_path(self, isolated_home: Path):
        mgr = SessionManager()
        original = mgr.start_session(
            description="round-trip",
            client_name="Cliente X",
            case_number="PROC-1",
            responsible_technician="Perito Y",
        )
        path = mgr.session_path
        assert path is not None

        mgr2 = SessionManager()
        loaded = mgr2.load_session(path)
        assert mgr2.session_path == path
        assert loaded.session_code == original.session_code
        assert loaded.metadata.client_name == "Cliente X"
        assert loaded.metadata.case_number == "PROC-1"
        assert loaded.metadata.responsible_technician == "Perito Y"
        assert loaded.metadata.description == "round-trip"

    def test_save_after_load_no_duplicate_extension(self, isolated_home: Path):
        mgr = SessionManager()
        mgr.start_session(description="antes")
        path = mgr.session_path

        mgr2 = SessionManager()
        mgr2.load_session(path)
        after = mgr2.save_session()
        assert after == path
        assert after.name == f"case{SESSION_FILE_EXTENSION}"
        assert "lexproof.lexproof" not in after.name

    def test_normalize_path_adds_extension_once(self, tmp_path: Path):
        raw = tmp_path / "caso"
        normalized = SessionManager._normalize_session_path(raw)
        assert normalized.name == f"case{SESSION_FILE_EXTENSION}".replace(
            "case", "caso"
        ) or normalized.name.endswith(SESSION_FILE_EXTENSION)
        again = SessionManager._normalize_session_path(normalized)
        assert again == normalized
        thrice = SessionManager._normalize_session_path(again)
        assert thrice == normalized

    def test_survives_process_end_close_session(self, isolated_home: Path):
        mgr = SessionManager()
        mgr.start_session(description="sobrevive")
        path = mgr.session_path
        mgr.session.metadata.description = "atualizado antes de fechar"
        mgr.close_session()
        assert path is not None and path.is_file()

        mgr2 = SessionManager()
        mgr2.load_session(path)
        assert mgr2.session.metadata.description == "atualizado antes de fechar"
        assert mgr2.session_path == path

    def test_full_round_trip_fields(self, isolated_home: Path):
        mgr = SessionManager()
        mgr.start_session(
            case_number="C-99",
            description="desc",
            client_name="ACME",
            responsible_technician="Ana",
        )
        path = mgr.session_path

        fresh = SessionManager()
        s = fresh.load_session(path)
        assert s.metadata.case_number == "C-99"
        assert s.metadata.client_name == "ACME"
        assert s.metadata.responsible_technician == "Ana"
        assert s.metadata.description == "desc"
        assert fresh.is_active
