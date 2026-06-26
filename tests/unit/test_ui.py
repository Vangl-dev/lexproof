"""Testes para a interface do usuario."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from lexproof.ui.icons import SvgIcons, create_icon, get_icon
from lexproof.ui.styles.theme import ThemeManager, ThemeMode
from lexproof.ui.widgets.placeholder_panel import PlaceholderPanel
from lexproof.ui.widgets.case_info_panel import CaseInfoPanel


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestSvgIcons:
    """Testes para o modulo de icones SVG."""

    def test_get_icon_returns_string(self) -> None:
        svg = get_icon("file")
        assert isinstance(svg, str)
        assert "svg" in svg.lower() or "viewBox" in svg

    def test_all_icon_names_available(self) -> None:
        names = [
            "file", "folder", "image", "text", "pdf", "video", "archive",
            "hash", "timeline", "ocr", "report", "shield", "blockchain",
            "settings", "add", "remove", "search", "close", "check",
            "warning", "error", "info", "drag_handle", "menu", "sidebar",
            "log", "export", "import", "case",
        ]
        for name in names:
            svg = get_icon(name)
            assert svg is not None, f"Icon '{name}' not found"

    def test_create_icon_returns_qicon(self, qapp: QApplication) -> None:
        icon = create_icon("file")
        assert icon is not None

    def test_svg_icons_class_methods(self) -> None:
        svg = SvgIcons.file()
        assert isinstance(svg, str)
        svg = SvgIcons.hash()
        assert isinstance(svg, str)


class TestThemeManager:
    """Testes para o gerenciador de temas."""

    def test_singleton(self) -> None:
        tm1 = ThemeManager.instance()
        tm2 = ThemeManager.instance()
        assert tm1 is tm2

    def test_default_mode(self) -> None:
        tm = ThemeManager()
        assert tm.current_mode == ThemeMode.SYSTEM

    def test_set_mode(self) -> None:
        tm = ThemeManager()
        tm.set_mode(ThemeMode.LIGHT)
        assert tm.current_mode == ThemeMode.LIGHT
        tm.set_mode(ThemeMode.DARK)
        assert tm.current_mode == ThemeMode.DARK

    def test_get_stylesheet_light(self) -> None:
        tm = ThemeManager()
        ss = tm.get_stylesheet("light")
        assert isinstance(ss, str)
        assert len(ss) > 100

    def test_get_stylesheet_dark(self) -> None:
        tm = ThemeManager()
        ss = tm.get_stylesheet("dark")
        assert isinstance(ss, str)
        assert len(ss) > 100


class TestPlaceholderPanel:
    """Testes para o painel placeholder."""

    def test_creation(self, qapp: QApplication) -> None:
        panel = PlaceholderPanel("Teste", "Descricao")
        assert panel is not None


class TestCaseInfoPanel:
    """Testes para o painel de informacoes do caso."""

    def test_creation(self, qapp: QApplication) -> None:
        panel = CaseInfoPanel()
        assert panel is not None

    def test_get_data(self, qapp: QApplication) -> None:
        panel = CaseInfoPanel()
        data = panel.get_data()
        assert isinstance(data, dict)

    def test_set_data(self, qapp: QApplication) -> None:
        panel = CaseInfoPanel()
        panel.set_data({"title": "Teste", "client": "Joao"})
        data = panel.get_data()
        assert data["title"] == "Teste"
        assert data["client"] == "Joao"

    def test_clear(self, qapp: QApplication) -> None:
        panel = CaseInfoPanel()
        panel.set_data({"title": "Teste"})
        panel.clear()
        data = panel.get_data()
        assert data["title"] == ""
