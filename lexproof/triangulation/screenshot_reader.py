"""Leitura estruturada de prints de conversa do WhatsApp.

Extrai do print o nome do contato, os separadores de data ("16 de marco de
2026", "Ontem", "Segunda-feira") e cada balao com seu texto e horario. Os
horarios sao relidos em recorte ampliado, porque sao pequenos demais para o
OCR da pagina inteira.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from lexproof.core.constants import DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)

_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
_WEEKDAYS = {
    "segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6,
}
_FULL_DATE_RE = re.compile(r"^(\d{1,2}) de ([a-z]+)(?: de (\d{4}))?$")
_SLASH_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$")
_WEEKDAY_RE = re.compile(r"^(segunda|terca|quarta|quinta|sexta)(?:-?feira)?$|^(sabado|domingo)$")
_TIME_LIKE_RE = re.compile(r"^[\dOoSlI|:;.,\->]{3,8}$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_CALL_RE = re.compile(
    r"(liga[cç][aã]o|chamada) (de voz|de v[ií]deo|perdida)|voice call|video call|missed",
    re.IGNORECASE,
)
_DOCUMENT_RE = re.compile(r"\b\d+\s+p[aá]ginas?\b|\b\d+(?:[.,]\d+)?\s?[kKmM]B\b|\bPDF\b|\bDOCX?\b")
_READ_MORE_RE = re.compile(r"\s*(?:\.{2,}|…)?\s*(?:Ler mais|Read more)\s*$", re.IGNORECASE)
# Palavras com confianca do Tesseract abaixo disto sao lixo de OCR (linha cortada
# na borda, miniatura de documento); o texto legivel fica acima de 80.
_MIN_WORD_CONFIDENCE = 30

_CAPTURE_NAME_RE = re.compile(
    r"(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})[-_. ]?(?:at )?(\d{2})[-_.:h]?(\d{2})[-_.:m]?(\d{2})"
)

# Balao recebido comeca rente a borda esquerda; o enviado, mais para dentro.
_LEFT_SIDE_MAX = 0.11

# Faixas de cabecalho (nome do contato) e rodape (campo "Mensagem")
_HEADER_FRACTION = 0.06
# Com barra de status (relogio) visivel, a barra do contato fica mais abaixo.
_HEADER_FRACTION_WITH_STATUS = 0.09
_FOOTER_FRACTION = 0.90


@dataclass
class ScreenBubble:
    """Um balao de mensagem visivel no print."""

    text: str
    time: Optional[str]
    top: int
    kind: str = "text"  # text, call ou document
    date: Optional[date] = None
    date_label: Optional[str] = None
    # Mensagem longa mostrada pela metade ("... Ler mais")
    truncated: bool = False
    # "left": recebida (contato); "right": enviada (dono do celular que fez o print)
    side: Optional[str] = None


@dataclass
class ScreenshotReading:
    """Conteudo estruturado de um print."""

    path: Path
    contact: str = ""
    captured_at: Optional[datetime] = None
    captured_at_source: str = ""
    dark_mode: bool = False
    size: Optional[tuple[int, int]] = None
    status_clock: Optional[str] = None
    # Data informada pelo usuario para resolver "Ontem" e dias da semana quando
    # o arquivo nao traz a data do print
    reference_date: Optional[date] = None
    bubbles: list[ScreenBubble] = field(default_factory=list)
    date_labels: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def first_separator_date(self) -> Optional[date]:
        for b in self.bubbles:
            if b.date is not None:
                return b.date
        return None


def _fold(text: str) -> str:
    """Minusculas, sem acentos e com espacos normalizados."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip()


def capture_time_from_file(path: Path, tz: ZoneInfo) -> tuple[Optional[datetime], str]:
    """Horario em que o print foi tirado: nome do arquivo ou EXIF."""
    m = _CAPTURE_NAME_RE.search(path.name)
    if m:
        try:
            y, mo, d, hh, mi, ss = (int(g) for g in m.groups())
            return datetime(y, mo, d, hh, mi, ss, tzinfo=tz), "nome do arquivo"
        except ValueError:
            pass
    try:
        from PIL import Image

        with Image.open(path) as img:
            exif = img.getexif()
            raw = exif.get_ifd(0x8769).get(0x9003) or exif.get(0x0132)
        if raw:
            return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").replace(tzinfo=tz), "EXIF"
    except Exception:
        pass
    return None, ""


