"""Testes da leitura do print do perfil do contato."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from lexproof.triangulation.contact_profile import (
    ContactProfile,
    link_profiles,
    parse_profile_text,
    read_contact_profile,
    same_contact,
)


class TestParseProfileText:
    def test_name_above_phone(self):
        lines = ["← ⋮", "Carlos Mendes", "+55 11 98765-4321", "Áudio Vídeo Pesquisar"]
        assert parse_profile_text(lines) == ("Carlos Mendes", "+55 11 98765-4321")

    def test_phone_formats_are_normalized(self):
        assert parse_profile_text(["Ana", "+55 (21) 9 1234-5678"])[1] == "+55 21 91234-5678"
        assert parse_profile_text(["Ana", "+5521912345678"])[1] == "+55 21 91234-5678"
        assert parse_profile_text(["Ana", "+55 11 3456-7890"])[1] == "+55 11 3456-7890"

    def test_interface_words_are_not_names(self):
        assert parse_profile_text(["Dados do contato", "+55 11 98765-4321"]) == ("", "+55 11 98765-4321")

    def test_no_phone(self):
        assert parse_profile_text(["Carlos Mendes", "online"]) is None


def test_same_contact_ignores_accents_case_and_spaces():
    assert same_contact("Carlos Mendes", "CarlosMendes")
    assert same_contact("João", "joao")
    assert not same_contact("Carlos", "Pedro")
    assert not same_contact("", "")


def test_link_profiles():
    ok = ContactProfile(Path("a.jpg"), "Carlos Mendes", "+55 11 98765-4321")
    other = ContactProfile(Path("b.jpg"), "Pedro Silva", "+55 21 91234-0000")
    links = link_profiles([ok, other], "Carlos Mendes", ["CarlosMendes", "Carlos Mendes"])
    assert links[0].ok and links[0].matches_export and links[0].matches_prints
    assert not links[1].ok and links[1].matches_export is False


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract ausente")
def test_reads_rendered_profile_screen(tmp_path):
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.truetype("/usr/share/fonts/noto/NotoSans-Regular.ttf", 64)
        small = ImageFont.truetype("/usr/share/fonts/noto/NotoSans-Regular.ttf", 42)
    except OSError:
        pytest.skip("fonte Noto ausente")
    im = Image.new("RGB", (1080, 2295), (11, 20, 26))
    d = ImageDraw.Draw(im)
    d.text((340, 560), "Carlos Mendes", font=font, fill=(233, 237, 239))
    d.text((360, 670), "+55 11 98765-4321", font=small, fill=(140, 150, 155))
    d.text((150, 860), "Áudio      Vídeo      Pesquisar", font=small, fill=(0, 168, 132))
    path = tmp_path / "Screenshot_20260701144700.jpg"
    im.save(path, quality=92)
    profile = read_contact_profile(path)
    assert profile is not None
    assert (profile.name, profile.phone) == ("Carlos Mendes", "+55 11 98765-4321")
    assert profile.captured_at is not None
