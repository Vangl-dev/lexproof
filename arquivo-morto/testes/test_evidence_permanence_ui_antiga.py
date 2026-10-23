"""Teste da interface antiga, retirado de tests/unit/test_evidence_permanence.py
quando a interface foi arquivada (23/10/2026). Depende das fixtures daquele arquivo."""

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
