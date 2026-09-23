"""Testes da evidência permanente (Etapa 3.3) — Alternativa A."""

from __future__ import annotations

import hashlib
import locale
import zipfile
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog

from lexproof.config.paths import Paths
from lexproof.core.session import SessionManager
from lexproof.pipeline.preservation import PreservationPipeline


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


@pytest.fixture
def user_dir(tmp_path: Path) -> Path:
    d = tmp_path / "user_downloads"
    d.mkdir()
    return d


@pytest.fixture
def sample_file(user_dir: Path) -> Path:
    p = user_dir / "prova.txt"
    p.write_text("conteudo da prova", encoding="utf-8")
    return p


@pytest.fixture
def sample_zip(user_dir: Path) -> Path:
    zpath = user_dir / "conversa.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("conversa/export.txt", "15/03/2024 10:00, Joao: Oi\n")
        zf.writestr("conversa/nota.txt", "nota interna\n")
    return zpath


@pytest.fixture
def mgr(isolated_home: Path) -> SessionManager:
    m = SessionManager()
    m.start_session(description="caso 3.3")
    return m


class TestEvidencePathsHelpers:
    def test_evidence_dir_layout(self, isolated_home: Path):
        d = Paths.evidence_dir("LEX-Ab12Cd34")
        assert d == isolated_home / ".lexproof" / "cases" / "LEX-Ab12Cd34" / "evidence"
        assert d.is_dir()

    def test_evidence_original_dir(self, isolated_home: Path):
        d = Paths.evidence_original_dir("LEX-Ab12Cd34")
        assert d == Paths.evidence_dir("LEX-Ab12Cd34") / "original"
        assert d.is_dir()

    def test_evidence_extracted_dir(self, isolated_home: Path):
        d = Paths.evidence_extracted_dir("LEX-Ab12Cd34")
        assert d == Paths.evidence_dir("LEX-Ab12Cd34") / "extracted"
        assert d.is_dir()

    def test_single_tree_under_case(self, isolated_home: Path):
        Paths.evidence_original_dir("X")
        Paths.evidence_extracted_dir("X")
        case = Paths.case_dir("X")
        assert (case / "evidence" / "original").is_dir()
        assert (case / "evidence" / "extracted").is_dir()
        assert not (isolated_home / "lexproof_evidence").exists()


class TestPermanentCopyCommonFile:
    def test_copies_to_evidence_original(self, mgr: SessionManager, sample_file: Path):
        ev = mgr.add_evidence(sample_file)
        original_dir = Paths.evidence_original_dir(mgr.session.session_code)
        assert ev.file_path.parent == original_dir
        assert ev.file_path.is_file()
        assert ev.file_path.name == "prova.txt"

    def test_file_path_is_permanent_not_user_location(
        self, mgr: SessionManager, sample_file: Path
    ):
        ev = mgr.add_evidence(sample_file)
        assert ev.file_path != sample_file
        assert ".lexproof" in str(ev.file_path)
        assert str(sample_file.parent) not in str(ev.file_path)

    def test_hash_matches_copy(self, mgr: SessionManager, sample_file: Path):
        ev = mgr.add_evidence(sample_file)
        actual = hashlib.sha256(ev.file_path.read_bytes()).hexdigest()
        assert ev.sha256 == actual
        original_hash = hashlib.sha256(sample_file.read_bytes()).hexdigest()
        assert actual == original_hash

    def test_user_original_not_modified(
        self, mgr: SessionManager, sample_file: Path
    ):
        before = sample_file.read_bytes()
        before_stat = sample_file.stat().st_mtime_ns
        mgr.add_evidence(sample_file)
        assert sample_file.read_bytes() == before
        assert sample_file.stat().st_mtime_ns == before_stat
        assert sample_file.exists()

    def test_name_collision_deterministic(
        self, mgr: SessionManager, user_dir: Path
    ):
        a = user_dir / "conversa.zip"
        a.write_bytes(b"zip-a")
        other = user_dir / "sub"
        other.mkdir()
        b = other / "conversa.zip"
        b.write_bytes(b"zip-b")

        ev1 = mgr.add_evidence(a)
        ev2 = mgr.add_evidence(b)
        assert ev1.file_path.name == "conversa.zip"
        assert ev2.file_path.name == "conversa (1).zip"
        assert ev1.file_path != ev2.file_path
        assert ev1.file_path.is_file() and ev2.file_path.is_file()

    def test_no_overwrite_existing(
        self, mgr: SessionManager, sample_file: Path
    ):
        ev1 = mgr.add_evidence(sample_file)
        # reimporta o MESMO arquivo de origem: segunda cópia em (1)
        ev2 = mgr.add_evidence(sample_file)
        # conteúdo idêntico; nomes podem ser prova.txt e prova (1).txt
        assert ev1.file_path.is_file()
        assert ev2.file_path.is_file()
        assert ev1.file_path != ev2.file_path

    def test_session_saves_with_permanent_path(
        self, mgr: SessionManager, sample_file: Path
    ):
        ev = mgr.add_evidence(sample_file)
        path = mgr.session_path
        assert path is not None and path.is_file()
        fresh = SessionManager()
        loaded = fresh.load_session(path)
        assert len(loaded.evidence_files) == 1
        loaded_ev = loaded.evidence_files[0]
        assert Path(str(loaded_ev.file_path)) == ev.file_path
        assert Path(str(loaded_ev.file_path)).is_file()

    def test_session_loadable_after_import(
        self, mgr: SessionManager, sample_file: Path
    ):
        mgr.add_evidence(sample_file)
        path = mgr.session_path
        fresh = SessionManager()
        s = fresh.load_session(path)
        assert s.evidence_files[0].file_path.exists()


