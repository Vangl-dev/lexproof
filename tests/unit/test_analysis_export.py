"""Testes da transcrição para análise e do álbum dos prints."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from lexproof.reports.album import album_items, generate_album
from lexproof.reports.analysis_export import write_analysis_files
from lexproof.triangulation.screenshot_reader import ScreenBubble, ScreenshotReading
from lexproof.triangulation.stitcher import ScreenshotStitcher

D25, D28 = date(2026, 3, 25), date(2026, 3, 28)


def _print(tmp_path: Path, name: str, bubbles: list[ScreenBubble]) -> ScreenshotReading:
    path = tmp_path / name
    Image.new("RGB", (100, 200), "white").save(path)
    return ScreenshotReading(path=path, contact="Carlos", size=(100, 200), bubbles=bubbles)


def _b(text, time, day=None, side="right"):
    return ScreenBubble(text=text, time=time, top=0, date=day, side=side)


@pytest.fixture
def stitched(tmp_path):
    a = _print(tmp_path, "a.jpg", [
        _b("tá demorando?", "10:44", date(2026, 3, 16), side="left"),
        _b("Se vc quiser comprar pão na padaria o cartão tem 14 reais", "08:39", D25),
    ])
    b = _print(tmp_path, "b.jpg", [
        _b("padaria o cartão tem 40 reais", "08:39"),
        _b("Carlos não abre a porta pra ninguém tá", "09:17", D28),
    ])
    c = _print(tmp_path, "c.jpg", [_b("Tô saindo da igreja", "12:09", date(2026, 6, 20))])
    return ScreenshotStitcher().stitch([a, b, c])


def test_prints_only_transcript_marks_sides_contradictions_and_gaps(tmp_path, stitched):
    out = write_analysis_files(tmp_path, {"metadata": {"title": "Caso"}, "stitch": stitched}, None)
    md = (out / "conversa.md").read_text()
    assert "Carlos [esquerda]" in md
    assert "dono do celular que fez os prints [direita]" in md
    assert md.count("CONTRADIÇÃO") == 2
    assert "Lacuna" in md and "Contexto possivelmente incompleto" in md
    assert "### quarta-feira, 25 de março de 2026" in md
    data = json.loads((out / "prints.json").read_text())
    assert data["fonte_do_texto"] == "ocr"
    assert [p["arquivo"] for p in data["prints"]] == ["a.jpg", "b.jpg", "c.jpg"]
    assert all(len(p["sha256"]) == 64 for p in data["prints"])
    assert data["mensagens"][0]["lado"] == "esquerda"


def test_album_orders_by_content_and_counts_pages(tmp_path, stitched):
    d = {"metadata": {"title": "Caso"}, "stitch": stitched}
    items = album_items(d)
    assert [i.path.name for i in items] == ["a.jpg", "b.jpg", "c.jpg"]
    assert items[1].day == D25  # data herdada do balão cortado
    pdf = generate_album(d, tmp_path / "album.pdf")
    assert pdf is not None and pdf.read_bytes().startswith(b"%PDF")
