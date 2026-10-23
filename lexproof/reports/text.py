"""Formatacao de textos e datas para o relatorio e a interface."""

from __future__ import annotations

import re
import unicodedata
from datetime import timezone
from typing import Any
from zoneinfo import ZoneInfo

from lexproof.core.constants import DEFAULT_TIMEZONE

# Faixas que a fonte do relatorio (Noto Sans) desenha; o resto vira "?".
_PRINTABLE = (
    (0x0020, 0x024F),  # latim, incluindo acentos
    (0x2010, 0x2027),  # travessoes, aspas curvas, reticencias
    (0x20AC, 0x20AC),  # euro
)


def _printable(c: str) -> bool:
    o = ord(c)
    return any(a <= o <= b for a, b in _PRINTABLE)


def safe_text(text: Any) -> str:
    """Texto exibivel: letras estilizadas viram comuns, emojis viram [emoji]."""
    t = unicodedata.normalize("NFKC", str(text or ""))
    t = "".join(
        "\x00" if unicodedata.category(c) in ("So", "Cs") or ord(c) > 0xFFFF else c
        for c in t
    )
    t = re.sub("\x00+", "[emoji]", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Cf")
    t = "".join(c if _printable(c) or c in "\n\t" else "?" for c in unicodedata.normalize("NFC", t))
    t = t.replace("?️", "").replace("[emoji]?", "[emoji]")
    return re.sub(r"\s+", " ", t).strip()


def person_name(text: Any) -> str:
    """Nome de pessoa sem os emojis decorativos."""
    return safe_text(text).replace("[emoji]", "").strip()


def local_time(dt: Any, with_utc: bool = True) -> str:
    """Data/hora no fuso de Brasilia (com o equivalente UTC)."""
    if dt is None:
        return "-"
    local = dt.astimezone(ZoneInfo(DEFAULT_TIMEZONE))
    text = f"{local:%d/%m/%Y às %H:%M:%S} (Brasília)"
    if with_utc:
        text += f" = {dt.astimezone(timezone.utc):%H:%M:%S} UTC"
    return text