class TestZipPermanentFlow:
    def test_zip_copied_to_original(self, mgr: SessionManager, sample_zip: Path):
        ev = mgr.add_evidence(sample_zip)
        original_dir = Paths.evidence_original_dir(mgr.session.session_code)
        assert ev.file_path.parent == original_dir
        assert ev.file_path.name == "conversa.zip"
        assert sample_zip.exists()

    def test_pipeline_extracts_to_permanent_extracted(
        self, mgr: SessionManager, sample_zip: Path
    ):
        ev = mgr.add_evidence(sample_zip)
        session_code = mgr.session.session_code
        case_dir = Paths.case_dir(session_code)

        pipeline = PreservationPipeline()
        result = pipeline.execute(
            [ev.file_path],
            case_dir=case_dir,
            session_code=session_code,
            output_dir=case_dir / "reports",
        )

        extracted_root = Paths.evidence_extracted_dir(session_code)
        assert extracted_root.is_dir()
        # membros extraídos sob extracted/<stem>/
        member_paths = [e.file_path for e in result.evidence_files]
        assert member_paths
        for p in member_paths:
            assert str(p).startswith(str(extracted_root))
            assert "lexproof_zip_" not in str(p)
            assert Path(p).is_file()

    def test_no_lexproof_zip_tmp_for_flow(
        self, mgr: SessionManager, sample_zip: Path, monkeypatch: pytest.MonkeyPatch
    ):
        import tempfile

        created: list[str] = []
        real_mkdtemp = tempfile.mkdtemp

        def spy(*args, **kwargs):
            p = real_mkdtemp(*args, **kwargs)
            created.append(p)
            return p

        monkeypatch.setattr(tempfile, "mkdtemp", spy)

        ev = mgr.add_evidence(sample_zip)
        session_code = mgr.session.session_code
        case_dir = Paths.case_dir(session_code)
        pipeline = PreservationPipeline()
        result = pipeline.execute(
            [ev.file_path],
            case_dir=case_dir,
            session_code=session_code,
        )
        assert result.evidence_files
        for p in created:
            assert "lexproof_zip_" not in p

    def test_zip_fallback_uses_permanent_copy(
        self, mgr: SessionManager, sample_zip: Path, monkeypatch: pytest.MonkeyPatch
    ):
        from lexproof.parsers import archive_parser

        def boom(self, file_path):
            raise RuntimeError("extracao forçada")

        monkeypatch.setattr(archive_parser.ArchiveParser, "extract", boom)

        ev = mgr.add_evidence(sample_zip)
        session_code = mgr.session.session_code
        case_dir = Paths.case_dir(session_code)

        pipeline = PreservationPipeline()
        result = pipeline.execute(
            [ev.file_path],
            case_dir=case_dir,
            session_code=session_code,
        )

        assert len(result.evidence_files) == 1
        fb = result.evidence_files[0]
        original_dir = Paths.evidence_original_dir(session_code)
        assert Path(fb.file_path).parent == original_dir
        assert Path(fb.file_path).is_file()
        assert sample_zip.exists()

    def test_fallback_copies_user_zip_if_not_permanent(
        self, mgr: SessionManager, sample_zip: Path, monkeypatch: pytest.MonkeyPatch
    ):
        from lexproof.parsers import archive_parser

        def boom(self, file_path):
            raise RuntimeError("falha")

        monkeypatch.setattr(archive_parser.ArchiveParser, "extract", boom)

        session_code = mgr.session.session_code
        case_dir = Paths.case_dir(session_code)
        # pipeline recebe o ZIP do usuário (não a cópia da session)
        pipeline = PreservationPipeline()
        result = pipeline.execute(
            [sample_zip],
            case_dir=case_dir,
            session_code=session_code,
        )
        fb = result.evidence_files[0]
        original_dir = Paths.evidence_original_dir(session_code)
        assert Path(fb.file_path).parent == original_dir
        assert Path(fb.file_path).resolve() != sample_zip.resolve()
        assert sample_zip.exists()


