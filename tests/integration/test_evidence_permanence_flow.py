"""Integração: fluxo completo de evidência permanente (Etapa 3.3)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from lexproof.config.paths import Paths
from lexproof.core.session import SessionManager
from lexproof.pipeline.preservation import PreservationPipeline


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


def test_new_case_import_zip_process_permanent(isolated_home: Path, tmp_path: Path):
    """novo caso → importar ZIP → processar → layout permanente verificado."""
    user_zip = tmp_path / "downloads" / "conversa.zip"
    user_zip.parent.mkdir()
    with zipfile.ZipFile(user_zip, "w") as zf:
        zf.writestr("export.txt", "15/03/2024 10:00, Ana: ola\n")
        zf.writestr("img/nota.txt", "nota\n")

    # 1. novo caso
    mgr = SessionManager()
    session = mgr.start_session(
        description="caso integracao 3.3",
        client_name="Cliente",
        case_number="PROC-33",
    )
    code = session.session_code
    case_dir = Paths.case_dir(code)

    # 2. importar ZIP (cópia permanente na fronteira)
    ev = mgr.add_evidence(user_zip)
    assert Path(ev.file_path).parent == Paths.evidence_original_dir(code)
    assert Path(ev.file_path).is_file()
    assert user_zip.exists()

    # 3. processar
    pipeline = PreservationPipeline()
    result = pipeline.execute(
        [Path(ev.file_path)],
        case_dir=case_dir,
        session_code=code,
        output_dir=case_dir / "reports",
    )

    # 4. case.lexproof.json
    session_file = Paths.session_file_path(code)
    assert session_file.is_file()

    # 5. evidence/original
    assert (Paths.evidence_original_dir(code) / "conversa.zip").is_file()

    # 6. evidence/extracted
    extracted = Paths.evidence_extracted_dir(code)
    assert any(p.is_file() for p in extracted.rglob("*"))

    # 7. Evidence.file_path do pipeline são permanentes
    assert result.evidence_files
    for e in result.evidence_files:
        p = Path(str(e.file_path))
        assert p.is_file()
        assert str(p).startswith(str(case_dir / "evidence"))
        assert "lexproof_zip_" not in str(p)

    # session reabre com paths permanentes
    fresh = SessionManager()
    loaded = fresh.load_session(session_file)
    assert len(loaded.evidence_files) == 1
    assert Path(str(loaded.evidence_files[0].file_path)).is_file()