def resolve_date_label(label: str, captured: Optional[date]) -> Optional[date]:
    """Converte um separador de data do WhatsApp em data.

    Rotulos relativos ("Hoje", "Ontem", dia da semana) e datas sem ano
    dependem da data do print.
    """
    folded = _fold(label)
    m = _FULL_DATE_RE.match(folded)
    if m and m.group(2) in _MONTHS:
        day, month = int(m.group(1)), _MONTHS[m.group(2)]
        if m.group(3):
            year = int(m.group(3))
        elif captured is not None:
            year = captured.year
            if (month, day) > (captured.month, captured.day):
                year -= 1
        else:
            return None
        try:
            return date(year, month, day)
        except ValueError:
            return None
    m = _SLASH_DATE_RE.match(folded)
    if m:
        year = int(m.group(3))
        year += 2000 if year < 100 else 0
        try:
            return date(year, int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    if captured is None:
        return None
    if folded == "hoje":
        return captured
    if folded == "ontem":
        return captured - timedelta(days=1)
    m = _WEEKDAY_RE.match(folded)
    if m:
        target = _WEEKDAYS[m.group(1) or m.group(2)]
        delta = (captured.weekday() - target) % 7 or 7
        return captured - timedelta(days=delta)
    return None


def is_date_label(text: str) -> bool:
    folded = _fold(text)
    if folded in ("hoje", "ontem"):
        return True
    m = _FULL_DATE_RE.match(folded)
    if m and m.group(2) in _MONTHS:
        return True
    return bool(_SLASH_DATE_RE.match(folded) or _WEEKDAY_RE.match(folded))


class ScreenshotReader:
    """Le prints de conversa com Tesseract."""

    def __init__(self, timezone_name: str = DEFAULT_TIMEZONE, lang: str = "por") -> None:
        self._tz = ZoneInfo(timezone_name)
        self._lang = lang

    def read(self, path: Path, reference_date: Optional[date] = None) -> ScreenshotReading:
        path = Path(path)
        reading = ScreenshotReading(path=path)
        reading.captured_at, reading.captured_at_source = capture_time_from_file(path, self._tz)
        if reading.captured_at is None:
            reading.reference_date = reference_date
        try:
            self._read_into(reading)
        except Exception as exc:
            logger.warning("Falha ao ler print %s: %s", path.name, exc)
            reading.error = str(exc)
        return reading

    # ------------------------------------------------------------------

    def _read_into(self, reading: ScreenshotReading) -> None:
        import pytesseract
        from PIL import Image, ImageOps, ImageStat
        from pytesseract import Output

        with Image.open(reading.path) as img:
            gray = img.convert("L")
            reading.size = img.size
        reading.dark_mode = ImageStat.Stat(gray).mean[0] < 110
        page = ImageOps.invert(gray) if reading.dark_mode else gray
        height = page.height

        data = pytesseract.image_to_data(
            page, lang=self._lang, config="--psm 4", output_type=Output.DICT
        )
        lines = _group_lines(data)

        captured_date = reading.captured_at.date() if reading.captured_at else reading.reference_date
        width = page.width
        current_date: Optional[date] = None
        current_label: Optional[str] = None
        pending: list[str] = []
        pending_top: Optional[int] = None
        pending_left: Optional[int] = None

        header_limit = height * _HEADER_FRACTION
        for line in lines:
            if line["top"] < header_limit:
                first = _normalize_time(line["words"][0]["text"])
                if reading.status_clock is None and not reading.contact and _TIME_RE.match(first):
                    reading.status_clock = first
                    header_limit = height * _HEADER_FRACTION_WITH_STATUS
                elif not reading.contact:
                    reading.contact = _clean_contact(line["words"])
                continue
            if line["top"] > height * _FOOTER_FRACTION:
                continue
            line = _clean_body_line(line)
            if line is None:
                continue

            text = " ".join(w["text"] for w in line["words"]).strip()
            if is_date_label(text):
                self._flush_call(reading, pending, pending_top, current_date, current_label)
                pending, pending_top, pending_left = [], None, None
                current_label = text
                current_date = resolve_date_label(text, captured_date)
                reading.date_labels.append(text)
                continue

            time_idx = _find_time_token(line["words"])
            line_left = min(w["left"] for w in line["words"])
            if time_idx is None:
                if len(text) >= 2:
                    pending.append(text)
                    pending_top = line["top"] if pending_top is None else pending_top
                    pending_left = line_left if pending_left is None else min(pending_left, line_left)
                continue

            body = " ".join(w["text"] for w in line["words"][:time_idx]).strip()
            if body:
                pending.append(body)
                pending_top = line["top"] if pending_top is None else pending_top
                pending_left = line_left if pending_left is None else min(pending_left, line_left)
            time_word = line["words"][time_idx]
            bubble_text = " ".join(pending).strip()
            truncated = bool(_READ_MORE_RE.search(bubble_text))
            if truncated:
                bubble_text = _READ_MORE_RE.sub("", bubble_text).rstrip(" .…")
            kind = "call" if _CALL_RE.search(bubble_text) else "text"
            if kind == "text" and _DOCUMENT_RE.search(bubble_text):
                kind = "document"
            if kind == "call":
                bubble_text = _CALL_RE.search(bubble_text).group(0)
            if bubble_text or kind == "call":
                reading.bubbles.append(ScreenBubble(
                    text=bubble_text,
                    time=self._read_time(page, time_word),
                    top=pending_top if pending_top is not None else line["top"],
                    kind=kind,
                    date=current_date,
                    date_label=current_label,
                    truncated=truncated,
                    side=None if pending_left is None else (
                        "left" if pending_left < width * _LEFT_SIDE_MAX else "right"),
                ))
            pending, pending_top, pending_left = [], None, None

        self._flush_call(reading, pending, pending_top, current_date, current_label)

    @staticmethod
    def _flush_call(
        reading: ScreenshotReading,
        pending: list[str],
        top: Optional[int],
        current_date: Optional[date],
        current_label: Optional[str],
    ) -> None:
        """Registra balao de ligacao cujo horario ficou ilegivel."""
        m = _CALL_RE.search(" ".join(pending))
        if m:
            reading.bubbles.append(ScreenBubble(
                text=m.group(0), time=None, top=top or 0, kind="call",
                date=current_date, date_label=current_label,
            ))

    def _read_time(self, page: Any, word: dict[str, Any]) -> Optional[str]:
        """Rele o horario de um balao em recorte ampliado so com digitos."""
        import pytesseract
        from PIL import Image

        candidates = [_normalize_time(word["text"])]
        try:
            box = (
                max(word["left"] - 12, 0), max(word["top"] - 8, 0),
                word["left"] + word["width"] + 12, word["top"] + word["height"] + 8,
            )
            crop = page.crop(box)
            crop = crop.resize((crop.width * 4, crop.height * 4), Image.LANCZOS)
            crop = crop.point(lambda p: 0 if p < 150 else 255)
            text = pytesseract.image_to_string(
                crop, config="--psm 7 -c tessedit_char_whitelist=0123456789:"
            ).strip()
            candidates.insert(0, _normalize_time(text))
        except Exception as exc:
            logger.debug("Releitura de horario falhou: %s", exc)
        for c in candidates:
            if c and _TIME_RE.match(c):
                return c
        return None


def _group_lines(data: dict[str, list[Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, int, int], dict[str, Any]] = {}
    for i, raw in enumerate(data["text"]):
        text = str(raw).strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (KeyError, TypeError, ValueError):
            conf = 100.0
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        word = {
            "text": text, "conf": conf,
            "left": data["left"][i], "top": data["top"][i],
            "width": data["width"][i], "height": data["height"][i],
        }
        line = groups.setdefault(key, {"top": word["top"], "words": []})
        line["top"] = min(line["top"], word["top"])
        line["words"].append(word)
    return sorted(groups.values(), key=lambda ln: ln["top"])


def _clean_body_line(line: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Linha do corpo da conversa sem o lixo de OCR.

    Descarta palavras com confianca baixa (linha cortada na borda, miniatura de
    documento), exceto horarios, que sao relidos depois; e linhas so de letras
    soltas ("d D D D"), que sao icones lidos como texto.
    """
    words = [
        w for w in line["words"]
        if w.get("conf", 100.0) >= _MIN_WORD_CONFIDENCE or sum(c.isdigit() for c in w["text"]) >= 2
    ]
    if not any(len(w["text"]) > 1 for w in words):
        return None
    return {"top": line["top"], "words": words}


def _find_time_token(words: list[dict[str, Any]]) -> Optional[int]:
    """Indice do horario do balao: um dos ultimos tokens da linha.

    O que vem depois dele sao os tiques de leitura, lidos como lixo.
    """
    for idx in range(len(words) - 1, max(len(words) - 4, -1), -1):
        t = words[idx]["text"]
        if _TIME_LIKE_RE.match(t) and sum(c.isdigit() for c in t) >= 2:
            return idx
    return None


def _normalize_time(text: str) -> str:
    table = str.maketrans({"O": "0", "o": "0", "S": "5", "l": "1", "I": "1", "|": "1", ";": ":", ".": ":", ",": ":"})
    t = text.translate(table)
    digits = re.sub(r"\D", "", t)
    if ":" not in t and len(digits) == 4:
        return f"{digits[:2]}:{digits[2:]}"
    m = re.search(r"(\d{1,2}):(\d{2})", t)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return t


def _clean_contact(words: list[dict[str, Any]]) -> str:
    """Nome no cabecalho da conversa, sem os icones lidos como texto."""
    kept: list[str] = []
    for w in words:
        t = w["text"]
        if len(t) < 2 or not any(c.isalpha() for c in t):
            continue
        kept.append(t)
        if t.endswith(("...", "…")):
            break  # nome truncado; o que vem depois sao os icones
    # Icones de video/ligacao a direita costumam virar tokens curtos ("R.", "M").
    while len(kept) > 1 and len(kept[-1].strip(".")) <= 2:
        kept.pop()
    return " ".join(kept).strip()