class TestEndToEndCaseLayout:
    def test_full_flow_structure(
        self, isolated_home: Path, sample_zip: Path
    ):
        mgr = SessionManager()
        session = mgr.start_session(description="fluxo completo")
        code = session.session_code

        ev = mgr.add_evidence(sample_zip)
        case_dir = Paths.case_dir(code)

        pipeline = PreservationPipeline()
        result = pipeline.execute(
            [ev.file_path],
            case_dir=case_dir,
            session_code=code,
            output_dir=case_dir / "reports",
        )

        # case.lexproof.json
        session_file = Paths.session_file_path(code)
        assert session_file.is_file()

        # evidence/original/ com o ZIP
        original_zip = Paths.evidence_original_dir(code) / "conversa.zip"
        assert original_zip.is_file()

        # evidence/extracted/ com membros
        extracted = Paths.evidence_extracted_dir(code)
        assert extracted.is_dir()
        members = list(extracted.rglob("*"))
        assert any(m.is_file() for m in members)

        # Evidence.file_path do pipeline permanentes
        for e in result.evidence_files:
            p = Path(str(e.file_path))
            assert p.is_file()
            assert str(p).startswith(str(case_dir / "evidence"))
            assert "lexproof_zip_" not in str(p)
            # não aponta para o local de origem do usuário
            assert not str(p).startswith(str(sample_zip.parent))

        # session ainda carregável
        fresh = SessionManager()
        loaded = fresh.load_session(session_file)
        assert loaded.evidence_files
        assert Path(str(loaded.evidence_files[0].file_path)).is_file()

        # original do usuário intacto
        assert sample_zip.exists()


class TestOpenCaseClearsTransientState:
    """Gap 3.3: _open_case não pode deixar estado do caso A sobreviver em B."""

    def test_open_case_clears_imported_sources_and_evidence_list(
        self,
        isolated_home: Path,
        qapp,
        monkeypatch: pytest.MonkeyPatch,
    ):
        from lexproof.ui.main_window import MainWindow
        from lexproof.ui.widgets.tour import TourManager

        monkeypatch.setattr(TourManager, "is_first_run", lambda self: False)

        # Caso A: sessão ativa + estado transitório "sujo"
        mgr_a = SessionManager()
        mgr_a.start_session(description="caso A")
        path_a = mgr_a.session_path
        assert path_a is not None and path_a.is_file()

        win = MainWindow(session_manager=mgr_a)
        source_a = str(isolated_home / "downloads" / "prova_A.txt")
        permanent_a = str(
            Paths.evidence_original_dir(mgr_a.session.session_code) / "prova_A.txt"
        )
        win._imported_sources.add(source_a)
        win._evidence_list.append(permanent_a)
        win._evidence_list_widget.add_file(permanent_a)
        assert source_a in win._imported_sources
        assert permanent_a in win._evidence_list

        # Caso B em disco (outra sessão)
        mgr_b = SessionManager()
        mgr_b.start_session(description="caso B")
        path_b = mgr_b.session_path
        assert path_b is not None and path_b.is_file()
        assert path_a != path_b

        monkeypatch.setattr(
            QFileDialog,
            "getOpenFileName",
            lambda *args, **kwargs: (str(path_b), ""),
        )

        win._open_case()

        # Estado do caso A não permanece
        assert source_a not in win._imported_sources
        assert win._imported_sources == set()
        assert permanent_a not in win._evidence_list
        # Lista visual reconstruída só com a sessão B (sem evidências)
        assert win._evidence_list == []
        assert win._evidence_list_widget.get_files() == []
        # Sessão carregada é a B
        assert win._session_manager.session.session_code == mgr_b.session.session_code

        win.close()
