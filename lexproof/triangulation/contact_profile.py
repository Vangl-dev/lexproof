"""Leitura do print da tela de perfil do contato ("Dados do contato").

A exportacao e o cabecalho dos prints mostram so o nome salvo na agenda de
quem exportou. O perfil do contato mostra esse nome e, logo abaixo, o numero
de telefone. Um print dessa tela liga o nome ao numero.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from lexproof.core.constants import DEFAULT_TIMEZONE
from lexproof.triangulation.screenshot_reader import capture_time_from_file

logger = logging.getLogger(__name__)

# "+" seguido de digitos e separadores; o total de digitos e conferido depois.
_PHONE_RE = re.compile(r"\+[\d\s.\-()]{9,24}\d")
# Textos da propria interface do WhatsApp que aparecem perto do nome
_UI_WORDS = {
    "dados do contato", "contact info", "audio", "video", "pesquisar", "search", "pagar",
    "recado", "about", "midia, links e docs", "media, links and docs", "editar", "edit",
}


@dataclass
class ContactProfile:
    """Nome e numero lidos no print do perfil."""

    path: Path
    name: str
    phone: str
    captured_at: Optional[datetime] = None

    @property
    def phone_digits(self) -> str:
        return re.sub(r"\D", "", self.phone)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return re.sub(r"\s+", " ", "".join(c for c in text if not unicodedata.combining(c)).lower()).strip()


def _clean_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("55") and len(digits) in (12, 13):
        local = digits[4:]
        return f"+55 {digits[2:4]} {local[:-4]}-{local[-4:]}"
    return "+" + digits


def parse_profile_text(lines: list[str]) -> Optional[tuple[str, str]]:
    """(nome, telefone) a partir das linhas de OCR de uma tela de perfil."""
    for idx, line in enumerate(lines):
        m = _PHONE_RE.search(line)
        if not m or not 10 <= len(re.sub(r"\D", "", m.group(0))) <= 15:
            continue
        phone = _clean_phone(m.group(0))
        # O nome fica logo acima do numero e pode ocupar duas linhas
        # ("Paulo Ricardo Souza Adv" / "(Inventario Helena)").
        parts: list[str] = []
        for prev in reversed(lines[:idx]):
            candidate = prev.strip(" ~<>-:|")
            if (
                len(candidate) >= 2
                and sum(c.isalpha() for c in candidate) >= 2
                and _fold(candidate) not in _UI_WORDS
                and not re.match(r"^\d{1,2}:\d{2}", candidate)
            ):
                parts.insert(0, candidate)
                if len(parts) == 2 or not candidate.startswith("("):
                    break
            elif parts:
                break
        return " ".join(parts), phone
    return None


def read_contact_profile(path: Path, lang: str = "por") -> Optional[ContactProfile]:
    """Le *path*; devolve o perfil se for um print da tela de dados do contato."""
    import pytesseract
    from PIL import Image, ImageOps, ImageStat

    path = Path(path)
    try:
        with Image.open(path) as img:
            gray = img.convert("L")
        if ImageStat.Stat(gray).mean[0] < 110:
            gray = ImageOps.invert(gray)
        # O perfil fica na metade de cima da tela.
        top = gray.crop((0, 0, gray.width, gray.height // 2))
        text = pytesseract.image_to_string(top, lang=lang, config="--psm 4")
    except Exception as exc:
        logger.warning("Falha ao ler perfil em %s: %s", path.name, exc)
        return None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    parsed = parse_profile_text(lines)
    if parsed is None:
        return None
    captured, _ = capture_time_from_file(path, ZoneInfo(DEFAULT_TIMEZONE))
    return ContactProfile(path=path, name=parsed[0], phone=parsed[1], captured_at=captured)


def same_contact(a: str, b: str) -> bool:
    """Mesmo nome, desconsiderando acentos, caixa, espacos e truncamento."""
    from lexproof.triangulation.matcher import names_match

    return names_match(a, b)


@dataclass
class ContactLink:
    """Perfil confrontado com o contato da conversa e dos prints."""

    profile: ContactProfile
    export_contact: Optional[str] = None
    matches_export: Optional[bool] = None
    print_contact: Optional[str] = None
    matches_prints: Optional[bool] = None

    @property
    def ok(self) -> bool:
        return bool(self.profile.name) and self.matches_export is not False and self.matches_prints is not False


def link_profiles(
    profiles: list[ContactProfile], export_contact: Optional[str], print_contacts: list[str]
) -> list[ContactLink]:
    """Confere o nome de cada perfil com a exportacao e com o cabecalho dos prints."""
    from collections import Counter

    counts = Counter(_fold(c).replace(" ", "") for c in print_contacts if c)
    main_print = None
    if counts:
        key = counts.most_common(1)[0][0]
        main_print = next(c for c in print_contacts if c and _fold(c).replace(" ", "") == key)
    links = []
    for p in profiles:
        link = ContactLink(profile=p, export_contact=export_contact, print_contact=main_print)
        if export_contact:
            link.matches_export = same_contact(p.name, export_contact)
        if main_print:
            link.matches_prints = same_contact(p.name, main_print)
        links.append(link)
    return links
